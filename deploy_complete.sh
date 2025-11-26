#!/bin/bash
#==============================================================================
# COMPLETE JETBOT OS DEPLOYMENT
# One command to deploy everything on Jetson Nano
#==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "\n${CYAN}=== $1 ===${NC}\n"
}

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${CYAN}ℹ${NC} $1"; }

INSTALL_DIR="/opt/jetbot"

print_header "JETBOT OS COMPLETE DEPLOYMENT"

# Check if running on Jetson
if [ -f /etc/nv_tegra_release ]; then
    print_success "Running on Jetson Nano"
    IS_JETSON=true
else
    print_info "Not running on Jetson - Development mode"
    IS_JETSON=false
fi

# Install system dependencies
print_header "Installing System Dependencies"
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev git curl

# Install Python dependencies
print_header "Installing Python Dependencies"
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create directories
print_header "Creating Directories"
sudo mkdir -p $INSTALL_DIR
sudo mkdir -p $INSTALL_DIR/media/photos
sudo mkdir -p $INSTALL_DIR/media/videos
sudo mkdir -p /var/log/jetbot

# Copy files
print_header "Copying Files"
sudo cp -r . $INSTALL_DIR/
sudo chown -R $USER:$USER $INSTALL_DIR
sudo chown -R $USER:$USER /var/log/jetbot

# Make scripts executable
chmod +x $INSTALL_DIR/jetbot_launcher.py
chmod +x $INSTALL_DIR/start_api_server.py

# Install systemd service
print_header "Installing Systemd Service"
sudo cp jetbot.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jetbot.service

print_header "DEPLOYMENT COMPLETE"

IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              JETBOT OS READY TO USE                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${CYAN}Service Control:${NC}"
echo "  Start:   sudo systemctl start jetbot"
echo "  Stop:    sudo systemctl stop jetbot"
echo "  Status:  sudo systemctl status jetbot"
echo "  Logs:    sudo journalctl -u jetbot -f"

echo ""
echo -e "${CYAN}API Endpoints:${NC}"
echo "  REST API:       http://$IP_ADDR:5000/api"
echo "  WebSocket:      ws://$IP_ADDR:8765"
echo "  Camera Stream:  http://$IP_ADDR:5001/stream"

echo ""
echo -e "${CYAN}Test Commands:${NC}"
echo "  Health check:   curl http://$IP_ADDR:5000/api/health"
echo "  Get status:     curl http://$IP_ADDR:5000/api/status"

echo ""
read -p "Start Jetbot service now? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    sudo systemctl start jetbot
    sleep 2
    sudo systemctl status jetbot --no-pager
fi

echo ""
print_success "Setup complete! Jetbot OS is running."
