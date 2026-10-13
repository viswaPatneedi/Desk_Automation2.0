"""
Slack Notification Service - Desk Automation v2.0 (Global)

Sends job lifecycle notifications to Slack via the chat.postMessage API,
mirroring the device-health-dashboard implementation.

Two notification events:
  1. Job started   -> triggered-by, device, methods, ETA (job-card details)
  2. Job ended     -> Completed / Cancelled (by whom) / Failed + failure analysis

All sends are non-blocking and never raise: any error is logged and swallowed so
notification failures can never break test execution.
"""

import os
import threading
from datetime import datetime, timezone

from config.config_slack import (
    APP_DISPLAY_NAME,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
    SLACK_ENABLED,
    SLACK_NOTIFY_ON_START,
    SLACK_NOTIFY_ON_COMPLETE,
    SLACK_NOTIFY_ON_FAILURE,
    SLACK_NOTIFY_ON_CANCEL,
    DASHBOARD_BASE_URL,
    SLACK_API_URL,
    SLACK_TIMEOUT,
    SLACK_USERNAME,
    SLACK_ICON_EMOJI,
)

_SLACK_LOG_FILE = 'slack_operations.log'


def _log(msg):
    """Log to stdout and a dedicated slack log file (safe from background threads)."""
    timestamp = datetime.now(timezone.utc).isoformat()
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        with open(_SLACK_LOG_FILE, 'a') as f:
            f.write(formatted + '\n')
    except Exception:
        pass


def send_slack_message(text, channel=None):
    """
    Low-level sender. POSTs a mrkdwn message to Slack chat.postMessage.
    Returns (success: bool, error: str|None). Never raises.
    """
    if not SLACK_ENABLED:
        _log("⚠️ [SLACK] Slack disabled (SLACK_ENABLED=false), skipping")
        return False, "disabled"
    if not SLACK_BOT_TOKEN:
        _log("⚠️ [SLACK] SLACK_BOT_TOKEN not configured, skipping notification")
        return False, "no_token"

    target_channel = channel or SLACK_CHANNEL
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": target_channel,
            "text": text,
            "mrkdwn": True,
            "username": SLACK_USERNAME,
            "icon_emoji": SLACK_ICON_EMOJI,
        }
        response = requests.post(SLACK_API_URL, headers=headers, json=payload, timeout=SLACK_TIMEOUT)
        result = response.json()
        if result.get("ok"):
            _log(f"✅ [SLACK] Notification sent to #{target_channel}")
            return True, None
        error = result.get("error", "Unknown error")
        _log(f"⚠️ [SLACK] API error: {error}")
        return False, error
    except Exception as e:
        _log(f"⚠️ [SLACK] Failed to send notification: {e}")
        return False, str(e)


def _send_async(text, channel=None):
    """Fire-and-forget send on a daemon thread so execution is never blocked."""
    try:
        t = threading.Thread(target=send_slack_message, args=(text, channel), daemon=True)
        t.start()
    except Exception as e:
        _log(f"⚠️ [SLACK] Could not start send thread: {e}")


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

def _fmt_duration(start_iso, end_iso):
    """Human readable duration between two ISO timestamps."""
    try:
        start = datetime.fromisoformat(str(start_iso).replace('Z', '+00:00'))
        end = datetime.fromisoformat(str(end_iso).replace('Z', '+00:00'))
        secs = int((end - start).total_seconds())
        if secs < 0:
            return "-"
        mins, s = divmod(secs, 60)
        hrs, m = divmod(mins, 60)
        if hrs:
            return f"{hrs}h {m}m {s}s"
        if mins:
            return f"{m}m {s}s"
        return f"{s}s"
    except Exception:
        return "-"


def _method_list(job):
    """Return the list of method display names for a job."""
    queue = getattr(job, 'execution_queue', None) or []
    names = []
    for item in queue:
        if isinstance(item, dict):
            names.append(item.get('method') or item.get('name') or 'unknown')
        else:
            names.append(str(item))
    if not names:
        names = list(getattr(job, 'methods', None) or [])
    return names


def _job_title(job):
    return getattr(job, 'sequence_name', None) or ", ".join(_method_list(job)[:3]) or "Test Execution"


def build_job_started_message(job):
    """Build the 'Job Started' message with the job-card details."""
    now = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
    methods = _method_list(job)
    method_lines = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(methods))

    lines = [
        f":rocket: *{APP_DISPLAY_NAME}* — *Job Started*",
        f"{now} :hourglass:",
        "",
        f"*Job ID:* `{job.job_id}`",
        f"*Triggered by:* {getattr(job, 'user_id', 'unknown')}",
    ]
    if getattr(job, 'team_name', None):
        lines.append(f"*Team:* {job.team_name}")
    lines += [
        f"*Device:* {getattr(job, 'device_name', '')} (`{getattr(job, 'device_ip', '')}`)",
        f"*Iterations:* {getattr(job, 'iterations', 1)}",
        f"*Methods ({len(methods)}):*",
        method_lines if method_lines else "  -",
        "",
        f"<{DASHBOARD_BASE_URL}/job_details/{job.job_id}|View Job> | <{DASHBOARD_BASE_URL}|Open Dashboard>",
    ]
    return "\n".join(lines)


