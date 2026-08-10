# Application Setup Summary - August 5, 2026

## ✅ SETUP COMPLETED SUCCESSFULLY

### 1. VIRTUAL ENVIRONMENT SETUP
- **Status**: ✅ Configured and Active
- **Location**: `venv/`
- **Python Version**: 3.8
- **Dependencies**: All installed from `requirements.txt`
  - Flask 3.0.0
  - Paramiko 3.4.0
  - Pillow 10.1.0
  - OpenCV 4.8.1.78
  - And 10+ more packages

### 2. APPLICATION STATUS
- **Port**: 11079 (Changed from default 11078)
- **Host**: 0.0.0.0 (Network accessible)
- **Status**: ✅ Running in background
- **Process ID**: 3278108
- **Environment**: Development mode (Debug enabled)

### 3. STORAGE CONFIGURATION CHANGES

#### Previous Configuration
- Storage Fallback: `Enhancement_output` folder
- USB Support: Enabled (tried to detect USB drives)

#### New Configuration
- **Storage Fallback**: `ExecutionResults` folder
- **USB Support**: Disabled (no USB available on server)
- **Storage Root**: `/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/ExecutionResults`

#### Files Modified
1. **usb_storage_manager.py**
   - Line 127: Changed fallback storage path from `Enhancement_output` to `ExecutionResults`
   - Enhanced `create_execution_folder()` method to support:
     - `team_name` parameter
     - `date_str` parameter
     - New folder structure: `ExecutionResults/<TEAM>/<DATE>/sessions/`

2. **app.py**
   - Line 3782: Changed default port from 11078 to 11079
   - Environment variable override: `FLASK_PORT=11079`

### 4. FOLDER STRUCTURE

#### Created Directory Tree
```
ExecutionResults/
├── screenshots/           (Captured screenshots from tests)
├── iteration_logs/        (Logs for each iteration)
├── execution_logs/        (Test execution summary logs)
├── device_logs/          (Device-specific logs)
├── app_logs/             (Application runtime logs)
├── sessions/             (Session data - will contain team/date structure)
└── storage_config.json   (Storage configuration metadata)
```

#### New Storage Path Structure (for test results)
```
ExecutionResults/
├── <TEAM_NAME>/
│   ├── 2026-08-05/
│   │   └── sessions/
│   │       └── METHOD_DEVICE_IP_ITERS_ITR_TIMESTAMP/
│   │           ├── screenshots/
│   │           ├── execution_logs/
│   │           └── device_logs/
│   ├── 2026-08-06/
│   │   └── sessions/
│   └── ...
├── DEFAULT/              (Default team if not specified)
│   └── 2026-08-05/
│       └── sessions/
└── ...
```

### 5. USAGE EXAMPLES

#### Creating Execution Folders with Team and Date
```python
from usb_storage_manager import get_storage_manager

storage_manager = get_storage_manager()

# Create folder with team name and date
session_folder, screenshots_dir, exec_logs_dir, device_logs_dir = storage_manager.create_execution_folder(
    method='reboot_performance',
    device_name='STB-Device-01',
    device_ip='192.168.1.100',
    iterations=10,
    team_name='QA_TEAM_A',           # Team name
    date_str='2026-08-05'            # Date in YYYY-MM-DD format
)

# Returns paths like:
# session_folder: ExecutionResults/QA_TEAM_A/2026-08-05/sessions/reboot_performance_STB-DEVICE-01_192-168-1-100_10_ITR_20260805_021543_UTC/
# screenshots_dir: ... /screenshots/
# exec_logs_dir: ... /execution_logs/
# device_logs_dir: ... /device_logs/
```

#### Using Default Team and Today's Date
```python
# Automatically uses 'DEFAULT' team and today's date
session_folder, screenshots_dir, exec_logs_dir, device_logs_dir = storage_manager.create_execution_folder(
    method='method_name',
    device_name='device_name',
    device_ip='192.168.1.1',
    iterations=5
)
```

### 6. ACCESSING THE APPLICATION

#### Web Interface
- **URL**: `http://localhost:11079`
- **Access**: Requires login credentials
- **Features**: Dashboard, test execution, result viewing, device management

#### Monitoring the Application

**Check if running:**
```bash
ps aux | grep "python3 app.py" | grep -v grep
```

**View startup logs:**
```bash
tail -f app_startup.log
```

**View real-time logs:**
```bash
tail -f nohup.out
```

**Stop the application:**
```bash
kill 3278108
```

**Restart the application:**
```bash
source venv/bin/activate
nohup python app.py > app_startup.log 2>&1 &
echo $! > app.pid
```

### 7. DISK SPACE & SYSTEM INFO
- **Available Disk Space**: ~191 GB
- **Current Usage**: ~31 GB (14%)
- **System**: Linux Desktop (Ubuntu-based)
- **Python Version**: 3.8
- **Timezone**: UTC

### 8. STORAGE CONFIGURATION FILE
The storage configuration is saved in: `ExecutionResults/storage_config.json`

```json
{
  "timestamp": "2026-08-04T20:34:56.279387+00:00",
  "system": "linux_desktop",
  "usb_available": false,
  "storage_root": "ExecutionResults",
  "usb_path": null,
  "directories": {
    "screenshots": "ExecutionResults/screenshots",
    "iteration_logs": "ExecutionResults/iteration_logs",
    "execution_logs": "ExecutionResults/execution_logs",
    "device_logs": "ExecutionResults/device_logs",
    "app_logs": "ExecutionResults/app_logs"
  }
}
```

### 9. FUTURE ENHANCEMENTS

To integrate team_name and date_str throughout the application:

1. **Update Job Model** (`models/job.py`):
   - Add `team_name` field to Job model
   - Add `execution_date` field

2. **Update Test Execution Service** (`services/test_execution_service.py`):
   - Pass `team_name` and `date` when calling `create_execution_folder()`
   - Use these values in result storage paths

3. **Update Controllers**:
   - Pass team information from API requests
   - Ensure team info is captured when jobs are created

4. **Database Schema**:
   - Add `team_name` column to jobs table
   - Update relevant queries to filter by team

### 10. IMPORTANT NOTES

- ⚠️ **USB Detection Disabled**: Since no USB is available on the server, storage falls back to the local `ExecutionResults` folder
- ⚠️ **Port 11079**: Make sure this port is not blocked by firewall
- ⚠️ **Permissions**: The `ExecutionResults` folder is created with read/write permissions for the current user
- ✅ **Automatic Cleanup**: Old job data (>60 days) is automatically cleaned up
- ✅ **Recovery Mode**: Application has recovery mode enabled for job resumption on restart
- ✅ **Email Notifications**: Enabled (Gmail SMTP configured)

### 11. TROUBLESHOOTING

**Port Already in Use:**
```bash
# Find process using port 11079
ss -tlnp | grep 11079
# Kill the process
kill -9 <PID>
```

**Storage Permission Issues:**
```bash
# Fix permissions on ExecutionResults
chmod -R 755 ExecutionResults/
```

**Clear Cache/Reset Application:**
```bash
# Stop the app
kill 3278108
# Clear state if needed
rm Json/app_state.json
# Restart
source venv/bin/activate
nohup python app.py > app_startup.log 2>&1 &
```

---

**Setup Date**: August 5, 2026
**Application Ready**: ✅ YES
**All Tests Passed**: ✅ YES
