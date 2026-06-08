# Docker Build and Deployment Guide for Mac

Complete step-by-step guide to build and run the RDK Testing Dashboard Docker image independently on a Mac machine.

---

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Prerequisites Installation](#prerequisites-installation)
3. [Prepare the Application](#prepare-the-application)
4. [Build the Docker Image](#build-the-docker-image)
5. [Run the Container](#run-the-container)
6. [Verify Deployment](#verify-deployment)
7. [Manage Container](#manage-container)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Specifications
- **Mac OS Version**: macOS 11 (Big Sur) or later
- **Processor**: Intel or Apple Silicon (M1/M2/M3/M4)
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: 20GB free (image + runtime data)
- **Network**: Internet connection for downloads

### Recommended Specifications
- **Mac OS Version**: macOS 12 or later
- **RAM**: 8GB or more
- **Disk Space**: 25GB or more
- **Processor**: Apple Silicon preferred (faster builds)

---

## Prerequisites Installation

### Step 1: Install Docker Desktop for Mac

1. **Download Docker Desktop**
   - Visit: https://www.docker.com/products/docker-desktop
   - Choose the appropriate version:
     - **Apple Silicon** (M1/M2/M3/M4): "Apple Silicon" version
     - **Intel**: "Intel Chip" version

2. **Install Docker**
   ```bash
   # After download, drag Docker.app to Applications folder
   # Or double-click the installer
   ```

3. **Launch Docker**
   - Open Applications folder
   - Double-click "Docker.app"
   - Grant permissions when prompted
   - Wait for Docker icon to appear in menu bar

4. **Verify Installation**
   ```bash
   # Open Terminal and run:
   docker --version
   # Output should be: Docker version 24.x.x or later
   
   # Test Docker is working:
   docker run hello-world
   # Should display "Hello from Docker!"
   ```

### Step 2: Setup Terminal Environment

1. **Open Terminal**
   ```bash
   # Press: Cmd + Space, type "Terminal", press Enter
   ```

2. **(Optional) Install iTerm2** for better terminal experience
   ```bash
   brew install iterm2
   # Or download from: https://iterm2.com/
   ```

---

## Prepare the Application

### Step 1: Navigate to Project Directory

```bash
# Navigate to the Enhancement directory
cd /path/to/Enhancement

# Verify you're in the correct directory
ls -la
# Should see: Dockerfile, docker-compose.yml, app.py, requirements.txt, etc.
```

### Step 2: Create Environment Configuration File

```bash
# Copy environment template (if it exists)
cp .env.example .env

# Or create a new .env file
cat > .env << EOF
# Flask Configuration
SECRET_KEY=your-secure-random-key-here-change-in-production

# SMTP Email Configuration (Gmail recommended)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-specific-password

# Alternative: Comcast Email Relay
# SMTP_HOST=mailrelay.comcast.com
# SMTP_PORT=587
# SENDER_EMAIL=your-email@comcast.net
# SENDER_PASSWORD=your-password
EOF
```

### Step 3: Configure Email Credentials

#### Option A: Gmail SMTP Setup (Recommended)

1. **Enable 2-Factor Authentication**
   - Go to: https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Mac"
   - Copy the generated 16-character password

3. **Update .env File**
   ```bash
   # Edit .env and add:
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-16-char-app-password
   ```

#### Option B: Comcast Email Relay

```bash
# Edit .env and add:
SMTP_HOST=mailrelay.comcast.com
SMTP_PORT=587
SENDER_EMAIL=your-email@comcast.net
SENDER_PASSWORD=your-comcast-password
```

### Step 4: Verify Application Files

```bash
# Check required files exist:
ls -la app.py
ls -la Dockerfile
ls -la docker-compose.yml
ls -la requirements.txt
ls -la .env

# All files should exist. If missing, restore from backup.
```

---

## Build the Docker Image

### Option A: Using Docker Compose (Recommended - Easiest)

This is the simplest method and uses predefined settings.

```bash
# Navigate to project directory
cd /path/to/Enhancement

# Build the Docker image
docker-compose build

# Monitor the build process (takes 10-15 minutes)
# You'll see progress for:
# - Downloading Python 3.11 base image
# - Installing system dependencies (tesseract, gcc)
# - Installing Python packages
# - Copying application code
# - Creating directories

# Optional: Verify image was created
docker images | grep rdk-testing-dashboard
```

**Expected Output:**
```
REPOSITORY                 TAG       IMAGE ID       SIZE
rdk-testing-dashboard      latest    abc123def456   6.5GB
```

### Option B: Using Docker CLI Directly

If you prefer more control or want to use a custom tag:

```bash
cd /path/to/Enhancement

# Build with default tag
docker build -t rdk-testing-dashboard:latest .

# Or build with version tag
docker build -t rdk-testing-dashboard:v1.0 .

# Build without using cache (clean build)
docker build --no-cache -t rdk-testing-dashboard:latest .

# Monitor progress (same as Option A)
```

### Build Process Details

- **Duration**: 10-15 minutes (first build), 2-5 minutes (subsequent builds with cache)
- **Network**: Requires internet connection
- **CPU**: Utilizes all available cores
- **Storage**: ~6.5GB final image size

### Troubleshooting Build Issues

**Issue: Build fails with "No space left"**
```bash
# Free up space
docker system prune -a

# Check available space
df -h
```

**Issue: Build timeouts**
```bash
# Press Ctrl+C to cancel
# Increase Docker resource limits:
# Docker Desktop → Preferences → Resources → Increase CPUs and Memory
# Retry build
```

**Issue: Package installation fails**
```bash
# Clean Docker system
docker system prune -a

# Try rebuilding with no cache
docker build --no-cache -t rdk-testing-dashboard:latest .
```

---

## Run the Container

### Option A: Using Docker Compose (Recommended)

This method manages the container lifecycle and volumes automatically.

```bash
cd /path/to/Enhancement

# Start the container in background
docker-compose up -d

# Verify container is running
docker-compose ps

# Expected output should show:
# NAME                    STATUS
# rdk-testing-dashboard   Up X seconds
```

### Option B: Using Docker CLI Directly

For more control over container settings:

```bash
docker run -d \
  --name rdk-testing-dashboard \
  -p 5000:5000 \
  -e SENDER_PASSWORD="$(grep SENDER_PASSWORD .env | cut -d '=' -f2)" \
  -e SMTP_HOST="$(grep SMTP_HOST .env | cut -d '=' -f2)" \
  -e SMTP_PORT="$(grep SMTP_PORT .env | cut -d '=' -f2)" \
  -e SENDER_EMAIL="$(grep SENDER_EMAIL .env | cut -d '=' -f2)" \
  -v "$(pwd)/devices.json:/app/devices.json" \
  -v "$(pwd)/jobs.json:/app/jobs.json" \
  -v "$(pwd)/device_job_queue.json:/app/device_job_queue.json" \
  -v "$(pwd)/device_locks.json:/app/device_locks.json" \
  -v "$(pwd)/saved_sequences.json:/app/saved_sequences.json" \
  -v "$(pwd)/app_state.json:/app/app_state.json" \
  -v "$(pwd)/iteration_logs:/app/iteration_logs" \
  -v "$(pwd)/screenshots:/app/screenshots" \
  --restart unless-stopped \
  rdk-testing-dashboard:latest
```

### Container Startup Output

```bash
# View startup logs
docker-compose logs -f

# You should see:
# [2026-03-25 15:30:45] Application starting...
# [2026-03-25 15:30:50] Gunicorn workers starting...
# [2026-03-25 15:30:52] Application ready on port 5000
```

---

## Verify Deployment

### Step 1: Check Container Status

```bash
# List running containers
docker ps

# Should show rdk-testing-dashboard container running
```

### Step 2: Check Application Health

```bash
# Method 1: Check health endpoint
curl -s http://localhost:5000/health | json_pp

# Expected response:
# {
#    "status": "healthy",
#    "timestamp": "2026-03-25T15:35:20Z"
# }

# Method 2: Check specific port
lsof -i :5000

# Should show gunicorn process listening on port 5000
```

### Step 3: Access the Web Interface

1. **Open Browser**
   - Type in address bar: `http://localhost:5000`
   - Press Enter

2. **Verify Application Loads**
   - Login page should appear
   - Enter credentials (if required)
   - Dashboard should display

### Step 4: Test Core Functionality

```bash
# 1. Verify devices.json is accessible
docker-compose exec web cat /app/devices.json | head -20

# 2. Check logs directory
docker-compose exec web ls -la /app/iteration_logs/

# 3. Verify Tesseract OCR is installed
docker-compose exec web tesseract --version
```

---

## Manage Container

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 50 lines
docker-compose logs -f --tail=50

# Logs from specific service
docker-compose logs -f web

# Exit logs view: Press Ctrl+C
```

### Stop Container

```bash
# Graceful stop (preferred)
docker-compose down

# Force stop
docker-compose kill

# Stop and remove all data
docker-compose down -v  # WARNING: Removes all volumes!
```

### Restart Container

```bash
# Restart container
docker-compose restart

# Restart specific service
docker-compose restart web
```

### Execute Commands in Container

```bash
# Run a command
docker-compose exec web python --version

# Open interactive shell
docker-compose exec web /bin/bash

# Exit shell: type 'exit' and press Enter
```

### View Resource Usage

```bash
# Real-time resource monitoring
docker stats rdk-testing-dashboard

# One-time snapshot
docker ps --no-trunc --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Exit stats: Press Ctrl+C (or press 'q')
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs web

# Look for error messages and note them
```

**Common causes:**
- Port 5000 already in use
- Insufficient memory
- Invalid environment variables

**Solutions:**
```bash
# Kill process using port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port in docker-compose.yml:
# Change "5000:5000" to "8000:5000"
```

### Connection Refused Error

```bash
# Verify container is running
docker-compose ps

# Check if port is listening
lsof -i :5000

# Restart container
docker-compose restart
```

### Out of Disk Space

```bash
# Check available space
df -h

# Clean up Docker images and containers
docker system prune -a

# Remove unused volumes
docker volume prune
```

### Application Crashes

```bash
# View crash logs
docker-compose logs web | tail -100

# Check resource limits in Docker Desktop
# Preferences → Resources → Increase limits

# Restart container
docker-compose down
docker-compose up -d
```

### SMTP Email Not Working

```bash
# Verify .env file
cat .env

# Check environment variables in container
docker-compose exec web env | grep SMTP

# Test SMTP connection from container
docker-compose exec web python -c "
import smtplib
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('your-email@gmail.com', 'your-app-password')
    print('SMTP connection successful!')
    server.quit()
except Exception as e:
    print(f'Error: {e}')
"
```

### Slow Performance

```bash
# Increase Docker resources
# Docker Menu → Preferences → Resources
# - CPUs: Set to at least 4
# - Memory: Set to at least 6GB

# Monitor resource usage
docker stats

# Check if container is CPU-bound
docker top rdk-testing-dashboard
```

---

## Advanced Operations

### Update the Application

```bash
# Pull latest code (if using git)
git pull origin main

# Rebuild image
docker-compose build --no-cache

# Restart container with new image
docker-compose up -d
```

### Backup Container Data

```bash
# Backup devices.json
cp devices.json devices.json.backup

# Backup all data
tar -czf backup-$(date +%Y%m%d_%H%M%S).tar.gz \
  devices.json \
  jobs.json \
  device_job_queue.json \
  iteration_logs/ \
  screenshots/

# Verify backup
ls -lh backup-*.tar.gz
```

### Export Image for Distribution

```bash
# Save image to file
docker save rdk-testing-dashboard:latest | gzip > rdk-dashboard.tar.gz

# Transfer to another Mac
# Then load with:
gunzip -c rdk-dashboard.tar.gz | docker load

# Verify image loaded
docker images | grep rdk-testing-dashboard
```

### Run Multiple Instances

```bash
# First instance (default)
docker-compose up -d

# Second instance (different port)
docker run -d \
  --name rdk-testing-2 \
  -p 5001:5000 \
  -v "$(pwd)/devices-2.json:/app/devices.json" \
  rdk-testing-dashboard:latest

# Access second instance at http://localhost:5001
```

---

## Quick Reference Commands

```bash
# Build image
docker-compose build

# Start container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Restart container
docker-compose restart

# Check status
docker-compose ps

# Execute command in container
docker-compose exec web <command>

# View resource usage
docker stats

# Remove everything (WARNING: destructive)
docker system prune -a
```

---

## Getting Help

### Useful Resources
- Docker Documentation: https://docs.docker.com/
- Flask Documentation: https://flask.palletsprojects.com/
- GitHub Issues: Check project repository for known issues

### Debugging Steps
1. Check container logs: `docker-compose logs -f`
2. Verify environment variables: `docker-compose exec web env`
3. Check file permissions: `docker-compose exec web ls -la /app/`
4. Test network connectivity: `docker-compose exec web ping 8.8.8.8`

---

## Maintenance

### Regular Tasks

**Weekly:**
```bash
# Check disk space
df -h

# Verify backup integrity
ls -lh backup-*.tar.gz
```

**Monthly:**
```bash
# Clean up old logs
find iteration_logs -mtime +30 -delete

# Update Docker Desktop
# Check for updates in Docker menu
```

**Quarterly:**
```bash
# Full system cleanup
docker system prune -a --volumes

# Rebuild image with latest packages
docker-compose build --no-cache
```

---

## Summary

You now have a complete Docker deployment of the RDK Testing Dashboard on your Mac. The application will:
- Run independently without needing host Python installation
- Persist data across container restarts
- Include all system dependencies (Tesseract OCR, etc.)
- Provide real-time log streaming
- Support email notifications via SMTP

For any issues or questions, refer to the troubleshooting section or contact your development team.

---

**Last Updated**: March 25, 2026
**Tested On**: macOS 12+, Docker Desktop 4.0+
**Python Version**: 3.11
**Framework**: Flask
