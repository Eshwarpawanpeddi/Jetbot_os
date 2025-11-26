#!/usr/bin/env python3
"""
Redis-based Event Bus for Inter-Process Communication
Works across subprocess.Popen spawned processes
"""

import json
import time
import logging
import threading
from enum import Enum
from typing import Callable, Any, Dict, List
from datetime import datetime

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using fallback mode")

# Event Types
class EventType(Enum):
    """Event types for the robot system"""
    # Mode and control
    MODE_CHANGED = "mode_changed"
    MOVEMENT_COMMAND = "movement_command"
    EMERGENCY_STOP = "emergency_stop"
    
    # LLM events
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    
    # Voice events
    VOICE_INPUT = "voice_input"
    VOICE_OUTPUT = "voice_output"
    EMOTION_DETECTED = "emotion_detected"
    
    # Face events
    FACE_EMOTION = "face_emotion"
    FACE_STATUS = "face_status"
    
    # Camera events
    CAMERA_FRAME = "camera_frame"
    PHOTO_TAKEN = "photo_taken"
    VIDEO_RECORDING = "video_recording"
    
    # Navigation events
    NAVIGATION_STATUS = "navigation_status"
    OBSTACLE_DETECTED = "obstacle_detected"
    GOAL_REACHED = "goal_reached"
    
    # Battery events
    BATTERY_STATUS = "battery_status"
    LOW_BATTERY = "low_battery"
    CRITICAL_BATTERY = "critical_battery"
    
    # System events
    MODULE_STARTED = "module_started"
    MODULE_STOPPED = "module_stopped"
    MODULE_ERROR = "module_error"

class Event:
    """Event object"""
    def __init__(self, event_type: EventType, data: Dict[str, Any], source: str):
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'event_type': self.event_type.value,
            'data': self.data,
            'source': self.source,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, d):
        """Create Event from dictionary"""
        event_type = EventType(d['event_type'])
        return cls(event_type, d['data'], d['source'])

class RedisEventBus:
    """Redis-based Event Bus for inter-process communication"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.subscribers = {}
        self.redis_client = None
        self.pubsub = None
        self.listener_thread = None
        self.running = False
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                self.pubsub = self.redis_client.pubsub()
                logging.info("Redis Event Bus connected")
            except Exception as e:
                logging.error(f"Redis connection failed: {e}")
                self.redis_client = None
        
        # Start listener thread
        if self.redis_client:
            self.running = True
            self.listener_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True
            )
            self.listener_thread.start()
    
    def publish(self, event_type: EventType, data: Dict[str, Any], source: str):
        """Publish an event"""
        event = Event(event_type, data, source)
        
        # Call local subscribers first
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logging.error(f"Subscriber error: {e}")
        
        # Publish to Redis
        if self.redis_client:
            try:
                channel = f"jetbot:{event_type.value}"
                message = json.dumps(event.to_dict())
                self.redis_client.publish(channel, message)
            except Exception as e:
                logging.error(f"Redis publish error: {e}")
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
            
            # Subscribe to Redis channel
            if self.pubsub:
                channel = f"jetbot:{event_type.value}"
                self.pubsub.subscribe(channel)
        
        self.subscribers[event_type].append(callback)
        logging.debug(f"Subscribed to {event_type.value}")
    
    def _listen_loop(self):
        """Listen for Redis messages"""
        while self.running and self.pubsub:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    self._handle_message(message)
            except Exception as e:
                logging.error(f"Listener error: {e}")
                time.sleep(1)
    
    def _handle_message(self, message):
        """Handle incoming Redis message"""
        try:
            data = json.loads(message['data'])
            event = Event.from_dict(data)
            
            # Call subscribers
            if event.event_type in self.subscribers:
                for callback in self.subscribers[event.event_type]:
                    try:
                        callback(event)
                    except Exception as e:
                        logging.error(f"Callback error: {e}")
        except Exception as e:
            logging.error(f"Message handling error: {e}")
    
    def get_history(self, event_type: EventType = None, limit: int = 100):
        """Get event history (not implemented in Redis version)"""
        logging.warning("Event history not available in Redis mode")
        return []
    
    def shutdown(self):
        """Shutdown event bus"""
        self.running = False
        if self.pubsub:
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()

# Singleton instance
event_bus = RedisEventBus()

# Cleanup on exit
import atexit
atexit.register(event_bus.shutdown)
