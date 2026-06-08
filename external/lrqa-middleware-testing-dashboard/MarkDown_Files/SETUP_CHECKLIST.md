# RDK Middleware - USB to Raspberry Pi Setup Checklist

**Date Started:** _______________  
**Raspberry Pi Model:** ☐ Pi 3  ☐ Pi 4 (8GB)  ☐ Pi 5  
**RAM:** _____GB  |  **Storage:** _____GB SD Card  
**Estimated Time:** 75-105 minutes

---

## PHASE 1: DEVELOPMENT MACHINE - FILE PREPARATION (10 min)

### Step 1.1: Mount USB Stick
- [ ] Insert USB stick into development machine
- [ ] Run command: `lsblk` to find device (e.g., /dev/sda1)
- [ ] Create mount point: `mkdir -p /mnt/usb`
- [ ] Mount USB: `sudo mount /dev/sda1 /mnt/usb`
- [ ] Verify: `ls /mnt/usb`

**Device name:** _______________

### Step 1.2: Run USB Preparation Script
- [ ] Navigate: `cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement`
- [ ] Run script: `bash prepare-usb-for-rpi.sh /mnt/usb`
- [ ] Verify file count shown in output: ~100+ files
- [ ] Check total size: ~200-300MB
- [ ] Wait for completion ("✓ Deployment Ready!")

### Step 1.3: Eject USB Safely
- [ ] Sync: `sync`
- [ ] Unmount: `sudo umount /mnt/usb`
- [ ] Eject: `sudo eject /dev/sda1`
- [ ] Remove USB stick from machine

**✓ Phase 1 Complete - USB Stick Ready**

---

## PHASE 2: RASPBERRY PI - INITIAL SETUP (10 min)

### Step 2.1: Install Raspberry Pi OS
- [ ] Download Raspberry Pi Imager from https://www.raspberrypi.com/software/
- [ ] Insert microSD card into computer
- [ ] Select OS: **Raspberry Pi OS (64-bit)**
- [ ] Select Device: Your Pi model
- [ ] Select Storage: microSD card
- [ ] Click "Write" (wait 5 minutes)
- [ ] Insert microSD card into Raspberry Pi
- [ ] Power on Pi
- [ ] Wait for first boot (5 minutes)

### Step 2.2: SSH Connection & System Update
- [ ] Find Pi's IP address from router or use: `nmap -sn 192.168.1.0/24`
- [ ] SSH into Pi: `ssh pi@<IP_ADDRESS>`
  - Username: `pi`
  - Password: `raspberry` (default)
  
**Pi's IP Address:** _______________

- [ ] Update system:
  ```bash
  sudo apt-get update
  sudo apt-get upgrade -y
  ```
- [ ] Create app directory: `mkdir -p ~/rdk-app/{logs,screenshots,iteration_logs,device_logs}`

### Step 2.3: Create USB Mount Directory
- [ ] Create mount point: `mkdir -p ~/usb-mount`
- [ ] When USB is inserted, mount: `sudo mount /dev/sda1 ~/usb-mount`
- [ ] Verify: `ls ~/usb-mount/rdk-middleware-deployment/`

**✓ Phase 2 Complete - Pi Ready to Receive Files**

---

## PHASE 3: TRANSFER FILES FROM USB (5 min)

### Step 3.1: Copy Application Files
- [ ] On Pi, copy files: `cp -r ~/usb-mount/rdk-middleware-deployment/* ~/rdk-app/`
- [ ] Verify files copied: `ls -la ~/rdk-app/ | head -20`
- [ ] Files should include:
  - [ ] `app.py`
  - [ ] `requirements.txt`
  - [ ] `Dockerfile.rpi`
  - [ ] `docker-compose.rpi.yml`
  - [ ] Directories: `controllers/`, `models/`, `services/`, `templates/`, `static/`

**✓ Phase 3 Complete - Files on Raspberry Pi**

---

## PHASE 4: DOCKER INSTALLATION (10 min)

### Step 4.1: Install Docker
- [ ] SSH into Pi (if disconnected)
- [ ] Run: `curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh`
- [ ] Wait for installation (5 minutes)
- [ ] Verify: `docker --version`

**Expected output example:** Docker version 24.x.x

### Step 4.2: Docker Permissions & Compose
- [ ] Add Pi user to docker group: `sudo usermod -aG docker pi`
- [ ] Apply changes: `newgrp docker`
- [ ] Install Docker Compose: `sudo apt-get install -y docker-compose-plugin`
- [ ] Verify: `docker compose version`

**Expected output example:** Docker Compose version v2.x.x

- [ ] Test Docker (should not require sudo): `docker ps`

**✓ Phase 4 Complete - Docker Ready**

---

## PHASE 5: APPLICATION CONFIGURATION (5 min)

