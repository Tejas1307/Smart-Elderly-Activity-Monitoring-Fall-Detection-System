import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import (
    init_db, log_activity, log_fall, resolve_fall,
    get_recent_falls, get_unresolved_falls, get_today_timeline,
    update_or_append_timeline, get_today_durations
)
from backend.models import (
    IMUSample, IMUPayload, ActivityState, FallAlert, SystemHealth, ActivitySummary
)
from backend.ml_pipeline import IMUMLPipeline
from backend.simulator import IMUSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elderly_monitor")

app = FastAPI(
    title="Smart Elderly Activity Monitoring & Fall Detection System",
    description="Caregiver Dashboard & Inference API (Wearable IMU MVP)",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Core singletons
ml_pipeline = IMUMLPipeline(window_size=50, fall_impact_threshold_g=2.8)
simulator = IMUSimulator()

# State variables
current_activity_state = ActivityState(
    activity="Walking",
    confidence=0.94,
    timestamp=datetime.now().strftime("%H:%M:%S"),
    impact_g=1.05,
    is_fall=False
)
system_health = SystemHealth(
    device_id="ESP32_NODE_01",
    connected=True,
    battery_pct=84,
    rssi=-63,
    last_packet_time=datetime.now().strftime("%H:%M:%S"),
    sample_rate_hz=50,
    latency_ms=22,
    server_status="HEALTHY",
    model_version="1D-CNN + Temporal Confirmation v1.0"
)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# Simulation controller
auto_simulation_enabled = True
last_esp32_packet_time = 0.0

@app.on_event("startup")
async def startup_event():
    # Start the continuous background broadcast loop
    asyncio.create_task(background_telemetry_loop())

async def broadcast_message(message: dict):
    if not active_connections:
        return
    dead_connections = set()
    data = json.dumps(message)
    for ws in list(active_connections):
        try:
            await ws.send_text(data)
        except Exception:
            dead_connections.add(ws)
    active_connections.difference_update(dead_connections)

# Background telemetry & simulation task
async def background_telemetry_loop():
    last_timeline_tick = time.time()
    last_status_tick = time.time()

    while True:
        try:
            await asyncio.sleep(0.1)  # 10 Hz broadcast for dashboard graphs
            now = time.time()

            # If ESP32 is silent for > 5 seconds and auto-simulation is on, use simulator
            is_using_simulator = (now - last_esp32_packet_time > 5.0) and auto_simulation_enabled

            if is_using_simulator:
                sample = simulator.generate_sample()
                state, is_fall = ml_pipeline.process_sample(sample)
                system_health.connected = True
                system_health.last_packet_time = datetime.now().strftime("%H:%M:%S")
                system_health.latency_ms = 18 + int((now * 10) % 12)
            else:
                sample = ml_pipeline.buffer[-1] if ml_pipeline.buffer else IMUSample(ax=0, ay=0, az=1, gx=0, gy=0, gz=0)
                state = current_activity_state
                is_fall = False

            # Update current state
            current_activity_state.activity = state.activity
            current_activity_state.confidence = state.confidence
            current_activity_state.timestamp = datetime.now().strftime("%H:%M:%S")
            current_activity_state.impact_g = state.impact_g
            current_activity_state.is_fall = is_fall

            # Handle fall detection event
            fall_payload = None
            if is_fall:
                fall_id = log_fall(impact_g=state.impact_g, pre_activity="Walking")
                fall_payload = {
                    "id": fall_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "severity": "CRITICAL",
                    "status": "UNRESOLVED",
                    "impact_g": state.impact_g,
                    "pre_activity": "Walking"
                }
                logger.warning(f"FALL DETECTED! ID: {fall_id}, Impact: {state.impact_g}g")

            # Timeline and duration aggregation (every 2 seconds)
            if now - last_timeline_tick >= 2.0:
                last_timeline_tick = now
                update_or_append_timeline(current_activity_state.activity, duration_delta_secs=2)

            # Broadcast live telemetry packet over WebSocket
            telemetry_msg = {
                "type": "telemetry",
                "sample": sample.model_dump(),
                "activity_state": current_activity_state.model_dump(),
                "system_health": system_health.model_dump(),
                "fall_alert": fall_payload
            }
            await broadcast_message(telemetry_msg)

        except Exception as e:
            logger.error(f"Error in telemetry loop: {e}", exc_info=True)
            await asyncio.sleep(1)

# WebSocket Endpoint
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        # Send initial full state snapshot
        today_durations = get_today_durations()
        timeline = get_today_timeline()
        recent_falls = get_recent_falls(limit=10)
        unresolved = get_unresolved_falls()

        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "activity_state": current_activity_state.model_dump(),
            "system_health": system_health.model_dump(),
            "durations": today_durations,
            "timeline": timeline[-15:],
            "recent_falls": recent_falls,
            "unresolved_falls": unresolved
        }))

        while True:
            # Keep connection open and accept client messages if any
            data = await websocket.receive_text()
            # Can receive ping or client commands
    except WebSocketDisconnect:
        active_connections.discard(websocket)
    except Exception:
        active_connections.discard(websocket)

