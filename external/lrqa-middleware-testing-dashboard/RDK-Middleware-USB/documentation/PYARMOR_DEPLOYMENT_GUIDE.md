# PyArmor Docker Deployment Guide - Raspberry Pi 4

## Overview
This guide explains how to build a Docker image with encrypted Python code using PyArmor, then deploy it to Raspberry Pi 4 devices. The code remains fully functional but is protected from inspection.

---

## Prerequisites

### On Build Machine (x86_64):
```bash
pip install pyarmor
docker --version  # v20.10+
```

### On Raspberry Pi 4:
- Docker installed (`curl -sSL https://get.docker.com | sh`)
- 2GB+ free storage
- ARMv7 or ARM64 architecture

---

## Building the Encoded Docker Image

### Option 1: Build on Build Machine and Push to Registry

```bash
# Navigate to project directory
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement

# Build image with PyArmor obfuscation
docker build -f Dockerfile.pyarmor -t myregistry/rdk-middleware:encrypted-latest .

# Verify image size (should be similar to non-obfuscated)
docker images | grep rdk-middleware

# Push to Docker Hub or private registry
docker push myregistry/rdk-middleware:encrypted-latest
```

### Option 2: Build Directly on Raspberry Pi 4

```bash
# SSH into RPi 4
ssh pi@192.168.1.100

# Clone or copy your code
git clone <your-repo> && cd Enhancement

# Build with PyArmor (may take 5-10 minutes on RPi 4)
docker build -f Dockerfile.pyarmor -t rdk-middleware:encrypted .

# Verify
docker images
```

---

## Running the Encoded Image on Raspberry Pi 4

### Basic Run Command
```bash
docker run -d \
  --name rdk-middleware \
  -p 11078:11078 \
  -v /opt/middleware/iteration_logs:/app/iteration_logs \
  -v /opt/middleware/screenshots:/app/screenshots \
  -e FLASK_ENV=production \
  rdk-middleware:encrypted
```

### With Docker Compose (Recommended)
Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  middleware:
    image: rdk-middleware:encrypted
    container_name: rdk-middleware
    ports:
      - "11078:11078"
    volumes:
      - ./iteration_logs:/app/iteration_logs
      - ./screenshots:/app/screenshots
      - ./devices.json:/app/devices.json
      - ./.env:/app/.env:ro
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11078/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

Then run:
```bash
docker-compose up -d
docker-compose logs -f
```

---

## Verifying the Deployment

### Check Image is Running
```bash
docker ps | grep middleware
```

### Verify Application Health
```bash
curl http://localhost:11078/api/health
curl http://localhost:11078/  # Should load dashboard
```

### Check Logs
```bash
docker logs rdk-middleware
docker logs -f rdk-middleware  # Follow logs
```

### Verify Code is Encrypted (in container)
```bash
# Connect to running container
docker exec -it rdk-middleware bash

# Check app.py is encrypted (not readable text)
cat app.py | head -20  # Will show binary/encrypted content

# But Python still executes it normally
python -c "import app"  # Should work without errors
```

---

## What Gets Encrypted

✅ **Encrypted:**
- `app.py` - Main Flask application
- `controllers/*.py` - Business logic
- `services/*.py` - Service layer
- `models/*.py` - Data models
- `utils/*.py` - Utility functions
- `methods/*.py` - Test methods
- All imported modules

❌ **NOT encrypted** (remains readable):
- `config*.py` - Configuration files
- `templates/*.html` - HTML templates
- `static/` - CSS, JavaScript, images
- `requirements.txt` - Dependencies
- `.env` - Environment variables

### Why Not Encrypt Everything?
- **Config files** need to be human-readable for deployment configuration
- **Templates** are non-executable data
- **Static assets** are served directly by Flask
- **Requirements** need to be readable for dependency resolution

To encrypt configs if needed:
```bash
# Add to your Dockerfile after PyArmor obfuscation:
RUN pyarmor obfuscate --output /app/dist --no-wrap config*.py
```

---

## Performance Impact

### On Raspberry Pi 4:
- **First run startup**: +2-3 seconds (PyArmor unpacking)
- **Subsequent runs**: No overhead (cached)
- **Runtime execution**: <1% overhead (negligible)
- **Memory usage**: +5-10MB for PyArmor runtime
- **Image size**: Similar to non-obfuscated (~500MB)

### Optimization for RPi 4:
```dockerfile
# If memory-constrained, use 2-stage build (already includes this)
# Keep runtime image slim (python:3.11-slim)
# Use --restrict off for faster startup
```

---

## Debugging Encoded Code

### Option 1: Keep Source Code Separately
```bash
# Development/debugging environment
docker run -it \
  -v $(pwd)/app.py:/app/app.py \
  -v $(pwd)/models:/app/models \
  rdk-middleware:debug python -m pdb app.py
```

### Option 2: Enable Symbolic Debugging in PyArmor
```dockerfile
# In Dockerfile.pyarmor, modify obfuscate command:
RUN pyarmor obfuscate \
    --output /app/dist \
    --restrict off \
    --no-wrap \
    --debug  \  # Enable symbolic debugging
    bootstrap=3 \
    app.py
```

