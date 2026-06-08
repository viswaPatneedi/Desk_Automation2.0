# USB DEPLOYMENT PACKAGE - COMPLETE DOCUMENTATION

## 🎯 OVERVIEW

This USB package contains a complete, production-ready deployment of the RDK-E Middleware QA Dashboard application optimized for Raspberry Pi 4.

**What You Get:**
- ✅ Complete application source code
- ✅ Docker containerization with ARM/ARM64 optimization
- ✅ Automated one-command deployment
- ✅ Pre-configured volumes for data persistence
- ✅ Health checks and monitoring
- ✅ Comprehensive documentation

**Deployment Time:** 10-15 minutes (first time)  
**Storage Required:** 20-25GB on new RPi  
**No Execution Data:** Clean build - no legacy logs/screenshots

---

## 📋 USB PACKAGE CONTENTS

### Application Core
```
Enhancement/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── log_patterns.json         # Log pattern database (FIXED)
├── wsgi.py                   # WSGI entry point
└── [other app files]
```

### Docker Infrastructure
```
├── Dockerfile.rpi.clean                    # Docker image definition
│   ├── Base: python:3.11-slim (ARM optimized)
│   ├── System packages: Tesseract, SSH, image processing libs
│   ├── Python dependencies from requirements.txt
│   ├── Exposed port: 11078
│   └── Health check: curl http://localhost:11078
│
├── docker-compose.rpi.clean.yml            # Service orchestration
│   ├── Service: rdk-middleware-dashboard
│   ├── Image: rdk-middleware-dashboard:rpi4-clean
│   ├── Port mapping: 11078:11078
│   ├── Volumes: app_data, reference_screens
│   ├── Resources: 1 CPU, 512MB RAM (adjustable)
│   ├── Health check: HTTP + 3 retries
│   └── Logging: JSON driver with rotation
│
├── docker-entrypoint.sh                    # Container startup
│   ├── Validates Python & config files
│   ├── Creates /app/data directory structure
│   ├── Initializes JSON files (devices, jobs, sequences)
│   ├── Exports environment variables
│   ├── Color-coded logging
│   └── Executes gunicorn
│
├── .dockerignore.rpi.clean                 # Build filter
│   └── Excludes: logs, screenshots, backups, .git, etc.
│       (Clean build only, no execution data)
│
├── rpi4-setup-complete.sh                  # ⭐ MAIN DEPLOYMENT SCRIPT
│   ├── 11-step automated workflow
│   ├── System requirements check
│   ├── Docker & Docker Compose installation
│   ├── Project file verification
│   ├── Image build with progress
│   ├── Service startup
│   ├── Health verification
│   ├── Access URL display
│   └── Colored progress output
│
└── docker-verify-setup.sh                  # Pre-deployment validator
    ├── 10 comprehensive checks
    ├── File presence verification
    ├── Application structure validation
    ├── Docker installation check
    ├── Python dependencies verification
    ├── Log patterns JSON validation
    ├── System requirements assessment
    └── Detailed pass/fail reporting
```

### Configuration Files  
```
├── config_commands.py           # Device commands & methods
├── config_ir_blaster.py         # IR blaster settings
├── config_log_patterns.py       # Log pattern configuration
├── config_timing.py             # Timing settings
├── config_screenshot.py         # Screenshot configuration
├── config_ssh_connection.py     # SSH connection settings
├── config_email.py              # Email/SMTP settings
├── config_deployment.py         # Deployment configuration
├── config_ai_vision.py          # AI vision settings
└── [other config files]
```

### Application Components
```
├── controllers/                 # Business logic
│   ├── device_controller.py
│   ├── test_controller.py
│   ├── job_controller.py
│   └── [other controllers]
│
├── models/                      # Data models & persistence
│   ├── device.py
│   ├── test_result.py
│   ├── job.py
│   └── [other models]
│
├── services/                    # Background services
│   ├── log_service.py           # Log streaming (SSE)
│   ├── queue_service.py         # Job queue management
│   ├── device_service.py        # Device operations
│   └── [other services]
│
├── templates/                   # HTML templates
│   ├── index.html               # Main dashboard
│   ├── device.html
│   ├── test.html
│   └── [other templates]
│
├── static/                      # CSS/JavaScript
│   ├── css/
│   ├── js/
│   └── [other assets]
│
└── [other working directories]
```

