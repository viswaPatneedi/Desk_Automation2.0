# 🎯 COMPLETE DOCKER SETUP GUIDE - Linux & Raspberry Pi

**RDK-E Middleware Testing Dashboard - Production Ready**

Quick, step-by-step guide with copy-paste commands to get the application running on any Linux or Raspberry Pi system.

---

## 🚀 FASTEST PATH (3 STEPS, ~10 MINUTES)

### Step 1: Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Navigate & Run
```bash
cd /path/to/Enhancement
bash docker-rpi-quickstart.sh
```

### Step 3: Access
```
Open browser: http://YOUR_PI_IP:11078
```

**Done!** Everything is configured and running.

---

## 📋 COMPLETE MANUAL SETUP (If you prefer more control)

### Prerequisites Check

```bash
# Check: Are you on 64-bit Linux?
uname -m
# Expected output: aarch64 (Raspberry Pi 4/5) or x86_64 (Linux)

# Check: Do you have internet?
ping 8.8.8.8

# Check: How much RAM?
free -h
# Need at least 2GB free

# Check: How much storage?
df -h
# Need at least 20GB free
```

---

## 📦 PHASE 1: INSTALL DOCKER & DEPENDENCIES

### Install Docker Engine (Choose One)

**Raspberry Pi / Debian Linux:**
```bash
# Official Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify
docker --version
```

**Alternative (if above fails):**
```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo apt-get install -y docker-compose
```

### Add User to Docker Group (Skip `sudo`)

```bash
# Allow current user to run docker without sudo
sudo usermod -aG docker $USER

# Apply group changes immediately
newgrp docker

# Verify (no sudo needed)
docker run hello-world
```

### Install Docker Compose

**Option A: Docker Compose Plugin (Recommended)**
```bash
sudo apt-get install -y docker-compose-plugin

# Verify
docker compose version
```

**Option B: Standalone (If Option A fails)**
```bash
# For ARM64 (Raspberry Pi 4/5)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-aarch64" \
  -o /usr/local/bin/docker-compose

# For ARM32 (Raspberry Pi 3)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-armv7" \
  -o /usr/local/bin/docker-compose

# For x86_64 (Regular Linux)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-x86_64" \
  -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
```

### Start Docker Service

```bash
# Enable Docker to start on boot
sudo systemctl enable docker

# Start Docker
sudo systemctl start docker

# Check status
sudo systemctl status docker
```

---

## 🎯 PHASE 2: PREPARE APPLICATION

### Navigate to Project Directory

```bash
cd /path/to/Enhancement

# Verify files exist
ls -la Dockerfile.rpi docker-compose.rpi.yml requirements.txt
```

### Create Environment Configuration

**Option A: Use Script**
```bash
bash docker-rpi-quickstart.sh
# The script will ask for configuration interactively
```

**Option B: Manual Setup**
```bash
# Copy template
cp .env.example .env

# Edit with your settings
nano .env
```

**What to put in .env:**
```bash
# EMAIL CONFIGURATION
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Gmail app password (NOT your main password!)

# APPLICATION
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production

# PERFORMANCE (optional)
WORKERS=2           # Use 1 for Pi 3, 2 for Pi 4, 4 for Pi 5
TIMEOUT=300
```

### Get Gmail App Password (Required for Email)

1. Go to: https://myaccount.google.com/account
2. Click "Security" in left menu
3. Enable "2-Step Verification" if not done
4. Go to: https://myaccount.google.com/apppasswords
5. Select "Mail" and "Windows Computer"
6. Click "Generate"
7. Copy the 16-character password
8. Paste into `.env` as `SENDER_PASSWORD`

---

## 🏗️ PHASE 3: BUILD DOCKER IMAGE

### Option A: Using Docker Compose (Recommended)

```bash
# Start build
docker compose -f docker-compose.rpi.yml build

# Watch progress
# Takes 30-90 minutes depending on Pi model
```

### Option B: Using Docker CLI

```bash
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .
```

### Option C: Faster Build (Using BuildKit)

```bash
export DOCKER_BUILDKIT=1
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .
```

### What Gets Built

```
✓ Python 3.11 slim base image
✓ System packages:
  - Tesseract OCR (for AI vision)
  - OpenCV (image processing)
  - Build tools (GCC, G++)
  - Math libraries (BLAS, LAPACK)
  - Text rendering (libharfbuzz)
  
✓ Python packages (15 total):
  - Flask, Paramiko (SSH), Pillow
  - OpenCV, pytesseract (OCR)
  - Gunicorn (WSGI server)
  - And 9 more packages
  
✓ Application code
✓ Necessary directories
```

