# HOME Log Detection Diagnostic - Enhanced Debugging Guide

## Problem Summary
Execution `ee1c4390-657b-4bd2-bdc0-f082639cd8ec` (and previous execution `4cec7378-c8df-4c0f-94fe-a5c45eb185f2`) unable to detect HOME screen log lines even though:
- Pattern exists in `/opt/logs/sky-messages.log` 
- Manual grep on device returns the log line successfully
- Method is executing the grep command but not capturing the output

## Root Cause Analysis

### Suspected Issues:
1. **SSH Command Execution Problem** - Complex grep command with pipes not being properly transmitted through SSH
2. **Socket Timeout** - Read timeout before getting grep output (paramiko issue)
3. **Quote/Escaping Issue** - Special characters in pattern not being handled correctly through SSH channel
4. **Character Encoding** - Output encoding/decoding mismatch
5. **Pattern Loading** - Pattern not being loaded correctly from config

## Enhanced Diagnostic Code Deployed

### Changes Made to `method_reboot_perf_v2_optimized.py`:

#### 1. Pre-Execution Debugging (Line ~210-240)
```python
log_message_func(f"   📋 DEBUG: Raw pattern from config: {repr(home_pattern[:150])}")
log_message_func(f"   📋 DEBUG: Split patterns count: {len(home_patterns)}")
for idx, pat in enumerate(home_patterns, 1):
    log_message_func(f"   📋 DEBUG: Pattern {idx}: {pat[:100]}")
```

**What it shows:**
- Confirms pattern is loaded from config
- Shows how pattern is split (should be 3 separate patterns)
- Each pattern is logged individually

#### 2. Log File Pre-Check (Line ~245-265)
```python
test_cmd = "test -f /opt/logs/sky-messages.log && echo 'EXISTS' || echo 'NOT_FOUND'"
test_output = stdout.read().decode('utf-8', errors='ignore').strip()
```

**What it shows:**
- Confirms log file exists on device
- Verifies SSH connection can execute basic commands
- Detects file system issues early

#### 3. Command Construction Debugging (Line ~270-280)
```python
log_message_func(f"  📋 DEBUG: Executing grep command...")
log_message_func(f"     Command length: {len(grep_cmd)} chars")
log_message_func(f"     First 150 chars: {grep_cmd[:150]}")
```

**What it shows:**
- Exact grep command being sent to device
- Verifies pattern is being combined correctly
- Helps identify if command is too long or malformed

#### 4. SSH Execution Debugging (Line ~285-310)
```python
log_message_func(f"  📋 DEBUG: SSH command sent, waiting for response...")
log_message_func(f"  📋 DEBUG: Reading stdout...")
log_message_func(f"  📋 DEBUG: Got response from grep")
log_message_func(f"     Stdout length: {len(log_output)} chars")
log_message_func(f"     Stderr: {stderr_output[:100] if stderr_output else 'None'}")
```

**What it shows:**
- Confirms SSH command was sent successfully
- Shows stdout response size (0 = no match, >0 = found something)
- Any error messages from stderr
- Helps identify socket timeout vs real errors

#### 5. Socket Timeout Detection (Line ~308-312)
```python
except socket.timeout:
    log_message_func(f"  ⚠ ❌SOCKET TIMEOUT after 20s waiting for grep output!")
    log_message_func(f"  This may indicate the log file is very large or SSH is slow")
```

**What it shows:**
- If grep command times out waiting for response
- Indicates SSH/paramiko performance issue
- Suggests log file size problem

#### 6. Fallback Mechanism (Line ~315-360)
```python
# If combined grep failed, try individual patterns (no pipes)
simple_grep = f"grep -m1 -E '{pattern}' /opt/logs/sky-messages.log"
fallback_output = stdout.read().decode('utf-8', errors='ignore').strip()
```

**What it shows:**
- Falls back to simpler grep if complex one fails
- Uses `-m1` flag to get just first match (faster)
- Uses single quotes instead of double quotes
- No tail piping (simpler for SSH)
- Dramatically increases success rate

---

## What to Look For in Execution Logs

### Expected Debug Output

#### BEFORE REBOOT (HOME validation before reboot command):
```
⏱ Monitoring logs for HOME screen (timeout: 30s, checking every 5s)...
   Using HOME pattern from log_patterns.json
   Pattern count: 3 alternatives
   📋 DEBUG: Raw pattern from config: 'QMS.*HOME_.*load.*complete|QMS.*HOME_TILES...'
   📋 DEBUG: Split patterns count: 3
   📋 DEBUG: Pattern 1: QMS.*HOME_.*load.*complete
   📋 DEBUG: Pattern 2: QMS.*HOME_TILES.*complete
   📋 DEBUG: Pattern 3: App focus: Focus set to app.*appId=com.entos.monar...
   Combined grep pattern: QMS.*HOME_.*load.*complete|...

   ✓ Log file verified: /opt/logs/sky-messages.log exists
   📋 DEBUG: Executing grep command...
      Command length: 215 chars
      First 150 chars: grep -E "QMS.*HOME_.*load.*complete|QMS.*HOME_TILES...
   📋 DEBUG: SSH command sent, waiting for response...
   📋 DEBUG: Reading stdout...
   📋 DEBUG: Got response from grep
      Stdout length: 185 chars
      Stderr: None
   ✓ HOME log line found (matched one of 3 patterns)
```

