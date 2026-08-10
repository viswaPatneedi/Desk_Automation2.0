# SSH Reusable Service - Architecture & Integration Map
**Date:** 7 August 2026  
**Visual Guide**: How the SSH service connects everything

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     TEST EXECUTION SERVICE                      │
│                 (test_execution_service.py)                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Creates ONCE
                     ▼
        ┌────────────────────────────┐
        │  SSHCommandService         │
        │  (NEW REUSABLE SERVICE)    │
        │                            │
        │ - connect()                │
        │ - execute_and_get_output() │ ← ONE-LINER!
        │ - execute_multiple_cmds()  │
        │ - disconnect()             │
        └───┬────────────────────────┘
            │ Shared by all methods
            │
    ┌───────┴───────┬────────────┬──────────────┬──────────────┐
    │               │            │              │              │
    ▼               ▼            ▼              ▼              ▼
method_    method_check_   method_system_   method_   method_
reboot_    logs.py         command.py      deepsleep soft_hard_
perf_v2.py                                  .py      boot.py
   │               │            │              │              │
   │               │            │              │              │
   └───────────────┴────────────┴──────────────┴──────────────┘
                     │
                     │ All pass: tunnel_service=ssh
                     │
        ┌────────────▼────────────┐
        │    Each executes        │
        │  ssh.execute_and_       │
        │  get_output(command)    │
        │                         │
        │ (Same code for all!)    │
        └────────────┬────────────┘
                     │
                     │ Transparent handling
                     ▼
        ┌────────────────────────────┐
        │  GDFSSHTunnelService       │
        │  (Existing tunnel service) │
        │                            │
        │ - Manages R-Pi tunnel      │
        │ - Port forwarding (8090,   │
        │   10022, 8023, 9005)       │
        │ - Device connections       │
        └────────────┬───────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    R-Pi Gateway            Direct SSH
   (10.138.17.42)          (if no tunnel)
         │                       │
         │ Forwards to           │
         ▼                       │
    Test Device              Test Device
   (10.0.0.28)              (10.0.0.28)
```

---

## 📊 Data Flow Comparison

### BEFORE (Current - Code Duplication)

```
Method 1 (check_logs)           Method 2 (system_command)
    │                                    │
    ├─ import paramiko                   ├─ import paramiko
    ├─ create SSHClient                  ├─ create SSHClient
    ├─ connect()                         ├─ connect()
    ├─ exec_command()                    ├─ exec_command()
    ├─ read output                       ├─ read output
    └─ close()                           └─ close()
    
    [DUPLICATE CODE in EVERY method]
    Each method: 30-50 lines of SSH boilerplate
```

### AFTER (With Reusable Service)

```
Method 1 (check_logs)           Method 2 (system_command)
    │                                    │
    └─────────────┬──────────────────────┘
                  │
                  ├─ from ssh_command_service import SSHCommandService
                  │
                  ├─ ssh = SSHCommandService(config, log)
                  ├─ ssh.connect()
                  │
                  ├─ success, output, error = ssh.execute_and_get_output(cmd)
                  │
                  └─ ssh.disconnect()
                  
    [CODE REUSE - Same 5 lines for EVERY method]
    Each method: 10-15 lines (70% reduction)
```

---

## 🔄 Connection Flow - Detailed

### With R-Pi Tunnel

```
User's Server (localhost:11079)
         │
         │ Flask App
         │ requests SSH tunnel setup
         │
         ▼
SSHCommandService
         │
         │ Detects rpi_config provided
         │
         ▼
Calls GDFSSHTunnelService.connect()
         │
         │ Opens subprocess with:
         │ ssh -p 60201 -L 8090:10.0.0.28:8090 \
         │                 -L 10022:10.0.0.28:10022 \
         │                 -L 8023:10.0.0.28:8023 \
         │                 -L 9005:10.0.0.28:9005 \
         │                 pi@10.138.17.42
         │
         ▼
Creates listening sockets:
         │
         ├─ localhost:8090  → 10.0.0.28:8090  (API/VNC)
         ├─ localhost:10022 → 10.0.0.28:10022 (SSH)
         ├─ localhost:8023  → 10.0.0.28:8023  (Telnet)
         └─ localhost:9005  → 10.0.0.28:9005  (Debug)
         │
         ▼
