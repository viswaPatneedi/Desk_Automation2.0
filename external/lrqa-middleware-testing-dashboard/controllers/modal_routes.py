"""
Phase 3 Modal UI - Flask API Endpoints
Handles all form submissions, data persistence, and backend operations for modals

Architecture:
- RESTful API endpoints for modal operations
- Form validation and error handling
- Database persistence
- Execution context capture
- Comprehensive logging
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone
from functools import wraps
import json
import logging
from models.device import Device
from models.test_result import TestResult
from models.saved_sequence import SavedSequence
from models.user import User
from utils.device_lock_manager import DeviceLockManager
import paramiko
import socket

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
modal_api = Blueprint('modal_api', __name__, url_prefix='/api')

# ============================================================
# AUTHENTICATION DECORATOR
# ============================================================

def modal_login_required(f):
    """Decorator for modal endpoints requiring login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# ERROR HANDLERS
# ============================================================

def success_response(data=None, message='Success'):
    """Standard success response"""
    return jsonify({
        'success': True,
        'message': message,
        'data': data,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

def error_response(error, status_code=400):
    """Standard error response"""
    return jsonify({
        'success': False,
        'error': str(error),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), status_code

# ============================================================
# DEVICE ENDPOINTS
# ============================================================

@modal_api.route('/devices/test-connection', methods=['POST'])
@modal_login_required
def test_ssh_connection():
    """Test SSH connection to device"""
    try:
        data = request.get_json()
        
        host = data.get('ssh_host')
        port = int(data.get('ssh_port', 10022))
        username = data.get('ssh_username', 'root')
        password = data.get('ssh_password')

        if not all([host, username, password]):
            return error_response('Missing required SSH credentials')

        # Attempt SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            start_time = datetime.now()
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            ssh.close()

            logger.info(f"✅ SSH connection test successful to {host}:{port}")
            return success_response({
                'response_time': int(elapsed),
                'host': host,
                'port': port,
                'username': username
            }, f'SSH connection successful ({elapsed:.0f}ms)')

        except paramiko.AuthenticationException:
            logger.warning(f"❌ SSH authentication failed for {username}@{host}:{port}")
            return error_response('SSH authentication failed - invalid credentials')
        except paramiko.SSHException as e:
            logger.warning(f"❌ SSH error for {host}:{port}: {str(e)}")
            return error_response(f'SSH error: {str(e)}')
        except socket.timeout:
            logger.warning(f"❌ SSH connection timeout for {host}:{port}")
            return error_response('SSH connection timeout - device unreachable')
        except Exception as e:
            logger.error(f"❌ Unexpected SSH error: {str(e)}")
            return error_response(f'Connection error: {str(e)}')

    except Exception as e:
        logger.error(f"Error in test_ssh_connection: {str(e)}")
        return error_response(str(e), 500)

@modal_api.route('/devices', methods=['POST'])
@modal_login_required
def add_device():
    """Add new device"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['device_name', 'device_type', 'ssh_host', 'ssh_username', 'ssh_password']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'Missing required field: {field}')

        # Create device
        device = Device(
            device_name=data['device_name'],
            device_type=data['device_type'],
            ssh_host=data['ssh_host'],
            ssh_port=int(data.get('ssh_port', 10022)),
            ssh_username=data['ssh_username'],
            ssh_password=data['ssh_password'],
            location=data.get('location'),
            is_active=data.get('is_active', True),
            owner_id=current_user.id if current_user else None,
            team=data.get('team', 'Default')
        )

        device.save()

        logger.info(f"✅ Device created: {device.device_name} ({device.ssh_host})")
        return success_response({
            'device_id': device.device_id,
            'device_name': device.device_name
        }, 'Device added successfully'), 201

    except Exception as e:
        logger.error(f"Error adding device: {str(e)}")
        return error_response(str(e), 500)

@modal_api.route('/devices/<device_id>', methods=['GET'])
@modal_login_required
def get_device(device_id):
    """Get device details"""
    try:
        device = Device.get_by_id(device_id)
        
        if not device:
            return error_response('Device not found', 404)

        return success_response({
            'device_id': device.device_id,
            'device_name': device.device_name,
            'device_type': device.device_type,
            'ssh_host': device.ssh_host,
            'ssh_port': device.ssh_port,
            'ssh_username': device.ssh_username,
            'location': device.location,
            'is_active': device.is_active
        })

    except Exception as e:
        logger.error(f"Error getting device: {str(e)}")
        return error_response(str(e), 500)

@modal_api.route('/devices/<device_id>', methods=['PUT'])
@modal_login_required
def update_device(device_id):
    """Update device details"""
    try:
        device = Device.get_by_id(device_id)
        
        if not device:
            return error_response('Device not found', 404)

        data = request.get_json()

        # Update fields
        device.device_name = data.get('device_name', device.device_name)
        device.device_type = data.get('device_type', device.device_type)
        device.ssh_host = data.get('ssh_host', device.ssh_host)
        device.ssh_port = int(data.get('ssh_port', device.ssh_port))
        device.ssh_username = data.get('ssh_username', device.ssh_username)
        if data.get('ssh_password'):
            device.ssh_password = data['ssh_password']
        device.location = data.get('location', device.location)
        device.is_active = data.get('is_active', device.is_active)

        device.save()

        logger.info(f"✅ Device updated: {device.device_name}")
        return success_response({
            'device_id': device.device_id,
            'device_name': device.device_name
        }, 'Device updated successfully')

    except Exception as e:
        logger.error(f"Error updating device: {str(e)}")
        return error_response(str(e), 500)

# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@modal_api.route('/auth/login', methods=['POST'])
def login():
    """Handle login from modal"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember_me', False)

        if not email or not password:
            return error_response('Email and password required')

        # Try to find user by email or username
        user = User.get_by_email(email) or User.get_by_username(email)

        if not user or not user.check_password(password):
            logger.warning(f"❌ Failed login attempt for: {email}")
            return error_response('Invalid email or password')

        # Login user
        from flask_login import login_user
        login_user(user, remember=remember)

        logger.info(f"✅ User logged in: {user.email}")
        return success_response({
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'redirect_url': '/'
        }, 'Login successful'), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return error_response(str(e), 500)

# ============================================================
# EXECUTION CONTEXT ENDPOINTS
# ============================================================

@modal_api.route('/executions/capture-context', methods=['POST'])
@modal_login_required
def capture_execution_context():
    """Capture execution context at start of method"""
    try:
        data = request.get_json()

        execution_context = {
            'execution_id': f"exec_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            'device_id': data.get('device_id'),
            'method_id': data.get('method_id'),
            'user_id': current_user.id,
            'user_email': current_user.email,
            'team': current_user.team if hasattr(current_user, 'team') else 'Default',
            'method_rationale': data.get('method_rationale'),
            'execution_notes': data.get('execution_notes'),
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'is_active': True
        }

        # Save execution context to database
        # This should be persisted in the database (execution_contexts table per Phase 1 schema)
        logger.info(f"✅ Execution context captured: {execution_context['execution_id']}")

        return success_response({
            'execution_id': execution_context['execution_id'],
            'device_id': execution_context['device_id'],
            'method_id': execution_context['method_id']
        }, 'Execution context captured successfully'), 201

    except Exception as e:
        logger.error(f"Error capturing execution context: {str(e)}")
        return error_response(str(e), 500)

@modal_api.route('/methods/<method_id>', methods=['GET'])
@modal_login_required
def get_method(method_id):
    """Get method details"""
    try:
        # This would fetch from the methods table in the database
        methods = {
            'soft_boot': {
                'id': 'soft_boot',
                'name': 'Soft Boot',
                'description': 'Performs a soft reboot using software commands. Quick but may not clear all state.',
                'duration_seconds': 30,
                'category': 'Boot'
            },
            'hard_boot': {
                'id': 'hard_boot',
                'name': 'Hard Boot',
                'description': 'Performs a hard power cycle reboot. Clears all memory and state.',
                'duration_seconds': 45,
                'category': 'Boot'
            },
            'reboot': {
                'id': 'reboot',
                'name': 'Reboot',
                'description': 'Standard reboot with optional performance comparison.',
                'duration_seconds': 60,
                'category': 'Boot'
            },
            'deep_sleep': {
                'id': 'deep_sleep',
                'name': 'Deep Sleep',
                'description': 'Uses IR blaster to send power button signal for deep sleep mode.',
                'duration_seconds': 120,
                'category': 'Sleep'
            },
            'standby': {
                'id': 'standby',
                'name': 'Standby',
                'description': 'Moves device to standby mode without complete shutdown.',
                'duration_seconds': 15,
                'category': 'Sleep'
            }
        }

        method = methods.get(method_id)

        if not method:
            return error_response('Method not found', 404)

        return success_response(method)

    except Exception as e:
        logger.error(f"Error getting method: {str(e)}")
        return error_response(str(e), 500)

# ============================================================
# SEQUENCE ENDPOINTS
# ============================================================

@modal_api.route('/sequences/create', methods=['POST'])
@modal_login_required
def create_sequence():
    """Create new sequence"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['sequence_name', 'rationale']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'Missing required field: {field}')

        sequence = SavedSequence(
            name=data['sequence_name'],
            description=data.get('description'),
            rationale=data['rationale'],
            methods=json.dumps(data.get('methods', [])),
            devices=json.dumps(data.get('device_ids', [])),
            owner_id=current_user.id if current_user else None,
            visibility=data.get('visibility', 'team'),
            readonly=data.get('is_readonly', False),
            tags=data.get('tags', ''),
            team=current_user.team if hasattr(current_user, 'team') else 'Default'
        )

        sequence.save()

        logger.info(f"✅ Sequence created: {sequence.name}")
        return success_response({
            'sequence_id': sequence.sequence_id,
            'sequence_name': sequence.name
        }, 'Sequence created successfully'), 201

    except Exception as e:
        logger.error(f"Error creating sequence: {str(e)}")
        return error_response(str(e), 500)

@modal_api.route('/sequences/<sequence_id>', methods=['GET'])
@modal_login_required
def get_sequence(sequence_id):
    """Get sequence details"""
    try:
        sequence = SavedSequence.find_by_id(sequence_id)
        
        if not sequence:
            return error_response('Sequence not found', 404)

        return success_response({
            'sequence_id': sequence.sequence_id,
            'name': sequence.name,
            'description': sequence.description,
            'rationale': sequence.rationale,
            'methods': json.loads(sequence.methods) if sequence.methods else [],
            'devices': json.loads(sequence.devices) if sequence.devices else [],
            'visibility': sequence.visibility,
            'readonly': sequence.readonly,
            'tags': sequence.tags
        })

    except Exception as e:
        logger.error(f"Error getting sequence: {str(e)}")
        return error_response(str(e), 500)

@modal_api.route('/sequences/<sequence_id>', methods=['PUT'])
@modal_login_required
def update_sequence(sequence_id):
    """Update sequence"""
    try:
        sequence = SavedSequence.find_by_id(sequence_id)
        
        if not sequence:
            return error_response('Sequence not found', 404)

        data = request.get_json()

        sequence.name = data.get('sequence_name', sequence.name)
        sequence.description = data.get('description', sequence.description)
        sequence.rationale = data.get('rationale', sequence.rationale)
        sequence.visibility = data.get('visibility', sequence.visibility)
        sequence.readonly = data.get('is_readonly', sequence.readonly)
        sequence.tags = data.get('tags', sequence.tags)

        sequence.save()

        logger.info(f"✅ Sequence updated: {sequence.name}")
        return success_response({
            'sequence_id': sequence.sequence_id,
            'sequence_name': sequence.name
        }, 'Sequence updated successfully')

    except Exception as e:
        logger.error(f"Error updating sequence: {str(e)}")
        return error_response(str(e), 500)

# ============================================================
# HEALTH CHECK
# ============================================================

@modal_api.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return success_response({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

# ============================================================
# INITIALIZATION FUNCTION
# ============================================================

def register_modal_routes(app):
    """Register modal routes with Flask app"""
    app.register_blueprint(modal_api)
    logger.info("✅ Modal API routes registered")