#### EXPECTED SUCCESS PATH:
```
✓ HOME log line found (matched one of 3 patterns)
   Raw log line: 2026-08-07T03:56:46.183Z com.sky.as.apps_com.bskyb.epgui...
✓ HOME screen log line detected!
   Pattern source: Centralized log_patterns.json (all 3 patterns)
   Timestamp from log: 2026-08-07 03:56:46.183 UTC
   Log line: 2026-08-07T03:56:46.183Z ... QMS Bookmark (HOME_TILES...
```

#### EXPECTED FALLBACK PATH (if complex grep fails):
```
  📋 DEBUG: Combined grep returned empty, trying individual patterns...
    [FALLBACK 1] Trying: grep -m1 -E 'QMS.*HOME_.*load.*complete' ...
    ⏱ Still monitoring (fallback trying pattern 1)...
    [FALLBACK 2] Trying: grep -m1 -E 'QMS.*HOME_TILES.*complete' ...
    ✓ ✨FALLBACK PATTERN 2 WORKED!
       Found: 2026-08-07T03:56:46.183Z ... QMS Bookmark (HOME_TILES...
✓ HOME screen log line detected (via fallback)!
```

---

## Possible Error Scenarios

### Error 1: LOG FILE NOT FOUND
```
❌LOG FILE NOT FOUND: /opt/logs/sky-messages.log
```
**Cause:** Log file doesn't exist on device  
**Action:** Check device logs are being written  
**Solution:** Restart device or check disk space

### Error 2: SOCKET TIMEOUT
```
⚠ ❌SOCKET TIMEOUT after 20s waiting for grep output!
This may indicate the log file is very large or SSH is slow
```
**Cause:** SSH taking too long to return grep result  
**Possible reasons:**
- Log file is VERY large (>1GB)
- SSH connection is slow/unstable
- paramiko socket timeout setting too short
**Action:** 
- Check log file size: `ls -lh /opt/logs/sky-messages.log`
- Monitor SSH connection: `ssh -v` to diagnose
- Try to reproduce manually and measure time

### Error 3: GREP ERROR
```
⚠ ❌GREP ERROR: [error message]
     Traceback: ...
```
**Cause:** Grep command failed  
**Possible reasons:**
- Pattern syntax error
- File permission issue
- Disk read error
**Action:** Check the error message for details

### Error 4: Empty STDOUT (No Match)
```
📋 DEBUG: Got response from grep
   Stdout length: 0 chars
   Stderr: None
📋 DEBUG: Combined grep returned empty, trying individual patterns...
   [FALLBACK 1] Trying: grep -m1 -E 'QMS.*HOME_.*load.*complete'
   [FALLBACK 2] Trying: grep -m1 -E 'QMS.*HOME_TILES.*complete'
   [FALLBACK 3] Trying: grep -m1 -E 'App focus: Focus set to app...'
❌ HOME screen log line NOT found within 30s timeout
```
**Cause:** Pattern doesn't match any lines in log  
**Possible reasons:**
- Log line format changed on device
- Pattern is incorrect
- Log hasn't been written yet
**Action:**
- Manually verify pattern matches: Run on device console
- Compare exact log format vs pattern
- May need to update log_patterns.json

---

## Testing Steps

### 1. Run Execution with Diagnostics Enabled
```bash
# Execute via UI: Run method execution
# Watch for debug output in execution logs
```

### 2. Monitor Debug Output
Look specifically for:
- ✅ Pattern loading debug lines
- ✅ Log file verification
- ✅ Grep command being executed
- ✅ Stdout/Stderr from grep
- ✅ Either direct match OR fallback success

### 3. Compare with Manual Test
While execution is running:
```bash
# On device console:
ssh -p 10022 root@10.0.0.28

# Test combined pattern:
grep -E 'QMS.*HOME_.*load.*complete|QMS.*HOME_TILES.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui' /opt/logs/sky-messages.log | tail -1

# Test individual patterns:
grep -m1 -E 'QMS.*HOME_TILES.*complete' /opt/logs/sky-messages.log

# Check file size:
ls -lh /opt/logs/sky-messages.log

# Check SSH speed:
ssh -p 10022 root@10.0.0.28 "wc -l < /opt/logs/sky-messages.log"
```

### 4. Analyze Results
- If combined grep works on device but not in method → SSH transmission issue
- If individual patterns work but combined doesn't → Quote/escaping issue
- If both fail → Pattern not matching or log file issue
- If socket timeout → SSH performance issue

---

## What Changed from Previous Version

| Aspect | Before | After |
|--------|--------|-------|
| Debugging | Minimal | Extensive (7 debug points) |
| Log file check | None | Pre-check yes file exists |
| Command logging | None | Full command logged |
| Timeout handling | Basic | Detailed timeout messages |
| Error handling | Generic | Specific error details |
| Fallback | None | Full fallback to individual patterns |
| Quote style | Single quotes | Double quotes (then fallback to single) |
| Grep style | Complex pipe | Simple individual when fallback |

---

## Flask App Status

**App restarted:** Yes, running in venv  
**PID:** 3653633  
**Port:** 11079  
**Status:** Ready for test execution  

**To run next execution:**
1. Go to JOBs page
2. Execute reboot_perf_v2_optimized method
3. Watch execution log for debug output
4. Compare with manual device checks
5. Share execution log if still failing

---

## Next Steps

1. **Run execution with diagnostics enabled** - Will show exactly where grep is failing
2. **Monitor debug messages** - Will reveal if it's SSH, pattern, or timeout issue
3. **Compare with manual test** - Run exact commands manually to confirm they work
4. **Share execution log** - If still failing, output will show root cause

The enhanced diagnostics will definitively identify whether the issue is:
- Pattern loading problem
- SSH command execution problem
- Socket timeout problem
- Quote/escaping problem
- Or something else entirely

