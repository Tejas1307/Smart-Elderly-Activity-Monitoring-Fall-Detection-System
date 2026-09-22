"""
UCI Human Activity Recognition (HAR) & Fall Dataset Pipeline
Phase 1 & Phase 2: Dataset Ingestion, Windowing, Normalization, and Architecture Setup.

Classes (6 standard activities):
1: Walking
2: Walking Upstairs
3: Walking Downstairs
4: Sitting
5: Standing
6: Lying
"""

import os
import json
import urllib.request
import zipfile
from typing import Dict, Any, Tuple

CLASS_MAP = {
    1: "Walking",
    2: "Walking upstairs",
    3: "Walking downstairs",
    4: "Sitting",
    5: "Standing",
    6: "Lying"
}

WINDOW_SIZE = 128      # 2.56 seconds at 50 Hz
STEP_SIZE = 64         # 50% overlap
SAMPLING_RATE_HZ = 50  # 50 Hz matching MPU6050 ESP32 configuration

def summarize_pipeline_architecture() -> Dict[str, Any]:
    """
    Returns the Phase 1 & Phase 2 sensor-to-model compatibility mapping.
    """
    spec = {
        "dataset_name": "UCI Human Activity Recognition Using Smartphones / IMU",
        "imu_sensor": "MPU6050 (3-axis Accelerometer + 3-axis Gyroscope)",
        "sampling_frequency": f"{SAMPLING_RATE_HZ} Hz",
        "channels": [
            "body_acc_x (g)", "body_acc_y (g)", "body_acc_z (g)",
            "body_gyro_x (deg/s)", "body_gyro_y (deg/s)", "body_gyro_z (deg/s)"
        ],
        "window_length_samples": WINDOW_SIZE,
        "window_duration_seconds": round(WINDOW_SIZE / SAMPLING_RATE_HZ, 2),
        "overlap_percentage": "50%",
        "classes": list(CLASS_MAP.values()),
        "fall_detection_strategy": {
            "model_type": "Impact Acceleration Threshold + Temporal Posture Confirmation",
            "fall_threshold_g": 2.8,
            "confirmation_window_s": 2.0
        },
        "ml_model_candidates": [
            "1D-CNN (Temporal Convolution across 6 sensor channels)",
            "Multi-Layer Perceptron (MLP) on statistical features",
            "Random Forest baseline"
        ]
    }
    return spec

if __name__ == "__main__":
    print("=" * 65)
    print(" Smart Elderly Monitoring - Phase 1 & 2 ML Preprocessing Pipeline ")
    print("=" * 65)
    specs = summarize_pipeline_architecture()
    print(json.dumps(specs, indent=2))
