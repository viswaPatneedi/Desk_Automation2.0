# Multi-R-Pi SSH Configuration Reference

## Active Configuration (August 11, 2026)

### DESK R-Pi Infrastructure (CELLO Control)

#### R-Pi Host Details
```
R-Pi IP       : 10.26.52.60
R-Pi Port     : 22
R-Pi Username : lrqa
R-Pi Password : Viswa123!
```

#### Controlled Devices
```
Device Name   : CELLO-SKY
Device IP     : 10.0.0.95
Device Port   : 10022
Device User   : root
```

#### Connection Command (Reference)
```bash
# Direct connection to DESK R-Pi
ssh -p 22 lrqa@10.26.52.60

# Via tunnel to CELLO-SKY (from DESK R-Pi)
ssh -L 10022:10.0.0.95:10022 lrqa@10.26.52.60 -p 22
ssh -p 10022 root@127.0.0.1 "cat /version.txt"
```

---

### LAB R-Pi Infrastructure (Lab Device Control)

#### R-Pi Host Details
```
R-Pi IP       : 10.138.17.42
R-Pi Port     : 60201
R-Pi Username : pi
R-Pi Password : Eastcoast-Goldfish-Progress
```

#### Controlled Devices
```
Device Name   : DT-XIONE_UK-0D-AB
Device IP     : 10.0.0.140
Device Port   : 10022
Device User   : root
```

#### Connection Command (Reference)
```bash
# Direct connection to LAB R-Pi
ssh -p 60201 pi@10.138.17.42

# Via tunnel to DT-XIONE device (from LAB R-Pi)
ssh -L 10022:10.0.0.140:10022 pi@10.138.17.42 -p 60201
ssh -p 10022 root@127.0.0.1 "cat /version.txt"
```

---

## Test Scripts Using This Configuration

### 1. test_parallel_rpi_ssh.py
Raw SSH testing using Paramiko library directly.

**Configuration Used:**
- DESK R-Pi: 10.26.52.60:22 (lrqa/Viswa123!)
- LAB R-Pi: 10.138.17.42:60201 (pi/Eastcoast-Goldfish-Progress)
- Target Devices: CELLO-SKY (10.0.0.95), DT-XIONE_UK-0D-AB (10.0.0.140)

**Initialization in Code:**
```python
self.desk_rpi = {
    'name': 'DESK-R-Pi',
    'ip': '10.26.52.60',
    'port': 22,
    'username': 'lrqa',
    'password': 'Viswa123!',
    'devices': [{'name': 'CELLO-SKY', 'ip': '10.0.0.95', ...}]
}

self.lab_rpi = {
    'name': 'LAB-R-Pi',
    'ip': '10.138.17.42',
    'port': 60201,
    'username': 'pi',
    'password': 'Eastcoast-Goldfish-Progress',
    'devices': [{'name': 'DT-XIONE_UK-0D-AB', 'ip': '10.0.0.140', ...}]
}
```

### 2. test_app_parallel_rpi_ssh.py
Application integration testing using GDFRPiShellService.

**Configuration Used:**
- DESK R-Pi: 10.26.52.60:22 (lrqa/Viswa123!)
- LAB R-Pi: 10.138.17.42:60201 (pi/Eastcoast-Goldfish-Progress)
- Same device targets as above

**Initialization in Code:**
```python
self.desk_rpi_config = {
    'rpi_ip': '10.26.52.60',
    'rpi_port': 22,
    'rpi_username': 'lrqa',
    'rpi_password': 'Viswa123!'
}

self.lab_rpi_config = {
    'rpi_ip': '10.138.17.42',
    'rpi_port': 60201,
    'rpi_username': 'pi',
    'rpi_password': 'Eastcoast-Goldfish-Progress'
}
```

---

## Network Connectivity Verification

### Direct R-Pi SSH Tests
```bash
# DESK R-Pi connectivity
timeout 5 ssh -p 22 lrqa@10.26.52.60 "echo 'DESK R-Pi OK'; hostname"

# LAB R-Pi connectivity  
timeout 5 ssh -p 60201 pi@10.138.17.42 "echo 'LAB R-Pi OK'; hostname"
```

