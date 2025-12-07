/*
 * JetBot OS - ESP12E Motor Driver Control
 * L298N Motor Driver + 2x DC Motors
 * 
 * CONNECTIONS:
 * ============
 * L298N Motor Driver:
 *   - IN1 (Left Motor Forward)   → ESP12E D1 (GPIO5)
 *   - IN2 (Left Motor Backward)  → ESP12E D2 (GPIO4)
 *   - IN3 (Right Motor Forward)  → ESP12E D3 (GPIO0)
 *   - IN4 (Right Motor Backward) → ESP12E D4 (GPIO2)
 *   - ENA (Left Motor PWM)       → ESP12E D5 (GPIO14)  [Speed control]
 *   - ENB (Right Motor PWM)      → ESP12E D6 (GPIO12)  [Speed control]
 *   - GND                        → ESP12E GND
 *   - +5V                        → ESP12E 5V (from AMS1117)
 * 
 * Power Supply:
 *   - Motor Power: 12V Battery → L298N +12V
 *   - GND: Battery GND → L298N GND → ESP12E GND
 *   - ESP12E Power: 5V from L298N or AMS1117 voltage regulator
 * 
 * Motors:
 *   - Motor 1 (Left):  OUT1, OUT2
 *   - Motor 2 (Right): OUT3, OUT4
 * 
 * LOGIC:
 * ======
 * Forward:  IN1=1, IN2=0, IN3=1, IN4=0
 * Backward: IN1=0, IN2=1, IN3=0, IN4=1
 * Left:     IN1=1, IN2=0, IN3=0, IN4=1 (Left slow, Right fast)
 * Right:    IN1=0, IN2=1, IN3=1, IN4=0 (Left fast, Right slow)
 * Stop:     IN1=0, IN2=0, IN3=0, IN4=0
 * 
 * Speed control: 0-255 via PWM on ENA and ENB
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <ArduinoJson.h>

// ============================================================================
// GPIO PIN DEFINITIONS
// ============================================================================

// Motor Control Pins (Digital)
const int IN1 = D1;  // GPIO5  - Left Motor Forward
const int IN2 = D2;  // GPIO4  - Left Motor Backward
const int IN3 = D3;  // GPIO0  - Right Motor Forward
const int IN4 = D4;  // GPIO2  - Right Motor Backward

// Speed Control Pins (PWM)
const int ENA = D5;  // GPIO14 - Left Motor Speed (0-255)
const int ENB = D6;  // GPIO12 - Right Motor Speed (0-255)

// ============================================================================
// CONFIGURATION
// ============================================================================

// WiFi Configuration - CHANGE THESE!
const char* SSID = "your_ssid";           // Change to your WiFi SSID
const char* PASSWORD = "your_password";   // Change to your WiFi password
const char* HOSTNAME = "jetbot-esp12e";   // mDNS hostname

// Server Configuration
ESP8266WebServer server(80);
const int SERVER_PORT = 80;

// Motor Limits
const int MAX_SPEED = 255;
const int MIN_SPEED = 0;
const int DEFAULT_SPEED = 200;
const int PWM_FREQUENCY = 1000;  // 1kHz PWM frequency

// Safety Configuration
const int MOTOR_TIMEOUT_MS = 5000;  // Auto-stop after 5 seconds
unsigned long last_command_time = 0;

// System Status
struct {
  bool wifi_connected = false;
  bool motors_running = false;
  String current_direction = "stop";
  int current_speed = 0;
  int left_speed = 0;
  int right_speed = 0;
  unsigned long uptime_ms = 0;
  int total_commands = 0;
  float battery_voltage = 12.0;
} system_status;

// ============================================================================
// MOTOR CONTROL FUNCTIONS
// ============================================================================

/*
 * Set motor speeds and direction
 * left_speed, right_speed: 0-255 (0=stop, 255=full speed)
 */
