# RDK Device Manager

Flask-based web application for managing and controlling RDK devices via SSH with automated testing, real-time logging, and AI-powered screen validation.

## Repository Information

**Project:** RDK Device Manager  
**Type:** Private Repository  
**Created:** December 15, 2025  
**License:** Proprietary - All Rights Reserved

## Features

- SSH-based device control and testing
- Real-time log streaming with Server-Sent Events (SSE)
- Screenshot capture and comparison
- AI-powered screen validation using OCR
- Test sequence automation
- Job queue management with priority scheduling
- User authentication and role-based permissions
- IR blaster integration for deep sleep wake-up
- Multi-device parallel testing
- Historical result tracking and reporting
- Email notifications (optional)

## Technology Stack

- **Backend:** Flask 3.0.0, Python 3.7+
- **SSH:** Paramiko 3.4.0
- **Authentication:** Flask-Login, Flask-Bcrypt
- **Image Processing:** Pillow, pytesseract
- **Production Server:** Gunicorn with gevent workers
- **Frontend:** HTML5, JavaScript, Bootstrap CSS

## Quick Start

```bash
# Install dependencies
./install_complete_system.sh

# Activate virtual environment
source venv/bin/activate

# Run development server
python3 app.py

# Access at http://localhost:5000
```

## Project Structure

```
├── app.py                    # Main Flask application
├── controllers/              # Business logic controllers
│   ├── device_controller.py
│   ├── queue_controller.py
│   ├── results_controller.py
│   └── test_controller.py
├── models/                   # Data models
│   ├── device.py
│   ├── job.py
│   ├── user.py
│   └── saved_sequence.py
├── services/                 # Background services
│   ├── log_service.py
│   ├── queue_service.py
│   └── recovery_service.py
├── templates/                # HTML templates
├── static/                   # CSS, JavaScript, images
├── config_*.py              # Configuration modules
├── method_*.py              # Device method implementations
└── requirements.txt         # Python dependencies
```

## Configuration

All configuration is externalized in `config_*.py` files:

- `config_commands.py` - SSH commands for devices
- `config_timing.py` - Timeout and delay settings
- `config_screenshot.py` - Screenshot capture settings
- `config_log_patterns.py` - Log parsing patterns
- `config_ir_blaster.py` - IR blaster configuration
- `config_ai_vision.py` - AI vision settings
- `config_screen_validation.py` - Screen validation rules

## Data Files (Not in Git)

These files contain sensitive data and are excluded:

- `devices.json` - Device registry with SSH credentials
- `users.json` - User accounts and passwords
- `jobs.json` - Job execution history
- `saved_sequences.json` - Test sequences

## Security Notes

⚠️ **IMPORTANT:** This is a private repository. Do not share or make public.

- SSH credentials stored in `devices.json`
- User passwords hashed in `users.json`
- All sensitive data excluded from version control
- Change default passwords after installation

## Installation from Backup

See `README_INSTALLATION.md` for complete setup instructions.

## Production Deployment

```bash
# Using systemd service
sudo bash install_service.sh
sudo systemctl start device-testing

# Using Gunicorn directly
bash run_production.sh
```

## Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in debug mode
python3 app.py
```

## Documentation

- `README_INSTALLATION.md` - Installation guide
- `SCREENSHOT_GUIDE.md` - Screenshot functionality
- `AI_VISION_SETUP.md` - AI screen validation setup
- `QUICK_REFERENCE.md` - Command reference
- `PASSWORD_RESET_GUIDE.md` - Password management

## Support

For internal use only. Contact system administrator for support.

---

**© 2025 - All Rights Reserved**
