# SSH Tunnel Service Pattern - Reusable Abstraction for All Methods
**Date:** 7 August 2026  
**Purpose**: Standardize SSH usage across all methods using R-Pi tunneling + device SSH + command execution  
**Status:** ✅ READY FOR IMPLEMENTATION

---

## 🎯 Problem: Why Standardization Needed

### Current State (Scattered SSH Usage)
```
method_reboot_perf_v2_optimized.py
  ├─ Direct paramiko SSH
  ├─ Manual tunnel setup
  ├─ Custom error handling
  └─ No code reuse
  
method_check_logs.py
  ├─ Direct paramiko SSH (duplicate code!)
  ├─ Manual tunnel setup
  ├─ Different error handling
  └─ No code reuse
  
method_system_command.py
  ├─ Direct paramiko SSH (duplicate code!)
  ├─ Manual tunnel setup
  ├─ Different error handling
  └─ No code reuse
  
method_execute_command.py
  ├─ Direct paramiko SSH (duplicate code!)
  └─ ... and so on
```

### Solution: Universal SSH Service
```
UNIVERSAL SSH SERVICE
├─ R-Pi Tunnel Management
├─ Device SSH Connection
├─ Command Execution
├─ Output Fetching
├─ Error Handling
└─ Automatic Reconnection

     ↓ Used by ALL methods

method_reboot_perf_v2_optimized.py ──┐
method_check_logs.py ─────────────────┤
method_system_command.py ──────────────┼─→ SSHCommandService()
method_execute_command.py ─────────────┤
method_deepsleep.py ────────────────────┤
method_soft_hard_boot.py ───────────────┘
... and all other SSH-based methods
```

---

## 🏗️ Architecture: Reusable SSH Service

### Abstraction Layers

```
┌─────────────────────────────────────┐
│   Method (e.g., check_logs.py)      │
│   ├─ Load device config             │
│   ├─ Initialize SSHCommandService   │
│   └─ Execute SSH commands           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  SSHCommandService (NEW)            │
│  ├─ connect_via_tunnel()           │
│  ├─ execute_command()              │
│  ├─ fetch_output()                 │
│  ├─ execute_and_get_output()       │ ← One-liner
│  └─ disconnect()                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  GDFSSHTunnelService (Existing)     │
│  ├─ connect() - R-Pi tunnel        │
│  ├─ execute_command() - Device SSH │
│  └─ disconnect()                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Native SSH (subprocess)            │
│  └─ -L port forwarding              │
└─────────────────────────────────────┘
```

---

## 📋 Implementation Plan

### Phase 1: Create Universal SSH Service (5 files)

#### File 1: `/services/ssh_command_service.py` (NEW)
**Purpose**: High-level SSH command execution wrapper  
**Size**: 300-400 lines

```python
class SSHCommandService:
    """
    Universal SSH command execution service
    Handles tunnel setup, command execution, and output fetching
    """
    
    def __init__(self, device_config, log_callback=None):
        """
        Initialize SSH service with device configuration
        
        Args:
            device_config: {
                "lab_ip": "10.0.0.28",
                "lab_port": 22,
                "lab_username": "root",
                "lab_password": "encrypted",
                "rpi_config": {
                    "rpi_ip": "10.138.17.42",
                    "rpi_port": 60201,
                    "rpi_username": "pi"
                }
            }
            log_callback: Optional logging function
        """
    
    def connect(self):
        """Establish tunnel and SSH connection"""
    
    def execute_command(self, command, timeout=10):
        """Execute single command and return output"""
    
    def execute_and_get_output(self, command, timeout=10):
        """ONE-LINER: Execute command and return (success, output, error)"""
    
    def execute_with_parsing(self, command, parser_func=None, timeout=10):
        """Execute command and parse output with custom parser"""
    
    def execute_multiple_commands(self, commands_list, timeout=10):
        """Execute series of commands sequentially"""
    
    def get_file_content(self, remote_path, timeout=10):
        """Retrieve entire file content via SSH"""
    
    def fetch_command_output(self, command, lines_count=100):
        """Fetch last N lines from command output"""
    
    def is_connected(self):
        """Check if SSH connection is alive"""
    
    def disconnect(self):
        """Clean shutdown of tunnel and SSH"""
```

---

## 📝 Code Examples

