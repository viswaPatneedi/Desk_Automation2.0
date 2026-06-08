# RDK Dashboard Background Service Setup Guide

## 📋 Overview
The application is now configured to run in a Python virtual environment (venv) in the background with automatic logging and process management.

---

## 🚀 Quick Start

### Start the App (with venv in background)
```bash
cd /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard
./start-app.sh start
```

**Expected Output:**
```
✅ venv activated
📦 Installing dependencies...
✅ Dependencies installed
✅ App started successfully (PID: XXXXX)
📝 Log file: /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard/logs/app-background.log
🌐 Access: http://10.0.0.32:11078
```

### Check App Status
```bash
./start-app.sh status
```

### Stop the App
```bash
./start-app.sh stop
```

### Restart the App
```bash
./start-app.sh restart
```

### View Live Logs
```bash
./start-app.sh logs
```

---

## 🔧 How It Works

### Scripts Included

#### 1. `start-app.sh` - Main Control Script
Features:
- ✅ Automatic venv detection and creation
- ✅ Dependency installation from requirements.txt
- ✅ PID file management for process tracking
- ✅ Logging to `logs/app-background.log`
- ✅ SMTP configuration for email
- ✅ Health checks and status reporting

#### 2. `auto-start.sh` - Startup Helper
Used for:
- Boot-time automatic startup
- Cron job integration
- System startup services

#### 3. `rdk-flask-app.service` - Systemd Service
For optional system integration (requires sudo):
```bash
sudo cp rdk-flask-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rdk-flask-app
sudo systemctl start rdk-flask-app
```

---

## 🔄 Automatic Startup at Boot

### Option 1: Using Cron (Recommended)
Add to crontab:
```bash
crontab -e
```

Add this line:
```
@reboot /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard/start-app.sh start
```

### Option 2: Using Systemd (Requires sudo)
```bash
sudo systemctl enable rdk-flask-app
sudo systemctl start rdk-flask-app
```

Check status:
```bash
sudo systemctl status rdk-flask-app
```

### Option 3: Add to Bashrc
```bash
echo "./start-app.sh start" >> ~/.bashrc
```

---

## 📂 File Locations

| Item | Path |
|------|------|
| Main App | `app.py` |
| Virtual Environment | `venv/` |
| Startup Script | `start-app.sh` |
| Auto-start Script | `auto-start.sh` |
| App Logs | `logs/app-background.log` |
| PID File | `app.pid` |
| Systemd Service | `rdk-flask-app.service` |

---

## 🔍 Troubleshooting

### Check if App is Running
```bash
ps aux | grep "python.*app.py"
ss -tlnp | grep 11078
```

### View App Logs
```bash
tail -100 logs/app-background.log
```

### Follow Live Logs
```bash
./start-app.sh logs
```

### Kill Stuck Process
```bash
./start-app.sh stop
# or
pkill -9 -f "python.*app.py"
```

### Check Port Usage
```bash
ss -tlnp 2>/dev/null | grep 11078
```

### Reset and Start Fresh
```bash
./start-app.sh stop
rm -f app.pid
./start-app.sh start
```

---

## 📊 Environment Variables

The app auto-loads these SMTP settings:
- `SMTP_SERVER=smtp.gmail.com`
- `SMTP_PORT=587`
- `SENDER_EMAIL=cperdkemiddleware@gmail.com`
- `SENDER_PASSWORD=tbbwaifvmtzovqcs`

---

## ✅ Verification Steps

1. **Check App is Running:**
   ```bash
   ./start-app.sh status
   ```

2. **Access Dashboard:**
   ```
   http://10.0.0.32:11078
   ```

3. **View Recent Logs:**
   ```bash
   tail -50 logs/app-background.log
   ```

4. **Verify Port Listening:**
   ```bash
   ss -tlnp | grep 11078
   ```

---

## 📝 Notes

- **venv Path:** `/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard/venv/`
- **Port:** 11078 (hardcoded in app.py)
- **User:** viswa-pi4 (for cron and systemd)
- **Logs:** Stored in `logs/` directory with daily rotation recommendations
- **Database:** Jobs stored in `Json/jobs.json`

---

## 🆘 Support

For issues:
1. Check logs: `./start-app.sh logs`
2. Stop and restart: `./start-app.sh restart`
3. Verify venv: `./venv/bin/python3 --version`
4. Check dependencies: `./venv/bin/pip list`

---

**Setup Completed:** ✅
- App is running in venv in background
- Logs are being captured
- PID is tracked for status monitoring
- Ready for external access
