# Docker Image File Inclusion Guide

## What Files ARE Included in Docker Image

### Application Source Code (Required)
```
✓ app.py                                   (124 KB)      Main Flask application
✓ session_utils.py                         (~10 KB)      Session management
✓ usb_storage_manager.py                   (~15 KB)      USB detection (NEW)

Controllers/ (256 KB total)
✓ device_controller.py                     Device management logic
✓ test_controller.py                       Test execution logic
✓ queue_controller.py                      Job queue management
✓ results_controller.py                    Result retrieval
✓ __init__.py

Models/ (172 KB total)
✓ device.py                                Device model
✓ test_result.py                           Test result model
✓ saved_sequence.py                        Sequence model
✓ user.py                                  User model
✓ job.py                                   Job model
✓ device_lock.py                           Device lock model
✓ __init__.py

Services/ (472 KB total)
✓ test_execution_service.py                Test execution engine
✓ log_service.py                           Logging service (UPDATED)
✓ queue_service.py                         Queue management
✓ recovery_service.py                      Recovery logic
✓ execution_monitor_service.py             Monitoring
✓ email_service.py                         Email notifications
✓ ai_vision_service.py                     AI/Vision features
✓ __init__.py

Utils/ (76 KB total)
✓ device_lock_manager.py                   Lock management
✓ file_lock.py                             File-based locking
✓ ssh_connectivity_test.py                 SSH utilities
✓ ssh_pool.py                              SSH pool management
✓ ssh_sftp_utils.py                        SFTP utilities

Templates/ (1.2 MB total)
✓ index.html                               Dashboard UI
✓ admin_panel.html                         Admin interface
✓ settings.html                            Settings page
✓ login.html                               Login page
✓ base.html                                Base template
✓ device_control.html                      Device control
✓ *.html                                   All other templates

Static/ (956 KB total)
✓ css/
  ✓ style.css                              Main stylesheet
  ✓ admin.css                              Admin styles
  ✓ dashboard.css                          Dashboard styles
✓ js/
  ✓ main.js                                Main JavaScript
  ✓ device-control.js                      Device control scripts
  ✓ *.js                                   All other scripts
✓ images/
  ✓ *.png, *.jpg                           UI images

Configuration Files (Included)
✓ config_commands.py                       Device commands
✓ config_ir_blaster.py                     IR blaster config
✓ config_log_patterns.py                   Log pattern definitions
✓ config_screenshot.py                     Screenshot settings
✓ config_email.py                          Email configuration
✓ config_ssh_connection.py                 SSH configuration
✓ config_timing.py                         Timing parameters
✓ config_deployment.py                     Deployment settings
✓ config_eta.py                            ETA calculations
✓ config_ai_vision.py                      AI/Vision configuration
✓ config_jump_host.py                      Jump host configuration

Method Files (Included)
✓ method_*.py                              All method definitions
✓ method_maintenance_deepsleep_wakeup.py
✓ method_reboot.py
✓ method_reboot_performance.py
✓ (All other method files)

Python Dependencies (Installed during build)
✓ requirements.txt                         Dependency list
✓ venv/                                    Built from requirements.txt during Docker build
  ✓ bin/python                             Python interpreter
  ✓ lib/python3.11/site-packages/          All pip packages
    ✓ flask                                Web framework
    ✓ paramiko                             SSH library
    ✓ requests                             HTTP library
    ✓ pillow                               Image processing
    ✓ tesseract-ocr                        OCR library
    ✓ (All other dependencies)

Build & System Files (Included)
✓ Dockerfile                               Build instructions
✓ docker-compose.yml                       Compose configuration
✓ docker-compose.rpi.yml                   R-PI specific
✓ docker-compose.dev.yml                   Development config
✓ .dockerignore                            Exclusion rules
✓ README.md                                Documentation
✓ requirements.txt                         Python dependencies

System Dependencies (Installed in Dockerfile)
✓ Python 3.11                              Runtime
✓ tesseract-ocr                            OCR engine
✓ gcc                                      C compiler (for native extensions)
✓ python3-venv                             Virtual environment
```

**Total Included: ~1.5 GB** (dependencies drive most of the size)

---

## What Files ARE NOT Included (Mounted from USB/External)

### Execution & Output Data (NOT in image)
```
❌ Enhancement_output/                     (5.7 GB) - Mounted from USB
   ├── 2026-01-29/                        Session results
   ├── 2026-01-30/                        More results
   └── EXECUTION_LOGS/                    Execution logs

❌ screenshots/                            (703 MB) - Mounted from USB
   ├── device_ip_method_timestamp.png     Execution screenshots
   └── ...

❌ iteration_logs/                         (?) - Mounted from USB
   ├── device_ip_method_timestamp.log     Test logs
   └── ...

❌ logs/                                   (164 MB) - Mounted from USB
   ├── app.log
   ├── flask.log
   └── ...

❌ device_logs/                            (2.5 MB) - Mounted from USB
   ├── device_specific_logs.txt
   └── ...
```

