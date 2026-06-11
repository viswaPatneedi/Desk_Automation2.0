#!/bin/bash

# Quick Start Script for RDK Middleware on Raspberry Pi with Docker
# This script automates the build and deployment process
# Usage: ./docker-rpi-deploy.sh [build|run|stop|logs|clean]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="rdk-middleware"
IMAGE_NAME="rdk-middleware:rpi"
DOCKERFILE="Dockerfile.rpi"
DOCKER_COMPOSE_FILE="docker-compose.rpi.yml"
APP_PORT="11078"
APP_DIR="/home/rdk/app"  # Change to your app directory

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        echo "Install Docker: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    print_success "Docker is installed"
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        echo "Install Docker Compose: sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-aarch64 -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
        exit 1
    fi
    print_success "Docker Compose is installed"
}

build_image() {
    print_header "Building Docker Image for Raspberry Pi"
    
    check_docker
    
    echo "Building image: $IMAGE_NAME"
    echo "This may take 30-90 minutes on Raspberry Pi..."
    
    docker build -f $DOCKERFILE -t $IMAGE_NAME .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully!"
        docker images | grep rdk-middleware
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

run_container() {
    print_header "Running Docker Container"
    
    check_docker
    
    # Check if container already running
    if docker ps | grep -q $CONTAINER_NAME; then
        print_warning "Container is already running!"
        echo "Stop it first: ./docker-rpi-deploy.sh stop"
        exit 1
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_warning ".env file not found, creating default..."
        cat > .env << EOF
FLASK_ENV=production
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
WORKERS=3
WORKER_CLASS=gevent
TIMEOUT=300
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
EOF
        print_success ".env file created"
    fi
    
    echo "Starting container with docker-compose..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    
    # Wait for container to start
    sleep 5
    
    if docker ps | grep -q $CONTAINER_NAME; then
        print_success "Container started successfully!"
        echo ""
        echo "Application Information:"
        echo "  Container Name: $CONTAINER_NAME"
        echo "  Port: $APP_PORT"
        echo "  URL: http://$(hostname -I | awk '{print $1}'):$APP_PORT"
        echo ""
        echo "View logs: docker logs -f $CONTAINER_NAME"
        echo "Stop container: ./docker-rpi-deploy.sh stop"
    else
        print_error "Failed to start container"
        docker logs $CONTAINER_NAME
        exit 1
    fi
}

stop_container() {
    print_header "Stopping Docker Container"
    
    check_docker_compose
    
    if docker ps | grep -q $CONTAINER_NAME; then
        echo "Stopping container..."
        docker-compose -f $DOCKER_COMPOSE_FILE down
        print_success "Container stopped"
    else
        print_warning "Container is not running"
    fi
}

view_logs() {
    print_header "Container Logs"
    
    check_docker
    
    if docker ps -a | grep -q $CONTAINER_NAME; then
        docker logs -f $CONTAINER_NAME
    else
        print_error "Container does not exist"
        exit 1
    fi
}

check_health() {
    print_header "Checking Container Health"
    
    check_docker
    
    if docker ps | grep -q $CONTAINER_NAME; then
        PI_IP=$(hostname -I | awk '{print $1}')
        echo "Testing health endpoint: http://$PI_IP:$APP_PORT/health"
        
        RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:$APP_PORT/health 2>/dev/null || echo "Connection failed\n000")
        HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
        BODY=$(echo "$RESPONSE" | head -n -1)
        
        if [ "$HTTP_CODE" -eq 200 ]; then
            print_success "Health check passed!"
            echo "Response: $BODY"
        else
            print_error "Health check failed (HTTP $HTTP_CODE)"
            echo "Response: $BODY"
        fi
    else
        print_error "Container is not running"
        exit 1
    fi
}

view_stats() {
    print_header "Container Resource Usage"
    
    check_docker
    
    if docker ps | grep -q $CONTAINER_NAME; then
        docker stats $CONTAINER_NAME --no-stream
    else
        print_error "Container is not running"
        exit 1
    fi
}

clean_all() {
    print_header "Cleaning Up"
    
    check_docker
    
    read -p "This will remove all Docker containers and images. Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f $DOCKER_COMPOSE_FILE down
        docker rmi $IMAGE_NAME
        print_success "Cleanup complete"
    else
        print_warning "Cleanup cancelled"
    fi
}

full_deploy() {
    print_header "Full Deployment (Build + Run)"
    
    build_image
    echo ""
    run_container
}

show_help() {
    cat << EOF
${BLUE}RDK Middleware Docker Deployment Script${NC}

Usage: $0 [command]

Commands:
  build       Build Docker image (${YELLOW}first time: 30-90 minutes${NC})
  run         Run container with docker-compose
  stop        Stop running container
  logs        View container logs (streaming)
  health      Check container health
  stats       View container resource usage
  clean       Remove container and image
  deploy      Build and run (full deployment)
  help        Show this help message

Examples:
  $0 build       # Build the image
  $0 deploy      # Build and run
  $0 logs        # View live logs
  $0 stop        # Stop the container

Environment:
  CONTAINER_NAME: $CONTAINER_NAME
  IMAGE_NAME: $IMAGE_NAME
  PORT: $APP_PORT

${YELLOW}First Time Setup:${NC}
  1. $0 deploy        # Build image and start container
  2. $0 health        # Verify health
  3. Open http://$(hostname -I | awk '{print $1}'):$APP_PORT in browser

${YELLOW}Systemd Service Setup:${NC}
  sudo cp docker-rpi-deploy.sh /usr/local/bin/rdk-middleware
  sudo chmod +x /usr/local/bin/rdk-middleware
  
  Create: /etc/systemd/system/rdk-middleware.service
  [Unit]
  Description=RDK Middleware Docker
  After=docker.service
  [Service]
  Type=simple
  WorkingDirectory=$APP_DIR
  ExecStart=/bin/bash /usr/local/bin/rdk-middleware run
  Restart=on-failure
  [Install]
  WantedBy=multi-user.target
EOF
}

# Main script
case "$1" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    stop)
        stop_container
        ;;
    logs)
        view_logs
        ;;
    health)
        check_health
        ;;
    stats)
        view_stats
        ;;
    clean)
        clean_all
        ;;
    deploy)
        full_deploy
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        if [ -z "$1" ]; then
            show_help
        else
            print_error "Unknown command: $1"
            echo "Use: $0 help"
            exit 1
        fi
        ;;
esac
