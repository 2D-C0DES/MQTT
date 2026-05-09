"""
publisher.py — Patient-Side MQTT Publisher (Vitals Simulator)
=============================================================
Simulates multiple patients, each continuously generating health vitals
and publishing them as encrypted MQTT messages to the broker.

Topics published:
  health/status        — heart rate, SpO2, temperature, blood pressure
  health/symptoms      — randomly generated symptom reports
  health/medication    — medication adherence checks
  health/wellness      — sleep, hydration, stress level

Run:
  python publisher.py [--patients N] [--interval SECONDS] [--qos 0|1|2]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import random
import argparse
import threading
from datetime import datetime

import paho.mqtt.client as mqtt

from crypto.otp import package_payload

# ── Broker config ──────────────────────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1884
KEEPALIVE   = 60

# ── Topics (mirrors the paper's topic structure) ───────────────────────────────
TOPIC_STATUS     = "health/status"
TOPIC_SYMPTOMS   = "health/symptoms"
TOPIC_MEDICATION = "health/medication"
TOPIC_WELLNESS   = "health/wellness"

# ── Symptom bank for random selection ─────────────────────────────────────────
SYMPTOM_POOL = [
    "Mild headache",
    "Slight dizziness",
    "Shortness of breath",
    "Chest tightness",
    "Fatigue",
    "Nausea",
    "Back pain",
    "Joint pain",
    "Blurred vision",
    "Rapid heartbeat",
    "No symptoms reported",
    "No symptoms reported",
    "No symptoms reported",   # weighted toward no symptoms
]

MEDICATIONS = ["Aspirin", "Metformin", "Lisinopril", "Atorvastatin", "Amlodipine"]


# ── Simulator helpers ──────────────────────────────────────────────────────────

def simulate_vitals(patient_id: int, abnormal: bool = False) -> dict:
    """
    Generate a realistic set of patient vitals.
    If abnormal=True, one or more values will be out of healthy range
    to demonstrate alert triggering on the subscriber side.
    """
    if abnormal:
        heart_rate  = random.randint(120, 160)     # tachycardia
        spo2        = round(random.uniform(88, 93), 1)  # low oxygen
        temperature = round(random.uniform(38.5, 40.0), 1)  # fever
        systolic    = random.randint(150, 180)
        diastolic   = random.randint(95, 110)
    else:
        heart_rate  = random.randint(60, 100)
        spo2        = round(random.uniform(96.0, 99.9), 1)
        temperature = round(random.uniform(36.1, 37.4), 1)
        systolic    = random.randint(110, 130)
        diastolic   = random.randint(70, 85)

    return {
        "patient_id": f"PID-{patient_id:03d}",
        "timestamp": datetime.now().isoformat(),
        "vitals": {
            "heart_rate_bpm": heart_rate,
            "spo2_percent":   spo2,
            "temperature_c":  temperature,
            "blood_pressure": f"{systolic}/{diastolic} mmHg",
        },
        "alert": abnormal,
    }


def simulate_symptom_report(patient_id: int) -> dict:
    symptom = random.choice(SYMPTOM_POOL)
    severity = random.choice(["mild", "moderate", "severe"]) if symptom != "No symptoms reported" else "none"
    return {
        "patient_id": f"PID-{patient_id:03d}",
        "timestamp": datetime.now().isoformat(),
        "symptom": symptom,
        "severity": severity,
    }


def simulate_medication(patient_id: int) -> dict:
    med = random.choice(MEDICATIONS)
    taken = random.random() > 0.15  # 85% adherence rate
    return {
        "patient_id": f"PID-{patient_id:03d}",
        "timestamp": datetime.now().isoformat(),
        "medication": med,
        "taken": taken,
        "dose": f"{random.choice([50, 100, 200, 500])} mg",
    }


def simulate_wellness(patient_id: int) -> dict:
    return {
        "patient_id": f"PID-{patient_id:03d}",
        "timestamp": datetime.now().isoformat(),
        "sleep_hours": round(random.uniform(4.0, 9.0), 1),
        "hydration_glasses": random.randint(2, 10),
        "stress_level": random.choice(["low", "medium", "high"]),
        "steps_today": random.randint(500, 15000),
    }


# ── Publisher class ────────────────────────────────────────────────────────────

class PatientPublisher:
    def __init__(self, patient_id: int, interval: float, qos: int):
        self.patient_id = patient_id
        self.interval   = interval
        self.qos        = qos
        self.running    = False

        self.client = mqtt.Client(
            client_id=f"patient-{patient_id:03d}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish    = self._on_publish

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        status = "✓ Connected" if reason_code == 0 else f"✗ Failed (rc={reason_code})"
        print(f"  [PID-{self.patient_id:03d}] Broker {status}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        print(f"  [PID-{self.patient_id:03d}] Disconnected from broker")

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        pass  # quiet publish acknowledgement

    def connect(self):
        self.client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        self.client.loop_start()

    def disconnect(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()

    def publish_once(self):
        """Publish one round of all four topics."""
        # 10% chance of abnormal vitals per cycle to keep demo interesting
        abnormal = random.random() < 0.10

        # 1. Health Status (vitals)
        vitals_data = simulate_vitals(self.patient_id, abnormal)
        self._publish(TOPIC_STATUS, vitals_data)

        # 2. Symptoms (every 3rd cycle to avoid flooding)
        if random.random() < 0.33:
            symptom_data = simulate_symptom_report(self.patient_id)
            self._publish(TOPIC_SYMPTOMS, symptom_data)

        # 3. Medication (every 5th cycle)
        if random.random() < 0.20:
            med_data = simulate_medication(self.patient_id)
            self._publish(TOPIC_MEDICATION, med_data)

        # 4. Wellness (every 10th cycle)
        if random.random() < 0.10:
            wellness_data = simulate_wellness(self.patient_id)
            self._publish(TOPIC_WELLNESS, wellness_data)

    def _publish(self, topic: str, data: dict):
        """Encrypt data and publish to MQTT topic."""
        encrypted_payload = package_payload(topic, data)
        result = self.client.publish(topic, encrypted_payload, qos=self.qos)

        # Console log
        tag = "🚨 ALERT" if data.get("alert") else "📤 PUB  "
        pid = data.get("patient_id", f"PID-{self.patient_id:03d}")
        print(f"  {tag} [{pid}] → {topic:<22} | QoS={self.qos} | "
              f"{len(encrypted_payload)} bytes (encrypted)")

    def run_loop(self):
        """Main simulation loop — runs in its own thread."""
        self.running = True
        # Stagger start so all patients don't publish simultaneously
        time.sleep(random.uniform(0, self.interval))
        while self.running:
            self.publish_once()
            time.sleep(self.interval + random.uniform(-0.5, 0.5))  # slight jitter


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MQTT Health Monitor — Patient Publisher")
    parser.add_argument("--patients", type=int, default=3,
                        help="Number of simulated patients (default: 3)")
    parser.add_argument("--interval", type=float, default=3.0,
                        help="Seconds between publish cycles per patient (default: 3)")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=1,
                        help="MQTT QoS level (default: 1)")
    args = parser.parse_args()

    print("=" * 65)
    print("  MQTT Health Monitor — Patient Publisher (Simulator)")
    print("=" * 65)
    print(f"  Broker   : {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Patients : {args.patients}")
    print(f"  Interval : {args.interval}s")
    print(f"  QoS      : {args.qos}")
    print(f"  Crypto   : OTP (XOR + SHA-256 key conditioning)")
    print("=" * 65)
    print()

    publishers = []
    threads    = []

    for i in range(1, args.patients + 1):
        pub = PatientPublisher(patient_id=i, interval=args.interval, qos=args.qos)
        pub.connect()
        publishers.append(pub)

        t = threading.Thread(target=pub.run_loop, daemon=True)
        t.start()
        threads.append(t)

    print(f"\n  {args.patients} patient(s) online. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n  Shutting down publishers...")
        for pub in publishers:
            pub.disconnect()
        print("  Done.")


if __name__ == "__main__":
    main()
