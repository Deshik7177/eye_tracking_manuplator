import cv2
import mediapipe as mp
import serial
from collections import deque

# --- CONFIGURATION ---
# Ensure 'COM7' matches your actual port
ser = None
try:
    ser = serial.Serial('COM7', 115200, timeout=1)
    print("Serial connection established on COM7")
except Exception as e:
    print(f"ERROR: Serial Port not found. Check your connection. ({e})")
    print("Make sure ESP32 is connected and COM7 is correct.")

BUFFER_SIZE = 15  # Higher = smoother, but more lag
x_buffer = deque(maxlen=BUFFER_SIZE)           # Base rotation (center eye horizontal)
shoulder_y_buffer = deque(maxlen=BUFFER_SIZE)  # Shoulder up/down (left eye vertical)
elbow_y_buffer = deque(maxlen=BUFFER_SIZE)     # Elbow extend/retract (right eye vertical)

# --- JITTER PREVENTION ---
DEADZONE = 3  # If eye moves less than 3 units, ignore it
last_sent_x = 50      # Start at center (50) - Base
last_sent_shoulder_y = 50  # Start at center (50) - Shoulder
last_sent_elbow_y = 50     # Start at center (50) - Elbow

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
cap = cv2.VideoCapture(0)

gripper_state = 0
blink_frames = 0

