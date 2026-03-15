import cv2
import mediapipe as mp
import serial
import time

ser = serial.Serial('COM7', 115200, timeout=1)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
cap = cv2.VideoCapture(0)

# Smoothing & State variables
smooth_x, smooth_y = 50, 50
alpha = 0.15  # Lower = Smoother (Less jitter)
gripper_state = 0
blink_frames = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    if results.multi_face_landmarks:
        mesh = results.multi_face_landmarks[0].landmark
        
        # --- CALCULATE RELATIVE PUPIL X (Horizontal) ---
        # 33: Outer Corner, 133: Inner Corner, 468: Pupil Center
        p = mesh[468].x
        l = mesh[33].x
        r = mesh[133].x
        # Normalizing pupil position between the corners (0.0 to 1.0)
        relative_x = (p - l) / (r - l)
        
        # --- CALCULATE RELATIVE PUPIL Y (Vertical) ---
        # 159: Upper Lid, 145: Lower Lid
        p_y = mesh[468].y
        t = mesh[159].y
        b = mesh[145].y
        relative_y = (p_y - t) / (b - t)

        # --- BLINK DETECTION (EAR) ---
        ear = b - t
        if ear < 0.012: # Tune this if it blinks too easily
            blink_frames += 1
        else:
            if 2 <= blink_frames <= 10: # Quick blink toggle
                gripper_state = 1 if gripper_state == 0 else 0
            blink_frames = 0

        # --- CONVERT TO 0-100 AND SMOOTH ---
        target_x = int(relative_x * 100)
        target_y = int(relative_y * 100)
        
        # Deadzone: Only update if change is > 3% to kill micro-jitter
        if abs(target_x - smooth_x) > 3:
            smooth_x = (alpha * target_x) + ((1 - alpha) * smooth_x)
        if abs(target_y - smooth_y) > 3:
            smooth_y = (alpha * target_y) + ((1 - alpha) * smooth_y)
        
        # Send to Arduino
        ser.write(f"{int(smooth_x)},{int(smooth_y)},{gripper_state}\n".encode())

    cv2.imshow('Pure Pupil Tracking', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()