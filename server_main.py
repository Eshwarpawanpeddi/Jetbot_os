#!/usr/bin/env python3
"""
JetBot OS - Flask Server
Updated for ESP12E WiFi control + Face Display
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, broadcast
import logging
import time
import json
from datetime import datetime
from esp12e_controller import ESP12EController
from enhanced_face_renderer import Emotion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize ESP12E controller
ESP12E_IP = "192.168.1.50"  # Change to your ESP12E IP
motor_controller = ESP12EController(ESP12E_IP)

# Track system state
system_state = {
    'motor_running': False,
    'current_emotion': 'neutral',
    'robot_connected': False,
    'esp12e_status': 'disconnected'
}

# ============================================================================
# INITIALIZATION
# ============================================================================

@app.before_request
def initialize_system():
    """Initialize system on first request"""
    global motor_controller
    
    if not motor_controller.connected:
        if motor_controller.test_connection():
            system_state['robot_connected'] = True
            system_state['esp12e_status'] = 'connected'
            logger.info("✓ ESP12E connected via WiFi")
        else:
            logger.warning("✗ ESP12E not responding")

# ============================================================================
# MOTOR CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/motor/<direction>', methods=['POST'])
def control_motor(direction):
    """
    Control motors via WiFi to ESP12E
    
    Args:
        direction: 'forward', 'backward', 'left', 'right', 'stop'
    """
    try:
        data = request.get_json() or {}
        speed = data.get('speed', 255)
        duration = data.get('duration', 0)
        
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
        else:
            return jsonify({'status': 'error', 'message': 'Unknown direction'}), 400
        
        if success:
            system_state['motor_running'] = (direction != 'stop')
            socketio.emit('motor_update', {
                'direction': direction,
                'speed': speed,
                'status': 'success'
            }, broadcast=True)
            
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
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/motor/timed', methods=['POST'])
def motor_timed():
    """
    Move motor for specific duration
    
    Body: {
        'direction': 'forward',
        'duration_ms': 2000,
        'speed': 200
    }
    """
    try:
        data = request.get_json()
        direction = data.get('direction')
        duration_ms = data.get('duration_ms', 2000)
        speed = data.get('speed', 255)
        
        success = motor_controller.move_timed(direction, duration_ms, speed)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Motor moved {direction} for {duration_ms}ms'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send timed command'
            }), 500
            
    except Exception as e:
        logger.error(f"Timed motor error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# SENSOR ENDPOINTS
# ============================================================================

@app.route('/api/sensor/<sensor_type>', methods=['GET'])
def read_sensor(sensor_type):
    """
    Read sensor from ESP12E
    
    sensor_type: 'distance', 'battery', 'temperature'
    """
    try:
        value = motor_controller.read_sensor(sensor_type)
        
        if value is not None:
            return jsonify({
                'status': 'success',
                'sensor': sensor_type,
                'value': value,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to read {sensor_type}'
            }), 500
            
    except Exception as e:
        logger.error(f"Sensor read error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# EMOTION CONTROL (Face Display)
# ============================================================================

@app.route('/api/emotion/<emotion_name>', methods=['POST'])
def set_emotion(emotion_name):
    """
    Set robot emotion (triggers face animation on Jetson display)
    
    Valid emotions: happy, sad, excited, neutral, confused, angry, thinking, love, skeptical, sleeping
    """
    try:
        # Validate emotion
        try:
            emotion = Emotion[emotion_name.upper()]
        except KeyError:
            return jsonify({
                'status': 'error',
                'message': f'Invalid emotion: {emotion_name}',
                'valid_emotions': [e.value for e in Emotion]
            }), 400
        
        system_state['current_emotion'] = emotion.value
        
        # Broadcast to all connected clients (including Jetson display)
        socketio.emit('emotion_update', {
            'emotion': emotion.value,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        logger.info(f"Emotion updated: {emotion.value}")
        
        return jsonify({
            'status': 'success',
            'emotion': emotion.value
        })
        
    except Exception as e:
        logger.error(f"Emotion set error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# SYSTEM STATUS ENDPOINTS
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get full system status"""
    try:
        esp12e_status = motor_controller.get_status()
        
        return jsonify({
            'status': 'success',
            'system': system_state,
            'esp12e': esp12e_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/connection/test', methods=['POST'])
def test_connection():
    """Test ESP12E connection"""
    try:
        connected = motor_controller.test_connection()
        
        system_state['robot_connected'] = connected
        system_state['esp12e_status'] = 'connected' if connected else 'disconnected'
        
        return jsonify({
            'status': 'success',
            'connected': connected,
            'esp12e_ip': motor_controller.esp12e_ip
        })
        
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# WEB INTERFACE (Optional Dashboard)
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

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

@socketio.on('request_status')
def handle_status_request():
    emit('system_state', system_state)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("JETBOT OS - FLASK SERVER")
    logger.info("=" * 70)
    logger.info(f"ESP12E IP: {ESP12E_IP}")
    logger.info(f"Server: http://0.0.0.0:5000")
    logger.info("=" * 70)
    
    # Start server
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )

