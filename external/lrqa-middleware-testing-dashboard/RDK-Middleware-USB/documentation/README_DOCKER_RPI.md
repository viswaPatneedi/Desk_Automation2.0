# 🐳 Docker for Raspberry Pi - RDK-E Middleware Testing Dashboard

Complete Docker containerization for running the RDK-E Middleware Testing Dashboard on Raspberry Pi (Models 3, 4, and 5) with Linux OS.

---

## 🎯 Choose Your Path

### 🚀 **I want to get started NOW** (5 minutes)
→ Run this command:
```bash
bash docker-rpi-quickstart.sh
```
This automated script handles everything!

---

### 📖 **I want detailed instructions** (30 minutes)
→ Read: **[DOCKER_RPI_SETUP.md](DOCKER_RPI_SETUP.md)**

Comprehensive guide covering:
- Prerequisites & hardware requirements
- Docker installation on Pi
- Building & running containers  
- Configuration & tuning
- Troubleshooting
- Auto-start on boot

---

### ⚡ **I want quick reference** (2 minutes)
→ Read: **[DOCKER_RPI_QUICKREF.md](DOCKER_RPI_QUICKREF.md)**

Quick reference with:
- Common commands
- Key configuration
- Brief troubleshooting
- Next steps

---

### 📊 **I want system overview** (10 minutes)
→ Read: **[DOCKER_RPI_SUMMARY.md](DOCKER_RPI_SUMMARY.md)**

Overview of:
- All Docker files created
- Requirements & benchmarks
- Quick start options
- Support information

---

### ✅ **I need to verify my setup** (3 minutes)
→ Run this command:
```bash
bash docker-rpi-validate.sh
```
Checks:
- ✓ Docker installation
- ✓ Configuration files
- ✓ Container status
- ✓ Network connectivity
- ✓ System resources
- ✓ Data persistence

---

## 📦 What's Included

### Docker Files
- **Dockerfile.rpi** - Optimized image for ARM architecture
- **docker-compose.rpi.yml** - Full container configuration
- **.dockerignore** - Build optimization

### Setup & Automation
- **docker-rpi-quickstart.sh** - Automated setup (recommended!)
- **docker-rpi-validate.sh** - Post-setup validation
- **Makefile.rpi** - Simplified Docker commands

### Documentation
- **DOCKER_RPI_SETUP.md** - Comprehensive guide
- **DOCKER_RPI_QUICKREF.md** - Quick reference
- **DOCKER_RPI_SUMMARY.md** - Files overview
- **README_DOCKER_RPI.md** - This file

---

## ⚙️ System Requirements

### Minimum Hardware
| Model | RAM | microSD | Build Time |
|-------|-----|---------|------------|
| **Pi 3** | 512MB | 16GB | ~20 min |
| **Pi 4** | 2GB | 32GB | ~8 min |
| **Pi 5** | 4GB+ | 32GB | ~3 min |

### Software
- Raspberry Pi OS (Bullseye or newer)
- 64-bit OS recommended
- Internet connection for setup

---

## 🐳 What's Inside the Docker Image

The Docker image (~1.2GB) includes:
- **Python 3.11** with all dependencies
- **Flask** web framework
- **Tesseract OCR** for AI vision capabilities
- **OpenCV** for image processing
- **Paramiko** for SSH device connections
- **Gunicorn** for production serving
- **Gevent** for async workers
- All system libraries for ARM architecture

---

## 🚀 Quick Start (5 minutes)

### Step 1: Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Step 2: Run Quick Start
```bash
cd /path/to/Enhancement
bash docker-rpi-quickstart.sh
```

### Step 3: Access
```
Web UI: http://<your-pi-ip>:11078
```

That's it! The script handles:
- Detecting your Pi model
- Asking for email configuration
- Building the image
- Starting the container
- Showing access information

---

## 💻 Available Commands

### Using Quick Start Script
```bash
bash docker-rpi-quickstart.sh
```

### Using Make Commands
```bash
make -f Makefile.rpi help          # Show all commands
make -f Makefile.rpi build         # Build image
make -f Makefile.rpi up            # Start container
make -f Makefile.rpi down          # Stop container
make -f Makefile.rpi logs          # View logs
```

### Using Docker Compose Directly
```bash
docker compose -f docker-compose.rpi.yml build
docker compose -f docker-compose.rpi.yml up -d
docker compose -f docker-compose.rpi.yml logs -f
docker compose -f docker-compose.rpi.yml down
```

---

## 🔐 Configuration

### Email Setup (Gmail)
1. Enable 2FA: https://myaccount.google.com/account
2. Get App Password: https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```

### Performance Tuning
Edit `docker-compose.rpi.yml` to adjust for your Pi:
```yaml
WORKERS=2        # Pi 3/4: 2, Pi 5: 4-8
memory: 2G       # Pi 4: 2G, Pi 5: 4G
```

---

## ✅ Validation After Setup

Verify everything is working:
```bash
bash docker-rpi-validate.sh
```

Or manually:
```bash
# Check container is running
docker ps | grep rdk-middleware

# Test health endpoint
curl http://localhost:11078/health

# View resource usage
docker stats rdk-middleware

# Check logs
docker logs rdk-middleware -f
```

---

## 📊 Performance Expectations

### System Resources (Idle)
- **Memory**: 300-600MB
- **CPU**: 5-30%
- **Disk I/O**: Minimal

### Build Performance
- **Pi 3**: ~20 minutes (first build)
- **Pi 4**: ~8 minutes
- **Pi 5**: ~3 minutes

### Response Times
- Web pages: 500-2000ms
- API calls: 50-500ms
- Screenshot: 5-15 seconds

---

## 🔄 Auto-Start on Boot

Create systemd service for auto-start:

```bash
sudo tee /etc/systemd/system/docker-rdk.service > /dev/null << EOF
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

