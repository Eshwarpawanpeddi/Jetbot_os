import pygame
import time
import queue
from core.event_bus import EventType, RobotEvent

def draw_face(screen, mood, mouth_open=False):
    screen.fill((0, 0, 0)) # Black background
    width, height = screen.get_size()
    
    # Colors
    WHITE = (255, 255, 255)
    BLUE = (50, 100, 255)
    RED = (255, 50, 50)
    
    eye_color = WHITE
    if mood == "ANGRY": eye_color = RED
    if mood == "SAD": eye_color = BLUE
    
    # Simple Eye Logic
    eye_radius = 60
    left_eye_pos = (width // 3, height // 2.5)
    right_eye_pos = (width * 2 // 3, height // 2.5)

    if mood == "SLEEPY":
        # Draw lines for closed eyes
        pygame.draw.line(screen, eye_color, (left_eye_pos[0]-50, left_eye_pos[1]), (left_eye_pos[0]+50, left_eye_pos[1]), 5)
        pygame.draw.line(screen, eye_color, (right_eye_pos[0]-50, right_eye_pos[1]), (right_eye_pos[0]+50, right_eye_pos[1]), 5)
    else:
        pygame.draw.circle(screen, eye_color, left_eye_pos, eye_radius)
        pygame.draw.circle(screen, eye_color, right_eye_pos, eye_radius)

    # Mouth Logic
    mouth_y = height // 1.5
    if mouth_open:
        pygame.draw.circle(screen, WHITE, (width // 2, int(mouth_y)), 30)
    else:
        if mood == "HAPPY":
            pygame.draw.arc(screen, WHITE, (width//2 - 50, mouth_y - 20, 100, 50), 3.14, 6.28, 5)
        elif mood == "SAD":
            pygame.draw.arc(screen, WHITE, (width//2 - 50, mouth_y + 10, 100, 50), 0, 3.14, 5)
        else:
            pygame.draw.line(screen, WHITE, (width//2 - 40, mouth_y), (width//2 + 40, mouth_y), 5)

    pygame.display.flip()

def run_face_module(bus, sub_queue, config):
    pygame.init()
    
    # Setup full screen or windowed based on config
    # flags = pygame.FULLSCREEN if not config['system']['debug'] else 0
    screen = pygame.display.set_mode((config['hardware']['screen_width'], config['hardware']['screen_height']))
    pygame.display.set_caption("Jetbot Face")

    current_mood = "HAPPY"
    is_speaking = False
    running = True

    while running:
        # 1. Process Events
        try:
            while True:
                event = sub_queue.get_nowait()
                if event.type == EventType.EmotionChange:
                    current_mood = event.payload
                elif event.type == EventType.Speak:
                    is_speaking = event.payload.get('active', False)
        except queue.Empty:
            pass

        # 2. Render Loop
        # Simulate mouth movement if speaking
        mouth_state = is_speaking and (int(time.time() * 10) % 2 == 0)
        
        draw_face(screen, current_mood, mouth_state)
        
        # 3. Handle Pygame Quit (Safety)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        time.sleep(0.05) # 20 FPS

    pygame.quit()
