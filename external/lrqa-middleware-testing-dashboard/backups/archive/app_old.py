#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, Response
import json
import os
import paramiko
import threading
import queue
import time
import re
import socket
import logging
import warnings
from datetime import datetime, timezone, timedelta

# Suppress Paramiko's verbose logging and warnings
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=ResourceWarning)

# Import configuration files
from config_commands import *
from config_log_patterns import *
from config_ir_blaster import *
from config_timing import *
from config_screenshot import *

# Import screenshot utilities
from screenshot_utils import get_screen_state, take_and_analyze_screenshot

# Import method implementations
from method_reboot import execute_reboot_process
from method_deepsleep import execute_deepsleep_process
from method_ir_test import execute_ir_test_process

app = Flask(__name__)

# USB stick configuration for Raspberry Pi (Linux)
USB_BASE_PATH = "/media/pi/Lexar"
USB_ENHANCEMENT_OUTPUT = "Enhancement-output"

# Path to store device IPs
DEVICES_FILE = 'devices.json'

# Shared real-time log file for streaming across workers
REALTIME_LOG_FILE = os.path.join(os.path.dirname(__file__), 'realtime_logs.txt')

# Persistent storage for test results (3 days retention)
RESULTS_STORAGE_FILE = os.path.join(os.path.dirname(__file__), 'test_results_history.json')
RESULTS_RETENTION_DAYS = 3

# Queue for operation logs (kept for backward compatibility)
log_queue = queue.Queue()

# Execution Queue System - for scheduling multiple test rounds
execution_queue = queue.Queue()
execution_queue_lock = threading.Lock()
queue_processor_thread = None
queue_running = False
queued_jobs = []  # List to track queued jobs for UI display

# Thread-local storage for execution session paths (prevents cross-contamination between concurrent executions)
thread_local = threading.local()

# Global variables for current execution session (legacy - being phased out)
current_session_folder = None
current_screenshots_dir = None
current_execution_logs_dir = None
current_device_logs_dir = None
current_log_file = None
current_log_handle = None
current_html_results = []

# Track last execution context for consolidated results page
last_device_ip = None
last_method = None
last_iterations = 0
# Track multi-device results history across executions
device_results_history = {}

def create_execution_session_folder(method, device_name, device_ip, iterations):
    """Create main execution session folder with structure:
    <METHOD>_<DEVICENAME>_<IP>_<ITERATIONS>_ITR_<UTC_TIMESTAMP>
    
    Returns tuple: (session_folder, screenshots_dir, execution_logs_dir, device_logs_dir)
    """
    global current_session_folder, current_screenshots_dir, current_execution_logs_dir, current_device_logs_dir
    
    # Clean device name for folder
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').upper()
    safe_ip = device_ip.replace('.', '-')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
    
    # Create session folder name: REBOOT_ELEMENT-A4K_10-0-0-172_20_ITR_20231119_143022_UTC
    session_name = f"{method.upper()}_{safe_device_name}_{safe_ip}_{iterations}_ITR_{timestamp}"
    
    # Determine base path
    import sys
    if sys.platform.startswith('linux') and os.path.exists(USB_BASE_PATH):
        base_output = os.path.join(USB_BASE_PATH, USB_ENHANCEMENT_OUTPUT)
        print(f"[INFO] Using USB stick: {base_output}")
    else:
        base_output = USB_ENHANCEMENT_OUTPUT
        print(f"[INFO] Using local directory: {base_output}")
    
    # Create main session folder
    session_folder = os.path.join(base_output, session_name)
    
    # Create subfolders
    screenshots_dir = os.path.join(session_folder, "SCREENSHOTS")
    execution_logs_dir = os.path.join(session_folder, "EXECUTION_LOGS")
    device_logs_dir = os.path.join(session_folder, "DEVICE_LOGS")
    
    # Create all directories
    for folder in [session_folder, screenshots_dir, execution_logs_dir, device_logs_dir]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"[INFO] Created folder: {folder}")
    
    # Store in thread-local storage (prevents cross-contamination)
    thread_local.session_folder = session_folder
    thread_local.screenshots_dir = screenshots_dir
    thread_local.execution_logs_dir = execution_logs_dir
    thread_local.device_logs_dir = device_logs_dir
    
    # Also store in global variables for backward compatibility
    current_session_folder = session_folder
    current_screenshots_dir = screenshots_dir
    current_execution_logs_dir = execution_logs_dir
    current_device_logs_dir = device_logs_dir
    
    return session_folder, screenshots_dir, execution_logs_dir, device_logs_dir

def load_devices():
    """Load device IPs from JSON file"""
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_devices(devices):
    """Save device IPs to JSON file"""
    with open(DEVICES_FILE, 'w') as f:
        json.dump(devices, f, indent=4)

