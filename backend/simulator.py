import math
import random
import time
from typing import List, Tuple
from backend.models import IMUSample

class IMUSimulator:
    """
    Generates realistic 6-axis IMU time-series data for testing and demonstration.
    Models human gait dynamics, stationary posture, and rapid fall transients.
    """
    def __init__(self):
        self.current_activity = "Walking"
        self.step_phase = 0.0
        self.is_fall_sequence = False
        self.fall_step = 0
        self.fall_impact_val = 3.65
        self.active_simulation = True

    def set_activity(self, activity: str):
        self.is_fall_sequence = False
        self.current_activity = activity

    def trigger_fall(self, impact_g: float = 3.65):
        self.is_fall_sequence = True
        self.fall_step = 0
        self.fall_impact_val = impact_g

    def generate_sample(self) -> IMUSample:
        now = time.time()
        self.step_phase += 0.15

        # Handle Fall Transient Sequence
        if self.is_fall_sequence:
            self.fall_step += 1
            if self.fall_step == 1:
                # Loss of balance / start of fall
                ax = random.uniform(-0.4, 0.4)
                ay = random.uniform(0.8, 1.3)
                az = 0.6 + random.uniform(-0.1, 0.1)
                gx = random.uniform(120, 240)
                gy = random.uniform(180, 320)
                gz = random.uniform(90, 160)
            elif self.fall_step == 2:
                # Free-fall phase: acceleration drops near 0g
                ax = random.uniform(-0.15, 0.15)
                ay = random.uniform(-0.15, 0.15)
                az = random.uniform(0.05, 0.25)
                gx = random.uniform(180, 420)
                gy = random.uniform(220, 500)
                gz = random.uniform(100, 280)
            elif self.fall_step == 3:
                # Impact spike: violent deceleration
                peak = self.fall_impact_val
                ax = random.choice([-1, 1]) * peak * 0.5
                ay = random.choice([-1, 1]) * peak * 0.4
                az = peak * 0.8
                gx = random.uniform(-350, 350)
                gy = random.uniform(-400, 400)
                gz = random.uniform(-250, 250)
            elif self.fall_step in [4, 5, 6]:
                # Post-impact rebound and settling
                ax = 0.85 + random.uniform(-0.05, 0.05)
                ay = 0.12 + random.uniform(-0.04, 0.04)
                az = 0.15 + random.uniform(-0.03, 0.03)
                gx = random.uniform(-8, 8)
                gy = random.uniform(-6, 6)
                gz = random.uniform(-4, 4)
            else:
                # Senior is motionless on the ground (Lying)
                self.is_fall_sequence = False
                self.current_activity = "Lying"
                ax = 0.95 + random.uniform(-0.02, 0.02)
                ay = 0.05 + random.uniform(-0.02, 0.02)
                az = 0.10 + random.uniform(-0.02, 0.02)
                gx = random.uniform(-2, 2)
                gy = random.uniform(-2, 2)
                gz = random.uniform(-2, 2)

            return IMUSample(
                ax=round(ax, 3), ay=round(ay, 3), az=round(az, 3),
                gx=round(gx, 2), gy=round(gy, 2), gz=round(gz, 2),
                timestamp=now
            )

        # Standard Activity Waveforms
        sin_val = math.sin(self.step_phase)
        cos_val = math.cos(self.step_phase)
        noise_a = lambda: random.uniform(-0.04, 0.04)
        noise_g = lambda: random.uniform(-3.0, 3.0)

        if self.current_activity == "Walking":
            # Walking gait at ~1.2 Hz
            ax = 0.15 * sin_val + noise_a()
            ay = 0.25 * cos_val + noise_a()
            az = 1.0 + 0.35 * abs(sin_val) + noise_a()
            gx = 35.0 * sin_val + noise_g()
            gy = 20.0 * cos_val + noise_g()
            gz = 15.0 * sin_val + noise_g()

        elif self.current_activity == "Walking upstairs":
            # Higher vertical thrust
            ax = 0.22 * sin_val + noise_a()
            ay = 0.32 * cos_val + noise_a()
            az = 1.08 + 0.55 * abs(sin_val) + noise_a()
            gx = 50.0 * sin_val + noise_g()
            gy = 30.0 * cos_val + noise_g()
            gz = 22.0 * sin_val + noise_g()

        elif self.current_activity == "Walking downstairs":
            # Sharp downward impacts
            ax = 0.18 * sin_val + noise_a()
            ay = 0.28 * cos_val + noise_a()
            az = 0.92 + 0.48 * (sin_val if sin_val > 0 else -0.2) + noise_a()
            gx = 45.0 * sin_val + noise_g()
            gy = 35.0 * cos_val + noise_g()
            gz = 18.0 * sin_val + noise_g()

        elif self.current_activity == "Sitting":
            # Body upright with slight incline, resting
            ax = 0.12 + noise_a() * 0.3
            ay = 0.38 + noise_a() * 0.3
            az = 0.88 + noise_a() * 0.3
            gx = noise_g() * 0.2
            gy = noise_g() * 0.2
            gz = noise_g() * 0.2

        elif self.current_activity == "Standing":
            # Stationary vertical posture, subtle postural sway
            ax = 0.05 + 0.03 * math.sin(self.step_phase * 0.2) + noise_a() * 0.4
            ay = 0.04 + 0.02 * math.cos(self.step_phase * 0.2) + noise_a() * 0.4
            az = 0.99 + noise_a() * 0.4
            gx = noise_g() * 0.3
            gy = noise_g() * 0.3
            gz = noise_g() * 0.3

        elif self.current_activity == "Lying":
            # Reclined / resting state (gravity mainly along X/Y axis)
            ax = 0.94 + noise_a() * 0.15
            ay = 0.08 + noise_a() * 0.15
            az = 0.12 + noise_a() * 0.15
            gx = noise_g() * 0.1
            gy = noise_g() * 0.1
            gz = noise_g() * 0.1

        else:
            ax, ay, az = 0.0, 0.0, 1.0
            gx, gy, gz = 0.0, 0.0, 0.0

        return IMUSample(
            ax=round(ax, 3), ay=round(ay, 3), az=round(az, 3),
            gx=round(gx, 2), gy=round(gy, 2), gz=round(gz, 2),
            timestamp=now
        )

    def generate_batch(self, count: int = 10) -> List[IMUSample]:
        return [self.generate_sample() for _ in range(count)]
