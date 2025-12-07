// ============================================================================
// ESP32 - MOTOR & AUDIO CONTROL MODULE (Arduino/PlatformIO)
// ============================================================================
// Purpose: Control motors, speakers, and LEDs via Bluetooth from laptop server
// Receives: Bluetooth commands from laptop server
// Hardware: ESP32 DevKit, 2x DC Motors, Bluetooth Module, Speaker, LED Strip
// ============================================================================

#include <BluetoothSerial.h>
#include <Arduino.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

// Bluetooth Configuration
BluetoothSerial SerialBT;
const char* BT_NAME = "PET_ROBOT_ESP32";
const char* BT_PIN = "1234";

// Motor Configuration
#define MOTOR_LEFT_FORWARD 25   // GPIO pin for left motor forward
#define MOTOR_LEFT_BACKWARD 26  // GPIO pin for left motor backward
#define MOTOR_LEFT_PWM 15       // PWM pin for left motor speed
#define MOTOR_LEFT_FREQ 5000
#define MOTOR_LEFT_CHANNEL 0

#define MOTOR_RIGHT_FORWARD 32  // GPIO pin for right motor forward
#define MOTOR_RIGHT_BACKWARD 33 // GPIO pin for right motor backward
#define MOTOR_RIGHT_PWM 23      // PWM pin for right motor speed
#define MOTOR_RIGHT_FREQ 5000
#define MOTOR_RIGHT_CHANNEL 1

#define PWM_MAX 255

// Audio Configuration
#define SPEAKER_PIN 19
#define AUDIO_PWM_FREQ 1000
#define AUDIO_PWM_CHANNEL 2

// LED Configuration (RGB Strip)
#define LED_RED_PIN 12
#define LED_GREEN_PIN 13
#define LED_BLUE_PIN 14
#define LED_PWM_FREQ 1000
#define LED_RED_CHANNEL 3
#define LED_GREEN_CHANNEL 4
#define LED_BLUE_CHANNEL 5

// Status LED
#define STATUS_LED_PIN 2
#define STATUS_LED_BLINK_INTERVAL 500

// Logging
#define DEBUG_ENABLED 1
#define BAUD_RATE 115200

// ============================================================================
// GLOBAL STATE
// ============================================================================

struct MotorState {
  int left_speed;
  int right_speed;
  boolean left_forward;
  boolean right_forward;
};

struct LEDState {
  int red;
  int green;
  int blue;
  int brightness;
};

struct SystemState {
  MotorState motor;
  LEDState led;
  boolean audio_playing;
  unsigned long last_command_time;
  boolean connected;
  unsigned long startup_time;
};

SystemState state;
unsigned long last_blink_time = 0;
boolean status_led_state = LOW;

