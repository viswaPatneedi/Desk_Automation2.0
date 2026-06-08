# Complete Project Installation Guide
# Device Testing & Management Application for Raspberry Pi

## System Requirements

- **Hardware**: Raspberry Pi 4 or newer (4GB+ RAM recommended)
- **OS**: Raspberry Pi OS (64-bit) or Ubuntu Server 22.04+ ARM64
- **Architecture**: ARM64 (aarch64)
- **Storage**: 16GB+ SD card (32GB+ recommended)
- **Network**: Ethernet or WiFi connection
- **Python**: 3.9 or newer (3.12 recommended)

## Quick Setup (Automated)

### Fresh Installation on New Pi

```bash
# 1. Copy entire project to Raspberry Pi
# From your computer:
scp -r Enhancement/ pi@<raspberry-pi-ip>:/home/pi/Desktop/viswa/Latest_Enhancement/

# Or if copying from another Pi:
rsync -avz --exclude='venv' --exclude='__pycache__' \
    old-pi:/home/pi/Desktop/viswa/Latest_Enhancement/Enhancement/ \
    /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement/

# 2. On the new Pi
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

# 3. Make setup script executable
chmod +x setup_complete_project.sh

# 4. Run complete setup (creates venv and installs all dependencies)
./setup_complete_project.sh

# 5. Activate virtual environment
source venv/bin/activate

# 6. Start application
python app.py

# Access at: http://<raspberry-pi-ip>:8080
```

### Migration from Existing Pi (with venv)

```bash
# Option A: Transfer entire project including venv (FASTER but LARGE)
# From old Pi, create complete archive:
cd /home/pi/Desktop/viswa/Latest_Enhancement
tar -czf enhancement-complete.tar.gz Enhancement/

# Transfer to new Pi:
scp enhancement-complete.tar.gz pi@new-pi:/home/pi/Desktop/viswa/Latest_Enhancement/

# On new Pi, extract:
cd /home/pi/Desktop/viswa/Latest_Enhancement
tar -xzf enhancement-complete.tar.gz
cd Enhancement
source venv/bin/activate
python app.py

# Option B: Transfer without venv, rebuild on new Pi (RECOMMENDED)
# From old Pi:
cd /home/pi/Desktop/viswa/Latest_Enhancement
tar -czf enhancement-no-venv.tar.gz --exclude='Enhancement/venv' Enhancement/

# Transfer and setup:
scp enhancement-no-venv.tar.gz pi@new-pi:/home/pi/Desktop/viswa/Latest_Enhancement/
ssh pi@new-pi
cd /home/pi/Desktop/viswa/Latest_Enhancement
tar -xzf enhancement-no-venv.tar.gz
cd Enhancement
./setup_complete_project.sh  # Recreates venv with all packages
```

## Manual Installation Steps

### 1. System Preparation

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    wget \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    libhdf5-dev \
    openssh-client \
    rsync
```

### 2. Python Virtual Environment

```bash
# Create virtual environment
cd /path/to/Enhancement
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 3. Core Dependencies

```bash
# Flask and web framework
pip install Flask==3.0.0
pip install Flask-SocketIO==5.3.5
pip install python-socketio==5.10.0

# SSH and networking
pip install paramiko==3.4.0
pip install requests==2.31.0

# Image processing
pip install Pillow==10.1.0
pip install opencv-python==4.8.1.78

# Data processing
pip install numpy==1.24.3
pip install pandas==2.0.3

# Utilities
pip install python-dateutil==2.8.2
pip install pytz==2023.3
```

### 4. Screen Validation (Lightweight)

```bash
# Image comparison libraries
pip install imagehash==4.3.1
pip install scikit-image==0.21.0
pip install scipy==1.11.4
```

**Note**: SAM-CD deep learning model is NOT compatible with ARM64. The lightweight alternatives (ImageHash + OpenCV) provide fast and reliable screen comparison.

### 5. OCR Support (Optional)

```bash
# Install Tesseract OCR
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# Install Python wrapper
pip install pytesseract
```

### 6. Additional Packages

```bash
# Email support
pip install secure-smtplib

# JSON validation
pip install jsonschema

# Logging
pip install colorlog

# Testing (optional)
pip install pytest pytest-cov
```

## Complete Package List

### requirements.txt
```
Flask==3.0.0
Flask-SocketIO==5.3.5
python-socketio==5.10.0
paramiko==3.4.0
requests==2.31.0
Pillow==10.1.0
opencv-python==4.8.1.78
numpy==1.24.3
pandas==2.0.3
python-dateutil==2.8.2
pytz==2023.3
imagehash==4.3.1
scikit-image==0.21.0
scipy==1.11.4
pytesseract
secure-smtplib
jsonschema
colorlog
pytest
pytest-cov
```

## Project Structure Setup

