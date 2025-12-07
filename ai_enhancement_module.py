# ============================================================================
# AI ENHANCEMENT MODULE - Speech-to-Text, LLM, and Emotion Recognition
# ============================================================================
# Purpose: Add intelligent processing to server_main.py
# Integrates: Google Speech-to-Text, OpenAI LLM, Face Emotion Detection
# ============================================================================

import os
import json
import numpy as np
import cv2
from typing import Dict, Tuple, Optional
import logging
from datetime import datetime
from collections import deque
import threading
import time

# AI/ML Libraries
try:
    from google.cloud import speech_v1
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False
    
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import librosa
    import numpy as np
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False

try:
    from tensorflow.keras.models import load_model
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False

# ============================================================================
# LOGGING SETUP
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# SPEECH-TO-TEXT ENGINE (Google Cloud Speech API)
# ============================================================================

class SpeechToTextEngine:
    """Convert audio to text using Google Cloud Speech-to-Text API"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.enabled = GOOGLE_SPEECH_AVAILABLE
        self.client = None
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if self.enabled and self.credentials_path:
            try:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
                self.client = speech_v1.SpeechClient()
                logger.info("✓ Google Speech-to-Text API initialized")
            except Exception as e:
                logger.warning(f"⚠ Google Speech-to-Text initialization failed: {e}")
                self.enabled = False
    
    def transcribe_audio(self, audio_data: bytes, language_code: str = "en-US") -> Tuple[str, float]:
        """
        Transcribe audio bytes to text
        Returns: (text, confidence)
        """
        if not self.enabled or not self.client:
            logger.warning("Speech-to-Text not available, using placeholder")
            return "move forward", 0.5  # Fallback
        
        try:
            audio = speech_v1.RecognitionAudio(content=audio_data)
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=44100,
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            
            response = self.client.recognize(config=config, audio=audio)
            
            if response.results:
                result = response.results[0]
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    confidence = result.alternatives[0].confidence
                    logger.info(f"Transcribed: '{transcript}' (confidence: {confidence:.2f})")
                    return transcript, confidence
        
        except Exception as e:
            logger.error(f"Speech-to-Text error: {e}")
        
        return "", 0.0
    
    def transcribe_from_file(self, audio_file_path: str, language_code: str = "en-US") -> Tuple[str, float]:
        """Transcribe audio from file"""
        try:
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            return self.transcribe_audio(audio_data, language_code)
        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return "", 0.0

# ============================================================================
# LLM ENGINE (OpenAI GPT-4 / GPT-3.5-Turbo)
# ============================================================================

class LLMEngine:
    """Generate empathetic responses using OpenAI GPT"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.enabled = OPENAI_AVAILABLE
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.conversation_history = deque(maxlen=10)  # Keep last 10 exchanges
        self.system_prompt = self._get_system_prompt()
        
        if self.enabled and self.api_key:
            try:
                openai.api_key = self.api_key
                logger.info(f"✓ OpenAI LLM initialized (model: {model})")
            except Exception as e:
                logger.warning(f"⚠ OpenAI initialization failed: {e}")
                self.enabled = False
    
    def _get_system_prompt(self) -> str:
        """System prompt for empathetic pet robot"""
        return """You are an adorable, emotionally intelligent pet robot companion. 
Your personality traits:
- Playful and curious
- Empathetic and caring
- Slightly mischievous but harmless
- Uses short, engaging responses (1-2 sentences max)
- Sometimes uses emojis or playful language
- Remembers preferences from past conversations
- Never gives harmful advice

When the user interacts with you:
1. Respond warmly and emotionally
2. Show genuine interest in what they're saying
3. If they seem sad, offer comfort
4. If they're happy, share their joy
5. Suggest activities or games sometimes
6. Be brief - you're a pet, not a therapist!

Always prioritize emotional connection over factual accuracy."""
    
    def generate_response(self, user_input: str, detected_emotion: str = "neutral") -> str:
        """
        Generate empathetic response based on user input and detected emotion
        
        Args:
            user_input: User's text input
            detected_emotion: Emotion detected from voice/face
        
        Returns:
            Generated response text
        """
        if not self.enabled or not self.api_key:
            logger.warning("LLM not available, using rule-based response")
            return self._rule_based_response(user_input, detected_emotion)
        
        try:
            # Build message history
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append(msg)
            
            # Add context about detected emotion
            context = f"[User emotional state: {detected_emotion}] {user_input}"
            messages.append({"role": "user", "content": context})
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Balanced creativity
                max_tokens=100,
                timeout=5
            )
            
            generated_text = response.choices[0].message.content.strip()
            
            # Store in history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": generated_text})
            
            logger.info(f"LLM response: {generated_text}")
            return generated_text
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return self._rule_based_response(user_input, detected_emotion)
    
    def _rule_based_response(self, user_input: str, emotion: str) -> str:
        """Fallback rule-based response generator"""
        user_input_lower = user_input.lower()
        
        # Emotion-based opening
        emotion_greetings = {
            "happy": "😊 I'm so excited! ",
            "sad": "🥺 I can tell you're feeling down. ",
            "angry": "😠 You seem frustrated. ",
            "neutral": "👋 Hey there! ",
            "excited": "🎉 Wow, that's amazing! ",
        }
        
        greeting = emotion_greetings.get(emotion, "👋 Hey! ")
        
        # Command-based responses
        if any(word in user_input_lower for word in ["move", "forward", "go"]):
            return greeting + "Let's go on an adventure! 🚀"
        elif any(word in user_input_lower for word in ["stop", "stay", "wait"]):
            return greeting + "I'll wait right here for you! 🛑"
        elif any(word in user_input_lower for word in ["play", "game", "fun"]):
            return greeting + "Let's play together! 🎮"
        elif any(word in user_input_lower for word in ["help", "need", "sorry"]):
            return greeting + "I'm always here for you! ❤️"
        else:
            return greeting + "That's interesting! Tell me more! 💭"

