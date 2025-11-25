#!/usr/bin/env python3
"""
Face Display Module - Animated face with emotions and status display
Displays on Jetson-attached screen using pygame
"""
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

import os
import sys
import time
import logging
import pygame
import threading
from datetime import datetime
from event_bus import event_bus, EventType

class FaceModule:
    """Animated face display with emotions"""
    
    # Emotion definitions (eye and mouth shapes)
    EMOTIONS = {
        'happy': {
            'eyes': 'open',
            'mouth': 'smile',
            'color': (50, 200, 50)
        },
        'sad': {
            'eyes': 'open',
            'mouth': 'frown',
            'color': (100, 100, 255)
        },
        'angry': {
            'eyes': 'angry',
            'mouth': 'frown',
            'color': (255, 50, 50)
        },
        'crying': {
            'eyes': 'crying',
            'mouth': 'frown',
            'color': (100, 150, 255)
        },
        'excited': {
            'eyes': 'wide',
            'mouth': 'smile',
            'color': (255, 200, 50)
        },
        'sleepy': {
            'eyes': 'sleepy',
            'mouth': 'neutral',
            'color': (150, 150, 200)
        },
        'thinking': {
            'eyes': 'looking_up',
            'mouth': 'neutral',
            'color': (200, 200, 100)
        },
        'confused': {
            'eyes': 'asymmetric',
            'mouth': 'wavy',
            'color': (255, 150, 100)
        },
        'neutral': {
            'eyes': 'open',
            'mouth': 'neutral',
            'color': (150, 150, 150)
        }
    }
    
    def __init__(self, width=800, height=480):
        pygame.init()
        
        # Try to use actual display, fallback to virtual display
        try:
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption("Jetbot Face")
        except:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            self.screen = pygame.display.set_mode((width, height))
        
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()
        
        # State
        self.current_emotion = 'neutral'
        self.is_speaking = False
        self.status_text = ""
        self.display_text = ""
        
        # Animation
        self.blink_timer = 0
        self.blink_duration = 0.2
        self.next_blink = time.time() + 3
        self.is_blinking = False
        
        self.mouth_animation_frame = 0
        self.mouth_animation_speed = 10
        
        # Font
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Colors
        self.bg_color = (20, 20, 30)
        
        logging.info(f"Face Module initialized ({width}x{height})")
    
    def set_emotion(self, emotion: str):
        """Change facial emotion"""
        if emotion in self.EMOTIONS:
            self.current_emotion = emotion
            logging.info(f"Face emotion changed to: {emotion}")
        else:
            logging.warning(f"Unknown emotion: {emotion}")
    
    def set_speaking(self, speaking: bool):
        """Set speaking state"""
        self.is_speaking = speaking
    
    def set_status(self, text: str):
        """Display status message"""
        self.status_text = text
        logging.info(f"Status: {text}")
    
    def set_text(self, text: str):
        """Display text message"""
        self.display_text = text
    
    def draw_eyes(self, emotion_data: dict):
        """Draw eyes based on emotion"""
        eye_type = emotion_data['eyes']
        color = emotion_data['color']
        
        # Eye positions
        left_eye_center = (self.width // 3, self.height // 3)
        right_eye_center = (2 * self.width // 3, self.height // 3)
        eye_radius = 60
        pupil_radius = 30
        
        if self.is_blinking:
            # Draw closed eyes (horizontal lines)
            pygame.draw.line(self.screen, color,
                           (left_eye_center[0] - eye_radius, left_eye_center[1]),
                           (left_eye_center[0] + eye_radius, left_eye_center[1]), 8)
            pygame.draw.line(self.screen, color,
                           (right_eye_center[0] - eye_radius, right_eye_center[1]),
                           (right_eye_center[0] + eye_radius, right_eye_center[1]), 8)
            return
        
        # Draw based on eye type
        if eye_type == 'open':
            # Normal open eyes
            pygame.draw.circle(self.screen, color, left_eye_center, eye_radius, 5)
            pygame.draw.circle(self.screen, color, right_eye_center, eye_radius, 5)
            pygame.draw.circle(self.screen, color, left_eye_center, pupil_radius)
            pygame.draw.circle(self.screen, color, right_eye_center, pupil_radius)
        
        elif eye_type == 'wide':
            # Wide eyes (excited)
            pygame.draw.circle(self.screen, color, left_eye_center, eye_radius + 10, 5)
            pygame.draw.circle(self.screen, color, right_eye_center, eye_radius + 10, 5)
            pygame.draw.circle(self.screen, color, left_eye_center, pupil_radius + 5)
            pygame.draw.circle(self.screen, color, right_eye_center, pupil_radius + 5)
        
        elif eye_type == 'angry':
            # Angled eyes
            pygame.draw.line(self.screen, color,
                           (left_eye_center[0] - eye_radius, left_eye_center[1] + 20),
                           (left_eye_center[0] + eye_radius, left_eye_center[1] - 20), 8)
            pygame.draw.line(self.screen, color,
                           (right_eye_center[0] - eye_radius, right_eye_center[1] - 20),
                           (right_eye_center[0] + eye_radius, right_eye_center[1] + 20), 8)
        
        elif eye_type == 'sleepy':
            # Half-closed eyes
            pygame.draw.arc(self.screen, color,
                          (left_eye_center[0] - eye_radius, left_eye_center[1] - eye_radius,
                           eye_radius * 2, eye_radius * 2), 0, 3.14, 8)
            pygame.draw.arc(self.screen, color,
                          (right_eye_center[0] - eye_radius, right_eye_center[1] - eye_radius,
                           eye_radius * 2, eye_radius * 2), 0, 3.14, 8)
        
        elif eye_type == 'crying':
            # Eyes with tears
            pygame.draw.circle(self.screen, color, left_eye_center, eye_radius, 5)
            pygame.draw.circle(self.screen, color, right_eye_center, eye_radius, 5)
            # Tears
            pygame.draw.circle(self.screen, (100, 150, 255),
                             (left_eye_center[0], left_eye_center[1] + eye_radius + 20), 10)
            pygame.draw.circle(self.screen, (100, 150, 255),
                             (right_eye_center[0], right_eye_center[1] + eye_radius + 20), 10)
        
        elif eye_type == 'looking_up':
            # Eyes looking up (thinking)
            pygame.draw.circle(self.screen, color, left_eye_center, eye_radius, 5)
            pygame.draw.circle(self.screen, color, right_eye_center, eye_radius, 5)
            pygame.draw.circle(self.screen, color,
                             (left_eye_center[0], left_eye_center[1] - 20), pupil_radius)
            pygame.draw.circle(self.screen, color,
                             (right_eye_center[0], right_eye_center[1] - 20), pupil_radius)
        
        elif eye_type == 'asymmetric':
            # One eye bigger (confused)
            pygame.draw.circle(self.screen, color, left_eye_center, eye_radius, 5)
            pygame.draw.circle(self.screen, color, right_eye_center, eye_radius + 15, 5)
    
    def draw_mouth(self, emotion_data: dict):
        """Draw mouth based on emotion"""
        mouth_type = emotion_data['mouth']
        color = emotion_data['color']
        
        mouth_center = (self.width // 2, 2 * self.height // 3)
        mouth_width = 200
        mouth_height = 60
        
        if self.is_speaking:
            # Animate mouth when speaking
            frame_offset = (self.mouth_animation_frame % 20) - 10
            mouth_height += abs(frame_offset)
        
        if mouth_type == 'smile':
            # Happy smile
            pygame.draw.arc(self.screen, color,
                          (mouth_center[0] - mouth_width // 2, mouth_center[1] - mouth_height // 2,
                           mouth_width, mouth_height), 3.14, 0, 8)
        
        elif mouth_type == 'frown':
            # Sad frown
            pygame.draw.arc(self.screen, color,
                          (mouth_center[0] - mouth_width // 2, mouth_center[1],
                           mouth_width, mouth_height), 0, 3.14, 8)
        
        elif mouth_type == 'neutral':
            # Neutral line
            pygame.draw.line(self.screen, color,
                           (mouth_center[0] - mouth_width // 2, mouth_center[1]),
                           (mouth_center[0] + mouth_width // 2, mouth_center[1]), 8)
        
        elif mouth_type == 'wavy':
            # Confused wavy mouth
            points = []
            for i in range(10):
                x = mouth_center[0] - mouth_width // 2 + (mouth_width * i // 9)
                y = mouth_center[1] + (20 if i % 2 == 0 else -20)
                points.append((x, y))
            pygame.draw.lines(self.screen, color, False, points, 8)
    
    def draw_status_bar(self):
        """Draw status bar at top"""
        if self.status_text:
            text_surface = self.small_font.render(self.status_text, True, (200, 200, 200))
            text_rect = text_surface.get_rect(center=(self.width // 2, 30))
            self.screen.blit(text_surface, text_rect)
    
    def draw_text_display(self):
        """Draw text at bottom"""
        if self.display_text:
            # Word wrap
            words = self.display_text.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + word + " "
                if self.font.size(test_line)[0] < self.width - 40:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word + " "
            lines.append(current_line)
            
            y_offset = self.height - 100
            for line in lines[-2:]:  # Show max 2 lines
                text_surface = self.font.render(line.strip(), True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(self.width // 2, y_offset))
                self.screen.blit(text_surface, text_rect)
                y_offset += 40
    
    def update_animations(self):
        """Update animation states"""
        current_time = time.time()
        
        # Blink animation
        if current_time >= self.next_blink:
            self.is_blinking = True
            self.blink_timer = current_time
            self.next_blink = current_time + (2 + (hash(str(current_time)) % 4))
        
        if self.is_blinking and (current_time - self.blink_timer) > self.blink_duration:
            self.is_blinking = False
        
        # Mouth animation
        if self.is_speaking:
            self.mouth_animation_frame += 1
    
    def render(self):
        """Render one frame"""
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Get current emotion data
        emotion_data = self.EMOTIONS[self.current_emotion]
        
        # Draw face components
        self.draw_eyes(emotion_data)
        self.draw_mouth(emotion_data)
        
        # Draw overlays
        self.draw_status_bar()
        self.draw_text_display()
        
        # Update display
        pygame.display.flip()
    
    def handle_emotion_event(self, event):
        """Handle emotion change events"""
        emotion = event.data.get('emotion', 'neutral')
        self.set_emotion(emotion)
    
    def handle_status_event(self, event):
        """Handle status display events"""
        status = event.data.get('status', '')
        self.set_status(status)
    
    def handle_text_event(self, event):
        """Handle text display events"""
        text = event.data.get('text', '')
        self.set_text(text)
    
    def handle_voice_output(self, event):
        """Handle voice output events (speaking)"""
        text = event.data.get('text', '')
        self.set_text(text)
        self.set_speaking(True)
        
        # Stop speaking after estimated duration
        words = len(text.split())
        duration = words * 0.5  # ~0.5 seconds per word
        
        def stop_speaking():
            time.sleep(duration)
            self.set_speaking(False)
        
        threading.Thread(target=stop_speaking, daemon=True).start()
    
    def run(self):
        """Main run loop"""
        # Subscribe to events
        event_bus.subscribe(EventType.FACE_EMOTION, self.handle_emotion_event)
        event_bus.subscribe(EventType.FACE_STATUS, self.handle_status_event)
        event_bus.subscribe(EventType.FACE_TEXT, self.handle_text_event)
        event_bus.subscribe(EventType.VOICE_OUTPUT, self.handle_voice_output)
        event_bus.subscribe(EventType.LLM_RESPONSE, self.handle_text_event)
        
        logging.info("Face Module running")
        
        try:
            running = True
            while running:
                # Handle pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                
                # Update animations
                self.update_animations()
                
                # Render frame
                self.render()
                
                # Maintain 30 FPS
                self.clock.tick(30)
        
        except KeyboardInterrupt:
            logging.info("Face Module shutting down")
        finally:
            pygame.quit()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | FACE | %(levelname)s | %(message)s'
    )
    
    module = FaceModule()
    module.run()

if __name__ == "__main__":
    main()
