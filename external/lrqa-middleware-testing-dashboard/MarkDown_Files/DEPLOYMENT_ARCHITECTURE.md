# RDK Middleware USB to Pi Deployment - Visual Architecture

## 📐 DEPLOYMENT ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────┐
│             SYSTEM OVERVIEW & DATA FLOW                          │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐
│  YOUR DEVELOPMENT MACHINE   │
│  (Windows/Mac/Linux)        │
│                             │
│  /home/.../Enhancement/     │
│  ├── app.py                 │
│  ├── requirements.txt       │
│  ├── controllers/           │
│  ├── models/                │
│  ├── templates/             │
│  └── static/                │
└─────────────────────────────┘
             ↓ COPY (USB prep script)
        [prepare-usb-for-rpi.sh]
             ↓
┌─────────────────────────────┐
│   USB STICK (250-300MB)     │
│                             │
│  /rdk-middleware-deployment/├── Entire app code
│  ├── app.py                 ├── Config files
│  ├── config_*.py            ├── Documentation
│  ├── Dockerfile.rpi         └── Setup scripts
│  ├── controllers/           
│  ├── models/                
│  └── ... (100+ files)       
└─────────────────────────────┘
             ↓ INSERT USB INTO PI
        [Manual Step]
             ↓
┌─────────────────────────────┐
│   RASPBERRY PI (New)        │
│                             │
│  ┌─────────────────────────┐│
│  │  ~/rdk-app/             ││ (Files copied from USB)
│  │  ├── app.py             ││
│  │  ├── requirements.txt   ││
│  │  ├── controllers/       ││
│  │  └── ...                ││
│  └─────────────────────────┘│
│                             │
│  Docker Build:              │
│  ├── Docker pulls base      │
│  ├── Installs dependencies  │
│  ├── Copies app code        │
│  └── Creates container      │
│      image (~1.2GB)         │
│                             │
│  Container Running:         │
│  ┌─────────────────────────┐│
│  │  Flask App (Port 11078) ││
│  │  ├── Web UI             ││
│  │  ├── Device SSH         ││
│  │  ├── Job Queue          ││
│  │  └── Log Streaming      ││
│  └─────────────────────────┘│
│                             │
│  Data Directories:          │
│  ├── /logs/                 │ (App logs)
│  ├── /screenshots/          │ (Test screenshots)
│  ├── /iteration_logs/       │ (Execution logs)
│  └── /device_logs/          │ (Device system logs)
│                             │
│  USB Output (Optional):     │
│  └── /media/pi/Lexar/       │ (Test results on USB)
│      Enhancement-output/    │
└─────────────────────────────┘
             ↓ WEB ACCESS
        [Network]
             ↓
┌─────────────────────────────┐
│   YOUR BROWSER              │
│   (Any device on LAN)       │
│                             │
│   http://<PI_IP>:11078      │
│   ├── Dashboard             │
│   ├── Device Management     │
│   ├── Job Execution         │
│   ├── Results/Reports       │
│   └── Log Viewer            │
└─────────────────────────────┘

             ↓ SSH CONNECTIONS (from Pi container)

      ┌─────────────────────┐
      │   MANAGED DEVICES   │
      │                     │
      │  [Device 1]         │ ← SSH Port 10022
      │  [Device 2]         │ ← SSH Port 10022
      │  [Device 3]         │ ← SSH Port 10022
      │  ...                │
      └─────────────────────┘
```

---

## 🔄 DATA FLOW - TEST EXECUTION

```
┌──────────────────────────────────────────────────────────────────┐
│         TEST EXECUTION DATA FLOW                                 │
└──────────────────────────────────────────────────────────────────┘

