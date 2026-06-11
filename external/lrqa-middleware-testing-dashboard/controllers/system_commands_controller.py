"""System Commands Controller with DB-first approval workflow."""

import json
import os
import uuid
from datetime import datetime, timezone

from config.config_paths import SYSTEM_COMMANDS_FILE, SYSTEM_COMMANDS_SUBMISSIONS_FILE
from models.database import (
    Session,
    StagingChange,
    SystemCommand as DBSystemCommand,
    User as DBUser,
)


class SystemCommandsController:
    """Controller for managing system commands."""

    ENTITY_TYPE = "system_command"

    @staticmethod
    def _normalize_command_name(command_name):
        return (command_name or "").strip().lower()

    @staticmethod
    def _get_user_id(session, username):
        if not username:
            return None
        user = session.query(DBUser).filter_by(username=username).first()
        return user.id if user else None

    @staticmethod
    def _get_username(session, user_id):
        if not user_id:
            return "unknown"
        user = session.query(DBUser).filter_by(id=user_id).first()
        return user.username if user else "unknown"

    @staticmethod
    def _format_pending(change, session):
        payload = change.entity_data or {}
        return {
            "id": change.change_id,
            "command_name": payload.get("command_name", ""),
            "command": payload.get("command", ""),
            "description": payload.get("description", ""),
            "submitted_by": SystemCommandsController._get_username(session, change.submitted_by),
            "submitted_at": change.submitted_at.isoformat() if change.submitted_at else None,
            "requested_action": payload.get("action", "add"),
            "change_comment": payload.get("change_comment", ""),
            "target_command": payload.get("target_command") or payload.get("command_name", ""),
        }

    @staticmethod
    def _sync_json_from_db(session):
        rows = (
            session.query(DBSystemCommand)
            .filter_by(is_active=True)
            .order_by(DBSystemCommand.cmd_id.asc())
            .all()
        )
        user_defined = {}
        approved = {}
        for row in rows:
            key = (row.cmd_id or row.name or "").strip().lower()
            if not key:
                continue
            item = {
                "name": key,
                "command": row.command,
                "description": row.description or "",
                "submitted_by": SystemCommandsController._get_username(session, row.created_by),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "is_builtin": False,
            }
            user_defined[key] = item
            approved[key] = {
                "id": key,
                "command_name": key,
                "command": row.command,
                "description": row.description or "",
                "submitted_by": item["submitted_by"],
                "submitted_at": item["created_at"],
                "approved_at": item["updated_at"],
            }

        pending_rows = (
            session.query(StagingChange)
            .filter_by(entity_type=SystemCommandsController.ENTITY_TYPE, status="pending")
            .order_by(StagingChange.submitted_at.desc())
            .all()
        )
        pending = {
            row.change_id: SystemCommandsController._format_pending(row, session)
            for row in pending_rows
        }

        rejected_rows = (
            session.query(StagingChange)
            .filter_by(entity_type=SystemCommandsController.ENTITY_TYPE, status="rejected")
            .order_by(StagingChange.reviewed_at.desc())
            .all()
        )
        rejected = [SystemCommandsController._format_pending(row, session) for row in rejected_rows]

        os.makedirs(os.path.dirname(SYSTEM_COMMANDS_FILE) or ".", exist_ok=True)
        with open(SYSTEM_COMMANDS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"user_defined": user_defined}, handle, indent=2)

        os.makedirs(os.path.dirname(SYSTEM_COMMANDS_SUBMISSIONS_FILE) or ".", exist_ok=True)
        with open(SYSTEM_COMMANDS_SUBMISSIONS_FILE, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "approved": approved,
                    "pending": pending,
                    "rejected": rejected,
                },
                handle,
                indent=2,
            )

    @staticmethod
    def get_builtin_commands():
        from config.config_log_patterns import get_system_commands

        checks = get_system_commands()
        builtin_commands = {}
        for name, check_data in checks.items():
            key = (name or "").strip().lower()
            builtin_commands[key] = {
                "name": key,
                "command": check_data.get("command"),
                "description": check_data.get("description"),
                "is_builtin": True,
                "created_at": "System",
            }
        return builtin_commands

    @staticmethod
    def get_approved_commands():
        session = Session()
        try:
            rows = (
                session.query(DBSystemCommand)
                .filter_by(is_active=True)
                .order_by(DBSystemCommand.cmd_id.asc())
                .all()
            )
            approved = {}
            for row in rows:
                key = (row.cmd_id or row.name or "").strip().lower()
                if not key:
                    continue
                approved[key] = {
                    "id": key,
                    "command_name": key,
                    "command": row.command,
                    "description": row.description or "",
                    "submitted_by": SystemCommandsController._get_username(session, row.created_by),
                    "submitted_at": row.created_at.isoformat() if row.created_at else None,
                    "approved_at": row.updated_at.isoformat() if row.updated_at else None,
                }
            return approved
        finally:
            session.close()

    @staticmethod
    def get_pending_submissions():
        session = Session()
        try:
            rows = (
                session.query(StagingChange)
                .filter_by(entity_type=SystemCommandsController.ENTITY_TYPE, status="pending")
                .order_by(StagingChange.submitted_at.desc())
                .all()
            )
            return {
                row.change_id: SystemCommandsController._format_pending(row, session)
                for row in rows
            }
        finally:
            session.close()

    @staticmethod
    def get_all_submissions():
        return {
            "approved": SystemCommandsController.get_approved_commands(),
            "pending": SystemCommandsController.get_pending_submissions(),
            "rejected": [],
        }

    @staticmethod
    def get_all_commands():
        return {
            "builtin": SystemCommandsController.get_builtin_commands(),
            "user_defined": SystemCommandsController.get_approved_commands(),
        }

    @staticmethod
    def submit_command(
        command_name,
        command_text,
        description="",
        submitted_by="",
        is_admin=False,
        requested_action="add",
        target_command=None,
        change_comment="",
    ):
        if not command_name or not command_name.strip():
            return False, "Command name cannot be empty", None

        requested_action = (requested_action or "add").strip().lower()
        normalized_name = SystemCommandsController._normalize_command_name(command_name)
        target_name = SystemCommandsController._normalize_command_name(target_command or normalized_name)
        change_comment = (change_comment or "").strip()

        if requested_action not in {"add", "edit", "delete"}:
            return False, "Invalid requested action", None

        if requested_action in {"add", "edit"} and (not command_text or not command_text.strip()):
            return False, "Command text cannot be empty", None

        if requested_action in {"edit", "delete"} and not change_comment:
            return False, "Comment is required for edit/delete requests", None

        if not normalized_name.replace("_", "").isalnum():
            return False, "Command name can only contain alphanumeric characters and underscores", None

        session = Session()
        try:
            builtin = SystemCommandsController.get_builtin_commands()

            if requested_action == "add":
                if normalized_name in builtin:
                    return False, f"Command name '{normalized_name}' conflicts with builtin command", None
                existing = (
                    session.query(DBSystemCommand)
                    .filter_by(cmd_id=normalized_name, is_active=True)
                    .first()
                )
                if existing:
                    return False, f"Command '{normalized_name}' already exists", None
            else:
                existing = (
                    session.query(DBSystemCommand)
                    .filter_by(cmd_id=target_name, is_active=True)
                    .first()
                )
                if not existing:
                    return False, f"Command '{target_name}' not found", None

            submission_id = str(uuid.uuid4())
            payload = {
                "action": requested_action,
                "command_name": normalized_name,
                "target_command": target_name,
                "command": (command_text or "").strip(),
                "description": (description or "").strip(),
                "change_comment": change_comment,
                "is_admin_submission": bool(is_admin),
            }

            change = StagingChange(
                change_id=submission_id,
                entity_type=SystemCommandsController.ENTITY_TYPE,
                entity_data=payload,
                submitted_by=SystemCommandsController._get_user_id(session, submitted_by),
                status="pending",
            )
            session.add(change)
            session.commit()

            if is_admin:
                ok, msg = SystemCommandsController.approve_submission(
                    submission_id,
                    reviewed_by=submitted_by,
                )
                if ok:
                    return True, msg, submission_id
                return False, msg, None

            SystemCommandsController._sync_json_from_db(session)
            return True, f"Command '{normalized_name}' submitted for approval", submission_id
        except Exception as e:
            session.rollback()
            return False, f"Failed to submit command request: {str(e)}", None
        finally:
            session.close()

    @staticmethod
    def approve_submission(submission_id, reviewed_by=None):
        session = Session()
        try:
            change = (
                session.query(StagingChange)
                .filter_by(
                    change_id=submission_id,
                    entity_type=SystemCommandsController.ENTITY_TYPE,
                    status="pending",
                )
                .first()
            )
            if not change:
                return False, f"Submission '{submission_id}' not found in pending"

            payload = change.entity_data or {}
            action = (payload.get("action") or "add").lower()
            command_name = SystemCommandsController._normalize_command_name(payload.get("command_name"))
            target_name = SystemCommandsController._normalize_command_name(
                payload.get("target_command") or command_name
            )

            if action == "add":
                existing = (
                    session.query(DBSystemCommand)
                    .filter_by(cmd_id=command_name, is_active=True)
                    .first()
                )
                if existing:
                    return False, f"Command '{command_name}' already exists"

                row = DBSystemCommand(
                    cmd_id=command_name,
                    name=command_name,
                    command=payload.get("command", "").strip(),
                    description=payload.get("description", "").strip(),
                    category="user_defined",
                    is_custom=True,
                    created_by=change.submitted_by,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    is_active=True,
                )
                session.add(row)

            elif action == "edit":
                row = (
                    session.query(DBSystemCommand)
                    .filter_by(cmd_id=target_name, is_active=True)
                    .first()
                )
                if not row:
                    return False, f"Command '{target_name}' not found"
                row.command = payload.get("command", row.command).strip()
                row.description = payload.get("description", row.description).strip()
                row.updated_at = datetime.now(timezone.utc)

            elif action == "delete":
                row = (
                    session.query(DBSystemCommand)
                    .filter_by(cmd_id=target_name, is_active=True)
                    .first()
                )
                if not row:
                    return False, f"Command '{target_name}' not found"
                session.delete(row)
            else:
                return False, f"Unsupported action '{action}'"

            change.status = "approved"
            change.reviewed_by = SystemCommandsController._get_user_id(session, reviewed_by)
            change.reviewed_at = datetime.now(timezone.utc)
            change.approved_at = datetime.now(timezone.utc)

            session.commit()
            SystemCommandsController._sync_json_from_db(session)
            return True, f"Command request '{submission_id}' approved successfully"
        except Exception as e:
            session.rollback()
            return False, f"Failed to approve submission: {str(e)}"
        finally:
            session.close()

    @staticmethod
    def reject_submission(submission_id, rejection_reason=""):
        session = Session()
        try:
            change = (
                session.query(StagingChange)
                .filter_by(
                    change_id=submission_id,
                    entity_type=SystemCommandsController.ENTITY_TYPE,
                    status="pending",
                )
                .first()
            )
            if not change:
                return False, f"Submission '{submission_id}' not found in pending"

            change.status = "rejected"
            change.review_comment = (rejection_reason or "No reason provided").strip()
            change.reviewed_at = datetime.now(timezone.utc)
            session.commit()
            SystemCommandsController._sync_json_from_db(session)
            return True, f"Command request rejected: {change.review_comment}"
        except Exception as e:
            session.rollback()
            return False, f"Failed to reject submission: {str(e)}"
        finally:
            session.close()

    @staticmethod
    def add_command(command_name, command_text, description="", submitted_by=""):
        return SystemCommandsController.submit_command(
            command_name=command_name,
            command_text=command_text,
            description=description,
            submitted_by=submitted_by,
            is_admin=True,
            requested_action="add",
        )[:2]

    @staticmethod
    def update_command(command_name, command_text, description=""):
        session = Session()
        try:
            key = SystemCommandsController._normalize_command_name(command_name)
            row = session.query(DBSystemCommand).filter_by(cmd_id=key, is_active=True).first()
            if not row:
                return False, f"Command '{key}' not found"
            row.command = (command_text or "").strip()
            row.description = (description or "").strip()
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            SystemCommandsController._sync_json_from_db(session)
            return True, f"Command '{key}' updated successfully"
        except Exception as e:
            session.rollback()
            return False, f"Failed to update command: {str(e)}"
        finally:
            session.close()

    @staticmethod
    def delete_command(command_name):
        session = Session()
        try:
            key = SystemCommandsController._normalize_command_name(command_name)
            row = session.query(DBSystemCommand).filter_by(cmd_id=key, is_active=True).first()
            if not row:
                return False, f"Command '{key}' not found"
            session.delete(row)
            session.commit()
            SystemCommandsController._sync_json_from_db(session)
            return True, f"Command '{key}' deleted successfully"
        except Exception as e:
            session.rollback()
            return False, f"Failed to delete command: {str(e)}"
        finally:
            session.close()

    @staticmethod
    def promote_to_config(command_name):
        submissions = SystemCommandsController.get_all_submissions()
        approved = submissions.get("approved", {})
        key = SystemCommandsController._normalize_command_name(command_name)

        if key not in approved:
            return False, f"Command '{key}' not found in approved commands"

        command_data = approved[key]
        try:
            with open("config_log_patterns.py", "r", encoding="utf-8") as handle:
                config_content = handle.read()

            var_name = f"system_command_{key}"
            command_text = command_data.get("command", "")
            new_line = f'{var_name} = "{command_text}"'
            insert_marker = "def get_system_commands():"

            if insert_marker not in config_content:
                return False, "Could not find insertion point in config file"

            config_content = config_content.replace(insert_marker, f"{new_line}\n\n\n{insert_marker}")
            with open("config_log_patterns.py", "w", encoding="utf-8") as handle:
                handle.write(config_content)

            return True, f"Command '{key}' promoted to config successfully"
        except Exception as e:
            return False, f"Error promoting command to config: {str(e)}"

    @staticmethod
    def get_all_optional_checks():
        builtin = SystemCommandsController.get_builtin_commands()
        approved = SystemCommandsController.get_approved_commands()
        approved_checks = {}
        for name, cmd_data in approved.items():
            approved_checks[name] = {
                "command": cmd_data.get("command"),
                "description": cmd_data.get("description"),
                "submitted_by": cmd_data.get("submitted_by"),
            }
        return {**builtin, **approved_checks}
