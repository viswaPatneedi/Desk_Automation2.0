# IR Command Test via Pi Tunnel - Unified Solution

## Executive Summary

**Current Situation:**
- IR commands sent directly to iTach IR blaster (10.0.0.12:4998)
- Works for devices on direct network access
- **FAILS** for devices accessed through R-Pi tunnels (DESK & LAB R-Pi)

**Problem:**
- When device is accessed via R-Pi tunnel, iTach is unreachable
- IR test method needs to route commands through R-Pi
- Multiple methods (`method_ir_test.py`, `method_gdf_ir_test.py`, etc.) have similar issues

**Solution Approach:**
Create **ONE centralized abstraction layer** (`IRCommandRouter`) that:
- Auto-detects connection type (direct vs R-Pi tunnel)
- Routes IR commands appropriately
- Works transparently across ALL methods
- No need to modify individual method files

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    All IR Test Methods                  │
│  (method_ir_test.py, method_gdf_ir_test.py, etc)       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  IRCommandRouter       │ ◄─── NEW ABSTRACTION LAYER
        │  (Centralized Logic)   │
        └────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
   ┌──────────────┐        ┌──────────────────┐
   │   Direct IR  │        │  Tunnel-based IR │
   │  Blaster via │        │  via R-Pi SSH    │
   │  Socket      │        │  (New)           │
   └──────────────┘        └──────────────────┘
        │                         │
        ▼                         ▼
    iTach 10.0.0.12           R-Pi SSH CLI
    Port 4998                 (sends IR through device)
```

---

## Current IR Flow (BROKEN for tunnel)

```
method_ir_test.py
   ↓
get_ir_config_for_device() [socket direct to iTach]
   ↓
send_ir_command(ir_code, itach_ip='10.0.0.12')
   ↓
❌ FAILS - iTach unreachable through R-Pi tunnel
```

---

## New IR Flow (CENTRALIZED SOLUTION)

```
method_ir_test.py
   ↓
IRCommandRouter.send_ir_command(
    ir_code=ir_code,
    device_ip=device_ip,
    rpi_config=rpi_config    ◄─── NEW: Pass R-Pi info
)
   ↓
IRCommandRouter (logic):
   ├─ Has rpi_config?
   │  ├─ YES → Use R-Pi tunnel method
   │  │        ssh root@device 'irtool send ...'
   │  └─ NO → Use direct socket method
   │          Direct to iTach 10.0.0.12:4998
   └─ Returns: True/False and logs result
```

---

## Implementation Plan

### 1. Create Centralized Router Service

**File:** `services/ir_command_router.py`

```python
class IRCommandRouter:
    """
    Unified IR command routing service for both direct and tunneled connections.
    
    Features:
    - Auto-detect connection type (direct vs R-Pi tunnel)
    - Route IR commands appropriately
    - Retry logic with detailed logging
    - Works across all methods without modification
    """
    
    @staticmethod
    def send_ir_command(
        ir_code,
        device_ip,
        device_name="Device",
        itach_ip='10.0.0.12',
        itach_port=4998,
        rpi_config=None,
        rpi_client=None,
        log_callback=None
    ):
        """
        Send IR command via optimal route:
        - If rpi_config provided → Use R-Pi tunnel method
        - Otherwise → Use direct socket method
        
        Args:
            ir_code (str): IR command code
            device_ip (str): Target device IP
            device_name (str): Device name for logging
            itach_ip (str): iTach server IP (default 10.0.0.12)
            itach_port (int): iTach server port (default 4998)
            rpi_config (dict): R-Pi configuration with ip, port, username, password
            rpi_client (paramiko.SSHClient): Existing SSH client (optional)
            log_callback (callable): Logging function
            
        Returns:
            dict: {
                'success': bool,
                'method': str ('direct' or 'tunnel'),
                'message': str,
                'attempted_at': str (timestamp)
            }
        """
