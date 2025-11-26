import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.event_bus import EventType, RobotEvent
import threading

# Data Models
class MoveCommand(BaseModel):
    x: float # Linear velocity
    y: float # Angular velocity

class ModeCommand(BaseModel):
    mode: str # "auto" or "manual"

class SpeakCommand(BaseModel):
    text: str

def run_api_module(bus, sub_queue, config):
    """
    Starts the FastAPI server. 
    Note: Uvicorn runs in a thread here to allow non-blocking usage if needed, 
    but since this is a dedicated process, blocking is fine.
    """
    app = FastAPI(title="Jetbot Controller API")

    @app.get("/")
    def status():
        return {"status": "online", "battery": "85%"} # Placeholder for actual battery read

    @app.post("/control/move")
    def move_robot(cmd: MoveCommand):
        # Publish move command to bus
        bus.publish(RobotEvent(EventType.MoveCommand, {"x": cmd.x, "y": cmd.y}))
        return {"status": "command_sent"}

    @app.post("/control/speak")
    def make_speak(cmd: SpeakCommand):
        bus.publish(RobotEvent(EventType.Speak, {"text": cmd.text}))
        return {"status": "speaking"}

    @app.post("/system/mode")
    def set_mode(cmd: ModeCommand):
        if cmd.mode.upper() not in ["AUTO", "MANUAL"]:
            raise HTTPException(status_code=400, detail="Invalid mode")
        bus.publish(RobotEvent(EventType.ModeSwitch, cmd.mode.upper()))
        return {"mode": cmd.mode.upper()}

    # Start Server
    uvicorn.run(app, host="0.0.0.0", port=config['network']['api_port'], log_level="info")
