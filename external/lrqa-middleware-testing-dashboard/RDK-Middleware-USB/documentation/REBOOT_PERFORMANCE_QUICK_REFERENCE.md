# Reboot Performance - Sequential Communication Quick Reference

## ⚡ EXECUTION TIME COMPARISON: Regular SSH vs Lightspeed SSH

```
┌─────────────────────────────────────────────────────────────────────────┐
│       REBOOT PERFORMANCE - TIMING COMPARISON                           │
│            Regular SSH (Paramiko) vs Lightspeed API                    │
└─────────────────────────────────────────────────────────────────────────┘

PHASE-BY-PHASE TIMING COMPARISON:
═════════════════════════════════════════════════════════════════════════

PHASE 1: PRE-REBOOT PREPARATION
─────────────────────────────────────────────────────────────────────────
Commands: 6 SSH calls (connect + 5 exec_command)

REGULAR SSH:                          LIGHTSPEED SSH:
├─ Connect: 200-500ms                 ├─ Auth (token): 500-1000ms (first time)
├─ Build version: 100-200ms           ├─ Submit #1: 200-400ms + Poll: 15s
├─ Build date: 100-200ms              ├─ Submit #2: 200-400ms + Poll: 15s
├─ Device model: 100-200ms            ├─ Submit #3: 200-400ms + Poll: 15s
├─ ScreenCapture: 100-200ms           ├─ Submit #4: 200-400ms + Poll: 15s
├─ ScreenCapture verify: 100-200ms    ├─ Submit #5: 200-400ms + Poll: 15s
└─ Total: ~1.5-2s                     └─ Total: ~80-90s (6 Lightspeed ops × 16s)
                                       ⚠️  OVERHEAD: +80x slower


PHASE 2: SEND REBOOT COMMAND
─────────────────────────────────────────────────────────────────────────
Commands: 1 SSH call (reboot) + 1 close

REGULAR SSH:                          LIGHTSPEED SSH:
├─ Send reboot: 100-300ms             ├─ Auth (cached): ~1ms
├─ Close: instant                     ├─ Submit reboot: 200-400ms + Poll: 15s
└─ Total: ~0.3s                       └─ Total: ~15-16s
                                       ⚠️  OVERHEAD: +50x slower


PHASE 3: MANDATORY REBOOT WAIT
─────────────────────────────────────────────────────────────────────────
No SSH communication (device rebooting)

REGULAR SSH:         80 seconds        LIGHTSPEED SSH:      80 seconds
└─ Same for both    (Exactly 80s)      └─ Same for both    (Exactly 80s)


PHASE 4: WAIT FOR DEVICE TO COME ONLINE
─────────────────────────────────────────────────────────────────────────
Polling for SSH connectivity

REGULAR SSH:                          LIGHTSPEED SSH:
├─ Polling attempts every 5s          ├─ Same polling mechanism
├─ Success typically: 60-120s          ├─ Success typically: 60-120s
└─ Total: ~60-120s                    └─ Total: ~60-120s
                                       ✓ SAME (physical device behavior)


PHASE 5: POST-REBOOT INITIALIZATION
─────────────────────────────────────────────────────────────────────────
Commands: 4 SSH calls (reconnect + 3 exec_command)

REGULAR SSH:                          LIGHTSPEED SSH:
├─ Verify build: 100-200ms            ├─ Submit #1: 200-400ms + Poll: 15s
├─ ScreenCapture: 100-200ms           ├─ Submit #2: 200-400ms + Poll: 15s
├─ ScreenCapture verify: 100-200ms    ├─ Submit #3: 200-400ms + Poll: 15s
└─ Total: ~0.5-1.0s                   └─ Total: ~48-51s (3 Lightspeed ops × 16s)
                                       ⚠️  OVERHEAD: +50x slower


PHASE 6: MONITOR HOME SCREEN LOGS (MAX 150 SECONDS)
─────────────────────────────────────────────────────────────────────────
Commands: 30+ SSH polling calls (every 5 seconds)

REGULAR SSH:                          LIGHTSPEED SSH:
├─ Polling loop: 30 iterations        ├─ Polling loop: 30 iterations
├─ Each iteration: ~200ms             ├─ Each iteration: ~16s (Lightspeed overhead)
│  └─ 5s wait + SSH command           │  └─ 5s wait + 16s API call overhead
└─ Total: ~50-150s (typical: 110s)    └─ Total: ~350-630s (typical: ~500s!)
   ✓ EFFICIENT                         ❌ VERY SLOW (4.5x longer!)


PHASE 7-8: SCREENSHOT & VALIDATION
─────────────────────────────────────────────────────────────────────────
Commands: 2 SSH calls (screenshot + validation)

REGULAR SSH:                          LIGHTSPEED SSH:
├─ SFTP: 2-5s (native SFTP)           ├─ SFTP: 2-5s (same)
├─ OCR: 2-5s                          ├─ OCR: 2-5s (same)
├─ Validation: 100-300ms              ├─ Submit validation: 200-400ms + Poll: 15s
└─ Total: ~4-10s                      └─ Total: ~20-26s (screenshot) + 16s (validation)
                                       ⚠️  OVERHEAD: +3-4x slower


═════════════════════════════════════════════════════════════════════════

TOTAL TIME BREAKDOWN:

REGULAR SSH (Current):
  ├─ Phase 1-2 (Pre-reboot):        2s
  ├─ Phase 3 (Mandatory wait):      80s
  ├─ Phase 4 (Device reconnect):    90s (typical)
  ├─ Phase 5 (Post-reboot init):    1s
  ├─ Phase 6 (Home screen):         110s (typical)
  ├─ Phase 7-8 (Screenshot+Val):    10s
  └─ TOTAL: ✓ 293 seconds (4-5 minutes)

LIGHTSPEED SSH (With API polling):
  ├─ Phase 1-2 (Pre-reboot):        105s  (+103s overhead!)
  ├─ Phase 3 (Mandatory wait):      80s
  ├─ Phase 4 (Device reconnect):    90s (typical)
  ├─ Phase 5 (Post-reboot init):    50s  (+49s overhead!)
  ├─ Phase 6 (Home screen):         500s (+390s overhead!)
  ├─ Phase 7-8 (Screenshot+Val):    42s  (+32s overhead!)
  └─ TOTAL: ❌ 867 seconds (14-15 minutes!)

═════════════════════════════════════════════════════════════════════════

TIME COMPARISON SUMMARY:

┌────────────────────────────────────────────────────────────────────┐
│ METRIC                    REGULAR SSH    LIGHTSPEED SSH  RATIO    │
├────────────────────────────────────────────────────────────────────┤
│ Phase 1-2 (Pre-reboot)    2s            105s            52x ❌   │
│ Phase 5 (Post-reboot)     1s            50s             50x ❌   │
│ Phase 6 (Log polling)     110s          500s            4.5x ❌  │
│ Phase 7-8 (Validate)      10s           42s             4x ❌   │
├────────────────────────────────────────────────────────────────────┤
│ TOTAL TIME (1 iteration)  293 seconds   867 seconds     3x ❌   │
│                           ~5 minutes    ~14-15 minutes         │
├────────────────────────────────────────────────────────────────────┤
│ Reboot Metric Captured    70-120s       70-120s         1x ✓   │
│ (Device time to HOME)     (Same)        (Same)          (Same) │
└────────────────────────────────────────────────────────────────────┘

KEY FINDINGS:
═════════════════════════════════════════════════════════════════════════

1. ❌ LIGHTSPEED SSH IS 3x SLOWER (14-15 min vs 4-5 min per iteration)

2. ❌ MAIN BOTTLENECK: Log polling phase
   - Regular SSH: 110s (30 commands × 200ms each)
   - Lightspeed SSH: 500s (30 commands × 16s each)
   ├─ Each polling iteration: 5s + 16s API overhead
   └─ Results in 390s+ additional wait

3. ⚠️  PRE-REBOOT OVERHEAD: 105s instead of 2s
   - Regular SSH: 2s (direct connection)
   - Lightspeed SSH: 105s (6 commands × 16-17s each)

4. ⚠️  NOT RECOMMENDED FOR THIS USE CASE
   - Single iteration becomes 14-15 minutes
   - 5 iterations: ~70-75 minutes with Lightspeed vs ~20-25 with Regular SSH
   - ❌ 3x increase in total test time

RECOMMENDATION:
─────────────────────────────────────────────────────────────────────
✅ ALWAYS USE REGULAR SSH FOR REBOOT PERFORMANCE TESTING

Lightspeed SSH only justifiable if:
  ├─ Device is behind restrictive firewall (blocks SSH)
  ├─ No direct network access available
  └─ Willing to accept 3x longer test duration

Otherwise: Direct SSH is clearly superior for this workflow.
```

