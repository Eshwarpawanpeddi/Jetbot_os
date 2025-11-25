import multiprocessing
import queue
import time
from enum import Enum

class EventType(Enum):
    Log = "LOG"
    StatusUpdate = "STATUS"
    EmotionChange = "EMOTION"
    Speak = "SPEAK"
    MoveCommand = "MOVE"
    ModeSwitch = "MODE_SWITCH"
    SensorData = "SENSOR"
    EmergencyStop = "ESTOP"

class RobotEvent:
    def __init__(self, event_type, payload):
        self.type = event_type
        self.payload = payload
        self.timestamp = time.time()

class EventBus:
    """
    A Multiprocessing-safe Event Bus.
    Modules can subscribe to queues and publish events to a central distributor.
    """
    def __init__(self):
        self._queues = []
        self._lock = multiprocessing.Lock()

    def create_subscriber(self):
        """Creates a new queue for a module to listen to."""
        q = multiprocessing.Queue()
        with self._lock:
            self._queues.append(q)
        return q

    def publish(self, event: RobotEvent):
        """Distributes an event to all subscribers."""
        with self._lock:
            # Clean up dead queues if necessary, or just put to all
            # In production, we might want to filter dead queues
            for q in self._queues:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass  # Drop packet if module is stuck

# Global instance factory (to be instantiated in main process)
def create_event_bus():
    return EventBus()
