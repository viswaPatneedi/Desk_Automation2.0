# Quick Setup Reference - USB to New Raspberry Pi
**One-Page Quick Start - Complete Process in ~60 minutes**

---

## 📋 PART 1: PREPARE USB ON DEVELOPMENT MACHINE (10 min)

```bash
# 1. Mount USB
mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb    # Adjust device name per lsblk

# 2. Navigate to project
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement

# 3. Copy files to USB (use provided script)
bash prepare-usb-for-rpi.sh /mnt/usb

# 4. Sync and eject
sync
sudo umount /mnt/usb
sudo eject /dev/sda1
```

---

## 📋 PART 2: INITIAL RASPBERRY PI SETUP (10 min)

```bash
# 1. Install Raspberry Pi OS on microSD card
#    - Use Raspberry Pi Imager (https://www.raspberrypi.com/software/)
#    - Select OS: Raspberry Pi OS 64-bit
#    - Insert microSD, power on Pi

# 2. SSH into Pi (find IP from router or use nmap)
ssh pi@<YOUR_PI_IP>
# Password: raspberry (default)

# 3. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 4. Create app directory
mkdir -p ~/rdk-app ~/rdk-app/{logs,screenshots,iteration_logs,device_logs}
```

---

## 📋 PART 3: TRANSFER FILES FROM USB (5 min)

```bash
# 1. Mount USB on Pi
mkdir -p ~/usb-mount
sudo mount /dev/sda1 ~/usb-mount  # Adjust based on lsblk

# 2. Copy to home
cp -r ~/usb-mount/rdk-middleware-deployment/* ~/rdk-app/

# 3. Verify copy
ls -la ~/rdk-app/ | grep -E "app.py|requirements.txt|Dockerfile"
```

---

## 📋 PART 4: INSTALL DOCKER (10 min)

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh

# 2. Add Pi user to docker group
sudo usermod -aG docker pi
newgrp docker

# 3. Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# 4. Verify
docker --version
docker compose version
```

---

## 📋 PART 5: CONFIGURE APPLICATION (5 min)

```bash
cd ~/rdk-app

# 1. Create .env file
cat > .env << 'EOF'
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SECRET_KEY=generated-random-key
WORKERS=2
TIMEOUT=300
FLASK_ENV=production
EOF

# 2. Update devices.json with your device credentials
nano devices.json
# Update: IP addresses, usernames, passwords
# Ctrl+X → Y → Enter to save

# 3. Adjust memory for Pi model (optional)
nano docker-compose.rpi.yml
# Find: memory: 2G
# Change to: Pi 3=1G, Pi 4=2G, Pi 5=4G
# Ctrl+X → Y → Enter
```

---

## 📋 PART 6: BUILD & START DOCKER (30-60 min)

```bash
cd ~/rdk-app

# 1. Build Docker image (LONGEST STEP - be patient!)
# Pi 3: ~60 min | Pi 4: ~20 min | Pi 5: ~10 min
docker compose -f docker-compose.rpi.yml build

# 2. Start container
docker compose -f docker-compose.rpi.yml up -d

# 3. Wait for startup (monitor logs)
docker logs rdk-middleware -f
# Look for: "Listening on 0.0.0.0:11078"
# Press Ctrl+C when ready
```

---

## 📋 PART 7: VERIFY & TEST (5 min)

```bash
# 1. Check container is running
docker ps | grep rdk-middleware

# 2. Get Pi's IP
hostname -I

# 3. Test in browser
# Open: http://<YOUR_PI_IP>:11078
# Example: http://192.168.1.100:11078
# Should show dashboard with device list

# 4. Test device connectivity
# In web UI: Devices → Select device → Test Connection
# Should show ✓ Connected
```

---

## 🔧 TROUBLESHOOTING QUICK FIXES

| Problem | Solution |
|---------|----------|
| Build fails (disk/network) | `docker system prune -a` then retry |
| Port 11078 in use | `docker compose down` then `up -d` |
| Cannot connect to web UI | `curl http://localhost:11078` from Pi |
| Device SSH fails | Check devices.json IP/port/password |
| High memory usage | Reduce WORKERS=1 in .env, restart container |
| No internet on Pi | Check Ethernet/WiFi, run `ping 8.8.8.8` |

---

## 📱 WEB UI DEFAULT URL
```
http://<YOUR_PI_IP>:11078
```
Example: `http://192.168.1.100:11078`

Find your IP:
```bash
ssh pi@<YOUR_PI_IP>
hostname -I
```

---

## 🔐 EMAIL CONFIG (Gmail Required)

1. Enable 2-Factor Auth: https://myaccount.google.com
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Update .env: `SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx`
4. Test: Restart container, send test email from web UI

---

## 📚 DETAILED GUIDES IN USB

- **USB_TO_RPi_COMPLETE_GUIDE.md** - Full step-by-step (what you're doing)
- **DOCKER_RPI_SETUP.md** - Docker-specific details
- **README_RPi_SETUP.md** - Alternative setup method
- **USB_FOLDER_STRUCTURE.md** - Output folder organization

---

## 🚀 ENABLE AUTO-START ON BOOT (Optional)

```bash
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

sudo systemctl enable rdk-middleware.service
sudo systemctl start rdk-middleware.service
```

---

## 💾 USEFUL COMMANDS

```bash
# View real-time logs
docker logs rdk-middleware -f

# Enter container shell
docker exec -it rdk-middleware bash

# Check resource usage
docker stats rdk-middleware

# Restart container
docker compose -f docker-compose.rpi.yml restart

# Stop container
docker compose -f docker-compose.rpi.yml down

# Reboot Pi
sudo reboot

# SSH into Pi
ssh pi@<PI_IP>
```

---

## ⏱️ SETUP TIME BREAKDOWN

| Step | Time | Notes |
|------|------|-------|
| USB Prep on Dev Machine | 10 min | One-time |
| Pi OS + SSH Setup | 10 min | First boot setup |
| USB Transfer | 5 min | Copy files |
| Docker Install | 10 min | Downloads ~300MB |
| Configuration | 5 min | Update .env & devices.json |
| Docker Build | 30-60 min | **Longest step** (Pi model dependent) |
| Verify & Test | 5 min | Access web UI |
| **TOTAL** | **~75-105 min** | Mostly automated |

---

## 📞 GETTING HELP

1. **Check Docker logs:**
   ```bash
   docker logs rdk-middleware -n 50
   ```

2. **Check system resources:**
   ```bash
   free -h       # RAM
   df -h /       # Disk
   docker stats  # Docker usage
   ```

3. **Test SSH to device:**
   ```bash
   ssh root@<DEVICE_IP> -p 10022
   ```

4. **Restart everything:**
   ```bash
   docker compose -f docker-compose.rpi.yml down
   docker compose -f docker-compose.rpi.yml up -d
   docker logs rdk-middleware -f
   ```

---

**Created:** April 13, 2026  
**Status:** Ready for Production  
**Tested on:** Raspberry Pi 3/4/5  
**Support:** See USB_TO_RPi_COMPLETE_GUIDE.md for full documentation
