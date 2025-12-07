# 🚀 JETBOT OS v2.0.0 - COMPLETE DEPLOYMENT GUIDE

## Phase 1: Pre-Deployment Preparation (15 minutes)

### 1.1 Verify Hardware Setup

**Check you have all components:**
```bash
# Hardware checklist
- Jetson Nano (with JetOS installed)
- NodeMCU 1.0 (ESP-12E)
- L298N Motor Driver
- 2x DC Motors (12V, 2A max)
- 12V Battery (LiPo 4S or 4x18650)
- AMS1117 5V Voltage Regulator
- USB cable for ESP12E (CH340 driver)
- Network connection for Jetson
```

**Verify connections:**
```bash
# On Jetson, test network
ping 8.8.8.8

# Check that you have internet access
curl https://www.google.com -I
```

### 1.2 Verify Hardware Wiring

**Double-check motor driver wiring:**
```
ESP12E          L298N           Motors
─────────────────────────────────────
D1 (GPIO5)  → IN1              Left Motor +
D2 (GPIO4)  → IN2              Left Motor -
D3 (GPIO0)  → IN3              Right Motor +
D4 (GPIO2)  → IN4              Right Motor -
D5 (GPIO14) → ENA (PWM)        Left Speed
D6 (GPIO12) → ENB (PWM)        Right Speed

Power:
GND → GND (all common)
5V  → +5V (L298N + ESP12E)
12V → L298N +12V
```

**Test battery power:**
```bash
# With multimeter check:
# - Battery: 12V between + and -
# - Regulator output: 5V
# - L298N +12V: 12V when powered
```

### 1.3 Prepare Jetson Nano

**Connect to Jetson:**
```bash
# Via SSH
ssh jetson@192.168.x.x
# Or via monitor/keyboard

# Update system
sudo apt update
sudo apt upgrade -y

# Check Python version (need 3.7+)
python3 --version

# Check git
git --version
```

---

## Phase 2: Clone Repository (5 minutes)

### 2.1 Clone from GitHub

```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/Eshwarpawanpeddi/Jetbot_os.git

# Enter directory
cd Jetbot_os

# Verify files exist
ls -la

# Should show:
# - server_main.py
# - esp12e_controller.py
# - jetson_display.py
# - esp12e_motor_control.ino
# - requirements.txt
# - config.json
# - .env.example
# - setup.sh
```

### 2.2 Verify Repository Structure

```bash
# Check branch
git branch

# Check remote
git remote -v

# Show last commit
git log --oneline -5
```

---

## Phase 3: Arduino Firmware Upload (10 minutes)

### 3.1 Install Arduino IDE (on your computer, not Jetson)

**On Windows/Mac/Linux:**
```bash
# Download from: https://www.arduino.cc/en/software
# Or via package manager:

# Ubuntu/Debian
sudo apt install arduino

# Or download the AppImage
wget https://downloads.arduino.cc/arduino-1.8.19-linux64.AppImage
chmod +x arduino-1.8.19-linux64.AppImage
./arduino-1.8.19-linux64.AppImage
```

### 3.2 Install ESP8266 Board Support

**In Arduino IDE:**
```
1. Go to: File → Preferences
2. Add Board Manager URL:
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
3. Go to: Tools → Board Manager
4. Search for "ESP8266"
5. Install: "ESP8266 Community" by ESP8266 Community
```

### 3.3 Configure Arduino IDE for ESP-12E

**Board Settings:**
```
Board:           NodeMCU 1.0 (ESP-12E Module)
Upload Speed:    921600
CPU Frequency:   80 MHz
Flash Size:      4M (3M SPIFFS)
Port:            COM3 (or /dev/ttyUSB0 on Linux)
Programmer:      esptool
```

### 3.4 Prepare Firmware Code