### Documentation
```
├── USB_DEPLOYMENT_GUIDE.md              # Full deployment guide
├── USB_QUICK_START.txt                  # Quick reference
├── USB_DEPLOYMENT_README.md             # This file
├── DOCKER_SETUP_GUIDE_RPI4.md           # Comprehensive guide
├── DOCKER_QUICK_REFERENCE.txt           # Commands reference
├── DOCKER_COMPLETE_SETUP.md             # Architecture overview
└── [other documentation]
```

---

## 🚀 DEPLOYMENT WORKFLOW

### Pre-Deployment (On Your Laptop/PC)

1. **Insert SanDisk USB into current RPi**
   - Verify copy is complete: `du -sh /media/lrqa/6077-248A/Enhancement/`
   - Should be ~18GB total

2. **Eject and remove SanDisk USB**
   ```bash
   sudo umount /media/lrqa/6077-248A
   ```

3. **Install Raspberry Pi OS on new RPi**
   - Download: https://www.raspberrypi.com/software/
   - Use Raspberry Pi Imager to flash to microSD
   - Boot new RPi and connect to network

---

### Deployment (On New Raspberry Pi 4)

#### Phase 1: Setup (5 minutes)
1. SSH to new RPi
2. Insert SanDisk USB
3. Mount USB: `sudo mount /dev/sda1 /mnt/usb`
4. Navigate: `cd /mnt/usb/Enhancement`

#### Phase 2: Deployment (10-15 minutes - Automated)
```bash
chmod +x rpi4-setup-complete.sh
./rpi4-setup-complete.sh
```

**Script does automatically:**
- ✅ Checks system (RAM, CPU, disk)
- ✅ Installs Docker & Docker Compose
- ✅ Verifies project files
- ✅ Cleans old containers
- ✅ Builds Docker image (5-10 min)
- ✅ Starts services
- ✅ Verifies health
- ✅ Displays URLs

#### Phase 3: Access (Immediate)
```
Dashboard: http://<new-rpi-ip>:11078
```

---

## 📊 ARCHITECTURE

```
┌─────────────────────────────────────────────┐
│  Raspberry Pi 4 (New Deployment)            │
├─────────────────────────────────────────────┤
│                                             │
│  ┌────────────────────────────────────┐   │
│  │  Docker Container                  │   │
│  │  (rdk-middleware-dashboard)        │   │
│  │                                    │   │
│  │  ┌──────────────────────────────┐ │   │
│  │  │  Python 3.11 + Flask         │ │   │
│  │  │  - Controllers               │ │   │
│  │  │  - Models                    │ │   │
│  │  │  - Services                  │ │   │
│  │  │  - API Endpoints             │ │   │
│  │  └──────────────────────────────┘ │   │
│  │                                    │   │
│  │  ┌──────────────────────────────┐ │   │
│  │  │  Gunicorn + Gevent           │ │   │
│  │  │  (WSGI Server)               │ │   │
│  │  └──────────────────────────────┘ │   │
│  │                                    │   │
│  └────────────────────────────────────┘   │
│           ↕                                 │
│  ┌────────────────────────────────────┐   │
│  │  Docker Volumes                    │   │
│  │  - app_data (execution logs)       │   │
│  │  - reference_screens (validation)  │   │
│  └────────────────────────────────────┘   │
│           ↕                                 │
│  ┌────────────────────────────────────┐   │
│  │  Network                           │   │
│  │  Port 11078 (HTTP)                │   │
│  └────────────────────────────────────┘   │
│                                             │
│  Resources (Adjustable):                    │
│  - CPU: 1 core (configurable)              │
│  - Memory: 512MB (configurable)            │
│  - Storage: Docker volumes                 │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🔐 SECURITY NOTES

### Default Configuration
- Fine for **development/testing**
- Basic security settings
- Local network recommended

### Production Recommendations
Before going to production:

1. **Generate new SECRET_KEY**
   ```python
   import secrets
   secrets.token_hex(32)
   ```

2. **Set strong passwords**
   - SMTP password for email notifications
   - Database credentials (if used)
   - SSH keys for device access

3. **Configure firewall**
   ```bash
   sudo ufw enable
   sudo ufw allow 22/tcp      # SSH
   sudo ufw allow 11078/tcp   # Dashboard
   ```

4. **Use HTTPS reverse proxy**
   - Nginx or Traefik recommended
   - SSL certificates (Let's Encrypt)

5. **Set up backups**
   - Docker volume backups
   - Automated snapshot schedule
   - Off-site storage

6. **Monitor logs**
   - Regular log review
   - Anomaly detection
   - Error alerting

---

## 💾 DATA PERSISTENCE

### Docker Volumes
Application data persists in Docker volumes:

```bash
# View all volumes
docker volume ls | grep rdk

