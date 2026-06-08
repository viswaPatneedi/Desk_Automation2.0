# Screenshot Integration - Complete Implementation Guide

## Overview

The screenshot feature has been fully integrated into the Flask application based on the `Device-Reboot-Deepsleep-Wakeup_new.py` implementation. Screenshots are now automatically captured at all critical device state checkpoints.

## Screenshot Capture Points

### 1. **Reboot Process**

#### Checkpoint 1: After Device Comes Back Online
- **Condition**: Device is on HOME screen (log pattern found)
- **Action**: Take screenshot for visual confirmation
- **Screenshot Name**: `screenshot_reboot_iter{N}_{timestamp}.png`
- **Purpose**: Verify device actually shows home screen UI

**Example Log Output:**
```
[2025-11-12 14:30:45 UTC] ✓ Device is in Home Screen (log pattern found)
[2025-11-12 14:30:45 UTC] Taking screenshot for visual confirmation...
[2025-11-12 14:30:46 UTC] Taking screenshot and uploading to http://10.0.0.32:8018/screenshot_reboot_iter1_20251112_143045.png...
[2025-11-12 14:30:56 UTC] Screenshot command response: {"success":true}
[2025-11-12 14:30:56 UTC] ✓ Screenshot uploaded successfully
[2025-11-12 14:30:58 UTC] ✓ Text extraction completed (245 characters)
[2025-11-12 14:30:58 UTC] Screenshot indication text: Sky Home Menu Apps...
```

#### Checkpoint 2: Device Not on HOME Screen
- **Condition**: HOME screen log pattern NOT found
- **Action**: Check device state with screenshot
- **Screenshot Name**: `screenshot_notHome_iter{N}_{timestamp}.png`
- **Checks Performed**:
  - Power state (STANDBY check)
  - Process crashes
  - Network errors
  - **Screenshot if not in STANDBY**

**Example Log Output:**
```
[2025-11-12 14:31:00 UTC] ⚠ Device is not in Home Screen. Checking for process crashes and errors...
[2025-11-12 14:31:01 UTC] Checking device power state...
[2025-11-12 14:31:01 UTC] Device status output: ON
[2025-11-12 14:31:01 UTC] Device is not in STANDBY state...
[2025-11-12 14:31:01 UTC] Taking screenshot to see current UI state...
[2025-11-12 14:31:12 UTC] Screenshot saved at: http://10.0.0.32:8018/screenshot_notHome_iter1_20251112_143101.png
[2025-11-12 14:31:12 UTC] Screenshot indication text: Error Loading Content...
```

### 2. **Deep Sleep Process**

#### Checkpoint 1: Before Entering Deep Sleep
- **Condition**: Step 1 - Ensuring device is on HOME screen
- **Action**: Take screenshot to verify starting state
- **Screenshot Name**: `deepsleep_before_{IP}_iter{N}_{timestamp}.png`
- **Purpose**: Document state before deep sleep

#### Checkpoint 2: After Waking Up - Success Case
- **Condition**: Device woke up and HOME screen pattern found
- **Action**: Take screenshot for confirmation
- **Screenshot Name**: `screenshot_wakeup_iter{N}_{timestamp}.png`
- **Purpose**: Visual confirmation of successful wake-up

**Example Log Output:**
```
[2025-11-12 14:45:30 UTC] ✓ Device woke up from Deepsleep successfully and is on Home Screen
[2025-11-12 14:45:30 UTC] Taking screenshot and uploading to http://10.0.0.32:8018/screenshot_wakeup_iter1_20251112_144530.png...
[2025-11-12 14:45:40 UTC] ✓ Screenshot uploaded successfully
[2025-11-12 14:45:41 UTC] Wake-up screenshot saved at: http://10.0.0.32:8018/screenshot_wakeup_iter1_20251112_144530.png
```

#### Checkpoint 3: After Waking Up - Error Case
- **Condition**: Device woke up but NOT on HOME screen (network errors detected)
- **Action**: Take screenshot to see error state
- **Screenshot Name**: `screenshot_wakeup_error_iter{N}_{timestamp}.png`
- **Purpose**: Capture error UI for debugging

**Example Log Output:**
```
[2025-11-12 14:45:35 UTC] ⚠ Device woke up but not on Home Screen
[2025-11-12 14:45:35 UTC] ❌ Device woke up from Deepsleep, Not in Home Screen after DeepSleep. Network errors detected.
[2025-11-12 14:45:36 UTC] Taking screenshot and uploading to http://10.0.0.32:8018/screenshot_wakeup_error_iter1_20251112_144535.png...
[2025-11-12 14:45:46 UTC] Error state screenshot saved at: http://10.0.0.32:8018/screenshot_wakeup_error_iter1_20251112_144535.png
[2025-11-12 14:45:47 UTC] Screenshot indication text: No Connection - Check your network settings...
```

## New Functions

### `take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_callback)`

Complete screenshot workflow matching original implementation:
1. Build RPC command with exact format
2. Execute screenshot upload command
3. Download screenshot from server
4. Extract text using pytesseract OCR
5. Analyze screen state
6. Return complete result

**Returns:**
```python
{
    'success': True/False,
    'screenshot_url': 'http://...',
    'extracted_text': 'Full text from OCR...',
    'screen_state': {
        'state': 'home_screen',
        'is_home_screen': True,
        'has_error': False,
        ...
    },
    'error': None or error message
}
```

