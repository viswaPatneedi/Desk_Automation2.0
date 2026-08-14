# Pi Connection Validation & Build Details Scripts

## Overview
Recently developed scripts to validate R-Pi connections and fetch build details using `cat /version.txt` command. Three main implementations are available.

---

## 1. **test_parallel_rpi_ssh.py** (Primary Implementation)

### Purpose
Raw SSH connection testing to multiple R-Pi devices in parallel, fetching build details without framework dependencies.

### Key Features
- **Direct SSH Connections**: Uses `paramiko` library directly
- **Parallel Testing**: Multi-threaded testing of multiple R-Pis and devices
- **No Tunnel Dependencies**: Direct connection via R-Pi as proxy
- **Build Details Fetch**: Executes `cat /version.txt` on devices
- **Color-Coded Output**: Pretty-printed results with status indicators

### Supported Infrastructure

#### DESK R-Pi (CELLO Devices)
```
R-Pi: 10.26.52.60:22
  User: lrqa
  Pass: Viswa123!
  
Devices:
  ├─ CELLO-SKY (10.0.0.95:10022)
  └─ SKY-Glass (10.0.0.166:10022)
```

#### LAB R-Pi (Rack Devices)
```
R-Pi: 10.138.17.42:60201
  User: pi
  Pass: Eastcoast-Goldfish-Progress
  
Devices:
  ├─ DT-XIONE_UK-0D-AB (10.0.0.140:10022)
  ├─ DT-XIONE_UK-17-97 (10.0.0.28:10022)
  └─ DT-XIONE_UK-5D-54 (10.0.0.199:10022)
```

### Connection Flow
```
test_parallel_rpi_ssh.py
│
├─ test_rpi_direct_connection()
│  └─ Validates direct SSH connection to R-Pi
│     Returns: ssh_client object
│
├─ test_device_via_rpi()
│  ├─ SSH command: ssh -o StrictHostKeyChecking=no -p {port} {user}@{ip} 'cat /version.txt'
│  ├─ Executes via R-Pi's SSH client (R-Pi acts as proxy)
│  └─ Returns device version info + hostname
│
└─ 🔄 Parallel execution with threading
   └─ All devices tested simultaneously
```

### Key Methods

#### `test_rpi_direct_connection(rpi_config)`
Tests SSH connection to R-Pi and verifies connectivity
```python
success, message, ssh_client = test_rpi_direct_connection(rpi_config)
# Returns: (True/False, "message", SSHClient object)
```

#### `test_device_via_rpi(rpi_config, device_config, rpi_client)`
Executes commands on device through R-Pi tunnel
```python
result = {
    'device_name': 'CELLO-SKY',
    'device_ip': '10.0.0.95',
    'success': True,
    'version_info': 'Image Name: RDK_MAIN\nImage Version: 20260813...',
    'output': 'Get device hostname: device-name\nGet version info: ...',
    'timestamp': '2026-08-13T18:15:30.123456'
}
```

### Build Details Information
The script retrieves `/version.txt` which typically contains:
```
Image Name: RDK_MAIN
Image Version: 20260813_release_v1.2.3
Build Date: 2026-08-13
Build ID: abc123def456
Manufacturer: YOURCOMPANY
Device Model: SKY-STREAM
```

### Usage
```bash
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard

python3 test_parallel_rpi_ssh.py

# Output:
# ✓ Successfully connected to DESK-R-Pi
# ✓ Get device hostname: cello-sky
# ✓ Image Name: RDK_MAIN
# ✓ Successfully accessed CELLO-SKY (10.0.0.95)
# ✓ Success Rate: 100% - ALL TESTS PASSED ✓
```

### Connection Details
| Component | Details |
|-----------|---------|
| **R-Pi Access Method** | Direct SSH connection via paramiko |
| **Device Access** | SSH through R-Pi (R-Pi executes SSH command) |
| **Authentication** | Username/Password auth to R-Pi and devices |
| **Build Info Source** | `cat /version.txt` on remote device |
| **Timeout** | 10 seconds per command |
| **Concurrency** | Parallel threading (max limited by system threads) |

---

## 2. **test_app_parallel_rpi_ssh.py** (Application Integration)

### Purpose
Tests the application's `GDFRPiShellService` with multiple R-Pi connections, verifying framework integration.

### Key Features
- **Framework Integration**: Uses application's GDFRPiShellService
- **Identical Device Setup**: Same R-Pi and device configurations
- **Service Quality**: Full application service testing
- **Connection Metrics**: Measures tunnel setup time and success rates
- **Error Handling**: Comprehensive error tracking

### Connection Flow
```
test_app_parallel_rpi_ssh.py
│
├─ Import GDFRPiShellService from services/
│
├─ GDFRPiShellService.connect()
│  └─ Establishes tunnel via application layer
│
├─ execute_command('cat /version.txt')
│  └─ Returns version info through tunnel
│
└─ GDFRPiShellService.disconnect()
   └─ Closes tunnel
```

### Result Structure
```python
{
    'infrastructure': 'desk',
    'device_name': 'CELLO-SKY',
    'device_ip': '10.0.0.95',
    'rpi_ip': '10.26.52.60',
    'success': True,
    'tunnel_status': 'Connected',
    'connection_time': 2.345,  # seconds
    'version_info': 'Image Name: RDK_MAIN...',
    'error': '',
    'details': [
        'Tunnel service created for CELLO-SKY',
        'Tunnel established successfully',
        'Successfully retrieved version info',
        'Device hostname: cello-sky'
    ]
}
```

