# GDF IR Key Press Implementation - Analysis & Requirements

**Date:** August 5, 2026  
**Status:** Analysis Complete - Ready for Implementation  
**Current State:** DESK devices use iTach, GDF_RACK devices NOT supported yet

---

## 📊 Current Implementation Analysis

### **DESK Devices (Working)**
```
User selects IR keys in UI 
    ↓
test_execution_service.py calls execute_ir_test_process()
    ↓
Method gets IR config (iTach IP/Port, remote type)
    ↓
Generates IR code using device-specific keycodes
    ↓
Sends IR command via iTach device (socket/HTTP)
    ↓
Optionally verifies via SSH logs (device logs check)
```

**Files Involved:**
- `methods/method_ir_test.py` - Main IR test execution
- `services/test_execution_service.py` - Calls IR test method (line 1012-1019)
- `config/config_ir_blaster.py` - IR code generation
- `models/device.py` - Device properties (has `is_rack_device`, `mac_address`, `device_type`)

---

## 🎯 GDF_RACK Implementation Requirements

### **1. Device Properties Available**
✅ Device object has all needed properties:
- `device.is_rack_device` (bool) - Identifies rack devices
- `device.mac_address` (str) - Required for GDF API URL
- `device.device_type` (str) - Used to determine keySet

### **2. GDF API Format**

**URL Pattern:**
```
https://app.catsprd.comcast.net/gdf/gateway/rest/settop/<DEVICE_MAC>/ir/pressKey?command=<KEY>&keySet=<KEYSET>
```

**URL Components:**
- `<DEVICE_MAC>` - Device MAC address (e.g., `38:54:39:76:8E:90`)
- `<KEY>` - IR key command (e.g., `HOME`, `POWER`, `UP`, `DOWN`)
- `<KEYSET>` - Device-specific remote control set:
  - `PR1_T2` - XUMO devices
  - `LC103` - SKYSTREAM devices

**Example Request:**
```
GET https://app.catsprd.comcast.net/gdf/gateway/rest/settop/38:54:39:76:8E:90/ir/pressKey?command=HOME&keySet=PR1_T2
Response: HTTP 200
```

### **3. Key Mapping Strategy**

**Option A: Direct Key Pass-Through**
```
User selects: HOME → API sends: command=HOME
User selects: POWER → API sends: command=POWER
User selects: UP → API sends: command=UP
```

**Option B: Mapped Key Codes (if different from XUMO)**
```
If device_type == 'SKYSTREAM':
    Map key names to LC103 codes
Else:
    Use key names directly (PR1_T2)
```

## 🔧 Implementation Steps

### **Step 1: Modify `execute_ir_test_process()` signature**

**Current:**
```python
def execute_ir_test_process(device_ip, port, username, password, iteration=1, 
                            device_name="Device", selected_keys=None, 
                            combined_method_name=None, remote_type_override=None, 
                            device_type=None, key_delay=0.5):
```

**Updated:**
```python
def execute_ir_test_process(device_ip, port, username, password, iteration=1, 
                            device_name="Device", selected_keys=None, 
                            combined_method_name=None, remote_type_override=None, 
                            device_type=None, key_delay=0.5,
                            is_rack_device=False,        # NEW
                            device_mac_address=None,     # NEW
                            gdf_api_endpoint=None):      # NEW
```

### **Step 2: Add GDF API detection logic**

```python
# In execute_ir_test_process():
if is_rack_device and device_mac_address:
    # Use GDF API for rack devices
    return execute_gdf_ir_test_process(device_mac_address, selected_keys, 
                                      device_type, iteration, key_delay)
else:
    # Use existing iTach method for DESK devices
    return execute_ir_test_process_desk(device_ip, port, username, password, ...)
```

### **Step 3: Create new GDF IR function**

**New file:** `methods/method_gdf_ir_test.py`

