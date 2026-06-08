# PyArmor Docker - Quick Start Guide

## 5-Minute Setup

### Step 1: Verify Files Exist
```bash
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement

# Check required files
ls -la Dockerfile.pyarmor
ls -la build-encrypted-docker.sh
chmod +x build-encrypted-docker.sh
```

### Step 2: Build Encrypted Docker Image (Local Machine)
```bash
# Option A: Using the build script (recommended)
./build-encrypted-docker.sh build

# Option B: Manual Docker build
docker build -f Dockerfile.pyarmor -t rdk-middleware:encrypted .
```

**Expected output:**
```
Successfully built 1a2b3c4d5e6f
Successfully tagged rdk-middleware:encrypted
```

### Step 3: Test Locally (Verify It Works)
```bash
# Start container
docker run -d --name test-rdk -p 11078:11078 rdk-middleware:encrypted

# Wait 5 seconds for startup
sleep 5

# Test API
curl http://localhost:11078/api/health

# Check logs
docker logs test-rdk | tail -20

# Stop test
docker stop test-rdk && docker rm test-rdk
```

**Expected:**
- Status 200 on curl
- No import errors in logs
- Application running normally

### Step 4: Deploy to Docker Hub (Optional but Recommended)

#### 4a: Create Docker Hub Account
- Go to https://hub.docker.com/signup
- Create free account (e.g., `yourusername`)

#### 4b: Login to Docker Hub
```bash
docker login
# Enter username and password
```

#### 4c: Push Image
```bash
# Tag with your username
docker tag rdk-middleware:encrypted yourusername/rdk-middleware:encrypted
docker tag rdk-middleware:encrypted yourusername/rdk-middleware:latest

# Push
docker push yourusername/rdk-middleware:encrypted
docker push yourusername/rdk-middleware:latest

# Verify on Docker Hub dashboard
```

### Step 5: Deploy to Raspberry Pi 4

#### Option A: From Docker Hub (Easiest)
```bash
# SSH to RPi
ssh pi@192.168.1.100  # Replace with your RPi IP

# Create directories
mkdir -p /opt/middleware/{iteration_logs,screenshots}
cd /opt/middleware

# Pull and run
docker pull yourusername/rdk-middleware:encrypted
docker run -d \
  --name rdk-middleware \
  -p 11078:11078 \
  -v /opt/middleware/iteration_logs:/app/iteration_logs \
  -v /opt/middleware/screenshots:/app/screenshots \
  -e FLASK_ENV=production \
  yourusername/rdk-middleware:encrypted

# Verify
curl http://localhost:11078/api/health
docker logs rdk-middleware
```

#### Option B: Using Docker Compose (Better)
```bash
# On RPi: create docker-compose.yml
cat > /opt/middleware/docker-compose.yml << 'EOF'
version: '3.8'
services:
  middleware:
    image: yourusername/rdk-middleware:encrypted
    container_name: rdk-middleware
    ports:
      - "11078:11078"
    volumes:
      - ./iteration_logs:/app/iteration_logs
      - ./screenshots:/app/screenshots
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
EOF

# Run
cd /opt/middleware
docker-compose up -d
docker-compose logs -f
```

### Step 6: Verify Code is Encrypted
```bash
# On your local machine:
docker run rdk-middleware:encrypted cat app.py | head -20

# Should show: binary/garbled content, NOT readable Python code
# Example:
# OxrO2Zyc0Owr/pz1O7EyOyBz...  (binary content)
```

---

## Verification Checklist

✅ **Code Encryption**
```bash
# Inside container - app.py should be binary
docker run rdk-middleware:encrypted file app.py
# Should output: "data" or similar, NOT "Python script"
```

✅ **Application Works**
```bash
# Should return 200 OK
curl -v http://localhost:11078/api/health
```

✅ **Performance OK**
```bash
# On RPi - should stay under 200MB memory
docker stats rdk-middleware
```

✅ **Logs are Clean**
```bash
# Should show NO errors
docker logs rdk-middleware | grep -i error
```

---

## What's Different from Normal Image?

| Aspect | Normal Image | Encrypted Image |
|--------|---|---|
| Building | `docker build -f Dockerfile` | `docker build -f Dockerfile.pyarmor` |
| Running | `docker run` | `docker run` (same!) |
| Performance | Baseline | +3-5s first start, <1% overhead runtime |
| Code visibility | Source .py files readable | Binary/encrypted (unreadable) |
| Image size | ~500MB | ~500MB (same) |
| Deployment | Same | Same (transparent to user) |
| Debugging | Full access | Limited but possible |

