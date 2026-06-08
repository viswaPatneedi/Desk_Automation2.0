# Project Overview & Mapping

## Summary

This project is a **Flask-based web application** for managing and testing RDK (Reference Design Kit) middleware devices. It uses an **MVC architecture** and is designed for production on a Raspberry Pi, supporting auto-recovery, session-based logging, and organized output storage.

---

## Key Features

- Device operations: reboot, deep sleep, IR/voice command tests, power state queries.
- Iteration tracking: session folders with screenshots, logs, device logs.
- Queue management: job queue per device, status tracking, auto-recovery.
- Real-time logging: live streaming, per-iteration logs, UTC timestamps.
- Results dashboard: aggregated results/statistics in web UI.
- User management: admin roles, authentication, password reset via email.
- Configuration: device, IR, timing, command settings in config files.
- Auto-recovery: checkpoint every 30s, crash recovery restores queue/sessions.
- USB output: outputs saved to `/media/pi/Lexar/Enhancement-output/` in session folders.

---

## Main Components Mapping

- `app.py`: Main Flask app, routing, initializes services/controllers.
- `models/`: Data layer (Device, Job, TestResult, User, etc.).
- `controllers/`: HTTP request handlers (device, test, queue, results).
- `services/`: Business logic (test execution, logging, queue, recovery).
- `method_*.py`: Individual method implementations.
- `templates/`: HTML UI.
- `static/`: CSS/JS frontend.
- `config_*.py`: Configuration files.
- `iteration_logs/`: Execution log files.
- `devices.json`: Device registry.
- `jobs.json`: Job queue/history.
- `test_results_history.json`: Aggregated test results (3-day retention).
- USB output: Organized session folders.

---

## Usage

- Add devices via web UI (`devices.json`).
- Build/execute test queues (methods, IR keys, voice commands).
- View/download real-time logs.
- Access results/job history via dashboard.
- Outputs organized for review/archival.

---

## Production Setup

- Runs as Gunicorn service (`rdk-testing.service` or `device-testing.service`) with 8 workers.
- Auto-recovery/checkpointing enabled.
- USB stick required for output organization; falls back to local storage.

---

## For Future Reference

- Use this file for quick onboarding and understanding of project structure.
- Update this mapping when adding new features, components, or changing architecture.
- Refer to this overview for troubleshooting, scaling, or migration tasks.
- Use component mapping to locate files for maintenance or enhancement.
- Keep this document in sync with `README.md` and other documentation files.

---

## Related Docs

- `README.md`
- `USB_FOLDER_STRUCTURE.md`
- `MVC_RECOVERY_COMPLETE.md`

