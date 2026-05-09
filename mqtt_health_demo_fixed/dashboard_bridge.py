import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import asyncio
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

import paho.mqtt.client as mqtt
import websockets

from crypto.otp import unpackage_payload

# ── Config ─────────────────────────────────────────────────────────────────────
MQTT_HOST   = "localhost"
MQTT_PORT   = 1884
WS_HOST     = "localhost"
WS_PORT     = 8765

ALL_TOPICS  = [
    "health/status",
    "health/symptoms",
    "health/medication",
    "health/wellness",
]

# ── Shared state ───────────────────────────────────────────────────────────────
connected_ws_clients: set = set()
message_queue: asyncio.Queue = None
main_loop: asyncio.AbstractEventLoop = None   # ✅ NEW


# ── MQTT callbacks ─────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"  [MQTT] ✓ Connected to broker at {MQTT_HOST}:{MQTT_PORT}")
        for topic in ALL_TOPICS:
            client.subscribe(topic, qos=1)
            print(f"  [MQTT] Subscribed → {topic}")
    else:
        print(f"  [MQTT] ✗ Failed to connect (rc={reason_code})")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        raw = msg.payload.decode("utf-8")
        packet = json.loads(raw)

        data, integrity_ok = unpackage_payload(raw)

        encrypted_preview = packet.get("payload", {})
        frame = {
            "topic":             topic,
            "data":              data,
            "integrity_ok":      integrity_ok,
            "encrypted_preview": {
                "ciphertext": encrypted_preview.get("ciphertext", "")[:80] + "…",
                "key":        encrypted_preview.get("key", "")[:80] + "…",
                "checksum":   encrypted_preview.get("checksum", ""),
            },
            "timestamp": datetime.now().isoformat(),
        }

        ts = datetime.now().strftime("%H:%M:%S")
        pid = data.get("patient_id", "?")
        ok  = "✓" if integrity_ok else "✗ TAMPERED"
        print(f"  [{ts}] {topic:<22} │ {pid} │ integrity={ok}")

        # ✅ FIXED THREAD-SAFE COMMUNICATION
        if message_queue and main_loop:
            main_loop.call_soon_threadsafe(
                message_queue.put_nowait,
                json.dumps(frame)
            )

    except Exception as e:
        print(f"  [MQTT] Error on {topic}: {e}")


# ── WebSocket server ───────────────────────────────────────────────────────────

async def ws_handler(websocket):
    connected_ws_clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"  [WS]   ✓ Dashboard connected from {client_addr}")
    try:
        async for raw_msg in websocket:
            try:
                cmd = json.loads(raw_msg)
                if cmd.get("cmd") == "set_qos":
                    print(f"  [WS]   QoS changed to {cmd.get('qos')}")
            except Exception:
                pass
    except websockets.exceptions.ConnectionClosedOK:
        pass
    finally:
        connected_ws_clients.discard(websocket)
        print(f"  [WS]   Dashboard disconnected from {client_addr}")


async def broadcast_loop():
    global message_queue
    message_queue = asyncio.Queue()
    while True:
        frame = await message_queue.get()
        if connected_ws_clients:
            await asyncio.gather(
                *[client.send(frame) for client in list(connected_ws_clients)],
                return_exceptions=True
            )


async def main_async():
    global main_loop   # ✅ NEW

    print("\n" + "=" * 60)
    print("  MQTT Health Monitor — Dashboard Bridge")
    print("=" * 60)
    print(f"  WebSocket server : ws://{WS_HOST}:{WS_PORT}")
    print(f"  MQTT broker      : {MQTT_HOST}:{MQTT_PORT}")
    print("=" * 60 + "\n")

    # ✅ CAPTURE MAIN EVENT LOOP
    main_loop = asyncio.get_running_loop()

    mqtt_client = mqtt.Client(
        client_id="dashboard-bridge",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    except ConnectionRefusedError:
        print(f"  ✗ Cannot connect to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        print("    Start Mosquitto first: mosquitto -v")
        return

    mqtt_client.loop_start()

    dashboard_path = Path(__file__).parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        print(f"\n  Opening dashboard: {dashboard_path.as_uri()}")
        webbrowser.open(dashboard_path.as_uri())
    else:
        print(f"\n  Open dashboard/index.html in your browser manually")

    print(f"\n  Bridge running. Ctrl+C to stop.\n")

    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await broadcast_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n  Bridge stopped.")