#!/usr/bin/env python3
"""
Camera Module - Handles camera streaming, photos, and video recording
"""
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

import os
import cv2
import time
import logging
import threading
from datetime import datetime
from event_bus import event_bus, EventType

class CameraModule:
    """Camera capture and streaming"""
    
    def __init__(self):
        self.camera = None
        self.is_recording = False
        self.video_writer = None
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        
        # Camera settings
        self.camera_index = 0  # CSI camera
        self.width = 1280
        self.height = 720
        self.fps = 30
        
        # Storage paths
        self.photo_dir = "/opt/jetbot/media/photos"
        self.video_dir = "/opt/jetbot/media/videos"
        
        os.makedirs(self.photo_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        
        logging.info("Camera Module initialized")
    
    def _gstreamer_pipeline(self):
        """GStreamer pipeline for CSI camera on Jetson"""
        return (
            f"nvarguscamerasrc sensor_id={self.camera_index} ! "
            f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
            f"framerate={self.fps}/1, format=NV12 ! "
            f"nvvidconv flip-method=0 ! "
            f"video/x-raw, width={self.width}, height={self.height}, format=BGRx ! "
            f"videoconvert ! video/x-raw, format=BGR ! appsink"
        )
    
    def initialize_camera(self) -> bool:
        """Initialize camera capture"""
        try:
            # Try CSI camera first (GStreamer pipeline for Jetson)
            pipeline = self._gstreamer_pipeline()
            self.camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            
            if not self.camera.isOpened():
                logging.warning("CSI camera failed, trying USB camera...")
                # Fallback to USB camera
                self.camera = cv2.VideoCapture(self.camera_index)
            
            if self.camera.isOpened():
                logging.info("Camera initialized successfully")
                return True
            else:
                logging.error("Failed to open camera")
                return False
        
        except Exception as e:
            logging.error(f"Camera initialization error: {e}")
            return False
    
    def capture_frame(self):
        """Capture single frame"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                with self.frame_lock:
                    self.latest_frame = frame
                return frame
        return None
    
    def take_photo(self) -> str:
        """Take a photo and save to disk"""
        frame = self.capture_frame()
        
        if frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
            filepath = os.path.join(self.photo_dir, filename)
            
            cv2.imwrite(filepath, frame)
            logging.info(f"Photo saved: {filepath}")
            
            # Publish event
            event_bus.publish(
                EventType.PHOTO_TAKEN,
                {'path': filepath, 'timestamp': timestamp},
                source="camera_module"
            )
            
            return filepath
        else:
            logging.error("Failed to capture photo")
            return None
    
    def start_recording(self) -> bool:
        """Start video recording"""
        if self.is_recording:
            logging.warning("Already recording")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{timestamp}.avi"
        filepath = os.path.join(self.video_dir, filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(filepath, fourcc, self.fps, (self.width, self.height))
        
        if self.video_writer.isOpened():
            self.is_recording = True
            logging.info(f"Recording started: {filepath}")
            
            event_bus.publish(
                EventType.VIDEO_RECORDING,
                {'status': 'started', 'path': filepath},
                source="camera_module"
            )
            return True
        else:
            logging.error("Failed to start recording")
            return False
    
    def stop_recording(self) -> str:
        """Stop video recording"""
        if not self.is_recording:
            logging.warning("Not recording")
            return None
        
        self.is_recording = False
        filepath = self.video_writer.release()
        self.video_writer = None
        
        logging.info("Recording stopped")
        
        event_bus.publish(
            EventType.VIDEO_RECORDING,
            {'status': 'stopped'},
            source="camera_module"
        )
        
        return filepath
    
    def streaming_loop(self):
        """Main camera streaming loop"""
        while True:
            frame = self.capture_frame()
            
            if frame is not None:
                # Publish frame event for livestream
                event_bus.publish(
                    EventType.CAMERA_FRAME,
                    {'frame': frame, 'timestamp': time.time()},
                    source="camera_module"
                )
                
                # If recording, write frame
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame)
            
            time.sleep(1.0 / self.fps)
    
    def run(self):
        """Main run loop"""
        if not self.initialize_camera():
            logging.error("Camera module failed to initialize")
            return
        
        # Start streaming thread
        stream_thread = threading.Thread(target=self.streaming_loop, daemon=True)
        stream_thread.start()
        
        logging.info("Camera Module running")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Camera Module shutting down")
            if self.camera:
                self.camera.release()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | CAMERA | %(levelname)s | %(message)s'
    )
    
    module = CameraModule()
    module.run()

if __name__ == "__main__":
    main()
