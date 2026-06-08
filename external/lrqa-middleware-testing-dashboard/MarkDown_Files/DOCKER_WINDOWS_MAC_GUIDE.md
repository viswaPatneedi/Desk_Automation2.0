# Docker Setup Guide for Windows & Mac

This guide provides step-by-step instructions to build and run the RDK Testing Dashboard Docker image on Windows and Mac machines.

## Prerequisites

### System Requirements
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 15GB free space (for image + containers)
- **Processor**: Multi-core processor recommended

### Required Software

#### **Windows**
1. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop
   - WSL 2 backend recommended (enabled by default in modern versions)
   - Version: 4.0 or higher

2. **Windows Terminal** (optional but recommended)
   - Download from Microsoft Store or: https://github.com/microsoft/terminal

3. **Git Bash** (optional, for Unix-like commands)
   - Download: https://git-scm.com/download/win

#### **Mac**
1. **Docker Desktop for Mac**
   - Download: https://www.docker.com/products/docker-desktop
   - Version: 4.0 or higher
   - Supports both Intel and Apple Silicon (M1/M2/M3)

2. **Terminal** (built-in or iTerm2)
   - iTerm2 download: https://iterm2.com/

---

## Step 1: Install Docker Desktop

### Windows Installation
1. Download Docker Desktop for Windows
2. Run the installer
3. Follow the installation wizard
4. Restart your computer
5. Open PowerShell and verify installation:
   ```powershell
   docker --version
   docker run hello-world
   ```

### Mac Installation
1. Download Docker Desktop for Mac (choose Intel or Apple Silicon)
2. Drag Docker.app to Applications folder
3. Open Applications and launch Docker
4. Grant permissions when prompted
5. Open Terminal and verify installation:
   ```bash
   docker --version
   docker run hello-world
   ```

---

## Step 2: Prepare the Application

### Clone or Download Repository
```bash
# Clone the repository (if using Git)
git clone <repository-url>
cd Enhancement

# Or if you already have the files, navigate to the directory
cd /path/to/Enhancement
```

### Create Environment File
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings (SMTP credentials, etc.)
# - On Windows: Open .env with Notepad or VS Code
# - On Mac: Use nano, vim, or open with TextEdit
```

**Key Environment Variables to Configure:**
```
SECRET_KEY=your-secure-key-here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

---

## Step 3: Build the Docker Image

### Option A: Using Docker Compose (Easiest - Recommended)

#### Windows (PowerShell)
```powershell
# Navigate to the Enhancement directory
cd C:\path\to\Enhancement

# Build the image
docker-compose build

# Or force rebuild
docker-compose build --no-cache
```

#### Mac (Terminal)
```bash
# Navigate to the Enhancement directory
cd /path/to/Enhancement

# Build the image
docker-compose build

# Or force rebuild
docker-compose build --no-cache
```

### Option B: Using Docker CLI Directly

#### Windows (PowerShell)
```powershell
cd C:\path\to\Enhancement
docker build -t rdk-testing-dashboard:latest .
```

#### Mac (Terminal)
```bash
cd /path/to/Enhancement
docker build -t rdk-testing-dashboard:latest .
```

**Build Process Details:**
- Downloads Python 3.11 slim image (~150 MB)
- Installs system dependencies (Tesseract OCR, etc.)
- Installs Python packages from requirements.txt (~1-2 GB)
- Copies application code
- Total image size: ~6.5 GB
- Estimated build time: 10-15 minutes (first build)

---

## Step 4: Run the Docker Container

### Option A: Using Docker Compose (Easiest - Recommended)

#### Windows (PowerShell)
```powershell
cd C:\path\to\Enhancement

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

#### Mac (Terminal)
```bash
cd /path/to/Enhancement

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### Option B: Using Docker CLI Directly

#### Windows (PowerShell)
```powershell
docker run -d `
  --name rdk-testing `
  -p 5000:5000 `
  -e SENDER_PASSWORD="your-password" `
  -v "$(Get-Location)\devices.json:/app/devices.json" `
  -v "$(Get-Location)\iteration_logs:/app/iteration_logs" `
  -v "$(Get-Location)\screenshots:/app/screenshots" `
  --restart unless-stopped `
  rdk-testing-dashboard:latest
```

#### Mac (Terminal)
```bash
docker run -d \
  --name rdk-testing \
  -p 5000:5000 \
  -e SENDER_PASSWORD="your-password" \
  -v "$(pwd)/devices.json:/app/devices.json" \
  -v "$(pwd)/iteration_logs:/app/iteration_logs" \
  -v "$(pwd)/screenshots:/app/screenshots" \
  --restart unless-stopped \
  rdk-testing-dashboard:latest
```

---

## Step 5: Access the Application

### Open in Browser
- **URL**: http://localhost:5000
- **Admin Panel**: http://localhost:5000/admin
- **Logs Endpoint**: http://localhost:5000/logs/stream

