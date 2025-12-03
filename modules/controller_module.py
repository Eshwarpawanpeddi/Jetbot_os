#!/usr/bin/env python3
import sys
import os
import time
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.event_bus import event_bus, EventType

# Set dummy driver to prevent crash on headless systems
os.environ["SDL_VIDEODRIVER"] = "dummy"

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

class ControllerModule:
    def __init__(self):
        self.controller = None
        self.current_mode = "auto"
        if PYGAME_AVAILABLE:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                logging.info(f"Controller: {self.controller.get_name()}")
            else:
                logging.warning("No joystick detected.")
        else:
            logging.warning("Pygame not installed.")

    def run(self):
        logging.info("Controller running (Headless Mode)")
        try:
            while True:
                if self.controller:
                    pygame.event.pump()
                    # Axis 1 is Left Stick Y (Speed), Axis 0 is Left Stick X (Turn)
                    speed = -self.controller.get_axis(1)
                    turn = self.controller.get_axis(0)
                    
                    if abs(speed) > 0.1 or abs(turn) > 0.1:
                         # Simple steering mix
                        left = speed + turn
                        right = speed - turn
                        # Clamp
                        left = max(-1, min(1, left))
                        right = max(-1, min(1, right))
                        
                        event_bus.publish(EventType.MOVEMENT_COMMAND, 
                            {'left_motor': left, 'right_motor': right}, "controller")
                time.sleep(0.05)
        except KeyboardInterrupt: pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | CTRL | %(levelname)s | %(message)s')
    ControllerModule().run()
