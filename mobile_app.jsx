// ============================================================================
// MOBILE APP - React Native (Expo) Implementation
// ============================================================================
// Purpose: Voice input microphone, HDMI display mirror, manual robot control
// Communicates with laptop server via WebSocket & Bluetooth
// Platforms: iOS & Android (using Expo)
// ============================================================================

// ============================================================================
// App.js - Main Application Entry Point
// ============================================================================

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Dimensions,
  ScrollView,
  Image,
  ActivityIndicator,
  Vibration,
} from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { Camera } from 'expo-camera';
import io from 'socket.io-client';
import { GestureHandlerRootView, PanGestureHandler } from 'react-native-gesture-handler';
import RNBluetoothClassic from 'react-native-bluetooth-classic';

const { width, height } = Dimensions.get('window');

const SERVER_HOST = '192.168.1.101'; // Update with your laptop IP
const SERVER_PORT = 5000;

export default function App() {
  // ========== STATE MANAGEMENT ==========
  const [connected, setConnected] = useState(false);
  const [displayFrame, setDisplayFrame] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [robotEmotion, setRobotEmotion] = useState('neutral');
  const [controlMode, setControlMode] = useState('automatic'); // 'automatic' or 'manual'
  const [motorLeft, setMotorLeft] = useState(0);
  const [motorRight, setMotorRight] = useState(0);
  const [loading, setLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState({
    jetson: false,
    esp32: false,
    server: false,
  });
  
  const socketRef = useRef(null);
  const audioRef = useRef(null);
  const recordingRef = useRef(null);

  // ========== INITIALIZATION ==========
  useEffect(() => {
    initializeApp();
    
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (recordingRef.current) {
        recordingRef.current.stopAndUnloadAsync();
      }
    };
  }, []);

  const initializeApp = async () => {
    // Request audio permissions
    const { status } = await Audio.requestPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Error', 'Audio permissions required');
      return;
    }

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    // Initialize recording
    try {
      const recording = new Audio.Recording();
      recordingRef.current = recording;
    } catch (err) {
      console.error('Failed to initialize recording:', err);
    }

    // Connect to WebSocket server
    connectToServer();
  };

  // ========== WEBSOCKET CONNECTION ==========
  const connectToServer = () => {
    try {
      const socket = io(`http://${SERVER_HOST}:${SERVER_PORT}`, {
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
      });

      socket.on('connect', () => {
        console.log('Connected to server');
        setConnected(true);
      });

      socket.on('disconnect', () => {
        console.log('Disconnected from server');
        setConnected(false);
      });

      // Receive display frames
      socket.on('display_frame', (data) => {
        if (data.frame) {
          setDisplayFrame(`data:image/jpeg;base64,${data.frame}`);
          if (data.emotion) {
            setRobotEmotion(data.emotion);
          }
        }
      });

      // Receive status updates
      socket.on('status_update', (data) => {
        console.log('Status update:', data);
        setSystemStatus(data);
      });

      // Handle command processed
      socket.on('command_processed', (response) => {
        if (response.emotion) {
          setRobotEmotion(response.emotion);
        }
      });

      socketRef.current = socket;
    } catch (err) {
      console.error('Connection error:', err);
      Alert.alert('Connection Error', 'Failed to connect to server');
    }
  };

  // ========== VOICE COMMAND PROCESSING ==========
  const startListening = async () => {
    try {
      setIsListening(true);
      setLoading(true);

      const recording = recordingRef.current;
      
      await recording.startAsync();
      
      // Record for 5 seconds
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      await recording.stopAndUnloadAsync();

      const uri = recording.getURI();
      console.log('Recording saved to:', uri);

      // Simulate speech-to-text (in production, use Google Speech-to-Text API)
      const voiceText = await processVoiceToText(uri);
      
      if (voiceText && socketRef.current) {
        console.log('Sending voice command:', voiceText);
        socketRef.current.emit('voice_command', { text: voiceText });
        
        // Visual feedback
        Vibration.vibrate(100);
      }

      setIsListening(false);
      setLoading(false);
    } catch (err) {
      console.error('Error during voice recording:', err);
      setIsListening(false);
      setLoading(false);
      Alert.alert('Error', 'Failed to record voice command');
    }
  };

  const processVoiceToText = async (audioUri) => {
    // TODO: Integrate with Google Speech-to-Text API
    // For now, return mock data
    const mockCommands = [
      'move forward',
      'move backward',
      'turn left',
      'turn right',
      'show shopping list',
      'be happy',
    ];
    return mockCommands[Math.floor(Math.random() * mockCommands.length)];
  };

  // ========== MANUAL MOTOR CONTROL ==========
  const handleJoystickChange = (gestureEvent) => {
    const { translationX, translationY } = gestureEvent.nativeEvent;
    
    // Convert joystick position to motor speeds
    const maxTranslation = 50;
    const leftSpeed = Math.max(-100, Math.min(100, -translationY / maxTranslation * 100));
    const rightSpeed = Math.max(-100, Math.min(100, -translationY / maxTranslation * 100));
    
    // Handle rotation (turning)
    const turnAmount = translationX / maxTranslation * 50;
    
    const finalLeft = Math.round(leftSpeed - turnAmount);
    const finalRight = Math.round(rightSpeed + turnAmount);
    
    setMotorLeft(finalLeft);
    setMotorRight(finalRight);
    
    if (socketRef.current) {
      socketRef.current.emit('manual_control', {
        left_speed: finalLeft,
        right_speed: finalRight,
      });
    }
  };

  const sendMotorCommand = (left, right) => {
    setMotorLeft(left);
    setMotorRight(right);
    
    if (socketRef.current) {
      socketRef.current.emit('manual_control', {
        left_speed: left,
        right_speed: right,
      });
    }
  };

  // ========== EMOTION CONTROL ==========
  const changeEmotion = (emotion) => {
    setRobotEmotion(emotion);
    if (socketRef.current) {
      socketRef.current.emit('emotion_request', { emotion });
    }
    Vibration.vibrate(50);
  };

  // ========== DISPLAY TEXT CONTENT ==========
  const sendDisplayRequest = (type, title = '', content = '') => {
    if (socketRef.current) {
      socketRef.current.emit('display_request', {
        type,
        title,
        content,
      });
    }
  };

  // ========== UI COMPONENTS ==========
  const DisplayMirror = () => (
    <View style={styles.displayContainer}>
      {displayFrame ? (
        <Image
          source={{ uri: displayFrame }}
          style={styles.displayImage}
          resizeMode="contain"
        />
      ) : (
        <View style={styles.displayPlaceholder}>
          <ActivityIndicator size="large" color="#3498db" />
          <Text style={styles.placeholderText}>Waiting for display...</Text>
        </View>
      )}
      
      {/* Emotion Indicator */}
      <View style={styles.emotionIndicator}>
        <Text style={styles.emotionText}>{robotEmotion.toUpperCase()}</Text>
      </View>
      
      {/* Connection Status */}
      <View style={styles.statusIndicator}>
        <View style={[styles.statusDot, { backgroundColor: connected ? '#27ae60' : '#e74c3c' }]} />
        <Text style={styles.statusText}>{connected ? 'Connected' : 'Disconnected'}</Text>
      </View>
    </View>
  );

  const VoiceCommandPanel = () => (
    <View style={styles.voicePanel}>
      <TouchableOpacity
        style={[styles.voiceButton, isListening && styles.voiceButtonActive]}
        onPress={startListening}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.voiceButtonText}>
            {isListening ? '🎤 Listening...' : '🎤 Voice Command'}
          </Text>
        )}
      </TouchableOpacity>
      
      <View style={styles.quickCommandsContainer}>
        <TouchableOpacity
          style={styles.quickCommand}
          onPress={() => sendDisplayRequest('text', 'Shopping List', '1. Milk\n2. Bread\n3. Eggs')}
        >
          <Text style={styles.quickCommandText}>📝 List</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.quickCommand}
          onPress={() => sendDisplayRequest('text', 'Formula', 'E = mc²')}
        >
          <Text style={styles.quickCommandText}>📐 Formula</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.quickCommand}
          onPress={() => sendDisplayRequest('face')}
        >
          <Text style={styles.quickCommandText}>😊 Face</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const ManualControlPanel = () => (
    <View style={styles.controlPanel}>
      <Text style={styles.controlTitle}>Manual Control</Text>
      
      {/* Mode Toggle */}
      <View style={styles.modeToggle}>
        <TouchableOpacity
          style={[styles.modeButton, controlMode === 'automatic' && styles.modeButtonActive]}
          onPress={() => setControlMode('automatic')}
        >
          <Text style={styles.modeButtonText}>Auto</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.modeButton, controlMode === 'manual' && styles.modeButtonActive]}
          onPress={() => setControlMode('manual')}
        >
          <Text style={styles.modeButtonText}>Manual</Text>
        </TouchableOpacity>
      </View>
      
      {controlMode === 'manual' && (
        <>
          {/* Direction Pad */}
          <View style={styles.directionPad}>
            <TouchableOpacity
              style={styles.directionButton}
              onPress={() => sendMotorCommand(80, 80)}
            >
              <Text style={styles.directionButtonText}>⬆️</Text>
            </TouchableOpacity>
            
            <View style={styles.directionRow}>
              <TouchableOpacity
                style={styles.directionButton}
                onPress={() => sendMotorCommand(-50, 80)}
              >
                <Text style={styles.directionButtonText}>⬅️</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.directionButton}
                onPress={() => sendMotorCommand(0, 0)}
              >
                <Text style={styles.directionButtonText}>⏹️</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.directionButton}
                onPress={() => sendMotorCommand(80, -50)}
              >
                <Text style={styles.directionButtonText}>➡️</Text>
              </TouchableOpacity>
            </View>
            
            <TouchableOpacity
              style={styles.directionButton}
              onPress={() => sendMotorCommand(-80, -80)}
            >
              <Text style={styles.directionButtonText}>⬇️</Text>
            </TouchableOpacity>
          </View>
          
          {/* Speed Indicator */}
          <View style={styles.speedIndicator}>
            <Text style={styles.speedText}>L: {motorLeft}</Text>
            <Text style={styles.speedText}>R: {motorRight}</Text>
          </View>
        </>
      )}
    </View>
  );

  const EmotionPanel = () => (
    <View style={styles.emotionPanel}>
      <Text style={styles.emotionTitle}>Robot Emotion</Text>
      
      <View style={styles.emotionGrid}>
        {['happy', 'sad', 'excited', 'neutral', 'confused'].map((emotion) => (
          <TouchableOpacity
            key={emotion}
            style={[
              styles.emotionButton,
              robotEmotion === emotion && styles.emotionButtonActive,
            ]}
            onPress={() => changeEmotion(emotion)}
          >
            <Text style={styles.emotionButtonText}>
              {emotion === 'happy' && '😊'}
              {emotion === 'sad' && '😢'}
              {emotion === 'excited' && '🤩'}
              {emotion === 'neutral' && '😐'}
              {emotion === 'confused' && '😕'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  // ========== MAIN RENDER ==========
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>🤖 PET ROBOT CONTROL</Text>
          <Text style={styles.subtitle}>
            {connected ? '✅ Connected' : '❌ Disconnected'}
          </Text>
        </View>

        {/* Display Mirror */}
        <DisplayMirror />

        {/* Voice Command Panel */}
        <VoiceCommandPanel />

        {/* Emotion Panel */}
        <EmotionPanel />

        {/* Manual Control Panel */}
        <ManualControlPanel />

        {/* System Status */}
        <View style={styles.statusPanel}>
          <Text style={styles.statusPanelTitle}>System Status</Text>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Server:</Text>
            <View style={[styles.statusIndicatorSmall, { backgroundColor: systemStatus.server ? '#27ae60' : '#e74c3c' }]} />
          </View>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Jetson:</Text>
            <View style={[styles.statusIndicatorSmall, { backgroundColor: systemStatus.jetson ? '#27ae60' : '#e74c3c' }]} />
          </View>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>ESP32:</Text>
            <View style={[styles.statusIndicatorSmall, { backgroundColor: systemStatus.esp32 ? '#27ae60' : '#e74c3c' }]} />
          </View>
        </View>
      </ScrollView>
    </GestureHandlerRootView>
  );
}

// ============================================================================
// STYLES
// ============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  contentContainer: {
    padding: 12,
    paddingBottom: 30,
  },
  header: {
    marginBottom: 20,
    paddingVertical: 15,
    backgroundColor: '#2c3e50',
    borderRadius: 10,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 14,
    color: '#ecf0f1',
    marginTop: 5,
  },
  displayContainer: {
    marginBottom: 20,
    backgroundColor: '#000',
    borderRadius: 10,
    overflow: 'hidden',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  displayImage: {
    width: '100%',
    height: 300,
  },
  displayPlaceholder: {
    width: '100%',
    height: 300,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
  },
  placeholderText: {
    color: '#999',
    marginTop: 10,
    fontSize: 14,
  },
  emotionIndicator: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  emotionText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  statusIndicator: {
    position: 'absolute',
    bottom: 10,
    left: 10,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  voicePanel: {
    marginBottom: 20,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    elevation: 3,
  },
  voiceButton: {
    backgroundColor: '#e74c3c',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 15,
  },
  voiceButtonActive: {
    backgroundColor: '#c0392b',
  },
  voiceButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  quickCommandsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  quickCommand: {
    flex: 1,
    backgroundColor: '#ecf0f1',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  quickCommandText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  controlPanel: {
    marginBottom: 20,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    elevation: 3,
  },
  controlTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  modeToggle: {
    flexDirection: 'row',
    marginBottom: 15,
  },
  modeButton: {
    flex: 1,
    paddingVertical: 10,
    backgroundColor: '#ecf0f1',
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  modeButtonActive: {
    backgroundColor: '#3498db',
  },
  modeButtonText: {
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  directionPad: {
    alignItems: 'center',
    marginBottom: 15,
  },
  directionButton: {
    width: 60,
    height: 60,
    backgroundColor: '#3498db',
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 8,
  },
  directionRow: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  directionButtonText: {
    fontSize: 24,
  },
  speedIndicator: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#ecf0f1',
    borderRadius: 8,
  },
  speedText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  emotionPanel: {
    marginBottom: 20,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    elevation: 3,
  },
  emotionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  emotionGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  emotionButton: {
    width: '18%',
    aspectRatio: 1,
    backgroundColor: '#ecf0f1',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emotionButtonActive: {
    backgroundColor: '#f39c12',
  },
  emotionButtonText: {
    fontSize: 24,
  },
  statusPanel: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    elevation: 3,
  },
  statusPanelTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#ecf0f1',
  },
  statusLabel: {
    fontSize: 14,
    color: '#2c3e50',
  },
  statusIndicatorSmall: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
});