```

### 2. Two Implementation Methods

#### Method A: Direct Socket (Existing - No R-Pi)
```python
def _send_ir_direct(ir_code, itach_ip, itach_port, log_callback):
    """Send IR via direct socket to iTach"""
    # Existing logic from config_ir_blaster.py
    # Note: Works only when device on same network as iTach
```

#### Method B: Tunnel-based (NEW - Via R-Pi)
```python
def _send_ir_via_tunnel(ir_code, device_ip, rpi_config, rpi_client, log_callback):
    """Send IR through R-Pi tunnel"""
    # Option 1: Generate IR command at runtime on device
    # Option 2: Use irtool/irblaster tool on device
    # Option 3: SSH to device and execute local IR tool
    
    # Flow:
    # 1. SSH into device (through R-Pi tunnel)
    # 2. Check if device has local IR command tool (irtool, etc.)
    # 3. Send IR command via that tool
    # 4. Return result
```

---

## Usage Examples

### Example 1: Direct Connection (No R-Pi)
```python
from services.ir_command_router import IRCommandRouter

# Send IR without R-Pi (existing behavior)
result = IRCommandRouter.send_ir_command(
    ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
    device_ip="10.0.0.95",
    device_name="CELLO-SKY"
    # rpi_config NOT provided → Uses direct socket
)
```

### Example 2: Tunnel Connection (Via R-Pi)
```python
from services.ir_command_router import IRCommandRouter

rpi_config = {
    'rpi_ip': '10.26.52.151',
    'rpi_port': 22,
    'rpi_username': 'lrqa',
    'rpi_password': 'Viswa123!'
}

# Send IR through R-Pi tunnel
result = IRCommandRouter.send_ir_command(
    ir_code="SEND_COMMAND DEVICE:39 ID:POWER",
    device_ip="10.0.0.95",
    device_name="CELLO-SKY",
    rpi_config=rpi_config  # ◄─── Enables tunnel routing
)

print(f"Success: {result['success']}")
print(f"Method: {result['method']}")
print(f"Message: {result['message']}")
```

### Example 3: Using Existing SSH Client
```python
# If already connected to R-Pi via SSH
import paramiko
from services.ir_command_router import IRCommandRouter

ssh_client = paramiko.SSHClient()
ssh_client.connect(...)

result = IRCommandRouter.send_ir_command(
    ir_code="SEND_COMMAND DEVICE:39 ID:HOME",
    device_ip="10.0.0.95",
    device_name="CELLO-SKY",
    rpi_config=rpi_config,
    rpi_client=ssh_client  # ◄─── Reuse existing connection
)
```

---

## Integration with Existing Methods

### No Changes Needed To:
✅ `method_ir_test.py` - Just pass `rpi_config` to send_ir_command()
✅ `method_gdf_ir_test.py` - Same approach
✅ All other IR methods - Single parameter addition

### Minimal Change Example:

**Before:**
```python
from config.config_ir_blaster import send_ir_command

success = send_ir_command(ir_code, itach_ip='10.0.0.12')
```

**After:**
```python
from services.ir_command_router import IRCommandRouter

result = IRCommandRouter.send_ir_command(
    ir_code=ir_code,
    device_ip=device_ip,
    device_name=device_name,
    rpi_config=rpi_config  # ◄─── Just add this
)
success = result['success']
```

---

## Technical Details

### Tunnel-Based IR Delivery Options

**Option 1: Device-side IR Tool (Recommended)**
```bash
# On device: Check if irtool exists
ssh root@10.0.0.95 "which irtool"

# If exists, send IR via device
ssh root@10.0.0.95 "irtool send DEVICE:39 ID:POWER"
```

**Option 2: R-Pi-side IR Relay**
```bash
# R-Pi acts as proxy and sends IR to iTach
ssh -p 22 lrqa@10.26.52.151 \
  "nc -w 1 10.0.0.12 4998 <<< 'SEND_COMMAND DEVICE:39 ID:POWER'"
