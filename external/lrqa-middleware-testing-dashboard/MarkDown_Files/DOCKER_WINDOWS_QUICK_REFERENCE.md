# Docker for Windows - Quick Reference & Summary

## 🚀 Super Quick Start (TL;DR)

```powershell
# 1. Download & install Docker Desktop: https://www.docker.com/products/docker-desktop
# 2. Copy project files to: C:\Docker\RDKDashboard
# 3. In PowerShell:
cd C:\Docker\RDKDashboard
Copy-Item .env.example .env
notepad .env                    # Add your email: SENDER_EMAIL & SENDER_PASSWORD
.\build-and-run.ps1 -Action rebuild
# 4. Open browser: http://localhost:5000
```

**Done!** Your application is running. ✅

---

## 📋 What Each Step Does

### 1. Download Docker Desktop
- Download from: https://www.docker.com/products/docker-desktop
- Install size: ~1 GB
- Contains: Docker Engine, Docker CLI, Docker Compose

### 2. Get Project Files
- Copy all files from Enhancement project to: `C:\Docker\RDKDashboard`
- Required files: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `app.py`, etc.

### 3. Create .env File
- Copy template: `Copy-Item .env.example .env`
- Edit with your SMTP settings (Gmail recommended)
- This file is NEVER committed to git (security)

### 4. Build Docker Image
- Command: `.\build-and-run.ps1 -Action build`
- Time: 10-15 minutes (first time only)
- Creates: ~6.5 GB Docker image
- Includes: Python 3.11, Tesseract OCR, all dependencies

### 5. Start Container
- Command: `.\build-and-run.ps1 -Action run`
- Time: 30 seconds
- Result: Application running at http://localhost:5000

### 6. Add Devices & Test
- Web UI: http://localhost:5000
- Add devices with SSH details
- Test connections
- Run jobs

---

## 🛠️ Command Reference

### **Build Commands**

```powershell
# Build image (slow first time)
.\build-and-run.ps1 -Action build

# Build without docker cache (very slow, fresh dependencies)
docker-compose build --no-cache

# Quick check: is image built?
docker images | findstr rdk-testing
```

### **Start/Stop Commands**

```powershell
# Start container
.\build-and-run.ps1 -Action run

# Or:
docker-compose up -d

# Stop container
.\build-and-run.ps1 -Action stop

# Or:
docker-compose down

# Build AND start (one command)
.\build-and-run.ps1 -Action rebuild
```

### **Monitoring Commands**

```powershell
# View live logs
.\build-and-run.ps1 -Action logs

# See container status
docker ps

# Check resource usage
docker stats

# Inspect detailed container info
docker inspect rdk-testing
```

### **Troubleshooting Commands**

```powershell
# View error logs
docker-compose logs

# See last 100 lines of logs
docker-compose logs --tail=100

# Execute command in container
docker-compose exec web bash

# Open interactive bash shell
.\build-and-run.ps1 -Action bash

# Completely remove everything
.\build-and-run.ps1 -Action clean
```

---

## 📁 Project Structure on Windows

```
C:\Docker\RDKDashboard\
├── Dockerfile                  ← Docker configuration
├── docker-compose.yml          ← Container configuration
├── .env                        ← YOUR email settings (create from .env.example)
├── .env.example                ← Template (do NOT edit)
├── requirements.txt            ← Python dependencies
├── app.py                      ← Flask application
├── build-and-run.ps1           ← Windows automation script
│
├── controllers/                ← Flask logic
├── models/                     ← Data models
├── services/                   ← Services (SSH, logs, etc)
├── templates/                  ← HTML templates
├── static/                     ← CSS, JS, images
│
├── devices.json                ← ⭐ Your devices (PERSISTENT)
├── jobs.json                   ← ⭐ Job history (PERSISTENT)
├── app_state.json              ← ⭐ Application state (PERSISTENT)
│
├── iteration_logs/             ← ⭐ Execution logs (PERSISTENT)
├── screenshots/                ← ⭐ Device screenshots (PERSISTENT)
│
└── [other config files]
```

**⭐ = Your data persists even if container restarts!**

---

## 🔧 Configuration (.env File)

### Minimal .env (Gmail)
```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-char-app-password
```

### Full .env (All Options)
```env
# Flask
SECRET_KEY=your-secure-key-here
FLASK_ENV=production

# Email via Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# OR Email via Comcast
# SMTP_HOST=mailrelay.comcast.com
# SMTP_PORT=25
# SENDER_EMAIL=your-email@comcast.net
```

### Getting Gmail App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Select: **Mail** and **Windows Computer**
3. Copy the 16-character password → paste into `.env`

---

## ✅ Verification Checklist

After each step, verify:

```powershell
# Docker installed?
docker --version
# Output: Docker version X.X.X, build abc123

# Docker running?
docker ps
# Output: Shows container list (may be empty initially)

# Image built?
docker images | findstr rdk-testing
# Output: Shows rdk-testing-dashboard image

# Container running?
docker ps
# Output: Shows rdk-testing-dashboard container with status "Up X minutes"

# Application accessible?
curl http://localhost:5000
# Output: HTML content (or status code)

# Or open browser: http://localhost:5000
```

---

## 🐛 Common Problems & Solutions

