import cv2
import mediapipe as mp
import serial
from collections import deque

# --- CONFIGURATION ---
# Ensure 'COM7' matches your actual port
try:
    ser = serial.Serial('COM7', 115200, timeout=1)
except:
    print("Serial Port not found. Check your connection.")

BUFFER_SIZE = 5  # Higher = smoother, but more lag
x_buffer = deque(maxlen=BUFFER_SIZE)
y_buffer = deque(maxlen=BUFFER_SIZE)

# --- JITTER PREVENTION ---
DEADZONE = 3  # If eye moves less than 3 units, ignore it
last_sent_x = 50
last_sent_y = 50

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
cap = cv2.VideoCapture(0)

gripper_state = 0
blink_frames = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    if results.multi_face_landmarks:
        mesh = results.multi_face_landmarks[0].landmark
        
        # 1. Coordinates for Tracking (Relative to Eye)
        p_x, p_y = mesh[468].x, mesh[468].y
        l_x, r_x = mesh[33].x, mesh[133].x
        t_y, b_y = mesh[159].y, mesh[145].y

        # 2. Calculate Relative Gaze (0 to 100)
        rel_x = int(((p_x - l_x) / (r_x - l_x)) * 100)
        rel_y = int(((p_y - t_y) / (b_y - t_y)) * 100)

        # 3. Apply Moving Average Filter
        x_buffer.append(rel_x)
        y_buffer.append(rel_y)
        smooth_x = sum(x_buffer) / len(x_buffer)
        smooth_y = sum(y_buffer) / len(y_buffer)

        # 4. Deadzone Check (Only send if movement is significant)
        if abs(smooth_x - last_sent_x) > DEADZONE or abs(smooth_y - last_sent_y) > DEADZONE:
            last_sent_x = int(smooth_x)
            last_sent_y = int(smooth_y)

            # 5. Blink Detection
            ear = b_y - t_y
            if ear < 0.012:
                blink_frames += 1
            else:
                if 2 <= blink_frames <= 10: 
                    gripper_state = 1 if gripper_state == 0 else 0
                blink_frames = 0

            # Send Data to Arduino
            ser.write(f"{last_sent_x},{last_sent_y},{gripper_state}\n".encode())

        # --- VISUAL FEEDBACK (UI) ---
        # Draw Eye Box
        cv2.rectangle(frame, (int(l_x*w), int(t_y*h)), (int(r_x*w), int(b_y*h)), (0, 255, 0), 1)
        # Draw Pupil Crosshair
        px, py = int(p_x * w), int(p_y * h)
        cv2.line(frame, (px-10, py), (px+10, py), (0, 0, 255), 1)
        cv2.line(frame, (px, py-10), (px, py+10), (0, 0, 255), 1)
        
        cv2.putText(frame, f"Gaze: {last_sent_x},{last_sent_y} | Grip: {gripper_state}", (30, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow('Eye Manipulator v2', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()