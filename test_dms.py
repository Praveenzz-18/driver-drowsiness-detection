import sys
import os
import unittest
import numpy as np

# Adjust path to resolve packages correctly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.detector import DrowsinessDetector
from backend.fatigue import FatigueTracker
from backend.alerts import AlertsManager

class TestDMSPipeline(unittest.TestCase):
    """Unit testing suite for Driver Monitoring System core backend pipelines."""
    
    def setUp(self) -> None:
        self.detector = DrowsinessDetector()
        self.tracker = FatigueTracker(consecutive_frames=10, yawn_frames=15)
        self.alerts = AlertsManager()

    def test_detector_initialization(self) -> None:
        """Verifies MediaPipe Face Mesh model builds successfully."""
        self.assertIsNotNone(self.detector.face_landmarker)

    def test_ear_mar_math(self) -> None:
        """Validates EAR and MAR calculations with dummy coordinate points."""
        # Eye landmarks coordinates representing open eye: shape of aspect ratio ~0.3
        # Outline: 6 coordinates [(x, y)]
        eye_open = [(10, 20), (15, 15), (25, 15), (30, 20), (25, 25), (15, 25)]
        ear_open = self.detector.calculate_ear(eye_open)
        self.assertGreater(ear_open, 0.20)
        
        # Closed eye: vertical distance gets close to 0
        eye_closed = [(10, 20), (15, 20), (25, 20), (30, 20), (25, 20), (15, 20)]
        ear_closed = self.detector.calculate_ear(eye_closed)
        self.assertEqual(ear_closed, 0.0)

        # Mouth landmarks coordinates representing yawning
        mouth_yawn = [(50, 100), (90, 100), (60, 95), (80, 95), (65, 98), (75, 98), (70, 70), (70, 130)]
        mar_yawn = self.detector.calculate_mar(mouth_yawn)
        self.assertGreater(mar_yawn, 0.60)

    def test_fatigue_score_accumulation(self) -> None:
        """Checks fatigue levels and alertness score degradation loops."""
        # 1. Start clean
        state = self.tracker.get_state_dict()
        self.assertEqual(state["fatigue_score"], 0.0)
        self.assertEqual(state["alertness_score"], 100.0)
        
        # 2. Simulate 15 consecutive frames of eye closure
        # Threshold: 0.22, let's feed current_ear = 0.10
        for _ in range(15):
            state = self.tracker.update(
                face_detected=True,
                current_ear=0.10,
                current_mar=0.15,
                ear_threshold=0.22,
                mar_threshold=0.60,
                pitch_dev=0.0,
                yaw_dev=0.0,
                calibration_complete=True
            )
            
        # Fatigue score should build up and Alertness drops
        self.assertGreater(state["fatigue_score"], 0.0)
        self.assertLess(state["alertness_score"], 100.0)
        
    def test_alerts_manager_status(self) -> None:
        """Verifies driver warning severity classification levels."""
        # Safe
        status = self.alerts.update_status(25.0)
        self.assertEqual(status, "SAFE")
        
        # Warning
        status = self.alerts.update_status(50.0)
        self.assertEqual(status, "WARNING")
        
        # Drowsy
        status = self.alerts.update_status(85.0)
        self.assertEqual(status, "DROWSY")
        self.assertTrue(self.alerts.alarm_playing or self.alerts.alarm_sound is None)

if __name__ == "__main__":
    unittest.main()
