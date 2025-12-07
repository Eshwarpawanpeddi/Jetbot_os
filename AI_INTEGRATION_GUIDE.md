# 🚀 AI ENHANCEMENT INTEGRATION GUIDE

## Overview

This guide shows how to integrate the **AI Enhancement Module** (`ai_enhancement_module.py`) into your existing `server_main.py` to add:

- ✅ **Speech-to-Text** (Google Cloud Speech API)
- ✅ **LLM Integration** (OpenAI GPT-3.5/GPT-4)
- ✅ **Facial Emotion Detection** (TensorFlow/OpenCV)
- ✅ **Voice Emotion Recognition** (Librosa prosody analysis)
- ✅ **Intent Classification** (Natural language understanding)

---

## 📦 Installation

### Step 1: Install AI/ML Dependencies

```bash
# Core AI libraries
pip install google-cloud-speech openai librosa tensorflow numpy opencv-python

# Optional (for advanced features)
pip install dlib scikit-learn scipy

# All dependencies
pip install -r requirements_ai.txt
```

### Step 2: Setup API Credentials

#### Google Cloud Speech-to-Text
```bash
# 1. Create Google Cloud project
#    https://console.cloud.google.com/

# 2. Enable Speech-to-Text API
# 3. Create service account and download JSON key
# 4. Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/google-credentials.json"
```

#### OpenAI API Key
```bash
# 1. Get API key from https://platform.openai.com/
# 2. Set environment variable
export OPENAI_API_KEY="sk-..."
```

### Step 3: Download Emotion Recognition Model

```bash
# Option A: Use pre-trained model (FER2013)
wget https://github.com/fer2013/facial-expression/releases/download/v1.0/emotion_model.h5

# Option B: Train your own (advanced)
# See training script: train_emotion_model.py
```

---

## 🔌 Integration into server_main.py

### Step 1: Import Enhancement Module

Add to top of `server_main.py`:

```python
# Add these imports
from ai_enhancement_module import (
    EnhancedAIEngine,
    SpeechToTextEngine,
    LLMEngine,
    FacialEmotionDetector,
    VoiceEmotionDetector,
    IntentClassifier
)
```

### Step 2: Initialize in Config

In the `Config` class, add:

```python
class Config:
    # ... existing config ...
    
    # AI/ML Configuration
    GOOGLE_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    EMOTION_MODEL_PATH = './models/emotion_model.h5'
    
    # Feature toggles
    ENABLE_SPEECH_TO_TEXT = True
    ENABLE_LLM = True
    ENABLE_FACIAL_EMOTION = True
    ENABLE_VOICE_EMOTION = True
```

### Step 3: Initialize AI Engine

Replace the simple `AIProcessingEngine` initialization:

```python
# OLD (remove this):
# ai_engine = AIProcessingEngine()

# NEW (replace with):
ai_engine = EnhancedAIEngine(
    google_credentials=Config.GOOGLE_CREDENTIALS,
    openai_api_key=Config.OPENAI_API_KEY,
    emotion_model_path=Config.EMOTION_MODEL_PATH
)
```

### Step 4: Update Voice Command Handler

Replace the `handle_voice_command` function:

```python
@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle voice commands with full AI pipeline"""
    
    # Get audio data (if provided)
    audio_data = data.get('audio_bytes')  # Binary audio data
    voice_text = data.get('text')  # Or pre-transcribed text
    
    try:
        # Process through enhanced AI engine
        if audio_data:
            # Full pipeline: audio → text → intent → response
            result = ai_engine.process_voice_input(audio_data)
        else:
            # Text-only pipeline
            result = {
                'text': voice_text,
                'emotion_voice': 'neutral',
                'intent': ai_engine.intent_classifier.classify_intent(voice_text),
                'response': ai_engine.llm_engine.generate_response(
                    voice_text, 
                    'neutral'
                ),
                'emotion_for_robot': 'neutral',
                'action': None
            }
        
        # Update robot state
        if result['emotion_for_robot']:
            robot_state.emotion = result['emotion_for_robot']
        
        # Execute motor action if needed
        if result['action']:
            bluetooth_manager.send_motor_command(
                result['action']['left_speed'],
                result['action']['right_speed']
            )
        
        # Send response back to mobile app
        socketio.emit('voice_response', {
            'text': result['text'],
            'response': result['response'],
            'emotion': result['emotion_for_robot'],
            'confidence': result['intent']['confidence'] if result['intent'] else 0.0
        }, broadcast=True)
        
        logger.info(f"Voice command processed: {result['text']}")
        
    except Exception as e:
        logger.error(f"Voice command error: {e}")
        socketio.emit('error', {'message': 'Failed to process voice command'})
```

