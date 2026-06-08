# 🚀 R-Pi 4 DEPLOYMENT - QUICK REFERENCE

## ⚡ FASTEST OPTION - Run On NEW R-Pi Terminal

```bash
# Mount USB and run deployment in one command
mkdir -p /media/usb && sudo mount /dev/sda1 /media/usb && sudo bash /media/usb/rpi4-deploy.sh
```

**That's it!** The script will handle everything.

---

## 📋 STEP-BY-STEP BREAKDOWN (If Manual Preferred)

### Step 1: Prepare USB on Development Machine
```bash
# On your DEVELOPMENT MACHINE (Linux/Mac):
# Copy these files to USB at /media/usb/
cp rpi4-deploy.sh /media/usb/
cp rpi4-setup-assistant.py /media/usb/
cp RPI4_TERMINAL_COMMANDS.md /media/usb/
cp lrqa-middleware-latest.tar /media/usb/          # Docker image (~12GB)
cp docker-compose.yml /media/usb/
cp requirements.txt /media/usb/

# Eject USB safely
sudo umount /media/usb
```

### Step 2: Connect USB to R-Pi 4 and Boot

### Step 3: SSH into R-Pi and Run Deployment
```bash
# SSH into R-Pi
ssh pi@<rpi-ip-address>
# or if on R-Pi desktop: open terminal

# Mount USB
mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Run ONE of these deployment options:

# OPTION A: Automated (Recommended)
sudo bash /media/usb/rpi4-deploy.sh

# OPTION B: Interactive Setup
python3 /media/usb/rpi4-setup-assistant.py

# OPTION C: Manual Docker Load & Run
sudo docker load -i /media/usb/lrqa-middleware-latest.tar
sudo docker run -d --name=lrqa-middleware -p 11078:11078 lrqa-middleware:latest
```

### Step 4: Verify Deployment
```bash
# Check if container is running
sudo docker ps | grep lrqa-middleware

# View logs
sudo docker logs lrqa-middleware

# Open browser
http://<rpi-ip-address>:11078
```

---

## 📁 FILES TO COPY TO USB

| File | Size | Purpose |
|------|------|---------|
| `rpi4-deploy.sh` | 12 KB | 🔧 Automated deployment |
| `rpi4-setup-assistant.py` | 13 KB | 🎯 Interactive setup wizard |
| `USB_DEPLOYMENT_QUICK_START.py` | 6 KB | 🚀 One-command full deployment |
| `RPI4_TERMINAL_COMMANDS.md` | 5.5 KB | 📚 Complete command reference |
| `lrqa-middleware-latest.tar` | ~12 GB | 🐳 Docker image (most important!) |
| `docker-compose.yml` | 1.6 KB | ⚙️ Compose configuration |
| `requirements.txt` | 273 B | 📦 Python dependencies |

**Total**: ~12 GB plus scripts

---

## 🔧 ON R-Pi 4 - EXACT TERMINAL COMMANDS

### Minimum Commands Required
```bash
# Step 1: Mount USB
mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Step 2: Install Docker (if not installed)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Step 3: Start Docker
sudo systemctl start docker

# Step 4: Load Docker image from USB
sudo docker load -i /media/usb/lrqa-middleware-latest.tar

# Step 5: Start application
sudo docker run -d \
  --name=lrqa-middleware \
  --restart=unless-stopped \
  -p 11078:11078 \
  lrqa-middleware:latest

# Step 6: Verify it's running
sudo docker ps
sudo docker logs lrqa-middleware

# Step 7: Access application
# Open browser: http://localhost:11078 (on R-Pi)
# Or from another machine: http://<rpi-ip>:11078
```

---

## ✅ VERIFICATION CHECKLIST

After deployment, verify:

```bash
# 1. Docker image loaded
sudo docker images | grep lrqa-middleware

# 2. Container is running
sudo docker ps | grep lrqa-middleware

# 3. Port 11078 is listening
sudo netstat -tlnp | grep 11078

# 4. Application responds
curl http://localhost:11078

# 5. View recent logs
sudo docker logs lrqa-middleware | tail -30
```

---

## 🔄 COMMON OPERATIONS

### View Application Logs (Live)
```bash
sudo docker logs lrqa-middleware -f
```
(Press Ctrl+C to exit)

### Stop Application
```bash
sudo docker stop lrqa-middleware
```

### Start Application
```bash
sudo docker start lrqa-middleware
```

### Restart Application
```bash
sudo docker restart lrqa-middleware
```

### Remove & Redeploy
```bash
sudo docker stop lrqa-middleware
sudo docker rm lrqa-middleware
sudo docker run -d --name=lrqa-middleware -p 11078:11078 lrqa-middleware:latest
```

### Open Shell in Container
```bash
sudo docker exec -it lrqa-middleware /bin/bash
```

### Check Container Status
```bash
sudo docker inspect lrqa-middleware
```

---

## 🐛 TROUBLESHOOTING

### Container won't start?
```bash
sudo docker logs lrqa-middleware
# Check error message and address
```

### Port 11078 already in use?
```bash
sudo lsof -i :11078                  # See what's using it
sudo docker run -d -p 9999:11078 lrqa-middleware:latest  # Use different port
```

### USB won't mount?
```bash
lsblk                                # List all block devices
sudo mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb      # Try different device if needed
```

### Docker not responding?
```bash
sudo systemctl restart docker
sudo systemctl status docker
```

### Need to check disk space?
```bash
df -h                    # Overall disk
docker system df         # Docker disk usage
```

---

## 📊 EXPECTED RESULTS

After successful deployment:

```
✓ Docker image loaded: lrqa-middleware:latest (12.3GB)
✓ Container running: lrqa-middleware
✓ Port 11078 listening
✓ Application accessible at: http://<rpi-ip>:11078
✓ Container auto-restarts on reboot
✓ Logs available via: docker logs lrqa-middleware -f
```

---

## 📞 SUPPORT INFO

- **Application Port**: 11078
- **Docker Image**: lrqa-middleware:latest
- **Container Name**: lrqa-middleware
- **Log Location**: See via `docker logs`
- **Data Volume**: `/app/data` (inside container)
- **Resource Limit**: 1GB RAM, 2 CPUs

---

## 🚀 STARTUP TIME

| Stage | Time |
|-------|------|
| USB mount | 5 sec |
| Docker service start (if needed) | 5 sec |
| Load Docker image from USB | 2-3 min |
| Container startup | 5-10 sec |
| Application ready | 10-20 sec |
| **Total** | **3-4 minutes** |

---

## 📝 NOTES

- First-time deployment will download/copy the 12GB image
- Subsequent deployments only start existing container (< 1 minute)
- Container automatically restarts on R-Pi reboot
- No need to reinstall Docker each time
- Application data persists in volumes

---

**Save this file for reference!** 📌
