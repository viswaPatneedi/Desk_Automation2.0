# Log Pattern Management System

## Overview

The Log Pattern Management system allows users to add, view, and manage log validation patterns used to check device status and health. The system includes a **role-based approval workflow** where:

- **Regular Users**: Can submit new log patterns and view existing approved patterns
- **Admins**: Can approve/reject submissions, modify approved patterns, and manage the entire system

## Features

### 1. Submit New Log Patterns
Users can submit new log patterns with the following information:
- **Pattern Name**: Unique identifier (alphanumeric and underscores only)
- **Log Search Pattern**: Valid regex pattern to match in logs
- **File Location**: Path to the log file (must exist on the system)
- **Description**: Optional description of what the pattern validates

**Validation**:
- Pattern names are validated for proper format
- Regex patterns are validated in real-time
- File paths are checked for existence and readability

**Workflow**:
- Admins: Patterns are automatically approved
- Regular Users: Patterns go to pending queue for admin approval

### 2. View Approved Patterns
All users can view:
- List of all approved log patterns
- Pattern details (regex, file path, description)
- Who submitted the pattern and when

### 3. Admin Approval Workflow
Admins have access to:
- **Pending Submissions Queue**: View all submissions awaiting approval
- **Approve**: Accept a submission and add it to approved patterns
- **Reject**: Decline a submission with a reason provided
- **Modify**: Edit existing approved patterns
- **Delete**: Remove approved patterns

## File Structure

### New Files Created

1. **controllers/log_pattern_controller.py**
   - Core business logic for pattern management
   - Handles validation, submission, approval workflow
   - Manages persistence to JSON file

2. **log_pattern_submissions.json**
   - Stores all patterns (approved, pending, rejected)
   - JSON structure:
     ```json
     {
       "approved": { "pattern_name": { ...pattern data... } },
       "pending": { "submission_id": { ...submission data... } },
       "rejected": [ ...rejected submissions... ]
     }
     ```

3. **templates/log_patterns.html**
   - User interface for the log pattern management system
   - Responsive design with tabs for different sections
   - Real-time validation feedback

### Modified Files

1. **app.py**
   - Added 10 new API endpoints for pattern management
   - Routes handle CRUD operations and approval workflow

2. **config_log_patterns.py**
   - Added helper functions to load and work with approved patterns
   - Functions for backward compatibility with legacy patterns

## API Endpoints

### Public Endpoints (Login Required)

#### Get Pattern Summary
```
GET /api/log-patterns/summary
Response: { approved_count, pending_count, rejected_count, approved_patterns }
```

#### Get Approved Patterns
```
GET /api/log-patterns/approved
Response: { "pattern_name": { log_pattern, file_path, description, ... } }
```

#### Submit New Pattern
```
POST /api/log-patterns/submit
Body: {
    "pattern_name": "string",
    "log_pattern": "regex",
    "file_path": "string",
    "description": "string"
}
Response: { success, message, submission_id }
```

#### Validate File
```
POST /api/log-patterns/validate-file
Body: { "file_path": "string" }
Response: { success, message, file_path }
```

#### Validate Regex
```
POST /api/log-patterns/validate-regex
Body: { "pattern": "regex" }
Response: { success, message }
```

### Admin-Only Endpoints

#### Get Pending Submissions
```
GET /api/log-patterns/pending
Response: { "submission_id": { pattern_name, submitted_by, ... } }
```

#### Approve Submission
```
POST /api/log-patterns/{submission_id}/approve
Response: { success, message }
```

#### Reject Submission
```
POST /api/log-patterns/{submission_id}/reject
Body: { "rejection_reason": "string" }
Response: { success, message }
```

#### Modify Approved Pattern
```
POST /api/log-patterns/{pattern_name}/modify
Body: {
    "log_pattern": "regex",
    "file_path": "string",
    "description": "string"
}
Response: { success, message }
```

#### Delete Pattern
```
POST /api/log-patterns/{pattern_name}/delete
Response: { success, message }
```

## Usage Examples

### For Regular Users

1. **Navigate to Log Patterns**
   - Go to `/log-patterns` page

2. **Submit a New Pattern**
   - Fill in Pattern Name (e.g., "My_Custom_Check")
   - Enter regex pattern to match
   - Provide file path (e.g., `/opt/logs/my-log.txt`)
   - Click "Submit for Approval"
   - You'll see "pending approval" status

3. **View Approved Patterns**
   - See all available patterns on the same page
   - Can view pattern details

### For Admins

1. **Approve Pending Submissions**
   - Go to "Pending Approvals" section
   - Review submission details
   - Click "Approve" to accept or "Reject" to decline with reason

