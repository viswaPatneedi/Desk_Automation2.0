# System Commands Approval Workflow

## Overview
System commands now follow a two-tier approval workflow, similar to log patterns:

1. **User submits** → Command goes to **Pending Approvals**
2. **Admin reviews and approves** → Command moves to **Approved Commands**
3. **Optional: Admin promotes** → Command is added to `config_log_patterns.py` as a permanent builtin

## Workflow Stages

### 1. Submission
- **Regular users** submit commands → Goes to **Pending Approvals**
- **Admin users** submit commands → Automatically approved and added to **Approved Commands**

**Endpoint:** `POST /api/system-commands/submit`
```json
{
  "command_name": "my_check",
  "command_text": "df -h",
  "description": "Check disk space"
}
```

### 2. Pending Approvals (Admin Only)
- Admins can view all pending submissions
- Admins can approve or reject each submission
- Rejected submissions are archived with reason

**Get Pending:** `GET /api/system-commands/pending`

**Approve:** `POST /api/system-commands/approve/{submission_id}`

**Reject:** `POST /api/system-commands/reject/{submission_id}`
```json
{
  "rejection_reason": "Command conflicts with existing tool"
}
```

### 3. Approved Commands
- Commands that have been approved by admins
- Stored in `system_commands_submissions.json` under `approved` section
- Available for use immediately after approval

### 4. Promotion to Config (Optional)
- After a command proves useful, admins can promote it to permanent builtin status
- This adds it to `config_log_patterns.py` as a `system_command_*` variable
- Makes it part of the system's standard toolkit
- Useful for widely-used commands that should be in the codebase

**Promote:** `POST /api/system-commands/promote/{command_name}`

## Data Storage

### system_commands_submissions.json
```json
{
  "approved": {
    "my_check": {
      "id": "uuid-here",
      "command_name": "my_check",
      "command": "df -h",
      "description": "Check disk space",
      "submitted_by": "user@domain",
      "submitted_at": "2026-01-21T...",
      "approved_at": "2026-01-21T...",
      "is_admin_submission": false
    }
  },
  "pending": {
    "uuid-here": {
      "id": "uuid-here",
      "command_name": "pending_check",
      "command": "top -b -n 1",
      "description": "Check system load",
      "submitted_by": "user@domain",
      "submitted_at": "2026-01-21T...",
      "is_admin_submission": false
    }
  },
  "rejected": [
    {
      "submission_id": "uuid-here",
      "command_name": "bad_check",
      "command": "rm -rf /",
      "submitted_by": "user@domain",
      "submitted_at": "2026-01-21T...",
      "rejected_at": "2026-01-21T...",
      "rejection_reason": "Dangerous command"
    }
  ]
}
```

## UI Sections

### For Regular Users
- **Built-in Commands (System)** - Only system_command_* from config
- Can submit new commands
- See their own submissions in Pending (if not approved yet)

### For Admins
- **Built-in Commands (System)** - Only system_command_* from config
- **Approved System Commands** - Approved submissions, ready to use
- **Pending Approvals** - New submissions awaiting review
  - Review button shows command details
  - Approve/Reject buttons to process
  - Once approved, moves to Approved Commands section
- **Promote to Config** - Option to make approved commands permanent builtins

## API Endpoints

### Public (All Authenticated Users)
- `GET /api/system-commands` - Get builtin, approved, and pending (pending only shown to admins)
- `POST /api/system-commands/submit` - Submit a new command

### Admin Only
- `GET /api/system-commands/pending` - View all pending submissions
- `POST /api/system-commands/approve/{submission_id}` - Approve a submission
- `POST /api/system-commands/reject/{submission_id}` - Reject a submission
- `POST /api/system-commands/promote/{command_name}` - Promote approved command to config

### Legacy (Deprecated)
- `POST /api/system-commands/add` - For backward compatibility, auto-approves for admins
- `POST /api/system-commands/{name}/update` - Update approved commands
- `POST /api/system-commands/{name}/delete` - Delete approved commands

## Access Control

| Action | Regular User | Admin |
|--------|---|---|
| Submit command | ✅ (goes to pending) | ✅ (auto-approved) |
| View approved commands | ✅ | ✅ |
| View pending submissions | ❌ | ✅ |
| Approve/Reject | ❌ | ✅ |
| Promote to config | ❌ | ✅ |

## Benefits

1. **Quality Control** - All user-defined commands reviewed before approval
2. **Consistency** - Same workflow as log patterns
3. **Auditability** - Full history of submissions, approvals, and rejections
4. **Scalability** - Commands can be promoted to permanent builtins over time
5. **Safety** - Prevents dangerous commands from being added without review
6. **Traceability** - Know who submitted what and when
