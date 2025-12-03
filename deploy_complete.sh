#!/bin/bash
#==============================================================================
# JETBOT OS - COMPLETE DEPLOYMENT SCRIPT
# Installs dependencies, cleans old files, and sets up the service.
#==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="/opt/jetbot"
USER_NAME=${SUDO_USER:-$USER}

echo -e "${GREEN}=== STARTING JETBOT OS DEPLOYMENT ===${NC}"

# 1. PRE-FLIGHT CHECKS
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo).${NC}"
    exit 1
fi

# 2. SYSTEM DEPENDENCIES
echo -e "\n${YELLOW}[1/5] Installing System Libraries...${NC}"
apt-get update
# Install audio, redis, and build tools
apt-get install -y python3-pip python3-dev git curl redis-server \
    portaudio19-dev libespeak1 python3-pyaudio

# 3. PYTHON DEPENDENCIES
echo -e "\n${YELLOW}[2/5] Installing Python Libraries...${NC}"
# Create requirements if missing
if [ ! -f requirements.txt ]; then
    echo "Creating default requirements.txt..."
    cat > requirements.txt << EOL
pyyaml
requests
redis
flask
flask-cors
fastapi
uvicorn
websockets
openai
SpeechRecognition
pyttsx3
pygame
EOL
fi
pip3 install -r requirements.txt

# 4. FILE DEPLOYMENT
echo -e "\n${YELLOW}[3/5] Deploying Files to $INSTALL_DIR...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $INSTALL_DIR/config
mkdir -p $INSTALL_DIR/modules
mkdir -p $INSTALL_DIR/api
mkdir -p $INSTALL_DIR/data
mkdir -p $INSTALL_DIR/media/photos
mkdir -p $INSTALL_DIR/media/videos
mkdir -p /var/log/jetbot

# Copy files (Assume we are running from the source folder)
cp -r . $INSTALL_DIR/

# 5. CLEANUP OLD CONFLICTS (Crucial Step)
echo -e "\n${YELLOW}[4/5] Cleaning up old conflicting files...${NC}"
rm -f $INSTALL_DIR/main_launcher.py
rm -f $INSTALL_DIR/modules/face_display.py
rm -f $INSTALL_DIR/modules/llm_voice.py
rm -f $INSTALL_DIR/modules/navigation.py
rm -f $INSTALL_DIR/modules/web_api.py
rm -rf $INSTALL_DIR/core

# Set Permissions
chown -R $USER_NAME:$USER_NAME $INSTALL_DIR
chown -R $USER_NAME:$USER_NAME /var/log/jetbot
chmod +x $INSTALL_DIR/jetbot_launcher.py
chmod +x $INSTALL_DIR/start_api_server.py

# 6. SERVICE SETUP
echo -e "\n${YELLOW}[5/5] Configuring Systemd Service...${NC}"
if [ -f jetbot.service ]; then
    cp jetbot.service /lib/systemd/system/
    systemctl daemon-reload
    systemctl enable jetbot.service
    echo "Service enabled."
else
    echo -e "${RED}Warning: jetbot.service file not found!${NC}"
fi

echo -e "\n${GREEN}=== DEPLOYMENT COMPLETE ===${NC}"
echo "To start the robot:"
echo "  sudo systemctl start jetbot"
echo "To view logs:"
echo "  tail -f /var/log/jetbot/launcher_*.log"