### Expected Build Times

| System | Time |
|--------|------|
| Raspberry Pi 3 | 60-90 minutes |
| Raspberry Pi 4 | 20-40 minutes |
| Raspberry Pi 5 | 5-15 minutes |
| Linux/Intel | 10-20 minutes |

### If Build Fails

```bash
# Check available disk space (need 20GB+)
df -h

# Check available RAM
free -h

# Try again with BuildKit disabled
export DOCKER_BUILDKIT=0
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# Or clean and retry
docker system prune -a
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .
```

---

## 🚀 PHASE 4: START THE APPLICATION

### Option A: Using Docker Compose (Recommended)

```bash
# Start in background
docker compose -f docker-compose.rpi.yml up -d

# Wait for startup
sleep 10

# Check status
docker compose -f docker-compose.rpi.yml ps
```

### Option B: Using Make

```bash
# Start
make -f Makefile.rpi up

# View logs
make -f Makefile.rpi logs
```

### Option C: Using Docker CLI

```bash
docker run -d \
  --name rdk-middleware \
  -p 11078:5000 \
  --restart unless-stopped \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/device_locks.json:/app/device_locks.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  --env-file .env \
  rdk-middleware:rpi
```

### Verify Container Started

```bash
# Check if running
docker ps | grep rdk-middleware

# Check logs for errors
docker compose -f docker-compose.rpi.yml logs

# Check health
curl http://localhost:11078/health
```

---

## 📊 PHASE 5: ACCESS & CONFIGURE

### Find Your Device IP

```bash
hostname -I
```

Output: `192.168.1.100`

### Open in Browser

```
http://192.168.1.100:11078
```

### Test API Health

```bash
curl http://192.168.1.100:11078/health

# Expected output: {"status":"healthy",...}
```

### View Application Logs

```bash
# Real-time logs
docker compose -f docker-compose.rpi.yml logs -f

# Last 50 lines
docker compose -f docker-compose.rpi.yml logs --tail=50

# Search for errors
docker compose -f docker-compose.rpi.yml logs | grep ERROR
```

---

## 🔧 COMMON COMMANDS FOR DAILY USE

### Start Application

```bash
# Using Docker Compose
docker compose -f docker-compose.rpi.yml up -d

# Using Make
make -f Makefile.rpi up

# Check status
docker ps | grep rdk-middleware
```

### Stop Application

```bash
# Using Docker Compose
docker compose -f docker-compose.rpi.yml down

# Using Make
make -f Makefile.rpi down
```

### View Logs

```bash
# Follow logs live
docker compose -f docker-compose.rpi.yml logs -f

# Using Make
make -f Makefile.rpi logs
```

### Restart Application

```bash
docker compose -f docker-compose.rpi.yml restart
```

### Update/Rebuild After Code Changes

```bash
# Stop container
docker compose -f docker-compose.rpi.yml down

# Rebuild image
docker compose -f docker-compose.rpi.yml build --no-cache

# Start container
docker compose -f docker-compose.rpi.yml up -d
```

### Check Resource Usage

```bash
# View CPU/RAM usage
docker stats rdk-middleware

# View disk usage
docker exec rdk-middleware du -sh /app/*
```

---

## 🔍 TROUBLESHOOTING

### "Docker command not found"

```bash
# Verify Docker installed
docker --version

# If not found, install it
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# If permission denied, add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### "Port 11078 already in use"

```bash
# Find what's using the port
sudo lsof -i :11078

# Kill the process
sudo kill -9 PID

# Or use different port in docker-compose.rpi.yml
# Change: - "11078:5000" to - "11079:5000"
```

### "Container keeps restarting"

```bash
# Check logs for errors
docker logs rdk-middleware

# Common issues:
# 1. Missing .env file
# 2. Invalid configuration
# 3. Port conflict
# 4. Out of memory

# Fix and restart
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d
```

### "Build runs out of memory"

```bash
# Option 1: Build without cache
docker system prune -a
docker build -f Dockerfile.rpi -t rdk-middleware:rpi .

# Option 2: Build on external storage
# Move project to USB drive with more space

# Option 3: Build on another machine, transfer image
docker save rdk-middleware:rpi | gzip > image.tar.gz
# Transfer to Pi then:
gunzip < image.tar.gz | docker load
```

### "Can't connect to container from other devices"

```bash
# Ensure Docker is using host network
# In docker-compose.rpi.yml, check:
# network_mode: host