USER (Browser)
    │
    ├─► http://<PI_IP>:11078
    │   (Access Web Interface)
    │
    ├─► Select Device + Test Method + Iterations
    │
    ├─► Click "Execute"
    │
    └─► FLASK APP (Port 11078)
        │
        ├─► Validate input
        │
        ├─► Create Job record
        │
        ├─► Add to Job Queue
        │
        └─► QUEUE SERVICE (Background)
            │
            ├─► Get next job
            │
            ├─► SSH Connect to Device
            │   (IP:PORT from devices.json)
            │
            ├─► FOR EACH ITERATION:
            │   │
            │   ├─► 1. Capture BEFORE screenshot
            │   │
            │   ├─► 2. Execute test command
            │   │   (e.g., reboot)
            │   │
            │   ├─► 3. Wait for device
            │   │   (with timeout)
            │   │
            │   ├─► 4. Validate home screen
            │   │
            │   ├─► 5. Capture AFTER screenshot
            │   │
            │   ├─► 6. Collect device logs
            │   │   (Optional)
            │   │
            │   └─► 7. Store results
            │       ├─► Main Pi drive
            │       └─► USB stick (if configured)
            │
            └─► Job Complete
                │
                ├─► Generate Report
                │
                ├─► Send Email (if configured)
                │
                └─► Display on Dashboard
                    (User sees results)
```

---

## 📊 FILE & FOLDER ORGANIZATION

```
┌──────────────────────────────────────────────────────────────────┐
│    RASPBERRY PI DIRECTORY STRUCTURE AFTER DEPLOYMENT             │
└──────────────────────────────────────────────────────────────────┘

/home/pi/rdk-app/
│
├── 🔧 Application Core (Required)
│   ├── app.py                          ← Main Flask application
│   ├── requirements.txt                ← Python dependencies
│   ├── Dockerfile.rpi                  ← Docker image definition
│   ├── docker-compose.rpi.yml          ← Compose configuration
│   ├── .dockerignore                   ← Build optimization
│   └── .env                            ← ⚙️ Configuration (created locally)
│
├── 📂 Source Code Directories
│   ├── controllers/
│   │   ├── device_controller.py
│   │   ├── job_controller.py
│   │   ├── queue_controller.py
│   │   ├── results_controller.py
│   │   └── (more controllers)
│   │
│   ├── models/
│   │   ├── device.py
│   │   ├── job.py
│   │   ├── user.py
│   │   ├── result.py
│   │   └── (more models)
│   │
│   ├── services/
│   │   ├── log_service.py
│   │   ├── queue_service.py
│   │   ├── recovery_service.py
│   │   ├── email_service.py
│   │   └── (more services)
│   │
│   ├── utils/
│   │   ├── device_lock_manager.py
│   │   ├── ssh_connectivity_test.py
│   │   ├── screenshot_utils.py
│   │   └── (more utilities)
│   │
│   ├── templates/
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   ├── jobs.html
│   │   ├── components/
│   │   └── (more templates)
│   │
│   └── static/
│       ├── css/
│       │   └── styles.css
│       ├── js/
│       │   ├── lock-status-monitor.js
│       │   └── (more JS files)
│       └── images/
│
├── ⚙️ Configuration Files (update locally)
│   ├── config_commands.py              ← Device commands
│   ├── config_timing.py                ← Timing parameters
│   ├── config_ir_blaster.py            ← IR configuration
│   ├── config_screenshot.py            ← Screenshot settings
│   ├── config_log_patterns.py          ← Log patterns
│   ├── config_ssh_connection.py        ← SSH settings
│   ├── config_deployment.py            ← Deployment config
│   ├── config_email.py                 ← Email service
│   ├── config_eta.py                   ← ETA calculation
│   ├── config_ai_vision.py             ← AI vision
│   └── config_screen_validation.py     ← Screen validation
│
├── 📊 Data Files (created/updated locally)
│   ├── devices.json                    ← Device inventory (⚙️ update)
│   ├── saved_sequences.json            ← Test sequences
│   ├── log_patterns.json               ← Custom patterns
│   ├── system_commands.json            ← System commands
│   └── ir_keycodes.json                ← IR remote keys
│
├── 📚 Documentation (on USB)
│   ├── USB_TO_RPi_COMPLETE_GUIDE.md
│   ├── QUICK_SETUP_REFERENCE.md
│   ├── SETUP_CHECKLIST.md
│   ├── DOCKER_RPI_SETUP.md
│   └── (more docs)
│
├── 📁 Runtime Directories (created on first run)
│   ├── logs/                           ← Application logs
│   │   ├── app.log
│   │   ├── error.log
│   │   └── access.log
│   │
│   ├── screenshots/                    ← Test screenshots
│   │   ├── <device_ip>/
│   │   │   ├── ITR-1/
│   │   │   │   ├── BEFORE/
│   │   │   │   └── AFTER/
│   │   │   └── ITR-2/
│   │   └── (more iterations)
│   │
│   ├── iteration_logs/                 ← Execution logs
│   │   ├── <device>_<method>_<timestamp>.log
│   │   └── (more logs)
│   │
│   ├── device_logs/                    ← Device system logs
│   │   ├── ITR-1/
│   │   │   └── <device>_<timestamp>.tgz
│   │   └── (more iterations)
│   │
│   └── captured_images/                ← Reference images
│
└── 🖥️ Docker-specific (managed by Docker)
    ├── venv/                           ← Python virtualenv (in container)
    ├── __pycache__/                    ← Python cache (in container)
    └── (container-internal)