**On your computer:**
```bash
# Navigate to cloned repository
cd ~/Jetbot_os

# Open the .ino file in Arduino IDE:
# File → Open → esp12e_motor_control.ino

# OR from command line:
cat esp12e_motor_control.ino | head -50
# Check that you can see the WiFi setup code
```

### 3.5 Update WiFi Credentials

**In Arduino IDE, find lines 39-40:**
```cpp
// EDIT THESE WITH YOUR WIFI CREDENTIALS
const char* ssid = "YOUR_SSID";          // Change this
const char* password = "YOUR_PASSWORD";   // Change this
```

**Update with your actual WiFi:**
```cpp
const char* ssid = "YourWiFiName";
const char* password = "YourWiFiPassword";
```

### 3.6 Connect ESP12E to Computer

**Install USB driver (if needed):**
```bash
# For CH340 USB chip (most common)
# Windows: Download from https://www.wch.cn/downloads/category/12.html
# Mac: brew install wch-ch34x-usb-serial-driver
# Linux: Usually auto-detected
```

**Connect USB cable:**
```
ESP12E Micro USB → Computer USB
```

### 3.7 Upload Firmware

**In Arduino IDE:**
```
1. Sketch → Verify (compile only)
   [Wait for "Compiling sketch..." to complete]

2. Sketch → Upload
   [Wait for "Uploading..." and progress bar]

3. Check serial output:
   Tools → Serial Monitor (9600 baud initially)
   Then change to 115200 baud
```

**Expected output in Serial Monitor:**
```
[INIT] GPIO initialized...
[INIT] GPIO for motors configured
[WIFI] Connecting to: YourWiFiName
[WIFI] WiFi connected!
[WIFI] IP address: 192.168.x.x
[SERVER] HTTP server started on port 80
[DEBUG] Waiting for requests...
```

### 3.8 Verify ESP12E Firmware

**Find the ESP12E IP address from serial output (example: 192.168.1.50):**

```bash
# Open browser and visit:
http://192.168.1.50

# Should show simple web UI with buttons for:
# - Forward, Backward, Left, Right, Stop
# - Speed slider (0-255)

# Test forward command:
curl -X POST http://192.168.1.50/api/motor \
  -H "Content-Type: application/json" \
  -d '{"direction":"forward","speed":150}'

# Should respond:
# {"status":"success","direction":"forward","speed":150}
```

**If motors move → ESP12E firmware is working! ✅**

**Troubleshooting:**
```bash
# If can't access web UI:
# 1. Check Serial Monitor for IP address
# 2. Verify ESP12E is connected to same WiFi network
# 3. Try: ping 192.168.1.50
# 4. Check firewall settings
# 5. Try uploading firmware again
```

---

## Phase 4: Jetson Nano Setup (10 minutes)

### 4.1 Install Python Dependencies

```bash
# On Jetson Nano, navigate to project
cd ~/Jetbot_os

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This will install:
# - Flask 2.3.0
# - Flask-CORS 4.0.0
# - Flask-SocketIO 5.9.0
# - requests 2.31.0
# - opencv-python 4.8.0
# - numpy 1.24.0
# - eventlet 0.33.3
```

**Wait for installation to complete (5-10 minutes)**

**Verify installation:**
```bash
# Test imports
python3 << 'EOF'
import flask
import flask_cors
import flask_socketio
import requests
import cv2
import numpy
import eventlet
print("✅ All dependencies installed successfully!")
EOF
```

### 4.2 Create Environment File

```bash
# Create .env from template
cp .env.example .env

# Edit with your settings
nano .env

# Update the following values:
```

**Update .env file:**
```bash
# .env configuration

# Server settings
SERVER_HOST=0.0.0.0              # Listen on all interfaces
SERVER_PORT=5000                 # Flask port
DEBUG_MODE=false                 # Production mode

# ESP12E Motor Controller (IMPORTANT - Update this!)
ESP12E_IP=192.168.1.50           # Change to your ESP12E IP from Serial Monitor
ESP12E_PORT=80                   # ESP12E HTTP port
ESP12E_TIMEOUT=5                 # Connection timeout

# Motor settings
MOTOR_MAX_SPEED=255              # PWM max (0-255)
MOTOR_SAFETY_TIMEOUT=5000        # 5 second auto-stop timeout

# CORS (for mobile app)
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.x.x:3000

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/jetbot_server.log
```

