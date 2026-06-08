# USB Path Handling in Docker - Hardcoded vs Dynamic Analysis

## 🎯 Short Answer

**MIXED IMPLEMENTATION:**
- ✅ **Application Code**: USB path is **DYNAMICALLY FETCHED** at runtime
- ⚠️  **Docker Compose**: USB path is **HARDCODED** in volume mounts

---

## 📊 Detailed Analysis

### 1️⃣ Docker Compose: HARDCODED Path ⚠️

**File**: `docker-compose.yml`

```yaml
volumes:
  # ❌ HARDCODED: USB path is fixed in config
  - /media/lrqa/Lexar:/app/data:rw
  
  # Fallback commented out
  # - ./Enhancement_output:/app/data:rw
```

**Issues with Hardcoded Approach:**
- ❌ Path `/media/lrqa/Lexar` only works on this specific machine
- ❌ If your USB mounts to `/media/pi/Lexar` or `/mnt/usb`, it won't work
- ❌ If user is different (`viswa-pi4` instead of `lrqa`), path breaks
- ❌ Won't work if USB is not plugged in - no fallback to local storage

**Solution:** Mount point could be parameterized using `.env` file or `docker-compose.override.yml`

---

### 2️⃣ Application Code: DYNAMICALLY DETECTED ✅

The application code **intelligently detects** USB location at runtime. This is much better design!

#### Function: `get_lexar_base_path()` in `method_utils.py`

```python
def get_lexar_base_path():
    """Resolve Lexar USB base path dynamically"""
    
    # Preferred locations to check
    candidates = []
    user = os.environ.get('USER') or ''
    
    # Add common explicit paths (case-sensitive variants)
    if user:
        candidates.append(os.path.join('/media', user, 'Lexar'))
        candidates.append(os.path.join('/media', user, 'lexar'))
    
    # Add system default paths
    candidates.append('/media/pi/Lexar')
    candidates.append('/media/pi/lexar')
    
    # Scan /media/* directories for any 'lexar' folder
    try:
        if os.path.isdir('/media'):
            for entry in os.listdir('/media'):
                entry_path = os.path.join('/media', entry)
                possible = os.path.join(entry_path, 'Lexar')
                possible_lower = os.path.join(entry_path, 'lexar')
                
                if os.path.exists(possible):
                    candidates.append(possible)
                if os.path.exists(possible_lower):
                    candidates.append(possible_lower)
                
                # Check child dirs for 'lexar' (case-insensitive)
                try:
                    for child in os.listdir(entry_path):
                        if 'lexar' in child.lower():
                            candidates.append(os.path.join(entry_path, child))
                except Exception:
                    pass
    except Exception:
        pass
    
    # Return FIRST existing candidate
    for base in candidates:
        try:
            if base and os.path.exists(base):
                return os.path.join(base, 'Enhancement_output')
        except Exception:
            continue
    
    # FALLBACK: Use local directory if USB not found
    return 'Enhancement_output'
```

**How It Works:**
1. Checks 10+ possible USB mount locations
2. Case-insensitive matching (Lexar, lexar, LEXAR, etc.)
3. User-specific paths (handles different Linux users)
4. Scans `/media/*/` for any directory with "lexar" in the name
5. ✅ **FALLS BACK TO LOCAL** if USB not found: `Enhancement_output/`

---

### 3️⃣ How Images & Execution Data Are Saved

#### Screenshots Path Construction

**Code** (in `method_utils.py`):
```python
def create_screenshot_folder(device_ip, device_name, iteration, phase, method_name=None, execution_timestamp=None):
    # Get USB base path (dynamically detected ✅)
    usb_base = get_lexar_base_path()
    
    # Build path structure
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Example result:
    # /media/lrqa/Lexar/Enhancement_output/2025-12-08/10-0-0-126_DEVICE-NAME/METHOD/ITR-1_20251208_143025/SCREENSHOTS
    
    screenshot_path = os.path.join(
        usb_base,           # Dynamically found ✅
        current_date,
        device_folder,
        method_folder,
        itr_dir_name,
        'SCREENSHOTS'
    )
```

