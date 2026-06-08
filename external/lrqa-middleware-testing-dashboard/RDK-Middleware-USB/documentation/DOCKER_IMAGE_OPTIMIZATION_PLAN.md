# Docker Image Optimization & USB Storage Configuration

## Current Problem Analysis

### 1. **Why Docker Image is 10+GB**

Current directory sizes (from root):
```
5.7GB    Enhancement_output/          ← Execution results data (NOT needed in image)
2.9GB    updated_code/                ← Old code backups (NOT needed in image)
2.5GB    SAM-CD-2GB/                  ← External data (NOT needed in image)
703MB    screenshots/                 ← Execution screenshots (NOT needed in image)
550MB    venv/                        ← Virtual environment (rebuilt during Docker build)
164MB    logs/                        ← Execution logs (NOT needed in image)
37MB     reference_screens/           ← Reference data (should be externalized)
4.0MB    auto_deploy.log              ← Log files (NOT needed in image)
2.5MB    device_logs/                 ← Device logs (NOT needed in image)
```

**Total unnecessary files: ~13GB+** ➜ **This is why the Docker image is so large!**

### 2. **Files That SHOULD Be In Docker Image**

**Actual Application Code (~100-150MB):**
```
✓ app.py                               (124KB)
✓ controllers/                         (256KB)
✓ models/                              (172KB)
✓ services/                            (472KB)
✓ utils/                               (76KB)
✓ templates/                           (1.2MB)
✓ static/                              (956KB)
✓ config_*.py files                    (Various)
✓ requirements.txt                     (Dependencies)
✓ Dockerfile & docker-compose.yml     
✓ README.md & documentation           
```

**Expected Optimized Image Size: 400-500MB** (vs current 10GB+)

### 3. **Current USB Detection Logic**

Located in `session_utils.py`:
```python
# Current implementation looks for:
/media/pi/lexar       # For R-PI with user 'pi'
/media/pi/Lexar
/media/pi/LEXAR
```

**Problem:** Only hardcoded for R-PI 'pi' user. Doesn't work on other systems (like your current system where USB is at `/media/lrqa/Lexar`).

---

## Solution: Optimized Docker Image + USB Configuration

### Phase 1: Minimize Docker Image

#### Step 1A: Update `.dockerignore` (Already good, but needs review)

Current `.dockerignore` already excludes most data. Need to verify:
- ✓ iteration_logs/
- ✓ screenshots/
- ✓ logs/
- ✓ Enhanced_output/
- ✓ venv/

**ADD TO .dockerignore:**
```
updated_code/
SAM-CD-2GB/
device_logs/
captured_images/
base_images/
reference_screens/
*.log
*.pid
*.bak
*.backup*
```

#### Step 1B: Update Dockerfile - Add Cleanup

```dockerfile
# Remove after copying to keep image small
RUN rm -rf updated_code/ SAM-CD-2GB/ device_logs/ captured_images/
```

### Phase 2: Implement Smart USB Detection & Storage

#### Step 2A: Create New `usb_storage_manager.py`

This will handle:
1. Auto-detect USB on both Linux desktop systems and R-PI
2. Create necessary directories on USB
3. Handle fallback to local storage if USB not available
4. Manage mount rules

#### Step 2B: Update `session_utils.py`

Improve USB detection to work on:
- R-PI with different users (pi, root)
- Desktop Linux systems (`/media/lrqa/...`, `/mnt/...`)
- Windows systems (if needed)

#### Step 2C: Update Docker Compose

Configure volume mounts:
```yaml
volumes:
  - /mnt/usb:/app/data                 # External USB storage
  - ./devices.json:/app/devices.json   # Config
  - ./templates:/app/templates         # Code
```

---

## Implementation Steps

### **Step 1: Clean Current Image Build**
- [ ] Remove large unnecessary directories from workspace
- [ ] Update `.dockerignore`
- [ ] Update `Dockerfile` to exclude build artifacts

### **Step 2: Implement USB Management**
- [ ] Create `usb_storage_manager.py` with USB auto-detection
- [ ] Update `session_utils.py` to use USB storage manager
- [ ] Update `log_service.py` to support external storage paths
- [ ] Update Docker environment variables for storage root path

### **Step 3: Create R-PI Deployment Variant**
- [ ] Create `docker-compose.rpi.yml` with USB volume mount
- [ ] Create systemd service that:
  - Detects USB on boot
  - Creates mount points
  - Starts Docker container with proper volumes

### **Step 4: Create Desktop/Development Variant**
- [ ] Create `docker-compose.dev.yml` for local development
- [ ] Support both USB and local storage

### **Step 5: Update Documentation**
- [ ] Update deployment guides
- [ ] Add USB configuration instructions
- [ ] Add troubleshooting guide

---

## File Structure in Docker Image

**Expected Minimal Docker Image Structure (~400-500MB):**

```
/app/
├── app.py                      ✓ Include
├── controllers/                ✓ Include
├── models/                     ✓ Include
├── services/                   ✓ Include
├── utils/                      ✓ Include
├── templates/                  ✓ Include
├── static/                     ✓ Include
├── config_*.py                 ✓ Include
├── requirements.txt            ✓ Include
├── session_utils.py            ✓ Include (Updated)
├── usb_storage_manager.py      ✓ Include (New)
├── README.md                   ✓ Include
├── Dockerfile                  ✓ Include (Build artifact)
├── venv/                       ✓ Created during build
│   └── bin/python              (Dependencies installed here)
│
├── iteration_logs/             → MOUNT FROM USB/External
├── screenshots/                → MOUNT FROM USB/External  
├── logs/                       → MOUNT FROM USB/External
├── enhancement_output/         → MOUNT FROM USB/External
└── data/ (symlink)             → Points to mounted storage

❌ NOT Included:
- updated_code/
- SAM-CD-2GB/
- device_logs/
- captured_images/
- base_images/
- reference_screens/
- .git/
- *.log files
- *.bak files
```

---

## Expected Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Docker Image Size | 10-12GB | 400-500MB | **96% reduction** |
| Build Time | 15-20 min | 3-5 min | **75% faster** |
| Storage Needed | 10GB + app data | 500MB + USB data | **Decoupled** |
| Deployment | Large transfer | Quick + USB | **Flexible** |
| USB Auto-detection | ❌ Limited | ✓ Automatic | **Better UX** |

---

## Next Actions

1. **Confirm approach** - Do you want to proceed with this optimization?
2. **Update storage configuration** - Implement USB manager
3. **Create optimized Dockerfile** - Exclude data directories
4. **Test on R-PI** - Verify USB auto-detection
5. **Create deployment guide** - Document USB setup on R-PI

Would you like me to proceed with implementation?
