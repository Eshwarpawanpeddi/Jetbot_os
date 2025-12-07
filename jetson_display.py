# ============================================================================
# JETSON NANO - VIDEO CAPTURE & HDMI DISPLAY MODULE
# ============================================================================
# Purpose: Capture camera video, send to laptop server, receive & display HDMI output
# Receives: Display frames from Laptop Server (face/text animations)
# Sends: Camera video feed to Laptop Server
# Hardware: Jetson Nano 2GB, HDMI Display, USB Camera
# ============================================================================

import cv2
import numpy as np
import threading
import socket
import time
import logging
import json
from collections import deque
from datetime import datetime
import base64
import io

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Server Connection (Laptop)
    SERVER_HOST = "192.168.1.101"  # Update with your laptop IP
    SERVER_PORT = 5001
    RECONNECT_INTERVAL = 5  # seconds
    
    # Camera Configuration
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
    CAMERA_BRIGHTNESS = 100
    CAMERA_CONTRAST = 50
    
    # Display Configuration (HDMI Output)
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 600
    DISPLAY_FPS = 30
    
    # Network Configuration
    VIDEO_FRAME_QUALITY = 80  # JPEG quality 1-100
    VIDEO_SEND_INTERVAL = 1.0 / 30  # 30 FPS
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = "/home/jetson/robot_jetson.log"

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CAMERA MANAGER
# ============================================================================