#### Execution Logs Path Construction

**Code** (in `method_utils.py`):
```python
def create_execution_log_path(device_ip, device_name, iteration, method_name):
    # Get USB base path (dynamically detected ✅)
    usb_base = os.path.join(get_lexar_base_path(), "EXECUTION_LOGS")
    
    # Example result:
    # /media/lrqa/Lexar/Enhancement_output/EXECUTION_LOGS/2025-12-04/10-0-0-126_DEVICE-NAME/ITR-1/REBOOT_ITR_1.log
    
    log_path = os.path.join(
        usb_base,              # Dynamically found ✅
        current_date,
        device_folder,
        itr_dir_name,
        log_filename
    )
```

#### Flask App Screenshot Route

**Code** (in `app.py`):
```python
@app.route('/screenshots/<path:filename>')
def get_screenshot(filename):
    # Use dynamically detected USB path ✅
    from method_utils import get_lexar_base_path
    
    screenshot_folder = os.path.join(get_lexar_base_path(), 'screenshots')
    # Falls back to local if USB not found
    
    return send_file(full_path, mimetype='image/png')
```

---

## 📁 Directory Structure Created

When application runs, it creates:

```
/media/lrqa/Lexar/Enhancement_output/  (dynamically found base ✅)
├── EXECUTION_LOGS/
│   └── 2025-12-08/
│       └── 10-0-0-126_DEVICE-NAME/
│           ├── ITR-1/
│           │   ├── REBOOT_ITR_1.log
│           │   └── ...
│           └── ITR-2/
│
├── 2025-12-08/                        (Screenshot date folder)
│   └── 10-0-0-126_DEVICE-NAME/
│       ├── REBOOT/
│       │   ├── ITR-1_20251208_143025/
│       │   │   └── SCREENSHOTS/
│       │   │       ├── screenshot_001.png
│       │   │       └── ...
│       │   └── ITR-2_20251208_143045/
│       └── DEEPSLEEP/
│           └── ...
│
└── screenshots/                       (Legacy location)
    └── ...
```

---

## ⚠️ Current Issues & Solutions

### Issue 1: Docker Compose Hardcoded Path

**Problem:**
```yaml
- /media/lrqa/Lexar:/app/data:rw  # ❌ Hardcoded, breaks on different systems
```

**Solutions:**

**Option A: Use Environment Variable (Best)**
```yaml
volumes:
  - ${USB_PATH:-/media/lrqa/Lexar}:/app/data:rw
```

Then in `.env`:
```
USB_PATH=/media/lrqa/Lexar
```

Or on different system:
```
USB_PATH=/media/viswa-pi4/Lexar
```

**Option B: Create docker-compose.override.yml**
```yaml
version: '3.8'
services:
  web:
    volumes:
      - /media/viswa-pi4/Lexar:/app/data:rw  # Override for Pi
```

**Option C: Application Fallback**
The application **ALREADY HAS a fallback**, so even if USB not mounted, it will use local `Enhancement_output/` folder.

---

### Issue 2: Container-to-Host Path Mapping

**Current Issue:**
- Container's `/app/data` is mounted from host's USB
- But application code uses `get_lexar_base_path()` which returns **full host path**
- Inside container, these paths won't work!

**Example:**
```
Host: /media/lrqa/Lexar/Enhancement_output/screenshots
Container: /app/data/Enhancement_output/screenshots  (different!)
```

**Solution:** Two-part approach:

1. **Inside container** - Use container paths:
   ```python
   # In container, use /app/data directly
   screenshot_path = '/app/data/YYYY-MM-DD/DEVICE/ITR-1'
   ```

2. **Outside container** - Use host paths:
   ```python
   # On host, use detected USB path
   screenshot_path = get_lexar_base_path()
   ```

---

## 🔄 Data Flow in Docker Environment

