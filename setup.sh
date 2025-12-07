#!/bin/bash
#
# JetBot OS - Setup & Deployment Script
# Run this script on Jetson Nano to set up and deploy JetBot OS
#

set -e  # Exit on any error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         JetBot OS - Setup & Deployment Script              ║"
echo "║                   Version 2.0.0                            ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ============================================================================
# PHASE 1: VALIDATION
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 1: VALIDATION${NC}"
echo "═══════════════════════════════════════════════════════════"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed"
    exit 1
fi
print_success "Git found"

# Check if in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_warning "Not in a git repository. Some operations may be skipped."
fi

# ============================================================================
# PHASE 2: SETUP
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 2: SETUP${NC}"
echo "═══════════════════════════════════════════════════════════"

# Create necessary directories
print_info "Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p backups
print_success "Directories created"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_info "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env with your configuration"
    else
        print_error ".env.example not found"
    fi
else
    print_warning ".env already exists, skipping creation"
fi

# ============================================================================
# PHASE 3: VALIDATION
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 3: FILE VALIDATION${NC}"
echo "═══════════════════════════════════════════════════════════"

# Check required files
required_files=("server_main.py" "esp12e_controller.py" "jetson_display.py" "requirements.txt" "config.json")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "$file found"
    else
        print_error "$file NOT found"
        exit 1
    fi
done

# Check Python syntax
print_info "Checking Python syntax..."
python3 -m py_compile server_main.py && print_success "server_main.py syntax OK" || exit 1
python3 -m py_compile esp12e_controller.py && print_success "esp12e_controller.py syntax OK" || exit 1
python3 -m py_compile jetson_display.py && print_success "jetson_display.py syntax OK" || exit 1

# Check JSON syntax
print_info "Checking config.json syntax..."
python3 -c "import json; json.load(open('config.json'))" && print_success "config.json is valid JSON" || exit 1

# ============================================================================
# PHASE 4: DEPENDENCIES
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 4: INSTALLING DEPENDENCIES${NC}"
echo "═══════════════════════════════════════════════════════════"

print_info "Installing Python dependencies..."
print_warning "This may take a few minutes..."

pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r requirements.txt

print_success "Dependencies installed"

# ============================================================================
# PHASE 5: SYSTEMD SERVICES (optional, requires sudo)
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 5: SYSTEMD SERVICES${NC}"
echo "═══════════════════════════════════════════════════════════"

read -p "Create systemd services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Create jetbot-server service
    print_info "Creating jetbot-server service..."
    
    SERVICE_CONTENT="[Unit]
Description=JetBot OS Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
Environment=\"PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin\"
EnvironmentFile=$SCRIPT_DIR/.env
ExecStart=$(which python3) $SCRIPT_DIR/server_main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target"
    
    echo "$SERVICE_CONTENT" | sudo tee /etc/systemd/system/jetbot-server.service > /dev/null
    print_success "jetbot-server service created"
    
    # Create jetbot-display service
    print_info "Creating jetbot-display service..."
    
    SERVICE_CONTENT="[Unit]
Description=JetBot Display Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
Environment=\"PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin\"
Environment=\"DISPLAY=:0\"
EnvironmentFile=$SCRIPT_DIR/.env
ExecStart=$(which python3) $SCRIPT_DIR/jetson_display.py
Restart=always

[Install]
WantedBy=multi-user.target"
    
    echo "$SERVICE_CONTENT" | sudo tee /etc/systemd/system/jetbot-display.service > /dev/null
    print_success "jetbot-display service created"
    
    # Reload systemd
    print_info "Reloading systemd daemon..."
    sudo systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    # Enable services
    print_info "Enabling services..."
    sudo systemctl enable jetbot-server
    sudo systemctl enable jetbot-display
    print_success "Services enabled"
    
    # Ask to start
    read -p "Start services now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Starting services..."
        sudo systemctl start jetbot-server
        sudo systemctl start jetbot-display
        print_success "Services started"
        
        # Show status
        echo ""
        echo "Service Status:"
        sudo systemctl status jetbot-server --no-pager
        sudo systemctl status jetbot-display --no-pager
    fi
else
    print_warning "Systemd services not created"
fi

# ============================================================================
# PHASE 6: CLEANUP
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 6: CLEANUP${NC}"
echo "═══════════════════════════════════════════════════════════"

# Remove old files
print_info "Removing unnecessary files..."
[ -f "esp32_motor_control.ino" ] && rm -f esp32_motor_control.ino && print_success "Removed esp32_motor_control.ino"
[ -f "enhanced_face_system.py" ] && rm -f enhanced_face_system.py && print_success "Removed enhanced_face_system.py"
[ -f "ai_enhancement_module.py" ] && rm -f ai_enhancement_module.py && print_success "Removed ai_enhancement_module.py"

# Create backup
print_info "Creating backup..."
BACKUP_FILE="backups/jetbot_backup_$(date +%s).tar.gz"
tar -czf "$BACKUP_FILE" server_main.py esp12e_controller.py jetson_display.py requirements.txt config.json .env 2>/dev/null || true
print_success "Backup created: $BACKUP_FILE"

# ============================================================================
# PHASE 7: TESTING
# ============================================================================

echo ""
echo -e "${BLUE}PHASE 7: TESTING${NC}"
echo "═══════════════════════════════════════════════════════════"

print_info "Testing imports..."
python3 << 'EOF'
try:
    from esp12e_controller import ESP12EController
    print("✓ ESP12E controller imports OK")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)
EOF

print_success "All imports successful"

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              SETUP COMPLETED SUCCESSFULLY!                 ║"
echo "╚════════════════════════════════════════════════════════════╝"

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Edit .env with your configuration:"
echo "   nano .env"
echo ""
echo "2. Start the server:"
echo "   python3 server_main.py"
echo ""
echo "3. Or use systemd services:"
echo "   sudo systemctl start jetbot-server"
echo "   sudo systemctl start jetbot-display"
echo ""
echo "4. View logs:"
echo "   tail -f logs/jetbot_server.log"
echo ""
echo "5. Test health check:"
echo "   curl http://localhost:5000/health"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "- Server API: Run 'curl http://localhost:5000/api/status'"
echo "- Logs: Check logs/jetbot_server.log and logs/jetson_display.log"
echo "- Config: Edit config.json for advanced settings"
echo ""
print_success "Setup complete!"