def _build_failure_analysis(job):
    """Extract per-iteration / per-step failure reasons from execution_results."""
    lines = []
    iteration_results = getattr(job, 'iteration_results', {}) or {}
    execution_results = getattr(job, 'execution_results', {}) or {}

    # Collect failed step details from execution_results
    failed_steps = []
    try:
        if isinstance(execution_results, dict):
            for key, res in execution_results.items():
                if not isinstance(res, dict):
                    continue
                status = str(res.get('status') or res.get('result') or '').upper()
                success = res.get('success')
                if status in ('FAILED', 'FAIL') or success is False:
                    step_name = res.get('method') or res.get('step_name') or res.get('name') or key
                    reason = res.get('details') or res.get('error') or res.get('message') or ''
                    failed_steps.append((step_name, str(reason).strip()))
    except Exception:
        pass

    if iteration_results:
        passed = sum(1 for r in iteration_results.values() if str(r).lower() == 'passed')
        failed = sum(1 for r in iteration_results.values() if str(r).lower() == 'failed')
        lines.append(f"*Iterations:* {passed} passed / {failed} failed")

    if failed_steps:
        lines.append("")
        lines.append("*Failure Analysis:*")
        lines.append("```")
        for step_name, reason in failed_steps[:5]:  # cap to keep message small
            reason_snippet = (reason[:180] + '…') if len(reason) > 180 else reason
            lines.append(f"• {step_name}")
            if reason_snippet:
                lines.append(f"  {reason_snippet}")
        if len(failed_steps) > 5:
            lines.append(f"… +{len(failed_steps) - 5} more failed step(s)")
        lines.append("```")
    return "\n".join(lines)


def build_job_ended_message(job, status):
    """Build the 'Job Ended' message: Completed / Cancelled / Failed (+ analysis)."""
    now = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
    duration = _fmt_duration(getattr(job, 'start_time', None), getattr(job, 'end_time', None) or now)

    status_lower = str(status).lower()
    if status_lower == 'completed':
        emoji, label = ":white_check_mark:", "Completed"
    elif status_lower == 'cancelled':
        emoji, label = ":no_entry_sign:", "Cancelled"
    else:
        emoji, label = ":x:", "Failed"

    lines = [
        f"{emoji} *{APP_DISPLAY_NAME}* — *Job {label}*",
        f"{now} :hourglass:",
        "",
        f"*Job ID:* `{job.job_id}`",
        f"*Job:* {_job_title(job)}",
        f"*Triggered by:* {getattr(job, 'user_id', 'unknown')}",
        f"*Device:* {getattr(job, 'device_name', '')} (`{getattr(job, 'device_ip', '')}`)",
        f"*Duration:* {duration}",
    ]

    if status_lower == 'cancelled':
        cancelled_by = getattr(job, 'cancelled_by', None) or 'unknown'
        reason = getattr(job, 'cancellation_reason', None) or ''
        lines.append(f"*Cancelled by:* {cancelled_by}")
        if reason:
            lines.append(f"*Reason:* {reason}")
    elif status_lower == 'failed':
        analysis = _build_failure_analysis(job)
        if analysis:
            lines.append("")
            lines.append(analysis)

    lines += [
        "",
        f"<{DASHBOARD_BASE_URL}/job_details/{job.job_id}|View Job> | <{DASHBOARD_BASE_URL}|Open Dashboard>",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public notification entry points
# ---------------------------------------------------------------------------

def notify_job_started(job):
    """Send 'Job Started' notification (if enabled)."""
    if not SLACK_NOTIFY_ON_START:
        return
    try:
        _send_async(build_job_started_message(job))
    except Exception as e:
        _log(f"⚠️ [SLACK] notify_job_started error: {e}")


def notify_job_ended(job, status):
    """Send 'Job Ended' notification for completed / failed / cancelled."""
    status_lower = str(status).lower()
    enabled = (
        (status_lower == 'completed' and SLACK_NOTIFY_ON_COMPLETE) or
        (status_lower == 'failed' and SLACK_NOTIFY_ON_FAILURE) or
        (status_lower == 'cancelled' and SLACK_NOTIFY_ON_CANCEL)
    )
    if not enabled:
        return
    try:
        _send_async(build_job_ended_message(job, status))
    except Exception as e:
        _log(f"⚠️ [SLACK] notify_job_ended error: {e}")
