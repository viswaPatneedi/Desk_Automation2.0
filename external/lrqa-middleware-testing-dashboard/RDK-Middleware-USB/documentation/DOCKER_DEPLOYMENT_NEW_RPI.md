# 🐳 DOCKER IMAGE DEPLOYMENT GUIDE FOR NEW RASPBERRY PI 4

## 📊 CURRENT STATUS

**Docker Image:** Not yet built locally (Docker daemon not running)
**USB Copy Status:** In progress (3.4GB of 18GB transferred, ~19% complete)
**Estimated copy time:** 30-45 more minutes

**Recommendation:** Since copy is in progress, we'll proceed with **Option 2: Build on New RPi** (fastest & most reliable)

---

## 🚀 TWO DEPLOYMENT OPTIONS

### ✅ OPTION 1: Build Docker Image ON NEW RPi 4 (RECOMMENDED)
**Pros:**
- ✓ Fastest overall deployment
- ✓ No need to export/import large image files
- ✓ Optimized for exact hardware
- ✓ All dependencies auto-installed
- ✓ Simplest workflow

**Cons:**
- Takes 5-10 minutes on new RPi to build

**Process:**
1. Copy Enhancement directory to new RPi (from USB)
2. SSH into new RPi
3. Run: `./rpi4-setup-complete.sh` (does everything)
4. Done! Dashboard running

---

### ⚠️ OPTION 2: Export Docker Image, Load on New RPi (Complex)
**Pros:**
- ✓ Image pre-built locally
- ✓ No compilation on new RPi

**Cons:**
- ✗ Requires Docker daemon to be running locally
- ✗ Large file to export (~600-800MB)
- ✗ Complex export/import process
- ✗ Still needs Enhancement files on new RPi anyway

**This option is more complex for minimal benefit - not recommended**

---

## 📋 DEPLOYMENT WORKFLOW (RECOMMENDED - OPTION 1)

### STEP 1: Prepare USB devices
```bash
# On current RPi
# SanDisk USB: Will have complete Enhancement directory (being copied)
# Lexar USB: Keep for execution data
```

### STEP 2: Set Up New Raspberry Pi 4
```bash
# On laptop/PC:
# 1. Download Raspberry Pi Imager
#    https://www.raspberrypi.com/software/
#
# 2. Flash Raspberry Pi OS to microSD card
#    - Use 64GB+ card (recommended)
#    - Click "Choose Device" → Raspberry Pi 4
#    - Select OS: Raspberry Pi OS (full) or lite
#    - Choose storage → flash
#
# 3. Boot new RPi
#    - Connect network (WiFi or Ethernet)
#    - Wait 2-3 minutes for initialization
#
# 4. Enable SSH (if not automatic)
#    On RPi terminal:
#    $ sudo raspi-config
#    Navigate to: Interface Options > SSH > Enable
#    OR
#    $ sudo systemctl enable ssh && sudo systemctl start ssh
```

### STEP 3: Connect SanDisk USB to New RPi
```bash
# Insert SanDisk USB into RPi USB port
# Wait for auto-mount
```

### STEP 4: SSH to New RPi and Deploy
```bash
# On your laptop/PC:
$ ssh pi@<new-rpi-ip>

# On new RPi:
$ lsblk  # Find USB (usually /dev/sda1 or /dev/sdb1)

# Mount USB if not auto-mounted:
$ sudo mkdir -p /mnt/usb-deploy
$ sudo mount /dev/sda1 /mnt/usb-deploy

# Navigate to enhancement directory:
$ cd /mnt/usb-deploy/Enhancement
# OR copy to home for better performance:
$ cp -r /mnt/usb-deploy/Enhancement ~/Enhancement-deploy
$ cd ~/Enhancement-deploy

# Make deployment script executable:
$ chmod +x rpi4-setup-complete.sh

# Run ONE-COMMAND deployment:
$ ./rpi4-setup-complete.sh
```