### Option 3: Container Shell Access
```bash
# For emergency debugging/inspection
docker exec -it rdk-middleware bash
python -c "import app; print(app.__file__)"  # See module location
```

---

## Multi-Architecture Builds (RPi 4 & Other ARM devices)

Build for multiple architectures:
```bash
docker buildx build \
  --platform linux/arm/v7,linux/arm64 \
  -f Dockerfile.pyarmor \
  -t myregistry/rdk-middleware:encrypted-multiarch \
  --push \
  .
```

RPi 4 auto-selects correct image:
```bash
docker pull myregistry/rdk-middleware:encrypted-multiarch
# Automatically pulls linux/arm64 for RPi 4
```

---

## Troubleshooting

### Issue: "pyarmor: command not found" on RPi 4
**Solution:** PyArmor is included in the image. If running commands outside container:
```bash
pip install pyarmor
```

### Issue: Application fails to start in container
**Check:**
```bash
docker logs rdk-middleware | tail -50
# Look for ImportError, PermissionError, or module not found
```

**Solution:** Ensure requirements.txt is complete:
```bash
docker exec rdk-middleware pip list
# Compare with your development environment
```

### Issue: Encrypted code works locally but not in Docker
**Solution:** PyArmor versions must match:
```bash
# Check version used during build
docker run rdk-middleware python -m pyarmor --version

# Check on your build machine
pyarmor --version

# Update if different:
pip install --upgrade pyarmor
```

### Issue: Very slow startup on RPi 4
**Optimization:**
```dockerfile
# Use --no-bootstrap (slightly faster):
RUN pyarmor obfuscate \
    --output /app/dist \
    --restrict off \
    --no-wrap \
    --no-bootstrap \  # Skip bootstrap overhead
    app.py
```

---

## Security Considerations

### What PyArmor Protects:
✅ Prevents casual code inspection via `strings` command
✅ Prevents modification of Python bytecode
✅ Obfuscates proprietary algorithms/logic
✅ License protection ready

### What PyArmor Does NOT Protect:
❌ Doesn't prevent decompilation with specialized tools
❌ Doesn't protect against memory inspection (for strings, API keys)
❌ Doesn't hide encrypted layers in binary reverse engineering
❌ Not a replacement for proper secrets management

### Best Practices:
1. **Use environment variables** for secrets, not hardcoded in code:
```python
import os
API_KEY = os.getenv('API_KEY')  # Pulled from .env or Docker secrets
```

2. **Use Docker secrets** for sensitive data:
```dockerfile
# In docker-compose.yml
secrets:
  api_key:
    file: ./secrets/api_key.txt
```

3. **Combine with code signing** for additional authenticity:
```bash
# Sign your Docker images
docker trust sign myregistry/rdk-middleware:encrypted
```

---

## Advanced: License Protection with PyArmor

To add license control to your encrypted app:

```python
# In your app.py before Flask initialization:
from pyarmor.pyarmor import generate_license

# Create license (valid for 30 days)
generate_license('rdk-middleware', days=30, features={'mqtt': 1})

# Your code then checks license at startup
```

See `pyarmor-license-setup.md` for detailed license configuration.

---

## Performance Comparison

| Metric | Non-Obfuscated | PyArmor Encrypted |
|--------|---|---|
| Image Size | ~500MB | ~500MB |
| Startup Time | ~2s | ~4-5s |
| Runtime Overhead | baseline | <1% |
| Memory Usage | baseline | +5-10MB |
| Code Inspectability | Full | Binary/Encrypted |
| Deployment Speed | Reference | Similar |

---

## Supporting Multiple RPi Devices

### Deploy Same Image to Multiple RPi 4s:

```bash
# On any RPi 4:
docker pull myregistry/rdk-middleware:encrypted-latest
docker run -d --name middleware myregistry/rdk-middleware:encrypted-latest

# Configuration per device:
docker run -d \
  -e DEVICE_IP=10.0.0.150 \
  -e DEVICE_NAME="RPi-Device-01" \
  -v ./devices.json:/app/devices.json \
  myregistry/rdk-middleware:encrypted-latest
```

---

## Summary

| Step | Command |
|------|---------|
| **Build** | `docker build -f Dockerfile.pyarmor -t rdk-middleware:encrypted .` |
| **Test Locally** | `docker run -p 11078:11078 rdk-middleware:encrypted` |
| **Deploy to RPi** | `docker-compose up -d` |
| **Verify** | `curl http://localhost:11078/api/health` |
| **View Logs** | `docker logs -f rdk-middleware` |
| **Verify Encrypted** | `docker exec rdk-middleware cat app.py | head -10` |

---

## Next Steps

1. Test the build locally first:
   ```bash
   docker build -f Dockerfile.pyarmor -t test:encrypted .
   docker run -it test:encrypted bash
   ```

2. Verify code execution works:
   ```bash
   docker run test:encrypted python app.py
   ```

3. Deploy to Docker registry
4. Pull and run on RPi 4

Questions? Check PyArmor docs: https://pyarmor.readthedocs.io/