### Verify Container is Running

#### Windows (PowerShell)
```powershell
# List running containers
docker ps

# View specific container logs
docker logs rdk-testing

# Check container stats
docker stats rdk-testing
```

#### Mac (Terminal)
```bash
# List running containers
docker ps

# View specific container logs
docker logs rdk-testing

# Check container stats
docker stats rdk-testing
```

---

## Common Issues & Troubleshooting

### Issue: Docker not starting on Windows
**Solution:**
1. Ensure WSL 2 is installed: https://docs.microsoft.com/en-us/windows/wsl/install
2. Open PowerShell as Administrator
3. Try: `wsl --update`
4. Restart Docker Desktop

### Issue: Port 5000 already in use
**Solution:**
```powershell
# Windows: Find process using port 5000
netstat -ano | findstr :5000

# Mac: Find process using port 5000
lsof -i :5000

# Kill the process (Windows)
taskkill /PID <PID> /F

# Kill the process (Mac)
kill -9 <PID>

# Or use different port in docker-compose.yml
# Change "5000:5000" to "8000:5000"
```

### Issue: Out of memory or system resources
**Solution:**
1. Windows: Increase Docker Desktop memory
   - Settings → Resources → Memory (set to 6-8 GB)
2. Mac: Increase Docker Desktop memory
   - Preferences → Resources → Memory (set to 6-8 GB)
3. Restart Docker Desktop

### Issue: Volume mount permission denied
**Solution:**
- **Windows**: Ensure the directory is shared in Docker Desktop Settings
- **Mac**: Grant full disk access to Docker in System Preferences

### Issue: Application shows "Cannot connect to SSH"
**Solution:**
1. Verify devices.json contains valid device configurations
2. Ensure SSH credentials are correct
3. Test SSH connectivity from host machine
4. Check network connectivity from container:
   ```bash
   docker exec -it rdk-testing bash
   # Inside container: ping <device-ip>
   ```

---

## Useful Docker Commands

### Container Management
```bash
# List all containers
docker ps -a

# View running containers
docker ps

# Start a stopped container
docker start rdk-testing

# Stop a running container
docker stop rdk-testing

# Remove a container
docker rm rdk-testing

# View container logs
docker logs rdk-testing

# Stream container logs
docker logs -f rdk-testing

# Execute command in container
docker exec -it rdk-testing bash

# View container resource usage
docker stats rdk-testing
```

### Image Management
```bash
# List all images
docker images

# View image details
docker inspect rdk-testing-dashboard:latest

# Tag image
docker tag rdk-testing-dashboard:latest rdk-testing:v1.0

# Remove image
docker rmi rdk-testing-dashboard:latest

# Push to registry (requires Docker Hub account)
docker tag rdk-testing-dashboard:latest <your-username>/rdk-testing-dashboard:latest
docker push <your-username>/rdk-testing-dashboard:latest
```

### Docker Compose Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild services
docker-compose build

# Remove all containers, networks
docker-compose down -v

# Execute command in service
docker-compose exec web bash
```

---

## Performance Tips

### Windows
1. Use WSL 2 backend (faster than Hyper-V)
2. Allocate sufficient resources in Docker Desktop settings
3. Store project on local drive (not network share)
4. Use `.dockerignore` to exclude unnecessary files

### Mac
1. For Apple Silicon (M1/M2/M3): Ensure Docker Desktop is native ARM version
2. Use named volumes instead of bind mounts when possible
3. Disable VPN if experiencing slow performance
4. Monitor memory usage in Docker Dashboard

### General
1. Use `--no-cache` flag when rebuilding with fresh dependencies
2. Keep your local image up-to-date with `docker-compose build`
3. Regularly clean unused images and containers:
   ```bash
   docker system prune -a
   ```

---

## Next Steps

### Deploy to Cloud
- **AWS**: See [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)
- **Azure**: Configure ACR (Azure Container Registry)
- **Google Cloud**: Configure GCR (Google Container Registry)

### Monitor and Maintain
1. Set up log rotation for iteration_logs
2. Configure automated backups for devices.json
3. Monitor container resource usage
4. Plan for auto-restart policies

### Security
1. Change `SECRET_KEY` in `.env` file
2. Use strong SMTP passwords
3. Regularly update base image: `docker-compose build --no-cache`
4. Don't commit `.env` file to version control

---

## Additional Resources

- Docker Official Documentation: https://docs.docker.com/
- Docker Desktop Installation: https://www.docker.com/products/docker-desktop
- Docker Compose Documentation: https://docs.docker.com/compose/
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/

---

### Support

If you encounter issues not mentioned here:
1. Check Docker Desktop logs
2. Review application logs: `docker-compose logs`
3. Check Docker system status: `docker system info`
4. Consult official Docker documentation
