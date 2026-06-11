# RDK-E Middleware QA Dashboard - Production Deployment Guide

## Overview

This is a **production-ready Docker setup** for the RDK-E Middleware QA Testing Dashboard. The application runs in a Docker container with all dependencies included, while execution data (logs, screenshots) is stored in mounted volumes on the host.

## ✨ Key Features

- ✅ **Full Application Codebase**: All Python code, configs, and dependencies included in Docker image
- ✅ **Execution Data Separation**: App data, logs, and screenshots stored in host volumes (not in image)
- ✅ **Multi-Platform Support**: Runs on Raspberry Pi 4/5, x86 Linux, and other platforms
- ✅ **Automatic Startup**: Container auto-starts on boot with proper health checks
- ✅ **Easy Management**: Simple shell scripts for start/stop/restart/status
- ✅ **Persistent Data**: All execution data persists even if container is recreated
- ✅ **Production Optimized**: Gunicorn + Gevent for performance, logging configured

## 📁 Data Storage Structure

### Data Stored in Docker Image (Application Code)
```
Dockerfile.production     # Build configuration
app.py                   # Flask application
config_*.py              # Configuration files
controllers/             # Business logic
models/                  # Data models
services/                # Background services
templates/               # HTML templates
static/                  # CSS/JS files
requirements.txt         # Python dependencies
```

### Data Stored in Host Volumes (Execution Data - Persisted)
```
iteration_logs/          # Execution logs with UTC timestamps
screenshots/             # Test screenshots
data/                    # Application runtime data
reference_screens/       # Reference images for validation
Json/                    # Configuration data (devices.json, jobs.json, etc)
```

## 🚀 Quick Start

### 1. Build the Docker Image

```bash
# From the application root directory
./build-rdk-image.sh

# Options:
./build-rdk-image.sh --no-cache        # Rebuild from scratch
./build-rdk-image.sh --platform arm64  # Specify platform
```

**Time**: ~5-10 min on RPi, ~2-3 min on x86
**Result**: 1.2-1.5 GB Docker image: `rdk-middleware:latest`

### 2. Start the Application

```bash
./start-rdk-app.sh
```

The script will:
- ✅ Create required directories (iteration_logs, screenshots, etc)
- ✅ Check for Docker and required files
- ✅ Build image if not present
- ✅ Start the container
- ✅ Display access URL

**Access**: `http://YOUR_IP:11078`

### 3. Verify It's Running

```bash
./status-rdk-app.sh
```

Shows:
- Container status (running/stopped)
- Port listening status
- Recent logs
- Data volume information

## 📋 Available Commands

### Daily Usage
```bash
./start-rdk-app.sh      # Start application
./stop-rdk-app.sh       # Stop application gracefully
./restart-rdk-app.sh    # Stop and start
./status-rdk-app.sh     # Check status and logs
```

### Docker Direct Commands
```bash
# View logs
docker logs -f rdk-middleware-dashboard

# Access container shell
docker exec -it rdk-middleware-dashboard bash

# Check container stats
docker stats rdk-middleware-dashboard

# Inspect configuration
docker inspect rdk-middleware-dashboard
```

## 📊 Configuration

### Port Configuration
Edit `docker-compose.production.yml`:
```yaml
ports:
  - "11078:11078"  # HOST_PORT:CONTAINER_PORT
```

### Resource Limits
Edit `docker-compose.production.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 1024M
```

### Environment Variables
Edit `docker-compose.production.yml`:
```yaml
environment:
  FLASK_ENV: production
  PORT: 11078
  TZ: UTC
```

## 💾 Data Management

### Backup Execution Data
```bash
# Backup all execution data
tar -czf backup-$(date +%Y%m%d).tar.gz \
  iteration_logs/ screenshots/ data/ reference_screens/ Json/

# List backed up files
tar -tzf backup-20260420.tar.gz | head
```

### Restore from Backup
```bash
# Restore execution data
tar -xzf backup-20260420.tar.gz

# Restart app (uses restored data)
./restart-rdk-app.sh
```

### Clear Old Run Data
```bash
# CAREFUL: This deletes execution logs and screenshots!
rm -rf iteration_logs/* screenshots/*

# Then restart
./restart-rdk-app.sh
```

## 🔄 Deployment on Another RPi

### Option 1: Build Locally on Each RPi
```bash
# On new RPi
git clone <repo>
cd Enhancement
./build-rdk-image.sh      # Builds on this RPi
./start-rdk-app.sh        # Starts app
```

### Option 2: Export & Transfer Image
```bash
# On original RPi
docker save rdk-middleware:latest -o rdk-app.tar

# Transfer to new RPi (via USB, SCP, etc)
scp rdk-app.tar user@new-rpi:/home/user/

# On new RPi
docker load -i rdk-app.tar
./start-rdk-app.sh
```

### File Size Reference
- Dockerfile: ~2KB
- Application code: ~500MB (uncompressed)
- Docker image: ~1.2GB
- Compressed tar: ~400MB

## 🔧 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs rdk-middleware-dashboard

# Check if port is in use
netstat -tlnp | grep 11078

# Check disk space
df -h

# Rebuild image
./build-rdk-image.sh --no-cache
./restart-rdk-app.sh
```

### Execution Data Missing
```bash
# Verify volumes are mounted
docker inspect rdk-middleware-dashboard | grep -A 10 Mounts

# Check permissions
ls -la iteration_logs/ screenshots/ Json/

# Fix permissions if needed
sudo chown -R $USER:$USER iteration_logs screenshots data reference_screens Json
chmod 755 iteration_logs screenshots data reference_screens Json
```

### Application Not Responding
```bash
# Check if service is listening
curl http://localhost:11078

# Check container CPU/memory
docker stats rdk-middleware-dashboard

# Restart container
./restart-rdk-app.sh
```

## 📈 Performance

### Recommended Resources
- **RPi 4**: 4GB RAM minimum, 8GB+ recommended
- **RPi 5**: 8GB RAM minimum
- **x86 Linux**: 2GB RAM, 2 CPU cores minimum

### Typical Startup Time
- **First build**: 5-10 minutes on RPi
- **Image load**: <1 second
- **Container startup**: 5-10 seconds
- **App ready**: ~30 seconds total

### Memory Usage
- Container: ~300-500MB
- Application: ~100-200MB
- Total with OS: ~500-800MB on RPi

## 🔐 Security Considerations

### Sensitive Data
- Device credentials stored in `Json/devices.json`
- Backup these files regularly
- Don't share containers with credentials included

### Network Access
- Application listens on port 11078
- Consider firewall rules for production
- Use HTTPS proxy in front for internet exposure

### Log Retention
- Execution logs in `iteration_logs/` grow over time
- Implement log rotation if running long-term
- Archive old logs regularly

## 📚 Additional Resources

- **Docker Compose Docs**: https://docs.docker.com/compose/
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Gunicorn Docs**: https://gunicorn.org/
- **Raspberry Pi Docker**: https://docs.docker.com/install/linux/docker-ce/debian/

## 💡 Tips & Best Practices

1. **Regular Backups**: Backup `Json/` and `iteration_logs/` folders weekly
2. **Monitor Disk Space**: Execution data grows with each test run
3. **Update Regularly**: Rebuild image monthly with latest code
4. **Use Timestamps**: Logs are named with UTC timestamps for easy tracking
5. **Version Control**: Keep compose file in git for configuration history

---

**Last Updated**: April 20, 2026  
**Version**: 2.0.1  
**Application**: RDK-E Middleware QA Testing Dashboard
