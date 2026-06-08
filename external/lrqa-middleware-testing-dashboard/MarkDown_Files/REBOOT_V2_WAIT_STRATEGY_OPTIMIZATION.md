# Reboot Performance V2 - Wait Strategy Optimization Analysis

## Current Implementation vs Proposed Optimized Approach

### **Problem Statement**

You've identified a critical gap in the current wait strategy:

**Current Flow - Potential Issue:**
```
T=0s:   Send reboot command
T=0s:   Close SSH connection
T=0-85s: HARD WAIT (no action, just waiting)
        ↳ If device comes back at T=70s with HOME log already written...
        ↳ We miss it because we're not checking yet!
T=85s:  Start SSH reconnection attempts
T=90s:  Finally get SSH connection
T=90s:  START monitoring for HOME log
        ↳ By this time, HOME log (written at T=72s) might be old/missed
```

**Risk Scenarios:**
1. ⚠️ Device boots faster than 85 seconds (some devices boot in 40-60s)
2. ⚠️ HOME log written during initial wait period (not monitored)
3. ⚠️ Increased timeout waiting for nothing
4. ⚠️ Lost log data if logs rotate/are pruned during wait

---

## Current Implementation (Lines 450-500)

```python
# STEP 2: SEND REBOOT COMMAND
reboot_start_time = datetime.now(timezone.utc)
stdin, stdout, stderr = ssh.exec_command(reboot_command)
ssh.close()
log_message("✓ Reboot command sent successfully")

# STEP 3: HARD WAIT 85 SECONDS
log_message(f"[STEP 3] Waiting 85 seconds for device to reboot...")
initial_wait = 85
for remaining in range(initial_wait, 0, -10):
    log_message(f"  ⏳ {remaining} seconds remaining...")
    time.sleep(10)

# STEP 4: SSH RECONNECTION
log_message("[STEP 4] Waiting for device to come back online...")
ssh = wait_for_device(device_ip, port, username, password)  # Up to ~90 seconds
if not ssh:
    return {"success": False}

# STEP 5: MONITOR LOGS FOR HOME
elapsed_since_reboot = time.time() - reboot_start_time.timestamp()
remaining_timeout = max(30, home_screen_timeout - elapsed_since_reboot)
home_found = check_for_home_log_continuously(ssh, timeout_seconds=int(remaining_timeout))
```

**Current Timing Breakdown:**
```
Phase               Duration        Total Elapsed    Action
─────────────────────────────────────────────────────────────
Reboot sent         1-2s            0-2s            Command execution
Hard wait (STEP 3)  85s            85s             Just waiting...
SSH attempts        0-90s          85-175s         Trying to connect
Log monitoring      Up to 180s     175-355s        Looking for HOME log

WORST CASE TOTAL: ~6 minutes for single iteration (too long!)
```

---

## **PROPOSED OPTIMIZED APPROACH**

### **Strategy: Intelligent Early Detection**

```python
# STEP 2: SEND REBOOT COMMAND (Same as before)
reboot_start_time = datetime.now(timezone.utc)
stdin, stdout, stderr = ssh.exec_command(reboot_command)
ssh.close()
log_message("✓ Reboot command sent at {reboot_start_time}")

# STEP 3: REDUCED INITIAL WAIT + ACTIVE SSH MONITORING
log_message("[STEP 3] Waiting 50 seconds + attempting early SSH reconnection...")
ssh_reconnected = False
initial_wait = 50
attempt_ssh_after = 30  # Start SSH attempts after 30 seconds

for elapsed in range(0, initial_wait, 5):
    if elapsed >= attempt_ssh_after and not ssh_reconnected:
        log_message(f"  [Device bootup phase] Attempting SSH connection...")
        try:
            test_ssh = paramiko.SSHClient()
            test_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            test_ssh.connect(device_ip, port=port, username=username, 
                           password=password, timeout=5)
            log_message(f"  ✓ Device came back online at {elapsed}s!")
            ssh_reconnected = True
            ssh = test_ssh
            break
        except Exception:
            log_message(f"  ⏳ Still waiting... ({elapsed}s elapsed)")
            time.sleep(5)
    else:
        log_message(f"  ⏳ {initial_wait - elapsed}s remaining in initial phase...")
        time.sleep(5)

# STEP 4: DYNAMIC SSH RECONNECTION (if not already done)
if not ssh_reconnected:
    log_message("[STEP 4] Extended SSH reconnection attempt (max 60 more seconds)...")
    ssh = wait_for_device(device_ip, port, username, password, 
                         timeout=60, log_callback=log_message)
    if not ssh:
        log_message("❌ Device did not come back online")
        return {"success": False}

log_message(f"✓ SSH connection established")

# STEP 5: IMMEDIATE LOG MONITORING (as soon as SSH is available)
elapsed_since_reboot = time.time() - reboot_start_time.timestamp()
remaining_timeout = max(30, home_screen_timeout - elapsed_since_reboot)

log_message(f"[STEP 5] Monitoring logs for HOME screen...")
log_message(f"  Device came back after: {elapsed_since_reboot:.0f}s")
log_message(f"  Remaining monitor time: {remaining_timeout:.0f}s")
home_found = check_for_home_log_continuously(ssh, timeout_seconds=int(remaining_timeout),
                                            reboot_start_time=reboot_start_time)
```

