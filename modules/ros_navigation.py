#!/usr/bin/env python3
"""
ROS Navigation Module - Robust Implementation
Supports ROS 1 (Melodic/Noetic) with fallback to Simulation
"""

import os
import sys
import time
import logging
import threading
from enum import Enum
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# ============================================================================
# ROS IMPORT HANDLING
# ============================================================================
ROS_VERSION = None
try:
    import rospy
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    # Try importing move_base tools
    try:
        import actionlib
        from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
        from actionlib_msgs.msg import GoalStatus
        import tf
    except ImportError:
        logging.warning("ROS Navigation Stack (move_base) not found. Only basic movement available.")
    
    ROS_VERSION = 1
    logging.info("ROS 1 (rospy) loaded successfully")

except ImportError:
    # Future: Add ROS 2 (rclpy) support here
    logging.warning("ROS libraries not found. Falling back to SIMULATION MODE.")
    ROS_VERSION = None

# ============================================================================
# DATA CLASSES
# ============================================================================

class NavigationState(Enum):
    IDLE = "idle"
    NAVIGATING = "navigating"
    AVOIDING_OBSTACLE = "avoiding_obstacle"
    GOAL_REACHED = "goal_reached"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class RobotPose:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

@dataclass
class ObstacleInfo:
    detected: bool = False
    min_distance: float = float('inf')
    direction: str = "unknown"

# ============================================================================
# MAIN NAVIGATION MODULE
# ============================================================================

class ROSNavigationModule:
    """ROS navigation with fallback to simulation"""
    
    def __init__(self):
        self.is_enabled = False
        self.current_mode = "manual" # Default to manual for safety
        self.state = NavigationState.IDLE
        self.current_pose = RobotPose()
        self.obstacle_info = ObstacleInfo()
        
        # ROS variables
        self.cmd_vel_pub = None
        self.move_base_client = None
        
        if ROS_VERSION == 1:
            self._initialize_ros1()
        else:
            self._initialize_simulation()
        
        logging.info(f"Navigation Module initialized (Mode: {'ROS' if ROS_VERSION else 'SIM'})")

    def _initialize_ros1(self):
        """Initialize ROS 1 Node"""
        try:
            rospy.init_node('jetbot_os_nav', anonymous=True, disable_signals=True)
            self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
            
            # Subscriptions
            rospy.Subscriber('/scan', LaserScan, self._ros_scan_callback)
            
            # Action Client (if available)
            if 'actionlib' in sys.modules:
                self.move_base_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
                # We don't wait for server here to avoid blocking startup if nav stack isn't running
            
        except Exception as e:
            logging.error(f"Error initializing ROS 1: {e}")
            self._initialize_simulation()

    def _initialize_simulation(self):
        """Initialize internal simulation"""
        self.simulation_running = True
        logging.info("Simulation backend active")

    def _ros_scan_callback(self, data):
        """Handle LaserScan from ROS"""
        try:
            # Simple obstacle check
            # Filter out zeros/infinities
            valid_ranges = [r for r in data.ranges if data.range_min < r < data.range_max]
            if valid_ranges:
                min_dist = min(valid_ranges)
                if min_dist < 0.5: # 50cm threshold
                    self.obstacle_info.detected = True
                    self.obstacle_info.min_distance = min_dist
                    self._handle_obstacle(min_dist)
                else:
                    self.obstacle_info.detected = False
        except Exception as e:
            pass

    def _handle_obstacle(self, distance):
        """React to obstacle"""
        event_bus.publish(EventType.OBSTACLE_DETECTED, {'distance': distance}, "navigation")
        if self.current_mode == "auto" and distance < 0.3:
            self.send_velocity(0, 0) # Emergency stop

    def send_velocity(self, linear, angular):
        """Send movement command"""
        if ROS_VERSION == 1 and self.cmd_vel_pub:
            msg = Twist()
            msg.linear.x = linear
            msg.angular.z = angular
            self.cmd_vel_pub.publish(msg)
        else:
            # Simulation log
            if abs(linear) > 0 or abs(angular) > 0:
                logging.debug(f"[SIM] Motors: Linear={linear:.2f}, Angular={angular:.2f}")

    def handle_movement_command(self, event):
        """Handle manual movement commands"""
        if self.current_mode == "manual":
            left = event.data.get('left_motor', 0)
            right = event.data.get('right_motor', 0)
            
            # Simple differential drive conversion
            # Linear = average of both
            # Angular = difference
            linear = (left + right) / 2.0
            angular = (right - left) / 2.0
            
            self.send_velocity(linear, angular)

    def handle_mode_change(self, event):
        self.current_mode = event.data.get('mode', 'manual')
        logging.info(f"Navigation Mode set to: {self.current_mode}")

    def run(self):
        """Main loop"""
        event_bus.subscribe(EventType.MOVEMENT_COMMAND, self.handle_movement_command)
        event_bus.subscribe(EventType.MODE_CHANGED, self.handle_mode_change)
        
        logging.info("Navigation Module running")
        
        rate = 10 # 10 Hz
        while True:
            # If using ROS 1, we rely on callbacks, but we need to keep thread alive
            # If using ROS 2 or Sim, we might do more here
            time.sleep(1.0/rate)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | NAV | %(levelname)s | %(message)s')
    module = ROSNavigationModule()
    module.run()

if __name__ == "__main__":
    main()