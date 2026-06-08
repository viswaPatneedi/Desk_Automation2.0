# Maintenance > DeepSleep > Wakeup - Optional DeepSleep Feature

## 🎯 Feature Overview

The method now supports **optional DeepSleep & Wakeup phases**. Users can choose to:

### **Option A: Full Workflow** (Default)
```
Maintenance Cycle (steps 1-7) + DeepSleep & Wakeup (steps 8-12)
Total: 60-95 minutes
```

### **Option B: Maintenance Only** (New)
```
Maintenance Cycle (steps 1-7) ONLY
Total: ~45-65 minutes
Stops after maintenance completion, device remains in STANDBY
```

---

## 🔧 How to Use

### **Method 1: Queue Parameter** (Recommended for UI)

```python
# Option A: Full workflow (default)
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY",
        "sleep_duration_minutes": 60,
        "execute_deepsleep_wakeup": True  # ← Include deep sleep & wake-up
    }
]

# Option B: Maintenance only (skip deep sleep & wake-up)
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY",
        "execute_deepsleep_wakeup": False  # ← Skip deep sleep & wake-up
    }
]

# Option C: Default (if parameter not specified)
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY"
        # execute_deepsleep_wakeup defaults to True
    }
]

test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=1
)
```

### **Method 2: Direct Function Call**

```python
from method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process

# Full workflow
result = execute_maintenance_deepsleep_wakeup_process(
    device_ip="10.0.0.126",
    port=10022,
    username="root",
    password="skypass",
    device_name="SKY-Device-1",
    remote_type="SKY",
    execute_deepsleep_wakeup=True  # ← Full workflow
)

# Maintenance only
result = execute_maintenance_deepsleep_wakeup_process(
    device_ip="10.0.0.126",
    port=10022,
    username="root",
    password="skypass",
    device_name="SKY-Device-1",
    remote_type="SKY",
    execute_deepsleep_wakeup=False  # ← Skip deep sleep & wake-up
)

print(f"Success: {result['success']}")
print(f"Details: {result['details']}")
```

---

## 📊 Comparison

| Aspect | Full Workflow | Maintenance Only |
|--------|---------------|-----------------|
| **Execution Steps** | 1-12 (all steps) | 1-7 (maintenance cycle) |
| **Duration** | 60-95 min | ~45-65 min |
| **Includes DeepSleep** | ✅ Yes | ❌ No |
| **Includes Wake-up** | ✅ Yes (with timing) | ❌ No |
| **Final Device State** | ON (after wake-up) | STANDBY (after maintenance) |
| **wakeup_time_seconds** | Returns time (~30-60s) | Returns None |
| **Use Case** | Full device testing | Quick maintenance only |
| **Parameter Value** | `True` (default) | `False` |

---

## 🔑 Return Values

### Full Workflow (execute_deepsleep_wakeup=True)
```json
{
    "iteration": 1,
    "success": True,
    "wakeup_time_seconds": 45.3,
    "screenshots": ["before.png", "after.png"],
    "logs": ["maintenance_log.log"],
    "details": "Maintenance completed, DeepSleep verified, wakeup time: 45.3s"
}
```

### Maintenance Only (execute_deepsleep_wakeup=False)
```json
{
    "iteration": 1,
    "success": True,
    "wakeup_time_seconds": None,
    "screenshots": [],
    "logs": ["maintenance_log.log"],
    "details": "Maintenance cycle completed successfully. DeepSleep and wake-up phases skipped as requested."
}
```

---

## 📍 Steps Breakdown

### **Always Executed (Steps 1-7)**
```
✅ [1-2] Check & manage maintenance status (5 min)
✅ [3] Put device in STANDBY (1 min)
✅ [4-5] Start maintenance & poll (30-60 min)
✅ [6-7] Reboot & verify STANDBY (5 min)

Subtotal: ~45-65 minutes (device dependent)
```

### **Conditionally Executed (Steps 8-12)**
```
When execute_deepsleep_wakeup=True:
  ✅ [8-9] Wait for DeepSleep entry (15 min)
  ✅ [10] Verify DeepSleep (SSH test)
  ✅ [11-12] IR wake-up & measure time (30-60 sec)
  ✅ [13-14] Post-wakeup validation

When execute_deepsleep_wakeup=False:
  ⏭️  SKIPPED - Method returns after step 7
```

---

## 💡 Use Cases

### **Use Maintenance Only When:**
- ✅ You only need to run device firmware maintenance
- ✅ You want faster execution (skip 15-minute wait)
- ✅ You don't need to test deep sleep functionality
- ✅ Device will remain in standby for other operations
- ✅ You want to manually test wake-up separately

### **Use Full Workflow When:**
- ✅ You need complete device validation
- ✅ You want to measure wake-up performance
- ✅ You need to verify deep sleep capability
- ✅ You're testing device recovery from deep sleep
- ✅ You need comprehensive device testing

---

## 🎨 UI/Execution Queue Configuration

### **For Execution Queue UI:**

