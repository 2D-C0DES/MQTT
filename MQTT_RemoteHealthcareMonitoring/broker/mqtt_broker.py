"""
MQTT Broker Simulation
======================
Simulates the EMQX/MQTTx broker behavior described in the paper:

  - Publish-Subscribe architecture (OASIS standard)
  - Topic-based message routing
  - QoS Level 0, 1, 2 support with retransmission logic
  - Access Control Lists (ACLs) — topic-level, NOT payload-visible
  - Clinician-specific subscriptions (Table 5 of paper)
  - Broker-broker communication for patient mobility
  - Session persistence (clean_session=True/False)
  - Retained message handling (Table 9 of paper)
  - MQTT message format: fixed header + variable header + payload

MQTT Topics managed (paper Section: Security analysis):
  health/status
  medication/update
  symptom/reporting
  wellness/tips

Fixed Header format (Fig. 6):
  Byte 1: Control Field (Payload type + Flags)
  Bytes 2-5: Remaining Length

Variable Header (Fig. 7):
  Protocol Name Length (2 bytes)
  Protocol Name
  Protocol Level
  Connect Flag
  Keep Alive
"""

import threading
import queue
import time
import uuid
import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Set
from enum import IntEnum


# ─────────────────────────────────────────────
#  QoS Levels (paper Table 4 / Section QoS)
# ─────────────────────────────────────────────

class QoSLevel(IntEnum):
    AT_MOST_ONCE  = 0   # QoS 0 (00) – fire and forget
    AT_LEAST_ONCE = 1   # QoS 1 (01) – acknowledged delivery
    EXACTLY_ONCE  = 2   # QoS 2 (10) – guaranteed, no duplicates


# ─────────────────────────────────────────────
#  MQTT Fixed Header (Fig. 6 of paper)
# ─────────────────────────────────────────────

@dataclass
class MQTTFixedHeader:
    """
    2-5 byte fixed header.
    Byte 1: Control Field = [MessageType(4bits) | Flags(4bits)]
    Bytes 2-5: Remaining Length (variable encoding)
    """
    message_type: str         # CONNECT, CONNACK, PUBLISH, PUBACK, SUBSCRIBE, SUBACK, etc.
    dup_flag: bool = False
    qos_level: QoSLevel = QoSLevel.AT_MOST_ONCE
    retain: bool = False
    remaining_length: int = 0

    MSG_TYPES = {
        "CONNECT": 0x10, "CONNACK": 0x20, "PUBLISH": 0x30,
        "PUBACK": 0x40, "PUBREC": 0x50, "PUBREL": 0x60,
        "PUBCOMP": 0x70, "SUBSCRIBE": 0x80, "SUBACK": 0x90,
        "UNSUBSCRIBE": 0xA0, "UNSUBACK": 0xB0,
        "PINGREQ": 0xC0, "PINGRESP": 0xD0, "DISCONNECT": 0xE0
    }

    def encode(self) -> bytes:
        ctrl = self.MSG_TYPES.get(self.message_type, 0x30)
        flags = (
            (0x08 if self.dup_flag else 0) |
            (self.qos_level << 1) |
            (0x01 if self.retain else 0)
        )
        byte1 = ctrl | flags
        # Variable-length remaining length encoding
        x = self.remaining_length
        rem_bytes = b""
        while True:
            enc = x % 128
            x //= 128
            if x > 0:
                enc |= 0x80
            rem_bytes += bytes([enc])
            if x == 0:
                break
        return bytes([byte1]) + rem_bytes

    def size_bytes(self) -> int:
        # 1 (control) + 1-4 (remaining length)
        if self.remaining_length < 128:      return 2
        if self.remaining_length < 16384:    return 3
        if self.remaining_length < 2097152:  return 4
        return 5


# ─────────────────────────────────────────────
#  MQTT Variable Header (Fig. 7 of paper)
# ─────────────────────────────────────────────

