🤖 Jetbot OS: AI Mental Health CompanionA fully autonomous, empathetic pet robot powered by NVIDIA Jetson Nano.This project converts a standard Jetbot into an intelligent emotional support companion. It can see your face to detect emotions, hold conversations with long-term memory, and provide empathetic feedback using a localized personality engine.🌟 Key Features🧠 Mental Health & AIVisual Emotion Recognition: Uses efficient computer vision (Haar Cascades) to detect if you look happy, excited, or neutral without lagging the CPU.Therapeutic Brain: Integrated LLM (OpenAI) with a specific "Mental Health" persona. It tracks your mood over time and offers empathetic responses.Long-Term Memory: Remembers past conversations and context to build a relationship with the user.Mood Logging: Automatically logs detected emotions (voice & vision) to data/mood_log.csv for health monitoring.🤖 Core CapabilitiesExpressive Face: An animated display that blinks, looks around, and changes expression based on the robot's "feelings."Voice Interaction: Full Text-to-Speech (TTS) and Speech-to-Text (STT) for natural conversation.Autonomous Navigation: ROS-based navigation stack for moving safely around a room (or Simulation mode for dev).Remote Control: REST API and WebSocket server for Android app control.📂 System ArchitectureThe system runs as a collection of independent micro-services managed by a central launcher./opt/jetbot/
├── jetbot_launcher.py       # Main Process Manager (Systemd Service)
├── config/
│   ├── launcher_config.yaml # Module settings
│   └── api_config.yaml      # Network settings
├── modules/
│   ├── vision_emotion_module.py  # [NEW] The "Eyes" (Emotion detection)
│   ├── llm_module.py             # [NEW] The "Brain" (Memory & Empathy)
│   ├── face_module.py            # The "Face" (PyGame Display)
│   ├── voice_module.py           # The "Mouth/Ears" (TTS/STT)
│   ├── controller_module.py      # Manual Control (Joystick)
│   └── ros_navigation.py         # Autonomous Movement
└── api/                          # Web/Phone Connectivity
🚀 Installation & DeploymentPrerequisitesHardware: NVIDIA Jetson Nano (4GB recommended), Waveshare Jetbot Kit, USB Audio Adapter, Speaker/Mic.OS: JetPack 4.6 (Ubuntu 18.04).Step 1: Install System DependenciesRun this on your Jetson Nano terminal:sudo apt-get update
sudo apt-get install -y python3-pip python3-numpy python3-opencv libatlas-base-dev \
    portaudio19-dev libespeak1 redis-server
Step 2: Deploy the CodeClone this repository to your Jetson.Run the deployment script:sudo chmod +x deploy_complete.sh
sudo ./deploy_complete.sh
This script will:Install Python libraries.Setup the jetbot service.Enable auto-start on boot.Step 3: Configure API KeyThe robot needs an OpenAI API key to "think."Edit the service file:sudo nano /lib/systemd/system/jetbot.service
Find the line Environment="LLM_API_KEY=..." and paste your key.Then reload:sudo systemctl daemon-reload
sudo systemctl restart jetbot
🎮 UsageTo Check Status:sudo systemctl status jetbot
To View Logs:tail -f /var/log/jetbot/launcher_*.log
To View the Mood Log:cat /opt/jetbot/data/mood_log.csv
🛠️ TroubleshootingRobot is silent? Check your speaker connection and run speaker-test -c2.Face not showing? Ensure the HDMI/DSI display is connected before boot, or check config/launcher_config.yaml.High CPU usage? The vision_emotion_module is tuned to process 1 frame every 6 frames. You can adjust process_every_n_frames in the file if it's still too heavy.