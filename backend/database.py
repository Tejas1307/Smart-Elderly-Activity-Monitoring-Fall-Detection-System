import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "elderly_monitor.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity TEXT NOT NULL,
        confidence REAL NOT NULL,
        impact_g REAL DEFAULT 1.0,
        timestamp TEXT NOT NULL,
        device_id TEXT DEFAULT 'ESP32_NODE_01'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fall_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        severity TEXT DEFAULT 'CRITICAL',
        status TEXT DEFAULT 'UNRESOLVED',
        impact_g REAL NOT NULL,
        pre_activity TEXT DEFAULT 'Walking',
        resolved_at TEXT,
        notes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timeline_intervals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        duration_seconds INTEGER NOT NULL,
        date_str TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed initial realistic historical data if database is fresh
    cursor.execute("SELECT COUNT(*) FROM timeline_intervals")
    if cursor.fetchone()[0] == 0:
        seed_sample_data(conn)

    conn.close()

def seed_sample_data(conn):
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()

    # Create realistic timeline blocks for today leading up to the current hour
    current_hour = now.hour
    cursor_time = datetime(now.year, now.month, now.day, 6, 0, 0)
    
    schedule = [
        ("Lying", 45),              # 06:00 - 06:45
        ("Sitting", 30),            # 06:45 - 07:15
        ("Walking", 40),            # 07:15 - 07:55 Morning stroll
        ("Sitting", 50),            # 07:55 - 08:45 Breakfast
        ("Standing", 35),           # 08:45 - 09:20 Preparing tea
        ("Walking upstairs", 15),   # 09:20 - 09:35 Upstairs bedroom
        ("Sitting", 110),           # 09:35 - 11:25 Reading & TV
        ("Walking", 25),            # 11:25 - 11:50 Garden walk
        ("Standing", 20),           # 11:50 - 12:10 Lunch prep
        ("Sitting", 60),            # 12:10 - 13:10 Lunch
        ("Lying", 75),              # 13:10 - 14:25 Afternoon nap
        ("Sitting", 45),            # 14:25 - 15:10 Waking up, sitting
        ("Walking downstairs", 15), # 15:10 - 15:25 Coming downstairs
        ("Walking", 30),            # 15:25 - 15:55 Living room movement
    ]

    for act, duration_mins in schedule:
        end_time = cursor_time + timedelta(minutes=duration_mins)
        if cursor_time > now:
            break
        actual_end = min(end_time, now)
        dur_secs = int((actual_end - cursor_time).total_seconds())
        if dur_secs > 0:
            cursor.execute("""
            INSERT INTO timeline_intervals (activity, start_time, end_time, duration_seconds, date_str)
            VALUES (?, ?, ?, ?, ?)
            """, (act, cursor_time.strftime("%H:%M"), actual_end.strftime("%H:%M"), dur_secs, today_str))
        cursor_time = end_time

    # Seed one historical resolved fall event from yesterday afternoon for verification/auditing demonstration
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d 16:42:15")
    yesterday_res = (now - timedelta(days=1)).strftime("%Y-%m-%d 16:43:08")
    cursor.execute("""
    INSERT INTO fall_events (timestamp, severity, status, impact_g, pre_activity, resolved_at, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        yesterday_str,
        "CRITICAL",
        "ACKNOWLEDGED",
        3.42,
        "Walking",
        yesterday_res,
        "Slip in living room carpet. Caregiver assisted within 53 seconds; senior reported no injury."
    ))

    conn.commit()

def log_activity(activity: str, confidence: float, impact_g: float = 1.0, device_id: str = "ESP32_NODE_01"):
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO activity_logs (activity, confidence, impact_g, timestamp, device_id)
    VALUES (?, ?, ?, ?, ?)
    """, (activity, confidence, impact_g, now_str, device_id))
    conn.commit()
    conn.close()

def log_fall(impact_g: float, pre_activity: str = "Walking") -> int:
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO fall_events (timestamp, severity, status, impact_g, pre_activity)
    VALUES (?, ?, ?, ?, ?)
    """, (now_str, "CRITICAL", "UNRESOLVED", impact_g, pre_activity))
    fall_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return fall_id

def resolve_fall(fall_id: int, status: str, notes: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE fall_events 
    SET status = ?, resolved_at = ?, notes = ?
    WHERE id = ?
    """, (status, now_str, notes, fall_id))
    conn.commit()
    conn.close()

def get_recent_falls(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, timestamp, severity, status, impact_g, pre_activity, resolved_at, notes
    FROM fall_events
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_unresolved_falls() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, timestamp, severity, status, impact_g, pre_activity, resolved_at, notes
    FROM fall_events
    WHERE status = 'UNRESOLVED'
    ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_today_timeline() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
    SELECT id, activity, start_time, end_time, duration_seconds
    FROM timeline_intervals
    WHERE date_str = ?
    ORDER BY id ASC
    """, (today_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_or_append_timeline(activity: str, duration_delta_secs: int = 1):
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_hm = datetime.now().strftime("%H:%M")

    cursor.execute("""
    SELECT id, activity, start_time, end_time, duration_seconds 
    FROM timeline_intervals 
    WHERE date_str = ? 
    ORDER BY id DESC LIMIT 1
    """, (today_str,))
    last_row = cursor.fetchone()

    if last_row and last_row["activity"] == activity:
        # Extend the current interval
        new_dur = last_row["duration_seconds"] + duration_delta_secs
        cursor.execute("""
        UPDATE timeline_intervals 
        SET end_time = ?, duration_seconds = ?
        WHERE id = ?
        """, (now_hm, new_dur, last_row["id"]))
    else:
        # Start a new interval
        cursor.execute("""
        INSERT INTO timeline_intervals (activity, start_time, end_time, duration_seconds, date_str)
        VALUES (?, ?, ?, ?, ?)
        """, (activity, now_hm, now_hm, duration_delta_secs, today_str))

    conn.commit()
    conn.close()

def get_today_durations() -> Dict[str, int]:
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
    SELECT activity, SUM(duration_seconds) as total_secs
    FROM timeline_intervals
    WHERE date_str = ?
    GROUP BY activity
    """, (today_str,))
    rows = cursor.fetchall()
    conn.close()
    result = {
        "Walking": 0,
        "Walking upstairs": 0,
        "Walking downstairs": 0,
        "Sitting": 0,
        "Standing": 0,
        "Lying": 0
    }
    for row in rows:
        result[row["activity"]] = row["total_secs"]
    return result
