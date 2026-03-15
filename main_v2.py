import cv2
import mediapipe as mp
import serial

# ---------------- SERIAL ----------------
ser = serial.Serial("COM7",115200)

# ---------------- MEDIAPIPE ----------------
mp_face_mesh = mp.solutions.face_mesh
mp_draw = mp.solutions.drawing_utils

face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

cap = cv2.VideoCapture(0)
cap.set(3,320)
cap.set(4,240)

# ---------------- SERVO START POSITIONS ----------------
base = 90
shoulder = 90
elbow = 90
gripper = 40

blink_state = False

while True:

    ret, frame = cap.read()
    frame = cv2.flip(frame,1)

    h,w,_ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            # draw face mesh
            mp_draw.draw_landmarks(
                frame,
                face_landmarks,
                mp_face_mesh.FACEMESH_CONTOURS)

            # LEFT EYE
            left = face_landmarks.landmark[33]
            right = face_landmarks.landmark[133]
            iris = face_landmarks.landmark[468]

            # eyelids
            top = face_landmarks.landmark[159]
            bottom = face_landmarks.landmark[145]

            lx = int(left.x*w)
            rx = int(right.x*w)
            ix = int(iris.x*w)
            iy = int(iris.y*h)

            top_y = int(top.y*h)
            bottom_y = int(bottom.y*h)

            cv2.circle(frame,(ix,iy),4,(0,0,255),-1)

            # ---------------- HORIZONTAL CONTROL ----------------

            gaze = (ix-lx)/(rx-lx)

            offset = gaze-0.5

            base += int(offset*10)

            # ---------------- VERTICAL CONTROL ----------------

            eye_height = bottom_y-top_y

            if eye_height > 0:

                v = (iy-top_y)/eye_height
                v_offset = v-0.5

                # forward/back motion
                shoulder += int(v_offset*8)
                elbow += int(v_offset*6)

            # ---------------- BLINK DETECTION ----------------

            if abs(top_y-bottom_y) < 3:

                if not blink_state:

                    gripper = 10 if gripper==40 else 40
                    blink_state = True

            else:

                blink_state = False

            # ---------------- LIMITS ----------------

            base = max(0,min(180,base))
            shoulder = max(40,min(140,shoulder))
            elbow = max(40,min(140,elbow))

            # ---------------- DISPLAY VALUES ----------------

            cv2.putText(frame,f"Base:{base}",(10,30),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)

            cv2.putText(frame,f"Shoulder:{shoulder}",(10,55),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)

            cv2.putText(frame,f"Elbow:{elbow}",(10,80),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)

            cv2.putText(frame,f"Gripper:{gripper}",(10,105),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)

            # ---------------- SEND TO ESP32 ----------------

            command = f"{base},{shoulder},{elbow},{gripper}\n"
            ser.write(command.encode())

    cv2.imshow("Eye Controlled Robot Arm",frame)

    if cv2.waitKey(1)==27:
        break

cap.release()
cv2.destroyAllWindows()
ser.close()