def load_test_results():
    """Load test results from persistent storage and clean up old data (>3 days)"""
    if not os.path.exists(RESULTS_STORAGE_FILE):
        return []
    
    try:
        with open(RESULTS_STORAGE_FILE, 'r') as f:
            all_results = json.load(f)
        
        # Filter results within retention period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=RESULTS_RETENTION_DAYS)
        filtered_results = []
        
        for result in all_results:
            result_date = result.get('timestamp', '')
            if result_date:
                try:
                    result_dt = datetime.fromisoformat(result_date.replace('Z', '+00:00'))
                    if result_dt >= cutoff_date:
                        filtered_results.append(result)
                except:
                    # Keep results with invalid dates to avoid data loss
                    filtered_results.append(result)
            else:
                # Keep results without timestamp
                filtered_results.append(result)
        
        # Save cleaned results back if we removed any
        if len(filtered_results) < len(all_results):
            save_test_results(filtered_results)
        
        return filtered_results
    except Exception as e:
        log_message(f"Error loading test results: {e}")
        return []

def save_test_results(results):
    """Save test results to persistent storage"""
    try:
        with open(RESULTS_STORAGE_FILE, 'w') as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        log_message(f"Error saving test results: {e}")

def log_message(message, write_to_file=True):
    """Add a log message to the queue with UTC timestamp and shared realtime log"""
    timestamp = datetime.now(timezone.utc).strftime('[%Y-%m-%d %H:%M:%S UTC]')
    formatted_message = f"{timestamp} {message}"
    log_queue.put(formatted_message)
    
    # Write to shared realtime log file for cross-worker streaming
    try:
        with open(REALTIME_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(formatted_message + '\n')
            f.flush()
            os.fsync(f.fileno())  # Force write to disk immediately
    except Exception as e:
        pass  # Don't let logging errors crash the app
    
    # Also write to execution-specific file if enabled
    if write_to_file and current_log_handle:
        try:
            current_log_handle.write(formatted_message + '\n')
            current_log_handle.flush()
        except:
            pass

def create_iteration_log_file(device_ip, method):
    """Create a new log file for the current execution in EXECUTION_LOGS folder"""
    global current_log_file, current_log_handle, current_execution_logs_dir
    
    # Close previous log file if open
    if current_log_handle:
        try:
            current_log_handle.close()
        except:
            pass
    
    # Create new log file with timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
    filename = f"{device_ip}_{method}_{timestamp}.log"
    
    # Use thread-local execution logs directory if available
    execution_logs_dir = getattr(thread_local, 'execution_logs_dir', current_execution_logs_dir)
    if execution_logs_dir and os.path.exists(execution_logs_dir):
        filepath = os.path.join(execution_logs_dir, filename)
    else:
        # Fallback to legacy location
        logs_dir = 'iteration_logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        filepath = os.path.join(logs_dir, filename)
    
    current_log_file = filepath
    current_log_handle = open(filepath, 'w', encoding='utf-8')
    
    # Write header
    header = f"""{'='*80}
DEVICE OPERATION LOG
{'='*80}
Device IP: {device_ip}
Method: {method}
Start Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
{'='*80}

"""
    current_log_handle.write(header)
    current_log_handle.flush()
    
    return filepath

def close_iteration_log_file():
    """Close the current iteration log file"""
    global current_log_handle
    
    if current_log_handle:
        try:
            footer = f"""
{'='*80}
End Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
{'='*80}
"""
            current_log_handle.write(footer)
            current_log_handle.flush()
            current_log_handle.close()
            current_log_handle = None
        except:
            pass

def generate_html_report(device_ip, method, html_results):
    """Generate HTML report with iteration results in EXECUTION_LOGS folder"""
    global current_execution_logs_dir
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
    html_filename = f"{device_ip}_{method}_{timestamp}.html"
    
    # Use execution logs directory if available
    if current_execution_logs_dir and os.path.exists(current_execution_logs_dir):
        html_output_path = os.path.join(current_execution_logs_dir, html_filename)
    else:
        # Fallback
        logs_dir = 'iteration_logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        html_output_path = os.path.join(logs_dir, html_filename)
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Device Reboot & DeepSleep Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        h1 { color: #333; }
        .info { background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .info p { margin: 5px 0; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        tr:hover { background-color: #e8f5e9; }
        .passed { color: green; font-weight: bold; }
        .failed { color: red; font-weight: bold; }
        .warning { color: orange; font-weight: bold; }
        .footer { margin-top: 30px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <h1>Device Reboot & DeepSleep Test Execution Results</h1>
    <div class="info">
        <p><strong>Device IP:</strong> """ + device_ip + """</p>
        <p><strong>Method:</strong> """ + method.upper() + """</p>
        <p><strong>Generated:</strong> """ + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
        <p><strong>Total Iterations:</strong> """ + str(len(html_results)) + """</p>
    </div>
    <table>
        <tr>
            <th>Iteration</th>
            <th>Phase</th>
            <th>Status</th>
            <th>Details</th>
            <th>Screenshots</th>
            <th>Logs</th>
        </tr>
"""
    
    for result in html_results:
        status_class = 'passed' if result['status'] == 'PASSED' else ('warning' if result['status'] == 'WARNING' else 'failed')
        html_content += f"""        <tr>
            <td>{result['iteration']}</td>
            <td>{result['phase']}</td>
            <td class="{status_class}">{result['status']}</td>
            <td>{result['details']}</td>
            <td>{result['screenshots']}</td>
            <td>{result['logs']}</td>
        </tr>
"""
    # Compute overall iteration status summary
    iteration_status = {}
    for r in html_results:
        itr = r['iteration']
        # Initialize as PASSED; downgrade on FAILURE
        if itr not in iteration_status:
            iteration_status[itr] = 'PASSED'
        if r['status'] == 'FAILED':
            iteration_status[itr] = 'FAILED'
        elif r['status'] == 'WARNING' and iteration_status[itr] != 'FAILED':
            iteration_status[itr] = 'WARNING'

    html_content += "    </table>\n"
    html_content += "    <h2>Iteration Summary</h2>\n"
    html_content += "    <ul>\n"
    for itr in sorted(iteration_status.keys()):
        status = iteration_status[itr]
        status_class = 'passed' if status == 'PASSED' else ('warning' if status == 'WARNING' else 'failed')
        html_content += f"        <li><span class='{status_class}'>Iteration {itr}: {status}</span> &mdash; Method: {method.upper()}</li>\n"
    html_content += "    </ul>\n"
    
    html_content += """    <div class="footer">\n        <p>Generated by Device Test Automation System</p>\n    </div>\n</body>\n</html>"""
    
    try:
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log_message(f"✓ HTML report generated: {html_output_path}")
        return html_output_path
    except Exception as e:
        log_message(f"❌ Error generating HTML report: {e}")
        return None

def add_html_result(iteration, phase, status, details, screenshots="", logs="", device_ip=None, method=None):
    """Add a result entry to the HTML results list and persistent storage"""
    global current_html_results, device_results_history, last_device_ip, last_method
    
    # Use provided device_ip and method, or fall back to global variables
    result_device_ip = device_ip or last_device_ip or 'N/A'
    result_method = method or last_method or 'unknown'
    
    # Create timestamp and date
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    date_str = now.strftime('%Y-%m-%d')
    
    entry = {
        'iteration': iteration,
        'phase': phase,
        'status': status,
        'details': details,
        'screenshots': screenshots,
        'logs': logs,
        'timestamp': timestamp,
        'date': date_str,
        'device_ip': result_device_ip,
        'method': result_method
    }
    current_html_results.append(entry)
    
    # Add to in-memory device history
    if result_device_ip and result_device_ip != 'N/A':
        if result_device_ip not in device_results_history:
            device_results_history[result_device_ip] = []
        device_results_history[result_device_ip].append(dict(entry))
    
    # Save to persistent storage
    try:
        all_results = load_test_results()
        all_results.append(entry)
        save_test_results(all_results)
    except Exception as e:
        log_message(f"Error saving result to persistent storage: {e}")

def test_ssh_connection(ip, port, username, password):
    """Test SSH connection to device"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=username, password=password, timeout=10)
        ssh.close()
        return True, "Connection successful", None
    except Exception as e:
        return False, str(e), None

def execute_method(device_ip, methods, iterations, username, password, port=10022, device_name="Device", selected_ir_keys=None):
    """Execute the selected method(s) on the device
    
    Args:
        methods: Single method string or list of methods to execute in sequence
        device_name: Device name for screenshot folder naming
        selected_ir_keys: List of IR keys to test for IR Command Test method
    """
    # Default to both keys if none specified
    if selected_ir_keys is None:
        selected_ir_keys = ['HOME', 'POWER']
    global current_html_results
    
    # Convert single method to list for uniform processing
    if isinstance(methods, str):
        methods_list = [methods]
    else:
        methods_list = methods
    
    # Reset HTML results for new execution and record context
    current_html_results = []
    global last_device_ip, last_method, last_iterations
    last_device_ip = device_ip
    last_method = ','.join(methods_list)
    last_iterations = iterations
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # CREATE EXECUTION SESSION FOLDER STRUCTURE
    method_name = methods_list[0] if len(methods_list) == 1 else "sequence"
    session_folder, screenshots_dir, exec_logs_dir, device_logs_dir = create_execution_session_folder(
        method_name, device_name, device_ip, iterations
    )
    log_message(f"✓ Created session folder: {session_folder}")
    log_message(f"  - Screenshots: {screenshots_dir}")
    log_message(f"  - Execution Logs: {exec_logs_dir}")
    log_message(f"  - Device Logs: {device_logs_dir}")
    
    # Create iteration log file in the execution logs folder
    log_file = create_iteration_log_file(device_ip, method_name)
    log_message(f"Iteration log file created: {log_file}")
    
    log_message(f"Starting execution on device {device_ip}")
    if len(methods_list) > 1:
        log_message(f"Method Sequence: {' -> '.join(methods_list)}, Iterations: {iterations}")
    else:
        log_message(f"Method: {methods_list[0]}, Iterations: {iterations}")
    log_message("=" * 60)
    
    for i in range(iterations):
        log_message(f"\n{'='*60}")
        log_message(f"ITERATION {i+1}/{iterations}")
        log_message(f"{'='*60}")
        
        # Execute each method in the sequence
        for method_index, method in enumerate(methods_list):
            if len(methods_list) > 1:
                log_message(f"\n--- Executing method {method_index+1}/{len(methods_list)}: {method.upper()} ---")
            
            if method == "reboot":
                success = execute_reboot_process(device_ip, port, username, password, iteration=i+1, device_name=device_name)
                if not success:
                    log_message(f"❌ Reboot process failed at iteration {i+1}")
                    break
                    
            elif method == "deepsleep":
                # Skip pre-validation if DeepSleep is not the first method in sequence
                skip_pre_validation = (len(methods_list) > 1 and method_index > 0)
                success = execute_deepsleep_process(device_ip, port, username, password, iteration=i+1, skip_pre_validation=skip_pre_validation, device_name=device_name)
                if not success:
                    log_message(f"❌ Deep Sleep process failed at iteration {i+1}")
                    break
                    
            elif method == "power_key":
                try:
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(device_ip, port=port, username=username, password=password)
                    
                    # Fetch build details from device
                    fetch_build_details(ssh, log_message)
                    
                    # Activate ScreenCapture service immediately after connection
                    log_message("Activating ScreenCapture service...")
                    activate_screencapture_service(ssh, log_message)
                    
                    # Check device power state before sending power key
                    log_message(f"[POWER KEY] Checking device power state...")
                    stdin, stdout, stderr = ssh.exec_command(device_status_command)
                    device_status = stdout.read().decode('utf-8', errors='ignore').strip()
                    log_message(f"Device power state: {device_status}")
                    
                    # Only send power key if device is in STANDBY
                    if "STANDBY" in device_status:
                        log_message(f"[POWER KEY] Device is in STANDBY - Sending power key command to turn ON...")
                        stdin, stdout, stderr = ssh.exec_command(power_key_command)
                        log_message(f"✓ Power key command sent to device")
                        error_output = stderr.read().decode('utf-8', errors='ignore')
                        if error_output:
                            log_message(f"⚠ Error: {error_output}")
                        
                        # Wait for device state to stabilize
                        time.sleep(3)
                        
                        # Capture screenshot after power key
                        screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, i+1, "After")
                        screenshot_name = f"{device_ip}_{safe_device_name}_AfterPowerKey_{timestamp}"
                        log_message(f"[SCREENSHOT] Capturing device state after Power Key...")
                        screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)
                        
                        if screenshot_result and screenshot_result.get('success'):
                            log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path')}")
                        else:
                            log_message(f"⚠ Screenshot capture failed or incomplete")
                    else:
                        log_message(f"⚠ Device is not in STANDBY (current state: {device_status}) - Skipping power key command")
                        log_message(f"ℹ Power key is only executed when device is in STANDBY state")
                        # NOTE: Can be used later - If device is ON → puts it in STANDBY (off)
                        # Uncomment below to enable power key when device is ON:
                        # if "ON" in device_status:
                        #     log_message(f"[POWER KEY] Device is ON - Sending power key to put in STANDBY...")
                        #     stdin, stdout, stderr = ssh.exec_command(power_key_command)
                        #     time.sleep(3)
                        #     screenshot_name = f"ITR-{i+1}_AfterPowerKey_{timestamp}"
                        #     screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message)
                    
                    ssh.close()
                except Exception as e:
                    log_message(f"❌ Error in power key operation: {e}")
                    
            elif method == "status":
                try:
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(device_ip, port=port, username=username, password=password)
                    
                    # Fetch build details from device
                    fetch_build_details(ssh, log_message)
                    
                    # Activate ScreenCapture service immediately after connection
                    log_message("Activating ScreenCapture service...")
                    activate_screencapture_service(ssh, log_message)
                    
                    log_message(f"[STATUS CHECK] Querying device power state...")
                    stdin, stdout, stderr = ssh.exec_command(device_status_command)
                    output = stdout.read().decode('utf-8', errors='ignore')
                    log_message(f"Device status: {output.strip()}")
                    
                    # Capture screenshot after status check
                    screenshot_folder = create_screenshot_folder(device_ip, safe_device_name, i+1, "After")
                    screenshot_name = f"{device_ip}_{safe_device_name}_AfterStatusCheck_{timestamp}"
                    log_message(f"[SCREENSHOT] Capturing device state after Status Check...")
                    screenshot_result = take_and_analyze_screenshot(ssh, screenshot_name, device_ip, log_message, screenshot_folder)
                    
                    if screenshot_result and screenshot_result.get('success'):
                        log_message(f"✓ Screenshot saved: {screenshot_result.get('local_path')}")
                    else:
                        log_message(f"⚠ Screenshot capture failed or incomplete")
                    
                    ssh.close()
                except Exception as e:
                    log_message(f"❌ Error checking device status: {e}")
                    
            elif method == "ir_test":
                success = execute_ir_test_process(device_ip, port, username, password, iteration=i+1, device_name=device_name, selected_keys=selected_ir_keys)
                if not success:
                    log_message(f"⚠ IR test completed with warnings at iteration {i+1}")
    
    log_message(f"\n{'='*60}")
    log_message(f"✓ Execution completed - {iterations} iteration(s) finished")
    log_message(f"Log file saved at: {log_file}")
    log_message(f"{'='*60}")
    
    # Generate HTML report
    if method in ["reboot", "deepsleep"] and current_html_results:
        html_file = generate_html_report(device_ip, method, current_html_results)
        if html_file:
            log_message(f"HTML report saved at: {html_file}")
    
    # Close the iteration log file
    close_iteration_log_file()

@app.route('/')
def index():
    """Render the main page"""
    devices = load_devices()
    return render_template('index.html', devices=devices)

@app.route('/api/devices', methods=['GET', 'POST', 'DELETE'])
def manage_devices():
    """Manage device IPs"""
    if request.method == 'GET':
        devices = load_devices()
        return jsonify(devices)
    
    elif request.method == 'POST':
        data = request.json
        ip = data.get('ip')
        name = data.get('name', ip)
        
        if not ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        devices = load_devices()
        
        # Check if IP already exists
        if any(d['ip'] == ip for d in devices):
            return jsonify({'error': 'IP address already exists'}), 400
        
        devices.append({
            'ip': ip,
            'name': name,
            'port': data.get('port', 10022),
            'username': data.get('username', 'root'),
            'password': data.get('password', ''),
            # Optional IR blaster configuration overrides per device
            'itach_ip': data.get('itach_ip', '10.0.0.12'),
            'itach_port': data.get('itach_port', 4998),
            'ir_port': data.get('ir_port', 2)
        })
        
        save_devices(devices)
        return jsonify({'message': 'Device added successfully', 'devices': devices})
    
    elif request.method == 'DELETE':
        data = request.json
        ip = data.get('ip')
        
        devices = load_devices()
        devices = [d for d in devices if d['ip'] != ip]
        save_devices(devices)
        
        return jsonify({'message': 'Device removed successfully', 'devices': devices})

@app.route('/api/execute', methods=['POST'])
def execute():
    """Execute the selected method(s) on device"""
    data = request.json
    device_ip = data.get('device_ip')
    method = data.get('method')  # Can be single method or list of methods
    iterations = int(data.get('iterations', 1))
    selected_ir_keys = data.get('selected_ir_keys', ['HOME', 'POWER'])  # Get selected IR keys from frontend
    
    # Get device credentials
    devices = load_devices()
    device = next((d for d in devices if d['ip'] == device_ip), None)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Clear log queue
    while not log_queue.empty():
        log_queue.get()
    
    # Clear the shared realtime log file for new execution
    try:
        with open(REALTIME_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write('')
    except:
        pass
    
    # Execute in background thread
    thread = threading.Thread(
        target=execute_method,
        args=(device_ip, method, iterations, device['username'], device['password'], device.get('port', 10022), device.get('name', 'Device'), selected_ir_keys)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Execution started'})

def process_execution_queue():
    """Background worker to process queued test executions sequentially"""
    global queue_running
    
    while queue_running:
        try:
            # Get next job from queue (blocks until available or timeout)
            job = execution_queue.get(timeout=1)
            
            if job is None:  # Poison pill to stop the processor
                break
            
            # Remove from queued_jobs list
            with execution_queue_lock:
                queued_jobs[:] = [j for j in queued_jobs if j['id'] != job['id']]
            
            log_message(f"[QUEUE] Starting job {job['id']}: {job['device_name']} - {job['method']} ({job['iterations']} iterations)")
            
            # Execute the test
            execute_method(
                job['device_ip'],
                job['method'],
                job['iterations'],
                job['username'],
                job['password'],
                job['port'],
                job['device_name'],
                job.get('selected_ir_keys', ['HOME', 'POWER'])
            )
            
            log_message(f"[QUEUE] Completed job {job['id']}")
            execution_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            log_message(f"[QUEUE] Error processing job: {e}")
            try:
                execution_queue.task_done()
            except:
                pass

def start_queue_processor():
    """Start the queue processor thread if not already running"""
    global queue_processor_thread, queue_running
    
    if queue_processor_thread is None or not queue_processor_thread.is_alive():
        queue_running = True
        queue_processor_thread = threading.Thread(target=process_execution_queue, daemon=True)
        queue_processor_thread.start()
        log_message("[QUEUE] Queue processor started")

@app.route('/api/queue/add', methods=['POST'])
def add_to_queue():
    """Add a test execution to the queue"""
    data = request.json
    device_ip = data.get('device_ip')
    method = data.get('method')
    iterations = int(data.get('iterations', 1))
    selected_ir_keys = data.get('selected_ir_keys', ['HOME', 'POWER'])
    
    # Get device credentials
    devices = load_devices()
    device = next((d for d in devices if d['ip'] == device_ip), None)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Create job ID
    job_id = f"{device_ip}_{method}_{int(time.time())}"
    
    # Create job object
    job = {
        'id': job_id,
        'device_ip': device_ip,
        'device_name': device.get('name', 'Device'),
        'method': method,
        'iterations': iterations,
        'username': device['username'],
        'password': device['password'],
        'port': device.get('port', 10022),
        'selected_ir_keys': selected_ir_keys,
        'queued_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Add to queue
    with execution_queue_lock:
        queued_jobs.append(job)
    
    execution_queue.put(job)
    
    # Start queue processor if not running
    start_queue_processor()
    
    log_message(f"[QUEUE] Added job {job_id} to queue (position: {execution_queue.qsize()})")
    
    return jsonify({
        'message': 'Job added to queue',
        'job_id': job_id,
        'position': execution_queue.qsize()
    })

@app.route('/api/queue/status', methods=['GET'])
def get_queue_status():
    """Get current queue status"""
    with execution_queue_lock:
        jobs_copy = list(queued_jobs)
    
    return jsonify({
        'queue_size': execution_queue.qsize(),
        'processor_running': queue_running and queue_processor_thread and queue_processor_thread.is_alive(),
        'queued_jobs': jobs_copy
    })

@app.route('/api/queue/clear', methods=['POST'])
def clear_queue():
    """Clear all queued jobs (doesn't stop currently running job)"""
    global queued_jobs
    
    # Clear the queue
    with execution_queue.queue.mutex:
        execution_queue.queue.clear()
    
    with execution_queue_lock:
        queued_jobs.clear()
    
    log_message("[QUEUE] Queue cleared")
    
    return jsonify({'message': 'Queue cleared'})

@app.route('/api/logs')
def stream_logs():
    """Stream operation logs from shared file (works across Gunicorn workers)"""
    def generate():
        # Track the last position in the file
        last_position = 0
        
        # Ensure log file exists
        if not os.path.exists(REALTIME_LOG_FILE):
            try:
                with open(REALTIME_LOG_FILE, 'w') as f:
                    f.write('')
            except:
                pass
        
        while True:
            try:
                with open(REALTIME_LOG_FILE, 'r', encoding='utf-8') as f:
                    # Move to last known position
                    f.seek(last_position)
                    
                    # Read new lines
                    new_lines = f.readlines()
                    
                    # Update position
                    last_position = f.tell()
                    
                    # Send each new line
                    if new_lines:
                        for line in new_lines:
                            line = line.strip()
                            if line:
                                yield f"data: {json.dumps({'message': line})}\n\n"
                    else:
                        # Send heartbeat to keep connection alive
                        yield f"data: {json.dumps({'message': ''})}\n\n"
                
                # Small sleep to prevent busy-waiting
                time.sleep(0.5)
                
            except Exception as e:
                # On error, send heartbeat and continue
                yield f"data: {json.dumps({'message': ''})}\n\n"
                time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/ir_keycodes', methods=['GET'])
def get_ir_keycodes():
    """Get available IR keycodes from JSON file"""
    try:
        keycodes = load_ir_keycodes()
        # Format for frontend
        keycode_list = []
        for key, value in keycodes.items():
            keycode_list.append({
                'name': value.get('name', key),
                'display_name': value.get('display_name', key),
                'description': value.get('description', '')
            })
        return jsonify({'keycodes': keycode_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ir_port', methods=['GET'])
def api_get_ir_port():
    """Return the configured IR blaster port for a device (by name or IP).

    Query params:
      device: device name or IP (required)

    Response JSON example:
      {
        "device": "SkyBox-1",
        "ip": "10.0.0.172",
        "ir_port": 2,
        "itach_ip": "10.0.0.12",
        "itach_port": 4998,
        "source": "devices.json"
      }
    """
    device_query = request.args.get('device')
    if not device_query:
        return jsonify({'error': 'Missing device query parameter'}), 400
    devices = load_devices()
    for d in devices:
        if d.get('name') == device_query or d.get('ip') == device_query:
            ir_cfg = get_ir_config_for_device(d.get('name'))
            return jsonify({
                'device': d.get('name'),
                'ip': d.get('ip'),
                'ir_port': ir_cfg.get('ir_port'),
                'itach_ip': ir_cfg.get('itach_ip'),
                'itach_port': ir_cfg.get('itach_port'),
                'source': 'devices.json'
            })
    return jsonify({'error': 'Device not found'}), 404

def probe_ir_ports(itach_ip='10.0.0.12', itach_port=4998, ports=(1, 2, 3)):
    """Probe iTach IR ports by sending a short valid IR code to each.

    Global Caché requires a full IR waveform. We reuse a known HOME code tail
    and vary the leading port spec 'sendir,<port>:2'. Success response starts with 'completeir'.

    Returns: {port: {success: bool, response: str}}
    """
    results = {}
    base_code_tail = '24624,38000,1,37,8,29,8,65,8,34,8,107,8,49,8,49,8,44,8,101,8,494,8,29,8,55,8,29,8,34,8,81,8,29,8,29,8,29,8,3040,8,29,8,65,8,34,8,107,8,49,8,49,8,44,8,101,8,494,8,29,8,96,8,70,8,34,8,81,8,29,8,29,8,29,8,3040\r'
    for p in ports:
        ir_code = f'ir,{p}:2,{base_code_tail}'
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(4)
                s.connect((itach_ip, itach_port))
                s.(ir_code.encode('ascii'))
                resp = s.recv(256).decode('ascii', errors='ignore').strip()
                results[p] = {'success': resp.startswith('completeir'), 'response': resp}
        except Exception as e:
            results[p] = {'success': False, 'response': str(e)}
    return results

@app.route('/api/ir_port_probe', methods=['GET'])
def api_ir_port_probe():
    """Probe all IR ports and return their responses.

    Optional query params: itach_ip (default 10.0.0.12), itach_port (default 4998)
    """
    itach_ip = request.args.get('itach_ip', '10.0.0.12')
    try:
        itach_port = int(request.args.get('itach_port', 4998))
    except ValueError:
        return jsonify({'error': 'Invalid itach_port'}), 400
    probe = probe_ir_ports(itach_ip, itach_port)
    return jsonify({'itach_ip': itach_ip, 'itach_port': itach_port, 'probes': probe})

@app.route('/api/iteration_logs', methods=['GET'])
def get_iteration_logs():
    """Get list of iteration log files"""
    try:
        log_files = []
        # Check current execution logs dir first, then fallback
        check_dirs = []
        if current_execution_logs_dir and os.path.exists(current_execution_logs_dir):
            check_dirs.append(current_execution_logs_dir)
        if os.path.exists('iteration_logs'):
            check_dirs.append('iteration_logs')
        
        for logs_dir in check_dirs:
            files = os.listdir(logs_dir)
            for filename in files:
                if filename.endswith('.log'):
                    filepath = os.path.join(logs_dir, filename)
                    file_stats = os.stat(filepath)
                    log_files.append({
                        'filename': filename,
                        'size': file_stats.st_size,
                        'modified': datetime.fromtimestamp(file_stats.st_mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                    })
        
        # Sort by modified time, most recent first
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify(log_files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/iteration_logs/<filename>', methods=['GET'])
def download_iteration_log(filename):
    """Download a specific iteration log file"""
    try:
        # Check current execution logs dir first, then fallback
        filepath = None
        if current_execution_logs_dir and os.path.exists(current_execution_logs_dir):
            test_path = os.path.join(current_execution_logs_dir, filename)
            if os.path.exists(test_path):
                filepath = test_path
        if not filepath and os.path.exists('iteration_logs'):
            test_path = os.path.join('iteration_logs', filename)
            if os.path.exists(test_path):
                filepath = test_path
        
        if not filepath:
            return jsonify({'error': 'File not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get test results organized by device"""
    try:
        results_by_device = {}
        
        # Check current execution logs dir first, then fallback
        check_dirs = []
        if current_execution_logs_dir and os.path.exists(current_execution_logs_dir):
            check_dirs.append(current_execution_logs_dir)
        if os.path.exists('iteration_logs'):
            check_dirs.append('iteration_logs')
        
        for logs_dir in check_dirs:
            files = os.listdir(logs_dir)
            
            for filename in files:
                filepath = os.path.join(logs_dir, filename)
                file_stats = os.stat(filepath)
                
                # Parse filename to extract device info
                # Format: DeviceIP_method_timestamp.log or DeviceIP_method_timestamp.html
                if '_' in filename:
                    parts = filename.split('_')
                    device_ip = parts[0]
                    
                    if device_ip not in results_by_device:
                        # Get device name from devices.json
                        devices = load_devices()
                        device = next((d for d in devices if d['ip'] == device_ip), None)
                        device_name = device['name'] if device else device_ip
                        
                        results_by_device[device_ip] = {
                            'device_ip': device_ip,
                            'device_name': device_name,
                            'logs': [],
                            'html_reports': [],
                            'screenshots': []
                        }
                    
                    file_info = {
                        'filename': filename,
                        'size': file_stats.st_size,
                        'modified': datetime.fromtimestamp(file_stats.st_mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                        'method': parts[1] if len(parts) > 1 else 'unknown'
                    }
                    
                    if filename.endswith('.html'):
                        results_by_device[device_ip]['html_reports'].append(file_info)
                    elif filename.endswith('.log'):
                        results_by_device[device_ip]['logs'].append(file_info)
                    elif filename.endswith('.tgz'):
                        results_by_device[device_ip]['logs'].append(file_info)
        
        # Get screenshots organized by device
        # Check current screenshots dir first, then fallback
        check_screenshot_dirs = []
        if current_screenshots_dir and os.path.exists(current_screenshots_dir):
            check_screenshot_dirs.append(current_screenshots_dir)
        if os.path.exists('screenshots'):
            check_screenshot_dirs.append('screenshots')
        
        for screenshots_dir in check_screenshot_dirs:
            for device_folder in os.listdir(screenshots_dir):
                device_folder_path = os.path.join(screenshots_dir, device_folder)
                if os.path.isdir(device_folder_path):
                    # Extract device IP from folder name (format: DeviceIP_DeviceName)
                    device_ip = device_folder.split('_')[0]
                    
                    if device_ip not in results_by_device:
                        devices = load_devices()
                        device = next((d for d in devices if d['ip'] == device_ip), None)
                        device_name = device['name'] if device else device_ip
                        
                        results_by_device[device_ip] = {
                            'device_ip': device_ip,
                            'device_name': device_name,
                            'logs': [],
                            'html_reports': [],
                            'screenshots': []
                        }
                    
                    # Count iterations and screenshots
                    iteration_folders = [f for f in os.listdir(device_folder_path) if os.path.isdir(os.path.join(device_folder_path, f))]
                    total_screenshots = 0
                    
                    for itr_folder in iteration_folders:
                        itr_path = os.path.join(device_folder_path, itr_folder)
                        for phase_folder in os.listdir(itr_path):
                            phase_path = os.path.join(itr_path, phase_folder)
                            if os.path.isdir(phase_path):
                                screenshots = [f for f in os.listdir(phase_path) if f.endswith('.png')]
                                total_screenshots += len(screenshots)
                    
                    results_by_device[device_ip]['screenshots'] = {
                        'folder': device_folder,
                        'iterations': len(iteration_folders),
                        'total_count': total_screenshots
                    }
        
        # Sort logs and reports by modified time
        for device_data in results_by_device.values():
            device_data['logs'].sort(key=lambda x: x['modified'], reverse=True)
            device_data['html_reports'].sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify(results_by_device)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results_page():
    """Render a consolidated results page with 3-day persistent storage"""
    # Load all results from persistent storage (auto-cleaned to 3 days)
    all_results = load_test_results()
    
    # Sort by timestamp descending (newest first)
    all_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Calculate statistics
    devices = load_devices()
    iteration_status_by_device = {}
    
    # Group results by device
    for result in all_results:
        dev_ip = result.get('device_ip', 'N/A')
        itr = result.get('iteration')
        
        if dev_ip not in iteration_status_by_device:
            iteration_status_by_device[dev_ip] = {}
        
        if itr not in iteration_status_by_device[dev_ip]:
            iteration_status_by_device[dev_ip][itr] = 'PASSED'
        
        if result.get('status') == 'FAILED':
            iteration_status_by_device[dev_ip][itr] = 'FAILED'
        elif result.get('status') == 'WARNING' and iteration_status_by_device[dev_ip][itr] != 'FAILED':
            iteration_status_by_device[dev_ip][itr] = 'WARNING'
    
    # Overall iteration status (across all devices)
    iteration_status = {}
    for r in all_results:
        itr = r.get('iteration')
        if itr not in iteration_status:
            iteration_status[itr] = 'PASSED'
        if r.get('status') == 'FAILED':
            iteration_status[itr] = 'FAILED'
        elif r.get('status') == 'WARNING' and iteration_status[itr] != 'FAILED':
            iteration_status[itr] = 'WARNING'
    
    # Get unique devices from results
    distinct_devices = list(set(r.get('device_ip', 'N/A') for r in all_results))
    
    generated_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    return render_template(
        'results.html',
        devices=devices,
        results=all_results,
        iteration_status=iteration_status,
        device_ip=last_device_ip,
        method=last_method,
        total_iterations=len(all_results),
        aggregated_results=all_results,
        iteration_status_by_device=iteration_status_by_device,
        distinct_devices=distinct_devices,
        generated=generated_ts
    )

@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    """Test SSH connection to device"""
    data = request.json
    device_ip = data.get('device_ip')
    
    devices = load_devices()
    device = next((d for d in devices if d['ip'] == device_ip), None)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    success, message, _ = test_ssh_connection(
        device['ip'],
        device.get('port', 10022),
        device['username'],
        device['password']
    )
    
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve screenshots from USB or local storage"""
    from flask import send_from_directory
    import sys
    
    # Determine base path (USB stick or local)
    if sys.platform.startswith('linux') and os.path.exists(USB_BASE_PATH):
        base_path = os.path.join(USB_BASE_PATH, USB_ENHANCEMENT_OUTPUT)
    else:
        base_path = USB_ENHANCEMENT_OUTPUT
    
    # Search for the screenshot file recursively
    for root, dirs, files in os.walk(base_path):
        if filename in files:
            return send_from_directory(root, filename)
    
    # If not found, return 404
    return "Screenshot not found", 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)

