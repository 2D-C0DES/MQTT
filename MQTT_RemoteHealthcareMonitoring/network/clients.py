"""
IoT Healthcare Clients
======================
Implements Publisher (Patient) and Subscriber (Medical Expert) nodes
as described in the paper.

Publisher (Patient / ESP32 IoT device):
  - Implanted with sensors during initial registration
  - Encrypts health messages with OTP before publishing via MQTT
  - Publishes to: health/status, medication/update, symptom/reporting, wellness/tips
  - Simulates ESP32 sensor readings (BP, temperature, heart rate, SpO2, glucose)
  - Manages patient mobility (broker handover)

Subscriber (Medical Practitioner):
  - Registers domain/specialization with broker
  - Subscribes to relevant topics (ACL-controlled, Table 5)
  - Decrypts received OTP messages
  - Generates medical responses
  - Clustered by specialization (Table 2)

Online Wrapper Application:
  - Generates communication keys
  - Authenticates clients
  - Manages publisher-subscriber matching
"""

import time
import uuid
import json
import queue
import threading
import random
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from core.otp_cipher import OTPCipher
from broker.mqtt_broker import MQTTBroker, QoSLevel, MQTTMessage, ACLManager


# ─────────────────────────────────────────────
#  Sensor Data Simulator (ESP32 sensors)
# ─────────────────────────────────────────────

class SensorSimulator:
    """
    Simulates ESP32-connected medical sensors.
    Produces realistic physiological readings with configurable anomalies.
    """

    NORMAL_RANGES = {
        "bp_systolic":   (110, 130),
        "bp_diastolic":  (70,  85),
        "heart_rate":    (60,  100),
        "temperature":   (36.1, 37.5),
        "spo2":          (95,  100),
        "glucose":       (70,  140),
        "respiration":   (12,  20),
    }

    def __init__(self, patient_id: str, anomaly_prob: float = 0.15):
        self.patient_id = patient_id
        self.anomaly_prob = anomaly_prob
        self._rng = random.Random(int(patient_id.replace("P", "").replace("MC","0") or 0))

    def read_sensors(self) -> dict:
        readings = {}
        for sensor, (lo, hi) in self.NORMAL_RANGES.items():
            val = self._rng.uniform(lo, hi)
            # Inject anomaly
            if self._rng.random() < self.anomaly_prob:
                val *= self._rng.choice([0.75, 1.25])
            if sensor in ("bp_systolic", "bp_diastolic", "heart_rate",
                           "spo2", "respiration"):
                val = int(val)
            else:
                val = round(val, 1)
            readings[sensor] = val
        readings["timestamp"] = time.time()
        readings["patient_id"] = self.patient_id
        return readings

    def format_health_status(self) -> str:
        r = self.read_sensors()
        return (
            f"PID:{self.patient_id} | "
            f"BP:{r['bp_systolic']}/{r['bp_diastolic']} | "
            f"HR:{r['heart_rate']} | "
            f"Temp:{r['temperature']}C | "
            f"SpO2:{r['spo2']}% | "
            f"Glucose:{r['glucose']}"
        )

    def format_symptom_report(self) -> str:
        symptoms = self._rng.choice([
            "chest tightness, mild shortness of breath",
            "persistent headache, dizziness",
            "fatigue, loss of appetite",
            "joint pain, swelling in lower limbs",
            "irregular heartbeat sensation",
            "nausea, abdominal discomfort",
        ])
        return f"PID:{self.patient_id} | Symptoms: {symptoms}"


# ─────────────────────────────────────────────
#  Online Wrapper Application
# ─────────────────────────────────────────────

