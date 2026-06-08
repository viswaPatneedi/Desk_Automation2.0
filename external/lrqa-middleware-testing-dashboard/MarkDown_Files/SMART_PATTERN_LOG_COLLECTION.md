# Smart Pattern-Based Log Collection Feature

## Overview

The log collection feature has been enhanced to support **smart pattern-based collection**. Users can now specify custom regex patterns to search for in device logs, and when those patterns are found, device logs are automatically collected to `/media/app`.

## Key Features

### Pattern-Based Log Collection
Users can specify one or more regex patterns to search for in device logs:
- Example: `["process crashed", "ERROR", "CRASH", ".*process crash.*"]`
- When ANY pattern is found → Automatically collect device logs
- Useful for capturing logs when specific errors occur

### Use Cases

**Example 1: Crash Detection**
```
Pattern: "process crashed"
Command: grep -E ".*process crash.*" /opt/logs/core_log.txt
Result:  2026-02-01T05:58:11.485Z process crashed = rfcMgr
Action:  Automatically collect logs to /media/app
```

**Example 2: Multiple Error Patterns**
```
Patterns: ["CRASH", "ERROR", "FATAL", "segfault"]
Action:   Collect logs if ANY of these patterns found
```

**Example 3: No Patterns + Auto-Collect**
```
If no patterns specified but auto_collect_logs=True:
Action:   Collect logs when HOME screen is found (fallback)
```

## Implementation Details

### Method Signature

```python
def execute_reboot_perf_v2_optimized_process(
    ...,
    auto_collect_logs=False,
    log_search_patterns=None  # ← NEW PARAMETER
)
```

### Parameter Details

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `log_search_patterns` | list | None | Regex patterns to search for, e.g., `["process crashed", "ERROR"]` |
| `auto_collect_logs` | bool | False | If True and no patterns: collect when HOME found (fallback) |

### New Function: `check_and_collect_logs_for_patterns()`

```python
def check_and_collect_logs_for_patterns(
    ssh, 
    device_ip, 
    device_name, 
    iteration, 
    log_patterns,          # List of patterns to search
    log_message_func
):
    """
    Search device logs for specific patterns
    If any pattern found → automatically collect logs
    
    Returns: dict with:
        - 'found_patterns': List of patterns that matched
        - 'log_paths': List of collected log file paths
        - 'matched_lines': Sample lines from matched patterns
    """
```

### Execution Flow

```
Step 5.5: SMART LOG COLLECTION

├─ IF log_search_patterns specified:
│  └─ Search for patterns in /opt/logs/core_log.txt
│  └─ IF pattern found:
│     └─ Collect logs to /media/app
│     └─ Return collected log path
│  └─ IF no patterns found:
│     └─ Skip collection
│
├─ ELSE IF auto_collect_logs=True:
│  └─ Collect logs when HOME found (fallback)
│
└─ ELSE:
   └─ Skip collection
```

## Configuration

### Queue Item Structure

```json
{
  "method": "reboot_perf_v2_optimized",
  "optional_checks": { ... },
  "home_screen_timeout": 180,
  "auto_collect_logs": false,
  "log_search_patterns": [
    "process crashed",
    "ERROR",
    "CRASH"
  ]
}
```

## Execution Examples

### Example 1: Pattern Found - Auto-Collect

**Configuration:**
```json
{
  "log_search_patterns": ["process crashed"]
}
```

**Execution Output:**
```
[STEP 5.5] Pattern-based log collection...
  ✓ Pattern FOUND: 'process crashed'
     2026-02-01T05:58:11.485Z process crashed = rfcMgr

[LOG COLLECTION] Found 1 pattern(s) - Collecting device logs...

📋 Collecting device logs for iteration 42...
  ✓ /media/app directory ready
  ✓ Archive created on device
✓ Device logs successfully collected in /media/app
  File: /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz

[STEP 6] Calculating reboot performance time...
```

### Example 2: No Patterns - Use Auto-Collect Fallback

**Configuration:**
```json
{
  "log_search_patterns": [],
  "auto_collect_logs": true
}
```

**Execution Output:**
```
[STEP 5.5] Auto-collecting device logs (configured at method selection)...
✓ Logs available at: /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz

[STEP 6] Calculating reboot performance time...
```

### Example 3: Patterns Specified - No Match

**Configuration:**
```json
{
  "log_search_patterns": ["process crashed"]
}
```

**Execution Output:**
```
[STEP 5.5] Pattern-based log collection...
  ℹ No patterns found - skipping log collection

[STEP 6] Calculating reboot performance time...
```

### Example 4: Multiple Patterns - One Match

**Configuration:**
```json
{
  "log_search_patterns": [
    "process crashed",
    "FATAL ERROR",
    "segfault"
  ]
}
```