```
┌─── HOST MACHINE ───────────────────────────────────┐
│                                                     │
│  /media/lrqa/Lexar/ (USB Mount Point)             │
│  ├── Enhancement_output/                          │
│  │   ├── EXECUTION_LOGS/                          │
│  │   ├── YYYY-MM-DD/                              │
│  │   └── screenshots/                             │
│  │                                                 │
│  ↓ VOLUME MOUNT                                   │
│                                                     │
│  ┌── DOCKER CONTAINER ───────────────────────┐    │
│  │                                            │    │
│  │  /app/data/ (mounted from host)           │    │
│  │  ├── EXECUTION_LOGS/ (same as host)       │    │
│  │  ├── YYYY-MM-DD/ (same as host)           │    │
│  │  └── screenshots/ (same as host)          │    │
│  │                                            │    │
│  │  Application Code:                        │    │
│  │  • get_lexar_base_path() called           │    │
│  │  • Returns: /media/lrqa/Lexar ⚠️          │    │
│  │    BUT INSIDE CONTAINER THIS IS WRONG!   │    │
│  │    Should be: /app/data                   │    │
│  │                                            │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## ✅ Recommendations

### 1. Fix Docker Compose (IMMEDIATE)

Test if USB path is actually working or if there's an issue:

```bash
# Check if container can access the volume
docker exec rdk-testing-dashboard ls -la /app/data

# Check if files are being created
find /media/lrqa/Lexar -name '*ITR*' | head -10
```

### 2. Improve Dynamic Path Detection (SHORT TERM)

Modify `get_lexar_base_path()` to also check `/app/data` when running in Docker:

```python
def get_lexar_base_path():
    # Inside Docker container - /app/data is the mounted volume
    if os.path.exists('/app/data'):
        return '/app/data'
    
    # Outside Docker - detect USB dynamically
    # ... existing logic ...
```

### 3. Parameterize docker-compose.yml (SHORT TERM)

```yaml
volumes:
  - ${USB_PATH:-$(pwd)/Enhancement_output}:/app/data:rw
```

### 4. Add .env Configuration File (BEST PRACTICE)

Create `.env` file:
```ini
# USB Mount Point (adjust for your system)
USB_PATH=/media/lrqa/Lexar

# Application Settings
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
```

Then docker-compose can reference it:
```yaml
volumes:
  - ${USB_PATH}:/app/data:rw
```

---

## 📋 Summary Table

| Aspect | Status | Location | Hardcoded? | Notes |
|--------|--------|----------|-----------|-------|
| **Docker Compose Mount** | ⚠️ Needs Fix | `docker-compose.yml` | ❌ YES - `/media/lrqa/Lexar` | Should use env variable |
| **USB Detection in Code** | ✅ Good | `method_utils.py` | ✅ NO - Dynamic + Fallback | Checks 10+ locations |
| **Screenshot Paths** | ✅ Dynamic | `method_utils.py:create_screenshot_folder()` | ✅ NO | Uses `get_lexar_base_path()` |
| **Log Paths** | ✅ Dynamic | `method_utils.py:create_execution_log_path()` | ✅ NO | Uses `get_lexar_base_path()` |
| **Flask Screenshot Route** | ✅ Dynamic | `app.py:@screenshots route` | ✅ NO | Uses `get_lexar_base_path()` |
| **Fallback for USB Missing** | ✅ YES | Code | ✅ YES | Falls back to `Enhancement_output/` |

---

## 🚀 Recommended Immediate Action

1. **Check if volume mount is working:**
   ```bash
   docker ps  # Get container ID
   docker exec <container-id> df -h  # Check mounts
   docker exec <container-id> ls -la /app/data  # Check USB contents
   ```

2. **If USB path wrong in docker-compose.yml, fix it:**
   ```bash
   # Edit docker-compose.yml
   sed -i 's|/media/lrqa/Lexar|/media/viswa-pi4/Lexar|g' docker-compose.yml
   
   # Restart container
   docker-compose down
   docker-compose up -d
   ```

3. **Verify images are being saved:**
   ```bash
   ls -la /media/lrqa/Lexar/Enhancement_output/screenshots/
   ls -la /media/lrqa/Lexar/Enhancement_output/EXECUTION_LOGS/
   ```

---

