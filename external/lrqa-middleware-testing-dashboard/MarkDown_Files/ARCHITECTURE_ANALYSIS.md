# Flask Device Management Application - Architecture Analysis

## 1. PROJECT STRUCTURE OVERVIEW

### Controllers (`/controllers/`)
- **`device_controller.py`** (191 lines)
  - CRUD operations: `get_devices()`, `add_device()`, `delete_device()`, `update_device()`
  - Connection validation: `test_connection()`
  - Focus: Device management and registration only
  - Does NOT contain device method execution logic

### Models (`/models/`)
- **`device.py`** (247 lines)
  - Device representation with SSH/Jump Host connectivity
  - Methods: `load_all()`, `find_by_ip()`, `add()`, `delete()`, `update()`
  - `validate_connection()`: Direct SSH or Jump Host validation
  - Data persistence: Reads/writes to `devices.json`

### Services (`/services/`)
- **`test_execution_service.py`**: Main orchestrator for test execution
  - `execute_test()`: Entry point for method execution
  - `_execute_method_sequence()`: Iterates through methods and calls appropriate handlers
- **`ssh_connection_helper.py`**: Unified SSH interface (direct or Jump Host)
- **`log_service.py`**: Real-time log streaming via SSE
- **`queue_service.py`**: Background task queue management
- **`execution_monitor_service.py`**: Job monitoring and cancellation
- **`jump_host_service.py`**: Jump Host SSH relay connectivity

### Method Implementations (Root Directory)
- **`method_reboot.py`**: `execute_reboot_process()`
- **`method_deepsleep.py`**: `execute_deepsleep_process()`
- **`method_ir_test.py`**: IR command testing
- **`method_voice_command.py`**: Voice command execution
- **`method_utils.py`**: Shared utilities (SSH retry, polling, error checking)

---

## 2. KEY METHOD PATTERNS

### Pattern: Device Method Execution via Flask Route

**Route**: `/api/execute` (POST) → `test_controller.execute_test()`
```
app.py (/api/execute)
    ↓
test_controller.execute_test()
    ↓
TestExecutionService.execute_test(device_ip, methods, iterations)
    ↓
Threading -> _execute_method_sequence()
    ↓
Calls specific method handler (method_reboot.py, method_deepsleep.py, etc.)
```

---

## 3. SSH OPERATIONS PATTERN

### Direct SSH Connection Pattern (from `method_utils.py`)

```python
# Basic SSH connection establishment
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)

# Execute command
stdin, stdout, stderr = ssh.exec_command(command_string)
output = stdout.read().decode('utf-8', errors='ignore').strip()
error = stderr.read().decode('utf-8', errors='ignore').strip()

# Close connection
ssh.close()
```

### Key SSH Commands (from `config_commands.py`)

```python
device_status_command = "QueryPowerState\n"
reboot_command = "systemctl reboot\n"
power_key_command = "keySimulator -ktvpower"
home_key_command = "keySimulator -khome"
deepsleep_command = "curl -s -X POST http://127.0.0.1:9001/as/test/preferences -d '{\"lowPowerTimerDuration\": \"20\"}'"
```

### SSH Retry/Reconnection Pattern

**Function**: `reconnect_to_device_with_retry()` (method_utils.py:398)

```python
def reconnect_to_device_with_retry(device_ip, port, username, password, max_retries=10, retry_interval=5):
    """Reconnect with exponential backoff"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, 
                       password=password, timeout=10)
            return ssh  # Success - return connection
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(retry_interval)  # Wait before retry
            else:
                return None  # Failed after all retries
```

---

## 4. IR BLASTER USAGE PATTERN

### Configuration Retrieval (from `config_ir_blaster.py`)

```python
def get_ir_config_for_device(device_name):
    """Get IR configuration from devices.json"""
    device = Device.find_by_name(device_name)
    if device:
        return device.ir_config  # Contains: ir_port, itach_ip, itach_port
    return None
```

### IR Code Generation

```python
def generate_ir_code(command_type, ir_port, remote_type=None):
    """Generate IR code from ir_keycodes.json"""
    keycodes_data = load_ir_keycodes()
    
    # Get command template from JSON (e.g., "POWER", "HOME")
    cmd_upper = command_type.upper()
    if cmd_upper in codes_section:
        command_template = codes_section[cmd_upper].get('command_template', '')
        ir_code = command_template.replace('{IR_PORT}', str(ir_port))
        return ir_code
    return None
```

### IR Command Transmission (from `config_ir_blaster.py:75`)