```python
def execute_gdf_ir_test_process(device_mac, selected_keys, device_type, 
                                iteration, key_delay, gdf_api_endpoint=None):
    """
    Execute IR Command Test for GDF_RACK devices using ECATS API
    
    Args:
        device_mac: Device MAC address (e.g., '38:54:39:76:8E:90')
        selected_keys: List of IR keys to send
        device_type: Device type ('XUMO', 'SKYSTREAM')
        iteration: Current iteration number
        key_delay: Delay between key presses
        gdf_api_endpoint: GDF API base URL (default from config)
    
    Returns:
        Dict with success status and results
    """
    
    if not gdf_api_endpoint:
        gdf_api_endpoint = "https://app.catsprd.comcast.net/gdf/gateway/rest/settop"
    
    # Determine keySet based on device type
    key_set = determine_keyset(device_type)  # Returns 'PR1_T2' or 'LC103'
    
    # Send each key via GDF API
    for key in selected_keys:
        url = f"{gdf_api_endpoint}/{device_mac}/ir/pressKey?command={key}&keySet={key_set}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                log_message(f"✓ IR key '{key}' sent successfully (status: 200)")
            else:
                log_message(f"❌ IR key '{key}' failed (status: {response.status_code})")
                log_message(f"   Response: {response.text}")
                return {"success": False, "message": f"GDF API error: {response.status_code}"}
        
        except requests.ConnectTimeout:
            log_message(f"❌ GDF API timeout sending key '{key}'")
            return {"success": False, "message": "GDF API timeout"}
        except Exception as e:
            log_message(f"❌ Error sending IR key '{key}': {e}")
            return {"success": False, "message": str(e)}
        
        # Wait between key presses
        time.sleep(key_delay)
    
    return {"success": True, "message": "All IR keys sent successfully"}
```

### **Step 4: Update test_execution_service.py call**

**Current (line 1012-1019):**
```python
method_result = execute_ir_test_process(
    conn_device_ip, conn_port, conn_username, conn_password,
    i + 1, device.name, ir_keys, 
    combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
    remote_type_override=remote_type, key_delay=ir_key_delay
)
```

**Updated:**
```python
method_result = execute_ir_test_process(
    conn_device_ip, conn_port, conn_username, conn_password,
    i + 1, device.name, ir_keys, 
    combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
    remote_type_override=remote_type, key_delay=ir_key_delay,
    is_rack_device=device.is_rack_device,              # NEW
    device_mac_address=device.mac_address,            # NEW
)
```

### **Step 5: Add keySet mapping helper**

```python
def determine_keyset(device_type):
    """
    Determine GDF keySet based on device type
    
    Args:
        device_type: Device type string (e.g., 'XUMO', 'SKY STREAM', 'SKYSTREAM')
    
    Returns:
        keySet string ('PR1_T2' or 'LC103')
    """
    if not device_type:
        return 'PR1_T2'  # Default to XUMO
    
    device_type_upper = device_type.upper()
    
    if 'SKY' in device_type_upper:
        return 'LC103'
    elif 'XUMO' in device_type_upper:
        return 'PR1_T2'
    else:
        return 'PR1_T2'  # Default to XUMO
```

---

## 📋 Configuration Requirements

### **Required Device Properties**
When adding a GDF_RACK device, ensure these are set:
- ✅ `ip` - Device IP (for SSH fallback if needed)
- ✅ `name` - Device name
- ✅ `mac_address` - **REQUIRED** for GDF API (e.g., `38:54:39:76:8E:90`)
- ✅ `device_type` - **REQUIRED** for keySet selection (`XUMO` or `SKYSTREAM`)
- ✅ `is_rack_device` - **REQUIRED** must be `true`

### **Optional Configuration**
- `gdf_api_endpoint` - Can be overridden (default: `https://app.catsprd.comcast.net/gdf/gateway/rest/settop`)
- Device-specific auth if needed (currently assumes public API)

---

## 🔑 Supported IR Key Commands

**Common keys for both XUMO (PR1_T2) and SKYSTREAM (LC103):**

| Key Name | Purpose | Works With |
|----------|---------|-----------|
| `HOME` | Go to home screen | Both |
| `POWER` | Toggle power | Both |
| `UP` | Navigate up | Both |
| `DOWN` | Navigate down | Both |
| `LEFT` | Navigate left | Both |
| `RIGHT` | Navigate right | Both |
| `SELECT` / `OK` | Confirm selection | Both |
| `ENTER` | Confirm action | Both |
| `BACK` / `EXIT` | Go back | Both |
| `MENU` | Open menu | Both |
| `GUIDE` | Open guide | Both |
| `INFO` | Show info | Both |
| `CHUP` | Channel up | Both |
| `CHDOWN` | Channel down | Both |
| `VOLUP` | Volume up | Both |
| `VOLDOWN` | Volume down | Both |
| `MUTE` | Mute audio | Both |

