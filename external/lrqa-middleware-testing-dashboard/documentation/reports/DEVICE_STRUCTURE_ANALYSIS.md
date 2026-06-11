# Device Structure & Remote Type Mapping Analysis

## 1. Device JSON Structure

**Location:** `Json/devices.json`

**Example Device Entry:**
```json
{
    "ip": "10.0.0.102",
    "name": "WestingHouse-4K-DESK",
    "username": "root",
    "password": "",
    "port": 10022,
    "ir_config": {
        "itach_ip": "10.0.0.142",
        "itach_port": 4998,
        "ir_port": "2"
    },
    "mac_address": "58:41:46:5C:E4:B4",
    "vnc_url": "http://10.0.0.101:5800/",
    "use_jump_host": false,
    "jump_host_config": {},
    "device_type": "XUMO",
    "location": "US",
    "team_name": "LRQA"
}
```

### Key Fields:
- **device_type**: String indicating device type (e.g., "XUMO", "SKY STREAM")
- **ir_config**: Object containing IR blaster settings
  - `itach_ip`: IP of iTach IR blaster
  - `itach_port`: Port of iTach IR blaster (typically 4998)
  - `ir_port`: Port number on iTach (e.g., "1", "2", "3")
- **port**: SSH port (default 10022)
- **username**: SSH username (typically "root")

---

## 2. Device Type Constants & Remote Type Mappings

**No centralized device type constant file exists.** The mapping is done dynamically in method files.

### Device Type → Remote Type Mapping Logic

**Location:** `method_deepsleep.py` (lines 650-659)

```python
# Auto-detection logic when remote_type is not explicitly provided
if remote_type:
    selected_remote_type = remote_type.strip()
else:
    # Auto-detect based on device_name
    selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'
```

### Mapping Rules:
| Device Type | Device Name Pattern | Remote Type | IR Keycodes Section |
|------------|-------------------|------------|-------------------|
| XUMO | Any name without "SKY" | `XUMO_PR3` | `remotes.XUMO_PR3.keycodes` |
| SKY STREAM | Contains "SKY" in name | `SKY_LC103` | `remotes.SKY_LC103.keycodes` |

### Available Remote Types in IR Keycodes

**Location:** `Json/ir_keycodes.json`

```json
{
    "remotes": {
        "XUMO_PR3": {
            "device_info": {
                "manufacturer": "Comcast/Xumo",
                "device_model": "Element Apache 4K",
                "remote_model": "Xumo XR100-UQ",
                "remote_ic": "R34010"
            },
            "keycodes": { /* HOME, POWER, UP, INPUT, QAM, GUIDE, etc. */ }
        },
        "SKY_LC103": {
            "device_info": { /* SKY-specific info */ },
            "keycodes": { /* SKY remote keycodes */ }
        }
    }
}
```

---

## 3. Method File Structure & Parameter Passing

### Method Signature Example: `method_deepsleep.py`

```python
def execute_deepsleep_process(
    device_ip,                    # IP of target device
    port,                         # SSH port
    username,                     # SSH username
    password,                     # SSH password
    iteration=1,                  # Iteration number
    skip_pre_validation=False,    # Skip pre-validation
    device_name="Device",         # Device name (used for remote_type auto-detect)
    combined_method_name=None,    # Combined name for multi-method execution
    remote_type=None,             # ⭐ IR remote type (XUMO_PR3, SKY_LC103, or None for auto-detect)
    sleep_duration_minutes=60,    # Duration to sleep
    job_id=None,                  # Job identifier
    perform_reboot=False          # Whether to perform reboot first
):
```

### How Remote Type is Used in Methods

**Location:** `method_deepsleep.py` (lines 296, 334, 365, 477)

```python
# When sending IR commands, remote_type is passed to generate_ir_code()
ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=remote_type)
```

### Method Return Structure

All execute methods return a dictionary:
```python
{
    "iteration": int,           # Iteration number
    "screenshots": list,        # List of screenshot paths
    "logs": list,              # List of log file paths
    "success": bool,           # Whether method succeeded
    "details": str             # Status message
}
```

---

## 4. How Methods are Called from Test Execution Service

**Location:** `services/test_execution_service.py`

### Method Execution Flow

The test execution service calls methods with parameters extracted from the execution queue:

```python
# Line 726-749: Deepsleep execution example
elif method == "deepsleep":
    skip_pre = method_index > 0
    
    # Extract remote_type from queue item
    remote_type_ds = queue_item.get('remote_type', None)  # Can be None (auto-detect)
    sleep_duration = queue_item.get('sleep_duration_minutes', 60)
    perform_reboot = queue_item.get('perform_reboot', False)
    
    # Log parameters being used
    log_service.log(f"DeepSleep remote_type: {remote_type_ds or 'auto-detect'}")
    log_service.log(f"DeepSleep duration: {sleep_duration} minutes")
    log_service.log(f"DeepSleep perform_reboot: {perform_reboot}")
    
    # Call the method with all parameters
    method_result = execute_deepsleep_process(
        device.ip,
        device.port,
        device.username,
        device.password,
        i + 1,
        skip_pre,
        device.name,
        combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
        remote_type=remote_type_ds,           # ⭐ Passed here
        sleep_duration_minutes=sleep_duration,
        job_id=job_id,
        perform_reboot=perform_reboot
    )
```

### Execution Queue Item Structure