// ============================================================================
// SETUP FUNCTION
// ============================================================================

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  delay(100);
  
  if (DEBUG_ENABLED) {
    Serial.println("\n\n=== ESP32 Motor Control - Initializing ===");
  }
  
  // Initialize Bluetooth
  if (!SerialBT.begin(BT_NAME, true)) { // true = slave mode
    if (DEBUG_ENABLED) Serial.println("✗ Bluetooth initialization failed");
  } else {
    if (DEBUG_ENABLED) {
      Serial.println("✓ Bluetooth initialized as: " + String(BT_NAME));
    }
    state.connected = true;
  }
  
  // Configure motor pins
  pinMode(MOTOR_LEFT_FORWARD, OUTPUT);
  pinMode(MOTOR_LEFT_BACKWARD, OUTPUT);
  pinMode(MOTOR_RIGHT_FORWARD, OUTPUT);
  pinMode(MOTOR_RIGHT_BACKWARD, OUTPUT);
  
  digitalWrite(MOTOR_LEFT_FORWARD, LOW);
  digitalWrite(MOTOR_LEFT_BACKWARD, LOW);
  digitalWrite(MOTOR_RIGHT_FORWARD, LOW);
  digitalWrite(MOTOR_RIGHT_BACKWARD, LOW);
  
  // Configure PWM for motors
  ledcSetup(MOTOR_LEFT_CHANNEL, MOTOR_LEFT_FREQ, 8);
  ledcAttachPin(MOTOR_LEFT_PWM, MOTOR_LEFT_CHANNEL);
  
  ledcSetup(MOTOR_RIGHT_CHANNEL, MOTOR_RIGHT_FREQ, 8);
  ledcAttachPin(MOTOR_RIGHT_PWM, MOTOR_RIGHT_CHANNEL);
  
  if (DEBUG_ENABLED) Serial.println("✓ Motors configured");
  
  // Configure audio pin
  pinMode(SPEAKER_PIN, OUTPUT);
  ledcSetup(AUDIO_PWM_CHANNEL, AUDIO_PWM_FREQ, 8);
  ledcAttachPin(SPEAKER_PIN, AUDIO_PWM_CHANNEL);
  if (DEBUG_ENABLED) Serial.println("✓ Audio configured");
  
  // Configure LED pins (PWM for analog control)
  ledcSetup(LED_RED_CHANNEL, LED_PWM_FREQ, 8);
  ledcAttachPin(LED_RED_PIN, LED_RED_CHANNEL);
  
  ledcSetup(LED_GREEN_CHANNEL, LED_PWM_FREQ, 8);
  ledcAttachPin(LED_GREEN_PIN, LED_GREEN_CHANNEL);
  
  ledcSetup(LED_BLUE_CHANNEL, LED_PWM_FREQ, 8);
  ledcAttachPin(LED_BLUE_PIN, LED_BLUE_CHANNEL);
  
  if (DEBUG_ENABLED) Serial.println("✓ LED configured");
  
  // Configure status LED (simple digital)
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);
  
  // Initialize state
  state.motor.left_speed = 0;
  state.motor.right_speed = 0;
  state.motor.left_forward = true;
  state.motor.right_forward = true;
  state.led.red = 255;
  state.led.green = 255;
  state.led.blue = 255;
  state.led.brightness = 100;
  state.audio_playing = false;
  state.last_command_time = millis();
  state.startup_time = millis();
  
  if (DEBUG_ENABLED) {
    Serial.println("=== ESP32 Ready ===");
    Serial.println("Waiting for Bluetooth connections...");
  }
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Check for Bluetooth commands
  if (SerialBT.available()) {
    processBluetoothCommand();
  }
  
  // Check for Serial commands (debugging)
  if (Serial.available()) {
    processSerialCommand();
  }
  
  // Status LED blink
  updateStatusLED();
  
  // Motor safety timeout (stop motors if no command for 5 seconds)
  if (millis() - state.last_command_time > 5000) {
    stopMotors();
  }
  
  delay(10);
}

// ============================================================================
// BLUETOOTH COMMAND PROCESSING
// ============================================================================

void processBluetoothCommand() {
  byte cmd_type = SerialBT.read();
  
  if (DEBUG_ENABLED) {
    Serial.print("Command received: 0x");
    Serial.println(cmd_type, HEX);
  }
  
  state.last_command_time = millis();
  
  switch(cmd_type) {
    case 0x01: // Motor control
      handleMotorCommand();
      break;
      
    case 0x02: // Audio command
      handleAudioCommand();
      break;
      
    case 0x03: // LED command
      handleLEDCommand();
      break;
      
    case 0xFF: // Heartbeat
      handleHeartbeat();
      break;
      
    default:
      if (DEBUG_ENABLED) Serial.println("Unknown command");
  }
}

// ============================================================================
// MOTOR CONTROL HANDLER
// ============================================================================

void handleMotorCommand() {
  // Wait for speed bytes
  int timeout = 100;
  unsigned long start_time = millis();
  
  while (!SerialBT.available() && (millis() - start_time < timeout)) {
    delay(1);
  }
  
  if (SerialBT.available()) {
    byte left_byte = SerialBT.read();
    
    while (!SerialBT.available() && (millis() - start_time < timeout)) {
      delay(1);
    }
    
    if (SerialBT.available()) {
      byte right_byte = SerialBT.read();
      byte checksum = SerialBT.read();
      
      // Convert from 0-200 range back to -100..100
      int left_speed = ((int)left_byte * 2) - 100;
      int right_speed = ((int)right_byte * 2) - 100;
      
      // Clamp to valid range
      left_speed = constrain(left_speed, -100, 100);
      right_speed = constrain(right_speed, -100, 100);
      
      // Set motors
      setMotorSpeed(left_speed, right_speed);
      
      if (DEBUG_ENABLED) {
        Serial.print("Motor: L=");
        Serial.print(left_speed);
        Serial.print(" R=");
        Serial.println(right_speed);
      }
    }
  }
}

