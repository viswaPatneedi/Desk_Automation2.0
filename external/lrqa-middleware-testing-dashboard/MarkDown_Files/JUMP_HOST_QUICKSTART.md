# Jump Host Quick Start Guide

## What's New?
The application now supports connecting to devices via GRRE jump hosts using MAC addresses. This enables cloud deployment without direct device access.

## Quick Setup (5 Minutes)

### Step 1: Add Jump Host Config to Device
Edit `devices.json` and add these fields to any device:

```json
{
    "ip": "10.0.0.250",
    "name": "Element-A4K-DESK",
    "mac_address": "1C:2F:A2:30:35:B6",
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "your_username",
        "password": "your_password",
        "port": 22
    }
}
```

### Step 2: Test Connection
```bash
python test_jump_host.py
```

Or via API:
```bash
curl -X POST http://localhost:5000/api/test_connection \
  -H "Content-Type: application/json" \
  -d '{"device_ip": "10.0.0.250"}'
```

### Step 3: Run Test Job
Use the existing UI or API to run any method on the device. The application will automatically use jump host connection.

## Key Points

✅ **Backward Compatible**: Devices without `use_jump_host` continue using direct SSH  
✅ **Zero Code Changes**: Existing methods work automatically with jump host  
✅ **Per-Device Configuration**: Enable jump host only for specific devices  
✅ **Automatic Failover**: If jump host fails, error is logged clearly  

## Configuration Options

### Minimal (Required)
```json
{
    "mac_address": "1C:2F:A2:30:35:B6",
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "vpatne290",
        "password": "your_pass"
    }
}
```

### Full (All Options)
```json
{
    "mac_address": "1C:2F:A2:30:35:B6",
    "use_jump_host": true,
    "jump_host_config": {
        "host": "96.118.26.235",
        "username": "vpatne290",
        "password": "your_pass",
        "port": 22
    }
}
```

## Common Issues

### "MAC address required"
- Add `mac_address` field to device config
- MAC format: `XX:XX:XX:XX:XX:XX` or `XXXXXXXXXXXX`

### "Jump host config missing: username"
- Ensure all fields (host, username, password) are set in `jump_host_config`

### "Device shell prompt not found"
- Verify MAC address is correct
- Check device is powered on
- Confirm jump host has access to device network

## Testing

### Test Jump Host Only
```bash
python test_jump_host.py
# Select option 2 for manual jump host test
```

### Test Specific Device
```python
from models.device import Device

device = Device.find_by_ip("10.0.0.250")
success, message = device.validate_connection()
print(f"Connection: {message}")
```

### Test with Commands
```python
from services.ssh_connection_helper import execute_device_command
from models.device import Device

device = Device.find_by_ip("10.0.0.250")
success, output = execute_device_command(device, "hostname")
print(output)
```

## Migration Path

### Phase 1: Keep Current Setup ✓
- No changes needed
- All devices use direct SSH
- Application works as before

### Phase 2: Test One Device
- Enable jump host for 1 device
- Run test jobs
- Verify functionality

### Phase 3: Cloud Deployment
- Deploy app to cloud
- Enable jump host for all devices
- Update jump host credentials

## Files Changed

| File | Purpose |
|------|---------|
| `services/jump_host_service.py` | Jump host connection logic |
| `services/ssh_connection_helper.py` | Unified SSH interface |
| `models/device.py` | Device model with jump host support |
| `config_jump_host.py` | Jump host configuration |
| `test_jump_host.py` | Test script |
| `JUMP_HOST_INTEGRATION.md` | Full documentation |

## Need Help?

1. **Full Documentation**: Read `JUMP_HOST_INTEGRATION.md`
2. **Test Script**: Run `python test_jump_host.py`
3. **GRRE Jump Hosts**: #grre-jumphosts on Slack
4. **ETWiki**: https://etwiki.sys.comcast.net/display/ccpps/GRRE+Jumphost+Info

## Next Steps

- [ ] Test jump host connection manually
- [ ] Configure one device with jump host
- [ ] Run test execution
- [ ] Update remaining devices as needed
- [ ] Deploy to cloud (when ready)

---

**Ready to test?** Run: `python test_jump_host.py`