```python
def send_ir_command(ir_code, itach_ip='10.0.0.12', itach_port=4998, log_callback=None):
    """Send IR command to iTach device via TCP socket"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((itach_ip, itach_port))
            sock.sendall(ir_code.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            
            if 'ERR' in response:
                log_callback(f"⚠ iTach returned error: {response.strip()}")
                return False
            else:
                log_callback(f"✓ IR command sent successfully")
                return True
    except socket.timeout:
        log_callback("⚠ Socket timeout connecting to iTach")
        return False
    except Exception as e:
        log_callback(f"❌ IR send failed: {e}")
        return False
```

---

## 5. STATUS POLLING & WAITING PATTERNS

### Active Device Polling (from `method_utils.py:424`)

**Function**: `wait_for_device()` - Actively polls for device to come back online

```python
def wait_for_device(device_ip, port, username, password, log_callback=None):
    """Actively poll for device to come back online after reboot.
    Eliminates fixed countdown, breaks as soon as SSH is reachable."""
    
    max_wait = wait_for_bootime  # from config_timing.py: 100 seconds
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < max_wait:
        remaining = max_wait - (time.time() - start_time)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, 
                       password=password, timeout=8)
            
            log_callback(f"✓ Device back online after {int(time.time() - start_time)}s (attempt {attempt+1}).")
            return ssh  # Success - return connection immediately
        except Exception:
            attempt += 1
            log_callback(f"Attempt {attempt} failed; {int(remaining)}s remaining...")
            
            sleep_interval = min(wait_before_retry, max_wait - (time.time() - start_time))
            if sleep_interval > 0:
                time.sleep(sleep_interval)  # Wait before next attempt (10 seconds)
    
    log_callback("❌ Device did not come back online within the allotted wait window.")
    return None
```

### Timing Configuration (from `config_timing.py`)

```python
wait_for_bootime = 100          # Wait time for device to boot after reboot
wait_before_retry = 10          # Wait time between SSH retry attempts
total_timeout = 300             # Total timeout for waiting for device
wait_after_reboot = 15          # Wait time after device comes online to check logs
wait_for_deepsleep = 60         # Wait time for device to enter deep sleep
wait_after_wakeup = 20          # Wait time after sending IR wake command
wait_for_logs = 15              # Wait time for logs to populate after wake up
```

### Status Verification via Log Pattern Matching

```python
# From method_reboot.py and method_deepsleep.py
stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
log_output = stdout.read().decode('utf-8', errors='ignore')

if log_line_HOME.split(".*")[0] in log_output:
    log_message("✓ Device is on HOME screen")
    # Device is in expected state
else:
    log_message("⚠ Device is not on HOME screen")
    # Error diagnostics
```

### Error Checking Pattern

**Function**: `check_network_and_realtek_errors()` (method_utils.py:469)

```python
def check_network_and_realtek_errors(ssh, log_callback=None):
    """Check for network/WiFi errors and Realtek module issues"""
    
    # Check for network errors
    stdin, stdout, stderr = ssh.exec_command(log_check_command_Network_Error)
    network_error_log = stdout.read().decode('utf-8', errors='ignore').strip()
    if network_error_log:
        log_callback("⚠ Network Error detected in logs")
        return True
    
    # Check for Realtek module errors
    stdin, stdout, stderr = ssh.exec_command(log_check_command_Realtek)
    realtek_log = stdout.read().decode('utf-8', errors='ignore').strip()
    if realtek_log:
        log_callback("⚠ Realtek module error detected")
        return True
    
    return False  # No errors detected
```

---

## 6. MULTI-STEP OPERATION PATTERNS

### Reboot Process (3-step workflow)

**File**: `method_reboot.py:35`

```python
def execute_reboot_process(device_ip, port, username, password, iteration=1, 
                          device_name="Device", combined_method_name=None, 
                          has_deepsleep=False, job_id=None):
    """
    Step 1: Pre-Reboot validation
      - Connect to device
      - Fetch build details
      - Send HOME key to load HOME screen
      - Wait for HOME screen (10 seconds)
      - Check HOME screen status via log pattern
      - Capture BEFORE screenshot
    
    Step 2: Execute reboot
      - Send reboot command via SSH
      - Close connection immediately
      - Mandatory wait: 80 seconds for device to reboot
    
    Step 3: Reconnection & validation
      - Actively poll device for SSH availability (up to 100 seconds)
      - Once available, fetch build details
      - Activate ScreenCapture service
      - Check HOME screen status
      - Capture AFTER screenshot
      - Compare screenshots (before vs after)
      - Check for network/Realtek errors
      - Wait for maintenance (2-15 minutes based on next operation)
    
    Error Handling:
      - If device not online after reboot: capture device logs and diagnostics
      - If not on HOME screen: perform OCR analysis and error diagnostics
      - If network errors detected: log additional information for analysis
    """
```

