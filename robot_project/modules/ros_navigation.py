#!/usr/bin/env python3
"""
ROS Navigation Module - Full Implementation
Works in both ROS mode (on Jetson) and simulation mode (for development)
"""

import os
import sys
import time
import logging
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# Check if ROS is available
ROS_AVAILABLE = False
try:
    import rospy
    from geometry_msgs.msg import Twist, Pose, Point, Quaternion
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
    from actionlib_msgs.msg import GoalStatus
    import actionlib
    import tf
    ROS_AVAILABLE = True
    logging.info("ROS libraries loaded successfully")
except ImportError:
    logging.warning("ROS not available - running in SIMULATION MODE")

# ============================================================================
# DATA CLASSES
# ============================================================================

class NavigationState(Enum):
    """Navigation states"""
    IDLE = "idle"
    NAVIGATING = "navigating"
    AVOIDING_OBSTACLE = "avoiding_obstacle"
    GOAL_REACHED = "goal_reached"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class RobotPose:
    """Robot position and orientation"""
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0  # Orientation in radians

@dataclass
class ObstacleInfo:
    """Obstacle detection information"""
    detected: bool = False
    min_distance: float = float('inf')
    direction: str = "unknown"  # front, left, right, back

# ============================================================================
# SIMULATION MODE (For development without ROS)
# ============================================================================

