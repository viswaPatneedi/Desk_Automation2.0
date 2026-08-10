# Shared R-Pi Direct Shell Implementation

## Overview

This implementation enables **multiple devices on the same R-Pi to execute tests SIMULTANEOUSLY** without port conflicts by using a single shared SSH connection to the R-Pi and executing device commands through it directly.

## Problem Solved

**Previous Issue:**
- When executing same methods on 2+ devices with same R-Pi
- Both devices tried to use same forwarded local ports (127.0.0.1:10022, 127.0.0.1:8090, etc.)
- First device: ✅ PASSED (got the ports)
- Second device: ❌ FAILED (ports already in use)

**New Solution:**
- One shared R-Pi SSH connection (actual R-Pi at 10.138.17.42)
- Each device connects through R-Pi using actual IPs (10.0.0.28, 10.0.0.140)
- NO local port conflicts (uses real device IPs, not localhost)
- Both devices execute SIMULTANEOUSLY

## Architecture

### 1. **New Service: GDFRPiDirectShellService**
**File:** `services/gdf_rpi_direct_shell_service.py`

Pure SSH-based approach (no port forwarding):
- Connects to R-Pi once: `ssh -p 60201 pi@10.138.17.42`
- Keeps connection alive for multiple device commands
- Each device SSH: `ssh -p 10022 root@10.0.0.28` (actual device IP)
- Supports multiple concurrent device executions

**Key Methods:**
- `connect()` - Establish R-Pi SSH connection
- `execute_device_command()` - Execute commands on device through R-Pi
- `disconnect()` - Close R-Pi connection
- `is_healthy()` - Check connection state

### 2. **Enhanced TestExecutionService**
**File:** `services/test_execution_service.py`

Added global shared R-Pi connection registry:

```python
_SHARED_RPI_CONNECTIONS = {}  # {rpi_key: {service, ref_count, job_ids, ...}}
_SHARED_RPI_LOCK = threading.RLock()
```

**New Functions:**
- `get_or_create_shared_rpi_connection()` - Get/create shared connection
- `release_shared_rpi_connection()` - Release reference (closes when ref_count=0)
- `check_devices_share_rpi()` - Detect if devices have same R-Pi credentials
- `get_shared_rpi_for_devices()` - Extract shared R-Pi config
- `_get_rpi_connection_key()` - Generate unique key per R-Pi

**Updated Methods:**
- `establish_tunnel_for_device()` - Three-tier tunnel strategy:
  1. Check for pre-created shared connection
  2. Wait for companion device tunnel
  3. Acquire exclusive tunnel

### 3. **Device Selection Logic**
**File:** `controllers/test_controller.py`

Added R-Pi sharing detection in `execute_test_multiple()`:

```python
devices_share_rpi = check_devices_share_rpi(devices)
if devices_share_rpi and shared_rpi_config:
    # Pre-create shared R-Pi connection
    success, conn_msg, rpi_service = get_or_create_shared_rpi_connection(
        rpi_config=shared_rpi_config,
        device_identifier="Group execution"
    )
```

**Logic:**
- When user selects multiple devices and clicks "Execute"
- System checks if all devices have same R-Pi credentials
- If yes: Creates ONE shared connection
- If no: Falls back to per-device connections

## Execution Flow

### Multiple Devices, Same R-Pi (10 devices on same R-Pi)

```
User selects 10 devices with same R-Pi, clicks "Execute"
        ↓
Controller receives request (POST /api/execute-multiple)
        ↓
Check if devices share R-Pi credentials
        ↓
YES! All 10 have: {rpi_ip: 10.138.17.42, rpi_port: 60201, rpi_username: pi}
        ↓
Create shared R-Pi connection (ONCE)
ssh -p 60201 pi@10.138.17.42 ← Connection stays open
        ↓
Create 10 job records (one per device)
        ↓
Execution starts for all 10 simultaneously:

Device 1             Device 2             ...  Device 10
  ↓                    ↓                        ↓
ssh -p 10022     ssh -p 10022           ssh -p 10022
root@10.0.0.28   root@10.0.0.29         root@10.0.0.37
(through R-Pi)   (through R-Pi)         (through R-Pi)
  ↓                    ↓                        ↓
[Method 1]      [Method 1]             [Method 1]
  ↓                    ↓                        ↓
[Result ✅]     [Result ✅]            [Result ✅]
    ↓                ↓                        ↓
   Execution complete - ALL PASSED (no conflicts!)
```

### Multiple Devices, Different R-Pis (5 on R-Pi A, 5 on R-Pi B)

```
Check devices:
- 5 devices have R-Pi A (10.138.17.42)
- 5 devices have R-Pi B (10.138.17.43)
        ↓
Create TWO separate groups
        ↓
Group A: Shared connection to R-Pi A
Group B: Shared connection to R-Pi B
        ↓
Both groups execute SIMULTANEOUSLY (independent R-Pis)
        ↓
All 10 devices running in parallel without conflicts!
```

## Reference Counting & Connection Lifecycle

