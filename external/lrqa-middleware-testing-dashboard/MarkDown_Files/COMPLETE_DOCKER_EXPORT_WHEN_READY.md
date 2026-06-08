# Commands to Complete Once Docker Build Finishes

## Quick Reference - Copy & Paste

### Step 1: Check if image is built
```bash
sudo docker images | grep rpi4-app
```

**Expected output:**
```
rpi4-app          latest    abc123def456    30 seconds ago    850MB
```

If you see this, proceed to Step 2. If not, build is still running.

---

### Step 2: Export image to tar file
```bash
sudo docker save -o /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar rpi4-app:latest
```

**Time**: 5-15 minutes (this is normal - Docker is compressing the image)

**What it looks like:**
```
(No output is normal - it's working silently)
(Wait for prompt to return)
```

---

### Step 3: Verify tar file was created
```bash
ls -lh /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar
```

**Expected output:**
```
-rw-r--r-- 1 lrqa lrqa 850M Apr 17 14:30 /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar
```

Size should be **800MB-1GB** ✅

---

### Step 4: Quick integrity check (optional)
```bash
file /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar
```

**Expected output:**
```
/media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar: POSIX tar archive
```

---

### Step 5: Verify Lexar folder contents
```bash
ls -lh /media/lrqa/Lexar/Pi4-Dockerimage/ | grep -E "\.tar$|\.sh$|\.yml$"
```

**Expected output:**
```
-rw-r--r-- 1 lrqa lrqa 850M Apr 17 14:30 rpi4-app-image.tar
-rwxr-xr-x 1 lrqa lrqa  13K Apr 17 12:47 rpi4-setup-with-prebuilt.sh
-rwxr-xr-x 1 lrqa lrqa  12K Apr 17 12:47 rpi4-setup-complete.sh
-rw-r--r-- 1 lrqa lrqa 5.0K Apr 17 12:47 docker-compose.rpi.clean.yml
```

---

## ⏳ Monitor Build Progress

### Method 1: Check if image exists (quickest)
```bash
sudo docker images | grep rpi4-app && echo "✅ READY" || echo "🔄 BUILDING"
```

### Method 2: See all image builds in progress
```bash
sudo docker ps -a
```

### Method 3: Check system resources while building
```bash
# Show CPU/Memory usage
top -b -n1 | head -15

# Show disk I/O
iostat -d -x 1 2

# Show network if pulling packages
iftop
```

---

## 🎯 One-Line Builder (when ready)

Once you confirm image exists, copy & paste this to export immediately:

```bash
echo "Exporting Docker image..."  && sudo docker save -o /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar rpi4-app:latest && echo "✅ Export complete!" && ls -lh /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar
```

This will:
1. Export the image
2. Confirm completion
3. Show file size

---

## ✅ Success Indicators

### Build Complete ✅
```bash
sudo docker images | grep rpi4-app:latest
```

Shows something like:
```
rpi4-app    latest    sha256:abc...    X days ago    800MB
```

### Export Complete ✅
```bash
ls -lh /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar | awk '{print $5}'
```

Shows: `800M` or similar (800MB-1GB range)

### Ready for Deployment ✅
```bash
test -f /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar && echo "✅ DEPLOYMENT READY" || echo "❌ NOT READY"
```

---

## 🚀 Once Tar File Exists

Your Lexar USB will be ready for **FAST deployment**:

```bash
# On new RPi:
cd /mnt/usb/Pi4-Dockerimage
./rpi4-setup-with-prebuilt.sh

# Deployment: 5-10 minutes ⚡
# Access: http://<rpi-ip>:11078
```

---

## 📊 Expected Times

| Phase | Duration |
|-------|----------|
| Docker build (current) | 30-45 min |
| Image export to tar | 5-15 min |
| **Total prep time** | **40-60 min** |
| Deployment on new RPi | 5-10 min |
| **Total start-to-ready** | **45-70 min** |

---

## 🆘 If Something Goes Wrong

### "Build seems stuck"
Check what's happening:
```bash
sudo docker ps -a
```

### "Out of disk space"
Check available space:
```bash
df -h /home
```

Need to free up? (Warning: be careful):
```bash
# Remove old Docker images
sudo docker image prune -a

# Check again
df -h /home
```

### "Export failed"
Retry with more verbose output:
```bash
sudo docker save rpi4-app:latest | gzip > /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar.gz
```

### "Need to manually rebuild"
```bash
cd /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement
sudo docker build -f Dockerfile.rpi.clean -t rpi4-app:latest . --no-cache
```

---

## 📝 Log File Location

Save output to file for reference:
```bash
{
    echo "=== BUILD STATUS ==="
    date
    echo ""
    echo "Image status:"
    sudo docker images | grep rpi4-app
    echo ""
    echo "File status:"
    ls -lh /media/lrqa/Lexar/Pi4-Dockerimage/rpi4-app-image.tar 2>/dev/null || echo "Not yet created"
    echo ""
    echo "=== END STATUS ==="
} | tee build-status-$(date +%Y%m%d-%H%M%S).log
```

---

## 🎯 Next Steps

1. **Wait for build to complete** (check status periodically)
2. **Run export command** (Step 2 above) once image exists
3. **Verify tar file** is 800MB-1GB
4. **Connect Lexar to new RPi**
5. **Run deployment script**
6. **Access application** at http://<ip>:11078

---

**Generated**: April 17, 2026  
**Purpose**: Help complete Option B (pre-built image) deployment  
**Status**: Ready to execute once Docker build completes  
