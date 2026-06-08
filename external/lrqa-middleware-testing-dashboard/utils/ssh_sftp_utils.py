"""
SSH/SFTP Utility Functions - Safe operations with fallback handling
Handles "EOF during negotiation" errors and provides SSH fallbacks for SFTP operations
"""
import paramiko
import time
import os
from typing import Optional, Dict, List


def safe_open_sftp(ssh_client: paramiko.SSHClient, max_retries: int = 3, delay_between_retries: float = 1.0) -> Optional[paramiko.SFTPClient]:
    """
    Safely open an SFTP channel with automatic retry on EOF errors.
    
    Args:
        ssh_client: Active SSH client connection
        max_retries: Number of times to retry on failure
        delay_between_retries: Delay in seconds between retries
        
    Returns:
        SFTP client if successful, None otherwise
    """
    for attempt in range(max_retries):
        try:
            sftp = ssh_client.open_sftp()
            return sftp
        except paramiko.ssh_exception.SSHException as e:
            if "EOF during negotiation" in str(e):
                if attempt < max_retries - 1:
                    # Delay before retry to allow SSH subsystem to recover
                    time.sleep(delay_between_retries)
                    continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay_between_retries)
                continue
            raise
    
    return None


def get_file_via_sftp(ssh_client: paramiko.SSHClient, remote_path: str, local_path: str, 
                     log_func=None) -> bool:
    """
    Get a file from remote device via SFTP with retry logic.
    
    Args:
        ssh_client: Active SSH client connection
        remote_path: Path on remote device
        local_path: Path to save locally
        log_func: Optional logging function
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sftp = safe_open_sftp(ssh_client, max_retries=2)
        if sftp is None:
            if log_func:
                log_func(f"   ⚠ Could not open SFTP channel for {remote_path}")
            return False
        
        try:
            sftp.get(remote_path, local_path)
            if log_func:
                log_func(f"   ✓ Retrieved {os.path.basename(remote_path)} via SFTP")
            return True
        finally:
            try:
                sftp.close()
            except:
                pass
                
    except Exception as e:
        if log_func:
            log_func(f"   ⚠ SFTP error for {remote_path}: {str(e)}")
        return False


def get_file_via_ssh_fallback(ssh_client: paramiko.SSHClient, remote_path: str, 
                             local_path: str, log_func=None) -> bool:
    """
    Get a file from remote device via SSH command as fallback (using cat).
    
    Args:
        ssh_client: Active SSH client connection
        remote_path: Path on remote device
        local_path: Path to save locally
        log_func: Optional logging function
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First check if file exists
        stdin, stdout, stderr = ssh_client.exec_command(f"test -f {remote_path} && echo 'exists'")
        stdout.channel.recv_exit_status()
        result = stdout.read().decode('utf-8', errors='ignore').strip()
        
        if result != 'exists':
            if log_func:
                log_func(f"   ⚠ File does not exist: {remote_path}")
            return False
        
        # Read file content
        stdin, stdout, stderr = ssh_client.exec_command(f"cat {remote_path}")
        content = stdout.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            if log_func:
                log_func(f"   ⚠ Failed to read {remote_path} via SSH (exit code: {exit_code})")
            return False
        
        if content:
            with open(local_path, 'w') as f:
                f.write(content)
            if log_func:
                log_func(f"   ✓ Retrieved {os.path.basename(remote_path)} via SSH fallback")
            return True
        else:
            if log_func:
                log_func(f"   ⚠ File is empty: {remote_path}")
            return False
            
    except Exception as e:
        if log_func:
            log_func(f"   ⚠ SSH fallback error for {remote_path}: {str(e)}")
        return False


def get_file_with_fallback(ssh_client: paramiko.SSHClient, remote_path: str, 
                           local_path: str, log_func=None) -> bool:
    """
    Get a file from remote device, trying SFTP first then SSH fallback.
    
    Args:
        ssh_client: Active SSH client connection
        remote_path: Path on remote device
        local_path: Path to save locally
        log_func: Optional logging function
        
    Returns:
        True if successful via either method, False otherwise
    """
    # Try SFTP first
    if get_file_via_sftp(ssh_client, remote_path, local_path, log_func):
        return True
    
    # Fallback to SSH
    if log_func:
        log_func(f"   ℹ SFTP failed, trying SSH fallback for {remote_path}...")
    
    return get_file_via_ssh_fallback(ssh_client, remote_path, local_path, log_func)


def collect_files_with_fallback(ssh_client: paramiko.SSHClient, remote_paths: List[str],
                               local_directory: str, log_func=None) -> Dict[str, bool]:
    """
    Collect multiple files with SFTP/SSH fallback.
    
    Args:
        ssh_client: Active SSH client connection
        remote_paths: List of remote file paths
        local_directory: Directory to save files
        log_func: Optional logging function
        
    Returns:
        Dictionary mapping remote path to success status
    """
    results = {}
    
    for remote_path in remote_paths:
        local_path = os.path.join(local_directory, os.path.basename(remote_path))
        success = get_file_with_fallback(ssh_client, remote_path, local_path, log_func)
        results[remote_path] = success
        
        # Small delay between operations to prevent connection exhaustion
        if remote_path != remote_paths[-1]:
            time.sleep(0.2)
    
    return results


def ensure_ssh_channel_clean(ssh_client: paramiko.SSHClient, log_func=None) -> None:
    """
    Ensure SSH channels are properly cleaned up to prevent connection exhaustion.
    
    Args:
        ssh_client: Active SSH client connection
        log_func: Optional logging function
    """
    try:
        if ssh_client and ssh_client.get_transport():
            # Get the transport to clean up any hanging channels
            transport = ssh_client.get_transport()
            if hasattr(transport, '_channels'):
                open_channels = len(transport._channels)
                if open_channels > 0 and log_func:
                    log_func(f"   ℹ Cleaning up {open_channels} open channel(s)")
    except Exception as e:
        if log_func:
            log_func(f"   ⚠ Error during SSH cleanup: {str(e)}")
