# Docker Windows Installation & Testing Guide - Complete Step-by-Step

## 📦 Overview

This guide will help you:
1. Install Docker Desktop on Windows
2. Build the Docker image on your Windows machine
3. Run the application in Docker
4. Test all functionality
5. Verify data persistence

---

## **PART 1: INSTALL DOCKER DESKTOP ON WINDOWS**

### Step 1.1: Download Docker Desktop

1. Go to: https://www.docker.com/products/docker-desktop
2. Click **"Download for Windows"**
3. Save the file: `Docker Desktop Installer.exe`

### Step 1.2: Install Docker

1. Double-click **`Docker Desktop Installer.exe`**
2. In the installation wizard:
   - Leave default options
   - Click **"Install"**
3. Grant Admin permissions when prompted
4. Wait for installation (3-5 minutes)
5. Click **"Finish"**
6. **RESTART YOUR COMPUTER** (very important!)

### Step 1.3: Verify Installation

After restart:

1. Open **PowerShell** (search for it in Start menu)
2. Run this command:
   ```powershell
   docker --version
   ```
   
   **Expected output:** `Docker version 24.0.0, build abcdef`

3. Run this command:
   ```powershell
   docker run hello-world
   ```
   
   **Expected output:** Should show "Hello from Docker!" message

✅ **If both commands work, Docker is installed correctly!**

---

## **PART 2: PREPARE YOUR PROJECT FILES**

### Step 2.1: Get the Project Files

You need these files from the Enhancement project:
- All Python files (`.py` files)
- `requirements.txt`
- `templates/` folder
- `static/` folder
- `controllers/` folder
- `models/` folder
- `services/` folder
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.env.example`
- All config files (`config_*.py`)

### Step 2.2: Create Project Directory on Windows

```powershell
# Create a directory for the project
mkdir C:\Docker\RDKDashboard
cd C:\Docker\RDKDashboard

# Copy all the project files here
# You can either:
# A) Copy from your current Enhancement folder
# B) Clone from Git repository
# C) Download as ZIP and extract
```

**Method A: Copy from current folder**
```powershell
# If you have the files locally, copy them
Copy-Item -Path "C:\path\to\Enhancement\*" -Destination "C:\Docker\RDKDashboard" -Recurse
```

**Method B: Clone from Git (if available)**
```powershell
cd C:\Docker
git clone <your-repository-url> RDKDashboard
cd RDKDashboard
```

### Step 2.3: Verify All Files are Present

```powershell
cd C:\Docker\RDKDashboard

# List all files to verify
dir

# Check for required files
if (Test-Path "Dockerfile") { Write-Host "✓ Dockerfile found" }
if (Test-Path "docker-compose.yml") { Write-Host "✓ docker-compose.yml found" }
if (Test-Path "requirements.txt") { Write-Host "✓ requirements.txt found" }
if (Test-Path "app.py") { Write-Host "✓ app.py found" }
```

---

## **PART 3: CONFIGURE ENVIRONMENT**

### Step 3.1: Create .env File

```powershell
cd C:\Docker\RDKDashboard

# Copy the example file
Copy-Item .env.example .env

# Verify it was created
dir .env
```

### Step 3.2: Edit .env File with Your Settings

**Option A: Using Notepad**
```powershell
notepad .env
```

**Option B: Using VS Code**
```powershell
code .env
```

### Step 3.3: Configure Email Settings

In the `.env` file, update these lines:

```env
# Security key
SECRET_KEY=my-secure-key-12345-change-this

# Flask
FLASK_ENV=production

# Gmail SMTP (easiest option)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-gmail-app-password
```

**How to get Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select: **Mail** → **Windows Computer**
3. Google will generate a 16-character password
4. Copy and paste into `.env` as `SENDER_PASSWORD`

**Save the file** (Ctrl+S)

Example completed `.env` file:
```env
SECRET_KEY=my-super-secure-key-abc123
FLASK_ENV=production
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=john.doe@gmail.com
SENDER_PASSWORD=abcd efgh ijkl mnop
```

---

## **PART 4: BUILD THE DOCKER IMAGE ON WINDOWS**

### Step 4.1: Open PowerShell in Project Directory

```powershell
cd C:\Docker\RDKDashboard
```

### Step 4.2: Build the Docker Image

**Using the automation script (easiest):**
```powershell
.\build-and-run.ps1 -Action build
```

**OR using docker-compose directly:**
```powershell
docker-compose build
```

### Step 4.3: Monitor the Build Process

**What you'll see:**
```
Building docker image for rdk-testing-dashboard...
Sending build context to Docker daemon...
Step 1/20 : FROM python:3.11-slim
 ---> abc123def456
