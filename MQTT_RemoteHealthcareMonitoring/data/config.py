"""
Data Configuration Module
==========================
Centralised data definitions for the IoT healthcare simulation.

Matches paper:
  - MQTT topic hierarchy (Section: Security analysis)
  - Message type configs (Table 10)
  - Clinician role → topic mapping (Table 5)
  - Sample messages from Fig. 10 (MQTT Communication with subscriptions)
  - Broker configuration fields (Table 3)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set


# ─────────────────────────────────────────────
#  MQTT Topic Definitions
# ─────────────────────────────────────────────

MQTT_TOPICS = {
    "health/status":      "Real-time patient vitals (BP, HR, Temp, SpO2, Glucose)",
    "medication/update":  "Medication requests, dosage updates, prescriptions",
    "symptom/reporting":  "Patient-reported symptoms and complaints",
    "wellness/tips":      "Wellness and lifestyle recommendations",
}

# Topics grouped for display (paper Fig. 8 & 9)
TOPIC_GROUPS = {
    "Group 1": ["health/status",     "medication/update"],
    "Group 2": ["symptom/reporting", "wellness/tips"],
}


# ─────────────────────────────────────────────
#  Message Communication Types (Table 10)
# ─────────────────────────────────────────────

@dataclass
class MessageType:
    type_id: int
    bit_length: int
    sample_text: str
    description: str

MESSAGE_TYPES: List[MessageType] = [
    MessageType(1,  82,  "Hello doctor",    "Short greeting / connection check"),
    MessageType(2, 120,  "Query on health", "General health inquiry"),
    MessageType(3, 160,  "Take one dose",   "Medication instruction"),
    MessageType(4, 180,  "Health is normal","Status confirmation"),
]

WIFI_CONFIG = {
    "standard":       "802.11 b/g/n",
    "download_speed": "7.46 Mbps",
    "upload_speed":   "5.37 Mbps",
    "protocol":       "WiFi",
}


# ─────────────────────────────────────────────
#  MQTT Broker Configuration (Table 3)
# ─────────────────────────────────────────────

BROKER_CONFIG = {
    "client_name":       "espclient@broker.emqx.io",
    "client_id":         "mqttx_b6bacfd7",
    "username":          "emqx",
    "password":          "******",
    "keep_alive":        60,
    "clean_start":       False,
    "ssid_uname":        "hotspot_user",
    "ssid_password":     "hotspot_pass",
    "host":              "broker.emqx.io",
    "port":              1883,
    "protocol":          "MQTT v3.1.1",
}


# ─────────────────────────────────────────────
#  Clinician → Topic Subscription Map (Table 5)
# ─────────────────────────────────────────────

CLINICIAN_SUBSCRIPTIONS: Dict[str, Set[str]] = {
    "Cardiologist":       {"health/status", "medication/update"},
    "General Physician":  {"health/status", "medication/update",
                           "symptom/reporting", "wellness/tips"},
    "Psychologist":       {"symptom/reporting", "wellness/tips"},
    "Pharmacologist":     {"medication/update"},
    "Patient":            set(),   # Publishers only
}


# ─────────────────────────────────────────────
#  Sample Medical Messages (Fig. 10)
# ─────────────────────────────────────────────

SAMPLE_CONVERSATIONS = [
    {
        "patient":  "PID:272 | Please review the health status",
        "doctor":   "Medician 1: You are alright now",
        "topic":    "health/status",
    },
    {
        "patient":  "PID:273 | Request Medication",
        "doctor":   "Medician 2:1 Tablet Aspirin Twice daily",
        "topic":    "medication/update",
    },
    {
        "patient":  "PID: 274 | temp: 37.5 | heart rate: 80",
        "doctor":   "Medician 3: No immediate action required",
        "topic":    "symptom/reporting",
    },
    {
        "patient":  "PID: 2745 | Wellness Tips",
        "doctor":   "Medician 4: Get at least 8 hours of sleep",
        "topic":    "wellness/tips",
    },
]


# ─────────────────────────────────────────────
#  Medical Practitioner Pool (Table 2 basis)
# ─────────────────────────────────────────────

MEDICAL_PRACTITIONERS = [
    {"id": "MP-1",  "specialization": "General Physician"},
    {"id": "MP-2",  "specialization": "Cardiologist"},
    {"id": "MP-3",  "specialization": "Neurologist"},
    {"id": "MP-4",  "specialization": "General Physician"},
    {"id": "MP-5",  "specialization": "Cardiologist"},
    {"id": "MP-6",  "specialization": "Oncologist"},
    {"id": "MP-7",  "specialization": "Cardiologist"},
    {"id": "MP-8",  "specialization": "General Physician"},
    {"id": "MP-9",  "specialization": "Neurologist"},
    {"id": "MP-10", "specialization": "Oncologist"},
    {"id": "MP-11", "specialization": "General Physician"},
    {"id": "MP-12", "specialization": "Cardiologist"},
]

MEDICAL_CLIENTS = [
    {"id": f"MC{i}", "name": f"Medical Client {i}"} for i in range(1, 16)
]

# Table 2 exact allocation
TABLE_2_ALLOCATION = [
    {
        "S.No": 1,
        "Queue_Size": 4,
        "Publishers": ["Medical Client 1", "Medical Client 4",
                       "Medical Client 7", "Medical Client 8"],
        "Primary_Subscriber": "Medical Practitioner-1",
        "Consulting_Specialists": ["MP-1", "MP-4", "MP-5", "MP-6"],
    },
    {
        "S.No": 2,
        "Queue_Size": 5,
        "Publishers": ["Medical Client 3", "Medical Client 5", "Medical Client 6"],
        "Primary_Subscriber": "Medical Practitioner-2",
        "Consulting_Specialists": ["MP-2", "MP-7", "MP-9"],
    },
    {
        "S.No": 3,
        "Queue_Size": 4,
        "Publishers": ["Medical Client 2", "Medical Client 9", "Medical Client 10"],
        "Primary_Subscriber": "Medical Practitioner-3",
        "Consulting_Specialists": ["MP-3", "MP-10", "MP-11"],
    },
    {
        "S.No": 4,
        "Queue_Size": 5,
        "Publishers": ["Medical Client 11", "Medical Client 12", "Medical Client 15"],
        "Primary_Subscriber": "Medical Practitioner-4",
        "Consulting_Specialists": ["MP-4", "MP-8", "MP-12"],
    },
]


# ─────────────────────────────────────────────
#  OTP Notation Table (Table 1)
# ─────────────────────────────────────────────

OTP_NOTATION_TABLE = [
    ("Secret_msgp/d",         "Patient/Doctor Message (plaintext)"),
    ("L",                     "Length of Message"),
    ("X0, X1, X2, ..., Xn",  "Generated Random Keys per session"),
    ("Sk",                    "Shared_key (one-time, session-specific)"),
    ("Encrypted_msgp/d",      "Encrypted Message (ciphertext)"),
    ("Decrypted_msgp/d",      "Decrypted Message (recovered plaintext)"),
]


# ─────────────────────────────────────────────
#  BAN Logic Notation Table (Table 7)
# ─────────────────────────────────────────────

BAN_NOTATION_TABLE = [
    ("P |≡ X",   "P believes the message from X"),
    ("#X",       "The message X is newly generated (fresh)"),
    ("P ◁ X",   "P sees the message of X"),
    ("P |~ X",   "P once said X"),
    ("P => X",   "P monitors and controls message of X"),
    ("<X>Y",     "Formula X is combined with the formula Y"),
    ("{X}k",     "Formula X is encrypted by the key k"),
    ("k P ↔ Q", "Players P and Q communicate using K as shared key"),
    ("SK",       "Session key"),
]


# ─────────────────────────────────────────────
#  Performance reference values
# ─────────────────────────────────────────────

PERFORMANCE_PAPER_VALUES = {
    "otp_mqtt": {
        "avg_latency_ms":        85,
        "throughput_msg_s":     145,
        "cpu_utilization_pct":   18,
        "memory_usage_mb":       22,
        "encryption_time_ms":   1.8,
    },
    "aes128_mqtt": {
        "avg_latency_ms":       132,
        "throughput_msg_s":     112,
        "cpu_utilization_pct":   27,
        "memory_usage_mb":       30,
        "encryption_time_ms":   6.4,
    },
    "improvements_pct": {
        "avg_latency_ms":       35.60,
        "throughput_msg_s":     29.50,
        "cpu_utilization_pct":  33.30,
        "memory_usage_mb":      26.70,
        "encryption_time_ms":   71.90,
    }
}

COMPUTATION_TIME_REFERENCE = {
    10: {"enc_us": 477, "dec_us": 487, "pub_us": 495},
    15: {"enc_us": 529, "dec_us": 540, "pub_us": 552},
    20: {"enc_us": 688, "dec_us": 710, "pub_us": 693},
    25: {"enc_us": 690, "dec_us": 715, "pub_us": 697},
}

PACKET_LOSS_REFERENCE = {
    0:  {"qos0": 0.00, "qos1": 0.00},
    5:  {"qos0": 0.25, "qos1": 0.32},
    10: {"qos0": 0.29, "qos1": 0.37},
    15: {"qos0": 0.30, "qos1": 0.40},
    20: {"qos0": 0.70, "qos1": 0.72},
    25: {"qos0": 0.80, "qos1": 0.90},
}

SCALABILITY_REFERENCE = {
    5:  {"throughput": 25,  "latency_ms": 40,  "emqx_cpu": 12, "emqx_mem": 120, "esp32_cpu": 18, "key_dist": 12},
    10: {"throughput": 50,  "latency_ms": 55,  "emqx_cpu": 28, "emqx_mem": 210, "esp32_cpu": 20, "key_dist": 25},
    15: {"throughput": 75,  "latency_ms": 75,  "emqx_cpu": 45, "emqx_mem": 360, "esp32_cpu": 22, "key_dist": 60},
}
