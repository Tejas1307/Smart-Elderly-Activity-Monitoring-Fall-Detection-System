# Smart Elderly Activity Monitoring & Fall Detection System (MVP)

A wearable motion sensing and AI-assisted healthcare monitoring platform designed for senior safety and caregiver situational awareness.

---

## 📋 System Architecture

```text
[MPU6050 IMU] ──(I²C @ 50Hz)──> [ESP32 Node] ──(Wi-Fi JSON Stream)──> [Python Server / FastAPI]
                                                                               │
                                                                   ┌───────────┴───────────┐
                                                                   ▼                       ▼
                                                        [Preprocessing & AI]     [SQLite Database]
                                                        • 6-Class Activity       • Activity Durations
                                                        • Fall Detection         • Fall History Logs
                                                                   │                       │
                                                                   └───────────┬───────────┘
                                                                               ▼
                                                                [Caregiver Web Dashboard]
                                                                (Real-Time WebSocket)
```

---

## 🎯 20% Milestone Demonstration Features

This prototype fulfills the initial **20% milestone** (Days 1–4 of the 15–20 day plan):
1. **Interactive Caregiver Web Dashboard**: Includes all 6 core modules specified in **Section 8** of the proposal.
2. **Real-time Telemetry & Oscilloscope**: 50Hz 3-axis accelerometer (`Ax`, `Ay`, `Az`) and gyroscope waveform streaming with sub-second latency.
3. **AI Activity Classification Pipeline**: Recognizes 6 distinct human activities matching the UCI HAR dataset:
   - `Walking` (Active movement)
   - `Walking upstairs` (High-intensity movement)
   - `Walking downstairs` (High-intensity movement)
   - `Sitting` (Sedentary state)
   - `Standing` (Stationary upright state)
   - `Lying` (Resting state)
4. **Safety-Critical Fall Detection Workflow**:
   - Impact acceleration shock detection (`SVM > 2.8g`)
   - Temporal confirmation rule (post-impact stationary posture) to filter false alarms
   - High-priority emergency alert modal with audio chime (Web Audio API)
   - Event logging with caregiver acknowledgment/false alarm resolution
5. **Interactive Sensor Simulator Toolbar**: Test and demonstrate all motion states and emergency fall alerts directly from the browser without needing physical hardware attached.
6. **ESP32 Firmware**: Arduino sketch (`firmware/esp32_mpu6050/esp32_mpu6050.ino`) ready for flashing to an ESP32 board.
7. **ESP32 Telemetry Test Script**: Standalone Python script (`scripts/simulate_esp32.py`) simulating remote Wi-Fi sensor packets.

---

## 📊 Dashboard Modules (Section 8 Mapping)

| Module | Features & Implementation |
| :--- | :--- |
| **Module 1: Current Activity** | Real-time recognized activity badge, AI confidence gauge (%), and dynamic impact g-force. |
| **Module 2: Activity Duration** | Cumulative time spent today across all 6 activities with proportional progress bars. |
| **Module 3: Daily Timeline** | 24-hour visual ribbon breakdown and chronological history log of today's activities. |
| **Module 4: Activity Summary** | Compact daily overview: Active vs. Sedentary vs. Resting time, movement intensity metric, donut chart. |
| **Module 5: Fall Events** | Incident log table (timestamp, pre-activity, impact shock g-force, status) with quick response buttons. |
| **Module 6: System Status** | ESP32 hardware diagnostics (battery %, RSSI, sampling rate, transmission latency, server health). |

---

## 🚀 Quickstart Guide

### 1. Environment Setup
```bash
cd /home/tejas/project/idp
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Backend & Caregiver Dashboard
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in any web browser.

### 3. How to Demonstrate in Presentation:
- **Demonstrate Activities**: Click any of the state buttons in the top toolbar (`Walking`, `Stairs (Up)`, `Sitting`, etc.). The dashboard will immediately update the current activity, confidence, description, and live oscilloscope waveforms.
- **Demonstrate Fall Detection**: Click the red **"Simulate Fall (3.8g)"** button. The dashboard will:
  1. Trigger an urgent emergency modal with blinking red beacon.
  2. Play an audible chime sequence through the browser.
  3. Log the incident into the Fall Events table with a `CRITICAL ALERT` badge.
  4. Allow the reviewer to click **"Acknowledge & Dispatch Help"** or **"Mark False Alarm"**.
- **Demonstrate External ESP32 Streaming**:
  In a separate terminal, run:
  ```bash
  source venv/bin/activate
  python scripts/simulate_esp32.py
  ```

---

## 🔌 Hardware Setup (ESP32 + MPU6050)

When you are ready to test the physical wearable hardware:

### Wiring Diagram
| MPU6050 Pin | ESP32 Dev Board Pin | Notes |
| :--- | :--- | :--- |
| **VCC** | **3.3V** | Power supply |
| **GND** | **GND** | Ground reference |
| **SDA** | **GPIO 21** | I²C Data line |
| **SCL** | **GPIO 22** | I²C Clock line |

### Flashing Firmware
1. Open [`firmware/esp32_mpu6050/esp32_mpu6050.ino`](file:///home/tejas/project/idp/firmware/esp32_mpu6050/esp32_mpu6050.ino) in Arduino IDE or VS Code PlatformIO.
2. Install libraries: `Wire`, `WiFi`, `HTTPClient`, `ArduinoJson` (v6+).
3. Set your Wi-Fi SSID, Password, and your server's local IP address (`http://<SERVER_IP>:8000/api/imu/stream`).
4. Select board **ESP32 Dev Module** and upload.

---

## 📁 Project Structure

```text
idp/
├── Smart_Elderly_Activity_Monitoring_Fall_Detection_Revised_Proposal-1.pdf
├── README.md
├── requirements.txt
├── backend/
│   ├── main.py              # FastAPI server with WebSockets & REST endpoints
│   ├── database.py          # SQLite schema & persistence (activities, falls, timeline)
│   ├── ml_pipeline.py       # Sensor windowing, 6-class HAR & fall temporal confirmation
│   ├── models.py            # Pydantic data schemas
│   └── simulator.py         # Realistic IMU waveform generator
├── static/
│   ├── index.html           # Clinical Caregiver Dashboard (Tailwind CSS + Chart.js)
│   ├── css/styles.css       # Custom animations, pulse beacons, glassmorphism
│   └── js/
│       ├── dashboard.js     # Real-time WebSocket client, chart rendering, UI state
│       └── audio_alerts.js  # Emergency alarm chime (Web Audio API)
├── scripts/
│   ├── simulate_esp32.py    # Remote ESP32 Wi-Fi streaming simulation
│   └── uci_har_pipeline.py  # Phase 1 & 2 dataset preprocessing definitions
└── firmware/
    └── esp32_mpu6050/
        └── esp32_mpu6050.ino # Complete ESP32 Arduino firmware sketch
```
