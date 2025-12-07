# 🤖 AI PET ROBOT - Complete System Documentation

## Table of Contents
1. [System Architecture](#architecture)
2. [Hardware Setup](#hardware-setup)
3. [Installation & Configuration](#installation)
4. [Deployment Guide](#deployment)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Features](#advanced-features)

---

## Architecture

### System Overview

```
                    LAPTOP SERVER (Python Flask)
                    ├─ AI/LLM Processing
                    ├─ Face Animation Engine  
                    ├─ WebSocket Server
                    └─ Bluetooth Manager
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    JETSON NANO    ESP32 (Bluetooth)   MOBILE APP
    │              │                   │
    ├─ Camera      ├─ Motors          ├─ Voice Input
    ├─ HDMI Out    ├─ Speaker         ├─ Display Mirror
    └─ Video TX    ├─ LED             └─ Manual Control
```

### Data Flow

1. **Camera Input**: Jetson Nano captures USB camera → Sends to Server via TCP Socket
2. **Display Output**: Server generates face/text animations → Sends to Jetson (HDMI) & Mobile App (WebSocket)
3. **Motor Control**: Server processes commands → Sends via Bluetooth to ESP32 → Controls DC Motors
4. **Audio Feedback**: ESP32 plays sounds via speaker
5. **Voice Commands**: Mobile app records → Sends to Server → Processes with NLP

---

## Hardware Setup

### Required Components

#### 1. Jetson Nano 2GB
- **HDMI Output**: Connect 800x600 display
- **USB Camera**: USB webcam (640x480 @ 30fps recommended)
- **Network**: Ethernet or WiFi module (for connectivity)
- **Power**: 5V/4A power supply

#### 2. Laptop (Server)
- **OS**: Ubuntu 20.04+ or similar Linux (Intel/AMD processor)
- **Python**: 3.8+
- **Network**: Connected to same network as Jetson Nano
- **Dependencies**: Flask, OpenCV, PyBluez (for Bluetooth)

#### 3. ESP32 DevKit
- **Microcontroller**: ESP32 (dual-core, 240MHz)
- **Connectivity**: Bluetooth Classic
- **Pinout** (as configured in code):
  - **Left Motor**:
    - Forward: GPIO 25
    - Backward: GPIO 26
    - Speed (PWM): GPIO 15
  - **Right Motor**:
    - Forward: GPIO 32
    - Backward: GPIO 33
    - Speed (PWM): GPIO 23
  - **Speaker**: GPIO 19
  - **LED RGB**: GPIO 12 (Red), GPIO 13 (Green), GPIO 14 (Blue)
  - **Status LED**: GPIO 2

#### 4. Motor & Power Setup
- **DC Motors**: 2x 6V/12V brushed DC motors
- **Motor Driver**: L298N or similar (H-bridge)
- **Power Supply**: 
  - Main: 12V/2A for motors
  - ESP32: 5V/1A
  - Jetson: 5V/4A
- **Wheels**: Appropriate wheel diameter for DC motors

#### 5. Sensors & Audio
- **Speaker**: 8Ω/0.5W or similar (connected to ESP32 GPIO 19)
- **LED Strip**: WS2812B or single RGB LED
- **Optional**: Distance sensor, IMU for advanced features

#### 6. Mobile Device
- **OS**: iOS 13+ or Android 6+
- **Network**: Same WiFi as laptop server
- **Storage**: ~100MB free space

### Wiring Diagram

#### ESP32 Motor Connections
```
ESP32             L298N Motor Driver
├─ GPIO 25 -----> IN1
├─ GPIO 26 -----> IN2
├─ GPIO 15 -----> ENA
├─ GPIO 32 -----> IN3
├─ GPIO 33 -----> IN4
└─ GPIO 23 -----> ENB

L298N             Motors
├─ OUT1 ---------> Left Motor +
├─ OUT2 ---------> Left Motor -
├─ OUT3 ---------> Right Motor +
└─ OUT4 ---------> Right Motor -
```

#### Power Distribution
```
12V Supply
├─> Motor Power
└─> L298N +12V

5V Supply
├─> ESP32 (with 100μF capacitor)
├─> Jetson Nano
└─> Additional sensors
```

---

## Installation & Configuration

### Step 1: Prepare Jetson Nano

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-opencv curl git

# Install Python dependencies
pip3 install opencv-python numpy requests

# Configure camera
sudo usermod -a -G video $USER
sudo reboot
```

**Test Camera**:
```bash
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
print('Camera available:', cap.isOpened())
cap.release()
"
```

### Step 2: Setup Laptop Server

#### 2.1 Install Dependencies
```bash
# Python 3.8+ required
python3 --version

# Install virtualenv
pip install virtualenv

# Create virtual environment
python3 -m venv robot_env
source robot_env/bin/activate

# Install required packages
pip install flask flask-socketio flask-cors opencv-python numpy pyserial pillow
```

#### 2.2 Bluetooth Setup (Linux)
```bash
# Install Bluetooth tools
sudo apt install -y bluez python3-bluez

# Pair ESP32
# 1. Make ESP32 discoverable (upload code to ESP32 first)
# 2. Scan for devices
bluetoothctl scan on

# Pair when found
bluetoothctl pair <ESP32_MAC_ADDRESS>

# Create RFCOMM device
sudo rfcomm bind /dev/rfcomm0 <ESP32_MAC_ADDRESS> 1

# Test connection
cat /dev/rfcomm0
```

#### 2.3 Start Server
```bash
cd /path/to/robot/server
source robot_env/bin/activate
python3 server_main.py
```

**Expected Output**:
```
============================================================
AI PET ROBOT SERVER - INITIALIZING
============================================================
2024-12-07 15:30:45 - __main__ - INFO - ✓ Bluetooth initialized
2024-12-07 15:30:46 - __main__ - INFO - ✓ Jetson Nano connection established
2024-12-07 15:30:47 - __main__ - INFO - ✓ Display engine started
============================================================
SYSTEM READY
============================================================
 * Serving Flask app 'app'
 * Running on http://0.0.0.0:5000
```

### Step 3: Configure & Upload ESP32 Code

#### 3.1 Using Arduino IDE
```bash
# 1. Install Arduino IDE
# 2. Add ESP32 board support (Preferences > Additional Boards URLs):
#    https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
# 3. Install esp32 board package (Tools > Board Manager)
# 4. Select board: Tools > Board > ESP32 Dev Module
# 5. Configure settings:
#    - Partition Scheme: Huge APP (3MB No OTA/1MB SPIFFS)
#    - Upload Speed: 115200
# 6. Open esp32_motor_control.ino
# 7. Click Upload
```

#### 3.2 Using PlatformIO
```bash
# Install PlatformIO
pip install platformio

# Create project
pio project init --board esp32

# Copy esp32_motor_control.ino to src/main.cpp
# Upload
pio run -t upload

# Monitor
pio device monitor
```

### Step 4: Deploy Jetson Nano Code

```bash
# Copy jetson_display.py to Jetson
scp jetson_display.py jetson@jetson-nano:/home/jetson/

# Connect to Jetson and run
ssh jetson@jetson-nano
cd /home/jetson
python3 jetson_display.py
```

**Configure IP Addresses** in `jetson_display.py`:
```python
class Config:
    SERVER_HOST = "192.168.1.101"  # Your laptop IP
    SERVER_PORT = 5001
```

### Step 5: Setup Mobile App

#### Option A: Using Expo (Recommended)
```bash
# Install Expo CLI
npm install -g expo-cli

# Create new Expo project
expo init PetRobotApp

# Copy mobile_app.jsx to App.js

# Update server IP in code:
# const SERVER_HOST = '192.168.1.101'; // Your laptop IP

# Install dependencies
npm install socket.io-client expo-av react-native-gesture-handler

# Run on device
expo start

# Scan QR code with phone (Expo app)
```

#### Option B: React Native CLI
```bash
# Create project
npx react-native init PetRobotApp
cd PetRobotApp

# Copy mobile_app.jsx to App.js

# Install dependencies
npm install socket.io-client expo-av react-native-gesture-handler

# Run
npm run android  # or: npm run ios
```

---

## Deployment Guide

### Production Checklist

- [ ] Update IP addresses in all config files
- [ ] Test Bluetooth pairing stability
- [ ] Verify camera resolution and FPS
- [ ] Test voice input on mobile device
- [ ] Check motor response time (<100ms)
- [ ] Verify HDMI display refresh rate
- [ ] Test complete workflow: Voice → Server → Motor
- [ ] Implement error handling & recovery
- [ ] Setup logging & monitoring
- [ ] Create systemd service files for auto-start

### Auto-Start Services (Linux)

#### Server Auto-Start
Create `/etc/systemd/system/robot-server.service`:
```ini
[Unit]
Description=AI Pet Robot Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/robot_server
ExecStart=/home/ubuntu/robot_env/bin/python3 server_main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable robot-server
sudo systemctl start robot-server
```

#### Jetson Auto-Start
Create `/home/jetson/.config/autostart/jetson-display.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=Robot Display
Exec=python3 /home/jetson/jetson_display.py
AutoStart=true
```

---

## API Reference

### WebSocket Events (Server ↔ Mobile App)

#### Client → Server
```javascript
// Voice command
socket.emit('voice_command', {
  text: 'move forward'
});

// Manual motor control
socket.emit('manual_control', {
  left_speed: 80,      // -100 to 100
  right_speed: 80
});

// Change emotion
socket.emit('emotion_request', {
  emotion: 'happy'  // happy, sad, excited, neutral, confused
});

// Display request
socket.emit('display_request', {
  type: 'text',         // 'face', 'text', 'hybrid'
  title: 'Shopping List',
  content: '1. Milk\n2. Bread\n3. Eggs'
});
```

#### Server → Client
```javascript
// Display frame update
socket.on('display_frame', (data) => {
  // data.frame: base64-encoded JPEG
  // data.emotion: current emotion
  // data.timestamp: server timestamp
});

// Command processed
socket.on('command_processed', (response) => {
  // response.action: executed action
  // response.emotion: robot emotion
  // response.display_content: display data
});

// Status update
socket.on('status_update', (data) => {
  // data.message: status message
  // data.timestamp: server timestamp
});
```

### Bluetooth Protocol (ESP32)

#### Packet Format
```
[CMD_TYPE][DATA_BYTES...][OPTIONAL_CHECKSUM]

CMD_TYPE:
  0x01 = Motor control
  0x02 = Audio command
  0x03 = LED command
  0xFF = Heartbeat
```

#### Motor Control Packet
```
[0x01][LEFT_SPEED][RIGHT_SPEED][CHECKSUM]

LEFT_SPEED, RIGHT_SPEED:
  Range: 0-200 (corresponds to -100..100 speed)
  Conversion: speed = (byte * 2) - 100

CHECKSUM:
  (0x01 + LEFT_SPEED + RIGHT_SPEED) & 0xFF
```

### REST API Endpoints (Server)

```
GET /api/status
  Returns: { mode, emotion, display_mode, connected_devices }

GET /api/video/latest
  Returns: { frame: base64_jpeg, timestamp }

POST /api/command
  Body: { command: string, params: object }
  Returns: { success: boolean, result: object }
```

---

## Troubleshooting

### Connection Issues

**Problem**: Jetson can't connect to Server
```bash
# Check IP address
ifconfig
# Update SERVER_HOST in jetson_display.py

# Test connectivity
ping 192.168.1.101

# Check firewall
sudo ufw allow 5000
sudo ufw allow 5001
```

**Problem**: Bluetooth connection unstable
```bash
# Check paired devices
bluetoothctl paired-devices

# Repair ESP32
bluetoothctl remove <ESP32_MAC>
bluetoothctl pair <ESP32_MAC>

# Check RFCOMM
sudo rfcomm -a

# Increase timeout in server code:
self.socket.settimeout(10)  # was 5
```

### Performance Issues

**Problem**: High latency in motor response
```
Typical latency breakdown:
- Voice processing: 200-500ms
- Network transmission: 20-50ms
- ESP32 processing: 10-20ms
- Motor response: 50-100ms
Total: 280-670ms

Optimization:
1. Use lightweight face generation (cache pre-rendered frames)
2. Reduce JPEG compression quality
3. Increase motor PWM frequency
4. Use direct Bluetooth instead of WebSocket for motors
```

**Problem**: Jetson camera laggy
```bash
# Check FPS
python3 -c "
import cv2
import time
cap = cv2.VideoCapture(0)
start = time.time()
for i in range(100):
    ret, frame = cap.read()
elapsed = time.time() - start
print(f'FPS: {100/elapsed:.1f}')
"

# Reduce resolution if needed:
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
```

### Common Errors

**Error**: `ModuleNotFoundError: No module named 'flask'`
```bash
source robot_env/bin/activate
pip install flask flask-socketio
```

**Error**: `Permission denied: '/dev/rfcomm0'`
```bash
sudo chmod 666 /dev/rfcomm0
# Or make permanent:
sudo usermod -a -G dialout $USER
```

**Error**: Camera not detected
```bash
# List connected devices
ls /dev/video*

# Check permissions
v4l2-ctl --list-devices

# Test with fswebcam
fswebcam test_image.jpg
```

---

## Advanced Features

### 1. Add LLM Integration (GPT-3/LLaMA)

```python
import openai  # or use Ollama for local LLM

def generate_response_with_llm(voice_text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": f"Robot emotional response to: {voice_text}"
        }]
    )
    return response.choices[0].message.content
```

### 2. Add Emotion Recognition from Camera

```python
import tensorflow as tf
from tensorflow.keras.models import load_model

emotion_model = load_model('emotion_detection_model.h5')

def detect_emotion_from_face(frame):
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = face_cascade.detectMultiScale(frame)
    
    if len(faces) > 0:
        x, y, w, h = faces[0]
        face_roi = frame[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (48, 48))
        prediction = emotion_model.predict(np.expand_dims(face_roi, axis=0))
        emotions = ['happy', 'sad', 'neutral', 'surprised', 'angry']
        return emotions[np.argmax(prediction)]
    return 'neutral'
```

### 3. Add Voice Synthesis (TTS)

```python
from google.cloud import texttospeech

def synthesize_speech(text):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    synthesis_input = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )
    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=synthesis_input,
    )
    return response.audio_content
