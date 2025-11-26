import multiprocessing
import time
import signal
import sys
import logging
import json
from core.event_bus import EventBus, RobotEvent, EventType

# Import Modules
from modules.face_display import run_face_module
from modules.web_api import run_api_module
from modules.llm_voice import run_voice_module
from modules.navigation import run_nav_module
from modules.camera_stream import run_camera_module  # <--- Added import

# Setup Logging
logging.basicConfig(filename='system.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

class ProcessManager:
    def __init__(self):
        self.bus = EventBus()
        self.processes = {}
        self.running = True
        self.config = load_config()

    def start_process(self, name, target_func, args=()):
        """Starts a process and tracks it."""
        p = multiprocessing.Process(target=target_func, args=args, name=name)
        p.start()
        self.processes[name] = {
            "process": p,
            "target": target_func,
            "args": args,
            "restarts": 0
        }
        logging.info(f"Started module: {name} (PID: {p.pid})")

    def monitor_loop(self):
        """Crash recovery loop."""
        while self.running:
            for name, info in self.processes.items():
                p = info["process"]
                if not p.is_alive():
                    logging.error(f"Module {name} died! Restarting...")
                    # Update Restart Count
                    info["restarts"] += 1
                    
                    # Restart
                    new_p = multiprocessing.Process(target=info["target"], args=info["args"], name=name)
                    new_p.start()
                    info["process"] = new_p
                    
                    # Notify system of crash/restart
                    # We can't use the bus easily here if we aren't a subscriber, 
                    # but typically the launcher just manages PIDs.
            
            time.sleep(2) # Check every 2 seconds

    def cleanup(self, signum, frame):
        logging.info("Shutting down robot...")
        self.running = False
        for name, info in self.processes.items():
            info["process"].terminate()
            info["process"].join()
        sys.exit(0)

if __name__ == "__main__":
    manager = ProcessManager()
    
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, manager.cleanup)
    signal.signal(signal.SIGTERM, manager.cleanup)

    logging.info("Initializing Robot OS...")

    # Create Subscriber Queues for each module
    q_face = manager.bus.create_subscriber()
    q_voice = manager.bus.create_subscriber()
    q_nav = manager.bus.create_subscriber()
    q_api = manager.bus.create_subscriber() # API usually pushes, but might listen for status

    # Start Modules
    # 1. Face Display (Critical for UI)
    manager.start_process("FaceModule", run_face_module, (manager.bus, q_face, manager.config))
    
    # 2. Web API (For Android App)
    manager.start_process("WebAPI", run_api_module, (manager.bus, q_api, manager.config))
    
    # 3. Navigation / ROS Bridge
    manager.start_process("NavModule", run_nav_module, (manager.bus, q_nav, manager.config))

    # 4. LLM & Voice
    manager.start_process("VoiceModule", run_voice_module, (manager.bus, q_voice, manager.config))

    # 5. Camera Stream (Added)
    manager.start_process("CameraModule", run_camera_module, (manager.bus, manager.bus.create_subscriber(), manager.config))

    # Enter Supervisor Loop
    manager.monitor_loop()
