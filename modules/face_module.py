#!/usr/bin/env python3
"""
Face Display Module - Animated face with emotions
Uses PyGame to render eyes/mouth on the display
"""
import sys
import os
import time
import logging
import threading
import random

# Headless check
os.environ['SDL_VIDEODRIVER'] = 'dummy'
# Remove the above line if you have a screen attached!

import pygame

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

class FaceModule:
    COLORS = {
        'happy': (50, 255, 50),    # Green
        'sad': (50, 100, 255),     # Blue
        'angry': (255, 50, 50),    # Red
        'neutral': (200, 200, 200),# White/Grey
        'thinking': (255, 255, 50),# Yellow
        'listening': (50, 255, 255)# Cyan
    }

    def __init__(self, width=800, height=480):
        pygame.init()
        self.width = width
        self.height = height
        
        # Setup display
        try:
            self.screen = pygame.display.set_mode((width, height))
        except pygame.error:
            # Fallback for headless
            self.screen = pygame.Surface((width, height))
            
        pygame.display.set_caption("Jetbot Face")
        
        self.current_emotion = 'neutral'
        self.is_speaking = False
        self.blink_timer = time.time()
        self.blink_interval = 3.0
        self.eyes_closed = False
        
        logging.info("Face Module initialized")

    def draw_eyes(self, color):
        if self.eyes_closed:
            # Draw lines
            pygame.draw.line(self.screen, color, (200, 200), (300, 200), 10)
            pygame.draw.line(self.screen, color, (500, 200), (600, 200), 10)
        else:
            # Draw circles (simple eyes)
            radius = 60
            if self.current_emotion == 'sad':
                # Sad eyes (droopy)
                pygame.draw.circle(self.screen, color, (250, 220), radius)
                pygame.draw.circle(self.screen, color, (550, 220), radius)
                # Eyelids
                pygame.draw.rect(self.screen, (0,0,0), (180, 150, 140, 60))
                pygame.draw.rect(self.screen, (0,0,0), (480, 150, 140, 60))
            elif self.current_emotion == 'happy':
                # Happy eyes (arches)
                pygame.draw.arc(self.screen, color, (200, 180, 100, 100), 0, 3.14, 10)
                pygame.draw.arc(self.screen, color, (500, 180, 100, 100), 0, 3.14, 10)
            else:
                # Normal
                pygame.draw.circle(self.screen, color, (250, 200), radius)
                pygame.draw.circle(self.screen, color, (550, 200), radius)

    def draw_mouth(self, color):
        center_x = self.width // 2
        center_y = 350
        
        if self.is_speaking:
            # Animated mouth (circle growing/shrinking)
            radius = random.randint(10, 30)
            pygame.draw.circle(self.screen, color, (center_x, center_y), radius)
        else:
            if self.current_emotion == 'happy':
                pygame.draw.arc(self.screen, color, (center_x-50, center_y-30, 100, 60), 3.14, 6.28, 5)
            elif self.current_emotion == 'sad':
                pygame.draw.arc(self.screen, color, (center_x-50, center_y+10, 100, 60), 0, 3.14, 5)
            else:
                pygame.draw.line(self.screen, color, (center_x-40, center_y), (center_x+40, center_y), 5)

    def update(self):
        # Handle Blinking
        if not self.eyes_closed and (time.time() - self.blink_timer > self.blink_interval):
            self.eyes_closed = True
            self.blink_timer = time.time()
        elif self.eyes_closed and (time.time() - self.blink_timer > 0.15):
            self.eyes_closed = False
            self.blink_timer = time.time()
            self.blink_interval = random.uniform(2.0, 6.0)

        # Draw
        self.screen.fill((0, 0, 0))
        color = self.COLORS.get(self.current_emotion, self.COLORS['neutral'])
        
        self.draw_eyes(color)
        self.draw_mouth(color)
        
        pygame.display.flip()

    def handle_emotion(self, event):
        self.current_emotion = event.data.get('emotion', 'neutral')
        
    def handle_voice_status(self, event):
        status = event.data.get('status')
        if status == 'start':
            self.is_speaking = True
        elif status == 'end':
            self.is_speaking = False

    def handle_listening(self, event):
        # When user speaks, look attentive
        self.current_emotion = 'listening'

    def run(self):
        event_bus.subscribe(EventType.FACE_EMOTION, self.handle_emotion)
        event_bus.subscribe(EventType.VOICE_OUTPUT, self.handle_voice_status)
        event_bus.subscribe(EventType.VOICE_INPUT, self.handle_listening)
        
        logging.info("Face Module running loop...")
        clock = pygame.time.Clock()
        
        try:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: return
                self.update()
                clock.tick(30)
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | FACE | %(levelname)s | %(message)s')
    FaceModule().run()