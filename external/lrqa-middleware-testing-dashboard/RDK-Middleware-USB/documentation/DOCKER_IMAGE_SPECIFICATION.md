╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║         🐳 DOCKER IMAGE SPECIFICATION - RPI4 CLEAN BUILD 🐳                 ║
║                                                                              ║
║            RDK-E Middleware QA Dashboard - ARM/ARM64 Optimized              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝


📊 IMAGE OVERVIEW:
═══════════════════════════════════════════════════════════════════════════════

IMAGE TAG:        rdk-middleware-dashboard:rpi4-clean
BASE IMAGE:       python:3.11-slim (ARM/ARM64)
ARCHITECTURE:     ARM/ARM64 (Raspberry Pi 4, Pi 5)
BUILD DATE:       2026-04-17
STATUS:           Production Ready


📦 IMAGE SIZE ESTIMATE:
═══════════════════════════════════════════════════════════════════════════════

| Component                    | Size      | Breakdown                      |
|------------------------------|-----------|--------------------------------|
| Base Image (python:3.11-slim)| ~150 MB   | Debian + Python 3.11 runtime   |
| System Dependencies          | ~250 MB   | GCC, openssh-client, Tesseract |
| Virtual Environment          | ~50 MB    | Python venv + pip/setuptools   |
| Python Packages              | ~400 MB   | Flask, OpenCV, NumPy, SciPy    |
| Application Code             | ~15 MB    | Flask app + configs + templates|
| Virtual Environment Overhead | ~50 MB    | Site-packages dependencies     |
|                              |           |                                |
| TOTAL IMAGE SIZE             | ~750-900  | Final compressed size: 750-900 |
|                              | MB        | MB (actual ~1.0 GB uncompressed)|

**Note:** Actual size depends on compression and optimization during build.
Typical range: **800MB-1.0 GB**


🏗️ IMAGE LAYER BREAKDOWN:
═══════════════════════════════════════════════════════════════════════════════

LAYER 1: Base Image
  ├── FROM python:3.11-slim
  ├── Debian Bullseye minimal runtime
  ├── Python 3.11 interpreter
  ├── pip, setuptools, wheel
  └── Size: ~150 MB