class OnlineWrapperApp:
    """
    The 'Online Wrapper Application' / 'Online Service Provider' from the paper.

    Responsibilities:
      - Client registration and authentication
      - Communication key issuance
      - Publisher ↔ Subscriber matching
      - Queue-size based load balancing (Table 2)
    """

    QUEUE_MAX = 5  # max clients per practitioner queue

    def __init__(self):
        self._registered: Dict[str, dict] = {}
        self._comm_keys: Dict[str, bytes] = {}     # client_id -> comm_key
        self._queues: Dict[str, List[str]] = {}    # practitioner_id -> [client_ids]
        self._lock = threading.Lock()

    def register_client(self, client_id: str, role: str,
                        username: str, password: str) -> dict:
        """
        Step 1-3 of paper execution sequence:
        Medical clients register → wrapper issues communication key.
        """
        with self._lock:
            if client_id in self._registered:
                return {"status": "ALREADY_REGISTERED",
                        "comm_key": self._comm_keys[client_id].hex()}

            # Issue communication key
            comm_key = hashlib.sha256(
                f"{client_id}{username}{password}{time.time()}".encode()
            ).digest()
            self._comm_keys[client_id] = comm_key
            self._registered[client_id] = {
                "client_id": client_id,
                "role": role,
                "username": username,
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                "registered_at": time.time(),
                "comm_key": comm_key.hex()
            }
            return {
                "status": "REGISTERED",
                "client_id": client_id,
                "role": role,
                "comm_key": comm_key.hex(),
                "comm_key_bytes": comm_key
            }

    def authenticate(self, client_id: str, password: str) -> bool:
        info = self._registered.get(client_id)
        if not info:
            return False
        expected = hashlib.sha256(password.encode()).hexdigest()
        return info.get("password_hash") == expected

    def allocate_practitioner(self, patient_id: str,
                               specialization: str) -> Optional[str]:
        """
        Load-balance patient to practitioner based on queue size (Table 2).
        """
        with self._lock:
            # Find matching practitioners with space
            candidates = [
                pid for pid, info in self._registered.items()
                if info.get("role") == "Medical Practitioner"
                and info.get("specialization") == specialization
                and len(self._queues.get(pid, [])) < self.QUEUE_MAX
            ]
            if not candidates:
                return None
            # Pick least loaded
            chosen = min(candidates,
                         key=lambda p: len(self._queues.get(p, [])))
            self._queues.setdefault(chosen, []).append(patient_id)
            return chosen

    def get_comm_key(self, client_id: str) -> Optional[bytes]:
        return self._comm_keys.get(client_id)


# ─────────────────────────────────────────────
#  Publisher Client (Patient / IoT Publisher)
# ─────────────────────────────────────────────

class PatientPublisher:
    """
    IoT Publisher node — simulates a patient with ESP32 + sensors.

    Paper roles:
      - "patients at the publisher's end"
      - Encrypts with OTP before MQTT publish
      - Manages session keys per message
      - Supports patient mobility (broker handover)
    """

    TOPICS = ACLManager.TOPICS

    def __init__(self, patient_id: str, broker: MQTTBroker,
                 wrapper: OnlineWrapperApp, keys_dir: str = "keys"):
        self.patient_id = patient_id
        self.broker = broker
        self.wrapper = wrapper
        self.cipher = OTPCipher(device_id=patient_id, keys_dir=keys_dir)
        self.sensor = SensorSimulator(patient_id)
        self.session_keys: Dict[str, bytes] = {}   # msg_id -> key_bytes (shared with doctor)
        self.published_messages: List[dict] = []
        self.connected = False
        self._username = f"user_{patient_id}"
        self._password = f"pass_{patient_id}_secure"
        self._comm_key: Optional[bytes] = None

    def register_and_connect(self, specialization: str = "General") -> dict:
        """Steps 1-4 of paper execution."""
        # Register with wrapper
        reg = self.wrapper.register_client(
            self.patient_id, "Patient",
            self._username, self._password
        )
        self._comm_key = reg.get("comm_key_bytes")

        # Connect to broker
        conn = self.broker.connect_client(
            client_id=self.patient_id,
            username=self._username,
            password=self._password,
            role="Patient",
            clean_session=False,   # supports mobility
            keep_alive=60
        )
        self.connected = (conn["return_code"] == 0)
        return {**reg, **conn}

    def publish_health_data(self, topic: str, message: str,
                            qos: QoSLevel = QoSLevel.AT_LEAST_ONCE,
                            retain: bool = False) -> dict:
        """
        Full publish pipeline:
          Encrypt with OTP → publish via MQTT broker.
        Returns complete audit record.
        """
        if not self.connected:
            return {"status": "ERROR", "msg": "Not connected"}

        # Generate unique message ID
        msg_id = f"{self.patient_id}_{topic.replace('/','_')}_{int(time.time()*1000)}"

        # OTP Encryption
        enc = self.cipher.encrypt(message)
        cipher_b64 = enc["cipher_b64"]

        # Store key for sharing with subscriber (secure channel simulation)
        self.session_keys[msg_id] = enc["key_bytes"]

        # Build MQTT payload: ciphertext + integrity hash
        mqtt_payload = json.dumps({
            "ciphertext_b64": cipher_b64,
            "sha256": enc["integrity_hash_sha256"],
            "msg_id": msg_id,
            "session_id": enc["session_id"],
            "sender": self.patient_id,
        })

        # Publish via broker
        pub_result = self.broker.publish(
            client_id=self.patient_id,
            topic=topic,
            payload=mqtt_payload,
            qos=qos,
            retain=retain,
            msg_id=msg_id
        )

        record = {
            "msg_id": msg_id,
            "topic": topic,
            "original_message": message,
            "encryption": enc,
            "mqtt_result": pub_result,
            "timestamp": time.time(),
        }
        self.published_messages.append(record)
        return record

    def publish_sensor_data(self, qos: QoSLevel = QoSLevel.AT_LEAST_ONCE) -> List[dict]:
        """Publish a full sensor reading cycle across all topics."""
        results = []
        
        results.append(self.publish_health_data(
            "health/status", self.sensor.format_health_status(), qos
        ))
        results.append(self.publish_health_data(
            "symptom/reporting", self.sensor.format_symptom_report(), qos
        ))
        results.append(self.publish_health_data(
            "medication/update",
            f"PID:{self.patient_id} | Medication request: daily dosage check", qos
        ))
        results.append(self.publish_health_data(
            "wellness/tips",
            f"PID:{self.patient_id} | Wellness query: diet and activity plan", qos
        ))
        return results

    def handover_to(self, new_broker: MQTTBroker) -> dict:
        """Patient mobility: move to new MQTT broker zone."""
        result = self.broker.handover_session(self.patient_id, new_broker)
        if result["status"] == "HANDOVER_COMPLETE":
            self.broker = new_broker
        return result

    def get_shared_key(self, msg_id: str) -> Optional[bytes]:
        """Returns the OTP key for a given message (secure side-channel to doctor)."""
        return self.session_keys.get(msg_id)


