#!/bin/bash

# ============================================================================
# RDK-E Middleware QA Dashboard - Complete RPi 4 Setup & Installation
# ============================================================================
# This script will:
# 1. Check system requirements
# 2. Install Docker & Docker Compose (if needed)
# 3. Build the clean Docker image (without execution data)
# 4. Configure and start the application
# 5. Verify healthy startup
# ============================================================================

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="rdk-middleware-dashboard"
IMAGE_NAME="rdk-middleware-dashboard:rpi4-clean"
CONTAINER_NAME="rdk-middleware-dashboard"
COMPOSE_FILE="docker-compose.rpi.clean.yml"
DOCKERFILE="Dockerfile.rpi.clean"
APP_PORT="11078"

# ============================================================================
# COLORS & FORMATTING
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

BOLD='\033[1m'

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_header() {
    echo ""
    echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC} $1"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_step() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}[STEP]${NC} $1"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 is installed"
        return 0
    else
        log_error "$1 is NOT installed"
        return 1
    fi
}

# ============================================================================
# MAIN SCRIPT START
# ============================================================================

clear

log_header "RDK-E Middleware QA Dashboard - RPi 4 Setup"

echo -e "${BOLD}System Information:${NC}"
echo "  Script Location: $SCRIPT_DIR"
echo "  Project Name: $PROJECT_NAME"
echo "  Docker Image: $IMAGE_NAME"
echo "  Container Name: $CONTAINER_NAME"
echo "  Web UI Port: $APP_PORT"
echo ""

# ============================================================================
# STEP 1: System Requirements Check
# ============================================================================

log_step "Checking System Requirements"

log_info "Detecting Raspberry Pi model..."
if [ -f /proc/device-tree/model ]; then
    RPI_MODEL=$(cat /proc/device-tree/model)
    log_success "Detected: $RPI_MODEL"
else
    log_warning "Could not detect RPi model"
fi

log_info "Checking CPU cores..."
CPU_CORES=$(nproc)
log_success "CPU Cores: $CPU_CORES"

log_info "Checking available RAM..."
RAM_GB=$(free -g | awk 'NR==2 {print $2}')
log_success "RAM: ${RAM_GB}GB"

if [ "$RAM_GB" -lt 4 ]; then
    log_warning "Minimum recommended RAM is 4GB. Performance may be limited with ${RAM_GB}GB."
fi

log_info "Checking disk space..."
DISK_AVAILABLE=$(df /app 2>/dev/null | awk 'NR==2 {printf "%.1f", $4/1024/1024}')
if command -v awk &> /dev/null; then
    log_success "Available Disk Space: ${DISK_AVAILABLE}GB"
fi

# ============================================================================
# STEP 2: Check Dependencies
# ============================================================================

log_step "Checking Docker Installation"

if ! check_command docker; then
    log_warning "Docker not found. Installing Docker for Raspberry Pi..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker "$USER"
    log_success "Docker installed. Please log out and back in for group changes to take effect."
fi

DOCKER_VERSION=$(docker --version)
log_success "Docker Version: $DOCKER_VERSION"

# ============================================================================
# STEP 3: Check Docker Compose
# ============================================================================

log_step "Checking Docker Compose Installation"

if ! check_command docker-compose; then
    log_warning "Docker Compose not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
    log_success "Docker Compose installed"
fi

COMPOSE_VERSION=$(docker-compose --version)
log_success "Docker Compose Version: $COMPOSE_VERSION"

# ============================================================================
# STEP 4: Verify Required Files
# ============================================================================

log_step "Verifying Project Files"

REQUIRED_FILES=(
    "$SCRIPT_DIR/app.py"
    "$SCRIPT_DIR/requirements.txt"
    "$SCRIPT_DIR/$DOCKERFILE"
    "$SCRIPT_DIR/$COMPOSE_FILE"
    "$SCRIPT_DIR/docker-entrypoint.sh"
    "$SCRIPT_DIR/log_patterns.json"
)

ALL_FILES_PRESENT=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "Found: $(basename $file)"
    else
        log_error "Missing: $file"
        ALL_FILES_PRESENT=false
    fi
done

if [ "$ALL_FILES_PRESENT" = false ]; then
    log_error "Some required files are missing. Please ensure all files are in place."
    exit 1
fi

# ============================================================================
# STEP 5: Cleanup Old Container (if exists)
# ============================================================================

log_step "Checking for Existing Container"

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_warning "Found existing container: $CONTAINER_NAME"
    read -p "Do you want to remove it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Stopping container..."
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        log_success "Container removed"
    fi
fi

# ============================================================================
# STEP 6: Build Docker Image
# ============================================================================

