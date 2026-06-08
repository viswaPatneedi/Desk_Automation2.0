# 🚀 RDK Testing Dashboard - Complete Application Overview

## 📋 Executive Summary

**RDK Testing Dashboard** is a production-grade, web-based automation platform for managing, testing, and monitoring RDK (Reference Design Kit) middleware devices over SSH. Built with Flask using industry-standard MVC architecture, the application provides real-time device control, automated testing workflows, comprehensive logging, and intelligent crash recovery.

> **💡 Key Highlight:** Designed for laboratory and production environments, this dashboard enables QA engineers to execute thousands of automated test iterations with full traceability, organized outputs, and email notifications.

---

## 🎯 Core Capabilities

### **1. Device Management**
- ✅ **Multi-Device Registry**: Manage unlimited devices with IP, port, credentials
- ✅ **SSH Connectivity Testing**: Verify device accessibility before test execution
- ✅ **MAC Address Fetch**: Auto-retrieve device MAC addresses
- ✅ **Device Lock Management**: Prevent concurrent testing on same device
- ✅ **Real-Time Device Viewer**: Live SSH session monitoring per device

### **2. Automated Testing Methods**
- ✅ **Reboot Testing**: Complete boot cycle verification with HOME screen detection
- ✅ **Deep Sleep Testing**: Sleep mode entry/exit with IR wake-up
- ✅ **Performance Reboot (V2)**: Advanced reboot with screen validation and timing analysis
- ✅ **IR Command Testing**: Blind IR key sequence testing via iTach
- ✅ **Voice Command Execution**: Voice assistant command testing
- ✅ **Remote Key Sequences**: Send IR key combinations with timing
- ✅ **Screen Validation**: AI-powered OCR for HOME screen detection
- ✅ **Xumo Activation**: Automated activation code fetching and device activation

### **3. Job Queue & Execution**
- ✅ **Device-Specific Queues**: Independent job queues per device
- ✅ **Multi-Iteration Support**: Run tests 1-100+ iterations
- ✅ **Sequential Execution**: Methods execute in order with proper state management
- ✅ **Job Cancellation**: Cancel running jobs safely
- ✅ **Queue Persistence**: Jobs survive application restarts
- ✅ **ETA Calculation**: Real-time progress and time estimates
- ✅ **Active Job Tracking**: Monitor running jobs across all devices

### **4. Logging & Results**
- ✅ **Real-Time Log Streaming**: Live execution logs via Server-Sent Events (SSE)
- ✅ **Per-Iteration Logs**: Separate log files for each execution
- ✅ **UTC Timestamping**: All logs use UTC with clear timestamps
- ✅ **Device System Logs**: SFTP capture of `/opt/logs/` from devices
- ✅ **Device-Specific Log Organization**: `device_logs/<device_ip>/ITR-<N>/`
- ✅ **Screenshot Capture**: Before/after screenshots per iteration
- ✅ **HTML Reports**: Summary reports with pass/fail statistics
- ✅ **USB Output Organization**: Session-based folder structure on USB

### **5. Auto-Recovery & Persistence**
- ✅ **Checkpoint Every 30s**: Automatic state persistence
- ✅ **Crash Detection**: Automatic detection on application restart
- ✅ **Queue Restoration**: Resume pending jobs after crash
- ✅ **Session Recovery**: Restore active test sessions
- ✅ **JSON & Pickle State**: Dual format for reliability

### **6. User Management & Security**
- ✅ **User Registration & Login**: Flask-Login authentication
- ✅ **Admin Permissions**: Role-based access control
- ✅ **Password Reset via Email**: Secure reset with 6-digit codes
- ✅ **Session Management**: 24-hour persistent sessions
- ✅ **Password Hashing**: Werkzeug secure password storage

### **7. Email Notifications**
- ✅ **SMTP Integration**: Gmail or Comcast mail relay support
- ✅ **Test Completion Emails**: Automatic notifications with results
- ✅ **Password Reset Emails**: 6-digit verification codes
- ✅ **Configuration Detection**: Auto-enable when SMTP configured

