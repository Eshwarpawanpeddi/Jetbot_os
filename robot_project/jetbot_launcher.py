#!/usr/bin/env python3
"""
Jetbot Robot Launcher - Main Orchestrator
Handles boot, module management, and crash recovery
"""

import os
import sys
import time
import signal
import logging
import subprocess
import yaml
from pathlib import Path
from datetime import datetime
from threading import Thread, Event
from enum import Enum
from typing import Dict, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

class ModuleState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    RESTARTING = "restarting"

class ModuleConfig:
    """Configuration for each module"""
    def __init__(self, name: str, script_path: str, enabled: bool = True, 
                 max_retries: int = 5, retry_delay: int = 10, critical: bool = False):
        self.name = name
        self.script_path = script_path
        self.enabled = enabled
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.critical = critical  # If critical module fails permanently, shutdown launcher

# ============================================================================
# MODULE MANAGER
# ============================================================================

class Module:
    """Represents a single robot module"""
    def __init__(self, config: ModuleConfig):
        self.config = config
        self.state = ModuleState.STOPPED
        self.process: Optional[subprocess.Popen] = None
        self.retry_count = 0
        self.last_start_time = None
        self.crash_count = 0
        
    def start(self) -> bool:
        """Start the module process"""
        try:
            if not Path(self.config.script_path).exists():
                logging.error(f"[{self.config.name}] Script not found: {self.config.script_path}")
                return False
                
            self.state = ModuleState.STARTING
            logging.info(f"[{self.config.name}] Starting module...")
            
            self.process = subprocess.Popen(
                [sys.executable, self.config.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            
            self.last_start_time = time.time()
            self.state = ModuleState.RUNNING
            logging.info(f"[{self.config.name}] Started successfully (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logging.error(f"[{self.config.name}] Failed to start: {e}")
            self.state = ModuleState.FAILED
            return False
    
    def stop(self):
        """Stop the module process"""
        if self.process:
            try:
                logging.info(f"[{self.config.name}] Stopping module...")
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning(f"[{self.config.name}] Force killing...")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except Exception as e:
                logging.error(f"[{self.config.name}] Error stopping: {e}")
            finally:
                self.process = None
                self.state = ModuleState.STOPPED
    
    def is_alive(self) -> bool:
        """Check if module process is running"""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def should_restart(self) -> bool:
        """Determine if module should be restarted after crash"""
        return self.retry_count < self.config.max_retries

# ============================================================================
# JETBOT LAUNCHER
# ============================================================================

class JetbotLauncher:
    """Main orchestrator for Jetbot robot system"""
    
    def __init__(self, config_path: str = "config/launcher_config.yaml"):
        self.config_path = config_path
        self.modules: Dict[str, Module] = {}
        self.shutdown_event = Event()
        self.monitor_thread: Optional[Thread] = None
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self._load_config()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logging.info("=" * 60)
        logging.info("JETBOT ROBOT LAUNCHER - INITIALIZING")
        logging.info("=" * 60)
    
    def _setup_logging(self):
        """Configure logging system"""
        log_dir = Path("/var/log/jetbot")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"launcher_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _load_config(self):
        """Load module configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            for module_name, module_cfg in config.get('modules', {}).items():
                if module_cfg.get('enabled', True):
                    module_config = ModuleConfig(
                        name=module_name,
                        script_path=module_cfg['script_path'],
                        enabled=module_cfg.get('enabled', True),
                        max_retries=module_cfg.get('max_retries', 5),
                        retry_delay=module_cfg.get('retry_delay', 10),
                        critical=module_cfg.get('critical', False)
                    )
                    self.modules[module_name] = Module(module_config)
                    logging.info(f"Loaded module config: {module_name}")
            
            logging.info(f"Loaded {len(self.modules)} module(s) from configuration")
            
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            logging.info("Using default module configuration")
            self._load_default_config()
    
    def _load_default_config(self):
        """Fallback default configuration"""
        default_modules = [
            ModuleConfig("llm", "modules/llm_module.py", critical=False),
            ModuleConfig("face", "modules/face_module.py", critical=False),
            ModuleConfig("voice", "modules/voice_module.py", critical=False),
            ModuleConfig("camera", "modules/camera_module.py", critical=False),
            ModuleConfig("controller", "modules/controller_module.py", critical=False),
            ModuleConfig("ros_nav", "modules/ros_navigation.py", critical=False),
        ]
        
        for config in default_modules:
            self.modules[config.name] = Module(config)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        sig_name = signal.Signals(signum).name
        logging.info(f"Received signal {sig_name} - Initiating graceful shutdown...")
        self.shutdown()
    
    def start_all_modules(self):
        """Start all enabled modules"""
        logging.info("Starting all modules...")
        
        for name, module in self.modules.items():
            if module.config.enabled:
                success = module.start()
                if not success:
                    logging.warning(f"Module {name} failed to start initially")
                time.sleep(2)  # Stagger module starts
        
        logging.info("All modules started")
    
    def monitor_modules(self):
        """Monitor module health and restart crashed modules"""
        logging.info("Module monitoring started")
        
        while not self.shutdown_event.is_set():
            for name, module in self.modules.items():
                if not module.config.enabled:
                    continue
                
                # Check if module is supposed to be running but isn't
                if module.state == ModuleState.RUNNING and not module.is_alive():
                    logging.error(f"[{name}] CRASHED - Process died unexpectedly")
                    module.crash_count += 1
                    module.state = ModuleState.FAILED
                    
                    # Attempt restart if within retry limit
                    if module.should_restart():
                        module.retry_count += 1
                        logging.info(f"[{name}] Attempting restart {module.retry_count}/{module.config.max_retries}")
                        module.state = ModuleState.RESTARTING
                        
                        time.sleep(module.config.retry_delay)
                        
                        if module.start():
                            module.retry_count = 0  # Reset on successful restart
                        else:
                            logging.error(f"[{name}] Restart attempt failed")
                    else:
                        logging.error(f"[{name}] Max retries exceeded - Module permanently failed")
                        
                        # If critical module fails permanently, shutdown system
                        if module.config.critical:
                            logging.critical(f"Critical module {name} failed permanently - Shutting down launcher")
                            self.shutdown()
                            break
            
            time.sleep(5)  # Check every 5 seconds
    
    def run(self):
        """Main run loop"""
        try:
            # Start all modules
            self.start_all_modules()
            
            # Start monitoring thread
            self.monitor_thread = Thread(target=self.monitor_modules, daemon=True)
            self.monitor_thread.start()
            
            logging.info("Jetbot launcher running - Press Ctrl+C to shutdown")
            
            # Keep main thread alive
            while not self.shutdown_event.is_set():
                time.sleep(1)
        
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")
            self.shutdown()
        
        except Exception as e:
            logging.critical(f"Fatal error in launcher: {e}", exc_info=True)
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown of all modules"""
        if self.shutdown_event.is_set():
            return  # Already shutting down
        
        logging.info("=" * 60)
        logging.info("JETBOT LAUNCHER - SHUTTING DOWN")
        logging.info("=" * 60)
        
        self.shutdown_event.set()
        
        # Stop all modules
        for name, module in self.modules.items():
            module.stop()
        
        # Wait for monitor thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        logging.info("Jetbot launcher shutdown complete")
        sys.exit(0)
    
    def get_status(self) -> Dict:
        """Get current status of all modules"""
        status = {}
        for name, module in self.modules.items():
            status[name] = {
                'state': module.state.value,
                'alive': module.is_alive(),
                'retry_count': module.retry_count,
                'crash_count': module.crash_count,
                'pid': module.process.pid if module.process else None
            }
        return status

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    launcher = JetbotLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
