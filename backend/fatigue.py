import time
from typing import Dict, Any

class FatigueTracker:
    """
    State tracking and scoring calculations for fatigue and alertness.
    Provides mathematical formulas to integrate eye closure times, yawning,
    and head pose coordinates into driver scores.
    """
    def __init__(self, consecutive_frames: int = 15, yawn_frames: int = 20) -> None:
        self.consecutive_frames = consecutive_frames
        self.yawn_frames = yawn_frames
        
        # State Accumulators
        self.fatigue_score: float = 0.0
        self.alertness_score: float = 100.0
        self.blink_count: int = 0
        self.yawn_count: int = 0
        
        # Current status
        self.eye_state: str = "OPEN"
        self.is_yawning: bool = False
        self.is_distracted: bool = False
        
        # Frame counters
        self.eye_closed_frames: int = 0
        self.yawn_frames_counter: int = 0
        
        # For blink state machine
        self.eye_closed_prev: bool = False
        
    def update(
        self, 
        face_detected: bool,
        current_ear: float, 
        current_mar: float, 
        ear_threshold: float,
        mar_threshold: float,
        pitch_dev: float,
        yaw_dev: float,
        calibration_complete: bool
    ) -> Dict[str, Any]:
        """
        Updates trackers based on current frame indices and computes
        fatigue and alertness scores.
        """
        # If no face is detected, we slowly increase fatigue or keep current state
        if not face_detected:
            # Let's count this as a distraction/loss of track
            self.eye_closed_frames = 0
            self.yawn_frames_counter = 0
            self.is_distracted = True
            # Slowly increase fatigue since driver is missing
            self.fatigue_score = min(100.0, self.fatigue_score + 0.3)
            self._compute_scores()
            return self.get_state_dict()

        # 1. Blink Detection & Eye Status
        is_closed = current_ear < ear_threshold
        if is_closed:
            self.eye_closed_frames += 1
            self.eye_state = "CLOSED"
        else:
            # Check if it was closed but not long enough for drowsiness (a blink)
            # Normal blink is short (e.g. 1 to 10 frames). Drowsiness starts at consecutive_frames (e.g. 15 frames)
            if self.eye_closed_frames > 1 and self.eye_closed_frames < self.consecutive_frames:
                self.blink_count += 1
            self.eye_closed_frames = 0
            self.eye_state = "OPEN"
            
        # 2. Yawn Detection
        if current_mar > mar_threshold:
            self.yawn_frames_counter += 1
            # Trigger yawn count increment on state transition
            if not self.is_yawning and self.yawn_frames_counter > self.yawn_frames:
                self.is_yawning = True
                self.yawn_count += 1
        else:
            # Exit yawning state with hysteresis
            if current_mar < (mar_threshold - 0.15):
                self.is_yawning = False
            self.yawn_frames_counter = 0

        # 3. Head Pose Distraction Detection
        # Distraction is registered if head pose deviates too far from baseline look-straight parameters
        if calibration_complete:
            self.is_distracted = (abs(yaw_dev) > 0.35) or (abs(pitch_dev) > 0.35)
        else:
            self.is_distracted = False

        # 4. Fatigue Score continuous update
        # Increase fatigue based on states:
        if self.eye_closed_frames >= self.consecutive_frames:
            # Eyes closed for too long (Drowsy)
            self.fatigue_score = min(100.0, self.fatigue_score + 2.5)
        elif self.is_yawning:
            # Currently yawning
            self.fatigue_score = min(100.0, self.fatigue_score + 0.6)
        elif self.is_distracted:
            # Looked away
            self.fatigue_score = min(100.0, self.fatigue_score + 0.8)
        else:
            # Driver is alert and looking straight. Fatigue slowly decays.
            self.fatigue_score = max(0.0, self.fatigue_score - 0.15)
            
        self._compute_scores()
        return self.get_state_dict()

    def _compute_scores(self) -> None:
        """Computes alertness score from fatigue and instantaneous distraction states."""
        # Baseline alertness is inverse of fatigue
        base_alertness = 100.0 - self.fatigue_score
        
        # Add bonus if eyes are open to improve alertness perception
        if self.eye_state == "OPEN":
            base_alertness = min(100.0, base_alertness + 10.0)
        
        # Subtract additional immediate penalties if driver is currently behaving unsafely
        penalties = 0.0
        if self.eye_state == "CLOSED":
            # Direct deduction if eye is shut right now
            penalties += 20.0 + min(30.0, self.eye_closed_frames * 1.5)
        if self.is_yawning:
            penalties += 15.0
        if self.is_distracted:
            penalties += 15.0
            
        self.alertness_score = max(0.0, min(100.0, base_alertness - penalties))

    def reset_counters(self) -> None:
        """Resets stats counters and scores."""
        self.fatigue_score = 0.0
        self.alertness_score = 100.0
        self.blink_count = 0
        self.yawn_count = 0
        self.eye_closed_frames = 0
        self.yawn_frames_counter = 0
        self.is_yawning = False
        self.is_distracted = False
        self.eye_state = "OPEN"

    def get_state_dict(self) -> Dict[str, Any]:
        """Returns the current metrics as a dictionary."""
        return {
            "fatigue_score": round(self.fatigue_score, 1),
            "alertness_score": round(self.alertness_score, 1),
            "blink_count": self.blink_count,
            "yawn_count": self.yawn_count,
            "eye_state": self.eye_state,
            "is_yawning": self.is_yawning,
            "is_distracted": self.is_distracted
        }
