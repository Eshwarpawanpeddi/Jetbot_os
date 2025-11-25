#!/usr/bin/env python3
"""
Event Bus - Central communication system for all modules
Allows modules to publish and subscribe to events without tight coupling
"""

import json
import logging
import threading
from typing import Callable, Dict, List, Any
from datetime import datetime
from collections import defaultdict

class Event:
    """Represents an event in the system"""
    def __init__(self, event_type: str, data: Any, source: str = "unknown"):
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            'type': self.event_type,
            'data': self.data,
            'source': self.source,
            'timestamp': self.timestamp.isoformat()
        }

class EventBus:
    """Thread-safe event bus for inter-module communication"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
            self.event_history: List[Event] = []
            self.max_history = 1000
            self.lock = threading.Lock()
            self.initialized = True
            logging.info("EventBus initialized")
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event type"""
        with self.lock:
            self.subscribers[event_type].append(callback)
            logging.debug(f"Subscribed to event: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from an event type"""
        with self.lock:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                logging.debug(f"Unsubscribed from event: {event_type}")
    
    def publish(self, event_type: str, data: Any, source: str = "unknown"):
        """Publish an event to all subscribers"""
        event = Event(event_type, data, source)
        
        with self.lock:
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
            
            # Notify subscribers
            callbacks = self.subscribers.get(event_type, []).copy()
        
        # Call callbacks outside lock to prevent deadlock
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(f"Error in event callback for {event_type}: {e}")
        
        logging.debug(f"Published event: {event_type} from {source}")
    
    def get_recent_events(self, event_type: str = None, limit: int = 10) -> List[Event]:
        """Get recent events, optionally filtered by type"""
        with self.lock:
            if event_type:
                filtered = [e for e in self.event_history if e.event_type == event_type]
                return filtered[-limit:]
            return self.event_history[-limit:]

# Singleton instance
event_bus = EventBus()

# Event type constants
class EventType:
    # Mode control
    MODE_CHANGED = "mode_changed"  # manual/auto mode switch
    
    # LLM events
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    
    # Voice events
    VOICE_INPUT = "voice_input"  # User spoke
    VOICE_OUTPUT = "voice_output"  # Bot speaks
    EMOTION_DETECTED = "emotion_detected"
    
    # Face events
    FACE_EMOTION = "face_emotion"  # Change face emotion
    FACE_STATUS = "face_status"  # Display status message
    FACE_TEXT = "face_text"  # Display text
    
    # Camera events
    CAMERA_FRAME = "camera_frame"
    PHOTO_TAKEN = "photo_taken"
    VIDEO_RECORDING = "video_recording"
    
    # Controller events
    CONTROLLER_INPUT = "controller_input"
    MOVEMENT_COMMAND = "movement_command"
    
    # ROS events
    OBSTACLE_DETECTED = "obstacle_detected"
    NAVIGATION_STATUS = "navigation_status"
    
    # System events
    BATTERY_STATUS = "battery_status"
    WIFI_STATUS = "wifi_status"
    ERROR = "error"
    WARNING = "warning"
