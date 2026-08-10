# Quick Reference: HOME Detection Debugging

## Changes Applied ✅

1. **Enhanced Pattern Logging** - Shows exactly how pattern is loaded and split
2. **Log File Pre-Check** - Verifies file exists before grepping
3. **Command Construction Logging** - Shows exact grep command being sent
4. **SSH Execution Debugging** - Tracks command sent/response received
5. **Socket Timeout Detection** - Specific timeout error messages
6. **Fallback Mechanism** - If complex grep fails, tries simpler individual patterns
7. **Detailed Error Reporting** - Full traceback for any errors

## What To Do Now

### Step 1️⃣: Run test execution
- Go to JOBs page
- Execute: `reboot_perf_v2_optimized`
- Device: Sky 10.0.0.28

### Step 2️⃣: Watch for debug output
Look in execution log for these key lines:

**Pattern Loading Section:**
```
📋 DEBUG: Raw pattern from config: 'QMS.*HOME_...'
📋 DEBUG: Split patterns count: 3
📋 DEBUG: Pattern 1: ... 
📋 DEBUG: Pattern 2: ...
📋 DEBUG: Pattern 3: ...
```

**File Check Section:**
```
✓ Log file verified: /opt/logs/sky-messages.log exists
```

**Grep Command Section:**
```
📋 DEBUG: Executing grep command...
   Command length: XXX chars
   First 150 chars: grep -E "QMS.*HOME...
📋 DEBUG: SSH command sent, waiting for response...
📋 DEBUG: Reading stdout...
📋 DEBUG: Got response from grep
   Stdout length: XXX chars  ← KEY: Should be > 0 if match found
   Stderr: None
```

**Result Section (ONE of these):**
```
✓ HOME log line found (matched one of 3 patterns)   ← SUCCESS
OR
✓ ✨FALLBACK PATTERN X WORKED!               ← SUCCESS (fallback)
OR
⚠ ❌SOCKET TIMEOUT after 20s                ← SOCKET ISSUE
OR
❌ HOME screen log line NOT found within Xs  ← PATTERN ISSUE
```

### Step 3️⃣: Share the execution ID
Once execution completes, share:
- **Execution ID:** (shown in JOBs as UUID)
- **Key debug lines** from execution log
- **Status:** Whether it succeeded or failed

### Step 4️⃣: Optional - Manual verification while execution runs
On device console during execution:

```bash
# Connect to device
ssh -p 10022 root@10.0.0.28

# Test combined pattern (what method tries):
time grep -E 'QMS.*HOME_.*load.*complete|QMS.*HOME_TILES.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui' /opt/logs/sky-messages.log | tail -1

# If above returns nothing, test individual patterns:
grep -m1 -E 'QMS.*HOME_TILES.*complete' /opt/logs/sky-messages.log

# Check file size (if timeout issue):
ls -lh /opt/logs/sky-messages.log

# Count lines in file:
wc -l /opt/logs/sky-messages.log
```

## Expected Outcomes

### ✅ SUCCESS (Combined grep works)
```
📋 DEBUG: Got response from grep
   Stdout length: 185 chars
✓ HOME log line found (matched one of 3 patterns)
✓ HOME screen log line detected!
```

### ✅ SUCCESS (Fallback works)
```
📋 DEBUG: Combined grep returned empty, trying individual patterns...
   [FALLBACK 2] Trying: grep -m1 -E 'QMS.*HOME_TILES.*complete'
   ✓ ✨FALLBACK PATTERN 2 WORKED!
✓ HOME screen log line detected (via fallback)!
```

### ❌ FAILURE (Timeout issue)
```
⚠ ❌SOCKET TIMEOUT after 20s waiting for grep output!
→ Log file too large OR SSH too slow
→ Manual test: Check if manual grep takes >20s
```

### ❌ FAILURE (Pattern issue)
```
📋 DEBUG: Got response from grep
   Stdout length: 0 chars
[FALLBACK 1/2/3] No output
❌ HOME screen log line NOT found within 30s
→ Pattern doesn't match device logs
→ Manual test: Run pattern on device console
```

### ❌ FAILURE (SSH error)
```
⚠ ❌GREP ERROR: [error details]
Traceback: ...
→ Check error message for specific issue
```

---

## Key Points

| Check | What it means | Next action |
|-------|---|---|
| `Stdout length: 0` | Grep found nothing | Test pattern on device |
| `Stdout length: >0` | Grep found match! | Check if it's HOME log line |
| `SOCKET TIMEOUT` | SSH too slow | Check file size with `ls -lh` |
| `FALLBACK PATTERN X WORKED` | Individual pattern worked | Method will succeed |
| `Stderr: [message]` | Grep had error | Check error details |

---

## Files Modified

- `methods/method_reboot_perf_v2_optimized.py` - Enhanced debugging & fallback
- Flask app restarted - Changes deployed

---

## Support

If execution still fails after seeing debug output:
1. Share the execution ID
2. Share the debug output lines from execution log  
3. Share manual test results from device console
4. This will pinpoint the exact cause