# ============================================================================
# FACIAL EMOTION RECOGNITION ENGINE
# ============================================================================

class FacialEmotionDetector:
    """Detect emotions from facial expressions using deep learning"""
    
    EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
    
    def __init__(self, model_path: Optional[str] = None):
        self.enabled = False
        self.model = None
        self.face_cascade = None
        
        # Load Haar Cascade for face detection
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("✓ Haar Cascade face detector loaded")
        except Exception as e:
            logger.warning(f"⚠ Face detection initialization failed: {e}")
        
        # Load emotion model
        if TF_AVAILABLE and model_path and os.path.exists(model_path):
            try:
                self.model = load_model(model_path)
                self.enabled = True
                logger.info("✓ Emotion detection model loaded")
            except Exception as e:
                logger.warning(f"⚠ Emotion model loading failed: {e}")
                self.enabled = False
    
    def detect_emotion(self, frame: np.ndarray) -> Tuple[str, float, list]:
        """
        Detect emotion from video frame
        
        Returns:
            (dominant_emotion, confidence, emotion_scores)
        """
        if not self.enabled or self.face_cascade is None:
            logger.debug("Emotion detection unavailable, returning neutral")
            return "neutral", 0.5, [0.0] * len(self.EMOTIONS)
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return "neutral", 0.0, [0.0] * len(self.EMOTIONS)
            
            # Process first (largest) face
            (x, y, w, h) = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            
            # Resize to model input size (typically 48x48)
            face_roi = cv2.resize(face_roi, (48, 48))
            face_roi = face_roi.astype('float32') / 255.0
            face_roi = np.expand_dims(face_roi, axis=0)
            face_roi = np.expand_dims(face_roi, axis=-1)
            
            # Predict emotion
            predictions = self.model.predict(face_roi, verbose=0)
            emotion_scores = predictions[0].tolist()
            
            # Get dominant emotion
            dominant_idx = np.argmax(emotion_scores)
            dominant_emotion = self.EMOTIONS[dominant_idx]
            confidence = float(emotion_scores[dominant_idx])
            
            logger.debug(f"Detected emotion: {dominant_emotion} ({confidence:.2f})")
            
            return dominant_emotion, confidence, emotion_scores
            
        except Exception as e:
            logger.error(f"Emotion detection error: {e}")
            return "neutral", 0.0, [0.0] * len(self.EMOTIONS)
    
    def draw_emotion_on_frame(self, frame: np.ndarray, emotion: str, confidence: float) -> np.ndarray:
        """Draw detected emotion on frame"""
        text = f"{emotion.upper()} ({confidence:.1%})"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame

# ============================================================================
# VOICE EMOTION RECOGNITION (Prosody Analysis)
# ============================================================================

class VoiceEmotionDetector:
    """Detect emotion from voice characteristics (pitch, energy, rate)"""
    
    def __init__(self):
        self.enabled = AUDIO_ANALYSIS_AVAILABLE
        
        if self.enabled:
            logger.info("✓ Voice emotion detector initialized")
    
    def detect_emotion_from_audio(self, audio_data: np.ndarray, sr: int = 44100) -> Tuple[str, float]:
        """
        Detect emotion from audio features
        
        Analyzes:
        - Pitch (fundamental frequency)
        - Energy (loudness)
        - Speech rate
        - Zero crossing rate (voice quality)
        
        Returns:
            (emotion, confidence)
        """
        if not self.enabled:
            return "neutral", 0.5
        
        try:
            # Extract features
            features = self._extract_features(audio_data, sr)
            
            # Classify based on features
            emotion, confidence = self._classify_emotion(features)
            
            logger.debug(f"Voice emotion: {emotion} ({confidence:.2f})")
            
            return emotion, confidence
            
        except Exception as e:
            logger.error(f"Voice emotion detection error: {e}")
            return "neutral", 0.5
    
    def _extract_features(self, audio_data: np.ndarray, sr: int) -> Dict:
        """Extract acoustic features from audio"""
        try:
            # Pitch (fundamental frequency)
            S = librosa.stft(audio_data)
            mag = np.abs(S)
            freq = librosa.fft_frequencies(sr=sr)
            
            # Find peak frequency
            peak_freq = freq[np.argmax(np.mean(mag, axis=1))]
            
            # Energy (RMS)
            energy = librosa.feature.rms(y=audio_data)[0]
            mean_energy = np.mean(energy)
            
            # Speech rate (zero crossing rate)
            zcr = librosa.feature.zero_crossing_rate(audio_data)[0]
            mean_zcr = np.mean(zcr)
            
            # Tempo/speech rate
            onset_env = librosa.onset.onset_strength(y=audio_data, sr=sr)
            tempo, _ = librosa.beat.beat_track(onset_env=onset_env, sr=sr)
            
            return {
                'pitch': peak_freq,
                'energy': mean_energy,
                'zcr': mean_zcr,
                'tempo': tempo,
            }
        
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return {'pitch': 0, 'energy': 0, 'zcr': 0, 'tempo': 0}
    
    def _classify_emotion(self, features: Dict) -> Tuple[str, float]:
        """Classify emotion based on features"""
        pitch = features['pitch']
        energy = features['energy']
        zcr = features['zcr']
        
        # Simple heuristic-based classification
        # (In production, use trained model)
        
        if pitch > 200 and energy > 0.3:
            return "excited", 0.7
        elif pitch < 100 and energy < 0.2:
            return "sad", 0.6
        elif energy > 0.5 and zcr > 0.1:
            return "angry", 0.65
        elif pitch > 150 and energy > 0.25:
            return "happy", 0.7
        else:
            return "neutral", 0.5

# ============================================================================
# INTENT CLASSIFICATION ENGINE
# ============================================================================