**Save: Press Ctrl+X, then Y, then Enter**

### 4.3 Create Logs Directory

```bash
# Create logs folder
mkdir -p logs

# Verify
ls -la logs/

# Should be empty initially
```

### 4.4 Validate Configuration

```bash
# Check syntax of all Python files
python3 -m py_compile server_main.py
python3 -m py_compile esp12e_controller.py
python3 -m py_compile jetson_display.py

# Should complete without errors

# Validate JSON config
python3 -c "import json; json.load(open('config.json'))" && echo "✅ Config valid"

# Check .env loading
python3 -c "from dotenv import load_dotenv; load_dotenv('.env'); print('✅ .env loaded')"
```

### 4.5 Test Local Run

```bash
# Start server temporarily (for testing only)
python3 server_main.py

# Should show:
# * Running on http://0.0.0.0:5000
# * Debug mode: off

# Leave it running, open another terminal
```

**In another terminal, test API:**
```bash
# Test health check
curl http://localhost:5000/health

# Should return:
# {"status":"healthy"}

# Press Ctrl+C to stop server
```

---

## Phase 5: Automated Deployment with Systemd (10 minutes)

### 5.1 Make Setup Script Executable

```bash
# Make script executable
chmod +x setup.sh

# Verify permissions
ls -l setup.sh
# Should show: -rwxr-xr-x
```

### 5.2 Run Automated Setup

```bash
# Run setup script
./setup.sh

# Follow the prompts:
# 1. Validate files? (yes)
# 2. Install dependencies? (yes)
# 3. Create systemd services? (yes)

# Script will:
# - Validate Python syntax
# - Check dependencies
# - Create systemd service files
# - Enable services for auto-start
# - Create backups of old files
# - Run verification tests
```

**Expected output:**
```
[✓] Validating files...
[✓] Installing dependencies...
[✓] Creating systemd services...
[✓] Enabling services...
[✓] Running tests...
[✓] Setup complete!
```

### 5.3 Create Systemd Services Manually (if needed)

**If setup.sh doesn't work, create services manually:**

```bash
# Create server service
sudo nano /etc/systemd/system/jetbot-server.service
```

**Paste this content:**
```ini
[Unit]
Description=JetBot OS Server
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson/Jetbot_os
Environment="PATH=/home/jetson/.local/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/jetson/Jetbot_os/.env
ExecStart=/usr/bin/python3 /home/jetson/Jetbot_os/server_main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Create display service
sudo nano /etc/systemd/system/jetbot-display.service
```

**Paste this content:**
```ini
[Unit]
Description=JetBot Display Service
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson/Jetbot_os
Environment="PATH=/home/jetson/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DISPLAY=:0"
EnvironmentFile=/home/jetbot_os/.env
ExecStart=/usr/bin/python3 /home/jetson/Jetbot_os/jetson_display.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Save both files (Ctrl+X, Y, Enter)**

### 5.4 Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services to auto-start on boot
sudo systemctl enable jetbot-server
sudo systemctl enable jetbot-display

# Start services
sudo systemctl start jetbot-server
sudo systemctl start jetbot-display

# Check status
sudo systemctl status jetbot-server
sudo systemctl status jetbot-display
```

**Expected status output:**
```
● jetbot-server.service - JetBot OS Server
   Loaded: loaded (/etc/systemd/system/jetbot-server.service; enabled; ...)
   Active: active (running) since Sun 2025-12-07 18:30:00 IST; 10s ago
```

---

## Phase 6: Verification & Testing (10 minutes)

### 6.1 Check Service Status

