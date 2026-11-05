
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math
from typing import Tuple, List, Optional

class DrowsinessDetector:
    """
    Handles MediaPipe Face Landmarker processing, feature extraction (EAR, MAR),
    head pose estimation, and real-time high-tech HUD visual overlays.
    """
    def __init__(self) -> None:
        # Create FaceLandmarker
        base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1
        )
        self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
        
    def process_frame(self, frame: cv2.Mat) -> vision.FaceLandmarkerResult:
        """Processes BGR frame from OpenCV and returns Face Landmarker results."""
        # Convert BGR frame to RGB for MediaPipe processing
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        return self.face_landmarker.detect(mp_image)

    def get_eye_landmarks(self, h: int, w: int, face_landmarks) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Extracts pixel coordinates for left and right eye outlines.
        Indices are standard MediaPipe FaceMesh landmarks.
        """
        # Indices around the eyes:
        # Left eye outline: 33, 160, 158, 133, 153, 144
        # Right eye outline: 362, 385, 387, 263, 373, 380
        left_eye_indices = [33, 160, 158, 133, 153, 144]
        right_eye_indices = [362, 385, 387, 263, 373, 380]
        
        left_eye = [(int(face_landmarks[idx].x * w), 
                     int(face_landmarks[idx].y * h)) for idx in left_eye_indices]
                     
        right_eye = [(int(face_landmarks[idx].x * w), 
                      int(face_landmarks[idx].y * h)) for idx in right_eye_indices]
                       
        return left_eye, right_eye

    def get_mouth_landmarks(self, h: int, w: int, face_landmarks) -> List[Tuple[int, int]]:
        """Extracts pixel coordinates for the inner mouth landmarks."""
        # Inner mouth indices for mouth aspect ratio calculations
        mouth_indices = [61, 291, 37, 267, 81, 311, 13, 14, 82, 312, 0, 17]
        mouth = [(int(face_landmarks[idx].x * w), 
                  int(face_landmarks[idx].y * h)) for idx in mouth_indices]
        return mouth

    def get_head_pose(self, h: int, w: int, face_landmarks) -> Tuple[float, float, float]:
        """
        Estimates head pitch, yaw, and roll based on landmark spatial distances.
        Returns:
            pitch (float): Up/Down tilt (approx -1.0 to 1.0)
            yaw (float): Left/Right turn (approx -1.0 to 1.0)
            roll (float): Side rotation in radians
        """
        # Key landmarks for estimation:
        # Nose tip (1), Chin (152), Left eye corner (33), Right eye corner (263), Forehead (10)
        nose_tip = face_landmarks[1]
        chin = face_landmarks[152]
        left_eye = face_landmarks[33]
        right_eye = face_landmarks[263]
        forehead = face_landmarks[10]
        
        # 1. Yaw (Left/Right look deviation)
        d_left = abs(nose_tip.x - left_eye.x)
        d_right = abs(nose_tip.x - right_eye.x)
        yaw = (d_left - d_right) / (d_left + d_right + 1e-6)
        
        # 2. Pitch (Up/Down tilt deviation)
        d_up = abs(nose_tip.y - forehead.y)
        d_down = abs(nose_tip.y - chin.y)
        pitch = (d_up - d_down) / (d_up + d_down + 1e-6)
        
        # 3. Roll (Angle between horizontal eye alignment)
        dy = right_eye.y - left_eye.y
        dx = right_eye.x - left_eye.x
        roll = math.atan2(dy, dx)
        
        return pitch, yaw, roll

    @staticmethod
    def calculate_ear(eye_landmarks: List[Tuple[int, int]]) -> float:
        """
        Calculates Eye Aspect Ratio (EAR) based on vertical and horizontal distances.
        EAR = (||P2 - P6|| + ||P3 - P5||) / (2 * ||P1 - P4||)
        """
        if len(eye_landmarks) < 6:
            return 0.0
        # Vertical eye distances
        dist_v1 = math.dist(eye_landmarks[1], eye_landmarks[5])
        dist_v2 = math.dist(eye_landmarks[2], eye_landmarks[4])
        
        # Horizontal eye distance
        dist_h = math.dist(eye_landmarks[0], eye_landmarks[3])
        
        if dist_h == 0:
            return 0.0
            
        return (dist_v1 + dist_v2) / (2.0 * dist_h)

    @staticmethod
    def calculate_mar(mouth_landmarks: List[Tuple[int, int]]) -> float:
        """
        Calculates Mouth Aspect Ratio (MAR) for inner lip area.
        Horizontal indices: 61 (index 0), 291 (index 1)
        Vertical indices: 13 (index 6), 14 (index 7)
        """
        if len(mouth_landmarks) < 8:
            return 0.0
        # Vertical inner lip distance (landmarks 13 & 14)
        dist_v = math.dist(mouth_landmarks[6], mouth_landmarks[7])
        # Horizontal inner corner distance (landmarks 61 & 291)
        dist_h = math.dist(mouth_landmarks[0], mouth_landmarks[1])
        
        if dist_h == 0:
            return 0.0
            
        return dist_v / dist_h

    def draw_hud_overlay(
        self, 
        frame: cv2.Mat, 
        face_landmarks, 
        is_eyes_open: bool, 
        is_yawning: bool,
        pitch_dev: float,
        yaw_dev: float,
        roll: float
    ) -> cv2.Mat:
        """
        Draws a premium, high-tech neon HUD overlay representing
        face landmarks, contours, gaze vectors, and status colors on the frame.
        """
        h, w, _ = frame.shape
        overlay = frame.copy()
        
        # Colors: Neon Cyan (Cyan/Blue HUD feel), Green for Normal, Red for Alerts
        hud_color = (255, 180, 0)  # BGR Cyan (0, 180, 255) -> (255, 180, 0)
        eye_color = (0, 255, 0) if is_eyes_open else (0, 0, 255)
        mouth_color = (0, 255, 0) if not is_yawning else (0, 165, 255)  # Orange for yawning
        
        # Draw a subtle face outline and key features
        # Face contour outline selection of landmarks
        face_contour_indices = [
            10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
            397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
            172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109
        ]
        
        # Draw face mesh contour lines
        points = []
        for idx in face_contour_indices:
            pt = face_landmarks[idx]
            points.append((int(pt.x * w), int(pt.y * h)))
            
        # Closed polygon for face outline
        for i in range(len(points)):
            cv2.line(overlay, points[i], points[(i + 1) % len(points)], hud_color, 1)
            
        # Draw Eye Contours
        left_eye, right_eye = self.get_eye_landmarks(h, w, face_landmarks)
        for i in range(6):
            cv2.line(overlay, left_eye[i], left_eye[(i + 1) % 6], eye_color, 2)
            cv2.line(overlay, right_eye[i], right_eye[(i + 1) % 6], eye_color, 2)
            cv2.circle(overlay, left_eye[i], 1, eye_color, -1)
            cv2.circle(overlay, right_eye[i], 1, eye_color, -1)
            
        # Draw Mouth Contour (inner lip)
        mouth = self.get_mouth_landmarks(h, w, face_landmarks)
        if len(mouth) >= 8:
            for i in range(len(mouth)):
                cv2.line(overlay, mouth[i], mouth[(i + 1) % len(mouth)], mouth_color, 1)
                cv2.circle(overlay, mouth[i], 2, mouth_color, -1)
                
        # Draw Gaze / Head Pose 3D Vector from nose tip
        nose_pt = face_landmarks[1]
        nose_x, nose_y = int(nose_pt.x * w), int(nose_pt.y * h)
        
        # Calculate projection based on head tilt
        gaze_x = int(nose_x + yaw_dev * 150)
        gaze_y = int(nose_y + pitch_dev * 150)
        
        # Gaze line and destination target crosshair
        cv2.line(overlay, (nose_x, nose_y), (gaze_x, gaze_y), (255, 0, 120), 2)
        cv2.circle(overlay, (gaze_x, gaze_y), 8, (255, 0, 120), 1)
        cv2.drawMarker(overlay, (gaze_x, gaze_y), (255, 0, 120), cv2.MARKER_CROSS, 10, 1)
        
        # Subtle blend with original frame for opacity
        alpha = 0.85
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)
        
        # Add head roll info indicator
        roll_deg = int(math.degrees(roll))
        cv2.putText(frame, f"ROLL: {roll_deg:+d}*", (15, h - 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_color, 1, cv2.LINE_AA)
        
        return frame