### `check_home_screen_with_screenshot(ssh, screenshot_name, device_ip, log_callback)`

Check HOME screen with screenshot capture:
1. Check log pattern for HOME screen
2. If found, take screenshot for visual confirmation
3. Return tuple: `(is_home_screen, screenshot_result)`

### `check_device_state_with_screenshot(ssh, screenshot_name, device_ip, log_callback)`

Comprehensive device state check:
1. Check power state (STANDBY detection)
2. If in STANDBY, send power key
3. If NOT in STANDBY, take screenshot
4. Check for process crashes
5. Check for network errors

**Returns:**
```python
{
    'is_home': False,
    'power_state': 'ON',
    'screenshot_result': {...},
    'has_crashes': False,
    'has_network_errors': True
}
```

## Screenshot Flow Diagrams

### Reboot Process Flow

```
Reboot Device
    ↓
Wait for Boot
    ↓
Check HOME Screen Logs
    ↓
┌─────────────────┬─────────────────┐
│ HOME Found      │ HOME Not Found  │
├─────────────────┼─────────────────┤
│ 📸 Screenshot   │ Check Power     │
│ (confirmation)  │ State           │
│                 │    ↓            │
│                 │ ┌───────┬───────┐
│                 │ │STANDBY│ NOT   │
│                 │ ├───────┼───────┤
│                 │ │Power  │📸 Take│
│                 │ │Key ON │Screen │
│                 │ └───────┴───────┘
│                 │    ↓            │
│                 │ Check Crashes   │
│                 │ Check Errors    │
└─────────────────┴─────────────────┘
```

### Deep Sleep Process Flow

```
Deep Sleep
    ↓
📸 Before Screenshot
    ↓
Set Timer + Standby
    ↓
Verify Deep Sleep
    ↓
Send IR Wake Command
    ↓
Ping Device
    ↓
SSH Reconnect
    ↓
Check HOME Logs
    ↓
┌──────────────┬──────────────────┐
│ HOME Found   │ HOME Not Found   │
├──────────────┼──────────────────┤
│ 📸 Success   │ Check Network    │
│ Screenshot   │ Errors           │
│              │    ↓             │
│              │ 📸 Error         │
│              │ Screenshot       │
└──────────────┴──────────────────┘
```

## Configuration

### Screenshot Server Settings
Edit `config_screenshot.py`:
```python
base_url = "http://10.0.0.32:8018"
rpc_url = "http://127.0.0.1:9998/jsonrpc"
screenshot_upload_timeout = 10
screenshot_download_timeout = 30
```

### Customize Detection Keywords
```python
HOME_SCREEN_KEYWORDS = ['home', 'sky', 'menu', 'apps', 'channels']
NETWORK_ERROR_KEYWORDS = ['no connection', 'network error', 'try again']
```

## Complete Example Log

```
[2025-11-12 14:30:00 UTC] Step 5: Checking for HOME screen and device state...
[2025-11-12 14:30:01 UTC] ✓ Device is in Home Screen
[2025-11-12 14:30:01 UTC] Taking screenshot for visual confirmation...
[2025-11-12 14:30:02 UTC] Taking screenshot and uploading to http://10.0.0.32:8018/screenshot_reboot_iter1_20251112_143000.png...
[2025-11-12 14:30:12 UTC] Screenshot command response: {"success":true,"message":"Screenshot uploaded"}
[2025-11-12 14:30:12 UTC] ✓ Screenshot uploaded to http://10.0.0.32:8018/screenshot_reboot_iter1_20251112_143000.png successfully
[2025-11-12 14:30:12 UTC] Downloading screenshot from http://10.0.0.32:8018/screenshot_reboot_iter1_20251112_143000.png for text extraction...
[2025-11-12 14:30:14 UTC] ✓ Text extraction completed (312 characters)
[2025-11-12 14:30:14 UTC] Screenshot indication text preview: Sky Home Menu Apps Channels Settings Continue Watching Recommended For You...
[2025-11-12 14:30:14 UTC] Screen state analysis: home_screen - Device appears to be on home screen
[2025-11-12 14:30:14 UTC] Screenshot saved at: http://10.0.0.32:8018/screenshot_reboot_iter1_20251112_143000.png
[2025-11-12 14:30:14 UTC] Extracted text length: 312 characters
```

## Files Modified

1. **`screenshot_utils.py`** - Added `take_and_analyze_screenshot()` function
2. **`app.py`** - Added three new functions and updated reboot/deepsleep processes
3. **`config_screenshot.py`** - Screenshot configuration

## Testing Checklist

- [ ] Reboot with HOME screen → Screenshot captured
- [ ] Reboot without HOME screen, device ON → Screenshot of current UI
- [ ] Reboot without HOME screen, device in STANDBY → No screenshot
- [ ] Deep sleep before entering → Screenshot captured
- [ ] Wake up successful → Screenshot captured
- [ ] Wake up with errors → Error screenshot captured
- [ ] OCR text extraction working
- [ ] Screenshot URLs accessible
- [ ] Log files contain screenshot URLs
- [ ] All timestamps in UTC

## Benefits

✅ **Visual Evidence** - See actual device UI, not just log patterns
✅ **Error Diagnosis** - Capture error screens for debugging
✅ **Test Verification** - Proof of device state at each checkpoint
✅ **Automated Analysis** - OCR extracts text for state detection
✅ **Complete Coverage** - Screenshots at ALL state checks
