# Jump Host Integration Guide

## Overview
This application now supports connecting to devices via GRRE jump hosts using MAC address-based device resolution. This enables cloud deployment scenarios where devices are not directly accessible but can be reached through a corporate jump host infrastructure.

## Architecture

### Connection Methods
The application supports two SSH connection methods:

1. **Direct SSH** (Default)
   - Direct SSH connection to device IP:Port
   - Used for local/on-premise deployments
   - No jump host required

2. **Jump Host SSH** (New)
   - SSH to GRRE jump host
   - Navigate menu to connect to device by MAC address
   - Used for cloud deployments or remote access

### Components

#### 1. Jump Host Service (`services/jump_host_service.py`)
Core service for managing jump host connections:
- `JumpHostService`: Main class for jump host operations
- Handles menu navigation (1 → 1 → MAC address)
- Manages interactive shell sessions
- Executes commands on target devices

#### 2. SSH Connection Helper (`services/ssh_connection_helper.py`)
Unified interface for both connection methods:
- `SSHConnectionHelper`: Wraps direct and jump host connections
- Provides consistent API regardless of connection method
- Context manager support for automatic cleanup

#### 3. Device Model Updates (`models/device.py`)
Extended device model with jump host support:
- `use_jump_host`: Boolean flag to enable jump host connection
- `jump_host_config`: Jump host credentials and settings
- `validate_connection()`: Updated to support both methods

#### 4. Configuration (`config_jump_host.py`)
Centralized jump host configuration:
- Pre-configured jump host locations (USA, India)
- Connection timeouts and settings
- Global enable/disable flag

## Configuration

### Device Configuration
Add jump host settings to `devices.json`:

```json
{
    "ip": "10.0.0.250",
    "name": "Element-A4K-DESK",
    "username": "root",
    "password": "",
    "port": 10022,
    "mac_address": "1C:2F:A2:30:35:B6",
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "vpatne290",
        "password": "your_jump_host_password",
        "port": 22
    },
    "ir_config": { ... },
    "vnc_url": "http://10.0.0.250:5800/"
}
```

### Required Fields for Jump Host
- `mac_address`: Device MAC address (required for jump host connection)
- `use_jump_host`: Set to `true` to enable jump host connection
- `jump_host_config`:
  - `host`: Jump host IP or hostname
  - `username`: Your jump host username
  - `password`: Your jump host password
  - `port`: SSH port (default: 22)

### Global Configuration
Edit `config_jump_host.py`:

```python
# Enable jump host globally
JUMP_HOST_ENABLED = True

# Configure jump hosts by location
JUMP_HOSTS = {
    'usa_philadelphia': {
        'host': '96.118.26.235',
        'port': 22,
        'name': 'acrylic-platco-only-lab'
    }
}
```

## Usage

### Testing Jump Host Connection
Use the existing test connection endpoint:

```bash
curl -X POST http://localhost:5000/api/test_connection \
  -H "Content-Type: application/json" \
  -d '{"device_ip": "10.0.0.250"}'
```

Response:
```json
{
    "success": true,
    "message": "Connection via jump host successful"
}
```

### Programmatic Usage

#### Direct Connection (Existing)
```python
from models.device import Device

device = Device.find_by_ip("10.0.0.250")
success, message = device.validate_connection()
```

#### Jump Host Connection (New)
```python
from services.ssh_connection_helper import execute_device_command

device = Device.find_by_ip("10.0.0.250")
device.use_jump_host = True
device.jump_host_config = {
    'host': '96.118.26.235',
    'username': 'vpatne290',
    'password': 'your_password',
    'port': 22
}

# Execute command
success, output = execute_device_command(device, "uname -a")
```

#### Context Manager Pattern
```python
from services.ssh_connection_helper import SSHConnectionHelper

device = Device.find_by_ip("10.0.0.250")

with SSHConnectionHelper(device) as ssh:
    success, output = ssh.execute_command("cat /version.txt")
    print(output)
```

## Migration Strategy

### Phase 1: Local Testing (Current)
- Keep `use_jump_host: false` for all devices
- Test application locally with direct SSH
- No changes to existing workflows

### Phase 2: Jump Host Testing
1. Enable jump host for one test device:
   ```json
   {
       "ip": "10.0.0.250",
       "mac_address": "1C:2F:A2:30:35:B6",
       "use_jump_host": true,
       "jump_host_config": { ... }
   }
   ```