# Inspect volume
docker volume inspect app_data

# Backup volume
docker run --rm -v app_data:/data \
  -v ~/backups:/backup \
  alpine tar czf /backup/app_data.tar.gz -C /data .

# Restore volume
docker run --rm -v app_data:/data \
  -v ~/backups:/backup \
  alpine tar xzf /backup/app_data.tar.gz -C /data
```

### Connecting LEXAR USB (Optional)
For execution data storage:

```bash
# Mount LEXAR USB
sudo mkdir -p /mnt/lexar-data
sudo mount /dev/sdb1 /mnt/lexar-data

# Link to Docker volume (if needed)
# or configure app to use specified path
```

---

## 🔧 CONFIGURATION & CUSTOMIZATION

### Change Dashboard Port
Edit `docker-compose.rpi.clean.yml`:
```yaml
ports:
  - "9000:11078"    # Change 9000 to your desired port
```

Then restart:
```bash
docker-compose -f docker-compose.rpi.clean.yml restart
```

### Adjust Resource Limits
For 8GB RPi (edit docker-compose.rpi.clean.yml):
```yaml
deploy:
  resources:
    limits:
      cpus: '2'           # Increase from '1'
      memory: 1024M       # Increase from 512M
```

### Enable Email Notifications
Set environment variables in docker-compose.rpi.clean.yml:
```yaml
environment:
  - FLASK_EMAIL_ENABLED=true
  - FLASK_EMAIL_SMTP_SERVER=smtp.gmail.com
  - FLASK_EMAIL_SMTP_PORT=587
  - FLASK_EMAIL_USERNAME=your-email@gmail.com
  - FLASK_EMAIL_PASSWORD=your-app-password
```

### Customize SSH Connection
Edit `config_ssh_connection.py`:
```python
SSH_PORT = 22              # Default SSH port
SSH_TIMEOUT = 30           # Connection timeout
SSH_KEEP_ALIVE_INTERVAL = 30
```

---

## 📈 MONITORING & MANAGEMENT

### View Application Logs
```bash
# Real-time logs
docker logs -f rdk-middleware-dashboard

# Docker Compose logs
docker-compose -f docker-compose.rpi.clean.yml logs -f

# Last 100 lines
docker logs --tail 100 rdk-middleware-dashboard

# Export logs to file
docker logs rdk-middleware-dashboard > /tmp/app.log 2>&1
```

### Check Container Status
```bash
# Running containers
docker ps

# All containers (including stopped)
docker ps -a

# Container details
docker inspect rdk-middleware-dashboard

# Health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Monitor Resources
```bash
# Real-time stats
docker stats rdk-middleware-dashboard

# One-time snapshot
docker stats --no-stream rdk-middleware-dashboard

# System resources
top
free -h
df -h
```

### Container Lifecycle

```bash
# Restart
docker-compose -f docker-compose.rpi.clean.yml restart

# Stop (graceful)
docker-compose -f docker-compose.rpi.clean.yml stop

# Start
docker-compose -f docker-compose.rpi.clean.yml up -d

# Remove (delete container, keep volumes)
docker-compose -f docker-compose.rpi.clean.yml down

# Remove everything including volumes
docker-compose -f docker-compose.rpi.clean.yml down -v
```

---

## 🛠️ UPDATE & MAINTENANCE

### Update Application Code
```bash
# Copy new files to Enhancement/
cp new-version/app.py ./app.py
# ... copy other files ...

# Rebuild Docker image
docker build -f Dockerfile.rpi.clean \
  -t rdk-middleware-dashboard:rpi4-clean .

# Restart with new image
docker-compose -f docker-compose.rpi.clean.yml restart

# ✅ Data in volumes persists automatically!
```

### Clean Up Old Images
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune
```

### Backup Before Updates
```bash
# Backup volume
docker run --rm \
  -v app_data:/data \
  -v ~/backups:/backup \
  alpine tar czf /backup/pre-update.tar.gz -C /data .