USB STICK OUTPUT (optional):
/media/pi/Lexar/Enhancement-output/
├── REBOOT_DEVICE-A4K_10-0-0-172_20_ITR_20260413_150000_UTC/
│   ├── SCREENSHOTS/
│   │   ├── ITR-1/BEFORE/
│   │   ├── ITR-1/AFTER/
│   │   └── (more iterations)
│   │
│   ├── EXECUTION_LOGS/
│   │   ├── <device>_<method>_<timestamp>.log
│   │   └── <device>_<method>_<timestamp>.html
│   │
│   └── DEVICE_LOGS/
│       ├── ITR-1/
│       └── (more iterations)
│
└── (more test sessions)
```

---

## 🔐 NETWORK & CONNECTIVITY DIAGRAM

```
┌──────────────────────────────────────────────────────────────────┐
│              NETWORK CONNECTIVITY OVERVIEW                       │
└──────────────────────────────────────────────────────────────────┘

                    LOCAL AREA NETWORK (LAN)
    ┌──────────────────────────────────────────────────────────┐
    │                                                          │
    │  ┌──────────────────────┐                               │
    │  │   Router/WiFi       │                               │
    │  │   (192.168.1.1)     │                               │
    │  └──────────────────────┘                               │
    │      ▲              ▲                                   │
    │      │              │                                   │
    │      │ Ethernet     │ Ethernet/WiFi                    │
    │      │              │                                   │
    │      v              v                                   │
    │  ┌──────────────┐  ┌──────────────────────────────┐   │
    │  │ Raspberry Pi │  │    Your Devices             │   │
    │  │ (12X:100)    │  │    (10.0.0.100-200)         │   │
    │  │              │  │                              │   │
    │  │ Docker       │──┼─► Device A (SSH 10022)       │   │
    │  │ Container    │  │    Device B (SSH 10022)       │   │
    │  │ Port 11078   │  │    Device C (SSH 10022)       │   │
    │  │              │  │    ...                        │   │
    │  └──────────────┘  └──────────────────────────────┘   │
    │      ▲                                                 │
    │      │ HTTP/Browser                                   │
    │      │ (Port 11078)                                   │
    │      │                                                 │
    │      v                                                 │
    │  ┌──────────────────────┐                              │
    │  │  Your Browser        │                              │
    │  │ (Windows/Mac/Linux)  │                              │
    │  │                      │                              │
    │  │ http://<PI_IP>:11078 │                              │
    │  └──────────────────────┘                              │
    │                                                         │
    │  ┌──────────────────────┐                              │
    │  │  USB Data Storage    │                              │
    │  │  (Optional)          │                              │
    │  │  /media/pi/Lexar/    │                              │
    │  └──────────────────────┘                              │
    └──────────────────────────────────────────────────────────┘
```

---

## 📈 DOCKER DEPLOYMENT FLOW

```
┌──────────────────────────────────────────────────────────────────┐
│            DOCKER BUILD & DEPLOYMENT PROCESS                     │
└──────────────────────────────────────────────────────────────────┘

