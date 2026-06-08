#!/bin/bash

###############################################################################
# Docker Build and Run Script for Mac
# Quick-start script to build and manage the RDK Testing Dashboard in Docker
# 
# Usage:
#   ./docker-mac-setup.sh build      - Build Docker image
#   ./docker-mac-setup.sh run        - Start container
#   ./docker-mac-setup.sh stop       - Stop container
#   ./docker-mac-setup.sh logs       - View logs
#   ./docker-mac-setup.sh clean      - Remove image and container
#   ./docker-mac-setup.sh status     - Show container status
#   ./docker-mac-setup.sh shell      - Open container shell
#
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="rdk-testing-dashboard"
CONTAINER_NAME="rdk-testing-dashboard"
PORT=5000
APP_PORT=5000

# Functions
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running!"
        print_info "Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found"
        print_info "Creating .env file from template..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success ".env file created from template"
            print_warning "Please edit .env with your SMTP credentials"
        else
            cat > .env << EOF
# Flask Configuration
SECRET_KEY=change-me-in-production

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
EOF
            print_success ".env file created"
            print_warning "Please edit .env with your SMTP credentials"
        fi
    fi
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"
    check_docker
    check_env_file
    
    print_info "Starting Docker build..."
    print_info "This will take 10-15 minutes on first build"
    print_info "Downloading base image, installing dependencies..."
    
    docker-compose build
    
    print_success "Docker image built successfully!"
    docker images | grep "$IMAGE_NAME"
}

# Run container
run_container() {
    print_header "Starting Container"
    check_docker
    check_env_file
    
    # Check if container already running
    if docker-compose ps | grep -q "Up"; then
        print_warning "Container is already running"
        return
    fi
    
    print_info "Starting container..."
    docker-compose up -d
    
    sleep 3
    
    if docker-compose ps | grep -q "Up"; then
        print_success "Container started successfully!"
        print_info "Application URL: ${GREEN}http://localhost:${PORT}${NC}"
        print_info "View logs: ${GREEN}./docker-mac-setup.sh logs${NC}"
    else
        print_error "Container failed to start"
        docker-compose logs
        exit 1
    fi
}

# Stop container
stop_container() {
    print_header "Stopping Container"
    
    if docker-compose ps | grep -q "Up"; then
        print_info "Stopping container..."
        docker-compose down
        print_success "Container stopped"
    else
        print_warning "Container is not running"
    fi
}

# View logs
view_logs() {
    print_header "Container Logs"
    docker-compose logs -f
}

# Show status
show_status() {
    print_header "Container Status"
    docker-compose ps
    
    echo ""
    print_info "Docker Image:"
    docker images | grep "$IMAGE_NAME" || echo "Image not found"
    
    echo ""
    if docker-compose ps | grep -q "Up"; then
        print_info "Application URL: ${GREEN}http://localhost:${PORT}${NC}"
        print_success "Container is running"
    else
        print_warning "Container is not running"
    fi
}

# Open shell
open_shell() {
    print_header "Opening Container Shell"
    
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Container is not running"
        print_info "Start it with: ./docker-mac-setup.sh run"
        exit 1
    fi
    
    print_info "Opening interactive shell in container..."
    print_info "Type 'exit' to exit"
    
    docker-compose exec web /bin/bash
}

# Clean up
clean_up() {
    print_header "Cleanup"
    
    read -p "$(echo -e ${YELLOW}Are you sure you want to remove the image and containers? [y/N]${NC} )" -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping container..."
        docker-compose down 2>/dev/null || true
        
        print_info "Removing image..."
        docker rmi "$IMAGE_NAME:latest" 2>/dev/null || true
        
        print_success "Cleanup complete"
    else
        print_info "Cleanup cancelled"
    fi
}

# Restart container
restart_container() {
    print_header "Restarting Container"
    docker-compose restart
    print_success "Container restarted"
}

# Health check
health_check() {
    print_header "Health Check"
    
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Container is not running"
        return 1
    fi
    
    print_info "Checking application health..."
    
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        print_success "Application is healthy"
        curl -s http://localhost:5000/health | python -m json.tool 2>/dev/null || echo "Health check endpoint responded"
    else
        print_error "Application health check failed"
        return 1
    fi
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}Docker Commands:${NC}"
    echo "  build        Build Docker image"
    echo "  run          Start container"
    echo "  stop         Stop container"
    echo "  restart      Restart container"
    echo "  logs         View container logs"
    echo "  status       Show container status"
    echo "  health       Check application health"
    echo "  shell        Open container shell"
    echo "  clean        Remove image and containers"
    echo ""
}

# Main script logic
main() {
    local command=${1:---help}
    
    case "$command" in
        build)
            build_image
            ;;
        run)
            run_container
            ;;
        stop)
            stop_container
            ;;
        restart)
            restart_container
            ;;
        logs)
            view_logs
            ;;
        status)
            show_status
            ;;
        health)
            health_check
            ;;
        shell)
            open_shell
            ;;
        clean)
            clean_up
            ;;
        --help|-h)
            print_header "Docker Mac Setup Helper"
            show_menu
            ;;
        *)
            print_error "Unknown command: $command"
            show_menu
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