### **8. Advanced Features**
- ✅ **Saved Sequences**: Save/load method sequences with inputs
- ✅ **IR Keycode Management**: JSON-based IR key mapping
- ✅ **AI Vision OCR**: Tesseract-based screen text detection
- ✅ **Screenshot Comparison**: Base image capture and validation
- ✅ **Layout Validation**: Multi-reference screen comparison
- ✅ **Dynamic Port Detection**: Auto-detect iTach IR blaster ports
- ✅ **Health Check Endpoint**: Container health monitoring

---

## 🏗️ Technical Architecture

### **MVC Pattern Implementation**

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                      │
│                  HTML/CSS/JavaScript UI                      │
└─────────────────────────────────────────────────────────────┘
                              ▲│
                              │▼
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLLERS (Routes)                      │
│  device_controller.py │ test_controller.py │ queue_controller│
│  results_controller.py                                       │
└─────────────────────────────────────────────────────────────┘
                              ▲│
                              │▼
┌─────────────────────────────────────────────────────────────┐
│                 SERVICES (Business Logic)                    │
│  test_execution_service │ queue_service │ recovery_service   │
│  log_service │ email_service                                 │
└─────────────────────────────────────────────────────────────┘
                              ▲│
                              │▼
┌─────────────────────────────────────────────────────────────┐
│                    MODELS (Data Layer)                       │
│  Device │ Job │ User │ TestResult │ SavedSequence           │
│  (JSON Persistence: devices.json, jobs.json, users.json)    │
└─────────────────────────────────────────────────────────────┘
```

### **Technology Stack**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.11 | Core application logic |
| **Web Framework** | Flask 3.0.0 | HTTP routing and templating |
| **WSGI Server** | Gunicorn | Production-grade server (4-8 workers) |
| **Authentication** | Flask-Login | User session management |
| **SSH/SFTP** | Paramiko 3.4.0 | Device communication |
| **OCR** | Tesseract | Screen text recognition |
| **Email** | smtplib | SMTP notifications |
| **Frontend** | Bootstrap 5 | Responsive UI framework |
| **Real-Time** | Server-Sent Events | Live log streaming |
| **Persistence** | JSON files | Data storage |
| **Containerization** | Docker | Cloud deployment |

---

## 📂 File Structure Overview

```
Enhancement/
│
├── app.py                          # 🔹 Main Flask application (thin routing layer)
│
├── models/                         # 🔹 Data Models (JSON persistence)
│   ├── device.py                   # Device CRUD operations
│   ├── job.py                      # Job queue management
│   ├── user.py                     # User authentication
│   ├── test_result.py              # Test results (3-day retention)
│   ├── saved_sequence.py           # Saved test sequences
│   └── device_lock.py              # Device lock management
│
├── controllers/                    # 🔹 Request Handlers (HTTP routes)
│   ├── device_controller.py        # Device management API
│   ├── test_controller.py          # Test execution API
│   ├── queue_controller.py         # Queue management API
│   └── results_controller.py       # Results & logs API
│
├── services/                       # 🔹 Business Logic
│   ├── test_execution_service.py   # Test orchestration
│   ├── queue_service.py            # Job queue processing
│   ├── log_service.py              # Log streaming
│   ├── recovery_service.py         # Auto-recovery & checkpointing
│   └── email_service.py            # Email notifications
│
├── method_*.py                     # 🔹 Test Method Implementations
│   ├── method_reboot.py            # Reboot testing logic
│   ├── method_deepsleep.py         # Deep sleep testing
│   ├── method_reboot_performance_v2.py  # Advanced reboot with validation
│   ├── method_ir_test.py           # IR command testing
│   ├── method_voice_command.py     # Voice assistant testing
│   ├── method_remote_keys.py       # IR key sequences
│   ├── method_xumo_activation.py   # Xumo activation automation
│   ├── method_screen_validation.py # Screen validation logic
│   └── method_utils.py             # Shared utilities
│
├── config_*.py                     # 🔹 Configuration Files
│   ├── config_commands.py          # SSH command templates
│   ├── config_ir_blaster.py        # IR blaster settings
│   ├── config_timing.py            # Timing constants
│   ├── config_log_patterns.py      # Log pattern matching
│   ├── config_screenshot.py        # Screenshot settings
│   ├── config_eta.py               # ETA calculations
│   ├── config_ai_vision.py         # OCR settings
│   ├── config_screen_validation.py # Screen validation configs
│   └── config_deployment.py        # Deployment info
│
├── templates/                      # 🔹 HTML Templates (Jinja2)
│   ├── index.html                  # Main dashboard
│   ├── results.html                # Results page
│   ├── jobs.html                   # Jobs page
│   ├── job_detail.html             # Job detail view
│   ├── device_viewer.html          # Device SSH viewer
│   ├── login.html                  # Login page
│   ├── register.html               # Registration page
│   └── forgot_password.html        # Password reset
│
├── static/                         # 🔹 Static Assets
│   ├── css/styles.css              # Custom styles
│   └── js/main.js                  # Client-side logic
│
├── iteration_logs/                 # 🔹 Execution Logs (per-iteration)
│   └── <device_ip>_<method>_<timestamp>_UTC.log
│
├── device_logs/                    # 🔹 Device System Logs (from /opt/logs/)
│   └── <device_ip>/
│       └── ITR-<N>/
│           ├── sky-messages.log
│           ├── core_log.txt
│           └── *.tar.gz
│
├── screenshots/                    # 🔹 Screenshots
│   └── <device_ip>_<method>_<phase>_<timestamp>.png
│
├── reference_screens/              # 🔹 Base Images for Validation
│   └── <device>_home_screen_base.png
│
├── Data Files (JSON)               # 🔹 Persistent Data
│   ├── devices.json                # Device registry
│   ├── jobs.json                   # Job queue/history
│   ├── users.json                  # User accounts
│   ├── test_results_history.json   # Test results (3-day retention)
│   ├── saved_sequences.json        # Saved test sequences
│   ├── device_locks.json           # Device lock state
│   ├── ir_keycodes.json            # IR key mappings
│   ├── reset_codes.json            # Password reset codes
│   ├── app_state.json              # Recovery state (JSON)
│   └── checkpoint.pkl              # Recovery checkpoint (binary)
│
├── Docker Files                    # 🔹 Containerization
│   ├── Dockerfile                  # Production Docker image
│   ├── docker-compose.yml          # Container orchestration
│   ├── .dockerignore               # Docker ignore rules
│   └── .env.example                # Environment variable template
│
├── Service Files                   # 🔹 Systemd Services (Linux)
│   ├── rdk-testing.service         # Main service
│   └── device-testing.service      # Alternative service
│
└── Documentation                   # 🔹 Guides & References
    ├── README.md                   # Main documentation
    ├── INSTALLATION_GUIDE.md       # Setup instructions
    ├── DOCKER_BUILD_GUIDE.md       # Docker deployment
    ├── EMAIL_SETUP_GUIDE.md        # Email configuration
    ├── DEVICE_LOGS_ORGANIZATION.md # Log folder structure
    ├── USB_FOLDER_STRUCTURE.md     # USB output organization
    ├── MVC_RECOVERY_COMPLETE.md    # Architecture details
    ├── FEATURES_IMPLEMENTED_NOV20.md  # Feature summary
    └── ... (many more guides)
