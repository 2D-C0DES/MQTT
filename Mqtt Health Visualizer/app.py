from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json, random, time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

PATIENTS = {}
DOCTOR_TOPICS = {
    'cardiology': ['heart_rate', 'bp'],
    'psychiatry': ['mood', 'sleep'],
    'general': ['temp', 'fatigue']
}

def analyze(topic, data):
    if topic == 'cardiology':
        if data['heart_rate'] > 110 or data['bp'] > 140:
            return 'Possible cardiac issue detected'
    elif topic == 'psychiatry':
        if data['mood'] == 'anxious' or data['sleep'] < 5:
            return 'Stress / anxiety indicators'
    elif topic == 'general':
        if data['temp'] > 100 or data['fatigue']:
            return 'General illness suspected'
    return None


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    pid = payload['patient_id']

    PATIENTS[pid] = payload
    socketio.emit('patient_update', payload)

    for topic in DOCTOR_TOPICS:
        response = analyze(topic, payload)
        if response:
            socketio.emit('doctor_alert', {
                'doctor': topic,
                'patient_id': pid,
                'response': response
            })

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect('localhost', 1883)
mqtt_client.subscribe('patients/data')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    import threading
    threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()
    socketio.run(app, debug=True)