Step 2/20 : WORKDIR /app
 ---> Running in xyz789
 ---> New image abc123xyz789
Step 3/20 : ENV PYTHONDONTWRITEBYTECODE=1
...
[Many more steps...]
...
Successfully built abc123def456
Successfully tagged rdk-testing-dashboard:latest
```

**Time Required:** 
- First build: 10-15 minutes (downloading Python, packages, etc.)
- Subsequent builds: 2-5 minutes (due to caching)

### Step 4.4: If Build Gets Stuck

If it seems stuck or takes too long:

```powershell
# Press Ctrl+C to cancel
# Then try rebuilding without cache:
docker-compose build --no-cache
```

### Step 4.5: Verify Image Was Built

```powershell
# List all Docker images
docker images

# Should show: rdk-testing-dashboard | latest
```

---

## **PART 5: START THE APPLICATION**

### Step 5.1: Start the Container

**Using the automation script:**
```powershell
.\build-and-run.ps1 -Action run
```

**OR using docker-compose:**
```powershell
docker-compose up -d
```

### Step 5.2: Wait for Startup

```powershell
# Check if container is running
docker ps

# Should show: rdk-testing-dashboard container in the list
```

### Step 5.3: Check Container Logs

```powershell
# View live logs
docker-compose logs -f

# Wait until you see: "Running on http://127.0.0.1:5000"
```

---

## **PART 6: ACCESS THE APPLICATION**

### Step 6.1: Open in Browser

Open your web browser and go to:
```
http://localhost:5000
```

✅ **You should see the RDK Testing Dashboard login page!**

### Step 6.2: Check Health Endpoint

You can also verify health:
```
http://localhost:5000/health
```

Should show: `OK` or similar response

---

## **PART 7: TESTING THE APPLICATION**

### Test 7.1: Add a New Device

1. Open http://localhost:5000
2. Click **"Devices"** or **"Add Device"**
3. Fill in device details:
   - **Device Name**: "Test Device 1"
   - **IP Address**: `192.168.1.100` (or your actual device IP)
   - **SSH Port**: `10022`
   - **Username**: `root`
   - **Password**: `your-device-password`
4. Click **"Save"** or **"Add Device"**

✅ **Device should be added successfully**

### Test 7.2: Test Data Persistence

1. **Verify device was saved:**
   ```powershell
   # In PowerShell, check the devices.json file
   Get-Content devices.json | ConvertFrom-Json
   ```
   Should show your new device in the JSON output

2. **Stop the container:**
   ```powershell
   .\build-and-run.ps1 -Action stop
   # OR
   docker-compose down
   ```

3. **Start the container again:**
   ```powershell
   .\build-and-run.ps1 -Action run
   # OR
   docker-compose up -d
   ```

4. **Check the application:**
   - Open http://localhost:5000
   - Go to Devices
   - ✅ **Your device should still be there!**

### Test 7.3: Test SSH Connection

1. Go to Devices page
2. Click the device you added
3. Click **"Test Connection"** or **"Test SSH"**
4. View results:
   - ✅ **Green**: SSH connection successful
   - ❌ **Red**: Check IP address, port, credentials

### Test 7.4: Create a Job (Optional)

1. Go to **Jobs**
2. Click **"Create New Job"**
3. Select your test device
4. Choose a test method
5. Click **"Run"** or **"Submit"**
6. Monitor execution in logs

---

## **PART 8: COMPLETE AUTOMATION COMMANDS**

### Build Commands

```powershell
# Build image only
.\build-and-run.ps1 -Action build

# Build with fresh dependencies (no cache)
docker-compose build --no-cache
```

### Running Commands

```powershell
# Start container
.\build-and-run.ps1 -Action run

# Start and build if needed (one command)
.\build-and-run.ps1 -Action rebuild

# Start using docker-compose
docker-compose up -d
```

### Monitoring Commands

```powershell
# View live logs
.\build-and-run.ps1 -Action logs

# View container status
.\build-and-run.ps1 -Action status

# Check running containers
docker ps

# Check all containers (including stopped)
docker ps -a

# View resource usage
docker stats
```

### Management Commands

```powershell
# Stop the application
.\build-and-run.ps1 -Action stop
docker-compose down

# Remove container
docker rm rdk-testing

# Remove image
docker rmi rdk-testing-dashboard:latest

# Remove everything (containers, images, volumes)
.\build-and-run.ps1 -Action clean

# Open bash shell in container
.\build-and-run.ps1 -Action bash
```

---

## **PART 9: TROUBLESHOOTING**

### Problem: PowerShell Script Execution Error

**Error:** `Cannot be loaded because running scripts is disabled`

**Solution:**
```powershell
# Run once to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force