```

---

## 🔄 Application Workflow

### **Typical Test Execution Flow**

```
1. USER ACTIONS
   └─> Login to dashboard
   └─> Add/select device from registry
   └─> Choose test method (Reboot, Deep Sleep, etc.)
   └─> Set iteration count (1-100+)
   └─> Configure method inputs (IR keys, voice text)
   └─> Add to queue or execute immediately

2. QUEUE PROCESSING
   └─> Queue Service validates job
   └─> Checks device lock (prevents concurrent tests)
   └─> Acquires device lock
   └─> Submits to Test Execution Service

3. TEST EXECUTION
   └─> Creates session folder (USB or local)
   └─> Establishes SSH connection to device
   └─> Streams real-time logs to browser (SSE)
   └─> Executes method logic (per-iteration):
       ├─> Take "BEFORE" screenshot
       ├─> Execute test commands (reboot, IR keys, etc.)
       ├─> Wait for device state changes
       ├─> Verify expected state (HOME screen, etc.)
       ├─> Take "AFTER" screenshot
       ├─> Capture device logs via SFTP (/opt/logs/)
       └─> Record pass/fail result

4. RESULT STORAGE
   └─> Save iteration logs to iteration_logs/
   └─> Save device logs to device_logs/<device_ip>/ITR-<N>/
   └─> Save screenshots to screenshots/ or USB
   └─> Update test_results_history.json
   └─> Generate HTML report

