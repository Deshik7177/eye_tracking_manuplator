// --- ESP32 ROBOTIC ARM CONTROLLER ---
// Receives eye tracking data from Python and controls arm servos
// Serial Format: X,Y,Gripper (values 0-100)

#include <ESP32Servo.h>

// --- PIN DEFINITIONS ---
#define PIN_BASE 13
#define PIN_SHOULDER 12
#define PIN_ELBOW 14
#define PIN_GRIPPER 27

// --- SERVO OBJECTS ---
Servo base;
Servo shoulder;
Servo elbow;
Servo gripper;

// --- ANGLE LIMITS (adjust based on your arm) ---
const int SHOULDER_MIN = 0;
const int SHOULDER_MAX = 180;
const int ELBOW_MIN = 10;
const int ELBOW_MAX = 170;
const int GRIPPER_OPEN = 10;
const int GRIPPER_CLOSE = 90;

// --- MOVEMENT SPEED ---
const int SERVO_SPEED = 3;   // degrees per step (lower = smoother)
const int SERVO_DELAY = 15;  // milliseconds between steps

// --- VARIABLES ---
String inputBuffer = "";
int currentX = 50;
int currentY = 50;
int currentGrip = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Attach servos
  base.attach(PIN_BASE);
  shoulder.attach(PIN_SHOULDER);
  elbow.attach(PIN_ELBOW);
  gripper.attach(PIN_GRIPPER);
  
  // Home position
  base.write(90);
  shoulder.write(90);
  elbow.write(90);
  gripper.write(GRIPPER_OPEN);
  
  delay(500);
  Serial.println("\nARM READY - Waiting for data...");
  Serial.println("Format: X,Y,Gripper");
}

void loop() {
  // Read serial data
  while (Serial.available()) {
    char ch = Serial.read();
    
    if (ch == '\n' || ch == '\r') {
      if (inputBuffer.length() > 0) {
        handleCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += ch;
    }
  }
}

void handleCommand(String cmd) {
  // Parse: X,Y,Gripper
  int comma1 = cmd.indexOf(',');
  int comma2 = cmd.lastIndexOf(',');
  
  if (comma1 < 0 || comma2 < 0 || comma1 == comma2) return;
  
  int x = cmd.substring(0, comma1).toInt();
  int y = cmd.substring(comma1 + 1, comma2).toInt();
  int grip = cmd.substring(comma2 + 1).toInt();
  
  // Validate ranges
  if (x < 0 || x > 100 || y < 0 || y > 100) return;
  
  // Store values
  currentX = x;
  currentY = y;
  currentGrip = grip;
  
  // Convert 0-100 to servo angles
  int baseAngle = map(x, 0, 100, SHOULDER_MIN, SHOULDER_MAX);
  int shoulderAngle = map(x, 0, 100, SHOULDER_MIN, SHOULDER_MAX);
  int elbowAngle = map(y, 0, 100, ELBOW_MIN, ELBOW_MAX);
  int gripperAngle = (grip == 1) ? GRIPPER_CLOSE : GRIPPER_OPEN;
  
  // Move servos smoothly
  smoothMove(base, baseAngle);
  smoothMove(shoulder, shoulderAngle);
  smoothMove(elbow, elbowAngle);
  smoothMove(gripper, gripperAngle);
  
  // Serial feedback
  Serial.print("X=");
  Serial.print(x);
  Serial.print(" Y=");
  Serial.print(y);
  Serial.print(" G=");
  Serial.println(grip);
}

void smoothMove(Servo &servo, int targetAngle) {
  int currentAngle = servo.read();
  
  while (currentAngle != targetAngle) {
    if (currentAngle < targetAngle) {
      currentAngle = min(currentAngle + SERVO_SPEED, targetAngle);
    } else {
      currentAngle = max(currentAngle - SERVO_SPEED, targetAngle);
    }
    servo.write(currentAngle);
    delay(SERVO_DELAY);
  }
}
