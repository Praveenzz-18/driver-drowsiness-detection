import mediapipe as mp
print(dir(mp))
print("\n---")
try:
    print("mp.solutions:", dir(mp.solutions))
except Exception as e:
    print("Error mp.solutions:", e)
try:
    import mediapipe as mp
    from mediapipe.tasks import vision
    print("Successfully imported mediapipe.tasks.vision")
except Exception as e:
    print("Error importing mediapipe.tasks.vision:", e)
