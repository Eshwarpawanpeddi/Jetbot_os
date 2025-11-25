#!/bin/bash
# Jetbot Launcher Installation Script

set -e

echo "======================================="
echo "Jetbot Launcher Installation"
echo "======================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/jetbot"
SERVICE_FILE="jetbot.service"
USER="jetbot"
GROUP="jetbot"

# Create jetbot user if it doesn't exist
if ! id "$USER" &>/dev/null; then
    echo "Creating user: $USER"
    addgroup --system $GROUP
    adduser --system --no-create-home --disabled-login --disabled-password --ingroup $GROUP $USER
else
    echo "User $USER already exists"
fi

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p $INSTALL_DIR
mkdir -p $INSTALL_DIR/modules
mkdir -p $INSTALL_DIR/config
mkdir -p /var/log/jetbot

# Copy files
echo "Copying launcher files..."
cp jetbot_launcher.py $INSTALL_DIR/
cp config/launcher_config.yaml $INSTALL_DIR/config/
chmod +x $INSTALL_DIR/jetbot_launcher.py

# Set permissions
echo "Setting permissions..."
chown -R $USER:$GROUP $INSTALL_DIR
chown -R $USER:$GROUP /var/log/jetbot
chmod 755 $INSTALL_DIR/jetbot_launcher.py

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install pyyaml

# Install systemd service
echo "Installing systemd service..."
cp $SERVICE_FILE /lib/systemd/system/
chmod 644 /lib/systemd/system/$SERVICE_FILE

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling jetbot service..."
systemctl enable jetbot.service

echo ""
echo "======================================="
echo "Installation Complete!"
echo "======================================="
echo ""
echo "Next steps:"
echo "1. Add your module scripts to: $INSTALL_DIR/modules/"
echo "2. Edit configuration: $INSTALL_DIR/config/launcher_config.yaml"
echo "3. Start the service: sudo systemctl start jetbot"
echo "4. Check status: sudo systemctl status jetbot"
echo "5. View logs: sudo journalctl -u jetbot -f"
echo ""
echo "To make service start on boot (already enabled):"
echo "  sudo systemctl enable jetbot"
echo ""
echo "To disable autostart:"
echo "  sudo systemctl disable jetbot"

# Create media directories
echo "Creating media directories..."
mkdir -p /opt/jetbot/media/photos
mkdir -p /opt/jetbot/media/videos
chown -R $USER:$GROUP /opt/jetbot/media

