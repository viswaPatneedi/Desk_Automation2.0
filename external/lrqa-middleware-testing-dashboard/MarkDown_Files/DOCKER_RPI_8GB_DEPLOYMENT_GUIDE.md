# Docker Deployment Guide for Raspberry Pi 8GB - Latest Version

## System Assessment: Is 8GB RPi Enough?

✅ **YES - 8GB Raspberry Pi is EXCELLENT for this application!**

### Resource Requirements:
- **CPU**: ARMv8 (Pi 4/5 recommended, Pi 3 workable)
- **RAM**: 
  - Minimum: 2GB
  - Recommended: 4GB
  - Optimal: 8GB ✅
  - Your Pi: 8GB 💪 (More than enough!)
- **Storage**: 
  - Minimum: 32GB SD card
  - Recommended: 64GB+ SD card or SSD
  - Flask app: ~500MB
  - Dependencies: ~300MB
  - Room for logs/screenshots: ~10-20GB recommended

### 8GB RPi Performance Profile:
- Concurrent users: 5-10
- Simultaneous device tests: 3-5
- Background jobs: Multiple without slowdown
- Screenshots storage: 1000+ images
- Log retention: 6-12 months
- **Verdict**: Perfect for this middleware testing dashboard

---

## Prerequisites

### 1. Raspberry Pi Setup
```bash
# Ensure Pi is updated
sudo apt-get update
sudo apt-get upgrade -y

# Verify OS
uname -m  # Should output: aarch64 (64-bit) for Pi 4/5
```

### 2. Install Docker & Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker
docker --version
docker run hello-world

# Install Docker Compose (as standalone)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-aarch64" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 3. Enable SSH Service (for device testing)
```bash
sudo systemctl start ssh
sudo systemctl enable ssh
```

---

## Building the Docker Image

### Option 1: Quick Start (Recommended)
```bash
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement

# Build using RPi-optimized Dockerfile
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# This builds with:
# - Python 3.11 slim (ARM64 optimized)
# - Tesseract OCR
# - All dependencies from requirements.txt
# - Device lock fixes (NEW: device_lock_manager.py, ssh_connectivity_test.py)
# - DeepSleep results UI enhancements
```

### Option 2: Using Docker Compose (Full Stack)
```bash
docker-compose -f docker-compose.rpi.yml build
```

### Build Progress Indicators
```
# Initial layer pull: 5-15 minutes
# Dependency installation: 20-45 minutes (RPi 4)
# Dependency installation: 45-90 minutes (RPi 3)
# Total time: 30-70 minutes depending on Pi model

# For faster builds, use:
docker buildx build --platform linux/arm64 -f Dockerfile.rpi -t rdk-middleware:rpi .
```

---

## Running the Container

### Option 1: Basic Docker Run
```bash
docker run -d \
  --name rdk-middleware \
  --network host \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  -p 11078:11078 \
  rdk-middleware:rpi

# Access application
curl http://localhost:11078
# Browser: http://<pi-ip>:11078
```

### Option 2: Docker Compose (Recommended)
```bash
# Create .env file for configuration
cat > .env << EOF
# Flask Configuration
FLASK_ENV=production
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)

# Gunicorn Settings (RPi 8GB optimized)
WORKERS=3
WORKER_CLASS=gevent
TIMEOUT=300

# Email Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
EOF

# Start container
docker-compose -f docker-compose.rpi.yml up -d

# View logs
docker-compose -f docker-compose.rpi.yml logs -f rdk-middleware

# Stop container
docker-compose -f docker-compose.rpi.yml down
```

### Option 3: Systemd Service (Persistent)
```bash
# Create systemd service
sudo tee /etc/systemd/system/docker-rdk.service > /dev/null <<EOF
[Unit]
Description=RDK Middleware Testing Dashboard (Docker)
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
WorkingDirectory=/home/rdk/app
ExecStart=/usr/bin/docker-compose -f docker-compose.rpi.yml up
ExecStop=/usr/bin/docker-compose -f docker-compose.rpi.yml down
User=rdk

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable docker-rdk.service
sudo systemctl start docker-rdk.service

# View status
sudo systemctl status docker-rdk.service
sudo journalctl -u docker-rdk.service -f
```

---

## Resource Monitoring

### CPU & Memory Usage (8GB Pi)
```bash
# Real-time monitoring
docker stats rdk-middleware

# Expected values (idle):
# - Memory: 200-400MB (4-5% of 8GB)
# - CPU: 0-5%

# Expected values (during execution):
# - Memory: 600-1200MB (7-15% of 8GB)
# - CPU: 20-60% (depending on parallelism)
```

### Disk Usage
```bash
# Check container size
docker exec rdk-middleware du -sh /app

# Expected:
# - Image size: ~1.2-1.5GB
# - Container size: ~500MB
# - Data/logs: Grows over time (plan 10-20GB)
```

---

## Volume Management (Data Persistence)

### Mounted Paths
```
Host Path                          → Container Path
./devices.json                     → /app/devices.json
./jobs.json                        → /app/jobs.json
./device_locks.json               → /app/device_locks.json (NEW - Device Lock Fixes)
./iteration_logs                   → /app/iteration_logs
./screenshots                      → /app/screenshots
./saved_sequences.json            → /app/saved_sequences.json
./ir_keycodes.json                → /app/ir_keycodes.json
```

