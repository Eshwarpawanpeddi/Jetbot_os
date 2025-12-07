#!/bin/bash
# ============================================================================
# QUICK START SCRIPT - Automated Setup & Launch
# ============================================================================
# Usage: bash quickstart.sh
# ============================================================================

set -e  # Exit on error

echo "=========================================="
echo "🤖 AI PET ROBOT - QUICK START"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/robot_env"
PYTHON_CMD="python3"
PIP_CMD="pip3"

# ============================================================================
# FUNCTIONS
# ============================================================================

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_python() {
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 not found"
        exit 1
    fi
    print_status "Python 3 found: $($PYTHON_CMD --version)"
}

check_pip() {
    if ! command -v $PIP_CMD &> /dev/null; then
        print_error "pip not found"
        exit 1
    fi
    print_status "pip found"
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv $VENV_DIR
        print_status "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    source $VENV_DIR/bin/activate
    print_status "Virtual environment activated"
}

install_dependencies() {
    echo "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Dependencies installed"
}

check_config() {
    if [ ! -f "$SCRIPT_DIR/config.json" ]; then
        print_warning "config.json not found, creating from template..."
        cp "$SCRIPT_DIR/config.json.template" "$SCRIPT_DIR/config.json" 2>/dev/null || {
            print_warning "Please edit config.json with your IP addresses"
        }
    else
        print_status "config.json found"
    fi
}

check_bluetooth() {
    if command -v bluetoothctl &> /dev/null; then
        print_status "Bluetooth tools found"
        
        echo ""
        echo "Paired Bluetooth devices:"
        bluetoothctl paired-devices || print_warning "No paired devices found"
        
        echo ""
        read -p "Enter Bluetooth device MAC (or press Enter to skip): " mac_address
        if [ ! -z "$mac_address" ]; then
            sudo rfcomm bind /dev/rfcomm0 $mac_address 1
            print_status "RFCOMM bound to /dev/rfcomm0"
        fi
    else
        print_warning "Bluetooth tools not found. Install with: sudo apt install bluez"
    fi
}

check_camera() {
    if command -v v4l2-ctl &> /dev/null; then
        echo ""
        echo "Detected cameras:"
        v4l2-ctl --list-devices
        print_status "Camera detection complete"
    else
        print_warning "v4l2-utils not found. Install with: sudo apt install v4l-utils"
    fi
}

start_server() {
    echo ""
    echo "=========================================="
    echo "Starting AI PET ROBOT SERVER"
    echo "=========================================="
    echo ""
    echo "Configuration:"
    echo "  Server: http://0.0.0.0:5000"
    echo "  WebSocket: ws://0.0.0.0:5000"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy Jetson Nano code (jetson_display.py)"
    echo "  2. Upload ESP32 code (esp32_motor_control.ino)"
    echo "  3. Start mobile app (mobile_app.jsx)"
    echo "  4. Open http://localhost:5000 to monitor"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    cd "$SCRIPT_DIR"
    source $VENV_DIR/bin/activate
    $PYTHON_CMD server_main.py
}

# ============================================================================
# MAIN FLOW
# ============================================================================

main() {
    # Check system requirements
    echo "Checking system requirements..."
    check_python
    check_pip
    echo ""
    
    # Setup Python environment
    echo "Setting up Python environment..."
    setup_venv
    echo ""
    
    # Install dependencies
    install_dependencies
    echo ""
    
    # Check configuration
    echo "Checking configuration..."
    check_config
    echo ""
    
    # Optional: Check Bluetooth
    read -p "Setup Bluetooth? (y/n): " setup_bt
    if [[ $setup_bt == "y" ]]; then
        check_bluetooth
        echo ""
    fi
    
    # Optional: Check camera
    read -p "Check camera? (y/n): " check_cam
    if [[ $check_cam == "y" ]]; then
        check_camera
        echo ""
    fi
    
    # Start server
    read -p "Start server now? (y/n): " start_now
    if [[ $start_now == "y" ]]; then
        start_server
    else
        echo ""
        echo "To start server later, run:"
        echo "  source robot_env/bin/activate"
        echo "  python3 server_main.py"
    fi
}

# Run main function
main