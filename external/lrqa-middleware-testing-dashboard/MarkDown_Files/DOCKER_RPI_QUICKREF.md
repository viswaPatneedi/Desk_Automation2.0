# 🚀 Docker for Raspberry Pi - Quick Reference

**RDK-E Middleware Testing Dashboard**

---

## 📦 What Was Created

✅ **Dockerfile.rpi** - Optimized Docker image for Pi  
✅ **docker-compose.rpi.yml** - Compose configuration  
✅ **docker-rpi-quickstart.sh** - Automated setup script  
✅ **Makefile.rpi** - Simplified make commands  
✅ **DOCKER_RPI_SETUP.md** - Complete setup guide  
✅ **.dockerignore** - Build optimization  

---

## ⚡ Fastest Way to Get Started

### Step 1: Install Docker (5 minutes)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install -y docker-compose-plugin
```

### Step 2: Run Quick Start Script (2 minutes)
```bash
cd /path/to/Enhancement
bash docker-rpi-quickstart.sh
```

**That's it!** The script will:
- ✓ Check Docker installation
- ✓ Detect your Pi model
- ✓ Ask for email config
- ✓ Build the image
- ✓ Start the container

---

## 📊 What Gets Installed (Inside Docker)

- **Python 3.11** with all required libraries
- **Tesseract OCR** for AI vision
- **OpenCV** for image processing
- **Flask** web framework
- **Paramiko** for SSH
- **Gunicorn** for production serving
- **Gevent** for async workers

---

## 🎯 System Requirements (Minimum)

| Model | RAM | microSD | Build Time |
|-------|-----|---------|------------|
| Pi 3  | 512MB | 16GB | 20 min |
| Pi 4  | 2GB | 32GB | 8 min |
| Pi 5  | 4GB+ | 32GB | 3 min |

---

## 📍 Access After Setup

```
Web Interface: http://<your-pi-ip>:11078
Health Check: http://<your-pi-ip>:11078/health
```

Find your Pi IP:
```bash
hostname -I
```

---

## 🔧 Common Commands (Using Make)

```bash
make -f Makefile.rpi help          # Show all commands
make -f Makefile.rpi build         # Build image
make -f Makefile.rpi up            # Start container
make -f Makefile.rpi down          # Stop container
make -f Makefile.rpi logs          # View logs
make -f Makefile.rpi shell         # Shell access
make -f Makefile.rpi restart       # Restart container
make -f Makefile.rpi health        # Check health
make -f Makefile.rpi backup        # Backup data
```

---

## 🔧 Common Commands (Using Docker Compose)

```bash
# Start
docker compose -f docker-compose.rpi.yml up -d

# Stop
docker compose -f docker-compose.rpi.yml down

# View logs
docker compose -f docker-compose.rpi.yml logs -f

# Restart
docker compose -f docker-compose.rpi.yml restart

# Check status
docker ps | grep rdk-middleware
```

---

## 📧 Email Configuration

1. Enable 2FA on Gmail: https://myaccount.google.com/account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```

---

## 💾 Data Backup

```bash
# Backup everything
make -f Makefile.rpi backup

# Restore from backup
make -f Makefile.rpi restore
```

Backups include:
- Device configuration
- Job history
- Execution logs
- Screenshots

---

## 🚨 Troubleshooting

### Not enough memory?
```bash
# Reduce workers
# Edit docker-compose.rpi.yml:
WORKERS=1  # Instead of 2
```

### Port 11078 in use?
```bash
# Find process
sudo lsof -i :11078

# Kill it
sudo kill -9 <PID>
```

### Build taking too long?
```bash
# It's normal! Build times by Pi model:
# Pi 3: ~20 min (first time)
# Pi 4: ~8 min (first time)
# Pi 5: ~3 min (first time)

# Afterwards, use existing image
```

### Container won't start?
```bash
# Check logs
docker logs rdk-middleware

# Run in debug mode (don't use -d flag)
docker compose -f docker-compose.rpi.yml up
```

---

## 📚 Detailed Documentation

- **Full Setup Guide**: `DOCKER_RPI_SETUP.md`
- **System Overview**: `DOCKER_RPI_SUMMARY.md`
- **Make Commands**: `Makefile.rpi`
- **Compose Config**: `docker-compose.rpi.yml`
- **Image Details**: `Dockerfile.rpi`

---

## 🔄 Auto-Start on Boot

```bash
# Create systemd service (copy-paste this)
sudo tee /etc/systemd/system/docker-rdk.service > /dev/null << 'EOF'
[Unit]
Description=RDK Middleware Testing Dashboard
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/Enhancement
ExecStart=/usr/bin/docker compose -f docker-compose.rpi.yml up
ExecStop=/usr/bin/docker compose -f docker-compose.rpi.yml down
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable
sudo systemctl daemon-reload
sudo systemctl enable docker-rdk.service
sudo systemctl start docker-rdk.service

# Check status
sudo systemctl status docker-rdk.service
```

---

## 📊 Performance Expectations

### Idle (No Execution)
- CPU: 5-15%
- Memory: 300-600MB
- Disk I/O: Minimal

### During Execution
- CPU: 30-80% (device-dependent)
- Memory: 600-1000MB
- Disk I/O: Active (logging)

### Response Times
- Web pages: 500-2000ms
- API requests: 50-500ms
- Screenshot: 5-15 seconds

---

## 🎯 Next Steps After Setup

1. **Access the web UI**: `http://<pi-ip>:11078`
2. **Login** with your credentials
3. **Add devices**: Enter device IPs in Device Management
4. **Test SSH**: Use "Test SSH" button to verify connectivity
5. **Create sequence**: Build a test sequence
6. **Execute**: Click "Execute NOW" to start testing

---

## 📞 Need Help?

1. **Quick issues**: Check "Troubleshooting" section above
2. **Detailed help**: Read `DOCKER_RPI_SETUP.md`
3. **Docker commands**: Use `make -f Makefile.rpi help`
4. **Container logs**: `docker logs rdk-middleware -f`
5. **Resource issues**: `docker stats rdk-middleware`

---

## 🔐 Important Notes

⚠️ **Never commit `.env` file** - it contains passwords  
⚠️ **Change SECRET_KEY** in production  
⚠️ **Update email credentials** from `.env.example`  
⚠️ **Allocate sufficient microSD space** for logs  

---

## 📈 Upgrade/Rebuild

```bash
# To update with latest code
docker compose -f docker-compose.rpi.yml down
git pull  # Get latest code
docker compose -f docker-compose.rpi.yml build --no-cache
docker compose -f docker-compose.rpi.yml up -d
```

---

**Created**: April 2, 2026  
**For**: Raspberry Pi 3, 4, 5  
**OS**: Linux (Bullseye+)  
**Docker Version**: 20.10+