### Unnecessary/Development Files (NOT in image)
```
❌ updated_code/                           (2.9 GB) - Old code backups
❌ SAM-CD-2GB/                             (2.5 GB) - External data
❌ reference_screens/                      (37 MB) - Reference data
❌ captured_images/                        (?) - Old captures
❌ base_images/                            (?) - Image data
❌ venv/                                   (550 MB) - Rebuilt from requirements.txt
```

### Build Artifacts & Logs (NOT in image)
```
❌ __pycache__/                            (752 KB) - Python cache
❌ *.log files                             (4+ MB) - Build/startup logs
❌ *.pid files                             - Process IDs
❌ *.bak files                             - Backups
❌ .git/                                   - Git history
❌ .vscode/                                - IDE config
❌ .idea/                                  - IDE config
```

### Dynamic Runtime Files (Created at runtime, NOT in image)
```
❌ devices.json                            Mounted as volume (config)
❌ jobs.json                               Mounted as volume
❌ device_job_queue.json                   Mounted as volume
❌ device_locks.json                       Mounted as volume
❌ saved_sequences.json                    Mounted as volume
❌ app_state.json                          Mounted as volume
❌ ir_keycodes.json                        Mounted as volume
❌ reset_codes.json                        Mounted as volume
❌ realtime_logs.txt                       Mounted from USB
```

---

## Docker Image Build Process (in order)

1. **Base Image** (200 MB)
   - FROM python:3.11-slim

2. **System Dependencies** (300 MB)
   - apt-get install tesseract-ocr, gcc, python3-venv

3. **Python Virtual Environment** (Included in next step)

4. **Project Dependencies** (800-900 MB)
   - Install from requirements.txt

5. **Application Code** (150-200 MB)
   - COPY everything EXCEPT items in .dockerignore

6. **Final Image Size** (~1.5 GB)
   - Includes: App code + dependencies
   - Excludes: Execution data, old code, artifacts

7. **Runtime Volumes** (Mounted at container start)
   - USB storage for execution results
   - Config files for settings
   - Static files for UI

---

## Volume Mount Strategy

### Running on Docker Desktop (Development)
```yaml
volumes:
  # Configuration - persisted locally
  - ./devices.json:/app/devices.json
  - ./saved_sequences.json:/app/saved_sequences.json
  
  # Execution data - stored on USB if available, else local
  - /media/lrqa/Lexar/enhancement_data:/app/data:rw
  OR
  - ./local_data:/app/data:rw
```

### Running on R-PI (Production)
```yaml
volumes:
  # Configuration - persisted locally
  - ./devices.json:/app/devices.json
  
  # Execution data - auto-mounted from detected USB
  - /mnt/usb_storage:/app/data:rw
  
# USB auto-detected by systemd service before starting container
```

---

## .dockerignore Updated Version

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg
.pytest_cache/
.coverage
htmlcov/

# Virtual environments (rebuilt from requirements.txt)
venv/
env/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Git
.git/
.gitignore
.gitattributes

# Build artifacts
*.log
*.pid
*.bak
*.backup*
*.corrupt*
*.old

# Large unnecessary directories
updated_code/
SAM-CD-2GB/
captured_images/
base_images/
Enhancement_output/
device_logs/
reference_screens/

# Execution data (will be mounted at runtime)
logs/
iteration_logs/
screenshots/

# Runtime state files (will be mounted)
test_results_history.json
app_state.json*
device_job_queue.json
device_locks.json
saved_sequences.json
realtime_logs.txt

# Temporary files
*.tmp
temp/

# Deployment scripts we don't need
build-and-run.sh
docker-mac-setup.sh
docker-rpi-quickstart.sh
docker-rpi-validate.sh
restore_backup.sh
backup_to_usb.sh

# Deployment specific
BACKUP_SUMMARY.txt
GIT_GUIDE.txt

# Service files (managed separately)
*.service

# Development/test files
app_old.py
test_*.py
*_test.py
```

---

## Summary

| Category | Size | Included | Location |
|----------|------|----------|----------|
| **App Code** | ~500 KB | ✓ | In image |
| **Dependencies** | ~1-1.2 GB | ✓ | In image |
| **Execution Data** | 5.7+ GB | ❌ | USB volume |
| **Old Code/Backups** | 5.4 GB | ❌ | Not included |
| **Total Image Size** | **~1.5 GB** | | Final |

**Space Saved: ~10 GB** when excluding execution data from image!