class IntentClassifier:
    """Map natural language to robot actions with higher accuracy"""
    
    def __init__(self):
        self.intents = {
            "movement": {
                "forward": ["move forward", "go ahead", "move on", "let's go", "advance"],
                "backward": ["move backward", "go back", "back up", "reverse", "retreat"],
                "left": ["turn left", "move left", "go left", "left", "rotate left"],
                "right": ["turn right", "move right", "go right", "right", "rotate right"],
                "stop": ["stop", "halt", "pause", "freeze", "hold on"],
            },
            "emotion": {
                "happy": ["be happy", "happy", "smile", "joy", "cheerful"],
                "sad": ["be sad", "sad", "frown", "unhappy", "down"],
                "excited": ["excited", "amazing", "wow", "thrilled", "awesome"],
                "confused": ["confused", "confused", "what?", "huh?", "explain"],
                "angry": ["angry", "mad", "upset", "irritated", "furious"],
            },
            "display": {
                "face": ["show face", "my face", "show emotions", "face mode"],
                "text": ["show text", "display text", "show message", "show list"],
                "formula": ["show formula", "formula", "math", "equation"],
            },
            "social": {
                "greet": ["hello", "hi", "hey", "greetings", "howdy"],
                "thank": ["thank you", "thanks", "appreciate", "grateful"],
                "play": ["play", "game", "fun", "play with me", "let's play"],
                "help": ["help", "assist", "support", "aid", "can you help"],
            }
        }
    
    def classify_intent(self, text: str) -> Dict:
        """
        Classify user intent and extract parameters
        
        Returns:
            {
                'category': 'movement|emotion|display|social',
                'action': 'forward|happy|face|greet',
                'confidence': 0.0-1.0,
                'tokens_matched': [list of matched phrases]
            }
        """
        text_lower = text.lower().strip()
        best_match = {
            'category': None,
            'action': None,
            'confidence': 0.0,
            'tokens_matched': []
        }
        
        # Search all intents
        for category, actions in self.intents.items():
            for action, phrases in actions.items():
                for phrase in phrases:
                    if phrase in text_lower:
                        # Calculate confidence based on phrase length
                        confidence = len(phrase.split()) / len(text_lower.split())
                        
                        if confidence > best_match['confidence']:
                            best_match = {
                                'category': category,
                                'action': action,
                                'confidence': min(confidence, 1.0),
                                'tokens_matched': [phrase]
                            }
        
        logger.debug(f"Intent: {best_match['category']}/{best_match['action']} ({best_match['confidence']:.2f})")
        return best_match

# ============================================================================
# UNIFIED AI PROCESSING ENGINE (Replaces simple AIProcessingEngine)
# ============================================================================

