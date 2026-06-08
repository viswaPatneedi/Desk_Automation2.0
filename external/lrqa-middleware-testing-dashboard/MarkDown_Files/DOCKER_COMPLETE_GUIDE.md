# Docker Deployment Guide - RDK Testing Dashboard

## 📋 Complete Guide to Building & Running on Windows/Mac

This document provides complete instructions to build and deploy the RDK Testing Dashboard Docker image on Windows and Mac machines.

---

## Table of Contents
1. [What You'll Need](#what-youll-need)
2. [Quick Start (5 minutes)](#quick-start-5-minutes)
3. [Step-by-Step Setup](#step-by-step-setup)
4. [Using Docker Commands](#using-docker-commands)
5. [Troubleshooting](#troubleshooting)
6. [Next Steps](#next-steps)

---

## What You'll Need

### Hardware Requirements
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Disk Space**: 15GB minimum (for Docker image + container + data)
- **Processor**: Multi-core (performance is better with more cores)
- **Network**: Stable internet connection for first build

### Software Requirements

#### For Windows
1. **Windows 10/11 Pro, Enterprise, or Education**
   - Home edition requires WSL 2 upgrade (Windows 11)
   
2. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop
   - Install with default settings
   - Version 4.0 or higher recommended

3. **Terminal (Optional but Recommended)**
   - PowerShell 7+ (built-in): Recommended
   - Or install Windows Terminal from Microsoft Store

#### For Mac
1. **macOS 11 (Big Sur) or newer**
   - M1/M2/M3 chips supported natively

2. **Docker Desktop for Mac**
   - Download: https://www.docker.com/products/docker-desktop
   - Choose correct version:
     - **Intel**: If your Mac has Intel processor
     - **Apple Silicon**: If your Mac has M1/M2/M3 chips
   - Version 4.0 or higher recommended

3. **Terminal**
   - Built-in Terminal app works fine
   - Or install iTerm2 from https://iterm2.com/

---

## Quick Start (5 minutes)

### ⚡ Windows Quick Start
```powershell
# Start PowerShell and navigate to project
cd C:\path\to\Enhancement

# Copy environment file
Copy-Item .env.example .env

# Edit .env file with your email credentials
notepad .env

# Build and start in one command
.\build-and-run.ps1 -Action rebuild

# Wait for "Application is ready" message
# Then open: http://localhost:5000
```

### ⚡ Mac Quick Start
```bash
# Open Terminal and navigate to project
cd /path/to/Enhancement

# Copy environment file
cp .env.example .env

# Edit .env file with your email credentials
nano .env  # or: open -a TextEdit .env

# Make script executable
chmod +x build-and-run.sh

# Build and start in one command
./build-and-run.sh rebuild

# Wait for "Application is ready" message
# Then open: http://localhost:5000
```

---

## Step-by-Step Setup

### Step 1: Install Docker Desktop

<details>
<summary><b>Windows Installation</b></summary>

1. Download from: https://www.docker.com/products/docker-desktop
2. Run the installer (`Scratch.exe`)
3. Follow installation wizard (keep defaults)
4. **DO NOT SKIP**: Select "Use WSL 2 instead of Hyper-V" if prompted
5. Restart your computer when installation completes
6. Open PowerShell and verify:
   ```powershell
   docker --version
   docker run hello-world
   ```
   - Should show Docker version and Hello message
   - Container should exit successfully after message

**Troubleshooting Windows Installation:**
- If Docker doesn't start: Restart your computer
- If "WSL 2 not found": Enable via Control Panel → Programs → Windows Features → Check "Windows Subsystem for Linux"
- If stuck on "starting": Ensure virtualization is enabled in BIOS

</details>

<details>
<summary><b>Mac Installation</b></summary>

1. Download from: https://www.docker.com/products/docker-desktop
2. Choose your chip type:
   - **Intel**: docker-desktop-*-amd64.dmg
   - **Apple Silicon (M1/M2/M3)**: docker-desktop-*-arm64.dmg
3. Run the DMG installer
4. Drag Docker to Applications folder
5. Open Applications → Docker
   - Grant password when prompted
   - Wait for "Docker is running" in menu bar
6. Open Terminal and verify:
   ```bash
   docker --version
   docker run hello-world
   ```
   - Should show Docker version and Hello message

**Troubleshooting Mac Installation:**
- If Docker won't open: Try: `open /Applications/Docker.app`
- If "permission denied": Grant permissions in System Preferences
- If M1 Mac is running Intel image: Download arm64 version

</details>

### Step 2: Get the Project Files

```bash
# Option A: Clone from Git (if you have Git installed)
git clone <repository-url>
cd Enhancement

# Option B: Use existing directory
cd /path/to/Enhancement
```

### Step 3: Configure Environment

```bash
# Copy the example environment file
# Windows PowerShell
Copy-Item .env.example .env

# Mac/Linux
cp .env.example .env
```

**Edit the `.env` file with your settings:**

```env
# Flask security key (change this!)
SECRET_KEY=your-secure-random-key-here

# Gmail SMTP settings (simplest option)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-gmail-app-password

# Alternative: Comcast Mail Relay
# SMTP_HOST=mailrelay.comcast.com
# SMTP_PORT=25
# SENDER_EMAIL=your-email@comcast.net
# SENDER_PASSWORD=  (usually blank for internal use)
```

**How to get Gmail App Password:**
1. Go to https://myaccount.google.com/
2. Security (left menu) → 2-Step Verification (enable if needed)
3. App passwords
4. Select "Mail" and "Windows Computer" (or Mac)
5. Copy the 16-character password → paste into .env

### Step 4: Build the Docker Image

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
# Navigate to project folder
cd C:\path\to\Enhancement

# Build the image (takes 10-15 minutes first time)
.\build-and-run.ps1 -Action build

# Or use docker-compose directly
docker-compose build
```

What happens:
1. ✓ Downloads Python 3.11 base image (~150 MB)
2. ✓ Installs system dependencies (Tesseract, etc)
3. ✓ Installs Python packages from requirements.txt (~1-2 GB)
4. ✓ Copies your application code
5. ✓ Prepares the container for running

You'll see progress with percentages. Wait until you see "Successfully tagged" or completion message.

</details>

<details>
<summary><b>Mac (Terminal)</b></summary>

```bash
# Navigate to project folder
cd /path/to/Enhancement

# Make script executable (one-time)
chmod +x build-and-run.sh

# Build the image (takes 10-15 minutes first time)
./build-and-run.sh build

# Or use docker-compose directly
docker-compose build
```

What happens:
1. ✓ Downloads Python 3.11 base image (~150 MB)
2. ✓ Installs system dependencies (Tesseract, etc)
3. ✓ Installs Python packages from requirements.txt (~1-2 GB)
4. ✓ Copies your application code
5. ✓ Prepares the container for running

You'll see progress with percentages. Wait until you see "Successfully tagged" or completion message.

</details>

### Step 5: Start the Container

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
# Option 1: Using the automation script (easiest)
.\build-and-run.ps1 -Action run

# Option 2: Using docker-compose directly
docker-compose up -d

# Wait a few seconds for startup...
```

You should see:
```
✓ Container started successfully
ℹ Waiting for application to be ready...
✓ Application is ready
ℹ Access the application at: http://localhost:5000
ℹ View logs with: docker-compose logs -f
```

</details>

<details>
<summary><b>Mac (Terminal)</b></summary>

```bash
# Option 1: Using the automation script (easiest)
./build-and-run.sh run

# Option 2: Using docker-compose directly
docker-compose up -d

# Wait a few seconds for startup...
```

You should see:
```
✓ Container started successfully
ℹ Waiting for application to be ready...
✓ Application is ready
ℹ Access the application at: http://localhost:5000
ℹ View logs with: docker-compose logs -f
```

</details>

### Step 6: Access the Application

Open your web browser and go to:
- **Main Dashboard**: http://localhost:5000
- **Admin Panel**: http://localhost:5000/admin
- **Health Check**: http://localhost:5000/health
- **Log Streaming**: http://localhost:5000/logs/stream

You should see the RDK Testing Dashboard login page.

**Default Credentials:**
- Check `users.json` for configured admin users
- Or add via API/command line if needed

---

## Using Docker Commands

### View Application Logs

```bash
# Windows PowerShell
.\build-and-run.ps1 -Action logs

# Mac Terminal
./build-and-run.sh logs

# Direct docker-compose
docker-compose logs -f

# View last 50 lines
docker-compose logs --tail=50
```

### Stop the Application

```bash
# Windows PowerShell
.\build-and-run.ps1 -Action stop

# Mac Terminal
./build-and-run.sh stop

# Direct docker-compose
docker-compose down
```

### Access Container Shell

```bash
# Windows PowerShell
.\build-and-run.ps1 -Action bash

# Mac Terminal
./build-and-run.sh bash

# Direct docker-compose
docker-compose exec web bash
```

### Check Container Status

```bash
# Windows PowerShell
.\build-and-run.ps1 -Action status

# Mac Terminal
./build-and-run.sh status

# Direct commands
docker ps                           # Show running containers
docker-compose ps                   # Show compose services
docker stats rdk-testing           # Show resource usage
```

### Restart the Container

```bash
# Windows
docker-compose restart web

# Mac
docker-compose restart web

# Or use scripts
.\build-and-run.ps1 -Action stop
.\build-and-run.ps1 -Action run
```

---

## Useful Development Commands

### Rebuild with Fresh Dependencies
```bash
# Windows
docker-compose build --no-cache

# Mac
docker-compose build --no-cache
```

### Remove Everything and Start Over
```bash
# Windows
.\build-and-run.ps1 -Action clean

# Mac
./build-and-run.sh clean

# Manual
docker-compose down -v
docker rmi rdk-testing-dashboard:latest
```

### Execute Command in Container
```bash
# Run a Python command
docker-compose exec web python -c "import app; print('OK')"

# Run a shell command
docker-compose exec web ls -la iteration_logs/

# Get container IP
docker-compose exec web hostname -I
```

---

## Troubleshooting

<details>
<summary><b>Port 5000 already in use</b></summary>

**Error message**: `bind: address already in use`

**Solution**:
```bash
# Windows PowerShell - find what's using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac Terminal - find what's using port 5000
lsof -i :5000
kill -9 <PID>

# Or change the port in docker-compose.yml
# Change "5000:5000" to "8000:5000"
```

</details>

<details>
<summary><b>Container keeps restarting</b></summary>

**Error message**: Container exits/restarts continuously

**Solution**:
```bash
# Check logs
docker-compose logs

# Look for Python errors or missing files
# Common fixes:
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

</details>

<details>
<summary><b>Out of memory error</b></summary>

**Error message**: `docker: Error response from daemon... no memory`

**Solution**:
1. Windows: Docker Desktop → Settings → Resources → Memory
2. Mac: Docker → Preferences → Resources → Memory
3. Increase to 6-8 GB
4. Click "Apply"
5. Restart Docker
6. Try building again

</details>

<details>
<summary><b>Cannot connect to SSH devices</b></summary>

**Error message**: "SSH connection failed" or "Timeout"

**Solution**:
1. Test SSH manually first:
   ```bash
   ssh root@<device-ip> -p 10022
   ```
2. Verify devices.json has correct:
   - IP addresses
   - SSH port (usually 10022)
   - Username (usually root)
   - Password
3. Check firewall allows port 10022
4. Verify device is powered on and connected

</details>

<details>
<summary><b>Build fails with "curl not found"</b></summary>

**Error message**: `curl: command not found` or similar

**Solution**:
1. This shouldn't happen (curl is installed in Dockerfile)
2. Try rebuild:
   ```bash
   docker-compose build --no-cache
   ```
3. Check internet connection during build

</details>

<details>
<summary><b>Docker Desktop won't start</b></summary>

**Windows Solution**:
1. Ensure Virtualization is enabled in BIOS
2. Restart Docker Desktop
3. Check Event Viewer for errors
4. Try: `wsl --update`

**Mac Solution**:
1. Restart Mac
2. Verify Docker installation: `open /Applications/Docker.app`
3. Check System Preferences for permission issues

</details>

### Getting Help

1. **Check the logs**:
   ```bash
   docker-compose logs
   ```

2. **Check Docker system status**:
   ```bash
   docker info
   docker system df
   ```

3. **Clean and retry**:
   ```bash
   docker system prune -a
   docker-compose build --no-cache
   ```

4. **Restart everything**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

## Next Steps

### 1. Add Devices
1. Open http://localhost:5000
2. Login with admin credentials
3. Go to Devices → Add Device
4. Enter SSH details:
   - IP Address
   - Port (usually 10022)
   - Username (usually root)
   - Password
5. Test connection

### 2. Configure SMTP Email
1. Settings → Email Configuration
2. Enter your SMTP credentials
3. Send test email
4. Verify it works

### 3. Create Your First Job
1. Jobs → New Job
2. Select a device
3. Choose a test method
4. Run job
5. Monitor in Real-time Logs

### 4. Schedule Recurring Tests
1. Sequences → Create Sequence
2. Add multiple jobs
3. Set schedule (daily, weekly, etc.)
4. Enable automation

### 5. Deploy to Cloud (Optional)
For production deployment on AWS, Azure, or Google Cloud:
- See [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)

---

## Docker Compose Commands Cheat Sheet

```bash
# Start services in background
docker-compose up -d

# Stop services
docker-compose down

# View running services
docker-compose ps

# View logs (stream)
docker-compose logs -f

# View specific service logs
docker-compose logs -f web

# Rebuild images
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Remove all (containers, volumes, networks)
docker-compose down -v

# Execute command in service
docker-compose exec web bash

# View service resource usage
docker stats
```

---

## Performance Tips

### Windows
- Enable WSL 2 backend (Settings → General → WSL 2)
- Allocate 6-8 GB RAM to Docker
- Store project on C:\ drive, not network share
- Keep Docker Desktop updated

### Mac
- Apple Silicon (M1/M2/M3): Download native ARM64 version
- Allocate 6-8 GB RAM to Docker
- Use wired network for SSH if possible
- Keep Docker Desktop updated

### General
- Close unused applications to free RAM
- Regular cleanup: `docker system prune -a`
- Don't run too many containers simultaneously

---

## Data Persistence

Your data is stored in local files that persist across container restarts:

| Data | Location | Persists? |
|------|----------|-----------|
| Devices | `devices.json` | ✓ Yes |
| Jobs | `jobs.json` | ✓ Yes |
| Logs | `iteration_logs/` | ✓ Yes |
| Screenshots | `screenshots/` | ✓ Yes |
| Application State | `app_state.json` | ✓ Yes |

Backup these files regularly!

---

## Useful Links

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Docker Desktop Download](https://www.docker.com/products/docker-desktop)
- [Container Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

## Documentation Files Reference

| Document | Purpose |
|----------|---------|
| **DOCKER_QUICKSTART.md** | 5-minute quick start |
| **DOCKER_WINDOWS_MAC_GUIDE.md** | Comprehensive setup guide |
| **DOCKER_IMPLEMENTATION_SUMMARY.md** | Technical details |
| **DOCKER_BUILD_GUIDE.md** | Cloud deployment guide |
| **README.md** | Application overview |

---

## Summary

You now have:
✅ Docker image built
✅ Container running
✅ Application accessible at http://localhost:5000
✅ Complete documentation for Windows & Mac
✅ Automation scripts for easy management

**Next**: Add your devices and start testing!

Good luck! 🚀