class CameraManager:
    def __init__(self, camera_index=Config.CAMERA_INDEX):
        self.camera_index = camera_index
        self.cap = None
        self.is_connected = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_count = 0
        self.fps_start_time = time.time()
        
    def connect(self):
        """Initialize and configure camera"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, Config.CAMERA_BRIGHTNESS)
            self.cap.set(cv2.CAP_PROP_CONTRAST, Config.CAMERA_CONTRAST)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
            
            self.is_connected = True
            logger.info(f"✓ Camera connected (index={self.camera_index})")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to connect camera: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Release camera"""
        if self.cap:
            self.cap.release()
            self.is_connected = False
            logger.info("Camera disconnected")
    
    def capture_frame(self):
        """Capture frame from camera"""
        if not self.is_connected:
            return None
        
        try:
            ret, frame = self.cap.read()
            
            if ret:
                with self.frame_lock:
                    self.current_frame = frame
                    self.frame_count += 1
                    
                    # Calculate FPS every 30 frames
                    if self.frame_count % 30 == 0:
                        elapsed = time.time() - self.fps_start_time
                        fps = 30 / elapsed if elapsed > 0 else 0
                        logger.debug(f"Camera FPS: {fps:.2f}")
                        self.fps_start_time = time.time()
                
                return frame
            else:
                logger.warning("Failed to read from camera")
                return None
                
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def get_latest_frame(self):
        """Get the most recent captured frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

# ============================================================================
# DISPLAY MANAGER (HDMI Output)
# ============================================================================

class DisplayManager:
    def __init__(self, width=Config.DISPLAY_WIDTH, height=Config.DISPLAY_HEIGHT):
        self.width = width
        self.height = height
        self.current_frame = None
        self.display_lock = threading.Lock()
        self.frame_count = 0
        self.last_frame_time = time.time()
        
    def update_frame(self, frame_base64):
        """Update display with new frame from server"""
        try:
            # Decode base64 frame
            frame_data = base64.b64decode(frame_base64)
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Resize to display resolution
                frame_resized = cv2.resize(frame, (self.width, self.height))
                
                with self.display_lock:
                    self.current_frame = frame_resized
                    self.frame_count += 1
                    
                return True
            else:
                logger.warning("Failed to decode display frame")
                return False
                
        except Exception as e:
            logger.error(f"Error updating display frame: {e}")
            return False
    
    def get_current_frame(self):
        """Get current frame for display"""
        with self.display_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def display_on_hdmi(self):
        """
        Display frames on HDMI output via cv2.imshow()
        Requires X11 forwarding or direct display connection
        """
        cv2.namedWindow('PET ROBOT', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('PET ROBOT', self.width, self.height)
        
        while True:
            frame = self.get_current_frame()
            
            if frame is not None:
                cv2.imshow('PET ROBOT', frame)
            else:
                # Display waiting screen
                blank = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for display...", (100, self.height//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.imshow('PET ROBOT', blank)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        
        cv2.destroyAllWindows()

# ============================================================================
# SERVER COMMUNICATION (Laptop)
# ============================================================================

class ServerCommunicator:
    def __init__(self, host=Config.SERVER_HOST, port=Config.SERVER_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.receive_queue = deque(maxlen=10)
        self.lock = threading.Lock()
        
    def connect(self):
        """Establish connection to laptop server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            logger.info(f"✓ Connected to server at {self.host}:{self.port}")
            
            # Start receive thread
            recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            recv_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to connect to server: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Close connection"""
        try:
            if self.socket:
                self.socket.close()
                self.is_connected = False
                logger.info("Disconnected from server")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def send_video_frame(self, frame):
        """Send video frame to server"""
        try:
            if not self.is_connected:
                return False
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                return False
            
            frame_data = buffer.tobytes()
            
            # Send frame with simple delimiter
            # Format: FRAME_START[JPEG_DATA]FRAME_END
            packet = b'FRAME_START' + frame_data + b'FRAME_END'
            
            self.socket.sendall(packet)
            return True
            
        except Exception as e:
            logger.error(f"Error sending video frame: {e}")
            self.is_connected = False
            return False
    
    def _receive_loop(self):
        """Continuously receive display updates from server"""
        self.socket.settimeout(5)  # 5 second timeout
        
        while self.is_connected:
            try:
                # Receive display frame
                data = self.socket.recv(1024 * 100)  # 100KB chunks
                
                if not data:
                    logger.warning("Server connection lost (no data)")
                    self.is_connected = False
                    break
                
                # Parse display frame
                try:
                    message = json.loads(data.decode('utf-8'))
                    
                    if message.get('type') == 'display_frame':
                        with self.lock:
                            self.receive_queue.append(message)
                        logger.debug(f"Received display frame")
                    
                except json.JSONDecodeError:
                    logger.debug("Non-JSON data received")
                    
            except socket.timeout:
                # Timeout is expected, continue
                continue
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                self.is_connected = False
                break
    
    def get_latest_display(self):
        """Get the latest display frame from queue"""
        with self.lock:
            if self.receive_queue:
                return self.receive_queue.pop()
        return None

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

camera = CameraManager()
display = DisplayManager()
server = ServerCommunicator()

# ============================================================================
# MAIN LOOPS
# ============================================================================

def camera_capture_loop():
    """Continuously capture video and send to server"""
    last_send_time = time.time()
    frame_count = 0
    
    while True:
        try:
            # Capture frame from camera
            frame = camera.capture_frame()
            
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Send to server at configured FPS
            current_time = time.time()
            if current_time - last_send_time >= Config.VIDEO_SEND_INTERVAL:
                
                # Compress for network transmission
                ret, jpeg_buffer = cv2.imencode('.jpg', frame, 
                    [cv2.IMWRITE_JPEG_QUALITY, Config.VIDEO_FRAME_QUALITY])
                
                if ret and server.is_connected:
                    if server.send_video_frame(frame):
                        frame_count += 1
                        if frame_count % 30 == 0:
                            elapsed = current_time - last_send_time
                            fps = 30 / elapsed if elapsed > 0 else 0
                            logger.info(f"Sending video at {fps:.1f} FPS")
                
                last_send_time = current_time
            
            time.sleep(0.01)  # Small sleep to prevent CPU spinning
            
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
            time.sleep(1)

def display_update_loop():
    """Continuously update HDMI display with received frames"""
    while True:
        try:
            # Check for new display frame from server
            display_data = server.get_latest_display()
            
            if display_data and 'frame' in display_data:
                display.update_frame(display_data['frame'])
            
            # Update HDMI display
            frame = display.get_current_frame()
            if frame is not None:
                cv2.imshow('PET ROBOT', frame)
            else:
                # Show waiting message
                blank = np.zeros((Config.DISPLAY_HEIGHT, Config.DISPLAY_WIDTH, 3), dtype=np.uint8)
                cv2.putText(blank, "Initializing...", (150, Config.DISPLAY_HEIGHT//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
                cv2.imshow('PET ROBOT', blank)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            time.sleep(1.0 / Config.DISPLAY_FPS)
            
        except Exception as e:
            logger.error(f"Error in display loop: {e}")
            time.sleep(1)

def server_connection_monitor():
    """Monitor and maintain server connection"""
    while True:
        try:
            if not server.is_connected:
                logger.warning("Attempting to reconnect to server...")
                server.connect()
            
            time.sleep(Config.RECONNECT_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in connection monitor: {e}")
            time.sleep(Config.RECONNECT_INTERVAL)

# ============================================================================
# INITIALIZATION & STARTUP
# ============================================================================

def initialize_system():
    """Initialize all Jetson components"""
    logger.info("=" * 60)
    logger.info("JETSON NANO - INITIALIZING")
    logger.info("=" * 60)
    
    # Initialize camera
    if camera.connect():
        logger.info("✓ Camera initialized")
    else:
        logger.error("✗ Camera initialization failed")
        return False
    
    # Connect to server
    if server.connect():
        logger.info("✓ Server connection established")
    else:
        logger.warning("⚠ Server connection failed (will retry)")
    
    # Start background threads
    camera_thread = threading.Thread(target=camera_capture_loop, daemon=True)
    camera_thread.start()
    logger.info("✓ Camera capture thread started")
    
    display_thread = threading.Thread(target=display_update_loop, daemon=True)
    display_thread.start()
    logger.info("✓ Display update thread started")
    
    monitor_thread = threading.Thread(target=server_connection_monitor, daemon=True)
    monitor_thread.start()
    logger.info("✓ Connection monitor started")
    
    logger.info("=" * 60)
    logger.info("JETSON NANO READY")
    logger.info("=" * 60)
    
    return True

if __name__ == '__main__':
    if initialize_system():
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            camera.disconnect()
            server.disconnect()
            cv2.destroyAllWindows()