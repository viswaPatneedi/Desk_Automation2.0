"""Log Pattern Controller with DB-first approval workflow."""

import json
import os
import re
import uuid
from datetime import datetime, timezone

from config.config_paths import LOG_PATTERNS_FILE
from models.database import (
    LogPattern as DBLogPattern,
    Session,
    StagingChange,
    User as DBUser,
)


class LogPatternController:
    """Controller for managing log patterns and validations."""

    ENTITY_TYPE = "log_pattern"

    @staticmethod
    def _normalize_pattern_name(pattern_name):
        return (pattern_name or "").strip().upper()

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
    def _format_submission(change, session):
        payload = change.entity_data or {}
        return {
            "id": change.change_id,
            "pattern_name": payload.get("pattern_name", ""),
            "log_pattern": payload.get("log_pattern", ""),
            "file_path": payload.get("file_path", ""),
            "description": payload.get("description", ""),
            "submitted_by": LogPatternController._get_username(session, change.submitted_by),
            "submitted_at": change.submitted_at.isoformat() if change.submitted_at else None,
            "requested_action": payload.get("action", "add"),
            "change_comment": payload.get("change_comment", ""),
            "base_pattern": payload.get("target_pattern") or payload.get("pattern_name", ""),
            "review_comment": change.review_comment,
        }

    @staticmethod
    def _sync_json_from_db(session):
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

        rows = (
            session.query(DBLogPattern)
            .filter_by(is_active=True)
            .order_by(DBLogPattern.pattern_id.asc())
            .all()
        )
        approved = {}
        for row in rows:
            key = row.pattern_id
            approved[key] = {
                "id": key,
                "pattern_name": key,
                "log_pattern": row.regex,
                "regex": row.regex,
                "file_path": row.location or "",
                "description": row.description or "",
                "submitted_by": LogPatternController._get_username(session, row.created_by),
                "submitted_at": row.created_at.isoformat() if row.created_at else None,
                "approved_at": row.updated_at.isoformat() if row.updated_at else None,
                "is_admin_submission": False,
                "team_name": row.team_name or "",
            }

        pending_changes = (
            session.query(StagingChange)
            .filter_by(entity_type=LogPatternController.ENTITY_TYPE, status="pending")
            .order_by(StagingChange.submitted_at.desc())
            .all()
        )
        pending = {}
        for change in pending_changes:
            pending[change.change_id] = LogPatternController._format_submission(change, session)

        rejected_changes = (
            session.query(StagingChange)
            .filter_by(entity_type=LogPatternController.ENTITY_TYPE, status="rejected")
            .order_by(StagingChange.reviewed_at.desc())
            .all()
        )
        rejected = [LogPatternController._format_submission(change, session) for change in rejected_changes]

        current["LOG_PATTERNS"] = approved
        current["PENDING_PATTERNS"] = pending
        current["REJECTED_PATTERNS"] = rejected

        os.makedirs(os.path.dirname(LOG_PATTERNS_FILE) or ".", exist_ok=True)
        with open(LOG_PATTERNS_FILE, "w", encoding="utf-8") as handle:
            json.dump(current, handle, indent=2)

    @staticmethod
    def sync_json_snapshot():
        session = Session()
        try:
            LogPatternController._sync_json_from_db(session)
            return True
        except Exception:
            return False
        finally:
            session.close()

    @staticmethod
    def ensure_submissions_file_exists():
        if not os.path.exists(LOG_PATTERNS_FILE):
            os.makedirs(os.path.dirname(LOG_PATTERNS_FILE) or ".", exist_ok=True)
            with open(LOG_PATTERNS_FILE, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "LOG_PATTERNS": {},
                        "SYSTEM_COMMAND_PATTERNS": {},
                        "PENDING_PATTERNS": {},
                        "REJECTED_PATTERNS": [],
                    },
                    handle,
                    indent=2,
                )

    @staticmethod
    def get_all_submissions():
        return {
            "LOG_PATTERNS": LogPatternController.get_approved_patterns(),
            "PENDING_PATTERNS": LogPatternController.get_pending_submissions(),
            "REJECTED_PATTERNS": LogPatternController.get_rejected_submissions(),
            "SYSTEM_COMMAND_PATTERNS": {},
        }

    @staticmethod
    def save_submissions(_data):
        return True
    
    @staticmethod
    def validate_file_path_format(file_path):
        """
        Validate if a file path format is valid (without checking existence)
        Useful for patterns where the file might not exist yet but will be used at runtime
        
        Args:
            file_path: Path to validate
            
        Returns:
            Tuple (success: bool, message: str, expanded_path: str)
        """
        try:
            if not file_path or not file_path.strip():
                return False, "File path cannot be empty", file_path
            
            # Expand home directory
            expanded_path = os.path.expanduser(file_path)
            
            # Check if path is reasonable (not empty, contains valid characters)
            if len(expanded_path) < 3:
                return False, f"File path is too short: {expanded_path}", expanded_path
            
            # Ensure path contains a file extension or seems like a valid path
            if not ('/' in expanded_path or '\\' in expanded_path):
                return False, f"Invalid file path format: {expanded_path}", expanded_path
            
            return True, "File path format is valid", expanded_path
        except Exception as e:
            return False, f"Error validating file path: {str(e)}", file_path

    @staticmethod
    def validate_file_exists(file_path):
        """
        Validate if a file exists on the system.
        If file doesn't exist but path format is valid, returns success with a warning.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple (success: bool, message: str, file_path: str)
        """
        try:
            # Expand home directory
            expanded_path = os.path.expanduser(file_path)
            
            # Check if path exists
            if os.path.exists(expanded_path):
                if os.path.isdir(expanded_path):
                    return False, f"Path is a directory, not a file: {expanded_path}", expanded_path
                
                if not os.path.isfile(expanded_path):
                    return False, f"Path is not a file: {expanded_path}", expanded_path
                
                # Check if file is readable
                if not os.access(expanded_path, os.R_OK):
                    return False, f"File is not readable: {expanded_path}", expanded_path
                
                return True, "File found and validated successfully", expanded_path
            else:
                # File doesn't exist, but path format looks valid
                # This is acceptable since log files may be created at runtime
                return True, f"File path is valid (file not found yet, which is OK)", expanded_path
        except Exception as e:
            return False, f"Error validating file: {str(e)}", file_path
    
    @staticmethod
    def validate_log_pattern(pattern):
        """
        Validate if the log pattern is a valid regex
        
        Args:
            pattern: Regex pattern string
            
        Returns:
            Tuple (valid: bool, message: str)
        """
        try:
            re.compile(pattern)
            return True, "Pattern is valid regex"
        except re.error as e:
            return False, f"Invalid regex pattern: {str(e)}"
    
    @staticmethod
    def submit_log_pattern(
        pattern_name,
        log_pattern,
        file_path,
        description="",
        submitted_by_user=None,
        is_admin=False,
        requested_action="add",
        target_pattern=None,
        change_comment="",
    ):
        """
        Submit a new log pattern validation
        
        Args:
            pattern_name: Name/identifier for the pattern
            log_pattern: The regex pattern to match
            file_path: File path where the log should be checked
            description: Optional description of the pattern
            submitted_by_user: User who submitted (NTID)
            is_admin: Whether submitter is admin (currently not used for auto-approval)
            
        Returns:
            Tuple (success: bool, message: str, submission_id: str or None)
        """
        if not pattern_name or not pattern_name.strip():
            return False, "Pattern name cannot be empty", None

        pattern_name = LogPatternController._normalize_pattern_name(pattern_name)
        target_pattern = LogPatternController._normalize_pattern_name(target_pattern or pattern_name)
        requested_action = (requested_action or "add").strip().lower()
        change_comment = (change_comment or "").strip()

        if requested_action not in {"add", "edit", "delete"}:
            return False, "Invalid requested action", None

        if requested_action in {"edit", "delete"} and not change_comment:
            return False, "Comment is required for edit/delete requests", None
        
        if not re.match(r'^[a-zA-Z0-9_]+$', pattern_name):
            return False, "Pattern name can only contain alphanumeric characters and underscores", None
        
        # Validate log pattern
        valid_pattern, pattern_msg = LogPatternController.validate_log_pattern(log_pattern)
        if not valid_pattern:
            return False, pattern_msg, None
        
        # Validate file path format (not existence - file may not exist yet)
        file_valid, file_msg, expanded_path = LogPatternController.validate_file_path_format(file_path)
        if not file_valid:
            return False, file_msg, None
        
        session = Session()
        try:
            if requested_action == "add":
                existing = (
                    session.query(DBLogPattern)
                    .filter_by(pattern_id=pattern_name, is_active=True)
                    .first()
                )
                if existing:
                    return False, f"Pattern '{pattern_name}' already exists", None
            else:
                existing = (
                    session.query(DBLogPattern)
                    .filter_by(pattern_id=target_pattern, is_active=True)
                    .first()
                )
                if not existing:
                    return False, f"Pattern '{target_pattern}' not found", None

            submission_id = str(uuid.uuid4())
            submission_payload = {
                "action": requested_action,
                "pattern_name": pattern_name,
                "target_pattern": target_pattern,
                "log_pattern": log_pattern,
                "file_path": expanded_path,
                "description": description,
                "change_comment": change_comment,
                "is_admin_submission": bool(is_admin),
            }

            change = StagingChange(
                change_id=submission_id,
                entity_type=LogPatternController.ENTITY_TYPE,
                entity_data=submission_payload,
                submitted_by=LogPatternController._get_user_id(session, submitted_by_user),
                status="pending",
            )
            session.add(change)
            session.commit()
            LogPatternController._sync_json_from_db(session)
            return True, f"Pattern request '{requested_action}' submitted for admin approval", submission_id
        except Exception as e:
            session.rollback()
            return False, f"Failed to submit request: {str(e)}", None
        finally:
            session.close()
    
    @staticmethod
    def get_pending_submissions():
        """Get all pending submissions awaiting admin approval."""
        session = Session()
        try:
            rows = (
                session.query(StagingChange)
                .filter_by(entity_type=LogPatternController.ENTITY_TYPE, status="pending")
                .order_by(StagingChange.submitted_at.desc())
                .all()
            )
            return {
                row.change_id: LogPatternController._format_submission(row, session)
                for row in rows
            }
        except Exception:
            return {}
        finally:
            session.close()
    
    @staticmethod
    def get_approved_patterns():
        """Get all approved log patterns from database."""
        session = Session()
        try:
            rows = (
                session.query(DBLogPattern)
                .filter_by(is_active=True)
                .order_by(DBLogPattern.pattern_id.asc())
                .all()
            )
            approved = {}
            for row in rows:
                approved[row.pattern_id] = {
                    "id": row.pattern_id,
                    "pattern_name": row.pattern_id,
                    "log_pattern": row.regex,
                    "regex": row.regex,
                    "file_path": row.location or "",
                    "description": row.description or "",
                    "submitted_by": LogPatternController._get_username(session, row.created_by),
                    "submitted_at": row.created_at.isoformat() if row.created_at else None,
                    "approved_at": row.updated_at.isoformat() if row.updated_at else None,
                    "is_admin_submission": False,
                    "team_name": row.team_name or "",
                }
            return approved
        except Exception:
            return LogPatternController.get_existing_patterns()
        finally:
            session.close()

    @staticmethod
    def get_existing_patterns():
        """Get the configured patterns shown in the Existing Patterns view."""
        if not os.path.exists(LOG_PATTERNS_FILE):
            return {}
        try:
            with open(LOG_PATTERNS_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data.get("LOG_PATTERNS", {}) if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def get_rejected_submissions():
        session = Session()
        try:
            rows = (
                session.query(StagingChange)
                .filter_by(entity_type=LogPatternController.ENTITY_TYPE, status="rejected")
                .order_by(StagingChange.reviewed_at.desc())
                .all()
            )
            return [LogPatternController._format_submission(row, session) for row in rows]
        except Exception:
            return []
        finally:
            session.close()
    
    @staticmethod
    def approve_submission(submission_id, reviewed_by_user=None):
        """
        Approve a pending submission (admin only)
        
        Args:
            submission_id: ID of the submission to approve
            
        Returns:
            Tuple (success: bool, message: str)
        """
        session = Session()
        try:
            change = (
                session.query(StagingChange)
                .filter_by(
                    change_id=submission_id,
                    entity_type=LogPatternController.ENTITY_TYPE,
                    status="pending",
                )
                .first()
            )
            if not change:
                return False, f"Submission '{submission_id}' not found in pending"

            payload = change.entity_data or {}
            action = (payload.get("action") or "add").lower()
            pattern_name = LogPatternController._normalize_pattern_name(payload.get("pattern_name"))
            target_pattern = LogPatternController._normalize_pattern_name(
                payload.get("target_pattern") or pattern_name
            )

            if action == "add":
                existing = (
                    session.query(DBLogPattern)
                    .filter_by(pattern_id=pattern_name, is_active=True)
                    .first()
                )
                if existing:
                    return False, f"Pattern '{pattern_name}' already exists"

                creator_id = change.submitted_by
                row = DBLogPattern(
                    pattern_id=pattern_name,
                    name=pattern_name,
                    regex=payload.get("log_pattern", ""),
                    description=payload.get("description", ""),
                    location=payload.get("file_path", ""),
                    is_custom=True,
                    created_by=creator_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    is_active=True,
                )
                session.add(row)

            elif action == "edit":
                row = (
                    session.query(DBLogPattern)
                    .filter_by(pattern_id=target_pattern, is_active=True)
                    .first()
                )
                if not row:
                    return False, f"Pattern '{target_pattern}' not found"
                row.regex = payload.get("log_pattern", row.regex)
                row.description = payload.get("description", row.description)
                row.location = payload.get("file_path", row.location)
                row.updated_at = datetime.now(timezone.utc)

            elif action == "delete":
                row = (
                    session.query(DBLogPattern)
                    .filter_by(pattern_id=target_pattern, is_active=True)
                    .first()
                )
                if not row:
                    return False, f"Pattern '{target_pattern}' not found"
                session.delete(row)
            else:
                return False, f"Unsupported action '{action}'"

            change.status = "approved"
            change.reviewed_by = LogPatternController._get_user_id(session, reviewed_by_user)
            change.reviewed_at = datetime.now(timezone.utc)
            change.approved_at = datetime.now(timezone.utc)

            session.commit()
            LogPatternController._sync_json_from_db(session)
            return True, f"Submission '{submission_id}' approved successfully"
        except Exception as e:
            session.rollback()
            return False, f"Failed to approve submission: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def reject_submission(submission_id, rejection_reason=""):
        """
        Reject a pending submission (admin only)
        
        Args:
            submission_id: ID of the submission to reject
            rejection_reason: Reason for rejection
            
        Returns:
            Tuple (success: bool, message: str)
        """
        session = Session()
        try:
            change = (
                session.query(StagingChange)
                .filter_by(
                    change_id=submission_id,
                    entity_type=LogPatternController.ENTITY_TYPE,
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
            LogPatternController._sync_json_from_db(session)
            return True, f"Submission rejected: {change.review_comment}"
        except Exception as e:
            session.rollback()
            return False, f"Failed to reject submission: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def modify_approved_pattern(pattern_name, new_log_pattern, new_file_path, new_description=""):
        """
        Modify an approved pattern (admin only)
        
        Args:
            pattern_name: Name of the pattern to modify
            new_log_pattern: New regex pattern
            new_file_path: New file path
            new_description: New description
            
        Returns:
            Tuple (success: bool, message: str)
        """
        # Validate new pattern
        valid_pattern, pattern_msg = LogPatternController.validate_log_pattern(new_log_pattern)
        if not valid_pattern:
            return False, pattern_msg
        
        # Validate file path format (not existence - file may not exist yet)
        file_valid, file_msg, expanded_path = LogPatternController.validate_file_path_format(new_file_path)
        if not file_valid:
            return False, file_msg
        
        session = Session()
        try:
            key = LogPatternController._normalize_pattern_name(pattern_name)
            row = session.query(DBLogPattern).filter_by(pattern_id=key, is_active=True).first()
            if not row:
                return False, f"Pattern '{key}' not found in approved patterns"

            row.regex = new_log_pattern
            row.location = expanded_path
            row.description = new_description
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            LogPatternController._sync_json_from_db(session)
            return True, f"Pattern '{key}' modified successfully"
        except Exception as e:
            session.rollback()
            return False, f"Failed to modify pattern: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def delete_approved_pattern(pattern_name):
        """
        Delete an approved pattern (admin only)
        
        Args:
            pattern_name: Name of the pattern to delete
            
        Returns:
            Tuple (success: bool, message: str)
        """
        session = Session()
        try:
            key = LogPatternController._normalize_pattern_name(pattern_name)
            row = session.query(DBLogPattern).filter_by(pattern_id=key, is_active=True).first()
            if not row:
                return False, f"Pattern '{key}' not found in approved patterns"
            session.delete(row)
            session.commit()
            LogPatternController._sync_json_from_db(session)
            return True, f"Pattern '{key}' deleted successfully"
        except Exception as e:
            session.rollback()
            return False, f"Failed to delete pattern: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def get_pattern_summary():
        """
        Get a summary of all patterns
        
        Returns:
            Dictionary with counts and summary information
        """
        approved = LogPatternController.get_approved_patterns()
        pending = LogPatternController.get_pending_submissions()
        rejected = LogPatternController.get_rejected_submissions()

        return {
            "approved_count": len(approved),
            "pending_count": len(pending),
            "rejected_count": len(rejected),
            "approved_patterns": list(approved.keys()),
            "pending_patterns": [
                {
                    "id": pid,
                    "name": p.get("pattern_name"),
                    "submitted_by": p.get("submitted_by"),
                    "submitted_at": p.get("submitted_at"),
                    "requested_action": p.get("requested_action", "add"),
                }
                for pid, p in pending.items()
            ],
        }


def require_admin(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    from flask import jsonify
    from flask_login import current_user
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function
