# Log Pattern Management - API Usage Guide

## Overview

Complete reference for all API endpoints with examples.

## Authentication

All endpoints require login:
```
- Must be authenticated user
- Use appropriate session/cookies
- Admin-only endpoints checked server-side
```

## Base URL

```
http://localhost:8080  (development)
https://your-domain.com (production)
```

---

## Endpoints

### 1. Display Log Patterns Page

**Endpoint**: `GET /log-patterns`

**Auth**: Required (redirects to login if not authenticated)

**Response**: HTML page with UI

**Example**:
```bash
curl -b cookies.txt http://localhost:8080/log-patterns
```

---

### 2. Get Pattern Summary

**Endpoint**: `GET /api/log-patterns/summary`

**Auth**: Required

**Response**:
```json
{
  "success": true,
  "data": {
    "approved_count": 3,
    "pending_count": 1,
    "rejected_count": 2,
    "approved_patterns": ["HOME", "Network_Error", "Process_Crash"],
    "pending_patterns": [
      {
        "id": "Custom_Pattern_1234567890",
        "name": "Custom_Pattern",
        "submitted_by": "john.doe",
        "submitted_at": "2026-01-21T10:00:00+00:00"
      }
    ]
  }
}
```

**Example**:
```bash
curl -b cookies.txt http://localhost:8080/api/log-patterns/summary | jq
```

---

### 3. Get All Approved Patterns

**Endpoint**: `GET /api/log-patterns/approved`

**Auth**: Required

**Response**:
```json
{
  "success": true,
  "data": {
    "HOME": {
      "id": "HOME_1234567890",
      "pattern_name": "HOME",
      "log_pattern": "QMS Bookmark.*HOME_TILES.*load.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui",
      "file_path": "/opt/logs/sky-messages.log",
      "description": "Detects when HOME screen loads successfully",
      "submitted_by": "system",
      "submitted_at": "2026-01-21T00:00:00+00:00",
      "is_admin_submission": true
    },
    "Network_Error": { ... },
    "Process_Crash": { ... }
  }
}
```

**Example**:
```bash
curl -b cookies.txt http://localhost:8080/api/log-patterns/approved | jq '.data.HOME'
```

**Usage in Code**:
```python
import requests
import json

response = requests.get(
    'http://localhost:8080/api/log-patterns/approved',
    cookies={'session': 'your-session-cookie'}
)
patterns = response.json()['data']

for pattern_name, pattern_data in patterns.items():
    print(f"{pattern_name}: {pattern_data['log_pattern']}")
```

---

### 4. Get Pending Submissions (Admin Only)

**Endpoint**: `GET /api/log-patterns/pending`

**Auth**: Required, Admin only

**Status Codes**:
- `200`: Success
- `403`: Not admin
- `500`: Server error

**Response**:
```json
{
  "success": true,
  "data": {
    "Custom_Pattern_1234567890": {
      "id": "Custom_Pattern_1234567890",
      "pattern_name": "Custom_Pattern",
      "log_pattern": "My custom.*pattern",
      "file_path": "/opt/logs/custom.log",
      "description": "My custom validation",
      "submitted_by": "jane.smith",
      "submitted_at": "2026-01-21T09:15:00+00:00",
      "is_admin_submission": false
    }
  }
}
```

**Admin Error Response**:
```json
{
  "success": false,
  "message": "Admin access required"
}
```

**Example**:
```bash
curl -b cookies.txt http://localhost:8080/api/log-patterns/pending | jq
```

---

### 5. Submit New Log Pattern

**Endpoint**: `POST /api/log-patterns/submit`

**Auth**: Required

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "pattern_name": "MY_PATTERN",
  "log_pattern": "my regex.*pattern",
  "file_path": "/opt/logs/my-log.txt",
  "description": "Optional description"
}
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Pattern 'MY_PATTERN' submitted for admin approval",
  "submission_id": "MY_PATTERN_1234567890"
}
```

**Response (Error)**:
```json
{
  "success": false,
  "message": "Pattern name can only contain alphanumeric characters and underscores"
}
```

**Validation Errors**:
```json
{
  "success": false,
  "message": "File does not exist at path: /opt/logs/nonexistent.log"
}
```

**Examples**:

Python:
```python
import requests

