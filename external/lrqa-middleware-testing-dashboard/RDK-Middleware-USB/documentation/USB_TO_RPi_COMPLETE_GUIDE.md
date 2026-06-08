# Complete USB to New Raspberry Pi Deployment Guide

**Date:** April 13, 2026  
**Target:** Raspberry Pi 3/4/5 with Docker  
**Total Setup Time:** 45-90 minutes (depends on Pi model)

---

## TABLE OF CONTENTS
1. [Files to Copy to USB](#files-to-copy-to-usb)
2. [USB Preparation Steps](#usb-preparation-steps)
3. [Raspberry Pi Pre-Setup](#raspberry-pi-pre-setup)
4. [Transfer Files from USB](#transfer-files-from-usb)
5. [Installation Steps](#installation-steps)
6. [Configuration](#configuration)
7. [Startup & Verification](#startup--verification)
8. [Troubleshooting](#troubleshooting)

---

## FILES TO COPY TO USB

### Total Size: ~250MB (without runtime data)

### REQUIRED FILES & DIRECTORIES
```
✅ MUST COPY (Application Core):
  │
  ├── app.py                           [~20KB]  - Main Flask application
  ├── requirements.txt                 [~2KB]   - Python dependencies
  ├── Dockerfile.rpi                   [~5KB]   - Docker image definition
  ├── docker-compose.rpi.yml           [~3KB]   - Docker orchestration
  ├── docker-rpi-quickstart.sh         [~8KB]   - Installation script
  ├── .dockerignore                    [<1KB]   - Docker build optimization
  │
  ├── controllers/                     [~200KB] - Business logic layer
  │   ├── __init__.py
  │   ├── device_controller.py
  │   ├── job_controller.py
  │   ├── queue_controller.py
  │   ├── results_controller.py
  │   ├── test_controller.py
  │   └── (all other controller files)
  │
  ├── models/                          [~100KB] - Data models
  │   ├── __init__.py
  │   ├── device.py
  │   ├── job.py
  │   ├── user.py
  │   ├── result.py
  │   ├── sequence.py
  │   └── (all other model files)
  │
  ├── services/                        [~150KB] - Background processing
  │   ├── __init__.py
  │   ├── log_service.py
  │   ├── queue_service.py
  │   ├── recovery_service.py
  │   ├── test_service.py
  │   ├── email_service.py
  │   └── (all other service files)
  │
  ├── utils/                           [~80KB]  - Utility functions
  │   ├── __init__.py
  │   ├── device_lock_manager.py
  │   ├── ssh_connectivity_test.py
  │   ├── screenshot_utils.py
  │   ├── session_utils.py
  │   └── (all other utility files)
  │
  ├── templates/                       [~150KB] - HTML UI templates
  │   ├── index.html
  │   ├── dashboard.html
  │   ├── jobs.html
  │   ├── job_details.html
  │   ├── reboot_perf_results.html
  │   ├── deepsleep_results.html
  │   ├── components/
  │   └── (all other template files)
  │
  ├── static/                          [~200KB] - CSS, JS, images
  │   ├── css/
  │   │   ├── styles.css
  │   │   └── (all CSS files)
  │   ├── js/
  │   │   ├── lock-status-monitor.js
  │   │   ├── filter-state.js
  │   │   └── (all JS files)
  │   └── images/
  │       └── (all image assets)
  │
  ├── config_commands.py               [~5KB]   - Device commands
  ├── config_timing.py                 [~2KB]   - Timing parameters
  ├── config_ir_blaster.py             [~3KB]   - IR blaster config
  ├── config_screenshot.py             [~2KB]   - Screenshot settings
  ├── config_log_patterns.py           [~10KB]  - Log parsing patterns
  ├── config_ssh_connection.py         [~4KB]   - SSH connection settings
  ├── config_deployment.py             [~2KB]   - Deployment config
  ├── config_email.py                  [~3KB]   - Email service config
  ├── config_eta.py                    [~2KB]   - ETA calculation config
  ├── config_ai_vision.py              [~3KB]   - AI vision settings
  └── config_screen_validation.py      [~2KB]   - Screen validation config
```

### SHOULD COPY (Device & Test Configuration)
```
📋 IMPORTANT (Device/Sequence Config):
  │
  ├── devices.json                     - Device registry (SSH credentials, IPs)
  ├── saved_sequences.json             - Pre-saved test sequences
  ├── log_patterns.json                - Custom log patterns
  ├── system_commands.json             - System command configurations
  └── ir_keycodes.json                 - IR remote key mappings (if using IR)
```

### OPTIONAL - Include for Reference
```
📚 OPTIONAL (Documentation):
  │
  ├── DOCKER_RPI_SETUP.md              - Detailed Docker setup
  ├── DOCKER_RPI_8GB_DEPLOYMENT_GUIDE.md
  ├── README_RPi_SETUP.md              - RPi setup instructions
  └── USB_FOLDER_STRUCTURE.md          - Output folder organization
```

### DO NOT COPY (Too Large / Generated at Runtime)
```
❌ DO NOT INCLUDE:
  │
  ├── venv/                            - Python virtual environment (will be recreated)
  ├── logs/                            - Runtime logs
  ├── screenshots/                     - Captured screenshots (runtime generated)
  ├── iteration_logs/                  - Test execution logs
  ├── device_logs/                     - Device system logs
  ├── captured_images/                 - Reference images
  ├── .git/                            - Git history
  ├── __pycache__/                     - Python bytecode cache
  ├── *.pyc files                      - Python compiled files
  ├── SAM-CD-2GB/                      - Large reference folder
  ├── backups/                         - Old backup versions
  ├── updated_code/                    - Backup code
  └── node_modules/ (if any)           - Other large dependencies

Total exclusions: ~2-5GB
```

---

## USB PREPARATION STEPS

### ON YOUR DEVELOPMENT MACHINE (Linux/Mac/Windows WSL)

#### Step 1: Insert USB and Find Mount Point
```bash
# Linux/Mac
lsblk                           # Find USB device (usually /dev/sda1, /dev/sdb1)
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb   # Adjust device based on lsblk output

# Verify mount
df -h | grep usb
```

#### Step 2: Create Deployment Directory on USB
```bash
# Navigate to project directory
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement

# Create target deployment folder
mkdir -p /mnt/usb/rdk-middleware-deployment
```

#### Step 3: Copy All Required Files to USB

**Option A: Using Provided Script** (If you create this)
```bash
#!/bin/bash
# Copy all necessary files to USB

USB_PATH="/mnt/usb/rdk-middleware-deployment"

# Create directory structure
mkdir -p $USB_PATH

# Copy main app files
cp app.py $USB_PATH/
cp requirements.txt $USB_PATH/
cp Dockerfile.rpi $USB_PATH/
cp docker-compose.rpi.yml $USB_PATH/
cp docker-rpi-quickstart.sh $USB_PATH/
cp .dockerignore $USB_PATH/

# Copy all code directories
cp -r controllers $USB_PATH/
cp -r models $USB_PATH/
cp -r services $USB_PATH/
cp -r utils $USB_PATH/
cp -r templates $USB_PATH/
cp -r static $USB_PATH/

# Copy config files
cp config_*.py $USB_PATH/

# Copy configuration files
cp devices.json $USB_PATH/ 2>/dev/null
cp saved_sequences.json $USB_PATH/ 2>/dev/null
cp log_patterns.json $USB_PATH/ 2>/dev/null
cp system_commands.json $USB_PATH/ 2>/dev/null
cp ir_keycodes.json $USB_PATH/ 2>/dev/null

# Copy documentation
cp DOCKER_RPI_*.md $USB_PATH/
cp README_RPi_SETUP.md $USB_PATH/
cp USB_FOLDER_STRUCTURE.md $USB_PATH/

# Verify copy
echo "Copied $(find $USB_PATH -type f | wc -l) files to USB"
du -sh $USB_PATH

# Sync to USB
sync
echo "✓ USB deployment complete!"
```

**Option B: Manual Copy Commands** (One at a time)
```bash
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement

# Copy main files
cp app.py /mnt/usb/rdk-middleware-deployment/
cp requirements.txt /mnt/usb/rdk-middleware-deployment/
cp Dockerfile.rpi /mnt/usb/rdk-middleware-deployment/
cp docker-compose.rpi.yml /mnt/usb/rdk-middleware-deployment/
cp docker-rpi-quickstart.sh /mnt/usb/rdk-middleware-deployment/
cp .dockerignore /mnt/usb/rdk-middleware-deployment/

# Copy directories
cp -r controllers /mnt/usb/rdk-middleware-deployment/
cp -r models /mnt/usb/rdk-middleware-deployment/
cp -r services /mnt/usb/rdk-middleware-deployment/
cp -r utils /mnt/usb/rdk-middleware-deployment/
cp -r templates /mnt/usb/rdk-middleware-deployment/
cp -r static /mnt/usb/rdk-middleware-deployment/

# Copy config files
cp config_*.py /mnt/usb/rdk-middleware-deployment/

# Copy device config
cp devices.json /mnt/usb/rdk-middleware-deployment/
cp saved_sequences.json /mnt/usb/rdk-middleware-deployment/
cp log_patterns.json /mnt/usb/rdk-middleware-deployment/

# Sync and verify
sync
ls -lah /mnt/usb/rdk-middleware-deployment/
```

#### Step 4: Verify USB Contents
```bash
# Check file count
find /mnt/usb/rdk-middleware-deployment -type f | wc -l
# Should show ~100+ files

# Check total size
du -sh /mnt/usb/rdk-middleware-deployment/
# Should show ~200-300MB

# List top-level structure
ls -lah /mnt/usb/rdk-middleware-deployment/
```

#### Step 5: Safely Eject USB
```bash
# Linux
sudo umount /mnt/usb
sudo eject /dev/sda1

# Or check if ejectable
sudo umount /dev/sda1
```

---

## RASPBERRY PI PRE-SETUP

### Step 1: Fresh Raspberry Pi OS Installation

**Required:**
- Raspberry Pi 3 (1GB+), Pi 4 (2GB+), or Pi 5 (4GB+)
- 32GB+ microSD card (64GB recommended)
- USB adapter for microSD card
- A development PC (Windows/Mac/Linux)

**Install OS:**
1. Download **Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. Select:
   - OS: Raspberry Pi OS (64-bit) - Latest
   - Device: Your Pi model
   - Storage: microSD card
3. Click "Write" and wait 5 minutes
4. Insert microSD into Pi and power on

### Step 2: Initial Setup (First Boot)

**Option A: With Monitor & Keyboard**
1. Connect monitor, keyboard, mouse to Pi
2. Power on and complete setup wizard
3. Choose locale, timezone, password
4. Connect to WiFi or Ethernet

**Option B: Headless Setup (SSH only)**
```bash
# On your development machine, mount the SD card

# For Windows: Use WinSCP or PuTTY
# For Mac/Linux: Create SSH credentials file

# Mount Pi's boot partition
sudo mkdir -p /mnt/pi-boot
sudo mount /dev/sda1 /mnt/pi-boot  # Adjust device name

# Enable SSH by creating empty file
sudo touch /mnt/pi-boot/ssh

# Create wpa_supplicant.conf for WiFi (optional)
sudo cat > /mnt/pi-boot/wpa_supplicant.conf << EOF
country=US
update_config=1
ctrl_interface=/var/run/wpa_supplicant

network={
 ssid="YOUR_SSID"
 psk="YOUR_PASSWORD"
 key_mgmt=WPA-PSK
}
EOF

sudo umount /mnt/pi-boot
```

### Step 3: Connect to Raspberry Pi

```bash
# Find Pi's IP address (check your router or use nmap)
arp-scan --interface=eth0 --localnet  # Linux/Mac
nmap -sn 192.168.1.0/24  # Or use your subnet

# SSH into Pi (default credentials: pi / raspberry)
ssh pi@<YOUR_PI_IP>
# Enter password when prompted

# Update system
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 4: Create Data Directories

```bash
# Create necessary folders
mkdir -p ~/rdk-deployment
mkdir -p ~/rdk-app/{logs,screenshots,iteration_logs,device_logs}

# If using USB for output storage
sudo mkdir -p /media/pi/Lexar/Enhancement-output
sudo chown -R pi:pi /media/pi/Lexar/
```

---

## TRANSFER FILES FROM USB

### Step 1: Connect USB to Raspberry Pi

```bash
# SSH into Pi
ssh pi@<YOUR_PI_IP>

# Insert USB stick into Pi's USB port

# Verify USB is mounted
lsblk
# Look for something like: sda1 (or sdb1)

# If not auto-mounted, mount it manually
mkdir -p ~/usb-mount
sudo mount /dev/sda1 ~/usb-mount  # Adjust device name

# Verify contents
ls ~/usb-mount/rdk-middleware-deployment/
```

### Step 2: Copy Files from USB to Home Directory

```bash
# Navigate and copy
cd ~
cp -r ~/usb-mount/rdk-middleware-deployment ~/rdk-app

# Verify copy
ls -lah ~/rdk-app/
# Should show: app.py, requirements.txt, controllers/, models/, etc.

# Check file count
find ~/rdk-app -type f | wc -l
# Should match USB count (~100+ files)

# Optional: Create symlink for easy access
ln -s ~/rdk-app ~/Enhancement
```

---

## INSTALLATION STEPS

### STEP 1: Install Docker & Docker Compose (5-10 minutes)

```bash
# SSH into Pi (if not already connected)
ssh pi@<YOUR_PI_IP>

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify Docker
docker --version
# Output: Docker version 20.x.x or higher

# Add user to docker group (avoid using sudo for docker commands)
sudo usermod -aG docker pi

# Apply group changes
newgrp docker

# Verify docker works without sudo
docker ps
# Should show empty container list (no error)

# Install Docker Compose (plugin version - modern)
sudo apt-get install -y docker-compose-plugin

# Verify Docker Compose
docker compose version
# Output: Docker Compose version v2.x.x or higher
```

### STEP 2: Navigate to Application Directory

```bash
# Go to app directory
cd ~/rdk-app

# Verify essential files are present
ls -la | grep -E "app.py|requirements.txt|Dockerfile.rpi|docker-compose.rpi.yml"
# Should show all 4 files

# List directories
ls -la | grep "^d"
# Should show: controllers/, models/, services/, utils/, templates/, static/
```

### STEP 3: Create Configuration Files

#### 3.1 Create `.env` file for Email & Security

```bash
# Navigate to app directory
cd ~/rdk-app

# Create .env file
cat > .env << 'EOF'
# ===== EMAIL CONFIGURATION (Gmail SMTP) =====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password-16-chars

# ===== APPLICATION SECURITY =====
SECRET_KEY=change-me-to-random-secure-key-32-chars

# ===== PERFORMANCE TUNING =====
# Pi 3: WORKERS=1 | Pi 4: WORKERS=2 | Pi 5: WORKERS=4
WORKERS=2
TIMEOUT=300

# ===== LOGGING =====
LOG_LEVEL=INFO
FLASK_ENV=production

# ===== OPTIONAL FEATURES =====
# Enable when configured
ENABLE_AI_VISION=false
ENABLE_SCREENSHOT=true
ENABLE_DEEPSLEEP_RESULTS=true
EOF

# Verify .env was created
cat .env
```

**📌 EMAIL SETUP REQUIRED:**
1. Go to https://myaccount.google.com/apppasswords
2. Enable 2-Factor Authentication (if not already enabled)
3. Generate "App Password" for Mail:
   - Select: "Mail" and "Windows Computer" (or custom device)
   - Google will generate 16-character password (xxxx-xxxx-xxxx-xxxx)
4. Update `SENDER_PASSWORD` in `.env` above

#### 3.2 Verify device.json Configuration

```bash
# Check if devices.json exists
cat devices.json

# If empty, create template
cat > devices.json << 'EOF'
{
  "devices": [
    {
      "name": "Device-1",
      "ip": "10.0.0.100",
      "port": 10022,
      "username": "root",
      "password": "your-device-password",
      "model": "RDK Device",
      "status": "available",
      "description": "Test device 1"
    }
  ]
}
EOF

# Update with your actual device credentials
echo "⚠️ Update devices.json with your device IP addresses and credentials"
```

### STEP 4: Update Docker Compose for Your Pi Model

```bash
# Edit docker-compose.rpi.yml to set memory limits
nano docker-compose.rpi.yml

# Update WORKERS based on Pi model:
# Line: WORKERS=2

# Find section: deploy > resources > limits > memory
# Update based on your Pi:
# - Pi 3: memory: 1G
# - Pi 4: memory: 2G
# - Pi 5: memory: 4G

# Example (Pi 4 with 2GB RAM):
# deploy:
#   resources:
#     limits:
#       memory: 2G
#     reservations:
#       memory: 1G

# Save: Ctrl+X, then Y, then Enter (if using nano)
```

### STEP 5: Build Docker Image (30-90 minutes depending on Pi model)

⏱️ **Estimated Times:**
- Raspberry Pi 3: 60-90 minutes
- Raspberry Pi 4: 20-40 minutes  
- Raspberry Pi 5: 10-20 minutes

```bash
# Build the Docker image
cd ~/rdk-app

docker compose -f docker-compose.rpi.yml build

# Expected output:
# Step 1/XX : FROM python:3.11-slim
# Step 2/XX : WORKDIR /app
# ...
# Successfully built abc123def456

# If build fails, check:
docker logs rdk-middleware  # If container was started
docker compose logs         # For compose errors
```

**⚠️ This is the LONGEST step - be patient!**

### STEP 6: Start the Application

```bash
# Start the container
docker compose -f docker-compose.rpi.yml up -d

# Verify container is running
docker ps

# Check logs (first 50 lines)
docker logs rdk-middleware -n 50

# Follow logs in real-time (Ctrl+C to stop)
docker logs rdk-middleware -f

# Expected log output:
# [INFO] Starting Flask application...
# [INFO] Listening on 0.0.0.0:11078
```

### STEP 7: Test Application Accessibility

```bash
# Test from Pi itself
curl http://localhost:11078

# Get Pi's IP address
hostname -I
# Output: 192.168.1.100 (or similar)

# Test health endpoint
curl http://192.168.1.100:11078/health

# Expected response:
# {"status":"healthy","timestamp":"2026-04-13T12:00:00Z"}
```

---

## CONFIGURATION

### Post-Installation Verification

#### 1. Check Docker Container Status

```bash
# SSH into Pi
ssh pi@<YOUR_PI_IP>

# Verify container is running
docker ps | grep rdk-middleware
# Output should show: rdk-middleware (running)

# Check container health
docker inspect rdk-middleware | grep -A 5 "Health"

# View recent logs
docker logs rdk-middleware --tail 20
```

#### 2. Verify Application Files

```bash
# Enter container shell
docker exec -it rdk-middleware bash

# Verify application files inside container
ls -la /app/
# Should show: app.py, controllers/, models/, services/, utils/, templates/, static/

# Check Python version
python --version
# Should be 3.11.x

# Verify dependencies installed
pip list | grep -E "Flask|Paramiko|Gunicorn"
# Should show all required packages

# Exit container
exit
```

#### 3. Verify SSH Connectivity to Devices

```bash
# From Pi, test SSH connection to a device
ssh root@10.0.0.100 -p 10022  # Replace with your device

# If successful, you'll see device prompt or key exchange
# Ctrl+C to exit

# Check device connectivity from web UI:
# 1. Open http://<PI_IP>:11078 in browser
# 2. Go to Devices section
# 3. Click "Test Connection" for each device
```

#### 4. Enable Auto-Start on Boot

```bash
# Create a systemd service file
sudo bash -c 'cat > /etc/systemd/system/rdk-middleware.service << EOF
[Unit]
Description=RDK Middleware Testing Dashboard
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/docker compose -f ~/rdk-app/docker-compose.rpi.yml up
ExecStop=/usr/bin/docker compose -f ~/rdk-app/docker-compose.rpi.yml down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

# Enable service
sudo systemctl enable rdk-middleware.service

# Start service
sudo systemctl start rdk-middleware.service

# Check status
sudo systemctl status rdk-middleware.service

# View logs
sudo journalctl -u rdk-middleware.service -f
```

---

## STARTUP & VERIFICATION

### Access the Web Interface

1. **Find Your Pi's IP Address:**
   ```bash
   ssh pi@<YOUR_PI_IP>
   hostname -I
   ```

2. **Open in Browser:**
   ```
   http://<YOUR_PI_IP>:11078
   ```
   Example: `http://192.168.1.100:11078`

3. **Verify UI Elements:**
   - Dashboard loads without errors
   - Device list displays
   - Navigation menu appears
   - CSS/JS loads correctly

### Run Diagnostic Checks

```bash
# SSH into Pi
ssh pi@<YOUR_PI_IP>

# 1. Check Docker container
docker ps | grep rdk-middleware

# 2. Check memory usage
docker stats rdk-middleware --no-stream
# Compare with memory limit in docker-compose.rpi.yml

# 3. Check disk space
df -h ~/rdk-app

# 4. Check network connectivity
docker exec rdk-middleware ping -c 1 8.8.8.8  # Google DNS

# 5. View last 100 lines of app logs
docker logs rdk-middleware -n 100

# 6. Test web endpoint
curl -s http://localhost:11078/api/health | python -m json.tool
```

---

## TROUBLESHOOTING

### Problem 1: Docker Image Build Failed

**Symptom:** Build stops with error, often related to package installation

**Solutions:**
```bash
# Check Pi internet connection
ping -c 3 8.8.8.8

# Free up disk space
df -h
# Need at least 5GB free

# Clear Docker build cache
docker system prune -a

# Retry build with verbose output
docker compose -f docker-compose.rpi.yml build --no-cache

# Check for Pi model specific issues
uname -m  # Should be aarch64
cat /sys/firmware/devicetree/base/model  # Shows Pi model
```

### Problem 2: Container Won't Start

**Symptom:** `docker ps` shows container but it's not running

**Solutions:**
```bash
# Check container logs for errors
docker logs rdk-middleware

# Common errors:
# - Port 11078 already in use: Stop other services
# - OutOfMemory: Reduce WORKERS or increase Pi RAM
# - Missing files: Verify all files were copied

# Try restarting container
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d

# Check system resources
free -h        # RAM usage
df -h /        # Disk usage
docker stats   # Real-time stats
```

### Problem 3: Cannot Access Web Interface

**Symptom:** Browser shows "Connection refused" or "Unable to connect"

**Solutions:**
```bash
# 1. Verify container is running
docker ps
# If not listed, restart it

# 2. Check port is listening
docker exec rdk-middleware netstat -tlnp | grep 11078
# or
sudo netstat -tlnp | grep 11078

# 3. Test from Pi itself
curl http://localhost:11078
# Should return HTML

# 4. Check firewall (if enabled)
sudo ufw status
# If active, allow port 11078
sudo ufw allow 11078

# 5. Verify network connectivity
ping <ANOTHER_DEVICE_IP>  # Ping from Pi
ssh pi@<ANOTHER_DEVICE> "ping -c1 <PI_IP>"  # Ping Pi from other device

# 6. Check IP address
hostname -I  # On Pi
# Use this IP in browser
```

### Problem 4: Devices Not Connecting

**Symptom:** SSH connection tests fail, devices show "offline"

**Solutions:**
```bash
# 1. Verify devices.json has correct credentials
cat ~/rdk-app/devices.json | grep -E "ip|port|username"

# 2. Test SSH manually from Pi
ssh root@<DEVICE_IP> -p 10022  # Check port number
# If "Connection refused": Device port is wrong or device offline
# If "Permission denied": Password is wrong

# 3. Check SSH key-based auth (optional)
ssh -i ~/.ssh/id_rsa root@<DEVICE_IP> -p 10022

# 4. Verify network connectivity
ping <DEVICE_IP>
# If no response: Device unreachable, check network

# 5. Check SSH config
cat ~/rdk-app/config_ssh_connection.py
# Verify SSH timeout and retry settings
```

### Problem 5: High Memory Usage, Pi Freezes

**Symptom:** Docker stats show memory near limit, Pi becomes unresponsive

**Solutions:**
```bash
# 1. Reduce concurrent workers
docker exec -it rdk-middleware bash
# Edit: nano /app/.env
# Change: WORKERS=2  →  WORKERS=1

# 2. Lower memory limits
nano ~/rdk-app/docker-compose.rpi.yml
# Change: memory: 2G  →  memory: 1G

# 3. Restart container with new settings
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d

# 4. Monitor memory in real-time
docker stats --no-stream

# 5. Free up Pi system resources
sudo systemctl stop cups      # Stop print service (if not needed)
sudo systemctl stop bluetooth # Stop bluetooth (if not needed)
```

### Problem 6: Cannot Copy Files from USB

**Symptom:** "Permission denied" when copying from USB

**Solutions:**
```bash
# Check USB mount permissions
ls -la /media/pi/

# Fix permissions
sudo chown -R pi:pi /media/pi/Lexar/

# Re-mount USB with correct permissions
sudo umount /media/pi/Lexar/usb
sudo mount -o uid=pi,gid=pi /dev/sda1 /media/pi/Lexar/usb

# Retry copy
cp -r /media/pi/Lexar/usb/rdk-middleware-deployment ~/rdk-app
```

### Problem 7: Email Tests Fail

**Symptom:** Email sending fails, logs show SMTP error

**Solutions:**
```bash
# 1. Verify .env file
cat ~/rdk-app/.env | grep -E "SMTP|SENDER"

# 2. Check Gmail app password
# - Go to https://myaccount.google.com/apppasswords
# - Regenerate if needed
# - Update .env with new 16-char password

# 3. Test SMTP connection manually
docker exec rdk-middleware python -c "
import smtplib
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('your-email@gmail.com', 'your-app-password')
    print('✓ SMTP connection successful')
except Exception as e:
    print(f'✗ SMTP error: {e}')
"

# 4. Verify no firewall blocking SMTP
# Port 587 (TLS) or 465 (SSL) should be accessible

# 5. Restart email service
docker compose -f docker-compose.rpi.yml restart
```

### Emergency Restart Procedures

```bash
# 1. Soft Restart (Graceful)
docker compose -f docker-compose.rpi.yml restart

# 2. Hard Restart (Complete stop/start)
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d

# 3. Full System Restart
sudo reboot
# Pi will restart, container auto-starts if systemd service is enabled

# 4. Container Shell Access (for debugging)
docker exec -it rdk-middleware bash
# Then run commands inside container
# Type 'exit' to return to Pi shell
```

---

## QUICK REFERENCE - Installation Checklist

- [ ] Raspberry Pi OS installed on microSD card
- [ ] Pi powered on and connected to network
- [ ] SSH access verified
- [ ] USB stick formatted and files copied
- [ ] USB mounted on Pi and files transferred
- [ ] Docker & Docker Compose installed
- [ ] `.env` file created with email credentials
- [ ] `devices.json` updated with device details
- [ ] `docker-compose.rpi.yml` memory/worker settings adjusted
- [ ] Docker image built successfully
- [ ] Container started and running
- [ ] Web interface accessible at `http://<PI_IP>:11078`
- [ ] SSH connectivity tests passing
- [ ] Auto-start service enabled (optional)

---

## SUPPORT RESOURCES

- **Docker Logs:** `docker logs rdk-middleware -f`
- **Systemd Service:** `sudo systemctl status rdk-middleware.service`
- **System Monitor:** `docker stats`
- **File Check:** `docker exec -it rdk-middleware ls -la /app`
- **Network Test:** `docker exec rdk-middleware ping -c 1 <DEVICE_IP>`

**For persistent issues:**
1. Collect logs: `docker logs rdk-middleware > rdk-logs.txt`
2. System info: `uname -a && free -h && df -h`
3. Docker info: `docker compose config`
4. Check documentation in USB deployment folder

---

**Last Updated:** April 13, 2026  
**Version:** 1.0  
**Test Drive Time:** ~45-90 minutes from USB to running application