### STEP 5: Wait for Automated Setup (5-15 minutes)
The script automatically:
- ✓ Checks system requirements
- ✓ Installs Docker & Docker Compose
- ✓ Builds Docker image (5-10 min)
- ✓ Starts application
- ✓ Verifies health checks
- ✓ Displays access URL

### STEP 6: Access Dashboard
```bash
# Once script completes:
http://<new-rpi-ip>:11078
```

---

## 📂 FILES NEEDED ON USB FOR DEPLOYMENT

The SanDisk USB being copied contains everything needed:

```
Enhancement/ (being copied to USB)
├── 🐳 DOCKER FILES:
│   ├── Dockerfile.rpi.clean              ✓ Image definition
│   ├── docker-compose.rpi.clean.yml      ✓ Service config
│   ├── docker-entrypoint.sh              ✓ Startup script
│   ├── .dockerignore.rpi.clean           ✓ Build filter
│   ├── rpi4-setup-complete.sh            ✓ MAIN DEPLOYMENT SCRIPT ⭐
│   └── docker-verify-setup.sh            ✓ Verification tool
│
├── 📚 DOCUMENTATION:
│   ├── DOCKER_SETUP_GUIDE_RPI4.md
│   ├── DOCKER_QUICK_REFERENCE.txt
│   ├── USB_DEPLOYMENT_GUIDE.md
│   ├── USB_QUICK_START.txt
│   └── DOCKER_IMAGE_SPECIFICATION.md
│
├── 🛠️ APPLICATION CODE:
│   ├── app.py                            ✓ Main Flask app
│   ├── requirements.txt                  ✓ Python dependencies
│   ├── log_patterns.json                 ✓ Log patterns (FIXED)
│   ├── controllers/                      ✓ Business logic
│   ├── models/                           ✓ Data models
│   ├── services/                         ✓ Background services
│   ├── templates/                        ✓ HTML UI
│   ├── static/                           ✓ CSS/JS
│   └── config_*.py                       ✓ Configuration files
│
└── ✅ ALL LATEST CHANGES INCLUDED
    All newest updates, fixes, and enhancements
    No execution data/logs (clean build)
```

---

## ⏱️ TIMELINE & EXPECTATIONS

### Current USB Copy
```
Status: In Progress
Transferred: 3.4GB of 18GB (~19%)
Elapsed: ~20 minutes
Estimated remaining: 30-45 minutes
ETA completion: ~1 hour total
```

### New RPi Deployment
```
Total Time: ~20-30 minutes

Breakdown:
- SSH setup: 2-3 min
- USB mount: 1 min
- Download from USB: 1-2 min
- ./rpi4-setup-complete.sh execution:
  - System checks: 30 sec
  - Docker install (if needed): 1-2 min
  - Image build: 5-10 min ⏳ (largest part)
  - Service startup: 1 min
  - Health verification: 1 min
- Total: 10-15 minutes for automation
```

---

## 🎯 QUICK CHECKLIST

### Before Starting:
- [ ] SanDisk USB copy completed (monitor in terminal)
- [ ] New RPi 4 with Raspberry Pi OS installed
- [ ] Network configured on new RPi
- [ ] SSH enabled on new RPi
- [ ] Can SSH from laptop to new RPi
- [ ] Know new RPi's IP address

### Deployment:
- [ ] Connect SanDisk USB to new RPi
- [ ] Mount USB: `sudo mount /dev/sda1 /mnt/usb`
- [ ] Navigate: `cd /mnt/usb/Enhancement`
- [ ] Make executable: `chmod +x rpi4-setup-complete.sh`
- [ ] Deploy: `./rpi4-setup-complete.sh`
- [ ] Wait 10-15 minutes
- [ ] Access: `http://<new-rpi-ip>:11078`

### Verification:
- [ ] Dashboard loads in browser
- [ ] All UI elements display
- [ ] Device can be added/configured
- [ ] Test methods available
- [ ] Log patterns loaded ("Check Available Logs" works)

---

## 🔧 MANUAL ALTERNATIVE (If Script Fails)

If `rpi4-setup-complete.sh` encounters issues:

