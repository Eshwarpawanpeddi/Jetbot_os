#!/usr/bin/env python3
"""
ESP12E Motor Controller
Handles WiFi communication with ESP12E microcontroller
Uses JSON over HTTP for reliable command transmission
"""

import requests
import json
import time
import logging
from typing import Dict, Optional, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MotorCommand(Enum):
    """Motor control commands"""
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    STOP = "stop"


class ESP12EController:
    """
    Controller for ESP12E microcontroller via WiFi
    
    Commands are sent as JSON over HTTP POST requests
    ESP12E listens on port 80 by default
    """
    
    def __init__(self, esp12e_ip: str, timeout: int = 5):
        """
        Initialize ESP12E controller
        
        Args:
            esp12e_ip: IP address of ESP12E (e.g., "192.168.1.50")
            timeout: Request timeout in seconds
        """
        self.esp12e_ip = esp12e_ip
        self.base_url = f"http://{esp12e_ip}"
        self.timeout = timeout
        self.connected = False
        
        # Motor parameters
        self.motor_speed = 255  # 0-255
        self.motor_pins = {
            'left_fwd': 5,   # GPIO5
            'left_bwd': 4,   # GPIO4
            'right_fwd': 0,  # GPIO0
            'right_bwd': 2   # GPIO2
        }
        
        logger.info(f"ESP12E Controller initialized: {esp12e_ip}")
    
    def test_connection(self) -> bool:
        """Test connection to ESP12E"""
        try:
            response = requests.get(
                f"{self.base_url}/status",
                timeout=self.timeout
            )
            if response.status_code == 200:
                self.connected = True
                logger.info(f"✓ Connected to ESP12E at {self.esp12e_ip}")
                return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            self.connected = False
        return False
    
    def send_command(self, command: Dict) -> bool:
        """
        Send command to ESP12E via JSON
        
        Args:
            command: Dictionary with command parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.warning("ESP12E not connected, attempting reconnection...")
            if not self.test_connection():
                return False
        
        try:
            response = requests.post(
                f"{self.base_url}/api/motor",
                json=command,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"Command sent: {command}")
                return True
            else:
                logger.error(f"Command failed: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout - ESP12E may be unresponsive")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Command error: {e}")
            return False
    
    def move_forward(self, speed: int = 255) -> bool:
        """Move robot forward"""
        command = {
            'action': 'motor',
            'direction': 'forward',
            'speed': min(255, max(0, speed)),
            'duration': 0  # 0 = continuous
        }
        return self.send_command(command)
    
    def move_backward(self, speed: int = 255) -> bool:
        """Move robot backward"""
        command = {
            'action': 'motor',
            'direction': 'backward',
            'speed': min(255, max(0, speed)),
            'duration': 0
        }
        return self.send_command(command)
    
    def turn_left(self, speed: int = 200) -> bool:
        """Turn robot left"""
        command = {
            'action': 'motor',
            'direction': 'left',
            'speed': min(255, max(0, speed)),
            'duration': 0
        }
        return self.send_command(command)
    
    def turn_right(self, speed: int = 200) -> bool:
        """Turn robot right"""
        command = {
            'action': 'motor',
            'direction': 'right',
            'speed': min(255, max(0, speed)),
            'duration': 0
        }
        return self.send_command(command)
    
    def stop(self) -> bool:
        """Stop all motors"""
        command = {
            'action': 'motor',
            'direction': 'stop',
            'speed': 0,
            'duration': 0
        }
        return self.send_command(command)
    
    def move_timed(self, direction: str, duration_ms: int, speed: int = 255) -> bool:
        """
        Move for specific duration
        
        Args:
            direction: 'forward', 'backward', 'left', 'right'
            duration_ms: Duration in milliseconds
            speed: Motor speed (0-255)
        """
        command = {
            'action': 'motor',
            'direction': direction,
            'speed': min(255, max(0, speed)),
            'duration': duration_ms
        }
        return self.send_command(command)
    
    def read_sensor(self, sensor_type: str) -> Optional[float]:
        """
        Read sensor data from ESP12E
        
        Args:
            sensor_type: 'distance', 'battery', 'temperature'
            
        Returns:
            Sensor reading or None if failed
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/sensor/{sensor_type}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                value = data.get('value')
                logger.debug(f"Sensor {sensor_type}: {value}")
                return value
                
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
        
        return None
    
    def get_status(self) -> Optional[Dict]:
        """Get full system status from ESP12E"""
        try:
            response = requests.get(
                f"{self.base_url}/status",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            logger.error(f"Status read error: {e}")
        
        return None
    
    def calibrate_motors(self) -> bool:
        """Calibrate motor responses"""
        command = {
            'action': 'calibrate',
            'type': 'motors'
        }
        return self.send_command(command)


# Example usage
if __name__ == "__main__":
    # Replace with your ESP12E IP address
    esp12e = ESP12EController("192.168.1.50")
    
    # Test connection
    if esp12e.test_connection():
        print("✓ Connected to ESP12E")
        
        # Test motor commands
        print("Moving forward...")
        esp12e.move_forward(speed=200)
        time.sleep(2)
        
        print("Turning left...")
        esp12e.turn_left(speed=180)
        time.sleep(1)
        
        print("Stopping...")
        esp12e.stop()
        
        # Read sensors
        distance = esp12e.read_sensor("distance")
        battery = esp12e.read_sensor("battery")
        print(f"Distance: {distance}cm, Battery: {battery}V")
        
        # Get full status
        status = esp12e.get_status()
        print(f"System Status: {json.dumps(status, indent=2)}")
    else:
        print("✗ Failed to connect to ESP12E")

