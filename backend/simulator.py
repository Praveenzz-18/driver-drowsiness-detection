import random
import time
import math
from typing import List, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────────────────────
#  Road Segment — encodes a curved section of the track
# ─────────────────────────────────────────────────────────────────────────────
class RoadSegment:
    """One slice of the infinite road.  curve > 0 → bends right, < 0 → left."""

    SEGMENT_LEN = 200  # world units per segment

    def __init__(self, curve: float = 0.0, gradient: float = 0.0) -> None:
        self.curve: float = curve        # lateral curvature for this segment
        self.gradient: float = gradient  # hill up/down (not rendered, kept for extension)


# ─────────────────────────────────────────────────────────────────────────────
#  Traffic Car — world-space object driving ahead of the player
# ─────────────────────────────────────────────────────────────────────────────
class TrafficCar:
    LANE_X = {0: -1.0, 1: 0.0, 2: 1.0}   # normalised x per lane (-1 left … +1 right)

    def __init__(self) -> None:
        self.lane: int = random.randint(0, 2)
        self.z: float = random.uniform(400, 900)   # world Z ahead of player
        self.speed: float = random.uniform(15, 40)  # km/h slower than player
        self.color: Tuple = random.choice([
            (200, 50, 50), (50, 50, 200), (240, 180, 30),
            (50, 200, 100), (200, 120, 50), (180, 50, 200),
        ])
        self.width: float = 0.35   # normalised width on road

    def update(self, player_speed: float) -> None:
        # Approach rate = player speed − traffic car speed
        approach = max(0.0, player_speed - self.speed)
        self.z -= approach * 0.10

    def respawn(self) -> None:
        self.lane = random.randint(0, 2)
        self.z = random.uniform(600, 1000)
        self.speed = random.uniform(15, 40)
        self.color = random.choice([
            (200, 50, 50), (50, 50, 200), (240, 180, 30),
            (50, 200, 100), (200, 120, 50), (180, 50, 200),
        ])


# ─────────────────────────────────────────────────────────────────────────────
#  Roadside object (pole / tree)
# ─────────────────────────────────────────────────────────────────────────────
class RoadsideObject:
    def __init__(self, side: int, z: float) -> None:
        self.side = side   # -1 = left side, +1 = right side
        self.z: float = z
        self.obj_type: str = random.choice(['pole', 'tree', 'tree'])

    def update(self, player_speed: float) -> None:
        self.z -= player_speed * 0.12

    def respawn(self) -> None:
        self.z = random.uniform(700, 1000)


# ─────────────────────────────────────────────────────────────────────────────
#  Track generator — generates an infinite road as a list of segments
# ─────────────────────────────────────────────────────────────────────────────
ROAD_SEGMENTS: List[RoadSegment] = []

def _build_track() -> None:
    """Build a looping track with alternating straights and curves."""
    ROAD_SEGMENTS.clear()
    patterns = [
        (20, 0.0),   (8, 0.6),   (15, 0.0), (10, -0.5),
        (20, 0.0),   (6, 0.8),   (12, 0.0), (8, -0.7),
        (18, 0.0),   (10, 0.4),  (10, 0.0), (7, -0.6),
    ]
    for count, curve in patterns:
        for _ in range(count):
            ROAD_SEGMENTS.append(RoadSegment(curve=curve))

_build_track()
TRACK_LEN = len(ROAD_SEGMENTS)


