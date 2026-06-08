# 🐳 Docker Run Commands for Linux & Raspberry Pi

**RDK-E Middleware Testing Dashboard**

Complete guide with all commands to build and run the Docker image on Linux and Raspberry Pi systems with all dependencies installed.

---

## 📋 Table of Contents

1. [Prerequisites & Dependencies](#prerequisites--dependencies)
2. [Quick Start (Fastest)](#quick-start-fastest)
3. [Manual Setup](#manual-setup)
4. [Build Commands](#build-commands)
5. [Run Commands](#run-commands)
6. [Docker Compose Commands](#docker-compose-commands)
7. [Makefile Commands](#makefile-commands)
8. [Environment Variables](#environment-variables)
9. [Troubleshooting](#troubleshooting)

---

## 📦 Prerequisites & Dependencies

### System Dependencies (Installed Automatically in Docker)

The Docker image automatically installs ALL required dependencies:

```
✓ Python 3.11 slim
✓ Tesseract OCR (for AI vision/OCR)
✓ Tesseract language packs (English)
✓ OpenCV (image processing)
✓ GCC/G++ (C compilation)
✓ Python development headers
✓ Build essentials
✓ BLAS/LAPACK math libraries
✓ JPEG turbo libraries
✓ libharfbuzz (text rendering)
✓ curl & ca-certificates
```

### Python Dependencies (Installed Automatically)

```
Flask==3.0.0
Flask-Login==0.6.3
Flask-Bcrypt==1.0.1
paramiko==3.4.0 (SSH)
Pillow==10.1.0 (Image processing)
pytesseract==0.3.10 (OCR)
requests==2.31.0 (HTTP)
gunicorn==21.2.0 (WSGI server)
gevent==24.2.1 (Async workers)
openpyxl==3.1.5 (Excel)
opencv-python==4.8.1.78 (Computer vision)
numpy==1.24.3 (Math)
imagehash==4.3.1 (Image comparison)
scikit-image==0.22.0 (Image processing)
scipy==1.12.0 (Scientific computing)
```

### Host Machine Prerequisites

```bash
# Linux/Raspberry Pi OS (Debian-based)
✓ 64-bit OS (ARMv8 for RPi 4/5, ARMv7 for RPi 3)
✓ Docker Engine (install below)
✓ Docker Compose (install below)
✓ 2GB+ RAM (4GB recommended, 8GB optimal)
✓ 32GB+ SD card or storage
✓ Internet connection for initial setup
```

---

## ⚡ Quick Start (Fastest)

### Using the Automated Script (Recommended)

```bash
# Navigate to project directory
cd /path/to/Enhancement

# Run the automated quick-start script
bash docker-rpi-quickstart.sh

# The script will:
# ✓ Check Docker installation
# ✓ Detect Raspberry Pi model
# ✓ Create .env configuration
# ✓ Build the image
# ✓ Start the container
# ✓ Display access URL
```

**Total Time**: ~5-70 minutes (depending on Pi model)
- Pi 5: 5-10 minutes
- Pi 4: 10-20 minutes  
- Pi 3: 30-70 minutes

---

## 🔧 Manual Setup

### Step 1: Install Docker on Linux/Raspberry Pi

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (avoid sudo requirement)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker run hello-world
```

### Step 2: Install Docker Compose

```bash
# Option A: Install Docker Compose Plugin (Recommended)
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Verify
docker compose version

# Option B: Install as Standalone (if Option A doesn't work)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-aarch64" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### Step 3: Verify Prerequisites

```bash
# Check Pi model (for RPi)
cat /sys/firmware/devicetree/base/model

# Check system architecture
uname -m  # Should show: aarch64 (64-bit RPi 4/5) or armv7l (32-bit RPi 3)

# Check available RAM
free -h

# Check available storage
df -h
```

### Step 4: Clone or Navigate to Project

```bash
cd /path/to/Enhancement
ls -la  # Should see: Dockerfile, docker-compose.rpi.yml, requirements.txt
```

---

## 🏗️ Build Commands

### Build Using Docker Compose (Recommended)

```bash
# Build the image
docker compose -f docker-compose.rpi.yml build

# Build without cache (fresh rebuild)
docker compose -f docker-compose.rpi.yml build --no-cache --pull

# Build with specific Dockerfile
docker compose -f docker-compose.rpi.yml build --no-cache
```

### Build Using Docker CLI Directly

```bash
# Standard build
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# No-cache build (fresh)
docker build --no-cache -f Dockerfile.rpi -t rdk-middleware:rpi .

# With platform specification
docker buildx build --platform linux/arm64 -f Dockerfile.rpi -t rdk-middleware:rpi .
```

### Build Progress Indicators

```
Layer pulling:           5-15 minutes
Base Python setup:       5-10 minutes
System dependencies:     10-20 minutes
Python dependencies:     15-40 minutes (depends on Pi model)
─────────────────────────────────────
Total: 30-70 minutes (Pi 4/5) to 90+ minutes (Pi 3)
```

**Optimization Tips for Faster Builds:**
```bash
# Use buildkit for faster, more efficient builds
DOCKER_BUILDKIT=1 docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# Pre-pull base image
docker pull python:3.11-slim

# Monitor build progress in real-time
docker build -f Dockerfile.rpi -t rdk-middleware:rpi . --progress=plain
```

---

## 🚀 Run Commands

### Run Using Docker Compose (Recommended)

```bash
# Start container in background
docker compose -f docker-compose.rpi.yml up -d

# Start with log output
docker compose -f docker-compose.rpi.yml up

# Stop container
docker compose -f docker-compose.rpi.yml down

# Restart container
docker compose -f docker-compose.rpi.yml restart

# View logs
docker compose -f docker-compose.rpi.yml logs -f

# View last 50 lines
docker compose -f docker-compose.rpi.yml logs --tail=50
```

### Run Using Docker CLI Directly

```bash
# Basic run command (interactive with terminal)
docker run -it \
  --name rdk-middleware \
  -p 11078:5000 \
  --hostname rdk-middleware \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  -e FLASK_ENV=production \
  -e SENDER_EMAIL=your-email@gmail.com \
  -e SENDER_PASSWORD=your-app-password \
  rdk-middleware:rpi

# Detached mode (background)
docker run -d \
  --name rdk-middleware \
  -p 11078:5000 \
  --hostname rdk-middleware \
  --restart unless-stopped \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  -e FLASK_ENV=production \
  -e SENDER_EMAIL=your-email@gmail.com \
  -e SENDER_PASSWORD=your-app-password \
  rdk-middleware:rpi

# With resource limits
docker run -d \
  --name rdk-middleware \
  -p 11078:5000 \
  --memory=2g \
  --cpus=2 \
  --hostname rdk-middleware \
  --restart unless-stopped \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  -v /etc/localtime:/etc/localtime:ro \
  -e FLASK_ENV=production \
  -e SENDER_EMAIL=your-email@gmail.com \
  -e SENDER_PASSWORD=your-app-password \
  rdk-middleware:rpi

# With all data volumes
docker run -d \
  --name rdk-middleware \
  -p 11078:5000 \
  --hostname rdk-middleware \
  --restart unless-stopped \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/device_job_queue.json:/app/device_job_queue.json \
  -v $(pwd)/device_locks.json:/app/device_locks.json \
  -v $(pwd)/saved_sequences.json:/app/saved_sequences.json \
  -v $(pwd)/app_state.json:/app/app_state.json \
  -v $(pwd)/ir_keycodes.json:/app/ir_keycodes.json \
  -v $(pwd)/reset_codes.json:/app/reset_codes.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  -v $(pwd)/captured_images:/app/captured_images \
  -e FLASK_ENV=production \
  rdk-middleware:rpi
```

### View Logs After Starting

```bash
# View container logs
docker logs rdk-middleware

# Follow logs in real-time
docker logs -f rdk-middleware

# Show last 100 lines
docker logs --tail=100 rdk-middleware

# Show logs with timestamps
docker logs -f --timestamps rdk-middleware
```

### Access the Application

```bash
# Get your Raspberry Pi IP address
hostname -I

# Access the web interface
# Open in browser: http://<your-pi-ip>:11078

# Check health endpoint
curl http://localhost:11078/health

# Check API endpoints
curl http://localhost:11078/api/devices
curl http://localhost:11078/api/jobs
```

---

## 🐳 Docker Compose Commands

### Complete Docker Compose Workflow

```bash
# 1. Create environment configuration
nano .env  # Edit with your email settings

# 2. Build the image
docker compose -f docker-compose.rpi.yml build

# 3. Start services
docker compose -f docker-compose.rpi.yml up -d

# 4. Wait for startup
sleep 10

# 5. Check health
docker compose -f docker-compose.rpi.yml ps

# 6. View logs
docker compose -f docker-compose.rpi.yml logs -f

# 7. Execute commands in container
docker compose -f docker-compose.rpi.yml exec rdk-middleware ps aux

# 8. Stop services
docker compose -f docker-compose.rpi.yml down

# 9. Remove volumes (careful!)
docker compose -f docker-compose.rpi.yml down -v

# 10. Restart
docker compose -f docker-compose.rpi.yml restart
```

### Useful Docker Compose Queries

```bash
# Show all running services
docker compose -f docker-compose.rpi.yml ps

# Show running processes in container
docker compose -f docker-compose.rpi.yml exec rdk-middleware ps aux

# Show container resource usage
docker stats rdk-middleware

# Show container disk usage
docker compose -f docker-compose.rpi.yml exec rdk-middleware du -sh /app/*

# Test database connectivity
docker compose -f docker-compose.rpi.yml exec rdk-middleware curl http://localhost:5000/health
```

---

## 📋 Makefile Commands

### Using Make for Simple Commands

```bash
# Install Docker (first time)
make -f Makefile.rpi install-docker

# Create .env file from example
make -f Makefile.rpi env

# Build image
make -f Makefile.rpi build

# Rebuild from scratch
make -f Makefile.rpi build-no-cache

# Start container
make -f Makefile.rpi up

# Stop container
make -f Makefile.rpi down

# View logs
make -f Makefile.rpi logs

# Restart container
make -f Makefile.rpi restart

# Open shell in container
make -f Makefile.rpi shell

# Check health
make -f Makefile.rpi health

# Show container stats
make -f Makefile.rpi stats

# Backup data
make -f Makefile.rpi backup

# Restore from backup
make -f Makefile.rpi restore

# Clean up
make -f Makefile.rpi clean

# Remove and rebuild everything
make -f Makefile.rpi clean build up
```

---

## 🔐 Environment Variables

### Required for Email Configuration

Create a `.env` file:

```bash
# Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-char-app-password  # NOT your main Gmail password!

# Application
SECRET_KEY=your-secure-random-key-here

# Performance (optional)
WORKERS=2          # For Pi 4; use 1 for Pi 3, 4 for Pi 5
TIMEOUT=300        # Request timeout in seconds
WORKER_CLASS=gevent
```

### How to Get Gmail App Password

1. Go to https://myaccount.google.com/account
2. Enable 2-Factor Authentication
3. Go to https://myaccount.google.com/apppasswords
4. Select "Mail" and "Windows Computer"
5. Generate and copy the 16-character password
6. Add to `.env` as `SENDER_PASSWORD`

### Override at Runtime

```bash
# Using -e flag
docker run -e SENDER_EMAIL=myemail@gmail.com \
           -e SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx \
           rdk-middleware:rpi

# Using --env-file
docker run --env-file .env rdk-middleware:rpi
```

---

## 🔍 Useful Inspection Commands

### Container Status

```bash
# Check if running
docker ps | grep rdk-middleware

# Get container details
docker inspect rdk-middleware

# Show resource usage
docker stats rdk-middleware

# Show logs
docker logs rdk-middleware

# Show recent events
docker events --filter container=rdk-middleware
```

### Inside Container

```bash
# Open shell
docker exec -it rdk-middleware /bin/bash

# Run python command
docker exec rdk-middleware python -c "import flask; print(flask.__version__)"

# Check tesseract installation
docker exec rdk-middleware tesseract --version

# Check Python packages
docker exec rdk-middleware pip list

# Check disk usage
docker exec rdk-middleware du -sh /app/*

# List devices
docker exec rdk-middleware cat /app/devices.json
```

### Network & Connectivity

```bash
# Test web server
curl http://localhost:11078/health

# Test from same Pi
ssh pi@<other-pi-ip> curl http://<first-pi-ip>:11078/health

# Check active connections
docker exec rdk-middleware netstat -tulpn

# Monitor logs live
docker exec -it rdk-middleware tail -f /var/log/gunicorn.log
```

---

## 📊 System Resource Requirements

### By Raspberry Pi Model

| Model | Recommended RAM | Storage | Build Time | Run Performance |
|-------|-----------------|---------|-----------|-----------------|
| Pi 3  | 2GB min, 2-4GB better | 32GB+ | 60-90 min | Slow (1 worker) |
| Pi 4  | 2GB min, 4GB better | 32GB+ | 20-30 min | Good (2 workers) |
| Pi 5  | 4GB+ | 32GB+ | 5-10 min | Excellent (4 workers) |

### Limit Resources

```bash
# Set memory limit
docker run -d --memory=2g --memswap=3g rdk-middleware:rpi

# Set CPU limit
docker run -d --cpus=2.0 rdk-middleware:rpi

# Set both
docker run -d \
  --memory=2g \
  --cpus=2.0 \
  rdk-middleware:rpi
```

---

## ⚠️ Troubleshooting

### Build Fails with Out of Memory

```bash
# Option 1: Reduce parallel builds
export DOCKER_BUILDKIT=0
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# Option 2: Build on external SD card with more space
# Move project to external USB drive with more space

# Option 3: Clean up and retry
docker system prune -a --volumes
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .
```

### Container Won't Start

```bash
# Check logs
docker logs rdk-middleware

# Check if port 11078 is in use
sudo lsof -i :11078

# Kill process using port
sudo kill -9 <PID>

# Remove old container
docker rm -f rdk-middleware

# Try starting again
docker run -d -p 11078:5000 rdk-middleware:rpi
```

### Rebuild If Base Image Updates

```bash
# Pull latest Python base image
docker pull python:3.11-slim

# Rebuild without cache
docker build --no-cache -f Dockerfile.rpi -t rdk-middleware:rpi .
```

### Check All Volumes are Mounted

```bash
# Inspect mounted volumes
docker inspect rdk-middleware | grep -A 20 Mounts

# Check if devices.json exists outside container
ls -la devices.json jobs.json iteration_logs/
```

### Slow Performance

```bash
# Increase workers (if on Pi 4+)
docker run -e WORKERS=4 rdk-middleware:rpi

# Check container resource usage
docker stats rdk-middleware

# Check Pi system usage
top
free -h
df -h

# Optimize by reducing memory
docker run --memory=1.5g rdk-middleware:rpi
```

---

## 💾 Backup & Restore

### Backup All Data

```bash
# Using makefile
make -f Makefile.rpi backup

# Manual backup
mkdir -p backup
cp -r devices.json jobs.json *.json iteration_logs screenshots backup/
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz backup/

# Backup Docker image
docker save rdk-middleware:rpi | gzip > rdk-middleware-rpi-$(date +%Y%m%d).tar.gz
```

### Restore from Backup

```bash
# Using makefile
make -f Makefile.rpi restore

# Manual restore
tar -xzf backup-YYYYMMDD-HHMMSS.tar.gz

# Restore Docker image
gunzip < rdk-middleware-rpi-YYYYMMDD.tar.gz | docker load
```

---

## ✅ Verification Checklist

After starting the container, verify:

```bash
# ✓ Container is running
docker ps | grep rdk-middleware

# ✓ Web server responds
curl http://localhost:11078/health

# ✓ Logs show no errors
docker logs rdk-middleware | tail -20

# ✓ Ports are accessible
netstat -tulpn | grep 11078

# ✓ Data files exist
ls -la devices.json jobs.json iteration_logs/

# ✓ Python packages installed
docker exec rdk-middleware pip list | grep -E "Flask|paramiko|pillow"

# ✓ Tesseract installed
docker exec rdk-middleware tesseract --version

# ✓ All services healthy
curl http://localhost:11078/api/health
```

---

## 📞 Quick Reference

```bash
# Full workflow from scratch
bash docker-rpi-quickstart.sh

# Alternative manual workflow
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .
docker compose -f docker-compose.rpi.yml up -d
docker compose -f docker-compose.rpi.yml logs -f

# View on browser
http://<your-pi-ip>:11078

# Stop and cleanup
docker compose -f docker-compose.rpi.yml down
docker system prune -a
```

---

_Last Updated: April 2026_
_For updates and Docker guides, see: DOCKER_RPI_SETUP.md, DOCKER_RPI_8GB_DEPLOYMENT_GUIDE.md_
