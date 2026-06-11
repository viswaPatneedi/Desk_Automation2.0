"""
Collect Device Logs Method
Collect all device logs from /opt/logs/ and store as compressed archive in /media/apps/
"""

import time
import paramiko
from datetime import datetime, timezone
import os

from methods.method_utils import (
    log_message,
    get_folder_method_name,
    get_lexar_base_path
)


def _get_collect_logs_log_path(device_ip, device_name, iteration, method_folder=None):
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
    safe_ip = device_ip.replace('.', '-')
    device_folder = f"{safe_ip}_{safe_device_name}"
    folder_name = (method_folder or "COLLECT_LOGS").replace(' ', '_')
    itr_dir = os.path.join(get_lexar_base_path(), "EXECUTION_LOGS", current_date, device_folder, folder_name, f"ITR-{iteration}")
    os.makedirs(itr_dir, exist_ok=True)
    return os.path.join(itr_dir, f"COLLECT_LOGS_ITR_{iteration}.log")


def collect_device_logs(device_ip, port, username, password, iteration=1, device_name="Device",
                       combined_method_name=None, log_callback=None):
    """
    Collect device logs from /opt/logs/ and store in /media/apps/ as compressed archive.
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Iteration number
        device_name: Device name
        combined_method_name: Combined method name for sequence context
        log_callback: Optional callback for logging
    
    Returns:
        dict: {
            'success': bool,
            'details': str,
            'archive_name': str,
            'archive_path': str,
            'file_size': str,
            'logs': list
        }
    """
    
    def log_message_wrapper(msg):
        print(msg)
        if log_callback:
            log_callback(msg)
    
    start_time = datetime.now(timezone.utc)
    method_folder = get_folder_method_name() or combined_method_name or None
    log_file = _get_collect_logs_log_path(device_ip, device_name, iteration, method_folder)
    logs = []
    
    try:
        log_message_wrapper(f"COLLECT_LOGS - START")
        log_message_wrapper(f"Device: {device_name} ({device_ip}:{port})")
        log_message_wrapper(f"Iteration: {iteration}")
        
        # Connect to device via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        log_message_wrapper(f"🔌 Connecting to {device_ip}:{port}...")
        ssh.connect(device_ip, port=int(port), username=username, password=password, timeout=30)
        log_message_wrapper(f"✓ Connected to device")
        logs.append(f"Connected to {device_ip}:{port}")
        
        # Create /media/apps directory if it doesn't exist
        log_message_wrapper(f"📁 Creating /media/apps directory...")
        mkdir_cmd = "mkdir -p /media/apps && echo 'DIR_READY'"
        stdin, stdout, stderr = ssh.exec_command(mkdir_cmd, timeout=10)
        mkdir_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        if "DIR_READY" in mkdir_output:
            log_message_wrapper(f"✓ /media/apps directory ready")
            logs.append("/media/apps directory created/verified")
        
        # Generate archive filename with iteration and timestamp
        timestamp = start_time.strftime('%Y%m%d_%H%M%S')
        archive_filename = f"ITR-{iteration}-device_logs_{timestamp}.tgz"
        remote_log_archive = f"/media/apps/{archive_filename}"
        
        log_message_wrapper(f"📦 Creating archive: {archive_filename}")
        log_message_wrapper(f"   Source: /opt/logs/*")
        logs.append(f"Archive: {archive_filename}")
        
        # Check if /opt/logs exists
        log_message_wrapper(f"🔍 Checking /opt/logs directory...")
        check_cmd = "ls -la /opt/logs 2>/dev/null | head -3 || echo 'NO_LOGS_DIR'"
        stdin, stdout, stderr = ssh.exec_command(check_cmd, timeout=10)
        check_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        if "NO_LOGS_DIR" in check_output:
            log_message_wrapper(f"⚠️  /opt/logs directory not found or empty")
            logs.append("Warning: /opt/logs directory not found")
        else:
            log_message_wrapper(f"✓ /opt/logs directory found")
        
        # Create tar.gz archive of device logs
        log_message_wrapper(f"🗜️  Compressing logs...")
        tar_cmd = f"tar -czf {remote_log_archive} /opt/logs/* 2>/dev/null || echo 'tar_done'"
        stdin, stdout, stderr = ssh.exec_command(tar_cmd, timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        tar_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        log_message_wrapper(f"✓ Archive creation completed")
        logs.append("Archive compressed successfully")
        
        # Verify file exists and get size
        log_message_wrapper(f"✅ Verifying archive...")
        verify_cmd = f"ls -lh {remote_log_archive} 2>/dev/null && echo 'SIZE_OK' || echo 'FILE_NOT_FOUND'"
        stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=10)
        verify_output = stdout.read().decode('utf-8', errors='ignore').strip()
        stdout.channel.close()
        
        # Extract file size
        file_size = "Unknown"
        for line in verify_output.split('\n'):
            if remote_log_archive in line:
                parts = line.split()
                if len(parts) >= 5:
                    file_size = parts[4]
                log_message_wrapper(f"  📊 {line}")
                logs.append(line)
        
        if "SIZE_OK" in verify_output or archive_filename in verify_output:
            log_message_wrapper(f"\n✓ Device logs successfully collected")
            log_message_wrapper(f"  Archive: {archive_filename}")
            log_message_wrapper(f"  Location: /media/apps/")
            log_message_wrapper(f"  Size: {file_size}")
            
            success_msg = f"Logs collected successfully - {archive_filename} ({file_size})"
            log_message_wrapper(f"\n✓ {success_msg}")
            
            ssh.close()
            
            # Write to log file
            with open(log_file, 'w') as f:
                f.write(f"COLLECT_LOGS - ITR {iteration}\n")
                f.write(f"Device: {device_name} ({device_ip}:{port})\n")
                f.write(f"Timestamp: {start_time.isoformat()}\n")
                f.write(f"Archive: {archive_filename}\n")
                f.write(f"Location: /media/apps/\n")
                f.write(f"Size: {file_size}\n")
                f.write(f"\n--- Details ---\n")
                for log_entry in logs:
                    f.write(f"{log_entry}\n")
            
            log_message_wrapper(f"📄 Log saved to: {log_file}")
            
            return {
                'success': True,
                'details': success_msg,
                'archive_name': archive_filename,
                'archive_path': remote_log_archive,
                'file_size': file_size,
                'logs': logs
            }
        else:
            log_message_wrapper(f"\n❌ Failed to verify archive")
            log_message_wrapper(f"  Output: {verify_output}")
            
            ssh.close()
            
            error_msg = "Archive verification failed"
            with open(log_file, 'w') as f:
                f.write(f"COLLECT_LOGS - ITR {iteration} - FAILED\n")
                f.write(f"Device: {device_name} ({device_ip}:{port})\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Verification output: {verify_output}\n")
            
            return {
                'success': False,
                'details': error_msg,
                'archive_name': archive_filename,
                'archive_path': remote_log_archive,
                'file_size': 'N/A',
                'logs': logs
            }
    
    except paramiko.AuthenticationException as e:
        msg = f"SSH Authentication failed: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        
        with open(log_file, 'w') as f:
            f.write(f"COLLECT_LOGS - ITR {iteration} - AUTH_ERROR\n")
            f.write(f"Device: {device_name} ({device_ip}:{port})\n")
            f.write(f"Error: {msg}\n")
        
        return {
            'success': False,
            'details': msg,
            'archive_name': '',
            'archive_path': '',
            'file_size': '',
            'logs': [msg]
        }
    
    except paramiko.SSHException as e:
        msg = f"SSH connection failed: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        
        with open(log_file, 'w') as f:
            f.write(f"COLLECT_LOGS - ITR {iteration} - SSH_ERROR\n")
            f.write(f"Device: {device_name} ({device_ip}:{port})\n")
            f.write(f"Error: {msg}\n")
        
        return {
            'success': False,
            'details': msg,
            'archive_name': '',
            'archive_path': '',
            'file_size': '',
            'logs': [msg]
        }
    
    except Exception as e:
        msg = f"Error collecting logs: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        import traceback
        log_message_wrapper(f"  Traceback: {traceback.format_exc()}")
        
        with open(log_file, 'w') as f:
            f.write(f"COLLECT_LOGS - ITR {iteration} - ERROR\n")
            f.write(f"Device: {device_name} ({device_ip}:{port})\n")
            f.write(f"Error: {msg}\n")
            f.write(f"Traceback: {traceback.format_exc()}\n")
        
        return {
            'success': False,
            'details': msg,
            'archive_name': '',
            'archive_path': '',
            'file_size': '',
            'logs': [msg]
        }
