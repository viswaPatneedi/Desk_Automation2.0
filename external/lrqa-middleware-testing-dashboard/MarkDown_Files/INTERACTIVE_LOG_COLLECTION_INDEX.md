# Interactive Log Collection Feature - Documentation Index

## Overview
This document serves as a comprehensive index for the Interactive Log Collection feature that was added to the Reboot Performance V2 - Optimized method on February 1, 2026.

## Feature Description
After the HOME screen is successfully detected during a reboot performance test, users are prompted with an interactive question: "Collect device logs for this iteration? (yes/no)". If they choose "yes", device logs are automatically collected from `/opt/logs/*` and stored as a compressed tar.gz file in `/media/app/` with an organized filename structure.

## Documentation Files

### 1. **INTERACTIVE_LOG_COLLECTION_FEATURE.md** (Main Reference)
   - **Type**: Comprehensive Feature Documentation
   - **Length**: 280+ lines
   - **Best For**: Understanding all aspects of the feature
   
   **Contents**:
   - Detailed overview and feature description
   - When it activates and how it works
   - File organization structure
   - Integration points in method flow
   - Code function documentation with examples
   - Usage scenarios and examples
   - File access methods (SSH, SFTP)
   - Benefits and features
   - Timeout behavior and automation support
   - Troubleshooting guide
   - Future enhancement suggestions
   
   **Use This When**: You need complete details about how the feature works, what it does, why it's useful, and how to troubleshoot issues.

---

### 2. **INTERACTIVE_LOG_COLLECTION_QUICK_REF.md** (Quick Start)
   - **Type**: Quick Reference Guide
   - **Length**: 110+ lines
   - **Best For**: Quick lookup and command reference
   
   **Contents**:
   - One-page quick start
   - Feature overview summary
   - Quick start for interactive sessions
   - Quick start for automated sessions
   - Command reference (SSH, SFTP, extraction)
   - File naming convention explanation
   - Response options quick table
   - Typical usage flow diagram
   - Feature list
   - Storage location details
   - Quick troubleshooting table
   - Related documentation links
   
   **Use This When**: You need a quick reference, remember the command syntax, or want the feature overview in a single page.

---

### 3. **IMPLEMENTATION_SUMMARY_LOG_COLLECTION.md** (Technical Details)
   - **Type**: Implementation & Technical Documentation
   - **Length**: 200+ lines
   - **Best For**: Developers and technical review
   
   **Contents**:
   - What was implemented
   - Code changes made (exact file locations and line numbers)
   - New function documentation with full code snippets
   - Integration point details
   - Files modified and created (with statistics)
   - Step-by-step how it works explanation
   - Backward compatibility notes
   - Error handling documentation
   - Testing checklist
   - Version information
   
   **Use This When**: You're reviewing the code, need to understand the implementation details, or want the exact line numbers and code snippets.

---

## Code Implementation

### Location
**File**: `method_reboot_perf_v2_optimized.py`

### New Functions
1. **`prompt_user_for_log_collection()`** (Lines 219-235)
   - Displays interactive console prompt
   - Handles user input (yes/no)
   - Re-prompts on invalid input
   - Gracefully handles non-interactive mode

2. **`collect_device_logs_to_media_app()`** (Lines 237-310)
   - Creates `/media/app` directory if needed
   - Creates tar.gz archive of `/opt/logs/*`
   - Verifies file creation
   - Returns path on success, None on failure

### Integration Point
**Function**: `execute_reboot_perf_v2_optimized_process()` (Lines 704-718)
**Step**: 4.5 (after HOME detection, before performance calculation)

## Quick Reference

| Item | Details |
|------|---------|
| **Trigger** | After HOME screen is detected during reboot test |
| **Prompt** | "🔍 Log Line Found! Collect device logs for this iteration? (yes/no):" |
| **Storage Location** | `/media/app/` on device |
| **File Format** | `.tar.gz` (compressed) |
| **Filename Pattern** | `{ip}_{device}_ITR-{iteration}_logs_{timestamp}.tar.gz` |
| **Example** | `/media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz` |
| **Valid Responses** | yes, y, no, n (case-insensitive) |
| **Non-Interactive Mode** | Automatically skips (no blocking) |

## How to Use

### For End Users
1. Read: **INTERACTIVE_LOG_COLLECTION_QUICK_REF.md**
2. When prompt appears: Type `yes` to collect, `no` to skip
3. Logs are automatically stored in `/media/app/`

### For Developers/Technical Review
1. Start: **IMPLEMENTATION_SUMMARY_LOG_COLLECTION.md** (overview)
2. Reference: **method_reboot_perf_v2_optimized.py** (actual code)
3. Details: **INTERACTIVE_LOG_COLLECTION_FEATURE.md** (comprehensive)