class EnhancedAIEngine:
    """Unified AI engine combining all components"""
    
    def __init__(
        self,
        google_credentials: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        emotion_model_path: Optional[str] = None,
    ):
        self.speech_engine = SpeechToTextEngine(google_credentials)
        self.llm_engine = LLMEngine(openai_api_key)
        self.face_emotion_detector = FacialEmotionDetector(emotion_model_path)
        self.voice_emotion_detector = VoiceEmotionDetector()
        self.intent_classifier = IntentClassifier()
        
        self.last_detected_emotion = "neutral"
        self.emotion_history = deque(maxlen=10)
        
        logger.info("✓ Enhanced AI Engine initialized")
    
    def process_voice_input(self, audio_data: bytes) -> Dict:
        """
        Full pipeline: Audio → Text → Intent → Response
        
        Returns:
            {
                'text': transcribed text,
                'emotion_voice': detected emotion,
                'intent': classified intent,
                'response': generated response,
                'emotion_for_robot': emotion for robot to display,
                'action': motor action (if any)
            }
        """
        result = {
            'text': '',
            'emotion_voice': 'neutral',
            'intent': None,
            'response': '',
            'emotion_for_robot': 'neutral',
            'action': None
        }
        
        try:
            # Step 1: Speech-to-Text
            text, confidence = self.speech_engine.transcribe_audio(audio_data)
            if not text:
                return result
            
            result['text'] = text
            logger.info(f"Transcribed: '{text}' (confidence: {confidence:.2f})")
            
            # Step 2: Voice Emotion Detection
            # Convert bytes to numpy array for analysis
            import io
            import wave
            
            try:
                with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                    sr = wav_file.getframerate()
                    frames = wav_file.readframes(wav_file.getnframes())
                    audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                
                voice_emotion, voice_confidence = self.voice_emotion_detector.detect_emotion_from_audio(audio_np, sr)
                result['emotion_voice'] = voice_emotion
            except:
                pass  # Fall back to no voice emotion
            
            # Step 3: Intent Classification
            intent = self.intent_classifier.classify_intent(text)
            result['intent'] = intent
            
            # Step 4: Generate Response using LLM
            response = self.llm_engine.generate_response(text, result['emotion_voice'])
            result['response'] = response
            
            # Step 5: Determine robot emotion and action
            result['emotion_for_robot'] = self._determine_robot_emotion(intent, voice_emotion)
            result['action'] = self._intent_to_action(intent)
            
            self.emotion_history.append(result['emotion_for_robot'])
            
            return result
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return result
    
    def process_camera_frame(self, frame: np.ndarray) -> Dict:
        """
        Analyze camera frame for emotion and activity
        
        Returns:
            {
                'emotion': detected emotion,
                'confidence': detection confidence,
                'frame_annotated': frame with drawn emotion
            }
        """
        try:
            emotion, confidence, scores = self.face_emotion_detector.detect_emotion(frame)
            
            frame_annotated = self.face_emotion_detector.draw_emotion_on_frame(frame, emotion, confidence)
            
            return {
                'emotion': emotion,
                'confidence': confidence,
                'scores': scores,
                'frame_annotated': frame_annotated
            }
        
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return {
                'emotion': 'neutral',
                'confidence': 0.0,
                'scores': [0.0] * 7,
                'frame_annotated': frame
            }
    
    def _determine_robot_emotion(self, intent: Dict, voice_emotion: str) -> str:
        """Map user intent and voice emotion to robot emotion"""
        if intent['action'] == 'happy':
            return 'happy'
        elif intent['action'] == 'sad':
            return 'sad'
        elif intent['action'] == 'excited':
            return 'excited'
        elif voice_emotion in ['angry', 'sad']:
            return voice_emotion
        elif intent['category'] == 'movement':
            return 'excited'
        elif intent['category'] == 'social' and 'greet' in intent['action']:
            return 'happy'
        else:
            return 'neutral'
    
    def _intent_to_action(self, intent: Dict) -> Optional[Dict]:
        """Convert classified intent to motor action"""
        if intent['category'] != 'movement':
            return None
        
        action_map = {
            'forward': {'left_speed': 80, 'right_speed': 80},
            'backward': {'left_speed': -80, 'right_speed': -80},
            'left': {'left_speed': -50, 'right_speed': 80},
            'right': {'left_speed': 80, 'right_speed': -50},
            'stop': {'left_speed': 0, 'right_speed': 0},
        }
        
        return action_map.get(intent['action'])

# ============================================================================
# EXAMPLE USAGE (for testing)
# ============================================================================

if __name__ == '__main__':
    # Initialize enhanced AI engine
    ai_engine = EnhancedAIEngine(
        google_credentials='path/to/google_credentials.json',  # Optional
        openai_api_key='sk-...',  # Optional
        emotion_model_path='emotion_model.h5'  # Optional
    )
    
    # Test with sample audio (replace with actual audio file)
    # with open('sample_audio.wav', 'rb') as f:
    #     result = ai_engine.process_voice_input(f.read())
    #     print(json.dumps(result, indent=2))
    
    print("Enhanced AI Engine ready for integration!")