# GDF IR Key Press Implementation - Technical Architecture

## 🏗️ System Architecture

### **Before Implementation (Current)**
```
┌─────────────────────────────────────────────────────────────┐
│                    UI: IR Command Test                       │
│            User selects keys: [HOME, DOWN, SELECT]           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
         ┌──────────────────────────┐
         │ test_execution_service   │
         │                          │
         │ Calls: execute_ir_test   │
         │ _process()               │
         └────────────┬─────────────┘
                      │
                      ↓
    ┌────────────────────────────────────┐
    │  method_ir_test.py                 │
    │                                    │
    │  (Only handles DESK devices)       │
    │  - iTach IR blaster                │
    │  - SSH verification                │
    └────────────────────────────────────┘
           │                │
           └─ Works ✅     └─ Fails ❌ for GDF_RACK
         (DESK devices)    (No MAC→No API call)
```

### **After Implementation (New)**
```
┌─────────────────────────────────────────────────────────────┐
│                    UI: IR Command Test                       │
│            User selects keys: [HOME, DOWN, SELECT]           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
         ┌──────────────────────────────────────┐
         │   test_execution_service             │
         │                                      │
         │   Passes:                            │
         │   - is_rack_device                   │
         │   - device_mac_address              │
         │   - device_type                      │
         └────────────────────┬─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ↓                   ↓
        ┌─────────────────────┐  ┌────────────────────┐
        │ method_ir_test.py   │  │method_gdf_ir_test  │
        │                     │  │.py (NEW)           │
        │ DESK Logic          │  │                    │
        │ - iTach IR blaster  │  │ GDF_RACK Logic     │
        │ - SSH verification  │  │ - HTTP API calls   │
        └─────────────────────┘  │ - Response handling│
               │                 └────────────────────┘
               │                         │
               └───────┬─────────────────┘
                       │
            Device Type Branch
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ↓                      ↓
    DESK Devices         GDF_RACK Devices
    (XUMO/Other)         (XUMO/SKYSTREAM)
        │                      │
        ↓                      ↓
   ┌─────────────────┐  ┌──────────────────────────┐
   │ iTach Blaster   │  │ GDF ECATS API            │
   │ IR Codes        │  │                          │
   │ SSH Logs        │  │ URL Format:              │
   └─────────────────┘  │ https://.../settop/     │
                        │ <MAC>/ir/pressKey       │
                        │ ?command=<KEY>          │
                        │ &keySet=<KEYSET>        │
                        └──────────────────────────┘
```

---

## 🔄 Call Flow Diagram

### **Decision Tree**
```
START: execute_ir_test_process()
│
├─ Is device a GDF_RACK? (is_rack_device==true)
│  │
│  ├─ YES
│  │  │
│  │  ├─ Does device have MAC address?
│  │  │  │
│  │  │  ├─ YES → Call execute_gdf_ir_test_process()
│  │  │  │           │
│  │  │  │           ├─ Determine keySet
│  │  │  │           │  (based on device_type)
│  │  │  │           │
│  │  │  │           ├─ For each IR key:
│  │  │  │           │  └─ Send HTTP GET to GDF API
│  │  │  │           │     └─ Wait for response
│  │  │  │           │     └─ Log result
│  │  │  │           │     └─ Wait key_delay
│  │  │  │           │
│  │  │  │           └─ Return success/failure
│  │  │  │
│  │  │  └─ NO → Log error & return failure
│  │  │
│  │  └─ (ELSE) Continue to DESK method
│  │
│  └─ NO → Call execute_ir_test_process_desk()
│           │
│           ├─ Get iTach config
│           ├─ Generate IR codes
│           ├─ Send via iTach
│           └─ Verify via SSH logs
```

---

## 📝 Code Changes Required

### **File 1: method_ir_test.py (EXISTING)**

**Changes:**
- Split logic into DESK and GDF paths
- Add parameters: `is_rack_device`, `device_mac_address`
- Add routing logic

**Before:**
```python
def execute_ir_test_process(device_ip, port, username, password, 
                            iteration=1, device_name="Device", 
                            selected_keys=None, ...):
    # Only handles DESK devices
    ...
```

**After:**
```python
def execute_ir_test_process(device_ip, port, username, password, 
                            iteration=1, device_name="Device", 
                            selected_keys=None,
                            is_rack_device=False,          # NEW
                            device_mac_address=None,       # NEW
                            ...):
    
    # Route to appropriate handler
    if is_rack_device and device_mac_address:
        from methods.method_gdf_ir_test import execute_gdf_ir_test_process
        return execute_gdf_ir_test_process(
            device_mac_address, selected_keys, 
            device_type, iteration, key_delay
        )
    else:
        # Existing DESK device logic
        return execute_ir_test_process_desk(...)
```

---

### **File 2: method_gdf_ir_test.py (NEW)**