```bash
# Create required directories
mkdir -p logs/jobs
mkdir -p device_logs
mkdir -p iteration_logs
mkdir -p screenshots
mkdir -p execution_outputs
mkdir -p reference_screens
mkdir -p ssl
mkdir -p static/css
mkdir -p templates
mkdir -p controllers
mkdir -p models
mkdir -p services

# Initialize configuration files
echo "[]" > devices.json
echo "[]" > users.json
echo "[]" > jobs.json
echo "[]" > saved_sequences.json
echo "{}" > device_locks.json
echo "[]" > test_results_history.json
echo "{}" > app_state.json
```

## Configuration

### 1. Application Settings

Edit `app.py` to configure:
- Server port (default: 8080)
- Debug mode
- Secret key
- Upload folders

### 2. Device Configuration

Edit `devices.json`:
```json
[
  {
    "ip": "10.0.0.172",
    "name": "Element-A4K-DESK",
    "port": 10022,
    "username": "root",
    "password": "your_password",
    "ir_port": 1
  }
]
```

### 3. User Configuration

Edit `users.json` for web authentication:
```json
[
  {
    "username": "admin",
    "password": "hashed_password",
    "email": "admin@example.com"
  }
]
```

### 4. Method Configuration

Edit config files:
- `config_commands.py` - Device SSH commands
- `config_timing.py` - Wait times and timeouts
- `config_log_patterns.py` - Log validation patterns
- `config_screenshot.py` - Screenshot settings
- `config_ir_blaster.py` - IR blaster settings
- `config_screen_validation.py` - Screen validation settings

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run application
python app.py

# Access at: http://<raspberry-pi-ip>:8080
```

### Production Mode

```bash
# HTTP (port 8080)
./run_production.sh

# HTTPS (port 8443)
./run_production_https.sh
```

### As System Service

```bash
# Copy service file
sudo cp device-testing.service /etc/systemd/system/

# Edit service file paths
sudo nano /etc/systemd/system/device-testing.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable device-testing
sudo systemctl start device-testing

# Check status
sudo systemctl status device-testing

# View logs
sudo journalctl -u device-testing -f
```

## Verification

### Test Installation

```bash
source venv/bin/activate

python3 << 'EOF'
import flask
import paramiko
import cv2
import numpy
import PIL
import requests
import imagehash
import skimage

print("✓ All core packages imported successfully")
print(f"Flask: {flask.__version__}")
print(f"Paramiko: {paramiko.__version__}")
print(f"OpenCV: {cv2.__version__}")
print(f"NumPy: {numpy.__version__}")
print(f"Pillow: {PIL.__version__}")
EOF
```

### Test Application

```bash
# Start application
python app.py

# In another terminal, test endpoint
curl http://localhost:8080/

# Should return HTML of login page
```

## Common Issues and Solutions

### Issue: Import errors after installation
**Solution**: Ensure virtual environment is activated
```bash
source venv/bin/activate
```

### Issue: Permission denied on scripts
**Solution**: Make scripts executable
```bash
chmod +x *.sh
```

### Issue: Port already in use
**Solution**: Change port in app.py or kill process
```bash
sudo lsof -i :8080
sudo kill -9 <PID>
```

### Issue: SSH connection fails
**Solution**: Check device credentials and network
```bash
ssh root@<device-ip> -p 10022
```

### Issue: Screenshot capture fails
**Solution**: Verify Thunder plugin is running on device
```bash
# On device
curl http://localhost:9998/screenshot
```

## Backup and Migration

### Option 1: Backup Configuration Only (Recommended - Small Size)

```bash
# Backup configuration and data (excludes venv for smaller size)
tar -czf enhancement-backup-$(date +%Y%m%d).tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    devices.json \
    users.json \
    jobs.json \
    saved_sequences.json \
    test_results_history.json \
    device_locks.json \
    app_state.json \
    config_*.py \
    logs/ \
    screenshots/ \
    reference_screens/
```

### Option 2: Complete Backup Including Virtual Environment

```bash
# Full backup including venv (LARGE - 500MB+)
# Only use this if you want to preserve exact package versions
tar -czf enhancement-full-backup-$(date +%Y%m%d).tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    venv/ \
    devices.json \
    users.json \
    jobs.json \
    saved_sequences.json \
    test_results_history.json \
    device_locks.json \
    app_state.json \
    config_*.py \
    *.py \
    *.sh \
    controllers/ \
    models/ \
    services/ \
    templates/ \
    static/ \
    screenshots/ \
    reference_screens/ \
    SAM-CD-2GB/
```

### Restore on New Pi (Option 1 - Configuration Only)

```bash
# 1. Copy backup to new Pi
scp enhancement-backup-*.tar.gz pi@new-pi:/home/pi/

# 2. On new Pi - Setup project directory
ssh pi@new-pi
mkdir -p /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

