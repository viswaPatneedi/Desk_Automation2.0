#!/bin/bash
# ============================================================================
# LRQA Middleware Docker Deployment Script for Raspberry Pi 4
# Purpose: Complete installation & deployment of encrypted Docker image
# Run with: bash rpi4-deploy.sh
# ============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE_NAME="lrqa-middleware"
DOCKER_IMAGE_TAG="latest"
CONTAINER_NAME="lrqa-middleware"
INSTALL_DIR="/opt/middleware"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_DIR="${INSTALL_DIR}/logs"
USB_MOUNT_POINT="/media/usb"
DOCKER_IMAGE_FILE="lrqa-middleware-latest.tar"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_step() {
    echo -e "\n${CYAN}[STEP] $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

print_header "LRQA Middleware Docker Deployment for R-Pi 4"

print_step "1. Pre-flight checks"

# Check if running on R-Pi 4
if ! grep -q "BCM2711" /proc/cpuinfo 2>/dev/null && ! grep -q "arm64" /proc/cpuinfo 2>/dev/null; then
    print_info "Note: Not detected as R-Pi 4, but proceeding (may be emulator or compatible system)"
fi

# Check for required tools
print_info "Checking for required tools..."
check_command "sudo" || true  # Might not be needed on some systems
check_command "curl" || { print_error "curl not found. Run: sudo apt-get install curl"; exit 1; }

print_success "Basic tools available"

# ============================================================================
# SYSTEM UPDATES
# ============================================================================

print_step "2. Update system packages"
print_info "Running apt-get update and upgrade (this may take 10-15 minutes)..."
sudo apt-get update
sudo apt-get upgrade -y

print_success "System packages updated"

# ============================================================================
# DOCKER INSTALLATION
# ============================================================================

print_step "3. Install Docker Engine"

if check_command "docker"; then
    print_success "Docker already installed: $(docker --version)"
else
    print_info "Installing Docker for R-Pi 4..."
    
    # Official Docker installation for Raspberry Pi
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    echo \
        "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    print_success "Docker installed: $(docker --version || echo 'version check pending')"
fi

# ============================================================================
# DOCKER SETUP
# ============================================================================

print_step "4. Configure Docker for R-Pi 4"

# Add current user to docker group
if ! groups $USER | grep -q docker; then
    print_info "Adding user to docker group..."
    sudo usermod -aG docker $USER
    print_info "You may need to log out and back in, or run: newgrp docker"
fi

# Create directory for Docker images
sudo mkdir -p /var/lib/docker/images
print_success "Docker directories created"

# ============================================================================
# LOAD DOCKER IMAGE FROM USB
# ============================================================================

print_step "5. Load Docker image from USB"

# Get the script's directory (where it's being run from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
print_info "Script location: $SCRIPT_DIR"

# Start with script's own directory
USB_MOUNT_POINT="$SCRIPT_DIR"
FOUND_IMAGE=""

# Define all possible Docker image filenames
POSSIBLE_IMAGES=(
    "lrqa-middleware-latest.tar"
    "lrqa-middleware-encrypted.tar.gz"
    "lrqa-middleware.tar"
)

# First, check in script's own directory
print_info "Checking script directory for Docker image..."
for img in "${POSSIBLE_IMAGES[@]}"; do
    if [ -f "$USB_MOUNT_POINT/$img" ]; then
        FOUND_IMAGE="$img"
        print_success "Found image in script directory: $FOUND_IMAGE"
        break
    fi
done

# If not found, search common USB mount points
if [ -z "$FOUND_IMAGE" ]; then
    print_info "Image not found in script directory. Searching common USB locations..."
    
    SEARCH_PATHS=(
        "/media/viswa-pi4/VISWA"
        "/media/$USER/VISWA"
        "/media/$USER/usb"
        "/media/usb"
        "/mnt/usb"
        "/mnt/VISWA"
    )
    
    for search_path in "${SEARCH_PATHS[@]}"; do
        if [ -d "$search_path" ]; then
            for img in "${POSSIBLE_IMAGES[@]}"; do
                if [ -f "$search_path/$img" ]; then
                    USB_MOUNT_POINT="$search_path"
                    FOUND_IMAGE="$img"
                    print_success "Found USB at: $USB_MOUNT_POINT"
                    print_success "Found image: $FOUND_IMAGE"
                    break 2
                fi
            done
        fi
    done
fi

# If still not found, exit with helpful message
if [ -z "$FOUND_IMAGE" ]; then
    print_error "Docker image not found!"
    print_info ""
    print_info "Expected location: $SCRIPT_DIR"
    print_info "Expected filenames:"
    for img in "${POSSIBLE_IMAGES[@]}"; do
        echo "  - $img"
    done
    print_info ""
    print_info "Files available in $USB_MOUNT_POINT:"
    ls -lh "$USB_MOUNT_POINT/" 2>/dev/null || echo "  (directory not accessible)"
    print_info ""
    print_info "Please verify:"
    print_info "  1. You're running this script FROM the USB directory"
    print_info "  2. The Docker image file is on the USB"
    print_info "  3. USB is properly mounted"
    exit 1
fi

# Load the Docker image
print_info "Loading Docker image: $FOUND_IMAGE"
print_info "This may take 2-5 minutes depending on USB speed..."
print_info ""

if sudo docker load -i "$USB_MOUNT_POINT/$FOUND_IMAGE"; then
    print_success "Docker image loaded successfully"
else
    print_error "Failed to load Docker image"
    print_info "File: $USB_MOUNT_POINT/$FOUND_IMAGE"
    exit 1
fi

# ============================================================================
# APPLICATION DIRECTORY SETUP
# ============================================================================

print_step "6. Create application directories"

print_info "Creating installation directory: $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR/iteration_logs"
sudo mkdir -p "$INSTALL_DIR/screenshots"
sudo mkdir -p "$INSTALL_DIR/device_logs"
sudo mkdir -p "$LOG_DIR"

# Set permissions
sudo chown -R $USER:$USER "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"/{iteration_logs,screenshots,device_logs,logs}

print_success "Directories created and configured"

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

print_step "7. Configure environment variables"

# Create .env file
ENV_FILE="$INSTALL_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    print_info "Creating .env file..."
    
    cat > "$ENV_FILE" << 'EOF'
# Flask Configuration
FLASK_ENV=production
FLASK_APP=app.py

# Email Configuration (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Optional: PyArmor Debug (set to 1 for debugging)
PYARMOR_DEBUG=0

# Application Port
FLASK_PORT=11078
EOF
    
    print_success ".env file created"
    print_info "Please update $ENV_FILE with your email credentials"
else
    print_info ".env already exists"
fi

# ============================================================================
# DOCKER CONTAINER STARTUP
# ============================================================================

print_step "8. Start Docker container"

# Stop any existing container
if sudo docker ps -a | grep -q "$CONTAINER_NAME"; then
    print_info "Stopping existing container..."
    sudo docker stop "$CONTAINER_NAME" 2>/dev/null || true
    sudo docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Start new container
print_info "Starting Docker container: $CONTAINER_NAME"
sudo docker run -d \
    --name "$CONTAINER_NAME" \
    --restart=unless-stopped \
    -p 11078:11078 \
    -v "$INSTALL_DIR/iteration_logs:/app/iteration_logs:rw" \
    -v "$INSTALL_DIR/screenshots:/app/screenshots:rw" \
    -v "$INSTALL_DIR/device_logs:/app/device_logs:rw" \
    --env-file "$ENV_FILE" \
    -e PYTHONUNBUFFERED=1 \
    -e PYTHONDONTWRITEBYTECODE=1 \
    --memory=1g \
    --cpus=2 \
    "$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG"

sleep 5

# Check if container started successfully
if sudo docker ps | grep -q "$CONTAINER_NAME"; then
    print_success "Container started successfully"
    CONTAINER_ID=$(sudo docker ps -q -f name="$CONTAINER_NAME" | head -c 12)
    print_info "Container ID: $CONTAINER_ID"
else
    print_error "Container failed to start"
    print_info "Check logs with: sudo docker logs $CONTAINER_NAME"
    exit 1
fi

# ============================================================================
# VERIFY APPLICATION
# ============================================================================

print_step "9. Verify application"

print_info "Waiting for application to initialize (15 seconds)..."
sleep 15

# Check container logs for errors
print_info "Checking application logs..."
LOGS=$(sudo docker logs "$CONTAINER_NAME" 2>&1 | tail -20)

if echo "$LOGS" | grep -q "Running on"; then
    print_success "Flask application is running"
else
    print_info "Application still initializing, check with: sudo docker logs $CONTAINER_NAME"
fi

# Test health endpoint
print_info "Testing health endpoint..."
if curl -s http://localhost:11078/health 2>/dev/null | grep -q . ; then
    print_success "Health endpoint responsive"
else
    print_info "Health check pending (application may still be booting)"
fi

# ============================================================================
# SETUP AUTO-START
# ============================================================================

print_step "10. Configure auto-start on boot"

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/lrqa-middleware.service"

print_info "Creating systemd service file..."
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=LRQA Middleware Docker Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=unless-stopped
RestartSec=5
ExecStart=/usr/bin/docker start -a $CONTAINER_NAME
ExecStop=/usr/bin/docker stop $CONTAINER_NAME
User=root

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable lrqa-middleware.service

print_success "Auto-start configured"

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header "✓ DEPLOYMENT COMPLETE"

echo ""
echo -e "${GREEN}Installation Summary:${NC}"
echo "  Container Name: $CONTAINER_NAME"
echo "  Image: $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG"
echo "  Application URL: http://localhost:11078"
echo "  Data Directory: $INSTALL_DIR"
echo "  Environment File: $ENV_FILE"
echo ""

echo -e "${YELLOW}Quick Management Commands:${NC}"
echo "  View logs:     sudo docker logs -f $CONTAINER_NAME"
echo "  Stop:          sudo docker stop $CONTAINER_NAME"
echo "  Start:         sudo docker start $CONTAINER_NAME"
echo "  Restart:       sudo docker restart $CONTAINER_NAME"
echo "  Remove:        sudo docker rm $CONTAINER_NAME"
echo "  Status:        sudo systemctl status lrqa-middleware"
echo ""

echo -e "${CYAN}Important Next Steps:${NC}"
echo "  1. Edit environment file: nano $ENV_FILE"
echo "  2. Add your Gmail credentials"
echo "  3. Access application: http://<R-Pi-IP>:11078"
echo "  4. Container will auto-start on reboot"
echo ""

echo -e "${BLUE}Troubleshooting:${NC}"
echo "  • Check logs: sudo docker logs $CONTAINER_NAME"
echo "  • Verify container: sudo docker ps"
echo "  • Test connectivity: curl http://localhost:11078/health"
echo "  • View service status: sudo systemctl status lrqa-middleware"
echo ""

print_success "LRQA Middleware is ready to use!"
echo ""
