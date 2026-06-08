# R-Pi 4 Complete Deployment & Setup Guide

## Overview

This guide provides complete instructions for deploying the **LRQA Middleware Dashboard** with **encrypted Python code (PyArmor)** to a fresh Raspberry Pi 4.

### What You'll Get
✓ Encrypted Docker image with protected Python code  
✓ Automated deployment scripts  
✓ Virtual environment execution  
✓ Background service with auto-restart  
✓ USB-based deployment for offline installation  

---

## Files Provided

| File | Type | Purpose |
|------|------|---------|
| `Dockerfile.pyarmor.prod` | Docker | Multi-stage encrypted build configuration |
| `docker-compose.pyarmor.yml` | Docker Compose | Production Docker Compose setup |
| `rpi4-deploy.sh` | Shell Script | **PRIMARY**: Automated deployment (recommended) |
| `rpi4-setup-assistant.py` | Python Script | Interactive setup wizard |
| `PYARMOR_ENCRYPTED_DOCKER_GUIDE.md` | Documentation | Detailed PyArmor setup guide |
| `USB_DEPLOYMENT_GUIDE.md` | Documentation | USB transfer and deployment guide |

---

## Quick Start (3 Steps)

### Step 1: Prepare USB Drive

**On your local machine (with Docker):**

```bash
# Navigate to project
cd /path/to/lrqa-middleware

# Wait for Docker build to complete, then:
sudo docker save lrqa-middleware:encrypted-latest | gzip > lrqa-middleware-encrypted.tar.gz

# Copy to USB
# Insert USB drive and run:
sudo cp lrqa-middleware-encrypted.tar.gz /media/usb/
sudo cp rpi4-deploy.sh /media/usb/
sudo cp rpi4-setup-assistant.py /media/usb/
sudo chmod +x /media/usb/*.sh /media/usb/*.py

# Verify (should be ~200-300MB image + scripts)
ls -lh /media/usb/

# Eject USB safely
sudo umount /media/usb
```

### Step 2: Boot R-Pi 4 & Mount USB

**On R-Pi 4:**

```bash
# SSH into R-Pi 4
ssh pi@raspberry-pi.local
# or
ssh pi@<R-Pi-IP>

# Mount USB drive
mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Verify
ls -l /media/usb/
```

### Step 3: Deploy Application

**Choose ONE method:**

#### Method A: Automated Deployment (Recommended)
```bash
bash /media/usb/rpi4-deploy.sh
```

This automates:
- System updates
- Docker installation
- Docker image loading
- App directory setup
- Environment configuration
- Container startup
- Auto-start configuration
- Health verification

#### Method B: Interactive Setup
```bash
python3 /media/usb/rpi4-setup-assistant.py
```

Provides:
- Step-by-step guidance
- Interactive configuration
- Health checks
- Troubleshooting help

---

## Full Manual Deployment (Advanced)

If you prefer control over each step:

### 1. Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Install Docker
```bash
# Official Docker for Debian/Raspberry Pi
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

### 3. Add User to Docker Group
```bash
sudo usermod -aG docker $USER
newgrp docker
# or logout and login
```

### 4. Load Docker Image
```bash
# From USB
sudo docker load < /media/usb/lrqa-middleware-encrypted.tar.gz

