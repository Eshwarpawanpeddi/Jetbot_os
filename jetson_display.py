#!/usr/bin/env python3
"""
JetBot OS - Jetson Display Service
Renders face animations and displays emotions
Communicates with server via REST API
"""

import os
import logging
import sys
import cv2
import numpy as np
from datetime import datetime
import time
import requests
import json

# ============================================================================
# LOGGING SETUP
# ============================================================================

os.makedirs('logs', exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(
    'logs/jetson_display.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(console_handler)

# ============================================================================
# CHECK DISPLAY AVAILABILITY
# ============================================================================

def check_display_available():
    """Check if X11 display is available"""
    if not os.getenv('DISPLAY'):
        logger.warning("No X11 DISPLAY set. Running headless mode.")
        return False
    try:
        # Try to import cv2 and check if display works
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        # Don't actually display if headless
        return True
    except Exception as e:
        logger.warning(f"Display check failed: {e}")
        return False

display_available = check_display_available()

# ============================================================================
# FACE RENDERER
# ============================================================================

class FaceRenderer:
    """Renders animated face on display"""
    
    # Emotion configurations
    EMOTIONS = {
        'neutral': {
            'mouth_type': 'line',
            'eye_openness': 1.0,
            'eye_angle': 0,
            'brightness': 100,
            'color': [240, 200, 160],
            'animation_speed': 1.0
        },
        'happy': {
            'mouth_type': 'smile',
            'eye_openness': 1.0,
            'eye_angle': 10,
            'brightness': 110,
            'color': [255, 220, 100],
            'animation_speed': 1.0,
            'add_sparkles': True,
            'sparkle_count': 8
        },
        'sad': {
            'mouth_type': 'frown',
            'eye_openness': 0.8,
            'eye_angle': -10,
            'brightness': 80,
            'color': [180, 150, 200],
            'animation_speed': 0.8,
            'add_tears': True,
            'tear_count': 2
        },
        'excited': {
            'mouth_type': 'big_smile',
            'eye_openness': 1.3,
            'eye_angle': 20,
            'brightness': 120,
            'color': [255, 200, 100],
            'animation_speed': 1.3,
            'add_sparkles': True,
            'sparkle_count': 16,
            'glow_intensity': 0.6
        },
        'confused': {
            'mouth_type': 'question',
            'eye_openness': 0.9,
            'eye_angle': -5,
            'brightness': 90,
            'color': [200, 150, 100],
            'animation_speed': 1.0,
            'head_tilt': 15
        },
        'angry': {
            'mouth_type': 'frown',
            'eye_openness': 0.7,
            'eye_angle': -15,
            'brightness': 95,
            'color': [220, 80, 80],
            'animation_speed': 0.7,
            'eyebrow_angle': 20
        },
        'thinking': {
            'mouth_type': 'hmm',
            'eye_openness': 0.8,
            'eye_angle': 45,
            'brightness': 95,
            'color': [150, 200, 255],
            'animation_speed': 0.9,
            'add_sparkles': False
        },
        'love': {
            'mouth_type': 'smile',
            'eye_openness': 1.2,
            'eye_angle': 30,
            'brightness': 115,
            'color': [255, 150, 200],
            'animation_speed': 1.2,
            'eye_shape': 'heart',
            'add_sparkles': True,
            'sparkle_count': 12
        },
        'skeptical': {
            'mouth_type': 'neutral',
            'eye_openness': 0.9,
            'eye_angle': 0,
            'brightness': 100,
            'color': [200, 200, 150],
            'animation_speed': 0.8,
            'eyebrow_angle': -15
        },
        'sleeping': {
            'mouth_type': 'zzz',
            'eye_openness': 0.0,
            'eye_angle': 0,
            'brightness': 50,
            'color': [150, 150, 200],
            'animation_speed': 0.5,
            'eyes_closed': True,
            'add_zzz': True
        }
    }
    
    def __init__(self, width=1280, height=720):
        """Initialize face renderer"""
        self.width = width
        self.height = height
        self.current_emotion = 'neutral'
        self.animation_frame = 0
        self.blink_frame = 0
        
        logger.info(f"Face renderer initialized: {width}x{height}")
    
    def render_frame(self) -> np.ndarray:
        """Render current emotion frame"""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        emotion_config = self.EMOTIONS.get(self.current_emotion, self.EMOTIONS['neutral'])
        
        # Draw background with gradient
        color = tuple(emotion_config.get('color', [240, 200, 160]))
        brightness = emotion_config.get('brightness', 100)
        
        # Simple background fill with brightness adjustment
        color = tuple(int(c * brightness / 100) for c in color)
        frame[:] = color
        
        # Draw face circle
        self._draw_face(frame, emotion_config)
        
        # Update animation frame
        self.animation_frame += 1
        self.blink_frame += 1
        
        if self.animation_frame > 100:
            self.animation_frame = 0
        if self.blink_frame > 50:
            self.blink_frame = 0
        
        return frame
    
    def _draw_face(self, frame, config):
        """Draw face elements"""
        center_x = self.width // 2
        center_y = self.height // 2
        face_size = 400
        
        # Face color (slightly darker than background)
        face_color = tuple(int(c * 0.9) for c in config.get('color', [240, 200, 160]))
        
        # Draw face circle
        cv2.circle(frame, (center_x, center_y), face_size // 2, face_color, -1)
        
        # Draw eyes
        eye_separation = 320
        eye_size = 80
        
        # Left eye
        left_eye_x = center_x - eye_separation // 2
        right_eye_x = center_x + eye_separation // 2
        eye_y = center_y - 100
        
        eye_color = tuple(config.get('eye_color', [50, 50, 200]))
        eye_openness = config.get('eye_openness', 1.0)
        
        # Draw eyes
        cv2.ellipse(
            frame,
            (left_eye_x, eye_y),
            (int(eye_size * eye_openness), int(eye_size * eye_openness * 0.6)),
            0,
            0,
            360,
            eye_color,
            -1
        )
        
        cv2.ellipse(
            frame,
            (right_eye_x, eye_y),
            (int(eye_size * eye_openness), int(eye_size * eye_openness * 0.6)),
            0,
            0,
            360,
            eye_color,
            -1
        )
        
        # Draw eye shine
        shine_color = (255, 255, 255)
        cv2.circle(frame, (left_eye_x - 15, eye_y - 15), 8, shine_color, -1)
        cv2.circle(frame, (right_eye_x - 15, eye_y - 15), 8, shine_color, -1)
        
        # Draw mouth
        mouth_y = center_y + 150
        mouth_type = config.get('mouth_type', 'line')
        mouth_color = (0, 0, 0)
        
        if mouth_type == 'smile':
            pts = np.array([
                [center_x - 80, mouth_y],
                [center_x - 40, mouth_y + 40],
                [center_x, mouth_y + 50],
                [center_x + 40, mouth_y + 40],
                [center_x + 80, mouth_y]
            ], dtype=np.int32)
            cv2.polylines(frame, [pts], False, mouth_color, 3)
        elif mouth_type == 'frown':
            pts = np.array([
                [center_x - 80, mouth_y],
                [center_x - 40, mouth_y - 40],
                [center_x, mouth_y - 50],
                [center_x + 40, mouth_y - 40],
                [center_x + 80, mouth_y]
            ], dtype=np.int32)
            cv2.polylines(frame, [pts], False, mouth_color, 3)
        else:  # Line
            cv2.line(frame, (center_x - 80, mouth_y), (center_x + 80, mouth_y), mouth_color, 3)
        
        # Add sparkles if needed
        if config.get('add_sparkles', False):
            self._draw_sparkles(frame, center_x, center_y, config.get('sparkle_count', 8))
    
    def _draw_sparkles(self, frame, center_x, center_y, count):
        """Draw sparkle effects"""
        import math
        
        sparkle_color = (255, 255, 100)
        angle_step = 360 / count
        radius = 200
        
        for i in range(count):
            angle = (i * angle_step + self.animation_frame * 3) % 360
            rad = math.radians(angle)
            x = int(center_x + radius * math.cos(rad))
            y = int(center_y + radius * math.sin(rad))
            
            if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                cv2.circle(frame, (x, y), 5, sparkle_color, -1)
    
    def set_emotion(self, emotion_name):
        """Set current emotion"""
        if emotion_name in self.EMOTIONS:
            self.current_emotion = emotion_name
            self.animation_frame = 0
            logger.info(f"Emotion changed to: {emotion_name}")
            return True
        return False

# ============================================================================
# DISPLAY SERVICE
# ============================================================================

class DisplayService:
    """Main display service"""
    
    def __init__(self, server_host='localhost', server_port=5000):
        """Initialize display service"""
        self.server_host = server_host
        self.server_port = server_port
        self.server_url = f"http://{server_host}:{server_port}"
        self.renderer = FaceRenderer()
        self.running = False
        self.display_window = 'JetBot OS'
        
        logger.info(f"Display service initialized: {server_url}")
    
    def get_system_state(self):
        """Get current system state from server"""
        try:
            response = requests.get(
                f"{self.server_url}/api/status",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('system', {})
        except Exception as e:
            logger.warning(f"Failed to get system state: {e}")
        return None
    
    def run(self):
        """Main display loop"""
        logger.info("Starting display service...")
        self.running = True
        
        if display_available:
            cv2.namedWindow(self.display_window, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.display_window, self.renderer.width, self.renderer.height)
        
        last_emotion_check = time.time()
        fps_timer = time.time()
        frame_count = 0
        
        try:
            while self.running:
                # Check for emotion updates every 500ms
                if time.time() - last_emotion_check > 0.5:
                    system_state = self.get_system_state()
                    if system_state:
                        current_emotion = system_state.get('current_emotion', 'neutral')
                        self.renderer.set_emotion(current_emotion)
                    last_emotion_check = time.time()
                
                # Render frame
                frame = self.renderer.render_frame()
                
                # Add FPS indicator
                frame_count += 1
                if time.time() - fps_timer > 1.0:
                    fps = frame_count
                    frame_count = 0
                    fps_timer = time.time()
                
                cv2.putText(
                    frame,
                    f"JetBot OS - {self.renderer.current_emotion.upper()} - FPS: {fps}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2
                )
                
                # Display frame
                if display_available:
                    cv2.imshow(self.display_window, frame)
                    
                    # Handle key press
                    key = cv2.waitKey(30) & 0xFF
                    if key == ord('q'):
                        logger.info("Quit command received")
                        break
                else:
                    # Headless mode - just delay
                    time.sleep(0.03)
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Display error: {e}")
        finally:
            self.running = False
            if display_available:
                cv2.destroyAllWindows()
            logger.info("Display service stopped")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("JETBOT OS - JETSON DISPLAY SERVICE")
    logger.info("=" * 70)
    
    # Configuration
    server_host = os.getenv('SERVER_HOST', 'localhost')
    server_port = os.getenv('SERVER_PORT', 5000)
    
    logger.info(f"Server: {server_host}:{server_port}")
    logger.info(f"Display Available: {display_available}")
    logger.info("=" * 70)
    
    # Run service
    service = DisplayService(server_host, server_port)
    
    try:
        service.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