```

### 4. Add Database for Memory

```python
import sqlite3

def save_interaction(user_input, robot_response, emotion):
    conn = sqlite3.connect('robot_memory.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interactions (user_input, robot_response, emotion, timestamp)
        VALUES (?, ?, ?, datetime('now'))
    ''', (user_input, robot_response, emotion))
    conn.commit()
    conn.close()

def get_conversation_history(limit=10):
    conn = sqlite3.connect('robot_memory.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_input, robot_response FROM interactions 
        ORDER BY timestamp DESC LIMIT ?
    ''', (limit,))
    return cursor.fetchall()
```

### 5. Add Web Dashboard

```python
@app.route('/dashboard')
def dashboard():
    return '''
    <html>
    <head>
        <title>Robot Dashboard</title>
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    </head>
    <body>
        <h1>PET ROBOT Dashboard</h1>
        <div id="video-stream"></div>
        <div id="status"></div>
        <script>
            const socket = io();
            socket.on('display_frame', (data) => {
                document.getElementById('video-stream').innerHTML = 
                    '<img src="data:image/jpeg;base64,' + data.frame + '">';
            });
        </script>
    </body>
    </html>
    '''
```

---

## Network Configuration

### Static IP Assignment (Recommended)

**Jetson Nano**:
```bash
# Edit /etc/netplan/01-netcfg.yaml
sudo nano /etc/netplan/01-netcfg.yaml

