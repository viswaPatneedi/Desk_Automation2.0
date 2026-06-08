# USB Folder Structure - Enhancement Output

## Overview
When running tests from the Raspberry Pi with USB stick connected at `/media/pi/Lexar`, all outputs are organized in a session-based folder structure.

## Folder Structure

```
/media/pi/Lexar/Enhancement-output/
│
└── <METHOD>_<DEVICENAME>_<IP>_<ITERATIONS>_ITR_<UTC_TIMESTAMP>/
    ├── SCREENSHOTS/
    │   ├── ITR-1/
    │   │   ├── BEFORE/
    │   │   │   └── <device>_<method>_beforeReboot_HomeScreen_<timestamp>.png
    │   │   └── AFTER/
    │   │       └── <device>_<method>_afterReboot_HomeScreen_<timestamp>.png
    │   ├── ITR-2/
    │   │   ├── BEFORE/
    │   │   └── AFTER/
    │   └── ...
    │
    ├── EXECUTION_LOGS/
    │   ├── <device_ip>_<method>_<timestamp>.log
    │   └── <device_ip>_<method>_<timestamp>.html
    │
    └── DEVICE_LOGS/
        ├── ITR-1/
        │   └── ITR-1-NO-HOMESCREEN_AFTERREBOOT_<timestamp>.tgz
        ├── ITR-2/
        └── ...
```

## Example

If you select **REBOOT** method for **20 iterations** on **Element A4K** device (10.0.0.172):

```
/media/pi/Lexar/Enhancement-output/
└── REBOOT_ELEMENT-A4K_10-0-0-172_20_ITR_20251119_143022_UTC/
    ├── SCREENSHOTS/
    │   ├── ITR-1/
    │   │   ├── BEFORE/
    │   │   │   └── 10.0.0.172_Element-A4K_beforeReboot_HomeScreen_20251119_143025_UTC.png
    │   │   └── AFTER/
    │   │       └── 10.0.0.172_Element-A4K_AfterReboot_HomeScreen_20251119_143145_UTC.png
    │   ├── ITR-2/
    │   │   ├── BEFORE/
    │   │   └── AFTER/
    │   ├── ...
    │   └── ITR-20/
    │       ├── BEFORE/
    │       └── AFTER/
    │
    ├── EXECUTION_LOGS/
    │   ├── 10.0.0.172_REBOOT_20251119_143022_UTC.log
    │   └── 10.0.0.172_REBOOT_20251119_151500_UTC.html
    │
    └── DEVICE_LOGS/
        ├── ITR-1/
        │   └── ITR-1-NO-HOMESCREEN_AFTERREBOOT_20251119_143145_UTC.tgz
        ├── ITR-5/
        │   └── ITR-5-NO-HOMESCREEN_AFTERREBOOT_20251119_145212_UTC.tgz
        └── ...
```

## File Naming Convention

### Session Folder
**Format:** `<METHOD>_<DEVICENAME>_<IP>_<ITERATIONS>_ITR_<UTC_TIMESTAMP>`

**Components:**
- `<METHOD>`: REBOOT, DEEPSLEEP, REBOOT+DEEPSLEEP, IR-COMMAND-TEST
- `<DEVICENAME>`: Device name with spaces replaced by hyphens (ELEMENT-A4K)
- `<IP>`: IP address with dots replaced by hyphens (10-0-0-172)
- `<ITERATIONS>`: Number of iterations (20)
- `<UTC_TIMESTAMP>`: YYYYMMDD_HHMMSS_UTC

**Example:** `REBOOT_ELEMENT-A4K_10-0-0-172_20_ITR_20251119_143022_UTC`

### Screenshots
**Path:** `SCREENSHOTS/ITR-<N>/BEFORE` or `SCREENSHOTS/ITR-<N>/AFTER`

**Filename:** `<IP>_<DeviceName>_<Phase>_<Screen>_<Timestamp>.png`

**Examples:**
- `10.0.0.172_Element-A4K_beforeReboot_HomeScreen_20251119_143025_UTC.png`
- `10.0.0.172_Element-A4K_AfterReboot_HomeScreen_20251119_143145_UTC.png`
- `10.0.0.172_Element-A4K_AfterDeepSleep_NO-HOMESCREEN_20251119_145030_UTC.png`

### Execution Logs
**Path:** `EXECUTION_LOGS/`

**Files:**
- `.log` file: Real-time execution log with all console output
- `.html` file: HTML report with iteration results table

**Examples:**
- `10.0.0.172_REBOOT_20251119_143022_UTC.log`
- `10.0.0.172_REBOOT_20251119_151500_UTC.html`

### Device Logs
**Path:** `DEVICE_LOGS/ITR-<N>/`

**Filename:** `ITR-<N>-NO-HOMESCREEN_AFTER<METHOD>_<Timestamp>.tgz`

Device logs are only captured when device fails to reach HOME screen.

**Examples:**
- `DEVICE_LOGS/ITR-1/ITR-1-NO-HOMESCREEN_AFTERREBOOT_20251119_143145_UTC.tgz`
- `DEVICE_LOGS/ITR-5/ITR-5-NO-HOMESCREEN_AFTERDEEPSLEEP_20251119_145212_UTC.tgz`

## Fallback Behavior

### Windows Development Mode
If running on Windows (not Raspberry Pi), folders are created locally:
- `Enhancement-output/` in current directory
- Same structure applies

### No USB Stick
If USB stick is not connected on Raspberry Pi:
- Falls back to local `Enhancement-output/` folder
- Warning message displayed in console

### Legacy Compatibility
If session folder creation fails:
- Screenshots: `screenshots/<DeviceIP>_<DeviceName>/ITR-X/Before|After/`
- Logs: `iteration_logs/`
- Device Logs: `device_logs/`

## Benefits

1. **Session Isolation**: Each test run has its own complete folder
2. **Easy Identification**: Folder name contains all key information
3. **Organized**: Screenshots, logs, and device logs clearly separated
4. **Iteration Tracking**: Easy to find artifacts for specific iterations
5. **Archival**: Simple to archive or delete entire test sessions

## Accessing Results

### Via File System
Connect to Raspberry Pi and navigate:
```bash
cd /media/pi/Lexar/Enhancement-output
ls -lrt  # List sessions by time
cd REBOOT_ELEMENT-A4K_10-0-0-172_20_ITR_20251119_143022_UTC
```

### Via Web Interface
Access the results page at:
```
http://<RASPBERRY_PI_IP>:5000/results
```

The web interface shows aggregated results from all devices and methods.

## Storage Recommendations

- **USB Stick**: Minimum 32GB recommended for extensive testing
- **Cleanup**: Periodically archive old session folders
- **Backup**: Copy important session folders to permanent storage

## Troubleshooting

### USB Not Detected
```bash
# Check if USB is mounted
ls /media/pi/Lexar

# If not mounted, mount manually
sudo mount /dev/sda1 /media/pi/Lexar
```

### Permission Issues
```bash
# Ensure pi user has write permissions
sudo chown -R pi:pi /media/pi/Lexar/Enhancement-output
sudo chmod -R 755 /media/pi/Lexar/Enhancement-output
```

### Disk Space
```bash
# Check USB disk space
df -h /media/pi/Lexar

# Find large session folders
du -sh /media/pi/Lexar/Enhancement-output/* | sort -h
```
