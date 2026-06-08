# Docker for Windows - Final Summary & Setup Instructions

## 📦 What You've Been Given

You have received a **complete Docker-based RDK Testing Dashboard application** that you can build and run on your Windows machine.

### Included Files:
1. **Application Code** - All Python files, Flask app, controllers, models, services
2. **Docker Configuration** - Dockerfile, docker-compose.yml
3. **Automation Scripts** - build-and-run.ps1 (PowerShell for Windows)
4. **Documentation** - Complete guides for setup and usage

---

## 🚀 3-Minute Setup (TL;DR)

```powershell
# Step 1: Install Docker Desktop
# Download: https://www.docker.com/products/docker-desktop
# Install & Restart Computer

# Step 2: Copy all files to Windows
mkdir C:\Docker\RDKDashboard
# Copy all project files here

# Step 3: Setup email config
cd C:\Docker\RDKDashboard
Copy-Item .env.example .env
notepad .env
# Edit: Add your Gmail email & app password

# Step 4: Build & Run
.\build-and-run.ps1 -Action rebuild

# Step 5: Open Application
# Browser: http://localhost:5000
```

**That's it!** ✅

---

## 📋 Complete Step-by-Step Guide

### **Step 1: Install Docker Desktop (5 minutes)**

1. Go to: https://www.docker.com/products/docker-desktop
2. Click "Download for Windows" → `Docker Desktop Installer.exe`
3. Double-click the installer
4. Click "Install" → Grant admin permissions
5. Wait for completion → Click "Finish"
6. **RESTART YOUR COMPUTER** (important!)

**Verify Installation:**
```powershell
# Open PowerShell and run:
docker --version
docker run hello-world
# Both should work
```

---

### **Step 2: Prepare Project Files (5 minutes)**

**Option A: Copy from Email/USB**
```powershell
# Create directory
mkdir C:\Docker\RDKDashboard

# Copy all files here
# (You should have: app.py, Dockerfile, requirements.txt, etc.)
```

**Option B: Clone from Git**
```powershell
cd C:\Docker
git clone https://github.com/viswaPatneedi/lrqa-middleware-testing-dashboard.git RDKDashboard
cd RDKDashboard
```

**Verify Files:**
```powershell
cd C:\Docker\RDKDashboard
dir
# Should see: Dockerfile, docker-compose.yml, app.py, requirements.txt, etc.
```

---

### **Step 3: Configure Email (2 minutes)**

**Create .env file:**
```powershell
cd C:\Docker\RDKDashboard
Copy-Item .env.example .env
```

**Edit with your email:**
```powershell
notepad .env
```

**Add these lines (minimal config):**
```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-gmail-app-password
```

**Get Gmail App Password:**
1. Go to: https://myaccount.google.com/apppasswords
2. Select: Mail → Windows Computer
3. Copy generated password → Paste into .env

**Save file** (Ctrl+S)

---

### **Step 4: Build Docker Image (10-15 minutes)**

```powershell
cd C:\Docker\RDKDashboard

# Option A: Using automation script (recommended)
.\build-and-run.ps1 -Action build

# Option B: Using docker-compose directly
docker-compose build
```

**What's happening:**
- Downloading Python 3.11 (~150 MB)
- Installing Tesseract OCR
- Installing Python packages (~2 GB)
- Creating Docker image (~6.5 GB total)

**Wait until you see:** ✅ "Successfully tagged rdk-testing-dashboard:latest"

---

### **Step 5: Start the Application (30 seconds)**

```powershell
cd C:\Docker\RDKDashboard

# Option A: Using automation script
.\build-and-run.ps1 -Action run

# Option B: Using docker-compose
docker-compose up -d
```

**Verify it's running:**
```powershell
docker ps
# Should show: rdk-testing-dashboard | status: Up X minutes
```

---

### **Step 6: Access the Application**

Open your web browser to:
```
http://localhost:5000
```

✅ **You should see the RDK Testing Dashboard login page!**

---

## 🧪 Testing the Application

### Test 1: Add a Device

1. Open http://localhost:5000
2. Devices → Add Device
3. Fill in:
   - Device Name: "Test Device"
   - IP: `192.168.1.100` (your device IP)
   - Port: `10022`
   - Username: `root`
   - Password: `your-password`
4. Click Save

✅ Device should be added

### Test 2: Verify Data Persistence

1. Close browser
2. Stop Docker: `.\build-and-run.ps1 -Action stop`
3. Start Docker: `.\build-and-run.ps1 -Action run`
4. Open http://localhost:5000
5. Go to Devices

✅ Your device should still be there!

### Test 3: Check File Storage

```powershell
# Verify your device was saved
Get-Content C:\Docker\RDKDashboard\devices.json | ConvertFrom-Json
```

✅ Should show your device in JSON format

---

## 📊 Your Data Files Location

All your data is stored on your Windows machine:

```
C:\Docker\RDKDashboard\
├── devices.json          ← Your devices (PERSISTENT ✓)
├── jobs.json             ← Job history (PERSISTENT ✓)
├── iteration_logs\       ← Execution logs (PERSISTENT ✓)
├── screenshots\          ← Screenshots (PERSISTENT ✓)
└── app_state.json        ← App state (PERSISTENT ✓)
```

**Your data survives Docker restarts!** ✅

---

