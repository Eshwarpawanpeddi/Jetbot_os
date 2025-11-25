#!/usr/bin/env python3
"""
WebSocket Server - Real-time bidirectional communication with Android app
Pushes live updates and receives commands
"""

import os
import sys
import json
import logging
import asyncio
import websockets
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# Connected clients
connected_clients = set()

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

async def handle_client(websocket, path):
    """Handle WebSocket client connection"""
    client_id = id(websocket)
    connected_clients.add(websocket)
    logging.info(f"Client {client_id} connected (total: {len(connected_clients)})")
    
    try:
        # Send welcome message
        await websocket.send(json.dumps({
            'type': 'connection',
            'status': 'connected',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        }))
        
        # Listen for messages from client
        async for message in websocket:
            try:
                data = json.loads(message)
                await process_client_message(data, websocket)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON format'
                }))
            except Exception as e:
                logging.error(f"Error processing message: {e}")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
    
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"Client {client_id} disconnected")
    
    finally:
        connected_clients.remove(websocket)
        logging.info(f"Client {client_id} removed (remaining: {len(connected_clients)})")

async def process_client_message(data, websocket):
    """Process messages received from client"""
    message_type = data.get('type')
    
    if message_type == 'ping':
        # Heartbeat
        await websocket.send(json.dumps({
            'type': 'pong',
            'timestamp': datetime.now().isoformat()
        }))
    
    elif message_type == 'subscribe':
        # Client subscribing to specific events
        events = data.get('events', [])
        await websocket.send(json.dumps({
            'type': 'subscribed',
            'events': events
        }))
    
    elif message_type == 'command':
        # Execute command via event bus
        command = data.get('command')
        params = data.get('params', {})
        
        # Map commands to event types
        command_map = {
            'set_mode': EventType.MODE_CHANGED,
            'move': EventType.MOVEMENT_COMMAND,
            'set_emotion': EventType.FACE_EMOTION,
            'speak': EventType.VOICE_OUTPUT,
            'chat': EventType.LLM_REQUEST
        }
        
        if command in command_map:
            event_bus.publish(
                command_map[command],
                params,
                source='websocket'
            )
            
            await websocket.send(json.dumps({
                'type': 'command_ack',
                'command': command,
                'status': 'executed'
            }))
        else:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Unknown command: {command}'
            }))

# ============================================================================
# BROADCAST FUNCTIONS
# ============================================================================

async def broadcast_to_clients(message_dict):
    """Broadcast message to all connected clients"""
    if not connected_clients:
        return
    
    message = json.dumps(message_dict)
    
    # Send to all clients concurrently
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True
    )

def broadcast_event(event_type, data):
    """Broadcast event to WebSocket clients (sync wrapper)"""
    message = {
        'type': 'event',
        'event_type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    
    # Schedule broadcast in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_to_clients(message))
        else:
            loop.run_until_complete(broadcast_to_clients(message))
    except RuntimeError:
        # No event loop running
        pass

# ============================================================================
# EVENT BUS LISTENERS
# ============================================================================

def handle_mode_change(event):
    """Broadcast mode changes"""
    broadcast_event('mode_changed', {
        'mode': event.data.get('mode')
    })

def handle_llm_response(event):
    """Broadcast LLM responses"""
    broadcast_event('llm_response', {
        'text': event.data.get('text'),
        'intent': event.data.get('intent')
    })

def handle_face_emotion(event):
    """Broadcast face emotion changes"""
    broadcast_event('face_emotion', {
        'emotion': event.data.get('emotion')
    })

def handle_battery_status(event):
    """Broadcast battery status"""
    broadcast_event('battery_status', {
        'level': event.data.get('level'),
        'charging': event.data.get('charging', False)
    })

def handle_obstacle_detected(event):
    """Broadcast obstacle detection"""
    broadcast_event('obstacle_detected', {
        'distance': event.data.get('distance'),
        'direction': event.data.get('direction')
    })

def handle_navigation_status(event):
    """Broadcast navigation status"""
    broadcast_event('navigation_status', {
        'status': event.data.get('status')
    })

# Subscribe to events
event_bus.subscribe(EventType.MODE_CHANGED, handle_mode_change)
event_bus.subscribe(EventType.LLM_RESPONSE, handle_llm_response)
event_bus.subscribe(EventType.FACE_EMOTION, handle_face_emotion)
event_bus.subscribe(EventType.BATTERY_STATUS, handle_battery_status)
event_bus.subscribe(EventType.OBSTACLE_DETECTED, handle_obstacle_detected)
event_bus.subscribe(EventType.NAVIGATION_STATUS, handle_navigation_status)

# ============================================================================
# MAIN SERVER
# ============================================================================

async def run_websocket_server(host='0.0.0.0', port=8765):
    """Start WebSocket server"""
    logging.info(f"Starting WebSocket server on ws://{host}:{port}")
    
    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()  # Run forever

def start_server(host='0.0.0.0', port=8765):
    """Start WebSocket server (blocking)"""
    asyncio.run(run_websocket_server(host, port))

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | WEBSOCKET | %(levelname)s | %(message)s'
    )
    start_server()