### Example 1: Using in method_check_logs.py (Simple)

**Before (Current - Direct Paramiko):**
```python
def execute_check_logs(device_ip, port, username, password, 
                      selected_patterns=None, log_callback=None):
    # Manual SSH setup
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(device_ip, port=port, username=username, password=password)
    
    # Manual command execution
    stdin, stdout, stderr = ssh.exec_command("grep 'HOME' /opt/logs/sky-messages.log")
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    # Manual cleanup
    ssh.close()
    
    return {
        'success': True if output else False,
        'output': output,
        'error': error
    }
```

**After (Using SSHCommandService - R-Pi Tunnel):**
```python
def execute_check_logs(device_ip, port, username, password, 
                      selected_patterns=None, log_callback=None,
                      rpi_config=None):  # ← NEW PARAMETER
    
    # Load device config (could come from Device model)
    device_config = {
        "lab_ip": device_ip,
        "lab_port": port,
        "lab_username": username,
        "lab_password": password,
        "rpi_config": rpi_config  # ← NEW: R-Pi tunnel info
    }
    
    # Initialize service
    ssh_service = SSHCommandService(device_config, log_callback)
    
    try:
        # Connect through R-Pi tunnel
        ssh_service.connect()
        
        # ONE-LINER execution
        success, output, error = ssh_service.execute_and_get_output(
            "grep 'HOME' /opt/logs/sky-messages.log"
        )
        
        return {
            'success': success,
            'output': output,
            'error': error
        }
    finally:
        ssh_service.disconnect()
```

### Example 2: Using in method_system_command.py (Complex)

**Before (Current):**
```python
def execute_system_command(device_ip, port, username, password, 
                          command="whoami", log_callback=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(device_ip, port=port, username=username, password=password)
    
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()
        
        return {
            'success': True if not error else False,
            'command': command,
            'output': output,
            'error': error
        }
    finally:
        ssh.close()
```

**After (Using SSHCommandService):**
```python
def execute_system_command(device_ip, port, username, password, 
                          command="whoami", log_callback=None,
                          rpi_config=None):  # ← NEW
    
    device_config = {
        "lab_ip": device_ip,
        "lab_port": port,
        "lab_username": username,
        "lab_password": password,
        "rpi_config": rpi_config
    }
    
    ssh_service = SSHCommandService(device_config, log_callback)
    
    try:
        ssh_service.connect()
        
        # Tuple unpacking for clarity
        success, output, error = ssh_service.execute_and_get_output(
            command,
            timeout=30
        )
        
        return {
            'success': success,
            'command': command,
            'output': output,
            'error': error
        }
    finally:
        ssh_service.disconnect()
```

### Example 3: Using in method_deepsleep.py (With Parsing)

**Before (Current):**
```python
def execute_deepsleep(device_ip, port, username, password, log_callback=None):
    ssh = paramiko.SSHClient()
    ssh.connect(device_ip, port=port, username=username, password=password)
    
    # Check if in deepsleep
    stdin, stdout, stderr = ssh.exec_command("cat /proc/power_mode")
    power_mode = stdout.read().decode('utf-8').strip()
    
    if "deepsleep" in power_mode.lower():
        status = "IN_DEEPSLEEP"
    else:
        status = "AWAKE"
    
    ssh.close()
    
    return {'status': status}
```

**After (Using SSHCommandService):**
```python
def execute_deepsleep(device_ip, port, username, password, 
                     log_callback=None, rpi_config=None):  # ← NEW
    
    device_config = {
        "lab_ip": device_ip,
        "lab_port": port,
        "lab_username": username,
        "lab_password": password,
        "rpi_config": rpi_config
    }
    
    ssh_service = SSHCommandService(device_config, log_callback)
    
    try:
        ssh_service.connect()
        
        # Custom parser function
        def parse_power_mode(output):
            return "IN_DEEPSLEEP" if "deepsleep" in output.lower() else "AWAKE"
        
        # Execute with parser
        status = ssh_service.execute_with_parsing(
            "cat /proc/power_mode",
            parser_func=parse_power_mode
        )
        
        return {'status': status}
    finally:
        ssh_service.disconnect()
```

### Example 4: Using in method_reboot_perf_v2_optimized.py (Current Pattern)