STEP 1: Docker Build Process
┌────────────────────────────────────────────────────────────┐
│ ~/rdk-app/                       Dockerfile.rpi            │
│ ├── app.py                   ────►  Step 1: FROM python:3.11-slim
│ ├── requirements.txt         ────►  Step 2: WORKDIR /app
│ ├── controllers/             ────►  Step 3: Install system packages
│ ├── models/                  ────►  Step 4: Install Tesseract, OpenCV
│ └── ...                      ────►  Step 5: Copy app code
│                              ────►  Step 6: pip install -r requirements.txt
│  ~30-60 minutes              ────►  Step 7: Expose port 11078
│  (build time)                ────►  Step 8: Gunicorn entrypoint
│                                    │
│                                    └─► Docker Image Created
│                                        (~1.2-1.5 GB)
│                                        Tag: rdk-middleware:rpi
└────────────────────────────────────────────────────────────┘
                    ↓
STEP 2: Container Start
┌────────────────────────────────────────────────────────────┐
│ docker compose -f docker-compose.rpi.yml up -d            │
│ │                                                          │
│ ├─► Mount volumes:                                        │
│ │   ├─ ~/rdk-app/devices.json   → /app/devices.json      │
│ │   ├─ ~/rdk-app/log_patterns.json → /app/log_patterns.json
│ │   ├─ ~/rdk-app/iteration_logs → /app/iteration_logs    │
│ │   └─ ~/rdk-app/screenshots   → /app/screenshots        │
│ │                                                          │
│ ├─► Set environment (.env):                              │
│ │   ├─ SMTP_HOST, SENDER_EMAIL, SENDER_PASSWORD         │
│ │   ├─ SECRET_KEY                                        │
│ │   ├─ WORKERS=2, TIMEOUT=300                           │
│ │   └─ FLASK_ENV=production                             │
│ │                                                          │
│ ├─► Map ports:                                           │
│ │   └─ Host:11078 → Container:11078                     │
│ │                                                          │
│ └─► Start Flask App                                      │
│     "[INFO] Listening on 0.0.0.0:11078"                 │
│                                                          │
│     Container Status: UP ✓                              │
└────────────────────────────────────────────────────────────┘
                    ↓
STEP 3: Application Ready
┌────────────────────────────────────────────────────────────┐
│ Running Container: rdk-middleware                         │
│                                                            │
│ Inside Container:                                         │
│ ├─ Flask App (Gunicorn)                                 │
│ ├─ Python 3.11 interpreter                             │
│ ├─ 100+ Python packages installed                       │
│ ├─ Tesseract OCR engine                                 │
│ ├─ SSH client (for device connectivity)               │
│ └─ All app code (controllers, models, etc.)            │
│                                                            │
│ Volumes Mounted:                                          │
│ ├─ /app/devices.json (from Pi host)                     │
│ ├─ /app/iteration_logs (from Pi host)                   │
│ └─ /app/screenshots (from Pi host)                      │
│                                                            │
│ Access Points:                                            │
│ ├─ http://localhost:11078 (from Pi)                     │
│ ├─ http://<PI_IP>:11078 (from network)                  │
│ └─ Data stored on Pi host (persistent)                  │
└────────────────────────────────────────────────────────────┘

Network Isolation:
┌─────────────────┐
│   Docker Bridge │
│                 │
│  ┌─────────────┐
│  │ rdk-        │
│  │ middleware  │ ◄─ Isolated from other containers
│  │ container   │ ◄─ But port 11078 exposed to host
│  └─────────────┘
│
└─────────────────┘
       ▲
       │ Port 11078 (TCP)
       │
       v
   Raspberry Pi
       Host
```

---

## 🎯 DEPLOYMENT TIMELINE

```
TIME    ACTIVITY                           STATUS          DURATION
════════════════════════════════════════════════════════════════════

00:00   USB Prep on Dev Machine            ████░░░░░░░░░  10 min
        (Copy files to USB)

00:10   Raspberry Pi Initial Setup         ████░░░░░░░░░  10 min
        (Install OS, SSH, update)

00:20   File Transfer USB → Pi             ████░░░░░░░░░   5 min
        (Copy files from USB)

00:25   Docker Installation                ████░░░░░░░░░  10 min
        (Install Docker, Compose)

00:35   Application Configuration          ████░░░░░░░░░   5 min
        (Create .env, devices.json)

