# R-Pi 4 Deployment - Terminal Commands

## Option 1: Using Pre-Built Docker Image (RECOMMENDED - Faster)

Run these commands on the **NEW R-Pi 4** terminal to automatically deploy:

```bash
# Step 1: Ensure Docker is installed
sudo apt-get update && sudo apt-get install -y docker.io docker-compose

# Step 2: Start Docker service
sudo systemctl start docker && sudo systemctl enable docker

# Step 3: Add your user to docker group (if needed)
sudo usermod -aG docker $USER
newgrp docker

# Step 4: Load the pre-built Docker image from USB
# After mounting USB at /media/usb/:
sudo docker load < /media/usb/lrqa-middleware-latest.tar

# Step 5: Verify image is loaded
sudo docker images | grep lrqa-middleware

# Step 6: Run the application container
sudo docker run -d \
  --name=lrqa-middleware \
  --restart=unless-stopped \
  -p 11078:11078 \
  -v /app/data:/app/data \
  -v /app/logs:/app/logs \
  --memory=1g \
  --cpus=2 \
  lrqa-middleware:latest

# Step 7: Verify container is running
sudo docker ps | grep lrqa-middleware

# Step 8: Check application logs
sudo docker logs lrqa-middleware

# Step 9: Access the application
# Open browser: http://localhost:11078
```

---

## Option 2: Using Deployment Script (FASTEST - Automated)

Run a single command on NEW R-Pi:

```bash
# Mount USB
mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Run automated deployment script (all-in-one)
bash /media/usb/rpi4-deploy.sh

# Follow prompts for configuration
```

---

## Option 3: Using Python Interactive Setup (BEGINNER-FRIENDLY)

```bash
# Mount USB
mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Run interactive setup wizard
python3 /media/usb/rpi4-setup-assistant.py

# Follow interactive prompts
```

---

## Files to Copy to USB

Prepare USB with these files:
1. `lrqa-middleware-latest.tar` - Docker image (copy once ready)
2. `rpi4-deploy.sh` - Automated deployment script
3. `rpi4-setup-assistant.py` - Interactive setup wizard
4. `requirements.txt` - Python dependencies (if needed)
5. `docker-compose.yml` - Compose file for manual configuration

---

## Quick Start (TL;DR - Copy & Paste on R-Pi)

```bash
# Single command to deploy everything
mkdir -p /media/usb && sudo mount /dev/sda1 /media/usb && bash /media/usb/rpi4-deploy.sh
```

---

## Post-Deployment Configuration

After deployment completes:

### 1. Check Container Status
```bash
sudo docker ps
sudo docker logs lrqa-middleware -f  # Follow logs
```

### 2. Stop/Start Application
```bash
sudo docker stop lrqa-middleware      # Stop
sudo docker start lrqa-middleware     # Start
sudo docker restart lrqa-middleware   # Restart
```

### 3. View Application
```bash
# Open browser on R-Pi or another machine:
# http://<rpi-ip-address>:11078
```

### 4. SSH into Container (if needed)
```bash
sudo docker exec -it lrqa-middleware /bin/bash
```

### 5. Access Data Directories
```bash
# Application data stored at:
sudo ls -la /app/data/

# Application logs at:
sudo ls -la /app/logs/
```

---

## Troubleshooting

### Container won't start?
```bash
sudo docker logs lrqa-middleware
sudo docker inspect lrqa-middleware
```

### Port 11078 already in use?
```bash
sudo lsof -i :11078  # Find what's using it
# Or use different port in docker run command
```

### USB not mounting?
```bash
lsblk                                    # List all devices
sudo mount /dev/sda1 /media/usb         # Mount manually
sudo umount /media/usb                  # Unmount if needed
```

### Docker daemon issues?
```bash
sudo systemctl restart docker
sudo systemctl status docker
```

---

## SystemD Auto-Start (Optional)

To make application auto-start on R-Pi reboot:

```bash
# Create systemd service file
sudo nano /etc/systemd/system/lrqa-middleware.service
```

Paste this content:
```ini
[Unit]
Description=LRQA Middleware Application
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker run \
  --rm \
  --name=lrqa-middleware \
  -p 11078:11078 \
  -v /app/data:/app/data \
  -v /app/logs:/app/logs \
  --memory=1g \
  --cpus=2 \
  lrqa-middleware:latest
Restart=unless-stopped
RestartSec=10s
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lrqa-middleware.service
sudo systemctl start lrqa-middleware.service
sudo systemctl status lrqa-middleware.service
```

---

## USB Preparation Checklist

- [ ] Copy `docker-compose.yml` to USB
- [ ] Copy `rpi4-deploy.sh` to USB
- [ ] Copy `rpi4-setup-assistant.py` to USB
- [ ] Copy `Dockerfile.prod` to USB (reference only)
- [ ] Copy `requirements.txt` to USB
- [ ] Copy Docker image `lrqa-middleware-latest.tar` to USB (when ready)
- [ ] Verify all files copied: `ls -lh /media/usb/`
- [ ] USB is FAT32 or ext4 formatted
- [ ] Safe eject USB before unplugging

---

## Image Size & Deployment Time

- **Image Size**: ~12GB (compressed: ~3-4GB)
- **USB Copy Time**: 5-10 minutes (depends on USB speed)
- **Docker Load Time**: 2-3 minutes on R-Pi 4
- **Total Deployment**: 10-15 minutes

---

## Support Files Reference

| File | Purpose | Run On |
|------|---------|--------|
| `rpi4-deploy.sh` | Automated one-command deployment | R-Pi (bash) |
| `rpi4-setup-assistant.py` | Interactive setup wizard | R-Pi (python3) |
| `docker-compose.yml` | Manual Docker Compose orchestration | R-Pi (docker-compose) |
| `Dockerfile.prod` | Reference - production image definition | Development |
| `RPI4_COMPLETE_DEPLOYMENT_GUIDE.md` | Full deployment documentation | Reference |
