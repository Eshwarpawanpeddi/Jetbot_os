#!/usr/bin/env python3
"""
API Module - Integrated module for launcher
Starts API servers as part of the main system
"""

import os
import sys
import time
import logging
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

class APIModule:
    """API server module for launcher integration"""
    
    def __init__(self):
        self.api_process = None
        logging.info("API Module initialized")
    
    def start_api_servers(self):
        """Start API server process"""
        try:
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'start_api_server.py'
            )
            
            self.api_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logging.info(f"API servers started (PID: {self.api_process.pid})")
            
            # Publish status event
            event_bus.publish(
                EventType.FACE_STATUS,
                {'status': 'API servers online'},
                source='api_module'
            )
            
        except Exception as e:
            logging.error(f"Failed to start API servers: {e}")
    
    def stop_api_servers(self):
        """Stop API server process"""
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                logging.info("API servers stopped")
            except Exception as e:
                logging.error(f"Error stopping API servers: {e}")
                self.api_process.kill()
    
    def is_alive(self):
        """Check if API servers are running"""
        if self.api_process:
            return self.api_process.poll() is None
        return False
    
    def run(self):
        """Main run loop"""
        self.start_api_servers()
        
        logging.info("API Module running")
        
        try:
            while True:
                # Monitor API process
                if not self.is_alive():
                    logging.error("API servers crashed, restarting...")
                    self.start_api_servers()
                
                time.sleep(5)
        
        except KeyboardInterrupt:
            logging.info("API Module shutting down")
            self.stop_api_servers()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | API | %(levelname)s | %(message)s'
    )
    
    module = APIModule()
    module.run()

if __name__ == "__main__":
    main()
