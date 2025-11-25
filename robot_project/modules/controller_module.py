#!/usr/bin/env python3
"""
Controller Module - Handle manual controller input for robot movement
Supports various game controllers (PS4, Xbox, Generic)
"""

import time
import logging
import threading
from event_bus import event_bus, EventType

# Try to import pygame for controller support
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("pygame not available - controller module will run in stub mode")

class ControllerModule:
    """Manual controller input handler"""
    
    def __init__(self):
        self.controller = None
        self.is_active = False
        self.current_mode = "auto"  # auto or manual
        
        if PYGAME_AVAILABLE:
            pygame.init()
            pygame.joystick.init()
        
        logging.info("Controller Module initialized")
    
    def initialize_controller(self) -> bool:
        """Initialize game controller"""
        if not PYGAME_AVAILABLE:
            logging.warning("Controller support not available")
            return False
        
        try:
            joystick_count = pygame.joystick.get_count()
            
            if joystick_count == 0:
                logging.warning("No controller detected")
                return False
            
            self.controller = pygame.joystick.Joystick(0)
            self.controller.init()
            
            logging.info(f"Controller connected: {self.controller.get_name()}")
            logging.info(f"Axes: {self.controller.get_numaxes()}, Buttons: {self.controller.get_numbuttons()}")
            
            return True
        
        except Exception as e:
            logging.error(f"Controller initialization error: {e}")
            return False
    
    def get_controller_input(self) -> dict:
        """Read current controller state"""
        if not self.controller:
            return None
        
        pygame.event.pump()
        
        # Read axes (joysticks)
        # Typically: axis 0 = left X, axis 1 = left Y, axis 2 = right X, axis 3 = right Y
        left_x = self.controller.get_axis(0) if self.controller.get_numaxes() > 0 else 0
        left_y = self.controller.get_axis(1) if self.controller.get_numaxes() > 1 else 0
        right_x = self.controller.get_axis(2) if self.controller.get_numaxes() > 2 else 0
        right_y = self.controller.get_axis(3) if self.controller.get_numaxes() > 3 else 0
        
        # Read buttons
        buttons = {}
        for i in range(self.controller.get_numbuttons()):
            buttons[i] = self.controller.get_button(i)
        
        return {
            'left_stick': {'x': left_x, 'y': left_y},
            'right_stick': {'x': right_x, 'y': right_y},
            'buttons': buttons
        }
    
    def process_input(self, input_data: dict):
        """Process controller input and publish movement commands"""
        if not input_data:
            return
        
        # Check mode switch button (button 9 - typically Start button)
        if input_data['buttons'].get(9):
            self.toggle_mode()
            time.sleep(0.3)  # Debounce
        
        # Only process movement in manual mode
        if self.current_mode != "manual":
            return
        
        # Get left stick for movement (forward/backward/turn)
        left_x = input_data['left_stick']['x']
        left_y = -input_data['left_stick']['y']  # Invert Y axis
        
        # Apply deadzone
        deadzone = 0.15
        if abs(left_x) < deadzone:
            left_x = 0
        if abs(left_y) < deadzone:
            left_y = 0
        
        # Calculate motor speeds (differential drive)
        # left_y = forward/backward, left_x = turning
        speed = left_y
        turn = left_x
        
        left_motor = speed + turn
        right_motor = speed - turn
        
        # Clamp to [-1, 1]
        left_motor = max(-1, min(1, left_motor))
        right_motor = max(-1, min(1, right_motor))
        
        # Publish movement command
        if abs(left_motor) > 0.01 or abs(right_motor) > 0.01:
            event_bus.publish(
                EventType.MOVEMENT_COMMAND,
                {
                    'left_motor': left_motor,
                    'right_motor': right_motor,
                    'source': 'controller'
                },
                source="controller_module"
            )
    
    def toggle_mode(self):
        """Toggle between manual and auto mode"""
        self.current_mode = "auto" if self.current_mode == "manual" else "manual"
        
        logging.info(f"Mode switched to: {self.current_mode.upper()}")
        
        # Publish mode change event
        event_bus.publish(
            EventType.MODE_CHANGED,
            {'mode': self.current_mode},
            source="controller_module"
        )
        
        # Update face status
        event_bus.publish(
            EventType.FACE_STATUS,
            {'status': f"Mode: {self.current_mode.upper()}"},
            source="controller_module"
        )
    
    def handle_mode_change(self, event):
        """Handle external mode change events"""
        mode = event.data.get('mode')
        if mode in ['auto', 'manual']:
            self.current_mode = mode
            logging.info(f"Mode changed externally to: {mode}")
    
    def run(self):
        """Main run loop"""
        # Subscribe to mode change events
        event_bus.subscribe(EventType.MODE_CHANGED, self.handle_mode_change)
        
        # Try to initialize controller
        if not self.initialize_controller():
            logging.warning("Running without controller")
        
        logging.info("Controller Module running")
        
        try:
            while True:
                if self.controller:
                    input_data = self.get_controller_input()
                    self.process_input(input_data)
                
                time.sleep(0.05)  # 20Hz update rate
        
        except KeyboardInterrupt:
            logging.info("Controller Module shutting down")
        finally:
            if PYGAME_AVAILABLE:
                pygame.quit()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | CONTROLLER | %(levelname)s | %(message)s'
    )
    
    module = ControllerModule()
    module.run()

if __name__ == "__main__":
    main()
