# Docker Image Deployment Guide for Raspberry Pi

## ✅ Image Ready for Distribution

**Pre-built Docker Image**: `rpi4-app-image.tar`  
**File Size**: 1.2 GB  
**Built Date**: April 20, 2026  
**Latest Fixes**: ✅ IR Remotes fix included  
**Location**: `/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/`

---

## What's Included in This Image

This pre-built Docker image contains:
- ✅ **Latest application code** (including IR remotes fix)
- ✅ **All dependencies** installed (Flask, Paramiko, OpenCV, Tesseract, etc.)
- ✅ **All JSON configuration files** (ir_keycodes.json, device configs, etc.)
- ✅ **All Docker Compose files** for easy deployment
- ✅ **Optimized for ARM64** (Raspberry Pi 4 & Pi 5)
- ✅ **Production-ready** with Gunicorn, Gevent, Health checks

### Features Included
- Flask 3.0.0 web framework
- SSH device management (Paramiko)
- IR remote control (iTach support)
- Screen validation/OCR (Tesseract, OpenCV)
- Image processing (Pillow, scikit-image)
- Multi-worker support (Gevent)
- Auto-restart capability

---

## Deployment Steps

### Step 1: Transfer to Raspberry Pi

**Option A: Via USB Drive**
```bash
# On your development machine:
cp /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/rpi4-app-image.tar /media/RPI_DRIVE/

# Optional: Copy latest docker-compose file
cp docker-compose.rpi.clean.yml /media/RPI_DRIVE/
```

**Option B: Via SCP (Network)**
```bash
# On your development machine:
scp rpi4-app-image.tar pi-user@192.168.1.XX:/home/pi/
scp docker-compose.rpi.clean.yml pi-user@192.168.1.XX:/home/pi/
```

**Option C: Via SSH Direct Transfer**
```bash
# From your machine to RPi:
ssh pi-user@RPI_IP "mkdir -p /home/pi/docker-images"
scp rpi4-app-image.tar pi-user@RPI_IP:/home/pi/docker-images/
```

---

### Step 2: Load Image on Raspberry Pi

```bash
# SSH into the Raspberry Pi
ssh pi-user@RPI_IP

# Navigate to image location
cd /path/to/image/folder

# Load the Docker image
docker load -i rpi4-app-image.tar

# Verify it loaded (should show 'rpi4-app:latest')
docker images | grep rpi4-app
```

**Expected Output:**
```
REPOSITORY   TAG       IMAGE ID      CREATED       SIZE
rpi4-app     latest    a8c2a3cb13d9  5 hours ago   1.2GB
```

---

### Step 3: Run the Container

**Option A: Using Docker Compose (Recommended)**
```bash
# Copy the docker-compose file if not already there
cd /home/pi/app
cp docker-compose.rpi.clean.yml . # If copied separately

# Start the container
docker-compose -f docker-compose.rpi.clean.yml up -d

# View logs
docker-compose -f docker-compose.rpi.clean.yml logs -f
```

**Option B: Using Docker Run (Direct)**
```bash
docker run -d \
  --name rdk-middleware-dashboard \
  --restart unless-stopped \
  -p 11078:11078 \
  -v app_data:/app/data \
  -v reference_screens:/app/reference_screens \
  -v /path/to/Json:/app/Json:rw \
  -e FLASK_APP=app.py \
  -e FLASK_ENV=production \
  rpi4-app:latest
```

---

### Step 4: Verify Deployment

```bash
# Check container is running
docker ps | grep rdk-middleware

# Check application logs
docker logs rdk-middleware-dashboard

# Access the web interface
# http://RPI_IP:11078

# Test API endpoint (verify IR remotes are available)
curl http://localhost:11078/api/ir-remotes | python -m json.tool
```

**Expected Health Check Output:**
```
✅ Container running
✅ Web UI accessible at http://RPI_IP:11078
✅ API responding with IR remotes list
✅ Database connections working
```

---

## Post-Deployment Configuration

### 1. Update Device Configuration
```bash
# On the RPi, edit device configuration
docker exec -it rdk-middleware-dashboard nano /app/Json/devices.json

# Or mount the Json directory for easy editing from host
docker volume inspect app_data
```

### 2. Configure Network/SSH Access
```bash
# Ensure device IPs are configured correctly in devices.json
cat /app/Json/devices.json | grep -A 5 "test_device"

# Test SSH connectivity to devices
ssh root@DEVICE_IP -p 10022
```

### 3. Verify IR Configuration
Log into the web UI at http://RPI_IP:11078 and:
1. Add a method → Select "IR Test"
2. Verify remote types appear (XUMO_PR3, SKY_LC103, etc.)
3. Verify available keys are listed

---

## Deployment Checklist

### Pre-Deployment
- [ ] Docker image file received (1.2 GB)
- [ ] MD5/SHA checksum verified (optional)
- [ ] Raspberry Pi has 4GB+ RAM
- [ ] RPi has 2GB+ free disk space
- [ ] Network connectivity to test devices confirmed

