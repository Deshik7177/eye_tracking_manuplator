import cv2
import mediapipe as mp
import serial
import numpy as np

ser = serial.Serial('COM7', 115200)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
cap = cv2.VideoCapture(0)

gripper_state = 0 # 0 = Open, 1 = Closed
blink_frames = 0
smooth_x, smooth_y = 50, 50

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    
    frame = cv2.flip(frame, 1)
    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    if results.multi_face_landmarks:
        mesh = results.multi_face_landmarks[0].landmark
        
        # --- BLINK DETECTION ---
        # Vertical distance between upper and lower eyelid (landmarks 159 and 145)
        up = mesh[159].y
        down = mesh[145].y
        ear = down - up 
        
        if ear < 0.015: # Threshold for a blink
            blink_frames += 1
        else:
            if blink_frames >= 3: # Valid blink duration
                gripper_state = 1 if gripper_state == 0 else 0 # Toggle
            blink_frames = 0

        # --- SMOOTHING ---
        raw_x, raw_y = int(mesh[468].x * 100), int(mesh[468].y * 100)
        smooth_x = (0.2 * raw_x) + (0.8 * smooth_x)
        smooth_y = (0.2 * raw_y) + (0.8 * smooth_y)
        
        # Send format: X,Y,G\n
        ser.write(f"{int(smooth_x)},{int(smooth_y)},{gripper_state}\n".encode())

    cv2.imshow('Blink to Grip', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()