# REST Endpoints for ESP32 and Caregiver Dashboard

@app.post("/api/imu/stream")
async def ingest_imu_stream(payload: IMUPayload):
    """
    Receives live batches of timestamped IMU windows from ESP32 over Wi-Fi.
    """
    global last_esp32_packet_time
    last_esp32_packet_time = time.time()

    if payload.battery_pct is not None:
        system_health.battery_pct = payload.battery_pct
    if payload.rssi is not None:
        system_health.rssi = payload.rssi
    system_health.connected = True
    system_health.last_packet_time = datetime.now().strftime("%H:%M:%S")

    state, is_fall = ml_pipeline.process_batch(payload.samples)
    current_activity_state.activity = state.activity
    current_activity_state.confidence = state.confidence
    current_activity_state.impact_g = state.impact_g
    current_activity_state.is_fall = is_fall

    log_activity(state.activity, state.confidence, state.impact_g, device_id=payload.device_id)

    fall_id = None
    if is_fall:
        fall_id = log_fall(impact_g=state.impact_g, pre_activity=state.activity)

    return {
        "status": "success",
        "activity": state.activity,
        "confidence": state.confidence,
        "is_fall": is_fall,
        "fall_id": fall_id
    }

@app.get("/api/dashboard/current")
async def get_current_status():
    return {
        "activity_state": current_activity_state,
        "system_health": system_health,
        "unresolved_falls": get_unresolved_falls()
    }

@app.get("/api/dashboard/durations")
async def get_durations():
    return get_today_durations()

@app.get("/api/dashboard/timeline")
async def get_timeline():
    return get_today_timeline()

@app.get("/api/dashboard/summary")
async def get_summary():
    durations = get_today_durations()
    # Active = Walking, Walking upstairs, Walking downstairs
    active_secs = durations.get("Walking", 0) + durations.get("Walking upstairs", 0) + durations.get("Walking downstairs", 0)
    sedentary_secs = durations.get("Sitting", 0) + durations.get("Standing", 0)
    resting_secs = durations.get("Lying", 0)

    recent_falls = get_recent_falls(limit=50)
    today_falls = len([f for f in recent_falls if f["timestamp"].startswith(datetime.now().strftime("%Y-%m-%d"))])

    movement_intensity = "Moderate"
    if active_secs > 7200:
        movement_intensity = "High"
    elif active_secs < 1800:
        movement_intensity = "Low"

    return {
        "active_minutes": active_secs // 60,
        "sedentary_minutes": sedentary_secs // 60,
        "resting_minutes": resting_secs // 60,
        "total_monitoring_hours": round((active_secs + sedentary_secs + resting_secs) / 3600, 1),
        "movement_intensity": movement_intensity,
        "total_falls_today": today_falls,
        "durations": durations
    }

@app.get("/api/dashboard/falls")
async def get_falls():
    return get_recent_falls(limit=25)

class ResolveFallRequest(BaseModel):
    status: str = "ACKNOWLEDGED"  # ACKNOWLEDGED or FALSE_ALARM
    notes: str = ""

@app.post("/api/dashboard/falls/{fall_id}/resolve")
async def resolve_fall_endpoint(fall_id: int, req: ResolveFallRequest):
    resolve_fall(fall_id, status=req.status, notes=req.notes)
    # Broadcast fall resolution to all connected dashboards
    await broadcast_message({
        "type": "fall_resolved",
        "fall_id": fall_id,
        "status": req.status,
        "notes": req.notes
    })
    return {"status": "ok", "fall_id": fall_id, "resolved_as": req.status}

# Simulator interactive control endpoints
class ActivityChangeRequest(BaseModel):
    activity: str

@app.post("/api/simulator/activity")
async def set_simulator_activity(req: ActivityChangeRequest):
    if req.activity not in IMUMLPipeline.ACTIVITIES:
        raise HTTPException(status_code=400, detail="Invalid activity label")
    simulator.set_activity(req.activity)
    current_activity_state.activity = req.activity
    return {"status": "ok", "current_activity": req.activity}

class TriggerFallRequest(BaseModel):
    impact_g: float = 3.8

@app.post("/api/simulator/fall")
async def trigger_simulated_fall(req: TriggerFallRequest):
    simulator.trigger_fall(impact_g=req.impact_g)
    return {"status": "ok", "message": f"Simulated fall triggered with {req.impact_g}g impact"}

@app.post("/api/simulator/toggle")
async def toggle_simulator():
    global auto_simulation_enabled
    auto_simulation_enabled = not auto_simulation_enabled
    return {"status": "ok", "auto_simulation": auto_simulation_enabled}

# Static file serving
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "Caregiver Dashboard API running."})

@app.get("/history")
async def serve_history():
    return FileResponse(os.path.join(static_dir, "history.html"))

@app.get("/alerts")
async def serve_alerts():
    return FileResponse(os.path.join(static_dir, "alerts.html"))

@app.get("/patient")
async def serve_patient():
    return FileResponse(os.path.join(static_dir, "patient.html"))

@app.get("/device")
async def serve_device():
    return FileResponse(os.path.join(static_dir, "device.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