# Or map ports explicitly:
# ports:
#   - "11078:5000"

# Restart container
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d
```

---

## 📁 FILE STRUCTURE AFTER SETUP

```
/path/to/Enhancement/
├── Dockerfile                    # Base Dockerfile
├── Dockerfile.rpi               # RPi-optimized Dockerfile
├── docker-compose.rpi.yml       # Docker Compose configuration
├── requirements.txt             # Python dependencies
├── .env                         # Your configuration (created)
├── app.py                       # Main Flask application
├── devices.json                 # Device configuration
├── jobs.json                    # Job history
├── iteration_logs/              # Execution logs (created at runtime)
├── screenshots/                 # Screenshots (created at runtime)
└── [other files]
```

---

## ✅ VERIFICATION CHECKLIST

After setup, verify each step:

```bash
# ✓ Docker installed
docker --version

# ✓ Docker Compose installed
docker compose version

# ✓ Image built
docker images | grep rdk-middleware

# ✓ Container running
docker ps | grep rdk-middleware

# ✓ Port accessible
curl http://localhost:11078/health

# ✓ Volumes mounted
docker inspect rdk-middleware | grep -A 20 Mounts

# ✓ Logs show no errors
docker logs rdk-middleware | grep -i error

# ✓ Web interface responsive
curl http://localhost:11078/ | head -20

# ✓ All packages installed
docker exec rdk-middleware pip list | wc -l  # Should show ~50+

# ✓ Tesseract working
docker exec rdk-middleware tesseract --version
```

---

## 📞 QUICK REFERENCE CARDS

### Startup (Copy & Paste)

```bash
cd /path/to/Enhancement
docker compose -f docker-compose.rpi.yml build
docker compose -f docker-compose.rpi.yml up -d
sleep 10
curl http://localhost:11078/health
```

### Shutdown

```bash
docker compose -f docker-compose.rpi.yml down
```

### View Logs

```bash
docker compose -f docker-compose.rpi.yml logs -f
```

### Full Restart

```bash
docker compose -f docker-compose.rpi.yml restart
```

### Shell Access

```bash
docker exec -it rdk-middleware /bin/bash
```

### Backup Everything

```bash
mkdir -p backup
cp -r *.json iteration_logs screenshots backup/
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz backup/
```

---

## 📊 SYSTEM REQUIREMENTS

| Requirement | Minimum | Recommended | Optimal |
|------------|---------|-------------|---------|
| RAM | 1GB | 2GB | 4GB+ |
| CPU | Single Core | Dual Core | Quad Core+ |
| Storage | 20GB | 32GB | 64GB+ |
| SD Card Speed | Class 6 | Class 10 | A1/A2 |
| Network | 100Mbps | 1Gbps | 1Gbps |

---

## 🎓 WHAT'S INSTALLED

### System Level

```
Python 3.11
Tesseract OCR v4+
OpenCV 4.8
GCC/G++ compiler
Build tools
BLAS/LAPACK math libraries
```

### Application Level

```
Flask 3.0.0          - Web framework
Paramiko 3.4.0       - SSH client
Pillow 10.1.0        - Image handling
OpenCV-Python 4.8    - Computer vision
Pytesseract 0.3.10   - OCR interface
Requests 2.31.0      - HTTP library
Gunicorn 21.2.0      - Production server
Gevent 24.2.1        - Async workers
(+7 more packages)
```

---

## 🎯 NEXT STEPS

1. **Access Dashboard**: http://YOUR_PI_IP:11078
2. **Add Devices**: Use web interface to add your devices
3. **Configure SSH**: Ensure SSH access to test devices
4. **Run Tests**: Start executing test sequences
5. **Monitor Logs**: Watch iteration_logs/ for execution details
6. **Set Email**: Configure SMTP for result notifications

---

## 📞 SUPPORT

For detailed information, see:
- `DOCKER_RPI_SETUP.md` - Complete setup guide
- `DOCKER_RPI_8GB_DEPLOYMENT_GUIDE.md` - 8GB Pi specific
- `DOCKER_RUN_COMMANDS_LINUX_RPI.md` - All commands reference
- `docker-commands-reference.sh` - Run for interactive command list

Generate command reference:
```bash
bash docker-commands-reference.sh
```

---

**Last Updated**: April 2026  
**Ready to Deploy**: ✅ Yes  
**All Dependencies**: ✅ Included  
**Production Ready**: ✅ Yes
