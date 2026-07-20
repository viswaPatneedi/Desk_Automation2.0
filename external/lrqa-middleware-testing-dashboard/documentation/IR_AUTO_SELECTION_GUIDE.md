# IR Remote Type & Keys Auto-Selection Implementation Guide

## Overview
This document describes the new automatic remote type selection and key retrieval feature based on device type (XUMO vs SKY STREAM).

## Implementation Summary

### ✅ Completed Features

#### 1. Device Type to Remote Type Mapping Configuration
**File**: `config/config_ir_blaster.py`

```python
# Mapping dictionary
DEVICE_TYPE_TO_REMOTE_TYPE = {
    'XUMO': 'XUMO_PR3',
    'SKY STREAM': 'SKY_LC103',
    'SKY': 'SKY_LC103',
    ...
}

# Helper functions
get_remote_type_for_device_type(device_type) → remote_type
get_default_keys_for_device_type(device_type) → ['HOME', 'POWER']
```

#### 2. API Endpoint for Auto-Detection
**File**: `app.py`  
**Endpoint**: `GET /api/ir-remote-for-device/<device_type>`

**Request**:
```bash
GET /api/ir-remote-for-device/XUMO
```

**Response**:
```json
{
    "success": true,
    "device_type": "XUMO",
    "remote_type": "XUMO_PR3",
    "default_keys": ["HOME", "POWER"],
    "available_keys": ["POWER", "MUTE", "VOL_UP", "VOL_DOWN", "HOME", "BACK", ...]
}
```

#### 3. Backend IR Test Method Enhancement
**File**: `methods/method_ir_test.py`

The `execute_ir_test_process()` function now accepts `device_type` parameter and uses priority-based detection:

1. **Override**: `remote_type_override` parameter (highest priority)
2. **Device Type**: Auto-detect from `device_type` using mapping
3. **IR Config**: Use value from device's `ir_config`
4. **Device Name Pattern**: Fallback pattern matching (SKY in name → SKY_LC103)

**Example Call**:
```python
execute_ir_test_process(
    device_ip="10.0.0.95",
    device_name="Device-XUMO-01",
    device_type="XUMO",  # ← NEW: Triggers auto-detection
    selected_keys=['HOME', 'POWER']
)
# Will automatically use: XUMO_PR3 remote type
```

---

## Usage Workflow

### For Device Management
When adding/editing a device:

1. **Set Device Type**: Select from dropdown: "XUMO" or "SKY STREAM"
   ```
   Device Type: XUMO ← This determines the remote type
                ↓
            XUMO_PR3 ← Automatically selected
   ```

2. Device Information Stored:
   ```json
   {
     "name": "Living-Room-Device",
     "ip": "10.0.0.95",
     "device_type": "XUMO",     // ← Used for auto-detection
     "ir_config": {...},         // ← Stored IR settings
   }
   ```

### For IR Test Execution
When executing IR test on a device:

1. **At Execution Time**: Backend retrieves device info including `device_type`
2. **Auto-Detection**: Remote type determined from device_type
3. **Keys Sent**: Pre-configured default keys or user-selected keys

**Flow**:
```
User selects device in execution → Device Type retrieved → 
Remote Type auto-determined → Keys selected → IR sent
```

---

## API Reference

### Get Remote Type for Device Type
```http
GET /api/ir-remote-for-device/XUMO
Authorization: Bearer <token>
```

**Parameters**: None (device_type in URL)

**Success Response** (200):
```json
{
    "success": true,
    "device_type": "XUMO",
    "remote_type": "XUMO_PR3",
    "default_keys": ["HOME", "POWER"],
    "available_keys": [
        "POWER", "MUTE", "VOL_UP", "VOL_DOWN",
        "HOME", "BACK", "SELECT", "OK", ...
    ]
}
```

**Error Response** (404):
```json
{
    "success": false,
    "error": "Unknown device type: INVALID_TYPE",
    "device_type": "INVALID_TYPE",
    "remote_type": null,
    "default_keys": [],
    "available_keys": []
}
```

---

## Device Type Mapping Table

| Device Type | Remote Type | Commands | Keys Available |
|-------------|-------------|----------|-----------------|
| XUMO        | XUMO_PR3    | IR codes | Power, Mute, Volume, Navigation, Select |
| SKY STREAM  | SKY_LC103   | IR codes | Power, Mute, Volume, Navigation, Select |

---

## Configuration Files

### 1. Device Configuration (`devices.json`)
```json
{
  "ip": "10.0.0.95",
  "name": "Living-Room-XUMO",
  "device_type": "XUMO",          // ← Used for auto-detection
  "ir_config": {
    "itach_ip": "10.0.0.12",
    "itach_port": 4998,
    "ir_port": 5
  }
}
```

