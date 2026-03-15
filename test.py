import cv2
import mediapipe as mp
import numpy as np
import time

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True,
    max_num_faces=1
)

cap = cv2.VideoCapture(0)

# lower resolution for higher FPS
cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)

LEFT_EYE = [33,160,158,133,153,144]

prev_time = 0

while True:

    ret, frame = cap.read()
    frame = cv2.flip(frame,1)

    h,w,_ = frame.shape

    rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    if result.multi_face_landmarks:

        for face_landmarks in result.multi_face_landmarks:

            eye_points = []

            for id in LEFT_EYE:

                lm = face_landmarks.landmark[id]
                x = int(lm.x*w)
                y = int(lm.y*h)

                eye_points.append((x,y))
                cv2.circle(frame,(x,y),2,(0,255,0),-1)

            eye_region = np.array(eye_points,np.int32)

            x,y,w_eye,h_eye = cv2.boundingRect(eye_region)

            eye_crop = frame[y:y+h_eye,x:x+w_eye]

            gray = cv2.cvtColor(eye_crop,cv2.COLOR_BGR2GRAY)

            _,thresh = cv2.threshold(gray,40,255,cv2.THRESH_BINARY_INV)

            contours,_ = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

            if contours:

                c = max(contours,key=cv2.contourArea)

                (cx,cy),radius = cv2.minEnclosingCircle(c)

                cx = int(cx)
                cy = int(cy)

                cv2.circle(eye_crop,(cx,cy),3,(0,0,255),-1)

                gaze_ratio = cx / w_eye

                if gaze_ratio < 0.35:
                    direction = "LEFT"

                elif gaze_ratio > 0.65:
                    direction = "RIGHT"

                else:
                    direction = "CENTER"

                cv2.putText(frame,direction,(50,60),
                            cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),2)

            frame[y:y+h_eye,x:x+w_eye] = eye_crop

    # FPS calculation
    curr_time = time.time()
    fps = 1/(curr_time-prev_time)
    prev_time = curr_time

    cv2.putText(frame,f"FPS: {int(fps)}",(50,30),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

    cv2.imshow("Real-Time Pupil Tracking",frame)

    if cv2.waitKey(1)==27:
        break

cap.release()
cv2.destroyAllWindows()