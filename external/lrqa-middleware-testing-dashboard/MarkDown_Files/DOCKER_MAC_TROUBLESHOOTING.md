# Mac Docker Troubleshooting Guide

Comprehensive troubleshooting for Docker setup on macOS.

---

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Container Startup Issues](#container-startup-issues)
3. [Performance Issues](#performance-issues)
4. [Network/Connectivity Issues](#networkconnectivity-issues)
5. [Resource Issues](#resource-issues)
6. [File Permission Issues](#file-permission-issues)
7. [SMTP/Email Issues](#smtpemail-issues)

---

## Installation Issues

### Problem: Docker Desktop Won't Install

**Symptoms:**
- Installer fails
- Permission denied error
- Mac displays "damaged" warning

**Solutions:**

```bash
# 1. Check macOS version (must be 11+)
sw_vers -productVersion

# 2. Clear cache and retry
rm -rf ~/Library/Caches/Docker

# 3. Check disk space (need 20GB+)
df -h

# 4. Force remove DMG from quarantine
sudo xattr -rd com.apple.quarantine ~/Downloads/Docker.dmg

# 5. Install using Homebrew (alternative)
brew install docker
```

---

### Problem: Docker Daemon Won't Start

**Symptoms:**
- "Docker daemon not running" error
- Docker menu icon missing from top bar
- Commands fail with "Cannot connect to Docker daemon"

**Solutions:**

```bash
# 1. Restart Docker Desktop
# Click Docker icon → Quit Docker Desktop
# Wait 10 seconds
# Open Applications → Docker.app

# 2. Check logs
cat ~/Library/Logs/Docker/com.docker.docker/docker.log | tail -50

# 3. Verify permission
ls -la /var/run/docker.sock

# 4. Reset Docker
# Docker menu → Preferences → Reset → Reset to factory defaults
# WARNING: This removes all images and containers

# 5. Reinstall Docker
brew uninstall docker
brew install docker
```

---

### Problem: Can't Run "docker run hello-world"

**Symptoms:**
- "Cannot connect to Docker daemon" error
- "Connection refused" error
- Command hangs

**Solutions:**

```bash
# 1. Ensure Docker Desktop is running
# Look for Docker icon in top-right menu bar

# 2. Check if Docker service is active
docker version

# 3. Check Docker socket permissions
ls -la ~/.docker/run/docker.sock

# 4. Restart Docker daemon
killall Docker

# 5. Check system logs for errors
log show --predicate 'eventMessage contains[cd] "docker"' --last 10m
```

---

## Container Startup Issues

### Problem: "Port 5000 Already in Use"

**Symptoms:**
```
ERROR: for rdk-testing-dashboard
bind: Address already in use
```

**Solutions:**

```bash
# 1. Check what's using port 5000
lsof -i :5000

# 2. Kill the process
lsof -ti:5000 | xargs kill -9

# 3. Or use different port - edit docker-compose.yml:
# Change: "5000:5000"
# To:     "8000:5000"  (access on port 8000)

# 4. Verify port is free
nc -zv localhost 5000  # Should return connection refused
```

---

### Problem: Container Exits Immediately

**Symptoms:**
- Container shows "Exited" status
- No error message in logs
- Container won't stay running

**Solutions:**

```bash
# 1. Check exit code
docker-compose ps

# 2. View detailed logs
docker-compose logs --tail=100

# 3. Check Python errors
docker-compose logs web | grep -i "error\|exception"

# 4. Insufficient memory - increase in Docker preferences
# Docker menu → Preferences → Resources → Increase Memory to 6GB

# 5. Invalid config - check .env file
cat .env

# 6. Rebuild image (fixes many issues)
docker-compose build --no-cache
docker-compose down
docker-compose up -d
```

---

### Problem: "Failed to Build Image"

**Symptoms:**
```
ERROR: failed to solve with frontend dockerfile.v0
```

**Solutions:**

```bash
# 1. Check available disk space (need 20GB+)
df -h | grep -E "^/dev"

# 2. Clean up Docker resources
docker system prune -a --volumes

# 3. Rebuild without cache
docker-compose build --no-cache --progress=plain

# 4. Check Dockerfile syntax
docker build --help

# 5. Increase Docker resources
# Docker menu → Preferences → Resources
# - CPUs: At least 4
# - Memory: At least 6GB

# 6. Try building with original Dockerfile
docker build -f Dockerfile -t rdk-testing-dashboard:latest .
```

---

## Performance Issues

### Problem: Very Slow Build (>45 minutes)

**Symptoms:**
- Build hangs at specific step
- Very high CPU/memory usage
- Timeouts during package installation

**Solutions:**

```bash
# 1. Check available resources
docker stats

# 2. Increase Docker resource allocation
# Docker menu → Preferences → Resources
# Set to maximum available (not system max)

# 3. Change to Apple Silicon image (if on M1/M2/M3/M4)
# Dockerfile should auto-detect, but verify:
docker buildx ls

# 4. Clear build cache
docker builder prune -a

# 5. Build step-by-step with verbose output
docker-compose build --no-cache --progress=plain

# 6. Check internet connection
ping -c 3 8.8.8.8

# 7. Reduce concurrent operations
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)":/app alpine sh -c "rm -rf /app/.docker"
```

---

### Problem: Container Runs Slowly / High CPU Usage

**Symptoms:**
- Slow web page loads
- High CPU usage even when idle
- Memory usage increases over time

**Solutions:**

```bash
# 1. Check resource usage
docker stats rdk-testing-dashboard

# 2. View process details
docker-compose exec web top

# 3. Check CPU cores available
docker-compose exec web nproc

# 4. Increase Docker resource limits
# Docker menu → Preferences → Resources
# Increase CPU and Memory sliders

# 5. Reduce Gunicorn workers in Dockerfile
# Change: --workers 4
# To: --workers 2
# Then rebuild: docker-compose build --no-cache

# 6. Optimize Python startup
docker-compose exec web env | grep PYTHONOPTIMIZE

# 7. Monitor network I/O
docker stats --no-stream --format "table {{.Container}}\t{{.NetIO}}"
```

---

## Network/Connectivity Issues

### Problem: Can't Access http://localhost:5000

**Symptoms:**
- Connection refused
- Browser shows "ERR_CONNECTION_REFUSED"
- Port 5000 unreachable

**Solutions:**

```bash
# 1. Verify container is running
docker-compose ps

# 2. Check if port is mapped
docker ports rdk-testing-dashboard

# 3. Check Docker network
docker network ls

# 4. Test connectivity from Mac
curl -v http://localhost:5000

# 5. Test from inside container
docker-compose exec web curl http://localhost:5000

# 6. Check firewall (Mac sometimes blocks)
# System Preferences → Security & Privacy → Firewall
# Ensure Docker is allowed

# 7. Try alternative URL
# If 127.0.0.1:5000 works but localhost:5000 doesn't:
curl http://127.0.0.1:5000

# 8. Restart Docker
killall Docker
open /Applications/Docker.app
sleep 10
docker-compose up -d
```

---

### Problem: "DNS Resolution Failed"

**Symptoms:**
- Container can't reach external services
- "Name or service not known" error
- Email sending fails (SMTP connection)

**Solutions:**

```bash
# 1. Test DNS from container
docker-compose exec web nslookup 8.8.8.8

# 2. Check DNS configuration
docker-compose exec web cat /etc/resolv.conf

# 3. Restart Docker network
docker network prune

# 4. Specify DNS servers in docker-compose.yml
# Add to web service:
# dns:
#   - 8.8.8.8
#   - 8.8.4.4

# 5. Restart container
docker-compose down
docker-compose up -d

# 6. Test SMTP connection specifically
docker-compose exec web python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
print('Connected to SMTP!')
"
```

---

## Resource Issues

### Problem: "Out of Disk Space"

**Symptoms:**
```
no space left on device
```

**Solutions:**

```bash
# 1. Check available space
df -h

# 2. Find large files
du -sh * | sort -rh | head -20

# 3. Clean Docker resources
docker system prune -a --volumes

# 4. Remove old images
docker image ls | grep -v REPOSITORY | head -5 | awk '{print $3}' | xargs docker rmi

# 5. Remove dangling volumes
docker volume prune

# 6. Clear Docker Desktop cache
# Docker menu → Preferences → Resources → Reset
# Or manually:
rm -rf ~/Library/Containers/com.docker.docker/Data/vms/0

# 7. Clear system cache
rm -rf ~/Library/Caches/Docker

# 8. Check log files
du -sh ~/Library/Logs/Docker/*

# 9. Increase Mac storage
# Add external drive or upgrade storage
```

---

### Problem: "Memory Limit Exceeded"

**Symptoms:**
- Container crashes with out-of-memory error
- Slowed performance then crash
- High memory usage in stats

**Solutions:**

```bash
# 1. Check memory usage
docker stats rdk-testing-dashboard

# 2. Increase Docker memory allocation
# Docker menu → Preferences → Resources → Memory slider
# Set to 6GB-8GB minimum

# 3. Check app memory leaks
docker-compose logs --tail=50 | grep -i "memory\|oom\|killed"

# 4. Restart container to free memory
docker-compose restart

# 5. Monitor memory trends
watch -n 2 'docker stats --no-stream rdk-testing-dashboard'

# 6. Reduce workers if app uses too much
# Edit Dockerfile: --workers 2 (instead of 4)
docker-compose build --no-cache
```

---

## File Permission Issues

### Problem: "Permission Denied" on Mounted Volumes

**Symptoms:**
- Cannot access devices.json
- Cannot write to iteration_logs/
- "Permission denied" errors in logs

**Solutions:**

```bash
# 1. Check file permissions
ls -la devices.json
ls -la iteration_logs/

# 2. Fix permissions
chmod 644 devices.json
chmod 755 iteration_logs/

# 3. Make files writable
sudo chown $(whoami) *.json

# 4. Reset volume permissions
docker-compose down
rm -rf iteration_logs screenshots
mkdir -p iteration_logs screenshots
chmod 777 iteration_logs screenshots
docker-compose up -d

# 5. Check Docker's user context
docker-compose exec web id

# 6. Fix from inside container
docker-compose exec web chmod 777 /app/iteration_logs
```

---

### Problem: Files Not Persisting After Container Stops

**Symptoms:**
- Changes lost after restart
- Log files disappear
- Data not saved

**Solutions:**

```bash
# 1. Verify volumes are mounted
docker-compose config | grep -A 5 "volumes"

# 2. Check volume creation
docker volume ls | grep rdk

# 3. Rebuild with proper volumes
docker-compose down -v
docker-compose up -d

# 4. Verify file is actually saved
ls -la devices.json
ls -la iteration_logs/

# 5. Check if volumes are read-only
docker inspect rdk-testing-dashboard | grep -A 20 "Mounts"

# 6. Ensure absolute paths in docker-compose.yml
# Use: ${PWD}/devices.json (not ~/devices.json)
```

---

## SMTP/Email Issues

### Problem: "SMTP Connection Failed"

**Symptoms:**
- "Connection refused" when sending email
- Port 587 unreachable
- Email service not working

**Solutions:**

```bash
# 1. Verify .env configuration
cat .env | grep SMTP

# 2. Test SMTP from container
docker-compose exec web python << 'EOF'
import smtplib
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    print("SMTP connection successful!")
    server.quit()
except Exception as e:
    print(f"Error: {e}")
EOF

# 3. Check internet connectivity
docker-compose exec web ping -c 3 8.8.8.8

# 4. Test Gmail specifically
docker-compose exec web python << 'EOF'
import smtplib
email = input("Enter Gmail: ")
password = input("Enter App Password: ")
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email, password)
    print("Gmail authentication successful!")
    server.quit()
except Exception as e:
    print(f"Error: {e}")
EOF

# 5. If Gmail fails, check app password
# Visit: https://myaccount.google.com/apppasswords
# Copy 16-character password to .env

# 6. Verify firewall allows port 587
# System Preferences → Security & Privacy → Firewall

# 7. Restart container with correct credentials
# Edit .env
# Then: docker-compose restart
```

---

## Still Not Working?

### Diagnostic Commands

```bash
# 1. Full system status
docker-compose ps -a
docker images
docker volume ls

# 2. Complete logs
docker-compose logs --tail=200

# 3. Container inspection
docker inspect rdk-testing-dashboard

# 4. Docker system info
docker system info

# 5. Mac system info
system_profiler SPHardwareDataType
system_profiler SPSoftwareDataType

# 6. Check Docker settings
cat ~/.docker/config.json

# 7. Network diagnostics
docker network inspect bridge
```

### Getting Help

1. Collect diagnostic info:
   ```bash
   docker-compose logs > logs.txt
   docker inspect rdk-testing-dashboard > container.txt
   cat .env > env.txt  # (remove passwords first!)
   ```

2. Check logs files directory

3. Search GitHub issues for similar problems

4. Contact support with diagnostic output

---

## Quick Reset

If everything is broken:

```bash
# WARNING: This is destructive!

# 1. Stop everything
docker-compose down -v

# 2. Remove images
docker system prune -a

# 3. Reset Docker Desktop
# Docker menu → Preferences → Reset → Reset to factory defaults
# OR
rm -rf ~/Library/Containers/com.docker.docker/Data/*

# 4. Restart Docker
killall Docker
open /Applications/Docker.app

# 5. Try again
docker-compose build
docker-compose up -d
```

---

## References

- Docker Documentation: https://docs.docker.com/docker-for-mac/
- Docker Troubleshooting: https://docs.docker.com/docker-for-mac/troubleshoot/
- Mac System Preferences: https://support.apple.com/en-us/HT201238
- Gmail App Passwords: https://support.google.com/accounts/answer/185833

---

**Last Updated**: March 25, 2026
**Tested On**: macOS 12+, Docker Desktop 4.0+, M1/M2/M3/Intel Macs