---

## One-Page Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│         REBOOT PERFORMANCE OPTIMIZED METHOD                        │
│              All Sequential Communication Steps                     │
└─────────────────────────────────────────────────────────────────────┘

EXECUTION PHASES (In Order):

PHASE 1: PRE-REBOOT PREPARATION (0-1.5s)
───────────────────────────────────────────────────────────────────────
  [SSH] Connect to device @ 10022
        └─ Paramiko.connect(device_ip, port=10022, timeout=15)
  [SSH] Get build version
        └─ Paramiko.exec_command("cat /etc/version.txt")
  [SSH] Get build date & device model  
        └─ Paramiko.exec_command() × 2 more commands
  [SSH] Activate ScreenCapture service
        └─ Paramiko.exec_command("systemctl restart screencapture")
  
  ✓ Status: Connection established, device info captured


PHASE 2: CAPTURE START TIME & SEND REBOOT (1.5-1.8s)
───────────────────────────────────────────────────────────────────────
  [TIMER] Capture UTC timestamp
          └─ reboot_start_time = datetime.now(timezone.utc)
  [SSH]  Send reboot command
         └─ Paramiko.exec_command("reboot")
  [SSH]  Close connection
         └─ Paramiko.close()
  
  ⏱️  DEVICE GOES OFFLINE (Rebooting)
  🔴 No SSH communication possible