# Verify
sudo docker images | grep lrqa-middleware
```

### 5. Create Application Directories
```bash
APP_DIR="/opt/middleware"
sudo mkdir -p $APP_DIR/{iteration_logs,screenshots,device_logs,logs}
sudo chown -R $USER:$USER $APP_DIR
chmod 755 $APP_DIR/*
```

### 6. Configure Environment
```bash
cat > /opt/middleware/.env << 'EOF'
FLASK_ENV=production
FLASK_APP=app.py
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PYARMOR_DEBUG=0

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
EOF

chmod 600 /opt/middleware/.env
```

### 7. Start Container
```bash
sudo docker run -d \
  --name lrqa-middleware \
  --restart=unless-stopped \
  -p 11078:11078 \
  -v /opt/middleware/iteration_logs:/app/iteration_logs:rw \
  -v /opt/middleware/screenshots:/app/screenshots:rw \
  -v /opt/middleware/device_logs:/app/device_logs:rw \
  --env-file /opt/middleware/.env \
  -e PYTHONUNBUFFERED=1 \
  --memory=1g \
  --cpus=2 \
  lrqa-middleware:encrypted-latest
```

### 8. Verify Startup
```bash
# Check if running
sudo docker ps | grep lrqa-middleware

# View logs
sudo docker logs -f lrqa-middleware

# Test health endpoint
curl http://localhost:11078/health

# Access web UI
# Browser: http://<R-Pi-IP>:11078
```

### 9. Setup Auto-Start (Optional)
```bash
sudo tee /etc/systemd/system/lrqa-middleware.service > /dev/null << 'EOF'
[Unit]
Description=LRQA Middleware Docker Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=unless-stopped
RestartSec=5
ExecStart=/usr/bin/docker start -a lrqa-middleware
ExecStop=/usr/bin/docker stop lrqa-middleware
User=root

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lrqa-middleware.service
sudo systemctl start lrqa-middleware.service
```

---

## Running in Virtual Environment (Alternative)

If you prefer NOT to use Docker:

### 1. Install Python & Dependencies

```bash
sudo apt-get install -y python3-venv python3-pip git

# Create virtual environment
python3 -m venv /opt/middleware/venv

# Activate venv
source /opt/middleware/venv/bin/activate

# Copy application code
cp -r /media/usb/app /opt/middleware/

# Install dependencies
cd /opt/middleware/app
pip install -r requirements.txt

# Run application
python app.py
```

### 2. Run as Background Service

```bash
# Create systemd service
sudo tee /etc/systemd/system/lrqa-middleware-venv.service > /dev/null << 'EOF'
[Unit]
Description=LRQA Middleware (Virtual Env)
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/middleware/app
Environment="PATH=/opt/middleware/venv/bin"
ExecStart=/opt/middleware/venv/bin/python app.py
Restart=unless-stopped
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lrqa-middleware-venv.service
sudo systemctl start lrqa-middleware-venv.service
```

### 3. View Logs
```bash
# Real-time logs
sudo journalctl -u lrqa-middleware-venv -f

# Last 100 lines
sudo journalctl -u lrqa-middleware-venv -n 100
```

---

## Application Management

### Docker-Based Deployment

```bash
# View logs
sudo docker logs -f lrqa-middleware

# Check status
sudo docker ps

# Stop
sudo docker stop lrqa-middleware

# Start
sudo docker start lrqa-middleware

# Restart
sudo docker restart lrqa-middleware

# Remove container
sudo docker rm lrqa-middleware

# View resource usage
sudo docker stats lrqa-middleware
```

### Virtual Environment Deployment

```bash
# View logs
sudo journalctl -u lrqa-middleware-venv -f

# Check status
sudo systemctl status lrqa-middleware-venv

# Stop
sudo systemctl stop lrqa-middleware-venv

# Start
sudo systemctl start lrqa-middleware-venv

# Restart
sudo systemctl restart lrqa-middleware-venv

# View system resources
top
```

---

## Configuration

### Environment Variables

Edit `/opt/middleware/.env` (Docker) or `/opt/middleware/app/.env` (venv):

```bash
nano /opt/middleware/.env
```

Key variables:
- `FLASK_PORT=11078`: Application port
- `SMTP_HOST`: Email server (default: smtp.gmail.com)
- `SENDER_EMAIL`: Your email address
- `SENDER_PASSWORD`: Email app-specific password
- `PYARMOR_DEBUG=0`: Set to 1 for debugging

### Restart After Changes
```bash
# Docker
sudo docker restart lrqa-middleware

# venv
sudo systemctl restart lrqa-middleware-venv
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check Docker logs
sudo docker logs lrqa-middleware

# Check if port is in use
sudo lsof -i :11078

# Kill process on port
sudo kill -9 <PID>

# Check disk space
df -h

# Check memory
free -m
```

### Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply immediately
newgrp docker

# Or logout and back in
```

### USB Not Detected

```bash
# List devices
lsblk

# Try different mount points
sudo mount /dev/sdb1 /media/usb
sudo mount /dev/sdc1 /media/usb
```

### Application Slow/Unresponsive

```bash
# Check resource usage
sudo docker stats
free -m
df -h

# Increase Docker limits if needed
# Edit docker run command to increase --memory or --cpus
```

### PyArmor Errors

```bash
# Enable debugging
sudo docker run -e PYARMOR_DEBUG=1 ...

# Check logs for PyArmor initialization
sudo docker logs lrqa-middleware | grep -i pyarmor

# Verify PyArmor is installed
python -m pip show pyarmor
```

---

## Performance Optimization

### For R-Pi 4 with Limited Resources

#### Reduce Docker Resource Limits
```bash
# Less aggressive defaults:
--memory=512m \
--cpus=1
```

#### Disable Debug Logging
```bash
# In .env
PYARMOR_DEBUG=0
```

#### Use Virtual Environment Instead of Docker
```bash
# Lighter footprint, no containerization overhead
source /opt/middleware/venv/bin/activate
```

---

## Security Considerations

### Code Protection
✓ Python bytecode encrypted with PyArmor  
✓ Not human-readable even if container compromised  
✓ Requires Python runtime + PyArmor to execute  

### Container Security
✓ Resource limits enforced (memory, CPU)  
✓ Restart policy limits crash loops  
✓ Health checks enabled  

### Data Security
✓ Environment variables for sensitive data  
✓ Logs stored locally (portable)  
✓ No hardcoded credentials  

### Network Security
✓ Run on private network when possible  
✓ Use firewall rules to restrict access  
✓ Update R-Pi 4 OS regularly  

---

## Monitoring

### Docker-Based

```bash
# Real-time monitoring
watch 'sudo docker stats lrqa-middleware'

# Log rotation (automatic in Docker Compose)
sudo docker logs --tail 1000 lrqa-middleware

# Historical logs (if configured)
cat /opt/middleware/logs/*.log
```

### Virtual Environment-Based

```bash
# System monitoring
top
htop (if installed)

# Application logs
tail -f /opt/middleware/logs/*.log
journalctl -u lrqa-middleware-venv -f
```

---

## Backup & Recovery

### Create Backup
```bash
# Backup application data
sudo tar -czf /backup/middleware-backup-$(date +%Y%m%d).tar.gz /opt/middleware

# Backup Docker image
sudo docker save lrqa-middleware:encrypted-latest | gzip > /backup/lrqa-middleware-encrypted.tar.gz
```

### Restore from Backup
```bash
# Extract files
sudo tar -xzf /backup/middleware-backup-*.tar.gz -C /

# Load Docker image
sudo docker load < /backup/lrqa-middleware-encrypted.tar.gz

# Restart service
sudo docker restart lrqa-middleware
```

---

## FAQ

**Q: Can I run without Docker?**  
A: Yes, use the virtual environment setup instead. See "Running in Virtual Environment" section.

**Q: How much disk space do I need?**  
A: Minimum 2GB free (1GB for Docker image + overlay); 4GB+ recommended.

**Q: Will the code be visible if I SSH into the container?**  
A: No. PyArmor encrypts bytecode; even inside the container, code is not human-readable.

**Q: Can I access the web UI from another computer?**  
A: Yes. Use `http://<R-Pi-IP>:11078` from any computer on the network.

**Q: How do I update the application?**  
A: Rebuild Docker image or update virtual environment code, then restart service.

**Q: Is PyArmor required for venv setup?**  
A: No. PyArmor is Docker-only. Venv setup has unencrypted code but lighter footprint.

---

## Support & Documentation

- **PyArmor Guide:** See `PYARMOR_ENCRYPTED_DOCKER_GUIDE.md`
- **USB Setup:** See `USB_DEPLOYMENT_GUIDE.md`
- **Docker Compose:** See `docker-compose.pyarmor.yml`
- **Application Logs:** Check `/opt/middleware/logs/` or `docker logs`

---

## Next Steps

1. ✓ Copy files to USB (if starting from scratch)
2. ✓ Boot R-Pi 4 and mount USB
3. ✓ Run deployment script: `bash rpi4-deploy.sh`
4. ✓ Configure .env with email credentials
5. ✓ Access web UI at `http://<R-Pi-IP>:11078`
6. ✓ Monitor logs and verify operation

---

**Deployment Date:** _(Fill in after deployment)_  
**R-Pi 4 Hostname:** _(Fill in)_  
**Application URL:** `http://<hostname-or-IP>:11078`  

---