| Problem | Command to Fix |
|---------|---|
| "Cannot run scripts" | `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force` |
| Port 5000 in use | `netstat -ano \| findstr :5000` then `taskkill /PID <PID> /F` |
| Out of memory | Docker Desktop → Settings → Resources → Memory: 6-8 GB |
| Build too slow | `docker-compose build --no-cache` (slower but fresh) |
| Container won't start | `docker-compose logs` (shows error details) |
| Lost my data | Check `devices.json`, `jobs.json` in project folder |
| Docker won't start | `net stop com.docker.service` then `net start com.docker.service` |

---

## 📊 Data Persistence & Backup

### Your Data Files (PERSISTENT - Safe!)
```
devices.json      ← Devices you add
jobs.json         ← Job history
iteration_logs/   ← Execution logs
screenshots/      ← Device screenshots
app_state.json    ← Application state
```

### Backup Strategy
```powershell
# Backup important files
Copy-Item devices.json C:\Backup\devices.json.backup
Copy-Item jobs.json C:\Backup\jobs.json.backup
Copy-Item iteration_logs C:\Backup\iteration_logs -Recurse
```

### Restore from Backup
```powershell
# Stop container
.\build-and-run.ps1 -Action stop

# Restore files
Copy-Item C:\Backup\devices.json C:\Docker\RDKDashboard\devices.json -Force

# Start container
.\build-and-run.ps1 -Action run
```

---

## 🎯 Daily Workflows

### **First Time (Day 1)**
```powershell
# 30 minutes total
cd C:\Docker\RDKDashboard
Copy-Item .env.example .env
notepad .env                    # ~2 min: Add Gmail password
.\build-and-run.ps1 -Action rebuild  # ~15 min: Build
# Open http://localhost:5000   # Application ready!
# Add devices & test            # ~10 min
```

### **Next Day (Start Fresh)**
```powershell
# 2 minutes total
cd C:\Docker\RDKDashboard
.\build-and-run.ps1 -Action run
# Open http://localhost:5000
# All data still there! ✓
```

### **Resume Interrupted Testing**
```powershell
# Container is already running
# Just open browser: http://localhost:5000
# Continue testing
```

### **Stop for the Day**
```powershell
cd C:\Docker\RDKDashboard
.\build-and-run.ps1 -Action stop
# Container is stopped, data is safe
```

### **Troubleshoot Issues**
```powershell
cd C:\Docker\RDKDashboard
docker-compose logs          # See what went wrong
docker-compose down          # Stop everything
docker-compose build --no-cache  # Rebuild fresh
docker-compose up -d         # Start again
```

---

## 💡 Pro Tips

### Tip 1: View Real-Time Logs
```powershell
# In a separate PowerShell window:
.\build-and-run.ps1 -Action logs

# See live output while testing
# Press Ctrl+C to exit
```

### Tip 2: Quick Status Check
```powershell
# See what's running
docker ps

# See resource usage
docker stats
```

### Tip 3: Keep Container Running
- Docker Desktop stays in system tray
- Container continues running in background
- No need to rebuild next time

### Tip 4: Use Docker Desktop GUI
- Docker Desktop has UI to see containers, images, logs
- Sometimes easier than PowerShell commands

### Tip 5: Advanced: Open Container Shell
```powershell
# Run commands inside container
docker-compose exec web bash

# Inside container:
ls -la                    # List files
python app.py --version   # Check app version
exit                      # Exit bash
```

---

## 🚨 Emergency Cleanup

If everything breaks:

```powershell
# Complete reset
docker-compose down -v                    # Remove everything
docker system prune -a                    # Clean up
docker images                             # View remaining images
docker rmi rdk-testing-dashboard:latest   # Remove image

# Then rebuild
docker-compose build --no-cache
docker-compose up -d
```

**Note:** Your `devices.json`, `jobs.json`, etc. are safe even after complete reset!

---

## 📚 Full Documentation

For more details, see:
- **DOCKER_QUICKSTART.md** - 5-minute quick start
- **DOCKER_COMPLETE_GUIDE.md** - Very detailed guide
- **DOCKER_WINDOWS_INSTALLATION_GUIDE.md** - This detailed Windows guide
- **DOCKER_IMPLEMENTATION_SUMMARY.md** - Technical details

---

## 🎓 Learn More

### Docker Basics
- https://docs.docker.com/get-started/ (official intro)
- https://docker.com/ (official site)

### Docker Desktop for Windows
- https://docs.docker.com/desktop/install/windows/
- https://docs.docker.com/desktop/troubleshoot/

### Docker Compose
- https://docs.docker.com/compose/ (official reference)
- https://docs.docker.com/compose/compose-file/ (file reference)

---

## ✨ You Have Everything You Need!

You now have:
- ✅ Docker installed on Windows
- ✅ All project files
- ✅ Configuration template (.env)
- ✅ Automation script (build-and-run.ps1)
- ✅ Complete documentation
- ✅ Troubleshooting guide
- ✅ Daily workflow examples

### Ready to Go! 🚀

```powershell
# One command to start everything:
.\build-and-run.ps1 -Action rebuild

# Then open: http://localhost:5000
```

**Happy testing!** 🎉

---

## 📞 Need Help?

1. **Check the logs:** `docker-compose logs`
2. **Google the error message**
3. **Check Docker troubleshooting:** https://docs.docker.com/desktop/troubleshoot/
4. **Review this guide's "Common Problems" section**

Good luck! 🍀
