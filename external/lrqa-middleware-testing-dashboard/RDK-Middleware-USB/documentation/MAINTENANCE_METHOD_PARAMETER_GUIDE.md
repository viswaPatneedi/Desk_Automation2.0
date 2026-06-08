# Maintenance > DeepSleep > Wakeup - Parameter Configuration Guide

**Status**: ✅ **LIVE & READY TO USE**

---

## 🎯 What Changed

The maintenance method now has **full parameter handling** with:
- ✅ **Remote Type dropdown** (COMCAST, XUMO, SKY, etc.)
- ✅ **DeepSleep wait duration** (configurable: 5-600 minutes)
- ✅ **Optional Steps 8-12 checkbox** (skip DeepSleep for faster execution)
- ✅ **Edit dialog** with all parameters displayed

---

## 📋 How to Use

### **Step 1: Drag Method to Queue**
1. Open Dashboard: http://10.0.0.123:11078
2. Find **"Maintenance > DeepSleep > Wakeup"** in left sidebar
3. Drag it to **"Execution Order"** (middle column)

### **Step 2: Edit Parameters** 
1. **Single-click** on the method card in Execution Order
2. **Edit dialog appears** with:
   - **Remote Type dropdown** (required)
   - **DeepSleep Duration** (minutes)
   - **Execute Steps 8-12 checkbox** (optional phases)

### **Step 3: Configure Options**

#### **Option A: Full Workflow (Steps 1-12)**
```
✓ Remote Type: COMCAST
✓ Sleep Duration: 60 minutes
✓ Execute Steps 8-12: CHECKED (enabled)
Duration: ~95 minutes total
```

#### **Option B: Maintenance Only (Steps 1-7 - FASTER)**
```
✓ Remote Type: COMCAST
✓ Sleep Duration: 60 minutes
✓ Execute Steps 8-12: UNCHECKED (disabled)
Duration: ~60 minutes total
Saves: ~20 minutes
```

### **Step 4: Save & Execute**
1. Click **"Save Changes"** button
2. View updated parameters in queue:
   - Phases: `Full (1-12)` or `Maintenance only (1-7)`
   - Remote type shown
   - Duration shown
3. Click **"Execute NOW"** to start

---

## 🔧 Parameter Details

### **Remote Type Dropdown**
**Purpose**: Specifies which IR remote to use for power key commands

**Available Options**:
- `COMCAST` - Comcast/Xfinity remote
- `XUMO` - XUMO TV remote
- `SKY` - Sky remote
- `ALTICE` - Altice remote
- `DISCOVERY` - Discovery remote
- `OTHER` - Custom/other remote

**Used For**:
- Putting device in STANDBY (step 1)
- Verifying STANDBY (step 7)
- Waking device from DeepSleep (step 11, if enabled)

---

### **DeepSleep Wait Duration**
**Purpose**: How long to wait before checking if device entered DeepSleep

**Range**: 5 - 600 minutes
**Default**: 60 minutes
**Typical**: 15 minutes (time for device to naturally enter DeepSleep)

---

### **Execute Steps 8-12 Checkbox**
**Purpose**: Control whether to run DeepSleep & Wakeup testing phases

| Setting | Steps | Duration | Use Case |
|---------|-------|----------|----------|
| **CHECKED** (✓) | 1-12 | ~95 min | Full stress test with DeepSleep |
| **UNCHECKED** (✗) | 1-7 | ~60 min | Quick maintenance only |

**Steps 8-12 Include**:
8️⃣ Initiate deep sleep  
9️⃣ Check device is in DeepSleep  
🔟 Verify DeepSleep state again  
1️⃣1️⃣ Send IR wake-up command  
1️⃣2️⃣ Verify wake-up & measure time  

---

## ✅ Edit Dialog Fields

When you edit the method, you'll see:

```
┌─────────────────────────────────────────┐
│ Edit: maintenance_deepsleep_wakeup      │
├─────────────────────────────────────────┤
│                                         │
│ Remote Type (for Power Keys): *         │
│ [-- Select Remote Type --       ▼]     │
│  • COMCAST                              │
│  • XUMO                                 │
│  • SKY                                  │
│  • ALTICE                               │
│  • DISCOVERY                            │
│  • OTHER                                │
│                                         │
│ DeepSleep Wait Duration (minutes): *    │
│ [60                                  ]  │
│ Time to wait before checking...         │
│                                         │
│ ☑ Execute Steps 8-12 (DeepSleep &      │
│   Wakeup)                               │
│   If unchecked: Only runs maintenance   │
│   (steps 1-7), saves ~20 minutes        │
│                                         │
│              [Cancel] [Save Changes]    │
└─────────────────────────────────────────┘
```