```bash
# Check if services are running
sudo systemctl status jetbot-server jetbot-display

# Should show "active (running)"

# Check if services auto-start on boot
sudo systemctl is-enabled jetbot-server
sudo systemctl is-enabled jetbot-display

# Should show "enabled"
```

### 6.2 Test Health Check

```bash
# Test server is responding
curl http://localhost:5000/health

# Should return:
# {"status":"healthy"}
```

### 6.3 Test ESP12E Connection

```bash
# Test connection to ESP12E
curl -X POST http://localhost:5000/api/connection/test \
  -H "Content-Type: application/json"

# Should return:
# {"status":"success","connected":true,"esp12e_ip":"192.168.1.50"}

# If connected=false, check:
# 1. ESP12E_IP in .env file
# 2. ESP12E is powered on and connected to WiFi
# 3. Network connectivity between Jetson and ESP12E
```

### 6.4 Test Motor Forward Command

```bash
# Send motor forward command
curl -X POST http://localhost:5000/api/motor/forward \
  -H "Content-Type: application/json" \
  -d '{"speed":200}'

# Should return:
# {"status":"success","direction":"forward","speed":200}

# Watch motors: They should spin forward at 78% speed

# If motors don't move:
# 1. Check L298N has 12V power
# 2. Verify GPIO connections
# 3. Test directly on ESP12E: curl http://192.168.1.50/api/motor?...
# 4. Check motor wiring to L298N
```

### 6.5 Test Motor Directions

```bash
# Backward
curl -X POST http://localhost:5000/api/motor/backward \
  -H "Content-Type: application/json" \
  -d '{"speed":200}'

# Left
curl -X POST http://localhost:5000/api/motor/left \
  -H "Content-Type: application/json" \
  -d '{"speed":180}'

# Right
curl -X POST http://localhost:5000/api/motor/right \
  -H "Content-Type: application/json" \
  -d '{"speed":180}'

# Stop
curl -X POST http://localhost:5000/api/motor/stop
```

### 6.6 Test Emotion Display

```bash
# Set emotion
curl -X POST http://localhost:5000/api/emotion/happy

# Display should animate to happy face

# Test all emotions:
for emotion in neutral happy sad excited confused angry thinking love skeptical sleeping; do
  curl -X POST http://localhost:5000/api/emotion/$emotion
  sleep 2
done
```

### 6.7 Check System Status

```bash
# Get full system status
curl http://localhost:5000/api/status

# Should return JSON with:
# - Motor status
# - Last command timestamp
# - Motor timeout counter
# - ESP12E connection status
# - Battery voltage (if available)
```

### 6.8 View Logs

```bash
# Check server logs
tail -f logs/jetbot_server.log

# Should show:
# - Startup messages
# - API requests
# - Motor commands
# - Errors (if any)

# Press Ctrl+C to stop
```

### 6.9 Check Systemd Logs

```bash
# View server service logs
sudo journalctl -u jetbot-server -n 50

# View display service logs
sudo journalctl -u jetbot-display -n 50

# Follow logs in real-time
sudo journalctl -u jetbot-server -f
# Press Ctrl+C to stop
```

---

## Phase 7: Battery Monitoring (Optional, 5 minutes)

### 7.1 Test Battery Voltage Reading

```bash
# Check battery voltage from ESP12E
curl http://192.168.1.50/api/sensor/battery

# Should return voltage value (around 12V for full battery)

# Via Jetson server:
curl http://localhost:5000/api/sensor/battery
```

### 7.2 Voltage Monitoring

```bash
# Check status for voltage:
curl http://localhost:5000/api/status | grep battery

# Expected: "battery_voltage": 12.0
```

---

## Phase 8: Test Safety Timeout (5 minutes)

### 8.1 Test Auto-Stop Feature