**Current direct usage already exists but can be improved:**
```python
def execute_reboot(device_ip, port, username, password, 
                  rpi_config=None, log_callback=None, tunnel_service=None):
    
    # If no tunnel_service provided, create one
    if not tunnel_service:
        device_config = {
            "lab_ip": device_ip,
            "lab_port": port,
            "lab_username": username,
            "lab_password": password,
            "rpi_config": rpi_config
        }
        tunnel_service = SSHCommandService(device_config, log_callback)
        tunnel_service.connect()
        cleanup_needed = True
    else:
        cleanup_needed = False
    
    try:
        # Execute reboot command
        success, output, error = tunnel_service.execute_and_get_output(
            "reboot",
            timeout=5
        )
        
        log_callback(f"Reboot command sent: {success}")
        
        # Now wait and monitor
        time.sleep(10)
        
        # Check if device is back up
        uptime_success, uptime_output, _ = tunnel_service.execute_and_get_output(
            "uptime",
            timeout=5
        )
        
        if uptime_success:
            return {'success': True, 'uptime': uptime_output}
        
        return {'success': False}
    
    finally:
        if cleanup_needed:
            tunnel_service.disconnect()
```

### Example 5: Batch Commands with Error Handling

```python
def batch_system_checks(device_ip, port, username, password, 
                       rpi_config=None, log_callback=None):
    """
    Execute multiple commands and collect results
    """
    
    device_config = {
        "lab_ip": device_ip,
        "lab_port": port,
        "lab_username": username,
        "lab_password": password,
        "rpi_config": rpi_config
    }
    
    ssh_service = SSHCommandService(device_config, log_callback)
    
    try:
        ssh_service.connect()
        
        # List of commands to execute
        commands = [
            ("whoami", "Get current user"),
            ("df -h", "Check disk space"),
            ("free -h", "Check memory"),
            ("uptime", "Check uptime"),
            ("cat /proc/version", "Check kernel version"),
        ]
        
        results = {}
        for cmd, description in commands:
            log_callback(f"Executing: {description}")
            
            success, output, error = ssh_service.execute_and_get_output(cmd)
            
            results[description] = {
                'command': cmd,
                'success': success,
                'output': output[:500],  # Limit size
                'error': error[:500]
            }
        
        return {'success': True, 'results': results}
    
    finally:
        ssh_service.disconnect()
```

---

## 🔄 Migration Path for Existing Methods

### Step 1: Update Method Signature

**Old Signature:**
```python
def execute_check_logs(device_ip, port, username, password, 
                      selected_patterns=None, log_callback=None, 
                      job_id=None):
```

**New Signature:**
```python
def execute_check_logs(device_ip, port, username, password, 
                      selected_patterns=None, log_callback=None, 
                      job_id=None,
                      tunnel_service=None,  # ← NEW: Optional pre-initialized service
                      rpi_config=None,      # ← NEW: R-Pi tunnel config
                      device_config=None):  # ← NEW: Full device config
```

### Step 2: Add Initialization Logic

```python
def execute_check_logs(..., tunnel_service=None, rpi_config=None, device_config=None):
    
    # If full device_config provided, use it
    if device_config:
        config = device_config
    # If rpi_config provided, build from pieces
    elif rpi_config:
        config = {
            "lab_ip": device_ip,
            "lab_port": port,
            "lab_username": username,
            "lab_password": password,
            "rpi_config": rpi_config
        }
    # If service provided, use it
    elif tunnel_service:
        ssh_service = tunnel_service
        cleanup_needed = False
    # Default: create basic config
    else:
        config = {
            "lab_ip": device_ip,
            "lab_port": port,
            "lab_username": username,
            "lab_password": password,
            "rpi_config": None  # ← Will use direct connection
        }
    
    # Initialize service if not provided
    if tunnel_service is None:
        ssh_service = SSHCommandService(config, log_callback)
        cleanup_needed = True
    else:
        cleanup_needed = False
    
    try:
        if cleanup_needed:
            ssh_service.connect()
        
        # Execute commands using ssh_service
        success, output, error = ssh_service.execute_and_get_output(
            "your_command_here"
        )
        
        return {'success': success, 'output': output}
    
    finally:
        if cleanup_needed:
            ssh_service.disconnect()
```

### Step 3: Backward Compatibility