# ─────────────────────────────────────────────
#  Subscriber Client (Medical Practitioner)
# ─────────────────────────────────────────────

class DoctorSubscriber:
    """
    IoT Subscriber node — simulates a medical expert workstation.

    Paper roles:
      - "medical professionals at the subscriber's end"
      - Subscribes to specialization-specific topics
      - Decrypts received OTP messages
      - Generates clinical responses
    """

    RESPONSE_TEMPLATES = {
        "health/status": [
            "You are alright now. Continue monitoring.",
            "Vitals look stable. No immediate action required.",
            "BP slightly elevated. Reduce sodium intake, rest recommended.",
            "Heart rate irregular. Schedule ECG immediately.",
            "SpO2 low. Start supplemental oxygen, contact emergency.",
        ],
        "medication/update": [
            "Continue current medication. 1 tablet Aspirin twice daily.",
            "Adjust dosage: 500mg Metformin once daily with meals.",
            "Medication review required. Visit clinic within 48 hours.",
            "New prescription issued. Collect from pharmacy.",
        ],
        "symptom/reporting": [
            "No immediate action required. Monitor symptoms.",
            "Symptoms suggest dehydration. Increase fluid intake.",
            "Refer to specialist. Book appointment today.",
            "Emergency: proceed to nearest ER immediately.",
        ],
        "wellness/tips": [
            "Get at least 8 hours of sleep daily.",
            "30 minutes moderate exercise recommended.",
            "Mediterranean diet advised. Reduce processed foods.",
            "Mindfulness exercises for stress management.",
        ],
    }

    def __init__(self, doctor_id: str, specialization: str,
                 broker: MQTTBroker, wrapper: OnlineWrapperApp,
                 patient_publisher_registry: Dict[str, "PatientPublisher"],
                 keys_dir: str = "keys"):
        self.doctor_id = doctor_id
        self.specialization = specialization
        self.broker = broker
        self.wrapper = wrapper
        self.patient_registry = patient_publisher_registry
        self.cipher = OTPCipher(device_id=doctor_id, keys_dir=keys_dir)
        self.received_messages: List[dict] = []
        self.responses_sent: List[dict] = []
        self.inbox: queue.Queue = queue.Queue()
        self.connected = False
        self._username = f"doc_{doctor_id}"
        self._password = f"secpass_doc_{doctor_id}"

    def register_and_connect(self) -> dict:
        reg = self.wrapper.register_client(
            self.doctor_id, "Medical Practitioner",
            self._username, self._password
        )
        conn = self.broker.connect_client(
            client_id=self.doctor_id,
            username=self._username,
            password=self._password,
            role=self.specialization,
            clean_session=False,
            keep_alive=120
        )
        self.connected = (conn["return_code"] == 0)
        return {**reg, **conn}

    def subscribe_topics(self) -> dict:
        """Subscribe to all ACL-allowed topics for this specialization."""
        allowed = self.broker.acl.DEFAULT_ROLE_SUBSCRIPTIONS.get(
            self.specialization, set()
        )
        result = self.broker.subscribe(
            client_id=self.doctor_id,
            topics=list(allowed),
            callback=self._on_message_received
        )
        return result

    def _on_message_received(self, mqtt_msg: MQTTMessage):
        """
        Callback invoked by broker when a subscribed message arrives.
        Decrypts OTP payload and queues for processing.
        """
        try:
            payload_data = json.loads(mqtt_msg.payload)
            cipher_b64 = payload_data["ciphertext_b64"]
            sha256_hash = payload_data["sha256"]
            msg_id = payload_data["msg_id"]
            sender_id = payload_data["sender"]

            # Get the OTP key from the patient (secure side-channel)
            patient = self.patient_registry.get(sender_id)
            if not patient:
                return
            key_bytes = patient.get_shared_key(msg_id)
            if not key_bytes:
                return

            # Decrypt
            dec = self.cipher.decrypt(cipher_b64, key_bytes, sha256_hash)

            record = {
                "msg_id": msg_id,
                "topic": mqtt_msg.topic,
                "sender": sender_id,
                "received_at": time.time(),
                "decryption": dec,
                "mqtt_wire_size": mqtt_msg.wire_size(),
                "packet_id": mqtt_msg.packet_id,
            }
            self.received_messages.append(record)
            self.inbox.put(record)

            # Auto-generate response
            self._generate_response(record)

        except Exception as e:
            self.received_messages.append({
                "error": str(e),
                "raw_payload": mqtt_msg.payload[:100]
            })

    def _generate_response(self, record: dict):
        """Generate a clinical response and publish back to patient."""
        topic = record.get("topic", "health/status")
        templates = self.RESPONSE_TEMPLATES.get(topic, ["Acknowledged."])
        response_text = random.choice(templates)
        sender_id = record["sender"]

        # Encrypt response
        enc = self.cipher.encrypt(response_text)
        response_payload = json.dumps({
            "ciphertext_b64": enc["cipher_b64"],
            "sha256": enc["integrity_hash_sha256"],
            "msg_id": f"resp_{record['msg_id']}",
            "sender": self.doctor_id,
        })

        resp = {
            "response_to_msg": record["msg_id"],
            "patient_id": sender_id,
            "doctor_id": self.doctor_id,
            "specialization": self.specialization,
            "topic": topic,
            "response_text": response_text,
            "response_encrypted": enc["cipher_b64"],
            "timestamp": time.time(),
        }
        self.responses_sent.append(resp)

    def get_inbox_summary(self) -> List[dict]:
        msgs = []
        while not self.inbox.empty():
            msgs.append(self.inbox.get_nowait())
        return msgs


