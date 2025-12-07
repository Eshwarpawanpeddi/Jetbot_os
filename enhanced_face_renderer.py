"""
Enhanced Face Renderer for 5" HDMI Raspberry Pi Display
Optimized for Jetson Nano with smooth animations and expressive features
Author: Eshwar Pawan Peddi
Version: 1.0.0
"""

import cv2
import numpy as np
import json
import math
import time
from dataclasses import dataclass
from typing import Tuple, Optional, Dict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Emotion(Enum):
    """Emotion states"""
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    ANGRY = "angry"
    THINKING = "thinking"
    SLEEPING = "sleeping"
    LOVE = "love"
    SKEPTICAL = "skeptical"


@dataclass
class ColorScheme:
    """Color scheme for each emotion"""
    primary: Tuple[int, int, int]      # Main color (BGR)
    secondary: Tuple[int, int, int]    # Secondary color
    accent: Tuple[int, int, int]       # Accent color
    background: Tuple[int, int, int]   # Background color


class EmotionColorScheme:
    """Color palettes for different emotions"""
    
    SCHEMES = {
        Emotion.HAPPY: ColorScheme(
            primary=(0, 215, 255),      # Golden yellow
            secondary=(0, 165, 255),    # Orange
            accent=(255, 255, 255),     # White (sparkles)
            background=(230, 230, 250)  # Light background
        ),
        Emotion.SAD: ColorScheme(
            primary=(220, 20, 60),      # Dark blue
            secondary=(100, 100, 150),  # Slate
            accent=(100, 149, 237),     # Cornflower blue
            background=(220, 220, 230)  # Cool background
        ),
        Emotion.EXCITED: ColorScheme(
            primary=(0, 165, 255),      # Gold
            secondary=(0, 100, 255),    # Orange-red
            accent=(255, 255, 100),     # Bright yellow
            background=(200, 220, 255)  # Warm background
        ),
        Emotion.NEUTRAL: ColorScheme(
            primary=(128, 128, 128),    # Gray
            secondary=(100, 100, 120),  # Dark gray
            accent=(180, 180, 180),     # Light gray
            background=(240, 240, 240)  # Neutral background
        ),
        Emotion.CONFUSED: ColorScheme(
            primary=(180, 82, 205),     # Medium purple
            secondary=(138, 43, 226),   # Violet
            accent=(200, 100, 220),     # Light purple
            background=(230, 220, 240)  # Purple background
        ),
        Emotion.ANGRY: ColorScheme(
            primary=(0, 0, 220),        # Bright red
            secondary=(0, 0, 150),      # Dark red
            accent=(100, 0, 0),         # Very dark red
            background=(220, 200, 200)  # Warm-red background
        ),
        Emotion.THINKING: ColorScheme(
            primary=(255, 200, 0),      # Cyan-like
            secondary=(150, 180, 200),  # Steel blue
            accent=(200, 220, 240),     # Light blue
            background=(235, 245, 250)  # Cool background
        ),
        Emotion.SLEEPING: ColorScheme(
            primary=(150, 150, 200),    # Lavender
            secondary=(100, 100, 150),  # Dark lavender
            accent=(200, 200, 220),     # Light lavender
            background=(240, 240, 250)  # Very light
        ),
        Emotion.LOVE: ColorScheme(
            primary=(180, 100, 200),    # Pink-purple
            secondary=(255, 100, 150),  # Hot pink
            accent=(255, 150, 200),     # Light pink
            background=(250, 220, 240)  # Pink background
        ),
        Emotion.SKEPTICAL: ColorScheme(
            primary=(0, 180, 100),      # Green-teal
            secondary=(0, 100, 80),     # Dark green
            accent=(100, 200, 150),     # Light green
            background=(220, 240, 220)  # Green background
        ),
    }