### Step 5: Add Camera Emotion Analysis

Add to the display generation loop:

```python
def display_generation_loop():
    """Enhanced display loop with camera emotion analysis"""
    
    while True:
        try:
            # Get latest camera frame from Jetson
            camera_frame = jetson_receiver.get_latest_frame()
            
            # Analyze frame for emotions (optional)
            if camera_frame is not None and Config.ENABLE_FACIAL_EMOTION:
                emotion_result = ai_engine.process_camera_frame(camera_frame)
                
                # Could use detected emotion to influence robot emotion
                # (e.g., mirror user's emotion)
                detected_user_emotion = emotion_result['emotion']
                logger.debug(f"User emotion detected: {detected_user_emotion}")
            
            # Generate display frame (existing code)
            if robot_state.current_display_mode == "face":
                blink = face_engine.update_animation()
                display_frame = face_engine.generate_face(robot_state.emotion, blink)
            # ... rest of existing code ...
            
        except Exception as e:
            logger.error(f"Error in display loop: {e}")
            time.sleep(0.5)
```

---

## 📱 Update Mobile App

Update `mobile_app.jsx` to send audio data:

```javascript
const startListening = async () => {
    try {
        setIsListening(true);
        setLoading(true);

        const recording = recordingRef.current;
        
        await recording.startAsync();
        await new Promise(resolve => setTimeout(resolve, 5000));
        await recording.stopAndUnloadAsync();

        const uri = recording.getURI();
        
        // Convert audio file to bytes
        const fileInfo = await FileSystem.getInfoAsync(uri);
        const audioBytes = await FileSystem.readAsStringAsync(uri, {
            encoding: FileSystem.EncodingType.Base64
        });

        // Send to server with audio data (not just text)
        if (socketRef.current) {
            socketRef.current.emit('voice_command', {
                audio_bytes: audioBytes,
                timestamp: Date.now()
            });
        }

        setIsListening(false);
        setLoading(false);
        Vibration.vibrate(100);
        
    } catch (err) {
        console.error('Error during voice recording:', err);
        setIsListening(false);
        setLoading(false);
        Alert.alert('Error', 'Failed to record voice command');
    }
};
```

---

## 🧪 Testing the Integration

### Test 1: Speech-to-Text Only

```python
from ai_enhancement_module import SpeechToTextEngine

stt = SpeechToTextEngine('path/to/google-credentials.json')

# Test with audio file
with open('test_audio.wav', 'rb') as f:
    text, confidence = stt.transcribe_audio(f.read())
    print(f"Transcribed: {text} (confidence: {confidence})")
```

### Test 2: LLM Response

```python
from ai_enhancement_module import LLMEngine

llm = LLMEngine(api_key='sk-...')

response = llm.generate_response(
    "Can you move forward?",
    detected_emotion="happy"
)
print(f"Response: {response}")
```

### Test 3: Intent Classification

```python
from ai_enhancement_module import IntentClassifier

classifier = IntentClassifier()

intent = classifier.classify_intent("move forward and be happy")
print(f"Intent: {intent['category']}/{intent['action']} ({intent['confidence']})")
```

### Test 4: Facial Emotion

```python
from ai_enhancement_module import FacialEmotionDetector
import cv2

detector = FacialEmotionDetector('path/to/emotion_model.h5')

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    emotion, confidence, scores = detector.detect_emotion(frame)
    
    frame = detector.draw_emotion_on_frame(frame, emotion, confidence)
    cv2.imshow('Emotion Detection', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### Test 5: Full Pipeline

```python
from ai_enhancement_module import EnhancedAIEngine

ai_engine = EnhancedAIEngine(
    google_credentials='path/to/google-credentials.json',
    openai_api_key='sk-...',
    emotion_model_path='emotion_model.h5'
)

# Test with audio file
with open('test_audio.wav', 'rb') as f:
    result = ai_engine.process_voice_input(f.read())
    
    print(f"Text: {result['text']}")
    print(f"Voice Emotion: {result['emotion_voice']}")
    print(f"Intent: {result['intent']['action']}")
    print(f"Response: {result['response']}")
    print(f"Robot Emotion: {result['emotion_for_robot']}")
    print(f"Action: {result['action']}")
