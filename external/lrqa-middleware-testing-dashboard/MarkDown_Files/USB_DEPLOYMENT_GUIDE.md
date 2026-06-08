# 🔌 USB DEPLOYMENT GUIDE FOR RASPBERRY PI 4

## Overview
This guide explains how to deploy the RDK-E Middleware QA Dashboard Docker application on a **new Raspberry Pi 4** using the USB deployment package.

**USB Setup:**
- **LEXAR (231.1G)** - Execution & logging data storage (for current RPi)
- **SanDisk (28.6G)** - Complete application & Docker files (for new RPi deployment)

---

## 📋 WHAT'S ON THE SanDisk USB

```
/media/lrqa/6077-248A/Enhancement/
├── app.py                           [Main Flask application]
├── requirements.txt                 [Python dependencies]
├── log_patterns.json                [Log pattern configurations]
├── 
├── 🐳 DOCKER FILES:
│   ├── Dockerfile.rpi.clean         [Docker image definition]
│   ├── docker-compose.rpi.clean.yml [Service orchestration]
│   ├── docker-entrypoint.sh         [Container startup script]
│   ├── .dockerignore.rpi.clean      [Build filter]
│   ├── rpi4-setup-complete.sh       ⭐ MAIN DEPLOYMENT SCRIPT
│   └── docker-verify-setup.sh       [Pre-deployment verification]
│
├── 📚 DOCUMENTATION:
│   ├── DOCKER_SETUP_GUIDE_RPI4.md
│   ├── DOCKER_QUICK_REFERENCE.txt
│   ├── DOCKER_COMPLETE_SETUP.md
│   └── USB_DEPLOYMENT_GUIDE.md      [This file]
│
├── 🛠️  CONFIGURATION FILES:
│   ├── config_commands.py           [Device commands]
│   ├── config_ir_blaster.py         [IR blaster settings]
│   ├── config_log_patterns.py       [Log patterns]
│   ├── config_timing.py             [Timing configuration]
│   ├── config_screenshot.py         [Screenshot settings]
│   ├── config_ssh_connection.py     [SSH settings]
│   ├── config_email.py              [Email configuration]
│   └── [other config files]
│
├── 📂 CORE DIRECTORIES:
│   ├── controllers/                 [Business logic]
│   ├── models/                      [Data models]
│   ├── services/                    [Background services]
│   ├── templates/                   [HTML templates]
│   ├── static/                      [CSS/JavaScript assets]
│   └── [other working directories]
```

---

## 🚀 QUICK START (4 STEPS)

### STEP 1: Prepare New Raspberry Pi 4

1. **Install Raspberry Pi OS:**
   - Download: https://www.raspberrypi.com/software/
   - Flash to microSD card (64GB+ recommended)
   - Boot RPi and connect to network

2. **Update System:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y git curl wget
   ```

3. **Enable SSH:**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > SSH > Enable
   # Or use:
   sudo systemctl enable ssh
   sudo systemctl start ssh
   ```

---

### STEP 2: Connect SanDisk USB to New RPi

1. **Insert SanDisk USB into new RPi**
2. **SSH into RPi:**
   ```bash
   ssh pi@<new-rpi-ip>
   ```

3. **Find USB mount point:**
   ```bash
   lsblk -o NAME,SIZE,LABEL
   # Look for your USB (e.g., sda1) with ~28-29G capacity
   ```

4. **Mount USB (if not auto-mounted):**
   ```bash
   sudo mkdir -p /mnt/usb-deployment
   sudo mount /dev/sda1 /mnt/usb-deployment
   cd /mnt/usb-deployment/Enhancement
   ```

---

### STEP 3: Run One-Command Deployment

```bash
# Make deployment script executable
chmod +x rpi4-setup-complete.sh

# Run the deployment
./rpi4-setup-complete.sh
```

**What this script does:**
- ✅ Checks system requirements
- ✅ Installs Docker & Docker Compose (if needed)
- ✅ Verifies project files
- ✅ Builds optimized Docker image
- ✅ Starts the application
- ✅ Verifies health checks
- ✅ Displays access URLs

**Expected duration:** 10-15 minutes (first time)

---

### STEP 4: Access Dashboard

After the script completes, access the dashboard:

