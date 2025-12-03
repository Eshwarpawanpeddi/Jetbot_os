#!/usr/bin/env python3
"""
Battery Monitoring Module
Monitors battery level and publishes status
"""

import os
import sys
import time
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

class BatteryModule:
    """Battery monitoring and management"""
    
    def __init__(self):
        self.battery_level = 100
        self.is_charging = False
        self.low_battery_threshold = 20
        self.critical_battery_threshold = 10
        
        # Try to detect Jetson power management
        self.battery_path = self._find_battery_path()
        
        logging.info("Battery Module initialized")
    
    def _find_battery_path(self):
        """Find battery information path"""
        possible_paths = [
            '/sys/class/power_supply/battery/capacity',
            '/sys/class/power_supply/BAT0/capacity',
            '/sys/class/power_supply/BAT1/capacity'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logging.info(f"Battery found at: {path}")
                return path
        
        logging.warning("No battery detected - using simulation mode")
        return None
    
    def read_battery_level(self):
        """Read current battery level"""
        if self.battery_path:
            try:
                with open(self.battery_path, 'r') as f:
                    level = int(f.read().strip())
                return level
            except Exception as e:
                logging.error(f"Failed to read battery: {e}")
                return self.battery_level
        else:
            # Simulation mode - slowly decrease
            self.battery_level = max(0, self.battery_level - 0.1)
            return int(self.battery_level)
    
    def check_charging_status(self):
        """Check if battery is charging"""
        status_path = self.battery_path.replace('capacity', 'status') if self.battery_path else None
        
        if status_path and os.path.exists(status_path):
            try:
                with open(status_path, 'r') as f:
                    status = f.read().strip()
                return status == 'Charging'
            except:
                return False
        return False
    
    def publish_battery_status(self):
        """Publish battery status to event bus"""
        event_bus.publish(
            EventType.BATTERY_STATUS,
            {
                'level': self.battery_level,
                'charging': self.is_charging,
                'status': self._get_battery_status_text()
            },
            source='battery_module'
        )
    
    def _get_battery_status_text(self):
        """Get battery status description"""
        if self.is_charging:
            return "charging"
        elif self.battery_level >= 80:
            return "good"
        elif self.battery_level >= self.low_battery_threshold:
            return "normal"
        elif self.battery_level >= self.critical_battery_threshold:
            return "low"
        else:
            return "critical"
    
    def handle_low_battery(self):
        """Handle low battery situation"""
        logging.warning(f"Low battery: {self.battery_level}%")
        
        event_bus.publish(
            EventType.LOW_BATTERY,
            {'level': self.battery_level},
            source='battery_module'
        )
    
    def handle_critical_battery(self):
        """Handle critical battery - initiate safe shutdown"""
        logging.critical(f"Critical battery: {self.battery_level}%")
        
        event_bus.publish(
            EventType.CRITICAL_BATTERY,
            {'level': self.battery_level},
            source='battery_module'
        )
        
        # Stop all movement
        event_bus.publish(
            EventType.MOVEMENT_COMMAND,
            {'left_motor': 0, 'right_motor': 0},
            source='battery_module'
        )
    
    def run(self):
        """Main run loop"""
        logging.info("Battery Module running")
        
        low_battery_warned = False
        
        try:
            while True:
                # Read battery level
                self.battery_level = self.read_battery_level()
                self.is_charging = self.check_charging_status()
                
                # Publish status
                self.publish_battery_status()
                
                # Check thresholds
                if self.battery_level <= self.critical_battery_threshold and not self.is_charging:
                    self.handle_critical_battery()
                elif self.battery_level <= self.low_battery_threshold and not self.is_charging:
                    if not low_battery_warned:
                        self.handle_low_battery()
                        low_battery_warned = True
                else:
                    low_battery_warned = False
                
                time.sleep(30)  # Check every 30 seconds
        
        except KeyboardInterrupt:
            logging.info("Battery Module shutting down")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | BATTERY | %(levelname)s | %(message)s'
    )
    
    module = BatteryModule()
    module.run()

if __name__ == "__main__":
    main()
    