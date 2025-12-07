# ============================================================================
# AI PET ROBOT - LAPTOP SERVER (Main Application)
# ============================================================================
# Purpose: Central hub for AI/LLM processing, face generation, and system orchestration
# Receives: Video from Jetson Nano, Commands from Mobile App, Voice input from Phone
# Sends: Face/Display data to Jetson Nano, Bluetooth commands to ESP32, Mirror to Mobile App
# ============================================================================

import os
import json
import threading
import cv2
import numpy as np
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import logging
from collections import deque
import pickle
import base64
from queue import Queue
import serial
import struct

# AI/ML Libraries
import torch
from PIL import Image
import io

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Server Configuration
    FLASK_HOST = "0.0.0.0"  # Listen on all interfaces
    FLASK_PORT = 5000
    DEBUG = True
    
    # Bluetooth Configuration (ESP32)
    BLUETOOTH_ENABLED = True
    BLUETOOTH_PORT = "/dev/rfcomm0"  # Linux Bluetooth device (adjust for your system)
    BLUETOOTH_BAUDRATE = 115200
    
    # Jetson Nano Connection
    JETSON_HOST = "192.168.1.100"  # Update with your Jetson Nano IP
    JETSON_PORT = 5001
    
    # Display Configuration
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 600
    DISPLAY_MODE = "face"  # "face", "text", "hybrid"
    
    # Face Animation Parameters
    FACE_BLINK_INTERVAL = 3  # seconds
    FACE_EMOTION_UPDATE = 2  # seconds
    
    # Video Processing
    VIDEO_FPS = 30
    VIDEO_FRAME_BUFFER_SIZE = 10
    
    # Logging
    LOG_LEVEL = logging.INFO

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robot_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# ============================================================================
# GLOBAL STATE MANAGEMENT
# ============================================================================

class RobotState:
    def __init__(self):
        self.mode = "automatic"  # "automatic" or "manual"
        self.emotion = "neutral"  # "happy", "sad", "confused", "excited", "neutral"
        self.is_blinking = False
        self.current_display_mode = "face"  # "face", "text", "hybrid"
        self.display_content = {"type": "face", "emotion": "neutral"}
        self.voice_input_active = False
        self.motor_state = {"left": 0, "right": 0, "speed": 100}
        self.audio_playing = False
        self.connected_devices = {
            "jetson": False,
            "esp32": False,
            "mobile_app": False
        }
        self.frame_buffer = deque(maxlen=Config.VIDEO_FRAME_BUFFER_SIZE)
        self.last_frame_time = time.time()

robot_state = RobotState()

# Queues for asynchronous communication
command_queue = Queue()
display_queue = Queue()
bluetooth_queue = Queue()

# ============================================================================
# BLUETOOTH MANAGER (ESP32 Communication)
# ============================================================================

