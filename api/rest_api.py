#!/usr/bin/env python3
"""
REST API Server - HTTP endpoints for Android app integration
Provides control, status, and media access endpoints
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for Android app

# Configuration
MEDIA_DIR = Path("/opt/jetbot/media")
PHOTO_DIR = MEDIA_DIR / "photos"
VIDEO_DIR = MEDIA_DIR / "videos"

# Global state (will be updated by event bus)
robot_state = {
    'mode': 'auto',
    'battery': 100,
    'wifi_connected': True,
    'camera_active': False,
    'face_emotion': 'neutral',
    'status_message': 'Ready',
    'navigation_status': 'idle',
    'last_update': datetime.now().isoformat()
}

# ============================================================================
# STATUS ENDPOINTS
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current robot status"""
    robot_state['last_update'] = datetime.now().isoformat()
    return jsonify({
        'success': True,
        'data': robot_state
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# ============================================================================
# MODE CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/mode', methods=['GET'])
def get_mode():
    """Get current control mode"""
    return jsonify({
        'success': True,
        'mode': robot_state['mode']
    })

@app.route('/api/mode', methods=['POST'])
def set_mode():
    """Set control mode (manual/auto)"""
    data = request.json
    mode = data.get('mode', '').lower()
    
    if mode not in ['manual', 'auto']:
        return jsonify({
            'success': False,
            'error': 'Invalid mode. Must be "manual" or "auto"'
        }), 400
    
    # Publish mode change event
    event_bus.publish(
        EventType.MODE_CHANGED,
        {'mode': mode},
        source='rest_api'
    )
    
    robot_state['mode'] = mode
    
    return jsonify({
        'success': True,
        'mode': mode
    })

# ============================================================================
# MOVEMENT CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/movement', methods=['POST'])
def control_movement():
    """Send movement command (manual mode only)"""
    if robot_state['mode'] != 'manual':
        return jsonify({
            'success': False,
            'error': 'Movement control only available in manual mode'
        }), 403
    
    data = request.json
    left_motor = data.get('left_motor', 0)
    right_motor = data.get('right_motor', 0)
    
    # Validate motor values (-1 to 1)
    if not (-1 <= left_motor <= 1 and -1 <= right_motor <= 1):
        return jsonify({
            'success': False,
            'error': 'Motor values must be between -1 and 1'
        }), 400
    
    # Publish movement command
    event_bus.publish(
        EventType.MOVEMENT_COMMAND,
        {
            'left_motor': left_motor,
            'right_motor': right_motor,
            'source': 'app'
        },
        source='rest_api'
    )
    
    return jsonify({
        'success': True,
        'left_motor': left_motor,
        'right_motor': right_motor
    })

@app.route('/api/movement/stop', methods=['POST'])
def stop_movement():
    """Emergency stop"""
    event_bus.publish(
        EventType.MOVEMENT_COMMAND,
        {
            'left_motor': 0,
            'right_motor': 0,
            'source': 'app_stop'
        },
        source='rest_api'
    )
    
    return jsonify({
        'success': True,
        'message': 'Movement stopped'
    })

# ============================================================================
# CAMERA ENDPOINTS
# ============================================================================

@app.route('/api/camera/photo', methods=['POST'])
def take_photo():
    """Take a photo"""
    # Publish photo request event
    event_bus.publish(
        EventType.CAMERA_FRAME,
        {'action': 'take_photo'},
        source='rest_api'
    )
    
    # Wait briefly for photo to be taken
    # In production, use async/await or callbacks
    import time
    time.sleep(0.5)
    
    # Get latest photo
    photos = sorted(PHOTO_DIR.glob('*.jpg'), key=os.path.getmtime, reverse=True)
    
    if photos:
        latest_photo = photos[0]
        return jsonify({
            'success': True,
            'filename': latest_photo.name,
            'path': f'/api/media/photos/{latest_photo.name}',
            'timestamp': datetime.fromtimestamp(latest_photo.stat().st_mtime).isoformat()
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No photos available'
        }), 404

@app.route('/api/camera/recording/start', methods=['POST'])
def start_recording():
    """Start video recording"""
    event_bus.publish(
        EventType.VIDEO_RECORDING,
        {'action': 'start'},
        source='rest_api'
    )
    
    return jsonify({
        'success': True,
        'message': 'Recording started'
    })

@app.route('/api/camera/recording/stop', methods=['POST'])
def stop_recording():
    """Stop video recording"""
    event_bus.publish(
        EventType.VIDEO_RECORDING,
        {'action': 'stop'},
        source='rest_api'
    )
    
    return jsonify({
        'success': True,
        'message': 'Recording stopped'
    })

# ============================================================================
# MEDIA ACCESS ENDPOINTS
# ============================================================================

@app.route('/api/media/photos', methods=['GET'])
def list_photos():
    """List all photos"""
    photos = sorted(PHOTO_DIR.glob('*.jpg'), key=os.path.getmtime, reverse=True)
    
    photo_list = [
        {
            'filename': photo.name,
            'path': f'/api/media/photos/{photo.name}',
            'size': photo.stat().st_size,
            'timestamp': datetime.fromtimestamp(photo.stat().st_mtime).isoformat()
        }
        for photo in photos
    ]
    
    return jsonify({
        'success': True,
        'count': len(photo_list),
        'photos': photo_list
    })

@app.route('/api/media/photos/<filename>', methods=['GET'])
def get_photo(filename):
    """Download a specific photo"""
    photo_path = PHOTO_DIR / filename
    
    if not photo_path.exists():
        return jsonify({
            'success': False,
            'error': 'Photo not found'
        }), 404
    
    return send_file(photo_path, mimetype='image/jpeg')

@app.route('/api/media/videos', methods=['GET'])
def list_videos():
    """List all videos"""
    videos = sorted(VIDEO_DIR.glob('*.avi'), key=os.path.getmtime, reverse=True)
    
    video_list = [
        {
            'filename': video.name,
            'path': f'/api/media/videos/{video.name}',
            'size': video.stat().st_size,
            'timestamp': datetime.fromtimestamp(video.stat().st_mtime).isoformat()
        }
        for video in videos
    ]
    
    return jsonify({
        'success': True,
        'count': len(video_list),
        'videos': video_list
    })

@app.route('/api/media/videos/<filename>', methods=['GET'])
def get_video(filename):
    """Download a specific video"""
    video_path = VIDEO_DIR / filename
    
    if not video_path.exists():
        return jsonify({
            'success': False,
            'error': 'Video not found'
        }), 404
    
    return send_file(video_path, mimetype='video/x-msvideo')

# ============================================================================
# VOICE/LLM INTERACTION ENDPOINTS
# ============================================================================

@app.route('/api/chat', methods=['POST'])
def send_chat_message():
    """Send text message to LLM"""
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({
            'success': False,
            'error': 'Message is required'
        }), 400
    
    # Publish LLM request
    event_bus.publish(
        EventType.LLM_REQUEST,
        {
            'text': message,
            'source': 'app'
        },
        source='rest_api'
    )
    
    # TODO: In production, use async/await to get actual response
    # For now, return acknowledgment
    return jsonify({
        'success': True,
        'message': 'Message sent to robot',
        'sent_message': message
    })

@app.route('/api/voice/speak', methods=['POST'])
def speak_text():
    """Make robot speak text"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'Text is required'
        }), 400
    
    # Publish voice output event
    event_bus.publish(
        EventType.VOICE_OUTPUT,
        {'text': text},
        source='rest_api'
    )
    
    return jsonify({
        'success': True,
        'message': f'Speaking: {text}'
    })

# ============================================================================
# FACE CONTROL ENDPOINTS
# ============================================================================

@app.route('/api/face/emotion', methods=['POST'])
def set_face_emotion():
    """Set face emotion"""
    data = request.json
    emotion = data.get('emotion', 'neutral')
    
    valid_emotions = ['happy', 'sad', 'angry', 'crying', 'excited', 
                     'sleepy', 'thinking', 'confused', 'neutral']
    
    if emotion not in valid_emotions:
        return jsonify({
            'success': False,
            'error': f'Invalid emotion. Valid options: {", ".join(valid_emotions)}'
        }), 400
    
    # Publish face emotion event
    event_bus.publish(
        EventType.FACE_EMOTION,
        {'emotion': emotion},
        source='rest_api'
    )
    
    robot_state['face_emotion'] = emotion
    
    return jsonify({
        'success': True,
        'emotion': emotion
    })

# ============================================================================
# EVENT BUS LISTENERS
# ============================================================================

def handle_mode_change(event):
    """Update state when mode changes"""
    robot_state['mode'] = event.data.get('mode', robot_state['mode'])

def handle_battery_status(event):
    """Update battery status"""
    robot_state['battery'] = event.data.get('level', robot_state['battery'])

def handle_navigation_status(event):
    """Update navigation status"""
    robot_state['navigation_status'] = event.data.get('status', 'unknown')

def handle_face_emotion(event):
    """Update face emotion"""
    robot_state['face_emotion'] = event.data.get('emotion', robot_state['face_emotion'])

def handle_face_status(event):
    """Update status message"""
    robot_state['status_message'] = event.data.get('status', robot_state['status_message'])

# Subscribe to events
event_bus.subscribe(EventType.MODE_CHANGED, handle_mode_change)
event_bus.subscribe(EventType.BATTERY_STATUS, handle_battery_status)
event_bus.subscribe(EventType.NAVIGATION_STATUS, handle_navigation_status)
event_bus.subscribe(EventType.FACE_EMOTION, handle_face_emotion)
event_bus.subscribe(EventType.FACE_STATUS, handle_face_status)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# ============================================================================
# MAIN
# ============================================================================

def run_api_server(host='0.0.0.0', port=5000):
    """Run the REST API server"""
    logging.info(f"Starting REST API server on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | REST_API | %(levelname)s | %(message)s'
    )
    run_api_server()