### Step 5.1: Create .env Configuration File
- [ ] Navigate: `cd ~/rdk-app`
- [ ] Create .env file:
  ```bash
  cat > .env << 'EOF'
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SENDER_EMAIL=your-email@gmail.com
  SENDER_PASSWORD=your-app-password-here
  SECRET_KEY=your-random-secure-key-here
  WORKERS=2
  TIMEOUT=300
  FLASK_ENV=production
  EOF
  ```
- [ ] Verify: `cat .env` (should show all variables)

**Gmail Setup Required:**
- [ ] Go to https://myaccount.google.com
- [ ] Enable 2-Factor Authentication (if not enabled)
- [ ] Go to https://myaccount.google.com/apppasswords
- [ ] Generate App Password for Mail
- [ ] Copy 16-character password (format: xxxx-xxxx-xxxx-xxxx)
- [ ] Update `SENDER_PASSWORD` in .env

**Gmail App Password:** _______________  
**Secret Key Created:** _______________

### Step 5.2: Configure Devices
- [ ] Edit: `nano devices.json`
- [ ] Update with your device details:
  - Device IP addresses
  - SSH ports (usually 10022)
  - Usernames (usually "root")
  - Passwords
- [ ] Save: Ctrl+X → Y → Enter

**Devices Configured Count:** _____ devices

### Step 5.3: Optimize for Your Pi Model
- [ ] Edit: `nano docker-compose.rpi.yml`
- [ ] Find line: `memory: 2G` (under deploy > resources > limits)
- [ ] Change based on Pi model:
  - [ ] Pi 3: Change to `memory: 1G`
  - [ ] Pi 4 (8GB): Keep `memory: 2G`
  - [ ] Pi 5: Change to `memory: 4G`
- [ ] Find line: `WORKERS=2` (upper section)
- [ ] Change based on Pi model:
  - [ ] Pi 3: Change to `WORKERS=1`
  - [ ] Pi 4: Keep `WORKERS=2`
  - [ ] Pi 5: Change to `WORKERS=4`
- [ ] Save: Ctrl+X → Y → Enter

**Configuration Applied for:** _____ Model Pi

**✓ Phase 5 Complete - Configuration Complete**

---

## PHASE 6: BUILD DOCKER IMAGE (30-60 min) ⏱️ LONGEST STEP

### Step 6.1: Start Build Process
- [ ] Navigate: `cd ~/rdk-app`
- [ ] Start build: `docker compose -f docker-compose.rpi.yml build`
- [ ] **DO NOT INTERRUPT** - let it run to completion

**Estimated wait time by Pi model:**
- [ ] Pi 3: 60-90 minutes (grab coffee ☕)
- [ ] Pi 4: 20-40 minutes
- [ ] Pi 5: 10-20 minutes

### Step 6.2: Monitor Build Progress
- [ ] Watch for output like:
  ```
  Step 1/XX : FROM python:3.11-slim
  Step 2/XX : WORKDIR /app
  ...
  Installing collected packages: flask, paramiko, opencv-python...
  ```
- [ ] If asks to create layers/images, answer `y`
- [ ] Build may pause during package compilation (normal!)

### Step 6.3: Verify Build Completion
- [ ] Look for: `Successfully built abc123def456`
- [ ] Look for: `Successfully tagged rdk-middleware:rpi`
- [ ] **No errors** should appear (warnings are OK)

**Build Completed Time:** _______________

### Step 6.4: Verify Image Created
- [ ] Run: `docker images`
- [ ] Should show row with:
  - [ ] Repository: `rdk-middleware`
  - [ ] Tag: `rpi`
  - [ ] Size: ~1.2-1.5GB

**✓ Phase 6 Complete - Docker Image Built**

---

## PHASE 7: START APPLICATION (5 min)

### Step 7.1: Start Container
- [ ] Run: `docker compose -f docker-compose.rpi.yml up -d`
- [ ] Wait 10 seconds for container to start

### Step 7.2: Monitor Startup
- [ ] View logs: `docker logs rdk-middleware -f` (watch for 30 seconds)
- [ ] Look for: `[INFO] Starting Flask application...`
- [ ] Look for: `Listening on 0.0.0.0:11078`
- [ ] Press Ctrl+C when ready
- [ ] Run: `docker ps | grep rdk-middleware`
- [ ] Should show: Status "Up" (not "Exited")

**Container Started Successfully:** ☐ Yes ☐ No

**✓ Phase 7 Complete - Application Running**

---

## PHASE 8: VERIFICATION & TESTING (5 min)

### Step 8.1: Verify Container Health
- [ ] Check status: `docker ps | grep rdk-middleware`
- [ ] Should show "Up" status
- [ ] Run health check: `curl http://localhost:11078/health`
- [ ] Should return JSON with "status":"healthy"

### Step 8.2: Access Web Interface
- [ ] Get Pi's IP: `hostname -I`

**Pi's IP Address:** _______________

- [ ] Open browser on any device: `http://<PI_IP>:11078`
  - Example: `http://192.168.1.100:11078`
