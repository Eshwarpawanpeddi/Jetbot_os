#!/bin/bash
#==============================================================================
# ROS INSTALLATION SCRIPT FOR UBUNTU (Development PC)
# Installs ROS, navigation stack (without Jetson-specific packages)
#==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${CYAN}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Detect Ubuntu version
. /etc/os-release
OS_VERSION=$VERSION_ID

if [ "$OS_VERSION" = "18.04" ]; then
    ROS_DISTRO="melodic"
elif [ "$OS_VERSION" = "20.04" ]; then
    ROS_DISTRO="noetic"
else
    print_warning "Ubuntu $OS_VERSION detected. Trying with noetic..."
    ROS_DISTRO="noetic"
fi

print_info "Installing ROS $ROS_DISTRO for Ubuntu $OS_VERSION"

# Add ROS repository
print_info "Adding ROS repository..."
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
sudo apt install -y curl
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -

# Update
print_info "Updating package lists..."
sudo apt-get update

# Install ROS Desktop Full
print_info "Installing ROS (this takes 15-30 minutes)..."
sudo apt-get install -y ros-$ROS_DISTRO-desktop-full

# Install build tools
print_info "Installing build tools..."
sudo apt-get install -y \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    build-essential \
    python3-catkin-tools

# Initialize rosdep
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    print_info "Initializing rosdep..."
    sudo rosdep init
fi
rosdep update

# Setup environment
print_info "Setting up environment..."
if ! grep -q "source /opt/ros/$ROS_DISTRO/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> ~/.bashrc
fi

source /opt/ros/$ROS_DISTRO/setup.bash

# Install navigation packages
print_info "Installing navigation stack..."
sudo apt-get install -y \
    ros-$ROS_DISTRO-navigation \
    ros-$ROS_DISTRO-gmapping \
    ros-$ROS_DISTRO-move-base \
    ros-$ROS_DISTRO-amcl

# Install vision packages
print_info "Installing vision packages..."
sudo apt-get install -y \
    ros-$ROS_DISTRO-cv-bridge \
    ros-$ROS_DISTRO-image-transport \
    ros-$ROS_DISTRO-usb-cam

# Install simulation
print_info "Installing Gazebo simulation..."
sudo apt-get install -y \
    ros-$ROS_DISTRO-gazebo-ros \
    ros-$ROS_DISTRO-gazebo-ros-pkgs

# Create workspace
print_info "Creating catkin workspace..."
mkdir -p ~/jetbot_ws/src
cd ~/jetbot_ws
catkin_make

# Add workspace to bashrc
if ! grep -q "source ~/jetbot_ws/devel/setup.bash" ~/.bashrc; then
    echo "source ~/jetbot_ws/devel/setup.bash" >> ~/.bashrc
fi

# Test
print_info "Testing installation..."
source /opt/ros/$ROS_DISTRO/setup.bash

echo ""
print_success "ROS $ROS_DISTRO installed successfully!"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo "  1. Open new terminal (or run: source ~/.bashrc)"
echo "  2. Start ROS: roscore"
echo "  3. Test: rostopic list"
echo ""
echo -e "${CYAN}Workspace:${NC} ~/jetbot_ws"
echo ""
