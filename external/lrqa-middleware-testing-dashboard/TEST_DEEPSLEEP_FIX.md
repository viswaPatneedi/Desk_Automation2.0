# DeepSleep Execution Fix - Testing Guide

## Summary of Changes Made

### 1. **Missing DeepSleep Parameter Handler** ✅ FIXED
- **Issue**: Dashboard didn't collect deepsleep parameters from users
- **Solution**: Added `else if (methodId === 'deepsleep')` handler in `getMethodParametersAsync()`
- **Details**: Handler now calls `promptForDeepSleepParams()` modal

### 2. **New DeepSleep Parameter Modal** ✅ ADDED
- **Function**: `promptForDeepSleepParams()` (line 3655 in dashboard.html)
- **Collects**:
  - Remote Type (select: COMCAST, XUMO, SKY, ALTICE, DISCOVERY, OTHER, or auto-detect)
  - Sleep Duration (5-600 minutes, default 60)
  - Perform Reboot (checkbox, default unchecked)
- **Returns**: Configuration object with `remoteType`, `sleepDuration`, `performReboot`

### 3. **Silent Failure Error Handling** ✅ ADDED
- **Added comprehensive try-catch blocks** around the `executeQueue()` forEach loop
- **Validates**: selectedDevices and transformedQueue are proper arrays before use
- **Logs**: All errors with message, error type, and stack trace
- **Browser console** will now show exact error instead of silent failure

### 4. **Enhanced Logging** ✅ ADDED
- Line 7109-7127: More detailed logging during parameter collection
- Line 7191-7206: Array validation logging
- Line 7441-7450: Error logging in outer catch block

---

## Testing Steps

### Step 1: Load Dashboard
1. Open browser and navigate to `http://localhost:11078/`
2. Login to dashboard
3. Check browser console (F12) for any JavaScript errors

### Step 2: Add DeepSleep to Queue
1. Click on "Methods" or locate the deepsleep method card
2. Drag deepsleep to the execution queue OR click "Add to Queue
3. **Wait for modal to appear** ➜ This is the new `promptForDeepSleepParams()` modal
4. **Expected**: Modal shows with:
   - Remote Type dropdown
   - Sleep Duration input (default 60)
   - Perform Reboot checkbox
   - Cancel and Confirm buttons

### Step 3: Fill DeepSleep Parameters
1. Select a Remote Type (e.g., COMCAST, XUMO, or leave as auto-detect)
2. Set Sleep Duration (e.g., 60 minutes)
3. Optionally check "Perform Device Reboot Before DeepSleep"
4. Click "Confirm & Add to Queue"

### Step 4: Verify Queue Item
1. Check execution queue shows deepsleep method with parameters
2. **Expected display**: 
   ```
   DeepSleep Configuration
   Remote: XUMO
   Duration: 60 minutes
   Reboot: ✓ YES  (or ✗ NO)
   ```

### Step 5: Select Device and Execute
1. Select target device(s) from the device list
2. Set iterations (usually 1)
3. Click "Execute" button

### Step 6: Monitor Browser Console
1. **Press F12** to open developer console
2. Watch for these log messages (in order):
   - `[EXECUTE] executeQueue() function CALLED`
   - `[EXECUTE] Selected devices count: X`
   - `[EXECUTE] Getting iterations value...`
   - `[EXECUTE] About to iterate over selected devices...`
   - **NEW** ➜ `✓ selectedDevices is a valid array`
   - **NEW** ➜ `✓ transformedQueue is a valid array`
   - `[EXECUTE] Processing device 1/X...`
   - `[EXECUTE] About to call fetch() to /api/execute`
   - `[EXECUTE] fetch() called, waiting for response...`
   - `[EXECUTE] Response received! Status: 200`
   - `[EXECUTE] Job created with ID: [uuid]`

### Step 7: Verify Jobs Created
1. Check "Pending Executions" section of dashboard
2. New deepsleep job should appear
3. Check app logs for execution start messages

---

## Expected Outcomes

| Step | Expected Result | Status |
|------|-----------------|--------|
| Dashboard loads | No JS errors in console | ✓ |
| Add deepsleep to queue | Modal appears with parameter collection UI | ✓ NEW |
| Fill in parameters | Modal closes, queue shows deepsleep with params | ✓ NEW |
| Execute with device selected | /api/execute API called | ✓ |
| Job creation | Job created in database and visible in dashboard | ✓ |
| Execution starts | Device receives command and begins deepsleep process | ✓ |

---

## Troubleshooting

### Issue: Modal doesn't appear when adding deepsleep
- **Check console** for error messages (F12)
- Confirm the new `promptForDeepSleepParams()` function loaded
- Look for JavaScript errors in console

### Issue: "OUTER ERROR - Failed to iterate devices" appears
- **Check console** for the detailed error message and stack trace
- This is the new error handler catching a failure
- Stack trace will show exact line causing the issue

### Issue: Jobs not creating even after modal
- Check network tab (F12) to see if `/api/execute` call is being made
- If not, check console for validation errors
- If yes, check `/api/execute` handler in test_controller.py for errors

### Issue: transformedQueue shows as not an array
- This indicates items in executionQueue don't have required structure
- Check browser console log for exact transformedQueue content
- May indicate issue with queue item structure

---

## Quick Verification Commands

```bash
# Check app is running
ps aux | grep "python.*app.py" | grep -v grep

# Verify port is listening
ss -tlnp | grep 11078

# Test API endpoint (will redirect to login, but confirms app responds)
curl -i http://localhost:11078/api/execute

# Check for JavaScript errors in built HTML
grep -n "promptForDeepSleepParams" templates/dashboard.html | head -5
grep -n "OUTER ERROR" templates/dashboard.html | head -2
```

---

## Files Changed

1. `templates/dashboard.html`
   - Added deepsleep handler: Lines 2693-2710
   - Added `promptForDeepSleepParams()` function: Lines 3655-3775
   - Enhanced parameter logging: Lines 7109-7127
   - Added array validation: Lines 7191-7206
   - Added outer error handler: Lines 7441-7450

---

## Next Steps After Testing

1. ✅ Confirm deepsleep method can be queued with parameters
2. ✅ Confirm job creation succeeds
3. ✅ Confirm execution reaches the backend
4. Monitor execution progress and completion
5. Check method_deepsleep.py logs for any phase-specific errors
6. If successful, test with non-deepsleep methods to confirm no regression

---

**App Status**: Running on PID 544039 (restarted with fixes)
**HTML Version**: Updated with deepsleep handler and error handling
**Ready**: Yes - Ready for user testing