log_step "Building Docker Image"

log_info "Building image: $IMAGE_NAME"
log_info "This may take 5-10 minutes on Raspberry Pi 4..."
echo ""

cd "$SCRIPT_DIR"

docker build \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME" \
    --no-cache \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    log_success "Docker image built successfully"
    
    # Show image info
    IMAGE_SIZE=$(docker images "$IMAGE_NAME" --format "{{.Size}}")
    log_success "Image Size: $IMAGE_SIZE"
else
    log_error "Docker image build failed"
    exit 1
fi

# ============================================================================
# STEP 7: Verify Docker Image
# ============================================================================

log_step "Verifying Docker Image"

if docker inspect "$IMAGE_NAME" &> /dev/null; then
    log_success "Docker image verified successfully"
else
    log_error "Docker image verification failed"
    exit 1
fi

# ============================================================================
# STEP 8: Show Docker Compose Configuration
# ============================================================================

log_step "Docker Compose Configuration"

log_info "Services defined in $COMPOSE_FILE:"
docker-compose -f "$COMPOSE_FILE" config --services

# ============================================================================
# STEP 9: Start Application
# ============================================================================

log_step "Starting Application"

log_info "Starting application with Docker Compose..."
docker-compose -f "$COMPOSE_FILE" up -d

if [ $? -eq 0 ]; then
    log_success "Application started successfully"
else
    log_error "Failed to start application"
    exit 1
fi

# ============================================================================
# STEP 10: Wait for Startup & Verification
# ============================================================================

log_step "Verifying Application Startup"

log_info "Waiting for application to initialize (30 seconds)..."

# Check container status
sleep 5
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_success "Container is running"
else
    log_error "Container is not running"
    docker logs $CONTAINER_NAME
    exit 1
fi

# Wait for HTTP response
MAX_ATTEMPTS=30
ATTEMPT=0
HEALTH_CHECK_PASSED=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:$APP_PORT/ &> /dev/null; then
        HEALTH_CHECK_PASSED=true
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -ne "\r  Checking... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 1
done

echo ""

if [ "$HEALTH_CHECK_PASSED" = true ]; then
    log_success "Application is responding to HTTP requests"
else
    log_warning "Application startup may still be initializing..."
    log_info "Check container logs: docker logs -f $CONTAINER_NAME"
fi

# ============================================================================
# STEP 11: Show Startup Summary
# ============================================================================

log_header "✅ RDK-E Middleware QA Dashboard - Setup Complete!"

echo -e "${BOLD}Application Information:${NC}"
echo "  Container Name: $CONTAINER_NAME"
echo "  Image: $IMAGE_NAME"
echo "  Status: $(docker inspect -f '{{.State.Status}}' $CONTAINER_NAME 2>/dev/null || echo 'unknown')"
echo ""

# Get local IP for easy access
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo -e "${BOLD}Access the Dashboard:${NC}"
echo "  URL: ${GREEN}http://$LOCAL_IP:$APP_PORT${NC}"
echo "  Hostname: ${GREEN}http://$(hostname):$APP_PORT${NC}"
echo ""

echo -e "${BOLD}Container Management:${NC}"
echo "  View logs: ${CYAN}docker logs -f $CONTAINER_NAME${NC}"
echo "  Stop app: ${CYAN}docker stop $CONTAINER_NAME${NC}"
echo "  Start app: ${CYAN}docker start $CONTAINER_NAME${NC}"
echo "  Restart app: ${CYAN}docker restart $CONTAINER_NAME${NC}"
echo "  Remove app: ${CYAN}docker rm -f $CONTAINER_NAME${NC}"
echo ""

echo -e "${BOLD}Docker Compose Commands:${NC}"
echo "  Stop all services: ${CYAN}docker-compose -f $COMPOSE_FILE stop${NC}"
echo "  Start all services: ${CYAN}docker-compose -f $COMPOSE_FILE start${NC}"
echo "  View logs: ${CYAN}docker-compose -f $COMPOSE_FILE logs -f${NC}"
echo "  Restart services: ${CYAN}docker-compose -f $COMPOSE_FILE restart${NC}"
echo ""

echo -e "${BOLD}Important Notes:${NC}"
echo "  • Application data is stored in Docker volumes"
echo "  • All execution data (logs, screenshots) are persisted"
echo "  • Configuration files can be edited on the host"
echo "  • For production: Set SECRET_KEY environment variable"
echo "  • For email notifications: Set SMTP credentials in environment"
echo ""

echo -e "${BOLD}System Resources:${NC}"
docker stats --no-stream $CONTAINER_NAME

echo ""
log_success "Setup Complete! Your application is ready to use."
echo ""
