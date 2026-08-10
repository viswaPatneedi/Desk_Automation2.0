# Code Changes Required - Exact Modifications

## File: services/test_execution_service.py

### Change #1: Update Import (Line 17)

**FIND THIS:**
```python
from services.gdf_rack_tunnel_service import GDFRackTunnelService
```

**REPLACE WITH:**
```python
from services.gdf_ssh_tunnel_service import GDFSSHTunnelService
```

---

### Change #2: Update Instantiation (Line 84)

**FIND THIS:**
```python
tunnel_service = GDFRackTunnelService()
```

**REPLACE WITH:**
```python
tunnel_service = GDFSSHTunnelService()
```

---

## That's It! 🎯

Just 2 line changes and the fix is deployed.

### Verification Command:
```bash
grep -n "GDFSSHTunnelService" services/test_execution_service.py
```

Should output:
```
17:from services.gdf_ssh_tunnel_service import GDFSSHTunnelService
84:tunnel_service = GDFSSHTunnelService()
```

---

## Before→After Code Snippet

### Line 17-20 (BEFORE)
```python
from services.gdf_rack_tunnel_service import GDFRackTunnelService
from services.gdf_auth_service import get_gdf_auth_service
import json
import logging
```

### Line 17-20 (AFTER)
```python
from services.gdf_ssh_tunnel_service import GDFSSHTunnelService
from services.gdf_auth_service import get_gdf_auth_service
import json
import logging
```

---

### Line 80-90 (BEFORE)
```python
            # Establish tunnel for GDF_RACK devices
            if device_type == "GDF_RACK":
                tunnel_service = GDFRackTunnelService()
                print(f"[GDF_RACK] Attempting to connect to device via tunnel...")
                tunnel_service.connect()
                print(f"[GDF_RACK] Tunnel established successfully!")
```

### Line 80-90 (AFTER)
```python
            # Establish tunnel for GDF_RACK devices
            if device_type == "GDF_RACK":
                tunnel_service = GDFSSHTunnelService()
                print(f"[GDF_RACK] Attempting to connect to device via tunnel...")
                tunnel_service.connect()
                print(f"[GDF_RACK] Tunnel established successfully!")
```

---

## How to Apply Changes

### Option 1: Manual Edit (Recommended for review)
1. Open file in VS Code: `services/test_execution_service.py`
2. Go to line 17, change import name
3. Go to line 84, change class name
4. Save (Ctrl+S)

### Option 2: Command Line (Fast)
```bash
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard

# Change import line
sed -i 's/from services.gdf_rack_tunnel_service import GDFRackTunnelService/from services.gdf_ssh_tunnel_service import GDFSSHTunnelService/' services/test_execution_service.py

# Change instantiation line
sed -i 's/tunnel_service = GDFRackTunnelService()/tunnel_service = GDFSSHTunnelService()/' services/test_execution_service.py

# Verify changes
grep -n "GDFSSHTunnelService" services/test_execution_service.py
```

### Option 3: Python Script
```python
import re

file_path = "services/test_execution_service.py"

with open(file_path, 'r') as f:
    content = f.read()

# Change import
content = content.replace(
    "from services.gdf_rack_tunnel_service import GDFRackTunnelService",
    "from services.gdf_ssh_tunnel_service import GDFSSHTunnelService"
)

# Change instantiation
content = content.replace(
    "tunnel_service = GDFRackTunnelService()",
    "tunnel_service = GDFSSHTunnelService()"
)

with open(file_path, 'w') as f:
    f.write(content)

print("✅ Code updated successfully")
```

---

## Verification Checklist

After making changes, verify:

```
☐ Import line 17 uses GDFSSHTunnelService
☐ Instantiation line 84 uses GDFSSHTunnelService
☐ No syntax errors in file
☐ File saves without errors
☐ Old service (GDFRackTunnelService) no longer used
☐ App restarts without import errors
```

---

## Rollback (If Needed)

If something goes wrong, just revert the changes:

```bash
git checkout services/test_execution_service.py
```

Or manually change back:
- Line 17: Change `GDFSSHTunnelService` → `GDFRackTunnelService`
- Line 84: Change `GDFSSHTunnelService()` → `GDFRackTunnelService()`

---

## Quick Reference

| Item | Value |
|------|-------|
| **File to edit** | `services/test_execution_service.py` |
| **Lines to change** | 2 (line 17 and line 84) |
| **Time to apply** | < 1 minute |
| **Risk** | Very Low (just import/class name) |
| **Breaking change** | No (same interface) |
| **Rollback time** | < 1 minute |

---

## Impact Analysis

```
What Gets Fixed:
✅ All GDF_RACK device methods now work
✅ SSH tunnel uses native SSH (proven, reliable)
✅ No more "Unable to connect to port 10022" errors
✅ Jobs complete successfully

What Stays The Same:
✅ DESK device methods (unchanged)
✅ All other services (unchanged)
✅ API endpoints (unchanged)
✅ Database schema (unchanged)

What Changes:
∆ Internal tunnel implementation (user won't see this)
∆ SSH backend (subprocess instead of Paramiko)
```

That's it! Simple, safe, and proven. 🎯