### DeepSleep Process (6-step workflow)

**File**: `method_deepsleep.py:42`

```python
def execute_deepsleep_process(device_ip, port, username, password, iteration=1, 
                             skip_pre_validation=False, device_name="Device", 
                             combined_method_name=None, remote_type=None, 
                             sleep_duration_minutes=60, job_id=None):
    """
    Step 1: Pre-DeepSleep Validation (OPTIONAL - skipped if part of sequence)
      - Send HOME key to load HOME screen
      - Wait 10 seconds for HOME screen
      - Check HOME screen status via log pattern
      - Capture BEFORE screenshot
    
    Step 2: Initiate DeepSleep
      - Set DeepSleep timer (20 minutes via REST API)
      - Send POWER key to put device in STANDBY
      - Close SSH connection
      - Wait 60 seconds to allow full device shutdown
    
    Step 3: Verify DeepSleep State
      - Attempt SSH connection - should FAIL (device inaccessible)
      - Confirm device is truly in DeepSleep
    
    Step 4: Wait in DeepSleep
      - Sleep for configurable duration (default: 60 minutes)
      - Sleep in 10-second chunks for monitoring
      - Log progress every 60 seconds
      - Monitor for job cancellation every 10 seconds
      - Validate device lock hasn't expired
    
    Step 5: Wake Device with IR
      - Generate IR POWER code based on remote type (XUMO or SKY)
      - Send IR command to iTach device
      - Wait 20 seconds after IR command (from config_timing.py)
      - Attempt to reconnect to device
      - Retry reconnection up to 10 times (5 seconds between attempts)
    
    Step 6: Post-Wake Validation & Error Diagnostics
      - Check HOME screen status
      - Capture AFTER screenshot
      - If not on HOME screen:
        * Perform OCR analysis
        * Check for network errors
        * Check for Realtek module errors
        * Capture device logs via SFTP
      - Validate screenshot comparison (informational only)
    
    Return:
      - dict: {"iteration": int, "screenshots": list, "logs": list, "success": bool}
    """
```

### Method Sequence Orchestration

**File**: `services/test_execution_service.py:1588`

```python
def _execute_method_sequence(self, device: Device, methods: List[str], 
                            iterations: int, selected_ir_keys, voice_text):
    """Execute method sequence with multi-iteration support"""
    
    for i in range(iterations):
        for method_index, method in enumerate(methods):
            if method == "reboot":
                # Execute reboot with skip_pre_validation=False (standalone)
                execute_reboot_process(device.ip, device.port, device.username, 
                                      device.password, i + 1, device.name)
            
            elif method == "deepsleep":
                # If not first method, skip pre-validation (part of sequence)
                skip_pre = method_index > 0
                execute_deepsleep_process(device.ip, device.port, device.username, 
                                         device.password, i + 1, skip_pre, device.name)
            
            elif method == "status":
                # Simple status check - device connectivity verification
                ssh = paramiko.SSHClient()
                ssh.connect(...)
                stdin, stdout, stderr = ssh.exec_command('uptime')
                output = stdout.read().decode().strip()
                ssh.close()
            
            elif method == "ir_test":
                execute_ir_test_process(...)
            
            elif method == "voice_command":
                execute_voice_command_process(...)
```

---

## 7. EXISTING DEVICE METHODS

### Currently Available Methods (from `method_reboot.py`, `method_deepsleep.py`)

1. **`reboot`** - Device reboot with HOME screen validation
2. **`deepsleep`** - Deep sleep wake cycle with IR control
3. **`status`** - Basic device status check
4. **`ir_test`** - IR command testing (multiple keys)
5. **`voice_command`** - Voice command execution
6. **`reboot_performance`** - Performance-focused reboot
7. **`trail`** - Trail method (performance tracking)
8. **`soft_hard_boot`** - Soft and hard boot sequence

### Maintenance/DeepSleep Related Code

**DeepSleep Configuration**:
- Duration: Configurable (10, 30, 120, 300 minutes, or custom)
- Remote Type: XUMO or SKY (for IR wakeup)
- Pre-validation: Optional (skipped when part of sequence)
- Post-wakeup Wait: 20 seconds (from config_timing.py)