url = 'http://localhost:8080/api/log-patterns/submit'
headers = {'Content-Type': 'application/json'}
data = {
    'pattern_name': 'HOME_LOAD',
    'log_pattern': 'QMS Bookmark.*HOME_TILES.*complete',
    'file_path': '/opt/logs/sky-messages.log',
    'description': 'Detect home screen load'
}

response = requests.post(
    url,
    json=data,
    cookies={'session': 'your-session'}
)
print(response.json())
```

cURL:
```bash
curl -X POST http://localhost:8080/api/log-patterns/submit \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{
    "pattern_name": "HOME_LOAD",
    "log_pattern": "QMS Bookmark.*HOME_TILES.*complete",
    "file_path": "/opt/logs/sky-messages.log",
    "description": "Detect home screen load"
  }' | jq
```

---

### 6. Validate File Path

**Endpoint**: `POST /api/log-patterns/validate-file`

**Auth**: Required

**Request Body**:
```json
{
  "file_path": "/opt/logs/sky-messages.log"
}
```

**Response (Valid)**:
```json
{
  "success": true,
  "message": "File validated successfully",
  "file_path": "/opt/logs/sky-messages.log"
}
```

**Response (Invalid)**:
```json
{
  "success": false,
  "message": "File does not exist at path: /opt/logs/nonexistent.log",
  "file_path": "/opt/logs/nonexistent.log"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/log-patterns/validate-file \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"file_path": "/opt/logs/sky-messages.log"}' | jq
```

---

### 7. Validate Regex Pattern

**Endpoint**: `POST /api/log-patterns/validate-regex`

**Auth**: Required

**Request Body**:
```json
{
  "pattern": "QMS Bookmark.*HOME_TILES.*complete"
}
```

**Response (Valid)**:
```json
{
  "success": true,
  "message": "Pattern is valid regex"
}
```

**Response (Invalid)**:
```json
{
  "success": false,
  "message": "Invalid regex pattern: unbalanced parenthesis at position 10"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/log-patterns/validate-regex \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "QMS.*complete"}' | jq
