# Auto-Collect Logs Feature - Updated Implementation

## Overview

The log collection feature for Reboot Performance V2 - Optimized has been updated to support **automatic log collection configured at method selection time** rather than prompting the user during each iteration.

## Key Changes

### From Interactive Prompts to Pre-Execution Configuration

**Old Approach (Removed)**:
- At Step 4.5 during each iteration, after HOME is found
- Prompted user: "Collect device logs? (yes/no)"
- User had to respond to each iteration

**New Approach (Implemented)**:
- Configuration happens at method selection time (before execution starts)
- No interactive prompts during iterations
- Automatically collects logs when HOME is found (if enabled)
- Set-and-forget approach - same for all iterations

## How It Works

### Step 1: Method Selection (Frontend/API)

When the user selects the `reboot_perf_v2_optimized` method, they can optionally enable:
- **Auto-collect logs**: Yes/No checkbox or option

This preference is stored in the `queue_item` object:

```json
{
  "method": "reboot_perf_v2_optimized",
  "optional_checks": { ... },
  "home_screen_timeout": 180,
  "auto_collect_logs": true  // ← NEW PARAMETER
}
```

### Step 2: Execution Configuration

The `test_execution_service.py` reads the `auto_collect_logs` parameter:

```python
auto_collect_logs = queue_item.get('auto_collect_logs', False)  # Default: False
```

And passes it to the method:

```python
method_result = execute_reboot_perf_v2_optimized_process(
    ...,
    auto_collect_logs=auto_collect_logs
)
```

### Step 3: Automatic Collection During Execution

At Step 4.5 (after HOME is found):

```python
if home_found:
    if auto_collect_logs:
        # Automatically collect logs (no prompt)
        collected_log_path = collect_device_logs_to_media_app(
            ssh, device_ip, device_name, iteration, log_message
        )
    else:
        # Skip collection
        log_message("Log collection not configured")
```

## Implementation Details

### Method Signature

```python
def execute_reboot_perf_v2_optimized_process(
    device_ip, 
    port, 
    username, 
    password, 
    iteration=1, 
    device_name="Device", 
    combined_method_name=None, 
    optional_checks=None, 
    wait_after_reboot=80, 
    home_screen_timeout=180,
    auto_collect_logs=False  # ← NEW PARAMETER
):
```

### Parameter Details

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `auto_collect_logs` | bool | False | If True, automatically collect device logs when HOME is found |

### Files Modified

#### 1. `method_reboot_perf_v2_optimized.py`

**Changes**:
- ✅ Removed `prompt_user_for_log_collection()` function
- ✅ Updated method signature to include `auto_collect_logs` parameter
- ✅ Updated docstring to reflect pre-execution configuration
- ✅ Replaced Step 4.5 interactive prompt with automatic collection
- ✅ Kept `collect_device_logs_to_media_app()` function (still needed)

**Line Changes**:
- Function definition: Lines ~220-260
- Step 4.5 logic: Lines ~705-715
- Docstring: Lines ~220-255

#### 2. `services/test_execution_service.py`

**Changes**:
- ✅ Extract `auto_collect_logs` from `queue_item`
- ✅ Log the configuration status
- ✅ Pass parameter to method

**Line Changes**:
- Parameter extraction: ~375 (added 1 line)
- Logging: ~408-410 (added 3 lines)
- Method call: ~415 (updated to include parameter)

## Execution Flow

```
┌─ USER SELECTS METHOD
│  └─ Selects: reboot_perf_v2_optimized
│  └─ Configures: auto_collect_logs = true/false
│  └─ Clicks: Start Execution
│
├─ EXECUTION STARTS
│  └─ test_execution_service reads auto_collect_logs from queue_item
│  └─ Passes to method (no more interactive prompts)
│
├─ DURING ITERATION
│  └─ Device reboots
│  └─ HOME screen detected
│  └─ IF auto_collect_logs=true:
│     └─ Automatically collect logs to /media/app
│  └─ Continue to next steps
│
└─ NO USER INTERACTION NEEDED
```

## Benefits

✅ **No Interruptions**
- Iterations run continuously
- No waiting for user input
- Ideal for batch/automated testing

✅ **Consistency**
- Same behavior for all iterations
- No per-iteration decisions needed

✅ **Efficiency**
- Set preference once at start
- Apply to entire job

✅ **Flexibility**
- Can enable or disable at method selection
- Default is disabled (opt-in)

## Log Collection Behavior

