"""Periodic DB-to-JSON synchronization service.

Runs on a fixed interval (default 30 minutes) and mirrors database state
into JSON backup files. Sync is skipped while active executions are running
so background reconciliation does not interfere with in-flight jobs.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone

from config.config_paths import (
    DEVICES_FILE,
    USERS_FILE,
    SAVED_SEQUENCES_FILE,
    LOG_PATTERNS_FILE,
    SYSTEM_COMMANDS_FILE,
)
from models.database import (
    Session,
    User as DBUser,
    Device as DBDevice,
    SavedSequence as DBSavedSequence,
    LogPattern as DBLogPattern,
    SystemCommand as DBSystemCommand,
    Method as DBMethod,
    Job as DBJob,
)


class PeriodicDataSyncService:
    """Background service that keeps JSON backups in sync with database state."""

    def __init__(self, interval_seconds=1800):
        self.interval_seconds = max(60, int(interval_seconds or 1800))
        self._thread = None
        self._running = False
        self._stop_event = threading.Event()

    def start_monitoring(self):
        """Start the periodic synchronization loop."""
        if self._running:
            print("[SYNC MONITOR] Already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"[SYNC MONITOR] Started (interval={self.interval_seconds}s)")

    def stop_monitoring(self):
        """Stop the periodic synchronization loop."""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[SYNC MONITOR] Stopped")

    def run_sync_cycle(self):
        """Run one synchronization cycle immediately."""
        if self._has_active_executions():
            print("[SYNC MONITOR] Skipped sync cycle: active jobs running")
            return False

        session = Session()
        try:
            self._sync_users(session)
            self._sync_devices(session)
            self._sync_sequences(session)
            self._sync_log_patterns(session)
            self._sync_system_commands(session)
            self._sync_methods_snapshot(session)
            print(f"[SYNC MONITOR] Sync completed at {datetime.now(timezone.utc).isoformat()}")
            return True
        except Exception as exc:
            print(f"[SYNC MONITOR] Sync error: {exc}")
            return False
        finally:
            session.close()

    def _monitor_loop(self):
        """Main monitor loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self.run_sync_cycle()
            except Exception as exc:
                print(f"[SYNC MONITOR] Unexpected loop error: {exc}")

            waited = 0
            while waited < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(1)
                waited += 1

    @staticmethod
    def _write_json(path, payload):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    @staticmethod
    def _serialize_dt(value):
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def _has_active_executions():
        session = Session()
        try:
            active_db_jobs = (
                session.query(DBJob)
                .filter(DBJob.status.in_(["pending", "running"]))
                .count()
            )
            return active_db_jobs > 0
        except Exception:
            # If DB check fails, remain conservative and avoid sync.
            return True
        finally:
            session.close()

    def _sync_users(self, session):
        users = {}
        rows = session.query(DBUser).filter_by(active=True).order_by(DBUser.username.asc()).all()
        for row in rows:
            users[row.username] = {
                "user_id": row.username,
                "ntid": row.username,
                "email": row.email,
                "alternate_email": row.email or f"{row.username}@cable.comcast.com",
                "name": row.username,
                "password_hash": row.password_hash,
                "created_at": self._serialize_dt(row.created_at),
                "is_admin": row.is_admin,
                "team_name": row.team_name or "",
            }
        self._write_json(USERS_FILE, users)

    def _sync_devices(self, session):
        devices = []
        rows = session.query(DBDevice).filter_by(is_active=True).order_by(DBDevice.name.asc(), DBDevice.ip.asc()).all()
        for row in rows:
            devices.append({
                "ip": row.ip,
                "name": row.name,
                "username": row.username,
                "password": row.password,
                "port": row.port,
                "ir_config": row.ir_config or {},
                "mac_address": row.mac_address or "",
                "vnc_url": row.vnc_url or "",
                "use_jump_host": row.use_jump_host,
                "jump_host_config": row.jump_host_config or {},
                "device_type": row.device_type or "",
                "location": row.location or "",
                "team_name": row.team_name or "",
            })
        self._write_json(DEVICES_FILE, devices)

    def _sync_sequences(self, session):
        sequences = []
        rows = (
            session.query(DBSavedSequence)
            .order_by(DBSavedSequence.updated_at.desc(), DBSavedSequence.created_at.desc())
            .all()
        )
        for row in rows:
            queue_data = row.methods or []
            sequences.append({
                "sequence_id": row.seq_id,
                "name": row.name,
                "description": row.description or "",
                "queue_data": queue_data,
                "methods": [
                    item.get("method_id") or item.get("method") or item.get("name")
                    for item in queue_data
                    if isinstance(item, dict)
                ],
                "user_inputs": {},
                "created_at": self._serialize_dt(row.created_at),
                "created_by": str(row.created_by) if row.created_by is not None else None,
                "team_name": row.team_name or "",
                "method_rationale": row.method_rationale or [],
                "execution_count": row.execution_count or 0,
                "total_duration_seconds": row.total_duration_seconds,
                "average_duration_seconds": row.average_duration_seconds,
                "location": row.location or "",
                "is_active": row.is_active,
                "updated_at": self._serialize_dt(row.updated_at),
            })
        self._write_json(SAVED_SEQUENCES_FILE, sequences)

    def _sync_log_patterns(self, session):
        current = {
            "LOG_PATTERNS": {},
            "SYSTEM_COMMAND_PATTERNS": {},
            "PENDING_PATTERNS": {},
            "REJECTED_PATTERNS": [],
        }
        if os.path.exists(LOG_PATTERNS_FILE):
            try:
                with open(LOG_PATTERNS_FILE, "r", encoding="utf-8") as handle:
                    existing = json.load(handle)
                if isinstance(existing, dict):
                    current.update(existing)
            except Exception:
                pass

        rows = session.query(DBLogPattern).filter_by(is_active=True).order_by(DBLogPattern.pattern_id.asc()).all()
        updated_patterns = {}
        for row in rows:
            key = row.pattern_id
            updated_patterns[key] = {
                "id": key,
                "pattern_name": key,
                "log_pattern": row.regex,
                "regex": row.regex,
                "file_path": row.location or "",
                "description": row.description or "",
                "submitted_by": "db_sync",
                "submitted_at": self._serialize_dt(row.created_at),
                "approved_at": self._serialize_dt(row.updated_at) or self._serialize_dt(row.created_at),
                "is_admin_submission": True,
                "team_name": row.team_name or "",
            }

        current["LOG_PATTERNS"] = updated_patterns
        self._write_json(LOG_PATTERNS_FILE, current)

    def _sync_system_commands(self, session):
        current = {"user_defined": {}}
        if os.path.exists(SYSTEM_COMMANDS_FILE):
            try:
                with open(SYSTEM_COMMANDS_FILE, "r", encoding="utf-8") as handle:
                    existing = json.load(handle)
                if isinstance(existing, dict):
                    current.update(existing)
            except Exception:
                pass

        rows = session.query(DBSystemCommand).filter_by(is_active=True).order_by(DBSystemCommand.cmd_id.asc()).all()
        user_defined = {}
        for row in rows:
            key = (row.cmd_id or row.name or "").lower()
            if not key:
                continue
            user_defined[key] = {
                "name": key,
                "command": row.command,
                "description": row.description or "",
                "submitted_by": "db_sync",
                "created_at": self._serialize_dt(row.created_at),
                "updated_at": self._serialize_dt(row.updated_at),
                "is_builtin": False,
            }

        current["user_defined"] = user_defined
        self._write_json(SYSTEM_COMMANDS_FILE, current)

    def _sync_methods_snapshot(self, session):
        """Maintain a JSON snapshot of DB methods for diagnostics and backup."""
        methods_path = os.path.join(os.path.dirname(SYSTEM_COMMANDS_FILE), "methods_snapshot.json")
        rows = session.query(DBMethod).filter_by(is_active=True).order_by(DBMethod.method_id.asc()).all()
        payload = []
        for row in rows:
            payload.append({
                "method_id": row.method_id,
                "name": row.name,
                "description": row.description or "",
                "script_path": row.script_path,
                "parameters": row.parameters or {},
                "team_name": row.team_name or "",
                "location": row.location or "",
                "created_at": self._serialize_dt(row.created_at),
                "updated_at": self._serialize_dt(row.updated_at),
            })
        self._write_json(methods_path, payload)