# ─────────────────────────────────────────────────────────────────────────────
#  Main Simulator
# ─────────────────────────────────────────────────────────────────────────────
class DrivingSimulator:
    """
    DR.Driving-style lane-based simulator.

    The player drives a 3-lane road. Steering moves between lanes smoothly.
    The road curves are baked into track segments. Collision and off-road
    detection are handled here; rendering is handled by the dashboard.
    """

    NUM_LANES = 3
    LANE_WIDTH = 1.0          # normalised half-road width per lane
    ROAD_HALF_W = 1.5         # total normalised half-road width (3 lanes × 0.5)

    def __init__(self) -> None:
        self.speed: float = 0.0          # km/h
        self.rpm: float = 1000.0
        self.player_x: float = 0.0       # normalised lateral position (-1.5 … +1.5)
        self.steering_angle: float = 0.0  # visual only (degrees)
        self.camera_z: float = 0.0        # world-space Z camera position (advances with speed)
        self.curve_offset: float = 0.0    # accumulated curve for rendering

        self.safety_mode_active: bool = False
        self.crashed: bool = False
        self.crash_msg: str = ""

        # Traffic
        self.traffic: List[TrafficCar] = [TrafficCar() for _ in range(4)]
        # Roadside decoration
        self.roadside: List[RoadsideObject] = []
        for z in range(50, 1001, 80):
            self.roadside.append(RoadsideObject(-1, float(z)))
            self.roadside.append(RoadsideObject(+1, float(z)))

    # ── Controls ──────────────────────────────────────────────────────────────

    def trigger_safety_mode(self) -> None:
        self.safety_mode_active = True

    def reset_safety_mode(self) -> None:
        self.safety_mode_active = False

    # ── Main update (called every UI frame) ───────────────────────────────────

    def update(self, accelerate: bool, brake: bool, steer_dir: int) -> None:
        if self.crashed:
            return

        # 1. Steering
        steer_rate = 0.04 + self.speed / 2500.0   # responsive at all speeds
        if steer_dir == -1:
            self.player_x = max(-self.ROAD_HALF_W, self.player_x - steer_rate * 2.5)
            self.steering_angle = max(-45.0, self.steering_angle - 5.0)
        elif steer_dir == 1:
            self.player_x = min(self.ROAD_HALF_W, self.player_x + steer_rate * 2.5)
            self.steering_angle = min(45.0, self.steering_angle + 5.0)
        else:
            # Return steering wheel to centre
            self.steering_angle *= 0.85
            if abs(self.steering_angle) < 0.5:
                self.steering_angle = 0.0

        # 2. Speed / RPM
        if self.safety_mode_active:
            self.speed = max(0.0, self.speed - 6.0)
            self.rpm   = max(1000.0, self.rpm - 200.0)
        elif brake:
            self.speed = max(0.0, self.speed - 4.0)
            self.rpm   = max(1000.0, self.rpm - 130.0)
        elif accelerate:
            self.speed = min(180.0, self.speed + 2.0)
            self.rpm   = 1000.0 + self.speed * 28.0 + random.uniform(-40, 40)
            if 75 < self.speed < 80:   self.rpm -= 1200
            if 130 < self.speed < 135: self.rpm -= 1500
        else:
            self.speed = max(0.0, self.speed - 0.6)
            self.rpm   = max(1000.0, self.rpm - 60.0)

        self.rpm = max(1000.0, min(8000.0, self.rpm))

        # 3. Advance camera along the track
        self.camera_z += self.speed * 0.18

        # 4. Update traffic
        for car in self.traffic:
            car.update(self.speed)
            if car.z < -30:
                car.respawn()

        # 5. Update roadside objects
        for obj in self.roadside:
            obj.update(self.speed)
            if obj.z < 0:
                obj.respawn()

        # 6. Off-road collision
        if abs(self.player_x) > self.ROAD_HALF_W + 0.05:
            self.crashed = True
            self.speed = 0.0
            self.crash_msg = "VEHICLE DRIFTED OFF ROAD"
            return

        # 7. Traffic collision
        for car in self.traffic:
            if car.z < 50 and abs(car.z) < 40:
                lane_x = TrafficCar.LANE_X[car.lane] * self.ROAD_HALF_W
                if abs(lane_x - self.player_x) < 0.55:
                    self.crashed = True
                    self.speed = 0.0
                    self.crash_msg = "COLLISION WITH TRAFFIC VEHICLE"
                    return

    # ── Snapshot for renderer ─────────────────────────────────────────────────

    def get_render_data(self) -> Dict[str, Any]:
        """Return all data needed by the dashboard renderer."""
        return {
            "speed":          self.speed,
            "rpm":            self.rpm,
            "player_x":       self.player_x,
            "steering_angle": self.steering_angle,
            "camera_z":       self.camera_z,
            "safety_mode":    self.safety_mode_active,
            "crashed":        self.crashed,
            "crash_msg":      self.crash_msg,
            # traffic as list of dicts
            "traffic": [
                {"lane": c.lane, "z": c.z, "color": c.color, "width": c.width}
                for c in self.traffic
            ],
            # roadside as list of dicts
            "roadside": [
                {"side": o.side, "z": o.z, "obj_type": o.obj_type}
                for o in self.roadside
            ],
            # current curve from track segment
            "road_curve": _get_curve_at(self.camera_z),
        }


def _get_curve_at(camera_z: float) -> float:
    """Returns the curve value of the segment currently under the camera."""
    seg_index = int(camera_z / RoadSegment.SEGMENT_LEN) % TRACK_LEN
    return ROAD_SEGMENTS[seg_index].curve
