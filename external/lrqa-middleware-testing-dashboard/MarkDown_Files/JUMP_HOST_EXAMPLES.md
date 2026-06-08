# Jump Host Configuration Examples

## Example 1: Basic Jump Host Device

```json
{
    "ip": "10.0.0.250",
    "name": "Element-A4K-DESK",
    "username": "root",
    "password": "",
    "port": 10022,
    "mac_address": "1C:2F:A2:30:35:B6",
    "vnc_url": "http://10.0.0.250:5800/",
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "vpatne290",
        "password": "YOUR_PASSWORD_HERE",
        "port": 22
    },
    "ir_config": {
        "ir_port": 1,
        "itach_ip": "10.0.0.33",
        "itach_port": 4998
    }
}
```

## Example 2: Direct SSH Device (Unchanged)

```json
{
    "ip": "10.0.0.101",
    "name": "WestingHouse-4K-DESK",
    "username": "root",
    "password": "",
    "port": 10022,
    "mac_address": "58:41:46:5C:E4:B4",
    "vnc_url": "http://10.0.0.101:5800/",
    "ir_config": {
        "ir_port": 2,
        "itach_ip": "10.0.0.33",
        "itach_port": 4998
    }
}
```

## Example 3: Multiple Jump Host Devices

```json
[
    {
        "ip": "10.0.0.250",
        "name": "Element-A4K-USA",
        "username": "root",
        "password": "",
        "port": 10022,
        "mac_address": "1C:2F:A2:30:35:B6",
        "vnc_url": "http://10.0.0.250:5800/",
        "use_jump_host": true,
        "jump_host_config": {
            "host": "96.118.26.235",
            "username": "vpatne290",
            "password": "YOUR_PASSWORD",
            "port": 22
        },
        "ir_config": {}
    },
    {
        "ip": "10.0.0.195",
        "name": "SHARP-DEVICE-USA",
        "username": "root",
        "password": "",
        "port": 10022,
        "mac_address": "58:41:46:C6:11:DE",
        "vnc_url": "http://10.0.0.195:5800/",
        "use_jump_host": true,
        "jump_host_config": {
            "host": "96.118.26.235",
            "username": "vpatne290",
            "password": "YOUR_PASSWORD",
            "port": 22
        },
        "ir_config": {}
    },
    {
        "ip": "10.0.0.101",
        "name": "WestingHouse-LOCAL",
        "username": "root",
        "password": "",
        "port": 10022,
        "mac_address": "58:41:46:5C:E4:B4",
        "vnc_url": "http://10.0.0.101:5800/",
        "use_jump_host": false,
        "ir_config": {}
    }
]
```

## Testing Configuration

### Test Device JSON for `devices.json`

Add this to your `devices.json` file:

```json
{
    "ip": "10.0.0.250",
    "name": "TEST-JUMP-HOST-DEVICE",
    "username": "root",
    "password": "",
    "port": 10022,
    "mac_address": "1C:2F:A2:30:35:B6",
    "vnc_url": "http://10.0.0.250:5800/",
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "YOUR_USERNAME",
        "password": "YOUR_PASSWORD",
        "port": 22
    },
    "ir_config": {
        "ir_port": 1,
        "itach_ip": "10.0.0.33",
        "itach_port": 4998
    }
}
```

### Steps to Configure

1. **Get Your Jump Host Credentials**
   ```bash
   # Jump Host: 96.118.26.235
   # Username: Your Comcast username (e.g., vpatne290)
   # Password: Your Comcast password
   ```

2. **Get Device MAC Address**
   ```bash
   # SSH to device directly and run:
   cat /tmp/.deviceDetails.cache | grep -i 'estb_mac'
   # Or from jumpconnection-235.md example: 1C:2F:A2:30:35:B6
   ```

3. **Update devices.json**
   - Add the configuration above
   - Replace `YOUR_USERNAME` with your jump host username
   - Replace `YOUR_PASSWORD` with your jump host password
   - Replace `1C:2F:A2:30:35:B6` with your device's MAC address

4. **Test Connection**
   ```bash
   python3 test_jump_host.py
   # Or via API:
   curl -X POST http://localhost:5000/api/test_connection \
     -H "Content-Type: application/json" \
     -d '{"device_ip": "10.0.0.250"}'
   ```

## Environment Variable Configuration (Recommended for Production)

Instead of storing passwords in `devices.json`, use environment variables:

### Set Environment Variables
```bash
export JUMP_HOST_USER="vpatne290"
export JUMP_HOST_PASS="your_password"
```

### devices.json Configuration
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
        "username": "${JUMP_HOST_USER}",
        "password": "${JUMP_HOST_PASS}",
        "port": 22
    }
}
```

### Update Device Model (Future Enhancement)
Add environment variable substitution in `models/device.py`:

```python
import os

def resolve_env_vars(value):
    """Replace ${VAR} with environment variable value"""
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        var_name = value[2:-1]
        return os.getenv(var_name, value)
    return value
```

## MAC Address Format Examples

### Valid Formats
```
XX:XX:XX:XX:XX:XX  →  1C:2F:A2:30:35:B6
XXXXXXXXXXXX       →  1C2FA23035B6
xx:xx:xx:xx:xx:xx  →  1c:2f:a2:30:35:b6
```

### Invalid Formats
```
XX-XX-XX-XX-XX-XX  (wrong separator)
XX.XX.XX.XX.XX.XX  (wrong separator)
XX:XX:XX:XX:XX     (too short)
```

## Configuration Validation

### Python Validation Script
```python
import json

def validate_jump_host_config(device):
    """Validate jump host configuration"""
    errors = []
    
    if device.get('use_jump_host'):
        # Check MAC address
        if not device.get('mac_address'):
            errors.append("MAC address required for jump host")
        
        # Check jump_host_config
        config = device.get('jump_host_config', {})
        required = ['host', 'username', 'password']
        for field in required:
            if not config.get(field):
                errors.append(f"Jump host config missing: {field}")
    
    return errors

# Test
with open('devices.json') as f:
    devices = json.load(f)
    for device in devices:
        errors = validate_jump_host_config(device)
        if errors:
            print(f"Device {device['name']}:")
            for error in errors:
                print(f"  - {error}")
```

## Quick Configuration Checklist

Before testing:
- [ ] Jump host IP correct (96.118.26.235)
- [ ] Username correct (your Comcast username)
- [ ] Password correct (your Comcast password)
- [ ] MAC address correct (from device)
- [ ] MAC address format valid (XX:XX:XX:XX:XX:XX)
- [ ] `use_jump_host` set to `true`
- [ ] All required fields present in `jump_host_config`

## Common Configuration Mistakes

### ❌ Wrong
```json
{
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235"
    }
}
```
**Problem**: Missing username and password

### ✅ Correct
```json
{
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "vpatne290",
        "password": "your_password",
        "port": 22
    }
}
```

### ❌ Wrong
```json
{
    "mac_address": "",
    "use_jump_host": true
}
```
**Problem**: Empty MAC address

### ✅ Correct
```json
{
    "mac_address": "1C:2F:A2:30:35:B6",
    "use_jump_host": true
}
```

## Need Help?

1. **Configuration Issues**: Check `JUMP_HOST_QUICKSTART.md`
2. **Testing Issues**: Run `python3 test_jump_host.py`
3. **Connection Issues**: See `JUMP_HOST_INTEGRATION.md` troubleshooting section
4. **GRRE Jump Hosts**: #grre-jumphosts on Slack

---

**Ready to configure?** Follow the steps above and test with `python3 test_jump_host.py`