## 🎮 Daily Usage

### **Every Day: Start Application**
```powershell
cd C:\Docker\RDKDashboard
.\build-and-run.ps1 -Action run
# Open http://localhost:5000
```

### **Every Day: Stop Application**
```powershell
.\build-and-run.ps1 -Action stop
# Or: Ctrl+C if viewing logs
```

### **If Something Goes Wrong**
```powershell
# View error logs
docker-compose logs

# Restart
docker-compose down
docker-compose up -d
```

---

## 🛠️ Common Commands

```powershell
# ========== BUILDING ==========
.\build-and-run.ps1 -Action build      # Build image only
docker-compose build --no-cache        # Rebuild from scratch

# ========== RUNNING ==========
.\build-and-run.ps1 -Action run        # Start container
.\build-and-run.ps1 -Action stop       # Stop container
docker-compose up -d                   # Start using compose
docker-compose down                    # Stop using compose

# ========== MONITORING ==========
.\build-and-run.ps1 -Action logs       # View live logs
docker ps                              # List containers
docker stats                           # View resource usage

# ========== TROUBLESHOOTING ==========
docker-compose logs                    # Show error logs
docker images                          # List images
docker system prune -a                 # Clean everything up
```

---

## 🚨 If PowerShell Script Won't Run

```powershell
# Run this ONCE to allow scripts:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force

# Then try again:
.\build-and-run.ps1 -Action rebuild
```

---

## 💾 Your Files Checklist

Make sure you have these files in `C:\Docker\RDKDashboard\`:

```
☐ Dockerfile
☐ docker-compose.yml
☐ .dockerignore
☐ .env.example
☐ requirements.txt
☐ app.py
☐ build-and-run.ps1
☐ controllers/           (folder)
☐ models/              (folder)
☐ services/            (folder)
☐ templates/           (folder)
☐ static/              (folder)
☐ config_*.py files    (multiple)
```

All folders and files from the Enhancement project should be copied.

---

## ✅ Success Indicators

After following the guide, you should see:

✅ Docker Desktop installed and running  
✅ `docker --version` shows version number  
✅ Image built: `docker images` shows `rdk-testing-dashboard`  
✅ Container running: `docker ps` shows `rdk-testing-dashboard`  
✅ Application accessible at http://localhost:5000  
✅ Can see the login page  
✅ Can add devices  
✅ Data persists after restart  

**If all checks pass, you're done!** 🎉

---

## 📚 Documentation Available

Refer to these files for more details:

| File | Content |
|------|---------|
| **DOCKER_QUICKSTART.md** | 5-minute quick start |
| **DOCKER_COMPLETE_GUIDE.md** | Very detailed setup guide |
| **DOCKER_WINDOWS_INSTALLATION_GUIDE.md** | Comprehensive Windows-specific guide |
| **DOCKER_WINDOWS_QUICK_REFERENCE.md** | Commands reference & troubleshooting |
| **build-and-run.ps1** | PowerShell automation script (read the comments) |

---

## 🎯 Next Steps After Setup

1. **Add Devices** - UI: Devices → Add Device (with SSH details)
2. **Test Connection** - Click device → Test Connection
3. **Run Tests** - Jobs → Create Job → Run
4. **Monitor Logs** - View real-time execution logs
5. **Schedule Tests** - Set up recurring test sequences

---

## 💡 Pro Tips

1. **Keep Docker running** - It stays in system tray, no need to stop/start
2. **View logs while testing** - `.\build-and-run.ps1 -Action logs` in separate PowerShell
3. **Backup your data** - `Copy-Item devices.json C:\Backup\devices.json.backup`
4. **Use Docker Desktop UI** - Application icon in system tray has GUI
5. **First build is slow** - ~15 minutes, but cached on subsequent builds

---

## 🐛 Troubleshooting

### Port 5000 In Use
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Out of Memory
- Docker Desktop → Settings → Resources → Memory: 6-8 GB

### Build or Container Error
```powershell
docker-compose logs        # Shows what went wrong
docker-compose down        # Stop
docker-compose build --no-cache  # Rebuild
docker-compose up -d       # Start
```

### Script Won't Run
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
```

---

## 🎓 Learning Resources

- Docker Docs: https://docs.docker.com/
- Docker Desktop Windows: https://docs.docker.com/desktop/install/windows/
- Docker Compose: https://docs.docker.com/compose/

---

## ✨ You're All Set!

You now have everything to:
- ✅ Build Docker image on Windows
- ✅ Run application in Docker
- ✅ Add devices and test
- ✅ Persist your data
- ✅ Monitor execution
- ✅ Troubleshoot issues

### **Ready to Start?**

```powershell
cd C:\Docker\RDKDashboard
.\build-and-run.ps1 -Action rebuild
# Then open: http://localhost:5000
```

---

## 📞 Quick Support

**Problem?** Check in this order:
1. Run `docker-compose logs` to see errors
2. Check this file's "Troubleshooting" section
3. Check **DOCKER_WINDOWS_QUICK_REFERENCE.md**
4. Restart Docker: `docker-compose down && docker-compose up -d`

**Stuck?** Google the error message or check Docker official docs.

---

## 🚀 You Got This!

The hardest part is over - you have everything ready to go!

Start building and testing now! 🎉

**Happy testing!** 🍀
