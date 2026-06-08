# Docker Quick Start Guide - Windows & Mac

Get your RDK Testing Dashboard running in Docker in 5 minutes!

## Prerequisites Checklist

- [ ] **Windows Users**: Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- [ ] **Mac Users**: Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
- [ ] Docker is running and started
- [ ] You have this project cloned/downloaded
- [ ] You have at least 10GB free disk space

---

## Quick Start (Choose Your Platform)

### 🪟 Windows (PowerShell)

```powershell
# 1. Open PowerShell in the project directory
cd C:\path\to\Enhancement

# 2. Copy environment configuration
Copy-Item .env.example .env
# Edit .env with your SMTP credentials (use Notepad or VS Code)

# 3. Build and run in one command
.\build-and-run.ps1 -Action rebuild

# 4. Access the app
# Open browser to: http://localhost:5000

# 5. View logs
.\build-and-run.ps1 -Action logs

# 6. Stop when done
.\build-and-run.ps1 -Action stop
```

### 🍎 Mac/Linux (Terminal)

```bash
# 1. Navigate to project directory
cd /path/to/Enhancement

# 2. Copy environment configuration
cp .env.example .env
# Edit .env with your SMTP credentials (nano, vi, or VS Code)

# 3. Make script executable
chmod +x build-and-run.sh

# 4. Build and run in one command
./build-and-run.sh rebuild

# 5. Access the app
# Open browser to: http://localhost:5000

# 6. View logs
./build-and-run.sh logs

# 7. Stop when done
./build-and-run.sh stop
```

---

## Configuration (.env file setup)

Edit the `.env` file with your email settings:

```env
# Gmail (Recommended)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Or use Comcast Mail Relay (if available)
# SMTP_HOST=mailrelay.comcast.com
# SMTP_PORT=25
```

**Getting Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Generate app password for "Mail"
3. Copy and paste into `.env` as `SENDER_PASSWORD`

---

## First-Time Build

**Estimated time: 10-15 minutes**

The first build takes longer because it:
- Downloads Python 3.11 image (~150 MB)
- Installs system dependencies
- Installs Python packages (~1-2 GB)

Subsequent builds are much faster due to Docker caching.

---

## Command Reference

### Windows (PowerShell)

| Command | What it does |
|---------|------------|
| `.\build-and-run.ps1 -Action build` | Build the image only |
| `.\build-and-run.ps1 -Action run` | Start the container |
| `.\build-and-run.ps1 -Action rebuild` | Build and start (recommended first time) |
| `.\build-and-run.ps1 -Action logs` | Stream live logs |
| `.\build-and-run.ps1 -Action bash` | Open shell inside container |
| `.\build-and-run.ps1 -Action status` | Show container status |
| `.\build-and-run.ps1 -Action stop` | Stop the container |
| `.\build-and-run.ps1 -Action clean` | Remove all (containers, images) |

### Mac/Linux (Terminal)

| Command | What it does |
|---------|------------|
| `./build-and-run.sh build` | Build the image only |
| `./build-and-run.sh run` | Start the container |
| `./build-and-run.sh rebuild` | Build and start (recommended first time) |
| `./build-and-run.sh logs` | Stream live logs |
| `./build-and-run.sh bash` | Open shell inside container |
| `./build-and-run.sh status` | Show container status |
| `./build-and-run.sh stop` | Stop the container |
| `./build-and-run.sh clean` | Remove all (containers, images) |

---

## Accessing the Application

Once running, open your browser to:

| What | URL |
|-----|-----|
| Main dashboard | http://localhost:5000 |
| Admin panel | http://localhost:5000/admin |
| API health check | http://localhost:5000/health |
| Log streaming | http://localhost:5000/logs/stream |

---

## Troubleshooting

### "Docker command not found"
- Ensure Docker Desktop is installed and running
- Windows: Restart PowerShell after installing Docker

