# Docker Setup Guide - RDK-E Middleware QA Dashboard for Raspberry Pi 4

## Overview

This guide provides complete instructions for deploying the RDK-E Middleware QA Dashboard on Raspberry Pi 4 using Docker. The Docker image includes all latest code changes with a clean slate (no execution data).

---

## Quick Start (Automated)

The fastest way to get up and running is to use the automated setup script:

```bash
# Navigate to project directory
cd /path/to/Enhancement

# Make script executable
chmod +x rpi4-setup-complete.sh

# Run the setup script (will handle everything)
./rpi4-setup-complete.sh
```

This script will:
- ✅ Check system requirements
- ✅ Install Docker & Docker Compose (if needed)
- ✅ Build the clean Docker image
- ✅ Start the application
- ✅ Verify healthy startup
- ✅ Show access URLs

---

## Manual Installation

If you prefer to install step-by-step:

### 1. Install Docker on Raspberry Pi

```bash
# Download Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh

# Run installation
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

### 2. Install Docker Compose

```bash
# Install Docker Compose
sudo apt-get update
sudo apt-get install -y docker-compose

# Verify installation
docker-compose --version
```

### 3. Build Docker Image

```bash
# Navigate to project directory
cd /path/to/Enhancement

# Build the clean image (no execution data)
docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean .
```

### 4. Start Application with Docker Compose

```bash
# Start application in background
docker-compose -f docker-compose.rpi.clean.yml up -d

# View logs
docker-compose -f docker-compose.rpi.clean.yml logs -f
```

### 5. Access Dashboard

Open your browser and navigate to:
```
http://<rpi-ip-address>:11078
```

To find your RPi's IP address:
```bash
hostname -I
```

---

## Docker Files Overview

### File: `Dockerfile.rpi.clean`

- **Purpose**: Builds production-ready Docker image optimized for ARM/ARM64
- **Base Image**: `python:3.11-slim` (lightweight, ARM-compatible)
- **Excludes**: All execution data, logs, screenshots (clean slate)
- **Includes**: All application code and latest changes
- **Size**: ~800MB-1GB (optimized for RPi)

### File: `docker-compose.rpi.clean.yml`

- **Purpose**: Orchestrates container deployment with volumes and networking
- **Services**: Single application service with volume mounts
- **Volumes**: 
  - `app_data` - Persistent application data
  - `reference_screens` - Screen validation references
- **Port Mapping**: `11078:11078` (web UI)
- **Resource Limits**: Optimized for RPi 4 (1 CPU core, 512MB RAM)

### File: `docker-entrypoint.sh`

- **Purpose**: Container startup initialization script
- **Functions**:
  - Validates required files
  - Creates necessary directories
  - Initializes JSON files (empty)
  - Configures environment variables
  - Starts the Flask application
  - Provides startup diagnostics

### File: `.dockerignore.rpi.clean`

- **Purpose**: Specifies files/directories to exclude from Docker build
- **Excludes**:
  - Execution data (`iteration_logs/`, `screenshots/`, etc.)
  - Old logs and backups
  - IDE/git files
  - Large archives
- **Result**: Minimal, fast Docker builds

---

## Environment Configuration

### Default Environment Variables

The application uses these environment variables (can be customized):

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=0

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=11078
LOG_LEVEL=INFO

# SSH Configuration (device connections)
SSH_PORT=10022
SSH_USERNAME=root
SSH_TIMEOUT=30

# Email Configuration (optional - set for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=          # Leave empty to disable
SMTP_PASSWORD=
SMTP_FROM_EMAIL=

# Security
SECRET_KEY=change-this-in-production
SESSION_TIMEOUT=86400
```

### Customizing Environment Variables

#### Method 1: Edit docker-compose file

```yaml
environment:
  SMTP_USER: "your-email@gmail.com"
  SMTP_PASSWORD: "your-app-password"
  SECRET_KEY: "your-secure-32-char-key"
```

#### Method 2: Use .env file

Create `.env` file in project directory:

```env
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SECRET_KEY=your-secure-32-char-key
```

#### Method 3: Command line