@dataclass
class MQTTVariableHeader:
    """
    Variable header for CONNECT packet.
    Fields: Protocol Name Length | Protocol Name | Protocol Level | Connect Flag | Keep Alive
    """
    protocol_name: str = "MQTT"
    protocol_level: int = 4          # MQTTv3.1.1
    connect_flags: int = 0b11000010  # User+Pass+CleanSession
    keep_alive: int = 60             # seconds

    def encode(self) -> bytes:
        name_bytes = self.protocol_name.encode('utf-8')
        name_len = len(name_bytes)
        return (
            bytes([0x00, name_len]) +   # Protocol Name Length (2 bytes)
            name_bytes +                # Protocol Name
            bytes([self.protocol_level, self.connect_flags]) +
            bytes([self.keep_alive >> 8, self.keep_alive & 0xFF])
        )

    def size_bytes(self) -> int:
        return 2 + len(self.protocol_name) + 4


# ─────────────────────────────────────────────
#  MQTT Message (full packet)
# ─────────────────────────────────────────────

@dataclass
class MQTTMessage:
    """Complete MQTT message as transmitted over the wire."""
    msg_id: str
    topic: str
    payload: str                      # Base64-encoded ciphertext
    qos: QoSLevel
    retain: bool
    publisher_id: str
    timestamp: float = field(default_factory=time.time)
    packet_id: int = field(default_factory=lambda: int(uuid.uuid4()) & 0xFFFF)
    acked: bool = False
    topic_length: int = 0
    message_length: int = 0

    def __post_init__(self):
        self.topic_length = len(self.topic.encode())
        self.message_length = len(self.payload.encode())

    def wire_size(self) -> int:
        """Calculate total packet size on wire (bytes)."""
        fixed_hdr = 2
        topic_bytes = 2 + self.topic_length
        packet_id_bytes = 2 if self.qos > 0 else 0
        payload_bytes = self.message_length
        return fixed_hdr + topic_bytes + packet_id_bytes + payload_bytes

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "topic": self.topic,
            "payload_b64": self.payload,
            "payload_length": self.message_length,
            "topic_length": self.topic_length,
            "wire_size_bytes": self.wire_size(),
            "qos": int(self.qos),
            "retain": self.retain,
            "publisher_id": self.publisher_id,
            "packet_id": self.packet_id,
            "timestamp": self.timestamp,
            "acked": self.acked,
        }


# ─────────────────────────────────────────────
#  Access Control List (ACL) – Paper Table 5
# ─────────────────────────────────────────────

class ACLManager:
    """
    Topic-level Access Control Lists.
    Broker enforces these WITHOUT reading payload (payload is OTP-encrypted).
    
    Default roles (Table 5):
      Cardiologist    → health/status, medication/update
      General Physician → all four topics
      Psychologist    → symptom/reporting, wellness/tips
      Pharmacologist  → medication/update only
      Patient         → publish to all (own topics), subscribe to responses
    """

    TOPICS = [
        "health/status",
        "medication/update",
        "symptom/reporting",
        "wellness/tips"
    ]

    DEFAULT_ROLE_SUBSCRIPTIONS = {
        "Cardiologist":       {"health/status", "medication/update"},
        "General Physician":  {"health/status", "medication/update",
                               "symptom/reporting", "wellness/tips"},
        "Psychologist":       {"symptom/reporting", "wellness/tips"},
        "Pharmacologist":     {"medication/update"},
        "Patient":            set(),   # Publishers only
    }

    def __init__(self):
        self._client_roles: Dict[str, str] = {}
        self._client_publish_allowed: Dict[str, Set[str]] = {}
        self._client_subscribe_allowed: Dict[str, Set[str]] = {}

    def register_client(self, client_id: str, role: str,
                        publish_topics: Set[str] = None,
                        subscribe_topics: Set[str] = None):
        self._client_roles[client_id] = role
        # Publish
        if publish_topics is not None:
            self._client_publish_allowed[client_id] = publish_topics
        elif role == "Patient":
            self._client_publish_allowed[client_id] = set(self.TOPICS)
        else:
            self._client_publish_allowed[client_id] = set()
        # Subscribe
        if subscribe_topics is not None:
            self._client_subscribe_allowed[client_id] = subscribe_topics
        else:
            self._client_subscribe_allowed[client_id] = (
                self.DEFAULT_ROLE_SUBSCRIPTIONS.get(role, set()).copy()
            )

    def can_publish(self, client_id: str, topic: str) -> bool:
        return topic in self._client_publish_allowed.get(client_id, set())

    def can_subscribe(self, client_id: str, topic: str) -> bool:
        return topic in self._client_subscribe_allowed.get(client_id, set())

    def get_allowed_topics(self, client_id: str) -> dict:
        return {
            "role": self._client_roles.get(client_id, "unknown"),
            "can_publish": list(self._client_publish_allowed.get(client_id, set())),
            "can_subscribe": list(self._client_subscribe_allowed.get(client_id, set())),
        }


