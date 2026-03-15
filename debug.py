import mediapipe as mp

print("MediaPipe version:", mp.__version__)
print("solutions available:", "solutions" in dir(mp))

mp_face_mesh = mp.solutions.face_mesh
print("FaceMesh loaded successfully")