```bash
http://<new-rpi-ip>:11078
```

**Configuration:** Port 11078 (customizable in docker-compose.rpi.clean.yml)

---

## 📂 DEPLOYMENT OPTIONS

### Option A: Deploy from USB Directly (Simplest)
**Pros:** Fast, requires least space, direct from USB
**Cons:** Application runs slower from USB

```bash
# SSH to new RPi with USB mounted
cd /mnt/usb-deployment/Enhancement
chmod +x rpi4-setup-complete.sh
./rpi4-setup-complete.sh
```

---

### Option B: Copy to Home Directory (Recommended)
**Pros:** Better performance, application on fast storage
**Cons:** Takes ~20GB home directory space

```bash
# SSH to new RPi with USB mounted
cp -r /mnt/usb-deployment/Enhancement ~/Enhancement-deploy
cd ~/Enhancement-deploy
chmod +x rpi4-setup-complete.sh
./rpi4-setup-complete.sh
```

---

### Option C: Copy Selective Files Only
**Pros:** Minimal disk usage (~1-2GB only)
**Cons:** Manual setup required

```bash
# Copy only essential files (skip large directories)
mkdir -p ~/Enhancement
cd /mnt/usb-deployment/Enhancement

# Copy core files
cp -r controllers models services templates static *.py *.json ~/Enhancement/
cp requirements.txt Dockerfile.rpi.clean docker-compose.rpi.clean.yml *.sh ~/Enhancement/

cd ~/Enhancement
chmod +x rpi4-setup-complete.sh
./rpi4-setup-complete.sh
```

---

## 🔍 VERIFY DEPLOYMENT

### Pre-Deployment Verification (Optional)
Before running the main setup:

```bash
cd /mnt/usb-deployment/Enhancement
chmod +x docker-verify-setup.sh
./docker-verify-setup.sh

# Output shows:
# - Required files present/missing
# - Python packages available
# - System requirements met
# - Log patterns configuration valid
```

---

## 📊 SYSTEM REQUIREMENTS

| Component | Minimum | Recommended | Optimal |
|-----------|---------|-------------|---------|
| RAM | 2GB | 4GB | 8GB |
| Storage | 32GB | 64GB | 128GB+ |
| CPU | RPi4 2GB | RPi4 4GB | RPi4 8GB |
| Network | WiFi | Gigabit Ethernet | Ethernet SSD |

---

## 🐳 DOCKER AFTER DEPLOYMENT

### View Application Logs
```bash
docker logs -f rdk-middleware-dashboard
# or
docker-compose -f docker-compose.rpi.clean.yml logs -f
```

### Check Container Status
```bash
docker ps
docker stats rdk-middleware-dashboard
```

### Restart Application
```bash
docker-compose -f docker-compose.rpi.clean.yml restart
```

### Stop Application
```bash
docker-compose -f docker-compose.rpi.clean.yml stop
```

### Update Application Code
```bash
# Edit files in ~/Enhancement/

# Rebuild image
docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean .

# Restart
docker-compose -f docker-compose.rpi.clean.yml restart

# Data persists in volumes!
```

---

## 💾 DATA PERSISTENCE

### Docker Volumes
Application data is stored in Docker volumes:

```bash
# View volumes
docker volume ls | grep rdk

# Backup volumes
docker run --rm -v app_data:/data -v ~/backup:/backup \
  alpine tar czf /backup/app_data_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v app_data:/data -v ~/backup:/backup \
  alpine tar xzf /backup/app_data_backup.tar.gz -C /data
```

### Connect LEXAR USB for Execution Data
Once the new RPi application is running, you can connect the LEXAR USB to store:
- Execution logs
- Screenshots
- Test results
- Iteration data

**Mount LEXAR USB:**
```bash
sudo mkdir -p /mnt/lexar-data
sudo mount /dev/sdb1 /mnt/lexar-data
```

---

## 🔧 CUSTOMIZATION

### Change Port (Default: 11078)
Edit `docker-compose.rpi.clean.yml`:
```yaml
services:
  rdk-middleware-dashboard:
    ports:
      - "9000:11078"  # Change 9000 to desired port
```

Then restart:
```bash
docker-compose -f docker-compose.rpi.clean.yml restart
```

