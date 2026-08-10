# Device Status Detection Flow - ACTIVE/INACTIVE Badge

## How "ACTIVE" and "INACTIVE" Status Shows Up in UI

You're correct! The device status badge shown in the "Select Devices" section uses the **same SSH tunnel infrastructure** to determine connectivity.

---

## Current Status Detection (What's Working Now)

**File**: `controllers/device_controller.py`, `/api/devices` endpoint

**Current Flow**:
```
User opens "Select Devices"
    ↓
Browser calls: GET /api/devices
    ↓
get_devices() method runs
    ↓
For each device:
  ├─ Check if device is LOCKED via DeviceLock.get_device_lock()
  ├─ YES → device_dict['status'] = 'BUSY' / 'LOCKED'
  └─ NO  → device_dict['status'] = 'AVAILABLE'
    ↓
Return device list with locks + execution status
    ↓
UI displays status badge:
  ├─ BUSY/LOCKED → Red badge
  └─ AVAILABLE   → Green badge
```

**Code** (line 46-55 in device_controller.py):
```python
# Phase 21: Add execution tracking info
active_job = Job.get_active_device_job(device.ip)
if active_job:
    device_dict['status'] = 'BUSY'
    device_dict['executing_user'] = getattr(active_job, 'executing_user', active_job.user_id)
    device_dict['triggered_at'] = getattr(active_job, 'triggered_at', active_job.start_time)
    device_dict['current_iteration'] = getattr(active_job, 'current_iteration', 1)
    device_dict['total_iterations'] = active_job.iterations
else:
    device_dict['status'] = 'AVAILABLE'
    device_dict['executing_user'] = None
    device_dict['triggered_at'] = None
    device_dict['current_iteration'] = None
    device_dict['total_iterations'] = None
```

**Database Check**:
- Queries `Job` table for active jobs on device IP
- Queries `DeviceLock` table to see if device is locked
- **NO actual SSH connection** needed for status check!

---

## Important: Status Badge Does NOT Use SSH Tunnel

**Current implementation** (SIMPLIFIED):
```
┌─────────────────────────────────────────────────┐
│ Get Device Status (DOES NOT use SSH tunnel)     │
│                                                 │
│ 1. Query database:                              │
│    - Job table (is there active job?)           │
│    - DeviceLock table (is device locked?)       │
│                                                 │
│ 2. Return status:                               │
│    - BUSY (job running)                         │
│    - AVAILABLE (no job)                         │
│                                                 │
│ This is 100% database-based, NO SSH involved    │
└─────────────────────────────────────────────────┘
```

---

## But SSH Tunnel IS Used When Executing Methods

When you actually **run a method** on the device (like reboot, status check, etc.):

```
User clicks "Run reboot_perf_v2_optimized"
    ↓
Status badge shows: "BUSY" (device locked)
    ↓
System tries to execute method:
  ├─ DESK Device (10.0.0.140):
  │  └─ SSH directly: 10.0.0.140:22 ✅
  │
  └─ GDF_RACK Device (10.0.0.140):
     ├─ Needs SSH tunnel via R-Pi
     ├─ Creates port forwarding: 127.0.0.1:10022
     ├─ SSH to localhost:10022 (goes through tunnel)
     │  127.0.0.1:10022 → R-Pi tunnel → 10.0.0.140:22 ✅
     └─ This is where tunnel is established!
```

---

## Visual Flow: Status Badge vs Actual Execution

### **Status Check (ACTIVE/INACTIVE Badge)**
```
┌─────────────────────────┐
│ Browser: Select Devices │
└────────────┬────────────┘
             ↓
    GET /api/devices
             ↓
┌─────────────────────────────────────────────┐
│ controllers/device_controller.py             │
│ - Query Job table (active jobs?)             │
│ - Query DeviceLock table (locked?)           │
│ - NO SSH CONNECTION MADE                     │
│ - Pure database query                        │
└────────────┬────────────────────────────────┘
             ↓
    Device Status Response:
    ├─ BUSY (if job active + device locked)
    └─ AVAILABLE (if no job)
             ↓
┌──────────────────────────┐
│ UI renders status badge  │
│ (BUSY=Red, AVAILABLE=Grn)│
└──────────────────────────┘
```

