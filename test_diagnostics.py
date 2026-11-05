import cv2
import sys
import math
from backend.detector import DrowsinessDetector

def main():
    print("Initializing detector...")
    detector = DrowsinessDetector()
    
    print("Opening camera (0)...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit(1)
        
    print("\n--- Diagnostic Tool ---")
    print("Press 'q' in the camera window to quit.")
    print("Adjust your position and look straight to see the baseline values.\n")
    
    cv2.namedWindow("Diagnostics")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break
            
        results = detector.process_frame(frame)
        
        current_ear = 0.0
        current_mar = 0.0
        pitch, yaw, roll = 0.0, 0.0, 0.0
        face_detected = False
        
        if results.multi_face_landmarks:
            face_detected = True
            h, w, _ = frame.shape
            for fl in results.multi_face_landmarks:
                l_eye, r_eye = detector.get_eye_landmarks(h, w, fl)
                current_ear = (DrowsinessDetector.calculate_ear(l_eye) + DrowsinessDetector.calculate_ear(r_eye)) / 2.0
                
                mouth = detector.get_mouth_landmarks(h, w, fl)
                current_mar = DrowsinessDetector.calculate_mar(mouth)
                
                pitch, yaw, roll = detector.get_head_pose(h, w, fl)
                
                # Draw landmarks on frame
                for idx in [33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380]:
                    pt = fl.landmark[idx]
                    cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 2, (0, 255, 0), -1)
                for pt_m in mouth:
                    cv2.circle(frame, pt_m, 2, (0, 255, 255), -1)
                    
        # Print status to console (carriage return to keep line clean)
        status = f"Face: {'YES' if face_detected else 'NO'} | EAR: {current_ear:.3f} | MAR: {current_mar:.3f} | Pitch: {pitch:.3f} | Yaw: {yaw:.3f} | Roll: {roll:.3f}"
        print(status, end="\r", flush=True)
        
        # Display the frame
        cv2.putText(frame, f"EAR: {current_ear:.2f} MAR: {current_mar:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Pitch: {pitch:.2f} Yaw: {yaw:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Diagnostics", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("\nDiagnostics finished.")

if __name__ == "__main__":
    main()