### Adjust Resource Limits
Edit `docker-compose.rpi.clean.yml` for 8GB RPi:
```yaml
services:
  rdk-middleware-dashboard:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1024M
```

### Enable Email Notifications
Edit `docker-compose.rpi.clean.yml` - uncomment and configure:
```yaml
environment:
  FLASK_EMAIL_ENABLED: "true"
  FLASK_EMAIL_SMTP_SERVER: "your-smtp-server"
  FLASK_EMAIL_SMTP_PORT: "587"
  FLASK_EMAIL_USERNAME: "your-email"
  FLASK_EMAIL_PASSWORD: "your-password"
```

---

## ⚠️ TROUBLESHOOTING

### Issue: "USB Not Mounted"
```bash
# Check USB connection
lsblk
# Manually mount if needed
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb
```

### Issue: "Not enough space"
```bash
# Check available space
df -h
# Use Option C (selective copy) instead
```

### Issue: "Docker not found"
```bash
# The setup script installs Docker automatically
# But if manual install needed:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
```

### Issue: "Container won't start"
```bash
# Check logs
docker logs rdk-middleware-dashboard | tail -50

# Check health
docker ps -a | grep rdk-middleware-dashboard

# Restart
docker-compose -f docker-compose.rpi.clean.yml restart
```

### Issue: "Slow performance"
```bash
# Verify resources aren't maxed
docker stats rdk-middleware-dashboard

# Check disk space
df -h

# Ensure no other heavy processes
top
```

---

## 📝 POST-DEPLOYMENT CHECKLIST

After successful deployment:

- [ ] Dashboard accessible at http://<rpi-ip>:11078
- [ ] All UI elements loading correctly
- [ ] Can connect to devices via SSH
- [ ] Log patterns available (Check Available Logs method)
- [ ] Execution methods/tests function properly
- [ ] Screenshots/results saving correctly
- [ ] No Docker warnings/errors in logs
- [ ] Memory/CPU usage within normal range
- [ ] Ready for production testing

---

## 🆘 ADDITIONAL HELP

### Read Documentation
```bash
cat DOCKER_SETUP_GUIDE_RPI4.md      # Full setup guide (500+ lines)
cat DOCKER_QUICK_REFERENCE.txt      # Commands reference
cat DOCKER_COMPLETE_SETUP.md        # Architecture overview
```

### View Setup Logs
```bash
cat rpi4-setup-complete.sh          # Review setup script commands
./docker-verify-setup.sh             # Run verification checks
docker-compose config               # Verify Docker Compose config
```

### SSH to Container
```bash
docker exec -it rdk-middleware-dashboard bash
# Now you can inspect files inside the container
```

---

## 🎯 QUICK COMMANDS REFERENCE

```bash
# Start deployment
./rpi4-setup-complete.sh

# View logs
docker logs -f rdk-middleware-dashboard

# Check status
docker ps

# Monitor resources
docker stats

# Restart app
docker-compose restart

# Stop app
docker-compose stop

# Update and restart
docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean .
docker-compose restart

# SSH into container
docker exec -it rdk-middleware-dashboard bash

# View Docker volumes
docker volume ls

# Access dashboard
http://<new-rpi-ip>:11078
```

---

## 📞 SUPPORT

For detailed troubleshooting, see:
- **DOCKER_SETUP_GUIDE_RPI4.md** - Complete setup documentation
- **DOCKER_QUICK_REFERENCE.txt** - Command quick reference
- **docker-verify-setup.sh** - Validation tool

---

## ✨ Summary

You now have a complete deployment package on the SanDisk USB:

1. **Full application code** with all latest changes
2. **Docker infrastructure** optimized for Raspberry Pi 4
3. **Automated setup script** for one-command deployment
4. **Comprehensive documentation** for reference

**Next Steps:**
1. Connect SanDisk USB to new Raspberry Pi 4
2. SSH into new RPi
3. Navigate to USB-mounted Enhancement directory
4. Run: `./rpi4-setup-complete.sh`
5. Access dashboard at: `http://<new-rpi-ip>:11078`

**Expected time:** 10-15 minutes for complete deployment

---

**Version:** 2.0 (RPi 4 USB Deployment)  
**Status:** Production Ready  
**Last Updated:** 2026-04-17