**Optimized Timing Breakdown:**
```
Phase                           Duration        Total Elapsed    Action
────────────────────────────────────────────────────────────────────
Reboot sent                     1-2s            0-2s            Command execution
Initial wait (reduced)          30-50s          30-50s          Waiting for device
├─ First 30s: Device bootup     30s             30s             No SSH attempts
└─ After 30s: Active probing    20s             50s             Try SSH every 5s
SSH reconnection (if needed)    0-60s           50-110s         Connect as soon as possible
Log monitoring                  10-180s         60-290s         Detect HOME log immediately
                                (depends on)

AVERAGE CASE TOTAL: ~2-3 minutes (50% reduction!)
BEST CASE TOTAL: ~60-80 seconds (if device boots fast)
WORST CASE TOTAL: ~4.5 minutes (still better than 6min)
```

---

## Comparison Table

| Metric | Current | Proposed | Benefit |
|--------|---------|----------|---------|
| **Hard Wait (min)** | 85s | 50s | -35s |
| **SSH Detection Starts** | After 85s | After 30s | -55s earlier |
| **Log Monitoring Starts** | 175-265s | 50-110s | Much earlier |
| **Fast Device (40s boot)** | 175s total | 90s total | **51% faster** |
| **Slow Device (120s boot)** | 265s total | 180s total | **32% faster** |
| **Log Data Loss Risk** | High (if boot < 85s) | Low (probing at 30s) | **Better coverage** |
| **Real-time Responsiveness** | Poor | Good | **More accurate** |

---

## Key Advantages of Proposed Approach

### 1. **Early HOME Log Detection** ✓
- Starts SSH reconnection probing at 30 seconds (not 85 seconds)
- Captures HOME logs written during boot phase
- No missed logs due to timing gaps

### 2. **Adaptive Wait Time** ✓
- Doesn't waste time on hard 85-second wait
- If device boots in 40s, detects it in 40s (not 85s)
- Scales based on actual device performance

### 3. **Better Performance Metrics** ✓
- More accurate reboot duration measurement
- Real HOME log timestamp (not missed)
- Matches actual user experience

### 4. **Reduced Total Test Duration** ✓
- Average test: 2-3 minutes (vs current 5-6 minutes)
- Faster test cycles
- Higher throughput for batch testing

### 5. **Robust Log Monitoring** ✓
- Monitoring starts immediately after SSH reconnect
- No gap between reconnection and log monitoring
- Catches first HOME log entry without delay

---

## Implementation Details

### **Modified wait_for_device() Function**
Current signature:
```python
def wait_for_device(device_ip, port, username, password, 
                   timeout=90, log_callback=None):
    # Try to connect for 'timeout' seconds
```

Enhanced signature:
```python
def wait_for_device(device_ip, port, username, password, 
                   timeout=90, log_callback=None, 
                   start_attempts_at=0):
    # start_attempts_at: Second at which to begin connection attempts
    # (0 = immediate, 30 = after 30s, etc.)
```

### **Key Code Changes Needed**

**File:** [method_reboot_performance_v2.py](method_reboot_performance_v2.py)

**Change 1: Reduce initial wait**
```python
# OLD (Line ~472)
initial_wait = 85
for remaining in range(initial_wait, 0, -10):
    time.sleep(10)

# NEW
initial_wait = 50
for remaining in range(initial_wait, 0, -5):
    time.sleep(5)
```

**Change 2: Start SSH probing earlier**
```python
# OLD (Line ~478)
ssh = wait_for_device(device_ip, port, username, password)

# NEW
ssh = wait_for_device(device_ip, port, username, password,
                     timeout=120,  # Extended to 50+70
                     start_attempts_at=30)  # Begin after 30s initial wait
```