PHASE 3: MANDATORY REBOOT WAIT (1.8-81.8s)
───────────────────────────────────────────────────────────────────────
  Sleep 80 seconds in 10-second chunks
    ├─ Progress logged every 20s
    ├─ 0-20s: Device firmware loading
    ├─ 20-40s: Kernel initialization
    ├─ 40-60s: Linux boot
    └─ 60-80s: SSH daemon starting
  
  ⚠️  DEVICE OFFLINE (Rebooting)


PHASE 4: WAIT FOR SSH RECONNECTION (81.8-180s+)
───────────────────────────────────────────────────────────────────────
  Poll for SSH connectivity (up to 180 seconds)
    ├─ Attempt 1: SSH connect failed (Connection refused)
    ├─ Sleep 5s
    ├─ Attempt 2: SSH connect failed
    ├─ Sleep 5s
    ├─ ...
    └─ Attempt N: ✓ SSH connected successfully!
  
  Typical success: 60-120 seconds after reboot command
  🟢 DEVICE COMES ONLINE


PHASE 5: POST-REBOOT INITIALIZATION (180-202s)
───────────────────────────────────────────────────────────────────────
  [SSH] Re-verify build info
        └─ Paramiko.exec_command("cat /etc/version.txt")
  [SSH] Re-activate ScreenCapture service
        └─ Paramiko.exec_command("systemctl restart screencapture")
  
  ✓ Status: Device fully booted, services ready


