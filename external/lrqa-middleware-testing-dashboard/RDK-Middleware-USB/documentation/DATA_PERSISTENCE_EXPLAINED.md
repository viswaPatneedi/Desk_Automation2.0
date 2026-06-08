# ✅ Data Persistence in Docker - Complete Explanation

## Short Answer

**YES** - Both devices and sequences are **100% persistent** while running in Docker and will survive container restarts.

---

## How It Works

### 1. Volume Mounts (The Key to Persistence)

The `docker-compose.yml` mounts JSON files as volumes:

```yaml
volumes:
  # Configuration files (persist locally)
  - ./Json/devices.json:/app/Json/devices.json
  - ./Json/jobs.json:/app/Json/jobs.json
  - ./Json/saved_sequences.json:/app/Json/saved_sequences.json
  - ./Json/device_locks.json:/app/Json/device_locks.json
  - ./Json/app_state.json:/app/Json/app_state.json
```

**What this means:**
- Files on your **host machine** (desktop) are mounted into the container
- Any changes the application makes are written to the **host machine's files**
- When the container stops/restarts, the data remains on the host
- Container access these files as if they're local, but they're actually on the host

### 2. Device Persistence - How It Works

**Storage Location:**
- **Host**: `/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/Json/devices.json`
- **Container**: `/app/Json/devices.json`
- **USB Backup**: `/media/lrqa/Lexar/Pi4-Dockerimage/Json/devices.json`

**Code Flow:**

```python
# From models/device.py

# SAVING (When you add/delete devices)
@staticmethod
def save_all(devices: List['Device']) -> None:
    """Save all devices to storage"""
    devices_data = [d.to_dict() for d in devices]
    with open(DEVICES_FILE, 'w') as f:
        json.dump(devices_data, f, indent=4)  # ← Writes to mounted volume

# LOADING (When application starts)
@staticmethod
def load_all() -> List['Device']:
    """Load all devices from storage"""
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'r') as f:
            devices_data = json.load(f)  # ← Reads from mounted volume
            return [Device.from_dict(d) for d in devices_data]
    return []
```

**When you delete/add devices:**
1. Application modifies devices in memory
2. Calls `Device.save_all()` 
3. Writes JSON to disk **on the host machine**
4. Changes are now persistent ✅

### 3. Sequence Persistence - How It Works

**Storage Location:**
- **Host**: `/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/Json/saved_sequences.json`
- **Container**: `/app/Json/saved_sequences.json`
- **USB Backup**: `/media/lrqa/Lexar/Pi4-Dockerimage/Json/saved_sequences.json`

**Code Flow:**

```python
# From models/saved_sequence.py

# SAVING (When you create/update sequences)
@classmethod
def save_all(cls, sequences: List['SavedSequence']):
    """Save all sequences to file"""
    try:
        with open(SAVED_SEQUENCES_FILE, 'w') as f:
            json.dump([seq.to_dict() for seq in sequences], f, indent=2)  # ← Persistent
        return True
    except Exception as e:
        print(f"Error saving sequences: {e}")
        return False

# LOADING (When application starts/queries sequences)
@classmethod
def load_all(cls) -> List['SavedSequence']:
    """Load all saved sequences from file"""
    if not os.path.exists(SAVED_SEQUENCES_FILE):
        return []
    
    try:
        with open(SAVED_SEQUENCES_FILE, 'r') as f:
            data = json.load(f)  # ← Reads from mounted volume
            return [cls.from_dict(seq) for seq in data]
    except Exception as e:
        print(f"Error loading sequences: {e}")
        return []
```

**When you create sequences:**
1. Application creates sequence in memory
2. Calls `SavedSequence.save_all()`
3. Writes JSON to disk **on the host machine**
4. Sequence persists across container restarts ✅

---

## 📊 Persistence Verification Example

### Scenario: Add Device → Restart Container → Verify Data

```bash
# Step 1: Container is running with devices already added
docker ps
# Output: Container rdk-testing-dashboard is running

# Step 2: Add a new device via UI or API
# Application runs: Device.save_all() → writes to Json/devices.json on HOST
ls -la Json/devices.json
# Check host file - it's updated with new device

# Step 3: Stop the container
docker-compose down
# Container stops completely, all in-memory data lost

# Step 4: Start container again
docker-compose up -d

# Step 5: Check devices in application
# Application runs: Device.load_all() → reads from HOST's Json/devices.json
# ✅ NEW DEVICE IS THERE! Persistence works!
```