**Device Lock Management**:
- During DeepSleep: Device lock validated every 10 seconds
- Lock expiration: Automatic cleanup if expired
- Job cancellation: Monitored and enforced during sleep/wait periods

---

## 8. LOG/RESULT HANDLING PATTERN

### Logging Pattern

**Log Service** (services/log_service.py):
- Creates iteration-specific log files
- Real-time streaming via SSE
- Log format: `{device_ip}_{method}_{timestamp}_UTC.log`
- Path: `iteration_logs/`

### Result Documentation

**Pattern**: Each method captures screenshots and logs

```python
# Take BEFORE screenshot
screenshot_folder = create_screenshot_folder(device_ip, device_name, iteration, "Before", method)
screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, 
                                               log_message, screenshot_folder)
screenshots_list.append(screenshot_result.get('local_path', ''))

# Perform operation

# Take AFTER screenshot
screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip,
                                               log_message, screenshot_folder, 
                                               after_reboot=True)
screenshots_list.append(screenshot_result.get('local_path', ''))

# Capture device logs if error
if error_detected:
    log_path = capture_device_logs_sftp(ssh, log_filename, log_message, iteration, device_ip)
    logs_list.append(log_path)
```

---

## 9. DEVICE CONFIGURATION (from `devices.json`)

```json
{
  "ip": "192.168.1.100",
  "name": "Test-Device-1",
  "username": "root",
  "password": "password",
  "port": 10022,
  "device_type": "XUMO",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "ir_config": {
    "ir_port": 3,
    "itach_ip": "10.0.0.12",
    "itach_port": 4998,
    "remote_type": "XUMO"
  },
  "vnc_url": "vnc://192.168.1.100:5900",
  "use_jump_host": false,
  "jump_host_config": {},
  "location": "Lab A",
  "team_name": "QA"
}
```

---

## 10. KEY ARCHITECTURAL DECISIONS

### 1. Separation of Concerns
- Controllers: REST API routing only
- Services: Business logic and orchestration
- Models: Data persistence
- Method files: Specific operation implementations

### 2. SSH Connection Strategy
- Direct SSH for standard devices
- Jump Host SSH for secure/networked environments
- Paramiko library with timeout handling
- Automatic retry with configurable backoff

### 3. Async Execution
- All method execution happens in background threads
- Main Flask thread remains responsive
- Real-time log streaming via SSE
- Job cancellation support via thread-local storage

### 4. Multi-step Operation Flow
- Each method has distinct pre/execution/post phases
- Phase validation uses log pattern matching
- Screenshots capture device state transitions
- Error diagnostics capture logs and OCR data

### 5. IR Control Integration
- Centralized IR configuration in devices.json
- IR keycodes stored in ir_keycodes.json
- Socket-based communication with iTach device
- Support for multiple remote types (XUMO, SKY)

### 6. Status Validation Pattern
- Primary: Log file pattern matching (grep over SSH)
- Secondary: Screenshot analysis (OCR)
- Tertiary: System command execution (uptime, disk space, etc.)
- Comprehensive: Network/WiFi error checking

---

## 11. COMMON EXTENSION POINTS

To add a new device method or maintenance operation:

1. **Create method file** (`method_xxx.py`)
   ```python
   def execute_xxx_process(device_ip, port, username, password, iteration=1, 
                          device_name="Device", job_id=None):
       # Pre-validation → Operation → Post-validation
       # Use log_message() for logging
       # Use ssh.exec_command() for device control
       # return {"iteration": i, "screenshots": list, "logs": list, "success": bool}
   ```

2. **Register in `test_execution_service.py`**
   ```python
   elif method == "xxx":
       execute_xxx_process(device.ip, device.port, device.username, 
                          device.password, i + 1, device.name, job_id=job_id)
   ```

3. **Add to available methods list** (app.py:/api/available_methods)

4. **Use shared utilities**:
   - `method_utils.py`: Retry, polling, error checking
   - `config_commands.py`: Device commands
   - `config_log_patterns.py`: Status validation patterns
   - `config_timing.py`: Timing configuration
   - `screenshot_utils.py`: Screenshot capture and analysis

---

## 12. DEPLOYMENT PARAMETERS

**SSH Defaults** (from model and controllers):
- Port: 10022
- Username: root
- Timeout: 10 seconds

**iTach Defaults** (from config_ir_blaster.py):
- IP: 10.0.0.12
- Port: 4998

**Configuration Sources**:
- Device credentials: devices.json
- Commands: config_commands.py
- Timing: config_timing.py
- Log patterns: config_log_patterns.py and log_patterns.json
- IR codes: ir_keycodes.json
