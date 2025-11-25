import cv2
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from core.event_bus import EventType, RobotEvent

# MJPEG Stream Server
class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            while True:
                try:
                    if img_data is not None:
                        self.wfile.write(b"--jpgboundary\r\n")
                        self.send_header('Content-type', 'image/jpeg')
                        self.send_header('Content-length', str(len(img_data)))
                        self.end_headers()
                        self.wfile.write(img_data)
                        self.wfile.write(b"\r\n")
                        time.sleep(0.05)
                    else:
                        time.sleep(0.1)
                except BrokenPipeError:
                    break
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Jetbot Cam</h1><img src='cam.mjpg'></body></html>")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

img_data = None

def run_camera_module(bus, sub_queue, config):
    global img_data
    
    # Jetson Nano CSI Camera Pipeline (High Performance)
    # If using USB Cam, replace with: cap = cv2.VideoCapture(0)
    gst_pipeline = (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
        "nvvidconv ! video/x-raw, width=640, height=360, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! appsink"
    )
    
    # Try CSI first, fall back to USB (index 0 or 1)
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        logging.warning("GStreamer failed, falling back to USB Camera")
        cap = cv2.VideoCapture(config['hardware']['camera_index'])

    # Start MJPEG Server
    server_port = config['network'].get('stream_port', 8080)
    server = ThreadedHTTPServer(('0.0.0.0', server_port), CamHandler)
    logging.info(f"Camera Stream started on port {server_port}")
    
    # Server runs in background (non-blocking for the loop)
    import threading
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    while True:
        ret, frame = cap.read()
        if ret:
            # Compression for network streaming
            _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            img_data = jpg.tobytes()
        else:
            logging.error("Camera frame read failed")
            time.sleep(1)
            
        # Optional: Check bus for "Take Photo" commands
        try:
            event = sub_queue.get_nowait()
            if event.type == EventType.StatusUpdate and event.payload == "CAPTURE":
                timestamp = int(time.time())
                cv2.imwrite(f"capture_{timestamp}.jpg", frame)
                logging.info(f"Photo taken: capture_{timestamp}.jpg")
        except:
            pass
            
        time.sleep(0.03) # Limit capture rate slightly