# ─────────────────────────────────────────────
#  Session Manager (persistent sessions)
# ─────────────────────────────────────────────

@dataclass
class ClientSession:
    client_id: str
    clean_session: bool
    subscriptions: Set[str] = field(default_factory=set)
    queued_messages: list = field(default_factory=list)   # for offline delivery
    connected: bool = False
    last_seen: float = field(default_factory=time.time)
    keep_alive: int = 60


# ─────────────────────────────────────────────
#  MQTT Broker Core
# ─────────────────────────────────────────────

class MQTTBroker:
    """
    Full MQTT broker simulation (EMQX/MQTTx model).

    Handles:
      - CONNECT / CONNACK handshake
      - SUBSCRIBE / SUBACK per topic
      - PUBLISH routing with QoS 0/1/2
      - PUBACK acknowledgement
      - Retained messages (Table 9, TC-01, TC-02)
      - Persistent sessions (Table 9, TC-03, TC-04)
      - ACL enforcement
      - Packet statistics (Table 13)
      - QoS trip-time simulation (Table 12)
    """

    def __init__(self, broker_id: str = "broker.emqx.io", 
                 location: str = "Zone-A"):
        self.broker_id = broker_id
        self.location = location
        self.acl = ACLManager()

        # State
        self._sessions: Dict[str, ClientSession] = {}
        self._retained: Dict[str, MQTTMessage] = {}    # topic -> last retained msg
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)  # topic -> callbacks
        self._message_log: List[dict] = []
        self._packet_stats: Dict[str, int] = defaultdict(int)

        # QoS tracking
        self._pending_acks: Dict[str, MQTTMessage] = {}   # packet_id -> message

        self._lock = threading.Lock()
        self.running = True
        print(f"[BROKER] {broker_id} @ {location} initialized")

    # ── Client registration ──────────────────────────────────

    def connect_client(self, client_id: str, username: str, password: str,
                       role: str, clean_session: bool = True,
                       keep_alive: int = 60) -> dict:
        """Simulate CONNECT → CONNACK handshake."""
        with self._lock:
            # Authentication
            auth_ok = self._authenticate(username, password)
            if not auth_ok:
                return {"status": "CONNACK", "return_code": 5, "msg": "NOT AUTHORIZED"}

            # Session handling (TC-03, TC-04)
            if client_id in self._sessions and not clean_session:
                # Resume existing session
                session = self._sessions[client_id]
                session.connected = True
                session.last_seen = time.time()
                resumed = True
            else:
                session = ClientSession(
                    client_id=client_id,
                    clean_session=clean_session,
                    keep_alive=keep_alive
                )
                self._sessions[client_id] = session
                resumed = False

            # ACL registration
            self.acl.register_client(client_id, role)
            session.connected = True

            self._packet_stats["CONNECT"] += 1
            self._packet_stats["CONNACK"] += 1

            return {
                "status": "CONNACK",
                "return_code": 0,
                "session_present": resumed,
                "client_id": client_id,
                "role": role,
                "msg": "CONNECTION ACCEPTED"
            }

    def _authenticate(self, username: str, password: str) -> bool:
        """Simple credential check (EMQX pattern)."""
        # Simulated: any non-empty credentials accepted
        return bool(username and password)

    def disconnect_client(self, client_id: str):
        with self._lock:
            if client_id in self._sessions:
                session = self._sessions[client_id]
                if session.clean_session:
                    del self._sessions[client_id]
                else:
                    session.connected = False
                    session.last_seen = time.time()

    # ── Subscribe ────────────────────────────────────────────

    def subscribe(self, client_id: str, topics: List[str],
                  callback: Callable) -> dict:
        """SUBSCRIBE → SUBACK. Enforces ACL."""
        results = []
        with self._lock:
            session = self._sessions.get(client_id)
            if not session:
                return {"status": "ERROR", "msg": "Client not connected"}

            for topic in topics:
                if self.acl.can_subscribe(client_id, topic):
                    session.subscriptions.add(topic)
                    self._callbacks[topic].append((client_id, callback))
                    results.append({"topic": topic, "result": "SUBACK_QOS1"})

                    # Deliver retained message immediately (TC-02)
                    if topic in self._retained:
                        retained_msg = self._retained[topic]
                        threading.Thread(
                            target=callback,
                            args=(retained_msg,),
                            daemon=True
                        ).start()
                else:
                    results.append({"topic": topic, "result": "NOT_AUTHORIZED"})

            self._packet_stats["SUBSCRIBE"] += 1
            self._packet_stats["SUBACK"] += 1

        return {"status": "SUBACK", "topics": results}

    # ── Publish ──────────────────────────────────────────────

    def publish(self, client_id: str, topic: str, payload: str,
                qos: QoSLevel = QoSLevel.AT_MOST_ONCE,
                retain: bool = False,
                msg_id: str = None) -> dict:
        """PUBLISH with QoS handling and ACL check."""
        if not self.acl.can_publish(client_id, topic):
            return {"status": "ERROR", "msg": f"ACL DENIED: {client_id} → {topic}"}

        msg = MQTTMessage(
            msg_id=msg_id or str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain,
            publisher_id=client_id,
        )

        with self._lock:
            # Retained message handling (TC-01)
            if retain:
                self._retained[topic] = msg

            self._message_log.append(msg.to_dict())
            self._packet_stats["PUBLISH"] += 1

            # Track pending for QoS ≥ 1
            if qos >= QoSLevel.AT_LEAST_ONCE:
                self._pending_acks[str(msg.packet_id)] = msg

        # Route to subscribers
        delivered = self._route(msg)

        # QoS handshake simulation
        ack_info = {}
        if qos == QoSLevel.AT_LEAST_ONCE:
            ack_info = self._simulate_puback(msg)
        elif qos == QoSLevel.EXACTLY_ONCE:
            ack_info = self._simulate_pubcomp(msg)

        return {
            "status": "PUBLISHED",
            "msg_id": msg.msg_id,
            "packet_id": msg.packet_id,
            "topic": topic,
            "wire_size_bytes": msg.wire_size(),
            "topic_length": msg.topic_length,
            "message_length": msg.message_length,
            "delivered_to": delivered,
            "qos": int(qos),
            "retain": retain,
            **ack_info
        }

    def _route(self, msg: MQTTMessage) -> List[str]:
        """Route message to all matching subscribers."""
        delivered = []
        callbacks = self._callbacks.get(msg.topic, [])
        for (sub_id, cb) in callbacks:
            session = self._sessions.get(sub_id)
            if session and session.connected:
                threading.Thread(target=cb, args=(msg,), daemon=True).start()
                delivered.append(sub_id)
                self._packet_stats[f"DELIVERED_{msg.topic}"] += 1
            elif session and not session.clean_session:
                # Queue for offline delivery (TC-03)
                session.queued_messages.append(msg)
        self._packet_stats["ROUTE"] += 1
        return delivered

    def _simulate_puback(self, msg: MQTTMessage) -> dict:
        """Simulate QoS 1 PUBACK with realistic delay."""
        delay_ms = 5 + (len(msg.payload) * 0.01)
        time.sleep(delay_ms / 1000)
        with self._lock:
            pid = str(msg.packet_id)
            if pid in self._pending_acks:
                self._pending_acks[pid].acked = True
                del self._pending_acks[pid]
        self._packet_stats["PUBACK"] += 1
        return {"qos1_ack": "PUBACK", "ack_delay_ms": round(delay_ms, 2)}

    def _simulate_pubcomp(self, msg: MQTTMessage) -> dict:
        """Simulate QoS 2 PUBREC → PUBREL → PUBCOMP flow."""
        time.sleep(0.010)
        self._packet_stats["PUBREC"] += 1
        time.sleep(0.005)
        self._packet_stats["PUBREL"] += 1
        time.sleep(0.005)
        self._packet_stats["PUBCOMP"] += 1
        return {"qos2_flow": "PUBREC→PUBREL→PUBCOMP"}

    # ── Broker-Broker Handover (patient mobility) ────────────

    def handover_session(self, client_id: str, target_broker: "MQTTBroker"):
        """
        Transfer a mobile patient's session to a new broker zone.
        Paper: 'broker-broker communication to exchange configuration
                and authentication information of a mobile node'
        Transfers: session state, ACL role, topic subscriptions, callbacks.
        """
        with self._lock:
            session = self._sessions.get(client_id)
            if not session:
                return {"status": "ERROR", "msg": "Session not found"}

            subs_transferred = list(session.subscriptions)

            # Transfer session state to target broker
            import copy
            target_broker._sessions[client_id] = session
            target_broker._sessions[client_id].connected = True

            # Transfer ACL role to new broker
            client_role = self.acl._client_roles.get(client_id, "Patient")
            target_broker.acl.register_client(
                client_id,
                client_role,
                publish_topics=self.acl._client_publish_allowed.get(client_id, set()).copy(),
                subscribe_topics=self.acl._client_subscribe_allowed.get(client_id, set()).copy(),
            )

            # Transfer callbacks for all subscribed topics
            for topic in session.subscriptions:
                if topic in self._callbacks:
                    for entry in self._callbacks[topic]:
                        if entry[0] == client_id:
                            if entry not in target_broker._callbacks[topic]:
                                target_broker._callbacks[topic].append(entry)

            # Mark old session as offline (persistent session — not deleted)
            session.connected = False

        return {
            "status": "HANDOVER_COMPLETE",
            "client_id": client_id,
            "from_broker": self.broker_id,
            "to_broker": target_broker.broker_id,
            "subscriptions_transferred": subs_transferred,
            "role_transferred": client_role,
        }

    # ── Stats & diagnostics ──────────────────────────────────

    def get_packet_stats(self) -> dict:
        return dict(self._packet_stats)

    def get_message_log(self) -> List[dict]:
        return list(self._message_log)

    def get_session_info(self, client_id: str) -> Optional[dict]:
        s = self._sessions.get(client_id)
        if not s:
            return None
        return {
            "client_id": s.client_id,
            "connected": s.connected,
            "clean_session": s.clean_session,
            "subscriptions": list(s.subscriptions),
            "queued_messages": len(s.queued_messages),
            "last_seen": s.last_seen,
        }

    def get_broker_summary(self) -> dict:
        with self._lock:
            connected = sum(1 for s in self._sessions.values() if s.connected)
            return {
                "broker_id": self.broker_id,
                "location": self.location,
                "total_sessions": len(self._sessions),
                "connected_clients": connected,
                "retained_topics": list(self._retained.keys()),
                "total_messages": len(self._message_log),
                "packet_stats": dict(self._packet_stats),
                "acl_topics": ACLManager.TOPICS,
            }