### When `auto_collect_logs=True`

**After HOME screen is detected**:
```
[STEP 4.5] Auto-collecting device logs (configured at method selection)...

📋 Collecting device logs for iteration 42...
  ✓ /media/app directory ready
  ✓ Archive created on device
✓ Device logs successfully collected in /media/app
  File: /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

### When `auto_collect_logs=False`

**After HOME screen is detected**:
```
[STEP 4.5] Log collection not configured (auto_collect_logs=False)

[STEP 5] Calculating reboot performance time...
```

## Usage Example

### Queue Item Structure

```json
{
  "execution_queue": [
    {
      "method": "reboot_perf_v2_optimized",
      "ir_keys": [],
      "voice_text": "",
      "optional_checks": {
        "custom_commands": [
          {
            "check_key": "crash",
            "description": "Check Crash"
          }
        ]
      },
      "home_screen_timeout": 180,
      "auto_collect_logs": true
    }
  ],
  "iterations": 150,
  "sequence_name": "Reboot Performance Test"
}
```

### Expected Behavior

1. User selects method with `auto_collect_logs: true`
2. Job starts execution
3. For each iteration:
   - Device reboots
   - HOME screen detected
   - Logs automatically collected (no prompt)
   - Test continues
4. After 150 iterations:
   - 150 log files collected (if all iterations found HOME)
   - All stored in `/media/app/`
   - No user interruption

## Configuration Location

### In Frontend (To Be Implemented)

The UI should add a checkbox or option when selecting the method:

```html
<input type="checkbox" name="auto_collect_logs" value="true">
  Auto-collect logs when HOME is found
</input>
```

### How It Gets Passed

1. Frontend collects the checkbox value
2. Includes in request JSON: `"auto_collect_logs": true`
3. API receives in `queue_item`
4. Stored in job's execution_queue
5. Read during execution

## Testing Checklist

- [x] Method signature updated
- [x] Parameter extraction in test_execution_service
- [x] Parameter passing to method
- [x] Step 4.5 logic updated
- [x] No syntax errors
- [x] Backward compatible (defaults to False)
- [ ] Manual testing with actual device
- [ ] Verify logs are collected automatically
- [ ] Verify no user prompts appear
- [ ] Test with auto_collect_logs=false (no collection)
- [ ] Test with auto_collect_logs=true (auto collection)
- [ ] Verify multiple iterations work correctly

## Backward Compatibility

✅ **Fully Backward Compatible**

- Old method calls without `auto_collect_logs` parameter will use default `False`
- Existing jobs continue to work unchanged
- Only new jobs with `auto_collect_logs=True` will trigger auto-collection

## Related Files

- Implementation: [method_reboot_perf_v2_optimized.py](method_reboot_perf_v2_optimized.py)
- Service Integration: [services/test_execution_service.py](services/test_execution_service.py)
- Log Collection: [collect_device_logs_to_media_app()](method_reboot_perf_v2_optimized.py#L237)
- Queue Structure: [models/job.py](models/job.py)

## Comparison: Old vs New

| Aspect | Old (Interactive) | New (Auto) |
|--------|-------------------|-----------|
| **When Configured** | During each iteration | Before execution starts |
| **User Action** | Type yes/no for each iteration | Single checkbox selection |
| **Iterations Block** | Yes (wait for input) | No (runs continuously) |
| **Ideal For** | Manual, exploratory testing | Batch, automated testing |
| **Log Coverage** | Variable (user decides each time) | Consistent (configured once) |
| **Batch Testing** | Not ideal (too many prompts) | Perfect (no interruptions) |

## Migration Guide

### For Existing Code

If you have code calling the method:

**Old Way** (still works, defaults to false):
```python
result = execute_reboot_perf_v2_optimized_process(
    device_ip, port, username, password,
    iteration, device_name,
    optional_checks=checks,
    home_screen_timeout=180
)
```

**New Way** (explicit auto-collection):
```python
result = execute_reboot_perf_v2_optimized_process(
    device_ip, port, username, password,
    iteration, device_name,
    optional_checks=checks,
    home_screen_timeout=180,
    auto_collect_logs=True  # ← Add this
)
```

## Summary

The log collection feature has been redesigned to:
1. Ask users **once** at method selection time
2. Automatically apply the preference **to all iterations**
3. Never prompt users **during execution**
4. Maintain logs organized in `/media/app/`

This approach is much more suitable for batch testing where you want to collect logs for all iterations without manual interruption.