# Make backup immutable (optional)
chmod a-w ~/backups/pre-update.tar.gz
```

---

## ⚠️ TROUBLESHOOTING

### Common Issues & Solutions

#### "USB not mounting"
```bash
# Check device
lsblk
sudo apt install -y exfat-fuse exfat-utils  # If FAT32 issues

# Manually mount
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb
```

#### "Insufficient space"
```bash
# Check available space
df -h

# Consider:
# - Extending partition
# - Using external USB for volumes
# - Removing old Docker images
```

#### "Docker service not starting"
```bash
# Restart Docker daemon
sudo systemctl restart docker

# Check Docker status
sudo systemctl status docker

# View Docker logs
sudo journalctl -u docker -n 50
```

#### "Application crashes on startup"
```bash
# Check logs
docker logs -f rdk-middleware-dashboard | tail -100

# Verify config files exist
docker exec rdk-middleware-dashboard ls -la /app/

# Run verification
./docker-verify-setup.sh
```

#### "Out of memory"
```bash
# Check current usage
docker stats

# Increase memory limit in docker-compose.rpi.clean.yml
# Set up swap (if RPi with limited RAM)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### "Slow performance"
```bash
# Check resource limits
docker stats

# Check disk I/O
iostat -x 1 5

# If running from USB: copy to home directory
cp -r /mnt/usb/Enhancement ~/Enhancement-fast
```

#### "Network connectivity issues"
```bash
# Test network
ping 8.8.8.8
curl https://www.google.com

# Check Docker network
docker network ls
docker network inspect bridge

# Restart network
sudo systemctl restart networking
```

---

## 📞 SUPPORT & ADDITIONAL HELP

### Quick Reference Commands
```bash
# Deployment
./rpi4-setup-complete.sh

# Verification
./docker-verify-setup.sh

# Logs
docker logs -f rdk-middleware-dashboard

# Status
docker ps
docker stats

# Config
docker-compose config

# Rebuild
docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean .
docker-compose restart

# SSH into container
docker exec -it rdk-middleware-dashboard bash

# Access dashboard
http://<new-rpi-ip>:11078
```

### Documentation Files
- **USB_QUICK_START.txt** - Quick start guide (this format)
- **USB_DEPLOYMENT_GUIDE.md** - Full deployment guide
- **DOCKER_SETUP_GUIDE_RPI4.md** - Comprehensive setup (500+ lines)
- **DOCKER_QUICK_REFERENCE.txt** - Docker commands
- **DOCKER_COMPLETE_SETUP.md** - Architecture overview

### Additional Resources
- Docker docs: https://docs.docker.com/
- Raspberry Pi docs: https://www.raspberrypi.com/documentation/
- Flask docs: https://flask.palletsprojects.com/

---

## ✅ POST-DEPLOYMENT CHECKLIST

After successful deployment, verify:

- [ ] Dashboard accessible via browser
- [ ] All UI elements rendering correctly
- [ ] Device connection/SSH tests successful
- [ ] Log patterns loading ("Check Available Logs" works)
- [ ] Test methods/executions functioning
- [ ] Screenshots/results saving to volumes
- [ ] No Docker warnings in logs
- [ ] Resource usage within normal range
- [ ] Data volumes persisting across restarts
- [ ] Ready for production testing

---

## 🎉 SUMMARY

You have a complete, production-ready deployment package:

| Component | Status |
|-----------|--------|
| Application Code | ✅ Latest version included |
| Docker Infrastructure | ✅ ARM optimized |
| Automated Deployment | ✅ One-command setup |
| Documentation | ✅ Comprehensive |
| No Execution Data | ✅ Clean build |
| Data Persistence | ✅ Docker volumes |
| Production Ready | ✅ Health checks & monitoring |

**Next Steps:**
1. Connect SanDisk USB to new Raspberry Pi 4
2. SSH and mount USB
3. Run: `./rpi4-setup-complete.sh`
4. Access: `http://<new-rpi-ip>:11078`

**Expected Duration:** 10-15 minutes first time

---

**Version:** 2.0 (USB Deployment Package)  
**Status:** Production Ready  
**Last Updated:** 2026-04-17  
**Deployment Target:** Raspberry Pi 4 (2GB-8GB RAM)
