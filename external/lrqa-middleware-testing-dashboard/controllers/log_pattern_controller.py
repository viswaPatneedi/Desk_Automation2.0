"""
Log Pattern Controller
Manages log pattern validations, submissions, and admin approvals
"""

import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from config.config_paths import LOG_PATTERNS_FILE


class LogPatternController:
    """Controller for managing log patterns and validations"""
    
    def __init__(self):
        """Initialize the controller"""
        self.ensure_submissions_file_exists()
    
    @staticmethod
    def ensure_submissions_file_exists():
        """Ensure the submissions JSON file exists"""
        if not os.path.exists(LOG_PATTERNS_FILE):
            initial_data = {
                'LOG_PATTERNS': {},
                'SYSTEM_COMMAND_PATTERNS': {},
                'PENDING_PATTERNS': {},
                'REJECTED_PATTERNS': []
            }
            with open(LOG_PATTERNS_FILE, 'w') as f:
                json.dump(initial_data, f, indent=2)
    
    @staticmethod
    def get_all_submissions():
        """Get all log pattern submissions (approved, pending, rejected)"""
        try:
            with open(LOG_PATTERNS_FILE, 'r') as f:
                data = json.load(f)
                data.setdefault('LOG_PATTERNS', {})
                data.setdefault('SYSTEM_COMMAND_PATTERNS', {})
                data.setdefault('PENDING_PATTERNS', {})
                data.setdefault('REJECTED_PATTERNS', [])
                return data
        except (json.JSONDecodeError, IOError):
            return {
                'LOG_PATTERNS': {},
                'SYSTEM_COMMAND_PATTERNS': {},
                'PENDING_PATTERNS': {},
                'REJECTED_PATTERNS': []
            }
    
    @staticmethod
    def save_submissions(data):
        """Save submissions to file"""
        with open(LOG_PATTERNS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
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
        is_admin=False
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
        # Validate pattern name
        if not pattern_name or not pattern_name.strip():
            return False, "Pattern name cannot be empty", None

        # Normalize to uppercase for consistent naming
        pattern_name = pattern_name.strip().upper()
        
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
        
        # Create submission
        submission_id = f"{pattern_name}_{int(datetime.now(timezone.utc).timestamp())}"
        
        submissions = LogPatternController.get_all_submissions()
        
        # Check if pattern name already exists in approved patterns
        if pattern_name in submissions['LOG_PATTERNS']:
            return False, f"Pattern '{pattern_name}' already exists in approved patterns", None
        
        # Create submission object
        submission = {
            'id': submission_id,
            'pattern_name': pattern_name,
            'log_pattern': log_pattern,
            'file_path': expanded_path,
            'description': description,
            'submitted_by': submitted_by_user or 'unknown',
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'is_admin_submission': is_admin
        }
        
        # All submissions (admin and non-admin) go to pending for approval workflow
        # This allows proper review and tracking of all pattern changes
        submissions['PENDING_PATTERNS'][submission_id] = submission
        LogPatternController.save_submissions(submissions)
        return True, f"Pattern '{pattern_name}' submitted for admin approval", submission_id
    
    @staticmethod
    def get_pending_submissions():
        """Get all pending submissions awaiting admin approval"""
        submissions = LogPatternController.get_all_submissions()
        return submissions.get('PENDING_PATTERNS', {})
    
    @staticmethod
    def get_approved_patterns():
        """Get all approved log patterns"""
        submissions = LogPatternController.get_all_submissions()
        return submissions.get('LOG_PATTERNS', {})
    
    @staticmethod
    def approve_submission(submission_id):
        """
        Approve a pending submission (admin only)
        
        Args:
            submission_id: ID of the submission to approve
            
        Returns:
            Tuple (success: bool, message: str)
        """
        submissions = LogPatternController.get_all_submissions()
        pending = submissions.get('PENDING_PATTERNS', {})
        
        if submission_id not in pending:
            return False, f"Submission '{submission_id}' not found in pending"
        
        submission = pending[submission_id]
        pattern_name = submission['pattern_name']
        if pattern_name:
            pattern_name = pattern_name.strip().upper()
            submission['pattern_name'] = pattern_name
        
        # Check if this is an edit submission (pattern_name ends with _EDIT)
        is_edit_submission = pattern_name.endswith('_EDIT')
        
        if is_edit_submission:
            # Extract original pattern name
            original_pattern_name = pattern_name.rsplit('_EDIT', 1)[0]
            original_pattern_name = original_pattern_name.strip().upper()
            
            # Check if original pattern exists in approved patterns OR in config
            pattern_exists_in_approved = original_pattern_name in submissions['LOG_PATTERNS']
            
            # For both cases (config-based or approved), we add/update in approved patterns
            # Approved patterns take precedence over config patterns
            submissions['LOG_PATTERNS'][original_pattern_name] = {
                'id': submission.get('id'),
                'pattern_name': original_pattern_name,
                'log_pattern': submission.get('log_pattern'),
                'file_path': submission.get('file_path'),
                'description': submission.get('description'),
                'submitted_by': submission.get('submitted_by'),
                'submitted_at': submission.get('submitted_at'),
                'approved_at': datetime.now(timezone.utc).isoformat(),
                'is_admin_submission': False,
                'is_config_override': not pattern_exists_in_approved  # Mark if this overrides a config pattern
            }
            
            # Remove the edit submission from pending
            del submissions['PENDING_PATTERNS'][submission_id]
            LogPatternController.save_submissions(submissions)
            
            if pattern_exists_in_approved:
                return True, f"Edit for pattern '{original_pattern_name}' approved successfully"
            else:
                return True, f"Edit for config pattern '{original_pattern_name}' approved successfully (added to approved patterns)"
        else:
            # Regular new pattern submission
            # Check if pattern name already exists in approved
            if pattern_name in submissions['LOG_PATTERNS']:
                return False, f"Pattern '{pattern_name}' already exists in approved patterns"
            
            # Move to approved
            submissions['LOG_PATTERNS'][pattern_name] = submission
            del submissions['PENDING_PATTERNS'][submission_id]
            
            LogPatternController.save_submissions(submissions)
            return True, f"Submission '{pattern_name}' approved successfully"
    
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
        submissions = LogPatternController.get_all_submissions()
        pending = submissions.get('PENDING_PATTERNS', {})
        
        if submission_id not in pending:
            return False, f"Submission '{submission_id}' not found in pending"
        
        submission = pending[submission_id]
        submission['rejection_reason'] = rejection_reason
        submission['rejected_at'] = datetime.now(timezone.utc).isoformat()
        
        # Move to rejected
        submissions['REJECTED_PATTERNS'].append(submission)
        del submissions['PENDING_PATTERNS'][submission_id]
        
        LogPatternController.save_submissions(submissions)
        return True, f"Submission rejected: {rejection_reason}"
    
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
        
        submissions = LogPatternController.get_all_submissions()
        approved = submissions.get('LOG_PATTERNS', {})
        
        if pattern_name not in approved:
            return False, f"Pattern '{pattern_name}' not found in approved patterns"
        
        # Update the pattern
        approved[pattern_name]['log_pattern'] = new_log_pattern
        approved[pattern_name]['file_path'] = expanded_path
        approved[pattern_name]['description'] = new_description
        approved[pattern_name]['modified_at'] = datetime.now(timezone.utc).isoformat()
        
        LogPatternController.save_submissions(submissions)
        return True, f"Pattern '{pattern_name}' modified successfully"
    
    @staticmethod
    def delete_approved_pattern(pattern_name):
        """
        Delete an approved pattern (admin only)
        
        Args:
            pattern_name: Name of the pattern to delete
            
        Returns:
            Tuple (success: bool, message: str)
        """
        submissions = LogPatternController.get_all_submissions()
        approved = submissions.get('LOG_PATTERNS', {})
        
        if pattern_name not in approved:
            return False, f"Pattern '{pattern_name}' not found in approved patterns"
        
        del approved[pattern_name]
        LogPatternController.save_submissions(submissions)
        return True, f"Pattern '{pattern_name}' deleted successfully"
    
    @staticmethod
    def get_pattern_summary():
        """
        Get a summary of all patterns
        
        Returns:
            Dictionary with counts and summary information
        """
        submissions = LogPatternController.get_all_submissions()

        return {
            'approved_count': len(submissions.get('LOG_PATTERNS', {})),
            'pending_count': len(submissions.get('PENDING_PATTERNS', {})),
            'rejected_count': len(submissions.get('REJECTED_PATTERNS', [])),
            'approved_patterns': list(submissions.get('LOG_PATTERNS', {}).keys()),
            'pending_patterns': [
                {
                    'id': pid,
                    'name': p.get('pattern_name'),
                    'submitted_by': p.get('submitted_by'),
                    'submitted_at': p.get('submitted_at')
                }
                for pid, p in submissions.get('PENDING_PATTERNS', {}).items()
            ]
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