class BluetoothManager:
    def __init__(self, port=Config.BLUETOOTH_PORT, baudrate=Config.BLUETOOTH_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.lock = threading.Lock()
        self.heartbeat_thread = None
        
    def connect(self):
        """Establish Bluetooth connection to ESP32"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_connected = True
            logger.info(f"✓ Bluetooth connected to ESP32 on {self.port}")
            
            # Start heartbeat to maintain connection
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            
            robot_state.connected_devices["esp32"] = True
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect Bluetooth: {e}")
            self.is_connected = False
            robot_state.connected_devices["esp32"] = False
            return False
    
    def disconnect(self):
        """Close Bluetooth connection"""
        try:
            if self.serial_conn:
                self.serial_conn.close()
                self.is_connected = False
                logger.info("Bluetooth disconnected")
                robot_state.connected_devices["esp32"] = False
        except Exception as e:
            logger.error(f"Error closing Bluetooth: {e}")
    
    def send_motor_command(self, left_speed, right_speed):
        """
        Send motor control command to ESP32
        Speed range: -100 to +100 (negative = reverse)
        """
        try:
            with self.lock:
                if not self.is_connected:
                    logger.warning("Bluetooth not connected, cannot send motor command")
                    return False
                
                # Packet format: [CMD_TYPE][LEFT_SPEED][RIGHT_SPEED][CHECKSUM]
                cmd_type = 0x01  # Motor control command
                left_byte = int((left_speed + 100) / 2)  # Convert -100..100 to 0..200 then 0..100
                right_byte = int((right_speed + 100) / 2)
                
                checksum = (cmd_type + left_byte + right_byte) & 0xFF
                
                packet = bytes([cmd_type, left_byte, right_byte, checksum])
                self.serial_conn.write(packet)
                
                logger.debug(f"Motor command sent: L={left_speed}, R={right_speed}")
                return True
        except Exception as e:
            logger.error(f"Error sending motor command: {e}")
            self.is_connected = False
            return False
    
    def send_audio_command(self, audio_file, volume=80):
        """Send audio playback command to ESP32"""
        try:
            with self.lock:
                if not self.is_connected:
                    return False
                
                # Packet format: [CMD_TYPE][VOLUME][FILENAME_LENGTH][FILENAME][CHECKSUM]
                cmd_type = 0x02  # Audio command
                volume_byte = min(100, max(0, volume))
                
                # Send simplified command
                packet = bytes([cmd_type, volume_byte, 0x00])  # 0x00 = play default
                self.serial_conn.write(packet)
                
                logger.debug(f"Audio command sent: {audio_file}")
                return True
        except Exception as e:
            logger.error(f"Error sending audio command: {e}")
            return False
    
    def send_led_command(self, color_r, color_g, color_b, brightness=100):
        """Send LED control command to ESP32"""
        try:
            with self.lock:
                if not self.is_connected:
                    return False
                
                cmd_type = 0x03  # LED command
                packet = bytes([cmd_type, color_r, color_g, color_b, brightness])
                self.serial_conn.write(packet)
                
                logger.debug(f"LED command sent: RGB({color_r},{color_g},{color_b})")
                return True
        except Exception as e:
            logger.error(f"Error sending LED command: {e}")
            return False
    
    def _heartbeat_loop(self):
        """Periodically send heartbeat to maintain connection"""
        while self.is_connected:
            try:
                time.sleep(5)
                if self.serial_conn and self.is_connected:
                    self.serial_conn.write(bytes([0xFF, 0x00]))  # Heartbeat
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")

# ============================================================================
# FACE ANIMATION ENGINE
# ============================================================================

class FaceAnimationEngine:
    def __init__(self, width=Config.DISPLAY_WIDTH, height=Config.DISPLAY_HEIGHT):
        self.width = width
        self.height = height
        self.emotion = "neutral"
        self.blink_state = False
        self.last_blink_time = time.time()
        self.animation_frame = 0
        
    def generate_face(self, emotion="neutral", blink=False):
        """
        Generate cute robot face with emotion
        Returns: numpy array (RGB image)
        """
        face_img = np.ones((self.height, self.width, 3), dtype=np.uint8) * 255
        
        # Face circle (center, radius=250)
        center = (self.width // 2, self.height // 2)
        cv2.circle(face_img, center, 200, (240, 200, 160), -1)  # Beige face
        cv2.circle(face_img, center, 200, (200, 150, 100), 2)   # Border
        
        # Eyes positions
        left_eye = (center[0] - 80, center[1] - 40)
        right_eye = (center[0] + 80, center[1] - 40)
        
        # Draw eyes based on emotion
        if blink:
            # Closed eyes (lines)
            cv2.line(face_img, (left_eye[0] - 30, left_eye[1]), 
                    (left_eye[0] + 30, left_eye[1]), (0, 0, 0), 3)
            cv2.line(face_img, (right_eye[0] - 30, right_eye[1]), 
                    (right_eye[0] + 30, right_eye[1]), (0, 0, 0), 3)
        else:
            # Open eyes with emotion
            eye_color = (50, 50, 200)  # Blue eyes
            cv2.circle(face_img, left_eye, 25, eye_color, -1)
            cv2.circle(face_img, right_eye, 25, eye_color, -1)
            
            # Pupils
            cv2.circle(face_img, (left_eye[0] - 5, left_eye[1] + 3), 15, (0, 0, 0), -1)
            cv2.circle(face_img, (right_eye[0] - 5, right_eye[1] + 3), 15, (0, 0, 0), -1)
            
            # Highlights (shine)
            cv2.circle(face_img, (left_eye[0] - 10, left_eye[1] - 5), 5, (255, 255, 255), -1)
            cv2.circle(face_img, (right_eye[0] - 10, right_eye[1] - 5), 5, (255, 255, 255), -1)
        
        # Mouth based on emotion
        mouth_center = (center[0], center[1] + 100)
        
        if emotion == "happy":
            # Happy smile
            cv2.ellipse(face_img, mouth_center, (60, 40), 0, 0, 180, (0, 0, 0), 3)
        elif emotion == "sad":
            # Sad frown
            cv2.ellipse(face_img, mouth_center, (60, 40), 0, 180, 360, (0, 0, 0), 3)
        elif emotion == "excited":
            # Big open mouth
            cv2.ellipse(face_img, mouth_center, (70, 50), 0, 0, 180, (200, 100, 100), -1)
            cv2.ellipse(face_img, mouth_center, (70, 50), 0, 0, 180, (0, 0, 0), 2)
        elif emotion == "confused":
            # Question mark mouth
            cv2.line(face_img, (mouth_center[0] - 40, mouth_center[1] - 20),
                    (mouth_center[0] + 40, mouth_center[1] + 20), (0, 0, 0), 3)
        else:  # neutral
            # Neutral line
            cv2.line(face_img, (mouth_center[0] - 50, mouth_center[1]),
                    (mouth_center[0] + 50, mouth_center[1]), (0, 0, 0), 3)
        
        return face_img
    
    def generate_text_display(self, text, title="", background_color=(255, 255, 255)):
        """
        Generate text display for information
        Returns: numpy array (RGB image)
        """
        display_img = np.ones((self.height, self.width, 3), dtype=np.uint8) * background_color[0]
        display_img[:, :, 1] = background_color[1]
        display_img[:, :, 2] = background_color[2]
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if title:
            cv2.putText(display_img, title, (50, 80), font, 1.2, (50, 50, 50), 2)
            cv2.line(display_img, (50, 100), (self.width - 50, 100), (100, 100, 100), 2)
        
        # Wrap text
        y_offset = 150 if title else 100
        line_height = 40
        max_width = self.width - 100
        
        words = text.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word
            text_size = cv2.getTextSize(test_line, font, 0.8, 2)[0]
            
            if text_size[0] > max_width:
                if current_line:
                    cv2.putText(display_img, current_line, (50, y_offset), font, 0.8, (30, 30, 30), 2)
                    y_offset += line_height
                current_line = word
            else:
                current_line = test_line
        
        if current_line:
            cv2.putText(display_img, current_line, (50, y_offset), font, 0.8, (30, 30, 30), 2)
        
        return display_img
    
    def update_animation(self):
        """Update animation state (blink, etc.)"""
        current_time = time.time()
        
        # Blinking logic
        if current_time - self.last_blink_time > Config.FACE_BLINK_INTERVAL:
            self.blink_state = not self.blink_state
            self.last_blink_time = current_time
            
            if self.blink_state:
                self.last_blink_time += 0.2  # Blink duration
        
        return self.blink_state

# ============================================================================
# JETSON NANO VIDEO RECEIVER
# ============================================================================

class JetsonVideoReceiver:
    def __init__(self, host=Config.JETSON_HOST, port=Config.JETSON_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
    def connect(self):
        """Establish connection to Jetson Nano"""
        try:
            import socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            logger.info(f"✓ Connected to Jetson Nano at {self.host}:{self.port}")
            
            # Start receiving thread
            recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            recv_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to Jetson Nano: {e}")
            self.is_connected = False
            return False
    
    def _receive_loop(self):
        """Continuously receive frames from Jetson Nano"""
        buffer = b""
        
        while self.is_connected:
            try:
                data = self.socket.recv(65536)
                if not data:
                    break
                
                buffer += data
                
                # Simple frame delimiter: FRAME_START[size(4 bytes)][JPEG][FRAME_END]
                while b'FRAME_START' in buffer and b'FRAME_END' in buffer:
                    start_idx = buffer.find(b'FRAME_START')
                    end_idx = buffer.find(b'FRAME_END', start_idx)
                    
                    if start_idx != -1 and end_idx != -1:
                        frame_data = buffer[start_idx + 11:end_idx]
                        
                        try:
                            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                            
                            if frame is not None:
                                with self.frame_lock:
                                    self.current_frame = frame
                                    robot_state.frame_buffer.append(frame)
                        except Exception as e:
                            logger.debug(f"Frame decode error: {e}")
                        
                        buffer = buffer[end_idx + 9:]
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"Error receiving frame: {e}")
                self.is_connected = False
                break
    
    def get_latest_frame(self):
        """Get the latest frame received from Jetson"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

# ============================================================================
# AI/NLP PROCESSING ENGINE
# ============================================================================

class AIProcessingEngine:
    def __init__(self):
        self.emotion_history = deque(maxlen=5)
        self.last_emotion_update = time.time()
        
    def detect_emotion_from_voice(self, voice_data):
        """
        Detect emotion from voice input
        In production, use: librosa + emotion recognition model
        """
        # Placeholder: Random emotion for demo
        emotions = ["happy", "sad", "neutral", "excited", "confused"]
        detected_emotion = np.random.choice(emotions)
        confidence = np.random.random()
        
        logger.debug(f"Detected emotion: {detected_emotion} ({confidence:.2f})")
        return detected_emotion, confidence
    
    def process_voice_command(self, voice_text):
        """
        Process voice commands and generate responses
        In production, use: GPT-3/LLaMA via Ollama or similar
        """
        voice_text = voice_text.lower()
        
        # Simple command matching
        if "move forward" in voice_text or "go forward" in voice_text:
            return "move_forward"
        elif "move backward" in voice_text or "go back" in voice_text:
            return "move_backward"
        elif "turn left" in voice_text:
            return "turn_left"
        elif "turn right" in voice_text:
            return "turn_right"
        elif "stop" in voice_text:
            return "stop"
        elif "show shopping list" in voice_text:
            return "display_shopping_list"
        elif "show formula" in voice_text:
            return "display_formula"
        elif "happy" in voice_text:
            return "emotion_happy"
        elif "sad" in voice_text:
            return "emotion_sad"
        else:
            return "unknown"
    
    def generate_response(self, command, context=""):
        """Generate appropriate response or action"""
        response = {
            "action": None,
            "display_content": None,
            "emotion": "neutral",
            "audio": None
        }
        
        # Map commands to responses
        if command.startswith("move_"):
            direction = command.split("_")[1]
            response["action"] = command
            response["emotion"] = "excited"
        elif command.startswith("emotion_"):
            emotion = command.split("_")[1]
            response["emotion"] = emotion
        elif command == "display_shopping_list":
            response["display_content"] = {
                "type": "text",
                "title": "Shopping List",
                "content": "1. Milk\n2. Bread\n3. Eggs\n4. Vegetables\n5. Fruits"
            }
            response["emotion"] = "happy"
        elif command == "display_formula":
            response["display_content"] = {
                "type": "text",
                "title": "Formula",
                "content": "E = mc²\n\nEnergy = mass × speed of light squared"
            }
            response["emotion"] = "neutral"
        
        return response

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

bluetooth_manager = BluetoothManager()
face_engine = FaceAnimationEngine()
jetson_receiver = JetsonVideoReceiver()
ai_engine = AIProcessingEngine()

# ============================================================================
# FLASK ROUTES & WEBSOCKET HANDLERS
# ============================================================================

@app.route('/')
def index():
    """Serve main dashboard"""
    return jsonify({
        "status": "Server running",
        "timestamp": datetime.now().isoformat(),
        "connected_devices": robot_state.connected_devices
    })

@app.route('/api/status')
def get_status():
    """Get current robot status"""
    return jsonify({
        "mode": robot_state.mode,
        "emotion": robot_state.emotion,
        "display_mode": robot_state.current_display_mode,
        "connected_devices": robot_state.connected_devices,
        "motor_state": robot_state.motor_state,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/video/latest')
def get_latest_video():
    """Get latest video frame from Jetson"""
    frame = jetson_receiver.get_latest_frame()
    
    if frame is None:
        return jsonify({"error": "No frame available"}), 404
    
    # Encode frame to JPEG
    ret, buffer = cv2.imencode('.jpg', frame)
    frame_base64 = base64.b64encode(buffer).decode()
    
    return jsonify({
        "frame": frame_base64,
        "timestamp": time.time()
    })

# ============================================================================
# WEBSOCKET EVENT HANDLERS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    robot_state.connected_devices["mobile_app"] = True
    emit('status_update', {
        "message": "Connected to server",
        "timestamp": datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    robot_state.connected_devices["mobile_app"] = False

@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle voice commands from mobile app"""
    voice_text = data.get('text', '')
    logger.info(f"Voice command received: {voice_text}")
    
    # Process command
    command = ai_engine.process_voice_command(voice_text)
    response = ai_engine.generate_response(command)
    
    # Update robot state
    if response["emotion"]:
        robot_state.emotion = response["emotion"]
    
    if response["display_content"]:
        robot_state.display_content = response["display_content"]
        robot_state.current_display_mode = "text"
    
    # Execute action
    if response["action"]:
        if response["action"] == "move_forward":
            bluetooth_manager.send_motor_command(80, 80)
        elif response["action"] == "move_backward":
            bluetooth_manager.send_motor_command(-80, -80)
        elif response["action"] == "turn_left":
            bluetooth_manager.send_motor_command(-50, 80)
        elif response["action"] == "turn_right":
            bluetooth_manager.send_motor_command(80, -50)
        elif response["action"] == "stop":
            bluetooth_manager.send_motor_command(0, 0)
    
    # Broadcast update
    socketio.emit('command_processed', response, broadcast=True)

@socketio.on('manual_control')
def handle_manual_control(data):
    """Handle manual motor control from mobile app"""
    left_speed = data.get('left_speed', 0)
    right_speed = data.get('right_speed', 0)
    
    robot_state.mode = "manual"
    robot_state.motor_state["left"] = left_speed
    robot_state.motor_state["right"] = right_speed
    
    bluetooth_manager.send_motor_command(left_speed, right_speed)
    logger.debug(f"Manual control: L={left_speed}, R={right_speed}")

@socketio.on('emotion_request')
def handle_emotion_request(data):
    """Handle emotion change request"""
    emotion = data.get('emotion', 'neutral')
    robot_state.emotion = emotion
    
    logger.info(f"Emotion changed to: {emotion}")
    socketio.emit('emotion_update', {"emotion": emotion}, broadcast=True)

@socketio.on('display_request')
def handle_display_request(data):
    """Handle display content request"""
    display_type = data.get('type', 'face')
    content = data.get('content', '')
    title = data.get('title', '')
    
    robot_state.current_display_mode = display_type
    
    if display_type == "text":
        robot_state.display_content = {
            "type": "text",
            "title": title,
            "content": content
        }
    elif display_type == "face":
        robot_state.display_content = {
            "type": "face",
            "emotion": robot_state.emotion
        }
    
    socketio.emit('display_update', robot_state.display_content, broadcast=True)

# ============================================================================
# DISPLAY GENERATION LOOP (BACKGROUND THREAD)
# ============================================================================

def display_generation_loop():
    """Continuously generate and broadcast display frames"""
    while True:
        try:
            # Determine what to display
            if robot_state.current_display_mode == "face":
                blink = face_engine.update_animation()
                display_frame = face_engine.generate_face(robot_state.emotion, blink)
            elif robot_state.current_display_mode == "text":
                content = robot_state.display_content
                display_frame = face_engine.generate_text_display(
                    content.get("content", ""),
                    content.get("title", "")
                )
            else:  # hybrid
                # Show face 80% of the time, text on request
                if robot_state.display_content.get("type") == "text":
                    content = robot_state.display_content
                    display_frame = face_engine.generate_text_display(
                        content.get("content", ""),
                        content.get("title", "")
                    )
                else:
                    blink = face_engine.update_animation()
                    display_frame = face_engine.generate_face(robot_state.emotion, blink)
            
            # Encode and broadcast to Jetson and Mobile App
            ret, buffer = cv2.imencode('.jpg', display_frame)
            frame_base64 = base64.b64encode(buffer).decode()
            
            # Send to Jetson Nano (for HDMI display)
            socketio.emit('display_frame', {
                "frame": frame_base64,
                "timestamp": time.time(),
                "emotion": robot_state.emotion
            }, broadcast=True)
            
            # Control frame rate
            time.sleep(1.0 / Config.VIDEO_FPS)
            
        except Exception as e:
            logger.error(f"Error in display loop: {e}")
            time.sleep(0.5)

# ============================================================================
# INITIALIZATION & STARTUP
# ============================================================================

def initialize_system():
    """Initialize all system components"""
    logger.info("=" * 60)
    logger.info("AI PET ROBOT SERVER - INITIALIZING")
    logger.info("=" * 60)
    
    # 1. Initialize Bluetooth (ESP32)
    if Config.BLUETOOTH_ENABLED:
        if bluetooth_manager.connect():
            logger.info("✓ Bluetooth initialized")
        else:
            logger.warning("⚠ Bluetooth initialization failed - continuing without motor control")
    
    # 2. Connect to Jetson Nano
    if jetson_receiver.connect():
        logger.info("✓ Jetson Nano connection established")
    else:
        logger.warning("⚠ Jetson Nano connection failed - video input unavailable")
    
    # 3. Start display generation thread
    display_thread = threading.Thread(target=display_generation_loop, daemon=True)
    display_thread.start()
    logger.info("✓ Display engine started")
    
    logger.info("=" * 60)
    logger.info("SYSTEM READY")
    logger.info("=" * 60)

if __name__ == '__main__':
    initialize_system()
    socketio.run(app, host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.DEBUG, allow_unsafe_werkzeug=True)