- [ ] Should see dashboard
- [ ] Check if appears:
  - [ ] Navigation menu visible
  - [ ] Device list displays
  - [ ] No error messages
  - [ ] CSS/styling loaded correctly

### Step 8.3: Test Device Connectivity
- [ ] In web UI, go to: **Devices** section
- [ ] Select a device from list
- [ ] Click: **"Test Connection"**
- [ ] Result should be: **✓ Connected** (green checkmark)
- [ ] If failed, verify:
  - [ ] Device IP address is correct in devices.json
  - [ ] SSH port is correct (usually 10022)
  - [ ] Username/password are correct
  - [ ] Device is powered on and reachable (`ping <DEVICE_IP>` from Pi)

**Devices Connected:** _____ / _____ total

### Step 8.4: Run First Test (Optional)
- [ ] Go to: **Dashboard** → **Run Method**
- [ ] Select: A device and test method
- [ ] Set iterations: 1
- [ ] Click: **Execute**
- [ ] Monitor execution in web UI (should show progress)
- [ ] Verify results capture screenshots and logs

**✓ Phase 8 Complete - Application Verified**

---

## PHASE 9: OPTIONAL - AUTO-START ON BOOT

### Step 9.1: Create Systemd Service
- [ ] Run:
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
  ```

### Step 9.2: Enable & Start Service
- [ ] Enable: `sudo systemctl enable rdk-middleware.service`
- [ ] Start: `sudo systemctl start rdk-middleware.service`
- [ ] Verify: `sudo systemctl status rdk-middleware.service`
- [ ] Should show: **Active (running)**

### Step 9.3: Test Auto-Start
- [ ] Reboot Pi: `sudo reboot`
- [ ] Wait 2 minutes for Pi to restart
- [ ] SSH back in: `ssh pi@<PI_IP>`
- [ ] Check status: `docker ps | grep rdk-middleware`
- [ ] Should show container running

**Auto-Start Enabled:** ☐ Yes ☐ No

**✓ Phase 9 Complete - Auto-Start Configured (Optional)**

---

## FINAL STATUS

### Setup Complete Summary
- [ ] **Phase 1:** USB Files Prepared ✓
- [ ] **Phase 2:** Pi Initial Setup ✓
- [ ] **Phase 3:** Files Transferred ✓
- [ ] **Phase 4:** Docker Installed ✓
- [ ] **Phase 5:** Configuration Complete ✓
- [ ] **Phase 6:** Docker Image Built ✓
- [ ] **Phase 7:** Application Started ✓
- [ ] **Phase 8:** Verification Complete ✓
- [ ] **Phase 9:** Auto-Start (Optional) ✓

### Access Information
```
Web Interface URL: http://<YOUR_PI_IP>:11078
Example:         http://192.168.1.100:11078

SSH Access:      ssh pi@<YOUR_PI_IP>
Example:         ssh pi@192.168.1.100

Default SSH Port: 22
Default SSH User: pi
```

### Quick Reference Commands
```bash
# View live logs
docker logs rdk-middleware -f

# Restart application
docker compose -f docker-compose.rpi.yml restart

# Stop application
docker compose -f docker-compose.rpi.yml down

# Rebuild image
docker compose -f docker-compose.rpi.yml build

# Check resources
docker stats

# Reboot Pi
sudo reboot
```

---

## 🚨 IF SOMETHING GOES WRONG

1. **Cannot access web UI:**
   ```bash
   docker ps  # Check if container running
   curl http://localhost:11078  # Test from Pi
   docker logs rdk-middleware -n 50  # Check recent errors
   ```

2. **Devices not connecting:**
   - Verify IP addresses in devices.json
   - Test SSH manually: `ssh root@<DEVICE_IP> -p 10022`
   - Check if devices are powered on and reachable

3. **High memory usage / Pi freezes:**
   - Reduce WORKERS in .env (set to 1)
   - Restart container
   - Check: `docker stats`

4. **Docker build failed:**
   - Free disk space: `df -h`
   - Clean Docker: `docker system prune -a`
   - Check internet: `ping 8.8.8.8`
   - Retry build

5. **For detailed help:**
   - Read: `USB_TO_RPi_COMPLETE_GUIDE.md` (in USB)
   - Read: `USB_TO_RPi_COMPLETE_GUIDE.md` (on ~/rdk-app after copy)
   - Check troubleshooting section in complete guide

---

## 📊 FINAL NOTES

- **Total Setup Time:** 75-105 minutes (mostly automated)
- **Longest Step:** Docker Build (30-60 min based on Pi model)
- **Internet Required:** Yes (for initial setup only)
- **Devices Needed:** Raspberry Pi 3/4/5 with 32GB+ SD card
- **Support Files:** All documentation included on USB stick

---

**Setup Started:** _______________  
**Setup Completed:** _______________  
**Total Time:** _______________  

**Signed Off By:** ________________________

---

**Created:** April 13, 2026  
**Last Updated:** April 13, 2026  
**Version:** 1.0 - Production Ready