### Usage
```bash
python3 test_app_parallel_rpi_ssh.py

# Output:
# [INFO] Initializing tunnel to CELLO-SKY via 10.26.52.60
# [✓] Tunnel established
# [✓] Version info retrieved
# [✓] Test completed for CELLO-SKY
```

### Key Advantages Over Direct SSH
- Uses application's built-in tunnel management
- Consistent with production deployments
- Integration testing for GDFRPiShellService
- Automatic cleanup and resource management
- Follows application patterns

---

## 3. **test_tunnel_direct.py** (Service-Level Testing)

### Purpose
Single-device testing of `GDFRPiShellService` with detailed diagnostics.

### Key Features
- **Loads Device Config**: From `Json/devices.json`
- **Step-by-Step Testing**: Clear progression through connection and commands
- **Diagnostic Output**: Shows exactly what's happening at each step
- **Simple Interface**: Minimal setup required

### Connection Steps
```
Step 1: Initialize Service
  └─ Create GDFRPiShellService with R-Pi config

Step 2: Establish Tunnel
  └─ service.connect()

Step 3: Basic Test (echo)
  └─ execute_command("echo 'Tunnel Test OK'")

Step 4: Fetch Build Details
  └─ execute_command("cat /version.txt")

Step 5: Close Tunnel
  └─ service.disconnect()
```

### Usage
```bash
python3 test_tunnel_direct.py

# Output:
# 📋 Device Configuration:
#    Device IP: 10.0.0.28
#    Device Name: DT-XIONE_UK-17-97
# 
# 🚀 Initializing GDFRPiShellService...
#    ✓ Service initialized
# 
# 🔌 Step 1: Establishing tunnel...
#    ✓ Tunnel established
# 
# 🧪 Step 3: Testing build details fetch (cat /version.txt)...
#    ✓ Build details retrieved
#    Version: Image Name: RDK_MAIN...
```

---

## Comparison Matrix

| Feature | test_parallel_rpi_ssh.py | test_app_parallel_rpi_ssh.py | test_tunnel_direct.py |
|---------|--------------------------|------------------------------|----------------------|
| **Multiple Devices** | ✅ Yes (5+ parallel) | ✅ Yes (2 parallel) | ❌ Single device |
| **Framework Integration** | ❌ Direct paramiko | ✅ Uses GDFRPiShellService | ✅ Uses GDFRPiShellService |
| **Config Source** | Hardcoded | Hardcoded | From JSON file |
| **Connection Metrics** | Basic timing | Connection time tracked | Basic timing |
| **Threading** | ✅ Parallel | ✅ Parallel | ❌ Sequential |
| **Dependencies** | paramiko, sshtunnel | Application services | Application services |
| **Best For** | Raw SSH validation | App integration testing | Diagnostics & debugging |

---

## Build Details Extraction

### Command Used
```bash
cat /version.txt
```

### Expected Output Format
```
Image Name: RDK_MAIN
Image Version: 20260813_release_v1.2.3
Build Date: 2026-08-13
Build ID: abc123def456
Release Notes: Stable release
```

### Parsing Example
```python
version_info = device_result['version_info']
lines = version_info.split('\n')

# Extract all key-value pairs
build_details = {}
for line in lines:
    if ':' in line:
        key, value = line.split(':', 1)
        build_details[key.strip()] = value.strip()

image_name = build_details.get('Image Name')
image_version = build_details.get('Image Version')
build_date = build_details.get('Build Date')
```

---

## Common Issues & Solutions

### Issue: "No such file or directory" for /version.txt
**Cause**: Device doesn't have version file
**Solution**: 
```python
if 'No such file' in error:
    result['version_info'] = 'Not available'
    # Continue with test
```

### Issue: Connection timeout
**Cause**: R-Pi unreachable or slow network
**Solution**:
```python
# Increase timeout in any .exec_command() call
stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=30)
```

### Issue: "Permission denied" for SSH
**Cause**: R-Pi credentials incorrect
**Solution**: Verify credentials match configuration
```python
# Test credentials manually first
ssh -u lrqa@10.26.52.60 "echo test"
```

---

## File Locations

| Script | Location |
|--------|----------|
| Main Script | `test_parallel_rpi_ssh.py` |
| App Integration | `test_app_parallel_rpi_ssh.py` |
| Diagnostic Test | `test_tunnel_direct.py` |
| Device Config | `Json/devices.json` |
| Service Code | `services/gdf_rpi_shell_service.py` |
| Device Model | `models/device.py` |

---

## Recent Enhancements (Aug 13, 2026)

✅ **Multi-device parallel validation**
✅ **Build details extraction via /version.txt**
✅ **Comprehensive error handling**
✅ **Color-coded output for readability**
✅ **Threading-based parallel execution**
✅ **Application service integration testing**
✅ **Connection time metrics**
✅ **Device hostname verification**

---

## Next Steps

1. **Monitor Production**: Use test scripts in automation pipelines
2. **Alert on Failures**: Integration with monitoring system
3. **Log Collection**: Store build version history
4. **Regression Testing**: Run before each release
5. **Performance Tracking**: Monitor connection times over time

---

**Last Updated**: August 13, 2026  
**Status**: All scripts operational and tested ✅
