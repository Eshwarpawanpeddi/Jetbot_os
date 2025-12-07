# 🚀 DEPLOYMENT CHECKLIST - AI Pet Robot System

## Pre-Deployment Phase

### Hardware Verification
- [ ] **Jetson Nano 2GB**
  - [ ] Powers on correctly (green LED)
  - [ ] Can SSH into device
  - [ ] Ethernet/WiFi connected to network
  - [ ] Has 5V/4A power supply connected
  
- [ ] **Laptop Server**
  - [ ] Ubuntu 20.04+ or similar Linux
  - [ ] Python 3.8+ installed
  - [ ] Can ping Jetson Nano
  - [ ] Bluetooth dongle available (if no built-in)

- [ ] **ESP32 DevKit**
  - [ ] Powers on (status LED blinks)
  - [ ] USB cable connects to laptop
  - [ ] Arduino IDE or PlatformIO installed
  - [ ] ESP32 board package installed

- [ ] **Peripherals**
  - [ ] USB Camera working
  - [ ] HDMI Display connected to Jetson
  - [ ] 2x DC Motors connected with wiring
  - [ ] Motor Driver (L298N) configured
  - [ ] Speaker/Audio output available
  - [ ] RGB LEDs connected (optional)
  - [ ] Power supply 12V for motors
  - [ ] Power supply 5V for boards

- [ ] **Mobile Device**
  - [ ] iOS 13+ or Android 6+
  - [ ] Connected to same WiFi as server
  - [ ] Expo app installed (or dev environment ready)

### Network Configuration
- [ ] [ ] Assign static IP to Jetson Nano
  - Current IP: `________________`
  - Expected: `192.168.1.100`
  
- [ ] [ ] Assign static IP to Laptop Server
  - Current IP: `________________`
  - Expected: `192.168.1.101`
  
- [ ] [ ] Test connectivity
  ```bash
  ping 192.168.1.100  # Jetson
  ping 192.168.1.101  # Laptop
  ```
  
- [ ] [ ] Open firewall ports
  ```bash
  sudo ufw allow 5000   # Flask server
  sudo ufw allow 5001   # Jetson video
  sudo ufw allow 4242   # Bluetooth (if needed)
  ```

### Software Installation
- [ ] **Jetson Nano**
  ```bash
  sudo apt update && sudo apt upgrade -y
  sudo apt install python3-pip python3-opencv curl git
  pip3 install opencv-python numpy requests
  ```
  - [ ] OpenCV test passed: `python3 -c "import cv2; print(cv2.__version__)"`
  - [ ] NumPy test passed: `python3 -c "import numpy; print(numpy.__version__)"`

- [ ] **Laptop Server**
  ```bash
  python3 -m venv robot_env
  source robot_env/bin/activate
  pip install -r requirements.txt
  ```
  - [ ] Flask installed: `python3 -c "import flask; print(flask.__version__)"`
  - [ ] SocketIO installed: `python3 -c "import socketio; print(socketio.__version__)"`
  - [ ] OpenCV installed: `python3 -c "import cv2; print(cv2.__version__)"`

- [ ] **ESP32**
  - [ ] Arduino IDE downloaded and installed
  - [ ] ESP32 board package installed
  - [ ] BluetoothSerial library available
  - [ ] USB drivers installed for ESP32

- [ ] **Mobile App**
  ```bash
  npm install -g expo-cli
  npm install
  ```
  - [ ] Expo CLI installed: `expo --version`
  - [ ] Node.js 14+ available: `node --version`

## Configuration Phase

### Update IP Addresses
File: `server_main.py`
```python
class Config:
    JETSON_HOST = "192.168.1.100"  # Change to your Jetson IP
    JETSON_PORT = 5001
```
- [ ] Updated JETSON_HOST
- [ ] Updated JETSON_PORT (if different)

File: `jetson_display.py`
```python
class Config:
    SERVER_HOST = "192.168.1.101"  # Change to your Laptop IP
    SERVER_PORT = 5001
```
- [ ] Updated SERVER_HOST
- [ ] Updated SERVER_PORT (if different)

File: `mobile_app.jsx`
```javascript
const SERVER_HOST = '192.168.1.101';  // Change to your Laptop IP
const SERVER_PORT = 5000;
```
- [ ] Updated SERVER_HOST
- [ ] Updated SERVER_PORT (if different)

File: `config.json`
- [ ] Updated all IP addresses
- [ ] Verified camera settings
- [ ] Checked Bluetooth port (`/dev/rfcomm0` on Linux)
- [ ] Set appropriate FPS and quality settings

### Bluetooth Setup (Linux)
```bash
# 1. Pair ESP32
bluetoothctl
> scan on
> pair <MAC_ADDRESS>
> exit

# 2. Create RFCOMM device
sudo rfcomm bind /dev/rfcomm0 <MAC_ADDRESS> 1

# 3. Verify
ls -la /dev/rfcomm0
```