PHASE 6: MONITOR HOME SCREEN LOGS (202-252s typical)
───────────────────────────────────────────────────────────────────────
  LOOP: Check for HOME screen log line (max 150 seconds)
    ├─ Iteration 1 (0-5s):
    │   [SSH] Paramiko.exec_command(log_check_command_HOME)
    │   Result: ❌ NOT FOUND
    │
    ├─ Iteration 2 (5-10s):
    │   Sleep 5s, [SSH] check logs again
    │   Result: ❌ NOT FOUND
    │
    ├─ ... (Repeat every 5s)
    │
    └─ Iteration N (105-110s):
        Sleep 5s, [SSH] check logs
        Result: ✅ FOUND "HOME_SCREEN_FOUND" log line!
        └─ Parse timestamp from log line
        └─ Extract: 2026-03-27T14:31:32.456Z
        └─ Break loop, proceed
  
  🏠 HOME SCREEN DETECTED


PHASE 7: PERFORMANCE CALCULATION (252-252.1s)
───────────────────────────────────────────────────────────────────────
  Duration = HOME_time - reboot_start_time
           = 14:31:32.456 - 14:30:22.123
           = 70.333 seconds
  
  Display: "REBOOT TO HOME SCREEN TIME: 1m 10.33s"
  ✓ PERFORMANCE METRIC CAPTURED


PHASE 8: SCREENSHOT CAPTURE (252-257s)
───────────────────────────────────────────────────────────────────────
  [SCREENSHOT] Determine screenshot folder path
               └─ "screenshots/[device_ip]/[device_name]/[iteration]/After/"
  
  [SFTP]  Get screenshot from device
          └─ SFTP.get("/tmp/screenshot.png", "local_path.png")
          └─ Transfer: ~100-500KB binary file
  
  [OCR]   Analyze screenshot (if enabled)
          └─ pytesseract.image_to_string()
          └─ Search for: Network errors, error messages
  
  [LOG]   Store result path
          └─ screenshots_list.append(path)
  
  📸 SCREENSHOT CAPTURED & ANALYZED


PHASE 9: VALIDATION CHECK (257-257.3s)
───────────────────────────────────────────────────────────────────────
  [SSH] Query /lib/teetz/ directory
        └─ Paramiko.exec_command("ls -ltr /lib/teetz/")
  
  Validation rules:
    ├─ ✓ Directory exists AND contains .ta files → PASS
    ├─ ❌ Directory not found → FAIL (stop iterations)
    ├─ ❌ Directory empty (no .ta files) → FAIL (stop iterations)
    └─ ⚠️  Partial content → WARNING (log but continue)
  
  Set flag: validation_passed = True/False
            stop_iterations = not validation_passed
  
  ✓ VALIDATION COMPLETE


PHASE 10: RETURN RESULTS (257.3s)
───────────────────────────────────────────────────────────────────────
  [SSH] Close connection
        └─ Paramiko.close()
  
  [RETURN] Dictionary with:
           ├─ iteration: 1
           ├─ success: True/False
           ├─ performance_seconds: 70.33
           ├─ teetz_validation: True/False
           ├─ stop_iterations: bool (if validation failed)
           ├─ screenshots: [paths]
           └─ logs: [paths]
  
  [LOG]  Final status message
         ├─ "✓ REBOOT PERFORMANCE TEST PASSED"
         └─ "✓ Performance: 1m 10.33s"


═══════════════════════════════════════════════════════════════════════
                  TOTAL TEST TIME: ~257 seconds (4m 17s)
              ACTUAL REBOOT METRIC: 70-120 seconds
