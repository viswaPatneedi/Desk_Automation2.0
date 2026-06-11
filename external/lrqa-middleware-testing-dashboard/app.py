#!/usr/bin/env python3
"""
Flask Application - MVC Architecture
Main application entry point following Model-View-Controller pattern

Architecture:
- Models: Data layer (models/device.py, models/test_result.py)
- Views: Presentation layer (templates/*.html)
- Controllers: Request handlers (controllers/*.py)
- Services: Business logic (services/*.py)
"""

from flask import Flask, render_template, request, jsonify, Response, send_from_directory, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import logging
import warnings
import os
import sys
import json
import signal
import atexit
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

# Suppress Paramiko verbose logging
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=ResourceWarning)

# Import Models
from models.device import Device
from models.test_result import TestResult
from models.saved_sequence import SavedSequence
from models.user import User
from models.job import Job
from models.device_lock import DeviceLock

# Import Utilities
from utils.device_lock_manager import DeviceLockManager
from utils.file_lock import FileLockManager

# Import USB Storage Manager
try:
    from scripts.data_processing.usb_storage_manager import initialize_storage
    storage_manager = initialize_storage(enable_setup=True)
except Exception as e:
    print(f"⚠️  USB Storage Manager initialization warning: {e}")
    storage_manager = None

# Import Services
from services.test_execution_service import TestExecutionService
from services.log_service import LogService
from services.queue_service import QueueService
from services.recovery_service import RecoveryService
from services.execution_monitor_service import ExecutionMonitorService
from services.periodic_data_sync_service import PeriodicDataSyncService

# Import Controllers
from controllers.device_controller import DeviceController
from controllers.test_controller import TestController
from controllers.queue_controller import QueueController
from controllers.results_controller import ResultsController

# Import AI Agent Routes
from controllers.agents_routes import register_agents_blueprint

# Import Phase 3 Modal Routes
from controllers.modal_routes import register_modal_routes
from utils.modal_integration import inject_modal_assets

# Import configuration files
from config.config_commands import *
from config.config_ir_blaster import *
from config.config_eta import calculate_eta, format_eta
from config.config_deployment import print_deployment_info
import config.config_email  # Loads Gmail SMTP settings from .env

# Initialize Flask app
app = Flask(__name__)

# ===== DATABASE CONFIGURATION =====
from config.flask_database import DatabaseConfig, init_database_for_flask
db_config = DatabaseConfig()
init_database_for_flask(app, db_config)
print("✓ Database initialized for Flask")
# ===== END DATABASE CONFIGURATION =====

