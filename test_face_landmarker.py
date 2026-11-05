
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import cv2

# Create a dummy test image
h, w = 480, 640
img = np.zeros((h, w, 3), dtype=np.uint8)
img[:] = (255, 255, 255)

# Convert to MediaPipe Image
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)

# Create FaceLandmarker
print("Creating FaceLandmarker...")
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),  # We need to download the model!
    running_mode=vision.RunningMode.IMAGE,
    num_faces=1,
    refine_landmarks=True
)

print("Options created!")
try:
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        # Perform face landmark detection
        result = landmarker.detect(mp_image)
        print("Result type:", type(result))
        print("dir(result):", dir(result))
        print("Face landmarks present?", hasattr(result, 'face_landmarks'))
except Exception as e:
    print("Error:", e)
    import traceback
    print(traceback.format_exc())