2. Test connection:
   ```bash
   curl -X POST http://localhost:5000/api/test_connection \
     -H "Content-Type: application/json" \
     -d '{"device_ip": "10.0.0.250"}'
   ```

3. Run test job execution

4. Verify logs and results

### Phase 3: Cloud Deployment
1. Deploy application to OneCloud
2. Update all devices to use jump host
3. Test connectivity from cloud to all devices
4. Enable production workflows

### Phase 4: Multi-Location Support
1. Configure India jump host in `config_jump_host.py`
2. Assign devices to appropriate jump hosts
3. Test cross-location connectivity

## Jump Host Menu Flow

The application automates this interactive flow:

```
1. SSH to jump host (96.118.26.235)
   ↓
2. Main Menu → Select "1" (Reverse/Forward SSH)
   ↓
3. Device Type Menu → Select "1" (XUMO/XGLOBAL/PLATCO)
   ↓
4. MAC Address Prompt → Enter "1C:2F:A2:30:35:B6"
   ↓
5. Wait for device prompt (root@device:~#)
   ↓
6. Execute commands on device
   ↓
7. Disconnect and cleanup
```

## Troubleshooting

### Connection Issues

**Problem**: "MAC address required for jump host connection"
- **Solution**: Add `mac_address` field to device in `devices.json`

**Problem**: "Jump host config missing: username"
- **Solution**: Ensure all required fields in `jump_host_config` are set

**Problem**: "Device shell prompt not found"
- **Solution**: 
  - Check MAC address is correct
  - Verify device is powered on and accessible
  - Check jump host has access to device subnet

### Testing

Test jump host connection manually:
```python
from services.jump_host_service import test_jump_host_connection

result = test_jump_host_connection(
    jump_host='96.118.26.235',
    jump_user='vpatne290',
    jump_pass='your_password',
    device_mac='1C:2F:A2:30:35:B6',
    test_command='uname -a'
)

print(result)
```

Expected output:
```python
{
    'jump_host_connection': True,
    'device_connection': True,
    'command_execution': True,
    'output': 'Linux apache-4k ...',
    'errors': []
}
```

## Security Considerations

### Credentials Storage
- Jump host passwords stored in `devices.json` (same as device passwords)
- Consider using environment variables or secrets manager for production
- Implement encryption at rest for sensitive configuration files

### Network Security
- Jump host connections use SSH (port 22)
- All traffic encrypted end-to-end
- No direct inbound connections to devices required
- Follow corporate security policies for jump host access

### Access Control
- Use individual jump host credentials (not shared accounts)
- Rotate passwords regularly
- Monitor jump host access logs
- Implement audit logging in application

## Performance Considerations

### Connection Latency
- Jump host adds ~2-3 seconds per connection
- Menu navigation adds overhead
- Consider connection pooling for frequent operations

### Timeouts
Configure in `config_jump_host.py`:
```python
JUMP_HOST_CONNECTION_TIMEOUT = 10  # Initial connection
JUMP_HOST_COMMAND_TIMEOUT = 30     # Command execution
JUMP_HOST_MENU_TIMEOUT = 5         # Menu navigation
```

### Best Practices
- Reuse connections when executing multiple commands
- Use context manager for automatic cleanup
- Implement retry logic for transient failures
- Monitor connection success rates

## Future Enhancements

### Planned Features
1. **Connection Pooling**: Maintain persistent jump host connections
2. **Load Balancing**: Support multiple jump hosts per location
3. **Failover**: Automatic retry with backup jump host
4. **Metrics**: Track connection times, success rates
5. **SSH Key Auth**: Support SSH keys instead of passwords

### Integration Points
- Update all device methods to use `SSHConnectionHelper`
- Add jump host status to device dashboard
- Implement connection health checks
- Add jump host configuration UI

## Support

### Documentation
- Jump host service: `services/jump_host_service.py`
- SSH helper: `services/ssh_connection_helper.py`
- Configuration: `config_jump_host.py`
- This guide: `JUMP_HOST_INTEGRATION.md`

### Slack Channels
- GRRE Jump Hosts: #grre-jumphosts
- ETWiki: https://etwiki.sys.comcast.net/display/ccpps/GRRE+Jumphost+Info

### Contact
For questions or issues, contact the development team or refer to the GRRE jump host documentation.