```bash
docker-compose -f docker-compose.rpi.clean.yml up -d \
  -e SMTP_USER=your-email@gmail.com \
  -e SMTP_PASSWORD=your-app-password
```

---

## Container Management

### View Running Containers

```bash
# List all containers
docker ps

# List all containers (including stopped)
docker ps -a

# Show detailed container info
docker inspect rdk-middleware-dashboard
```

### View Application Logs

```bash
# Real-time logs
docker-compose -f docker-compose.rpi.clean.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.rpi.clean.yml logs --tail=100

# Logs from specific service
docker logs rdk-middleware-dashboard

# Timestamp-prefixed logs
docker logs -t rdk-middleware-dashboard
```

### Start/Stop/Restart

```bash
# Stop application
docker-compose -f docker-compose.rpi.clean.yml stop

# Start application
docker-compose -f docker-compose.rpi.clean.yml start

# Restart application
docker-compose -f docker-compose.rpi.clean.yml restart
docker restart rdk-middleware-dashboard

# Stop and remove containers
docker-compose -f docker-compose.rpi.clean.yml down
```

### Monitor Resource Usage

```bash
# Real-time stats
docker stats rdk-middleware-dashboard

# Memory usage
docker stats --no-stream rdk-middleware-dashboard
```

---

## Data Persistence

### Docker Volumes

Application data is stored in two Docker volumes:

1. **`app_data`** - Application state and execution data
   - Screenshots captured during tests
   - Iteration logs
   - Session data
   - Device logs collected

2. **`reference_screens`** - Screen validation references
   - Base images for screen comparison
   - Reference screenshots

### Accessing Volume Data

```bash
# Locate volume storage path
docker volume inspect app_data

# Mount volume to inspect files (Linux/Mac)
docker run --rm -v app_data:/mnt alpine ls /mnt

# Copy data from container
docker cp rdk-middleware-dashboard:/app/data ./local_data
```

### Backup Volume Data

```bash
# Create backup archive
docker run --rm -v app_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/app_data_backup.tar.gz /data

# Restore from backup
docker run --rm -v app_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/app_data_backup.tar.gz -C /
```

---

## Troubleshooting

### Issue: Container fails to start

**Check logs:**
```bash
docker logs rdk-middleware-dashboard
```

**Common causes:**
- Missing `requirements.txt`
- Missing `log_patterns.json`
- Port 11078 already in use
- Insufficient disk space

**Solution:**
```bash
# Stop and remove container
docker-compose -f docker-compose.rpi.clean.yml down

# Verify files exist
ls -la app.py requirements.txt log_patterns.json

# Rebuild image
docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean .

# Start again
docker-compose -f docker-compose.rpi.clean.yml up -d
```

### Issue: Web UI not accessible

**Check container status:**
```bash
docker ps | grep rdk-middleware-dashboard
```

**Check port binding:**
```bash
docker port rdk-middleware-dashboard
```

**Check network:**
```bash
# Verify RPi IP
hostname -I

# Test connectivity from RPi
curl http://localhost:11078

# Test from another machine
curl http://<rpi-ip>:11078
```

### Issue: High memory usage

**Check memory usage:**
```bash
docker stats rdk-middleware-dashboard
```

**Reduce resource limits in docker-compose.yml:**
```yaml
deploy:
  resources:
    limits:
      memory: 256M  # Reduce from 512M
```

**Restart:**
```bash
docker-compose -f docker-compose.rpi.clean.yml restart
```

### Issue: Application responses are slow

**Check system resources:**
```bash
free -h          # Memory
df -h            # Disk
ps aux | head    # CPU usage
```

**If disk is full:**
```bash
# Clean up Docker artifacts
docker system prune

# Remove unused volumes
docker volume prune
```

### Issue: Session data not persisting

**Verify volume is mounted:**
```bash
docker inspect rdk-middleware-dashboard | grep -A 10 Mounts
```

**Check volume contents:**
```bash
docker exec rdk-middleware-dashboard ls -la /app/data/
```

---

## Performance Optimization

### Recommended Settings for RPi 4 (4GB)