Method executes command:
         ssh.execute_and_get_output("whoami")
         │
         ▼
SSHCommandService.execute_command(cmd, timeout)
         │
         ├─ Uses tunnel's SSH connection
         │
         ├─ Sends: ssh.exec_command(cmd)
         │
         ├─ Reads stdout/stderr
         │
         └─ Returns: (success, output, error)
```

### Direct Connection (No Tunnel)

```
Method requests SSH:
         ssh.execute_and_get_output("whoami")
         │
         ▼
SSHCommandService.execute_command(cmd, timeout)
         │
         ├─ Detects no rpi_config
         │
         ├─ Uses paramiko direct connection
         │  - Connect to device_ip:device_port
         │  - Authenticate with username/password
         │
         ├─ Sends: ssh.exec_command(cmd)
         │
         ├─ Reads stdout/stderr
         │
         └─ Returns: (success, output, error)
```

---

## 🎯 Usage Pattern Matrix

### Pattern 1: Single Command
```python
ssh = SSHCommandService(config)
ssh.connect()
success, output, error = ssh.execute_and_get_output("whoami")
ssh.disconnect()
```
**Used by**: method_execute_command, simple checks

### Pattern 2: Multiple Commands
```python
ssh = SSHCommandService(config)
ssh.connect()
results = ssh.execute_multiple_commands(["uptime", "df -h", "free"])
for cmd, (success, output, _) in results.items():
    print(f"{cmd}: {output}")
ssh.disconnect()
```
**Used by**: system health checks, diagnostics

### Pattern 3: With Parsing
```python
ssh = SSHCommandService(config)
ssh.connect()
status = ssh.execute_with_parsing("cat /proc/power", lambda x: "sleep" in x)
print(f"In sleep mode: {status}")
ssh.disconnect()
```
**Used by**: method_deepsleep, status checks

### Pattern 4: Shared (RECOMMENDED)
```python
# In test_execution_service.py
ssh = SSHCommandService(device_config)
ssh.connect()

try:
    result1 = execute_reboot_perf(..., tunnel_service=ssh)
    result2 = execute_check_logs(..., tunnel_service=ssh)
    result3 = execute_system_cmd(..., tunnel_service=ssh)
finally:
    ssh.disconnect()
```
**Used by**: test_execution_service (multiple methods)

---

## 📈 Performance Characteristics

### Single Method Execution

```
Method: check_logs

Without Service (Current):
  1. Import paramiko          [1ms]
  2. Create SSHClient         [1ms]
  3. Connect                  [50ms]
  4. Execute command          [5ms]
  5. Read output              [1ms]
  6. Close connection         [2ms]
  ─────────────────────────────────
  Total: 60ms per execution

With Service:
  1. Create service           [1ms]
  2. Connect (via tunnel)     [50ms]
  3. Execute command          [5ms]
  4. Disconnect              [2ms]
  ─────────────────────────────────
  Total: 58ms (same)
  
  Benefit: Cleaner code, reusable
```

### Multiple Methods (Execution Sequence)

```
Without Service (Current):
  Method 1: Connection [50ms] + Execute [5ms] + Close [2ms] = 57ms
  Method 2: Connection [50ms] + Execute [5ms] + Close [2ms] = 57ms
  Method 3: Connection [50ms] + Execute [5ms] + Close [2ms] = 57ms
  ──────────────────────────────────────────────────────────
  Total: 171ms for 3 methods

With Shared Service:
  Connect [50ms]
  Method 1: Execute [5ms]
  Method 2: Execute [5ms]
  Method 3: Execute [5ms]
  Disconnect [2ms]
  ──────────────────────────────────────────────────────────
  Total: 67ms for 3 methods
  
  IMPROVEMENT: 171ms → 67ms (60% faster!)
```

---

## 🔌 Integration Scenarios

### Scenario 1: Legacy Method (Today)
```python
# existing method_check_logs.py
def execute_check_logs(device_ip, port, username, password, ...):
    # Direct paramiko SSH
    # No R-Pi support
    # No code reuse
