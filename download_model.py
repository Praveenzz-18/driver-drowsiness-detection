
import urllib.request
import os

model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
model_filename = "face_landmarker.task"

if not os.path.exists(model_filename):
    print(f"Downloading {model_filename} from {model_url}...")
    try:
        urllib.request.urlretrieve(model_url, model_filename)
        print(f"Successfully downloaded {model_filename}!")
    except Exception as e:
        print(f"Error downloading model: {e}")
        print("Trying mirror...")
        mirror_url = "https://github.com/sanderdesnaijer/mediapipe-model-mirrors/releases/download/v1/face_landmarker.task"
        try:
            urllib.request.urlretrieve(mirror_url, model_filename)
            print(f"Successfully downloaded {model_filename} from mirror!")
        except Exception as e2:
            print(f"Error downloading from mirror: {e2}")
            print("Please download the model manually.")
else:
    print(f"{model_filename} already exists!")
