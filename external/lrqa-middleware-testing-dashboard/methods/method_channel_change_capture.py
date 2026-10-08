#!/usr/bin/env python3
"""
Channel Change Log Capture Method
Sends a channel-change key (UP/DOWN) during live TV playback and captures the
IP_AAMP_TUNETIME, channel_number and xumo_contentName log lines produced by that action.

Avoids a blocking `tail -f`: takes a baseline line count of the log file, sends the key,
then polls `tail -n <N> | grep -E` for new matching lines that appeared after the baseline.
"""

import re
import time
import traceback
import paramiko

from methods.method_remote_keys import get_supported_keycodes

LOG_FILE_PATH = "/opt/logs/sky-messages.log"

# Log line patterns to capture after the channel-change key is sent
CAPTURE_PATTERNS = {
    "ip_aamp_tunetime": r"IP_AAMP_TUNETIME",
    "channel_number": r"channel_number",
    "xumo_content_name": r"xumo_contentName",
}

# Extracts "key=value" / "key:value" for a given field name out of a matched log line
FIELD_VALUE_PATTERN = r'{field}["\']?\s*[:=]\s*["\']?([^,"\'\s]+)'


def _get_log_line_count(ssh, log_file=LOG_FILE_PATH):
    """Return current line count of the log file, or None on error."""
    try:
        stdin, stdout, stderr = ssh.exec_command(f"wc -l < {log_file}")
        count_str = stdout.read().decode('utf-8', errors='ignore').strip()
        return int(count_str) if count_str.isdigit() else None
    except Exception:
        return None


def _send_channel_key(ssh, key, log_msg):
    """Send a single UP/DOWN keySimulator press for channel change."""
    keycodes = get_supported_keycodes()
    keycode = keycodes.get(key.upper())
    if not keycode:
        return False, f"Unsupported key: {key}"

    cmd = f"keySimulator -k{keycode} -r1"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        error_msg = stderr.read().decode('utf-8', errors='ignore').strip()
        return False, f"Failed to send key {key}: {error_msg}"

    log_msg(f"✓ Sent channel key: {key}")
    return True, ""


def _extract_new_matches(ssh, baseline_line_count, pattern, log_file=LOG_FILE_PATH, tail_lines=500):
    """Return list of (line_num, line_content) for `pattern` found after baseline_line_count."""
    cmd = f"tail -n {tail_lines} {log_file} | grep -n -E \"{pattern}\""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='ignore')

    # Recompute matching absolute line numbers relative to the whole file
    # (tail -n N only gives line numbers relative to the tail window, so re-grep the whole file
    # to get real line numbers, matching the same approach used by reboot performance monitoring)
    if output.strip():
        full_cmd = f"grep -n -E \"{pattern}\" {log_file}"
        stdin, stdout, stderr = ssh.exec_command(full_cmd)
        output = stdout.read().decode('utf-8', errors='ignore')

    matches = []
    for line_entry in output.strip().split('\n'):
        if not line_entry.strip() or ':' not in line_entry:
            continue
        line_num_str, _, line_content = line_entry.partition(':')
        try:
            line_num = int(line_num_str)
        except ValueError:
            continue
        if baseline_line_count is None or line_num > baseline_line_count:
            matches.append((line_num, line_content))
    return matches


def _extract_field_value(field_name, line_content):
    """Pull a specific field's value out of a matched log line, falling back to the raw line."""
    match = re.search(FIELD_VALUE_PATTERN.format(field=re.escape(field_name)), line_content)
    if match:
        return match.group(1)
    return line_content.strip()


def execute_channel_change_capture(device_ip, port, username, password, iteration=1, device_name="Device",
                                    channel_key="DOWN", wait_after_key=6, poll_timeout=15,
                                    log_callback=None, job_id=None):
    """
    Send a channel-change key (UP/DOWN) during live TV playback and capture the resulting
    IP_AAMP_TUNETIME, channel_number and xumo_contentName log lines.

    Returns:
        dict: {
            'success': bool,
            'details': str,
            'channel_key': str,
            'ip_aamp_tunetime': str,
            'channel_number': str,
            'xumo_content_name': str,
            'matched_lines': dict  # raw matched line per field
        }
    """
    def log_msg(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    result = {
        "success": False,
        "details": "",
        "channel_key": channel_key,
        "ip_aamp_tunetime": "",
        "channel_number": "",
        "xumo_content_name": "",
        "matched_lines": {}
    }

    ssh = None
    try:
        log_msg("=" * 80)
        log_msg("CHANNEL CHANGE LOG CAPTURE - START")
        log_msg("=" * 80)
        log_msg(f"Device: {device_name} ({device_ip})")
        log_msg(f"Channel key: {channel_key}")
        log_msg(f"Log file: {LOG_FILE_PATH}")
        log_msg("")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_msg("✓ Connected to device")

        baseline = _get_log_line_count(ssh)
        log_msg(f"Baseline log line count: {baseline}")

        sent, err = _send_channel_key(ssh, channel_key, log_msg)
        if not sent:
            result["details"] = err
            log_msg(f"❌ {err}")
            return result

        log_msg(f"⏱ Waiting {wait_after_key}s for tune/log activity to settle...")
        time.sleep(wait_after_key)

        start_time = time.time()
        check_interval = 2
        remaining_fields = set(CAPTURE_PATTERNS.keys())

        while (time.time() - start_time) < poll_timeout and remaining_fields:
            for field_name in list(remaining_fields):
                pattern = CAPTURE_PATTERNS[field_name]
                matches = _extract_new_matches(ssh, baseline, pattern)
                if matches:
                    # Use the latest matching line
                    matches.sort(key=lambda m: m[0])
                    _, line_content = matches[-1]
                    result[field_name] = _extract_field_value(pattern, line_content)
                    result["matched_lines"][field_name] = line_content.strip()
                    remaining_fields.discard(field_name)
                    log_msg(f"  ✓ {field_name}: {result[field_name]}")

            if remaining_fields:
                time.sleep(check_interval)

        if remaining_fields:
            log_msg(f"  ⚠ Missing field(s) after {poll_timeout}s: {', '.join(remaining_fields)}")

        result["success"] = len(remaining_fields) < len(CAPTURE_PATTERNS)
        found_count = len(CAPTURE_PATTERNS) - len(remaining_fields)
        result["details"] = (
            f"Captured {found_count}/{len(CAPTURE_PATTERNS)} field(s) after sending '{channel_key}' key"
        )
        log_msg(f"{'✓' if result['success'] else '✗'} {result['details']}")
        return result

    except paramiko.AuthenticationException:
        result["details"] = f"Authentication failed for {device_ip}"
        log_msg(f"❌ {result['details']}")
        return result
    except Exception as e:
        result["details"] = f"Error: {str(e)}\n{traceback.format_exc()}"
        log_msg(f"❌ Channel change capture failed: {str(e)}")
        return result
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
