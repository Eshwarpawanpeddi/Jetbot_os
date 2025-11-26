import time
import queue
import subprocess
from core.event_bus import EventType, RobotEvent

# Mocking ROS library for portability in code generation
# In real deployment: import rospy, from geometry_msgs.msg import Twist
ROS_AVAILABLE = False
try:
    import rospy
    from geometry_msgs.msg import Twist
    ROS_AVAILABLE = True
except ImportError:
    pass

class MotorController:
    def __init__(self):
        self.pub = None
        if ROS_AVAILABLE:
            rospy.init_node('jetbot_os_bridge', anonymous=True)
            self.pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        
    def move(self, x, y):
        if not ROS_AVAILABLE:
            print(f"[Simulation] Motors Moving: Linear={x}, Angular={y}")
            return
            
        twist = Twist()
        twist.linear.x = x
        twist.angular.z = y
        self.pub.publish(twist)

    def stop(self):
        self.move(0, 0)

def run_nav_module(bus, sub_queue, config):
    controller = MotorController()
    
    current_mode = config['system']['mode_default'] # MANUAL or AUTO
    ros_process = None

    def start_ros_nav():
        # Start the heavy ROS navigation stack (AMCL, MoveBase)
        cmd = config['ros']['launch_command'].split()
        return subprocess.Popen(cmd)

    def stop_ros_nav(proc):
        if proc:
            proc.terminate()
            return None

    while True:
        try:
            event = sub_queue.get(timeout=0.1)
            
            # 1. Mode Switching Logic
            if event.type == EventType.ModeSwitch:
                new_mode = event.payload
                if new_mode == "AUTO" and current_mode != "AUTO":
                    print("Engaging Autonomous Mode...")
                    # ros_process = start_ros_nav() # Uncomment to actually launch ROS stack
                    current_mode = "AUTO"
                    bus.publish(RobotEvent(EventType.EmotionChange, "THINKING"))
                
                elif new_mode == "MANUAL" and current_mode != "MANUAL":
                    print("Switching to Manual Mode...")
                    stop_ros_nav(ros_process)
                    current_mode = "MANUAL"
                    controller.stop()
                    bus.publish(RobotEvent(EventType.EmotionChange, "HAPPY"))

            # 2. Movement Logic (Only accept commands in Manual Mode)
            elif event.type == EventType.MoveCommand:
                if current_mode == "MANUAL":
                    # Safety check (Pseudo-code for sensor)
                    # if obstacle_distance < 10cm: controller.stop() else:
                    controller.move(event.payload['x'], event.payload['y'])

            # 3. Emergency Stop
            elif event.type == EventType.EmergencyStop:
                controller.stop()
                
        except queue.Empty:
            pass
            
        # Keep ROS node alive if needed
        if ROS_AVAILABLE and rospy.is_shutdown():
            break
