import cv2
import threading
import queue
import time
from typing import Dict, Any, Tuple, Optional
from backend.detector import DrowsinessDetector
from backend.fatigue import FatigueTracker
from backend.alerts import AlertsManager
from backend.simulator import DrivingSimulator

class DMSAPI:
    """
    Main Thread-safe API interface connecting Backend pipelines and Frontend dashboard.
    Runs double-threaded background loops:
      - Thread 1: Camera capture
      - Thread 2: Face mesh processing and score updates
    """
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.detector = DrowsinessDetector()
        self.fatigue_tracker = FatigueTracker()
        self.alerts_manager = AlertsManager()
        self.simulator = DrivingSimulator()
        
        # Thread Controls
        self.running: bool = False
        self.cap_thread: Optional[threading.Thread] = None
        self.proc_thread: Optional[threading.Thread] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=1)
        
        # Shared Telemetry State (Lock Protected)
        self.telemetry_lock = threading.Lock()
        self.latest_frame: Optional[cv2.Mat] = None
        self.latest_telemetry: Dict[str, Any] = {}
        
        # Calibration Parameters
        self.calibrated: bool = False
        self.calibration_frames: list = []
        self.calibration_progress: int = 0
        self.baseline_ear: float = 0.28
        self.baseline_pitch: float = -0.15
        self.baseline_yaw: float = 0.0
        
        # Diagnostic & FPS parameters
        self.processing_fps: float = 0.0
        self.frame_count: int = 0
        self.start_time: float = time.time()
        
        # Internal placeholders
        self.cap: Optional[cv2.VideoCapture] = None
        
    def start(self) -> None:
        """Starts video capture and launches double threads."""
        if self.running:
            return
            
        print("API: Opening camera...")
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("API ERROR: Webcam could not be initialized.")
            
        self.running = True
        self.alerts_manager.clear_history()
        
        # Thread 1: Camera Capture
        self.cap_thread = threading.Thread(target=self._capture_loop, name="DMS_CaptureThread", daemon=True)
        # Thread 2: Face Mesh & State Processing
        self.proc_thread = threading.Thread(target=self._processing_loop, name="DMS_ProcessingThread", daemon=True)
        
        self.cap_thread.start()
        self.proc_thread.start()
        print("API: Background threads started successfully.")

    def stop(self) -> None:
        """Stops background threads and releases resources."""
        self.running = False
        
        if self.cap_thread:
            self.cap_thread.join(timeout=1.0)
        if self.proc_thread:
            self.proc_thread.join(timeout=1.0)
            
        if self.cap:
            self.cap.release()
            self.cap = None
            
        self.alerts_manager.stop_alarm()
        print("API: Shutdown complete.")

    def _capture_loop(self) -> None:
        """Thread 1: Camera Capture. Feeds frame queue, dropping stale frames."""
        while self.running:
            if self.cap is None:
                time.sleep(0.01)
                continue
                
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
                
            # If queue is full, pop oldest frame to maintain 0 latency
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                    
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass
                
            # Slight sleep to control thread load matching camera rate (e.g. max 45 FPS)
            time.sleep(0.015)

    def _processing_loop(self) -> None:
        """Thread 2: Face Processing. Computes parameters, fatigue scores, and HUD drawings."""
        last_time = time.time()
        
        while self.running:
            try:
                # Get frame from queue
                frame = self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            h, w, _ = frame.shape
            results = self.detector.process_frame(frame)
            
            face_detected = False
            current_ear = 0.28
            current_mar = 0.0
            pitch, yaw, roll = 0.0, 0.0, 0.0
            pitch_dev = 0.0
            yaw_dev = 0.0
            
            if results.face_landmarks:
                face_detected = True
                face_landmarks = results.face_landmarks[0]
                
                # Extract landmarks
                l_eye, r_eye = self.detector.get_eye_landmarks(h, w, face_landmarks)
                current_ear = (self.detector.calculate_ear(l_eye) + self.detector.calculate_ear(r_eye)) / 2.0
                
                mouth = self.detector.get_mouth_landmarks(h, w, face_landmarks)
                current_mar = self.detector.calculate_mar(mouth)
                
                pitch, yaw, roll = self.detector.get_head_pose(h, w, face_landmarks)
                
                # Calibration sequence: collect first 30 frames with valid face detection
                if not self.calibrated:
                    self.calibration_frames.append((current_ear, pitch, yaw))
                    self.calibration_progress = int((len(self.calibration_frames) / 30.0) * 100)
                    
                    if len(self.calibration_frames) >= 30:
                        ears = [x[0] for x in self.calibration_frames]
                        pitches = [x[1] for x in self.calibration_frames]
                        yaws = [x[2] for x in self.calibration_frames]
                        
                        self.baseline_ear = sum(ears) / len(ears)
                        self.baseline_pitch = sum(pitches) / len(pitches)
                        self.baseline_yaw = sum(yaws) / len(yaws)
                        self.calibrated = True
                        self.alerts_manager.log_alert("Calibration successful", "SAFE")
                        print(f"API: Calibration complete. Baseline EAR={self.baseline_ear:.3f}")
                
                # Compute head deviation relative to baseline
                if self.calibrated:
                    pitch_dev = pitch - self.baseline_pitch
                    yaw_dev = yaw - self.baseline_yaw
                    
                # Render HUD visual overlay on the frame
                is_eyes_open = current_ear >= (self.baseline_ear * 0.82 if self.calibrated else 0.22)
                
                # Check for discrete warning events for the logger
                yawning_prev = self.fatigue_tracker.is_yawning
                eyes_open_prev = (self.fatigue_tracker.eye_state == "OPEN")
                
                # Update tracker states
                tracker_state = self.fatigue_tracker.update(
                    face_detected=True,
                    current_ear=current_ear,
                    current_mar=current_mar,
                    ear_threshold=max(0.20, min(0.28, self.baseline_ear * 0.82 if self.calibrated else 0.22)),
                    mar_threshold=0.60,
                    pitch_dev=pitch_dev,
                    yaw_dev=yaw_dev,
                    calibration_complete=self.calibrated
                )
                
                # Log alerts on threshold transitions
                if self.fatigue_tracker.is_yawning and not yawning_prev:
                    self.alerts_manager.log_alert("Yawn detected", "WARNING")
                if self.fatigue_tracker.eye_state == "CLOSED" and eyes_open_prev:
                    self.alerts_manager.log_alert("Eyes closed", "WARNING")
                    
                frame = self.detector.draw_hud_overlay(
                    frame=frame,
                    face_landmarks=face_landmarks,
                    is_eyes_open=is_eyes_open,
                    is_yawning=self.fatigue_tracker.is_yawning,
                    pitch_dev=pitch_dev,
                    yaw_dev=yaw_dev,
                    roll=roll
                )
            else:
                # No face detected
                tracker_state = self.fatigue_tracker.update(
                    face_detected=False,
                    current_ear=0.0,
                    current_mar=0.0,
                    ear_threshold=0.22,
                    mar_threshold=0.60,
                    pitch_dev=0.0,
                    yaw_dev=0.0,
                    calibration_complete=self.calibrated
                )
                
            # Update warning alert manager status
            driver_status = self.alerts_manager.update_status(tracker_state["fatigue_score"])
            
            # Synchronize simulator ADAS emergency braking with driver fatigue status
            if driver_status == "DROWSY":
                self.simulator.trigger_safety_mode()
            else:
                self.simulator.reset_safety_mode()
            
            # FPS Calculation (EMA smooth)
            now = time.time()
            dt = now - last_time
            last_time = now
            if dt > 0:
                current_fps = 1.0 / dt
                self.processing_fps = self.processing_fps + (current_fps - self.processing_fps) * 0.1
                
            # Expose data thread-safely
            with self.telemetry_lock:
                self.latest_frame = frame
                self.latest_telemetry = {
                    "face_detected": face_detected,
                    "ear": round(current_ear, 3),
                    "mar": round(current_mar, 3),
                    "pitch": round(pitch_dev, 2),
                    "yaw": round(yaw_dev, 2),
                    "roll": round(roll, 2),
                    "fatigue_score": tracker_state["fatigue_score"],
                    "alertness_score": tracker_state["alertness_score"],
                    "blink_count": tracker_state["blink_count"],
                    "yawn_count": tracker_state["yawn_count"],
                    "eye_state": tracker_state["eye_state"],
                    "is_yawning": tracker_state["is_yawning"],
                    "is_distracted": tracker_state["is_distracted"],
                    "driver_status": driver_status,
                    "fps": round(self.processing_fps, 1),
                    "calibrated": self.calibrated,
                    "calibration_progress": self.calibration_progress,
                    "history": self.alerts_manager.get_history(),
                    **self.simulator.get_render_data()
                }

    def trigger_calibration(self) -> None:
        """Triggers a manual baseline calibration."""
        self.calibrated = False
        self.calibration_frames.clear()
        self.calibration_progress = 0
        self.alerts_manager.log_alert("Calibration restarted", "WARNING")
        print("API: Calibration process restarted.")

    def reset_metrics(self) -> None:
        """Resets fatigue tracker scores and stats counters."""
        self.fatigue_tracker.reset_counters()
        self.alerts_manager.clear_history()
        print("API: Metrics and scores reset.")

    def update_simulator_controls(self, accelerate: bool, brake: bool, steer_dir: int) -> None:
        """Thread-safe update of simulator controls from main thread."""
        self.simulator.update(accelerate, brake, steer_dir)

    def reset_simulator(self) -> None:
        """Resets driving simulator and associated fatigue trackers."""
        self.simulator = DrivingSimulator()
        self.reset_metrics()
        print("API: Driving simulator restarted.")

    def get_latest_data(self) -> Tuple[Optional[cv2.Mat], Dict[str, Any]]:
        """Thread-safe retrieval of processed frame and latest telemetry."""
        with self.telemetry_lock:
            return self.latest_frame, self.latest_telemetry.copy()
