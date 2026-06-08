# Docker Setup for Raspberry Pi - RDK-E Middleware Testing Dashboard

This guide provides step-by-step instructions to build and run the RDK-E Middleware Testing Dashboard as a Docker container on Raspberry Pi (Pi 3, Pi 4, or Pi 5).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installing Docker on Raspberry Pi](#installing-docker-on-raspberry-pi)
3. [Building the Docker Image](#building-the-docker-image)
4. [Running the Container](#running-the-container)
5. [Configuration](#configuration)
6. [Managing the Container](#managing-the-container)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- **Raspberry Pi 3/4/5** with at least:
  - **Pi 3**: 512MB stable (1GB+ recommended)
  - **Pi 4/5**: 2GB+ RAM (4GB recommended for optimal performance)
  - 16GB+ microSD card (32GB recommended for logs and screenshots)
  
### Software Requirements
- Raspberry Pi OS (Bullseye or later - 64-bit recommended)
- Internet connection for downloading packages
- SSH access or display connected to Pi

---

## Installing Docker on Raspberry Pi

### Step 1: Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install Docker
```bash
# Official Docker installation script (recommended)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (optional, avoid using sudo)
sudo usermod -aG docker ${USER}

# Apply group changes (log out and log back in, or run:)
newgrp docker
```

### Step 3: Install Docker Compose
```bash
# Install Docker Compose v2
sudo apt-get install -y docker-compose-plugin

# Or for Docker Compose v1 (legacy)
sudo apt-get install -y docker-compose

# Verify installation
docker --version
docker compose version
```

### Step 4: Verify Docker Installation
```bash
docker run hello-world
```

---

## Building the Docker Image

### Option 1: Build from Dockerfile.rpi (Recommended)

Navigate to the application directory and build:

```bash
cd /path/to/Enhancement

# Build the image
docker build -f Dockerfile.rpi -t rdk-middleware:pi .

# With custom tag (optional)
docker build -f Dockerfile.rpi -t rdk-middleware:pi-latest .
docker buildx build -f Dockerfile.rpi -t rdk-middleware:pi --platform linux/arm/v7,linux/arm64/v8 .
```

### Build Time and Size
- **Build Time**: 10-20 minutes on Pi 3, 3-5 minutes on Pi 4/5 (slower due to package compilation)
- **Image Size**: ~1.2GB (includes Tesseract OCR, OpenCV, etc.)

### Option 2: Using Docker Compose

Create a `.env` file in the application directory:

```bash
cat > .env << EOF
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Application Settings
SECRET_KEY=your-secure-key-change-in-production

# Performance (optimize for your Pi)
WORKERS=2  # Pi 3/4: 2, Pi 5: 4
TIMEOUT=300
EOF
```

Build using docker-compose:

```bash
docker compose -f docker-compose.rpi.yml build
```

---

## Running the Container

### Option 1: Using Docker Run Command

```bash
docker run -d \
  --name rdk-middleware \
  --network host \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  -e SMTP_HOST=smtp.gmail.com \
  -e SMTP_PORT=587 \
  -e SENDER_EMAIL=your-email@gmail.com \
  -e SENDER_PASSWORD=your-app-password \
  -e SECRET_KEY=your-secure-key \
  rdk-middleware:pi
```

### Option 2: Using Docker Compose (Recommended)

```bash
# Start the container
docker compose -f docker-compose.rpi.yml up -d

# View logs
docker compose -f docker-compose.rpi.yml logs -f

# Stop the container
docker compose -f docker-compose.rpi.yml down
```

### Verify Container is Running

```bash
# Check container status
docker ps | grep rdk-middleware

# Check logs
docker logs rdk-middleware -f

# Test health endpoint
curl http://localhost:11078/health
```

---

## Configuration

### Email Setup (Gmail SMTP)

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or custom)
   - Copy the generated 16-character password

3. Update your `.env` file:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx  # 16-character app password
```

### Resource Limits

Adjust memory limits in `docker-compose.rpi.yml` based on your Pi model:

```yaml
deploy:
  resources:
    limits:
      memory: 2G  # Pi 4: 2G, Pi 5: 4G
    reservations:
      memory: 1G  # Pi 4: 1G, Pi 5: 2G
```

### Performance Tuning

Modify Gunicorn workers in `docker-compose.rpi.yml`:

```yaml
environment:
  - WORKERS=2  # Pi 3: 2, Pi 4: 2-4, Pi 5: 4-8
  - TIMEOUT=300  # Increase for slow operations
```

---

## Managing the Container

### Common Commands

```bash
# Start container
docker compose -f docker-compose.rpi.yml up -d

# Stop container gracefully
docker compose -f docker-compose.rpi.yml stop

# Restart container
docker compose -f docker-compose.rpi.yml restart

# View real-time logs
docker compose -f docker-compose.rpi.yml logs -f

# Execute command in running container
docker exec rdk-middleware bash

# View container stats (CPU, memory)
docker stats rdk-middleware

# Remove container (stops it first)
docker compose -f docker-compose.rpi.yml down
```

### Backup Data

```bash
# Backup all JSON data and logs
mkdir -p backup
cp devices.json jobs.json iteration_logs backup/
cp -r screenshots backup/
tar -czf rdk-backup-$(date +%Y%m%d-%H%M%S).tar.gz backup/
```

### Restore Data

```bash
# Extract backup
tar -xzf rdk-backup-YYYYMMDD-HHMMSS.tar.gz

# Copy files back
cp backup/*.json .
cp -r backup/screenshots .
cp -r backup/iteration_logs .
```

### Auto-Start on Boot

```bash
# Create systemd service
sudo tee /etc/systemd/system/docker-rdk-middleware.service > /dev/null << EOF
[Unit]
Description=RDK Middleware Testing Dashboard
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/Enhancement
ExecStart=/usr/bin/docker compose -f docker-compose.rpi.yml up
ExecStop=/usr/bin/docker compose -f docker-compose.rpi.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable docker-rdk-middleware
sudo systemctl start docker-rdk-middleware

# Check status
sudo systemctl status docker-rdk-middleware
```

---

## Troubleshooting

### Issue: "Port already in use"

```bash
# Find process using port 11078
sudo lsof -i :11078
sudo netstat -tulpn | grep 11078

# Kill process
sudo kill -9 <PID>

# Or use a different port in docker-compose.rpi.yml
```

### Issue: "Out of memory" or slow performance

**Solution**: Increase memory or enable swap
```bash
# Check memory usage
free -h

# Enable swap (Pi 3 only - not needed for Pi 4/5)
sudo dphys-swapfile swapon

# Increase swap size
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=2048 (default is 100)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Issue: "Tesseract OCR not found"

```bash
# Reinstall Tesseract
docker exec rdk-middleware apt-get update
docker exec rdk-middleware apt-get install -y tesseract-ocr

# Or rebuild image
docker compose -f docker-compose.rpi.yml rebuild
```

### Issue: "Build fails with 'No space left on device'"

```bash
# Check disk space
df -h

# Clean Docker images
docker system prune -a

# Increase microSD card space or remove unnecessary files
```

### Issue: "SSH connections timeout"

Ensure:
1. Device has proper network connectivity
2. SSH port (default 10022) is accessible
3. Device IP is correctly configured in UI
4. Try ping from Pi to device: `ping <device_ip>`

### Issue: "Container exits immediately"

```bash
# Check detailed logs
docker logs rdk-middleware --tail 50

# Run in interactive mode to debug
docker compose -f docker-compose.rpi.yml up  # Without -d flag
```

### Issue: "High CPU usage"

```bash
# Reduce number of workers
# Edit docker-compose.rpi.yml
environment:
  - WORKERS=1  # Reduce from 2 to 1
```

---

## Accessing the Dashboard

Once the container is running:

1. **Web Interface**: `http://<pi-ip>:11078`
   - Default login: NTID (check app for defaults)
   - Password: As configured

2. **From Another Computer**:
   ```bash
   curl http://<pi-ip>:11078/health
   ```

3. **From Pi Terminal**:
   ```bash
   curl http://localhost:11078/health
   ```

---

## Performance Benchmarks

### Raspberry Pi 3 Model B+
- Build Time: ~20 minutes
- Container Start: ~40 seconds
- Memory Usage: 600-800MB
- CPU Usage: 30-50% (idle)

### Raspberry Pi 4 Model B (2GB)
- Build Time: ~8 minutes
- Container Start: ~20 seconds
- Memory Usage: 400-600MB
- CPU Usage: 10-20% (idle)

### Raspberry Pi 4 Model B (4GB+)
- Build Time: ~5 minutes
- Container Start: ~15 seconds
- Memory Usage: 300-400MB
- CPU Usage: 5-10% (idle)

### Raspberry Pi 5 (Model B)
- Build Time: ~3 minutes
- Container Start: ~10 seconds
- Memory Usage: 200-300MB
- CPU Usage: 2-5% (idle)

---

## Next Steps

1. **Configure email settings** in `.env` for notifications
2. **Add devices** via the web UI at `http://<pi-ip>:11078`
3. **Set up SSH keys** for passwordless authentication to test devices
4. **Configure sequences** for automated testing workflows
5. **Enable auto-backup** using cron:
   ```bash
   0 2 * * * cd /path/to/Enhancement && docker compose -f docker-compose.rpi.yml exec -T rdk-middleware tar -czf /app/backup-$(date +\%Y\%m\%d).tar.gz -C /app devices.json jobs.json iteration_logs
   ```

---

## Support & Documentation

- **Flask App Logs**: `docker logs rdk-middleware -f`
- **Gunicorn Logs**: Check Docker logs above
- **Application Issues**: Check `iteration_logs/` directory
- **System Issues**: Check `docker stats` and `free -h`

For more information:
- Configuration: See `copilot-instructions.md`
- Features: See `README.md`
- Architecture: See `APPLICATION_OVERVIEW.md`

---

## License & Attribution

This Docker setup is part of the RDK-E Middleware QA Testing Tool.
For more information, see the main project documentation.