═══════════════════════════════════════════════════════════════════════
```

---

## SSH Command Execution Timeline

```
T+0.0s    [SSH CONNECT]        Paramiko.connect() → SSH session
│
├─ T+0.2s [CMD #1]             exec_command("cat /etc/version.txt")      
│         └─ Response: Build version
│
├─ T+0.3s [CMD #2]             exec_command(build_date_command)
│         └─ Response: Date string
│
├─ T+0.4s [CMD #3]             exec_command(device_model_command)
│         └─ Response: Model string
│
├─ T+0.6s [CMD #4-5]           exec_command("systemctl restart screencapture")
│         └─ Response: Service restarted
│
├─ T+0.8s [CMD #6]             exec_command("reboot")
│         └─ Response: Reboot sent
│
└─ T+0.9s [SSH CLOSE]          Paramiko.close()
          └─ 🔴 DEVICE OFFLINE

[80 second gap - device rebooting, no communication]

T+80.9s  [SSH CONNECT]        Paramiko.connect() → SSH SESSION ✓
│
├─ T+81.1s [CMD #7]           exec_command("cat /etc/version.txt")
│          └─ Response: Build (verify same version)
│
├─ T+81.2s [CMD #8-9]         exec_command("systemctl restart screencapture")
│          └─ Response: Service restarted
│
├─ T+81.4s [CMD #10]          exec_command(log_check_command_HOME)
│          ├─ Response: NOT FOUND
│          └─ Loop: Repeat every 5 seconds...
│
├─ T+81.4s to T+110.0s        POLLING LOOP (30+ iterations)
│          ├─ Every 5s: exec_command(log_check_command_HOME)
│          ├─ T+86.4s: Not found yet
│          ├─ T+91.4s: Not found yet
│          ├─ T+96.4s: Not found yet
│          ├─ T+101.4s: Not found yet
│          ├─ T+106.4s: Not found yet
│          └─ T+110s: ✓ HOME_SCREEN FOUND! (Break loop)
│
├─ T+110.2s [CMD #11]         exec_command(log_check_command_HOME) [one more time]
│           └─ Parse timestamp: 2026-03-27T14:31:32.456Z
│
├─ T+110.3s [CALCULATION]     Compute: performance = 70.33 seconds
│
├─ T+112.5s [SFTP TRANSFER]   SFTP.get(screenshot) → 100-500KB download
│           └─ Download complete
│
├─ T+114.5s [OCR ANALYSIS]    pytesseract.image_to_string()
│           └─ Extract text & check for errors
│
├─ T+115.0s [CMD #12]         exec_command("ls -ltr /lib/teetz/")
│           └─ Response: Directory listing (.ta files)
│
└─ T+115.2s [SSH CLOSE]       Paramiko.close()
            └─ Connection closed

TOTAL TIME: ~115 seconds (including OCR/SFTP)
MEASURED REBOOT TIME: 70.33 seconds (T+0.9s → T+71.23s in device time)
```

---

## Data Flow Diagram

```
Flask App
    │
    ├─→ method_reboot_performance.execute()
    │   │
    │   ├─→ Paramiko SSHClient
    │   │   │
    │   │   ├─ SSH Connect (device_ip:10022)
    │   │   ├─ 6× exec_command() calls (pre-reboot)
    │   │ │ 
    │   │   ├─ [DEVICE REBOOTS FOR 80 SECONDS]
    │   │   │
    │   │   ├─ SSH Connect (retry polling)
    │   │   ├─ 2× exec_command() calls (post-boot check)
    │   │   ├─ 30+ exec_command() calls (log polling)
    │   │   ├─ Parse log timestamp
    │   │   ├─ Calculate performance duration
    │   │   ├─ 1× exec_command() (validation)
    │   │   └─ SSH Close
    │   │
    │   ├─→ Paramiko SFTP (in same SSH session)
    │   │   └─ Download screenshot binary (100-500KB)
    │   │
    │   ├─→ pytesseract (Python)
    │   │   └─ OCR analyze screenshot (if enabled)
    │   │
    │   └─→ Return Results Dictionary
    │
    └─→ Flask: Store results in database/file
```

---

## Key Timing Milestones

| Milestone | Expected Time | Range | Event |
|-----------|----------------|-------|-------|
| SSH Connect | T+0.2s | 0.1-0.5s | Initial SSH established |
| Send Reboot Cmd | T+0.8s | 0.5-1.0s | Reboot command sent |
| Device Offline | T+0.9s | 0.8-1.2s | Connection closes |
| Mandatory Wait Done | T+80.9s | 80-81s | 80 second wait complete |
| Device Back Online | T+141s | 60-120s later | SSH reconnects |
| Pre-reboot Init Done | T+141.5s | 141-143s | Services re-activated |
| HOME Screen Found | T+251.7s | 150-310s | Log detection succeeds |
| Performance Metric | T+251.8s | Same as above | Duration calculated |
| Screenshot Captured | T+255.8s | 254-260s | Screenshot saved + OCR |
| Validation Done | T+256.3s | 256-258s | /lib/teetz/ checked |
| Test Complete | T+256.5s | 256-260s | Results returned |

---

## SSH Commands By Category

### Build Information Queries
```
exec_command("cat /etc/version.txt")
exec_command(build_date_command)              [from config_commands.py]
exec_command(device_model_command)             [from config_commands.py]
```

### System Service Control
```
exec_command("systemctl restart screencapture")
exec_command("systemctl status screencapture")
```

### Critical Commands
```
exec_command("reboot")                        [ONLY REBOOT COMMAND]
exec_command("ls -ltr /lib/teetz/")           [VALIDATION]
```

### Log Monitoring
```
exec_command(log_check_command_HOME)          [Repeated 30+ times, 5s intervals]
                                               [Typical pattern: grep/tail]
                                               [Example: "tail -100 /var/log/messages | grep HOME"]
```

---

## Performance Metrics Captured

```
TIMING METRIC                    VALUE            SOURCE
══════════════════════════════════════════════════════════════════════════
Reboot Command Sent      T+0.8s  Paramiko timestamp
Reboot Start Time        T+0.9s  datetime.now(timezone.utc)  ← REFERENCE
Device Reconnected       T+141s  wait_for_device() success
HOME Screen Detected     T+251s  log polling success
HOME Log Timestamp       14:31:32.456Z   Parsed from device log
Performance Duration     70.33 seconds   Calculated: HOME_time - start_time
Device Boot Time         ~140s           T+141s - T+0.9s
UI Load Time             ~110s           T+251s - T+141s
Total Test Time          ~256s           Full test duration
```

---

## Error Scenarios

| Scenario | Detection | Action | Result |
|----------|-----------|--------|--------|
| SSH initial connect fails | Exception during ssh.connect() | Return failure immediately | success=False |
| Device not online after 180s | wait_for_device() times out | Return failure | success=False |
| HOME screen not found in 150s | Polling loop expires | Capture screenshot for analysis | success=False |
| /lib/teetz/ missing | "No such file" in error | **Set stop_iterations=True** | Stop further iterations |
| /lib/teetz/ empty | ls output has no .ta files | **Set stop_iterations=True** | Stop further iterations |
| Screenshot capture fails | SFTP.get() exception | Log error, continue | Logged but non-fatal |
| Timestamp parse fails | Regex no match | Log warning, continue | performance_seconds=None |

---

## Return Value Structure

```python
{
    "iteration": 1,                           # Which iteration (1-5 typically)
    "success": True,                          # Test passed?
    "performance_seconds": 70.33,             # Reboot to HOME time
    "teetz_validation": True,                 # /lib/teetz/ check passed?
    "stop_iterations": False,                 # Stop further iterations?
    "screenshots": [
        "screenshots/.../iteration_1.png"     # Path to screenshot
    ],
    "logs": [
        "logs/device_FAILED_logs.tar.gz"      # Path to logs (if error)
    ]
}
```

---

## 🔍 Key Insights

1. **Longest component**: Device physical reboot (80s) + waiting for SSH (60-120s) + UI initialization (110s)
2. **Most critical**: Home screen log detection reliability (must match pattern exactly)
3. **Validation gate**: /lib/teetz/ directory must exist with .ta files, else subsequent iterations blocked
4. **Performance metric precision**: Depends on device log timestamp accuracy
5. **Polling overhead**: 30+ SSH calls for 150-second monitoring window (every 5 seconds)

---

**Reference Files:**
- `method_reboot_performance.py` - Main implementation
- `config_commands.py` - All SSH command definitions
- `config_log_patterns.py` - Log pattern matching for HOME screen
- `config_timing.py` - Timeout and wait duration constants
- `method_utils.py` - Shared utilities (wait_for_device, etc.)

---

**Last Updated:** 2026-03-27