**Change 3: Adjust log monitoring timeout**
```python
# OLD (Line ~491)
remaining_timeout = max(30, home_screen_timeout - elapsed_since_reboot)

# NEW (already handles this correctly)
# No change needed - automatically uses correct remaining time
```

---

## Real-World Scenario Analysis

### **Scenario 1: Fast Device (boots in 40 seconds)**

**Current Approach:**
```
T=0:    Reboot sent
T=0-85: Hard wait (wasting 45 seconds!)
T=85:   Start SSH attempts
T=90:   SSH connected (home log written at T=38 already!)
T=90:   Start monitoring logs
RESULT: HOME log written at T=38, but monitoring starts at T=90
        ⚠️ Potential miss if logs were pruned/rotated
```

**Proposed Approach:**
```
T=0:    Reboot sent
T=0-30: Initial wait
T=30:   Start SSH probing
T=40:   SSH connected! (catches device coming back)
T=40:   Start monitoring logs immediately
        HOME log detected at T=38-42 range
RESULT: ✓ Captures HOME log immediately
        ✓ Accurate 40-second reboot time
        ✓ Test complete in ~60 seconds
```

### **Scenario 2: Slow Device (boots in 120 seconds)**

**Current Approach:**
```
T=0:    Reboot sent
T=0-85: Hard wait
T=85:   Start SSH attempts
T=120:  SSH connected (home log written at T=115)
T=120:  Start monitoring logs
RESULT: HOME log at T=115 might be lost/old
        120-second reboot time recorded
        Test takes ~210 seconds
```

**Proposed Approach:**
```
T=0:    Reboot sent
T=0-50: Initial wait
T=50:   Start SSH probing every 5s
T=120:  SSH connected (after 70s probing)
T=120:  Start monitoring logs
        HOME log detected at T=115-125
RESULT: ✓ Catches HOME log
        ✓ Accurate 115-125 second timing
        ✓ Test complete in ~180 seconds (vs 210)
```

---

## Risks & Mitigation

### Risk 1: SSH Connection Dropped During Initial Boot
**Mitigation:** Already handled - `wait_for_device()` has retry logic
```python
ssh = wait_for_device(...)  # Keeps trying for 60 seconds
```

### Risk 2: Device Comes Back But Services Not Ready
**Mitigation:** Only log monitoring starts, not critical operations
```python
# SSH is up, but maybe some services still booting
# That's fine - we just monitor logs (read-only)
```

### Risk 3: Log Entries Written During Boot
**Mitigation:** We filter by `reboot_start_time` anyway
```python
if log_timestamp > reboot_start_time:
    # This log entry is AFTER reboot, valid ✓
```

### Risk 4: Early Reconnection Fails
**Mitigation:** Falls back to extended 60-second retry
```python
if not ssh_reconnected:
    # Continue with longer timeout
    ssh = wait_for_device(..., timeout=60)
```

---

## Recommended Implementation Priority

### **Phase 1: Low Risk (High Benefit)**
- ✅ Reduce initial hard wait from 85s to 50s
- ✅ Start SSH probing at 30s (not 85s)
- ✅ Keep everything else same
- **Benefit:** 30-40% faster execution, no logic changes

### **Phase 2: Medium Risk (Higher Benefit)**
- ✅ Implement adaptive wait based on actual reconnect time
- ✅ Adjust timeout dynamically
- ✅ Better logging of timing decisions
- **Benefit:** Further optimization, better visibility

### **Phase 3: Advanced (Requires Testing)**
- ✅ Machine learning to predict device boot time per device type
- ✅ Adjust wait times based on historical data
- ✅ Pre-boot device health checks
- **Benefit:** Predictive optimization

---

## Conclusion

Your observation is **spot-on**. The current 85-second hard wait is:
- ❌ Wasteful (doesn't adapt to actual device performance)
- ❌ Risky (might miss HOME logs written during boot)
- ❌ Slow (adds unnecessary delay to tests)

The proposed **intelligent early detection approach** would:
- ✅ Start SSH probing at 30 seconds (when device is actually booting)
- ✅ Capture HOME logs immediately when device comes online
- ✅ Reduce total test time by 30-50%
- ✅ Eliminate timing-related log loss
- ✅ Provide better accuracy for performance metrics

**Recommendation:** Implement Phase 1 first (minimal risk, high benefit). This involves just changing two numbers: `85` → `50` and adding SSH probing at 30-second mark.

Would you like me to create the implementation code for this optimization?