```bash
# Send forward command
curl -X POST http://localhost:5000/api/motor/forward -d '{"speed":200}'

# Motors should move for 5 seconds then stop automatically
# This is the safety timeout protecting battery and motors

# Verify in logs:
tail -f logs/jetbot_server.log | grep -i timeout
```

---

## Phase 9: System Verification Checklist (5 minutes)

```bash
# Run complete verification
cat > test_system.sh << 'EOF'
#!/bin/bash

echo "🔍 JETBOT OS VERIFICATION TEST"
echo "=================================="

# Test 1: Health check
echo -n "1. Health check... "
if curl -s http://localhost:5000/health | grep -q "healthy"; then
  echo "✅"
else
  echo "❌"
fi

# Test 2: ESP12E connection
echo -n "2. ESP12E connection... "
if curl -s -X POST http://localhost:5000/api/connection/test | grep -q "connected"; then
  echo "✅"
else
  echo "❌"
fi

# Test 3: System status
echo -n "3. System status... "
if curl -s http://localhost:5000/api/status | grep -q "motor_status"; then
  echo "✅"
else
  echo "❌"
fi

# Test 4: Systemd services
echo -n "4. Services running... "
if sudo systemctl is-active --quiet jetbot-server; then
  echo "✅"
else
  echo "❌"
fi

# Test 5: Logs exist
echo -n "5. Logs being written... "
if [ -f logs/jetbot_server.log ]; then
  echo "✅"
else
  echo "❌"
fi

echo "=================================="
echo "Verification complete!"
EOF

chmod +x test_system.sh
./test_system.sh
```

---

## Phase 10: Post-Deployment (Optional, 10 minutes)

### 10.1 Auto-Start Verification

```bash
# Test auto-start by rebooting
sudo reboot

# After reboot, check if services start automatically
sudo systemctl status jetbot-server jetbot-display

# Should show "active (running)"
```

### 10.2 Performance Monitoring

```bash
# Monitor system resources
top

# Press 'q' to quit

# Or check specific process
ps aux | grep python3
```

### 10.3 Enable Remote SSH (Optional)

```bash
# For easier remote management
sudo systemctl status ssh
sudo systemctl enable ssh
sudo systemctl start ssh

# From another computer:
ssh jetson@192.168.x.x
```

---

## ✅ Deployment Complete!

**Summary:**
```
✅ Phase 1: Hardware verified
✅ Phase 2: Repository cloned
✅ Phase 3: Arduino firmware uploaded
✅ Phase 4: Jetson setup completed
✅ Phase 5: Systemd services configured
✅ Phase 6: All systems tested
✅ Phase 7: Battery monitoring (optional)
✅ Phase 8: Safety timeout verified
✅ Phase 9: Final verification passed
✅ Phase 10: System ready for production

Total deployment time: ~45-60 minutes
Status: READY TO USE
```

---

## 🚀 Your JetBot is Now Ready!

**Quick test to confirm everything works:**
```bash
# Forward
curl -X POST http://localhost:5000/api/motor/forward -d '{"speed":200}'

# Check logs
tail -f logs/jetbot_server.log

# View status
curl http://localhost:5000/api/status
```

---

## 📞 Troubleshooting During Deployment

| Phase | Issue | Solution |
|-------|-------|----------|
| 3 | Arduino upload fails | Install CH340 driver, try different USB port |
| 4 | Pip install fails | Update pip: `pip install --upgrade pip` |
| 5 | Systemd service fails | Check user permissions, verify paths in service file |
| 6 | ESP12E unreachable | Ping ESP12E IP, check WiFi connection, verify IP in .env |
| 6 | Motors don't move | Check L298N power, verify GPIO connections |
| 7 | No battery reading | Check ADC pin on ESP12E |
| 8 | Timeout not working | Check motor_safety_timeout in .env |

---

**Version:** 2.0.0  
**Date:** December 7, 2025  
**Status:** DEPLOYMENT GUIDE COMPLETE  
**Next Step:** Follow each phase in order!
