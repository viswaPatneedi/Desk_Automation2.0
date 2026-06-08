# 🚀 RDK-E Middleware Testing Dashboard - Docker Package

## 📦 Overview
This is a complete, ready-to-deploy Docker package for the RDK-E Middleware Testing Dashboard. Everything is organized for seamless deployment to any Raspberry Pi or Linux machine.

## 📁 Folder Structure
```
RDK-Middleware-USB/
├── scripts/               # Automated deployment scripts
│   ├── start-rdk-app.sh          # Start the application
│   ├── stop-rdk-app.sh           # Stop the application
│   ├── restart-rdk-app.sh        # Restart the application
│   └── status-rdk-app.sh         # Check status and logs
├── docker-files/          # Docker configuration
│   ├── Dockerfile.production     # Production Docker image definition
│   ├── docker-compose.rpi.clean.yml  # Docker Compose configuration
│   └── .dockerignore             # Docker build exclusions
├── config/                # Application configuration
│   ├── config_*.py               # All configuration modules
│   └── requirements.txt          # Python dependencies
├── documentation/         # Full documentation (203 markdown files)
├── DEPLOYMENT_GUIDE.txt   # Quick deployment instructions
└── README.md              # This file
```

## 🚀 Quick Start (3 Steps)

### Step 1: Transfer to Target Machine
```bash
# From your development machine:
scp -r RDK-Middleware-USB/ pi-user@RASPBERRY_PI_IP:/home/pi/
```

### Step 2: SSH into Target Machine
```bash
ssh pi-user@RASPBERRY_PI_IP
cd RDK-Middleware-USB
```

### Step 3: Start Application
```bash
./scripts/start-rdk-app.sh
```

✅ **Access Dashboard**: Open browser to `http://RASPBERRY_PI_IP:11078`

---

## 🎯 Available Scripts

### Start Application
```bash
./scripts/start-rdk-app.sh
```
- Builds Docker image (if needed)
- Starts container in background
- Displays access URL

### Stop Application
```bash
./scripts/stop-rdk-app.sh
```
- Gracefully stops container
- Preserves data volumes

### Restart Application
```bash
./scripts/restart-rdk-app.sh
```
- Equivalent to: stop → start

### Check Status
```bash
./scripts/status-rdk-app.sh
```
- Shows running container info
- Displays recent logs
- Indicates port status

---

## 🔧 Manual Docker Commands

If you prefer command-line control:

```bash
# Build image
cd docker-files/
sudo docker build -f Dockerfile.production -t rdk-middleware:latest .

# Start with docker-compose
sudo docker-compose -f docker-compose.rpi.clean.yml up -d

# Check container status
docker ps

# View logs
sudo docker logs rdk-middleware-dashboard -f

# Stop container
sudo docker-compose down
```

---

## ✨ Features Included

✅ **Complete Application Code**
- Flask web application
- All controllers and services
- Full configuration system

✅ **Docker Packaging**
- Production-optimized Dockerfile
- Docker Compose configuration
- Pre-configured networking

✅ **Automation Scripts**
- One-command deployment
- Lifecycle management
- Status monitoring

✅ **Documentation**
- 203 comprehensive markdown files
- Architecture guides
- API documentation
- Troubleshooting guides

---

## 🛠️ System Requirements

- Raspberry Pi 4/5 or Linux x86_64
- Docker & Docker Compose installed
- 2GB+ available disk space
- 2GB+ RAM
- Network connectivity

### Install Docker (if needed)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## 🌐 Access & Configuration

### Dashboard URL
```
http://<raspberry-pi-ip>:11078
```

### Port Configuration
Default port: **11078**  
Change in: `docker-files/docker-compose.rpi.clean.yml`

### Data Volumes
- Application config: `/app/Json/`
- Logs: `./iteration_logs/`
- Screenshots: `./screenshots/`

---

## 🔍 Troubleshooting

### Container won't start
```bash
# Check logs
sudo docker logs rdk-middleware-dashboard

# Rebuild image
./scripts/start-rdk-app.sh
```

### Permission denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port 11078 in use
```bash
# Find what's using the port
sudo lsof -i :11078

# Or kill and restart
./scripts/restart-rdk-app.sh
```

### Out of disk space
```bash
# Clean Docker images/containers
sudo docker system prune -a

# Check disk usage
sudo df -h
```

---

## 📊 Features

- **Device Management**: Add, configure, and manage devices
- **Test Execution**: Run automated test methods
- **IR Remote Control**: Control devices via IR blaster
- **Screenshot Validation**: AI-powered screen verification
- **Real-time Logging**: Live log streaming
- **Job Queue**: Manage test execution queue
- **Performance Metrics**: Track and analyze results

---

## 📝 Documentation

Comprehensive guides available in `documentation/` folder:
- Application architecture
- API references
- Configuration details
- Device setup
- Troubleshooting
- Best practices

---

## 🤝 Support

For issues or questions:
1. Check `DEPLOYMENT_GUIDE.txt`
2. Review documentation in `documentation/` folder
3. Check Docker logs: `./scripts/status-rdk-app.sh`
4. Review docker-entrypoint.sh for startup details

---

## 📄 License

RDK-E Middleware Testing Dashboard

**Version**: 2.0.1  
**Built**: April 20, 2026  
**Architecture**: ARM64 (Raspberry Pi optimized)

---

**Happy Testing! 🎉**
