# MQTT Remote Medical Diagnosis Monitor

## 📌 Overview

This project implements a **real-time remote medical monitoring system** using:

* MQTT (for data ingestion)
* Flask (for backend server)
* Socket.IO (for real-time communication)
* HTML/JavaScript (for visualization)

The system simulates patient health data, processes it through a backend analysis engine, and displays live updates along with medical alerts categorized by doctor specialization.

---

# 🧠 System Architecture (Deep Explanation)

## 1. Architectural Pattern

This system follows a **hybrid event-driven + pub/sub architecture**:

### Key Layers:

```
[ Data Generator ] 
        ↓
[ MQTT Broker (Pub/Sub Layer) ]
        ↓
[ Flask + SocketIO Backend (Processing + Bridge Layer) ]
        ↓
[ WebSocket Channel ]
        ↓
[ Browser UI (Visualization Layer) ]
```

---

## 2. Core Architectural Concepts

### 🔹 Pub/Sub (Publisher–Subscriber Model)

* MQTT is used to decouple producers and consumers.
* The simulator publishes data.
* The Flask backend subscribes to it.

### 🔹 Event-Driven System

* System reacts to incoming data events (`on_message`)
* No polling → fully reactive

### 🔹 Real-Time Streaming

* WebSocket (Socket.IO) ensures instant UI updates
* No page refresh required

---

## 3. Component Roles

| Component      | Role                         |
| -------------- | ---------------------------- |
| MQTT Publisher | Simulates patient data       |
| MQTT Broker    | Message routing              |
| Flask Server   | Processing + decision engine |
| Socket.IO      | Real-time communication      |
| Frontend       | Visualization                |

---

# 📁 File Breakdown

---

## 1. Frontend (HTML Dashboard)

### Responsibilities:

* Display patient data
* Show doctor alerts
* Maintain UI state dynamically

---

### Key Features:

#### 🔸 Real-time connection

```javascript
const socket = io();
```

Creates persistent connection with backend.

---

#### 🔸 Dynamic patient tracking

* Uses `patient_id` as unique key
* Creates UI card if patient is new
* Updates existing card otherwise

---

#### 🔸 Data rendered:

* Heart Rate
* Blood Pressure
* Mood
* Sleep Duration
* Temperature
* Fatigue

---

#### 🔸 Doctor alert system

Each alert:

* Is routed to correct doctor panel
* Appears temporarily (6 seconds)
* Highlights abnormal conditions

---

---

## 2. Flask + MQTT Bridge (Backend Core)

### Responsibilities:

* Subscribe to MQTT topic
* Maintain latest patient state
* Analyze health conditions
* Emit updates to frontend

---

### Internal Data Structures

#### PATIENTS

```python
PATIENTS = {}
```

Stores latest data per patient.

---

#### DOCTOR_TOPICS

```python
{
  'cardiology': ['heart_rate', 'bp'],
  'psychiatry': ['mood', 'sleep'],
  'general': ['temp', 'fatigue']
}
```

Defines mapping between:

* Medical domain
* Relevant metrics

---

---

### 🔬 Analysis Engine

This is a **rule-based decision system**.

#### Cardiology:

* Heart rate > 110
* BP > 140

#### Psychiatry:

* Mood = anxious
* Sleep < 5

#### General:

* Temperature > 100
* Fatigue = True

---

### 🔄 MQTT Message Lifecycle

#### Step 1: Message arrives

```python
on_message(client, userdata, msg)
```

---

#### Step 2: Decode payload

```python
json.loads(msg.payload.decode())
```

---

#### Step 3: Update state

```python
PATIENTS[pid] = payload
```

---

#### Step 4: Emit patient update

```python
socketio.emit('patient_update', payload)
```

---

#### Step 5: Run analysis loop

```python
for topic in DOCTOR_TOPICS:
```

---

#### Step 6: Emit alerts

```python
socketio.emit('doctor_alert', {...})
```

---

---

### 🔌 MQTT Configuration

```python
mqtt_client.connect('localhost', 1883)
mqtt_client.subscribe('patients/data')
```

* Broker runs locally
* Topic: `patients/data`

---

### 🧵 Threading Model

```python
threading.Thread(target=mqtt_client.loop_forever, daemon=True)
```

Why needed:

* MQTT loop is blocking
* Flask must run simultaneously
* Thread ensures parallel execution

---

---

## 3. MQTT Publisher (Simulator)

### Responsibilities:

* Simulate real patient vitals
* Publish data continuously

---

### Key Concepts

#### Unique patient identity

```python
uuid.uuid4()
```

Each script instance = separate patient

---

#### Data generation

Randomized simulation:

* Heart rate: 60–130
* BP: 100–170
* Mood: happy / normal / anxious
* Sleep: 3–9 hours
* Temperature: 97–103°F
* Fatigue: boolean

---

#### Publishing

```python
client.publish('patients/data', json.dumps(payload))
```

---

#### Frequency

```python
time.sleep(3)
```

New data every 3 seconds

---

# 🔁 End-to-End Data Flow (Detailed)

### Step-by-step:

1. Simulator generates patient data
2. Publishes to MQTT topic `patients/data`
3. MQTT broker receives and forwards to subscribers
4. Flask backend receives message via `on_message`
5. Backend:

   * Stores data
   * Runs analysis rules
6. Backend emits:

   * `patient_update`
   * `doctor_alert` (if needed)
7. Frontend receives events via Socket.IO
8. UI updates instantly

---

# ⚙️ Integration Details

## MQTT ↔ Flask Integration

* Flask subscribes using `paho-mqtt`
* Callback `on_message` acts as entry point

---

## Flask ↔ Frontend Integration

* Uses Socket.IO protocol
* Enables bidirectional communication
* Avoids HTTP request overhead

---

## Data Contract

Payload format:

```json
{
  "patient_id": "string",
  "heart_rate": number,
  "bp": number,
  "mood": "string",
  "sleep": number,
  "temp": number,
  "fatigue": boolean
}
```

---

# 🚀 Manual: How to Run the Project

---

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2: Install MQTT Broker

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install mosquitto
```

---

## Step 3: Start MQTT Broker

```bash
mosquitto
```

Default:

* Host: localhost
* Port: 1883

---

## Step 4: Start Backend Server

```bash
python app.py
```
Expected:

* Flask server starts
* MQTT thread starts listening

---

## Step 5: Open Dashboard

Open browser:

```
http://localhost:5000
```

---

## Step 6: Start Simulator

```bash
python simulator.py
```

Optional:

* Run multiple times for multiple patients

---

## Step 7: Observe System Behavior

You should see:

* Patient cards updating every 3 seconds
* Alerts appearing under:

  * Cardiology
  * Psychiatry
  * General

---

# 🧩 Notes

* System runs fully locally
* No database persistence
* No authentication
* Designed for demonstration and extensibility

---

# 📈 Summary

This project demonstrates:

* Real-time distributed systems
* MQTT-based communication
* Event-driven backend processing
* Live UI updates using WebSockets
* Basic medical rule engine

---
