# Quick Reference - MVC Architecture with Auto-Recovery

## 🚀 Start/Stop Application

### Using Systemd Service (Recommended - Port 8080)
```bash
# Install service (one-time)
./install_service.sh

# Start
sudo systemctl start rdk-testing.service

# Stop
sudo systemctl stop rdk-testing.service

# Restart
sudo systemctl restart rdk-testing.service

# Status
sudo systemctl status rdk-testing.service

# View logs (live)
sudo journalctl -u rdk-testing.service -f
```

### Manual Start (Port 5000)
```bash
./run_production.sh
```

## 📊 Quick Health Checks

```bash
# Is app running?
ps aux | grep gunicorn

# Check recovery status
wget -q -O - http://localhost:8080/api/recovery/status | python3 -m json.tool

# List devices
wget -q -O - http://localhost:8080/api/devices | python3 -m json.tool

# Queue status
wget -q -O - http://localhost:8080/api/queue/status | python3 -m json.tool

# View recovery state
cat app_state.json | python3 -m json.tool
```

## 🔧 Architecture Quick Map

```
app.py                        → Routing layer
├── controllers/              → HTTP handlers
│   ├── device_controller     → /api/devices
│   ├── test_controller       → /api/execute
│   ├── queue_controller      → /api/queue/*
│   └── results_controller    → /api/results, /api/logs
├── services/                 → Business logic
│   ├── test_execution_service → Test orchestration
│   ├── log_service           → Logging + SSE streaming
│   ├── queue_service         → Job queue
│   └── recovery_service      → Auto-recovery
└── models/                   → Data layer
    ├── device                → Device CRUD
    └── test_result           → Results persistence
```

## 🛡️ Recovery Features

- **Auto-checkpoint:** Every 30 seconds
- **State files:** app_state.json, checkpoint.pkl
- **Crash detection:** Automatic on restart
- **Queue restoration:** All pending jobs restored
- **Session tracking:** 24-hour cleanup

## 📁 Important Files

```
app.py                  - Main application (290 lines)
app_old.py              - Original backup (1,239 lines)
rdk-testing.service     - Systemd service definition
install_service.sh      - Service installer
app_state.json          - Recovery state (JSON)
checkpoint.pkl          - Recovery checkpoint (binary)
devices.json            - Device configurations
test_results_history.json - Test results
```

## 🌐 Access URLs

- **Dashboard:** http://localhost:8080/
- **Results:** http://localhost:8080/results
- **API Docs:** See MVC_RECOVERY_COMPLETE.md

## ⚡ Common Tasks

### Kill stuck processes
```bash
pkill -f gunicorn
sudo systemctl restart rdk-testing.service
```

### View checkpoint details
```bash
cat app_state.json | python3 -m json.tool
ls -lh checkpoint.pkl app_state.json
```

### Test recovery
```bash
# During a test execution:
sudo systemctl stop rdk-testing.service
sleep 5
sudo systemctl start rdk-testing.service
# Check if test resumed
```

## 📈 Monitoring

```bash
# CPU/Memory usage
top -p $(pgrep -d',' gunicorn)

# Port binding
sudo lsof -i :8080

# Worker processes
ps aux | grep gunicorn | wc -l  # Should be 9 (1 master + 8 workers)

# Logs directory size
du -sh logs/ iteration_logs/
```

## 🎯 Status: ✅ Operational

Current application running on **port 8080** with:
- 8 Gunicorn workers
- Auto-recovery enabled
- 30-second checkpointing
- Systemd service ready to install