// ============================================================================
// SET MOTOR SPEED
// ============================================================================

void setMotorSpeed(int left_speed, int right_speed) {
  state.motor.left_speed = left_speed;
  state.motor.right_speed = right_speed;
  
  // Left Motor
  if (left_speed > 0) {
    // Forward
    digitalWrite(MOTOR_LEFT_FORWARD, HIGH);
    digitalWrite(MOTOR_LEFT_BACKWARD, LOW);
    ledcWrite(MOTOR_LEFT_CHANNEL, map(left_speed, 0, 100, 0, PWM_MAX));
  } else if (left_speed < 0) {
    // Backward
    digitalWrite(MOTOR_LEFT_FORWARD, LOW);
    digitalWrite(MOTOR_LEFT_BACKWARD, HIGH);
    ledcWrite(MOTOR_LEFT_CHANNEL, map(-left_speed, 0, 100, 0, PWM_MAX));
  } else {
    // Stop
    digitalWrite(MOTOR_LEFT_FORWARD, LOW);
    digitalWrite(MOTOR_LEFT_BACKWARD, LOW);
    ledcWrite(MOTOR_LEFT_CHANNEL, 0);
  }
  
  // Right Motor
  if (right_speed > 0) {
    // Forward
    digitalWrite(MOTOR_RIGHT_FORWARD, HIGH);
    digitalWrite(MOTOR_RIGHT_BACKWARD, LOW);
    ledcWrite(MOTOR_RIGHT_CHANNEL, map(right_speed, 0, 100, 0, PWM_MAX));
  } else if (right_speed < 0) {
    // Backward
    digitalWrite(MOTOR_RIGHT_FORWARD, LOW);
    digitalWrite(MOTOR_RIGHT_BACKWARD, HIGH);
    ledcWrite(MOTOR_RIGHT_CHANNEL, map(-right_speed, 0, 100, 0, PWM_MAX));
  } else {
    // Stop
    digitalWrite(MOTOR_RIGHT_FORWARD, LOW);
    digitalWrite(MOTOR_RIGHT_BACKWARD, LOW);
    ledcWrite(MOTOR_RIGHT_CHANNEL, 0);
  }
}

void stopMotors() {
  setMotorSpeed(0, 0);
}

// ============================================================================
// AUDIO HANDLER
// ============================================================================

void handleAudioCommand() {
  // Wait for volume byte
  int timeout = 100;
  unsigned long start_time = millis();
  
  while (!SerialBT.available() && (millis() - start_time < timeout)) {
    delay(1);
  }
  
  if (SerialBT.available()) {
    byte volume = SerialBT.read();
    playTone(1000, 500, volume); // 1kHz for 500ms
    
    if (DEBUG_ENABLED) {
      Serial.print("Audio: volume=");
      Serial.println(volume);
    }
  }
}

void playTone(int frequency, int duration, int volume) {
  long time_now = millis();
  state.audio_playing = true;
  
  int pwm_value = map(volume, 0, 100, 0, 127);
  
  while (millis() - time_now < duration) {
    ledcWrite(AUDIO_PWM_CHANNEL, pwm_value);
    delayMicroseconds(1000000 / frequency / 2);
    
    ledcWrite(AUDIO_PWM_CHANNEL, 0);
    delayMicroseconds(1000000 / frequency / 2);
  }
  
  ledcWrite(AUDIO_PWM_CHANNEL, 0);
  state.audio_playing = false;
}

// ============================================================================
// LED HANDLER
// ============================================================================