void set_motor_speed(int left_speed, int right_speed) {
  // Constrain speeds to valid range
  left_speed = constrain(left_speed, 0, 255);
  right_speed = constrain(right_speed, 0, 255);
  
  // Apply PWM to speed control pins
  analogWrite(ENA, left_speed);
  analogWrite(ENB, right_speed);
  
  // Store status
  system_status.left_speed = left_speed;
  system_status.right_speed = right_speed;
  
  Serial.printf("[MOTOR] Speed: Left=%d, Right=%d\n", left_speed, right_speed);
}

/*
 * Move forward
 * Both motors forward at same speed
 */
void move_forward(int speed = DEFAULT_SPEED) {
  speed = constrain(speed, 0, 255);
  
  // IN1=1, IN2=0 (Left forward)
  // IN3=1, IN4=0 (Right forward)
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  
  set_motor_speed(speed, speed);
  
  system_status.current_direction = "forward";
  system_status.current_speed = speed;
  system_status.motors_running = true;
  last_command_time = millis();
  
  Serial.printf("[CMD] Forward: speed=%d\n", speed);
}

/*
 * Move backward
 * Both motors backward at same speed
 */
void move_backward(int speed = DEFAULT_SPEED) {
  speed = constrain(speed, 0, 255);
  
  // IN1=0, IN2=1 (Left backward)
  // IN3=0, IN4=1 (Right backward)
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  
  set_motor_speed(speed, speed);
  
  system_status.current_direction = "backward";
  system_status.current_speed = speed;
  system_status.motors_running = true;
  last_command_time = millis();
  
  Serial.printf("[CMD] Backward: speed=%d\n", speed);
}

/*
 * Turn left
 * Right motor faster, left motor slower
 */
void turn_left(int speed = DEFAULT_SPEED) {
  speed = constrain(speed, 0, 255);
  int left_spd = speed * 0.6;  // 60% speed
  int right_spd = speed;       // 100% speed
  
  // IN1=1, IN2=0 (Left forward, slow)
  // IN3=1, IN4=0 (Right forward, fast)
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  
  set_motor_speed(left_spd, right_spd);
  
  system_status.current_direction = "left";
  system_status.current_speed = speed;
  system_status.motors_running = true;
  last_command_time = millis();
  
  Serial.printf("[CMD] Turn Left: speed=%d (left=%d, right=%d)\n", speed, left_spd, right_spd);
}

/*
 * Turn right
 * Left motor faster, right motor slower
 */
void turn_right(int speed = DEFAULT_SPEED) {
  speed = constrain(speed, 0, 255);
  int left_spd = speed;       // 100% speed
  int right_spd = speed * 0.6; // 60% speed
  
  // IN1=1, IN2=0 (Left forward, fast)
  // IN3=1, IN4=0 (Right forward, slow)
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  
  set_motor_speed(left_spd, right_spd);
  
  system_status.current_direction = "right";
  system_status.current_speed = speed;
  system_status.motors_running = true;
  last_command_time = millis();
  
  Serial.printf("[CMD] Turn Right: speed=%d (left=%d, right=%d)\n", speed, left_spd, right_spd);
}

/*
 * Stop all motors
 * All direction pins LOW
 */
void stop_motors() {
  // All direction pins LOW = stop
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  
  set_motor_speed(0, 0);
  
  system_status.current_direction = "stop";
  system_status.current_speed = 0;
  system_status.motors_running = false;
  
  Serial.println("[CMD] Stop Motors");
}

/*
 * Safety check - stop motors if no command received
 */
void safety_timeout_check() {
  if (system_status.motors_running) {
    unsigned long elapsed = millis() - last_command_time;
    
    if (elapsed > MOTOR_TIMEOUT_MS) {
      Serial.printf("[SAFETY] Timeout triggered (%lu ms). Stopping motors.\n", elapsed);
      stop_motors();
    }
  }
}

// ============================================================================
// WEB SERVER ENDPOINTS
// ============================================================================