00:40   Docker Build (LONGEST STEP)        ███████░░░░░░ 30-60 min
        ⚠️ Pi 3: up to 90 min             (Varies by Pi)
           Pi 4: 20-40 min
           Pi 5: 10-20 min

01:40   Container Startup & Testing        ████░░░░░░░░░  10 min
        (Start app, verify connectivity)

01:50   Verification & Web Access          ████░░░░░░░░░   5 min
        (Access dashboard, test device)

01:55   Complete! ✅                       ████████████░  Done!

TOTAL:  ~75-105 minutes (mostly automated)
```

---

## 🔗 CONNECTION CHECKLIST

```
VERIFY EACH CONNECTION:

Pi Host Machine:
  [ ] Power cable connected
  [ ] Network cable OR WiFi connected
  [ ] Monitor/HDMI connected (optional)
  
Docker Container:
  [ ] Running: docker ps shows "rdk-middleware"
  [ ] Port: docker port rdk-middleware shows 11078
  [ ] Healthy: curl http://localhost:11078 returns 200

Managed Devices:
  [ ] Powered on and online
  [ ] IP address accessible from Pi (ping <IP>)
  [ ] SSH port 10022 open and responsive
  [ ] SSH credentials correct in devices.json

Browser Access:
  [ ] Find Pi IP: hostname -I
  [ ] Open: http://<PI_IP>:11078
  [ ] JavaScript enabled in browser
  [ ] WebSocket capable (for log streaming)

USB Storage (Optional):
  [ ] USB stick formatted (FAT32 or exFAT)
  [ ] Mounted at /media/pi/Lexar/ (or similar)
  [ ] Has write permissions
  [ ] Space available (100GB+ recommended)
```

---

## 📊 SYSTEM RESOURCE PLANNING

```
RESOURCE REQUIREMENTS BY RASPBERRY PI MODEL

┌───────────────────────────────────────────────────────────┐
│                    Pi Model Comparison                    │
├─────────────┬──────────┬──────────┬──────────┬────────────┤
│   Feature   │   Pi3    │   Pi4    │   Pi5    │ Recommended
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ CPU         │ ARMv7    │ ARMv8    │ ARMv8    │ ✓ Pi5
│             │ 1.4 GHz  │ 1.5 GHz  │ 2.4 GHz  │
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ RAM         │ 1 GB     │ 2-8 GB ╔═ 4-8 GB   │ ✓ 8GB Pi4/5
│ Recommended │ min      │ (use 2) ║ (optimal)│
├─────────────┼──────────┼──────────┨──────────┼────────────┤
│ Docker      │ 1G       │ 2G       │ 4G       │ (memory:
│ Memory      │ (tight)  │ (good)   │ (plenty) │  config)
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ Workers     │ 1        │ 2        │ 4        │ (WORKERS
│ (concurrency)          │          │          │  env var)
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ Build Time  │ 60-90min │ 20-40min │ 10-20min │ (varies)
│ (first time)           │          │          │
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ Runtime     │ ~200MB   │ ~300MB   │ ~400MB   │ (memory
│ Memory      │ (typical)│ (typical)│ (typical)│  usage)
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ Concurrent  │ 1-2      │ 3-5      │ 5-10     │ (test
│ Tests       │          │          │          │  runs)
├─────────────┼──────────┼──────────┼──────────┼────────────┤
│ Suggested   │ 4GB SD   │ 32GB SD  │ 64GB SD+ │ (storage)
│ Storage     │ min      │ good     │ (best)   │
└─────────────┴──────────┴──────────┴──────────┴────────────┘

CALCULATION FORMULA:

Concurrent Tests = (Available_RAM - OS_Reserve - Docker_Reserve) / Avg_Per_Test
                 = (RAM - 512MB - 512MB) / 100-150MB

Example (8GB Pi 4):
                 = (8000MB - 512MB - 512MB) / 125MB
                 = 6976MB / 125MB
                 = ~55 concurrent tests possible
```

---

**Architecture & Deployment Diagrams - Visual Guide Created ✅**  
**For Complete Setup Instructions → Read USB_TO_RPi_COMPLETE_GUIDE.md**  
**For Quick Reference → Read QUICK_SETUP_REFERENCE.md**