# 3. Copy all project files first (code, scripts, etc.)
# Use rsync or scp to copy the entire project from old Pi
rsync -avz --exclude='venv' --exclude='logs' --exclude='__pycache__' \
    old-pi:/home/pi/Desktop/viswa/Latest_Enhancement/Enhancement/ .

# 4. Extract backup (configuration and data)
tar -xzf ~/enhancement-backup-*.tar.gz

# 5. Run setup script to recreate venv and install packages
chmod +x setup_complete_project.sh
./setup_complete_project.sh

# 6. Verify restoration
source venv/bin/activate
python -c "import flask, paramiko, cv2; print('✓ Environment ready')"
ls -la devices.json users.json
```

### Restore on New Pi (Option 2 - Full Backup with venv)

```bash
# 1. Copy full backup to new Pi
scp enhancement-full-backup-*.tar.gz pi@new-pi:/home/pi/

# 2. On new Pi - Setup project directory
ssh pi@new-pi
mkdir -p /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

# 3. Extract everything
tar -xzf ~/enhancement-full-backup-*.tar.gz

# 4. Fix venv paths for new location (if needed)
# The venv contains hardcoded paths that may need updating
rm -rf venv
./setup_complete_project.sh  # Recreate venv

# OR if same path on both Pis:
source venv/bin/activate
python -c "import flask; print('✓ venv working')"

# 5. Verify restoration
ls -la devices.json users.json
python app.py  # Test application
```

### Complete Migration Script (Automated)

```bash
#!/bin/bash
# migrate_to_new_pi.sh - Run on OLD Pi to backup and transfer

NEW_PI_IP="192.168.1.100"  # Change to your new Pi IP
NEW_PI_USER="pi"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

echo "Creating backup..."
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

# Create full project backup
tar -czf /tmp/enhancement-full-${BACKUP_DATE}.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs/*.log' \
    .

echo "Transferring to new Pi..."
scp /tmp/enhancement-full-${BACKUP_DATE}.tar.gz ${NEW_PI_USER}@${NEW_PI_IP}:/tmp/

echo "Setting up on new Pi..."
ssh ${NEW_PI_USER}@${NEW_PI_IP} << 'ENDSSH'
# Create directory structure
mkdir -p /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

# Extract backup
tar -xzf /tmp/enhancement-full-*.tar.gz

# Run setup
chmod +x setup_complete_project.sh
./setup_complete_project.sh

echo "✓ Migration complete on new Pi!"
ENDSSH

echo "✓ Migration completed successfully!"
echo "New Pi is ready at: ${NEW_PI_IP}:8080"
```

## Performance Optimization

### For Raspberry Pi 4 (4GB RAM)

```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Reduce Memory Usage

```python
# In app.py, limit concurrent jobs
MAX_CONCURRENT_JOBS = 2

# Disable debug mode in production
DEBUG = False
```

## Security Hardening

```bash
# 1. Use strong passwords
# 2. Enable firewall
sudo ufw allow 8080/tcp
sudo ufw allow 8443/tcp
sudo ufw enable

# 3. Use HTTPS in production
./run_production_https.sh

# 4. Restrict SSH access
sudo nano /etc/ssh/sshd_config
# PermitRootLogin no
# PasswordAuthentication no (use keys)
```

## Monitoring and Logs

```bash
# Application logs
tail -f logs/app.log

# Iteration logs
tail -f iteration_logs/<device>_<method>_*_UTC.log

# System service logs
sudo journalctl -u device-testing -f

# Disk usage
df -h
du -sh logs/ screenshots/ iteration_logs/
```

## Updates and Maintenance

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade

# Update Python packages
source venv/bin/activate
pip install --upgrade pip
pip list --outdated
pip install --upgrade <package>

# Clean old logs
find logs/ -type f -mtime +30 -delete
find iteration_logs/ -type f -mtime +30 -delete
```

## Support and Documentation

- **README.md** - Project overview
- **QUICK_REFERENCE.md** - Quick start guide
- **FEATURES_IMPLEMENTED_NOV20.md** - Feature list
- **PASSWORD_RESET_GUIDE.md** - Password management
- **SCREENSHOT_GUIDE.md** - Screenshot functionality
- **SCREEN_VALIDATION_STATUS.md** - Screen validation options
- **AI_SCREEN_VALIDATION_GUIDE.md** - Advanced validation (x86_64 only)

## Contact and Troubleshooting

For issues or questions:
1. Check logs in `logs/` directory
2. Review configuration files
3. Verify network connectivity
4. Test SSH connections manually
5. Check system resources (RAM, disk space)

---

**Last Updated**: December 8, 2025
**Tested On**: Raspberry Pi 4 (4GB RAM), Raspberry Pi OS 64-bit
**Python Version**: 3.12.3
