#!/bin/bash
# ==============================================================================
# JETBOT OS - SILENT MASTER FIX
# 1. Removes conflicting files automatically
# 2. Patches Voice & Controller modules automatically
# 3. Skips API Key prompt (Edit the variable below to set it)
# ==============================================================================

# --- CONFIGURATION ---
# Paste your key inside the quotes below if you want to set it now. 
# Otherwise, leave it empty.
OPENAI_API_KEY="" 
# ---------------------

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== STARTING SILENT REPAIR ===${NC}"

# --- STEP 1: REMOVE CONFLICTING FILES ---
echo -e "\n${YELLOW}[1/4] Removing conflicting 'System B' files...${NC}"
FILES_TO_REMOVE=(
    "main_launcher.py"
    "setup/robot-launcher.service"
    "core/event_bus.py"
    "core"
    "modules/face_display.py"
    "modules/llm_voice.py"
    "modules/navigation.py"
    "modules/web_api.py"
)

for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -e "$file" ]; then
        rm -rf "$file"
        echo "  - Deleted: $file"
    fi
done

# --- STEP 2: PATCH VOICE MODULE ---
echo -e "\n${YELLOW}[2/4] Patching Voice Module (Real Audio)...${NC}"
cat > modules/voice_module.py << 'EOF'
#!/usr/bin/env python3
"""
Voice Module - TTS, STT, and Emotion Detection
Fully implemented using SpeechRecognition and pyttsx3
"""
import sys
import os
import time
import logging
import threading
import shutil
import speech_recognition as sr
import pyttsx3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

class VoiceModule:
    def __init__(self):
        self.tts_enabled = True
        self.stt_enabled = True
        self.is_listening = False
        self.tts_engine = None
        
        # Check system audio dependencies
        if sys.platform == "linux":
            if not (shutil.which("espeak") or shutil.which("espeak-ng")):
                logging.error("CRITICAL: 'espeak' not found. Please run: sudo apt-get install espeak")
                self.tts_enabled = False

        if self.tts_enabled:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.9)
            except Exception as e:
                logging.error(f"TTS Init Failed: {e}")
                self.tts_enabled = False

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
        except Exception as e:
            logging.error(f"Mic Init Failed: {e}")
            self.stt_enabled = False

        logging.info(f"Voice Module initialized (TTS: {self.tts_enabled}, STT: {self.stt_enabled})")
    
    def text_to_speech(self, text: str):
        if not self.tts_enabled or not text: return
        logging.info(f"Speaking: {text}")
        event_bus.publish(EventType.VOICE_OUTPUT, {'text': text, 'status': 'start'}, "voice_module")
        try:
            if self.tts_engine:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
        except RuntimeError: pass
        except Exception as e: logging.error(f"TTS Error: {e}")
        event_bus.publish(EventType.VOICE_OUTPUT, {'text': text, 'status': 'end'}, "voice_module")
    
    def listen_loop(self):
        if not self.stt_enabled: return
        logging.info("Listening...")
        while self.is_listening:
            try:
                with self.microphone as source:
                    try:
                        audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=5.0)
                    except sr.WaitTimeoutError: continue
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    logging.info(f"Heard: {text}")
                    event_bus.publish(EventType.VOICE_INPUT, {'text': text}, source="voice_module")
                    event_bus.publish(EventType.LLM_REQUEST, {'text': text}, source="voice_module")
                except sr.UnknownValueError: pass
                except sr.RequestError as e: logging.error(f"STT Error: {e}")
            except Exception: time.sleep(1)

    def handle_llm_response(self, event):
        text = event.data.get('text', '')
        if text: threading.Thread(target=self.text_to_speech, args=(text,)).start()
    
    def run(self):
        event_bus.subscribe(EventType.LLM_RESPONSE, self.handle_llm_response)
        self.is_listening = True
        threading.Thread(target=self.listen_loop, daemon=True).start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt: self.is_listening = False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | VOICE | %(levelname)s | %(message)s')
    VoiceModule().run()
EOF

# --- STEP 3: PATCH CONTROLLER MODULE ---
echo -e "\n${YELLOW}[3/4] Patching Controller Module (Headless Safe)...${NC}"
cat > modules/controller_module.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import time
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.event_bus import event_bus, EventType

# Set dummy driver to prevent crash on headless systems
os.environ["SDL_VIDEODRIVER"] = "dummy"

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

class ControllerModule:
    def __init__(self):
        self.controller = None
        self.current_mode = "auto"
        if PYGAME_AVAILABLE:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                logging.info(f"Controller: {self.controller.get_name()}")
            else:
                logging.warning("No joystick detected.")
        else:
            logging.warning("Pygame not installed.")

    def run(self):
        logging.info("Controller running (Headless Mode)")
        try:
            while True:
                if self.controller:
                    pygame.event.pump()
                    # Axis 1 is Left Stick Y (Speed), Axis 0 is Left Stick X (Turn)
                    speed = -self.controller.get_axis(1)
                    turn = self.controller.get_axis(0)
                    
                    if abs(speed) > 0.1 or abs(turn) > 0.1:
                         # Simple steering mix
                        left = speed + turn
                        right = speed - turn
                        # Clamp
                        left = max(-1, min(1, left))
                        right = max(-1, min(1, right))
                        
                        event_bus.publish(EventType.MOVEMENT_COMMAND, 
                            {'left_motor': left, 'right_motor': right}, "controller")
                time.sleep(0.05)
        except KeyboardInterrupt: pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | CTRL | %(levelname)s | %(message)s')
    ControllerModule().run()
EOF

# --- STEP 4: SETUP API KEY (Silent Mode) ---
echo -e "\n${YELLOW}[4/4] Configuring Service...${NC}"

SERVICE_FILE="jetbot.service"
if [ -f "$SERVICE_FILE" ]; then
    if [ -n "$OPENAI_API_KEY" ]; then
        # Remove old key if exists and add new one
        sed -i '/Environment="LLM_API_KEY=/d' "$SERVICE_FILE"
        sed -i "/\[Service\]/a Environment=\"LLM_API_KEY=$OPENAI_API_KEY\"" "$SERVICE_FILE"
        echo "  - API Key applied from script variable."
    else
        echo "  - No API Key variable set. Skipping LLM configuration."
    fi
    
    # Reload service
    # Only try systemd reload if we are on the robot/Linux
    if command -v systemctl &> /dev/null; then
        sudo cp "$SERVICE_FILE" /lib/systemd/system/
        sudo systemctl daemon-reload
    else
        echo "  - Skipped systemd reload (Not on Linux/Robot)."
    fi
else
    echo "  ! Error: jetbot.service not found."
fi

echo -e "\n${GREEN}=== FIXES APPLIED SUCCESSFULLY ===${NC}"
echo "Restart the robot with: sudo systemctl restart jetbot"
