# JetBot OS - API Reference

This document provides comprehensive documentation for the JetBot OS REST API and WebSocket events.

## Table of Contents
- [REST API Endpoints](#rest-api-endpoints)
  - [Motor Control](#motor-control)
  - [Emotion Control](#emotion-control)
  - [Status & Health](#status--health)
  - [Sensor Readings](#sensor-readings)
  - [Connection Testing](#connection-testing)
- [WebSocket Events](#websocket-events)
- [Error Handling](#error-handling)

---

## REST API Endpoints

### Base URL
```
http://<SERVER_IP>:5000
```
Default: `http://localhost:5000`

---

## Motor Control

### Control Motors
Control robot movement in different directions.

**Endpoint:** `POST /api/motor/<direction>`

**Valid Directions:**
- `forward` - Move forward
- `backward` - Move backward
- `left` - Turn left
- `right` - Turn right
- `stop` - Stop all motors

**Request Body:**
```json
{
  "speed": 200
}
```

**Parameters:**
| Parameter | Type | Required | Range | Default | Description |
|-----------|------|----------|-------|---------|-------------|
| speed | integer | No | 0-255 | 200 | Motor speed (PWM value) |

**Response (Success):**
```json
{
  "status": "success",
  "direction": "forward",
  "speed": 200
}
```

**Response (Error - Invalid Direction):**
```json
{
  "status": "error",
  "message": "Invalid direction: backwards",
  "valid": ["forward", "backward", "left", "right", "stop"]
}
```

**Example Usage:**
```bash
# Move forward at speed 200
curl -X POST http://localhost:5000/api/motor/forward \
  -H "Content-Type: application/json" \
  -d '{"speed": 200}'

# Turn left at speed 150
curl -X POST http://localhost:5000/api/motor/left \
  -H "Content-Type: application/json" \
  -d '{"speed": 150}'

# Stop
curl -X POST http://localhost:5000/api/motor/stop
```

---

## Emotion Control

### Set Robot Emotion
Change the robot's facial expression/emotion displayed on screen.

**Endpoint:** `POST /api/emotion/<emotion_name>`

**Valid Emotions:**
- `neutral` - Neutral expression
- `happy` - Happy/smiling
- `sad` - Sad expression
- `excited` - Excited/energetic
- `confused` - Confused expression
- `angry` - Angry expression
- `thinking` - Thinking/pondering
- `love` - Love/heart eyes
- `skeptical` - Skeptical/doubtful
- `sleeping` - Sleeping/tired

**Response (Success):**
```json
{
  "status": "success",
  "emotion": "happy"
}
```

**Response (Error - Invalid Emotion):**
```json
{
  "status": "error",
  "message": "Invalid emotion: happpy",
  "valid_emotions": ["neutral", "happy", "sad", "excited", "confused", "angry", "thinking", "love", "skeptical", "sleeping"]
}
```

**Example Usage:**
```bash
# Set emotion to happy
curl -X POST http://localhost:5000/api/emotion/happy

# Set emotion to thinking
curl -X POST http://localhost:5000/api/emotion/thinking
```

**Notes:**
- Emotion changes are broadcasted to all connected WebSocket clients
- The Jetson display service polls this state every 500ms

---

## Status & Health

### Get System Status
Retrieve complete system status including motor state, emotion, and ESP12E connection.

**Endpoint:** `GET /api/status`

**Response:**
```json
{
  "status": "success",
  "system": {
    "robot_connected": true,
    "motor_running": false,
    "current_emotion": "neutral",
    "esp12e_status": "connected",
    "last_motor_command": {
      "direction": "forward",
      "speed": 200,
      "timestamp": "2025-12-07T15:30:45.123456"
    }
  },
  "esp12e": {
    "connected": true,
    "ip": "192.168.1.50",
    "uptime": 12345,
    "free_heap": 25600
  },
  "timestamp": "2025-12-07T15:30:50.123456"
}
```

**Example Usage:**
```bash
curl http://localhost:5000/api/status
```

### Health Check
Simple endpoint to verify server is running.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy"
}
```

**Example Usage:**
```bash
curl http://localhost:5000/health
```

---

## Connection Testing

### Test ESP12E Connection
Test connectivity to the ESP12E motor controller.

**Endpoint:** `POST /api/connection/test`

**Response (Success):**
```json
{
  "status": "success",
  "connected": true,
  "esp12e_ip": "192.168.1.50"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Motor controller not initialized"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/api/connection/test
```

---

## Sensor Readings

### Read Sensor Data
Read data from various sensors connected to the ESP12E.

**Endpoint:** `GET /api/sensor/<sensor_type>`

**Valid Sensor Types:**
- `distance` - Ultrasonic distance sensor (cm)
- `battery` - Battery voltage (V)
- `temperature` - Temperature sensor (°C)

**Response (Success):**
```json
{
  "status": "success",
  "sensor": "distance",
  "value": 45.2
}
```

**Response (Error - Invalid Sensor):**
```json
{
  "status": "error",
  "message": "Invalid sensor: humidity",
  "valid_sensors": ["distance", "battery", "temperature"]
}
```

**Example Usage:**
```bash
# Read distance sensor
curl http://localhost:5000/api/sensor/distance

# Read battery voltage
curl http://localhost:5000/api/sensor/battery

# Read temperature
curl http://localhost:5000/api/sensor/temperature
```

---

## WebSocket Events

### Connection
WebSocket endpoint: `ws://<SERVER_IP>:5000/socket.io/`

The server uses Socket.IO for WebSocket communication.

### Client → Server Events

#### motor_command
Send motor commands via WebSocket for real-time control.

**Event Name:** `motor_command`

**Payload:**
```json
{
  "direction": "forward",
  "speed": 200
}
```

**Parameters:**
| Parameter | Type | Required | Valid Values | Description |
|-----------|------|----------|--------------|-------------|
| direction | string | Yes | forward, backward, left, right, stop | Motor direction |
| speed | integer | No | 0-255 | Motor speed (default: 200) |

**Example (JavaScript):**
```javascript
const socket = io('http://localhost:5000');

// Send motor command
socket.emit('motor_command', {
  direction: 'forward',
  speed: 180
});
```

### Server → Client Events

#### connect
Fired when client successfully connects to the server.

**Payload:** Current system state
```json
{
  "robot_connected": true,
  "motor_running": false,
  "current_emotion": "neutral",
  "esp12e_status": "connected"
}
```

**Example (JavaScript):**
```javascript
socket.on('connect', () => {
  console.log('Connected to JetBot OS server');
});
```

#### disconnect
Fired when client disconnects from the server.

**Example (JavaScript):**
```javascript
socket.on('disconnect', () => {
  console.log('Disconnected from server');
});
```

#### motor_update
Broadcasted to all clients when a motor command is executed.

**Payload:**
```json
{
  "direction": "forward",
  "speed": 200,
  "status": "success"
}
```

**Example (JavaScript):**
```javascript
socket.on('motor_update', (data) => {
  console.log(`Motor: ${data.direction} @ ${data.speed}`);
});
```

#### emotion_update
Broadcasted to all clients when the robot's emotion changes.

**Payload:**
```json
{
  "emotion": "happy",
  "timestamp": "2025-12-07T15:30:45.123456"
}
```

**Example (JavaScript):**
```javascript
socket.on('emotion_update', (data) => {
  console.log(`Emotion changed to: ${data.emotion}`);
});
```

#### system_state
Sent to client on connection with current system state.

**Payload:**
```json
{
  "robot_connected": true,
  "motor_running": false,
  "current_emotion": "neutral",
  "esp12e_status": "connected",
  "last_motor_command": {
    "direction": "forward",
    "speed": 200,
    "timestamp": "2025-12-07T15:30:45.123456"
  }
}
```

#### error
Sent when an error occurs during WebSocket command processing.

**Payload:**
```json
{
  "message": "Failed to send command"
}
```

**Example (JavaScript):**
```javascript
socket.on('error', (data) => {
  console.error('Error:', data.message);
});
```

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found |
| 500 | Internal Server Error |
| 503 | Service Unavailable (ESP12E not connected) |

### Error Response Format

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Description of the error"
}
```

### Common Errors

#### Motor Controller Not Available
```json
{
  "status": "error",
  "message": "Motor controller not available"
}
```
**Cause:** ESP12E is not connected or not initialized  
**Solution:** Check ESP12E connection and IP configuration

#### Invalid Speed
```json
{
  "status": "error",
  "message": "Speed must be 0-255"
}
```
**Cause:** Speed parameter out of valid range  
**Solution:** Use speed value between 0 and 255

#### Invalid Direction
```json
{
  "status": "error",
  "message": "Invalid direction: backwards",
  "valid": ["forward", "backward", "left", "right", "stop"]
}
```
**Cause:** Invalid motor direction specified  
**Solution:** Use one of the valid directions

#### Failed to Send Command
```json
{
  "status": "error",
  "message": "Failed to send command to ESP12E"
}
```
**Cause:** Communication error with ESP12E  
**Solution:** Verify ESP12E is powered on and connected to WiFi

---

## Complete Example: Mobile App Integration

Here's a complete example of integrating the API into a mobile app:

```javascript
import io from 'socket.io-client';

class JetBotAPI {
  constructor(serverUrl = 'http://192.168.1.101:5000') {
    this.serverUrl = serverUrl;
    this.socket = io(serverUrl);
    this.setupSocketListeners();
  }

  setupSocketListeners() {
    this.socket.on('connect', () => {
      console.log('Connected to JetBot');
    });

    this.socket.on('motor_update', (data) => {
      console.log('Motor:', data.direction, data.speed);
    });

    this.socket.on('emotion_update', (data) => {
      console.log('Emotion:', data.emotion);
    });

    this.socket.on('error', (data) => {
      console.error('Error:', data.message);
    });
  }

  // Motor control via REST API
  async moveMotor(direction, speed = 200) {
    const response = await fetch(`${this.serverUrl}/api/motor/${direction}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed })
    });
    return response.json();
  }

  // Motor control via WebSocket (real-time)
  sendMotorCommand(direction, speed = 200) {
    this.socket.emit('motor_command', { direction, speed });
  }

  // Emotion control
  async setEmotion(emotion) {
    const response = await fetch(`${this.serverUrl}/api/emotion/${emotion}`, {
      method: 'POST'
    });
    return response.json();
  }

  // Get status
  async getStatus() {
    const response = await fetch(`${this.serverUrl}/api/status`);
    return response.json();
  }

  // Read sensor
  async readSensor(sensorType) {
    const response = await fetch(`${this.serverUrl}/api/sensor/${sensorType}`);
    return response.json();
  }

  // Test connection
  async testConnection() {
    const response = await fetch(`${this.serverUrl}/api/connection/test`, {
      method: 'POST'
    });
    return response.json();
  }
}

// Usage
const jetbot = new JetBotAPI('http://192.168.1.101:5000');

// Move forward
await jetbot.moveMotor('forward', 200);

// Set emotion
await jetbot.setEmotion('happy');

// Read distance sensor
const distance = await jetbot.readSensor('distance');
console.log('Distance:', distance.value, 'cm');

// Real-time motor control via WebSocket
jetbot.sendMotorCommand('left', 150);
```

---

## Notes

- **CORS:** The server is configured to accept requests from origins specified in the `ALLOWED_ORIGINS` environment variable
- **Rate Limiting:** Motor commands have a safety timeout (default 5 seconds) to prevent runaway motors
- **Auto-stop:** Motors automatically stop if no command is received within the timeout period
- **Emotion Polling:** The Jetson display service polls for emotion updates every 500ms
- **WebSocket Reconnection:** Clients should implement reconnection logic for reliable operation

---

**Version:** 1.0.0  
**Last Updated:** December 7, 2025