```python
# When first device on R-Pi needs connection:
get_or_create_shared_rpi_connection(rpi_config)
→ service created
→ ref_count = 1
→ connection stays open

# When second device on same R-Pi needs connection:
get_or_create_shared_rpi_connection(rpi_config)
→ finds existing healthy connection
→ ref_count = 2
→ both devices share it

# When device execution completes:
release_shared_rpi_connection(rpi_config)
→ ref_count = 1
→ connection stays open (other device still using)

# When last device completes:
release_shared_rpi_connection(rpi_config)
→ ref_count = 0
→ connection closes
```

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Port Conflicts** | ❌ Yes - both devices fight for localhost ports | ✅ No - uses actual device IPs |
| **Simultaneous Execution** | ❌ One passes, one fails | ✅ Both pass - parallel execution |
| **R-Pi Connections** | Multiple (one per device) | One shared (multiple devices use it) |
| **Scalability** | Breaks with 2+ devices | Handles dozens of devices |
| **Detection** | Manual per request | Automatic when devices share R-Pi |

## Implementation Details

### Connection Key Generation
```python
def _get_rpi_connection_key(rpi_config):
    # Unique key based on R-Pi credentials
    # Devices with SAME credentials → SAME key → SHARE connection
    return f"{rpi_username}@{rpi_ip}:{rpi_port}"
```

### Health Checking
```python
def is_healthy(self):
    # Verify connection is still alive
    stdin, stdout, stderr = ssh_client.exec_command('echo "health check"')
    return exit_code == 0
```

### Thread Safety
```python
_SHARED_RPI_LOCK = threading.RLock()  # All operations are locked
# Prevents race conditions when multiple threads access shared connections
```

## Testing the Implementation

### Test Scenario 1: Single Device
```bash
POST /api/jobs/{job_id}/execute
# Uses direct R-Pi connection if available
# Falls back to original tunnel if not
```

### Test Scenario 2: Two Devices, Same R-Pi
```bash
POST /api/execute-multiple
Body: {
  "device_ips": ["10.0.0.28", "10.0.0.140"],
  "execution_queue": [{"method": "reboot", "ir_keys": ["HOME"]}],
  "iterations": 1
}
# Response: Both connected through SHARED R-Pi connection
# Result: ✅ Both pass simultaneously
```

### Test Scenario 3: Two Devices, Different R-Pis
```bash
POST /api/execute-multiple
Body: {
  "device_ips": ["10.0.0.28", "10.0.0.130"],  # Different R-Pis
  "execution_queue": [{"method": "reboot", "ir_keys": ["HOME"]}],
  "iterations": 1
}
# Response: Two separate shared connections created
# Result: ✅ Both pass (independent R-Pi connections)
```

## Backward Compatibility

✅ **Fully backward compatible:**
- Old port forwarding still works for single devices
- Existing code paths unchanged
- Only affects multi-device execution with shared R-Pi
- Graceful fallback if shared connection not available

## Monitoring & Debugging

### Check Shared Connections
```python
# In Python console
from services.test_execution_service import _SHARED_RPI_CONNECTIONS
print(_SHARED_RPI_CONNECTIONS)
# Output: {
#   "pi@10.138.17.42:60201": {
#     "service": <GDFRPiDirectShellService>,
#     "ref_count": 3,
#     "job_ids": {"job1", "job2", "job3"}
#   }
# }
```

### Log Output Example
```
✅ [MULTI-DEVICE] All 3 devices share R-Pi: 10.138.17.42
   Strategy: SHARED R-Pi CONNECTION (direct shell approach)
✅ [MULTI-DEVICE] Shared R-Pi connection established
📡 [SHARED-R-Pi] Created new shared connection to pi@10.138.17.42:60201
📡 [SHARED-R-Pi] Reusing existing connection to pi@10.138.17.42:60201 (ref_count: 2)
📡 [TUNNEL-STRATEGY] Found pre-created shared R-Pi connection - REUSING for parallel execution
✅ [R-Pi DIRECT] Executing on root@10.0.0.28:10022
✅ [R-Pi DIRECT] Executing on root@10.0.0.140:10022
```

## Files Modified

1. **NEW:** `services/gdf_rpi_direct_shell_service.py` (500+ lines)
   - New service class for direct R-Pi shell approach

2. **MODIFIED:** `services/test_execution_service.py`
   - Added shared R-Pi connection registry
   - Added helper functions for R-Pi sharing detection
   - Updated `establish_tunnel_for_device()` with three-tier strategy
   - Import of new service

3. **MODIFIED:** `controllers/test_controller.py`
   - Added R-Pi sharing detection in `execute_test_multiple()`
   - Pre-creates shared connection before job execution

## Future Enhancements

1. **Connection Pooling** - Limit max connections per R-Pi
2. **Automatic Reconnection** - Detect dead connections and recreate
3. **Connection Statistics** - Dashboard showing shared connections
4. **Timeout Handling** - Auto-close idle connections after X seconds
5. **Load Balancing** - Distribute devices across multiple R-Pis intelligently

## Conclusion

This implementation solves the **port contention problem** by:
- Detecting when devices share same R-Pi credentials
- Creating ONE shared SSH connection to R-Pi
- Routing all device commands through it
- Enabling true parallel execution without conflicts

**Result:** Multiple devices on same R-Pi can execute simultaneously without failures!
