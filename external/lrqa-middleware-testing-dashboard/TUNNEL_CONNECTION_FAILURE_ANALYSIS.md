# Tunnel Connection Failure Analysis - Job 1ff29973-910d-41de-978d-c13a32b2b953

## Execution Summary

- **Job ID**: 1ff29973-910d-41de-978d-c13a32b2b953
- **Device**: DT_LAB_SKY_XIONE-UK-0D_AB (10.0.0.140)
- **Method**: reboot_perf_v2_optimized
- **Status**: ❌ FAILED in ~4 seconds
- **Error Time**: 2026-08-05T05:54:04

---

## Error Message

```
❌ GDF_RACK tunnel establishment failed: 
❌ Tunnel connection failed: 
Lab device connection failed: 
Lab device connection error: [Errno None] Unable to connect to port 10022 on 127.0.0.1
```

---

## Root Cause Analysis

### Problem 1: Incomplete Port Forwarding Implementation

**Location**: `services/gdf_rack_tunnel_service.py`, `_setup_port_forwarding()` method

**Issue**: 
The code calls `self.transport.request_port_forward()` but this is **NOT** the correct API for creating a local listening socket.

```python
# ❌ WRONG - This is for reverse port forwarding
self.transport.request_port_forward(
    self.lab_ip,     # Remote host to forward TO
    remote_port,     # Remote port to forward TO
    self._port_forward_handler  # Handler (never called)
)
```

**What happens**:
1. `request_port_forward()` registers a forward request at the remote end
2. No local listening socket is created on 127.0.0.1:10022
3. When `_connect_to_lab_device()` tries to connect to localhost:10022, it fails

**Correct approach** (Paramiko):
Use `paramiko.SSHClient.open_sftp_client()` or implement manual socket forwarding with `get_transport().open_session()`

---

### Problem 2: Missing Local Port Listening

The current implementation expects `request_port_forward()` to create a local listening socket, but it doesn't.

**Expected flow**:
```
Client: Connect to 127.0.0.1:10022
   ↓
Local socket listening on 127.0.0.1:10022 (doesn't exist!)
   ↓
SSH tunnel through R-Pi
   ↓
Lab device: 10.0.0.140:22
```

**Actual flow**:
```
Client: Try to connect to 127.0.0.1:10022
   ↓
Connection refused! (No local socket listening)
```

---

## Solution: Fix Port Forwarding Implementation

### Option A: Use SSH's Native `LocalTunnelForwarder` (Recommended)

Paramiko doesn't have a built-in LocalTunnelForwarder, but we can implement one using threading and socket forwarding:

```python
def _setup_port_forwarding(self) -> Tuple[bool, str]:
    """
    Set up local port forwarding using socket tunneling
    Creates listening sockets on localhost that forward through SSH tunnel
    """
    try:
        import socket
        import threading
        
        self.transport = self.rpi_ssh_client.get_transport()
        if not self.transport or not self.transport.is_active():
            return False, "R-Pi transport not active"
        
        # Start forwarding threads for each port
        self.forwarding_threads = []
        
        for local_port in self.FORWARDED_PORTS.keys():
            thread = threading.Thread(
                target=self._forward_tunnel,
                args=(local_port, self.lab_ip, local_port),
                daemon=True
            )
            thread.start()
            self.forwarding_threads.append(thread)
            print(f"✅ Forwarding: 127.0.0.1:{local_port} → {self.lab_ip}:{local_port}")
        
        # Wait briefly for sockets to be ready
        time.sleep(0.5)
        return True, "Port forwarding established"
        
    except Exception as e:
        return False, f"Port forwarding error: {str(e)}"

def _forward_tunnel(self, local_port, remote_host, remote_port):
    """Forward local port to remote host through SSH tunnel"""
    import socket
    
    try:
        # Create local listening socket
        local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        local_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        local_socket.bind(('127.0.0.1', local_port))
        local_socket.listen(1)
        
        while True:
            client_socket, addr = local_socket.accept()
            
            # Open SSH channel to remote
            chan = self.transport.open_session()
            chan.exec_command(f'ssh -W {remote_host}:{remote_port} {self.lab_username}@localhost')
            
            # Forward data between sockets
            self._forward_data(client_socket, chan)
            
    except Exception as e:
        print(f"⚠️ Tunnel error on port {local_port}: {e}")
```

### Option B: Use SSH ProxyCommand Approach

Instead of trying to set up port forwarding, connect directly through the SSH tunnel:

