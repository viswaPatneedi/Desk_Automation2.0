# Log Pattern Management - Quick Start Guide

## For Regular Users

### Step 1: Access the Log Patterns Page
```
Navigate to: http://your-app/log-patterns
```

### Step 2: Submit a New Log Pattern
1. Fill in the form on the left side:
   - **Pattern Name**: e.g., `HOME_LOADED`
   - **Log Pattern**: Regex to match, e.g., `QMS Bookmark.*HOME_TILES.*load.*complete`
   - **File Location**: Full path to log file, e.g., `/opt/logs/sky-messages.log`
   - **Description**: What this pattern checks for

2. The system will validate:
   - ✅ Pattern name format
   - ✅ Regex syntax
   - ✅ File existence and readability

3. Click **"Submit for Approval"**
   - Admin approval required for non-admins
   - Admins' patterns are auto-approved

### Step 3: View Approved Patterns
- Right side shows all currently approved patterns
- See pattern details, who added it, when it was added
- View the exact regex being used

---

## For Admins

### View Pending Submissions
```
Log Patterns page → Scroll down → "Pending Approvals" section
```

Shows all user submissions waiting for approval with:
- Pattern name and details
- Who submitted it and when
- Two action buttons: **Approve** or **Reject**

### Approve a Submission
1. Review the pending submission details
2. Click **"Approve"** button
3. Pattern moves to Approved section immediately
4. Available for use system-wide

### Reject a Submission
1. Click **"Reject"** button
2. Enter reason for rejection (required)
3. Click **"Reject"** in modal
4. Pattern goes to rejected archive
5. User can see reason and resubmit if needed

### Edit an Approved Pattern
1. Find pattern in "Approved Patterns" section
2. Click the **edit button** (pencil icon)
3. Update:
   - Log Pattern (regex)
   - File Location
   - Description
4. Click **"Save Changes"**

### Delete an Approved Pattern
1. Open pattern editor (click edit button)
2. Click **"Delete Pattern"** button
3. Confirm deletion
4. Pattern removed from system

---

## Common Tasks

### I submitted a pattern, where is it?
- **Status**: "Pending Approvals" (admin hasn't reviewed yet)
- **Action**: Wait for admin approval or check with admin
- **Time**: Usually approved within 1-2 business days

### How do I know if my pattern is valid?
- The form shows **green checkmark** if valid
- **Red X** means there's an issue
- Fix errors before submitting

### Can I use a pattern from a different device?
- Patterns are universal by default
- If device-specific, mention in description
- Admins can adjust file paths if needed

### Pattern isn't working after approval
- Verify file path still exists
- Check if log format changed
- Test regex: `grep -E "your_pattern" /path/to/log`
- Contact admin if pattern needs update

---

## Pattern Examples

### Home Screen Check
```
Name: HOME_SCREEN
Pattern: QMS Bookmark.*HOME_TILES.*load.*complete
File: /opt/logs/sky-messages.log
Description: Detects successful HOME screen load
```

### Network Error Check
```
Name: NETWORK_ERROR
Pattern: Argument missing: Let's try that again|to refresh your connection
File: /opt/logs/sky-messages.log
Description: Detects network connectivity errors
```

### Process Crash Check
```
Name: PROCESS_CRASH
Pattern: Process crashed.*
File: /opt/logs/core_log.txt
Description: Detects when any process crashes
```

---

## Regex Cheat Sheet

| Pattern | Meaning | Example |
|---------|---------|---------|
| `.` | Any character | `error.` matches "error!" or "error1" |
| `.*` | Any characters (0+) | `home.*load` matches "home tiles load" |
| `.+` | Any characters (1+) | `home.+load` requires at least 1 char |
| `^` | Start of line | `^ERROR` matches "ERROR" at start |
| `$` | End of line | `error$` matches "error" at end |
| `[abc]` | Character class | `[0-9]` matches any digit |
| `(a\|b)` | OR operator | `home\|screen` matches "home" or "screen" |
| `\w` | Word character | `\w+` matches word characters |
| `\d` | Digit | `\d+` matches one or more digits |

---

## FAQ

**Q: How often are pending submissions reviewed?**
A: Daily, typically within 24 hours.

**Q: Can I edit my submitted pattern before approval?**
A: No, resubmit a new one if needed.

**Q: What if a pattern matches too many results?**
A: Make it more specific by adding more details to the regex.

**Q: Can patterns be used in automated tests?**
A: Yes, they're automatically available in reboot performance checks.

**Q: How do I test my pattern before submitting?**
A: Use command line:
```bash
grep -E "your_pattern" /path/to/log
```

---

## Support

- **Need Help?** Contact your admin
- **Found a Bug?** Report with pattern name and error message
- **Have Suggestions?** Submit feedback to admin team

**Status Dashboard**: View approval stats at top of Log Patterns page
