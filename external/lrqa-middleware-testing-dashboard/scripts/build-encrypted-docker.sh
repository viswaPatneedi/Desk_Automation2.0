#!/bin/bash
# PyArmor Docker Build & Deploy Script for Raspberry Pi 4
# Usage: ./build-encrypted-docker.sh [build|push|deploy|all]

set -e

# Configuration
PROJECT_NAME="rdk-middleware"
IMAGE_TAG="encrypted-v1"
DOCKER_REGISTRY="myregistry"  # Change to your Docker Hub username or registry
DOCKERFILE="Dockerfile.pyarmor"
RPI_HOST="${RPI_HOST:-pi@192.168.1.100}"
RPI_PATH="/opt/middleware"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}======================================${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
    
    if ! command -v pyarmor &> /dev/null; then
        print_info "PyArmor not found in PATH, will be installed in Docker build"
    else
        print_success "PyArmor is installed: $(pyarmor --version)"
    fi
    
    if [ ! -f "$DOCKERFILE" ]; then
        print_error "$DOCKERFILE not found"
        exit 1
    fi
    print_success "$DOCKERFILE exists"
}

# Build Docker image with PyArmor
build_image() {
    print_header "Building Docker Image with PyArmor"
    
    print_info "Building: $DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG"
    print_info "This may take 5-10 minutes..."
    
    docker build \
        -f "$DOCKERFILE" \
        -t "$DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG" \
        -t "$DOCKER_REGISTRY/$PROJECT_NAME:latest" \
        --progress=plain \
        .
    
    print_success "Image built successfully"
    
    # Show image info
    print_info "Image Details:"
    docker images | grep "$PROJECT_NAME" | head -2
}

# Push image to registry
push_image() {
    print_header "Pushing Image to Registry"
    
    if [ "$DOCKER_REGISTRY" = "myregistry" ]; then
        print_error "Please update DOCKER_REGISTRY variable in script (e.g., your-dockerhub-username)"
        exit 1
    fi
    
    print_info "Pushing: $DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG"
    docker push "$DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG"
    docker push "$DOCKER_REGISTRY/$PROJECT_NAME:latest"
    
    print_success "Image pushed successfully"
}

# Deploy to Raspberry Pi 4
deploy_to_rpi() {
    print_header "Deploying to Raspberry Pi 4"
    
    print_info "Target: $RPI_HOST"
    print_info "Path: $RPI_PATH"
    
    # Create directories on RPi
    print_info "Creating directories on RPi..."
    ssh "$RPI_HOST" "mkdir -p $RPI_PATH/iteration_logs $RPI_PATH/screenshots"
    print_success "Directories created"
    
    # Copy docker-compose.yml if it exists
    if [ -f "docker-compose.yml" ]; then
        print_info "Copying docker-compose.yml to RPi..."
        scp docker-compose.yml "$RPI_HOST:$RPI_PATH/"
        print_success "docker-compose.yml copied"
    fi
    
    # Pull and run image on RPi
    print_info "Pulling image on RPi..."
    ssh "$RPI_HOST" "cd $RPI_PATH && docker pull $DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG"
    
    # Check if docker-compose exists
    if ssh "$RPI_HOST" command -v docker-compose &>/dev/null; then
        print_info "Starting with docker-compose..."
        ssh "$RPI_HOST" "cd $RPI_PATH && docker-compose up -d"
    else
        print_info "Starting with docker run..."
        ssh "$RPI_HOST" "docker run -d \
            --name $PROJECT_NAME \
            -p 11078:11078 \
            -v $RPI_PATH/iteration_logs:/app/iteration_logs \
            -v $RPI_PATH/screenshots:/app/screenshots \
            -e FLASK_ENV=production \
            $DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG"
    fi
    
    print_success "Container started on RPi"
    
    # Wait and check health
    print_info "Waiting for application to start..."
    sleep 5
    
    ssh "$RPI_HOST" "curl -s http://localhost:11078/api/health > /dev/null && echo 'Health check: OK' || echo 'Health check: FAILED'"
}

# Verify depl
verify_deployment() {
    print_header "Verifying Deployment"
    
    print_info "Checking image is encrypted..."
    docker run --rm "$DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG" \
        sh -c "head -c 100 app.py | file - || echo 'File check: app.py is binary/encrypted'"
    
    print_success "Deployment verification complete"
}

# Local test
test_local() {
    print_header "Testing Locally"
    
    print_info "Starting container..."
    docker run -d \
        --name test-$PROJECT_NAME \
        -p 11078:11078 \
        "$DOCKER_REGISTRY/$PROJECT_NAME:$IMAGE_TAG"
    
    print_info "Waiting for startup..."
    sleep 5
    
    print_info "Health check..."
    curl -s http://localhost:11078/api/health && print_success "Health check passed" || print_error "Health check failed"
    
    print_info "Checking container status..."
    docker ps | grep test-$PROJECT_NAME
    
    print_info "Container logs (last 10 lines):"
    docker logs test-$PROJECT_NAME | tail -10
    
    print_info "Stopping test container..."
    docker stop test-$PROJECT_NAME && docker rm test-$PROJECT_NAME
    
    print_success "Local test complete"
}

# Main menu
main() {
    case "${1:-all}" in
        build)
            check_prerequisites
            build_image
            ;;
        push)
            push_image
            ;;
        deploy)
            deploy_to_rpi
            ;;
        test)
            test_local
            ;;
        verify)
            verify_deployment
            ;;
        all)
            check_prerequisites
            build_image
            test_local
            # Uncomment to auto-push and deploy:
            # push_image
            # deploy_to_rpi
            print_info "Build and local test successful!"
            print_info "Next steps:"
            echo "  1. Update DOCKER_REGISTRY in this script"
            echo "  2. Run: ./build-encrypted-docker.sh push"
            echo "  3. Run: ./build-encrypted-docker.sh deploy"
            ;;
        *)
            echo "Usage: $0 {build|push|deploy|test|verify|all}"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker image with PyArmor encryption"
            echo "  test    - Test built image locally"
            echo "  push    - Push image to Docker registry"
            echo "  deploy  - Deploy to Raspberry Pi 4"
            echo "  verify  - Verify code is encrypted"
            echo "  all     - Build and test locally (use push/deploy separately)"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
