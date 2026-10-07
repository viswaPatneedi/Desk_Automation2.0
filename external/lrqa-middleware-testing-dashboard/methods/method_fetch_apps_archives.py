"""
Fetch & Clear Apps Archives Method
Pull *.tar.gz/*.tgz files from /media/apps on the device to a local folder,
verify each transfer by size, and only then delete the remote copy.

Unlike execute_command (which runs entirely on the device's own shell), this method
streams file content from the app/server process, so it can reach local paths such
as a mounted USB drive that the device itself has no access to.

NOTE: Some devices (e.g. dropbear-based BusyBox images) have no sftp-server binary,
so paramiko's open_sftp() fails with "EOF during negotiation". To stay compatible
with those devices, files are streamed via `cat <file>` over a plain exec_command
channel (the same mechanism execute_command/collect_device_logs already rely on)
instead of the SFTP subsystem.
"""

import os
import shlex
import time
import paramiko
from datetime import datetime, timezone

from methods.method_utils import (
    log_message,
    get_folder_method_name,
    get_lexar_base_path
)


def _run(ssh, command, timeout=30):
    """Run a command via exec_command and return (exit_code, stdout_text, stderr_text)."""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    stdin.close()
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    return exit_code, out, err


def _download_file(ssh, remote_path, local_path, timeout=300):
    """Stream a remote file's raw bytes to a local path via `cat` over exec_command."""
    stdin, stdout, stderr = ssh.exec_command(f"cat -- {shlex.quote(remote_path)}", timeout=timeout)
    stdin.close()
    with open(local_path, 'wb') as f:
        while True:
            chunk = stdout.read(65536)
            if not chunk:
                break
            f.write(chunk)
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    return exit_code, err


def _get_lexar_root():
    """Base Lexar mount point (get_lexar_base_path() appends 'Enhancement_output')."""
    return os.path.dirname(get_lexar_base_path())


def _get_fetch_archives_log_path(device_ip, device_name, iteration, method_folder=None):
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_').replace('__', '_').replace('--', '-').upper()
    safe_ip = device_ip.replace('.', '-')
    device_folder = f"{safe_ip}_{safe_device_name}"
    folder_name = (method_folder or "FETCH_APPS_ARCHIVES").replace(' ', '_')
    itr_dir = os.path.join(get_lexar_base_path(), "EXECUTION_LOGS", current_date, device_folder, folder_name, f"ITR-{iteration}")
    os.makedirs(itr_dir, exist_ok=True)
    return os.path.join(itr_dir, f"FETCH_APPS_ARCHIVES_ITR_{iteration}.log")


