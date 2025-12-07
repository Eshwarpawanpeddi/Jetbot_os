/*
 * JetBot OS - ESP12E Motor Controller
 * 
 * Hardware:
 * - ESP12E WiFi Module
 * - Motor Driver Module (e.g., L298N)
 * - 2x DC Motors
 * 
 * Connections:
 * ESP12E GPIO5  → Motor Driver IN1 (Left Motor Forward)
 * ESP12E GPIO4  → Motor Driver IN2 (Left Motor Backward)
 * ESP12E GPIO0  → Motor Driver IN3 (Right Motor Forward)
 * ESP12E GPIO2  → Motor Driver IN4 (Right Motor Backward)
 * 
 * Power: External 12V supply for motors
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>

// WiFi Configuration
const char* SSID = "your_ssid";
const char* PASSWORD = "your_password";
const int SERVER_PORT = 80;

// Motor Pins
const int LEFT_FWD = 5;   // GPIO5 - D1
const int LEFT_BWD = 4;   // GPIO4 - D2
const int RIGHT_FWD = 0;  // GPIO0 - D3
const int RIGHT_BWD = 2;  // GPIO2 - D4

// Create web server instance
ESP8266WebServer server(SERVER_PORT);

// System variables
bool motors_enabled = true;
uint8_t current_speed = 255;
unsigned long motor_timeout = 0;
const unsigned long MOTOR_SAFETY_TIMEOUT = 5000; // 5 seconds

// ============================================================================
// MOTOR CONTROL FUNCTIONS
// ============================================================================

void setup_motors() {
  pinMode(LEFT_FWD, OUTPUT);
  pinMode(LEFT_BWD, OUTPUT);
  pinMode(RIGHT_FWD, OUTPUT);
  pinMode(RIGHT_BWD, OUTPUT);
  
  // All motors off initially
  stop_motors();
}

void stop_motors() {
  digitalWrite(LEFT_FWD, LOW);
  digitalWrite(LEFT_BWD, LOW);
  digitalWrite(RIGHT_FWD, LOW);
  digitalWrite(RIGHT_BWD, LOW);
  motor_timeout = 0;
  Serial.println("[MOTOR] All motors stopped");
}

void move_forward(uint8_t speed) {
  if (!motors_enabled) return;
  
  analogWrite(LEFT_FWD, speed);
  digitalWrite(LEFT_BWD, LOW);
  analogWrite(RIGHT_FWD, speed);
  digitalWrite(RIGHT_BWD, LOW);
  
  motor_timeout = millis() + MOTOR_SAFETY_TIMEOUT;
  Serial.printf("[MOTOR] Forward: speed=%d\n", speed);
}

void move_backward(uint8_t speed) {
  if (!motors_enabled) return;
  
  digitalWrite(LEFT_FWD, LOW);
  analogWrite(LEFT_BWD, speed);
  digitalWrite(RIGHT_FWD, LOW);
  analogWrite(RIGHT_BWD, speed);
  
  motor_timeout = millis() + MOTOR_SAFETY_TIMEOUT;
  Serial.printf("[MOTOR] Backward: speed=%d\n", speed);
}

void turn_left(uint8_t speed) {
  if (!motors_enabled) return;
  
  // Right motor forward, left motor slower/backward
  analogWrite(RIGHT_FWD, speed);
  digitalWrite(RIGHT_BWD, LOW);
  analogWrite(LEFT_BWD, speed / 2);  // Slower left turn
  digitalWrite(LEFT_FWD, LOW);
  
  motor_timeout = millis() + MOTOR_SAFETY_TIMEOUT;
  Serial.printf("[MOTOR] Left: speed=%d\n", speed);
}

void turn_right(uint8_t speed) {
  if (!motors_enabled) return;
  
  // Left motor forward, right motor slower/backward
  analogWrite(LEFT_FWD, speed);
  digitalWrite(LEFT_BWD, LOW);
  analogWrite(RIGHT_BWD, speed / 2);  // Slower right turn
  digitalWrite(RIGHT_FWD, LOW);
  
  motor_timeout = millis() + MOTOR_SAFETY_TIMEOUT;
  Serial.printf("[MOTOR] Right: speed=%d\n", speed);
}

// ============================================================================
// WEB SERVER HANDLERS
// ============================================================================

void handle_motor_command() {
  // Parse JSON body
  String body = server.arg("plain");
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, body);
  
  if (error) {
    server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }
  
  String action = doc["action"] | "motor";
  String direction = doc["direction"] | "stop";
  uint8_t speed = doc["speed"] | 255;
  unsigned long duration = doc["duration"] | 0;
  
  // Limit speed
  speed = min((uint8_t)255, max((uint8_t)0, speed));
  
  // Execute motor command
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
  } else {
    server.send(400, "application/json", "{\"error\":\"Unknown direction\"}");
    return;
  }
  
  // If duration specified, set timeout
  if (duration > 0) {
    motor_timeout = millis() + duration;
  }
  
  // Send success response
  StaticJsonDocument<100> response;
  response["status"] = "success";
  response["direction"] = direction;
  response["speed"] = speed;
  
  String responseBody;
  serializeJson(response, responseBody);
  server.send(200, "application/json", responseBody);
}

void handle_status() {
  StaticJsonDocument<300> doc;
  doc["status"] = "connected";
  doc["ip"] = WiFi.localIP().toString();
  doc["ssid"] = WiFi.SSID();
  doc["rssi"] = WiFi.RSSI();
  doc["motors_enabled"] = motors_enabled;
  doc["uptime_ms"] = millis();
  doc["free_heap"] = ESP.getFreeHeap();
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handle_sensor_read() {
  String sensor = server.pathArg(0);
  StaticJsonDocument<100> doc;
  
  if (sensor == "battery") {
    // Read analog pin for battery voltage
    uint16_t adc_value = analogRead(A0);
    float voltage = (adc_value / 1023.0) * 3.3 * (4.0 / 1.0); // Voltage divider
    doc["value"] = voltage;
  } else if (sensor == "distance") {
    // Placeholder for distance sensor
    doc["value"] = 0;
  } else if (sensor == "temperature") {
    // Placeholder for temperature sensor
    doc["value"] = 25;
  } else {
    server.send(400, "application/json", "{\"error\":\"Unknown sensor\"}");
    return;
  }
  
  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handle_not_found() {
  server.send(404, "application/json", "{\"error\":\"Not Found\"}");
}

// ============================================================================
// SETUP & LOOP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("  JetBot OS - ESP12E Motor Controller");
  Serial.println("========================================");
  
  // Setup motors
  setup_motors();
  Serial.println("[SETUP] Motors initialized");
  
  // Connect to WiFi
  Serial.printf("[WIFI] Connecting to %s\n", SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WIFI] Failed to connect!");
  }
  
  // Setup web server routes
  server.on("/api/motor", HTTP_POST, handle_motor_command);
  server.on("/status", HTTP_GET, handle_status);
  server.on("/api/sensor", HTTP_GET, handle_sensor_read);
  server.onNotFound(handle_not_found);
  
  server.begin();
  Serial.printf("[SERVER] Web server started on port %d\n", SERVER_PORT);
  Serial.println("========================================\n");
}

void loop() {
  // Handle web requests
  server.handleClient();
  
  // Safety timeout for motors (auto-stop after 5 seconds)
  if (motor_timeout > 0 && millis() > motor_timeout) {
    stop_motors();
  }
  
  // Small delay to prevent watchdog timeout
  delay(10);
}

