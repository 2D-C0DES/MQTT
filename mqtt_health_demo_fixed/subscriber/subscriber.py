"""
subscriber.py — Doctor-Side MQTT Subscriber
============================================
Subscribes to all health topics, decrypts incoming messages using OTP,
and displays them in a formatted terminal dashboard.

Different clinician "roles" can be simulated by filtering topics:
  --role general       → all four topics
  --role cardiologist  → health/status + health/medication
  --role psychologist  → health/symptoms + health/wellness
  --role pharmacist    → health/medication only

Run:
  python subscriber.py [--role ROLE] [--qos 0|1|2]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import argparse
from datetime import datetime
from collections import defaultdict

import paho.mqtt.client as mqtt

from crypto.otp import unpackage_payload

# ── Broker config ──────────────────────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1884
KEEPALIVE   = 60

# ── Topic → role mapping (mirrors Table 5 in the paper) ───────────────────────
ROLE_TOPICS = {
    "general":      ["health/status", "health/symptoms", "health/medication", "health/wellness"],
    "cardiologist": ["health/status", "health/medication"],
    "psychologist": ["health/symptoms", "health/wellness"],
    "pharmacist":   ["health/medication"],
}

# ── ANSI colour codes ──────────────────────────────────────────────────────────
C = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "red":     "\033[91m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "blue":    "\033[94m",
    "magenta": "\033[95m",
    "cyan":    "\033[96m",
    "white":   "\033[97m",
    "grey":    "\033[90m",
}

def colour(text, *codes):
    return "".join(C[c] for c in codes) + str(text) + C["reset"]


# ── Message counters ───────────────────────────────────────────────────────────
stats = defaultdict(int)   # topic → count
alerts = []                # list of alert summaries


# ── Display helpers ────────────────────────────────────────────────────────────

def display_header(role: str, topics: list):
    print()
    print(colour("=" * 65, "cyan", "bold"))
    print(colour("  MQTT Health Monitor — Doctor Subscriber", "cyan", "bold"))
    print(colour("=" * 65, "cyan", "bold"))
    print(f"  Role     : {colour(role.title(), 'yellow', 'bold')}")
    print(f"  Broker   : {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Topics   : {', '.join(colour(t, 'blue') for t in topics)}")
    print(f"  Crypto   : OTP (XOR + SHA-256 key conditioning)")
    print(colour("=" * 65, "cyan", "bold"))
    print()


def display_vitals(data: dict, integrity_ok: bool):
    pid = data.get("patient_id", "???")
    v   = data.get("vitals", {})
    alert = data.get("alert", False)

    hr   = v.get("heart_rate_bpm", "?")
    spo2 = v.get("spo2_percent", "?")
    temp = v.get("temperature_c", "?")
    bp   = v.get("blood_pressure", "?")

    integrity_tag = colour("✓ OK", "green") if integrity_ok else colour("✗ TAMPERED", "red", "bold")

    if alert:
        prefix = colour("🚨 ALERT ", "red", "bold")
        stats["alerts"] += 1
        alerts.append(f"{pid} abnormal vitals at {data.get('timestamp','')[:19]}")
    else:
        prefix = colour("📋 STATUS", "green")

    print(f"\n  {prefix} │ {colour(pid, 'white', 'bold')} │ Integrity: {integrity_tag}")
    print(f"  {'─'*60}")
    print(f"    Heart Rate : {colour(f'{hr} bpm', 'yellow' if not alert else 'red')}")
    print(f"    SpO2       : {colour(f'{spo2}%', 'yellow' if not alert else 'red')}")
    print(f"    Temperature: {colour(f'{temp}°C', 'yellow' if not alert else 'red')}")
    print(f"    BP         : {colour(bp, 'yellow' if not alert else 'red')}")
    print(f"    Timestamp  : {colour(data.get('timestamp','')[:19], 'grey')}")


def display_symptoms(data: dict, integrity_ok: bool):
    pid      = data.get("patient_id", "???")
    symptom  = data.get("symptom", "?")
    severity = data.get("severity", "?")
    integrity_tag = colour("✓ OK", "green") if integrity_ok else colour("✗ TAMPERED", "red", "bold")

    sev_colour = "green" if severity == "none" else ("yellow" if severity == "mild" else "red")

    print(f"\n  {colour('🩺 SYMPTOM', 'magenta')} │ {colour(pid, 'white', 'bold')} │ Integrity: {integrity_tag}")
    print(f"  {'─'*60}")
    print(f"    Symptom  : {colour(symptom, 'white')}")
    print(f"    Severity : {colour(severity.upper(), sev_colour, 'bold')}")
    print(f"    Time     : {colour(data.get('timestamp','')[:19], 'grey')}")


def display_medication(data: dict, integrity_ok: bool):
    pid    = data.get("patient_id", "???")
    med    = data.get("medication", "?")
    taken  = data.get("taken", False)
    dose   = data.get("dose", "?")
    integrity_tag = colour("✓ OK", "green") if integrity_ok else colour("✗ TAMPERED", "red", "bold")

    taken_str = colour("✓ TAKEN", "green") if taken else colour("✗ MISSED", "red", "bold")

    print(f"\n  {colour('💊 MEDIC  ', 'blue')} │ {colour(pid, 'white', 'bold')} │ Integrity: {integrity_tag}")
    print(f"  {'─'*60}")
    print(f"    Medication : {colour(med, 'white')}")
    print(f"    Dose       : {colour(dose, 'cyan')}")
    print(f"    Status     : {taken_str}")
    print(f"    Time       : {colour(data.get('timestamp','')[:19], 'grey')}")


def display_wellness(data: dict, integrity_ok: bool):
    pid     = data.get("patient_id", "???")
    sleep   = data.get("sleep_hours", "?")
    water   = data.get("hydration_glasses", "?")
    stress  = data.get("stress_level", "?")
    steps   = data.get("steps_today", "?")
    integrity_tag = colour("✓ OK", "green") if integrity_ok else colour("✗ TAMPERED", "red", "bold")

    stress_colour = "green" if stress == "low" else ("yellow" if stress == "medium" else "red")

    print(f"\n  {colour('🌿 WELLNESS', 'cyan')} │ {colour(pid, 'white', 'bold')} │ Integrity: {integrity_tag}")
    print(f"  {'─'*60}")
    print(f"    Sleep      : {colour(f'{sleep}h', 'white')}")
    print(f"    Hydration  : {colour(f'{water} glasses', 'white')}")
    print(f"    Stress     : {colour(stress.upper(), stress_colour, 'bold')}")
    print(f"    Steps      : {colour(f'{steps:,}', 'white')}")
    print(f"    Time       : {colour(data.get('timestamp','')[:19], 'grey')}")


def display_stats():
    total = sum(v for k, v in stats.items() if k != "alerts")
    print(f"\n  {colour('─'*60, 'grey')}")
    print(f"  {colour('TOTALS', 'grey')} │ Messages received: {colour(total, 'white')} │ "
          f"Alerts: {colour(stats['alerts'], 'red' if stats['alerts'] else 'green')}")


TOPIC_DISPLAY = {
    "health/status":     display_vitals,
    "health/symptoms":   display_symptoms,
    "health/medication": display_medication,
    "health/wellness":   display_wellness,
}


# ── MQTT callbacks ─────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        topics = userdata["topics"]
        qos    = userdata["qos"]
        print(colour(f"  ✓ Connected to broker at {BROKER_HOST}:{BROKER_PORT}", "green"))
        for topic in topics:
            client.subscribe(topic, qos=qos)
            print(f"    Subscribed → {colour(topic, 'blue')} (QoS={qos})")
        print()
    else:
        print(colour(f"  ✗ Connection failed (rc={reason_code})", "red"))


def on_message(client, userdata, msg):
    topic = msg.topic
    stats[topic] += 1

    try:
        raw = msg.payload.decode("utf-8")

        # Show raw encrypted payload for demo purposes
        print(f"\n  {colour('🔒 RECV', 'grey')} → {colour(topic, 'blue')} "
              f"│ {len(raw)} bytes │ "
              f"Encrypted: {colour(raw[:60] + '...', 'grey')}")

        # Decrypt
        data, integrity_ok = unpackage_payload(raw)

        # Dispatch to appropriate display function
        display_fn = TOPIC_DISPLAY.get(topic)
        if display_fn:
            display_fn(data, integrity_ok)

        display_stats()

    except Exception as e:
        print(colour(f"  ✗ Error processing message on {topic}: {e}", "red"))


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(colour(f"\n  Disconnected from broker.", "yellow"))


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MQTT Health Monitor — Doctor Subscriber")
    parser.add_argument("--role", choices=["general", "cardiologist", "psychologist", "pharmacist"],
                        default="general",
                        help="Clinician role (controls which topics are subscribed)")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=1,
                        help="MQTT QoS level (default: 1)")
    args = parser.parse_args()

    topics = ROLE_TOPICS[args.role]
    display_header(args.role, topics)

    client = mqtt.Client(
        client_id=f"doctor-{args.role}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.user_data_set({"topics": topics, "qos": args.qos})
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        client.loop_forever()
    except KeyboardInterrupt:
        print(colour("\n\n  Subscriber stopped.", "yellow"))
        client.disconnect()
    except ConnectionRefusedError:
        print(colour(f"\n  ✗ Could not connect to broker at {BROKER_HOST}:{BROKER_PORT}", "red"))
        print(colour("    Is Mosquitto running? → mosquitto -v", "yellow"))


if __name__ == "__main__":
    main()
