import paho.mqtt.client as mqtt
import random, time, json, uuid

pid = str(uuid.uuid4())[:8]
client = mqtt.Client()
client.connect('localhost', 1883)

moods = ['happy', 'normal', 'anxious']

while True:
    payload = {
        'patient_id': pid,
        'heart_rate': random.randint(60,130),
        'bp': random.randint(100,170),
        'mood': random.choice(moods),
        'sleep': random.randint(3,9),
        'temp': round(random.uniform(97,103),1),
        'fatigue': random.choice([True, False])
    }
    client.publish('patients/data', json.dumps(payload))
    print('Published:', payload)
    time.sleep(3)