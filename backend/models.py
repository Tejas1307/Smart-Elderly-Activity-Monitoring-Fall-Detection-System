from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class IMUSample(BaseModel):
    ax: float = Field(..., description="Acceleration X in g or m/s^2")
    ay: float = Field(..., description="Acceleration Y in g or m/s^2")
    az: float = Field(..., description="Acceleration Z in g or m/s^2")
    gx: float = Field(..., description="Angular velocity X in deg/s or rad/s")
    gy: float = Field(..., description="Angular velocity Y in deg/s or rad/s")
    gz: float = Field(..., description="Angular velocity Z in deg/s or rad/s")
    timestamp: Optional[float] = Field(None, description="Epoch timestamp of sample")

class IMUPayload(BaseModel):
    device_id: str = "ESP32_NODE_01"
    battery_pct: Optional[int] = 85
    rssi: Optional[int] = -62
    samples: List[IMUSample] = []

class ActivityState(BaseModel):
    activity: str
    confidence: float
    timestamp: str
    impact_g: float = 1.0
    is_fall: bool = False

class FallAlert(BaseModel):
    id: int
    timestamp: str
    severity: str = "CRITICAL"
    status: str = "UNRESOLVED"  # UNRESOLVED, ACKNOWLEDGED, FALSE_ALARM
    impact_g: float
    pre_activity: str
    resolved_at: Optional[str] = None
    notes: Optional[str] = None

class SystemHealth(BaseModel):
    device_id: str = "ESP32_NODE_01"
    connected: bool = True
    battery_pct: int = 85
    rssi: int = -62
    last_packet_time: str
    sample_rate_hz: int = 50
    latency_ms: int = 24
    server_status: str = "HEALTHY"
    model_version: str = "1D-CNN + Temporal Confirmation v1.0"

class ActivitySummary(BaseModel):
    active_minutes: int
    sedentary_minutes: int
    resting_minutes: int
    movement_intensity: str  # "Low", "Moderate", "High"
    total_falls_today: int
    durations: Dict[str, int]  # Activity name -> seconds
