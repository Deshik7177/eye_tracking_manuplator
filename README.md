# Eye-Tracked 4-DOF Robotic Arm

A real-time eye-tracking system that controls a 4-DOF robotic arm using MediaPipe face detection and an ESP32 microcontroller.

## Features

- **Real-time Eye Tracking**: Uses MediaPipe to track eye gaze in real-time
- **4-DOF Control**: Controls Base, Shoulder, Elbow, and Gripper servo motors
- **Blink Detection**: Gripper toggle with eye blink detection
- **Zone-Based Movement**: Incremental step-based control using gaze zones
- **Smooth Servo Motion**: Gradual 3°/step servo transitions to prevent jitter
- **Serial Communication**: Direct ESP32 control via USB serial (COM7 @ 115200 baud)

## Hardware Requirements

### Servos
- **Base**: Pin 13 (0-180°, rotates left/right)
- **Shoulder**: Pin 12 (0-90°, moves up/down)
- **Elbow**: Pin 14 (0-90°, extends/retracts)
- **Gripper**: Pin 27 (0-90°, closes/opens)

### Microcontroller
- ESP32 with Arduino IDE support
- USB cable for serial communication

## Installation

### 1. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Upload ESP32 Code

1. Open `esp32.ino` in Arduino IDE
2. Select Board: **ESP32 Dev Module**
3. Select Port: **COM7** (or your ESP32's port)
4. Click **Upload**

### 3. Run Python Script

```bash
python new1.py
```

## Usage

### Eye Gaze Control

#### Base (Left/Right)
- **Look LEFT** → Base rotates left (0°)
- **Look CENTER** → Base stays centered (90°)
- **Look RIGHT** → Base rotates right (180°)

#### Shoulder (Up/Down)
- **Look DOWN** → Shoulder moves down (0°)
- **Look CENTER** → Shoulder stays center (45°)
- **Look UP** → Shoulder moves up (90°)

#### Elbow (Up/Down)
- **Look DOWN** (with RIGHT eye) → Elbow retracts (0°)
- **Look CENTER** → Elbow stays center (45°)
- **Look UP** (with RIGHT eye) → Elbow extends (90°)

#### Gripper (Blink)
- **BLINK** → Gripper toggles between closed (90°) and open (0°)

### Calibration Thresholds

Edit these values in `new1.py` (lines 118-124) to adjust sensitivity:

```python
# X-axis (LEFT/RIGHT) thresholds
LEFT_THRESHOLD = 30     # Lower = LEFT triggers more easily
RIGHT_THRESHOLD = 70    # Higher = RIGHT triggers more easily

# Y-axis (UP/DOWN) thresholds
UP_THRESHOLD = 20       # Lower = DOWN triggers more easily
DOWN_THRESHOLD = 60     # Higher = UP triggers more easily
```

### Fine-Tuning

- **Too many uncontrolled movements?** Increase thresholds (30→40, 70→80)
- **Not responsive enough?** Decrease thresholds (20→15, 60→55)
- **Gripper blink too sensitive?** Adjust `EAR_THRESHOLD` and blink frame counts in code

## File Structure

- **new1.py** - Main Python control script with eye tracking
- **new1.ino** - ESP32 Arduino code for servo control
- **requirements.txt** - Python dependencies
- **README.md** - This file

## Troubleshooting

### Serial Connection Error
```
ERROR: Serial Port not found
```
- Ensure ESP32 is connected via USB
- Check that COM7 matches your device (Device Manager → Ports)
- Update port in `new1.py` line 8: `ser = serial.Serial('COMX', 115200)`

### Eye Tracking Not Detecting
- Ensure good lighting
- Position camera to see both eyes clearly
- Adjust MediaPipe confidence: Change `min_detection_confidence` in code (line ~26)

### Servo Not Moving
- Check ESP32 serial output for angle commands
- Verify servo pins match your wiring (pins 13, 12, 14, 27)
- Test servo separately with fixed angle values

### Movement Too Slow/Fast
- Adjust `STEP_SIZE = 20` (line 20) - increase for bigger steps, decrease for smaller
- Adjust servo delay in `new1.ino` - default is 15ms per 3° step

## Technical Details

### Eye Tracking Pipeline
1. Capture camera frame with OpenCV
2. Detect face and 468 eye landmarks with MediaPipe
3. Calculate gaze position (0-100 scale for each axis)
4. Apply 5-frame moving average smoothing
5. Detect zone changes (LEFT/CENTER/RIGHT, UP/CENTER/DOWN)
6. Send servo commands when zone changes

### Movement System
- **Incremental**: Each gaze zone triggers ±20° servo step
- **Smooth**: ESP32 interpolates from current to target angle at 3°/step
- **Responsive**: Only moves when gaze enters new zone

### Blink Detection
- Eye Aspect Ratio (EAR) threshold: < 0.010
- Detection window: 2-20 consecutive frames
- Toggles gripper between 0° (open) and 90° (closed)

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| opencv-python | 4.8.0.76 | Camera capture & display |
| mediapipe | 0.10.0 | Face & eye landmark detection |
| pyserial | 3.5 | Serial communication to ESP32 |
| numpy | 1.24.3 | Numerical array operations |

## Notes

- Keep camera 30-60cm from face for best detection
- Lighting should be even (no harsh shadows on face)
- Serial baud rate must match ESP32: **115200**
- Each servo command format: `Base,Shoulder,Elbow,Gripper` (0-180 or 0-100 range)

## Future Improvements

- Add object detection for smart picking
- Implement trajectory recording/playback
- Gesture recognition for additional commands
- Web interface for remote control
- Multi-eye calibration profiles