All changes are **fully backward compatible**:
- Old calls without R-Pi config continue to work
- New parameters are optional
- Existing code doesn't break

---

## 📊 Methods That Should Use This Pattern

### High Priority (Use SSH heavily)
| Method | Current SSH Usage | Benefit |
|--------|------------------|---------|
| method_reboot_perf_v2_optimized.py | Check uptime, get logs | ✅ Already improved |
| method_check_logs.py | Grep log files | ✅ Reduces code |
| method_system_command.py | Execute system commands | ✅ Standardizes |
| method_deepsleep.py | Check power mode | ✅ Improves reliability |
| method_execute_command.py | Custom commands | ✅ Adds R-Pi support |

### Medium Priority (Use SSH occasionally)
| Method | Current Usage |
|--------|---------------|
| method_soft_hard_boot.py | Reboot commands |
| method_trail.py | Log checking |
| method_standby_deep_sleep_ir_control.py | Power state check |

### Future Enhancement
| Method | Potential |
|--------|-----------|
| All methods with logging | Could add output capture |
| All methods with remote execution | Could use unified service |

---

## 🚀 Implementation Roadmap

### Phase 1: Create Core Service (3 days)
```
- Create /services/ssh_command_service.py
- Write unit tests
- Documentation
```

### Phase 2: Migration (2-3 days per method)
```
Week 1:
  - method_check_logs.py
  - method_system_command.py
  - method_execute_command.py

Week 2:
  - method_deepsleep.py
  - method_soft_hard_boot.py
  - Others
```

### Phase 3: Optimization (1-2 days)
```
- Session pooling (reuse connections)
- Output streaming (large files)
- Batch operations optimization
```

---

## 💡 Advanced Features

### Feature 1: Connection Pooling
```python
class SSHConnectionPool:
    """
    Reuse SSH connections across multiple commands
    Reduces connection overhead
    """
    
    def __init__(self, max_connections=5):
        self.pool = {}
        self.max_connections = max_connections
    
    def get_connection(self, device_config):
        """Get or create connection for device"""
        
    def release_connection(self, device_id):
        """Release connection back to pool"""
```

### Feature 2: Output Streaming
```python
class StreamingSSHCommand:
    """
    Stream large output files line-by-line
    Prevents memory overload
    """
    
    def execute_streaming(self, command, callback=None):
        """Execute command and stream output"""
```

### Feature 3: Command Queuing
```python
class QueuedSSHService:
    """
    Queue commands and execute sequentially
    Better for high-volume operations
    """
    
    def queue_command(self, command):
        """Add to queue"""
    
    def execute_all(self):
        """Execute all queued commands"""
```

---

## 📋 Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Code Reuse** | ~50% duplicate SSH code | ~0% duplication |
| **R-Pi Support** | Only in tunnel service | All methods |
| **Error Handling** | Inconsistent | Standardized |
| **Maintenance** | Fix multiple files | Fix once |
| **New Methods** | Copy-paste pattern | Use service |
| **Testing** | Test each method | Test service once |
| **Timeout Handling** | Per-method logic | Central logic |
| **Reconnection** | Manual per-method | Automatic |
| **Documentation** | Scattered | Centralized |

---

## 🔧 Integration with test_execution_service.py

### How Execution Service Provides Tunnel

```python
# In /services/test_execution_service.py

def run_execution(self, device, method, iterations, ...):
    
    # Load device configuration
    device_config = {
        "lab_ip": device.ip,
        "lab_port": device.port,
        "lab_username": device.username,
        "lab_password": device.password,
        "rpi_config": device.rpi_config
    }
    
    # Create tunnel service ONCE
    tunnel_service = SSHCommandService(device_config, log_service.log)
    tunnel_service.connect()
    
    try:
        # Method 1: method_reboot_perf_v2_optimized
        result = execute_reboot_perf_v2_optimized_process(
            device_ip=device.ip,
            tunnel_service=tunnel_service,  # ← Pass service
            ...
        )
        
        # Method 2: method_check_logs
        result = execute_check_logs(
            device_ip=device.ip,
            tunnel_service=tunnel_service,  # ← Pass service
            ...
        )
    
    finally:
        tunnel_service.disconnect()
```

