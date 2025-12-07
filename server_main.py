#!/usr/bin/env python3
"""
JetBot OS - Flask Server (CORRECTED & PRODUCTION-READY)
Handles motor control, display, and mobile app communication
Fixed errors and production-ready with proper error handling
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from enum import Enum
import threading
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from esp12e_controller import ESP12EController

# ============================================================================
# LOGGING SETUP
# ============================================================================

os.makedirs('logs', exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler with rotation
file_handler = RotatingFileHandler(
    os.getenv('LOG_FILE', 'logs/jetbot_server.log'),
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(console_handler)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Emotion(Enum):
    """Robot emotions"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CONFUSED = "confused"
    ANGRY = "angry"
    THINKING = "thinking"
    LOVE = "love"
    SKEPTICAL = "skeptical"
    SLEEPING = "sleeping"


def load_config():
    """Load configuration from environment variables"""
    config = {
        'esp12e_ip': os.getenv('ESP12E_IP', '192.168.1.50'),
        'esp12e_port': int(os.getenv('ESP12E_PORT', 80)),
        'esp12e_timeout': int(os.getenv('ESP12E_TIMEOUT', 5)),
        'server_host': os.getenv('SERVER_HOST', '0.0.0.0'),
        'server_port': int(os.getenv('SERVER_PORT', 5000)),
        'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true',
        'motor_max_speed': int(os.getenv('MOTOR_MAX_SPEED', 255)),
        'motor_default_speed': int(os.getenv('MOTOR_DEFAULT_SPEED', 200)),
        'motor_safety_timeout': int(os.getenv('MOTOR_SAFETY_TIMEOUT', 5000)),
    }
    
    logger.info("Configuration loaded:")
    logger.info(f"  ESP12E: {config['esp12e_ip']}:{config['esp12e_port']}")
    logger.info(f"  Server: {config['server_host']}:{config['server_port']}")
    logger.info(f"  Motor Timeout: {config['motor_safety_timeout']}ms")
    
    return config


config = load_config()

# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')

# CORS - Use allowed origins from env
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, resources={r"/*": {"origins": allowed_origins}})
socketio = SocketIO(app, cors_allowed_origins=allowed_origins)

# ============================================================================
# MOTOR CONTROLLER INITIALIZATION
# ============================================================================

motor_controller = None

try:
    motor_controller = ESP12EController(
        esp12e_ip=config['esp12e_ip'],
        timeout=config['esp12e_timeout']
    )
    logger.info("✓ ESP12E controller initialized")
except Exception as e:
    logger.error(f"✗ Failed to initialize ESP12E controller: {e}")
    motor_controller = None

# ============================================================================
# SYSTEM STATE
# ============================================================================

system_state = {
    'motor_running': False,
    'current_emotion': 'neutral',
    'robot_connected': False,
    'esp12e_status': 'disconnected',
    'server_uptime': datetime.now().isoformat(),
    'last_motor_command': None
}

# Motor timeout tracking
class MotorSafetyTimeout:
    """Ensures motors stop if no command is received within timeout"""
    
    def __init__(self, timeout_ms=5000):
        self.timeout_ms = timeout_ms
        self.last_command_time = None
    
    def record_command(self):
        """Record when a motor command was last sent"""
        self.last_command_time = time.time()
    
    def check_timeout(self):
        """Check if motors should be stopped due to timeout"""
        if self.last_command_time:
            elapsed = (time.time() - self.last_command_time) * 1000
            if elapsed > self.timeout_ms:
                logger.warning(f"Motor safety timeout triggered ({elapsed:.0f}ms)")
                if motor_controller:
                    motor_controller.stop()
                self.last_command_time = None


motor_safety = MotorSafetyTimeout(config['motor_safety_timeout'])

# ============================================================================
# BACKGROUND SAFETY THREAD
# ============================================================================

def background_safety_monitor():
    """Monitor motor safety timeouts in background"""
    while True:
        try:
            motor_safety.check_timeout()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Safety monitor error: {e}")


safety_thread = threading.Thread(target=background_safety_monitor, daemon=True)
safety_thread.start()
logger.info("✓ Safety monitor thread started")

# ============================================================================
# INITIALIZATION ENDPOINT
# ============================================================================

@app.before_request
def initialize_system():
    """Initialize system on first request"""
    global motor_controller
    
    if motor_controller and not motor_controller.connected:
        if motor_controller.test_connection():
            system_state['robot_connected'] = True
            system_state['esp12e_status'] = 'connected'
            logger.info("✓ ESP12E connected via WiFi")
        else:
            logger.warning("✗ ESP12E not responding")
            system_state['esp12e_status'] = 'disconnected'

