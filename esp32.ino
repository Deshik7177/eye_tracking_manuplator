#include <ESP32Servo.h>

Servo baseServo;
Servo shoulderServo;
Servo elbowServo;
Servo gripperServo;

String data = "";

void setup() {

  Serial.begin(115200);

  baseServo.attach(13);
  shoulderServo.attach(12);
  elbowServo.attach(14);
  gripperServo.attach(27);

  baseServo.write(90);
  shoulderServo.write(70);
  elbowServo.write(50);
  gripperServo.write(40);

}

void loop() {

  if (Serial.available()) {

    data = Serial.readStringUntil('\n');

    int a = data.indexOf(',');
    int b = data.indexOf(',', a+1);
    int c = data.indexOf(',', b+1);

    int base = data.substring(0,a).toInt();
    int shoulder = data.substring(a+1,b).toInt();
    int elbow = data.substring(b+1,c).toInt();
    int gripper = data.substring(c+1).toInt();

    base = constrain(base,0,180);
    shoulder = constrain(shoulder,20,160);
    elbow = constrain(elbow,10,170);
    gripper = constrain(gripper,10,90);

    baseServo.write(base);
    shoulderServo.write(shoulder);
    elbowServo.write(elbow);
    gripperServo.write(gripper);

  }

}