**Purpose:** Handle GDF API calls for rack devices

```python
#!/usr/bin/env python3
"""
GDF IR Command Test Process Implementation
For GDF_RACK devices using ECATS REST API
"""

import requests
import time
import logging
from datetime import datetime, timezone
from methods.method_utils import log_message

def determine_keyset(device_type):
    """Determine keySet based on device type"""
    if not device_type:
        return 'PR1_T2'  # Default XUMO
    
    device_type_upper = device_type.upper()
    
    if 'SKY' in device_type_upper:
        return 'LC103'
    else:
        return 'PR1_T2'

def send_gdf_ir_command(mac_address, ir_key, keyset, api_endpoint, timeout=10):
    """
    Send single IR command via GDF API
    
    Returns:
        Tuple: (success: bool, response_status: int, message: str)
    """
    url = f"{api_endpoint}/{mac_address}/ir/pressKey?command={ir_key}&keySet={keyset}"
    
    try:
        log_message(f"[GDF API] Sending key '{ir_key}' via {url[:80]}...")
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            log_message(f"✓ IR key '{ir_key}' sent successfully (HTTP {response.status_code})")
            return (True, response.status_code, response.text[:100])
        else:
            log_message(f"❌ IR key '{ir_key}' API error (HTTP {response.status_code})")
            log_message(f"   Response: {response.text[:200]}")
            return (False, response.status_code, response.text[:200])
    
    except requests.Timeout:
        log_message(f"❌ Timeout sending IR key '{ir_key}' (>{timeout}s)")
        return (False, 0, f"Timeout after {timeout}s")
    
    except requests.ConnectionError as e:
        log_message(f"❌ Connection error sending IR key '{ir_key}': {e}")
        return (False, 0, f"Connection error: {str(e)[:100]}")
    
    except Exception as e:
        log_message(f"❌ Unexpected error sending IR key '{ir_key}': {e}")
        return (False, 0, f"Unexpected error: {str(e)[:100]}")

def execute_gdf_ir_test_process(device_mac, selected_keys, device_type, 
                                iteration=1, key_delay=0.5, 
                                gdf_api_endpoint=None):
    """
    Execute IR Command Test for GDF_RACK devices
    
    Args:
        device_mac: Device MAC address (e.g., '38:54:39:76:8E:90')
        selected_keys: List of IR keys to send
        device_type: Device type ('XUMO', 'SKYSTREAM', etc.)
        iteration: Current iteration number
        key_delay: Delay (sec) between key sends
        gdf_api_endpoint: GDF API base URL (optional)
    
    Returns:
        Dict: {'success': bool, 'message': str, 'iteration': int}
    """
    
    if not gdf_api_endpoint:
        gdf_api_endpoint = "https://app.catsprd.comcast.net/gdf/gateway/rest/settop"
    
    log_message(f"\n{'='*70}")
    log_message(f"[GDF IR TEST] Starting GDF IR command test - Iteration {iteration}")
    log_message(f"{'='*70}")
    log_message(f"[GDF CONFIG] Device MAC: {device_mac}")
    log_message(f"[GDF CONFIG] Device Type: {device_type}")
    log_message(f"[GDF CONFIG] Selected Keys: {', '.join(selected_keys)}")
    
    # Determine keySet
    keyset = determine_keyset(device_type)
    log_message(f"[GDF CONFIG] KeySet: {keyset}")
    log_message(f"[GDF CONFIG] API Endpoint: {gdf_api_endpoint}")
    log_message(f"[GDF CONFIG] Key Delay: {key_delay}s")
    
    # Validate inputs
    if not selected_keys:
        log_message("❌ No IR keys specified")
        return {
            "success": False,
            "message": "No IR keys provided",
            "iteration": iteration
        }
    
    if not device_mac:
        log_message("❌ No MAC address provided for GDF API")
        return {
            "success": False,
            "message": "GDF API requires device MAC address",
            "iteration": iteration
        }
    
    # Send IR commands
    all_success = True
    failed_keys = []
    results = []
    
    for idx, ir_key in enumerate(selected_keys):
        log_message(f"\n[IR COMMAND {idx+1}/{len(selected_keys)}] Sending '{ir_key}'...")
        
        success, status, response = send_gdf_ir_command(
            device_mac, ir_key, keyset, 
            gdf_api_endpoint, timeout=10
        )
        
        results.append({
            'key': ir_key,
            'success': success,
            'http_status': status,
            'response': response
        })
        
        if not success:
            all_success = False
            failed_keys.append(ir_key)
        
        # Wait before next key (except after last key)
        if idx < len(selected_keys) - 1:
            log_message(f"[WAIT] Waiting {key_delay}s before next key...")
            time.sleep(key_delay)
    
    # Summary
    log_message(f"\n{'='*70}")
    log_message(f"[SUMMARY] Total Keys: {len(selected_keys)}")
    log_message(f"[SUMMARY] Successful: {len(selected_keys) - len(failed_keys)}")
    log_message(f"[SUMMARY] Failed: {len(failed_keys)}")
    
    if failed_keys:
        log_message(f"[SUMMARY] Failed keys: {', '.join(failed_keys)}")
        log_message(f"{'='*70}")
        return {
            "success": False,
            "message": f"Failed to send keys: {', '.join(failed_keys)}",
            "iteration": iteration,
            "details": results
        }
    else:
        log_message("✓ All IR keys sent successfully")
        log_message(f"{'='*70}")
        return {
            "success": True,
            "message": f"All {len(selected_keys)} IR keys sent successfully via GDF API",
            "iteration": iteration,
            "details": results
        }
```