### Backup Strategy
```bash
# Daily backup
docker exec rdk-middleware cp /app/jobs.json /app/iteration_logs/jobs-backup-$(date +%Y%m%d).json
docker exec rdk-middleware cp /app/devices.json /app/iteration_logs/devices-backup-$(date +%Y%m%d).json
docker exec rdk-middleware cp /app/device_locks.json /app/iteration_logs/locks-backup-$(date +%Y%m%d).json

# External backup
rsync -av ./iteration_logs/ /backup/iteration_logs/
rsync -av ./screenshots/ /backup/screenshots/
```

---

## New Features Included (Latest Deployment)

### 1. Device Lock Architecture Fixes ✅
- Dynamic lock duration calculation
- Lock refresh at iteration boundaries
- Real-time lock validation during waits
- SSH connectivity pre-validation
- API endpoint: `/api/jobs/<job_id>/lock-status`

### 2. DeepSleep Results UI Enhancements ✅
- Date-based filtering capability
- Execution block layout (SEQUENCE vs METHOD)
- Responsive result cards
- Full-width display
- Device status reorganization

### 3. Utility Modules ✅
- `utils/device_lock_manager.py` - Lock management
- `utils/ssh_connectivity_test.py` - SSH validation
- `static/js/lock-status-monitor.js` - Real-time monitoring
- `templates/components/lock-status-indicator.html` - UI indicator

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs rdk-middleware

# Common issue: Port already in use
sudo lsof -i :11078
# Kill process if needed
kill -9 <PID>

# Restart container
docker restart rdk-middleware
```

### Memory Issues
```bash
# Monitor memory
docker stats rdk-middleware

# If > 80% usage:
# 1. Reduce workers in docker-compose.rpi.yml (WORKERS=2)
# 2. Reduce concurrent iterations
# 3. Clear old screenshots/logs

# Cleanup unused Docker objects
docker system prune -a
```

### SSH Connection Issues
```bash
# Verify host network mode
docker inspect rdk-middleware | grep NetworkMode

# Test SSH from container
docker exec rdk-middleware ssh -o ConnectTimeout=5 <device-ip> "echo test"

# Check if Pi SSH is enabled
sudo systemctl status ssh
```

### Slow Performance
```bash
# 1. Check SD card speed
iozone -a -n 1m -g 2g -i 0 -i 1 -f /tmp/iozone.tmp

# 2. Use SSD if possible (much faster)
# 3. Check container resource limits

# 4. Monitor CPU usage
docker stats --no-stream rdk-middleware

# 5. Profile application
docker exec rdk-middleware python -m cProfile -s cumtime app.py
```

---

## Performance Optimization (8GB RPi)

### Recommended Settings
```yaml
# In .env or docker-compose.rpi.yml
WORKERS=3                    # Pi 4/5: 2-4, Pi 3: 2
WORKER_CLASS=gevent         # Async for concurrency
WORKER_CONNECTIONS=100      # Connection pool
TIMEOUT=300                 # 5 minutes
```

### Memory Optimization
```bash
# Monitor Python memory usage
docker exec rdk-middleware python -m memory_profiler app.py

# Set memory limit (optional)
docker update --memory=6gb rdk-middleware
```

---

## Deployment Checklist

- [ ] RPi 8GB with 64GB+ SD card/SSD
- [ ] Docker and Docker Compose installed
- [ ] Pi configured with static IP
- [ ] SSH enabled on Pi
- [ ] Firewall allows port 11078
- [ ] All device IPs added to devices.json
- [ ] Email config set (optional)
- [ ] Volumes properly mounted
- [ ] Systemd service configured
- [ ] Backups scheduled
- [ ] DNS/domain setup (if cloud access needed)
- [ ] Health checks passing
- [ ] First test job successful

---

## Quick Commands Reference

```bash
# Build image
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# Run container
docker run -d --name rdk-middleware --network host -v $(pwd):/app/data rdk-middleware:rpi

# View logs
docker logs -f rdk-middleware

# Execute command in container
docker exec rdk-middleware curl http://localhost:11078/health

# Stop container
docker stop rdk-middleware

# Start container
docker start rdk-middleware

# Remove container
docker rm rdk-middleware

# System cleanup
docker system prune -a --volumes
```

---

## Support & Monitoring

### Health Endpoint
```bash
curl http://localhost:11078/health
# Returns: {"status": "ok", "timestamp": "..."}
```

### Access Log
```bash
docker logs rdk-middleware | grep "GET\|POST\|PUT\|DELETE"
```

### Metrics
```
Memory Usage: docker stats
CPU Usage: docker stats
Disk I/O: iostat
Network: netstat
```

---

## Next Steps

1. **Build & Deploy** - Start with Quick Start option
2. **Monitor** - Use docker stats to verify resources
3. **Backup** - Set up automated backups
4. **Test** - Run first job through dashboard
5. **Optimize** - Adjust settings based on performance
6. **Maintain** - Regular updates and log cleanup

With 8GB RAM, your RPi will comfortably handle multiple concurrent device tests, background jobs, and extensive logging for months of operation!