```

**Option 3: Direct SSH Command**
```bash
# Send IR command directly on device filesystem
# (if device has /dev/ir or similar)
ssh root@10.0.0.95 "echo 'POWER' > /dev/ir"
```

---

## Implementation Steps

### Phase 1: Create Router Service (1-2 hours)
1. Create `services/ir_command_router.py`
2. Implement direct socket method (copy from existing)
3. Implement tunnel method with R-Pi SSH
4. Add comprehensive logging
5. Add unit tests

### Phase 2: Integration (1 hour)
1. Update `method_ir_test.py` to use router
2. Update `method_gdf_ir_test.py` to use router
3. Test with both connection types
4. Verify backward compatibility

### Phase 3: Optional Enhancements (1-2 hours)
1. Add connection pooling for R-Pi SSH
2. Add retry logic with exponential backoff
3. Add IR command caching
4. Performance optimization

---

## Error Handling

The router shall handle:
- ✅ R-Pi connection failures (fallback to direct)
- ✅ Device SSH failures (report error)
- ✅ iTach unreachable (report error)
- ✅ Timeout management (configurable)
- ✅ Partial failures (retry logic)

---

## Benefits of This Approach

### Without Centralization (BAD)
```
method_ir_test.py          ❌ Edit needed
method_gdf_ir_test.py      ❌ Edit needed
method_standby_ir.py       ❌ Edit needed
method_power_control.py    ❌ Edit needed
... (other IR methods)     ❌ Edit needed
Total: 6+ files to modify, DRY violation
```

### With Centralization (GOOD)
```
services/ir_command_router.py  ✅ Edit once (ONE file)
   ↑
   Uses: All IR methods
   No modification needed to calling methods
   
Result: Single source of truth, DRY compliant
```

---

## Testing Strategy

```python
test_ir_command_router.py:

1. test_ir_direct_socket()
   - Send to iTach via direct socket
   - Expected: Success or timeout

2. test_ir_via_rpi_tunnel()
   - Send through R-Pi SSH tunnel
   - Expected: Success or connection error

3. test_ir_fallback()
   - When R-Pi fails, fall back to direct
   - Expected: Attempt both methods

4. test_ir_with_cache()
   - Cache R-Pi connections for reuse
   - Expected: Reduced SSH handshakes

5. test_ir_timeout_handling()
   - Timeout scenarios
   - Expected: Graceful degradation
```

---

## Deployment Checklist

- [ ] Create `services/ir_command_router.py`
- [ ] Write unit tests
- [ ] Update method files (minimal changes)
- [ ] Update documentation
- [ ] Test with DESK R-Pi devices
- [ ] Test with LAB R-Pi devices
- [ ] Test backward compatibility
- [ ] Performance testing
- [ ] Merge to main branch

---

## Files to Create/Modify

### New Files
- `services/ir_command_router.py` (centralized router)
- `tests/unit/test_ir_command_router.py` (tests)

### Modified Files
- `methods/method_ir_test.py` (1-2 line change)
- `methods/method_gdf_ir_test.py` (1-2 line change)
- `methods/method_standby_deep_sleep_ir_control.py` (1-2 line change)
- Any other IR-related methods (similar 1-2 line changes)

### Unchanged Files
- `config/config_ir_blaster.py` (backward compatible)
- `methods/method_utils.py` (no change)

---

## Success Criteria

✅ IR commands work on direct devices (10.0.0.95, 10.0.0.166)
✅ IR commands work on tunnel devices via R-Pi
✅ No changes to method logic (only router call added)
✅ Backward compatible with existing code
✅ Single point of configuration/testing
✅ Clear logging of routing decisions

---

## Questions for Implementation

1. Should we cache R-Pi SSH connections?
2. What's the best retry strategy?
3. Should tunnel method take priority over direct?
4. How to handle mixed scenarios (R-Pi available but direct faster)?
5. Should we implement connection pooling?

**Recommendation:** Start with simple implementation, optimize later based on performance metrics.

---

**Status:** Ready for implementation  
**Estimated Effort:** 3-4 hours total  
**Priority:** HIGH (unlocks IR testing via Pi tunnels)