app.secret_key = os.environ.get('SECRET_KEY', 'rdke-qa-dashboard-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True if using HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Reload templates on file changes
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching

# ===== AI SCREEN ANALYZER INITIALIZATION =====
# Set ANTHROPIC_API_KEY from environment variables if available
# Priority order: ANTROPIC_API_KEY env var → config file → fallback to None
ai_api_key = os.environ.get('ANTHROPIC_API_KEY')
if not ai_api_key:
    try:
        # Try to load from config file
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('ANTHROPIC_API_KEY'):
                    key_value = line.split('=', 1)[1].strip().strip("'\"")
                    os.environ['ANTHROPIC_API_KEY'] = key_value
                    ai_api_key = key_value
                    print(f"✓ Loaded ANTHROPIC_API_KEY from .env file")
                    break
    except:
        pass

if ai_api_key:
    print(f"✓ AI Screen Analyzer: ANTHROPIC_API_KEY is configured (key: {ai_api_key[:10]}...)")
else:
    print("⚠ AI Screen Analyzer: ANTHROPIC_API_KEY not found - AI validation will return 'Unknown'")
    print("  To enable AI features, set: export ANTHROPIC_API_KEY='sk-ant-xxxxx'")
    print("  Get key from: https://console.anthropic.com/account/keys")
# ===== END AI INITIALIZATION =====

# Set the server name for hostname-based access
#app.config['SERVER_NAME'] = 'lrqa-middleware:11078'
# app.config['SERVER_NAME'] = '10.0.0.123:11078'  # Not required for external access, only for URL generation

# Add cache-busting headers to prevent browser caching
@app.after_request
def add_cache_headers(response):
    """Add cache-busting headers to prevent stale content"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.before_request
def enforce_api_authentication():
    """Require authenticated app users for all API access except explicit public auth probe."""
    public_api_paths = {
        '/api/auth/status',
    }

    if request.path.startswith('/api/') and request.path not in public_api_paths:
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Login required to access application data'
            }), 401

# Endpoint to get available methods for UI (moved here to ensure 'app' is defined)
@app.route('/api/available_methods', methods=['GET'])
@login_required
def get_available_methods():
    try:
        from models.database import Session, Method as DBMethod

        session = Session()
        try:
            method_rows = (
                session.query(DBMethod)
                .filter_by(is_active=True)
                .order_by(DBMethod.name.asc())
                .all()
            )

            methods = [row.method_id for row in method_rows if row.method_id]
            if methods:
                return jsonify({'methods': methods, 'source': 'database'})
        finally:
            session.close()
    except Exception as e:
        app.logger.warning(f"Falling back to config methods: {e}")

    from config_commands import AVAILABLE_METHODS
    return jsonify({'methods': AVAILABLE_METHODS, 'source': 'config'})

@app.route('/api/available_log_patterns', methods=['GET'])
@login_required
def get_available_log_patterns():
    """Returns available log patterns for method parameter selection."""
    try:
        import json
        from config_paths import LOG_PATTERNS_FILE
        with open(LOG_PATTERNS_FILE, 'r') as f:
            data = json.load(f)
            log_patterns = data.get('LOG_PATTERNS', {})
            
            # Format patterns for UI display
            patterns_list = []
            for pattern_key, pattern_info in log_patterns.items():
                patterns_list.append({
                    'id': pattern_key,
                    'name': pattern_key.replace('_', ' ').title(),
                    'description': pattern_info.get('description', ''),
                    'file_path': pattern_info.get('file_path', '')
                })
            
            return jsonify({
                'success': True,
                'patterns': patterns_list
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/available_ir_remotes', methods=['GET'])
@login_required
def get_available_ir_remotes():
    """Returns available IR remote types from ir_keycodes.json for method parameter selection."""
    try:
        import json
        import os
        
        # Try multiple possible paths for ir_keycodes.json
        possible_paths = [
            'Json/ir_keycodes.json',
            'json/ir_keycodes.json',
            'ir_keycodes.json'
        ]
        
        ir_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                ir_file_path = path
                break
        
        if not ir_file_path:
            return jsonify({
                'success': False,
                'error': 'ir_keycodes.json not found'
            }), 404
        
        with open(ir_file_path, 'r') as f:
            data = json.load(f)
            remotes = data.get('remotes', {})
            
            # Format remotes for UI display
            remotes_list = []
            for remote_key, remote_info in remotes.items():
                device_info = remote_info.get('device_info', {})
                remotes_list.append({
                    'id': remote_key,
                    'name': remote_key,
                    'display_name': f"{remote_key} - {device_info.get('remote_model', remote_key)}",
                    'manufacturer': device_info.get('manufacturer', ''),
                    'description': f"{device_info.get('manufacturer', '')} {device_info.get('remote_model', '')}"
                })
            
            return jsonify({
                'success': True,
                'remotes': remotes_list
            })
    except Exception as e:
        print(f"Error fetching IR remotes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the dashboard.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.get_user_by_id(user_id)

# Initialize Services (Business Logic Layer)
# Recovery is ENABLED for automatic job resumption on app restart
RECOVERY_ENABLED = True
recovery_service = RecoveryService() if RECOVERY_ENABLED else None
test_execution_service = TestExecutionService(recovery_service)
log_service = LogService()
queue_service = QueueService(test_execution_service, recovery_service)
periodic_sync_service = PeriodicDataSyncService(interval_seconds=1800)

# Print deployment configuration
print_deployment_info()

# Check and initialize Email Service
print("\n" + "="*60)
print("EMAIL SERVICE INITIALIZATION")
print("="*60)
try:
    from services.email_service import EmailService
    email_service = EmailService()
    if email_service.enabled:
        print(f"✅ Email Service: ENABLED")
        print(f"   SMTP Server: {email_service.smtp_server}:{email_service.smtp_port}")
        print(f"   Sender Email: {email_service.sender_email}")
        print(f"   → Automatic email notifications will be sent after test executions")
    else:
        print(f"⚠️  Email Service: DISABLED")
        print(f"   Reason: Gmail SMTP not configured (missing SENDER_EMAIL or SENDER_PASSWORD)")
        print(f"   → To enable Gmail SMTP (requires app password):")
        print(f"      export SMTP_SERVER='smtp.gmail.com'")
        print(f"      export SMTP_PORT='587'")
        print(f"      export SENDER_EMAIL='your_gmail@gmail.com'")
        print(f"      export SENDER_PASSWORD='your_app_password'")
except Exception as e:
    print(f"⚠️  Email Service: ERROR - {e}")
print("="*60 + "\n")

# Initialize Execution Monitor Service (disabled when recovery is off)
execution_monitor_service = None
if RECOVERY_ENABLED:
    print("\n" + "="*60)
    print("EXECUTION MONITOR SERVICE INITIALIZATION")
    print("="*60)
    try:
        execution_monitor_service = ExecutionMonitorService(
            email_service=email_service if 'email_service' in locals() else None,
            test_execution_service=test_execution_service,
            queue_service=queue_service
        )
        print("✅ Execution Monitor Service: INITIALIZED")
        print("   → Will monitor running executions for stuck state")
        print("   → Auto-recovery for device reachable issues")
        print("   → Email notifications for completion/failure")
    except Exception as e:
        print(f"⚠️  Execution Monitor Service: ERROR - {e}")
        execution_monitor_service = None
    print("="*60 + "\n")

    # Initialize recovery on startup
    recovery_service.initialize()

# Start queue processor to handle any pending jobs
queue_service.start_processor()
print("[QUEUE] Queue processor started")

# Cleanup old jobs at startup (keep last 60 days)
Job.cleanup_old_pending_jobs(days=7)
Job.cleanup_old_completed_jobs(keep_days=60)
print("[QUEUE] Cleanup completed - keeping last 60 days of job history")

# Start Execution Monitor Service
if execution_monitor_service:
    execution_monitor_service.start_monitoring()
    print("[EXECUTION MONITOR] Monitoring thread started")

# Start periodic DB->JSON sync monitor (every 30 minutes)
periodic_sync_service.start_monitoring()
print("[SYNC MONITOR] Periodic DB->JSON sync started (every 30 minutes)")

# ===== AI AGENTS FRAMEWORK REGISTRATION =====
print("\n" + "="*60)
print("AI AGENTS FRAMEWORK INITIALIZATION")
print("="*60)
try:
    # Register agents blueprint for REST API endpoints
    register_agents_blueprint(app)
    print("✅ AI Agents Framework: REGISTERED")
    print("   → Available endpoints: /api/agents/*")
    print("   → Health check: /api/agents/health")
    print("   → Manager endpoints: /api/agents/orchestrator/*")
    print("   → Job management: /api/agents/job-orchestrator/*")
except Exception as e:
    print(f"⚠️  AI Agents Framework: Registration error - {e}")
    import traceback
    traceback.print_exc()
print("="*60 + "\n")

# ===== PHASE 3 MODAL UI SYSTEM REGISTRATION =====
print("\n" + "="*60)
print("PHASE 3 MODAL UI SYSTEM INITIALIZATION")
print("="*60)
try:
    # Register modal API routes
    register_modal_routes(app)
    print("✅ Phase 3 Modal UI: REGISTERED")
    print("   → Device management endpoints: /api/devices/*")
    print("   → Authentication endpoints: /api/auth/*")
    print("   → Execution endpoints: /api/executions/*")
    print("   → Sequence endpoints: /api/sequences/*")
    print("   → Methods endpoints: /api/methods/*")
    
    # Inject modal assets into template context
    inject_modal_assets(app)
    print("✅ Modal assets injected into Flask context")
    print("   → CSS files: /static/css/modals.css")
    print("   → JS files: /static/js/modal-handlers.js")
except Exception as e:
    print(f"⚠️  Phase 3 Modal UI: Initialization error - {e}")
    import traceback
    traceback.print_exc()
print("="*60 + "\n")

# Note: DO NOT cancel pending jobs at startup
# They may be legitimately queued from another process or recent creation
# The cleanup_old_pending_jobs() above already handles truly stale jobs (>2 days)

# Graceful shutdown handlers
def shutdown_handler(signum=None, frame=None):
    """Handle graceful shutdown"""
    print("\n🛑 Shutting down gracefully...")
    if periodic_sync_service:
        periodic_sync_service.stop_monitoring()
    if execution_monitor_service:
        execution_monitor_service.stop_monitoring()
    if recovery_service:
        recovery_service.mark_crash(is_actual_crash=False)  # Save state, but not a crash
    if signum:  # Only exit if called by signal
        sys.exit(0)

def cleanup_handler():
    """Cleanup handler for atexit"""
    if periodic_sync_service:
        periodic_sync_service.stop_monitoring()
    if execution_monitor_service:
        execution_monitor_service.stop_monitoring()
    if recovery_service:
        recovery_service.mark_crash(is_actual_crash=False)  # Save state, but not a crash

# Register signal handlers only in main thread
import threading
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    atexit.register(cleanup_handler)

# Initialize Controllers (Request Handlers)
test_controller = TestController(test_execution_service, log_service)
queue_controller = QueueController(queue_service)
results_controller = ResultsController(test_execution_service, log_service)

# Make services available globally for backward compatibility
log_queue = log_service.log_queue
current_log_handle = None
REALTIME_LOG_FILE = log_service.REALTIME_LOG_FILE

def log_message(message, write_to_file=True):
    """Global log message function for backward compatibility"""
    log_service.log(message, write_to_file)

def add_html_result(iteration, phase, status, details, screenshots="", logs="", device_ip=None, method=None, job_id=None):
    """Global add result function for backward compatibility"""
    test_execution_service.add_result(iteration, phase, status, details, screenshots, logs, device_ip, method, job_id)

# =============================================================================
# ROUTES - View Layer (Presentation)
# =============================================================================

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        if not identifier or not password:
            return render_template('login.html', error='Please provide both NTID/Email and password')
        
        user = User.authenticate(identifier, password)
        
        if user:
            login_user(user, remember=remember)
            if remember:
                session.permanent = True
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            return render_template('login.html', error='Invalid NTID/Email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        ntid = request.form.get('ntid', '').strip()
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        team_name = request.form.get('team_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([ntid, email, name, team_name, password, confirm_password]):
            return render_template('register.html', error='All fields are required')
        
        # Allow only @comcast.com or @cable.comcast.com emails
        if not (email.endswith('@comcast.com') or email.endswith('@cable.comcast.com')):
            return render_template('register.html', error='Please use a valid Comcast email address (@comcast.com or @cable.comcast.com)')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters long')
        
        # Create user with team_name
        user, error = User.create_user(ntid, email, name, password, team_name=team_name)
        
        if error:
            return render_template('register.html', error=error)
        
        # Auto-login after registration
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/auth/status')
def auth_status():
    """Check authentication status - Returns JSON regardless of auth state"""
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None,
        'username': current_user.name if current_user.is_authenticated else None,
        'login_url': url_for('login')
    })

# Password Reset - File-based storage for reset codes (works with multiple Gunicorn workers)
# Structure: {ntid: {'code': '123456', 'email': 'user@comcast.com', 'expires': 'ISO8601_timestamp'}}
RESET_CODES_FILE = 'reset_codes.json'

def load_reset_codes():
    """Load reset codes from file"""
    if not os.path.exists(RESET_CODES_FILE):
        return {}
    try:
        with open(RESET_CODES_FILE, 'r') as f:
            codes = json.load(f)
            # Clean up expired codes (but don't save during load to avoid recursion)
            current_time = datetime.now()
            valid_codes = {}
            for ntid, data in codes.items():
                try:
                    expires = datetime.fromisoformat(data['expires'])
                    if current_time < expires:
                        valid_codes[ntid] = data
                except (ValueError, KeyError):
                    continue
            return valid_codes
    except (json.JSONDecodeError, IOError, ValueError) as e:
        print(f"Error loading reset codes: {e}")
        return {}

def save_reset_codes(codes):
    """Save reset codes to file"""
    try:
        # Write to file directly (no temp file to avoid gevent issues)
        with open(RESET_CODES_FILE, 'w') as f:
            json.dump(codes, f, indent=2)
        print(f"✓ Saved {len(codes)} reset codes to {RESET_CODES_FILE}")
    except IOError as e:
        print(f"✗ Error saving reset codes: {e}")

def add_reset_code(ntid, code, email, expires):
    """Add a reset code to storage"""
    codes = load_reset_codes()
    codes[ntid] = {
        'code': code,
        'email': email,
        'expires': expires.isoformat()
    }
    save_reset_codes(codes)
    print(f"✓ Added reset code for {ntid}: {code} (expires: {expires.strftime('%H:%M:%S')})")

def get_reset_code(ntid):
    """Get reset code for NTID"""
    codes = load_reset_codes()
    return codes.get(ntid)

def delete_reset_code(ntid):
    """Delete reset code for NTID"""
    codes = load_reset_codes()
    if ntid in codes:
        del codes[ntid]
        save_reset_codes(codes)

def send_reset_email(email, code, name):
    """Send password reset email with 6-digit code"""
    from services.email_service import EmailService
    
    email_service = EmailService()
    success, message = email_service.send_password_reset_email(email, code, name)
    
    # For development - also log to console
    if not email_service.enabled:
        print(f"\n{'='*60}")
        print(f"PASSWORD RESET CODE FOR {email}: {code}")
        print(f"Code expires in 10 minutes")
        print(f"{'='*60}\n")
    
    return success, message

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password request"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        ntid = request.form.get('ntid', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not ntid or not email:
            return render_template('forgot_password.html', error='Please provide both NTID and email')
        
        # Validate email domain
        if not (email.endswith('@comcast.com') or email.endswith('@cable.comcast.com')):
            return render_template('forgot_password.html', 
                                 error='Please use a valid Comcast email address (@comcast.com or @cable.comcast.com)')
        
        # Verify user exists with matching NTID and email
        user = User.get_user_by_id(ntid) or User.get_user_by_ntid(ntid)
        
        if not user:
            # User doesn't exist - prompt to create account
            return render_template('forgot_password.html', 
                                 error=f'No account found with NTID "{ntid}". Please <a href="/register">create an account</a> first.')
        
        # Check if email matches either primary or alternate email
        if user.email.lower() != email and getattr(user, 'alternate_email', '').lower() != email:
            # Email doesn't match the NTID
            return render_template('forgot_password.html', 
                                 error='The email address does not match the NTID provided. Please verify your details.')
        
        # Generate 6-digit code
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store code with expiration (10 minutes) - using file-based storage
        expires = datetime.now() + timedelta(minutes=10)
        add_reset_code(ntid, code, email, expires)
        
        # Send email
        success, message = send_reset_email(email, code, user.name)
        
        if success:
            # Store email in session for verification page
            session['reset_email'] = email
            session['reset_ntid'] = ntid
            return redirect(url_for('verify_reset_code'))
        else:
            return render_template('forgot_password.html', error='Failed to send verification code. Please try again.')
    
    return render_template('forgot_password.html')

@app.route('/verify-reset-code', methods=['GET', 'POST'])
def verify_reset_code():
    """Verify the 6-digit reset code"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Check if user came from forgot-password
    if 'reset_email' not in session or 'reset_ntid' not in session:
        return redirect(url_for('forgot_password'))
    
    email = session.get('reset_email')
    ntid = session.get('reset_ntid')
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        if not code:
            return render_template('verify_code.html', email=email, error='Please enter the verification code')
        
        # Get reset code from file-based storage
        reset_data = get_reset_code(ntid)
        
        # Check if code exists
        if not reset_data:
            return render_template('verify_code.html', email=email, 
                                 error='Verification code expired or not found. Please request a new one.')
        
        # Check expiration
        expires = datetime.fromisoformat(reset_data['expires'])
        if datetime.now() > expires:
            delete_reset_code(ntid)
            return render_template('verify_code.html', email=email, 
                                 error='Verification code expired. Please request a new one.')
        
        # Verify code
        if code != reset_data['code']:
            return render_template('verify_code.html', email=email, 
                                 error='Invalid verification code. Please try again.')
        
        # Code is valid - proceed to password reset
        session['code_verified'] = True
        return redirect(url_for('reset_password'))
    
    return render_template('verify_code.html', email=email)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password after code verification"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Check if code was verified
    if not session.get('code_verified') or 'reset_ntid' not in session:
        return redirect(url_for('forgot_password'))
    
    ntid = session.get('reset_ntid')
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not new_password or not confirm_password:
            return render_template('reset_password.html', error='Please fill in all fields')
        
        if new_password != confirm_password:
            return render_template('reset_password.html', error='Passwords do not match')
        
        if len(new_password) < 8:
            return render_template('reset_password.html', error='Password must be at least 8 characters long')
        
        # Update password
        user = User.get_user_by_id(ntid)
        
        if user:
            user.set_password(new_password)
            user.save()
            
            # Clean up - delete reset code from file-based storage
            delete_reset_code(ntid)
            session.pop('reset_email', None)
            session.pop('reset_ntid', None)
            session.pop('code_verified', None)
            
            return render_template('login.html', success='Password reset successful! Please login with your new password.')
        else:
            return render_template('reset_password.html', error='User not found. Please try again.')
    
    return render_template('reset_password.html')

# Dashboard Routes
@app.route('/')
@login_required
def index():
    """Render dashboard page as landing page"""
    from models.device_lock import DeviceLock
    
    devices = Device.load_all()
    DeviceLock.cleanup_expired_locks()
    
    # Filter devices by team (unless admin)
    device_list = []
    user_team = getattr(current_user, 'team_name', None)
    is_admin = getattr(current_user, 'is_admin', False)
    
    for device in devices:
        if not is_admin and user_team and device.team_name != user_team:
            continue
        device_list.append(device.to_dict())
    
    return render_template('index.html', devices=device_list, user=current_user)

@app.route('/dashboard')
@login_required
def dashboard():
    """Render new dashboard page with 3-column layout"""
    from models.device_lock import DeviceLock
    
    devices = Device.load_all()
    DeviceLock.cleanup_expired_locks()
    
    # Filter devices by team (unless admin)
    device_list = []
    user_team = getattr(current_user, 'team_name', None)
    is_admin = getattr(current_user, 'is_admin', False)
    
    for device in devices:
        if not is_admin and user_team and device.team_name != user_team:
            continue
        device_list.append(device.to_dict())
    
    return render_template('index.html', devices=device_list, user=current_user)

@app.route('/methods-index')
@login_required
def methods_index():
    """Render methods index page - uses index2.html"""
    from models.device_lock import DeviceLock
    
    devices = Device.load_all()
    DeviceLock.cleanup_expired_locks()
    
    # Filter devices by team (unless admin)
    device_list = []
    user_team = getattr(current_user, 'team_name', None)
    is_admin = getattr(current_user, 'is_admin', False)
    
    for device in devices:
        if not is_admin and user_team and device.team_name != user_team:
            continue
        device_list.append(device.to_dict())
    
    return render_template('index2.html', devices=device_list, user=current_user)

@app.route('/results')
@login_required
def results_page():
    """Render results page"""
    return results_controller.results_page()

@app.route('/results-cards')
@login_required
def results_cards_page():
    """Render results cards page (card view)"""
    return render_template('results_cards.html', current_user=current_user)

@app.route('/reboot-perf-compare')
@login_required
def reboot_perf_compare_page():
    """Render reboot performance comparison page"""
    executions = results_controller._build_reboot_perf_executions()
    return render_template(
        'reboot_perf_compare.html',
        reboot_perf_executions=executions,
        current_user=current_user
    )

@app.route('/reboot-perf-results')
@login_required
def reboot_perf_results_page():
    """Render reboot performance results page"""
    return results_controller.reboot_perf_results_page(current_user)

# JOBS Queue Page (DEPRECATED - use Dashboard instead)
# Kept for backward compatibility - redirects to dashboard
@app.route('/jobs')
@login_required
def jobs_page():
    """Deprecated: Redirect to dashboard which shows all jobs
    The Dashboard's 'Current & Recent Executions' section displays all queued jobs
    in a better organized view with additional status information."""
    from flask import redirect, url_for
    return redirect(url_for('index'))

@app.route('/api/reboot-perf-results')
@login_required
def reboot_perf_results_api():
    """API for reboot performance results grouped by device and job"""
    return results_controller.get_reboot_perf_results()

@app.route('/tiles-results')
@login_required
def tiles_results_page():
    """Render tiles detection results page"""
    return results_controller.tiles_results_page(current_user)

@app.route('/api/tiles-results')
@login_required
def tiles_results_api():
    """API for tiles detection results grouped by device and job"""
    return results_controller.get_tiles_results()

@app.route('/soft-hard-boot-results')
@login_required
def soft_hard_boot_results_page():
    """Render soft_hard_boot results page"""
    return results_controller.soft_hard_boot_results_page(current_user)

@app.route('/api/soft-hard-boot-results')
@login_required
def soft_hard_boot_results_api():
    """API for soft_hard_boot results"""
    return results_controller.get_soft_hard_boot_results()

@app.route('/deepsleep-results')
@login_required
def deepsleep_results_page():
    """Render deepsleep results page"""
    return render_template('deepsleep_results.html')

@app.route('/download/reboot-perf-results')
@login_required
def download_reboot_perf_excel():
    """Download reboot performance results as Excel file"""
    return results_controller.download_reboot_perf_excel()

@app.route('/download/tiles-results')
@login_required
def download_tiles_excel():
    """Download tiles detection results as Excel file"""
    return results_controller.download_tiles_excel()

@app.route('/jobs/<job_id>')
@login_required
def job_details_page(job_id):
    """Render job details page"""
    try:
        job = Job.get_job(job_id)
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('index'))
        
        # Get current step from job object
        current_step = getattr(job, 'current_step', 0)
        current_iteration = getattr(job, 'current_iteration', 1)
        
        # Add timestamp for live screenshot cache busting
        from datetime import datetime
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # Build reboot performance V2 optimized and trail method summary table for this job
        reboot_perf_results = []
        reboot_perf_average = None
        try:
            all_results = [r.to_dict() for r in TestResult.load_all()]
            job_results = [r for r in all_results if r.get('job_id') == job_id and r.get('method') in ('reboot_perf_v2_optimized', 'trail_method')]
            job_results.sort(key=lambda x: x.get('iteration', 0))

            perf_values = []
            for r in job_results:
                performance_seconds = r.get('performance_seconds')
                if isinstance(performance_seconds, (int, float)):
                    perf_values.append(float(performance_seconds))

                optional_checks = r.get('optional_checks') or {}
                custom_checks = optional_checks.get('custom_checks', []) or []
                crash_checks = []
                for check in custom_checks:
                    if not check.get('pattern_found'):
                        continue
                    description = str(check.get('description', '')).lower()
                    command = str(check.get('command', '')).lower()
                    if 'crash' in description or 'crash' in command or 'segfault' in description or 'segfault' in command:
                        crash_checks.append(check)

                crash_found = len(crash_checks) > 0
                crash_details = []
                for c in crash_checks:
                    output = c.get('output', '').strip()
                    description = c.get('description', '').strip()
                    # Create detailed crash info with actual log lines if available
                    if output:
                        # Format output for display - show up to 5 lines
                        output_lines = output.split('\n')[:5]
                        crash_details.append({
                            'description': description or 'Crash pattern detected',
                            'output': output,
                            'output_lines': output_lines,
                            'line_count': len(output.split('\n'))
                        })
                    else:
                        crash_details.append({
                            'description': description or 'Crash pattern detected',
                            'output': '',
                            'output_lines': [],
                            'line_count': 0
                        })

                logs_list = []
                logs_field = r.get('logs')
                if isinstance(logs_field, list):
                    logs_list.extend([s for s in logs_field if s])
                elif isinstance(logs_field, str) and logs_field.strip():
                    logs_list.extend([s.strip() for s in logs_field.split(',') if s.strip()])

                collected_logs = optional_checks.get('collected_logs') or []
                if isinstance(collected_logs, list):
                    logs_list.extend([s for s in collected_logs if s])

                logs_collected = len(logs_list) > 0

                reboot_perf_results.append({
                    'iteration': r.get('iteration'),
                    'performance_seconds': performance_seconds,
                    'crash_found': crash_found,
                    'crash_details': crash_details,
                    'logs_collected': logs_collected,
                    'logs_list': logs_list
                })

            if perf_values:
                reboot_perf_average = sum(perf_values) / len(perf_values)
        except Exception:
            reboot_perf_results = []
            reboot_perf_average = None

        return render_template('job_details.html', 
                             job=job, 
                             current_step=current_step,
                             current_iteration=current_iteration,
                             timestamp=timestamp,
                             reboot_perf_results=reboot_perf_results,
                             reboot_perf_average=reboot_perf_average,
                             current_user=current_user)
    except Exception as e:
        flash(f'Error loading job: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/device_viewer/<device_ip>')