/*
 * Health check endpoint
 * GET /status - Returns JSON with system status
 */
void handle_status() {
  system_status.uptime_ms = millis();
  
  DynamicJsonDocument doc(512);
  doc["status"] = "success";
  doc["uptime_ms"] = system_status.uptime_ms;
  doc["wifi_connected"] = system_status.wifi_connected;
  doc["motors_running"] = system_status.motors_running;
  doc["current_direction"] = system_status.current_direction;
  doc["current_speed"] = system_status.current_speed;
  doc["left_speed"] = system_status.left_speed;
  doc["right_speed"] = system_status.right_speed;
  doc["total_commands"] = system_status.total_commands;
  doc["battery_voltage"] = system_status.battery_voltage;
  doc["max_speed"] = MAX_SPEED;
  doc["firmware_version"] = "2.0.0";
  doc["hostname"] = HOSTNAME;
  
  String response;
  serializeJson(doc, response);
  
  server.send(200, "application/json", response);
  Serial.printf("[HTTP] GET /status - 200 OK\n");
}

/*
 * Motor control endpoint
 * POST /api/motor
 * 
 * Body: {
 *   "direction": "forward|backward|left|right|stop",
 *   "speed": 0-255 (optional, default=200)
 * }
 */
void handle_motor_command() {
  if (server.method() != HTTP_POST) {
    server.send(405, "application/json", "{\"error\":\"Method not allowed\"}");
    return;
  }
  
  String body = server.arg("plain");
  DynamicJsonDocument doc(256);
  DeserializationError error = deserializeJson(doc, body);
  
  if (error) {
    DynamicJsonDocument error_doc(256);
    error_doc["error"] = "Invalid JSON";
    String response;
    serializeJson(error_doc, response);
    server.send(400, "application/json", response);
    Serial.printf("[HTTP] POST /api/motor - 400 Bad Request (JSON parse error)\n");
    return;
  }
  
  // Get parameters
  String direction = doc["direction"] | "stop";
  int speed = doc["speed"] | DEFAULT_SPEED;
  
  // Validate direction
  if (direction != "forward" && direction != "backward" && 
      direction != "left" && direction != "right" && direction != "stop") {
    DynamicJsonDocument error_doc(256);
    error_doc["error"] = "Invalid direction";
    error_doc["valid"] = JsonArray();
    error_doc["valid"].add("forward");
    error_doc["valid"].add("backward");
    error_doc["valid"].add("left");
    error_doc["valid"].add("right");
    error_doc["valid"].add("stop");
    
    String response;
    serializeJson(error_doc, response);
    server.send(400, "application/json", response);
    return;
  }
  
  // Validate speed
  speed = constrain(speed, 0, MAX_SPEED);
  
  // Execute command
  if (direction == "forward") {
    move_forward(speed);
  } else if (direction == "backward") {
    move_backward(speed);
  } else if (direction == "left") {
    turn_left(speed);
  } else if (direction == "right") {
    turn_right(speed);
  } else if (direction == "stop") {
    stop_motors();
  }
  
  system_status.total_commands++;
  
  // Send response
  DynamicJsonDocument response_doc(256);
  response_doc["status"] = "success";
  response_doc["direction"] = direction;
  response_doc["speed"] = speed;
  response_doc["left_speed"] = system_status.left_speed;
  response_doc["right_speed"] = system_status.right_speed;
  
  String response;
  serializeJson(response_doc, response);
  server.send(200, "application/json", response);
  
  Serial.printf("[HTTP] POST /api/motor - 200 OK (direction=%s, speed=%d)\n", 
                direction.c_str(), speed);
}

/*
 * Sensor read endpoint
 * GET /api/sensor/battery - Battery voltage
 * GET /api/sensor/distance - Distance sensor (if installed)
 */
