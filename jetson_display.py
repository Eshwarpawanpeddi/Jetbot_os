#!/usr/bin/env python3
"""
Jetson Nano Display - Enhanced Face Renderer Integration
Updated: December 7, 2025
Version: 2.0.0

This module handles all display rendering for the AI Pet Robot.
Uses the enhanced face renderer for professional, expressive animations.
"""

import cv2
import numpy as np
import socket
import threading
import time
import logging
from collections import deque
from enhanced_face_renderer import FaceRenderer, Emotion
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JetsonDisplay:
    """
    Jetson Nano Display Manager
    Handles face rendering and HDMI output with server communication
    """
    
    def __init__(self, config_path: str = 'config.json', 
                 server_host: str = '192.168.1.101', 
                 server_port: int = 5001):
        """
        Initialize Jetson Display
        
        Args:
            config_path: Path to configuration file
            server_host: Server IP address
            server_port: Server port for communication
        """
        self.server_host = server_host
        self.server_port = server_port
        self.running = True
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize enhanced face renderer
        display_width = self.config.get('display', {}).get('width', 1280)
        display_height = self.config.get('display', {}).get('height', 720)
        self.face_renderer = FaceRenderer(width=display_width, height=display_height)
        
        # State management
        self.current_emotion = Emotion.NEUTRAL
        self.speech_active = False
        self.mouth_position = 0
        self.text_display = ""
        
        # Camera (optional)
        self.camera = cv2.VideoCapture(0)
        self.camera_available = self.camera.isOpened()
        
        # Performance tracking
        self.fps_counter = deque(maxlen=30)
        self.frame_count = 0
        
        # Communication
        self.socket = None
        self.server_connected = False
        
        logger.info("✓ Jetson Display initialized")
        logger.info(f"  - Resolution: {display_width}x{display_height}")
        logger.info(f"  - Camera: {'Available' if self.camera_available else 'Not available'}")
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"✓ Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {
                'display': {'width': 1280, 'height': 720, 'fps': 30},
                'server': {'host': self.server_host, 'port': self.server_port}
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
            return {}
    
    def connect_to_server(self) -> bool:
        """
        Connect to Flask server for communication
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.server_host, self.server_port))
            self.server_connected = True
            logger.info(f"✓ Connected to server at {self.server_host}:{self.server_port}")
            return True
        except socket.timeout:
            logger.warning(f"Connection timeout to {self.server_host}:{self.server_port}")
            return False
        except ConnectionRefusedError:
            logger.warning(f"Server refused connection at {self.server_host}:{self.server_port}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def update_emotion(self, emotion: str):
        """
        Update current emotion from server
        
        Args:
            emotion: Emotion name (string)
        """
        try:
            emotion_enum = Emotion[emotion.upper()]
            self.current_emotion = emotion_enum
            logger.info(f"Emotion updated: {emotion}")
        except KeyError:
            logger.warning(f"Unknown emotion: {emotion}, defaulting to NEUTRAL")
            self.current_emotion = Emotion.NEUTRAL
    
    def update_mouth_for_speech(self, speech_data: dict):
        """
        Update mouth position for speech synchronization
        
        Args:
            speech_data: Dict with 'active' (bool) and 'position' (int) keys
        """
        self.speech_active = speech_data.get('active', False)
        self.mouth_position = speech_data.get('position', 0)
    
    def update_text_display(self, text: str):
        """
        Update text to display at bottom of screen
        
        Args:
            text: Text to display
        """
        self.text_display = text[:50]  # Limit to 50 chars
    
    def display_generation_loop(self):
        """Main display generation and rendering loop"""
        logger.info("Starting display generation loop...")
        
        frame_count = 0
        last_time = time.time()
        last_fps_log = time.time()
        
        try:
            # Create display window
            window_title = self.config.get('display', {}).get('window_title', 
                                                              'AI Pet Robot - Face Display')
            cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
            
            # Set window size
            width = self.config.get('display', {}).get('width', 1280)
            height = self.config.get('display', {}).get('height', 720)
            cv2.resizeWindow(window_title, width, height)
            
            logger.info("Display window created successfully")
            
            while self.running:
                current_time = time.time()
                frame_time = current_time - last_time
                last_time = current_time
                
                # Render face using enhanced renderer
                display_frame = self.face_renderer.render_face(
                    emotion=self.current_emotion,
                    speech_active=self.speech_active,
                    mouth_position=self.mouth_position
                )
                
                # Add text overlay if present
                if self.text_display:
                    cv2.putText(display_frame, self.text_display, (50, height - 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                
                # Display the frame
                cv2.imshow(window_title, display_frame)
                
                # FPS tracking
                if frame_time > 0:
                    current_fps = 1.0 / frame_time
                    self.fps_counter.append(current_fps)
                
                # Log FPS every 2 seconds
                if current_time - last_fps_log >= 2.0:
                    avg_fps = np.mean(self.fps_counter) if self.fps_counter else 0
                    logger.info(f"Avg FPS: {avg_fps:.1f} | Emotion: {self.current_emotion.value}")
                    last_fps_log = current_time
                
                # Handle keyboard input (for testing)
                key = cv2.waitKey(33) & 0xFF  # ~30 FPS
                if key == ord('q'):
                    logger.info("Quit command received")
                    self.running = False
                elif key == ord('h'):
                    self.update_emotion('happy')
                elif key == ord('s'):
                    self.update_emotion('sad')
                elif key == ord('e'):
                    self.update_emotion('excited')
                elif key == ord('n'):
                    self.update_emotion('neutral')
                elif key == ord('c'):
                    self.update_emotion('confused')
                elif key == ord('a'):
                    self.update_emotion('angry')
                elif key == ord('t'):
                    self.update_emotion('thinking')
                elif key == ord('l'):
                    self.update_emotion('love')
                
                frame_count += 1
                
        except KeyboardInterrupt:
            logger.info("Display interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Error in display loop: {e}")
        finally:
            cv2.destroyAllWindows()
            logger.info("Display window closed")
    
    def camera_capture_loop(self):
        """Optional: Capture camera feed in background"""
        if not self.camera_available:
            logger.warning("Camera not available, skipping capture loop")
            return
        
        logger.info("Starting camera capture loop...")
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                if ret:
                    # Could be used to overlay on face or send to server
                    self.camera_frame = frame
                else:
                    logger.warning("Failed to read camera frame")
                    break
                
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Camera capture error: {e}")
        finally:
            if self.camera:
                self.camera.release()
    
    def run(self):
        """Start the Jetson Display system"""
        logger.info("=" * 70)
        logger.info("JETSON NANO DISPLAY - INITIALIZATION")
        logger.info("=" * 70)
        
        # Try to connect to server
        if self.connect_to_server():
            self.server_connected = True
        else:
            logger.warning("Could not connect to server, running in standalone mode")
        
        # Start camera capture in background (optional)
        if self.camera_available:
            camera_thread = threading.Thread(target=self.camera_capture_loop, daemon=True)
            camera_thread.start()
        
        # Start main display loop
        logger.info("=" * 70)
        logger.info("DISPLAY READY - Press keys to test emotions:")
        logger.info("  h=Happy, s=Sad, e=Excited, n=Neutral")
        logger.info("  c=Confused, a=Angry, t=Thinking, l=Love")
        logger.info("  q=Quit")
        logger.info("=" * 70)
        
        try:
            self.display_generation_loop()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the display system"""
        logger.info("Shutting down Jetson Display...")
        self.running = False
        
        if self.camera:
            self.camera.release()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        logger.info("✓ Display shutdown complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Jetson Nano Display Manager')
    parser.add_argument('--config', default='config.json', help='Config file path')
    parser.add_argument('--host', default='192.168.1.101', help='Server host IP')
    parser.add_argument('--port', type=int, default=5001, help='Server port')
    
    args = parser.parse_args()
    
    # Create and run display
    display = JetsonDisplay(
        config_path=args.config,
        server_host=args.host,
        server_port=args.port
    )
    display.run()


if __name__ == "__main__":
    main()