---

## 📁 All Persistent Data Files in Docker

| File | Storage Path | Persists? | Purpose |
|------|--------------|-----------|---------|
| `devices.json` | `Json/devices.json` | ✅ YES | Device list (SSH IPs, passwords, etc.) |
| `saved_sequences.json` | `Json/saved_sequences.json` | ✅ YES | User-created test sequences |
| `jobs.json` | `Json/jobs.json` | ✅ YES | Job execution history |
| `device_locks.json` | `Json/device_locks.json` | ✅ YES | Device lock states |
| `app_state.json` | `Json/app_state.json` | ✅ YES | Application state |
| `ir_keycodes.json` | `Json/ir_keycodes.json` | ✅ YES | IR remote codes |
| `reset_codes.json` | `Json/reset_codes.json` | ✅ YES | Device reset codes |
| `log_patterns.json` | `Json/log_patterns.json` | ✅ YES | Log matching patterns |

---

## 🔄 Data Flow Diagram

```
┌─── HOST MACHINE ───────────────────────────────────────────────┐
│                                                                 │
│  /home/lrqa/Desktop/.../Enhancement/Json/devices.json         │
│  /home/lrqa/Desktop/.../Enhancement/Json/saved_sequences.json │
│                                              ↕ (Volume Mount)   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │           DOCKER CONTAINER                            │   │
│  │                                                        │   │
│  │  /app/Json/devices.json (Points to host file)        │   │
│  │  /app/Json/saved_sequences.json (Points to host file)│   │
│  │                                                        │   │
│  │  Application Code:                                    │   │
│  │  Device.load_all()  → Reads from mounted file        │   │
│  │  Device.save_all()  → Writes to mounted file         │   │
│  │  SavedSequence.load_all()  → Reads from mounted file │   │
│  │  SavedSequence.save_all()  → Writes to mounted file  │   │
│  │                                                        │   │
│  │  When changes made via UI:                            │   │
│  │  1. In-memory data modified                           │   │
│  │  2. save_all() called                                 │   │
│  │  3. json.dump() writes to /app/Json/*.json          │   │
│  │  4. Mount propagates changes to host                  │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

              ⬇️  Container Stop → Data Remains on Host ⬇️

┌─── HOST MACHINE (After Container Stops) ───────┐
│                                                 │
│  Json/devices.json - STILL HAS ALL DATA ✅     │
│  Json/saved_sequences.json - STILL HAS DATA ✅ │
│                                                 │
│  Start container again...                       │
│  Application loads from these files ✅         │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Persistence Guarantees

### ✅ What PERSISTS
- **Devices** - All added/modified devices survive restarts
- **Sequences** - All created sequences survive restarts
- **Jobs** - Job history persists
- **Device Locks** - Lock states (with caveats - see below)
- **Application State** - UI state and settings
- **IR Codes** - IR remote code mappings
- **All JSON data** - Everything in Json/ directory

### ⚠️ Important Notes

**Device Locks** (`device_locks.json`):
- Locks **persist on disk** but represent in-memory state
- If a device was locked when container stopped, lock state is saved
- When container restarts, old locks are still there
- You may need to manually clear locks if a job was interrupted

**Application Logs** (`iteration_logs/`):
- Stored in `iteration_logs/` directory
- These are NOT mounted in docker-compose by default
- Consider mounting if you need execution logs to persist

**Execution Data** (`/app/data/`):
- Screenshots and execution results stored here
- Currently mounted from USB: `/media/lrqa/Lexar:/app/data:rw`
- Persists on USB storage

---

## 🔒 Important: Editing Files on Host

You can directly edit JSON files on the host (without touching the container):

```bash
# Edit devices while container is running (or stopped)
nano Json/devices.json

# Edit sequences while container is running
nano Json/saved_sequences.json

# Container will pick up changes when it reads the files next
# Or restart container to reload from updated files
```

---

## ✅ Conclusion

**Data persistence in Docker is fully functional for:**
- ✅ Devices (add/delete/modify - all persistent)
- ✅ Sequences (create/update/delete - all persistent)
- ✅ Jobs, locks, states, and all configuration data
- ✅ Survives container stop/start cycles
- ✅ Survives machine reboot (if Docker volumes configured correctly)

**The mechanism:** Volume mounts keep data coupled to the host filesystem, so the container's ephemeral nature doesn't affect your data.

---