# Send home position on startup
if ser is not None:
    ser.write(f"90,30,0,0\n".encode())
    print("Moving arm to HOME position...")
    import time
    time.sleep(1)

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    if results.multi_face_landmarks:
        mesh = results.multi_face_landmarks[0].landmark
        
        # 1. Coordinates for Tracking (Using MediaPipe face mesh landmarks)
        # Base rotation: Center pupil horizontal movement
        p_x, p_y = mesh[468].x, mesh[468].y
        l_x, r_x = mesh[33].x, mesh[133].x  # Left and right eye corners
        
        # Shoulder (Y): LEFT eye vertical tracking
        # Using left eye landmarks: 33 (inner), 133 (outer), 159 (top), 145 (bottom)
        left_p_y = mesh[468].y  # Center pupil Y position
        left_t_y = mesh[159].y  # Left eye top
        left_b_y = mesh[145].y  # Left eye bottom
        
        # Elbow (Y): RIGHT eye vertical tracking
        # Using right eye landmarks: 362 (inner), 263 (outer), 386 (top), 374 (bottom)
        right_p_y = mesh[468].y  # Center pupil Y position (same as left, MediaPipe uses center)
        right_t_y = mesh[386].y  # Right eye top
        right_b_y = mesh[374].y  # Right eye bottom

        # 2. Calculate Relative Gaze (0 to 100)
        # Base: Horizontal (left/right) from center pupil
        rel_x = int(((p_x - l_x) / (r_x - l_x)) * 100)
        
        # Shoulder: Vertical position within LEFT eye (top=100, bottom=0)
        if left_b_y - left_t_y > 0:
            rel_shoulder_y = int(((left_b_y - left_p_y) / (left_b_y - left_t_y)) * 100)
        else:
            rel_shoulder_y = 50
        
        # Elbow: Vertical position within RIGHT eye (top=100, bottom=0)
        if right_b_y - right_t_y > 0:
            rel_elbow_y = int(((right_b_y - right_p_y) / (right_b_y - right_t_y)) * 100)
        else:
            rel_elbow_y = 50

        # 3. Apply Moving Average Filter
        x_buffer.append(rel_x)
        shoulder_y_buffer.append(rel_shoulder_y)
        elbow_y_buffer.append(rel_elbow_y)
        
        smooth_x = sum(x_buffer) / len(x_buffer)
        smooth_shoulder_y = sum(shoulder_y_buffer) / len(shoulder_y_buffer)
        smooth_elbow_y = sum(elbow_y_buffer) / len(elbow_y_buffer)
        
        # CLAMP to valid 0-100 range to prevent out-of-range servo angles
        smooth_x = max(0, min(100, smooth_x))
        smooth_shoulder_y = max(0, min(100, smooth_shoulder_y))
        smooth_elbow_y = max(0, min(100, smooth_elbow_y))

        # 4. Deadzone Check (Only send if movement is significant)
        if (abs(smooth_x - last_sent_x) > DEADZONE or 
            abs(smooth_shoulder_y - last_sent_shoulder_y) > DEADZONE or 
            abs(smooth_elbow_y - last_sent_elbow_y) > DEADZONE):
            
            last_sent_x = int(smooth_x)
            last_sent_shoulder_y = int(smooth_shoulder_y)
            last_sent_elbow_y = int(smooth_elbow_y)

            # 5. Blink Detection using LEFT eye
            ear = left_b_y - left_t_y  # Eye Aspect Ratio
            if ear < 0.010:  # Eye closed (more sensitive threshold)
                blink_frames += 1
            else:
                if 2 <= blink_frames <= 20:  # Expanded range for lighter blinks
                    gripper_state = 90 if gripper_state == 0 else 0
                    print(f"BLINK DETECTED! Gripper: {gripper_state}° ({'CLOSE' if gripper_state == 90 else 'OPEN'})")
                blink_frames = 0

            # Independent 4-DOF Control:
            # - Base: LEFT/RIGHT eye (horizontal center)
            # - Shoulder: UP/DOWN left eye (vertical within left eye)  
            # - Elbow: UP/DOWN right eye (vertical within right eye)
            # - Gripper: BLINK
            
            # Send Data to Arduino in format: Base,Shoulder,Elbow,Gripper
            if ser is not None:
                # Map to calibrated servo angles
                # Base (X): 0-180° (left to right rotation)
                base_angle = int((last_sent_x / 100) * 180)
                
                # Shoulder (LEFT eye Y): 0-90° (full range)
                # Looking down = 0°, looking up = 90°
                shoulder_angle = 90 - int((last_sent_shoulder_y / 100) * 90)
                shoulder_angle = max(0, min(90, shoulder_angle))
                
                # Elbow (RIGHT eye Y): 0-90° (inverted to match shoulder logic)
                # Looking down = 0°, looking up = 90°
                elbow_angle = 90 - int((last_sent_elbow_y / 100) * 90)
                elbow_angle = max(0, min(90, elbow_angle))
                
                # Gripper: 0 or 90
                gripper = gripper_state
                
                # Debug: Show values
                print(f"Base={base_angle:3d}° (X:{last_sent_x:3d}) | Shoulder={shoulder_angle:3d}° (LY:{last_sent_shoulder_y:3d}) | Elbow={elbow_angle:3d}° (RY:{last_sent_elbow_y:3d}) | Gripper={gripper:3d}°")
                
                ser.write(f"{base_angle},{shoulder_angle},{elbow_angle},{gripper}\n".encode())
            else:
                print("WARNING: Serial port not connected. Skipping command.")

        # --- VISUAL FEEDBACK (UI) ---
        # Draw Left Eye Box
        cv2.rectangle(frame, (int(l_x*w), int(left_t_y*h)), (int(r_x*w), int(left_b_y*h)), (0, 255, 0), 1)
        # Draw Pupil Crosshair
        px, py = int(p_x * w), int(p_y * h)
        cv2.line(frame, (px-10, py), (px+10, py), (0, 0, 255), 1)
        cv2.line(frame, (px, py-10), (px, py+10), (0, 0, 255), 1)
        
        cv2.putText(frame, f"Base: {last_sent_x} | Shoulder: {last_sent_shoulder_y} | Elbow: {last_sent_elbow_y} | Grip: {gripper_state}", (30, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow('Eye Manipulator v2', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

# Close serial connection if it was opened
if ser is not None:
    ser.close()
    print("Serial connection closed.")