@login_required
def device_viewer_page(device_ip):
    """Render device live viewer page (screenshot-based)"""
    # Validate device exists
    device = Device.find_by_ip(device_ip)
    if not device:
        flash('Device not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('device_viewer.html', 
                         device_ip=device_ip,
                         current_user=current_user)

# =============================================================================
# API ROUTES - Controller Layer (Request Handlers)
# =============================================================================

# Device Management
@app.route('/api/devices', methods=['GET'])
@login_required
def get_devices():
    return DeviceController.get_devices()

@app.route('/api/devices', methods=['POST'])
@login_required
def add_device():
    return DeviceController.add_device()

@app.route('/api/devices', methods=['DELETE'])
@login_required
def delete_device():
    return DeviceController.delete_device()

@app.route('/api/devices', methods=['PUT'])
@login_required
def update_device():
    return DeviceController.update_device()

@app.route('/api/device/<device_ip>', methods=['GET'])
@login_required
def get_device(device_ip):
    """GET /api/device/<device_ip> - Get a specific device by IP"""
    from models.device import Device
    device = Device.find_by_ip(device_ip)
    if device:
        return jsonify({'success': True, 'device': device.to_dict()})
    else:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

@app.route('/api/device/<device_ip>', methods=['DELETE'])
@login_required
def delete_device_by_ip(device_ip):
    """DELETE /api/device/<device_ip> - Delete a specific device by IP"""
    from flask_login import current_user
    from models.device import Device
    
    if not getattr(current_user, 'is_admin', False):
        return jsonify({'success': False, 'message': 'Only administrators can delete devices'}), 403
    
    device = Device.find_by_ip(device_ip)
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404
    
    if Device.delete(device_ip):
        return jsonify({'success': True, 'message': 'Device deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Error deleting device'}), 500

@app.route('/api/device/<device_ip>', methods=['PUT'])
@login_required
def update_device_by_ip(device_ip):
    """PUT /api/device/<device_ip> - Update a specific device by IP"""
    from models.device import Device
    
    data = request.json
    # Add old_ip to the request data for the controller
    data['old_ip'] = device_ip
    
    # Temporarily set request.json to updated data
    from flask import request as flask_request
    original_json = flask_request.get_json
    flask_request.get_json = lambda: data
    
    result = DeviceController.update_device()
    
    # Restore original method
    flask_request.get_json = original_json
    
    if result.status_code == 200 or result.status_code == 201:
        # Extract the response data
        response_data = result.get_json()
        return jsonify({'success': True, **response_data})
    else:
        response_data = result.get_json()
        return jsonify({'success': False, **response_data}), result.status_code

@app.route('/api/test_connection', methods=['POST'])
@login_required
def test_connection():
    return DeviceController.test_connection()

@app.route('/api/devices/delete-multiple', methods=['POST'])
@login_required
def delete_multiple_devices():
    """POST /api/devices/delete-multiple - Delete multiple devices (admin only)"""
    return DeviceController.delete_multiple_devices()

@app.route('/api/devices/fetch_mac', methods=['POST'])
@login_required
def fetch_device_mac():
    """Fetch MAC address from device"""
    data = request.json
    device_ip = data.get('device_ip')
    
    if not device_ip:
        return jsonify({'success': False, 'error': 'Device IP required'}), 400
    
    device = Device.find_by_ip(device_ip)
    if not device:
        return jsonify({'success': False, 'error': 'Device not found'}), 404
    
    mac_address = device.fetch_mac_address()
    if mac_address:
        Device.update_mac_address(device_ip, mac_address)
        return jsonify({'success': True, 'mac_address': mac_address})
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch MAC address'}), 500

# Test Execution
@app.route('/api/execute', methods=['POST'])
@login_required
def execute_test():
    return test_controller.execute_test()

# Queue Management
@app.route('/api/queue/add', methods=['POST'])
@login_required
def add_to_queue():
    return queue_controller.add_to_queue()

@app.route('/api/queue/status', methods=['GET'])
@login_required
def get_queue_status():
    return queue_controller.get_queue_status()

@app.route('/api/queue/clear', methods=['POST'])
@login_required
def clear_queue():
    return queue_controller.clear_queue()

# Results and Logging
@app.route('/api/results', methods=['GET'])
@login_required
def get_results():
    return results_controller.get_results()

@app.route('/api/logs')
@login_required
def stream_logs():
    return results_controller.stream_logs()

# IR Configuration
@app.route('/api/send_remote_keys', methods=['POST'])
@login_required
def send_remote_keys_api():
    from flask import request, jsonify
    data = request.get_json()
    device_ip = data.get('device_ip')
    key_sequence = data.get('key_sequence')
    if not device_ip or not key_sequence:
        return jsonify({'success': False, 'message': 'Device IP and key sequence required.'}), 400
    try:
        # Import and call the remote keys method
        from method_remote_keys import send_remote_keys
        result = send_remote_keys(device_ip, key_sequence)
        if result.get('success'):
            return jsonify({'success': True, 'message': result.get('message', 'Keys sent successfully.')})
        else:
            return jsonify({'success': False, 'message': result.get('message', 'Failed to send keys.')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
@app.route('/api/ir_keycodes', methods=['GET'])
@login_required
def get_ir_keycodes():
    """Get available IR keycodes"""
    from flask import jsonify
    try:
        keycodes_file = os.path.join(os.path.dirname(__file__), 'ir_keycodes.json')
        if os.path.exists(keycodes_file):
            import json
            with open(keycodes_file, 'r') as f:
                keycodes_data = json.load(f)

            # Backward compatibility: if keycodes are nested under remotes, expose a default keycodes map
            if 'keycodes' not in keycodes_data and 'remotes' in keycodes_data:
                remotes = keycodes_data.get('remotes') or {}
                default_remote = 'XUMO_PR3' if 'XUMO_PR3' in remotes else (next(iter(remotes), None))
                if default_remote:
                    keycodes_data['default_remote'] = default_remote
                    keycodes_data['keycodes'] = remotes.get(default_remote, {}).get('keycodes', {})
                else:
                    keycodes_data['keycodes'] = {}

            return jsonify(keycodes_data)
        else:
            return jsonify({'error': 'IR keycodes file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/optional_checks', methods=['GET'])
@login_required
def get_optional_checks():
    """Get dynamically discovered optional post-reboot checks from config_log_patterns"""
    from flask import jsonify
    try:
        from config.config_log_patterns import get_all_optional_checks
        checks = get_all_optional_checks()
        return jsonify(checks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ir_port', methods=['GET'])
@login_required
def get_ir_port():
    """Get IR port configuration for device"""
    from flask import jsonify, request
    device_query = request.args.get('device')
    if not device_query:
        return jsonify({'error': 'Device parameter required'}), 400
    
    device = Device.find_by_name(device_query) or Device.find_by_ip(device_query)
    if device:
        return jsonify({
            'device': device.name,
            'ip': device.ip,
            'ir_config': device.ir_config,
            'source': 'devices.json'
        })
    return jsonify({'error': 'Device not found'}), 404

# Device Screen Proxy
@app.route('/api/device_screen/<device_ip>', defaults={'path': ''})
@app.route('/api/device_screen/<device_ip>/<path:path>')
@login_required
def proxy_device_screen(device_ip, path):
    """Proxy device VNC screen through Flask to avoid browser security blocks"""
    import requests
    from flask import Response, stream_with_context
    
    try:
        # Validate device exists
        device = Device.find_by_ip(device_ip)
        if not device:
            return "Device not found", 404
        
        # Build the target URL
        vnc_base = f"http://{device_ip}:5800"
        
        # Handle query string
        query_string = request.query_string.decode('utf-8')
        if query_string:
            target_url = f"{vnc_base}/{path}?{query_string}"
        else:
            target_url = f"{vnc_base}/{path}" if path else vnc_base
        
        # Copy headers, excluding host
        headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'connection']}
        
        # Forward the request with the same method
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True,
            timeout=30
        )
        
        # Get content type
        content_type = resp.headers.get('content-type', 'text/html')
        
        # Create response headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(k, v) for k, v in resp.raw.headers.items() 
                           if k.lower() not in excluded_headers]
        
        # Return the proxied response
        return Response(
            stream_with_context(resp.iter_content(chunk_size=8192)),
            status=resp.status_code,
            headers=response_headers,
            content_type=content_type
        )
    except requests.exceptions.Timeout:
        return "Connection timeout to device screen", 504
    except requests.exceptions.RequestException as e:
        return f"Error connecting to device screen: {str(e)}", 502
    except Exception as e:
        return f"Proxy error: {str(e)}", 500

# WebSocket proxy for noVNC
@app.route('/api/device_screen_ws/<device_ip>')
def proxy_device_websocket(device_ip):
    """Proxy WebSocket connection for noVNC"""
    # Note: WebSocket proxying requires additional setup with flask-sockets or similar
    # For now, return info message
    return jsonify({
        'error': 'WebSocket proxy not yet implemented',
        'note': 'Direct WebSocket connection may be needed'
    }), 501

