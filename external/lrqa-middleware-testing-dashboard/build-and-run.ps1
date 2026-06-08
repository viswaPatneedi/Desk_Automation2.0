# PowerShell Script for Docker Build and Run on Windows
# Usage: .\build-and-run.ps1 -Action build|run|rebuild|stop|clean
# Run as: powershell -ExecutionPolicy Bypass -File build-and-run.ps1 -Action rebuild

param (
    [string]$Action = "help",
    [switch]$NoCache = $false
)

# Configuration
$PROJECT_NAME = "rdk-testing-dashboard"
$CONTAINER_NAME = "rdk-testing"
$IMAGE_NAME = "${PROJECT_NAME}:latest"
$PORT_MAPPING = "5000:5000"

# Color functions
function Write-Header {
    param([string]$Message)
    Write-Host "`n" -ForegroundColor White
    Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

# Check prerequisites
function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker found: $dockerVersion"
    }
    catch {
        Write-Error "Docker is not installed. Please install Docker Desktop for Windows."
        Write-Info "Download from: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    # Check Docker daemon
    try {
        docker info | Out-Null
        Write-Success "Docker daemon is running"
    }
    catch {
        Write-Error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    }
}

# Build Docker image
function Build-Image {
    Write-Header "Building Docker Image"
    
    Write-Info "Image name: $IMAGE_NAME"
    Write-Info "This may take 10-15 minutes on first build..."
    
    if ($NoCache) {
        Write-Info "Using --no-cache flag for fresh build..."
        docker-compose build --no-cache
    }
    else {
        docker-compose build
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image built successfully"
    }
    else {
        Write-Error "Failed to build Docker image"
        exit 1
    }
}

# Run Docker container
function Run-Container {
    Write-Header "Starting Docker Container"
    
    # Check if container exists
    $containerExists = docker ps -a --format '{{.Names}}' | Select-String "^${CONTAINER_NAME}$"
    if ($containerExists) {
        Write-Warning "Container '$CONTAINER_NAME' already exists"
        Write-Info "Removing existing container..."
        docker-compose down
    }
    
    Write-Info "Starting container with port mapping: $PORT_MAPPING"
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Container started successfully"
        
        Write-Info "Waiting for application to be ready..."
        Start-Sleep -Seconds 5
        
        $containerStatus = docker-compose ps
        if ($containerStatus -like "*Up*") {
            Write-Success "Application is ready"
            Write-Info "Access the application at: http://localhost:5000"
            Write-Info "View logs with: docker-compose logs -f"
        }
        else {
            Write-Warning "Container may not be ready yet. Check logs:"
            docker-compose logs
        }
    }
    else {
        Write-Error "Failed to start container"
        exit 1
    }
}

# Stop container
function Stop-Container {
    Write-Header "Stopping Docker Container"
    
    docker-compose down
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Container stopped successfully"
    }
    else {
        Write-Warning "Container may already be stopped"
    }
}

# Clean up resources
function Cleanup {
    Write-Header "Cleaning Up Docker Resources"
    Write-Warning "This will remove the container and image"
    
    $confirmation = Read-Host "Are you sure? (y/n)"
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        Write-Info "Removing containers and images..."
        docker-compose down -v
        docker rmi $IMAGE_NAME
        Write-Success "Cleanup completed"
    }
    else {
        Write-Info "Cleanup cancelled"
    }
}

# Show logs
function Show-Logs {
    Write-Header "Docker Container Logs"
    Write-Info "Press Ctrl+C to exit"
    docker-compose logs -f
}

# Show status
function Show-Status {
    Write-Header "Docker Container Status"
    
    Write-Info "Container Status:"
    docker-compose ps
    
    Write-Host "`n"
    Write-Info "Image Information:"
    docker images | Select-String $PROJECT_NAME
    
    Write-Host "`n"
    Write-Info "Container Resource Usage:"
    try {
        docker stats $CONTAINER_NAME --no-stream
    }
    catch {
        Write-Warning "Container not running or stats unavailable"
    }
}

# Open bash shell
function Open-Bash {
    Write-Header "Opening Bash Shell"
    
    $isRunning = docker ps --format '{{.Names}}' | Select-String "^${CONTAINER_NAME}$"
    if ($isRunning) {
        Write-Info "Opening shell in $CONTAINER_NAME"
        docker-compose exec -it web bash
    }
    else {
        Write-Error "Container is not running"
        Write-Info "Start the container first: .\build-and-run.ps1 -Action run"
        exit 1
    }
}

# Show help
function Show-Help {
    $helpText = @"
RDK Testing Dashboard - Docker Build and Run Script for Windows

Usage: .\build-and-run.ps1 -Action <action> [-NoCache]

Actions:
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
    .\build-and-run.ps1 -Action build
    .\build-and-run.ps1 -Action rebuild -NoCache
    .\build-and-run.ps1 -Action logs
    .\build-and-run.ps1 -Action bash

Prerequisites:
    - Docker Desktop for Windows installed and running
    - WSL 2 backend enabled (recommended)
    - .env file configured with SMTP credentials
    - At least 10GB free disk space

Troubleshooting:
    - If you get execution policy error, run:
      Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
    
    - If Docker commands don't work, ensure Docker Desktop is running
    - Check Docker Desktop Settings > Resources if you run out of memory

Documentation:
    See DOCKER_WINDOWS_MAC_GUIDE.md for detailed instructions

"@
    Write-Host $helpText
}

# Main function
function Main {
    $actionLower = $Action.ToLower()
    
    switch ($actionLower) {
        "build" {
            Check-Prerequisites
            Build-Image
        }
        "run" {
            Check-Prerequisites
            Run-Container
        }
        "rebuild" {
            Check-Prerequisites
            Build-Image
            Run-Container
        }
        "stop" {
            Check-Prerequisites
            Stop-Container
        }
        "clean" {
            Check-Prerequisites
            Cleanup
        }
        "logs" {
            Check-Prerequisites
            Show-Logs
        }
        "status" {
            Check-Prerequisites
            Show-Status
        }
        "bash" {
            Check-Prerequisites
            Open-Bash
        }
        "help" {
            Show-Help
        }
        default {
            Write-Error "Unknown action: $Action"
            Write-Host "`n"
            Show-Help
            exit 1
        }
    }
}

# Run main function
Main
