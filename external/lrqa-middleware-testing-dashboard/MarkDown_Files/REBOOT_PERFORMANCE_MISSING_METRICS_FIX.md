# Reboot Performance Results Missing for PIONEER-UHD - Diagnosis & Fix Guide

## Issue Diagnosed

The PIONEER-UHD (10.0.0.110) device's reboot performance results show "-" (empty) for all iterations, even though:
- ✓ Logs are being collected
- ✓ Crash detection works
- ✗ Reboot time is missing
- ✗ Performance metrics not captured

## Root Causes Identified

### 1. **Missing `performance_seconds` in Error Returns** ✅ FIXED
The method wasn't including `performance_seconds` in failure scenarios:
- When HOME screen not detected (timeout)
- When an exception occurs during execution

**Status**: ✅ Fixed in [method_reboot_perf_v2_optimized.py](method_reboot_perf_v2_optimized.py)
- Added `"performance_seconds": reboot_duration` to failure case (line ~987)
- Added `"performance_seconds": None` to exception handler (line ~1086)

### 2. **Possible Causes for PIONEER-UHD Not Detecting HOME**

The real issue for PIONEER-UHD is likely that HOME screen is NOT being detected after reboot, causing it to fall into the failure case. Possible reasons:

#### A. Log Pattern Mismatch
The HOME detection pattern is:
```
"QMS Bookmark.*HOME_TILES.*load.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui"
```
Looking in: `/opt/logs/sky-messages.log`

**PIONEER-UHD** might have:
- Different log file location
- Different message format
- Missing the expected log entries entirely

#### B. Device Not Actually Reaching HOME
The device might be:
- Stuck on boot screen
- Network connectivity issues  
- Display/UI framework not loading
- Firmware-specific behavior

#### C. Log File Not Accessible
SSH command execution might be failing to retrieve logs from PIONEER-UHD.

## How to Diagnose

### Step 1: Check Execution Logs
```bash
# Find the latest PIONEER-UHD execution log
ls -lth logs/jobs/43f12778-7c1c-4663-ac41-3f206b44308c/
cat logs/jobs/43f12778-7c1c-4663-ac41-3f206b44308c/execution.log | grep -A20 "HOME screen"
```

### Step 2: Manually SSH to PIONEER-UHD and Check Logs
```bash
ssh -p 10022 root@10.0.0.110

# Check if log files exist
ls -lh /opt/logs/sky-messages.log
ls -lh /opt/logs/wpeframework.log
ls -lh /opt/logs/core_log.txt

# Search for HOME pattern manually
grep -i "HOME\|home" /opt/logs/sky-messages.log | head -20
grep -i "QMS.*Bookmark\|App focus" /opt/logs/sky-messages.log | tail -20
```

### Step 3: Check Available Log Files
```bash
# See what logs are available
find /opt/logs -type f -ls
find /var/log -type f -ls | head -20

# After a reboot, check what messages appear
cat /opt/logs/* | grep -i "boot\|home\|startup" | tail -50
```

## Implementation Changes Made

### File: `method_reboot_perf_v2_optimized.py`

#### Fix 1: Failure Case (Line ~987)
```python
# BEFORE:
return {
    "iteration": iteration,
    "screenshots": screenshots_list,
    "logs": logs_list,
    "success": False,
    "build_info": build_info,
    # ❌ Missing performance_seconds
    ...
}

# AFTER:
return {
    "iteration": iteration,
    "screenshots": screenshots_list,
    "logs": logs_list,
    "success": False,
    "performance_seconds": reboot_duration,  # ✅ Added
    "build_info": build_info,
    ...
}
```

#### Fix 2: Exception Handler (Line ~1086)
```python
# BEFORE:
except Exception as e:
    return {
        "iteration": iteration,
        "screenshots": screenshots_list,
        "logs": logs_list,
        "success": False,
        "build_info": build_info,
        # ❌ Missing performance_seconds
        ...
    }

# AFTER:
except Exception as e:
    return {
        "iteration": iteration,
        "screenshots": screenshots_list,
        "logs": logs_list,
        "success": False,
        "performance_seconds": None,  # ✅ Added
        "build_info": build_info,
        ...
    }
```

