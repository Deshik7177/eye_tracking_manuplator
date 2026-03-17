// --- ESP32 4-DOF ARM CONTROLLER ---
// 4 Degrees of Freedom: Base, Shoulder, Elbow, Wrist
// Receives: Base,Shoulder,Elbow,Wrist values (0-180 degrees or 0-100 scale)

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

// --- ANGLE LIMITS (CALIBRATED) ---
const int BASE_MIN = 0;
const int BASE_MAX = 180;
const int SHOULDER_MIN = 30;
const int SHOULDER_MAX = 90;
const int ELBOW_MIN = 0;
const int ELBOW_MAX = 90;
const int GRIPPER_MIN = 0;      // Open
const int GRIPPER_MAX = 90;     // Close

// --- MOVEMENT PARAMETERS ---
const int SERVO_SPEED = 3;   // degrees per step
const int SERVO_DELAY = 15;  // milliseconds between steps

// --- VARIABLES ---
String inputBuffer = "";
int currentBase = 90;
int currentShoulder = 30;
int currentElbow = 0;
int currentGripper = 0;

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
  shoulder.write(30);
  elbow.write(0);
  gripper.write(GRIPPER_MIN);
  
  delay(500);
  Serial.println("\n=== 4-DOF ARM CONTROLLER ===");
  Serial.println("Ready! Waiting for commands...");
  Serial.println("Format: Base,Shoulder,Elbow,Gripper");
  Serial.println("Range: 0-180 degrees (or 0-100 auto-mapped)");
  Serial.println("Example: 90,80,100,70");
  Serial.println("============================");
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
  // Parse: Base,Shoulder,Elbow,Gripper
  int comma1 = cmd.indexOf(',');
  int comma2 = cmd.indexOf(',', comma1 + 1);
  int comma3 = cmd.lastIndexOf(',');
  
  if (comma1 < 0 || comma2 < 0 || comma3 < 0) {
    Serial.println("ERR: Format Base,Shoulder,Elbow,Gripper");
    return;
  }
  
  int b = cmd.substring(0, comma1).toInt();
  int s = cmd.substring(comma1 + 1, comma2).toInt();
  int e = cmd.substring(comma2 + 1, comma3).toInt();
  int g = cmd.substring(comma3 + 1).toInt();
  
  // Auto-map 0-100 to servo ranges if values are <= 100
  if (b <= 100) b = map(b, 0, 100, BASE_MIN, BASE_MAX);
  if (s <= 100) s = map(s, 0, 100, SHOULDER_MIN, SHOULDER_MAX);
  if (e <= 100) e = map(e, 0, 100, ELBOW_MIN, ELBOW_MAX);
  
  // Validate ranges
  if (b < BASE_MIN || b > BASE_MAX) {
    Serial.print("ERR: Base out of range: ");
    Serial.println(b);
    return;
  }
  if (s < SHOULDER_MIN || s > SHOULDER_MAX) {
    Serial.print("ERR: Shoulder out of range: ");
    Serial.println(s);
    return;
  }
  if (e < ELBOW_MIN || e > ELBOW_MAX) {
    Serial.print("ERR: Elbow out of range: ");
    Serial.println(e);
    return;
  }
  if (g < GRIPPER_MIN || g > GRIPPER_MAX) {
    Serial.print("ERR: Gripper out of range (0-90): ");
    Serial.println(g);
    return;
  }
  
  // Store current values
  currentBase = b;
  currentShoulder = s;
  currentElbow = e;
  currentGripper = g;
  
  // Move all servos
  smoothMove(base, b, "Base");
  smoothMove(shoulder, s, "Shoulder");
  smoothMove(elbow, e, "Elbow");
  gripper.write(g);
  
  // Feedback
  Serial.print("Cmd: B=");
  Serial.print(b);
  Serial.print(" S=");
  Serial.print(s);
  Serial.print(" E=");
  Serial.print(e);
  Serial.print(" G=");
  Serial.print(g);
  Serial.println("°");
}

void smoothMove(Servo &servo, int targetAngle, String name) {
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
  
  Serial.print("  ");
  Serial.print(name);
  Serial.print(" -> ");
  Serial.println(targetAngle);
}

// --- UTILITY FUNCTIONS ---
void homePosition() {
  Serial.println("Moving to HOME...");
  handleCommand("90,30,0,0");
}