### 2. IR Keycodes (`Json/ir_keycodes.json`)
```json
{
  "remotes": {
    "XUMO_PR3": {
      "keycodes": {
        "POWER": {"command_template": "..."},
        "MUTE": {"command_template": "..."},
        ...
      }
    },
    "SKY_LC103": {
      "keycodes": {
        "POWER": {"command_template": "..."},
        "MUTE": {"command_template": "..."},
        ...
      }
    }
  }
}
```

---

## Frontend / UI Integration

### Current State
- IR test modal still requires manual remote type selection during queue building
- Device type information is not available at queue building time (only during execution)

### Future Enhancement (Optional)
To enable full automation in the UI:

1. **Device Selection Modal**: First ask user to select device at queue time
2. **Pre-populate Remote Type**: Call `/api/ir-remote-for-device/<device_type>`
3. **Display Available Keys**: Show keys available for that remote type
4. **Allow Override**: Let user customize if needed

**Suggested Implementation**:
```javascript
async function getRemoteTypeForDevice(deviceType) {
    const response = await fetch(`/api/ir-remote-for-device/${deviceType}`);
    return await response.json();
}

// Usage in promptForIrKeysAsync
if (knownDeviceType) {
    const autoData = await getRemoteTypeForDevice(knownDeviceType);
    // Pre-populate modal with autoData.remote_type and autoData.available_keys
}
```

---

## Implementation Checklist

- [x] Device type to remote type mapping in `config_ir_blaster.py`
- [x] Helper functions: `get_remote_type_for_device_type()`
- [x] Helper functions: `get_default_keys_for_device_type()`
- [x] API endpoint: `/api/ir-remote-for-device/<device_type>`
- [x] IR test method: Accept `device_type` parameter
- [x] Priority-based remote type detection
- [x] Automatic logging of detected remote type
- [ ] Optional: UI modal enhancement for device pre-selection
- [ ] Optional: Real-time IR key preview in UI
- [ ] Optional: Test with multiple device types

---

## Testing Guide

### Test 1: Verify Device Type Mapping
```bash
curl -s http://localhost:11079/api/ir-remote-for-device/XUMO | jq
# Expected: remote_type: "XUMO_PR3"

curl -s http://localhost:11079/api/ir-remote-for-device/SKY%20STREAM | jq
# Expected: remote_type: "SKY_LC103"
```

### Test 2: IR Test with Device Type
```python
from methods.method_ir_test import execute_ir_test_process

# XUMO Device
result = execute_ir_test_process(
    device_ip="10.0.0.95",
    device_type="XUMO",
    selected_keys=['HOME', 'POWER']
)
# Should log: "Auto-detected remote type from device_type 'XUMO': XUMO_PR3"

# SKY STREAM Device
result = execute_ir_test_process(
    device_ip="10.0.0.166",
    device_type="SKY STREAM",
    selected_keys=['HOME', 'POWER']
)
# Should log: "Auto-detected remote type from device_type 'SKY STREAM': SKY_LC103"
```

### Test 3: API Endpoint
```bash
# Unknown device type
curl http://localhost:11079/api/ir-remote-for-device/UNKNOWN
# Should return 404 with error message

# Valid device type
curl http://localhost:11079/api/ir-remote-for-device/XUMO
# Should return 200 with remote_type and keys
```

---

## Benefits

✅ **Reduced Manual Input**: No more selecting remote type manually  
✅ **Consistent Accuracy**: Device type always maps to correct remote  
✅ **Faster Execution**: Pre-populated configurations  
✅ **Error Prevention**: Invalid remote type combinations impossible  
✅ **Scalability**: Easy to add new device types to mapping  

---

## Migration Guide (If Changing Existing Devices)

If you have devices without `device_type` set:

1. Add `device_type` field to each device in `devices.json`:
   ```json
   {
     "name": "device-name",
     "device_type": "XUMO"  // Add this field
   }
   ```

2. Save devices through the UI or bulk update

3. Existing `ir_config.remote_type` values will still work as fallback

---

## Troubleshooting

### Issue: Remote type not auto-detecting
**Solution**: Verify device has `device_type` field set in `devices.json`

### Issue: API returns unknown device type error
**Solution**: Check device_type value doesn't have typos. Valid values:
- `XUMO` (not `xumo_pr3` or `XUMO_PR3`)
- `SKY STREAM` (with space, not underscore)

### Issue: Keys not available for remote type
**Solution**: Verify `ir_keycodes.json` has entries for the detected remote type

---

## Support & Future Enhancements

For questions or improvements:
1. Check the API response for available keys
2. Verify device_type is correctly set
3. Review logs for "Auto-detected remote type" messages
4. Add new device types by updating `DEVICE_TYPE_TO_REMOTE_TYPE` mapping

**Future**: Consider adding device_type UI selector in device management form