```

---

### 8. Approve Submission (Admin Only)

**Endpoint**: `POST /api/log-patterns/{submission_id}/approve`

**Auth**: Required, Admin only

**URL Parameters**:
- `submission_id`: ID of submission to approve

**Request Body**: Empty or `{}`

**Response (Success)**:
```json
{
  "success": true,
  "message": "Submission 'HOME_LOAD' approved successfully"
}
```

**Response (Not Admin)**:
```json
{
  "success": false,
  "message": "Admin access required"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/log-patterns/MY_PATTERN_1234567890/approve \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{}' | jq
```

---

### 9. Reject Submission (Admin Only)

**Endpoint**: `POST /api/log-patterns/{submission_id}/reject`

**Auth**: Required, Admin only

**Request Body**:
```json
{
  "rejection_reason": "Pattern already exists with similar functionality"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Submission rejected: Pattern already exists with similar functionality"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/log-patterns/MY_PATTERN_1234567890/reject \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"rejection_reason": "Pattern too similar to HOME"}' | jq
```

---

### 10. Modify Approved Pattern (Admin Only)

**Endpoint**: `POST /api/log-patterns/{pattern_name}/modify`

**Auth**: Required, Admin only

**URL Parameters**:
- `pattern_name`: Name of approved pattern

**Request Body**:
```json
{
  "log_pattern": "updated regex.*pattern",
  "file_path": "/opt/logs/updated.log",
  "description": "Updated description"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Pattern 'HOME' modified successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/log-patterns/HOME/modify \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{
    "log_pattern": "QMS Bookmark.*HOME.*updated",
    "file_path": "/opt/logs/sky-messages.log",
    "description": "Updated HOME pattern"
  }' | jq
```

---

### 11. Delete Approved Pattern (Admin Only)

**Endpoint**: `POST /api/log-patterns/{pattern_name}/delete`

**Auth**: Required, Admin only

**URL Parameters**:
- `pattern_name`: Name of pattern to delete

**Request Body**: Empty or `{}`

**Response**:
```json
{
  "success": true,
  "message": "Pattern 'HOME' deleted successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/log-patterns/HOME/delete \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{}' | jq
```

---

## Common Workflows

### Workflow 1: User Submits Pattern

```bash
# 1. Validate the file exists
curl -X POST http://localhost:8080/api/log-patterns/validate-file \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"file_path": "/opt/logs/my.log"}'

# 2. Validate the regex
curl -X POST http://localhost:8080/api/log-patterns/validate-regex \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "my.*pattern"}'

# 3. Submit the pattern
curl -X POST http://localhost:8080/api/log-patterns/submit \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{
    "pattern_name": "MY_CHECK",
    "log_pattern": "my.*pattern",
    "file_path": "/opt/logs/my.log",
    "description": "Check for my pattern"
  }'
```

### Workflow 2: Admin Approves Submission

```bash
# 1. Get pending submissions
curl -b cookies.txt http://localhost:8080/api/log-patterns/pending | jq

# 2. Approve one
curl -X POST http://localhost:8080/api/log-patterns/MY_PATTERN_1234567890/approve \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{}'

# 3. Verify it's in approved list
curl -b cookies.txt http://localhost:8080/api/log-patterns/approved | jq
```

### Workflow 3: Get Pattern for Use

```bash
# 1. Get all approved patterns
curl -b cookies.txt http://localhost:8080/api/log-patterns/approved \
  | jq '.data.HOME'

# 2. Extract pattern and file
PATTERN=$(curl -b cookies.txt http://localhost:8080/api/log-patterns/approved \
  | jq -r '.data.HOME.log_pattern')
FILE=$(curl -b cookies.txt http://localhost:8080/api/log-patterns/approved \
  | jq -r '.data.HOME.file_path')

# 3. Use in grep command
grep -E "$PATTERN" "$FILE"
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "message": "Human-readable error message"  // or "error" field
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 403 | Forbidden (admin required) |
| 404 | Not found |
| 500 | Server error |

### Common Errors

**Pattern Name Format**:
```json
{"success": false, "message": "Pattern name can only contain alphanumeric characters and underscores"}
```

**Invalid Regex**:
```json
{"success": false, "message": "Invalid regex pattern: unbalanced parenthesis"}
```

**File Not Found**:
```json
{"success": false, "message": "File does not exist at path: /bad/path"}
```

**Not Admin**:
```json
{"success": false, "message": "Admin access required"}
```

---

## Rate Limiting

Currently: No rate limiting implemented

Future: May add rate limiting on submission endpoints

---

## Testing with Python

```python
import requests
import json

# Setup
BASE_URL = 'http://localhost:8080'
session = requests.Session()

# Login (assuming you have a login endpoint)
login_response = session.post(f'{BASE_URL}/login', data={
    'username': 'your_user',
    'password': 'your_pass'
})

# Get approved patterns
response = session.get(f'{BASE_URL}/api/log-patterns/approved')
patterns = response.json()['data']
print(json.dumps(patterns, indent=2))

# Submit new pattern
new_pattern = {
    'pattern_name': 'TEST_PATTERN',
    'log_pattern': 'test.*error',
    'file_path': '/opt/logs/test.log',
    'description': 'Test pattern'
}
response = session.post(f'{BASE_URL}/api/log-patterns/submit', json=new_pattern)
print(response.json())

# Admin: Get pending
response = session.get(f'{BASE_URL}/api/log-patterns/pending')
pending = response.json()['data']
print(json.dumps(pending, indent=2))

# Admin: Approve
if pending:
    first_id = list(pending.keys())[0]
    response = session.post(f'{BASE_URL}/api/log-patterns/{first_id}/approve', json={})
    print(response.json())
```

---

## Testing with JavaScript/Fetch

```javascript
const baseUrl = 'http://localhost:8080';

// Get approved patterns
async function getApprovedPatterns() {
  const response = await fetch(`${baseUrl}/api/log-patterns/approved`, {
    credentials: 'include'  // Include cookies
  });
  return await response.json();
}

// Submit new pattern
async function submitPattern(name, pattern, filepath, description) {
  const response = await fetch(`${baseUrl}/api/log-patterns/submit`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pattern_name: name,
      log_pattern: pattern,
      file_path: filepath,
      description: description
    })
  });
  return await response.json();
}

// Usage
const patterns = await getApprovedPatterns();
console.log(patterns);

const result = await submitPattern(
  'TEST',
  'test.*pattern',
  '/opt/logs/test.log',
  'Test'
);
console.log(result);
```

---

## Additional Resources

- **Full Documentation**: See `LOG_PATTERN_MANAGEMENT.md`
- **Quick Start**: See `LOG_PATTERN_QUICK_START.md`
- **Implementation Details**: See `LOG_PATTERN_IMPLEMENTATION.md`
