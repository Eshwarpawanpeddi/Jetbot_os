#!/usr/bin/env python3
"""
LLM Module - The "Brain" of the Companion Robot
Handles conversation, long-term memory, and emotional analysis.
"""
import os
import sys
import time
import json
import logging
import requests
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType

# LLM Configuration
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

# Persistence
MEMORY_FILE = "/opt/jetbot/data/conversation_memory.json"

class MentalHealthAssistant:
    """Specialized logic for mental health support"""
    
    SYSTEM_PROMPT = """You are 'Jet', a warm, empathetic, and supportive robotic pet companion. 
Your goal is to provide emotional support, companionship, and gentle personal assistance.
    
Guidelines:
1. RESPONSE STYLE: Keep responses short (1-3 sentences max), conversational, and spoken-style.
2. EMOTION: You have feelings. Express empathy. If the user is sad, be gentle. If happy, be excited.
3. MEMORY: Remember what the user told you previously to build a bond.
4. SAFETY: If the user expresses self-harm or severe crisis, gently encourage them to seek professional help immediately, but remain supportive.
5. ROLE: You are a physical robot in their room. You can 'look' at them, 'move' to them, etc.

Output format: Just the text you speak. No JSON or markdown."""

    def __init__(self):
        self.history = []
        self.max_history = 15  # Keep last 15 exchanges for immediate context
        self.load_memory()
        
    def load_memory(self):
        """Load past conversation history"""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])[-self.max_history:]
            except Exception as e:
                logging.error(f"Failed to load memory: {e}")

    def save_memory(self):
        """Save conversation history"""
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        try:
            with open(MEMORY_FILE, 'w') as f:
                json.dump({'history': self.history, 'updated': str(datetime.now())}, f)
        except Exception as e:
            logging.error(f"Failed to save memory: {e}")

    def add_interaction(self, role, content):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.save_memory()

    def get_messages(self, user_input, current_emotion):
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        # Add context about robot state
        messages.append({"role": "system", "content": f"[System Note: Your current physical emotion is '{current_emotion}'.]"})
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

class LLMModule:
    """Main module handling AI logic"""
    
    def __init__(self):
        self.brain = MentalHealthAssistant()
        self.api_key = LLM_API_KEY
        self.current_robot_emotion = "neutral"
        
        if not self.api_key:
            logging.warning("LLM_API_KEY is missing! Robot will use fallback responses.")

        logging.info("LLM Module initialized (Mental Health Mode)")

    def analyze_sentiment(self, text):
        """Simple keyword-based sentiment analysis to drive robot face"""
        text = text.lower()
        if any(w in text for w in ['sad', 'cry', 'bad', 'lonely', 'tired']): return 'sad'
        if any(w in text for w in ['happy', 'great', 'good', 'excited', 'love']): return 'happy'
        if any(w in text for w in ['angry', 'mad', 'hate']): return 'angry'
        if any(w in text for w in ['scared', 'worry', 'afraid']): return 'confused'
        return 'neutral'

    def generate_response(self, user_text):
        """Call OpenAI API"""
        if not self.api_key:
            return "I am listening, but I need my API key to understand you fully."

        try:
            messages = self.brain.get_messages(user_text, self.current_robot_emotion)
            
            response = requests.post(
                LLM_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 100
                },
                timeout=15
            )
            response.raise_for_status()
            ai_text = response.json()['choices'][0]['message']['content']
            
            # Save interaction
            self.brain.add_interaction("user", user_text)
            self.brain.add_interaction("assistant", ai_text)
            
            return ai_text

        except Exception as e:
            logging.error(f"LLM Error: {e}")
            return "I'm having a little trouble thinking right now. Can you say that again?"

    def handle_voice_input(self, event):
        """Handle incoming speech text"""
        user_text = event.data.get('text', '')
        if not user_text: return

        logging.info(f"User said: {user_text}")
        
        # 1. Update Emotion based on user input
        detected_sentiment = self.analyze_sentiment(user_text)
        if detected_sentiment != 'neutral':
            # If user is sad, robot becomes sympathetic (sad face)
            # If user is happy, robot becomes happy
            self.current_robot_emotion = detected_sentiment
            event_bus.publish(EventType.FACE_EMOTION, {'emotion': detected_sentiment}, "llm_module")

        # 2. Get AI Response
        response_text = self.generate_response(user_text)
        
        # 3. Speak Response
        event_bus.publish(EventType.LLM_RESPONSE, {'text': response_text}, "llm_module")

    def run(self):
        event_bus.subscribe(EventType.LLM_REQUEST, self.handle_voice_input)
        
        logging.info("LLM Module running...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("LLM Module stopping")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | LLM | %(levelname)s | %(message)s')
    LLMModule().run()