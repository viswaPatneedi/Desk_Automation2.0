# Mac Docker Setup - Complete Documentation Index

Welcome! This directory contains comprehensive guides for building and running the RDK Testing Dashboard Docker image on your Mac.

---

## Quick Navigation

### 🚀 **I want to get running NOW!**
→ Read: [DOCKER_MAC_QUICKSTART.md](DOCKER_MAC_QUICKSTART.md) (5 min read)

### 📖 **I need step-by-step detailed instructions**
→ Read: [DOCKER_MAC_BUILD_GUIDE.md](DOCKER_MAC_BUILD_GUIDE.md) (Complete guide)

### 🔧 **I'm having problems**
→ Read: [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md) (Solutions for common issues)

### 🤖 **I prefer scripted automation**
→ Use: `./docker-mac-setup.sh` (Helper script with commands)

---

## Files Overview

| File | Purpose | Read Time | Best For |
|------|---------|-----------|----------|
| **DOCKER_MAC_QUICKSTART.md** | 5-minute quick start | 5 min | Fast setup, experienced Docker users |
| **DOCKER_MAC_BUILD_GUIDE.md** | Complete step-by-step guide | 20-30 min | First-time Docker users, detailed walkthrough |
| **DOCKER_MAC_TROUBLESHOOTING.md** | Problem diagnosis & solutions | Reference | Debugging issues, errors, performance problems |
| **docker-mac-setup.sh** | Automated helper script | N/A | Running Docker commands easily |
| **DOCKER_MAC_SETUP_INDEX.md** | This file | 5 min | Navigation & overview |

---

## The 5-Step Quick Start

If you already know Docker basics, here's the fastest path:

```bash
# Step 1: Install Docker Desktop
# Download: https://www.docker.com/products/docker-desktop

# Step 2: Navigate to project
cd /path/to/Enhancement

# Step 3: Setup environment
cp .env.example .env
# Edit .env with SMTP credentials

# Step 4: Build image (15 minutes first time)
docker-compose build

# Step 5: Start container
docker-compose up -d

# Access: http://localhost:5000
```

---

## Choosing the Right Guide

### Scenario 1: "I'm brand new to Docker"
1. Read: [DOCKER_MAC_BUILD_GUIDE.md](DOCKER_MAC_BUILD_GUIDE.md) - System Requirements section
2. Follow: All step-by-step instructions
3. Refer: DOCKER_MAC_TROUBLESHOOTING.md if issues arise

### Scenario 2: "I know Docker but new to this project"
1. Skim: [DOCKER_MAC_QUICKSTART.md](DOCKER_MAC_QUICKSTART.md)
2. Use: `docker-compose build && docker-compose up -d`
3. Access: http://localhost:5000

### Scenario 3: "I have a specific problem"
1. Go: [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md)
2. Find: Section matching your issue
3. Follow: Provided solutions

### Scenario 4: "I want to automate everything"
```bash
chmod +x docker-mac-setup.sh
./docker-mac-setup.sh --help
```

---

## System Requirements

**Minimum:**
- macOS 11 (Big Sur) or later
- 4GB RAM (8GB recommended)
- 20GB free disk space
- Docker Desktop 4.0+
- Intel or Apple Silicon Mac

**Recommended:**
- macOS 12 or later
- 8GB+ RAM
- 25GB+ free disk space
- Docker Desktop latest version
- Apple Silicon preferably (faster)

---

## Installation Path Flowchart

```
Start
  ↓
Is Docker installed?
  ├─ No → Install Docker Desktop
  └─ Yes ↓
      Is App Directory Ready?
        ├─ No → Clone/Download project
        └─ Yes ↓
            Create .env file
            ↓
            Run: docker-compose build
            ↓
            Run: docker-compose up -d
            ↓
            Open: http://localhost:5000
            ↓
            Success! ✓
```

---

## Key Resources

### Documentation Files
- **[DOCKER_MAC_BUILD_GUIDE.md](DOCKER_MAC_BUILD_GUIDE.md)** - Comprehensive build & deployment
- **[DOCKER_MAC_QUICKSTART.md](DOCKER_MAC_QUICKSTART.md)** - Fast 5-minute start
- **[DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md)** - Issue diagnosis
- **[Dockerfile](Dockerfile)** - Image definition
- **[docker-compose.yml](docker-compose.yml)** - Container configuration

### Configuration Files
- **[.env.example](.env.example)** - Environment template (copy to .env)
- **[requirements.txt](requirements.txt)** - Python dependencies
- **[config_*.py](config_*.py)** - Application settings

### Helper Scripts
- **[docker-mac-setup.sh](docker-mac-setup.sh)** - Build/run automation

---

## Common Commands

```bash
# Build image
docker-compose build

# Start container
docker-compose up -d

# Stop container
docker-compose down

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Open shell
docker-compose exec web /bin/bash

# Health check
curl http://localhost:5000/health

# View container stats
docker stats rdk-testing-dashboard
```

**Using the helper script:**
```bash
./docker-mac-setup.sh build      # Build image
./docker-mac-setup.sh run        # Start container
./docker-mac-setup.sh stop       # Stop container
./docker-mac-setup.sh logs       # View logs
./docker-mac-setup.sh status     # Check status
./docker-mac-setup.sh shell      # Open shell
./docker-mac-setup.sh health     # Health check
./docker-mac-setup.sh clean      # Clean up
```

