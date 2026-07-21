# Background Service Setup - Feature Usage & Documentation

## Date: July 21, 2026

### Feature Overview
Both Flask applications (Enhancement and Desk-Automation 2.0) are now configured to run as background systemd services with automatic restart capabilities. This eliminates the need for manual application startup and provides persistent, production-ready deployment.

### Setup Details

#### 1. Enhancement Application
- **Port**: 11078
- **Service Name**: `enhancement-flask-app.service`
- **Working Directory**: `/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement`
- **Virtual Environment**: `/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/venv`
- **Service File**: `/etc/systemd/system/enhancement-flask-app.service`
- **Log File**: `/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/logs/enhancement-service.log`

#### 2. Desk-Automation 2.0 Application
- **Port**: 11079
- **Service Name**: `desk-automation-flask-app.service`
- **Working Directory**: `/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard`
- **Virtual Environment**: `/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/venv`
- **Service File**: `/etc/systemd/system/desk-automation-flask-app.service`
- **Log File**: `/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/logs/desk-automation-service.log`

### Issues Fixed

#### 1. Circular Import in job.py
**Problem**: `TransactionRollbackHandler` import at module level caused circular import issues during app startup.

**Solution**: Moved import statement inside the `save_all()` method where it's actually needed, preventing import-time circular dependency.

**Files Modified**: 
- `models/job.py` - Removed top-level import, added local import in `save_all()` method

#### 2. Missing requirements.txt
**Problem**: Desk-Automation 2.0 had no `requirements.txt` file, making dependency management unclear.

**Solution**: Created comprehensive `requirements.txt` with all dependencies matching the virtual environment.

**Files Created**:
- `requirements.txt` - Complete dependency list for reproducible installs

### Service Management

#### Start Services
```bash
sudo systemctl start enhancement-flask-app.service desk-automation-flask-app.service
```

#### Stop Services
```bash
sudo systemctl stop enhancement-flask-app.service desk-automation-flask-app.service
```

#### Check Status
```bash
sudo systemctl status enhancement-flask-app.service desk-automation-flask-app.service
```

#### View Logs
```bash
sudo journalctl -u enhancement-flask-app.service -f
sudo journalctl -u desk-automation-flask-app.service -f
```

#### Enable Auto-Start on Boot
```bash
sudo systemctl enable enhancement-flask-app.service desk-automation-flask-app.service
```

### Service Features
- **Type**: Simple (foreground process)
- **Restart Policy**: Always restart on failure
- **Restart Delay**: 10 seconds
- **Auto-Start**: Enabled on system boot
- **User**: lrqa
- **Logging**: Captured to respective log files with timestamps

### Verification Commands

```bash
# Check service status
ps aux | grep "python app.py" | grep -v grep

# Verify port listening
ss -tlnp | grep -E ":11078|:11079"

# Test connectivity
curl http://localhost:11078/
curl http://localhost:11079/

# Check systemd status
systemctl list-units --type=service | grep flask-app
```

### Environment Variables
Both services use the following environment variables:
- `FLASK_HOST`: 0.0.0.0 (listen on all interfaces)
- `FLASK_PORT`: 11078 (Enhancement) or 11079 (Desk-Automation)

### Troubleshooting

**Service fails to start:**
1. Check logs: `sudo journalctl -u <service-name> -n 50`
2. Verify venv exists and has dependencies installed
3. Check port availability: `sudo netstat -tlnp | grep 11078` or `grep 11079`
4. Verify file permissions on log directories

**Port already in use:**
```bash
# Find process using port
sudo lsof -i :11078
# Kill if needed
sudo kill -9 <PID>
```

### Dependencies

#### Enhancement
- Flask 3.0.0
- Flask-Login 0.6.3
- Flask-Bcrypt 1.0.1
- paramiko 3.4.0
- Pillow 10.1.0
- pytesseract 0.3.10
- requests 2.31.0
- And others (see requirements.txt)

#### Desk-Automation 2.0
- Flask 3.0.0
- Flask-Login 0.6.3
- Flask-Bcrypt 1.0.1
- paramiko 3.4.0
- Pillow 10.1.0
- openpyxl 3.1.5
- opencv-python 4.8.1.78
- numpy >= 1.26.0
- gevent 24.2.1
- And others (see requirements.txt)

### Future Enhancements
1. Add health check endpoints for monitoring
2. Implement log rotation policy
3. Add metrics collection for service uptime
4. Configure reverse proxy (nginx) for port mapping
5. Set up centralized logging aggregation

---
**Changes Committed**: 
- models/job.py (fixed circular import)
- requirements.txt (created)