- [ ] ESP32 Bluetooth MAC address: `__:__:__:__:__:__`
- [ ] RFCOMM device created: `/dev/rfcomm0`
- [ ] Device accessible: `cat /dev/rfcomm0` (test with timeout)

### Camera Setup
```bash
# Test camera
v4l2-ctl --list-devices
fswebcam test.jpg
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

- [ ] Camera detected and working
- [ ] Camera index: `0` (or adjust if different)
- [ ] Resolution supported: `640x480`
- [ ] FPS capability: `30 FPS`

## Hardware Testing Phase

### Component Testing

**Jetson Nano Camera & Display**
```bash
ssh jetson@192.168.1.100
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
cv2.namedWindow('Test')
for _ in range(30):
    ret, frame = cap.read()
    cv2.imshow('Test', frame)
    cv2.waitKey(1)
cv2.destroyAllWindows()
cap.release()
print('Camera OK')
"
```
- [ ] Camera shows live video
- [ ] Frame rate adequate (no lag)
- [ ] No dropped frames

**ESP32 Motor Control** (via Arduino Serial Monitor)
```
baud: 115200

Commands:
  test_motor        - Test both motors
  motor 50 50       - Move forward at 50% speed
  motor -50 -50     - Move backward at 50% speed
  motor 50 -50      - Turn right
  motor -50 50      - Turn left
  motor 0 0         - Stop
  test_led          - Test LED colors
  test_audio        - Test speaker tone
  status            - Show system status
```

- [ ] Motors respond to commands
- [ ] Forward/backward movement works
- [ ] Turning works (left/right)
- [ ] Stop command works
- [ ] LED colors cycle through RGB
- [ ] Audio output produces sound
- [ ] Status shows uptime

**Bluetooth Stability** (5 minute test)
```bash
python3 -c "
import serial
import time
port = serial.Serial('/dev/rfcomm0', 115200, timeout=1)
for i in range(60):
    port.write(bytes([0xFF, 0x00]))  # Heartbeat
    time.sleep(5)
    print(f'Heartbeat {i+1}')
port.close()
"
```
- [ ] No disconnections during 5-minute test
- [ ] Heartbeat received consistently
- [ ] No timeout errors

## Deployment Phase

### Start Services in Order

**1. Laptop Server (First)**
```bash
cd /path/to/robot_server
source robot_env/bin/activate
python3 server_main.py
```

Expected output:
```
============================================================
AI PET ROBOT SERVER - INITIALIZING
============================================================
[timestamp] - __main__ - INFO - ✓ Bluetooth initialized
[timestamp] - __main__ - INFO - ✓ Jetson Nano connection established
[timestamp] - __main__ - INFO - ✓ Display engine started
============================================================
SYSTEM READY
============================================================
 * Running on http://0.0.0.0:5000
```

- [ ] Server starts without errors
- [ ] Bluetooth initialized ✓
- [ ] Display engine started ✓
- [ ] Listening on port 5000
- [ ] No error messages in logs

**2. Jetson Nano (Second)**
```bash
ssh jetson@192.168.1.100
cd /home/jetson
python3 jetson_display.py
```

Expected output:
```
============================================================
JETSON NANO - INITIALIZING
============================================================
✓ Camera initialized
✓ Server connection established
✓ Camera capture thread started
✓ Display update thread started
✓ Connection monitor started
============================================================
JETSON NANO READY
============================================================
```

- [ ] Jetson connects to server
- [ ] Camera thread starts
- [ ] Display window opens
- [ ] No connection errors
- [ ] HDMI display shows content

**3. ESP32 Firmware (Third)**
- [ ] Arduino IDE: Open `esp32_motor_control.ino`
- [ ] Select board: Tools > Board > ESP32 Dev Module
- [ ] Select port: Tools > Port > /dev/ttyUSB0
- [ ] Click Upload
- [ ] Monitor shows: "ESP32 Ready"

**4. Mobile App (Fourth)**
```bash
cd mobile_app
npm install
expo start
```

- [ ] Expo starts and shows QR code
- [ ] Scan QR with phone (Expo app)
- [ ] App loads on mobile device
- [ ] WebSocket connects to server
- [ ] "Connected" indicator shows green

### Verify All Connections

**Server Dashboard (check logs)**
```
Connected Devices:
  - Jetson Nano: ✓
  - ESP32: ✓
  - Mobile App: ✓
  - Camera: ✓
```

- [ ] Server log shows: `✓ Connected to Jetson Nano`
- [ ] Server log shows: `✓ Bluetooth connected`
- [ ] Mobile app shows: "✅ Connected"
- [ ] HDMI display updates (face animation visible)

## Functional Testing Phase

### Voice Command Test
```
1. Open mobile app
2. Click 🎤 Voice Command
3. Say: "move forward"
4. Observe:
   - Face changes emotion (excited)
   - Motors move forward
   - Server logs command processed
