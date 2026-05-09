# MQTT Health Monitor
### An IoT Remote Medical Diagnosis Demo using OTP Encryption over MQTT

A college project implementation inspired by:
> *"An IoT based remote medical diagnosis system using one time pad cipher over MQTT protocol"*
> — Kumar et al., Scientific Reports (2025)

---

## What This Project Does

This project simulates a **secure remote healthcare monitoring system** where:

- 🏥 **Patients** (IoT publishers) continuously stream encrypted health vitals
- 📡 **An MQTT Broker** routes messages between patients and doctors without being able to read them
- 👨‍⚕️ **Doctors** (subscribers) receive and decrypt messages based on their specialisation
- 🔐 **OTP Encryption** (XOR + SHA-256) ensures the broker only ever sees ciphertext
- 🌐 **A live web dashboard** visualises everything in real time

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Patient (Publisher)                                           │
│   ┌─────────────────┐     Encrypted MQTT Message               │
│   │ Vitals Simulator│ ──────────────────────────────────┐      │
│   │ OTP Encrypt     │                                   ▼      │
│   └─────────────────┘                        ┌──────────────┐  │
│                                              │ MQTT Broker  │  │
│   Patient 2 ──────────────────────────────►  │ (Mosquitto)  │  │
│   Patient 3 ──────────────────────────────►  │              │  │
│                                              └──────┬───────┘  │
│                                                     │          │
│                              Encrypted messages     │          │
│                              (broker cannot read)   │          │
│                                                     ▼          │
│                                        ┌─────────────────────┐ │
│                                        │  Doctor (Subscriber)│ │
│                                        │  OTP Decrypt        │ │
│                                        │  Display Results    │ │
│                                        └─────────────────────┘ │
│                                                     │          │
│                                        ┌─────────────────────┐ │
│                                        │  Web Dashboard      │ │
│                                        │  (via WS Bridge)    │ │
│                                        └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### MQTT Topics (matching the paper)

| Topic | Data | Clinician Access |
|---|---|---|
| `health/status` | Heart rate, SpO2, temperature, blood pressure | General, Cardiologist |
| `health/symptoms` | Patient-reported symptoms, severity | General, Psychologist |
| `health/medication` | Medication name, dose, adherence | General, Cardiologist, Pharmacist |
| `health/wellness` | Sleep, hydration, stress, steps | General, Psychologist |

---

## Project Structure

```
mqtt_health_demo/
│
├── broker/
│   └── mosquitto.conf          # Mosquitto broker configuration
│
├── crypto/
│   └── otp.py                  # OTP encryption/decryption module
│
├── publisher/
│   └── publisher.py            # Patient simulator (publisher)
│
├── subscriber/
│   └── subscriber.py           # Doctor terminal subscriber
│
├── dashboard/
│   └── index.html              # Live web dashboard
│
├── dashboard_bridge.py         # MQTT → WebSocket bridge for the dashboard
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── crypto/README.md            # Encryption details
```

---

## Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Mosquitto broker
# Ubuntu/Debian:
sudo apt install mosquitto
# macOS:
brew install mosquitto
# Windows: Download from https://mosquitto.org/download/
```

### 2. Start the Broker

```bash
mosquitto -c broker/mosquitto.conf -v
```

> Leave this terminal open. You'll see all routing activity here.

### 3. Start the Patient Publisher (Simulator)

Open a **new terminal**:

```bash
cd publisher
python publisher.py --patients 3 --interval 3 --qos 1
```

This starts **3 simulated patients**, each publishing vitals every ~3 seconds.

### 4. Start a Doctor Subscriber

Open another **new terminal**:

```bash
cd subscriber
python subscriber.py --role general
```
~
You'll see decrypted messages arrive in real time, colour-coded by type.

### 5. (Optional) Open the Web Dashboard

Open yet another **new terminal**:

```bash
python dashboard_bridge.py
```

This will automatically open `dashboard/index.html` in your browser.
If it doesn't open automatically, open `dashboard/index.html` manually.

---

## CLI Options

### Publisher

```
python publisher.py [OPTIONS]

Options:
  --patients N     Number of simulated patients (default: 3)
  --interval SEC   Seconds between publish cycles (default: 3.0)
  --qos 0|1|2     MQTT Quality of Service level (default: 1)
```

### Subscriber

```
python subscriber.py [OPTIONS]

Options:
  --role ROLE     Clinician role — controls which topics are subscribed
                  Choices: general | cardiologist | psychologist | pharmacist
                  (default: general)
  --qos 0|1|2    MQTT Quality of Service level (default: 1)
```

---

## QoS Levels Explained

| Level | Name | Behaviour | Use Case |
|---|---|---|---|
| **QoS 0** | At most once | Fire-and-forget, no retries | Non-critical wellness data |
| **QoS 1** | At least once | Guaranteed delivery, possible duplicates | Vitals, medication |
| **QoS 2** | Exactly once | Guaranteed, no duplicates | Critical alerts |

Try running the publisher with `--qos 0` and the subscriber with `--qos 1` to observe the difference.

---

## Demo Script (for your presentation)

1. **Show the broker starting** — point out it's just routing encrypted bytes
2. **Show the publisher** — highlight that data is encrypted before sending
3. **Show the subscriber** — demonstrate decryption happening on the doctor's side
4. **Trigger an alert** — wait ~30s for a simulated abnormal vitals reading (🚨)
5. **Show two subscribers with different roles** — cardiologist vs psychologist, different topics
6. **Open the dashboard** — show the real-time visualisation
7. **Change QoS** — demonstrate the difference between QoS 0 and QoS 1

---

## References

- Kumar, N. R., et al. (2025). *An IoT based remote medical diagnosis system using one time pad cipher over MQTT protocol.* Scientific Reports, 15, 42117.
- MQTT Specification: https://mqtt.org
- Mosquitto Broker: https://mosquitto.org
- Shannon, C. E. (1949). *Communication theory of secrecy systems.* Bell System Technical Journal.
