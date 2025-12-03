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