void handleLEDCommand() {
  byte timeout = 100;
  unsigned long start_time = millis();
  
  // Read RGB values
  while (!SerialBT.available() && (millis() - start_time < timeout)) delay(1);
  byte red = SerialBT.available() ? SerialBT.read() : 255;
  
  while (!SerialBT.available() && (millis() - start_time < timeout)) delay(1);
  byte green = SerialBT.available() ? SerialBT.read() : 255;
  
  while (!SerialBT.available() && (millis() - start_time < timeout)) delay(1);
  byte blue = SerialBT.available() ? SerialBT.read() : 255;
  
  while (!SerialBT.available() && (millis() - start_time < timeout)) delay(1);
  byte brightness = SerialBT.available() ? SerialBT.read() : 100;
  
  setLEDColor(red, green, blue, brightness);
  
  if (DEBUG_ENABLED) {
    Serial.print("LED: RGB(");
    Serial.print(red); Serial.print(",");
    Serial.print(green); Serial.print(",");
    Serial.print(blue); Serial.print(") Brightness=");
    Serial.println(brightness);
  }
}

void setLEDColor(int red, int green, int blue, int brightness) {
  state.led.red = red;
  state.led.green = green;
  state.led.blue = blue;
  state.led.brightness = constrain(brightness, 0, 100);
  
  // Apply brightness
  int r = map(red * brightness / 100, 0, 255, 0, 255);
  int g = map(green * brightness / 100, 0, 255, 0, 255);
  int b = map(blue * brightness / 100, 0, 255, 0, 255);
  
  ledcWrite(LED_RED_CHANNEL, r);
  ledcWrite(LED_GREEN_CHANNEL, g);
  ledcWrite(LED_BLUE_CHANNEL, b);
}

// ============================================================================
// UTILITY HANDLERS
// ============================================================================

void handleHeartbeat() {
  if (DEBUG_ENABLED) Serial.println("Heartbeat received");
  state.last_command_time = millis();
}

void updateStatusLED() {
  if (millis() - last_blink_time > STATUS_LED_BLINK_INTERVAL) {
    status_led_state = !status_led_state;
    digitalWrite(STATUS_LED_PIN, status_led_state);
    last_blink_time = millis();
  }
}

// ============================================================================
// SERIAL COMMAND PROCESSING (for debugging)
// ============================================================================

void processSerialCommand() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  
  if (cmd == "test_motor") {
    Serial.println("Testing motors...");
    setMotorSpeed(50, 50);
    delay(1000);
    setMotorSpeed(-50, -50);
    delay(1000);
    setMotorSpeed(0, 0);
  }
  else if (cmd.startsWith("motor ")) {
    int left = 0, right = 0;
    sscanf(cmd.c_str(), "motor %d %d", &left, &right);
    setMotorSpeed(left, right);
    Serial.print("Motors set to: L=");
    Serial.print(left);
    Serial.print(" R=");
    Serial.println(right);
  }
  else if (cmd == "test_led") {
    Serial.println("Testing LED...");
    setLEDColor(255, 0, 0, 100);    // Red
    delay(500);
    setLEDColor(0, 255, 0, 100);    // Green
    delay(500);
    setLEDColor(0, 0, 255, 100);    // Blue
    delay(500);
    setLEDColor(255, 255, 255, 100); // White
  }
  else if (cmd == "test_audio") {
    Serial.println("Testing audio...");
    playTone(1000, 500, 80);
  }
  else if (cmd == "status") {
    Serial.println("=== ESP32 Status ===");
    Serial.print("Uptime: ");
    Serial.print((millis() - state.startup_time) / 1000);
    Serial.println("s");
    Serial.print("Motor L: ");
    Serial.print(state.motor.left_speed);
    Serial.print(" R: ");
    Serial.println(state.motor.right_speed);
    Serial.print("LED: RGB(");
    Serial.print(state.led.red); Serial.print(",");
    Serial.print(state.led.green); Serial.print(",");
    Serial.print(state.led.blue);
    Serial.print(") Brightness: ");
    Serial.println(state.led.brightness);
  }
  else if (cmd == "help") {
    Serial.println("Available commands:");
    Serial.println("  test_motor    - Test motor control");
    Serial.println("  motor L R     - Set motor speeds (-100 to 100)");
    Serial.println("  test_led      - Test LED control");
    Serial.println("  test_audio    - Test audio output");
    Serial.println("  status        - Show system status");
    Serial.println("  help          - Show this help");
  }
}