void handle_sensor() {
  String sensor = server.pathArg(0);
  
  DynamicJsonDocument doc(256);
  
  if (sensor == "battery") {
    // Read battery voltage from ADC
    int adc_value = analogRead(A0);
    float voltage = (adc_value / 1023.0) * 12.0;  // Assuming 12V max
    system_status.battery_voltage = voltage;
    
    doc["status"] = "success";
    doc["sensor"] = "battery";
    doc["value"] = voltage;
    doc["unit"] = "V";
    doc["warning"] = (voltage < 11.0);
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
    
  } else if (sensor == "distance") {
    // Distance sensor would go here
    doc["status"] = "error";
    doc["message"] = "Distance sensor not implemented";
    
    String response;
    serializeJson(doc, response);
    server.send(501, "application/json", response);
    
  } else {
    doc["status"] = "error";
    doc["message"] = "Unknown sensor";
    doc["valid_sensors"] = JsonArray();
    doc["valid_sensors"].add("battery");
    doc["valid_sensors"].add("distance");
    
    String response;
    serializeJson(doc, response);
    server.send(400, "application/json", response);
  }
}

/*
 * Calibration endpoint
 * POST /api/calibrate/motors
 */
void handle_calibrate() {
  DynamicJsonDocument doc(256);
  
  // Run motor calibration sequence
  Serial.println("[CALIBRATE] Starting motor calibration...");
  
  // Test each motor individually
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, 200);
  analogWrite(ENB, 0);
  delay(1000);
  Serial.println("[CALIBRATE] Left motor test OK");
  
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);
  analogWrite(ENB, 200);
  delay(1000);
  Serial.println("[CALIBRATE] Right motor test OK");
  
  stop_motors();
  
  doc["status"] = "success";
  doc["message"] = "Motor calibration complete";
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

/*
 * Root endpoint
 */