```python
# Add to execution queue builder/UI
method_config = {
    "method": "maintenance_deepsleep_wakeup",
    "parameters": {
        "remote_type": {
            "type": "select",
            "options": ["XUMO", "SKY", "auto-detect"],
            "default": "auto-detect",
            "description": "IR remote type"
        },
        "sleep_duration_minutes": {
            "type": "number",
            "default": 60,
            "min": 10,
            "max": 600,
            "description": "DeepSleep duration"
        },
        "execute_deepsleep_wakeup": {
            "type": "checkbox",
            "default": True,
            "description": "Include DeepSleep & Wakeup phases (steps 8-12)",
            "shown_when": True
        }
    }
}
```

---

## 📋 Examples

### **Example 1: Maintenance Only (Quick Test)**
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "execute_deepsleep_wakeup": False  # Skip deep sleep
    }
]

result = test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=1
)
# Expected duration: ~50 minutes
# Final state: Device in STANDBY
```

### **Example 2: Full Workflow with Custom Timeout (Complete Test)**
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY",
        "sleep_duration_minutes": 120,  # 2 hours
        "execute_deepsleep_wakeup": True  # Include everything
    }
]

result = test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=1
)
# Expected duration: ~140 minutes
# Final state: Device ON (after wake-up)
```

### **Example 3: Sequence with Optional Deep Sleep**
```python
execution_queue = [
    {"method": "reboot"},  # Warmup
    {
        "method": "maintenance_deepsleep_wakeup",
        "execute_deepsleep_wakeup": False  # Maintenance only
    },
    {"method": "ir_test"}  # Post-maintenance validation
]

# Much faster to run this sequence without deep sleep wait
```

### **Example 4: Multiple Iterations with Toggle**
```python
# First run: maintenance only (quick check)
result1 = test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=[
        {"method": "maintenance_deepsleep_wakeup", "execute_deepsleep_wakeup": False}
    ],
    iterations=1
)

# Second run: full workflow (complete validation)
result2 = test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=[
        {"method": "maintenance_deepsleep_wakeup", "execute_deepsleep_wakeup": True}
    ],
    iterations=1
)

wakeup_time = result2.get('wakeup_time_seconds')  # Only available in full workflow
```

---

## 🚀 Implementation Details

### **What Happens When execute_deepsleep_wakeup=False:**

1. ✅ Steps 1-7 execute normally (maintenance cycle)
2. 🛑 After 2-minute reboot wait, method checks the flag
3. ⏭️  If False, method stops and returns success
4. 📝 Log message: "DeepSleep and wake-up phases skipped as requested"
5. 🔄 Device remains in STANDBY state
6. ⚡ Total execution: ~45-65 minutes instead of 60-95 minutes

### **Backward Compatibility:**

- Default value: `execute_deepsleep_wakeup=True`
- Existing code without parameter continues to work as before
- All 12 steps execute by default (unchanged behavior)

---

## 📚 Documentation Updates

When using this feature in UI or test sequences, include:

```
Parameter: execute_deepsleep_wakeup

Type: Boolean
Default: True
Required: No

Description:
  Controls whether to execute steps 8-12 (DeepSleep & Wakeup phases)
  - True: Full workflow (maintenance + deep sleep + wake-up)
  - False: Maintenance only (skip deep sleep & wake-up)

Impact:
  Duration: Saves ~15-20 minutes when False
  Final State: STANDBY (when False) vs ON (when True)
  Metrics: wakeup_time_seconds only available when True

Use Cases:
  False: Quick maintenance cycle, faster execution
  True: Complete device validation, wake-up testing
```

---

## 🔍 Log Output Examples

### **With execute_deepsleep_wakeup=True**
```
...
[STEP 7] Rebooting device after maintenance...
✓ Reboot response: {...}
Waiting 2 minutes for device to process reboot...

[STEP 8] Verifying device is in STANDBY after maintenance reboot...
✓ Device confirmed in STANDBY

[STEP 9] Waiting 15 minutes for device to enter DeepSleep...
...
```

### **With execute_deepsleep_wakeup=False**
```
...
[STEP 7] Rebooting device after maintenance...
✓ Reboot response: {...}
Waiting 2 minutes for device to process reboot...

================================================================================
[STEPS 8-12] DeepSleep & Wakeup SKIPPED (as requested)
================================================================================
✓ Maintenance cycle completed successfully
✓ Device remains in STANDBY state
⏭️  DeepSleep and wake-up phases skipped per user selection

================================================================================
MAINTENANCE CYCLE COMPLETED - DEEPSLEEP PHASES SKIPPED
================================================================================
```

---

## ✅ Validation Checklist

- [x] Parameter added to function signature
- [x] Parameter extracted from queue item with default value
- [x] Conditional logic implemented after step 7
- [x] Early return with success status when skipped
- [x] Log messages updated to show skip reason
- [x] Return values correctly handle None for wakeup_time_seconds
- [x] Backward compatibility maintained
- [x] Syntax validation passed
- [x] Service handler updated
- [x] Documentation provided

---

## 🎯 Summary

**Feature**: Optional Deep Sleep & Wake-up Phases  
**Parameter**: `execute_deepsleep_wakeup` (boolean, default True)  
**Benefit**: Allows users to choose between maintenance-only or full workflow  
**Time Saved**: ~15-20 minutes when skipping phases  
**Status**: ✅ Ready to use

---

**Implementation Date**: 2026-04-14  
**Status**: Complete & Validated
