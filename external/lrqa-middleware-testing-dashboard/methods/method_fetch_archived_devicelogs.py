"""Fetch archived device logs through the active R-Pi connection."""

import os
import shlex

from methods import method_utils


def _run(ssh, command, timeout=30):
    """Execute a device command and return its output through the R-Pi shell."""
    _, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    return output, error


def fetch_archived_device_logs(device_ip, iteration=1, device_name='Device',
                               log_callback=None, tunnel_service=None,
                               remote_source_dir='/media/apps'):
    """Copy verified ``.tar.gz`` and ``.tgz`` archives into this job iteration.

    The supplied service is a device-bound view of the shared R-Pi connection;
    no direct device connection is created and the R-Pi lifecycle is untouched.
    """
    def log(message):
        if log_callback:
            log_callback(message)

    if not tunnel_service:
        return {'success': False, 'details': 'An active R-Pi connection is required', 'logs': []}

    destination_dir = getattr(method_utils.thread_local, 'device_logs_dir', None)
    if not destination_dir:
        return {'success': False, 'details': 'Job captured_device_logs folder is unavailable', 'logs': []}

    os.makedirs(destination_dir, exist_ok=True)
    quoted_source = shlex.quote(remote_source_dir)
    log(f'[FETCH ARCHIVED LOGS] Reading {remote_source_dir} through R-Pi for iteration {iteration}')

    listing, listing_error = _run(
        tunnel_service,
        f"find {quoted_source} -maxdepth 1 -type f \\( -name '*.tar.gz' -o -name '*.tgz' \\) -printf '%f\\n'",
        timeout=30,
    )
    if listing_error:
        return {'success': False, 'details': f'Cannot list device archives: {listing_error}', 'logs': []}

    filenames = [name for name in listing.splitlines() if name]
    if not filenames:
        return {'success': True, 'details': 'No archived device logs found in /media/apps', 'logs': []}

    copied_logs = []
    failures = []
    for filename in filenames:
        remote_path = f"{remote_source_dir.rstrip('/')}/{filename}"
        local_path = os.path.join(destination_dir, filename)
        remote_size_text, size_error = _run(
            tunnel_service, f"wc -c < {shlex.quote(remote_path)}", timeout=15
        )
        try:
            remote_size = int(remote_size_text)
        except ValueError:
            failures.append(f'{filename}: unable to read archive size ({size_error or remote_size_text})')
            continue

        # execute_command returns decoded output, unsuitable for binary archives.
        # Use base64 so archive bytes safely traverse the SSH command channel.
        encoded_archive, copy_error = _run(
            tunnel_service, f"base64 {shlex.quote(remote_path)}", timeout=300
        )
        if copy_error:
            failures.append(f'{filename}: copy failed ({copy_error})')
            continue

        try:
            import base64
            with open(local_path, 'wb') as archive_file:
                archive_file.write(base64.b64decode(encoded_archive))
        except Exception as error:
            failures.append(f'{filename}: could not write archive ({error})')
            continue

        local_size = os.path.getsize(local_path)
        if local_size != remote_size:
            failures.append(f'{filename}: size mismatch (device={remote_size}, local={local_size})')
            continue

        _, delete_error = _run(tunnel_service, f"rm -f {shlex.quote(remote_path)}", timeout=15)
        if delete_error:
            log(f'⚠ Verified copy retained on device: {filename} ({delete_error})')
        copied_logs.append(local_path)
        log(f'✓ Copied and verified: {local_path}')

    details = f'Copied {len(copied_logs)}/{len(filenames)} archived device log(s)'
    if failures:
        details += f'; failures: {"; ".join(failures)}'
    return {'success': not failures, 'details': details, 'logs': copied_logs, 'failures': failures}