2. **Modify Approved Pattern**
   - Click edit button on any approved pattern
   - Update regex, file path, or description
   - Click "Save Changes"

3. **Delete a Pattern**
   - Open pattern editor
   - Click "Delete Pattern"
   - Confirm deletion

## Integration with Code

### Using Approved Patterns

In your Python code, use the helper functions from `config_log_patterns.py`:

```python
from config_log_patterns import (
    get_log_pattern,
    get_log_file_path,
    build_log_check_command,
    get_all_approved_pattern_names,
    get_all_patterns_with_commands,
    merge_approved_with_legacy_checks
)

# Get a specific pattern
pattern = get_log_pattern('HOME')
file_path = get_log_file_path('HOME')

# Build a grep command
command = build_log_check_command('HOME')

# Get all patterns with commands
all_patterns = get_all_patterns_with_commands()

# Merge with legacy patterns for backward compatibility
all_checks = merge_approved_with_legacy_checks()
```

### Example: Reboot Performance Check

```python
from config_log_patterns import build_log_check_command

# In your device method
pattern_name = 'HOME'  # Previously approved pattern
check_command = build_log_check_command(pattern_name)

if check_command:
    # Execute the command
    result = execute_ssh_command(device_ip, check_command)
```

## Data Structure Details

### Approved Pattern Object
```json
{
    "id": "HOME_1234567890",
    "pattern_name": "HOME",
    "log_pattern": "QMS Bookmark.*HOME_TILES.*load.*complete",
    "file_path": "/opt/logs/sky-messages.log",
    "description": "Detects when HOME screen loads",
    "submitted_by": "john.doe",
    "submitted_at": "2026-01-21T10:30:00+00:00",
    "is_admin_submission": true,
    "modified_at": "2026-01-21T11:00:00+00:00"
}
```

### Pending Submission Object
```json
{
    "id": "Custom_Pattern_1234567890",
    "pattern_name": "Custom_Pattern",
    "log_pattern": "My custom regex.*pattern",
    "file_path": "/opt/logs/custom.log",
    "description": "My custom validation",
    "submitted_by": "jane.smith",
    "submitted_at": "2026-01-21T09:15:00+00:00",
    "is_admin_submission": false
}
```

## Security Considerations

1. **File Path Validation**
   - System validates file existence before accepting patterns
   - Prevents arbitrary path injection

2. **Regex Validation**
   - Patterns are validated before storage
   - Invalid regex is rejected

3. **Role-Based Access**
   - Non-admins cannot approve, reject, or modify patterns
   - API endpoints enforce admin checks

4. **Audit Trail**
   - All submissions include timestamp and submitter info
   - Rejected submissions retain reason for reference

## Troubleshooting

### Pattern Not Appearing in Approved List
- Check if it's still pending (admin approval needed)
- Verify the pattern is in the "approved" section of JSON
- Try refreshing the page

### "File does not exist" Error
- Ensure the file path is correct and absolute
- Check if the path exists on the server
- Verify file permissions (must be readable)

### Invalid Regex Error
- Test your regex pattern online
- Common issues:
  - Missing escape characters
  - Unbalanced parentheses
  - Invalid character classes

### Pattern Not Triggering Checks
- Verify the file path is correct
- Check if the log actually contains matching text
- Test the regex pattern in command line:
  ```bash
  grep -E "your_pattern" /path/to/log
  ```

## Migration from Legacy Patterns

The system maintains backward compatibility:

```python
# Old way (still works)
from config_log_patterns import log_line_HOME, log_check_command_HOME

# New way (using approved patterns)
from config_log_patterns import build_log_check_command
command = build_log_check_command('HOME')

# Get all available checks (legacy + new)
from config_log_patterns import merge_approved_with_legacy_checks
all_checks = merge_approved_with_legacy_checks()
```

## Best Practices

1. **Pattern Naming**
   - Use descriptive names: `HOME_SCREEN_CHECK`, not `check_1`
   - Use uppercase with underscores
   - Keep names short but clear

2. **Regex Patterns**
   - Test patterns thoroughly before submitting
   - Use character classes for variations
   - Document complex patterns in description

3. **File Paths**
   - Use absolute paths
   - Consider common log locations
   - Document if path may differ by device

4. **Descriptions**
   - Be specific about what the pattern detects
   - Include expected log content
   - Note any device-specific behavior

## Future Enhancements

Potential improvements:
- Pattern version control and history
- Test pattern against sample logs
- Pattern performance metrics
- Export/import pattern collections
- Pattern categorization/tagging
- Scheduled pattern reviews

---

For questions or issues, contact the admin team.
