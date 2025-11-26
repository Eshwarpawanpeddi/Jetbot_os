#!/usr/bin/env python3
"""
Camera Streaming Server - MJPEG stream for Android app
Provides live camera feed over HTTP
"""

import os
import sys
import cv2
import time
import logging
import threading
from flask import Flask, Response

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# Initialize Flask app for streaming
stream_app = Flask(__name__)

# Global frame storage
latest_frame = None
frame_lock = threading.Lock()

# ============================================================================
# FRAME MANAGEMENT
# ============================================================================

def handle_camera_frame(event):
    """Receive camera frames from event bus"""
    global latest_frame
    
    frame = event.data.get('frame')
    if frame is not None:
        with frame_lock:
            latest_frame = frame

# Subscribe to camera frames
event_bus.subscribe(EventType.CAMERA_FRAME, handle_camera_frame)

def generate_frames():
    """Generator function for MJPEG streaming"""
    global latest_frame
    
    while True:
        with frame_lock:
            if latest_frame is None:
                # Send placeholder frame if no camera frame available
                placeholder = create_placeholder_frame()
                frame = placeholder
            else:
                frame = latest_frame.copy()
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.033)  # ~30 FPS

def create_placeholder_frame():
    """Create placeholder frame when camera not available"""
    import numpy as np
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, 'Camera Not Available', (150, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return frame

# ============================================================================
# STREAMING ENDPOINTS
# ============================================================================

@stream_app.route('/stream')
def video_stream():
    """MJPEG video stream endpoint"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@stream_app.route('/stream/health')
def stream_health():
    """Stream health check"""
    from flask import jsonify
    return jsonify({
        'status': 'healthy',
        'frame_available': latest_frame is not None
    })

# ============================================================================
# MAIN
# ============================================================================

def run_stream_server(host='0.0.0.0', port=5001):
    """Run the camera streaming server"""
    logging.info(f"Starting camera stream server on http://{host}:{port}/stream")
    stream_app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | STREAM | %(levelname)s | %(message)s'
    )
    run_stream_server()