sudo systemctl daemon-reload
sudo systemctl enable docker-rdk.service
sudo systemctl start docker-rdk.service
```

---

## 🚨 Troubleshooting

### Port Already in Use
```bash
sudo lsof -i :11078
sudo kill -9 <PID>
```

### Out of Memory
```bash
# Reduce workers in docker-compose.rpi.yml
WORKERS=1
```

### Build Fails
```bash
# Try without cache
docker compose -f docker-compose.rpi.yml build --no-cache
```

### Container Won't Start
```bash
# Check logs
docker logs rdk-middleware --tail 100

# Run in debug mode
docker compose -f docker-compose.rpi.yml up  # No -d flag
```

For more troubleshooting, see **DOCKER_RPI_SETUP.md**

---

## 📚 Documentation Reference

| Document | Purpose | For Whom |
|----------|---------|----------|
| **DOCKER_RPI_QUICKREF.md** | Quick reference & commands | Impatient users |
| **DOCKER_RPI_SETUP.md** | Complete setup guide | Detailed learners |
| **DOCKER_RPI_SUMMARY.md** | Overview of all files | Curious users |
| **Makefile.rpi** | Docker make commands | Automation lovers |
| **docker-rpi-quickstart.sh** | Automated setup | Beginners |
| **docker-rpi-validate.sh** | Validation script | Verification |

---

## 🎯 Getting to the Dashboard

After setup is complete:

1. **Find your Pi's IP**
   ```bash
   hostname -I
   ```

2. **Open in browser**
   ```
   http://<your-pi-ip>:11078
   ```

3. **Login** (default credentials - check app configuration)

4. **Add devices** → Test SSH → Create sequences → Execute!

---

## 🔍 Key Files Overview

### Configuration Files
- **docker-compose.rpi.yml** - Full container setup
  - Volume mounts for data persistence
  - Environment variables
  - Health checks
  - Resource limits

- **Dockerfile.rpi** - Image definition
  - ARM architecture support
  - All required packages
  - Gunicorn + gevent setup

### Data Persistence
All data is persisted on the host machine:
- `devices.json` - Device configuration
- `jobs.json` - Job history
- `saved_sequences.json` - Test sequences
- `iteration_logs/` - Execution logs
- `screenshots/` - Screenshot storage

**Data survives container removal!**

---

## 💾 Backup & Restore

### Automatic Backup
```bash
make -f Makefile.rpi backup
```

### Restore from Backup
```bash
make -f Makefile.rpi restore
```

### Manual Backup
```bash
mkdir -p backup
cp *.json iteration_logs screenshots backup/
tar -czf backup-$(date +%Y%m%d).tar.gz backup/
```

---

## 📞 Need Help?

1. **Quick questions** → Check **DOCKER_RPI_QUICKREF.md**
2. **Setup issues** → Check **DOCKER_RPI_SETUP.md** (Troubleshooting section)
3. **Verify setup** → Run `bash docker-rpi-validate.sh`
4. **Check logs** → `docker logs rdk-middleware -f`
5. **View stats** → `docker stats rdk-middleware`

---

## 🎓 Learning Path

**New to Docker?**
1. Read **DOCKER_RPI_QUICKREF.md** (2 min)
2. Run **docker-rpi-quickstart.sh** (5 min)
3. Access web UI (2 min)
4. Read **DOCKER_RPI_SETUP.md** (20 min)
5. Explore commands in **Makefile.rpi**

**Experienced with Docker?**
1. Review **docker-compose.rpi.yml**
2. Review **Dockerfile.rpi**
3. Adjust resources as needed
4. Run **docker-rpi-validate.sh**

---

## 🏁 First Steps After Setup

1. ✅ Run validation: `bash docker-rpi-validate.sh`
2. ✅ Access dashboard: `http://<pi-ip>:11078`
3. ✅ Add devices: Device Management → Add Device
4. ✅ Test SSH: Use "Test SSH" button
5. ✅ Create sequence: Sequences → Create New
6. ✅ Execute: Select device → Execute NOW

---

## 📝 Important Notes

⚠️ **Security**
- Change `SECRET_KEY` in production
- Don't commit `.env` file with real passwords
- Use strong SSH credentials

⚠️ **Disk Space**
- Monitor `iteration_logs/` size
- Implement log rotation after 30 days
- Reserve space for backups

⚠️ **Memory**
- Monitor usage with `docker stats`
- Reduce `WORKERS` if memory is low
- Enable swap on Pi 3 if needed

---

## 📞 Support Resources

- **Configuration Docs**: `copilot-instructions.md`
- **Feature Overview**: `README.md`
- **Architecture**: `APPLICATION_OVERVIEW.md`
- **Cloud Deployment** (alternative): `CLOUD_DEPLOYMENT_GUIDE.md`

---

## 🎯 Next: Choose Your Setup Method

### Quick Setup (Recommended)
```bash
bash docker-rpi-quickstart.sh
```

### Manual Setup
1. Read: [DOCKER_RPI_SETUP.md](DOCKER_RPI_SETUP.md)
2. Create: `.env` file from `.env.example`
3. Build: `docker compose -f docker-compose.rpi.yml build`
4. Run: `docker compose -f docker-compose.rpi.yml up -d`

### Validate Setup
```bash
bash docker-rpi-validate.sh
```

---

**Ready? Start with:** `bash docker-rpi-quickstart.sh`

Questions? Check the guides above or use `docker logs rdk-middleware -f` for detailed output.

---

*Created: April 2, 2026*  
*Support: Raspberry Pi 3, 4, 5 | Bullseye or newer*