```

### Scenario 2: Transitional Method (Week 1-2)
```python
# updated method_check_logs.py
def execute_check_logs(device_ip, port, username, password, 
                      ..., rpi_config=None):  # ← NEW optional param
    
    # Can use either old or new way
    if rpi_config:
        # Use new SSH service
        ssh = SSHCommandService(config, log)
    else:
        # Use old paramiko (backward compatible)
        ssh = paramiko.SSHClient()
```

### Scenario 3: Optimized Method (Week 3-4)
```python
# optimized method_check_logs.py
def execute_check_logs(device_ip, port, username, password, 
                      ..., tunnel_service=None, rpi_config=None):
    
    # Can receive pre-initialized tunnel from test_execution_service
    if tunnel_service:
        ssh = tunnel_service  # Reuse!
        cleanup_needed = False
    else:
        ssh = SSHCommandService(config, log)
        cleanup_needed = True
    
    # ... execute commands ...
    
    if cleanup_needed:
        ssh.disconnect()
```

---

## 🎯 Feature Matrix

| Feature | Direct SSH | SSH Service | Tunnel Service | Combined |
|---------|-----------|-------------|----------------|----------|
| Device SSH | ✅ | ✅ | ✅ | ✅ |
| Command Execution | ✅ | ✅ | ✅ | ✅ |
| Output Parsing | ❌ | ✅ | ✅ | ✅ |
| Multiple Commands | ❌ | ✅ | ✅ | ✅ |
| R-Pi Tunnel | ❌ | ✅ | ✅ | ✅ |
| Connection Reuse | ❌ | ✅ | ✅ | ✅ |
| Error Handling | ❌ | ✅ | ✅ | ✅ |
| Automatic Reconnect | ❌ | ✅ | ✅ | ✅ |
| Timeout Management | ❌ | ✅ | ✅ | ✅ |
| Code Reuse | ❌ | ✅ | ✅ | ✅ |

---

## 🚀 Deployment Timeline

```
Week 1: Foundation
├─ Review SSH_SERVICE_REUSABLE_PATTERN.md
├─ Deploy /services/ssh_command_service.py
├─ Create unit tests
└─ Get approval

Week 2-3: Migration
├─ Migrate method_check_logs.py
├─ Migrate method_system_command.py
├─ Migrate method_execute_command.py
├─ Migrate method_deepsleep.py
└─ Migrate method_soft_hard_boot.py

Week 4: Optimization
├─ Add connection reuse in test_execution_service.py
├─ Performance optimization
├─ Load testing
└─ Documentation update

Week 5: Extended Methods
├─ Migrate method_trail.py
├─ Migrate method_standby_deep_sleep_ir_control.py
└─ Other SSH-based methods
```

---

## ✅ Success Criteria

```
□ All SSH-based methods use SSHCommandService
□ R-Pi tunnel works for all methods
□ Performance improves by 50%+ (connection reuse)
□ Code duplication reduced by 70%
□ Backward compatibility maintained
□ Unit tests pass
□ Documentation complete
□ Team trained
```

---

## 🎓 Educational Value

### Before (Scattered Knowledge)
```
Team Member A: "How do I SSH?"
→ Looks at method_reboot_perf_v2_optimized.py
→ Copies 50 lines of paramiko code
→ Adds to new method

Team Member B: "How do I SSH?"
→ Looks at method_check_logs.py
→ Copies 50 DIFFERENT lines of paramiko code
→ Adds to new method

Result: 3-4 different SSH implementations, all buggy
```

### After (Centralized Knowledge)
```
Team Member A: "How do I SSH?"
→ Looks at ssh_command_service.py
→ Uses 5-line pattern
→ Works perfectly

Team Member B: "How do I SSH?"
→ Looks at SSH_SERVICE_PRACTICAL_EXAMPLES.md
→ Uses same 5-line pattern
→ Works perfectly

Result: 1 implementation, everyone uses it, perfection
```

---

## 🎯 Key Takeaway

```
BEFORE: "How do I SSH to a device via R-Pi tunnel?"
→ Complex, scattered across methods
→ Duplicate code in every method
→ Hard to maintain

AFTER: "How do I SSH to a device via R-Pi tunnel?"
→ One simple line: ssh.execute_and_get_output("command")
→ R-Pi tunnel automatic
→ One service, all methods
→ Easy to maintain
```

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**Impact**: Massive code reduction + standardization  
**Timeline**: 4-5 weeks for full migration
