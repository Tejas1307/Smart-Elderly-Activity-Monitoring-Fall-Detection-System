#!/usr/bin/env python3
"""
Simulate an ESP32 Wearable Node transmitting 50Hz IMU windows over Wi-Fi to the server.
Usage:
    python scripts/simulate_esp32.py [--url http://localhost:8000/api/imu/stream]
"""

import argparse
import math
import random
import time
import requests

def run_simulation(server_url: str, duration_sec: int = 3600):
    print(f"[*] Starting ESP32 Sensor Node Simulator...")
    print(f"[*] Target Endpoint: {server_url}")
    print(f"[*] Streaming 50 Hz batches (25 samples / batch every 500ms)...")

    activities = ["Walking", "Walking upstairs", "Walking downstairs", "Sitting", "Standing", "Lying"]
    current_activity = "Walking"
    activity_switch_time = time.time() + 15
    phase = 0.0

    while True:
        now = time.time()
        if now > activity_switch_time:
            current_activity = random.choice(activities)
            activity_switch_time = now + random.randint(15, 30)
            print(f"[ESP32] Transitioning motion pattern to: {current_activity}")

        batch = []
        for _ in range(25):
            phase += 0.15
            sin_v = math.sin(phase)
            cos_v = math.cos(phase)

            if current_activity == "Walking":
                ax = 0.15 * sin_v + random.uniform(-0.03, 0.03)
                ay = 0.25 * cos_v + random.uniform(-0.03, 0.03)
                az = 1.0 + 0.35 * abs(sin_v)
                gx = 35.0 * sin_v
                gy = 20.0 * cos_v
                gz = 15.0 * sin_v
            elif "upstairs" in current_activity:
                ax = 0.22 * sin_v
                ay = 0.32 * cos_v
                az = 1.15 + 0.55 * abs(sin_v)
                gx = 50.0 * sin_v
                gy = 30.0 * cos_v
                gz = 20.0 * sin_v
            elif "downstairs" in current_activity:
                ax = 0.18 * sin_v
                ay = 0.28 * cos_v
                az = 0.90 + 0.48 * (sin_v if sin_v > 0 else -0.2)
                gx = 45.0 * sin_v
                gy = 35.0 * cos_v
                gz = 18.0 * sin_v
            elif current_activity == "Sitting":
                ax = 0.12 + random.uniform(-0.01, 0.01)
                ay = 0.38 + random.uniform(-0.01, 0.01)
                az = 0.88 + random.uniform(-0.01, 0.01)
                gx = gy = gz = random.uniform(-1, 1)
            elif current_activity == "Standing":
                ax = 0.05 + random.uniform(-0.01, 0.01)
                ay = 0.04 + random.uniform(-0.01, 0.01)
                az = 0.99 + random.uniform(-0.01, 0.01)
                gx = gy = gz = random.uniform(-1, 1)
            else:  # Lying
                ax = 0.94 + random.uniform(-0.01, 0.01)
                ay = 0.08 + random.uniform(-0.01, 0.01)
                az = 0.12 + random.uniform(-0.01, 0.01)
                gx = gy = gz = 0.0

            batch.append({
                "ax": round(ax, 3),
                "ay": round(ay, 3),
                "az": round(az, 3),
                "gx": round(gx, 2),
                "gy": round(gy, 2),
                "gz": round(gz, 2),
                "timestamp": now
            })

        payload = {
            "device_id": "ESP32_NODE_01",
            "battery_pct": random.randint(80, 85),
            "rssi": random.randint(-68, -60),
            "samples": batch
        }

        try:
            res = requests.post(server_url, json=payload, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                print(f"[ESP32 -> Server] Window sent. Recognized: {data.get('activity')} (conf: {data.get('confidence')})")
        except Exception as e:
            print(f"[ESP32] Transmission failed: {e}")

        time.sleep(0.5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/api/imu/stream", help="Server endpoint")
    args = parser.parse_args()
    run_simulation(args.url)