5. Repeat with: "turn left", "turn right", "stop", "be happy"
```

- [ ] Voice recording works
- [ ] Commands recognized
- [ ] Appropriate motor response
- [ ] Face emotion updates
- [ ] No crashes or errors

### Manual Control Test
```
1. Mobile app > Manual mode
2. Click Up Arrow
3. Observe:
   - Motors move forward
   - Speed indicator shows values
4. Click Down, Left, Right, Stop
5. Check all directions work
```

- [ ] Direction pad responds
- [ ] Motors match direction
- [ ] Speed indicator updates
- [ ] Smooth acceleration
- [ ] No lag or stuttering

### Emotion Test
```
1. Click Happy 😊
2. Face displays happy expression
3. Repeat for: Sad, Excited, Neutral, Confused
4. Each emotion should show distinct features
```

- [ ] Emotion changes reflected on display
- [ ] Face animations smooth
- [ ] No display glitches
- [ ] Emotions distinct and clear

### Display Mode Test
```
1. Click 📝 List (shopping list)
2. Display shows text content
3. Click 😊 Face (face display)
4. Face displays again
5. Click 📐 Formula
6. Display shows formula with formatting
```

- [ ] Text displays correctly
- [ ] Text wraps properly
- [ ] Face mode restores
- [ ] No display corruption
- [ ] Smooth transitions

### Video Latency Test
```
1. Place hand in front of Jetson camera
2. Observe latency to HDMI display
3. Expected: <200ms (nearly instant)
4. Check mobile app display latency
5. Expected: <500ms (perceptible but acceptable)
```

- [ ] HDMI latency acceptable (<200ms)
- [ ] Mobile app latency acceptable (<500ms)
- [ ] No frame drops
- [ ] Consistent frame rate

### Extended Runtime Test (1 hour)
```
Cycle through operations:
- Send voice commands every 30 seconds
- Alternate manual control with automatic
- Change emotions periodically
- Switch display modes
Monitor:
- CPU usage (should stay <40%)
- Memory usage (should stay <512MB)
- Temperature (should stay <70°C)
- No crashes or disconnects
```

- [ ] Server stable for 1 hour
- [ ] No memory leaks
- [ ] No CPU spikes
- [ ] No Bluetooth disconnects
- [ ] No camera freezes

## Post-Deployment Phase

### Documentation & Backup
- [ ] Backup `config.json`
- [ ] Backup all modified files
- [ ] Document your IP addresses
- [ ] Document any customizations
- [ ] Create system snapshot

### Performance Baseline
Document initial performance:
- [ ] Average latency: `_____ms`
- [ ] CPU usage: `_____%`
- [ ] Memory usage: `____MB`
- [ ] Bandwidth: `____Mbps`
- [ ] FPS achieved: `____`

### Auto-Start Configuration (Optional)
```bash
# Create systemd service for server
sudo nano /etc/systemd/system/robot-server.service

[Unit]
Description=AI Pet Robot Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/robot
ExecStart=/path/to/robot_env/bin/python3 server_main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target

# Enable
sudo systemctl daemon-reload
sudo systemctl enable robot-server
sudo systemctl start robot-server
```

- [ ] Created systemd service
- [ ] Service starts on boot
- [ ] Can stop/restart service
- [ ] Logs accessible

### Monitoring Setup
```bash
# Monitor resource usage
watch -n 1 'ps aux | grep server_main'

# Monitor network
iftop -i eth0

# Monitor Bluetooth
bluetoothctl info <ESP32_MAC>
```

- [ ] Set up monitoring tools
- [ ] Know how to check system health
- [ ] Can interpret resource metrics

## Troubleshooting Quick Reference

| Issue | Solution | Status |
|-------|----------|--------|
| Jetson can't connect | Check IP, firewall, ping | [ ] |
| Bluetooth unstable | Re-pair, check range | [ ] |
| Camera not detected | Check USB, permissions | [ ] |
| Motors not responding | Check power, firmware | [ ] |
| High latency | Reduce video quality | [ ] |
| Memory leak | Restart server | [ ] |
| Display frozen | Check HDMI cable | [ ] |

## Final Checklist

- [ ] All components connected and powered
- [ ] All IP addresses configured correctly
- [ ] All services start without errors
- [ ] All four components connected to server
- [ ] Voice commands working end-to-end
- [ ] Manual control working
- [ ] Emotions updating correctly
- [ ] Display modes switching properly
- [ ] Motor responses under 500ms
- [ ] No crashes during 1-hour test
- [ ] Documentation and backups complete
- [ ] Performance baseline recorded
- [ ] Monitoring tools operational

## Sign-Off

**Deployment Date**: `________________`

**Deployed By**: `________________`

**System Status**: 
- [ ] Development
- [ ] Testing
- [ ] Production Ready

**Notes**:
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

**Next Review Date**: `________________`

---

**Version**: 1.0.0  
**Last Updated**: December 7, 2024