```bash
# Install Docker manually:
$ curl -fsSL https://get.docker.com -o get-docker.sh
$ sudo sh get-docker.sh
$ sudo usermod -aG docker pi

# Install Docker Compose:
$ sudo apt install -y docker-compose

# Build image manually:
$ cd ~/Enhancement
$ docker build -f Dockerfile.rpi.clean \
  -t rdk-middleware-dashboard:rpi4-clean .

# Start with Docker Compose:
$ docker-compose -f docker-compose.rpi.clean.yml up -d

# View logs:
$ docker logs -f rdk-middleware-dashboard
```

---

## 💾 OPTIONAL: CONNECTING LEXAR USB FOR DATA

Once dashboard is running, you can connect Lexar USB for execution data:

```bash
# On new RPi:
$ lsblk  # Find Lexar USB (usually /dev/sdb1)
$ sudo mkdir -p /mnt/lexar-data
$ sudo mount /dev/sdb1 /mnt/lexar-data

# Configure app to use Lexar for data storage
# (Edit docker-compose or app configuration as needed)
```

---

## 📊 SYSTEM REQUIREMENTS VERIFICATION

New RPi 4 should have:
- ✓ RAM: 2GB minimum, 4GB+ recommended
- ✓ Storage: 32GB+ (64GB+ recommended)
- ✓ CPU: Quad-core (RPi 4 standard)
- ✓ Network: WiFi or Ethernet
- ✓ OS: Raspberry Pi OS (32-bit or 64-bit)

Check on new RPi:
```bash
$ free -h       # Check RAM
$ df -h         # Check storage
$ uname -m      # Check architecture
$ cat /proc/cpuinfo | grep processor | wc -l  # Check CPU cores
```

---

## 🆘 TROUBLESHOOTING

### "USB not found"
```bash
$ lsblk  # List all block devices
$ sudo apt install -y exfat-fuse exfat-utils  # If FAT32 issues
```

### "Docker not found"
```bash
# Script auto-installs, but manual install:
$ curl -fsSL https://get.docker.com | sh
```

### "Insufficient disk space"
```bash
$ df -h  # Check disk
# Need at least 5GB free for image build
$ docker system prune -a  # Clean old images
```

### "Slow build on RPi"
This is normal! ARM builds take longer:
- SoC is slower than PC
- Compiling packages takes time
- 5-10 minutes is expected

### "Container won't start"
```bash
$ docker logs -f rdk-middleware-dashboard
$ ./docker-verify-setup.sh  # Run verification
```

---

## 📞 GETTING HELP

### Check Deployment Script
```bash
cat ./rpi4-setup-complete.sh | head -50
```

### Run Verification
```bash
./docker-verify-setup.sh
```

### Check Logs
```bash
docker logs -f rdk-middleware-dashboard | tail -100
```

### View Documentation
```bash
cat USB_DEPLOYMENT_GUIDE.md
cat DOCKER_QUICK_REFERENCE.txt
cat DOCKER_IMAGE_SPECIFICATION.md
```

---

## ✅ SUCCESS INDICATORS

After deployment completes:

✓ Script shows: "✅ Setup Complete"  
✓ Dashboard accessible at: http://<new-rpi-ip>:11078  
✓ All UI elements loading  
✓ Device management working  
✓ Log patterns available  
✓ Test methods functional  
✓ No Docker errors in logs  

---

## 🎉 SUMMARY

**Recommended Approach:**
1. Wait for USB copy to complete
2. Connect SanDisk USB to new RPi 4
3. SSH and run: `./rpi4-setup-complete.sh`
4. Wait 10-15 minutes
5. Access dashboard at: `http://<new-rpi-ip>:11078`

**Why this approach?**
- ✓ Simplest
- ✓ Fastest overall
- ✓ Most reliable
- ✓ Docker built locally on hardware
- ✓ Automatic setup
- ✓ No complex export/import

---

**Version:** 2.0  
**Status:** Production Ready  
**Last Updated:** 2026-04-17