5. NOTIFICATIONS
   └─> Send email with test results (if configured)
   └─> Release device lock
   └─> Update job status to "completed"
   └─> Process next job in queue

6. RECOVERY CHECKPOINT
   └─> Every 30 seconds during execution:
       ├─> Save app_state.json
       ├─> Save checkpoint.pkl
       └─> Update session tracking
```

---

## 🎨 User Interface Features

### **Dashboard Sections**

1. **Device Control Panel**
   - Device selection dropdown
   - Iteration count input
   - Method selection cards
   - Quick SSH connectivity test
   - Execute button with progress indicator

2. **Job Queue Manager**
   - Add methods to queue with inputs
   - View pending jobs per device
   - Cancel running jobs
   - Real-time ETA display
   - Queue persistence indicator

3. **Real-Time Log Viewer**
   - Live execution log streaming
   - Color-coded status messages (✓ ✗ ⚠)
   - Auto-scroll with manual override
   - Download log button
   - Clear log button

4. **Results Dashboard**
   - Test statistics (pass/fail/error counts)
   - Recent test history table
   - Per-device result filtering
   - Download HTML reports
   - 3-day auto-cleanup

5. **Device Management**
   - Add/remove devices
   - View device list with credentials
   - Test SSH connectivity
   - Fetch MAC addresses
   - Device lock status

6. **Saved Sequences**
   - Save current queue as named sequence
   - Load saved sequences
   - View sequence details (methods + inputs)
   - Delete sequences
   - Sequence count badges

7. **User Account**
   - Login/logout
   - Registration
   - Password reset (email-based)
   - Admin permissions indicator

---

## 🔐 Security Features

| Feature | Implementation | Purpose |
|---------|---------------|---------|
| **Password Hashing** | Werkzeug PBKDF2 | Secure password storage |
| **Session Management** | Flask-Login | Secure user sessions |
| **CSRF Protection** | Flask built-in | Prevent cross-site attacks |
| **SSH Key Storage** | Encrypted JSON | Secure device credentials |
| **Email Verification** | 6-digit codes | Password reset validation |
| **Admin Role** | Role-based access | Restrict privileged operations |
| **Device Locks** | Mutex-style locks | Prevent concurrent device access |
| **HTTPS Support** | SSL certificates | Encrypted communication (optional) |

---

## 📊 Logging System

### **Two-Tier Log Structure**

#### **1. Iteration Logs** (`iteration_logs/`)
- **Purpose**: Dashboard's view of test execution
- **Content**: SSH commands, timing, status checks, results
- **Format**: `<device_ip>_<method>_<timestamp>_UTC.log`
- **Example**: `10.253.182.85_Reboot_20260114_042623_UTC.log`

#### **2. Device Logs** (`device_logs/`)
- **Purpose**: Device's internal system logs
- **Content**: Actual log files from device's `/opt/logs/`
- **Format**: `<device_ip>/ITR-<N>/<logfile>`
- **Example**: `10.253.182.85/ITR-5/sky-messages.log`
- **Files Captured**:
  - `sky-messages.log`
  - `core_log.txt`
  - `receiver.log`
  - Full tarball (`.tar.gz`)

### **Log File Features**
- ✅ **UTC Timestamps**: All logs use UTC timezone
- ✅ **Status Icons**: ✓ (success), ✗ (error), ⚠ (warning)
- ✅ **Structured Format**: Header, steps, footer
- ✅ **Real-Time Streaming**: SSE-based live updates
- ✅ **Download Support**: Download any log file
- ✅ **Auto-Organization**: Device-specific folders with iterations

---

## 📈 USB Output Organization

### **Session-Based Folder Structure**

When USB is connected at `/media/pi/Lexar/`, outputs are organized:

```
/media/pi/Lexar/Enhancement-output/
└── <METHOD>_<DEVICENAME>_<IP>_<ITERATIONS>_ITR_<TIMESTAMP>/
    ├── SCREENSHOTS/
    │   ├── ITR-1/
    │   │   ├── BEFORE/
    │   │   └── AFTER/
    │   ├── ITR-2/
    │   └── ...
    ├── EXECUTION_LOGS/
    │   ├── <device>_<method>_<timestamp>.log
    │   └── <device>_<method>_<timestamp>.html
    └── DEVICE_LOGS/
        ├── ITR-1/
        ├── ITR-2/
        └── ...