# Add:
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]

# Apply:
sudo netplan apply
```

### Port Forwarding (if accessing remotely)

```bash
# Router configuration:
# Forward external port 5000 → laptop:5000
# Forward external port 5001 → jetson:5001

# Test:
curl http://external-ip:5000/api/status
```

---

## Performance Monitoring

```python
import psutil
import threading

def monitor_system():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        logger.info(f"CPU: {cpu_percent}%, Memory: {memory.percent}%")
        
        # Alert if resources exceed threshold
        if cpu_percent > 80 or memory.percent > 85:
            logger.warning("High resource usage detected")
        
        time.sleep(10)

# Start monitoring thread
threading.Thread(target=monitor_system, daemon=True).start()
```

---

## Next Steps

1. **Implement Speech-to-Text**: Use Google Speech-to-Text API for voice commands
2. **Add Emotion Recognition**: Train model to recognize emotions from voice/face
3. **Implement Memory System**: Use database to remember user preferences
4. **Add Web Dashboard**: Create admin interface for system monitoring
5. **Optimize Performance**: Profile and optimize critical paths
6. **Deploy to Cloud**: Consider cloud deployment for voice processing
7. **Add Advanced Features**: Distance sensing, navigation, learning

---

**Created**: 2024-12-07
**Last Updated**: 2024-12-07
**Version**: 1.0.0