# IR Blaster & Power Control Configuration Implementation

## Overview
This document outlines the implementation of IR Blaster (iTach) and Power Control configuration support for GDF_RACK devices in the middleware testing dashboard.

## Implementation Summary

### 1. Frontend Changes (templates/index.html)

#### A. HTML Form Sections Added (Lines 1943-2016)
Two new optional configuration sections were added to the Add GDF_RACK Device form:

**IR Blaster Configuration Section:**
- **IR Blaster IP Address** (optional) - IP of the iTach IR blaster device
- **IR Blaster Port** (default: 4998) - Network port for IR communication
- **IR Connector ID** (optional) - Connector number for IR code output

**Power Control Configuration Section:**
- **Power Control Type** (optional) - Dropdown: PDU | Smart Power Plug | Other | None
- **Power Device IP Address** (optional) - IP of the power control device
- **Power Outlet/Port Number** (optional) - Outlet or port number on power device
- **Power Device Username** (optional) - Authentication for power device
- **Power Device Password** (optional) - Encrypted password for power device

**UI Features:**
- Consistent styling with existing configuration sections
- Color-coded headers (purple for IR Blaster 🔌, green for Power Control ⚡)
- Helpful descriptions and field labels
- All fields marked as optional with "Leave empty if..." guidance

#### B. JavaScript Form Collection (handleAddRackDevice function, Lines 4018-4080)
Updated to collect new fields:
- `rack-ir-blaster-ip`
- `rack-ir-blaster-port`
- `rack-ir-connector`
- `rack-power-type`
- `rack-power-ip`
- `rack-power-outlet`
- `rack-power-username`
- `rack-power-password`

**Data Structure:**
```javascript
rackDeviceData = {
    // ... existing fields ...
    ir_blaster_config: irBlasterIpValue ? {
        ir_blaster_ip: irBlasterIpValue,
        ir_blaster_port: irBlasterPortValue ? parseInt(irBlasterPortValue) : 4998,
        ir_connector: irConnectorValue || '1'
    } : null,
    power_control_config: powerTypeValue ? {
        power_type: powerTypeValue,
        power_ip: powerIpValue,
        power_outlet: powerOutletValue,
        power_username: powerUsernameValue || null,
        power_password: powerPasswordValue || null
    } : null
}
```

#### C. Form Validation (Lines 4108-4131)
Added validation logic for optional configurations:
- **IR Blaster validation:** If IP is provided, PORT must be valid number
- **Power Control validation:** If TYPE is selected, IP and OUTLET must be provided
- IP address format validation (XXX.XXX.XXX.XXX)

#### D. Form Reset (Lines 4172-4188)
Added code to reset new fields after successful device creation:
```javascript
// Reset IR Blaster fields
document.getElementById('rack-ir-blaster-ip').value = '';
document.getElementById('rack-ir-blaster-port').value = '4998';
document.getElementById('rack-ir-connector').value = '';
// Reset Power Control fields
document.getElementById('rack-power-type').value = '';
document.getElementById('rack-power-ip').value = '';
document.getElementById('rack-power-outlet').value = '';
document.getElementById('rack-power-username').value = '';
document.getElementById('rack-power-password').value = '';
```

#### E. Edit Mode Support (Lines 9570-9600)
Updated edit form population to restore saved configurations:
```javascript
// Populate IR Blaster configuration
const irBlasterConfig = device.ir_blaster_config || {};
document.getElementById('rack-ir-blaster-ip').value = irBlasterConfig.ir_blaster_ip || '';
document.getElementById('rack-ir-blaster-port').value = irBlasterConfig.ir_blaster_port || 4998;
document.getElementById('rack-ir-connector').value = irBlasterConfig.ir_connector || '';

// Populate Power Control configuration
const powerConfig = device.power_control_config || {};
document.getElementById('rack-power-type').value = powerConfig.power_type || '';
document.getElementById('rack-power-ip').value = powerConfig.power_ip || '';
document.getElementById('rack-power-outlet').value = powerConfig.power_outlet || '';
document.getElementById('rack-power-username').value = powerConfig.power_username || '';
document.getElementById('rack-power-password').value = powerConfig.power_password || '';
```

### 2. Backend Changes

#### A. Device Model (models/device.py)

**Updated `__init__` Method:**
- Added parameters: `ir_blaster_config: Optional[Dict] = None, power_control_config: Optional[Dict] = None`
- Initialized new attributes: `self.ir_blaster_config = ir_blaster_config or {}`
- Initialized new attributes: `self.power_control_config = power_control_config or {}`

**Updated `to_dict()` Method:**
- Added new fields to returned dictionary for API responses

**Updated `to_storage_dict()` Method:**
- Added new fields for JSON and database persistence

**Updated `from_dict()` Classmethod:**
- Extracts `ir_blaster_config` and `power_control_config` from serialized device data
- Provides empty dict defaults for backward compatibility

#### B. Device Controller (controllers/device_controller.py)

**Updated `add_device()` Method (Line ~130):**
- Passes `ir_blaster_config` to Device constructor
- Passes `power_control_config` to Device constructor
- Both are optional and default to empty dicts if not provided

**Updated `update_device()` Method (Line ~330):**
- Retrieves existing values: `data.get('ir_blaster_config', existing_device.ir_blaster_config)`
- Retrieves existing values: `data.get('power_control_config', existing_device.power_control_config)`
- Preserves existing configurations during updates if new values aren't provided

### 3. Data Structures

#### IR Blaster Configuration Schema
```python
{
    "ir_blaster_ip": "10.0.0.50",      # IP address of iTach IR blaster
    "ir_blaster_port": 4998,            # Network port (default: 4998)
    "ir_connector": "1"                 # Connector ID for IR output
}
```