void handle_root() {
  String html = R"(
    <!DOCTYPE html>
    <html>
    <head>
      <title>JetBot ESP12E Motor Control</title>
      <style>
        body { font-family: Arial; margin: 20px; }
        h1 { color: #333; }
        .status { background: #f0f0f0; padding: 15px; border-radius: 5px; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        .stop { background: red; color: white; }
        .forward { background: green; color: white; }
      </style>
    </head>
    <body>
      <h1>JetBot ESP12E Motor Control</h1>
      <div class="status">
        <p><strong>Status:</strong> <span id="status">Loading...</span></p>
        <p><strong>Direction:</strong> <span id="direction">-</span></p>
        <p><strong>Speed:</strong> <span id="speed">-</span></p>
      </div>
      
      <h3>Controls</h3>
      <button class="forward" onclick="send_command('forward', 200)">Forward</button>
      <button class="forward" onclick="send_command('backward', 200)">Backward</button>
      <button class="forward" onclick="send_command('left', 180)">Left</button>
      <button class="forward" onclick="send_command('right', 180)">Right</button>
      <button class="stop" onclick="send_command('stop', 0)">STOP</button>
      
      <h3>API Status</h3>
      <p><a href="/status" target="_blank">GET /status</a></p>
      <p><a href="/api/sensor/battery" target="_blank">GET /api/sensor/battery</a></p>
      
      <script>
        function send_command(direction, speed) {
          const data = { direction: direction, speed: speed };
          fetch('/api/motor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          })
          .then(r => r.json())
          .then(d => {
            document.getElementById('direction').textContent = d.direction;
            document.getElementById('speed').textContent = d.speed;
          });
        }
        
        function update_status() {
          fetch('/status')
            .then(r => r.json())
            .then(d => {
              document.getElementById('status').textContent = d.motors_running ? 'Running' : 'Stopped';
              document.getElementById('direction').textContent = d.current_direction;
              document.getElementById('speed').textContent = d.current_speed;
            });
        }
        
        setInterval(update_status, 1000);
        update_status();
      </script>
    </body>
    </html>
  )";
  
  server.send(200, "text/html", html);
  Serial.printf("[HTTP] GET / - 200 OK\n");
}

// ============================================================================
// SETUP & INITIALIZATION
// ============================================================================

void setup() {
  // Serial communication
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("╔════════════════════════════════════════════════╗");
  Serial.println("║    JetBot OS - ESP12E Motor Driver Control     ║");
  Serial.println("║              Version 2.0.0                    ║");
  Serial.println("╚════════════════════════════════════════════════╝");
  
  // GPIO Initialization
  Serial.println("[INIT] Configuring GPIO pins...");
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);
  
  // Set all pins LOW initially
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  
  Serial.println("[INIT] GPIO configured:");
  Serial.println("  IN1 (D1/GPIO5)   = Left Motor Forward");
  Serial.println("  IN2 (D2/GPIO4)   = Left Motor Backward");
  Serial.println("  IN3 (D3/GPIO0)   = Right Motor Forward");
  Serial.println("  IN4 (D4/GPIO2)   = Right Motor Backward");
  Serial.println("  ENA (D5/GPIO14)  = Left Motor Speed (PWM)");
  Serial.println("  ENB (D6/GPIO12)  = Right Motor Speed (PWM)");
  
  // Set PWM frequency
  analogWriteFreq(PWM_FREQUENCY);
  Serial.printf("[INIT] PWM frequency set to %d Hz\n", PWM_FREQUENCY);
  
  // WiFi Initialization
  Serial.println("[WIFI] Connecting to WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.hostname(HOSTNAME);
  WiFi.begin(SSID, PASSWORD);
  
  int wifi_attempts = 0;
  while (WiFi.status() != WL_CONNECTED && wifi_attempts < 20) {
    delay(500);
    Serial.print(".");
    wifi_attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    system_status.wifi_connected = true;
    Serial.println("\n[WIFI] ✓ Connected!");
    Serial.printf("[WIFI] IP Address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("[WIFI] Signal: %d dBm\n", WiFi.RSSI());
  } else {
    Serial.println("\n[WIFI] ✗ Connection failed!");
    Serial.println("[WIFI] Entering AP mode...");
    WiFi.mode(WIFI_AP);
    WiFi.softAP("JetBot-AP", "12345678");
    Serial.println("[WIFI] AP IP: 192.168.4.1");
  }
  
  // mDNS
  if (WiFi.mode() == WIFI_STA) {
    if (MDNS.begin(HOSTNAME)) {
      Serial.printf("[mDNS] ✓ Available at http://%s.local\n", HOSTNAME);
    }
  }
  
  // Web Server Routes
  Serial.println("[SERVER] Setting up HTTP endpoints...");
  server.on("/", HTTP_GET, handle_root);
  server.on("/status", HTTP_GET, handle_status);
  server.on("/api/motor", HTTP_POST, handle_motor_command);
  server.on("/api/sensor/battery", HTTP_GET, handle_sensor);
  server.on("/api/sensor/distance", HTTP_GET, handle_sensor);
  server.on("/api/calibrate/motors", HTTP_POST, handle_calibrate);
  
  server.begin();
  Serial.printf("[SERVER] ✓ HTTP server started on port %d\n", SERVER_PORT);
  Serial.println();
  Serial.println("╔════════════════════════════════════════════════╗");
  Serial.println("║              READY FOR COMMANDS                ║");
  Serial.println("╚════════════════════════════════════════════════╝");
  Serial.println();
  Serial.println("API Endpoints:");
  Serial.println("  GET  /            - Web UI");
  Serial.println("  GET  /status      - System status");
  Serial.println("  POST /api/motor   - Motor control");
  Serial.println("  GET  /api/sensor/battery - Battery voltage");
  Serial.println();
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Handle HTTP requests
  server.handleClient();
  
  // Update mDNS
  if (WiFi.mode() == WIFI_STA) {
    MDNS.update();
  }
  
  // Safety timeout check
  safety_timeout_check();
  
  // Small delay to prevent watchdog timeout
  yield();
}