# Live Screenshot Capture - Alternative to VNC
@app.route('/api/live_screenshot/<device_ip>')
@login_required
def live_screenshot(device_ip):
    """Capture and serve a live screenshot from the device using RDK ScreenCapture plugin - Fast version for live viewing"""
    import paramiko
    import requests
    import time
    from config_screenshot import rpc_url, upload_base_url, download_base_url
    
    try:
        # Validate device exists
        device = Device.find_by_ip(device_ip)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Use USB Lexar drive for screenshots (dynamic mount path)
        from method_utils import get_lexar_base_path
        screenshot_folder = os.path.join(get_lexar_base_path(), 'screenshots')
        os.makedirs(screenshot_folder, exist_ok=True)
        
        # Connect via SSH with tight timeouts
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=device_ip,
                port=device.port,
                username=device.username,
                password=device.password,
                timeout=5,
                banner_timeout=5,
                auth_timeout=5
            )
        except Exception as conn_err:
            return jsonify({'error': f'SSH connection failed: {str(conn_err)}'}), 502
        
        # Quick activate (skip if already active)
        activate_cmd = f"curl -d '{{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\": \"Controller.1.activate\", \"params\":{{\"callsign\":\"org.rdk.ScreenCapture\"}}}}' {rpc_url}"
        ssh.exec_command(activate_cmd)
        time.sleep(1)  # Brief wait
        
        # Fast screenshot capture
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        screenshot_name = f"live_{device_ip.replace('.', '_')}_{timestamp_str}"
        upload_filename = f"{screenshot_name}.png"
        upload_url = f"{upload_base_url}?filename={upload_filename}"
        download_url = f"{download_base_url}{upload_filename}"
        
        screenshot_cmd = f"curl -k -d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\": \"org.rdk.ScreenCapture.1.uploadScreenCapture\", \"params\" : {{\"url\": \"{upload_url}\"}}}}' {rpc_url}"
        ssh.exec_command(screenshot_cmd)
        ssh.close()
        
        # Wait for upload - increased timeout
        time.sleep(6)
        
        # Try to download with retries
        max_retries = 2
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                response = requests.get(download_url, stream=True, verify=False, timeout=10)
                if response.status_code == 200:
                    # Save to local cache
                    os.makedirs(screenshot_folder, exist_ok=True)
                    local_path = os.path.join(screenshot_folder, upload_filename)
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    return send_file(local_path, mimetype='image/png')
                else:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return jsonify({'error': f'Screenshot not ready (HTTP {response.status_code})'}), 503
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return jsonify({'error': 'Screenshot download timeout'}), 504
            except Exception as dl_err:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return jsonify({'error': f'Download failed: {str(dl_err)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# Screenshots
@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve screenshot files from USB or local storage"""
    from flask import send_from_directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_screenshots_dir = os.path.join(base_dir, 'screenshots')
    local_screenshots_upper_dir = os.path.join(base_dir, 'SCREENSHOTS')
    local_reference_dir = os.path.join(base_dir, 'reference_screens')

    # Normalize common prefixes so we don't double-join paths
    if filename.startswith('/'):
        filename = filename.lstrip('/')
    if 'Enhancement_output/' in filename:
        filename = filename.split('Enhancement_output/', 1)[-1]
    if 'Enhancement-output/' in filename:
        filename = filename.split('Enhancement-output/', 1)[-1]
    if filename.startswith('screenshots/'):
        filename = filename.split('screenshots/', 1)[-1]
    if filename.startswith('SCREENSHOTS/'):
        filename = filename.split('SCREENSHOTS/', 1)[-1]
    if filename.startswith('reference_screens/'):
        filename = filename.split('reference_screens/', 1)[-1]
    
    # Try all possible paths until we find the file
    # Dynamically resolve Lexar path(s)
    possible_paths = []
    try:
        from method_utils import get_lexar_base_path
        possible_paths.append(get_lexar_base_path())
    except Exception:
        pass

    # Common fallback locations
    possible_paths.extend([
        '/media/pi/Lexar/Enhancement_output',  # Legacy path
        '/media/lrqa/Lexar/Enhancement_output',
        local_screenshots_dir,                  # Local screenshots
        local_screenshots_upper_dir,            # Local screenshots (uppercase)
        local_reference_dir,                    # Local reference screens
        'reference_screens',                    # Local reference screens (cwd fallback)
        'Enhancement_output'                    # Local fallback
    ])
    
    # Try each possible base path
    for path in possible_paths:
        if os.path.exists(path):
            # Try to serve directly if the relative path exists
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                directory = os.path.dirname(full_path)
                file_only = os.path.basename(full_path)
                return send_from_directory(directory, file_only)
    
    # If not found with any direct path, search recursively in all paths
    filename_only = os.path.basename(filename)
    for path in possible_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                if filename_only in files:
                    return send_from_directory(root, filename_only)
    
    return "Screenshot not found", 404

# Legacy/Utility Functions (kept for backward compatibility)
# Import only what exists in app_old
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Thread-local storage
import threading
thread_local = threading.local()

# Global variables for backward compatibility
current_session_folder = None
current_screenshots_dir = None
current_execution_logs_dir = None
current_device_logs_dir = None

def create_execution_session_folder(method, device_name, device_ip, iterations):
    """Create execution session folder"""
    global current_session_folder, current_screenshots_dir, current_execution_logs_dir, current_device_logs_dir
    
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').upper()
    safe_ip = device_ip.replace('.', '-')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
    session_name = f"{method.upper()}_{safe_device_name}_{safe_ip}_{iterations}_ITR_{timestamp}"
    
    # Check for USB device on Linux (try both uppercase and lowercase)
    usb_path = None
    if sys.platform.startswith('linux'):
        for usb_variant in ['/media/pi/lexar', '/media/pi/Lexar', '/media/pi/LEXAR']:
            if os.path.exists(usb_variant):
                usb_path = usb_variant
                break
    
    # If USB is available, use it directly; otherwise use local Enhancement_output
    if usb_path:
        base_output = usb_path
    else:
        base_output = 'Enhancement_output'
    
    session_folder = os.path.join(base_output, session_name)
    screenshots_dir = os.path.join(session_folder, "SCREENSHOTS")
    execution_logs_dir = os.path.join(session_folder, "EXECUTION_LOGS")
    device_logs_dir = os.path.join(session_folder, "DEVICE_LOGS")
    
    for folder in [session_folder, screenshots_dir, execution_logs_dir, device_logs_dir]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    thread_local.session_folder = session_folder
    thread_local.screenshots_dir = screenshots_dir
    thread_local.execution_logs_dir = execution_logs_dir
    thread_local.device_logs_dir = device_logs_dir
    
    current_session_folder = session_folder
    current_screenshots_dir = screenshots_dir
    current_execution_logs_dir = execution_logs_dir
    current_device_logs_dir = device_logs_dir
    
    return session_folder, screenshots_dir, execution_logs_dir, device_logs_dir

def load_devices():
    """Load devices using Device model"""
    devices = Device.load_all()
    return [d.to_dict() for d in devices]

def save_devices(devices_list):
    """Save devices using Device model"""
    devices = [Device.from_dict(d) for d in devices_list]
    Device.save_all(devices)

def test_ssh_connection(ip, port, username, password):
    """Test SSH connection"""
    device = Device(ip=ip, name="test", username=username, password=password, port=port)
    return device.validate_connection() + (None,)

def load_test_results():
    """Load test results"""
    results = TestResult.load_all()
    return [r.to_dict() for r in results]

def save_test_results(results_list):
    """Save test results"""
    results = [TestResult.from_dict(r) for r in results_list]
    TestResult.save_all(results)

def generate_html_report(device_ip, method, html_results):
    """Generate HTML report (placeholder)"""
    return None

def create_iteration_log_file(device_ip, method):
    """Create iteration log"""
    return log_service.create_iteration_log(device_ip, method)

def close_iteration_log_file():
    """Close iteration log"""
    log_service.close_iteration_log()

def probe_ir_ports(itach_ip='10.0.0.12', itach_port=4998, ports=(1, 2, 3)):
    """Probe IR ports"""
    results = {}
    base_code_tail = '24624,38000,1,37,8,29,8,65,8,34,8,107,8,49,8,49,8,44,8,101,8,494,8,29,8,55,8,29,8,34,8,81,8,29,8,29,8,29,8,3040,8,29,8,65,8,34,8,107,8,49,8,49,8,44,8,101,8,494,8,29,8,96,8,70,8,34,8,81,8,29,8,29,8,29,8,3040\r'
    import socket
    for p in ports:
        ir_code = f'sendir,{p}:2,{base_code_tail}'
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                sock.connect((itach_ip, itach_port))
                sock.sendall(ir_code.encode('utf-8'))
                response = sock.recv(1024).decode('utf-8', errors='ignore')
                results[p] = {'success': True, 'response': response.strip()}
        except Exception as e:
            results[p] = {'success': False, 'response': str(e)}
    return results

@app.route('/api/ir_port_probe', methods=['GET'])
@login_required
def ir_port_probe():
    """Probe IR ports"""
    from flask import jsonify, request
    itach_ip = request.args.get('itach_ip', '10.0.0.12')
    try:
        itach_port = int(request.args.get('itach_port', 4998))
    except ValueError:
        itach_port = 4998
    probe = probe_ir_ports(itach_ip, itach_port)
    return jsonify({'itach_ip': itach_ip, 'itach_port': itach_port, 'probes': probe})

@app.route('/api/iteration_logs', methods=['GET'])
@login_required
def get_iteration_logs():
    """Get list of iteration log files"""
    from flask import jsonify
    import os
    import glob
    
    try:
        logs_dir = 'iteration_logs'
        if not os.path.exists(logs_dir):
            return jsonify({'logs': []})
        
        log_files = []
        for filepath in glob.glob(os.path.join(logs_dir, '*.log')):
            filename = os.path.basename(filepath)
            file_stats = os.stat(filepath)
            log_files.append({
                'filename': filename,
                'path': filepath,
                'size': file_stats.st_size,
                'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            })
        
        # Sort by modified date descending
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'logs': log_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/iteration_logs/<filename>', methods=['GET'])
@login_required
def download_iteration_log(filename):
    """Download iteration log file"""
    from flask import send_from_directory
    import os
    
    try:
        logs_dir = 'iteration_logs'
        filepath = os.path.join(logs_dir, filename)
        
        if os.path.exists(filepath):
            return send_from_directory(logs_dir, filename, as_attachment=True)
        else:
            return jsonify({'error': 'Log file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ir-remotes', methods=['GET'])
@login_required
def get_ir_remotes():
    """Get available IR remotes and keys from ir_keycodes.json"""
    try:
        import json
        keycodes_path = os.path.join(os.path.dirname(__file__), 'Json', 'ir_keycodes.json')
        if not os.path.exists(keycodes_path):
            return jsonify({'success': True, 'remotes': {}})

        with open(keycodes_path, 'r') as f:
            data = json.load(f)

        remotes = data.get('remotes') or {}
        response = {}
        for remote_name, remote_data in remotes.items():
            keys = list((remote_data.get('keycodes') or {}).keys())
            response[remote_name] = {
                'keys': keys,
                'device_info': remote_data.get('device_info', {})
            }

        return jsonify({'success': True, 'remotes': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# RECOVERY ENDPOINTS
# =============================================================================

@app.route('/api/recovery/status', methods=['GET'])
@login_required
def get_recovery_status():
    """Get recovery service status"""
    import os
    try:
        state_exists = os.path.exists('app_state.json')
        checkpoint_exists = os.path.exists('checkpoint.pkl')
        crash_detected = os.path.exists('.crash_marker')
        
        status = {
            'state_file_exists': state_exists,
            'checkpoint_file_exists': checkpoint_exists,
            'crash_detected': crash_detected,
            'recovery_enabled': recovery_service is not None
        }
        
        # Get current state info if available
        if recovery_service:
            status['checkpointing_active'] = True
            status['checkpoint_interval'] = 30
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# SAVED SEQUENCES ENDPOINTS
# =============================================================================

@app.route('/api/sequences/save', methods=['POST'])
@login_required
def save_sequence():
    """Save a method sequence"""
    try:
        data = request.json
        name = data.get('name')
        queue_data = data.get('queue_data', [])
        
        # Support old format for backwards compatibility
        methods = data.get('methods', [])
        user_inputs = data.get('user_inputs', {})
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if not queue_data and not methods:
            return jsonify({'success': False, 'error': 'Queue data or methods are required'}), 400
        
        # Capture creator and team for permission tracking
        created_by = current_user.ntid
        team_name = getattr(current_user, 'team_name', '')
        sequence = SavedSequence.add_sequence(name, queue_data, methods, user_inputs, created_by, team_name=team_name)
        return jsonify({'success': True, 'sequence': sequence.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/list', methods=['GET'])
@login_required
def list_sequences():
    """List all saved sequences with permission info, filtered by team"""
    try:
        sequences = SavedSequence.load_all()
        user_team = getattr(current_user, 'team_name', None)
        is_admin = getattr(current_user, 'is_admin', False)
        
        # Filter sequences by team unless user is admin
        filtered_sequences = []
        for seq in sequences:
            seq_team = getattr(seq, 'team_name', '')
            # Show if:
            # 1. User is admin (show all)
            # 2. Sequence has no team (empty) - show to all users
            # 3. Sequence belongs to user's team
            if is_admin or not seq_team or (user_team and seq_team == user_team):
                filtered_sequences.append(seq.to_dict())
        
        return jsonify({
            'success': True,
            'sequences': filtered_sequences,
            'current_user': current_user.ntid,
            'is_admin': is_admin
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<sequence_id>', methods=['GET'])
@login_required
def get_sequence(sequence_id):
    """Get a specific sequence by ID"""
    try:
        sequence = SavedSequence.find_by_id(sequence_id)
        if sequence:
            return jsonify({'success': True, 'sequence': sequence.to_dict()})
        else:
            return jsonify({'success': False, 'error': 'Sequence not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<sequence_id>', methods=['DELETE'])
@login_required
def delete_sequence(sequence_id):
    """Delete a saved sequence - Only creator or admin can delete"""
    try:
        # Check permissions
        sequence = SavedSequence.find_by_id(sequence_id)
        if not sequence:
            return jsonify({'success': False, 'error': 'Sequence not found'}), 404
        
        # Allow deletion only if user is creator or admin
        if sequence.created_by != current_user.ntid and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permission denied. Only creator or admin can delete this sequence.'}), 403
        
        success = SavedSequence.delete_sequence(sequence_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete sequence'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sequences/<sequence_id>', methods=['PUT'])
@login_required
def update_sequence(sequence_id):
    """Update a saved sequence - Only creator or admin can update"""
    try:
        print(f"\n[API_PUT] ===== UPDATE SEQUENCE REQUEST =====")
        print(f"[API_PUT] Sequence ID: {sequence_id}")
        print(f"[API_PUT] Current user: {current_user.ntid}, Is admin: {current_user.is_admin}")
        
        # Check permissions
        sequence = SavedSequence.find_by_id(sequence_id)
        print(f"[API_PUT] Sequence found: {sequence is not None}")
        
        if not sequence:
            print(f"[API_PUT] ERROR: Sequence not found for ID: {sequence_id}")
            return jsonify({'success': False, 'error': f'Sequence not found: {sequence_id}'}), 404
        
        print(f"[API_PUT] Sequence creator: {sequence.created_by}")
        
        # Allow update only if user is creator or admin
        if sequence.created_by != current_user.ntid and not current_user.is_admin:
            print(f"[API_PUT] PERMISSION DENIED: User {current_user.ntid} is not creator {sequence.created_by} and not admin")
            return jsonify({'success': False, 'error': 'Permission denied. Only creator or admin can edit this sequence.'}), 403
        
        data = request.json
        name = data.get('name')  # Can be None to skip updating name
        methods = data.get('methods')  # Can be None to skip updating methods
        user_inputs = data.get('user_inputs')  # Can be None to skip updating user_inputs
        queue_data = data.get('queue_data')  # Can be None or list
        
        print(f"[API_PUT] Request data: name={bool(name)}, methods={bool(methods)}, user_inputs={bool(user_inputs)}, queue_data={bool(queue_data)}")
        if queue_data:
            print(f"[API_PUT] Queue items: {len(queue_data)}")
            # Validate queue_data structure
            try:
                import json
                json_str = json.dumps(queue_data)
                print(f"[API_PUT] Queue data JSON serialization: OK ({len(json_str)} bytes)")
            except Exception as json_err:
                print(f"[API_PUT] ERROR: Queue data JSON serialization failed: {str(json_err)}")
                raise ValueError(f"Invalid queue data format: {str(json_err)}")
        
        success = SavedSequence.update_sequence(sequence_id, name, methods, user_inputs, queue_data)
        print(f"[API_PUT] Update result: {success}")
        
        if success:
            # Reload updated sequence to verify
            updated_seq = SavedSequence.find_by_id(sequence_id)
            print(f"[API_PUT] Verification - Updated sequence has {len(updated_seq.queue_data)} queue items")
            print(f"[API_PUT] ===== UPDATE SUCCESSFUL =====\n")
            return jsonify({'success': True, 'sequence': updated_seq.to_dict()})
        else:
            print(f"[API_PUT] ERROR: SavedSequence.update_sequence returned False")
            return jsonify({'success': False, 'error': 'Failed to update sequence'}), 500
    except Exception as e:
        print(f"[API_PUT] ERROR: Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"[API_PUT] ===== UPDATE FAILED =====\n")
        return jsonify({'success': False, 'error': f'Error updating sequence: {str(e)}'}), 500

# =============================================================================
# JOB MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/api/jobs', methods=['POST'])
@login_required
def create_job():
    """Create a new job"""
    try:
        data = request.json
        device_ip = data.get('device_ip')
        device_name = data.get('device_name', 'Unknown Device')
        methods = data.get('methods', [])
        execution_queue = data.get('execution_queue', [])
        iterations = data.get('iterations', 1)
        sequence_name = data.get('sequence_name')
        
        if not device_ip:
            return jsonify({'success': False, 'error': 'device_ip is required'}), 400
        
        # Check if device is locked
        if DeviceLock.is_device_locked(device_ip):
            lock = DeviceLock.get_device_lock(device_ip)
            return jsonify({
                'success': False, 
                'error': f'Device is locked by {lock["user_id"]} until {lock["estimated_completion"]}'
            }), 409
        
        # Create job
        job = Job.create_job(
            user_id=current_user.ntid,
            device_ip=device_ip,
            device_name=device_name,
            methods=methods,
            execution_queue=execution_queue,
            iterations=iterations,
            sequence_name=sequence_name
        )
        
        # Calculate ETA and lock device with dynamic duration
        eta_seconds = calculate_eta(execution_queue, iterations)
        
        # Use DeviceLockManager for intelligent lock duration calculation
        lock = DeviceLockManager.acquire_lock_with_duration(
            device_ip=device_ip,
            device_name=device_name,
            user_id=current_user.ntid,
            job_id=job['job_id'],
            execution_queue=execution_queue,
            iterations=iterations
        )
        
        if not lock:
            return jsonify({
                'success': False,
                'error': 'Could not acquire device lock - device may be in use'
            }), 409
        
        # Log lock duration for transparency
        from datetime import datetime as dt
        lock_duration_hours = (dt.fromisoformat(lock.get('estimated_completion', '')) - dt.now(timezone.utc)).total_seconds() / 3600
        print(f"🔒 [LOCK] Device {device_ip} locked for job {job['job_id']}")
        print(f"   Duration: {lock_duration_hours:.1f} hours")
        print(f"   Expires: {lock.get('estimated_completion', 'Unknown')}")
        
        # Calculate actual lock duration for response
        from datetime import datetime as dt
        lock_duration_seconds = (dt.fromisoformat(lock.get('estimated_completion', '')) - dt.now(timezone.utc)).total_seconds()
        
        return jsonify({
            'success': True, 
            'job': job,
            'eta_seconds': eta_seconds,
            'eta_formatted': format_eta(eta_seconds),
            'lock_duration_seconds': int(lock_duration_seconds),
            'lock_expires': lock.get('estimated_completion', '')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def load_test_results_history():
    """Load historical test results from JSON file for previous day execution viewing"""
    from config_paths import TEST_RESULTS_FILE
    from utils.file_lock import FileLockManager
    
    try:
        if not os.path.exists(TEST_RESULTS_FILE):
            return []
        
        # Safely read the file
        results = FileLockManager.safe_json_read(TEST_RESULTS_FILE, default=[])
        if not isinstance(results, list):
            return []
        
        # Return results (most recent at top)
        return sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)
    except Exception as e:
        print(f"⚠️  Error loading test results history: {e}")
        return []

def map_test_result_status_to_job_status(test_result_status):
    """Map test result status (PASSED/FAILED/WARNING) to job status (completed/failed)"""
    if not test_result_status:
        return 'completed'
    
    status_lower = test_result_status.upper()
    
    if status_lower == 'PASSED':
        return 'completed'
    elif status_lower == 'FAILED':
        return 'failed'
    elif status_lower == 'WARNING':
        return 'completed'  # WARNING results completed but with warnings
    else:
        return 'completed'  # Default to completed for unknown statuses

def group_test_results_into_executions(test_results, current_user_id='Unknown User', time_window_seconds=10):
    """
    Group individual test method results into logical executions.
    
    Tests are grouped if they:
    1. Occur on the same device
    2. Occur within a time_window (default 10 seconds - represents methods in same sequence execution)
    3. Have the same date
    
    Returns list of execution objects with enriched metadata
    """
    if not test_results:
        return []
    
    from dateutil import parser
    
    executions = []
    grouped = {}
    
    # First pass: group results by device and date
    for result in test_results:
        device_ip = result.get('device_ip', 'Unknown')
        result_date = result.get('date', '')
        
        key = f"{device_ip}_{result_date}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(result)
    
    # Second pass: further group by time window within each device/date
    for group_key, results_for_group in grouped.items():
        # Sort by timestamp ascending
        sorted_results = sorted(results_for_group, key=lambda x: x.get('timestamp', ''))
        
        current_batch = []
        last_timestamp = None
        
        for result in sorted_results:
            try:
                result_timestamp = result.get('timestamp', '')
                
                if last_timestamp is None:
                    # First result in batch
                    current_batch = [result]
                    last_timestamp = result_timestamp
                else:
                    # Check if within time window
                    last_dt = parser.isoparse(last_timestamp) if isinstance(last_timestamp, str) else last_timestamp
                    current_dt = parser.isoparse(result_timestamp) if isinstance(result_timestamp, str) else result_timestamp
                    time_diff = (current_dt - last_dt).total_seconds()
                    
                    if abs(time_diff) <= time_window_seconds:
                        # Within time window, add to current batch
                        current_batch.append(result)
                    else:
                        # Outside time window, create execution from current batch and start new batch
                        if current_batch:
                            execution = create_execution_from_batch(
                                current_batch, 
                                current_user_id=current_user_id
                            )
                            executions.append(execution)
                        
                        current_batch = [result]
                        last_timestamp = result_timestamp
            except Exception as e:
                print(f"⚠️  Error parsing timestamp {result.get('timestamp')}: {e}")
                # Add to current batch anyway
                current_batch.append(result)
        
        # Don't forget the last batch
        if current_batch:
            execution = create_execution_from_batch(
                current_batch,
                current_user_id=current_user_id
            )
            executions.append(execution)
    
    # Sort by timestamp descending (most recent first)
    executions.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    
    return executions

def create_execution_from_batch(batch, current_user_id='Unknown User'):
    """
    Create a single execution object from a batch of test results.
    
    An execution represents all the methods that ran together for one complete
    execution instance on a device.
    """
    if not batch:
        return None
    
    # Use first result's timestamp as execution start
    first_result = batch[0]
    last_result = batch[-1]
    
    device_ip = first_result.get('device_ip', 'Unknown Device')
    start_time = first_result.get('timestamp', '')
    end_time = last_result.get('timestamp', start_time)
    
    # Extract methods from the batch
    methods = [r.get('method', 'unknown') for r in batch]
    unique_methods = list(dict.fromkeys(methods))  # Remove duplicates, preserve order
    
    # Determine overall execution status
    statuses = [r.get('status', 'UNKNOWN') for r in batch]
    if 'FAILED' in statuses:
        overall_status = 'failed'
    else:
        overall_status = 'completed'
    
    # Create a meaningful execution title
    title = generate_execution_title(unique_methods)
    
    # Create unique ID based on device, date, and time
    execution_id = f"hist_{hash(str(start_time + device_ip))}"
    
    # Gather details from all methods in batch
    details_list = []
    for r in batch:
        phase = r.get('phase', 'Unknown phase')
        method = r.get('method', 'unknown')
        details_list.append(f"{method}: {phase}")
    
    execution = {
        'job_id': execution_id,
        'device_ip': device_ip,
        'device_name': device_ip,  # Use IP as device name for historical data
        'sequence_name': title,  # Show the generated title as sequence name
        'user_id': current_user_id,  # Use current user or 'Unknown User'
        'methods': unique_methods,
        'status': overall_status,  # 'completed' or 'failed
        'start_time': start_time,
        'end_time': end_time,
        'iterations': 1,
        'is_historical': True,
        'method_count': len(unique_methods),
        'result_count': len(batch),
        'methods_executed': ', '.join(unique_methods),
        'execution_details': details_list,
        'created_at': start_time,
        'timestamp': start_time,
        'date': first_result.get('date', '')
    }
    
    return execution

def generate_execution_title(methods):
    """
    Generate a meaningful execution title from the list of methods.
    
    Maps common method patterns to readable names.
    """
    if not methods:
        return "Execution"
    
    # Method name mapping to readable titles
    method_aliases = {
        'deepsleep': 'Deep Sleep Test',
        'ir_test': 'IR Remote Test',
        'send_remote_keys': 'Remote Keys',
        'reboot': 'Reboot Test',
        'reboot_perf_v2_optimized': 'Performance Reboot',
        'screen_validation': 'Screen Validation',
        'execute_command': 'Command Execution',
        'collect_device_logs': 'Log Collection',
        'wait': 'Wait/Delay',
        'voice_command': 'Voice Command',
        'maintenance_deepsleep_wakeup': 'Maintenance Deep Sleep',
        'maintenance_CURL_deepsleep_wakeup': 'Maintenance CURL Sleep',
        'deepsleep-reboot': 'Deep Sleep + Reboot'
    }
    
    # Build title from method names
    title_parts = []
    for method in methods:
        if method in method_aliases:
            title_parts.append(method_aliases[method])
        else:
            # Use method name as-is, capitalize and make human-readable
            readable = method.replace('_', ' ').title()
            title_parts.append(readable)
    
    # Create combined title
    if len(title_parts) == 1:
        return title_parts[0]
    elif len(title_parts) == 2:
        return f"{title_parts[0]} + {title_parts[1]}"
    else:
        return f"{title_parts[0]} + {len(title_parts) - 1} more methods"

@app.route('/api/jobs', methods=['GET'])
@login_required
def get_jobs():
    """List current jobs only - no historical data mixing
    
    PERMANENT FIX: This endpoint ONLY returns current jobs from jobs.json.
    It NEVER loads historical data as a fallback. This prevents:
    - Date filtering showing wrong results (yesterday's jobs appearing as current)
    - Data mixing (1244 jobs from yesterday appearing when selecting today)
    - Cache pollution from stale historical data
    """
    # Add cache-busting headers to prevent browser/proxy caching
    # This is CRITICAL to prevent users from seeing stale job data
    from datetime import datetime as dt
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',  # Strict no-cache
        'Pragma': 'no-cache',
        'Expires': '0',
        'Last-Modified': dt.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }
    
    try:
        user_id = request.args.get('user_id')
        device_ip = request.args.get('device_ip')
        status = request.args.get('status')
        
        if user_id:
            jobs = Job.get_user_jobs(user_id)
        elif device_ip:
            jobs = Job.get_device_jobs(device_ip)
        elif status == 'running':
            jobs = Job.get_running_jobs()
        else:
            jobs = Job.load_all()
        
        # Apply status filter if provided and not already filtered
        if status and not device_ip and not user_id:
            jobs = [job for job in jobs if job.status == status]
        
        # Convert Job objects to dictionaries
        jobs_data = [job.to_dict() for job in jobs]
        
        # FIX: PERMANENT - Removed historical data fallback
        # REASON: Mixing current jobs with stale historical data causes:
        #   1. Date filtering to show wrong results
        #   2. Yesterday's jobs to appear as current (1244 jobs issue)
        #   3. Today's jobs to disappear when historical data is loaded
        # SOLUTION: ONLY return current jobs from jobs.json, never load historical data
        # Historical data has a separate endpoint if needed for reporting
        
        print(f"[API] Returning {len(jobs_data)} CURRENT jobs (no historical data fallback)")

        
        # Log jobs with null or missing start_time (debugging)
        jobs_with_null_time = [j for j in jobs_data if not j.get('start_time')]
        if jobs_with_null_time:
            print(f"⚠️  [API] Found {len(jobs_with_null_time)} jobs with NULL start_time:")
            for job_dict in jobs_with_null_time[:5]:  # Show first 5
                print(f"   - Job {job_dict.get('job_id', 'unknown')[:8]}..., status: {job_dict.get('status')}, created_at: {job_dict.get('created_at')}")
        
        # Sort by start_time descending (most recent first)
        jobs_data.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        print(f"✅ [API] Returning {len(jobs_data)} CURRENT jobs (no historical mixing)")
        if jobs_data:
            print(f"   Most recent: {jobs_data[0].get('job_id', 'unknown')[:8]}..., status: {jobs_data[0].get('status')}")
        
        response = jsonify({'success': True, 'jobs': jobs_data})
        for header, value in response_headers.items():
            response.headers[header] = value
        return response
    except Exception as e:
        print(f"❌ [API] Error in get_jobs: {str(e)}")
        import traceback
        traceback.print_exc()
        response = jsonify({'success': False, 'error': str(e)})
        for header, value in response_headers.items():
            response.headers[header] = value
        return response, 500

@app.route('/api/execution-history', methods=['GET'])
@login_required
def get_execution_history():
    """Get execution history from test_results_history.json, optionally filtered by date
    
    Returns execution data grouped by job_id from the historical test results.
    Each method/phase execution is grouped under its parent job.
    """
    # Add cache-busting headers
    from datetime import datetime as dt
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Last-Modified': dt.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
    }
    
    try:
        from config_paths import TEST_RESULTS_FILE
        
        # Get optional date filter parameter
        filter_date = request.args.get('date')  # Format: YYYY-MM-DD
        device_ip = request.args.get('device_ip')
        
        # Load test results history
        if not os.path.exists(TEST_RESULTS_FILE):
            response = jsonify({'success': True, 'executions': []})
            for header, value in response_headers.items():
                response.headers[header] = value
            return response
        
        try:
            results_data = FileLockManager.safe_json_read(TEST_RESULTS_FILE, default=[])
        except Exception as e:
            print(f"❌ Failed to read file: {str(e)}")
            import traceback
            traceback.print_exc()
            results_data = []
        
        # Filter by date if provided
        if filter_date:
            results_data = [r for r in results_data if r.get('date') == filter_date or r.get('timestamp', '').startswith(filter_date)]
        
        # Filter by device if provided
        if device_ip:
            results_data = [r for r in results_data if r.get('device_ip') == device_ip]
        
        # Sort by timestamp descending (most recent first)
        results_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Load jobs to map job_id → user_id, sequence_name, and other details
        job_details_map = {}
        try:
            from models.job import Job
            all_jobs = Job.load_all()
            for job in all_jobs:
                job_details_map[job.job_id] = {
                    'user_id': job.user_id,
                    'sequence_name': job.sequence_name,  # Include sequence_name for completed jobs
                    'username': job.user_id
                }
        except Exception as e:
            print(f"⚠️  Could not load jobs for username/sequence lookup: {e}")
        
        # Group by job_id to create consolidated job records from test results
        try:
            jobs_from_results = {}
            for result in results_data:
                job_id = result.get('job_id')
                if not job_id:
                    continue
                
                if job_id not in jobs_from_results:
                    # Initialize job with all available metadata
                    device_name = result.get('device_name')
                    if not device_name:
                        # Fallback to device_ip if device_name not available
                        device_name = result.get('device_ip', 'Unknown')
                    
                    # Look up username and sequence_name from job, fallback to result fields
                    username = result.get('username') or result.get('user_id')
                    if not username and job_id in job_details_map:
                        username = job_details_map[job_id]['user_id']  # ← Get from Job object
                    
                    # Get sequence_name from result first, then fallback to job details
                    sequence_name = result.get('sequence_name')
                    if not sequence_name and job_id in job_details_map:
                        sequence_name = job_details_map[job_id]['sequence_name']  # ← FIX: Get sequence_name from Job
                    
                    jobs_from_results[job_id] = {
                        'job_id': job_id,
                        'device_ip': result.get('device_ip', ''),
                        'device_name': device_name,  # Use actual name or IP, not "Unknown"
                        'sequence_name': sequence_name,  # Include sequence_name for dashboard display
                        'username': username,  # User who triggered it (looked up from Job if needed)
                        'status': 'completed',
                        'start_time': result.get('timestamp', ''),
                        'end_time': result.get('timestamp', ''),
                        'methods': set(),  # Track unique methods
                        'iterations': result.get('iterations', 1),  # Total iterations for this job
                        'current_iteration': result.get('current_iteration', 1),
                        'iteration_results': {},  # Track iteration status
                        'results': [],  # All method/phase executions
                        'passed_count': 0,
                        'failed_count': 0,
                        'total_time': 0
                    }
                
                # Add this method execution to results
                method = result.get('method', '')
                status = result.get('status', 'UNKNOWN')
                iteration = result.get('iteration', 1)
                
                jobs_from_results[job_id]['methods'].add(method)
                
                # Track iteration results
                iter_key = f"iteration_{iteration}"
                if status.upper() == 'PASSED':
                    jobs_from_results[job_id]['iteration_results'][iter_key] = 'passed'
                    jobs_from_results[job_id]['passed_count'] += 1
                elif status.upper() == 'FAILED':
                    jobs_from_results[job_id]['iteration_results'][iter_key] = 'failed'
                    jobs_from_results[job_id]['failed_count'] += 1
                
                # Update end time to latest
                if result.get('timestamp', '') > jobs_from_results[job_id]['end_time']:
                    jobs_from_results[job_id]['end_time'] = result.get('timestamp', '')
                
                # Add result details
                jobs_from_results[job_id]['results'].append({
                    'method': method,
                    'status': status,
                    'timestamp': result.get('timestamp', ''),
                    'iteration': iteration,
                    'phase': result.get('phase', ''),
                    'performance_seconds': result.get('performance_seconds'),
                    'details': result.get('details', ''),
                    'logs': result.get('logs', ''),
                    'screenshots': result.get('screenshots', '')
                })
            
            # Convert to list, convert sets to lists, and sort
            execution_history = []
            for job in jobs_from_results.values():
                job['methods'] = sorted(list(job['methods']))  # Convert set to sorted list
                execution_history.append(job)
            
            execution_history.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        except Exception as e:
            print(f"❌ Grouping failed: {str(e)}")
            import traceback
            traceback.print_exc()
            execution_history = []
        
        response = jsonify({
            'success': True,
            'executions': execution_history,
            'jobs': execution_history,  # Also return as 'jobs' for compatibility with frontend
            'total': len(execution_history),
            'filtered_by_date': filter_date
        })
        for header, value in response_headers.items():
            response.headers[header] = value
        return response
    except Exception as e:
        print(f"❌ Error in get_execution_history: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """Get specific job details"""
    try:
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        return jsonify({'success': True, 'job': job.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/lock-status', methods=['GET'])
@login_required
def get_job_lock_status(job_id):
    """Get current lock status for a job (Change 6) - Provides real-time lock expiration info"""
    try:
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        device_ip = job.device_ip
        lock = DeviceLock.get_device_lock(device_ip)
        
        if not lock:
            return jsonify({
                'success': True,
                'locked': False,
                'device_ip': device_ip,
                'job_id': job_id,
                'status': 'Device is unlocked'
            })
        
        time_remaining = DeviceLock.get_time_until_expiration(device_ip)
        is_owned_by_job = lock.get('job_id') == job_id
        
        # Calculate hours and minutes for readability
        hours = time_remaining // 3600
        minutes = (time_remaining % 3600) // 60
        
        lock_status = {
            'success': True,
            'locked': True,
            'device_ip': device_ip,
            'job_id': job_id,
            'locked_by_job': is_owned_by_job,
            'locked_by_user': lock.get('user_id', 'Unknown'),
            'time_remaining_seconds': max(0, time_remaining),
            'time_remaining_formatted': f'{hours}h {minutes}m' if time_remaining > 0 else 'Expired',
            'estimated_completion': lock.get('estimated_completion', 'Unknown'),
            'warning': time_remaining < 600,  # Warning if <10 min remaining
            'critical': time_remaining < 300  # Critical if <5 min remaining
        }
        
        # Add status message
        if is_owned_by_job:
            lock_status['status'] = f'Locked by this job until {lock.get("estimated_completion", "Unknown")}'
        else:
            lock_status['status'] = f'Locked by job {lock.get("job_id", "Unknown")} (user: {lock.get("user_id", "Unknown")})'
        
        return jsonify(lock_status)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/status', methods=['PUT'])
@login_required
def update_job_status(job_id):
    """Update job status"""
    try:
        data = request.json
        status = data.get('status')
        end_time = data.get('end_time')
        log_file_path = data.get('log_file_path')
        
        if not status:
            return jsonify({'success': False, 'error': 'status is required'}), 400
        
        success = Job.update_job_status(job_id, status, end_time, log_file_path)
        
        if success:
            # Unlock device if job is completed/failed/cancelled
            if status in ['completed', 'failed', 'cancelled']:
                job = Job.get_job(job_id)
                if job:
                    DeviceLock.unlock_device(job.device_ip)
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/pending', methods=['GET'])
@login_required
def get_pending_jobs():
    """Get all pending jobs in the queue"""
    try:
        pending_jobs = Job.get_pending_jobs()
        return jsonify({
            'success': True,
            'pending_jobs': pending_jobs,
            'count': len(pending_jobs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/active', methods=['GET'])
@login_required
def get_active_jobs():
    """Get all active (running + pending) jobs with device and ETA info"""
    try:
        from models.device import Device
        from config_eta import calculate_eta, format_eta
        
        # Get running and pending jobs
        running_jobs = Job.get_running_jobs()
        pending_jobs_raw = Job.get_pending_jobs()
        
        # Convert pending jobs to Job objects
        pending_jobs = [Job.get_job(job_data['job_id']) for job_data in pending_jobs_raw]
        pending_jobs = [job for job in pending_jobs if job]  # Filter out None values
        
        # Combine running and pending
        all_active = running_jobs + pending_jobs
        
        # Enhance with device info and ETA
        jobs_data = []
        for job in all_active:
            job_dict = job.to_dict()
            
            # Add device name
            device = Device.find_by_ip(job.device_ip)
            if device:
                job_dict['device_name'] = device.name
            
            # Add device lock info for ETA
            lock = DeviceLock.get_lock(job.device_ip)
            if lock:
                job_dict['eta_formatted'] = lock.eta
                job_dict['estimated_completion'] = lock.estimated_completion
            else:
                # Calculate ETA if not available
                if job.execution_queue and job.execution_queue.get('iterations'):
                    eta_seconds = calculate_eta(job.execution_queue, job.execution_queue['iterations'])
                    job_dict['eta_formatted'] = format_eta(eta_seconds)
            
            jobs_data.append(job_dict)
        
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'count': len(jobs_data)
        })
    except Exception as e:
        import traceback
        print(f"Error in get_active_jobs: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
@login_required
def cancel_job(job_id):
    """Cancel a pending or running job (user must own the job or be admin)"""
    try:
        # Get the job to check ownership
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        # Check permissions: user must own the job OR be admin
        if job.user_id != current_user.user_id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Unauthorized: You can only cancel your own jobs'}), 403
        
        success = Job.cancel_job(job_id)
        
        if success:
            # Unlock the device
            DeviceLock.unlock_device(job.device_ip)
            
            return jsonify({'success': True, 'message': 'Job cancelled successfully'})
        else:
            return jsonify({'success': False, 'error': 'Cannot cancel job'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/logs', methods=['GET'])
@login_required
def get_job_logs(job_id):
    """Stream job-specific logs"""
    try:
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        log_file_path = job.log_file_path or ''
        
        # If log_file_path is not set, try the default job logs directory
        if not log_file_path or not os.path.exists(log_file_path):
            default_log_path = os.path.join('logs', 'jobs', job_id, 'execution.log')
            if os.path.exists(default_log_path):
                log_file_path = default_log_path
                # Update job with correct log path for future reference
                Job.update_job_status(job_id, job.status, log_file_path=log_file_path)
        
        # Check if log file exists
        if log_file_path and os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                logs = f.read()
            return jsonify({'success': True, 'logs': logs, 'log_file': log_file_path})
        else:
            # Return empty logs if file doesn't exist yet
            return jsonify({'success': True, 'logs': '', 'log_file': log_file_path or 'Not created yet'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/download', methods=['GET'])
@login_required
def download_job_log(job_id):
    """Download complete job log file"""
    try:
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        log_file_path = job.log_file_path or ''
        
        if not log_file_path or not os.path.exists(log_file_path):
            return jsonify({'success': False, 'error': 'Log file not found'}), 404
        
        return send_file(
            log_file_path,
            as_attachment=True,
            download_name=f'job_{job_id}_log.txt'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jobs/<job_id>/execute', methods=['POST'])
@login_required
def execute_pending_job(job_id):
    """Execute a pending job by moving it from device queue to running status"""
    try:
        from services.queue_service import QueueService
        import json
        
        # First check device_job_queue.json (for pending jobs in queue)
        # Use global queue_service to ensure proper test_execution_service is available
        global queue_service
        device_queue = queue_service.device_job_queue
        
        pending_job_data = None
        device_ip = None
        
        # Find the job in device queue
        for dev_ip, jobs_list in device_queue.items():
            for job_data in jobs_list:
                if job_data.get('job_id') == job_id:
                    pending_job_data = job_data
                    device_ip = dev_ip
                    break
            if pending_job_data:
                break
        
        # If not in device queue, check jobs.json
        if not pending_job_data:
            job = Job.get_job(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            pending_job_data = job.to_dict()
            device_ip = job.device_ip
        
        # Check permissions: user must own the job OR be admin
        if pending_job_data.get('user_id') != current_user.user_id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Unauthorized: You can only execute your own jobs'}), 403
        
        # Check if job is pending
        if pending_job_data.get('status') != 'pending':
            return jsonify({'success': False, 'error': f'Job status is "{pending_job_data.get("status")}", not pending. Only pending jobs can be executed.'}), 400
        
        # Check if device is available (no other running job)
        from models.device_lock import DeviceLock
        active_job = Job.get_active_device_job(device_ip)
        if active_job and active_job.job_id != job_id and active_job.status == 'running':
            return jsonify({'success': False, 'error': f'Device is busy running job {active_job.job_id}'}), 409
        
        # Lock the device
        # Calculate ETA for the pending job
        execution_queue = pending_job_data.get('execution_queue', [])
        iterations = pending_job_data.get('iterations', 1)
        eta_seconds = calculate_eta(execution_queue, iterations)
        
        # Use DeviceLockManager for intelligent lock duration calculation
        lock_acquired = DeviceLock.lock_device(
            device_ip=device_ip,
            device_name=pending_job_data.get('device_name', 'Unknown Device'),
            user_id=pending_job_data.get('user_id'),
            job_id=job_id,
            estimated_duration_seconds=eta_seconds
        )
        if not lock_acquired:
            return jsonify({'success': False, 'error': 'Could not acquire device lock'}), 409
        
        # Remove from device queue and update status to running
        if pending_job_data in device_queue.get(device_ip, []):
            # Job is in device queue - remove it
            device_queue[device_ip].remove(pending_job_data)
            queue_service._save_device_job_queue()
            
            # Update the job status to running in jobs.json
            pending_job_data['status'] = 'running'
            pending_job_data['start_time'] = datetime.utcnow().isoformat()
            
            # Add to jobs.json
            jobs = Job.load_all()
            # Check if already in jobs.json
            found = False
            for job in jobs:
                if job.job_id == job_id:
                    job.status = 'running'
                    job.start_time = datetime.utcnow().isoformat()
                    found = True
                    break
            if not found:
                # Create new job in jobs.json
                new_job = Job(
                    job_id=pending_job_data['job_id'],
                    user_id=pending_job_data['user_id'],
                    device_ip=pending_job_data['device_ip'],
                    device_name=pending_job_data['device_name'],
                    methods=pending_job_data.get('methods', []),
                    iterations=pending_job_data.get('iterations', 1),
                    status='running',
                    start_time=datetime.utcnow().isoformat(),
                    execution_queue=pending_job_data.get('execution_queue', []),
                    sequence_name=pending_job_data.get('sequence_name')
                )
                jobs.append(new_job)
            Job.save_all(jobs)
            
            # Queue the job for actual execution by the QueueService
            # This is crucial - without this, the job stays in RUNNING status but never executes
            queue_service.execution_queue.put({
                'job_id': job_id,
                'device_ip': device_ip,
                'execution_queue': pending_job_data.get('execution_queue', []),
                'iterations': pending_job_data.get('iterations', 1),
                'sequence_name': pending_job_data.get('sequence_name'),
                'status': 'running'
            })
            queue_service.start_processor()  # Ensure processor thread is running
            
            return jsonify({'success': True, 'message': 'Job execution started', 'job_id': job_id})
        else:
            # Job already in jobs.json, just move to running
            success = Job.execute_pending_job(job_id)
            if success:
                # Queue for execution
                execution_queue = pending_job_data.get('execution_queue', [])
                queue_service.execution_queue.put({
                    'job_id': job_id,
                    'device_ip': device_ip,
                    'execution_queue': execution_queue,
                    'iterations': pending_job_data.get('iterations', 1),
                    'sequence_name': pending_job_data.get('sequence_name'),
                    'status': 'running'
                })
                queue_service.start_processor()
                
                return jsonify({'success': True, 'message': 'Job execution started', 'job_id': job_id})
            else:
                DeviceLock.unlock_device(device_ip)
                return jsonify({'success': False, 'error': 'Failed to execute job'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jobs/<job_id>/delete', methods=['POST'])
@login_required
def delete_pending_job(job_id):
    """Delete a pending job from the device queue or jobs.json"""
    try:
        import json
        
        # First check device_job_queue.json (for pending jobs in queue)
        # Use global queue_service instance
        global queue_service
        device_queue = queue_service.device_job_queue
        
        pending_job_data = None
        device_ip = None
        
        # Find the job in device queue
        for dev_ip, jobs_list in device_queue.items():
            for job_data in jobs_list:
                if job_data.get('job_id') == job_id:
                    pending_job_data = job_data
                    device_ip = dev_ip
                    break
            if pending_job_data:
                break
        
        # If in device queue, delete from there
        if pending_job_data:
            # Check permissions: user must own the job OR be admin
            if pending_job_data.get('user_id') != current_user.user_id and not current_user.is_admin:
                return jsonify({'success': False, 'error': 'Unauthorized: You can only delete your own jobs'}), 403
            
            # Check if job is pending
            if pending_job_data.get('status') != 'pending':
                return jsonify({'success': False, 'error': f'Job status is "{pending_job_data.get("status")}", not pending. Only pending jobs can be deleted.'}), 400
            
            # Remove from device queue
            device_queue[device_ip].remove(pending_job_data)
            queue_service._save_device_job_queue()
            
            return jsonify({'success': True, 'message': 'Job deleted successfully', 'job_id': job_id})
        
        # Otherwise check jobs.json
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        # Check permissions: user must own the job OR be admin
        if job.user_id != current_user.user_id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Unauthorized: You can only delete your own jobs'}), 403
        
        # Check if job is pending (only delete pending jobs)
        if job.status != 'pending':
            return jsonify({'success': False, 'error': f'Job status is "{job.status}", not pending. Only pending jobs can be deleted.'}), 400
        
        # Delete the job from jobs.json
        success = Job.delete_pending_job(job_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Job deleted successfully', 'job_id': job_id})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete job'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/services/system-commands')
@login_required
def system_command_results_page():
    """Render System Command results page"""
    return render_template('system_command_results.html', current_user=current_user)


@app.route('/api/system-command-logs/<job_id>', methods=['GET'])
@login_required
def list_system_command_logs(job_id):
    """List system command log files for a job"""
    try:
        from method_utils import get_lexar_base_path
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        start_time = job.start_time or ''
        date_part = ''
        if 'T' in start_time:
            date_part = start_time.split('T')[0]
        elif start_time:
            date_part = start_time[:10]
        if not date_part:
            date_part = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        safe_device_name = job.device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
        safe_ip = job.device_ip.replace('.', '-')
        device_folder = f"{safe_ip}_{safe_device_name}"

        if job.sequence_name:
            method_folder = job.sequence_name.replace(' ', '_')
        else:
            methods = job.methods or []
            if len(methods) > 3:
                method_folder = ','.join(methods[:3]) + f'+{len(methods)-3}more'
            else:
                method_folder = ','.join(methods) if methods else 'SYSTEM_COMMAND'
        method_folder = method_folder.replace(' ', '_')

        exec_root = os.path.join(get_lexar_base_path(), 'EXECUTION_LOGS')
        candidate_dirs = []
        primary_dir = os.path.join(exec_root, date_part, device_folder, method_folder)
        if os.path.isdir(primary_dir):
            candidate_dirs.append(primary_dir)

        # Fallback: scan all date folders for this device/method
        if os.path.isdir(exec_root):
            for date_folder in sorted(os.listdir(exec_root)):
                date_path = os.path.join(exec_root, date_folder)
                if not os.path.isdir(date_path):
                    continue
                candidate = os.path.join(date_path, device_folder, method_folder)
                if os.path.isdir(candidate) and candidate not in candidate_dirs:
                    candidate_dirs.append(candidate)

        files = []
        for base_dir in candidate_dirs:
            for entry in sorted(os.listdir(base_dir)):
                if not entry.startswith('ITR-'):
                    continue
                itr_dir = os.path.join(base_dir, entry)
                if not os.path.isdir(itr_dir):
                    continue
                for fname in os.listdir(itr_dir):
                    if fname.startswith('SYSTEM_COMMAND_ITR_') and fname.endswith('.log'):
                        iteration = entry.replace('ITR-', '')
                        files.append({
                            'iteration': iteration,
                            'filename': fname,
                            'path': os.path.join(itr_dir, fname)
                        })

        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system-command-logs/<job_id>/preview', methods=['GET'])
@login_required
def preview_system_command_log(job_id):
    """Preview parsed system command log blocks for a job iteration"""
    try:
        from method_utils import get_lexar_base_path
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        iteration = request.args.get('iteration', '').strip()
        if not iteration:
            return jsonify({'success': False, 'error': 'iteration is required'}), 400

        start_time = job.start_time or ''
        date_part = ''
        if 'T' in start_time:
            date_part = start_time.split('T')[0]
        elif start_time:
            date_part = start_time[:10]
        if not date_part:
            date_part = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        safe_device_name = job.device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
        safe_ip = job.device_ip.replace('.', '-')
        device_folder = f"{safe_ip}_{safe_device_name}"

        if job.sequence_name:
            method_folder = job.sequence_name.replace(' ', '_')
        else:
            methods = job.methods or []
            if len(methods) > 3:
                method_folder = ','.join(methods[:3]) + f'+{len(methods)-3}more'
            else:
                method_folder = ','.join(methods) if methods else 'SYSTEM_COMMAND'
        method_folder = method_folder.replace(' ', '_')

        exec_root = os.path.join(get_lexar_base_path(), 'EXECUTION_LOGS')
        candidate_dirs = []
        primary_dir = os.path.join(exec_root, date_part, device_folder, method_folder)
        if os.path.isdir(primary_dir):
            candidate_dirs.append(primary_dir)

        if os.path.isdir(exec_root):
            for date_folder in sorted(os.listdir(exec_root)):
                date_path = os.path.join(exec_root, date_folder)
                if not os.path.isdir(date_path):
                    continue
                candidate = os.path.join(date_path, device_folder, method_folder)
                if os.path.isdir(candidate) and candidate not in candidate_dirs:
                    candidate_dirs.append(candidate)

        log_path = None
        for base_dir in candidate_dirs:
            candidate_path = os.path.join(base_dir, f"ITR-{iteration}", f"SYSTEM_COMMAND_ITR_{iteration}.log")
            if os.path.exists(candidate_path):
                log_path = candidate_path
                break

        if not log_path:
            return jsonify({'success': True, 'blocks': []})

        def strip_prefix(line):
            if '] ' in line:
                return line.split('] ', 1)[1]
            return line

        def parse_blocks(content):
            blocks = []
            current = None
            for line in content.splitlines():
                payload = strip_prefix(line).strip()
                if payload.startswith('SYSTEM_COMMAND_BLOCK_START|'):
                    label = payload.split('label=', 1)[1] if 'label=' in payload else 'TOP Capture'
                    current = {'label': label, 'rows': [], 'average': None}
                elif payload.startswith('SYSTEM_COMMAND_ROW|') and current is not None:
                    parts = payload.split('|')[1:]
                    current['rows'].append(parts)
                elif payload.startswith('SYSTEM_COMMAND_AVERAGE|') and current is not None:
                    current['average'] = payload.split('|')[1:]
                elif payload.startswith('SYSTEM_COMMAND_BLOCK_END') and current is not None:
                    blocks.append(current)
                    current = None
            return blocks

        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = parse_blocks(content)
        return jsonify({'success': True, 'blocks': blocks, 'log_path': log_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system-command-logs/<job_id>/consolidate', methods=['POST'])
@login_required
def consolidate_system_command_logs(job_id):
    """Consolidate selected system command log files into an Excel workbook."""
    try:
        from openpyxl import Workbook
    except Exception as exc:
        return jsonify({'success': False, 'error': f'openpyxl not available: {exc}'}), 500

    try:
        data = request.get_json(silent=True) or {}
        selected_files = data.get('files', [])
        if not selected_files:
            return jsonify({'success': False, 'error': 'No files selected'}), 400

        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        wb = Workbook()
        if wb.sheetnames:
            wb.remove(wb[wb.sheetnames[0]])

        header = [
            "Time",
            "MemTotal",
            "MemFree",
            "MemUsed",
            "BuffCache",
            "SwapTotal",
            "SwapFree",
            "SwapUsed",
            "AvailMem",
            "RSS_KB",
            "PSS_KB",
            "PID",
            "VIRT_KiB",
            "RES_KiB",
            "SHR_KiB",
            "CPU_pct",
            "MEM_pct"
        ]

        def strip_prefix(line):
            if '] ' in line:
                return line.split('] ', 1)[1]
            return line

        def parse_blocks(content):
            blocks = []
            current = None
            for line in content.splitlines():
                payload = strip_prefix(line).strip()
                if payload.startswith('SYSTEM_COMMAND_BLOCK_START|'):
                    label = payload.split('label=', 1)[1] if 'label=' in payload else 'TOP Capture'
                    current = {'label': label, 'rows': [], 'average': None}
                elif payload.startswith('SYSTEM_COMMAND_ROW|') and current is not None:
                    parts = payload.split('|')[1:]
                    current['rows'].append(parts)
                elif payload.startswith('SYSTEM_COMMAND_AVERAGE|') and current is not None:
                    current['average'] = payload.split('|')[1:]
                elif payload.startswith('SYSTEM_COMMAND_BLOCK_END') and current is not None:
                    blocks.append(current)
                    current = None
            return blocks

        for file_path in selected_files:
            if not os.path.exists(file_path):
                continue
            filename = os.path.basename(file_path)
            iteration = '1'
            if 'SYSTEM_COMMAND_ITR_' in filename:
                iteration = filename.split('SYSTEM_COMMAND_ITR_')[-1].split('.')[0]
            sheet_name = f"ITR-{iteration}"
            ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.create_sheet(title=sheet_name)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            blocks = parse_blocks(content)
            for block in blocks:
                ws.append([block['label']])
                ws.append(header)
                for row in block['rows']:
                    ws.append(row)
                if block['average']:
                    ws.append(block['average'])
                ws.append([])

        tmp_name = f"system_command_consolidated_{job_id}.xlsx"
        tmp_path = os.path.join('/tmp', tmp_name)
        wb.save(tmp_path)

        return send_file(tmp_path, as_attachment=True, download_name=tmp_name)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# DEVICE LOCK ENDPOINTS
# =============================================================================

@app.route('/api/locks', methods=['GET'])
@login_required
def get_locks():
    """Get all device locks"""
    try:
        DeviceLock.cleanup_expired_locks()
        devices = Device.load_all()
        DeviceLock.cleanup_expired_locks()
        device_list = []
        selected_team = request.args.get('team') if current_user.is_admin else current_user.team_name
        for device in devices:
            device_dict = device.to_dict()
            lock = DeviceLock.get_device_lock(device.ip)
            if lock:
                lock_dict = lock.to_dict() if hasattr(lock, 'to_dict') else lock
                device_dict['locked'] = True
                device_dict['locked_by'] = lock_dict['user_id']
                device_dict['job_id'] = lock_dict['job_id']
                device_dict['estimated_completion'] = lock_dict['estimated_completion']
                device_dict['eta'] = lock_dict.get('eta_formatted', 'Unknown')
            else:
                device_dict['locked'] = False
                device_dict['locked_by'] = None
                device_dict['job_id'] = None
                device_dict['estimated_completion'] = None
                device_dict['eta'] = None
            # Filter devices by team unless admin viewing all
            if current_user.is_admin:
                if selected_team and device_dict.get('team_name') != selected_team:
                    continue
            else:
                if device_dict.get('team_name') != current_user.team_name:
                    continue
            device_list.append(device_dict)
        return render_template('index.html', devices=device_list, user=current_user, selected_team=selected_team)
        estimated_duration_seconds = data.get('estimated_duration_seconds', 300)
        
        if not device_ip or not job_id:
            return jsonify({'success': False, 'error': 'device_ip and job_id are required'}), 400
        
        # Check if already locked
        if DeviceLock.is_device_locked(device_ip):
            lock = DeviceLock.get_device_lock(device_ip)
            return jsonify({
                'success': False, 
                'error': f'Device already locked by {lock["user_id"]}',
                'lock': lock
            }), 409
        
        lock = DeviceLock.lock_device(
            device_ip=device_ip,
            device_name=device_name,
            user_id=current_user.ntid,
            job_id=job_id,
            estimated_duration_seconds=estimated_duration_seconds
        )
        
        return jsonify({'success': True, 'lock': lock})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/locks/unlock', methods=['POST'])
@login_required
def unlock_device():
    """Unlock a device"""
    try:
        data = request.json
        device_ip = data.get('device_ip')
        
        if not device_ip:
            return jsonify({'success': False, 'error': 'device_ip is required'}), 400
        
        success = DeviceLock.unlock_device(device_ip)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Device not locked or lock not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/locks/cleanup', methods=['POST'])
@login_required
def cleanup_locks():
    """Remove all expired locks"""
    try:
        count = DeviceLock.cleanup_expired_locks()
        return jsonify({'success': True, 'cleaned_locks': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# LOG PATTERN MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/log-patterns', methods=['GET'])
@login_required
def log_patterns_page():
    """Display log patterns management page"""
    return render_template('log_patterns.html', current_user=current_user)

@app.route('/api/log-patterns/summary', methods=['GET'])
@login_required
def get_log_patterns_summary():
    """Get summary of log patterns"""
    try:
        from controllers.log_pattern_controller import LogPatternController
        summary = LogPatternController.get_pattern_summary()
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/approved', methods=['GET'])
@login_required
def get_approved_patterns():
    """Get all approved log patterns"""
    try:
        from controllers.log_pattern_controller import LogPatternController
        patterns = LogPatternController.get_approved_patterns()
        return jsonify({'success': True, 'data': patterns})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/existing', methods=['GET'])
@login_required
def get_existing_patterns():
    """Get existing patterns from both config file and approved submissions"""
    try:
        from controllers.log_pattern_controller import LogPatternController

        approved_patterns = LogPatternController.get_approved_patterns()
        return jsonify({'success': True, 'data': approved_patterns})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/pending', methods=['GET'])
@login_required
def get_pending_patterns():
    """Get all pending submissions (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.log_pattern_controller import LogPatternController
        pending = LogPatternController.get_pending_submissions()
        return jsonify({'success': True, 'data': pending})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/submit', methods=['POST'])
@login_required
def submit_log_pattern():
    """Submit a new log pattern for validation"""
    try:
        data = request.json
        
        pattern_name = data.get('pattern_name', '').strip()
        log_pattern = data.get('log_pattern', '').strip()
        file_path = data.get('file_path', '').strip()
        description = data.get('description', '').strip()
        
        if not pattern_name or not log_pattern or not file_path:
            return jsonify({
                'success': False,
                'message': 'Pattern name, log pattern, and file path are required'
            }), 400
        
        from controllers.log_pattern_controller import LogPatternController
        
        success, message, submission_id = LogPatternController.submit_log_pattern(
            pattern_name=pattern_name,
            log_pattern=log_pattern,
            file_path=file_path,
            description=description,
            submitted_by_user=current_user.ntid,
            is_admin=current_user.is_admin
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'submission_id': submission_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': message
            }), 400
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False, 
            'error': error_msg,
            'message': f'Error submitting pattern: {error_msg}'
        }), 500

@app.route('/api/log-patterns/submit-existing-edit', methods=['POST'])
@login_required
def submit_existing_edit():
    """Submit edits to an existing (system) pattern for admin approval"""
    try:
        data = request.get_json(silent=True) or {}
        
        pattern_name = data.get('pattern_name', '').strip()
        log_pattern = data.get('log_pattern', '').strip()
        file_path = data.get('file_path', '').strip()
        description = data.get('description', '').strip()
        change_reason = data.get('change_reason', '').strip()
        base_pattern = data.get('base_pattern', '').strip()
        
        if not pattern_name or not log_pattern or not file_path or not change_reason:
            return jsonify({
                'success': False,
                'message': 'Pattern name, log pattern, file path, and reason for change are required'
            }), 400
        
        from controllers.log_pattern_controller import LogPatternController
        
        # Submit as a new submission with a modified name to indicate it's an edit
        edit_submission_name = f"{pattern_name}_EDIT"
        
        success, message, submission_id = LogPatternController.submit_log_pattern(
            pattern_name=edit_submission_name,
            log_pattern=log_pattern,
            file_path=file_path,
            description=f"{description}\n\n[EDIT REQUEST for '{base_pattern}']\nReason: {change_reason}",
            submitted_by_user=current_user.ntid,
            is_admin=False  # Non-admin edit requests go to approval queue
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'submission_id': submission_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': message
            }), 400
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False, 
            'error': error_msg,
            'message': f'Error submitting changes: {error_msg}'
        }), 500