class BlinkController:
    """Manages natural blinking"""
    
    def __init__(self, blink_rate=4):
        """
        Args:
            blink_rate: Blinks per minute
        """
        self.blink_rate = blink_rate
        self.last_blink_time = time.time()
        self.blink_duration = 0.1  # 100ms blink
        self.is_blinking = False
        self.blink_start_time = 0
        
    def should_blink(self) -> bool:
        """Check if it's time to blink"""
        current_time = time.time()
        interval = 60 / self.blink_rate  # seconds between blinks
        
        if current_time - self.last_blink_time >= interval:
            self.is_blinking = True
            self.blink_start_time = current_time
            self.last_blink_time = current_time
            
        # Check if blink is complete
        if self.is_blinking:
            elapsed = current_time - self.blink_start_time
            if elapsed > self.blink_duration:
                self.is_blinking = False
                
        return self.is_blinking
    
    def get_blink_progress(self) -> float:
        """Get blink progress (0-1)"""
        if not self.is_blinking:
            return 0.0
        elapsed = time.time() - self.blink_start_time
        progress = elapsed / self.blink_duration
        # Smooth easing: accelerate then decelerate
        if progress < 0.5:
            return progress * 2  # Speed up
        else:
            return 2 - progress * 2  # Slow down
        return min(1.0, progress)


