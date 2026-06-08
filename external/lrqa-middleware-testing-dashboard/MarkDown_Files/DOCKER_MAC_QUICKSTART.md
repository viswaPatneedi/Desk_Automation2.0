# Mac Docker Quick Start (5 Minutes)

**TL;DR**: Get the Flask app running in Docker on Mac in 5 steps.

---

## Prerequisites (Do Once)

```bash
# 1. Install Docker Desktop for Mac
# Download: https://www.docker.com/products/docker-desktop
# Choose: Apple Silicon (M1/M2/M3) or Intel
# Drag Docker.app to Applications, launch it

# 2. Verify Docker is installed
docker --version
docker run hello-world
```

---

## Build & Run (Quick Path)

### Step 1: Prepare Environment
```bash
cd /path/to/Enhancement
cp .env.example .env  # Or create .env with SMTP credentials
```

### Step 2: Make Script Executable
```bash
chmod +x docker-mac-setup.sh
```

### Step 3: Build Image (First Time Only - ~15 min)
```bash
./docker-mac-setup.sh build
# Or: docker-compose build
```

### Step 4: Start Container
```bash
./docker-mac-setup.sh run
# Or: docker-compose up -d
```

### Step 5: Access Application
```
Open browser → http://localhost:5000
```

---

## Essential Commands

| Action | Command |
|--------|---------|
| **Build Image** | `./docker-mac-setup.sh build` |
| **Start Container** | `./docker-mac-setup.sh run` |
| **Stop Container** | `./docker-mac-setup.sh stop` |
| **View Logs** | `./docker-mac-setup.sh logs` |
| **Check Status** | `./docker-mac-setup.sh status` |
| **Open Shell** | `./docker-mac-setup.sh shell` |
| **Health Check** | `./docker-mac-setup.sh health` |
| **Clean Up** | `./docker-mac-setup.sh clean` |

---

## Troubleshooting

### Container Won't Start
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Restart container
./docker-mac-setup.sh restart
```

### View Error Logs
```bash
./docker-mac-setup.sh logs

# Or direct Docker command
docker-compose logs -f --tail=100
```

### Docker Not Running
```bash
# Make sure Docker Desktop is open
# Applications → Docker.app

# Then verify
docker ps
```

### Out of Disk Space
```bash
docker system prune -a
```

---

## Environment Setup (.env)

**Gmail (Recommended):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-char-app-password
# Get app password from: myaccount.google.com/apppasswords
```

**Comcast:**
```env
SMTP_HOST=mailrelay.comcast.com
SMTP_PORT=587
SENDER_EMAIL=your-email@comcast.net
SENDER_PASSWORD=your-password
```

---

## What's Running

- **Image Name**: `rdk-testing-dashboard:latest`
- **Container Name**: `rdk-testing-dashboard`
- **Port**: `5000`
- **URL**: `http://localhost:5000`
- **Framework**: Flask + Gunicorn
- **Python**: 3.11

---

## Next Steps

- Full Guide: See `DOCKER_MAC_BUILD_GUIDE.md`
- Logs Location**: Mounted at `./iteration_logs/`
- **Data Persists**: Volumes mapped for all JSON data files
- **Screenshots**: Stored in `./screenshots/`

---

## One-Liner Quick Start

```bash
cd /path/to/Enhancement && \
cp .env.example .env && \
docker-compose build && \
docker-compose up -d && \
echo "Open http://localhost:5000"
```

---

Need help? Run: `./docker-mac-setup.sh --help`