@app.route('/api/log-patterns/<pattern_name>/modify', methods=['POST'])
@login_required
def modify_log_pattern(pattern_name):
    """Modify an approved log pattern (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json(silent=True) or {}
        
        new_log_pattern = data.get('log_pattern', '').strip()
        new_file_path = data.get('file_path', '').strip()
        new_description = data.get('description', '').strip()
        
        if not new_log_pattern or not new_file_path:
            return jsonify({
                'success': False,
                'message': 'Log pattern and file path are required'
            }), 400
        
        from controllers.log_pattern_controller import LogPatternController
        
        success, message = LogPatternController.modify_approved_pattern(
            pattern_name=pattern_name,
            new_log_pattern=new_log_pattern,
            new_file_path=new_file_path,
            new_description=new_description
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': message
            }), 400
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False, 
            'error': error_msg,
            'message': f'Error modifying pattern: {error_msg}'
        }), 500

@app.route('/api/log-patterns/<pattern_name>/delete', methods=['POST'])
@login_required
def delete_log_pattern(pattern_name):
    """Delete an approved log pattern (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.log_pattern_controller import LogPatternController
        
        success, message = LogPatternController.delete_approved_pattern(pattern_name)
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/<submission_id>/approve', methods=['POST'])
@login_required
def approve_log_pattern_submission(submission_id):
    """Approve a pending log pattern submission (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.log_pattern_controller import LogPatternController
        
        success, message = LogPatternController.approve_submission(submission_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message,
                'error': message
            }), 400
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False, 
            'error': error_msg,
            'message': f'Error approving submission: {error_msg}'
        }), 500

@app.route('/api/log-patterns/<submission_id>/reject', methods=['POST'])
@login_required
def reject_log_pattern_submission(submission_id):
    """Reject a pending log pattern submission (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.json
        rejection_reason = data.get('rejection_reason', 'No reason provided').strip()
        
        from controllers.log_pattern_controller import LogPatternController
        
        success, message = LogPatternController.reject_submission(submission_id, rejection_reason)
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/validate-file', methods=['POST'])
@login_required
def validate_log_file():
    """Validate if a log file exists at the specified path"""
    try:
        data = request.json
        file_path = data.get('file_path', '').strip()
        
        if not file_path:
            return jsonify({
                'success': False,
                'message': 'File path is required'
            }), 400
        
        from controllers.log_pattern_controller import LogPatternController
        
        file_exists, message, expanded_path = LogPatternController.validate_file_exists(file_path)
        
        return jsonify({
            'success': file_exists,
            'message': message,
            'file_path': expanded_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/log-patterns/validate-regex', methods=['POST'])
@login_required
def validate_log_regex():
    """Validate if a regex pattern is valid"""
    try:
        data = request.json
        pattern = data.get('pattern', '').strip()
        
        if not pattern:
            return jsonify({
                'success': False,
                'message': 'Pattern is required'
            }), 400
        
        from controllers.log_pattern_controller import LogPatternController
        
        is_valid, message = LogPatternController.validate_log_pattern(pattern)
        
        return jsonify({
            'success': is_valid,
            'message': message
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# SYSTEM COMMANDS API ENDPOINTS
# =============================================================================

@app.route('/api/system-commands', methods=['GET'])
@login_required
def get_system_commands():
    """Get all system commands (builtin, approved, and pending)"""
    try:
        from controllers.system_commands_controller import SystemCommandsController
        
        builtin = SystemCommandsController.get_builtin_commands()
        approved = SystemCommandsController.get_approved_commands()
        
        # Show pending only to admins
        pending = {}
        if current_user.is_admin:
            pending = SystemCommandsController.get_pending_submissions()
        
        commands = {
            'builtin': builtin,
            'approved': approved,
            'pending': pending
        }
        return jsonify({'success': True, 'data': commands}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system-commands/submit', methods=['POST'])
@login_required
def submit_system_command():
    """Submit a new system command for approval"""
    try:
        data = request.get_json(silent=True) or {}
        
        command_name = data.get('command_name', '').strip()
        command_text = data.get('command_text', '').strip()
        description = data.get('description', '').strip()
        
        if not command_name or not command_text:
            return jsonify({
                'success': False,
                'message': 'Command name and command text are required'
            }), 400
        
        from controllers.system_commands_controller import SystemCommandsController
        
        success, message, submission_id = SystemCommandsController.submit_command(
            command_name=command_name,
            command_text=command_text,
            description=description,
            submitted_by=current_user.ntid,
            is_admin=current_user.is_admin
        )
        
        return jsonify({
            'success': success,
            'message': message,
            'submission_id': submission_id
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error submitting command: {error_msg}'
        }), 500

@app.route('/api/system-commands/pending', methods=['GET'])
@login_required
def get_pending_system_commands():
    """Get pending system command submissions (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.system_commands_controller import SystemCommandsController
        pending = SystemCommandsController.get_pending_submissions()
        return jsonify({'success': True, 'data': pending}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system-commands/approve/<submission_id>', methods=['POST'])
@login_required
def approve_system_command(submission_id):
    """Approve a pending system command submission (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.system_commands_controller import SystemCommandsController
        
        success, message = SystemCommandsController.approve_submission(submission_id)
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error approving command: {error_msg}'
        }), 500

@app.route('/api/system-commands/reject/<submission_id>', methods=['POST'])
@login_required
def reject_system_command(submission_id):
    """Reject a pending system command submission (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json(silent=True) or {}
        rejection_reason = data.get('rejection_reason', '')
        
        from controllers.system_commands_controller import SystemCommandsController
        
        success, message = SystemCommandsController.reject_submission(submission_id, rejection_reason)
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error rejecting command: {error_msg}'
        }), 500

@app.route('/api/system-commands/promote/<command_name>', methods=['POST'])
@login_required
def promote_system_command_to_config(command_name):
    """Promote an approved system command to config (make it builtin) - admin only"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.system_commands_controller import SystemCommandsController
        
        success, message = SystemCommandsController.promote_to_config(command_name)
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error promoting command: {error_msg}'
        }), 500

# Legacy endpoints - deprecated (kept for backward compatibility)
@app.route('/api/system-commands/add', methods=['POST'])
@login_required
def add_system_command():
    """DEPRECATED: Use /api/system-commands/submit instead"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json(silent=True) or {}
        
        command_name = data.get('command_name', '').strip()
        command_text = data.get('command_text', '').strip()
        description = data.get('description', '').strip()
        
        if not command_name or not command_text:
            return jsonify({
                'success': False,
                'message': 'Command name and command text are required'
            }), 400
        
        from controllers.system_commands_controller import SystemCommandsController
        
        # For backward compatibility, admin submissions bypass approval
        success, message, _ = SystemCommandsController.submit_command(
            command_name=command_name,
            command_text=command_text,
            description=description,
            submitted_by=current_user.ntid,
            is_admin=True
        )
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error adding command: {error_msg}'
        }), 500

@app.route('/api/system-commands/<command_name>/update', methods=['POST'])
@login_required
def update_system_command(command_name):
    """DEPRECATED: Update existing approved commands"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json(silent=True) or {}
        
        command_text = data.get('command_text', '').strip()
        description = data.get('description', '').strip()
        
        if not command_text:
            return jsonify({
                'success': False,
                'message': 'Command text is required'
            }), 400
        
        from controllers.system_commands_controller import SystemCommandsController
        
        success, message = SystemCommandsController.update_command(
            command_name=command_name,
            command_text=command_text,
            description=description
        )
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error updating command: {error_msg}'
        }), 500

@app.route('/api/system-commands/<command_name>/delete', methods=['POST'])
@login_required
def delete_system_command(command_name):
    """DEPRECATED: Delete existing approved commands"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        from controllers.system_commands_controller import SystemCommandsController
        
        success, message = SystemCommandsController.delete_command(command_name)
        
        return jsonify({
            'success': success,
            'message': message
        }), (200 if success else 400)
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg,
            'message': f'Error deleting command: {error_msg}'
        }), 500

# =============================================================================
# GLOBAL ERROR HANDLERS - Prevent DOCTYPE XML/JSON parsing errors
# =============================================================================

@app.errorhandler(400)
def handle_bad_request(error):
    """Handle 400 Bad Request - return JSON instead of HTML"""
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
    }), 400

@app.errorhandler(404)
def handle_not_found(error):
    """Handle 404 Not Found - return JSON instead of HTML"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 Internal Server Error - return JSON instead of HTML"""
    import traceback
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error.description) if hasattr(error, 'description') else 'An unexpected error occurred',
        'traceback': traceback.format_exc()
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Catch-all handler for any unhandled exceptions - return JSON"""
    import traceback
    print(f"❌ [UNHANDLED EXCEPTION] {type(error).__name__}: {str(error)}")
    print(f"Traceback:\n{traceback.format_exc()}")
    
    return jsonify({
        'error': type(error).__name__,
        'message': str(error),
        'traceback': traceback.format_exc()
    }), 500

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    from datetime import datetime
    is_production = os.environ.get('FLASK_ENV') == 'production'
    debug_mode = not is_production
    use_reloader = False
    
    # Allow host/port override via environment variables (default to 0.0.0.0 for network access)
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 11079))

    print(f"\n{'='*60}")
    print(f"FLASK STARTUP CONFIGURATION")
    print(f"{'='*60}")
    print(f"Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Auto Reload: {use_reloader}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"{'='*60}\n")

    app.run(debug=debug_mode, host=host, port=port, use_reloader=use_reloader, threaded=True)

