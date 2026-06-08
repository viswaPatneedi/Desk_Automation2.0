# Admin Permissions & Cancel Execution Feature

## Overview
Role-based access control has been implemented to allow users to cancel their own job executions, while admin users can cancel any job.

## Admin User
- **Admin User:** `vpatne290` (ViswaChaithanya Patneedi)
- **Permissions:** Can cancel any job (pending or running) regardless of who triggered it

## Regular Users
- Can only cancel their own jobs
- Cannot cancel jobs triggered by other users

## Features Implemented

### 1. Admin Role System
- Added `is_admin` field to User model
- Defaults to `false` for new users
- Only `vpatne290` is configured as admin

### 2. Cancel Execution Permissions
Users can cancel jobs in two locations:
1. **Execution Queue** (Pending Jobs section)
   - Shows only pending jobs
   - Cancel and Restart buttons visible only if:
     - User owns the job, OR
     - User is admin

2. **Current Running Jobs & Recent Executions**
   - Shows running, pending, and recently completed jobs
   - Cancel button visible for running/pending jobs only if:
     - User owns the job, OR
     - User is admin

### 3. API Security
- Endpoint: `POST /api/jobs/<job_id>/cancel`
- Permission check: Returns 403 Forbidden if:
  - User doesn't own the job AND
  - User is not admin
- Unlocks device automatically after successful cancellation

## UI Behavior

### For Regular Users
```
User: landel334
Jobs visible:
- Their own pending jobs → Cancel & Restart buttons shown
- Their own running jobs → Cancel button shown
- Other users' jobs → Only View button shown
```

### For Admin (vpatne290)
```
User: vpatne290 (Admin)
Jobs visible:
- All pending jobs → Cancel & Restart buttons shown
- All running jobs → Cancel button shown
- Can manage any user's jobs
```

## Technical Implementation

### Backend Changes

1. **models/user.py**
   - Added `is_admin` parameter to `__init__` (defaults to `False`)
   - Updated `to_dict()` to include `is_admin`
   - Updated `from_dict()` to load `is_admin` with default `False`

2. **users.json**
   - Added `"is_admin": true` to vpatne290 user record
   - Regular users default to no `is_admin` field (treated as `false`)

3. **app.py - /api/jobs/<job_id>/cancel**
   ```python
   # Get job and check ownership
   job = Job.get_job(job_id)
   
   # Permission check
   if job.user_id != current_user.user_id and not current_user.is_admin:
       return jsonify({'error': 'Unauthorized'}), 403
   
   # Cancel and unlock device
   Job.cancel_job(job_id)
   DeviceLock.unlock_device(job.device_ip)
   ```

### Frontend Changes

1. **templates/index.html**
   - Added `currentUser` JavaScript object with `user_id` and `is_admin`
   ```javascript
   const currentUser = {
       user_id: '{{ current_user.user_id }}',
       is_admin: {{ 'true' if current_user.is_admin else 'false' }}
   };
   ```

2. **Pending Jobs Section**
   - Conditional button rendering:
   ```javascript
   const canCancel = currentUser.is_admin || job.user_id === currentUser.user_id;
   ${canCancel ? '<button>Cancel</button>' : ''}
   ```

3. **Running Jobs Section**
   - Cancel button shown only for running/pending jobs with permission
   ```javascript
   const canCancel = (currentUser.is_admin || job.user_id === currentUser.user_id) && 
                    (job.status === 'running' || job.status === 'pending');
   ```

## Job Statuses
- `pending` - Job waiting in queue (can be cancelled)
- `running` - Job currently executing (can be cancelled)
- `completed` - Job finished successfully (cannot be cancelled)
- `failed` - Job failed execution (cannot be cancelled)
- `cancelled` - Job was cancelled by user/admin

## Security Features
- Server-side permission validation on API endpoint
- 403 Forbidden response for unauthorized cancel attempts
- Client-side UI hides buttons for unauthorized users (UX improvement)
- Admin flag stored in users.json, not modifiable from UI

## Adding More Admins
To add another admin user:

1. Open `users.json`
2. Add `"is_admin": true` to the user's record:
   ```json
   {
     "user_ntid": {
       "user_id": "user_ntid",
       "ntid": "user_ntid",
       "email": "user@comcast.com",
       "is_admin": true,
       ...
     }
   }
   ```
3. Restart the service:
   ```bash
   sudo systemctl restart device-testing.service
   ```

## Testing

### Test as Regular User (landel334)
1. Login as `landel334`
2. Trigger a job
3. Verify cancel button appears on your job
4. Verify cancel button does NOT appear on vpatne290's jobs
5. Try to cancel your job → Success
6. Try to manually call API for another user's job → 403 Forbidden

### Test as Admin (vpatne290)
1. Login as `vpatne290`
2. Verify cancel buttons appear on ALL jobs
3. Cancel a job triggered by another user → Success
4. Verify device is unlocked after cancellation

## Error Messages

### Unauthorized Cancel Attempt
```
Status: 403 Forbidden
Response: {"success": false, "error": "Unauthorized: You can only cancel your own jobs"}
```

### Job Not Found
```
Status: 404 Not Found
Response: {"success": false, "error": "Job not found"}
```

### Success
```
Status: 200 OK
Response: {"success": true, "message": "Job cancelled successfully"}
```

## Related Files
- `models/user.py` - User model with admin role
- `users.json` - User data storage
- `app.py` - Cancel endpoint with permission checks
- `templates/index.html` - Frontend with conditional cancel buttons
- `models/job.py` - Job cancellation logic

## Notes
- Cancel operation unlocks the associated device automatically
- Cancelled jobs remain in history for auditing
- Search filter includes cancelled jobs
- Auto-cleanup still applies to old pending jobs (>2 days)

---
**Feature Completed:** November 24, 2025
**Developer:** VISWA
