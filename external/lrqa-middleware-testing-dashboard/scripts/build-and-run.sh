#!/bin/bash

# Cross-platform Docker Build and Run Script for Mac and Linux
# Usage: ./build-and-run.sh [build|run|rebuild|stop|clean]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="rdk-testing-dashboard"
CONTAINER_NAME="rdk-testing"
IMAGE_NAME="${PROJECT_NAME}:latest"
PORT_MAPPING="5000:5000"

# Functions
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

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

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    fi
    print_success "Docker found: $(docker --version)"
}

# Check if Docker daemon is running
check_docker_daemon() {
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    print_success "Docker daemon is running"
}

# Build the Docker image
build_image() {
    print_header "Building Docker Image"
    
    print_info "Image name: $IMAGE_NAME"
    print_info "This may take 10-15 minutes on first build..."
    
    if docker-compose build --no-cache; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Run the Docker container
run_container() {
    print_header "Starting Docker Container"
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container '$CONTAINER_NAME' already exists"
        print_info "Removing existing container..."
        docker-compose down
    fi
    
    print_info "Starting container with port mapping: $PORT_MAPPING"
    
    if docker-compose up -d; then
        print_success "Container started successfully"
        
        # Wait for container to be ready
        print_info "Waiting for application to be ready..."
        sleep 5
        
        if docker-compose ps | grep -q "Up"; then
            print_success "Application is ready"
            print_info "Access the application at: http://localhost:5000"
            print_info "View logs with: docker-compose logs -f"
        else
            print_warning "Container may not be ready yet. Check logs:"
            docker-compose logs
        fi
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Stop the container
stop_container() {
    print_header "Stopping Docker Container"
    
    if docker-compose down; then
        print_success "Container stopped successfully"
    else
        print_warning "Container may already be stopped"
    fi
}

# Clean up - remove image, containers, and volumes
cleanup() {
    print_header "Cleaning Up Docker Resources"
    print_warning "This will remove the container and image"
    
    read -p "Are you sure? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing containers and images..."
        docker-compose down -v
        docker rmi $IMAGE_NAME || true
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Show usage information
show_usage() {
    cat << EOF
${BLUE}RDK Testing Dashboard - Docker Build and Run Script${NC}

Usage: ./build-and-run.sh [COMMAND]

Commands:
    build       - Build the Docker image
    run         - Run the Docker container
    rebuild     - Build image and run container
    stop        - Stop the running container
    clean       - Remove container, image, and volumes
    logs        - View container logs
    status      - Show container status
    bash        - Open bash shell in running container
    help        - Show this help message

Examples:
    ./build-and-run.sh build          # Build the image
    ./build-and-run.sh rebuild        # Build and run
    ./build-and-run.sh logs           # View logs
    ./build-and-run.sh bash           # Open shell

${YELLOW}Prerequisites:${NC}
    - Docker Desktop installed and running
    - .env file configured with SMTP credentials
    - At least 10GB free disk space

${BLUE}Documentation:${NC}
    See DOCKER_WINDOWS_MAC_GUIDE.md for detailed instructions

EOF
}

# View container logs
show_logs() {
    print_header "Docker Container Logs"
    print_info "Press Ctrl+C to exit"
    docker-compose logs -f
}

# Show container status
show_status() {
    print_header "Docker Container Status"
    
    echo
    print_info "Container Status:"
    docker-compose ps
    
    echo
    print_info "Image Information:"
    docker images | grep $PROJECT_NAME || print_warning "Image not found"
    
    echo
    print_info "Container Resource Usage:"
    docker stats $CONTAINER_NAME --no-stream 2>/dev/null || print_warning "Container not running"
}

# Open bash in running container
open_bash() {
    print_header "Opening Bash Shell"
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Opening shell in $CONTAINER_NAME"
        docker-compose exec -it web bash
    else
        print_error "Container is not running"
        print_info "Start the container first: ./build-and-run.sh run"
        exit 1
    fi
}

# Main script logic
main() {
    case "${1:-help}" in
        build)
            check_docker
            check_docker_daemon
            build_image
            ;;
        run)
            check_docker
            check_docker_daemon
            run_container
            ;;
        rebuild)
            check_docker
            check_docker_daemon
            build_image
            run_container
            ;;
        stop)
            check_docker
            check_docker_daemon
            stop_container
            ;;
        clean)
            check_docker
            check_docker_daemon
            cleanup
            ;;
        logs)
            check_docker
            check_docker_daemon
            show_logs
            ;;
        status)
            check_docker
            check_docker_daemon
            show_status
            ;;
        bash)
            check_docker
            check_docker_daemon
            open_bash
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