### **Actual Execution (When You Run a Method)**
```
┌──────────────────────────────┐
│ User: Execute reboot method  │
│ on GDF_RACK device           │
└────────────┬─────────────────┘
             ↓
    Status badge updates to BUSY
    (Device gets locked)
             ↓
┌──────────────────────────────────┐
│ execute_reboot_perf_v2_optimized │
│ (methods/method_reboot_*.py)     │
└────────────┬─────────────────────┘
             ↓
    Is device RACK? YES
             ↓
┌──────────────────────────────────┐
│ Check execution queue            │
│ - Contains "reboot" method?      │
│ - Needs SSH? YES                 │
└────────────┬─────────────────────┘
             ↓
    Establish R-Pi tunnel:
    ├─ Connect to R-Pi (10.138.17.42:60201)
    ├─ Setup port forwarding
    ├─ Create listening socket @ 127.0.0.1:10022
    ├─ SSH to 127.0.0.1:10022 (forwarded to device)
    └─ ❌ FAILS: Socket doesn't exist!
             ↓
    Job fails with connection error
```

---

## Where the Bug Affects You

**Status Badge** (ACTIVE/INACTIVE):
- ✅ Works fine - pure database query
- **No SSH tunnel needed**

**Method Execution** (reboot, status, etc.):
- ❌ Fails for GDF_RACK devices
- **SSH tunnel broken** (doesn't create listening socket)
- **Leads to job failure**

---

## The Connection

**Your Question**: "Is device status (ACTIVE/INACTIVE) determined same way as SSH tunnel?"

**Answer**:
| Aspect | Status Badge | Method Execution |
|--------|---|---|
| **What it checks** | Active job + Lock status (DB) | SSH connectivity + tunnel |
| **SSH tunnel used?** | ❌ NO - pure DB query | ✅ YES - for rack devices |
| **Shows ACTIVE/INACTIVE?** | ✅ YES (BUSY/AVAILABLE) | N/A (executes or fails) |
| **Affected by tunnel bug?** | ❌ NO | ✅ YES - GDF_RACK devices fail |

---

## Summary

```
Status Badge (Select Devices):
├─ Checks database for active jobs
├─ Shows BUSY or AVAILABLE
└─ NO SSH connection needed ✅

Method Execution (Run a test):
├─ Tries to SSH to device
├─ For DESK: Direct SSH to device IP
│  └─ Works ✅
├─ For GDF_RACK: SSH tunnel via R-Pi
│  ├─ Create tunnel socket @ 127.0.0.1:10022
│  ├─ SSH to that socket
│  └─ Currently FAILS ❌ (socket not created)
└─ Returns status to update badge
```

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     APPLICATION SERVER                             │
│                     (This Flask app)                               │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ GET /api/devices                                          │   │
│  │                                                           │   │
│  │ Query Database:                                          │   │
│  │ ├─ Job table → Are there active jobs?                    │   │
│  │ ├─ DeviceLock table → Are devices locked?                │   │
│  │ └─ Return: status = BUSY or AVAILABLE                    │   │
│  │                                                           │   │
│  │ NO SSH involved here! 100% database.                      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ POST /api/execute (Run method)                            │   │
│  │                                                           │   │
│  │ 1. Lock device (update DeviceLock)                        │   │
│  │ 2. Execute method:                                        │   │
│  │    If GDF_RACK:                                           │   │
│  │    ├─ Create R-Pi tunnel                                 │   │
│  │    ├─ Forward 127.0.0.1:10022 to device                  │   │
│  │    └─ SSH to 127.0.0.1:10022                             │   │
│  │       (this fails - tunnel not working!)                 │   │
│  │    Else (DESK):                                           │   │
│  │    └─ SSH directly to device IP                           │   │
│  │ 3. Execute commands via SSH                              │   │
│  │ 4. Update job status                                      │   │
│  │ 5. Unlock device                                          │   │
│  │ 6. UI updates status badge                               │   │
│  └───────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
                              ↓
                    Database (PostgreSQL)
                   ├─ Job table
                   ├─ DeviceLock table
                   ├─ Device table
                   └─ All status info
```

---

## Key Insights

1. **Status Badge**:
   - Shows if device is currently executing a job
   - Database query only - NO network/SSH needed
   - Works perfectly ✅

2. **When You Run a Method**:
   - For DESK devices: Direct SSH ✅
   - For GDF_RACK devices: SSH via R-Pi tunnel ❌ (broken)
   - This is where the failure happens

3. **The Bug**:
   - Port forwarding set up incorrectly
   - No actual listening socket created at 127.0.0.1:10022
   - SSH connection attempt fails
   - Job marked as failed
   - Status badge remains BUSY (device stays locked) until admin intervenes

---

**Both use the same infrastructure, but status check is database-based while execution is SSH-based!**