```

**Example:**
```
REBOOT_ELEMENT-A4K_10-0-0-172_20_ITR_20260114_143022_UTC/
```

- Complete isolation per test session
- Easy archival and transfer
- All outputs in one place
- Falls back to local storage if USB not available

---

## 🚀 Deployment Options

### **1. Docker Deployment (Recommended for Cloud)**

```bash
# Build Docker image
docker build -t rdk-testing-dashboard:latest .

# Run container
docker-compose up -d

# Access at http://localhost:5000
```

**Features:**
- ✅ Python 3.11 virtual environment
- ✅ Tesseract OCR pre-installed
- ✅ Gunicorn with 4 workers
- ✅ Volume mounts for persistence
- ✅ Health check endpoint
- ✅ Auto-restart on failure

### **2. Raspberry Pi Service (Recommended for Lab)**

```bash
# Install as systemd service
sudo ./install_service.sh

# Start service
sudo systemctl start rdk-testing.service

# Check status
sudo systemctl status rdk-testing.service
```

**Features:**
- ✅ 8 Gunicorn workers
- ✅ Auto-start on boot
- ✅ Crash recovery with restart
- ✅ USB stick integration
- ✅ Local network access

### **3. Development Mode**

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask development server
python app.py
```

---

## 🌐 Network Access

### **Local Network**
- **URL**: `http://<raspberry-pi-ip>:5000`
- **DNS**: `lrqa-testing-tool.local` (if dnsmasq configured)
- **Port**: 5000 (Flask default)

### **Cloud Deployment**
- **URL**: `http://<cloud-server-ip>:5000` or custom domain
- **Reverse Proxy**: Nginx recommended
- **HTTPS**: SSL certificate setup (optional)

---

## 📧 Email Configuration