```python
queue_item = {
    'method': 'deepsleep',              # Method name
    'remote_type': 'XUMO_PR3',          # ⭐ Optional: explicit remote type, or None for auto-detect
    'sleep_duration_minutes': 60,       # Optional: defaults to 60
    'perform_reboot': False,            # Optional: defaults to False
    # ... other method-specific parameters
}
```

---

## 5. IR Command Generation with Remote Type

**Location:** `config_ir_blaster.py` (lines 47-70)

```python
def generate_ir_code(command_type, ir_port, remote_type=None):
    """Generate IR code dynamically from ir_keycodes.json"""
    keycodes_data = load_ir_keycodes()
    
    if isinstance(keycodes_data, dict) and 'remotes' in keycodes_data:
        remotes = keycodes_data.get('remotes', {})
        selected_remote = (remote_type or '').upper()
        
        if selected_remote and selected_remote in remotes:
            # Use specified remote type
            codes_section = remotes[selected_remote].get('keycodes', {})
        else:
            # Default fallback to XUMO_PR3
            codes_section = remotes.get('XUMO_PR3', {}).get('keycodes', {})
    
    # Get command template from JSON
    cmd_upper = command_type.upper()
    if cmd_upper in codes_section:
        command_template = codes_section[cmd_upper].get('command_template', '')
        # Replace placeholders with actual IR port
        ir_code = command_template.replace('{IR_PORT}', str(ir_port))
        return ir_code
    
    return None
```

### Flow:
1. **Input:** `command_type="POWER"`, `ir_port="2"`, `remote_type="XUMO_PR3"`
2. **Load:** Fetch IR keycodes from `ir_keycodes.json`
3. **Select:** Look up remote in `remotes[XUMO_PR3]`
4. **Retrieve:** Get keycodes for that remote: `remotes[XUMO_PR3].keycodes`
5. **Build:** Get command template for POWER: `keycodes[POWER].command_template`
6. **Replace:** Replace `{ir_port}` placeholder with actual port number
7. **Output:** Return complete IR command string ready to send to iTach

---

## 6. Device Model Layer

**Location:** `models/device.py`

### Device Class Structure

```python
class Device:
    def __init__(self, 
                 ip: str,
                 name: str,
                 username: str,
                 password: str,
                 port: int = 10022,
                 ir_config: Optional[Dict] = None,
                 mac_address: str = None,
                 vnc_url: str = None,
                 use_jump_host: bool = False,
                 jump_host_config: Optional[Dict] = None,
                 device_type: str = None,           # ⭐ Device type field
                 location: str = None,
                 team_name: str = None):
        
        self.ip = ip
        self.name = name
        self.username = username
        self.password = password
        self.port = port
        self.ir_config = ir_config or {}
        self.device_type = device_type or ''       # ⭐ Stored here
        self.location = location or ''
        self.team_name = team_name or ''
```

### Device Persistence

```python
@staticmethod
def load_all() -> List['Device']:
    """Load all devices from Json/devices.json"""
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'r') as f:
            devices_data = json.load(f)
            return [Device.from_dict(d) for d in devices_data]

@staticmethod
def find_by_ip(ip: str) -> Optional['Device']:
    """Find device by IP address"""
    devices = Device.load_all()
    for device in devices:
        if device.ip == ip:
            return device
```

---

## 7. Summary: Data Flow for Remote Type Passing

```
devices.json
  ↓
  (device_type: "XUMO" or "SKY STREAM")
  ↓
Device Model (device.device_type)
  ↓
Execution Queue Item
  (remote_type: "XUMO_PR3" or "SKY_LC103" or None)
  ↓
execute_deepsleep_process()
  (parameter: remote_type)
  ↓
generate_ir_code()
  (parameter: remote_type)
  ↓
ir_keycodes.json[remotes][XUMO_PR3|SKY_LC103]
  ↓
IR Command Sent to iTach
```

---

## 8. Key Implementation Notes

### Auto-Detection Behavior
- If `remote_type` is **not provided** in queue item, it defaults to **None** ("auto-detect")
- In `execute_deepsleep_process()`, auto-detection uses device_name:
  - If device name contains "SKY" → use `SKY_LC103`
  - Otherwise → use `XUMO_PR3` (default)

### Remote Type Options
- **XUMO_PR3** - For XUMO/Comcast devices (Xumo XR100-UQ remote)
- **SKY_LC103** - For Sky Stream devices (Sky LC103 remote)

### Explicit vs. Auto-Detect
- **Explicit:** Pass `remote_type="XUMO_PR3"` in queue item
- **Auto-detect:** Pass `remote_type=None` or omit from queue item
  - Service logs: `"DeepSleep remote_type: auto-detect"`

### Error Handling
- If specified remote type not found in `ir_keycodes.json`, falls back to `XUMO_PR3`
- If IR port not in selected remote's keycodes, returns `None`

---

## 9. Files & Line References

| Component | File | Key Lines |
|-----------|------|-----------|
| Device JSON | `Json/devices.json` | All entries |
| Device Model | `models/device.py` | 1-150 |
| Deepsleep Method | `method_deepsleep.py` | 578 (signature), 650-659 (auto-detect) |
| IR Generation | `config_ir_blaster.py` | 47-70 |
| IR Keycodes | `Json/ir_keycodes.json` | Lines 1-80+ |
| Test Execution | `services/test_execution_service.py` | 726-749 (deepsleep call) |
| Queue Item | `services/test_execution_service.py` | 429, 446, 453, 457, 463 |