**Key point:** Once built and deployed, it runs identically to a normal image. Users can't tell the difference!

---

## Troubleshooting

### "app.py is still readable" after build
```bash
# Check if PyArmor worked:
docker run rdk-middleware:encrypted python -c "import app"
# If it imports successfully, obfuscation worked

# View raw file:
docker run rdk-middleware:encrypted od -c app.py | head
# Should show non-ASCII characters
```

### Application won't start on RPi
```bash
# Check RPi Docker logs
docker logs rdk-middleware | tail -50

# Common issues:
# 1. Port 11078 already in use: docker ps -a | grep 11078
# 2. Insufficient storage: docker system df
# 3. Architecture mismatch: docker inspect rdk-middleware:encrypted | grep Arch
```

### "Error: Port 11078 in use"
```bash
# Find and stop old container
docker ps -a | grep rdk-middleware
docker rm rdk-middleware

# Or use different port:
docker run -d -p 11079:11078 rdk-middleware:encrypted
```

### Very slow build on RPi 4
This is normal - PyArmor compilation takes longer on ARM:
- Local x86 build: 3-5 minutes
- RPi 4 build: 10-15 minutes

**Recommendation:** Build on local machine, push to Docker Hub, then pull on RPi.

### Application works locally but fails on RPi
```bash
# Check for architecture issues
docker run --rm manylinux/manylinux2014_aarch64 uname -m
# Should show: aarch64 or armv7l for RPi 4

# Might need to build for ARM specifically:
docker buildx build --platform linux/arm64 \
  -f Dockerfile.pyarmor \
  -t rdk-middleware:encrypted .
```

---

## Multiple RPi Deployments

Deploy same encrypted image to multiple RPi 4 devices:

```bash
RPI_DEVICES=("192.168.1.100" "192.168.1.101" "192.168.1.102")

for rpi in "${RPI_DEVICES[@]}"; do
  ssh pi@$rpi "docker pull yourusername/rdk-middleware:encrypted && \
               docker run -d -p 11078:11078 \
               yourusername/rdk-middleware:encrypted"
done

# Verify all running
for rpi in "${RPI_DEVICES[@]}"; do
  echo "=== RPi $rpi ==="
  ssh pi@$rpi "curl -s http://localhost:11078/api/health"
done
```

---

## Next Steps

1. **Build first image locally:**
   ```bash
   ./build-encrypted-docker.sh build
   ```

2. **Test locally:**
   ```bash
   ./build-encrypted-docker.sh test
   ```

3. **Create Docker Hub account and push:**
   ```bash
   docker login
   docker tag rdk-middleware:encrypted YOUR_USERNAME/rdk-middleware:encrypted
   docker push YOUR_USERNAME/rdk-middleware:encrypted
   ```

4. **Deploy to RPi 4:**
   ```bash
   ssh pi@YOUR_RPI_IP
   docker pull YOUR_USERNAME/rdk-middleware:encrypted
   docker run -d -p 11078:11078 YOUR_USERNAME/rdk-middleware:encrypted
   ```

5. **Access dashboard:**
   - Open browser: `http://YOUR_RPI_IP:11078`
   - Use normally (code is transparently protected)

---

## Common Commands Reference

```bash
# Build
docker build -f Dockerfile.pyarmor -t rdk-middleware:encrypted .

# Test locally
docker run -p 11078:11078 rdk-middleware:encrypted

# Push to registry
docker push yourusername/rdk-middleware:encrypted

# Deploy to RPi
ssh pi@192.168.1.100 "docker pull yourusername/rdk-middleware:encrypted"

# Start on RPi
ssh pi@192.168.1.100 "docker run -d -p 11078:11078 yourusername/rdk-middleware:encrypted"

# View logs
docker logs rdk-middleware

# Stop and remove
docker stop rdk-middleware && docker rm rdk-middleware

# Check if working
curl http://localhost:11078/api/health

# Verify code is encrypted
docker run rdk-middleware:encrypted cat app.py | head
```

---

## Support

- **PyArmor docs:** https://pyarmor.readthedocs.io/
- **Docker docs:** https://docs.docker.com/
- **Raspberry Pi Docker:** https://docs.docker.com/install/linux/docker-ce/debian/

**Questions?** Refer to `PYARMOR_DEPLOYMENT_GUIDE.md` for detailed information.

