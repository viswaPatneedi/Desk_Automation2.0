# SOFT_HARD_BOOT Execution Summary - Job d3fe5f99-49c1-40ac-baae-07ff2a95bc1c

## Complete Execution Report

**Device:** SHARP-DEVICE-DESK (10.0.0.232)  
**Method:** soft_hard_boot  
**Boot Type:** HARD (systemctl reboot)  
**Job ID:** d3fe5f99-49c1-40ac-baae-07ff2a95bc1c  
**Status:** ✅ PASSED  
**Execution Time:** 2026-03-08 05:53:44 - 05:57:23 UTC

---

## Execution Results

### Boot Performance
| Metric | Value |
|--------|-------|
| **Boot Command Sent** | 2026-03-08 05:54:52.037 UTC |
| **HOME Screen Detected** | 2026-03-08 05:56:11.348 UTC |
| **Total Boot Duration** | **79.31 seconds** |
| **Device Reconnection Time** | 41.0 seconds |

### Data Captured

#### ✅ Device Reboot
- **Status:** Successfully rebooted
- **Command:** `systemctl reboot`
- **Connection Loss:** Device disconnected immediately after reboot command
- **Reconnection:** Device came back online after 41 seconds

#### ✅ HOME Screen Detection
- **Pattern Matched:** QMS HOME_TILES complete
- **Log Entry:** `2026-03-08T05:56:11.348Z com.sky.as.apps_com.bskyb.epgui[1425]: QMSContentManager.log: QMS Bookmark (HOME_TILES - N2E26400E) load complete`
- **Detection Method:** Log pattern matching from /opt/logs/sky-messages.log

#### ✅ RDK Milestones.log Captured
**237 characters, 10 milestone entries:**

```
RDK_STARTED:5795
GST_CLEANUP_COMPLETE:9415
WPE_FRAMEWORK_START:9481
IP_ACQUISTION_COMPLETED:eth0:10415
CONNECT_TO_NTP_SERVER:14423
RIPPLE_START:15835
CONNECT_TO_XCONF_CDL:23130
EPG_STARTED:31592
SET_XSCT_TOKEN:34630
EPG_FIRST_FRAME:49905
```

#### ✅ Screenshots Captured
1. **BEFORE Boot:** 
   - File: 10.0.0.232_SHARP-DEVICE-DESK_Iteration-1_Before-HARDBoot_20260308_055345.png
   - Size: 2,664,351 bytes (2601.91 KB)
   - Dimensions: 1920x1080
   - Screen Detected: NetflixHome (25.2% confidence)

2. **AFTER Boot:**
   - File: 10.0.0.232_SHARP-DEVICE-DESK_Iteration-1_After-HARDBoot-SUCCESS_20260308_055345.png
   - Size: 1,917,794 bytes (1872.85 KB)
   - Dimensions: 1920x1080
   - Screen Detected: NetflixHome (42.7% confidence)

#### ✅ Build Information
- **Image Name:** SHUHTS11MEI_DEV_support_8.3_xumo_20260219201910_WST
- **OSS Version:** 4.7.10
- **Middleware Version:** 8.3.4.6
- **Vendor Version:** 3
- **Yocto Version:** kirkstone
- **SDK Version:** 2.2
- **Branch:** support_8.3_xumo
- **Build Time:** 2026-02-19 20:19:10

### Database Storage Status

**Location:** `test_results_history.json`

**Stored Fields:**
- ✅ `method`: soft_hard_boot
- ✅ `boot_type`: HARD
- ✅ `performance_seconds`: 79.310904
- ✅ `rdk_milestones_log`: [237 characters with all 10 milestones]
- ✅ `screenshots`: [2 screenshot paths]
- ✅ `status`: PASSED
- ✅ `job_id`: d3fe5f99-49c1-40ac-baae-07ff2a95bc1c
- ✅ `timestamp`: 2026-03-08T05:57:22.584058+00:00
- ✅ `device_ip`: 10.0.0.232
- ✅ `iteration`: 1
- ✅ `build_info`: [Full build details captured]

---

## Data Display in Results Page

The following columns should be visible in the Results Table:

| Column | Value | Status |
|--------|-------|--------|
| **Device** | SHARP-DEVICE-DESK (10.0.0.232) | ✅ Visible |
| **Method** | soft_hard_boot | ✅ Visible |
| **Status** | PASSED | ✅ Visible |
| **Boot Type** | ⚑ HARD (Red Badge) | ✅ Visible |
| **Performance** | 79.31 seconds | ✅ Visible |
| **RDK Milestones Log** | [View Log] Button | ✅ Visible |
| **Screenshots** | 2 captured | ✅ Visible |

### Interactive Features
- **Boot Type Badge:** Color-coded (Red for HARD, Blue for SOFT)
- **RDK Milestones Log Viewer:** Click "View Log" to open formatted milestone data in modal
- **Screenshots:** Hover to preview, click to view full resolution

---

## Verification Commands

To verify data in database:
```bash
# Check all soft_hard_boot results
python3 << 'EOF'
import json
with open('test_results_history.json') as f:
    data = json.load(f)
    soft_hard = [r for r in data if r.get('method') == 'soft_hard_boot']
    print(f"Total soft_hard_boot results: {len(soft_hard)}")
    for r in soft_hard:
        print(f"  Device: {r.get('device_ip')} | Boot: {r.get('boot_type')} | Performance: {r.get('performance_seconds')}s | RDK Log: {len(r.get('rdk_milestones_log', ''))} chars")
EOF
```

---

## Summary

✅ **All data successfully captured and stored**
✅ **Device rebooted correctly (79.31 second boot time)**
✅ **HOME screen detected via log pattern matching**
✅ **RDK milestones.log collected with 10 entries**
✅ **Screenshots captured before and after reboot**
✅ **Results saved to database with all required fields**
✅ **Ready to display in Results Table with Boot Type and RDK Milestones columns**

---

## Next Steps

1. **Refresh Results Page:** Open http://10.0.0.123:11078/results
2. **Search for Job:** Filter for device "SHARP-DEVICE-DESK" or "10.0.0.232"
3. **View Boot Type Column:** Should show "⚑ HARD" in red badge
4. **View RDK Milestones:** Click "View Log" button to see formatted milestone data
5. **Analyze Performance:** Compare 79.31 second boot time with target performance goals

---

**Generated:** 2026-03-08 06:00:00 UTC  
**Verified:** All data confirmed in test_results_history.json
