# System Commands Management - Quick Start Guide

## Overview

The System Commands Management feature is now available in the Log Pattern Management interface. This allows administrators to manage system commands (like disk space checks, memory usage, etc.) without editing code.

## Accessing System Commands

1. **Login to the Application**
   - Navigate to: `http://10.0.0.32:8080`
   - Login with admin credentials

2. **Go to Log Pattern Management**
   - Click on "Log Patterns" in the navigation menu
   - Or navigate to: `http://10.0.0.32:8080/log-patterns`

3. **Scroll to System Commands Section**
   - The section is located below "Pending Approvals"
   - Only visible when logged in as admin

## What You'll See

### Built-in Commands (System)
These are the default system commands provided by the system:
- **teetz** - List teetz directory contents
- **disk_space** - Show disk space usage
- **memory_usage** - Show memory usage
- **top** - Show top running processes
- **dsmgr_status** - Check dsmgr service status

**Note:** Built-in commands are read-only and displayed with a lock icon.

### User-Defined Commands
Custom commands you add. These have Edit and Delete buttons (pencil and trash icons).

## Adding a New System Command

### Steps:
1. Click the **"Add Command"** button (green button with + icon)
2. Fill in the required fields:
   - **Command Name:** Alphanumeric and underscores only (e.g., `my_disk_check`)
   - **Command:** The shell command to run (e.g., `df -h | grep -E "/$"`)
   - **Description:** (Optional) What this command does
3. Click **"Add Command"** to save

### Example:
```
Command Name: ssl_certificate_check
Command: openssl x509 -in /path/to/cert.pem -noout -dates
Description: Check SSL certificate expiration dates
```

## Editing a System Command

### Steps:
1. Find the command in the "User-Defined Commands" section
2. Click the **pencil icon** (Edit button)
3. Update the Command or Description
4. Click **"Save Changes"**

**Note:** You cannot edit the command name, only the command text and description.

## Deleting a System Command

### Steps:
1. Find the command in the "User-Defined Commands" section
2. Click the **trash icon** (Delete button)
3. Confirm the deletion in the popup
4. Command will be removed

## Understanding Command Information

Each command card displays:
- **Command Name** - The identifier for this command
- **Command Text** - The shell command that will be executed (in monospace font)
- **Description** - Human-readable explanation of what the command does
- **Date** - When the command was created or last updated

## Tips & Best Practices

### Command Naming
- Use descriptive names in snake_case: `check_disk_space` ✓
- Avoid special characters except underscore
- Keep names short but meaningful

### Command Text
- Test commands in terminal before adding
- Use absolute paths: `/opt/bin/command` ✓
- Avoid interactive commands or those requiring input
- Redirect output if needed: `command 2>&1 | head -20`

### Descriptions
- Be specific about what the command does
- Include any important notes
- Example: "Checks used disk space on root partition, shows % used"

## Common Commands to Add

### System Monitoring
```
# CPU temperature
Command: cat /sys/class/thermal/thermal_zone0/temp

# Network interfaces
Command: ip addr show

# Running services
Command: systemctl list-units --type=service --state=running

# System uptime
Command: uptime

# Current users
Command: who
```

### Log Analysis
```
# Recent errors
Command: tail -f /var/log/syslog | grep -i error

# Count log entries
Command: wc -l /opt/logs/sky-messages.log

# Search for pattern
Command: grep -c "WARN" /opt/logs/sky-messages.log
```

### File/Directory Operations
```
# Directory size
Command: du -sh /opt/

# File count
Command: find /opt/logs -type f | wc -l

# Disk usage by filesystem
Command: df -B1 | awk '{print $1, $2, $3}'
```

## Troubleshooting

### Command Not Appearing After Adding
- Check browser console for errors (F12)
- Refresh the page
- Verify you're logged in as admin

### Get Error Message When Adding Command
- **"Command name is required"** - Enter a command name
- **"Command text is required"** - Enter a shell command
- **"alphanumeric characters and underscores only"** - Use a-z, 0-9, or _ in name
- **"Error: ..."** - See the specific error message

### Command Doesn't Save
- Check Flask server logs for errors
- Verify file permissions on `system_commands.json`
- Try again or refresh the page

### Can't See System Commands Section
- You must be logged in as admin
- Check your user role/permissions
- Try logging out and back in

## API Usage (For Developers)

### Get All Commands
```bash
curl -X GET http://10.0.0.32:8080/api/system-commands \
  -H "Content-Type: application/json" \
  -c cookies.txt
```

### Add Command (Admin Only)
```bash
curl -X POST http://10.0.0.32:8080/api/system-commands/add \
  -H "Content-Type: application/json" \
  -d '{
    "command_name": "my_command",
    "command_text": "shell command here",
    "description": "optional description"
  }' \
  -b cookies.txt
```

### Update Command (Admin Only)
```bash
curl -X POST http://10.0.0.32:8080/api/system-commands/my_command/update \
  -H "Content-Type: application/json" \
  -d '{
    "command_text": "updated command",
    "description": "updated description"
  }' \
  -b cookies.txt
```

### Delete Command (Admin Only)
```bash
curl -X POST http://10.0.0.32:8080/api/system-commands/my_command/delete \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Focus Command Name | Tab within modal |
| Submit Form | Enter key (when applicable) |
| Cancel Modal | Escape key |
| Close Alert | Click X or wait 5 seconds |

## FAQs

**Q: Can I edit built-in commands?**
A: No, built-in commands are read-only. They come from system configuration.

**Q: Can I delete built-in commands?**
A: No, built-in commands cannot be deleted.

**Q: What if I accidentally delete a command?**
A: Unfortunately there's no undo. If it was a custom command, you'll need to add it again.

**Q: Can I import commands from a file?**
A: Currently, no. Commands must be added one at a time through the UI.

**Q: Can I export my commands?**
A: Currently, no. But you can view them on this page or in the `system_commands.json` file.

**Q: Do these commands get executed automatically?**
A: No. This interface only manages command definitions. For execution, you'll need to use other tools.

**Q: Can non-admin users see the commands?**
A: No. The System Commands section is hidden for non-admin users.

## Where to Get Help

- **For Questions:** Contact your administrator
- **For Bugs:** Check the Flask server logs at the console
- **For Feature Requests:** Add to the project documentation

## Related Features

- **Log Patterns:** Manage log search patterns (same page)
- **Device Management:** Manage devices for testing
- **Test Automation:** Run automated tests on devices

---

**Version:** 1.0  
**Last Updated:** January 15, 2025  
**Status:** Ready for Use ✓
