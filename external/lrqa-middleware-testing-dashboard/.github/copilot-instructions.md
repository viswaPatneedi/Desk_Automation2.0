# Copilot Instructions for AI Coding Agents

## Project Overview
This is a Flask-based web application for managing and controlling devices via SSH, with detailed logging and iteration tracking. The system is modular, with clear separation between configuration, device management, method execution, and logging.

## Architecture & Key Components
- **app.py**: Main Flask app, entry point for web UI and API routes.
- **controllers/**: Contains business logic for devices, jobs, queues, results, and tests. Each controller handles a specific domain (e.g., `device_controller.py` for device CRUD and SSH operations).
- **models/**: Data models for devices, jobs, users, results, and sequences. These interact with JSON files for persistence.
- **services/**: Service layer for log streaming, queue management, recovery, and test execution. Use these for background tasks and cross-component logic.
- **config_*.py**: Configuration files for commands, IR blaster, log patterns, timing, and screenshot settings. Always reference these for hardcoded values and device-specific logic.
- **iteration_logs/**: Stores per-execution log files with UTC timestamps. Log format includes header, step-by-step details, status icons, and footer.
- **devices.json**: Registry of all managed devices. Device credentials and metadata are stored here.
- **templates/**: Jinja2 HTML templates for the web UI.

## Developer Workflows
- **Install dependencies**: `pip install -r requirements.txt`
- **Run server**: `python app.py` (default Flask port 5000)
- **Test SSH connectivity**: Use the UI or call controller methods directly.
- **View logs**: Check `iteration_logs/` for detailed execution logs. Log streaming uses Server-Sent Events (SSE).
- **Add/remove devices**: Update via UI or edit `devices.json`.
- **Configuration changes**: Edit relevant `config_*.py` files. Changes are picked up on restart.

## Project-Specific Patterns
- **All device operations are performed over SSH.** Use Paramiko for SSH logic.
- **Iteration and logging**: Each method execution creates a new log file. Always include UTC timestamps and status icons (✓, ✗, ⚠) in logs.
- **Separation of concerns**: Controllers handle business logic, models handle data, services handle background tasks.
- **Configuration is always externalized**: Never hardcode device commands, IR codes, or timing in business logic—use config files.
- **Real-time log streaming**: Implemented via SSE in `log_service.py` and consumed in the UI.

## Integration Points
- **IR Blaster (iTach)**: Used for deep sleep wake-up. Configuration in `config_ir_blaster.py`.
- **Screenshots**: Managed via `screenshot_utils.py` and stored in `screenshots/`.
- **Job and queue management**: Handled by `queue_service.py` and related controllers.

## Examples
- To add a new device, update `devices.json` or use the UI form in `index.html`.
- To implement a new device method, add logic to the relevant controller and update `config_commands.py`.
- To change log patterns, edit `config_log_patterns.py`.

## Conventions
- **All timestamps are UTC.**
- **Log files are named as `<device_ip>_<method>_<timestamp>_UTC.log`.**
- **Default SSH port is 10022, username is root.**
- **Sensitive data (passwords) are stored in `devices.json`.**

## References
- See `README.md` for feature overview and usage.
- See `config_*.py` files for all device-specific logic and settings.
- See `controllers/` and `services/` for main business logic and background processing.

---
_If any section is unclear or missing, please provide feedback for further refinement._