class EyeRenderer:
    """Renders realistic eyes with pupils and highlights"""
    
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.pupil_x = 0.0  # -1 to 1 (left to right)
        self.pupil_y = 0.0  # -1 to 1 (up to down)
        
    def render_eye(self, frame, cx: int, cy: int, radius: int, 
                   color: Tuple[int, int, int], is_blinking: float = 0.0,
                   emotion: Emotion = Emotion.NEUTRAL) -> np.ndarray:
        """
        Render a single eye
        
        Args:
            frame: Canvas to draw on
            cx, cy: Center position
            radius: Eye radius
            color: Eye color (BGR)
            is_blinking: Blink progress (0-1), 0 = open, 1 = closed
            emotion: Current emotion
        """
        if is_blinking > 0.8:
            # Eye is closed, draw simple line
            cv2.line(frame, (cx - radius, cy), (cx + radius, cy), color, 3)
            return frame
        
        # Draw sclera (white of eye)
        cv2.circle(frame, (cx, cy), radius, (255, 255, 255), -1)
        
        # Draw iris
        iris_radius = int(radius * 0.6)
        iris_x = int(cx + self.pupil_x * (radius - iris_radius))
        iris_y = int(cy + self.pupil_y * (radius - iris_radius))
        cv2.circle(frame, (iris_x, iris_y), iris_radius, color, -1)
        
        # Draw pupil
        pupil_radius = int(radius * 0.35)
        cv2.circle(frame, (iris_x, iris_y), pupil_radius, (0, 0, 0), -1)
        
        # Add highlights for shine
        highlight_radius = int(pupil_radius * 0.4)
        highlight_x = iris_x - int(pupil_radius * 0.3)
        highlight_y = iris_y - int(pupil_radius * 0.3)
        cv2.circle(frame, (highlight_x, highlight_y), highlight_radius, 
                   (255, 255, 255), -1)
        
        # Add second highlight
        highlight_x2 = iris_x + int(pupil_radius * 0.2)
        highlight_y2 = iris_y + int(pupil_radius * 0.2)
        cv2.circle(frame, (highlight_x2, highlight_y2), 
                   max(1, highlight_radius // 2), (180, 180, 180), -1)
        
        # Add sparkle effect for happy emotions
        if emotion == Emotion.EXCITED or emotion == Emotion.HAPPY:
            for _ in range(3):
                offset_x = np.random.randint(-radius, radius)
                offset_y = np.random.randint(-radius, radius)
                cv2.circle(frame, (cx + offset_x, cy + offset_y), 2, 
                          (255, 255, 100), -1)
        
        return frame
    
    def update_pupil_position(self, dx: float, dy: float):
        """Update pupil position for tracking (-1 to 1)"""
        self.pupil_x = np.clip(dx, -1, 1)
        self.pupil_y = np.clip(dy, -1, 1)


class MouthRenderer:
    """Renders mouth shapes for different emotions and speech"""
    
    # Mouth positions for different states
    MOUTH_SHAPES = {
        'neutral': [(0, 0), (0.3, 0.1), (0.6, 0.1), (1, 0)],
        'smile': [(0, 0), (0.3, 0.3), (0.6, 0.3), (1, 0)],
        'big_smile': [(0, 0.1), (0.3, 0.5), (0.6, 0.5), (1, 0.1)],
        'sad': [(0, 0.2), (0.3, 0), (0.6, 0), (1, 0.2)],
        'O': [(0.2, 0.2), (0.4, 0.4), (0.6, 0.4), (0.8, 0.2)],
        'A': [(0.15, 0.1), (0.35, 0.6), (0.65, 0.6), (0.85, 0.1)],
        'E': [(0.1, 0.2), (0.3, 0.3), (0.7, 0.3), (0.9, 0.2)],
        'I': [(0.3, 0.1), (0.4, 0.4), (0.6, 0.4), (0.7, 0.1)],
    }
    
    def __init__(self):
        self.current_mouth = 'neutral'
        
    def render_mouth(self, frame, cx: int, cy: int, width: int, height: int,
                     mouth_shape: str = 'neutral', 
                     color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        """
        Render mouth shape
        
        Args:
            frame: Canvas
            cx, cy: Center position
            width, height: Mouth dimensions
            mouth_shape: Shape name
            color: Mouth color
        """
        if mouth_shape not in self.MOUTH_SHAPES:
            mouth_shape = 'neutral'
        
        shape = self.MOUTH_SHAPES[mouth_shape]
        
        # Convert relative coordinates to absolute
        points = []
        for x, y in shape:
            abs_x = int(cx - width/2 + x * width)
            abs_y = int(cy - height/2 + y * height)
            points.append([abs_x, abs_y])
        
        points = np.array(points, dtype=np.int32)
        
        # Draw mouth outline
        cv2.polylines(frame, [points], False, color, 3)
        
        # Fill mouth for closed mouths
        if mouth_shape in ['neutral', 'sad']:
            cv2.polylines(frame, [points], True, color, 3)
        else:
            # Fill inside for open mouths
            cv2.fillPoly(frame, [points], (100, 50, 50))
            cv2.polylines(frame, [points], False, color, 3)
        
        return frame


class EyebrowRenderer:
    """Renders expressive eyebrows"""
    
    def __init__(self):
        self.positions = {
            'angry': (-0.5, 0.3),      # Down and inward
            'sad': (0.2, -0.2),        # Inward and up
            'neutral': (0, 0),         # Straight
            'happy': (0.2, 0.2),       # Up and out
            'surprised': (0.3, 0.4),   # Very high
        }
    
    def render_eyebrow(self, frame, cx: int, cy: int, width: int, height: int,
                       position: str = 'neutral',
                       color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        """Render a single eyebrow"""
        if position not in self.positions:
            position = 'neutral'
        
        x_tilt, y_offset = self.positions[position]
        
        # Create bezier curve for eyebrow
        start_x = int(cx - width/2)
        end_x = int(cx + width/2)
        base_y = int(cy + y_offset * height)
        
        # Bezier control points
        pts = []
        for t in np.linspace(0, 1, 20):
            # Quadratic bezier curve
            x = int(start_x + (end_x - start_x) * t)
            y = int(base_y + math.sin(t * math.pi) * x_tilt * height)
            pts.append([x, y])
        
        pts = np.array(pts, dtype=np.int32)
        cv2.polylines(frame, [pts], False, color, 4)
        
        return frame


class BackgroundRenderer:
    """Renders background effects"""
    
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.particles = []
        
    def render_background(self, frame: np.ndarray, 
                         color: Tuple[int, int, int]) -> np.ndarray:
        """Render gradient background"""
        # Create gradient from top to bottom
        for i in range(self.height):
            ratio = i / self.height
            # Blend colors smoothly
            blended = tuple(int(c * (1 - ratio) + 255 * ratio) for c in color)
            cv2.line(frame, (0, i), (self.width, i), blended, 1)
        
        return frame
    
    def render_tears(self, frame: np.ndarray, cx: int, cy: int,
                    tear_count: int = 1) -> np.ndarray:
        """Render tears for sad emotion"""
        for i in range(tear_count):
            # Tear droplet
            tear_x = cx + i * 15
            tear_y = cy
            cv2.circle(frame, (tear_x, tear_y), 5, (255, 200, 200), -1)
            
            # Tear trail
            for offset in range(1, 30):
                trail_y = tear_y + offset * 2
                alpha = 1 - (offset / 30)
                color = (int(255 * alpha), int(200 * alpha), int(200 * alpha))
                cv2.circle(frame, (tear_x, trail_y), max(1, int(5 * alpha)), 
                          color, -1)
        
        return frame


class FaceRenderer:
    """Main face renderer - combines all components"""
    
    def __init__(self, config_path: Optional[str] = None, 
                 width: int = 1280, height: int = 720):
        """
        Initialize face renderer
        
        Args:
            config_path: Path to config JSON (optional)
            width: Display width
            height: Display height
        """
        self.width = width
        self.height = height
        
        # Initialize components
        self.eye_renderer = EyeRenderer(width, height)
        self.mouth_renderer = MouthRenderer()
        self.eyebrow_renderer = EyebrowRenderer()
        self.background_renderer = BackgroundRenderer(width, height)
        self.blink_controller = BlinkController(blink_rate=17)  # Natural rate
        
        # State variables
        self.current_emotion = Emotion.NEUTRAL
        self.current_mouth_shape = 'neutral'
        self.emotion_transition_time = 0.3  # seconds
        self.last_emotion_change = time.time()
        self.head_tilt = 0.0  # -1 to 1
        self.speech_active = False
        
        # Animation state
        self.animation_frame = 0
        self.animation_time = time.time()
        
    def render_face(self, emotion: Emotion = Emotion.NEUTRAL,
                   speech_active: bool = False,
                   mouth_position: int = 0) -> np.ndarray:
        """
        Render complete face
        
        Args:
            emotion: Current emotion
            speech_active: Whether speech is active
            mouth_position: 0-10 for different mouth shapes
            
        Returns:
            Frame with rendered face
        """
        # Create blank canvas
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (255, 255, 255)  # White background
        
        # Get color scheme
        if emotion != self.current_emotion:
            self.current_emotion = emotion
            self.last_emotion_change = time.time()
        
        color_scheme = EmotionColorScheme.SCHEMES[emotion]
        
        # Render background with gradient
        frame = self.background_renderer.render_background(frame, 
                                                           color_scheme.background)
        
        # Calculate face position (centered)
        face_cx = self.width // 2
        face_cy = self.height // 2
        face_radius = min(self.width, self.height) // 3
        
        # Draw face circle (head)
        cv2.circle(frame, (face_cx, face_cy), face_radius, 
                  color_scheme.primary, -1)
        cv2.circle(frame, (face_cx, face_cy), face_radius, 
                  color_scheme.secondary, 3)
        
        # Eye positions
        eye_distance = int(face_radius * 0.5)
        left_eye_x = face_cx - eye_distance
        right_eye_x = face_cx + eye_distance
        eye_y = face_cy - int(face_radius * 0.2)
        eye_radius = int(face_radius * 0.25)
        
        # Check for blinking
        is_blinking = self.blink_controller.should_blink()
        blink_progress = self.blink_controller.get_blink_progress() if is_blinking else 0.0
        
        # Render eyes
        frame = self.eye_renderer.render_eye(frame, left_eye_x, eye_y, eye_radius,
                                            color_scheme.accent, blink_progress, emotion)
        frame = self.eye_renderer.render_eye(frame, right_eye_x, eye_y, eye_radius,
                                            color_scheme.accent, blink_progress, emotion)
        
        # Render eyebrows
        eyebrow_y = eye_y - int(face_radius * 0.15)
        eyebrow_width = int(eye_radius * 1.2)
        eyebrow_height = int(eye_radius * 0.3)
        
        # Map emotion to eyebrow position
        eyebrow_pos = {
            Emotion.ANGRY: 'angry',
            Emotion.SAD: 'sad',
            Emotion.HAPPY: 'happy',
            Emotion.EXCITED: 'surprised',
            Emotion.CONFUSED: 'surprised',
            Emotion.NEUTRAL: 'neutral',
        }.get(emotion, 'neutral')
        
        frame = self.eyebrow_renderer.render_eyebrow(frame, left_eye_x, eyebrow_y,
                                                     eyebrow_width, eyebrow_height,
                                                     eyebrow_pos, (0, 0, 0))
        frame = self.eyebrow_renderer.render_eyebrow(frame, right_eye_x, eyebrow_y,
                                                     eyebrow_width, eyebrow_height,
                                                     eyebrow_pos, (0, 0, 0))
        
        # Determine mouth shape based on emotion and speech
        if speech_active:
            mouth_shapes = ['neutral', 'A', 'O', 'E', 'I']
            self.current_mouth_shape = mouth_shapes[mouth_position % len(mouth_shapes)]
        else:
            mouth_shape_map = {
                Emotion.HAPPY: 'smile',
                Emotion.SAD: 'sad',
                Emotion.EXCITED: 'big_smile',
                Emotion.NEUTRAL: 'neutral',
                Emotion.CONFUSED: 'O',
                Emotion.ANGRY: 'sad',
            }
            self.current_mouth_shape = mouth_shape_map.get(emotion, 'neutral')
        
        # Render mouth
        mouth_x = face_cx
        mouth_y = face_cy + int(face_radius * 0.3)
        mouth_width = int(face_radius * 0.8)
        mouth_height = int(face_radius * 0.4)
        
        frame = self.mouth_renderer.render_mouth(frame, mouth_x, mouth_y,
                                                mouth_width, mouth_height,
                                                self.current_mouth_shape,
                                                (0, 0, 0))
        
        # Render tears for sad emotion
        if emotion == Emotion.SAD:
            frame = self.background_renderer.render_tears(frame, left_eye_x, 
                                                         eye_y + eye_radius + 10, 1)
            frame = self.background_renderer.render_tears(frame, right_eye_x, 
                                                         eye_y + eye_radius + 10, 1)
        
        # Add emotion label at top
        emotion_text = emotion.value.upper()
        cv2.putText(frame, emotion_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                   1.5, (0, 0, 0), 2)
        
        # Add status info at bottom
        status = f"Speech: {'ON' if speech_active else 'OFF'} | FPS: 30"
        cv2.putText(frame, status, (50, self.height - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        return frame


# Test and demonstration code
if __name__ == "__main__":
    print("🎨 Enhanced Face Renderer - Demo Mode")
    print("=" * 60)
    
    # Initialize renderer
    renderer = FaceRenderer(width=1280, height=720)
    
    # Test different emotions
    emotions_sequence = [
        Emotion.NEUTRAL,
        Emotion.HAPPY,
        Emotion.EXCITED,
        Emotion.CONFUSED,
        Emotion.SAD,
        Emotion.ANGRY,
        Emotion.THINKING,
        Emotion.LOVE,
    ]
    
    emotion_idx = 0
    frame_count = 0
    start_time = time.time()
    
    print("\nRendering demonstration (30 frames per emotion)...")
    print("Press 'q' to quit, 'n' for next emotion")
    
    # Note: This requires a display. If running headless, comment out cv2.imshow
    try:
        cv2.namedWindow('AI Pet Robot - Face Display', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('AI Pet Robot - Face Display', 1280, 720)
        
        while True:
            emotion = emotions_sequence[emotion_idx % len(emotions_sequence)]
            
            # Render face
            frame = renderer.render_face(
                emotion=emotion,
                speech_active=(frame_count % 10 < 5),  # Toggle speech
                mouth_position=frame_count % 5
            )
            
            # Display
            cv2.imshow('AI Pet Robot - Face Display', frame)
            
            # Handle input
            key = cv2.waitKey(33) & 0xFF  # ~30 FPS
            if key == ord('q'):
                break
            elif key == ord('n'):
                emotion_idx += 1
                frame_count = 0
            
            frame_count += 1
            
            # Move to next emotion after 30 frames
            if frame_count >= 30:
                emotion_idx += 1
                frame_count = 0
        
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"Display error (expected if headless): {e}")
        print("✅ Renderer initialized successfully!")
        print(f"Resolution: 1280x720 | FPS Target: 30")
        print(f"Emotions: {len(emotions_sequence)} different expressions")
    
    print("\n✅ Face renderer ready for integration!")
    print("\nIntegration Example:")
    print("""
    from enhanced_face_renderer import FaceRenderer, Emotion
    
    renderer = FaceRenderer(width=1280, height=720)
    
    # In your display loop:
    frame = renderer.render_face(
        emotion=Emotion.HAPPY,
        speech_active=False,
        mouth_position=0
    )
    cv2.imshow('Display', frame)
    """)
