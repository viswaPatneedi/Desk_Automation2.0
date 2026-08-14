# Multi-R-Pi SSH Parallel Connection Test Suite

## Overview

This test suite verifies that your LRQA Middleware Testing Dashboard application can simultaneously establish SSH connections to multiple R-Pi devices and execute commands on target devices through tunneled connections.

**Key Capability Tested**: The application can handle parallel, non-blocking SSH connections to different R-Pi infrastructures without conflicts or resource exhaustion.

## Test Infrastructure

### DESK R-Pi Infrastructure
- **R-Pi Host**: `10.138.17.42:60201` (username: `pi`)
- **Devices Accessible**:
  - **OD-AB Device**: `10.0.0.140:10022` (via DESK R-Pi)
  - **DESK LAB Device**: `10.0.0.28:10022` (via DESK R-Pi)

### CELLO R-Pi Infrastructure  
- **R-Pi Host**: `10.26.52.60:22` (username: `lrqa`)
- **Devices Accessible**:
  - **CELLO-SKY Device**: `10.0.0.95:10022` (via CELLO R-Pi)

## Test Scripts

### 1. **test_parallel_rpi_ssh.py** - Raw SSH Connectivity Test
Direct testing using Paramiko SSH library without application services.

**What It Tests**:
- Direct connection to each R-Pi device
- SSH tunnel creation via R-Pi to target devices
- Command execution on target devices (cat /version.txt)
- Parallel execution without blocking

**Usage**:
```bash
python3 test_parallel_rpi_ssh.py
```

**Expected Output**:
```
[✓] Successfully connected to DESK-R-Pi
[✓] Successfully accessed OD-AB (DESK)
[✓] Successfully accessed DESK-LAB (17-97)
[✓] Successfully connected to CELLO-R-Pi
[✓] Successfully accessed CELLO-SKY
Success Rate: 100% - ALL TESTS PASSED ✓
```

### 2. **test_app_parallel_rpi_ssh.py** - Application Integration Test
Tests using the application's `GDFRPiShellService` (same service used by actual job execution).

**What It Tests**:
- Application's tunnel service initialization
- SSHTunnelForwarder configuration and lifecycle
- Port forwarding to multiple devices
- Command execution via application services
- Connection time measurements

**Usage**:
```bash
python3 test_app_parallel_rpi_ssh.py
```

**Expected Output**:
```
[INFO] [DESK] Initializing tunnel to OD-AB (DESK)...
[✓] [DESK] Tunnel established
[✓] [DESK] Version info retrieved
[INFO] Average Connection Time: 3.45s
Success Rate: 100% - ALL TESTS PASSED ✓
```

### 3. **run_rpi_ssh_tests.sh** - Test Runner Script
Wrapper script that checks dependencies, runs tests, and displays results.

**Usage**:
```bash
# Run standalone SSH test
./run_rpi_ssh_tests.sh standalone

# Run application integration test
./run_rpi_ssh_tests.sh app

# Run both tests sequentially
./run_rpi_ssh_tests.sh both

# Check dependencies only
./run_rpi_ssh_tests.sh check

# Show help
./run_rpi_ssh_tests.sh help
```

## Test Execution Flow

### Standalone Test Flow
```
1. Initialize Paramiko SSH client
2. Connect to DESK R-Pi (10.138.17.42:60201)
   └─ Execute hostname command (verify connection)
3. Create SSH tunnel through DESK R-Pi to OD-AB (10.0.0.140)
   └─ Connect via tunnel and execute cat /version.txt
4. Create SSH tunnel through DESK R-Pi to DESK LAB (10.0.0.28)
   └─ Connect via tunnel and execute cat /version.txt
5. Repeat steps 2-4 for CELLO infrastructure (parallel)
6. Report connection times, success rates, and version info
```

### Application Integration Test Flow
```
1. Initialize GDFRPiShellService with DESK R-Pi config
2. Call tunnel_service.connect()
   └─ Establishes SSHTunnelForwarder to OD-AB via DESK R-Pi
   └─ Sets up port forwarding (127.0.0.1:10022 → 10.0.0.140:10022)
3. Execute command on device: cat /version.txt
4. Retrieve output through tunnel
5. Call tunnel_service.disconnect()
6. Repeat for all devices (parallel in background threads)
7. Report tunnel status, connection times, and command outputs
```

## Expected Results

