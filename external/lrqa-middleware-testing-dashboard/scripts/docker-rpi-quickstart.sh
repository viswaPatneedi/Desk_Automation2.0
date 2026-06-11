#!/bin/bash

# Quick Start Script for RDK-E Middleware Testing Dashboard on Raspberry Pi
# This script automates the Docker setup process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    print_header "Checking Docker Installation"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Run: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
        exit 1
    fi
    
    print_success "Docker found: $(docker --version)"
    
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose not found. Installing..."
        sudo apt-get update
        sudo apt-get install -y docker-compose-plugin
    fi
    
    print_success "Docker Compose found: $(docker compose version)"
}

# Create .env file if it doesn't exist
create_env() {
    print_header "Configuration Setup"
    
    if [ -f .env ]; then
        print_warning ".env file already exists. Skipping..."
        return
    fi
    
    echo -e "${YELLOW}Creating .env file for email configuration...${NC}"
    
    read -p "Enter SMTP Host (default: smtp.gmail.com): " SMTP_HOST
    SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
    
    read -p "Enter SMTP Port (default: 587): " SMTP_PORT
    SMTP_PORT=${SMTP_PORT:-587}
    
    read -p "Enter Sender Email: " SENDER_EMAIL
    
    read -sp "Enter Sender Password (app password for Gmail): " SENDER_PASSWORD
    echo
    
    read -p "Enter Secret Key (or press Enter for auto-generated): " SECRET_KEY
    SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
    
    # Create .env file
    cat > .env << EOF
# Email Configuration
SMTP_HOST=$SMTP_HOST
SMTP_PORT=$SMTP_PORT
SENDER_EMAIL=$SENDER_EMAIL
SENDER_PASSWORD=$SENDER_PASSWORD

# Application Settings
SECRET_KEY=$SECRET_KEY

# Performance Tuning (automatic based on Pi model)
WORKERS=2
TIMEOUT=300
EOF
    
    print_success ".env file created"
}

# Detect Pi model and suggest worker count
detect_pi_model() {
    print_header "Raspberry Pi Model Detection"
    
    if [ -f /sys/firmware/devicetree/base/model ]; then
        PI_MODEL=$(cat /sys/firmware/devicetree/base/model)
        print_success "Detected: $PI_MODEL"
        
        if [[ "$PI_MODEL" == *"Pi 5"* ]]; then
            SUGGESTED_WORKERS=4
            SUGGESTED_MEMORY="4G"
        elif [[ "$PI_MODEL" == *"Pi 4"* ]]; then
            SUGGESTED_WORKERS=2
            SUGGESTED_MEMORY="2G"
        else
            SUGGESTED_WORKERS=1
            SUGGESTED_MEMORY="1G"
        fi
        
        echo "Suggested WORKERS=$SUGGESTED_WORKERS"
        echo "Suggested Memory Limit=$SUGGESTED_MEMORY"
        
        read -p "Update docker-compose.rpi.yml with these values? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sed -i "s/WORKERS=2/WORKERS=$SUGGESTED_WORKERS/" .env
            sed -i "s/memory: 2G/memory: $SUGGESTED_MEMORY/" docker-compose.rpi.yml
            print_success "Updated docker-compose.rpi.yml"
        fi
    else
        print_warning "Could not detect Pi model. Using defaults."
    fi
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"
    
    echo "This may take 10-30 minutes depending on your Raspberry Pi model..."
    echo "Pi 3: ~20 min | Pi 4: ~8 min | Pi 5: ~3 min"
    echo
    
    read -p "Continue with build? (y/n): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Build cancelled"
        return 1
    fi
    
    docker compose -f docker-compose.rpi.yml build
    
    print_success "Docker image built successfully"
}

# Start container
start_container() {
    print_header "Starting Container"
    
    docker compose -f docker-compose.rpi.yml up -d
    
    print_success "Container started"
    
    # Wait for health check
    echo "Waiting for container to be ready..."
    for i in {1..40}; do
        if curl -f http://localhost:11078/health &> /dev/null; then
            print_success "Container is healthy!"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if [ $i -eq 40 ]; then
        print_warning "Container health check timed out. Check logs with: docker logs rdk-middleware"
    fi
}

# Show access information
show_info() {
    print_header "Setup Complete!"
    
    print_success "RDK-E Middleware Testing Dashboard is ready"
    
    # Get Pi IP
    PI_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "Access the application at:"
    echo -e "  ${BLUE}http://$PI_IP:11078${NC}"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    docker compose -f docker-compose.rpi.yml logs -f"
    echo "  Stop:         docker compose -f docker-compose.rpi.yml stop"
    echo "  Restart:      docker compose -f docker-compose.rpi.yml restart"
    echo "  Shell access: docker exec -it rdk-middleware bash"
    echo ""
    echo "For more information, see DOCKER_RPI_SETUP.md"
    echo ""
}

# Main flow
main() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║  RDK-E Middleware Testing Dashboard - Docker Setup (Pi)    ║
║                  Quick Start Script                        ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_docker
    detect_pi_model
    create_env
    build_image && start_container && show_info
}

# Run main function
main
