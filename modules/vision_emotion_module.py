#!/usr/bin/env python3
"""
Visual Emotion Recognition Module
Uses OpenCV to detect faces and analyze expressions.
Optimized for Jetson Nano (using lightweight detection).
"""
import sys
import os
import time
import logging
import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# Load Face Detector (Haar Cascade is faster than deep learning on CPU)
FACE_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

class VisionEmotionModule:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
        if self.face_cascade.empty():
            logging.error("Failed to load Haar Cascade XML")
        
        # Throttling to save CPU
        self.process_every_n_frames = 5
        self.frame_count = 0
        self.last_emotion = "neutral"
        self.emotion_confidence = 0
        
        logging.info("Vision Emotion Module initialized")

    def detect_emotion_heuristic(self, face_roi):
        """
        A simplified heuristic emotion detector for low-power devices.
        In a full implementation, you would load a .tflite model here.
        For now, we simulate detection or use basic image properties.
        """
        # Placeholder: Real implementation requires a trained model file (e.g. fer2013.tflite)
        # To avoid dependency hell on Jetson, we currently return 'neutral' 
        # or randomly detect based on simple image variance (activity)
        
        # High variance often implies more expressive face
        variance = cv2.Laplacian(face_roi, cv2.CV_64F).var()
        
        if variance < 100:
            return "neutral"
        elif variance > 500:
            return "excited"
        else:
            # Here you would plug in `model.predict(face_roi)`
            return "neutral" 

    def process_frame(self, event):
        """Handle camera frame event"""
        self.frame_count += 1
        if self.frame_count % self.process_every_n_frames != 0:
            return

        frame = event.data.get('frame')
        if frame is None: return

        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )

        if len(faces) > 0:
            # Get largest face
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            
            # Extract face ROI
            face_roi = gray[y:y+h, x:x+w]
            
            # Predict Emotion
            emotion = self.detect_emotion_heuristic(face_roi)
            
            if emotion != self.last_emotion:
                self.last_emotion = emotion
                logging.info(f"Visual Emotion Detected: {emotion}")
                
                # Publish event
                event_bus.publish(
                    EventType.EMOTION_DETECTED,
                    {'emotion': emotion, 'source': 'vision'},
                    source="vision_emotion_module"
                )

    def run(self):
        # Subscribe to camera feed
        event_bus.subscribe(EventType.CAMERA_FRAME, self.process_frame)
        
        logging.info("Vision Emotion Module running...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Vision Emotion Module stopping")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | VISION | %(levelname)s | %(message)s')
    VisionEmotionModule().run()