### **Gmail SMTP** (Default)
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=cperdkemiddleware@gmail.com
SENDER_PASSWORD=<app-password>
```

### **Comcast Mail Relay** (Alternative)
```bash
SMTP_HOST=mailrelay.comcast.com
SMTP_PORT=25
SENDER_EMAIL=your_email@comcast.com
SENDER_PASSWORD=  # Empty for internal relay
```

**Email Features:**
- ✅ Test completion notifications
- ✅ Password reset verification codes
- ✅ Pass/fail result summaries
- ✅ Auto-disable if not configured

---

## 🔧 Configuration Management

All hardcoded values externalized to config files:

| Config File | Purpose | Key Settings |
|-------------|---------|--------------|
| `config_commands.py` | SSH commands | Reboot, status, power commands |
| `config_ir_blaster.py` | IR blaster | iTach IP, port, IR codes |
| `config_timing.py` | Timing | Boot time, retries, timeouts |
| `config_log_patterns.py` | Log patterns | HOME screen, errors, crashes |
| `config_screenshot.py` | Screenshots | Paths, naming conventions |
| `config_eta.py` | ETA calculation | Method durations |
| `config_ai_vision.py` | OCR | Tesseract settings |
| `config_screen_validation.py` | Validation | Reference images, thresholds |
| `config_deployment.py` | Deployment | Version info, USB paths |

**Benefits:**
- No hardcoded values in business logic
- Easy configuration changes without code edits
- Consistent settings across application
- Simple environment-specific overrides

---

## 🛡️ Auto-Recovery System

### **How It Works**

1. **Checkpointing (Every 30s during execution)**
   - Saves execution context to `app_state.json`
   - Saves binary snapshot to `checkpoint.pkl`
   - Creates `.crash_marker` file

2. **Crash Detection (On restart)**
   - Checks for `.crash_marker` presence
   - Loads `app_state.json` or `checkpoint.pkl`
   - Restores execution state

3. **Recovery Actions**
   - Re-queues pending jobs
   - Restores device locks
   - Continues from last iteration
   - Logs recovery details

### **What Gets Restored**
- ✅ Current device IP
- ✅ Test method in progress
- ✅ Iteration number (resumes from last checkpoint)
- ✅ Pending job queue
- ✅ Session folder paths
- ✅ User inputs (IR keys, voice text)

### **Failure Scenarios Handled**
- Application crash
- Power loss (Raspberry Pi)
- SSH connection timeout
- Device reboot during test
- Service restart (systemd)

---

## 📚 Key Documentation Files

| Document | Description |
|----------|-------------|
| `README.md` | Main documentation with feature overview |
| `INSTALLATION_GUIDE.md` | Step-by-step setup instructions |
| `DOCKER_BUILD_GUIDE.md` | Docker containerization guide |
| `EMAIL_SETUP_GUIDE.md` | Email service configuration |
| `DEVICE_LOGS_ORGANIZATION.md` | Log folder structure explanation |
| `USB_FOLDER_STRUCTURE.md` | USB output organization |
| `MVC_RECOVERY_COMPLETE.md` | Architecture & recovery details |
| `FEATURES_IMPLEMENTED_NOV20.md` | Feature implementation summary |
| `COMCAST_EMAIL_CONFIG.md` | Comcast mail relay setup |
| `EMAIL_TEST_RESULTS.md` | Email testing documentation |
| `AI_VISION_SETUP.md` | OCR and screen validation setup |
| `SCREENSHOT_GUIDE.md` | Screenshot capture documentation |
| `XUMO_ACTIVATION_SETUP.md` | Xumo activation feature guide |
| `PASSWORD_RESET_GUIDE.md` | Password reset workflow |
| `ADMIN_PERMISSIONS_GUIDE.md` | Admin role documentation |
| `CLOUD_DEPLOYMENT_GUIDE.md` | Cloud deployment instructions |

---

## 💡 Key Highlights

### **1. Production-Ready**
- ✅ MVC architecture
- ✅ Gunicorn WSGI server
- ✅ Auto-recovery from crashes
- ✅ Systemd service integration
- ✅ Docker containerization

### **2. Scalable**
- ✅ Device-specific job queues
- ✅ Concurrent device testing
- ✅ Multi-worker support (4-8 workers)
- ✅ JSON-based persistence (no database needed)

### **3. User-Friendly**
- ✅ Bootstrap 5 responsive UI
- ✅ Real-time log streaming
- ✅ Intuitive dashboard
- ✅ Mobile-friendly design
- ✅ Saved test sequences

### **4. Reliable**
- ✅ Crash recovery
- ✅ State persistence
- ✅ Device lock management
- ✅ SSH connection retries
- ✅ Error handling at every layer

### **5. Traceable**
- ✅ Per-iteration logs
- ✅ Device system logs capture
- ✅ Screenshots before/after
- ✅ HTML reports
- ✅ USB session folders
- ✅ Email notifications

### **6. Extensible**
- ✅ Config-driven design
- ✅ Modular method files
- ✅ Clear separation of concerns
- ✅ Easy to add new test methods
- ✅ Plugin-style architecture

### **7. Security-Conscious**
- ✅ Password hashing
- ✅ Session management
- ✅ Admin role enforcement
- ✅ CSRF protection
- ✅ Email-based password reset

### **8. Well-Documented**
- ✅ 20+ documentation files
- ✅ Inline code comments
- ✅ Docstrings on all functions
- ✅ Architecture diagrams
- ✅ Setup guides
- ✅ Feature summaries

---

## 🎓 Use Cases

### **QA Testing Lab**
- Execute 100+ reboot iterations overnight
- Validate firmware updates across device fleet
- Automated regression testing
- Screen validation after updates

### **Device Certification**
- Deep sleep compliance testing
- IR command responsiveness
- Boot time performance benchmarking
- Power state verification

### **Development Testing**
- Quick device control during development
- SSH session monitoring
- Log capture for debugging
- Screenshot comparison

### **Production Monitoring**
- Continuous device health checks
- Automated recovery testing
- Performance baseline tracking
- Email alerting on failures

---

## 🚦 Getting Started

### **Quick Start (5 Minutes)**

1. **Clone Repository**
   ```bash
   git clone https://github.com/viswaPatneedi/lrqa-middleware-testing-dashboard.git
   cd lrqa-middleware-testing-dashboard
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**
   ```bash
   python app.py
   ```