### Benefits Over Per-Method Connection
```
❌ CURRENT (5 methods = 5 connections each):
   method_1() → connect → execute → disconnect
   method_2() → connect → execute → disconnect
   method_3() → connect → execute → disconnect
   ... overhead and timing issues ...

✅ WITH SHARED SERVICE (1 connection for all):
   connect() ← ONE connection
   ├─ method_1() → execute
   ├─ method_2() → execute
   ├─ method_3() → execute
   └─ disconnect() ← ONE disconnect
   ... faster, more reliable ...
```

---

## 📖 Quick Start Guide

### For Method Developers: Use SSH Service

**3-Step Process:**

```python
# Step 1: Initialize service
ssh_service = SSHCommandService(device_config, log_callback)

# Step 2: Connect
ssh_service.connect()

# Step 3: Execute (one-liner)
try:
    success, output, error = ssh_service.execute_and_get_output(
        "your command here"
    )
finally:
    ssh_service.disconnect()
```

### For Frameworks: Provide Tunnel Service

**Pass pre-initialized service to methods:**
```python
# Get config from device
device_config = device.to_ssh_config()

# Create service
tunnel = SSHCommandService(device_config, log)

# Pass to methods
method_result = execute_method(
    device_ip=device.ip,
    tunnel_service=tunnel,
    ...
)
```

---

## ✅ Implementation Checklist

```
Phase 1: Service Creation
  [ ] Create ssh_command_service.py
  [ ] Implement all 10 methods
  [ ] Write comprehensive docstrings
  [ ] Add error handling
  [ ] Create unit tests
  [ ] Write usage documentation

Phase 2: Integration
  [ ] Update method_check_logs.py
  [ ] Update method_system_command.py
  [ ] Update method_execute_command.py
  [ ] Update method_deepsleep.py
  [ ] Update method_soft_hard_boot.py
  [ ] Update other SSH-based methods

Phase 3: Testing
  [ ] Test each updated method
  [ ] Verify R-Pi tunnel works
  [ ] Test error scenarios
  [ ] Test recovery/reconnection
  [ ] Load testing (multiple connections)

Phase 4: Documentation
  [ ] Update method READMEs
  [ ] Add migration guide
  [ ] Create best practices doc
  [ ] Add troubleshooting guide
```

---

## 🎓 Usage Patterns

### Pattern 1: Simple Command
```python
ssh = SSHCommandService(config, log)
ssh.connect()
success, output, _ = ssh.execute_and_get_output("whoami")
ssh.disconnect()
```

### Pattern 2: With Error Handling
```python
ssh = SSHCommandService(config, log)
try:
    ssh.connect()
    success, output, error = ssh.execute_and_get_output("df -h")
    if not success:
        log(f"Error: {error}")
finally:
    ssh.disconnect()
```

### Pattern 3: Multiple Commands
```python
ssh = SSHCommandService(config, log)
try:
    ssh.connect()
    for cmd in ["uptime", "whoami", "pwd"]:
        success, output, _ = ssh.execute_and_get_output(cmd)
        log(f"{cmd}: {output}")
finally:
    ssh.disconnect()
```

### Pattern 4: Shared Service (Recommended)
```python
# In test_execution_service.py
ssh = SSHCommandService(config, log)
try:
    ssh.connect()
    # Multiple methods use same connection
    method1_result = method1(tunnel_service=ssh, ...)
    method2_result = method2(tunnel_service=ssh, ...)
    method3_result = method3(tunnel_service=ssh, ...)
finally:
    ssh.disconnect()
```

---

## Summary

✅ **YES - This pattern can absolutely be reused across all methods!**

### Key Advantages:
1. **Unified R-Pi Tunneling** - All methods get tunnel support
2. **Code Reduction** - Eliminate 50% duplicate SSH code
3. **Standardization** - Consistent error handling everywhere
4. **Maintainability** - Fix bugs once, benefit everywhere
5. **Performance** - Connection reuse, batch operations
6. **Reliability** - Automatic reconnection, timeout handling

### Next Steps:
1. Create `/services/ssh_command_service.py`
2. Update high-priority methods (check_logs, system_command, execute_command)
3. Extend to remaining methods
4. Optimize with connection pooling
5. Document best practices

---

**Document Version**: 1.0  
**Implementation Status**: Ready for Development  
**Estimated Effort**: 2 weeks for complete migration