# ─────────────────────────────────────────────
#  Medical Practitioner Queue Manager (Table 2)
# ─────────────────────────────────────────────

class PractitionerQueueManager:
    """
    Manages patient-to-practitioner allocation based on queue size and
    domain specialization (paper Table 2).
    """

    def __init__(self):
        self.queues: Dict[str, List[str]] = {}  # practitioner_id -> [patient_ids]
        self.practitioners: Dict[str, dict] = {}

    def register_practitioner(self, pr_id: str, specialization: str):
        self.practitioners[pr_id] = {
            "id": pr_id,
            "specialization": specialization,
            "queue_size": 0
        }
        self.queues[pr_id] = []

    def allocate(self, patient_id: str, specialization: str) -> Optional[str]:
        candidates = [
            pr_id for pr_id, info in self.practitioners.items()
            if info["specialization"] == specialization
        ]
        if not candidates:
            return None
        chosen = min(candidates, key=lambda p: len(self.queues[p]))
        self.queues[chosen].append(patient_id)
        self.practitioners[chosen]["queue_size"] = len(self.queues[chosen])
        return chosen

    def get_allocation_table(self) -> List[dict]:
        rows = []
        for i, (pr_id, queue) in enumerate(self.queues.items(), 1):
            rows.append({
                "S.No": i,
                "Queue_Size": len(queue),
                "Publishers_on_Queue": queue[:4],
                "Subscriber": pr_id,
                "Consulting_Domain": self.practitioners[pr_id]["specialization"]
            })
        return rows
