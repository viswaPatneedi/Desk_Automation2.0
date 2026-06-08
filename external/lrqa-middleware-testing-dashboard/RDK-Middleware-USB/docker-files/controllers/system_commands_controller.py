"""
System Commands Controller
Manages system command definitions for log checking and system monitoring
Implements an approval workflow similar to log patterns
"""

import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from config_paths import SYSTEM_COMMANDS_FILE, SYSTEM_COMMANDS_SUBMISSIONS_FILE


class SystemCommandsController:
    """Controller for managing system commands"""
    
    @staticmethod
    def get_all_commands():
        """
        Get all system commands (both builtin and user-defined)
        
        Returns:
            dict: Dictionary with 'builtin' and 'user_defined' commands
        """
        builtin = SystemCommandsController.get_builtin_commands()
        user_defined = SystemCommandsController.get_user_defined_commands()
        
        return {
            'builtin': builtin,
            'user_defined': user_defined
        }
    
    @staticmethod
    def get_builtin_commands():
        """
        Get builtin system commands from config
        
        Returns:
            dict: Dictionary of builtin commands
        """
        from config_log_patterns import get_system_commands
        checks = get_system_commands()
        
        builtin_commands = {}
        for name, check_data in checks.items():
            builtin_commands[name] = {
                'name': name,
                'command': check_data.get('command'),
                'description': check_data.get('description'),
                'is_builtin': True,
                'created_at': 'System'
            }
        
        return builtin_commands
    
    @staticmethod
    def get_user_defined_commands():
        """
        Get user-defined system commands from storage
        
        Returns:
            dict: Dictionary of user-defined commands
        """
        if not os.path.exists(SYSTEM_COMMANDS_FILE):
            return {}
        
        try:
            with open(SYSTEM_COMMANDS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('user_defined', {})
        except (json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def save_user_commands(commands):
        """
        Save user-defined commands to file
        
        Args:
            commands: Dictionary of commands to save
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            all_data = {}
            if os.path.exists(SYSTEM_COMMANDS_FILE):
                with open(SYSTEM_COMMANDS_FILE, 'r') as f:
                    all_data = json.load(f)
            
            all_data['user_defined'] = commands
            
            with open(SYSTEM_COMMANDS_FILE, 'w') as f:
                json.dump(all_data, f, indent=2)
            
            return True, "Commands saved successfully"
        except Exception as e:
            return False, f"Error saving commands: {str(e)}"
    
    @staticmethod
    def add_command(command_name, command_text, description="", submitted_by=""):
        """
        Add a new system command
        
        Args:
            command_name: Name/identifier for the command
            command_text: The actual shell command
            description: Optional description
            submitted_by: User who submitted
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Validate inputs
        if not command_name or not command_name.strip():
            return False, "Command name cannot be empty"
        
        if not command_text or not command_text.strip():
            return False, "Command text cannot be empty"
        
        # Check for invalid characters in name
        if not command_name.replace('_', '').isalnum():
            return False, "Command name can only contain alphanumeric characters and underscores"
        
        # Check if command already exists
        existing = SystemCommandsController.get_user_defined_commands()
        if command_name.lower() in existing:
            return False, f"Command '{command_name}' already exists"
        
        # Check if it conflicts with builtin commands
        builtin = SystemCommandsController.get_builtin_commands()
        if command_name.lower() in builtin:
            return False, f"Command name '{command_name}' conflicts with builtin command"
        
        # Add new command
        existing[command_name.lower()] = {
            'name': command_name.lower(),
            'command': command_text.strip(),
            'description': description.strip(),
            'submitted_by': submitted_by or 'unknown',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_builtin': False
        }
        
        success, message = SystemCommandsController.save_user_commands(existing)
        if success:
            return True, f"Command '{command_name}' added successfully"
        return False, message
    
    @staticmethod
    def update_command(command_name, command_text, description=""):
        """
        Update an existing user-defined command
        
        Args:
            command_name: Name of command to update
            command_text: New command text
            description: New description
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not command_text or not command_text.strip():
            return False, "Command text cannot be empty"
        
        existing = SystemCommandsController.get_user_defined_commands()
        
        if command_name.lower() not in existing:
            return False, f"Command '{command_name}' not found"
        
        # Update command
        existing[command_name.lower()]['command'] = command_text.strip()
        existing[command_name.lower()]['description'] = description.strip()
        existing[command_name.lower()]['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        success, message = SystemCommandsController.save_user_commands(existing)
        if success:
            return True, f"Command '{command_name}' updated successfully"
        return False, message
    
    @staticmethod
    def delete_command(command_name):
        """
        Delete a user-defined command
        
        Args:
            command_name: Name of command to delete
            
        Returns:
            tuple: (success: bool, message: str)
        """
        existing = SystemCommandsController.get_user_defined_commands()
        
        if command_name.lower() not in existing:
            return False, f"Command '{command_name}' not found"
        
        del existing[command_name.lower()]
        
        success, message = SystemCommandsController.save_user_commands(existing)
        if success:
            return True, f"Command '{command_name}' deleted successfully"
        return False, message

    @staticmethod
    def get_all_submissions():
        """
        Get all system command submissions (approved, pending, rejected)
        
        Returns:
            dict: Dictionary with 'approved', 'pending', and 'rejected' submissions
        """
        if not os.path.exists(SYSTEM_COMMANDS_SUBMISSIONS_FILE):
            return {
                'approved': {},
                'pending': {},
                'rejected': []
            }
        
        try:
            with open(SYSTEM_COMMANDS_SUBMISSIONS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                'approved': {},
                'pending': {},
                'rejected': []
            }
    
    @staticmethod
    def save_submissions(submissions):
        """
        Save submissions to file
        
        Args:
            submissions: Dictionary of submissions
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with open(SYSTEM_COMMANDS_SUBMISSIONS_FILE, 'w') as f:
                json.dump(submissions, f, indent=2)
            return True, "Submissions saved successfully"
        except Exception as e:
            return False, f"Error saving submissions: {str(e)}"
    
    @staticmethod
    def submit_command(command_name, command_text, description="", submitted_by="", is_admin=False):
        """
        Submit a new system command for approval
        
        Args:
            command_name: Name/identifier for the command
            command_text: The actual shell command
            description: Optional description
            submitted_by: User who submitted
            is_admin: Whether the submitter is an admin
            
        Returns:
            tuple: (success: bool, message: str, submission_id or None)
        """
        # Validate inputs
        if not command_name or not command_name.strip():
            return False, "Command name cannot be empty", None
        
        if not command_text or not command_text.strip():
            return False, "Command text cannot be empty", None
        
        # Check for invalid characters in name
        if not command_name.replace('_', '').isalnum():
            return False, "Command name can only contain alphanumeric characters and underscores", None
        
        submissions = SystemCommandsController.get_all_submissions()
        
        # Check if command name already exists in approved submissions
        if command_name.lower() in submissions['approved']:
            return False, f"Command '{command_name}' already exists in approved commands", None
        
        # Check if command conflicts with builtin commands
        builtin = SystemCommandsController.get_builtin_commands()
        if command_name.lower() in builtin:
            return False, f"Command name '{command_name}' conflicts with builtin command", None
        
        submission_id = str(uuid.uuid4())
        submission = {
            'id': submission_id,
            'command_name': command_name.lower(),
            'command': command_text.strip(),
            'description': description.strip(),
            'submitted_by': submitted_by or 'unknown',
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'is_admin_submission': is_admin
        }
        
        if is_admin:
            # Admin submissions are automatically approved
            submissions['approved'][command_name.lower()] = submission
        else:
            # Non-admin submissions go to pending
            submissions['pending'][submission_id] = submission
        
        success, message = SystemCommandsController.save_submissions(submissions)
        if success:
            if is_admin:
                return True, f"Command '{command_name}' approved and added successfully", submission_id
            else:
                return True, f"Command '{command_name}' submitted for approval", submission_id
        return False, message, None
    
    @staticmethod
    def get_pending_submissions():
        """Get all pending submissions awaiting admin approval"""
        submissions = SystemCommandsController.get_all_submissions()
        return submissions.get('pending', {})
    
    @staticmethod
    def get_approved_commands():
        """Get all approved system commands"""
        submissions = SystemCommandsController.get_all_submissions()
        return submissions.get('approved', {})
    
    @staticmethod
    def approve_submission(submission_id):
        """
        Approve a pending submission (admin only)
        
        Args:
            submission_id: ID of the submission to approve
            
        Returns:
            tuple: (success: bool, message: str)
        """
        submissions = SystemCommandsController.get_all_submissions()
        pending = submissions.get('pending', {})
        
        if submission_id not in pending:
            return False, f"Submission '{submission_id}' not found in pending"
        
        submission = pending[submission_id]
        command_name = submission['command_name']
        
        # Check if command name already exists in approved
        if command_name in submissions['approved']:
            return False, f"Command '{command_name}' already exists in approved commands"
        
        # Move to approved
        submissions['approved'][command_name] = submission
        submissions['approved'][command_name]['approved_at'] = datetime.now(timezone.utc).isoformat()
        del submissions['pending'][submission_id]
        
        success, message = SystemCommandsController.save_submissions(submissions)
        if success:
            return True, f"Command '{command_name}' approved successfully"
        return False, message
    
    @staticmethod
    def reject_submission(submission_id, rejection_reason=""):
        """
        Reject a pending submission (admin only)
        
        Args:
            submission_id: ID of the submission to reject
            rejection_reason: Reason for rejection
            
        Returns:
            tuple: (success: bool, message: str)
        """
        submissions = SystemCommandsController.get_all_submissions()
        pending = submissions.get('pending', {})
        
        if submission_id not in pending:
            return False, f"Submission '{submission_id}' not found in pending"
        
        submission = pending[submission_id]
        command_name = submission['command_name']
        
        # Add to rejected list
        rejected_entry = {
            'submission_id': submission_id,
            'command_name': command_name,
            'command': submission.get('command'),
            'submitted_by': submission.get('submitted_by'),
            'submitted_at': submission.get('submitted_at'),
            'rejected_at': datetime.now(timezone.utc).isoformat(),
            'rejection_reason': rejection_reason or 'No reason provided'
        }
        
        submissions['rejected'].append(rejected_entry)
        del submissions['pending'][submission_id]
        
        success, message = SystemCommandsController.save_submissions(submissions)
        if success:
            return True, f"Command '{command_name}' rejected successfully"
        return False, message
    
    @staticmethod
    def promote_to_config(command_name):
        """
        Promote an approved command to the config file (make it builtin)
        
        Args:
            command_name: Name of the command to promote
            
        Returns:
            tuple: (success: bool, message: str)
        """
        submissions = SystemCommandsController.get_all_submissions()
        approved = submissions.get('approved', {})
        
        if command_name.lower() not in approved:
            return False, f"Command '{command_name}' not found in approved commands"
        
        command_data = approved[command_name.lower()]
        
        # Read the config file
        try:
            with open('config_log_patterns.py', 'r') as f:
                config_content = f.read()
            
            # Generate the new system command variable
            var_name = f"system_command_{command_name.lower()}"
            command_text = command_data.get('command', '')
            description = command_data.get('description', '')
            
            # Create the new line to add to config
            new_line = f'{var_name} = "{command_text}"'
            
            # Find where to insert (before the get_system_commands function)
            insert_marker = "def get_system_commands():"
            
            if insert_marker in config_content:
                # Insert the new command before the function definition
                config_content = config_content.replace(
                    insert_marker,
                    f'{new_line}\n\n\n{insert_marker}'
                )
                
                # Write back to config
                with open('config_log_patterns.py', 'w') as f:
                    f.write(config_content)
                
                # Mark as promoted in submissions
                command_data['promoted_to_config'] = True
                command_data['promoted_at'] = datetime.now(timezone.utc).isoformat()
                
                success, message = SystemCommandsController.save_submissions(submissions)
                if success:
                    return True, f"Command '{command_name}' promoted to config successfully"
                return False, "Command promoted but failed to update submissions"
            else:
                return False, "Could not find insertion point in config file"
                
        except Exception as e:
            return False, f"Error promoting command to config: {str(e)}"
    
    @staticmethod
    def get_all_optional_checks():
        """
        Dynamically discover all optional checks from approved commands.
        Returns a dictionary of available checks with their commands and descriptions.
        This combines builtin and approved user commands.
        """
        builtin = SystemCommandsController.get_builtin_commands()
        approved = SystemCommandsController.get_approved_commands()
        
        # Convert approved commands to the same format
        approved_checks = {}
        for name, cmd_data in approved.items():
            approved_checks[name] = {
                'command': cmd_data.get('command'),
                'description': cmd_data.get('description'),
                'submitted_by': cmd_data.get('submitted_by')
            }
        
        # Merge them (approved take precedence)
        all_checks = {**builtin, **approved_checks}
        return all_checks

