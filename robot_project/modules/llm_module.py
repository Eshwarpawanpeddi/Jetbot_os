#!/usr/bin/env python3
"""
LLM Module - Handles conversational AI and multi-intent detection
"""
import os
import sys
import time
import logging
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.event_bus import event_bus, EventType


# LLM Configuration
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

class IntentClassifier:
    """Classify user intent from text"""
    
    INTENTS = {
        'command': ['move', 'go', 'turn', 'stop', 'follow', 'come', 'navigate'],
        'question': ['what', 'why', 'how', 'when', 'where', 'who', 'is', 'are', 'can', 'will'],
        'emotional': ['feel', 'sad', 'happy', 'angry', 'love', 'hate', 'like', 'dislike']
    }
    
    @staticmethod
    def classify(text: str) -> str:
        """Classify intent of user input"""
        text_lower = text.lower()
        
        # Check for commands
        if any(word in text_lower for word in IntentClassifier.INTENTS['command']):
            return 'command'
        
        # Check for questions
        if any(text_lower.startswith(word) for word in IntentClassifier.INTENTS['question']):
            return 'question'
        
        # Check for emotional statements
        if any(word in text_lower for word in IntentClassifier.INTENTS['emotional']):
            return 'emotional'
        
        return 'general'

class LLMModule:
    """LLM integration for conversational AI"""
    
    def __init__(self):
        self.api_key = LLM_API_KEY
        self.api_url = LLM_API_URL
        self.model = LLM_MODEL
        self.conversation_history = []
        self.max_history = 10
        
        # System prompt
        self.system_prompt = """You are a friendly pet robot assistant. You can:
- Answer questions conversationally
- Execute movement commands (respond with acknowledgment)
- Respond empathetically to emotional statements
- Remember context from previous messages

Keep responses concise (1-3 sentences). Be warm and friendly."""
        
        if not self.api_key:
            logging.warning("LLM_API_KEY not set. Using fallback responses.")
        
        logging.info(f"LLM Module initialized (Model: {self.model})")
    
    def process_input(self, user_input: str, emotion: str = "neutral") -> dict:
        """Process user input and generate response"""
        
        # Classify intent
        intent = IntentClassifier.classify(user_input)
        
        logging.info(f"User input: '{user_input}' | Intent: {intent} | Emotion: {emotion}")
        
        # Get LLM response
        response_text = self._get_llm_response(user_input, emotion, intent)
        
        return {
            'text': response_text,
            'intent': intent,
            'emotion': emotion
        }
    
    def _get_llm_response(self, user_input: str, emotion: str, intent: str) -> str:
        """Get response from LLM API"""
        
        # Fallback if no API key
        if not self.api_key:
            return self._get_fallback_response(intent)
        
        try:
            # Add emotion context to input
            enhanced_input = user_input
            if emotion != "neutral":
                enhanced_input = f"[User sounds {emotion}] {user_input}"
            
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            for msg in self.conversation_history[-self.max_history:]:
                messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": enhanced_input})
            
            # Call API
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 150
                },
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            assistant_message = result['choices'][0]['message']['content']
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Trim history
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            return assistant_message
        
        except Exception as e:
            logging.error(f"LLM API error: {e}")
            return self._get_fallback_response(intent)
    
    def _get_fallback_response(self, intent: str) -> str:
        """Fallback responses when API unavailable"""
        responses = {
            'command': "Okay, I'll do that!",
            'question': "That's an interesting question! I'm not sure right now.",
            'emotional': "I understand how you feel. I'm here for you!",
            'general': "I hear you! Tell me more."
        }
        return responses.get(intent, "I'm listening!")
    
    def handle_llm_request(self, event):
        """Handle LLM request events"""
        user_input = event.data.get('text', '')
        emotion = event.data.get('emotion', 'neutral')
        
        if user_input:
            response = self.process_input(user_input, emotion)
            
            # Publish response
            event_bus.publish(
                EventType.LLM_RESPONSE,
                response,
                source="llm_module"
            )
    
    def run(self):
        """Main run loop"""
        # Subscribe to events
        event_bus.subscribe(EventType.LLM_REQUEST, self.handle_llm_request)
        event_bus.subscribe(EventType.VOICE_INPUT, self.handle_llm_request)
        
        logging.info("LLM Module running")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("LLM Module shutting down")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | LLM | %(levelname)s | %(message)s'
    )
    
    module = LLMModule()
    module.run()

if __name__ == "__main__":
    main()
