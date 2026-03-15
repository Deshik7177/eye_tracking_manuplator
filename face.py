import cv2
import mediapipe as mp
import numpy as np
import serial

# ---------------- SERIAL ----------------

ser = serial.Serial("COM7",115200)

# ---------------- MEDIAPIPE ----------------

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

# ---------------- CAMERA ----------------

cap = cv2.VideoCapture(0)
cap.set(3,320)
cap.set(4,240)

# ---------------- SERVO POSITIONS ----------------

base = 90
shoulder = 90
elbow = 90
gripper = 40

base_target = 90
shoulder_target = 90
elbow_target = 90

blink_state = False


# ---------------- SMOOTH SERVO MOVEMENT ----------------

def move_towards(current, target, step=4):
    # Increased step for faster movement
    if abs(target - current) < step:
        return target
    if current < target:
        current += step
    else:
        current -= step
    return current


# ---------------- MAIN LOOP ----------------

import time

last_cmd = ""

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                face_landmarks,
                mp_face_mesh.FACEMESH_CONTOURS)

            face_2d = []
            face_3d = []
            for idx in [33, 263, 1, 61, 291, 199]:
                lm = face_landmarks.landmark[idx]
                x, y = int(lm.x * w), int(lm.y * h)
                face_2d.append([x, y])
                face_3d.append([x, y, lm.z])

            face_2d = np.array(face_2d, dtype=np.float64)
            face_3d = np.array(face_3d, dtype=np.float64)
            focal = w
            cam_matrix = np.array([[focal, 0, w / 2],
                                   [0, focal, h / 2],
                                   [0, 0, 1]])
            dist = np.zeros((4, 1), dtype=np.float64)
            success, rot_vec, trans_vec = cv2.solvePnP(
                face_3d,
                face_2d,
                cam_matrix,
                dist)
            rmat, _ = cv2.Rodrigues(rot_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            pitch = angles[0] * 360
            yaw = angles[1] * 360
            pitch = -pitch

            # ---------------- LEFT RIGHT ----------------
            yaw = max(-30, min(30, yaw))
            base_target = np.interp(yaw, [-30, 30], [60, 120])

            # ---------------- UP DOWN SMOOTH ----------------
            pitch = max(-30, min(30, pitch))
            shoulder_target = np.interp(pitch, [-30, 30], [130, 60])
            elbow_target = np.interp(pitch, [-30, 30], [150, 40])

            # ---------------- BLINK GRIPPER ----------------
            upper = face_landmarks.landmark[159]
            lower = face_landmarks.landmark[145]
            top = int(upper.y * h)
            bottom = int(lower.y * h)
            if abs(top - bottom) < 3:
                if not blink_state:
                    if gripper == 40:
                        gripper = 10
                    else:
                        gripper = 40
                    blink_state = True
            else:
                blink_state = False

            # ---------------- SMOOTH MOTION ----------------
            prev_base, prev_shoulder, prev_elbow, prev_gripper = base, shoulder, elbow, gripper
            base = move_towards(base, base_target)
            shoulder = move_towards(shoulder, shoulder_target)
            elbow = move_towards(elbow, elbow_target)

            # ---------------- LIMITS ----------------
            base = max(0, min(180, base))
            shoulder = max(40, min(140, shoulder))
            elbow = max(20, min(160, elbow))

            # ---------------- DISPLAY ----------------
            cv2.putText(frame, f"Yaw:{int(yaw)}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Pitch:{int(pitch)}", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # ---------------- SEND DATA ----------------
            cmd = f"{int(base)},{int(shoulder)},{int(elbow)},{int(gripper)}\n"
            # Only send if changed
            if cmd != last_cmd:
                ser.write(cmd.encode())
                last_cmd = cmd

    cv2.imshow("Head Pose Robot Control", frame)
    # Add a small delay to reduce update rate and servo heating
    if cv2.waitKey(1) == 27:
        break
    time.sleep(0.02)  # 20 ms delay

cap.release()
cv2.destroyAllWindows()
ser.close()