# ============================================================================
# MOTOR CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/motor/<direction>', methods=['POST'])
def control_motor(direction):
    """
    Control motors via WiFi to ESP12E
    
    Request body:
    {
        "speed": 200  // Optional, 0-255
    }
    """
    try:
        # Validate direction
        valid_directions = ['forward', 'backward', 'left', 'right', 'stop']
        if direction not in valid_directions:
            return jsonify({
                'status': 'error',
                'message': f'Invalid direction: {direction}',
                'valid': valid_directions
            }), 400
        
        # Get and validate speed
        data = request.get_json() or {}
        try:
            speed = int(data.get('speed', config['motor_default_speed']))
            if not 0 <= speed <= config['motor_max_speed']:
                return jsonify({
                    'status': 'error',
                    'message': f'Speed must be 0-{config["motor_max_speed"]}'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Speed must be integer'
            }), 400
        
        # Send command
        if not motor_controller:
            return jsonify({
                'status': 'error',
                'message': 'Motor controller not available'
            }), 503
        
        success = False
        if direction == 'forward':
            success = motor_controller.move_forward(speed)
        elif direction == 'backward':
            success = motor_controller.move_backward(speed)
        elif direction == 'left':
            success = motor_controller.turn_left(speed)
        elif direction == 'right':
            success = motor_controller.turn_right(speed)
        elif direction == 'stop':
            success = motor_controller.stop()
        
        if success:
            system_state['motor_running'] = (direction != 'stop')
            system_state['last_motor_command'] = {
                'direction': direction,
                'speed': speed,
                'timestamp': datetime.now().isoformat()
            }
            motor_safety.record_command()
            
            socketio.emit('motor_update', {
                'direction': direction,
                'speed': speed,
                'status': 'success'
            }, broadcast=True)
            
            logger.info(f"Motor: {direction} @ {speed}")
            
            return jsonify({
                'status': 'success',
                'direction': direction,
                'speed': speed
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send command to ESP12E'
            }), 500
            
    except Exception as e:
        logger.error(f"Motor control error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================================
# EMOTION CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/emotion/<emotion_name>', methods=['POST'])
def set_emotion(emotion_name):
    """
    Set robot emotion display
    
    Valid emotions: neutral, happy, sad, excited, confused, angry, thinking, love, skeptical, sleeping
    """
    try:
        # Validate emotion
        try:
            emotion = Emotion[emotion_name.upper()]
        except KeyError:
            valid_emotions = [e.value for e in Emotion]
            return jsonify({
                'status': 'error',
                'message': f'Invalid emotion: {emotion_name}',
                'valid_emotions': valid_emotions
            }), 400
        
        system_state['current_emotion'] = emotion.value
        
        socketio.emit('emotion_update', {
            'emotion': emotion.value,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        logger.info(f"Emotion: {emotion.value}")
        
        return jsonify({
            'status': 'success',
            'emotion': emotion.value
        })
        
    except Exception as e:
        logger.error(f"Emotion set error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================================
# STATUS ENDPOINTS
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get full system status"""
    try:
        esp12e_status = None
        if motor_controller:
            esp12e_status = motor_controller.get_status()
        
        return jsonify({
            'status': 'success',
            'system': system_state,
            'esp12e': esp12e_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/connection/test', methods=['POST'])
def test_connection():
    """Test ESP12E connection"""
    try:
        if not motor_controller:
            return jsonify({
                'status': 'error',
                'message': 'Motor controller not initialized'
            }), 503
        
        connected = motor_controller.test_connection()
        system_state['robot_connected'] = connected
        system_state['esp12e_status'] = 'connected' if connected else 'disconnected'
        
        return jsonify({
            'status': 'success',
            'connected': connected,
            'esp12e_ip': config['esp12e_ip']
        })
        
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================================
# SENSOR ENDPOINTS
# ============================================================================

@app.route('/api/sensor/<sensor_type>', methods=['GET'])
def read_sensor(sensor_type):
    """
    Read sensor data
    
    Valid sensors: distance, battery, temperature
    """
    try:
        if not motor_controller:
            return jsonify({
                'status': 'error',
                'message': 'Motor controller not initialized'
            }), 503
        
        valid_sensors = ['distance', 'battery', 'temperature']
        if sensor_type not in valid_sensors:
            return jsonify({
                'status': 'error',
                'message': f'Invalid sensor: {sensor_type}',
                'valid_sensors': valid_sensors
            }), 400
        
        value = motor_controller.read_sensor(sensor_type)
        
        if value is not None:
            return jsonify({
                'status': 'success',
                'sensor': sensor_type,
                'value': value
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to read {sensor_type}'
            }), 500
            
    except Exception as e:
        logger.error(f"Sensor read error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Not Found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('system_state', system_state)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('motor_command')
def handle_motor_command(data):
    """Handle motor command via WebSocket"""
    try:
        direction = data.get('direction')
        speed = data.get('speed', config['motor_default_speed'])
        
        # Validate
        valid_directions = ['forward', 'backward', 'left', 'right', 'stop']
        if direction not in valid_directions:
            emit('error', {'message': f'Invalid direction: {direction}'})
            return
        
        speed = min(255, max(0, int(speed)))
        
        # Execute
        if not motor_controller:
            emit('error', {'message': 'Motor controller not available'})
            return
        
        success = False
        if direction == 'forward':
            success = motor_controller.move_forward(speed)
        elif direction == 'backward':
            success = motor_controller.move_backward(speed)
        elif direction == 'left':
            success = motor_controller.turn_left(speed)
        elif direction == 'right':
            success = motor_controller.turn_right(speed)
        elif direction == 'stop':
            success = motor_controller.stop()
        
        if success:
            motor_safety.record_command()
            emit('motor_update', {'direction': direction, 'speed': speed}, broadcast=True)
        else:
            emit('error', {'message': 'Failed to send command'})
            
    except Exception as e:
        logger.error(f"WebSocket motor command error: {e}")
        emit('error', {'message': str(e)})

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("JETBOT OS - FLASK SERVER")
    logger.info("=" * 70)
    logger.info(f"Server: {config['server_host']}:{config['server_port']}")
    logger.info(f"ESP12E: {config['esp12e_ip']}:{config['esp12e_port']}")
    logger.info(f"Debug: {config['debug_mode']}")
    logger.info("=" * 70)
    
    socketio.run(
        app,
        host=config['server_host'],
        port=config['server_port'],
        debug=config['debug_mode'],
        use_reloader=False,
        log_output=True
    )
