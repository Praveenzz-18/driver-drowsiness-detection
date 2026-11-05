import sys
sys.path.append('.')
from backend.fatigue import FatigueTracker

def simulate():
    ft = FatigueTracker()
    print('Initial state:', ft.get_state_dict())
    # Simulate 5 frames with open eyes, EAR high, MAR low
    for i in range(5):
        state = ft.update(
            face_detected=True,
            current_ear=0.35,  # above threshold
            current_mar=0.2,   # below threshold
            ear_threshold=0.25,
            mar_threshold=0.5,
            pitch_dev=0.0,
            yaw_dev=0.0,
            calibration_complete=True,
        )
        print(f'Frame {i+1} state:', state)
    # Simulate a blink (eye closure short)
    ft.update(True, 0.2, 0.2, 0.25, 0.5, 0.0, 0.0, True)
    ft.update(True, 0.35, 0.2, 0.25, 0.5, 0.0, 0.0, True)
    print('After blink:', ft.get_state_dict())
    # Simulate drowsy eyes (long closure)
    for i in range(20):
        ft.update(True, 0.1, 0.2, 0.25, 0.5, 0.0, 0.0, True)
    print('After prolonged closure:', ft.get_state_dict())

if __name__ == "__main__":
    simulate()