---

## Environment Setup (.env)

### Gmail Configuration (Recommended)
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-char-app-password
# Get app password: https://myaccount.google.com/apppasswords
```

### Comcast Configuration
```env
SMTP_HOST=mailrelay.comcast.com
SMTP_PORT=587
SENDER_EMAIL=your-email@comcast.net
SENDER_PASSWORD=your-password
```

---

## What Gets Installed

- **Python**: 3.11-slim image
- **Framework**: Flask 3.0.0
- **Server**: Gunicorn (production WSGI)
- **Database**: JSON file-based
- **OCR**: Tesseract OCR
- **Dependencies**: All from requirements.txt
- **Port**: 5000 (HTTP)

---

## Data Persistence

The following are automatically persisted across container restarts:

```
devices.json              → Device configurations
jobs.json                 → Job history
device_job_queue.json     → Queue state
device_locks.json         → Device locks
saved_sequences.json      → Saved sequences
app_state.json            → Application state
iteration_logs/           → Execution logs
screenshots/              → Screen captures
```

---

## Performance Tips

1. **Increase Docker Memory**
   - Docker menu → Preferences → Resources → Set to 6-8GB

2. **Increase Docker CPU**
   - Docker menu → Preferences → Resources → Set to 4+ cores

3. **Use Apple Silicon Image** (if on M1/M2/M3/M4)
   - Automatically detected by Docker

4. **Clean Up Regularly**
   ```bash
   docker system prune -a
   ```

5. **Monitor Resource Usage**
   ```bash
   docker stats
   ```

---

## Troubleshooting Quick Links

| Issue | Link |
|-------|------|
| Port already in use | [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md#problem-port-5000-already-in-use) |
| Build takes too long | [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md#problem-very-slow-build-45-minutes) |
| Can't access localhost:5000 | [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md#problem-cant-access-httplocalhost5000) |
| Out of disk space | [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md#problem-out-of-disk-space) |
| SMTP not working | [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md#problem-smtp-connection-failed) |
| Docker won't start | [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md#problem-docker-daemon-wont-start) |

---

## Next Steps After Installation

1. ✅ **Verify Application** - Access http://localhost:5000
2. ✅ **Configure Devices** - Add your target devices
3. ✅ **Test SSH** - Verify device connectivity
4. ✅ **Setup Email** - Configure SMTP credentials
5. ✅ **Review Logs** - Check iteration_logs/ for execution history
6. ✅ **Backup Data** - Regular backups of JSON files

---

## Getting Help

### Still confused?
1. Re-read the [DOCKER_MAC_BUILD_GUIDE.md](DOCKER_MAC_BUILD_GUIDE.md) slowly, section by section
2. Check [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md) for your specific issue
3. Review the [Dockerfile](Dockerfile) to understand what's being installed

### Having errors?
1. Copy error message
2. Search in [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md)
3. Follow the provided solution
4. Run diagnostic commands from troubleshooting guide

### Docker knowledge gaps?
- Docker Handbook: https://www.docker.com/blog/
- Docker Docs: https://docs.docker.com/
- Play with Docker: https://www.docker.com/play-with-docker/

---

## Support Resources

- **Docker Issues**: https://github.com/docker/issues
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Project Repository**: Check GitHub for issues & discussions
- **Mac Support**: https://support.apple.com/en-us/

---

## Pro Tips

- Use `docker-compose exec web bash` to run commands inside container
- Check `docker system df` to see disk usage by images/containers/volumes
- Run `docker logs -f` to tail logs in real-time
- Use `docker-compose config` to validate your configuration
- Store sensitive data in .env and never commit to git

---

## Architecture Overview

```
Your Mac
├── Docker Desktop (virtualization)
│   ├── Docker Engine (container runtime)
│   └── Linux VM (hidden)
├── Container (rdk-testing-dashboard)
│   ├── Python 3.11 runtime
│   ├── Flask application
│   ├── Gunicorn server
│   ├── Tesseract OCR
│   └── All dependencies
└── Mounted Volumes
    ├── devices.json
    ├── iteration_logs/
    ├── screenshots/
    └── ... (data persists)
```

---

## Document Versions

| Guide | Version | Last Updated | Status |
|-------|---------|--------------|--------|
| DOCKER_MAC_BUILD_GUIDE.md | 1.0 | March 25, 2026 | ✓ Current |
| DOCKER_MAC_QUICKSTART.md | 1.0 | March 25, 2026 | ✓ Current |
| DOCKER_MAC_TROUBLESHOOTING.md | 1.0 | March 25, 2026 | ✓ Current |
| docker-mac-setup.sh | 1.0 | March 25, 2026 | ✓ Current |

---

## Start Here!

👉 **Choose one:**

- **New to Docker?** → [DOCKER_MAC_BUILD_GUIDE.md](DOCKER_MAC_BUILD_GUIDE.md)
- **Experienced user?** → [DOCKER_MAC_QUICKSTART.md](DOCKER_MAC_QUICKSTART.md)
- **Having problems?** → [DOCKER_MAC_TROUBLESHOOTING.md](DOCKER_MAC_TROUBLESHOOTING.md)
- **Want automation?** → `./docker-mac-setup.sh --help`

---

Good luck! 🚀