---

## 📊 Queue Display

After configuring, the queue shows:

```
1. maintenance_deepsleep_wakeup
   ⚑ Remote: COMCAST
   ⏱ Duration: 60 min
   ⚙ Phases: Full (1-12)  ← or "Maintenance only (1-7)"
```

---

## 🚀 Workflow Examples

### **Example 1: Full Maintenance + DeepSleep Test**
```
Scenario: Testing device maintenance cycle + deep sleep stability
Configuration:
  • Remote Type: XUMO
  • Sleep Duration: 60 min
  • Steps 8-12: CHECKED ✓

Expected Results:
  • Step 1-7: Maintenance cycle (~45 min)
  • Step 8-12: DeepSleep test (~30 min)
  • Total: ~95 minutes
  • Output: wakeup_time_seconds metric
```

### **Example 2: Quick Maintenance Only**
```
Scenario: Running regular maintenance, no deep sleep testing needed
Configuration:
  • Remote Type: COMCAST
  • Sleep Duration: 60 min
  • Steps 8-12: UNCHECKED ✗

Expected Results:
  • Step 1-7: Maintenance cycle only (~60 min)
  • Steps 8-12: SKIPPED
  • Total: ~60 minutes
  • Time saved: ~20 minutes
```

### **Example 3: Custom Sleep Duration**
```
Scenario: Device takes longer to enter deep sleep
Configuration:
  • Remote Type: SKY
  • Sleep Duration: 90 min (instead of default 60)
  • Steps 8-12: CHECKED ✓

Note: Adjust based on observed device behavior
```

---

## 💾 Parameter Storage

Parameters are automatically saved in the queue and include:

```json
{
  "method": "maintenance_deepsleep_wakeup",
  "remote_type": "COMCAST",
  "sleep_duration_minutes": 60,
  "execute_deepsleep_wakeup": true
}
```

When you:
- ✅ **Save the queue** → Parameters persist
- ✅ **Re-open dashboard** → Parameters are restored
- ✅ **Execute method** → Parameters are passed to backend

---

## 🔄 Backend Integration

The parameters are automatically passed to the method implementation:

```python
execute_maintenance_deepsleep_wakeup_process(
    device_ip=device_ip,
    port=port,
    username=username,
    password=password,
    remote_type="COMCAST",              # ← User selected
    sleep_duration_minutes=60,          # ← User configured
    execute_deepsleep_wakeup=True,      # ← User toggled
    # ... other params
)
```

---

## ⚠️ Important Notes

1. **Remote Type is required** - Select one before executing
2. **Sleep duration range**: 5-600 minutes (recommended: 15-60)
3. **Steps 8-12 default: CHECKED** (full workflow by default for backward compatibility)
4. **Parameters are validated** - Invalid values will trigger error messages
5. **Device must have IR blaster** - Required for power commands

---

## 🆘 Troubleshooting

### **"This method has no editable parameters"**
- **Fixed!** ✅ This was the old error message
- Now you should see the full edit dialog with Remote Type, Duration, and checkbox

### **Remote Type dropdown not showing options**
- Hard refresh browser: `Ctrl+Shift+R`
- Clear cache if persistent

### **Parameters not saving**
- Check browser console for errors
- Verify Remote Type is selected (not blank)
- Try saving again

---

## 📞 Quick Reference

| Action | What Happens |
|--------|--------------|
| Drag method to queue | Method added with default parameters |
| Single-click method | Edit dialog opens |
| Select Remote Type | Dropdown has 6 common types |
| Change Sleep Duration | Numeric field, 5-600 min range |
| Toggle checkbox | Enables/disables steps 8-12 |
| Click Save Changes | Dialog closes, parameters saved |
| Click Execute NOW | Method runs with saved parameters |

---

## 🎓 Best Practices

1. **Always select Remote Type** - It's required for IR commands
2. **Use correct remote for device** - Ask user for their specific remote type
3. **Start with default 60 min sleep** - Adjust if device takes longer
4. **Use maintenance-only for quick tests** - Saves 20+ minutes
5. **Enable full workflow for stress tests** - Get complete metrics
6. **Save queue after configuration** - Preserves parameters for later use

---

**Status**: ✅ **FULLY OPERATIONAL**  
**Parameters**: ✅ **3 + Display info**  
**Edit Dialog**: ✅ **ACTIVE**  
**Backend Integration**: ✅ **CONNECTED**

You're all set! 🚀