### Deployment
- [ ] Image transferred to RPi
- [ ] Image loaded: `docker load -i rpi4-app-image.tar`
- [ ] Image verified: `docker images | grep rpi4-app`
- [ ] Container started: `docker-compose up -d`
- [ ] Container running: `docker ps`

### Post-Deployment
- [ ] Web UI accessible at http://RPI_IP:11078
- [ ] API endpoints responding (curl /api/ir-remotes)
- [ ] Devices configured in Json/devices.json
- [ ] SSH connectivity to test devices working
- [ ] IR remotes showing in UI dropdown
- [ ] Application logs clean (no errors)

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs rdk-middleware-dashboard

# Common issues:
# - Port 11078 already in use: Change port in docker-compose.yml
# - Out of memory: Check system resources
# - Missing volumes: Ensure Json directory exists

# Solution: 
docker-compose down  # Stop container
docker-compose up -d # Restart
```

### IR Remotes Not Showing
```bash
# Verify Json directory is mounted
docker exec rdk-middleware-dashboard ls -la /app/Json/

# Check if ir_keycodes.json exists
docker exec rdk-middleware-dashboard test -f /app/Json/ir_keycodes.json && echo "✅ Found" || echo "❌ Missing"

# Verify API endpoint
curl http://localhost:11078/api/ir-remotes | python -m json.tool
```

### Slow Performance
```bash
# Check resource usage
docker stats rdk-middleware-dashboard

# If memory maxed out:
# - Increase RPi RAM if possible
# - Reduce worker count in docker-compose

# If CPU maxed:
# - Close other applications
# - Reduce concurrent operations
```

### Can't Connect to Devices
```bash
# Test SSH connectivity
ssh -vvv root@DEVICE_IP -p 10022

# Check firewall rules
sudo iptables -L

# Verify device configuration
cat /app/Json/devices.json | python -m json.tool
```

---

## System Requirements

### Minimum
- **Raspberry Pi 4** (2GB RAM) - Not Recommended
- **Raspberry Pi 4** (4GB RAM) - Minimum
- **Raspberry Pi 5** (4GB RAM) - Recommended

### Recommended
- **Raspberry Pi 4** with 8GB RAM
- **Raspberry Pi 5** with 8GB+ RAM
- **USB 3.0 external SSD** for /app/data volume

### Storage
- **Image extraction**: ~2.5 GB (compressed: 1.2 GB)
- **Working data**: Variable (typically 500MB-2GB)
- **Total required**: 4-5 GB minimum

### Network
- Network connectivity to:
  - Test devices (SSH port 10022)
  - iTach IR blaster (IP: 10.0.0.12, Port: 4998)
  - Email servers (SMTP for notifications)

---

## Advanced Configuration

### Using Named Volumes (Recommended)
```yaml
volumes:
  app_data:
    driver: local
  reference_screens:
    driver: local
```

### Using Host Mounts (Alternative)
```yaml
volumes:
  - /mnt/external/app-data:/app/data:rw
  - /mnt/external/reference-screens:/app/reference_screens:ro
```

### Environment Variables
```
FLASK_ENV=production
LOG_LEVEL=INFO
SSH_TIMEOUT=30
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

---

## Performance Tuning

### Worker Count
```yaml
# In docker-compose or docker run:
CMD ["gunicorn", 
     "--workers", "2",      # 1 per CPU core + 1 (RPi 4 = 4 cores)
     "--worker-class", "gevent",
     "--timeout", "120",    # Increase if long SSH operations
     "app:app"]
```

### Memory Limits
```yaml
deploy:
  resources:
    limits:
      memory: 1024M  # Adjust for Pi's available memory
    reservations:
      memory: 512M
```

---

## Maintenance

### Regular Tasks
```bash
# Check container health
docker exec rdk-middleware-dashboard curl http://localhost:11078/health

# View logs
docker logs -f --tail=100 rdk-middleware-dashboard

# Backup configuration
docker cp rdk-middleware-dashboard:/app/Json /backup/

# Check disk usage
du -sh /var/lib/docker/volumes/app_data/
```

### Updates
```bash
# To deploy a newer image:
1. Stop current container: docker-compose down
2. Load new image: docker load -i new-image.tar
3. Start with new image: docker-compose up -d
```

---

## Containerized Application Info

**Web Interface**: http://RPI_IP:11078  
**API Endpoint**: http://RPI_IP:11078/api/  
**Admin Functions**: Accessible from web UI after login  
**Database**: JSON files in /app/Json (persistent volume)  
**Logs**: Accessible via `/api/logs` endpoint or `docker logs`

---

## Support

For issues or questions:

1. **Check logs**: `docker logs rdk-middleware-dashboard`
2. **Verify connectivity**: SSH to devices, test IR blaster
3. **Review API responses**: `curl http://localhost:11078/api/ir-remotes`
4. **Check documentation**: Refer to IR_DOCKER_FIX_GUIDE.md

---

**Image Build Date**: April 20, 2026  
**Docker Version**: 20.10+  
**Python Version**: 3.11  
**Status**: ✅ Production Ready