**Execution Output:**
```
[STEP 5.5] Pattern-based log collection...
  ✓ Pattern FOUND: 'process crashed'
     2026-02-01T05:58:11.485Z process crashed = rfcMgr
  ℹ Pattern 'FATAL ERROR' not found
  ℹ Pattern 'segfault' not found

[LOG COLLECTION] Found 1 pattern(s) - Collecting device logs...
✓ Device logs successfully collected in /media/app
  File: /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

## Priority Order

The log collection feature follows this priority:

1. **Pattern Search (Highest Priority)**
   - If `log_search_patterns` is specified and non-empty
   - Search for patterns in device logs
   - Collect logs if ANY pattern is found

2. **Auto-Collect Fallback**
   - If no patterns specified but `auto_collect_logs=True`
   - Collect logs when HOME screen is found

3. **No Collection**
   - If neither patterns specified nor auto-collect enabled
   - Skip collection entirely

## Pattern Examples

### Process Crash Detection
```json
"log_search_patterns": [
  ".*process crash.*",
  "process crashed"
]
```

### Error Detection
```json
"log_search_patterns": [
  "ERROR",
  "FATAL",
  "CRASH",
  "Exception"
]
```

### Timeout and Network Issues
```json
"log_search_patterns": [
  "timeout",
  "connection refused",
  "network unreachable"
]
```

### Memory Issues
```json
"log_search_patterns": [
  "out of memory",
  "OOM",
  "segmentation fault"
]
```

### Custom Application Errors
```json
"log_search_patterns": [
  "rfcMgr.*failed",
  "stbProv.*error",
  "dlmgr.*crash"
]
```

## Service Integration

### In test_execution_service.py

```python
# Extract log search patterns from queue_item
log_search_patterns = queue_item.get('log_search_patterns', [])

# Log configuration
if log_search_patterns and len(log_search_patterns) > 0:
    log_service.log(f"Pattern-based log collection: ENABLED")
    for pattern in log_search_patterns:
        log_service.log(f"  - Pattern: '{pattern}'")
elif auto_collect_logs:
    log_service.log("Auto-collect logs: ENABLED")
else:
    log_service.log("Log collection: DISABLED")

# Pass to method
method_result = execute_reboot_perf_v2_optimized_process(
    ...,
    log_search_patterns=log_search_patterns
)
```

## Log Search Behavior

### Search Location
- Primary: `/opt/logs/core_log.txt`
- Command: `grep -E 'pattern' /opt/logs/core_log.txt`
- Timeout: 15 seconds per pattern search
- Max Results: First 5 matches per pattern

### Pattern Format
- Supports regex patterns
- Case-sensitive by default
- Examples: `"process crashed"`, `".*ERROR.*"`, `"CRASH"`

### Search Output
- Displays pattern match status
- Shows sample lines (first 3 matches)
- Reports which patterns matched
- Collects logs if any pattern found

## Benefits

✅ **Targeted Log Collection**
- Only collect when relevant errors occur
- Reduce storage overhead
- Focus on problematic iterations

✅ **Flexible Patterns**
- Support multiple patterns
- User-defined error detection
- Easy to customize per test

✅ **Automatic**
- No manual intervention needed
- Works across all iterations
- Consistent behavior

✅ **Non-Blocking**
- Pattern search happens after HOME detection
- Doesn't interrupt test flow
- Graceful error handling

## Backward Compatibility

✅ **Fully Backward Compatible**

```python
# Old code without patterns still works
execute_reboot_perf_v2_optimized_process(
    ...,
    auto_collect_logs=True
    # log_search_patterns defaults to None
)

# Works with patterns
execute_reboot_perf_v2_optimized_process(
    ...,
    log_search_patterns=["process crashed"]
)

# Works with both
execute_reboot_perf_v2_optimized_process(
    ...,
    auto_collect_logs=True,
    log_search_patterns=["ERROR"]
    # Patterns take priority, auto-collect is fallback
)
```

## Testing Checklist

- [x] Function `check_and_collect_logs_for_patterns()` implemented
- [x] Pattern search logic implemented
- [x] Conditional log collection based on patterns
- [x] Fallback to auto-collect if no patterns match
- [x] Service integration updated
- [x] No syntax errors
- [x] Backward compatible
- [ ] Manual testing with actual device
- [ ] Test pattern matching works
- [ ] Test logs collected when pattern found
- [ ] Test no collection when pattern not found
- [ ] Test multiple patterns
- [ ] Test pattern with special characters

## Files Modified

1. **method_reboot_perf_v2_optimized.py**
   - Added: `check_and_collect_logs_for_patterns()` function
   - Updated: `execute_reboot_perf_v2_optimized_process()` signature
   - Updated: Step 5.5 logic with pattern-based collection
   - Updated: Docstring with new feature description

2. **services/test_execution_service.py**
   - Added: Pattern extraction from queue_item
   - Updated: Logging for pattern configuration
   - Updated: Method call with log_search_patterns parameter

## Migration Guide

### From Old to New

**Old (Auto-collect on HOME):**
```json
{
  "method": "reboot_perf_v2_optimized",
  "auto_collect_logs": true
}
```

**New (Pattern-based, same behavior):**
```json
{
  "method": "reboot_perf_v2_optimized",
  "auto_collect_logs": true,
  "log_search_patterns": []  // No patterns = fallback to auto-collect
}
```

**New (Pattern-based, targeted):**
```json
{
  "method": "reboot_perf_v2_optimized",
  "auto_collect_logs": false,
  "log_search_patterns": ["process crashed", "ERROR"]
}
```

## Summary

The Smart Pattern-Based Log Collection feature provides:
- **Flexibility**: Specify exactly which errors to capture
- **Efficiency**: Only collect logs when relevant issues occur
- **Automation**: Hands-off operation during batch testing
- **Compatibility**: Works with existing auto-collect feature
- **Control**: User-defined error detection patterns

