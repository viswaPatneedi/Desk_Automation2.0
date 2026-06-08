# Screenshot Integration - Enhancement Guide

## Overview

The application now includes comprehensive screenshot capture and OCR text analysis to verify device screen states at critical checkpoints.

## New Features

### 1. Screenshot Capture Module (`screenshot_utils.py`)

A dedicated utility module for screen capture and analysis:

- **`take_screenshot(ssh, screenshot_name, log_callback)`** - Captures screenshot from device
- **`extract_text_from_screenshot(screenshot_url, log_callback)`** - Performs OCR on captured image
- **`capture_and_analyze_screen(ssh, screenshot_name, log_callback)`** - Complete capture + OCR workflow
- **`analyze_screen_state(extracted_text, log_callback)`** - Analyzes text to determine screen state
- **`get_screen_state(ssh, screenshot_name, log_callback)`** - All-in-one function for complete state detection

### 2. Screen State Detection

The system can now automatically detect:

- **Home Screen** - Detects keywords like 'home', 'sky', 'menu', 'apps', 'channels'
- **Network Errors** - Detects error messages like 'no connection', 'try again'
- **Loading States** - Detects 'loading', 'please wait', 'buffering'
- **Blank/Standby Screen** - Minimal or no text detected
- **Error States** - Generic error messages

### 3. Screenshot Integration Points

Screenshots are now automatically captured and analyzed at:

#### During Reboot Process:
1. **After device comes back online** - Verifies home screen or error state
2. **When not on home screen** - Captures current UI state
3. **When in STANDBY** - Captures before sending power key

#### During Deep Sleep Process:
1. **Before entering deep sleep** - Confirms starting state
2. **After waking up from deep sleep** - Verifies successful wake-up and home screen

### 4. Configuration Files

**`config_screenshot.py`** - New configuration file with:
- Screenshot server URLs
- OCR timeout settings
- Screen state detection keywords
- Customizable thresholds

## Prerequisites

### System Requirements

1. **Tesseract OCR** must be installed on the system:

   **Windows:**
   ```powershell
   # Download installer from:
   # https://github.com/UB-Mannheim/tesseract/wiki
   # Add to PATH: C:\Program Files\Tesseract-OCR
   ```

   **Linux:**
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr
   ```

   **macOS:**
   ```bash
   brew install tesseract
   ```

2. **Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

   New dependencies:
   - `Pillow==10.1.0` - Image processing
   - `pytesseract==0.3.10` - OCR wrapper
   - `requests==2.31.0` - HTTP requests for screenshot download

### Device Requirements

1. **Screenshot Server** - Must be running at `base_url` (configurable in `config_screenshot.py`)
2. **RPC Endpoint** - Device must have RPC endpoint at `http://127.0.0.1:9998/jsonrpc`
3. **ScreenCapture Plugin** - Device must support `org.rdk.ScreenCapture.1.uploadScreenCapture` method

## Usage

### Automatic Screenshot Capture

Screenshots are automatically captured during device state checks. No manual intervention required.

### Screenshot Naming Convention

Screenshots are saved with descriptive names:
- `reboot_after_{IP}_iter{N}_{timestamp}.png` - After reboot completion
- `reboot_notHome_{IP}_iter{N}_{timestamp}.png` - When not on home screen
- `deepsleep_before_{IP}_iter{N}_{timestamp}.png` - Before deep sleep
- `deepsleep_wakeup_{IP}_iter{N}_{timestamp}.png` - After wake up

### Log Output Examples

```
[2025-11-12 10:30:45 UTC] Taking screenshot to verify screen state...
[2025-11-12 10:30:56 UTC] Screenshot captured: http://10.0.0.32:8018/reboot_after_10_0_0_20_iter1_20251112_103045.png
[2025-11-12 10:30:57 UTC] Screen state detected: home_screen
[2025-11-12 10:30:57 UTC] Details: Device appears to be on home screen
[2025-11-12 10:30:57 UTC] Text preview: Sky Home Menu Apps Channels Settings...
[2025-11-12 10:30:57 UTC] ✓ Device is on HOME screen
```

## Configuration

### Customize Screenshot Server

Edit `config_screenshot.py`:

```python
# Screenshot server settings
base_url = "http://YOUR_SERVER_IP:8018"
rpc_url = "http://127.0.0.1:9998/jsonrpc"
```

### Customize Detection Keywords

```python
HOME_SCREEN_KEYWORDS = ['home', 'sky', 'menu', 'apps', 'channels', 'your_keyword']
NETWORK_ERROR_KEYWORDS = ['no connection', 'network error', 'your_error']
```

### Adjust Timeouts

```python
screenshot_upload_timeout = 10  # seconds
screenshot_download_timeout = 30  # seconds
```

## Troubleshooting

### Issue: "Tesseract not found"

**Solution:**
1. Ensure Tesseract is installed
2. Add Tesseract to system PATH
3. On Windows, you may need to specify path in code:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### Issue: Screenshot upload fails

**Solution:**
1. Check screenshot server is running
2. Verify `base_url` in `config_screenshot.py`
3. Ensure device can reach the server
4. Check firewall settings

### Issue: OCR returns no text

**Solution:**
1. Check screenshot was captured successfully
2. Verify screenshot URL is accessible
3. Try downloading screenshot manually to verify content
4. Adjust OCR language if needed

### Issue: Screen state not detected correctly

**Solution:**
1. Review text preview in logs
2. Add custom keywords to `config_screenshot.py`
3. Adjust `MIN_TEXT_LENGTH` threshold
4. Check screenshot quality

## File Structure

```
Enhancement/
├── app.py                      # Main Flask app (updated)
├── screenshot_utils.py         # NEW: Screenshot utilities
├── config_screenshot.py        # NEW: Screenshot configuration
├── config_commands.py          # Device commands
├── config_log_patterns.py      # Log patterns
├── config_ir_blaster.py        # IR blaster config
├── config_timing.py            # Timing settings
├── templates/
│   └── index.html             # UI template
├── devices.json               # Device storage
├── iteration_logs/            # Execution log files
├── screenshots/               # NEW: Screenshot storage (optional)
├── requirements.txt           # Updated dependencies
└── README.md                  # Main documentation
```

## API Response Format

When `get_screen_state()` is called, it returns:

```python
{
    'success': True,
    'screenshot_url': 'http://...',
    'state': 'home_screen',  # or 'network_error', 'loading', 'blank_screen', 'unknown'
    'is_home_screen': True,
    'has_error': False,
    'has_network_error': False,
    'is_loading': False,
    'is_blank': False,
    'details': 'Device appears to be on home screen',
    'extracted_text': 'Full extracted text...',
    'text_preview': 'First 200 characters...'
}
```

## Benefits

1. **Visual Verification** - See actual screen state, not just logs
2. **Error Diagnosis** - Identify UI issues that logs might miss
3. **Test Evidence** - Screenshots provide visual proof of device state
4. **Automated Analysis** - OCR automatically determines screen state
5. **Historical Record** - Screenshots saved with timestamps for review