class SimulatedRobot:
    """Simulates robot for testing without ROS"""
    
    def __init__(self):
        self.pose = RobotPose()
        self.velocity = (0.0, 0.0)  # (linear, angular)
        self.obstacles = []
        self.update_thread = None
        self.running = False
        
    def start(self):
        """Start simulation"""
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logging.info("Simulation started")
    
    def stop(self):
        """Stop simulation"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
    
    def _update_loop(self):
        """Update robot state in simulation"""
        dt = 0.1  # 10 Hz update rate
        
        while self.running:
            # Update position based on velocity
            linear, angular = self.velocity
            
            self.pose.x += linear * dt * cos(self.pose.theta)
            self.pose.y += linear * dt * sin(self.pose.theta)
            self.pose.theta += angular * dt
            
            # Normalize angle to [-pi, pi]
            while self.pose.theta > 3.14159:
                self.pose.theta -= 2 * 3.14159
            while self.pose.theta < -3.14159:
                self.pose.theta += 2 * 3.14159
            
            time.sleep(dt)
    
    def set_velocity(self, linear: float, angular: float):
        """Set robot velocity"""
        self.velocity = (linear, angular)
    
    def get_pose(self) -> RobotPose:
        """Get current pose"""
        return self.pose
    
    def scan_obstacles(self) -> ObstacleInfo:
        """Simulate obstacle detection"""
        # Simple simulation: random obstacles
        import random
        
        info = ObstacleInfo()
        
        if random.random() < 0.1:  # 10% chance of obstacle
            info.detected = True
            info.min_distance = random.uniform(0.2, 2.0)
            info.direction = random.choice(["front", "left", "right"])
        
        return info

# Helper functions for simulation
def cos(angle):
    import math
    return math.cos(angle)

def sin(angle):
    import math
    return math.sin(angle)

# ============================================================================
# MAIN NAVIGATION MODULE
# ============================================================================

class ROSNavigationModule:
    """ROS navigation with fallback to simulation"""
    
    def __init__(self):
        self.is_enabled = False
        self.current_mode = "auto"
        self.state = NavigationState.IDLE
        
        # Robot state
        self.current_pose = RobotPose()
        self.obstacle_info = ObstacleInfo()
        
        # Safety thresholds
        self.min_obstacle_distance = 0.5  # meters
        self.emergency_stop_distance = 0.2  # meters
        self.max_linear_speed = 0.5  # m/s
        self.max_angular_speed = 1.0  # rad/s
        
        # ROS components (if available)
        self.cmd_vel_pub = None
        self.move_base_client = None
        self.tf_listener = None
        
        # Simulation mode
        self.simulation = None
        
        # Initialize based on ROS availability
        if ROS_AVAILABLE:
            self._initialize_ros()
        else:
            self._initialize_simulation()
        
        logging.info(f"ROS Navigation Module initialized (ROS: {ROS_AVAILABLE})")
    
    # ========================================================================
    # INITIALIZATION
    # ========================================================================
    
    def _initialize_ros(self):
        """Initialize ROS node and connections"""
        try:
            rospy.init_node('jetbot_navigation', anonymous=True)
            
            # Publishers
            self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
            
            # Subscribers
            rospy.Subscriber('/scan', LaserScan, self._laser_callback)
            rospy.Subscriber('/odom', Odometry, self._odom_callback)
            
            # TF listener for localization
            self.tf_listener = tf.TransformListener()
            
            # Action client for move_base
            self.move_base_client = actionlib.SimpleActionClient(
                'move_base',
                MoveBaseAction
            )
            
            logging.info("Waiting for move_base action server...")
            self.move_base_client.wait_for_server(timeout=rospy.Duration(5.0))
            logging.info("ROS node initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize ROS: {e}")
            logging.info("Falling back to simulation mode")
            self._initialize_simulation()
    
    def _initialize_simulation(self):
        """Initialize simulation mode"""
        self.simulation = SimulatedRobot()
        self.simulation.start()
        logging.info("Simulation mode initialized")
    
    # ========================================================================
    # ROS CALLBACKS
    # ========================================================================
    
    def _laser_callback(self, scan_data):
        """Handle laser scan data for obstacle detection"""
        if not self.is_enabled:
            return
        
        # Analyze scan data
        ranges = [r for r in scan_data.ranges if not (r < scan_data.range_min or r > scan_data.range_max)]
        
        if not ranges:
            return
        
        min_distance = min(ranges)
        min_index = ranges.index(min_distance)
        
        # Determine direction
        total_points = len(ranges)
        if min_index < total_points / 3:
            direction = "right"
        elif min_index > 2 * total_points / 3:
            direction = "left"
        else:
            direction = "front"
        
        # Update obstacle info
        self.obstacle_info = ObstacleInfo(
            detected=True,
            min_distance=min_distance,
            direction=direction
        )
        
        # Emergency stop if too close
        if min_distance < self.emergency_stop_distance:
            self.emergency_stop()
            event_bus.publish(
                EventType.OBSTACLE_DETECTED,
                {
                    'distance': min_distance,
                    'direction': direction,
                    'severity': 'critical'
                },
                source='ros_navigation'
            )
        
        # Warning if obstacle detected
        elif min_distance < self.min_obstacle_distance:
            self.state = NavigationState.AVOIDING_OBSTACLE
            event_bus.publish(
                EventType.OBSTACLE_DETECTED,
                {
                    'distance': min_distance,
                    'direction': direction,
                    'severity': 'warning'
                },
                source='ros_navigation'
            )
    
    def _odom_callback(self, odom_data):
        """Handle odometry data"""
        # Extract position
        self.current_pose.x = odom_data.pose.pose.position.x
        self.current_pose.y = odom_data.pose.pose.position.y
        
        # Extract orientation (quaternion to euler)
        orientation = odom_data.pose.pose.orientation
        euler = tf.transformations.euler_from_quaternion([
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w
        ])
        self.current_pose.theta = euler[2]  # yaw
    
    # ========================================================================
    # NAVIGATION CONTROL
    # ========================================================================
    
    def enable_navigation(self):
        """Enable autonomous navigation"""
        if self.current_mode == "auto":
            self.is_enabled = True
            self.state = NavigationState.IDLE
            logging.info("Navigation enabled")
            
            event_bus.publish(
                EventType.NAVIGATION_STATUS,
                {
                    'status': 'enabled',
                    'mode': 'auto'
                },
                source='ros_navigation'
            )
            
            # Update face
            event_bus.publish(
                EventType.FACE_EMOTION,
                {'emotion': 'happy'},
                source='ros_navigation'
            )
    
    def disable_navigation(self):
        """Disable autonomous navigation"""
        self.is_enabled = False
        self.state = NavigationState.IDLE
        
        # Cancel any active goals
        if ROS_AVAILABLE and self.move_base_client:
            self.move_base_client.cancel_all_goals()
        
        # Stop movement
        self.send_velocity_command(0, 0)
        
        logging.info("Navigation disabled")
        
        event_bus.publish(
            EventType.NAVIGATION_STATUS,
            {'status': 'disabled'},
            source='ros_navigation'
        )
    
    def send_velocity_command(self, linear_x: float, angular_z: float):
        """Send velocity command to robot"""
        # Clamp velocities to safe limits
        linear_x = max(-self.max_linear_speed, min(self.max_linear_speed, linear_x))
        angular_z = max(-self.max_angular_speed, min(self.max_angular_speed, angular_z))
        
        if ROS_AVAILABLE and self.cmd_vel_pub:
            # ROS mode
            twist = Twist()
            twist.linear.x = linear_x
            twist.angular.z = angular_z
            self.cmd_vel_pub.publish(twist)
        elif self.simulation:
            # Simulation mode
            self.simulation.set_velocity(linear_x, angular_z)
        
        logging.debug(f"Velocity command: linear={linear_x:.2f}, angular={angular_z:.2f}")
    
    def navigate_to_goal(self, x: float, y: float, theta: float = 0.0):
        """Navigate to a goal position"""
        if not self.is_enabled:
            logging.warning("Navigation not enabled")
            return False
        
        if ROS_AVAILABLE and self.move_base_client:
            # Create goal
            goal = MoveBaseGoal()
            goal.target_pose.header.frame_id = "map"
            goal.target_pose.header.stamp = rospy.Time.now()
            
            goal.target_pose.pose.position.x = x
            goal.target_pose.pose.position.y = y
            goal.target_pose.pose.position.z = 0.0
            
            # Convert theta to quaternion
            quat = tf.transformations.quaternion_from_euler(0, 0, theta)
            goal.target_pose.pose.orientation.x = quat[0]
            goal.target_pose.pose.orientation.y = quat[1]
            goal.target_pose.pose.orientation.z = quat[2]
            goal.target_pose.pose.orientation.w = quat[3]
            
            # Send goal
            self.move_base_client.send_goal(goal, done_cb=self._goal_done_callback)
            self.state = NavigationState.NAVIGATING
            
            logging.info(f"Navigating to goal: ({x:.2f}, {y:.2f}, {theta:.2f})")
            
            event_bus.publish(
                EventType.NAVIGATION_STATUS,
                {
                    'status': 'navigating',
                    'goal': {'x': x, 'y': y, 'theta': theta}
                },
                source='ros_navigation'
            )
            
            return True
        else:
            logging.warning("move_base not available (simulation mode)")
            return False
    
    def _goal_done_callback(self, status, result):
        """Callback when navigation goal completes"""
        if status == GoalStatus.SUCCEEDED:
            self.state = NavigationState.GOAL_REACHED
            logging.info("Goal reached successfully")
            
            event_bus.publish(
                EventType.NAVIGATION_STATUS,
                {'status': 'goal_reached'},
                source='ros_navigation'
            )
            
            # Happy face
            event_bus.publish(
                EventType.FACE_EMOTION,
                {'emotion': 'excited'},
                source='ros_navigation'
            )
        else:
            self.state = NavigationState.FAILED
            logging.warning(f"Navigation failed with status: {status}")
            
            event_bus.publish(
                EventType.NAVIGATION_STATUS,
                {'status': 'failed', 'code': status},
                source='ros_navigation'
            )
    
    def emergency_stop(self):
        """Emergency stop - override all movement"""
        logging.warning("EMERGENCY STOP activated")
        
        # Stop all movement immediately
        self.send_velocity_command(0, 0)
        
        # Cancel navigation goals
        if ROS_AVAILABLE and self.move_base_client:
            self.move_base_client.cancel_all_goals()
        
        self.state = NavigationState.PAUSED
        
        # Update UI
        event_bus.publish(
            EventType.FACE_EMOTION,
            {'emotion': 'confused'},
            source='ros_navigation'
        )
        
        event_bus.publish(
            EventType.FACE_STATUS,
            {'status': '⚠️ EMERGENCY STOP'},
            source='ros_navigation'
        )
        
        # Voice warning
        event_bus.publish(
            EventType.VOICE_OUTPUT,
            {'text': 'Emergency stop! Obstacle detected.'},
            source='ros_navigation'
        )
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def handle_mode_change(self, event):
        """Handle mode changes"""
        mode = event.data.get('mode')
        self.current_mode = mode
        
        if mode == "auto":
            self.enable_navigation()
        else:
            self.disable_navigation()
    
    def handle_movement_command(self, event):
        """Handle movement commands from controller/app"""
        # Only process in manual mode
        if self.current_mode != "manual":
            return
        
        left_motor = event.data.get('left_motor', 0)
        right_motor = event.data.get('right_motor', 0)
        
        # Convert differential drive to twist
        linear_x = (left_motor + right_motor) / 2.0 * self.max_linear_speed
        angular_z = (right_motor - left_motor) / 2.0 * self.max_angular_speed
        
        self.send_velocity_command(linear_x, angular_z)
    
    # ========================================================================
    # STATUS AND MONITORING
    # ========================================================================
    
    def get_current_pose(self) -> RobotPose:
        """Get current robot pose"""
        if self.simulation:
            return self.simulation.get_pose()
        return self.current_pose
    
    def check_obstacles(self):
        """Check for obstacles (simulation mode)"""
        if self.simulation:
            self.obstacle_info = self.simulation.scan_obstacles()
            
            if self.obstacle_info.detected and self.obstacle_info.min_distance < self.min_obstacle_distance:
                event_bus.publish(
                    EventType.OBSTACLE_DETECTED,
                    {
                        'distance': self.obstacle_info.min_distance,
                        'direction': self.obstacle_info.direction
                    },
                    source='ros_navigation'
                )
    
    def publish_status(self):
        """Publish navigation status periodically"""
        pose = self.get_current_pose()
        
        status = {
            'enabled': self.is_enabled,
            'mode': self.current_mode,
            'state': self.state.value,
            'ros_available': ROS_AVAILABLE,
            'position': {
                'x': pose.x,
                'y': pose.y,
                'theta': pose.theta
            },
            'obstacle': {
                'detected': self.obstacle_info.detected,
                'distance': self.obstacle_info.min_distance if self.obstacle_info.detected else None
            }
        }
        
        event_bus.publish(
            EventType.NAVIGATION_STATUS,
            status,
            source='ros_navigation'
        )
    
    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    
    def run(self):
        """Main run loop"""
        # Subscribe to events
        event_bus.subscribe(EventType.MODE_CHANGED, self.handle_mode_change)
        event_bus.subscribe(EventType.MOVEMENT_COMMAND, self.handle_movement_command)
        
        logging.info("ROS Navigation Module running")
        
        try:
            while True:
                # Publish status
                self.publish_status()
                
                # Check obstacles (simulation mode)
                if not ROS_AVAILABLE:
                    self.check_obstacles()
                
                # Process ROS callbacks or sleep
                if ROS_AVAILABLE:
                    try:
                        rospy.sleep(0.1)
                    except:
                        time.sleep(0.1)
                else:
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            logging.info("ROS Navigation Module shutting down")
            self.disable_navigation()
            
            if self.simulation:
                self.simulation.stop()

# ============================================================================
# MAIN
# ============================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | ROS_NAV | %(levelname)s | %(message)s'
    )
    
    module = ROSNavigationModule()
    module.run()

if __name__ == "__main__":
    main()