LAYER 2: System Dependencies (APT packages)
  ├── Build essentials: gcc, g++, build-essential
  ├── Python development: python3-dev, python3-venv
  ├── SSH: openssh-client (for device connections)
  ├── Image processing: libffi-dev, libssl-dev
  ├── OCR: tesseract-ocr, tesseract-ocr-eng
  ├── Utilities: git, curl, wget, nano
  ├── Cleanup: rm -rf /var/lib/apt/lists/* (removes ~100MB)
  └── Size: ~250 MB

LAYER 3: Python Virtual Environment
  ├── python -m venv /app/venv
  ├── Isolated Python environment
  ├── Upgraded pip/setuptools
  └── Size: ~50 MB

LAYER 4: Python Dependencies (requirements.txt)
  ├── 15 Python packages installed
  ├── Compiled from wheels (pre-built binaries for ARM)
  ├── --no-cache-dir flag (saves space)
  └── Size: ~400 MB
  
  Includes:
    • Flask 3.0.0 + extensions (Login, Bcrypt)
    • Paramiko 3.4.0 (SSH library)
    • OpenCV 4.8.1.78 (image processing)
    • NumPy 1.24.3 (numerical computing)
    • SciPy 1.12.0 (scientific computing)
    • scikit-image 0.22.0 (image recognition)
    • Pillow 10.1.0 (image manipulation)
    • pytesseract 0.3.10 (OCR wrapper)
    • gunicorn 21.2.0 + gevent (WSGI server)
    • requests 2.31.0 (HTTP library)
    • openpyxl 3.1.5 (Excel support)
    • imagehash 4.3.1 (image hashing)

LAYER 5: Application Code
  ├── COPY requirements.txt .
  ├── COPY . .  (copies all non-ignored files)
  ├── Application source code
  ├── Configuration files
  ├── Templates and static assets
  └── Size: ~15 MB

LAYER 6: Volume Directories & Permissions
  ├── mkdir -p /app/data/{screenshots, iteration_logs, ...}
  ├── chmod -R 755 /app/data
  ├── chown -R nobody:nogroup /app/data
  └── Size: <1 MB (empty directories)

LAYER 7: Entrypoint Script
  ├── COPY docker-entrypoint.sh /app/docker-entrypoint.sh
  ├── chmod +x /app/docker-entrypoint.sh
  └── Size: <1 MB


✅ WHAT'S INCLUDED IN IMAGE:
═══════════════════════════════════════════════════════════════════════════════

APPLICATION CODE (Full & Latest):
  ✅ app.py                    [Main Flask application]
  ✅ wsgi.py                   [WSGI entry point]
  ✅ log_patterns.json         [Log patterns database - FIXED]
  
  ✅ controllers/              [Business logic]
     ├── device_controller.py
     ├── test_controller.py
     ├── job_controller.py
     ├── queue_controller.py
     ├── result_controller.py
     └── [other controllers]
  
  ✅ models/                   [Data models]
     ├── device.py
     ├── test.py
     ├── result.py
     ├── job.py
     ├── user.py
     └── [other models]
  
  ✅ services/                 [Background services]
     ├── log_service.py        [Log streaming via SSE]
     ├── queue_service.py      [Job queue management]
     ├── device_service.py     [Device operations]
     ├── recovery_service.py   [Recovery & failover]
     └── [other services]
  
  ✅ templates/                [HTML templates]
     ├── index.html            [Main dashboard]
     ├── device.html
     ├── test.html
     ├── results.html
     └── [other templates]
  
  ✅ static/                   [CSS, JavaScript, assets]
     ├── css/style.css
     ├── js/app.js
     ├── js/charts.js
     └── [other static assets]

CONFIGURATION FILES (All Latest Changes):
  ✅ config_commands.py        [Device commands & methods]
  ✅ config_ir_blaster.py      [IR blaster settings]
  ✅ config_log_patterns.py    [Log pattern configuration]
  ✅ config_timing.py          [Execution timing settings]
  ✅ config_screenshot.py      [Screenshot configuration]
  ✅ config_ssh_connection.py  [SSH connection settings]
  ✅ config_email.py           [Email/SMTP configuration]
  ✅ config_deployment.py      [Deployment settings]
  ✅ config_ai_vision.py       [AI vision settings]

PYTHON PACKAGES (15 dependencies):
  ✅ Flask 3.0.0               [Web framework]
  ✅ Flask-Login 0.6.3         [User session management]
  ✅ Flask-Bcrypt 1.0.1        [Password hashing]
  ✅ Paramiko 3.4.0            [SSH client library]
  ✅ Pillow 10.1.0             [Image processing/manipulation]
  ✅ pytesseract 0.3.10        [OCR wrapper (uses system tesseract)]
  ✅ requests 2.31.0           [HTTP client library]
  ✅ gunicorn 21.2.0           [WSGI HTTP server]
  ✅ gevent 24.2.1             [Asynchronous framework]
  ✅ openpyxl 3.1.5            [Excel file handling]
  ✅ opencv-python 4.8.1.78    [Computer vision library]
  ✅ numpy 1.24.3              [Numerical computing]
  ✅ imagehash 4.3.1           [Image hashing/comparison]
  ✅ scikit-image 0.22.0       [Image processing algorithms]
  ✅ scipy 1.12.0              [Scientific computing]

SYSTEM PACKAGES (Preinstalled in container):
  ✅ build-essential           [C/C++ compiler toolchain]
  ✅ gcc, g++                  [GNU C/C++ compilers]
  ✅ openssh-client            [SSH client for device connections]
  ✅ libffi-dev, libssl-dev    [Libraries for cryptography]
  ✅ tesseract-ocr             [OCR engine]
  ✅ tesseract-ocr-eng         [English language model for OCR]
  ✅ git                       [Version control (for git operations)]
  ✅ curl, wget                [HTTP/download utilities]
  ✅ nano                      [Text editor (for debugging)]

OTHER FEATURES:
  ✅ Python 3.11 virtual environment prebuilt
  ✅ Entrypoint script (validates configs, initializes)
  ✅ Health check configured (HTTP)
  ✅ Non-root user (nobody) for security
  ✅ Data volume directories created

RUNTIME COMPONENTS:
  ✅ Gunicorn 2 worker processes
  ✅ Gevent worker class (async)
  ✅ 120-second request timeout
  ✅ Access/error logging enabled
  ✅ Port 11078 exposed


❌ WHAT'S NOT INCLUDED (Deliberately Excluded):
═══════════════════════════════════════════════════════════════════════════════

Python Cache & Build Artifacts:
  ❌ __pycache__/              [Removed]
  ❌ *.pyc, *.pyo files        [Removed]
  ❌ .pytest_cache/            [Removed]
  ❌ dist/, build/             [Removed]
  ❌ *.egg-info/               [Removed]

IDE & Editor Files:
  ❌ .vscode/                  [Removed]
  ❌ .idea/                    [Removed]
  ❌ *.swp, *.swo              [Removed]

Version Control:
  ❌ .git/                     [Removed]
  ❌ .github/                  [Removed]
  ❌ .gitignore                [Removed]

EXECUTION DATA (All runtime files - rebuilt on startup):
  ❌ iteration_logs/           [Not included - created at runtime]
  ❌ screenshots/              [Not included - created at runtime]
  ❌ device_logs/              [Not included - created at runtime]
  ❌ logs/                     [Not included - created at runtime]
  ❌ *.log files               [Not included - created at runtime]
  ❌ app.log, flask.log        [Not included - created at runtime]
  ❌ *.json.backup*            [Not included]
  ❌ *.pid files               [Not included]
  ❌ *.tmp, *.temp files       [Not included]

Archives & Backups:
  ❌ *.zip, *.tar.gz           [Not included]
  ❌ *.bak, *.backup*          [Not included]

Other Unnecessary Files:
  ❌ Virtual environment (venv/) [Rebuilt fresh]
  ❌ .env.local                [Not included]
  ❌ .DS_Store, Thumbs.db      [Not included]


📌 DOCKER BUILD PROCESS:
═══════════════════════════════════════════════════════════════════════════════

Dockerfile Location:  Dockerfile.rpi.clean
Ignore Configuration: .dockerignore.rpi.clean
Entrypoint:          docker-entrypoint.sh

Build Command (on RPi):
  docker build -f Dockerfile.rpi.clean \
    -t rdk-middleware-dashboard:rpi4-clean .

Build Time:
  - First build: 5-10 minutes (includes compilation)
  - Cached builds: 2-5 minutes (only changed layers)

Build Optimizations:
  ✅ Layer caching: requirements.txt copied separately
  ✅ Multi-stage considerations (slim base image)
  ✅ APT cleanup: --no-install-recommends + rm -rf /var/lib/apt/lists
  ✅ Pip cache disabled: --no-cache-dir flag
  ✅ ARM-optimized dependencies (precompiled wheels)


🚀 RUNTIME CONFIGURATION:
═══════════════════════════════════════════════════════════════════════════════

Container Runtime:
  - Entrypoint: /app/docker-entrypoint.sh
  - Default CMD: gunicorn (Flask WSGI server)
  - Workers: 2 (configurable for RPi resources)
  - Worker Class: gevent (async, efficient)
  - Timeout: 120 seconds
  - Binding: 0.0.0.0:11078

Health Check:
  - Type: HTTP (curl to /)
  - Interval: 30 seconds
  - Timeout: 10 seconds
  - Start Period: 40 seconds
  - Retries: 3

Logging:
  - Access log: stdout (for docker logs)
  - Error log: stderr (for docker logs)
  - Format: Gunicorn default format

User:
  - Runtime user: nobody (non-root)
  - Ownership: /app/data owned by nobody
  - Permissions: 755 (rwxr-xr-x)

Data Volumes:
  - /app/data              [Persistent execution data]
  - /app/reference_screens [Reference images storage]
  - /app/data/screenshots
  - /app/data/iteration_logs
  - /app/data/execution_logs
  - /app/data/device_logs
  - /app/data/app_logs
  - /app/data/sessions
  - /app/data/uploads


📊 LAYER SIZES BREAKDOWN:
═══════════════════════════════════════════════════════════════════════════════

Layer 1 - Base Image (python:3.11-slim)
  Size: ~150 MB
  Compressed: ~60 MB
  
Layer 2 - System Dependencies
  Size: ~250 MB
  Breakdown:
    - build-essential, gcc, g++: ~100 MB
    - openssh-client: ~10 MB
    - tesseract-ocr: ~30 MB
    - Other utilities: ~20 MB
    - After cleanup: ~110 MB (roughly)
  
Layer 3 - Venv Setup
  Size: ~50 MB
  
Layer 4 - Python Dependencies
  Size: ~400 MB
  Main contributors:
    - opencv-python: ~150 MB (with precompiled wheels)
    - numpy: ~100 MB
    - scipy: ~60 MB
    - scikit-image: ~40 MB
    - Other packages: ~50 MB
  
Layer 5 - Application Code
  Size: ~15 MB
  
Layer 6 - Volume Directories
  Size: <1 MB
  
Layer 7 - Entrypoint Script
  Size: <1 MB

TOTAL UNCOMPRESSED: ~750-900 MB
COMPRESSED (Docker): ~800 MB-1.0 GB


⚙️ DEPLOYMENT SPECIFICATIONS:
═══════════════════════════════════════════════════════════════════════════════

Supported Platforms:
  ✅ Raspberry Pi 4 (ARM v7l) - 2GB minimum, 4GB+ recommended
  ✅ Raspberry Pi 5 (ARM64)     - 8GB recommended
  ✅ Any ARM/ARM64 32-bit or 64-bit system

Minimum Requirements:
  - RAM: 2GB (tight - will use all)
  - Disk: 32GB (2-3GB for image + data)
  - CPU: Dual-core minimum (4+core recommended)
  - Storage type: SD card or USB (SSD better)

Recommended Requirements:
  - RAM: 4GB (comfortable operation)
  - Disk: 64GB+ (more room for data)
  - CPU: Quad-core (RPi 4 has 4 cores)
  - Storage: USB/SSD for better I/O

Optimal Requirements:
  - RAM: 8GB+ (excellent performance)
  - Disk: 128GB+ (plenty of room)
  - CPU: Quad-core+ with high clock
  - Storage: NVMe SSD (fastest)


🔐 IMAGE SECURITY:
═══════════════════════════════════════════════════════════════════════════════

Security Features:
  ✅ Non-root user: nobody (no privilege escalation)
  ✅ Minimal attack surface:
     - No SSH server (uses SSH client for connections)
     - No sudo access
     - Limited system utilities
     - Slim base image (fewer packages = fewer vulnerabilities)
  ✅ Read-only filesystem possible (can be configured)
  ✅ Network isolation (custom Docker networks)
  ✅ Health checks (automatic recovery)

Image Scanning:
  - No known critical vulnerabilities (base image)
  - Regular updates recommended for python:3.11-slim


📋 VERIFICATION CHECKLIST:
═══════════════════════════════════════════════════════════════════════════════

To verify image contents after build:

  # Check image info
  docker images rdk-middleware-dashboard:rpi4-clean
  
  # Inspect image layers
  docker history rdk-middleware-dashboard:rpi4-clean
  
  # SSH into running container
  docker exec -it <container-id> bash
  
  # Check application files
  docker exec -it <container-id> ls -la /app/
  
  # View Python packages
  docker exec -it <container-id> pip list
  
  # Check data directories
  docker exec -it <container-id> ls -la /app/data/
  
  # Verify system packages
  docker exec -it <container-id> dpkg -l


📞 DOCKER COMMANDS REFERENCE:
═══════════════════════════════════════════════════════════════════════════════

Build Image
  docker build -f Dockerfile.rpi.clean \
    -t rdk-middleware-dashboard:rpi4-clean .

View Built Images
  docker images | grep rdk-middleware

Check Image Size
  docker images --format "table {{.Repository}}\t{{.Size}}" | grep rdk

View Image Layers
  docker history rdk-middleware-dashboard:rpi4-clean

Inspect Image Details
  docker inspect rdk-middleware-dashboard:rpi4-clean

Remove Image
  docker rmi rdk-middleware-dashboard:rpi4-clean

Run Container
  docker run -d \
    -p 11078:11078 \
    -v app_data:/app/data \
    -v reference_screens:/app/reference_screens \
    --name rdk-dashboard \
    rdk-middleware-dashboard:rpi4-clean

View Logs
  docker logs -f rdk-dashboard


═══════════════════════════════════════════════════════════════════════════════

✅ SUMMARY:

IMAGE TOTAL SIZE:      ~800 MB - 1.0 GB (compressed)
BUILD TIME (First):    5-10 minutes on RPi 4
BUILD TIME (Updates):  2-5 minutes (cached)
RUNTIME MEMORY:        512 MB baseline + application data
STORAGE SPACE NEEDED:  ~20-25 GB on RPi for image + data

WHAT'S INCLUDED:
  ✅ Complete latest application code
  ✅ All 15 Python dependencies
  ✅ System packages (OCR, SSH, image processing)
  ✅ Flask web application
  ✅ Device controllers & services
  ✅ Web UI templates & static assets
  ✅ Configuration for all services
  ✅ Health checks & monitoring
  ✅ Non-root user execution
  ✅ Data persistence volumes

WHAT'S NOT INCLUDED:
  ❌ Execution data/logs (created at runtime)
  ❌ Screenshots/iteration logs
  ❌ Build artifacts/cache
  ❌ IDE files/.vscode
  ❌ .git repository

═══════════════════════════════════════════════════════════════════════════════

Version: 2.0 (RPi 4 Clean Build)
Status: Production Ready
Last Updated: 2026-04-17