# Then try again
.\build-and-run.ps1 -Action rebuild
```

### Problem: Port 5000 Already in Use

**Error:** `bind: address already in use`

**Solution:**
```powershell
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process
taskkill /PID <PID> /F

# Or change the port in docker-compose.yml
# Change "5000:5000" to "8000:5000"
# Then access at http://localhost:8000
```

### Problem: Out of Memory During Build

**Error:** `no memory`

**Solution:**
1. Open **Docker Desktop**
2. Click Settings (⚙️ gear icon)
3. Go to **Resources**
4. Set Memory to **6-8 GB**
5. Click **Apply & Restart**
6. Try building again

### Problem: Docker Desktop Won't Start

**Error:** Docker won't launch

**Solution:**
```powershell
# Restart Docker
net stop com.docker.service
net start com.docker.service

# Or restart your computer
```

### Problem: Build Fails (Random Errors)

**Solution:**
```powershell
# Clean everything
docker system prune -a

# Try building again
docker-compose build --no-cache
```

### Problem: Cannot Connect to SSH Devices

**Causes:**
- Incorrect device IP or SSH port
- Firewall blocking SSH
- Device is offline
- SSH credentials wrong

**Solution:**
1. Test SSH manually first:
   ```powershell
   # Install OpenSSH if needed, or:
   ssh root@192.168.1.100 -p 10022
   ```
2. Verify port forwarding/firewall settings
3. Check device is powered on and connected
4. Verify credentials in devices.json

---

## **PART 10: YOUR DATA IS PERSISTENT & SAFE**

### Files That Persist (Your Data is Safe!)

These files are saved on your Windows machine and survive container restarts:

```
C:\Docker\RDKDashboard\
├── devices.json              ← Devices you add via UI
├── jobs.json                 ← Job history
├── iteration_logs\           ← Execution logs & results
├── screenshots\              ← Device screenshots
├── app_state.json            ← Application state
└── [other persistent files]
```

### Backup Your Data

```powershell
# Backup to USB or cloud storage
Copy-Item devices.json C:\Backup\devices.json.backup
Copy-Item jobs.json C:\Backup\jobs.json.backup
Copy-Item iteration_logs C:\Backup\iteration_logs -Recurse
```

---

## **PART 11: QUICK REFERENCE CHEAT SHEET**

### Daily Usage

```powershell
# Day 1: First time setup
cd C:\Docker\RDKDashboard
Copy-Item .env.example .env
notepad .env                    # Configure email
.\build-and-run.ps1 -Action rebuild
# Open http://localhost:5000

# Day 2+: Resume from yesterday
cd C:\Docker\RDKDashboard
.\build-and-run.ps1 -Action run
# Open http://localhost:5000
# All your devices and data are there!

# When done for the day
.\build-and-run.ps1 -Action stop
```

### If Something Goes Wrong

```powershell
# View what's wrong
docker-compose logs

# Restart clean
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## **PART 12: NEXT STEPS**

1. ✅ **Build the image** (you're here!)
2. ✅ **Start the application** 
3. ✅ **Access http://localhost:5000**
4. ✅ **Add your first device**
5. ✅ **Test SSH connection**
6. ✅ **Run your first job**
7. 📊 **Monitor logs in real-time**
8. 📈 **Schedule recurring tests**

---

## **SUPPORT & RESOURCES**

### Documentation Files
- `DOCKER_QUICKSTART.md` - 5-minute quick start
- `DOCKER_COMPLETE_GUIDE.md` - Full documentation
- `README.md` - Application overview
- `build-and-run.ps1` - PowerShell automation script

### Docker Official Resources
- https://docs.docker.com/
- https://docs.docker.com/desktop/install/windows/
- https://docs.docker.com/compose/

### Common Issues
- Check `docker-compose logs` for detailed error messages
- Run `docker system df` to see disk usage
- Run `docker stats` to see resource usage

---

## **SUCCESS CHECKLIST**

- [ ] Docker Desktop installed and running
- [ ] Project files in `C:\Docker\RDKDashboard`
- [ ] `.env` file created and configured
- [ ] Docker image built successfully
- [ ] Container started successfully
- [ ] Application accessible at http://localhost:5000
- [ ] Can access login page
- [ ] Can add a device
- [ ] Data persists after container restart
- [ ] SSH connection test works

**If all boxes are checked, you're ready to go!** 🎉

---

## **YOU'RE ALL SET!**

Your Docker-based RDK Testing Dashboard is now running on Windows!

- Access the application: http://localhost:5000
- View logs: `.\build-and-run.ps1 -Action logs`
- Stop when done: `.\build-and-run.ps1 -Action stop`
- Start next time: `.\build-and-run.ps1 -Action run`

**Happy testing!** 🚀
