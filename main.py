import cv2
import mediapipe as mp
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# SERIAL (ENABLE WHEN ESP32 CONNECTED)
# -----------------------------
USE_SERIAL = False

if USE_SERIAL:
    import serial
    ser = serial.Serial("COM4",115200)

# -----------------------------
# MEDIAPIPE SETUP
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

cap = cv2.VideoCapture(0)

# -----------------------------
# ROBOT ARM PARAMETERS
# -----------------------------
L1 = 120
L2 = 100
L3 = 80

base = 90
shoulder = 70
elbow = 50
gripper = 40

# -----------------------------
# SIMULATION WINDOW
# -----------------------------
plt.ion()
fig = plt.figure()

def draw_arm(shoulder, elbow):

    shoulder_r = np.radians(shoulder)
    elbow_r = np.radians(elbow)

    x0,y0 = 0,0

    x1 = L1*np.cos(shoulder_r)
    y1 = L1*np.sin(shoulder_r)

    x2 = x1 + L2*np.cos(shoulder_r+elbow_r)
    y2 = y1 + L2*np.sin(shoulder_r+elbow_r)

    x3 = x2 + L3*np.cos(shoulder_r+elbow_r)
    y3 = y2 + L3*np.sin(shoulder_r+elbow_r)

    plt.cla()

    plt.plot([x0,x1],[y0,y1],'ro-',linewidth=4)
    plt.plot([x1,x2],[y1,y2],'go-',linewidth=4)
    plt.plot([x2,x3],[y2,y3],'bo-',linewidth=4)

    plt.xlim(-250,250)
    plt.ylim(0,250)

    plt.title("Manipulator Simulation")

    plt.pause(0.001)

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:

    ret, frame = cap.read()
    frame = cv2.flip(frame,1)

    h,w,_ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            # eye corners
            left = face_landmarks.landmark[33]
            right = face_landmarks.landmark[133]

            # iris center
            iris = face_landmarks.landmark[468]

            lx,ly = int(left.x*w), int(left.y*h)
            rx,ry = int(right.x*w), int(right.y*h)
            ix,iy = int(iris.x*w), int(iris.y*h)

            cv2.circle(frame,(ix,iy),4,(0,255,0),-1)
            cv2.line(frame,(lx,ly),(rx,ry),(255,0,0),2)

            eye_width = rx - lx

            if eye_width != 0:
                gaze_ratio = (ix - lx) / eye_width
            else:
                gaze_ratio = 0.5

            # -----------------------------
            # HORIZONTAL MOVEMENT
            # -----------------------------
            if gaze_ratio < 0.35:

                base -= 2
                direction = "LEFT"

            elif gaze_ratio > 0.65:

                base += 2
                direction = "RIGHT"

            else:

                direction = "CENTER"

            cv2.putText(frame,direction,(50,50),
                        cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)

            # -----------------------------
            # VERTICAL MOVEMENT
            # -----------------------------
            if iy < h*0.4:

                shoulder += 2
                cv2.putText(frame,"UP",(50,90),
                            cv2.FONT_HERSHEY_SIMPLEX,1,(255,0,0),2)

            elif iy > h*0.6:

                shoulder -= 2
                cv2.putText(frame,"DOWN",(50,90),
                            cv2.FONT_HERSHEY_SIMPLEX,1,(255,0,0),2)

            # -----------------------------
            # LIMIT SERVO ANGLES
            # -----------------------------
            base = max(0,min(180,base))
            shoulder = max(20,min(160,shoulder))

            # -----------------------------
            # UPDATE SIMULATION
            # -----------------------------
            draw_arm(shoulder, elbow)

            # -----------------------------
            # SEND TO ESP32
            # -----------------------------
            if USE_SERIAL:

                command = f"{base},{shoulder},{elbow},{gripper}\n"
                ser.write(command.encode())

    cv2.imshow("Eye Controlled Manipulator",frame)

    if cv2.waitKey(1)==27:
        break

cap.release()
cv2.destroyAllWindows()

if USE_SERIAL:
    ser.close()