### "Port 5000 already in use"
```powershell
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :5000
kill -9 <PID>
```

### "Out of memory" error
Windows/Mac: Docker Desktop Settings → Resources → Increase Memory to 6-8 GB

### Container keeps restarting
```powershell
# Check logs for errors
docker-compose logs

# Fix: May need to rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### "Cannot connect to SSH devices"
1. Verify devices.json has valid IP addresses
2. Ensure SSH credentials are correct
3. Test connectivity from host machine first
4. May need to configure jump host or SSH tunneling

---

## Using Docker Compose Directly (Advanced)

If you prefer manual Docker commands instead of scripts:

```bash
# Navigate to project directory
cd /path/to/Enhancement

# Build
docker-compose build

# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Execute commands inside container
docker-compose exec web bash

# Stop
docker-compose down
```

---

## Cross-Platform Configuration Files

This project includes optimized files for different platforms:

- **docker-compose.yml** - Standard configuration
- **docker-compose.cross-platform.yml** - Optimized for Windows/Mac with better volume handling
- **build-and-run.ps1** - Windows PowerShell automation script
- **build-and-run.sh** - Mac/Linux bash automation script

---

## What Gets Mounted?

Container persistence (your data survives after restart):

| Host File | Container Path | Purpose |
|-----------|---|---------|
| devices.json | /app/devices.json | Device configurations |
| jobs.json | /app/jobs.json | Job history |
| device_job_queue.json | /app/device_job_queue.json | Queue state |
| iteration_logs/ | /app/iteration_logs | Execution logs |
| screenshots/ | /app/screenshots | Device screenshots |

---

## Performance Tips

### Windows
- Use WSL 2 backend (faster than Hyper-V)
- Allocate 6-8GB RAM to Docker
- Store project on C:\ drive (not network share)

### Mac
- For Apple Silicon: Use native Docker Desktop (not Rosetta)
- Allocate 6-8GB RAM to Docker
- Use wired network if possible for SSH connectivity

### All Platforms
- Keep Docker Desktop updated
- Clean unused images: `docker system prune -a`
- Don't store huge files inside container

---

## Next Steps

### 1. Add Your Devices
After container starts, add devices via the web UI:
- http://localhost:5000 → Devices → Add Device
- Or edit devices.json directly

### 2. Test SSH Connectivity
- Dashboard → Devices → Click device → Test Connection
- Fix any credentials or network issues

### 3. Run Your First Test
- Dashboard → Jobs → Create New Job
- Select device and test method
- Monitor execution in live logs

### 4. Deploy to Cloud (Optional)
See [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md) to deploy to:
- AWS ECS/ECR
- Azure Container Registry
- Google Cloud
- Docker Hub

---

## Common Workflows

### Development: Quick changes
```bash
# Edit code locally
# Changes auto-reload (Flask development mode)
# View live logs
docker-compose logs -f
```

### Backup your data
```bash
# All persistent data is in local files/volumes
# Just backup these directories:
cp -r devices.json jobs.json iteration_logs/* /backup/location/
```

### Rebuild fresh
```bash
docker-compose down -v              # Remove everything
docker-compose build --no-cache     # Fresh build
docker-compose up -d                # Start fresh
```

---

## Resources

- **Detailed Guide**: [DOCKER_WINDOWS_MAC_GUIDE.md](DOCKER_WINDOWS_MAC_GUIDE.md)
- **Docker Docs**: https://docs.docker.com/
- **Docker Compose Reference**: https://docs.docker.com/compose/compose-file/
- **Docker for Desktop**: https://www.docker.com/products/docker-desktop

---

## Need Help?

1. **Check logs**: `docker-compose logs` or `./build-and-run.sh logs`
2. **Check Docker status**: `docker ps` or `docker info`
3. **Restart everything**: `docker-compose down && docker-compose up -d`
4. **Full reset**: `./build-and-run.ps1 -Action clean` then rebuild

Good luck! 🚀