---

### **File 3: test_execution_service.py (MODIFIED)**

**Change Location:** Line ~1012-1019

**Before:**
```python
method_result = execute_ir_test_process(
    conn_device_ip, conn_port, conn_username, conn_password,
    i + 1, device.name, ir_keys, 
    combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
    remote_type_override=remote_type, key_delay=ir_key_delay
)
```

**After:**
```python
method_result = execute_ir_test_process(
    conn_device_ip, conn_port, conn_username, conn_password,
    i + 1, device.name, ir_keys, 
    combined_method_name=combined_method_name if len(execution_queue) > 1 else None,
    remote_type_override=remote_type, key_delay=ir_key_delay,
    is_rack_device=device.is_rack_device,              # NEW
    device_mac_address=device.mac_address,            # NEW
    device_type=device.device_type                    # NEW (for keySet determination)
)
```

---

## 🧪 Test Cases

### **Test Case 1: XUMO Rack Device - Single Key**
```
Device: GDF_RACK XUMO
MAC: 38:54:39:76:8E:90
Keys: [HOME]

Expected API Call:
GET https://app.catsprd.comcast.net/gdf/gateway/rest/settop/38:54:39:76:8E:90/ir/pressKey?command=HOME&keySet=PR1_T2

Expected Result:
✓ IR key 'HOME' sent successfully (HTTP 200)
{
  "success": true,
  "message": "All 1 IR keys sent successfully via GDF API",
  "iteration": 1,
  "details": [
    {
      "key": "HOME",
      "success": true,
      "http_status": 200,
      "response": "..."
    }
  ]
}
```

### **Test Case 2: SKYSTREAM Rack Device - Multiple Keys**
```
Device: GDF_RACK SKYSTREAM
MAC: AA:BB:CC:DD:EE:FF
Keys: [HOME, DOWN, DOWN, SELECT]

Expected API Calls:
GET .../AA:BB:CC:DD:EE:FF/ir/pressKey?command=HOME&keySet=LC103
GET .../AA:BB:CC:DD:EE:FF/ir/pressKey?command=DOWN&keySet=LC103
GET .../AA:BB:CC:DD:EE:FF/ir/pressKey?command=DOWN&keySet=LC103
GET .../AA:BB:CC:DD:EE:FF/ir/pressKey?command=SELECT&keySet=LC103

Expected Result:
✓ All 4 IR keys sent successfully via GDF API
```

### **Test Case 3: DESK Device - Fallback to iTach**
```
Device: DESK (is_rack_device=false)
Keys: [HOME, POWER]

Expected Behavior:
Routes to DESK method (existing iTach logic)
No GDF API calls made
✓ Uses iTach IR blaster instead
```

### **Test Case 4: Missing MAC Address**
```
Device: GDF_RACK but mac_address=""
Keys: [HOME]

Expected Result:
❌ GDF API requires device MAC address
{
  "success": false,
  "message": "GDF API requires device MAC address",
  "iteration": 1
}
```

---

## ✅ Benefits

**For Users:**
- ✅ Can test GDF_RACK devices with IR commands
- ✅ Same UI experience as DESK devices
- ✅ Automatic routing (no user changes needed)

**For System:**
- ✅ Backward compatible (DESK devices unchanged)
- ✅ Modular design (GDF logic isolated)
- ✅ Extensible (easy to add new platforms)
- ✅ Proper error handling & logging

---

## 🚀 Deployment Checklist

- [ ] Create `method_gdf_ir_test.py`
- [ ] Update `method_ir_test.py` routing logic
- [ ] Update `test_execution_service.py` function calls
- [ ] Add `requests` library to requirements (if not present)
- [ ] Configure GDF API endpoint (if not standard)
- [ ] Test with XUMO rack device
- [ ] Test with SKYSTREAM rack device  
- [ ] Test fallback to DESK method
- [ ] Test error scenarios
- [ ] Update device registration UI (mention MAC requirement)
- [ ] Document device setup guide