4. **Access Dashboard**
   ```
   http://localhost:5000
   ```

5. **Add Device**
   - Go to Device Management section
   - Fill in device details (IP, port, credentials)
   - Click "Add Device"

6. **Run Test**
   - Select device
   - Choose method (e.g., Reboot)
   - Set iterations
   - Click "Execute Method"

---

## 📞 Support & Maintenance

### **Common Tasks**

**Add New Test Method:**
1. Create `method_<name>.py` with method logic
2. Add route in `app.py`
3. Update UI in `templates/index.html`
4. Add ETA calculation in `config_eta.py`

**Update Configuration:**
- Edit relevant `config_*.py` file
- No code changes needed
- Restart application

**View Logs:**
- Iteration logs: `iteration_logs/`
- Device logs: `device_logs/<device_ip>/`
- Application logs: `flask.log`, `gunicorn.log`

**Backup Data:**
- Copy JSON files: `devices.json`, `jobs.json`, `users.json`
- Copy `iteration_logs/` and `device_logs/`
- Use `backup_to_usb.sh` for automated backups

**Restore from Crash:**
- Application auto-recovers on restart
- Check `app_state.json` for recovery state
- Review recovery logs in console output

---

## 🏆 Project Achievements

- ✅ **1600+ lines** refactored from monolithic app.py to MVC structure
- ✅ **10+ test methods** implemented with full automation
- ✅ **30-second checkpointing** for crash recovery
- ✅ **3-day test result retention** with automatic cleanup
- ✅ **Device-specific log organization** for traceability
- ✅ **Email notification system** with Gmail/Comcast support
- ✅ **Docker containerization** for cloud deployment
- ✅ **USB session folders** for organized output
- ✅ **AI-powered screen validation** with Tesseract OCR
- ✅ **20+ documentation files** for comprehensive guidance

---

## 📅 Version History

- **November 2025**: Initial MVC refactoring, auto-recovery, saved sequences
- **December 2025**: Screen validation, Xumo activation, email notifications
- **January 2026**: Device-specific logs, Docker deployment, Gmail/Comcast email config

---

## 🔮 Future Enhancements

- [ ] WebSocket log streaming (upgrade from SSE)
- [ ] Database backend (PostgreSQL/MySQL) for scalability
- [ ] RESTful API with Swagger documentation
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Multi-user collaboration features
- [ ] CI/CD pipeline integration
- [ ] Kubernetes deployment manifests
- [ ] Video recording during tests
- [ ] AI-powered anomaly detection

---

## 📝 License & Contact

**Project Owner:** Viswa Chaithanya Patneedi  
**Repository:** [lrqa-middleware-testing-dashboard](https://github.com/viswaPatneedi/lrqa-middleware-testing-dashboard)  
**Email:** viswachaithanya_patneedi@comcast.com  

---

**🎉 Thank you for using RDK Testing Dashboard!**

*This application is designed to make device testing efficient, reliable, and traceable. For questions, issues, or feature requests, please refer to the documentation or open a GitHub issue.*

---

**Last Updated:** January 14, 2026
