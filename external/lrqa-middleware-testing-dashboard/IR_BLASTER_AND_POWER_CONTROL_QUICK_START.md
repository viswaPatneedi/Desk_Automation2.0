# IR Blaster & Power Control Configuration - Quick Start Guide

## Overview
This guide explains how to configure IR Blaster (iTach) and Power Control devices for GDF_RACK devices in the middleware testing dashboard.

## When to Use

### IR Blaster Configuration
Use IR Blaster when you need to:
- Send IR codes to devices (e.g., for remote control emulation)
- Wake up devices from deep sleep
- Control IR-based device functions
- Requires: iTach IR blaster device on network

### Power Control Configuration
Use Power Control when you need to:
- Power cycle devices remotely
- Control device power via PDU or smart outlet
- Reboot devices via power down/up
- Requires: PDU or smart power plug on network

## Accessing the Feature

### Adding a New GDF_RACK Device with Configurations

1. **Open Device Management Modal**
   - Click "Devices" → "Add/Manage Devices"
   - Nav to "GDF_RACK Devices" tab
   - Click "Add GDF_RACK Device"

2. **Fill Required Fields**
   - Device Name (e.g., "Lab-XUMO-01")
   - Device Type (XUMO or SKY STREAM)
   - Lab Device IP Address
   - Lab Device SSH Port (default: 10022)
   - Lab Device SSH Username (default: root)
   - Device MAC Address
   - Location
   - Team Name
   - R-Pi IP Address & Credentials

3. **Add Optional IR Blaster Configuration**
   - IR Blaster IP Address: `10.0.0.50`
   - IR Blaster Port: `4998` (default)
   - IR Connector ID: `1` (connector number on iTach)
   - Leave blank if not using IR Blaster

4. **Add Optional Power Control Configuration**
   - Power Control Type: Select from dropdown
     - PDU (Power Distribution Unit)
     - Smart Power Plug (WiFi/network outlet)
     - Other
   - Power Device IP Address: `10.0.0.51`
   - Power Outlet/Port Number: `5` (outlet number on PDU)
   - Power Device Username: `admin` (optional, if required)
   - Power Device Password: `password` (optional, encrypted before storage)
   - Leave blank if not using power control

5. **Submit**
   - Click "Add GDF_RACK Device"
   - Device will be saved with all configurations

## UI Sections Explained

### 🔌 IR Blaster (iTach) Configuration Section

**Purpose:** Allows IR code transmission to control devices

**Fields:**
| Field | Example | Required | Notes |
|-------|---------|----------|-------|
| IR Blaster IP | 10.0.0.50 | No | Leave empty if not available |
| IR Blaster Port | 4998 | No | Standard iTach port |
| IR Connector ID | 1 | No | Physical connector number |

**Help Text:**
- "Leave empty if IR Blaster is not available"
- "Standard iTach port"
- "Connector number for IR code output"

**Popular Products:**
- Control4 iTach IP2IR
- Global Cache iTach
- Other network IR blasters

### ⚡ Power Control Configuration Section

**Purpose:** Allows remote power management

**Fields:**
| Field | Example | Required | Notes |
|-------|---------|----------|-------|
| Power Control Type | PDU | No | Select: PDU / Smart Plug / Other |
| Power Device IP | 10.0.0.51 | If Type selected | Network address |
| Power Outlet/Port | 5 | If Type selected | Outlet number on device |
| Username | admin | No | Optional, device-specific |
| Password | ***** | No | Optional, encrypted storage |

**Dependencies:**
- If Power Type is selected, IP and Outlet become required
- Username and Password are optional

**How Validation Works:**
- ✓ All fields can be left blank (defaults to no power control)
- ✓ Power Type selected → IP & Outlet required
- ✓ Username/Password optional but fields must be valid IPs
- ✗ Partial config (Type but no IP) → Error

**Supported Power Types:**
1. **PDU (Power Distribution Unit)**
   - Requires: SNMP or HTTP management
   - Example: APC PDU, Raritan PDU
   - Outlet format: Usually 1-24

2. **Smart Power Plug**
   - Requires: Network connectivity
   - Example: KASA HS110, TP-Link, Meross
   - Outlet format: Usually just 1 (single plug) or specific outlet

3. **Other**
   - Generic / Custom power management
   - Requires manual integration

## Editing Device Configurations

### To Update a Device:

1. **Open Device Management Modal**
2. **Find the device** in the device list
3. **Click the device name** or edit icon
4. **Form pre-populates** with existing values
5. **Modify configurations** as needed
6. **Click "Update GDF_RACK Device"**
7. Device updated with new configurations

### To Clear a Configuration:

1. Open edit form (see above)
2. **Clear the fields** you want to remove:
   - Empty IR Blaster IP → removes all IR Blaster config
   - Empty Power Type → removes all Power Control config
3. **Click "Update GDF_RACK Device"**
4. Configuration cleared

## API Response Examples

### Get All Devices with Configurations

**Request:**
```bash
curl http://localhost:5000/api/devices
```

