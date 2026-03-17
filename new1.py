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

BUFFER_SIZE = 5  # Reduced for faster response with less lag
x_buffer = deque(maxlen=BUFFER_SIZE)           # Base rotation (center eye horizontal)
shoulder_y_buffer = deque(maxlen=BUFFER_SIZE)  # Shoulder up/down (left eye vertical)
elbow_y_buffer = deque(maxlen=BUFFER_SIZE)     # Elbow extend/retract (right eye vertical)

# --- INCREMENTAL MOVEMENT ---
DEADZONE = 8  # Center zone - no movement
STEP_SIZE = 20  # degrees per step
last_sent_x = 50      # Start at center (50) - Base
last_sent_shoulder_y = 50  # Start at center (50) - Shoulder
last_sent_elbow_y = 50     # Start at center (50) - Elbow
last_zone_x = 0  # Track zone: -1=left, 0=center, 1=right
last_zone_shoulder_y = 0  # Track zone: -1=down, 0=center, 1=up
last_zone_elbow_y = 0  # Track zone: -1=down, 0=center, 1=up
virtual_base = 90  # Current servo angle
virtual_shoulder = 45  # Current servo angle
virtual_elbow = 45  # Current servo angle

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
cap = cv2.VideoCapture(0)

gripper_state = 0
blink_frames = 0

# --- PICK & PLACE STATE MACHINE ---
STATE_IDLE = 0
STATE_PICK = 1
STATE_PLACE = 2
current_state = STATE_IDLE
last_sent_command = None  # Track last command to avoid repeats

# Predefined positions
PICK_POS = (30, 0, 90)    # S, E, G - shoulder down, elbow extended, gripper closed
PLACE_POS = (60, 60, 0)   # S, E, G - shoulder mid, elbow mid, gripper open

# Send home position on startup
if ser is not None:
    ser.write(f"90,30,0,0\n".encode())
    print("Moving arm to HOME position...")
    print("Look DOWN to PICK | Look UP to PLACE")
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
        
        # Shoulder: Vertical position within LEFT eye (0=looking down, 100=looking up)
        if left_b_y - left_t_y > 0:
            rel_shoulder_y = int(((left_b_y - left_p_y) / (left_b_y - left_t_y)) * 100)  # bottom-pupil / eye_height
        else:
            rel_shoulder_y = 50
        
        # Elbow: Vertical position within RIGHT eye (0=looking down, 100=looking up)
        if right_b_y - right_t_y > 0:
            rel_elbow_y = int(((right_b_y - right_p_y) / (right_b_y - right_t_y)) * 100)  # bottom-pupil / eye_height
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

        # 4. Threshold-based Zone Detection (UP/CENTER/DOWN for each axis)
        # Determine current zones
        # X-axis (LEFT/RIGHT) thresholds
        LEFT_THRESHOLD = 30    # LEFT triggers when smooth_x < this
        RIGHT_THRESHOLD = 60   # RIGHT triggers when smooth_x > this
        
        # Y-axis (UP/DOWN) thresholds
        UP_THRESHOLD = 30      # DOWN triggers when smooth_y < this (lower = more sensitive)
        DOWN_THRESHOLD = 80    # UP triggers when smooth_y > this (lower = more sensitive)
        
        # X-axis zones (left/center/right)
        zone_x = 0
        if smooth_x < LEFT_THRESHOLD:
            zone_x = -1  # LEFT
        elif smooth_x > RIGHT_THRESHOLD:
            zone_x = 1  # RIGHT
        
        # Shoulder Y-axis zones (UP is high value 70+, DOWN is low value 30-)
        zone_shoulder_y = 0
        if smooth_shoulder_y > DOWN_THRESHOLD:
            zone_shoulder_y = 1  # UP (high value = looking up)
        elif smooth_shoulder_y < UP_THRESHOLD:
            zone_shoulder_y = -1  # DOWN (low value = looking down)
        
        # Elbow Y-axis zones
        zone_elbow_y = 0
        if smooth_elbow_y > DOWN_THRESHOLD:
            zone_elbow_y = 1  # UP
        elif smooth_elbow_y < UP_THRESHOLD:
            zone_elbow_y = -1  # DOWN
        
        # DEBUG OUTPUT
        print(f"Shoulder Y: {int(smooth_shoulder_y):3d} [{['DOWN','CENTER','UP'][zone_shoulder_y+1]}] | Elbow Y: {int(smooth_elbow_y):3d} [{['DOWN','CENTER','UP'][zone_elbow_y+1]}]", end="  ")
        
        # Move only when entering a new zone (zone changed)
        moved = False
        if zone_x != last_zone_x:
            virtual_base += zone_x * STEP_SIZE
            virtual_base = max(0, min(180, virtual_base))
            last_zone_x = zone_x
            moved = True
            print(f"  Base zone: {zone_x} ({['LEFT','CENTER','RIGHT'][zone_x+1]})")
        
        if zone_shoulder_y != last_zone_shoulder_y:
            virtual_shoulder += zone_shoulder_y * STEP_SIZE
            virtual_shoulder = max(0, min(90, virtual_shoulder))
            last_zone_shoulder_y = zone_shoulder_y
            moved = True
            print(f"  Shoulder zone: {zone_shoulder_y} ({['DOWN','CENTER','UP'][zone_shoulder_y+1]})")
        
        if zone_elbow_y != last_zone_elbow_y:
            virtual_elbow += zone_elbow_y * STEP_SIZE
            virtual_elbow = max(0, min(90, virtual_elbow))
            last_zone_elbow_y = zone_elbow_y
            moved = True
            print(f"  Elbow zone: {zone_elbow_y} ({['DOWN','CENTER','UP'][zone_elbow_y+1]})")
        
        # 5. Blink Detection
        ear = left_b_y - left_t_y
        if ear < 0.010:
            blink_frames += 1
        else:
            if 2 <= blink_frames <= 20:
                gripper_state = 90 if gripper_state == 0 else 0
                print(f"BLINK DETECTED! Gripper: {gripper_state}° ({'CLOSE' if gripper_state == 90 else 'OPEN'})")
                moved = True
            blink_frames = 0
        
        # Send command only when something changed
        if moved and ser is not None:
            command = f"{int(virtual_base)},{int(virtual_shoulder)},{int(virtual_elbow)},{gripper_state}"
            if command != last_sent_command:
                print(f"[MOVE] Base={int(virtual_base):3d}° Shoulder={int(virtual_shoulder):3d}° Elbow={int(virtual_elbow):3d}° Gripper={gripper_state:3d}°")
                ser.write(f"{command}\n".encode())
                last_sent_command = command

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