### Device Access Through Tunnels
```bash
# CELLO-SKY through DESK R-Pi
ssh -L 10022:10.0.0.95:10022 -p 22 lrqa@10.26.52.60 -f sleep 30
ssh -p 10022 root@127.0.0.1 "cat /version.txt"

# DT-XIONE through LAB R-Pi
ssh -L 10022:10.0.0.140:10022 -p 60201 pi@10.138.17.42 -f sleep 30
ssh -p 10022 root@127.0.0.1 "cat /version.txt"
```

---

## Expected Test Outcomes

### Successful Connection Flow
1. **DESK R-Pi Connection** → ✓ Connected
2. **Create tunnel to CELLO-SKY** → ✓ Tunnel established
3. **Execute commands on CELLO-SKY** → ✓ Hostname and version retrieved
4. **LAB R-Pi Connection** → ✓ Connected
5. **Create tunnel to DT-XIONE** → ✓ Tunnel established
6. **Execute commands on DT-XIONE** → ✓ Hostname and version retrieved

### Success Metrics
```
Total R-Pi Tests:        2
Total Devices Tested:    2
Successful Connections:  2/2 (100%)
Average Connection Time: 2-4 seconds per tunnel
Total Execution Time:    15-30 seconds (parallel)
```

---

## Troubleshooting Reference

### DESK R-Pi Connection Issues
**Error**: "Connection refused" 
```
→ Verify network access to 10.26.52.60:22
→ Check firewall rules on DESK R-Pi
→ Confirm lrqa user can SSH with password auth
```

**Error**: "Authentication failed"
```
→ Verify password: Viswa123!
→ Confirm username: lrqa
→ Check if password authentication is enabled on R-Pi
```

### LAB R-Pi Connection Issues
**Error**: "Connection timeout"
```
→ Verify network access to 10.138.17.42:60201
→ Check non-standard port (60201) is accessible
→ Confirm firewall allows port 60201
```

**Error**: "Password authentication refused"
```
→ Verify password: Eastcoast-Goldfish-Progress
→ Confirm username: pi
→ Check SSH configuration on LAB R-Pi
```

### Device Access Through Tunnel Issues
**Error**: "Tunnel timeout or connection refused"
```
→ Confirm R-Pi connection is working first
→ Verify device IP and port are correct
→ Check that R-Pi can reach target device
→ Verify SSH is running on target device
```

**Error**: "cat: /version.txt: No such file or directory"
```
→ File may not exist on all devices
→ This is expected - test continues without error
→ Try alternative command: 'echo "version test OK"'
```

---

## Files Modified/Created

### Test Scripts
- `test_parallel_rpi_ssh.py` - Raw Paramiko SSH tests
- `test_app_parallel_rpi_ssh.py` - Application integration tests  
- `run_rpi_ssh_tests.sh` - Bash test runner wrapper

### Documentation
- `MULTI_RPI_SSH_TEST_GUIDE.md` - Comprehensive test guide
- `QUICK_START_RPI_TEST.sh` - Quick reference script
- `RPI_SSH_CONFIG_REFERENCE.md` - This file

### Scripts Location
```
/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/
```

---

## Running Tests

### Quick Start
```bash
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard

# Run all tests
bash run_rpi_ssh_tests.sh both

# Or individually
python3 test_parallel_rpi_ssh.py
python3 test_app_parallel_rpi_ssh.py
```

### Expected Output
```
======================================================================
  PARALLEL MULTI-R-Pi SSH CONNECTION TEST
======================================================================

[INFO] Testing simultaneous connections to multiple R-Pi infrastructures
[INFO] Start time: 2026-08-11 07:51:20

======================================================================
  DESK R-Pi Infrastructure (CELLO Devices)
======================================================================

[✓] Successfully connected to DESK-R-Pi
[✓] Tunnel established: 127.0.0.1:10022 → 10.0.0.95:10022
[✓] Successfully accessed CELLO-SKY

======================================================================
  LAB R-Pi Infrastructure (Lab Devices)
======================================================================

[✓] Successfully connected to LAB-R-Pi
[✓] Tunnel established: 127.0.0.1:10022 → 10.0.0.140:10022
[✓] Successfully accessed DT-XIONE_UK-0D-AB

======================================================================
  STATISTICS
======================================================================

Total R-Pi Tests: 2
Total Devices Tested: 2
Successful Connections: 2/2
Success Rate: 100% - ALL TESTS PASSED ✓
```

---

## Last Updated
- **Date**: August 11, 2026
- **Configuration**: Desk R-Pi / LAB R-Pi Dual Infrastructure
- **Status**: ✓ Ready for Testing