**Response:**
```json
{
  "success": true,
  "devices": [
    {
      "ip": "10.0.0.28",
      "name": "Lab-XUMO-01",
      "device_type": "XUMO",
      "mac_address": "1C:2F:A2:30:35:B6",
      "location": "IND",
      "team_name": "QA",
      "is_rack_device": true,
      "rpi_config": {
        "rpi_ip": "10.138.17.42",
        "rpi_port": 60201,
        "rpi_username": "pi",
        "rpi_password": "***encrypted***"
      },
      "ir_blaster_config": {
        "ir_blaster_ip": "10.0.0.50",
        "ir_blaster_port": 4998,
        "ir_connector": "1"
      },
      "power_control_config": {
        "power_type": "PDU",
        "power_ip": "10.0.0.51",
        "power_outlet": "5",
        "power_username": "admin",
        "power_password": "***encrypted***"
      }
    }
  ]
}
```

## Common Configuration Scenarios

### Scenario 1: Lab Device with IR Blaster Only
**Use Case:** Device needs remote control wake-up via IR

**Configuration:**
```
IR Blaster IP: 10.0.0.50
IR Blaster Port: 4998
IR Connector: 1

Power Control Type: (leave empty)
```

### Scenario 2: Lab Device with Power Control Only
**Use Case:** Device needs remote power cycle

**Configuration:**
```
IR Blaster IP: (leave empty)

Power Control Type: PDU
Power Device IP: 10.0.0.51
Power Outlet: 5
Username: admin
Password: pdupwd123
```

### Scenario 3: Lab Device with Both
**Use Case:** Complete remote device control

**Configuration:**
```
IR Blaster IP: 10.0.0.50
IR Blaster Port: 4998
IR Connector: 1

Power Control Type: Smart Power Plug
Power Device IP: 10.0.0.52
Power Outlet: 1
```

### Scenario 4: Minimal Lab Device
**Use Case:** Basic device without extras

**Configuration:**
```
IR Blaster IP: (leave empty)
Power Control Type: (leave empty)
```

## Validation Rules

### Field Requirements

| Field | Required | Condition |
|-------|----------|-----------|
| IR Blaster IP | No | Always optional |
| IR Blaster Port | No | Optional (default: 4998) |
| IR Connector | No | Optional (default: 1) |
| Power Type | No | Always optional |
| Power IP | Conditional | Only if Power Type selected |
| Power Outlet | Conditional | Only if Power Type selected |
| Username | No | Always optional |
| Password | No | Always optional |

### IP Address Format
- Must match pattern: `XXX.XXX.XXX.XXX`
- Valid: `10.0.0.50`
- Invalid: `10.0.0`, `a.b.c.d`, `localhost`

### Port Format
- Must be valid number
- Valid: `4998`, `5000`, `9000`
- Invalid: `port`, `-1`, `99999`

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "IR Blaster IP: invalid IP" | Wrong format | Use XXX.XXX.XXX.XXX format |
| "IR Blaster Port: must be a number" | Non-numeric input | Enter port number only |
| "Power Device IP: required" | Type selected but IP empty | Fill Power IP field |
| "Power Device IP: invalid IP" | Wrong format | Use XXX.XXX.XXX.XXX format |
| "Power Outlet: required" | Type selected but outlet empty | Fill Outlet field |

## Testing Connectivity

After adding/updating a device, verify configurations are working:

### Test IR Blaster Connectivity
```bash
# Check if IR Blaster is reachable
curl -I http://10.0.0.50:4998/

# Expected: HTTP response (200-404 OK)
# If timeout/refused: Check IP, port, firewall
```

### Test Power Control Connectivity
```bash
# For PDU (replace with your management IP/credentials)
snmpwalk -v2c -c public 10.0.0.51 .1.3.6.1.4.1.318

# For Smart Plug (manufacturer specific)
curl http://admin:password@10.0.0.52/info
```

## Troubleshooting

### Issue: Configurations not saving
- ✓ Check all required fields completed
- ✓ Verify IP addresses are valid format
- ✓ Check browser console for errors (F12)
- ✓ Refresh page and try again

### Issue: "Device already exists" error
- Device with same IP already in system
- Either update existing device or use different IP

### Issue: Configurations lost after update
- Ensure new config is filled in edit form
- Check that you're clicking "Update" not "Add"
- Verify form shows values before submitting

### Issue: API returns null configs
- Device added before this feature (backward compat)
- Edit and re-save device to populate configs
- Or manually update via database (admin only)

## Best Practices

✅ **DO:**
- Test connectivity to IR/Power devices before adding
- Document which outlet/connector is which
- Use descriptive device names
- Set correct location for team filtering
- Keep credentials in secure environment

❌ **DON'T:**
- Share passwords in logs or screenshots
- Mix different device vendors without testing
- Leave incomplete power control config
- Hardcode IP addresses in tests

## Future Use Cases

These configurations enable:
1. **Automated device power cycling** - for recovery tests
2. **Deep sleep wake testing** - IR codes to wake from sleep
3. **Reboot verification** - power cycle + status check
4. **Health checks** - periodic connectivity tests
5. **Automated recovery** - power reset on failures

## Getting Help

- Check configuration is stored: API `/api/devices` response
- Enable debug logging in frontend: Open browser console (F12)
- Check backend logs: app.log or console output
- Verify network connectivity: ping IR/Power device IPs
- Review this guide for common scenarios

---

**Status:** ✅ Feature available
**Tested:** Yes
**Backward Compatible:** Yes
**Requires Migration:** Yes (database only)