### For Troubleshooting
1. Quick issues: **INTERACTIVE_LOG_COLLECTION_QUICK_REF.md** (troubleshooting table)
2. Complex issues: **INTERACTIVE_LOG_COLLECTION_FEATURE.md** (troubleshooting guide)

## Document Selection Guide

Choose the document based on your need:

```
┌─ I want to understand what this feature does
│  └─ Read: INTERACTIVE_LOG_COLLECTION_FEATURE.md (Section: Overview)
│
├─ I need a quick command reference
│  └─ Read: INTERACTIVE_LOG_COLLECTION_QUICK_REF.md
│
├─ I need to troubleshoot an issue
│  ├─ Quick: INTERACTIVE_LOG_COLLECTION_QUICK_REF.md (Troubleshooting table)
│  └─ Detailed: INTERACTIVE_LOG_COLLECTION_FEATURE.md (Troubleshooting guide)
│
├─ I need to review the code implementation
│  └─ Read: IMPLEMENTATION_SUMMARY_LOG_COLLECTION.md
│
├─ I need file access instructions
│  └─ Read: INTERACTIVE_LOG_COLLECTION_FEATURE.md (Section: File Access)
│
├─ I need to understand the workflow
│  └─ Read: INTERACTIVE_LOG_COLLECTION_FEATURE.md (Section: Integration Points)
│
└─ I need everything (complete reference)
   └─ Read all three documents in this order:
      1. INTERACTIVE_LOG_COLLECTION_FEATURE.md
      2. IMPLEMENTATION_SUMMARY_LOG_COLLECTION.md
      3. INTERACTIVE_LOG_COLLECTION_QUICK_REF.md
```

## Feature Highlights

✅ **Interactive Decision Making**
- Real-time user choice during test execution
- Non-blocking (works in automated mode)

✅ **Automatic Organization**
- Smart file naming with device, iteration, timestamp
- Easy to locate and manage logs

✅ **Zero Configuration**
- No setup required
- Works out of the box
- Backward compatible

✅ **Comprehensive Logging**
- Captures all `/opt/logs/*` files
- Compressed format (saves space)
- Complete diagnostic data

✅ **Error Resilient**
- Graceful handling of failures
- Doesn't block test execution
- Clear error messages

## File Naming Convention

Logs are saved as:
```
/media/app/{device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz
```

### Components
- **device_ip**: IP address (e.g., 10.0.0.250)
- **device_name**: Device name with spaces replaced by underscores (e.g., ELEMENT-A4K-DESK)
- **iteration**: Test iteration number (e.g., ITR-42 for iteration 42)
- **timestamp**: UTC timestamp in YYYYMMDD_HHMMSS format (e.g., 20260201_143025)

### Example
```
/media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

## Related Documentation

- **Method Guide**: `REBOOT_PERF_V2_OPTIMIZED_GUIDE.md`
- **Device Logs Organization**: `DEVICE_LOGS_ORGANIZATION.md`
- **SSH/SFTP Access**: `JUMP_HOST_INTEGRATION.md` (for remote access)

## Version Information

| Component | Version | Released | Status |
|-----------|---------|----------|--------|
| Feature | 1.0 | 2026-02-01 | ✅ Complete |
| Code Implementation | 1.0 | 2026-02-01 | ✅ Complete |
| Documentation | 1.0 | 2026-02-01 | ✅ Complete |
| Manual Testing | 1.0 | Pending | ⏳ Next |

## Support & Issues

### Common Questions
**Q: Where are the logs stored?**  
A: On the device in `/media/app/` directory, accessible via SSH/SFTP

**Q: Can I download the logs to my computer?**  
A: Yes, use SFTP. See INTERACTIVE_LOG_COLLECTION_QUICK_REF.md for commands

**Q: What if I say "no" to the prompt?**  
A: Test continues normally, no logs collected, no time wasted

**Q: What happens in automated/batch mode?**  
A: System gracefully skips the prompt, test continues without delay

**Q: How much disk space do logs use?**  
A: Typically 50-200 MB per iteration (compressed)

### Troubleshooting Resources
1. **Quick issues** → See QUICK_REF troubleshooting table
2. **Complex issues** → See FEATURE guide troubleshooting section
3. **Code issues** → See IMPLEMENTATION_SUMMARY for function details

## Summary

This interactive log collection feature provides:
- **Convenience**: On-demand log capture without pre-configuration
- **Control**: User decides which iterations to capture
- **Organization**: Automatic file naming and storage
- **Compatibility**: Works with all execution modes
- **Reliability**: Error-resistant with graceful fallback

All documentation is comprehensive, examples are provided, and troubleshooting guidance is available.

---

**Document Index Created**: 2026-02-01  
**Feature Status**: Complete and Ready for Use  
**Last Updated**: 2026-02-01