---

## ⚠️ Error Handling Strategy

### **Failures to Handle**

1. **Missing MAC Address**
   ```
   ❌ Error: MAC address not configured for GDF_RACK device
   Solution: User must enter MAC address in device setup
   ```

2. **GDF API Unreachable**
   ```
   ❌ Error: Cannot reach https://app.catsprd.comcast.net/gdf/gateway/rest/settop
   Solution: Check network connectivity to GDF endpoint
   ```

3. **Invalid IR Key**
   ```
   ❌ Error: Key 'INVALID_KEY' not supported by keySet PR1_T2
   Solution: Validate key before sending
   ```

4. **API Response Errors**
   ```
   ❌ Error: HTTP 400 - Bad Request
   ❌ Error: HTTP 403 - Forbidden (auth issue)
   ❌ Error: HTTP 404 - Device not found
   ❌ Error: HTTP 500 - Server error
   ```

### **Retry Logic**
- Retry count: 2 attempts per key
- Retry delay: 2 seconds between attempts
- Fail-fast on 403/404 (auth/device issues)

---

## 🧪 Testing Scenarios

### **Test 1: Single Key - XUMO Device**
```
Device: GDF_RACK XUMO
MAC: 38:54:39:76:8E:90
Key: HOME
Expected: HTTP 200 ✓
Log: ✓ IR key 'HOME' sent successfully (status: 200)
```

### **Test 2: Multiple Keys - SKYSTREAM Device**
```
Device: GDF_RACK SKYSTREAM
MAC: AA:BB:CC:DD:EE:FF
Keys: [HOME, DOWN, DOWN, SELECT]
Expected: All 4 keys sent with delays
Log: ✓ All IR keys sent successfully
```

### **Test 3: Fallback to DESK method**
```
Device: DESK device (is_rack_device=false)
Keys: [HOME, POWER]
Expected: Routes to iTach method (existing behavior)
Log: [IR CONFIG] Device using iTach...
```

### **Test 4: Missing MAC Address**
```
Device: GDF_RACK but mac_address is empty
Expected: Graceful error
Log: ❌ ERROR: MAC address not configured for GDF_RACK device
```

---

## 📊 API Response Timeline

**Current behavior (typical timings):**

| Step | Time | Notes |
|------|------|-------|
| Single IR key via API | 1-2 sec | Network latency + API processing |
| Key delay (between keys) | 0.5-2 sec | Configurable |
| Total for 5 keys | 5-10 sec | 5 keys × (1s API + 1s delay) |

---

## 🚀 Implementation Checklist

- [ ] **Create** `methods/method_gdf_ir_test.py` with GDF API logic
- [ ] **Update** `methods/method_ir_test.py` to route to GDF for rack devices
- [ ] **Add** function parameters to pass `is_rack_device`, `mac_address`, etc.
- [ ] **Update** `services/test_execution_service.py` to pass new parameters
- [ ] **Add** keySet mapping logic
- [ ] **Add** error handling and logging
- [ ] **Add** configuration for GDF API endpoint (config file)
- [ ] **Test** with GDF_RACK XUMO device
- [ ] **Test** with GDF_RACK SKYSTREAM device
- [ ] **Test** fallback to DESK iTach method
- [ ] **Document** in UI help for device MAC address requirement
- [ ] **Add** validation to ensure MAC address provided for rack devices

---

## 📝 Summary

**Current State:**
- ❌ GDF_RACK devices cannot use "IR Command Test" method
- ✅ DESK devices use iTach successfully

**After Implementation:**
- ✅ GDF_RACK XUMO devices can send IR via `keySet=PR1_T2`
- ✅ GDF_RACK SKYSTREAM devices can send IR via `keySet=LC103`
- ✅ Automatic routing based on `is_rack_device` flag
- ✅ Full error handling and logging
- ✅ Backward compatible with DESK devices

**Key Dependencies:**
- Device must have `mac_address` configured
- Device must have `device_type` set to determine keySet
- GDF API endpoint must be accessible from server
- HTTP requests library (requests) available