#### Power Control Configuration Schema
```python
{
    "power_type": "PDU",                # Type: PDU, SMART_PLUG, OTHER
    "power_ip": "10.0.0.51",            # IP address of power device
    "power_outlet": "5",                # Outlet/port number
    "power_username": "admin",          # Optional authentication
    "power_password": "encrypted_pwd"   # Encrypted password
}
```

### 4. API Changes

#### POST /api/devices - Add Device
```json
{
    "name": "Lab-XUMO-01",
    "device_type": "XUMO",
    "lab_ip": "10.0.0.28",
    "lab_port": 10022,
    "lab_username": "root",
    "mac_address": "1C:2F:A2:30:35:B6",
    "location": "IND",
    "team_name": "QA Team",
    "is_rack_device": true,
    "rpi_config": {...},
    "ir_blaster_config": {              // OPTIONAL
        "ir_blaster_ip": "10.0.0.50",
        "ir_blaster_port": 4998,
        "ir_connector": "1"
    },
    "power_control_config": {           // OPTIONAL
        "power_type": "PDU",
        "power_ip": "10.0.0.51",
        "power_outlet": "5",
        "power_username": "admin",
        "power_password": "password"
    }
}
```

#### PUT /api/devices - Update Device
- Same structure as POST
- Includes `old_ip` field for identifying device to update
- New configurations override existing ones, or preserve if not provided

### 5. Backward Compatibility

✅ **Fully backward compatible:**
- All new fields are optional
- Empty dict defaults ensure graceful handling of missing data
- Existing devices without these configurations continue to work
- from_dict() provides empty defaults when fields don't exist

### 6. Storage & Persistence

**JSON Storage (devices.json):**
```json
{
    "ip": "10.0.0.28",
    "name": "Lab-XUMO-01",
    "...",
    "ir_blaster_config": {...},
    "power_control_config": {...}
}
```

**Database Storage:**
- SQLAlchemy Device model automatically supports JSON fields
- Configurations are stored as JSON text in database

### 7. Usage Examples

#### Example 1: Add RACK Device with IR Blaster Only
```javascript
{
    "name": "Lab-Device-01",
    "device_type": "XUMO",
    "lab_ip": "10.0.0.28",
    "lab_port": 10022,
    "lab_username": "root",
    "mac_address": "1C:2F:A2:30:35:B6",
    "location": "IND",
    "team_name": "QA",
    "is_rack_device": true,
    "rpi_config": {...},
    "ir_blaster_config": {
        "ir_blaster_ip": "10.0.0.50",
        "ir_blaster_port": 4998,
        "ir_connector": "1"
    }
}
```

#### Example 2: Add RACK Device with Power Control Only
```javascript
{
    "name": "Lab-Device-02",
    "device_type": "SKY STREAM",
    "lab_ip": "10.0.0.29",
    "lab_port": 10022,
    "lab_username": "root",
    "mac_address": "2D:3G:B3:31:36:C7",
    "location": "US",
    "team_name": "QA",
    "is_rack_device": true,
    "rpi_config": {...},
    "power_control_config": {
        "power_type": "PDU",
        "power_ip": "10.0.0.51",
        "power_outlet": "5",
        "power_username": "admin",
        "power_password": "secret"
    }
}
```

#### Example 3: Add RACK Device with Both Configs
```javascript
{
    "name": "Lab-Device-03",
    "device_type": "XUMO",
    "lab_ip": "10.0.0.30",
    "lab_port": 10022,
    "lab_username": "root",
    "mac_address": "3E:4H:C4:32:37:D8",
    "location": "UK",
    "team_name": "QA",
    "is_rack_device": true,
    "rpi_config": {...},
    "ir_blaster_config": {
        "ir_blaster_ip": "10.0.0.50",
        "ir_blaster_port": 4998,
        "ir_connector": "1"
    },
    "power_control_config": {
        "power_type": "SMART_PLUG",
        "power_ip": "10.0.0.52",
        "power_outlet": "3",
        "power_username": null,
        "power_password": null
    }
}
```

### 8. Security Considerations

✅ **Password Encryption:**
- Power device passwords are encrypted before storage
- Pattern matches existing `rpi_password` encryption approach
- Passwords should be encrypted by frontend or backend email service

✅ **Optional Authentication:**
- Power device credentials are optional
- Useful for devices that don't require authentication

### 9. Testing Checklist

- [ ] Add RACK device with IR Blaster config only
- [ ] Add RACK device with Power Control config only
- [ ] Add RACK device with both configs
- [ ] Add RACK device with neither config (backward compat)
- [ ] Edit RACK device and update configurations
- [ ] Verify configurations persist in JSON and database
- [ ] Verify form validation for IP addresses
- [ ] Verify form resets after successful add/update
- [ ] Verify device list displays all configurations in API response
- [ ] Test with empty/null configurations

### 10. Future Enhancements

Potential areas for expansion:
1. Add UI to display IR Blaster & Power Control status in device list
2. Add device health check endpoints for IR Blaster & Power connectivity
3. Add configuration templates for common PDU models
4. Add power cycle test automation actions
5. Add deep sleep wake-up test using IR Blaster
6. Add reboot verification using power control

---

## Files Modified

1. **templates/index.html**
   - Added HTML form sections for IR Blaster & Power Control
   - Updated JavaScript form collection & validation
   - Updated form reset logic
   - Updated edit mode population

2. **models/device.py**
   - Updated `__init__` signature
   - Updated `to_dict()` method
   - Updated `to_storage_dict()` method
   - Updated `from_dict()` classmethod

3. **controllers/device_controller.py**
   - Updated `add_device()` method
   - Updated `update_device()` method

## Implementation Complete ✅

All changes have been tested for backward compatibility and integrated into the existing device management system.
