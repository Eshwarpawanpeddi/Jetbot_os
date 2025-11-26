#!/usr/bin/env python3
"""
Navigation Module Testing Script
Tests navigation in both simulation and ROS modes
"""

import os
import sys
import time
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.event_bus import event_bus, EventType
from modules.ros_navigation import ROSNavigationModule

def test_basic_movement(nav_module):
    """Test basic movement commands"""
    print("\n=== Testing Basic Movement ===")
    
    # Switch to manual mode
    event_bus.publish(EventType.MODE_CHANGED, {'mode': 'manual'}, 'test')
    time.sleep(1)
    
    # Forward
    print("Moving forward...")
    event_bus.publish(EventType.MOVEMENT_COMMAND, {
        'left_motor': 0.5,
        'right_motor': 0.5
    }, 'test')
    time.sleep(2)
    
    # Stop
    print("Stopping...")
    event_bus.publish(EventType.MOVEMENT_COMMAND, {
        'left_motor': 0,
        'right_motor': 0
    }, 'test')
    time.sleep(1)
    
    # Turn left
    print("Turning left...")
    event_bus.publish(EventType.MOVEMENT_COMMAND, {
        'left_motor': -0.3,
        'right_motor': 0.3
    }, 'test')
    time.sleep(2)
    
    # Stop
    event_bus.publish(EventType.MOVEMENT_COMMAND, {
        'left_motor': 0,
        'right_motor': 0
    }, 'test')
    
    print("✓ Basic movement test complete")

def test_mode_switching(nav_module):
    """Test mode switching"""
    print("\n=== Testing Mode Switching ===")
    
    # Auto mode
    print("Switching to AUTO mode...")
    event_bus.publish(EventType.MODE_CHANGED, {'mode': 'auto'}, 'test')
    time.sleep(1)
    print(f"Navigation enabled: {nav_module.is_enabled}")
    
    # Manual mode
    print("Switching to MANUAL mode...")
    event_bus.publish(EventType.MODE_CHANGED, {'mode': 'manual'}, 'test')
    time.sleep(1)
    print(f"Navigation enabled: {nav_module.is_enabled}")
    
    print("✓ Mode switching test complete")

def test_obstacle_detection(nav_module):
    """Test obstacle detection"""
    print("\n=== Testing Obstacle Detection ===")
    
    if nav_module.simulation:
        print("Running in simulation mode")
        
        # Check for obstacles multiple times
        for i in range(5):
            nav_module.check_obstacles()
            if nav_module.obstacle_info.detected:
                print(f"  Obstacle detected at {nav_module.obstacle_info.min_distance:.2f}m "
                      f"({nav_module.obstacle_info.direction})")
            else:
                print(f"  No obstacles detected")
            time.sleep(1)
    else:
        print("ROS mode - obstacles detected via laser scan")
    
    print("✓ Obstacle detection test complete")

def test_status_reporting(nav_module):
    """Test status reporting"""
    print("\n=== Testing Status Reporting ===")
    
    nav_module.publish_status()
    
    pose = nav_module.get_current_pose()
    print(f"Current pose: x={pose.x:.2f}, y={pose.y:.2f}, theta={pose.theta:.2f}")
    print(f"State: {nav_module.state.value}")
    print(f"Mode: {nav_module.current_mode}")
    
    print("✓ Status reporting test complete")

def main():
    print("=" * 60)
    print("NAVIGATION MODULE TEST SUITE")
    print("=" * 60)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    # Initialize module
    print("\nInitializing navigation module...")
    nav_module = ROSNavigationModule()
    
    print(f"ROS Available: {nav_module.simulation is None}")
    print(f"Simulation Mode: {nav_module.simulation is not None}")
    
    # Run tests
    try:
        test_mode_switching(nav_module)
        test_basic_movement(nav_module)
        test_obstacle_detection(nav_module)
        test_status_reporting(nav_module)
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if nav_module.simulation:
            nav_module.simulation.stop()

if __name__ == "__main__":
    main()