```

---

## ⚙️ Performance Tuning

### Latency Optimization

```python
# In ai_enhancement_module.py, use threading for long operations:

class EnhancedAIEngine:
    def __init__(self, ...):
        # ... existing init ...
        self.llm_queue = Queue()
        self.llm_thread = threading.Thread(
            target=self._llm_worker,
            daemon=True
        )
        self.llm_thread.start()
    
    def _llm_worker(self):
        """Background thread for LLM processing"""
        while True:
            task = self.llm_queue.get()
            if task is None:
                break
            
            text, emotion, callback = task
            response = self.llm_engine.generate_response(text, emotion)
            callback(response)
    
    def generate_response_async(self, text, emotion, callback):
        """Non-blocking LLM call"""
        self.llm_queue.put((text, emotion, callback))
```

### Batch Processing

```python
# Process multiple voice commands together (if buffering)
def batch_process_voice_commands(audio_list):
    """Process multiple voice inputs efficiently"""
    results = []
    
    for audio_data in audio_list:
        result = ai_engine.process_voice_input(audio_data)
        results.append(result)
    
    return results
```

### Memory Management

```python
# Limit conversation history to prevent memory bloat
self.conversation_history = deque(maxlen=10)  # Max 10 exchanges

# Clear emotion history periodically
if len(self.emotion_history) > 100:
    self.emotion_history.clear()
```

---

## 🔒 Security Considerations

### API Key Management

```bash
# Don't hardcode API keys! Use environment variables:
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/creds.json"

# Or use .env file with python-dotenv
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
```

### Audio Data Privacy

```python
# Don't store raw audio data unnecessarily
# Only keep transcriptions
class EnhancedAIEngine:
    def process_voice_input(self, audio_data):
        # Process immediately
        text, _ = self.speech_engine.transcribe_audio(audio_data)
        
        # Discard audio_data after transcription
        del audio_data
        
        # Continue with text
        return self.llm_engine.generate_response(text)
```

---

## 📊 Monitoring & Metrics

```python
# Track performance metrics
class AIMetrics:
    def __init__(self):
        self.stt_latency = []
        self.intent_latency = []
        self.llm_latency = []
        self.emotion_latency = []
    
    def record_stt(self, latency_ms):
        self.stt_latency.append(latency_ms)
        avg = np.mean(self.stt_latency[-10:])
        logger.info(f"STT Latency: {avg:.0f}ms")
    
    def get_summary(self):
        return {
            'avg_stt': np.mean(self.stt_latency) if self.stt_latency else 0,
            'avg_intent': np.mean(self.intent_latency) if self.intent_latency else 0,
            'avg_llm': np.mean(self.llm_latency) if self.llm_latency else 0,
        }

metrics = AIMetrics()
```

---

## 🐛 Troubleshooting

### Issue: "Google Cloud Speech API not available"
```bash
# Verify credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/json"
python3 -c "from google.cloud import speech; print('✓ Google Cloud available')"
```

### Issue: "OpenAI API timeout"
```python
# Increase timeout and add retries
openai.request_timeout = 10

import tenacity
@tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
def generate_with_retry(text):
    return llm_engine.generate_response(text)
```

### Issue: "Emotion model not found"
```bash
# Download pre-trained model
wget https://github.com/fer2013/facial-expression/releases/download/v1.0/emotion_model.h5 -O emotion_model.h5
```

### Issue: "Out of memory"
```python
# Reduce model precision or use quantization
import tensorflow as tf
quantized_model = tf.lite.TFLiteConverter.from_keras_model(model)
quantized_model.optimizations = [tf.lite.Optimize.DEFAULT]
```

---

## 📈 Expected Performance

After integration, expect:

| Component | Latency | Status |
|-----------|---------|--------|
| Speech-to-Text | 1-2s | ⚠️ (network dependent) |
| Intent Classification | 10-50ms | ✅ |
| LLM Response | 1-3s | ⚠️ (API dependent) |
| Facial Emotion | 100-200ms | ✅ |
| **Total E2E** | **3-5s** | ✅ (acceptable) |

> Note: This exceeds the <3 second requirement. To optimize further, use background threads and async processing.

---

## 🎉 Next Steps

1. ✅ Install dependencies
2. ✅ Set up API credentials
3. ✅ Download emotion model
4. ✅ Integrate into server_main.py
5. ✅ Test individual components
6. ✅ Deploy to Jetson
7. ✅ Monitor performance
8. ✅ Iterate and improve

---

**Version**: 1.0.0  
**Last Updated**: December 7, 2025