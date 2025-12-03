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
    """Voice processing - TTS, STT, emotion detection"""
    
    def __init__(self):
        self.tts_enabled = True
        self.stt_enabled = True
        self.is_listening = False
        self.tts_engine = None
        
        # 1. Pre-flight Check: Verify System Dependencies
        # pyttsx3 on Linux requires 'espeak' or 'espeak-ng' to be installed.
        if sys.platform == "linux":
            if not (shutil.which("espeak") or shutil.which("espeak-ng")):
                logging.error("CRITICAL: 'espeak' library not found. TTS will fail.")
                logging.error("Please run: sudo apt-get install espeak")
                self.tts_enabled = False

        # 2. Initialize TTS Engine (Safely)
        if self.tts_enabled:
            try:
                self.tts_engine = pyttsx3.init()
                
                # Test the driver by querying properties
                # This usually triggers the crash if the driver is broken
                voices = self.tts_engine.getProperty('voices')
                if not voices:
                    logging.warning("TTS Warning: No voices detected. Output might be silent.")
                
                self.tts_engine.setProperty('rate', 150) # Speed
                self.tts_engine.setProperty('volume', 0.9)
                logging.info("TTS Engine initialized successfully.")
                
            except OSError as e:
                logging.error(f"TTS Driver Error (Shared library missing?): {e}")
                self.tts_enabled = False
            except Exception as e:
                logging.error(f"Failed to init TTS: {e}")
                self.tts_enabled = False

        # Initialize STT Recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise
        try:
            with self.microphone as source:
                logging.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source)
        except Exception as e:
            logging.error(f"Microphone initialization failed: {e}")
            self.stt_enabled = False

        logging.info("Voice Module initialized")
    
    def text_to_speech(self, text: str):
        """Convert text to speech"""
        if not self.tts_enabled or not text:
            return

        logging.info(f"Speaking: {text}")
        
        # Notify system we are speaking (for face animation)
        event_bus.publish(EventType.VOICE_OUTPUT, {'text': text, 'status': 'start'}, "voice_module")
        
        try:
            # We run the runAndWait in a loop or thread carefully, 
            # but pyttsx3 main loop can block.
            # For this simple implementation, we block briefly.
            if self.tts_engine:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
        except RuntimeError:
            # Engine loop already running
            pass
        except Exception as e:
            logging.error(f"TTS Error: {e}")
        
        event_bus.publish(EventType.VOICE_OUTPUT, {'text': text, 'status': 'end'}, "voice_module")
    
    def listen_loop(self):
        """Continuous listening loop"""
        if not self.stt_enabled:
            return
            
        logging.info("Microphone listening...")
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen with a timeout so we can check is_listening flag
                    try:
                        audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=5.0)
                    except sr.WaitTimeoutError:
                        continue
                
                # Recognize
                try:
                    text = self.recognizer.recognize_google(audio)
                    logging.info(f"Heard: {text}")
                    
                    # Publish heard text to LLM or Command system
                    event_bus.publish(
                        EventType.VOICE_INPUT,
                        {'text': text},
                        source="voice_module"
                    )
                    
                    # Also trigger LLM directly for conversation
                    event_bus.publish(
                        EventType.LLM_REQUEST,
                        {'text': text},
                        source="voice_module"
                    )

                except sr.UnknownValueError:
                    pass # unintelligible
                except sr.RequestError as e:
                    logging.error(f"STT Service Error: {e}")

            except Exception as e:
                logging.error(f"Listening Error: {e}")
                time.sleep(1)

    def handle_llm_response(self, event):
        """Handle LLM responses and speak them"""
        text = event.data.get('text', '')
        if text:
            # Run TTS in a separate thread so we don't block the event listener
            threading.Thread(target=self.text_to_speech, args=(text,)).start()
    
    def run(self):
        """Main run loop"""
        # Subscribe to LLM responses to speak them
        event_bus.subscribe(EventType.LLM_RESPONSE, self.handle_llm_response)
        
        logging.info("Voice Module running")
        self.is_listening = True
        
        # Start listening thread
        listen_thread = threading.Thread(target=self.listen_loop, daemon=True)
        listen_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Voice Module shutting down")
            self.is_listening = False

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | VOICE | %(levelname)s | %(message)s'
    )
    
    module = VoiceModule()
    module.run()

if __name__ == "__main__":
    main()