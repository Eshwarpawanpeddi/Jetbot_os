#!/usr/bin/env python3
"""
API Server Launcher - Starts all API services
Runs REST API, WebSocket, and Camera Streaming in parallel
"""

import os
import sys
import yaml
import logging
import threading
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.rest_api import run_api_server
from api.websocket_server import start_server as run_websocket_server
from api.camera_stream import run_stream_server

# ============================================================================
# CONFIGURATION
# ============================================================================

def load_config():
    """Load API configuration"""
    config_path = Path("config/api_config.yaml")
    
    if not config_path.exists():
        logging.warning("API config not found, using defaults")
        return get_default_config()
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Failed to load API config: {e}")
        return get_default_config()

def get_default_config():
    """Default configuration"""
    return {
        'rest_api': {'host': '0.0.0.0', 'port': 5000},
        'websocket': {'host': '0.0.0.0', 'port': 8765},
        'camera_stream': {'host': '0.0.0.0', 'port': 5001}
    }

# ============================================================================
# SERVER MANAGEMENT
# ============================================================================

class APIServerManager:
    """Manages all API servers"""
    
    def __init__(self, config):
        self.config = config
        self.threads = []
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging"""
        log_dir = Path("/var/log/jetbot")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "api.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def start_rest_api(self):
        """Start REST API server in thread"""
        config = self.config['rest_api']
        
        def run():
            logging.info("Starting REST API server...")
            run_api_server(
                host=config.get('host', '0.0.0.0'),
                port=config.get('port', 5000)
            )
        
        thread = threading.Thread(target=run, daemon=True, name='REST_API')
        thread.start()
        self.threads.append(thread)
        logging.info(f"REST API started on {config['host']}:{config['port']}")
    
    def start_websocket(self):
        """Start WebSocket server in thread"""
        config = self.config['websocket']
        
        def run():
            logging.info("Starting WebSocket server...")
            run_websocket_server(
                host=config.get('host', '0.0.0.0'),
                port=config.get('port', 8765)
            )
        
        thread = threading.Thread(target=run, daemon=True, name='WEBSOCKET')
        thread.start()
        self.threads.append(thread)
        logging.info(f"WebSocket started on ws://{config['host']}:{config['port']}")
    
    def start_camera_stream(self):
        """Start camera streaming server in thread"""
        config = self.config['camera_stream']
        
        def run():
            logging.info("Starting Camera Stream server...")
            run_stream_server(
                host=config.get('host', '0.0.0.0'),
                port=config.get('port', 5001)
            )
        
        thread = threading.Thread(target=run, daemon=True, name='CAMERA_STREAM')
        thread.start()
        self.threads.append(thread)
        logging.info(f"Camera Stream started on http://{config['host']}:{config['port']}/stream")
    
    def start_all(self):
        """Start all API servers"""
        logging.info("=" * 60)
        logging.info("JETBOT API SERVER - STARTING ALL SERVICES")
        logging.info("=" * 60)
        
        self.start_rest_api()
        self.start_websocket()
        self.start_camera_stream()
        
        logging.info("=" * 60)
        logging.info("ALL API SERVICES RUNNING")
        logging.info("=" * 60)
        logging.info("")
        logging.info("API Endpoints:")
        logging.info(f"  REST API:       http://{self.config['rest_api']['host']}:{self.config['rest_api']['port']}/api")
        logging.info(f"  WebSocket:      ws://{self.config['websocket']['host']}:{self.config['websocket']['port']}")
        logging.info(f"  Camera Stream:  http://{self.config['camera_stream']['host']}:{self.config['camera_stream']['port']}/stream")
        logging.info("")
        logging.info("Press Ctrl+C to shutdown")
        logging.info("=" * 60)
        
        # Keep main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutting down API servers...")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    config = load_config()
    manager = APIServerManager(config)
    manager.start_all()

if __name__ == "__main__":
    main()