```yaml
# docker-compose.rpi.clean.yml
deploy:
  resources:
    limits:
      cpus: '1'        # Use 1 CPU core
      memory: 512M     # Use 512MB
    reservations:
      cpus: '0.5'
      memory: 256M

# app.py (Gunicorn)
CMD: ["gunicorn", "--workers", "2", "--worker-class", "gevent"]
```

### Recommended Settings for RPi 4 (8GB)

```yaml
deploy:
  resources:
    limits:
      cpus: '2'        # Use 2 CPU cores
      memory: 1024M    # Use 1GB
    reservations:
      cpus: '1'
      memory: 512M

# app.py (Gunicorn)
CMD: ["gunicorn", "--workers", "4", "--worker-class", "gevent"]
```

---

## Updating Application

### With New Code Changes

```bash
# Stop running container
docker-compose -f docker-compose.rpi.clean.yml stop

# Update application code from git or copy
git pull  # or manually update files

# Rebuild image
docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean .

# Remove old container
docker-compose -f docker-compose.rpi.clean.yml down

# Start with new image
docker-compose -f docker-compose.rpi.clean.yml up -d
```

### Data Persistence During Update

```bash
# Old data (iterations, screenshots) is preserved in app_data volume
docker volume ls | grep app_data

# Data persists even if container is recreated
docker-compose -f docker-compose.rpi.clean.yml down
docker-compose -f docker-compose.rpi.clean.yml up -d
# All previous data still accessible
```

---

## Production Deployment

### Security Recommendations

1. **Change Secret Key:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   # Copy output and set in environment
   ```

2. **Enable HTTPS (with reverse proxy):**
   - Use nginx or Apache in front of Docker
   - Install SSL certificates
   - Configure port 443

3. **Set Strong Passwords:**
   - Change default user credentials
   - Use encrypted password hashes

4. **Enable Email Notifications:**
   ```yaml
   SMTP_USER: your-email@gmail.com
   SMTP_PASSWORD: your-app-password  # Use Gmail app password
   ```

5. **Regular Backups:**
   ```bash
   # Daily backup cron job
   0 2 * * * docker volume inspect app_data | tar czf /backups/app_data_$(date +\%Y\%m\%d).tar.gz
   ```

### High Availability Setup (Optional)

```bash
# Create Docker swarm cluster
docker swarm init

# Deploy as service (scales across nodes)
docker service create \
  --name rdk-middleware \
  --publish 11078:11078 \
  rdk-middleware-dashboard:rpi4-clean
```

---

## Monitoring & Alerts

### Health Check

Application has built-in health check:

```bash
docker inspect rdk-middleware-dashboard | grep -i health
```

### Real-time Monitoring

```bash
# Dashboard-style monitoring
docker stats --no-stream

# Custom monitoring
while true; do
  clear
  echo "=== RDK Middleware Dashboard ===" 
  docker stats --no-stream rdk-middleware-dashboard
  echo ""
  docker logs -n 5 rdk-middleware-dashboard
  sleep 5
done
```

---

## Support & Additional Resources

### Useful Docker Commands

```bash
# Remove image
docker rmi rdk-middleware-dashboard:rpi4-clean

# Tag image for registry
docker tag rdk-middleware-dashboard:rpi4-clean user/rdk:latest

# Push to registry
docker push user/rdk:latest

# Pull from registry
docker pull user/rdk:latest

# Show image layers
docker history rdk-middleware-dashboard:rpi4-clean
```

### Docker Documentation

- [Docker Official Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Hub](https://hub.docker.com/)
- [Raspberry Pi Docker Documentation](https://docs.docker.com/engine/install/raspberry-pi-os/)

### Getting Help

1. Check container logs: `docker logs rdk-middleware-dashboard`
2. Verify file permissions: `ls -la /app/`
3. Check port availability: `netstat -tulpn | grep 11078`
4. Review docker-compose config: `docker-compose config`

---

## End of Docker Setup Guide

For questions or issues, consult the troubleshooting section above or refer to official Docker documentation.

Last Updated: 2026-04-17
Version: 2.0 (RPi 4 Optimized, Clean Build)