def fetch_apps_archives(device_ip, port, username, password, iteration=1, device_name="Device",
                         combined_method_name=None, log_callback=None,
                         remote_source_dir="/media/apps", local_dest_dir=None):
    """
    Copy *.tar.gz/*.tgz files from remote_source_dir on the device to local_dest_dir
    on this machine, verify each by size, then delete the remote copy only for files
    that verified successfully.

    Args:
        device_ip, port, username, password: SSH connection details
        iteration: Iteration number
        device_name: Device name
        combined_method_name: Combined method name for sequence context
        log_callback: Optional callback for logging
        remote_source_dir: Directory on the device to scan (default /media/apps)
        local_dest_dir: Local destination folder (default <Lexar root>/A4K_reboot_logs)

    Returns:
        dict: {
            'success': bool,
            'details': str,
            'files': list of {name, size, seconds, copied, deleted},
            'logs': list
        }
    """

    def log_message_wrapper(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    if not local_dest_dir:
        local_dest_dir = os.path.join(_get_lexar_root(), "A4K_reboot_logs")

    start_time = datetime.now(timezone.utc)
    method_folder = get_folder_method_name() or combined_method_name or None
    log_file = _get_fetch_archives_log_path(device_ip, device_name, iteration, method_folder)
    logs = []
    files_report = []

    ssh = None
    try:
        log_message_wrapper(f"FETCH_APPS_ARCHIVES - START")
        log_message_wrapper(f"Device: {device_name} ({device_ip}:{port})")
        log_message_wrapper(f"Remote source: {remote_source_dir}")
        log_message_wrapper(f"Local destination: {local_dest_dir}")

        os.makedirs(local_dest_dir, exist_ok=True)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        log_message_wrapper(f"🔌 Connecting to {device_ip}:{port}...")
        ssh.connect(device_ip, port=int(port), username=username, password=password, timeout=30)
        log_message_wrapper(f"✓ Connected to device")
        logs.append(f"Connected to {device_ip}:{port}")

        remote_dir_quoted = shlex.quote(remote_source_dir)
        exit_code, _, _ = _run(ssh, f"test -d {remote_dir_quoted}", timeout=10)
        if exit_code != 0:
            msg = f"Remote directory not found: {remote_source_dir}"
            log_message_wrapper(f"❌ {msg}")
            return {'success': False, 'details': msg, 'files': [], 'logs': logs}

        # List archive filenames (cd first so the glob resolves inside remote_source_dir,
        # not the SSH login shell's home directory)
        list_cmd = f"cd {remote_dir_quoted} && ls -1 *.tar.gz *.tgz 2>/dev/null"
        _, list_out, _ = _run(ssh, list_cmd, timeout=15)
        filenames = [line.strip() for line in list_out.splitlines() if line.strip()]

        if not filenames:
            msg = "No .tar.gz/.tgz archives found"
            log_message_wrapper(f"ℹ️  {msg}")
            return {'success': True, 'details': msg, 'files': [], 'logs': logs}

        log_message_wrapper(f"📦 Found {len(filenames)} archive(s) to copy")

        all_ok = True
        for fname in filenames:
            remote_path = f"{remote_source_dir.rstrip('/')}/{fname}"
            local_path = os.path.join(local_dest_dir, fname)

            size_code, size_out, _ = _run(ssh, f"stat -c%s -- {shlex.quote(remote_path)}", timeout=10)
            try:
                remote_size = int(size_out) if size_code == 0 else -1
            except ValueError:
                remote_size = -1

            log_message_wrapper(f"⬇️  Copying {fname} ({remote_size} bytes)...")
            t0 = time.time()
            dl_code, dl_err = _download_file(ssh, remote_path, local_path)
            elapsed = round(time.time() - t0, 2)

            if dl_code != 0:
                msg = f"Copy failed for {fname} (exit {dl_code}): {dl_err}"
                log_message_wrapper(f"❌ {msg}")
                logs.append(msg)
                files_report.append({'name': fname, 'size': remote_size, 'seconds': elapsed, 'copied': False, 'deleted': False})
                all_ok = False
                continue

            local_size = os.path.getsize(local_path) if os.path.exists(local_path) else -1

            if remote_size == -1 or local_size != remote_size:
                msg = f"Size mismatch for {fname}: remote={remote_size} local={local_size} -- NOT deleting remote copy"
                log_message_wrapper(f"⚠️  {msg}")
                logs.append(msg)
                files_report.append({'name': fname, 'size': remote_size, 'seconds': elapsed, 'copied': False, 'deleted': False})
                all_ok = False
                continue

            log_message_wrapper(f"✓ Copied {fname} in {elapsed}s, verified size match")
            logs.append(f"Copied {fname} in {elapsed}s ({remote_size} bytes, verified)")

            del_code, _, del_err = _run(ssh, f"rm -f -- {shlex.quote(remote_path)}", timeout=10)
            deleted = (del_code == 0)
            if deleted:
                log_message_wrapper(f"🗑️  Deleted {fname} from device")
                logs.append(f"Deleted {fname} from {remote_source_dir}")
            else:
                msg = f"Verified copy of {fname} but failed to delete remote file: {del_err}"
                log_message_wrapper(f"⚠️  {msg}")
                logs.append(msg)

            files_report.append({'name': fname, 'size': remote_size, 'seconds': elapsed, 'copied': True, 'deleted': deleted})

        copied_count = sum(1 for f in files_report if f['copied'])
        deleted_count = sum(1 for f in files_report if f['deleted'])
        success = all_ok and copied_count == len(filenames)
        details = f"Copied {copied_count}/{len(filenames)} archive(s), deleted {deleted_count} from device"
        log_message_wrapper(f"\n{'✓' if success else '⚠️ '} {details}")

        with open(log_file, 'w') as f:
            f.write(f"FETCH_APPS_ARCHIVES - ITR {iteration}\n")
            f.write(f"Device: {device_name} ({device_ip}:{port})\n")
            f.write(f"Timestamp: {start_time.isoformat()}\n")
            f.write(f"Remote source: {remote_source_dir}\n")
            f.write(f"Local destination: {local_dest_dir}\n")
            f.write(f"\n--- Files ---\n")
            for fr in files_report:
                f.write(f"{fr['name']}: size={fr['size']} time={fr['seconds']}s copied={fr['copied']} deleted={fr['deleted']}\n")
            f.write(f"\n--- Details ---\n")
            for log_entry in logs:
                f.write(f"{log_entry}\n")

        log_message_wrapper(f"📄 Log saved to: {log_file}")

        return {'success': success, 'details': details, 'files': files_report, 'logs': logs}

    except paramiko.AuthenticationException as e:
        msg = f"SSH Authentication failed: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        return {'success': False, 'details': msg, 'files': files_report, 'logs': logs}

    except (paramiko.SSHException, OSError) as e:
        msg = f"SSH/Connection error: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        return {'success': False, 'details': msg, 'files': files_report, 'logs': logs}

    except Exception as e:
        msg = f"Unexpected error: {str(e)}"
        log_message_wrapper(f"❌ {msg}")
        return {'success': False, 'details': msg, 'files': files_report, 'logs': logs}

    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