```python
def _connect_to_lab_device(self) -> Tuple[bool, str]:
    """
    Connect to lab device through R-Pi tunnel using ProxyCommand
    This is simpler and more reliable than port forwarding
    """
    try:
        self.lab_ssh_client = paramiko.SSHClient()
        self.lab_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Create a \"proxy\" command that goes through the R-Pi tunnel
        sock = self.rpi_ssh_client.get_transport().open_session()
        sock.set_combine_stderr(True)
        
        # Execute command to create tunnel to lab device
        sock.exec_command(f'cat')
        
        # Use the SSH channel as a socket-like object
        self.lab_ssh_client.connect(
            hostname='10.0.0.140',  # Lab device IP
            port=22,
            username='root',
            sock=sock,  # Use the SSH channel as socket
            timeout=10,
            allow_agent=True,
            look_for_keys=True
        )
        
        return True, "Lab device connection successful"
        
    except Exception as e:
        return False, f"Lab device connection error: {str(e)}"
```

### Option C: Simple Manual Forwarding (Most Reliable)

```python
def _setup_port_forwarding(self) -> Tuple[bool, str]:
    """Simplified: Don't pre-setup, handle in _connect_to_lab_device"""
    try:
        self.transport = self.rpi_ssh_client.get_transport()
        if not self.transport or not self.transport.is_active():
            return False, "R-Pi transport not active"
        
        # Just verify transport is ready
        print(f"✅ SSH transport active, ready for port forwarding")
        return True, "Transport ready"
        
    except Exception as e:
        return False, f"Transport error: {str(e)}"

def _connect_to_lab_device(self) -> Tuple[bool, str]:
    """Connect using SSH channel directly through R-Pi"""
    try:
        # Open an SSH session channel from R-Pi to lab device
        transport = self.rpi_ssh_client.get_transport()
        
        # Create a socket for direct connection
        chan = transport.open_session()
        chan.settimeout(self.TIMEOUT_RPI_CONNECT)
        
        # Execute SSH command to lab device from R-Pi
        chan.exec_command(
            f'ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no {self.lab_username}@{self.lab_ip}'
        )
        
        # Connect Paramiko client through this channel
        self.lab_ssh_client = paramiko.SSHClient()
        self.lab_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.lab_ssh_client._transport = chan
        
        print(f"✅ Connected to lab device through R-Pi tunnel")
        return True, "Lab device connection successful"
        
    except Exception as e:
        return False, f"Lab device connection error: {str(e)}"
```

---

## Recommended Fix: Socket-Based Forwarding

I recommend implementing **Option A** (socket-based forwarding) as it's:
- ✅ Most reliable and battle-tested
- ✅ Handles multiple ports cleanly
- ✅ Works with standard SSH connection methods
- ✅ Error recovery is straightforward

---

## Immediate Workaround

Until the proper fix is implemented, you can:

1. **Increase R-Pi tunnel timeout** (gives more time for setup to fail cleanly)
2. **Add retry logic** with exponential backoff
3. **Use direct SSH** if R-Pi tunnel isn't critical for this device

---

## Files to Modify

1. **`services/gdf_rack_tunnel_service.py`**
   - Rewrite `_setup_port_forwarding()` method
   - Update `_connect_to_lab_device()` method
   - Add threading/socket forwarding helpers
   - Update `_cleanup()` to handle forwarding threads

2. **`services/test_execution_service.py`** (optional)
   - Add retry logic for tunnel establishment
   - Add timeout settings

---

## Testing Plan

1. Test tunnel establishment with logging at each step
2. Verify localhost:10022 socket is actually listening
3. Test with device in DEEPSLEEP state
4. Test with various reboot methods (reboot_perf_v2_optimized, etc.)

---

## Related Issues

- **Device**: DT_LAB_SKY_XIONE-UK-0D_AB is a GDF_RACK device
- **Method**: reboot_perf_v2_optimized requires direct SSH (via tunnel for rack devices)
- **Tunnel Type**: 2-stage (Client → R-Pi → Lab Device)
- **Port**: SSH tunnel expects localhost:10022

---

## Prevention

Add these to prevent similar issues:

1. **Verify socket before connecting**
   ```python
   import socket
   sock = socket.create_connection(('127.0.0.1', 10022), timeout=2)
   sock.close()
   ```

2. **Add detailed logging**
   ```python
   log_service.log(f"[TUNNEL] Verifying localhost:10022 listening...")
   log_service.log(f"[TUNNEL] Transports: RPI={self.rpi_ssh_client is not None}, LAB={self.lab_ssh_client is not None}")
   ```

3. **Test connectivity step-by-step**
   ```python
   # Step 1: R-Pi connection
   # Step 2: Port forwarding setup
   # Step 3: Verify listening socket
   # Step 4: Lab device connection
   ```

---

## Summary

**Status**: 🔴 Critical Issue - Port forwarding not implemented correctly

**Impact**:
- All GDF_RACK device methods requiring SSH tunnel will fail
- Affects: reboot_perf_v2_optimized, status, log_collection, etc.
- DESK devices unaffected (direct SSH)

**Fix Complexity**: Medium (requires socket/threading implementation)

**Timeline**: Should be fixed before next GDF_RACK batch execution

---

**Analysis Date**: August 5, 2026
**Job Date**: August 5, 2026 05:54:04 UTC