## Next Steps to Fix PIONEER-UHD

### Option 1: Add PIONEER-Specific Log Pattern (Recommended)

1. **Determine correct log pattern for PIONEER**
   - SSH to device after reboot
   - Examine actual HOME screen detection messages
   - Identify distinctive patterns

2. **Update log_patterns.json**
   ```json
   {
     "HOME": {
       "log_pattern": "PIONEER_PATTERN|existing_pattern",
       "file_path": "/opt/logs/sky-messages.log",
       "description": "Detects HOME on XUMO, SKY, Rogers-Xfinity, AND PIONEER devices"
     }
   }
   ```

3. **Re-run job with updated patterns**

### Option 2: Create Device-Specific Configuration

Create PIONEER-specific configuration:
```python
# config_device_patterns.py
DEVICE_LOG_PATTERNS = {
    'PIONEER': {
        'home_pattern': 'PIONEER_SPECIFIC_PATTERN',
        'log_file': '/var/log/pioneer_messages.log',
        'timestamp_format': 'YYYY-MM-DD HH:MM:SS'
    },
    'HISENSE': {
        'home_pattern': existing_pattern,
        ...
    }
}
```

### Option 3: Enhanced Log Detection

Add fallback detection methods:
1. Check multiple log files
2. Look for generic "boot complete" indicators
3. Use SSH command to verify device on HOME screen visually
4. Parse system uptime as fallback

## Test the Fix

### Re-run Job After Fix
```bash
# Trigger a new job run with PIONEER-UHD
curl -X POST http://localhost:5000/run_job \
  -H "Content-Type: application/json" \
  -d '{
    "sequence_name": "InputsRow_Check",
    "device_ip": "10.0.0.110",
    "iterations": 3
  }'
```

### Expected Results After Fix
- Performance times should start appearing (either actual values or None)
- If HOME is never detected: `-` stays, but now it's consistent behavior
- Logs should still show "Collected" status

## Files Modified
✅ [method_reboot_perf_v2_optimized.py](method_reboot_perf_v2_optimized.py)
- Line ~987: Added `performance_seconds` to failure return
- Line ~1086: Added `performance_seconds` to exception return

## Performance Metrics Data Structure

After fix, all results will include `performance_seconds`:
```python
{
    "success": True,
    "performance_seconds": 73.45,  # ✅ Now included always
    "build_info": {...}
}

{
    "success": False,
    "performance_seconds": None,   # ✅ Now included (was missing before)
    "build_info": {...}
}

{
    "success": False,
    "performance_seconds": None,   # ✅ Now included in exception cases too
    "build_info": {...}
}
```

## Related Files
- [config_log_patterns.py](config_log_patterns.py) - Log pattern definitions
- [log_patterns.json](log_patterns.json) - Actual patterns (configurable)
- [method_reboot_perf_v2_optimized.py](method_reboot_perf_v2_optimized.py) - Main reboot method

## Known Limitations

1. **Device-specific log formats not yet handled**
   - Each device type may have different log files/formats
   - Currently only checks sky-messages.log
   - PIONEER may need custom configuration

2. **No fallback detection methods**
   - If log doesn't contain expected message, performance = None
   - Could add screen-based detection as fallback
   - Could add system uptime-based approximation

## Recommendations

### Short-term (Apply now)
✅ Use the fixed version that includes performance_seconds in all cases

### Medium-term (Next sprint)
- Analyze PIONEER device logs to find HOME detection pattern
- Add PIONEER-specific configuration
- Test and verify performance measurement works

### Long-term (Architecture improvement)
- Implement device-specific configuration system
- Add multiple detection methods (logs, screen state, system checks)
- Create automated pattern discovery tool
- Build device capability matrix

---

**Status**: ✅ Ready for Testing  
**Fix Applied**: 2026-02-25  
**Affected Method**: `reboot_perf_v2_optimized`  
**Affected Devices**: PIONEER-UHD, any device where HOME detection fails
