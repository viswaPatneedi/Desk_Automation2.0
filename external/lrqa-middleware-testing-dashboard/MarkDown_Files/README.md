# Device Control Panel - Flask UI

A web-based interface for managing and controlling devices via SSH with detailed logging and iteration tracking.

## Features

### Section 1: Device Operations
- **Iteration Count**: Set the number of times to execute the selected method
- **Device Selection**: Select from registered devices by IP address
- **Method Selection**: Choose from available methods:
  - **Reboot Device**: Complete reboot process with step-by-step verification
  - **Deep Sleep**: Put device into deep sleep and wake it up with IR command
  - **Power Key**: Send power key command to device
  - **Query Power State**: Check device power status
- **SSH Connection Test**: Test SSH connectivity before executing methods
- **Real-time Operation Log**: View execution logs in real-time with UTC timestamps

### Section 2: Device Management
- **View Registered Devices**: List of all stored devices with IP, port, and username
- **Add New Device**: Form to register new devices with:
  - Device Name
  - IP Address
  - Port (default: 10022)
  - Username (default: root)
  - Password
- **Remove Device**: Remove devices from the registry

### Iteration Log Files
- **Separate Log Files**: Each execution creates a separate log file
- **UTC Timestamps**: All log messages include UTC timestamps
- **Download Logs**: Download individual log files for review
- **Organized Storage**: Logs stored in `iteration_logs/` directory
- **File Information**: View file size and modification time

## Configuration Files

The application uses separate configuration files for better organization:

- **`config_commands.py`**: Device control commands
  - Reboot, deep sleep, power key, status commands

- **`config_log_patterns.py`**: Log patterns for device status checking
  - HOME screen detection
  - Network error detection
  - Crash detection

- **`config_ir_blaster.py`**: IR blaster (iTach) configuration
  - iTach IP and port settings
  - IR codes for HOME and POWER buttons

- **`config_timing.py`**: Timing settings for device operations
  - Boot time, retry intervals, timeouts
  - Deep sleep and wake-up timings

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

### 1. Add a Device (Section 2)
- Fill in the device details (name, IP, port, username, password)
- Click "Add Device"
- Device information is stored in `devices.json`

### 2. Execute Method (Section 1)
- Select a device from the dropdown
- Choose the number of iterations
- Select a method to execute
- Optionally test SSH connection first
- Click "Execute Method"
- Watch the real-time operation log

### 3. View Iteration Logs
- Click "Refresh Log Files" to update the list
- View log file details (size, modification time)
- Click "Download" to download a specific log file
- Log files include complete execution details with UTC timestamps

## Detailed Method Processes

### Reboot Process
1. Test SSH connectivity to the selected device
2. Execute the reboot command
3. Wait for device to complete boot-up (100 seconds)
4. Re-establish SSH connection with retries
5. Verify device state:
   - Check if device is on HOME screen
   - If not, check for network errors
   - Print results accordingly

### Deep Sleep Process
1. Ensure device is on HOME screen
2. Send curl command to set device into deep sleep
3. Send power key command to put device into standby
4. Verify device is in STANDBY mode
5. Wait for 60 seconds for device to enter deep sleep
6. Check if device is in deep sleep (SSH should fail)
7. Wake up device with IR POWER command
8. Verify device returns to HOME screen or check for network errors

## File Structure

```
Enhancement/
├── app.py                      # Flask application
├── config_commands.py          # Device commands configuration
├── config_log_patterns.py      # Log patterns configuration
├── config_ir_blaster.py        # IR blaster configuration
├── config_timing.py            # Timing settings configuration
├── templates/
│   └── index.html             # UI template
├── devices.json               # Stored device configurations
├── iteration_logs/            # Directory for iteration log files
│   └── *.log                  # Individual execution logs
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Log File Format

Each iteration log file includes:
- **Header**: Device IP, method, start time (UTC)
- **Detailed Steps**: Each step with UTC timestamp
- **Status Indicators**: ✓ (success), ❌ (error), ⚠ (warning)
- **Footer**: End time (UTC)

Example log filename: `10.0.0.20_reboot_20251111_143052_UTC.log`

## Notes

- Device credentials are stored in `devices.json`
- All operations are performed over SSH
- Logs are streamed in real-time using Server-Sent Events (SSE)
- Iteration logs are saved to separate files with UTC timestamps
- The UI is responsive and works on mobile devices
- Configuration is separated into multiple files for easier management

## Requirements

- Python 3.7+
- Flask 3.0.0
- Paramiko 3.4.0
- SSH access to target devices
- iTach IR blaster (for deep sleep wake-up)