### Success Criteria
- ✓ All 5 connections established (2 DESK devices + 1 CELLO device)
- ✓ All R-Pi SSH authentications successful
- ✓ All device SSH tunnels created and working
- ✓ All commands executed and returned output
- ✓ No connection conflicts or timeouts
- ✓ Parallel execution completes within 60 seconds

### Typical Output Metrics
```
Total R-Pi Tests: 3 (2 for DESK, 1 for CELLO)
Total Devices Tested: 5 (2 DESK + 1 CELLO per R-Pi) 
Successful Connections: 5/5 (100%)
Average Connection Time: 2-4 seconds per tunnel
Total Execution Time: 15-30 seconds (parallel)
```

## Requirements

### Python Packages
```bash
pip install paramiko==3.4.0
pip install sshtunnel
```

### Network Requirements
- Access to DESK R-Pi: `10.138.17.42:60201`
- Access to CELLO R-Pi: `10.26.52.60:22`
- Access to devices: 10.0.0.28, 10.0.0.95, 10.0.0.140
- SSH keys or passwords configured for all hosts

### Credentials
Credentials are embedded in the test scripts:
- **DESK R-Pi**: `pi:Eastcoast-Goldfish-Progress`
- **CELLO R-Pi**: `lrqa:Viswa123!`
- **Target Devices**: `root:` (SSH key-based auth)

## Troubleshooting

### Connection Timeout
```
Error: timed out (Connection refused)
→ Check network connectivity to R-Pi
→ Verify R-Pi IP and port are correct
→ Check firewall rules on R-Pi
```

### Authentication Failed
```
Error: Authentication failed
→ Verify username and password in script
→ Check if SSH key-based auth is required
→ Verify SSH service is running on R-Pi
```

### Tunnel Timeout
```
Error: Tunnel operation timed out
→ Increase timeout value in script
→ Check if device is reachable through R-Pi
→ Verify forwarding rules on R-Pi
```

### Command Execution Error
```
Error: Remote command failed
→ Check if /version.txt exists on device
→ Verify device is accessible via tunnel
→ Check user permissions on device
```

## Application Integration

These tests validate that your application's SSH infrastructure can:

1. **Create Multiple Tunnels**: Establish simultaneous SSH tunnels to different R-Pi devices
2. **Execute Commands**: Run commands on target devices through tunnels
3. **Handle Failures**: Gracefully handle connection failures and timeouts
4. **Measure Performance**: Track connection times and success rates
5. **Run in Parallel**: Execute multiple connections without blocking

### Integration with Job Execution
- Jobs that execute on DESK devices use DESK R-Pi tunnel
- Jobs that execute on CELLO devices use CELLO R-Pi tunnel
- Multiple jobs can run simultaneously on different R-Pi infrastructures
- Each job maintains its own SSH tunnel for isolation

## Performance Benchmarks

### Expected Connection Times
- DESK R-Pi SSH connect: 1-2 seconds
- Tunnel via DESK R-Pi: 2-3 seconds
- Device SSH connect through tunnel: 1-2 seconds
- Command execution: < 1 second
- **Total per device**: 2-4 seconds

### Parallel Execution
- Sequential execution (3 devices): 9-12 seconds
- Parallel execution (3 devices): 4-6 seconds
- **Parallelization improvement**: ~50-60%

## Running on Application Server

To run on your LRQA application server:

```bash
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard

# Check dependencies
bash run_rpi_ssh_tests.sh check

# Run both test suites
bash run_rpi_ssh_tests.sh both

# View results
# All outputs are sent to stdout with color coding
```

## Continuous Testing

To run tests periodically:

```bash
# Add to crontab for daily testing at 2 AM
0 2 * * * cd /path/to/app && bash run_rpi_ssh_tests.sh both >> test_results.log 2>&1

# Or run via systemd timer (recommended)
# Create: /etc/systemd/system/rpi-ssh-test.timer
# Create: /etc/systemd/system/rpi-ssh-test.service
```

## Logs and Output

Test results include:
- Connection success/failure status
- Device hostnames retrieved
- Version information from /version.txt
- Connection timing information
- Error messages and stack traces
- Statistical summary

All output is color-coded:
- 🟢 Green: Successful operations
- 🔴 Red: Failed operations
- 🟡 Yellow: Warnings
- 🔵 Blue: Informational messages

## Security Notes

⚠️ **Important**: 
- Credentials are hardcoded in scripts - use only in secure environments
- For production, integrate with credential management system
- Consider using SSH key-based authentication instead of passwords
- Restrict script access to authorized personnel only

---

**Created**: August 11, 2026
**Version**: 1.0
**Status**: Ready for Testing
