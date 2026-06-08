"""
Repair missing reboot_perf_v2_optimized results by parsing job execution logs.
Usage: python3 fix_missing_reboot_perf_results.py <job_id> [<job_id> ...]
    or: python3 fix_missing_reboot_perf_results.py --all
"""
import os
import re
import sys
from datetime import datetime, timezone

from models.job import Job
from models.test_result import TestResult

ITERATION_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\] ITERATION (\d+)/(\d+)")
PERF_RE = re.compile(r"Performance:\s*([0-9]+(?:\.[0-9]+)?)s")
SHOT_RE = re.compile(r"Screenshot saved: (.+\.png)")
BEFORE_RE = re.compile(r"BEFORE screenshot saved: (.+\.png)")


def parse_execution_log(log_path: str):
    iterations = {}
    if not os.path.exists(log_path):
        return iterations

    current_iter = None
    current_ts = None
    buffer = []

    def finalize():
        if current_iter is None:
            return
        text = "".join(buffer)
        status = None
        if "REBOOT PERFORMANCE TEST V2 OPTIMIZED PASSED" in text:
            status = "PASSED"
        elif "REBOOT PERFORMANCE TEST V2 OPTIMIZED FAILED" in text:
            status = "FAILED"

        if not status:
            return

        perf_match = PERF_RE.search(text)
        performance_seconds = float(perf_match.group(1)) if perf_match else None
        screenshots = []
        screenshots.extend([m.group(1).strip() for m in BEFORE_RE.finditer(text)])
        screenshots.extend([m.group(1).strip() for m in SHOT_RE.finditer(text)])
        iterations[current_iter] = {
            "status": status,
            "timestamp": current_ts,
            "performance_seconds": performance_seconds,
            "screenshots": screenshots,
        }

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = ITERATION_RE.search(line)
            if match:
                finalize()
                current_iter = int(match.group(2))
                current_ts = match.group(1)
                buffer = [line]
            else:
                buffer.append(line)

    finalize()
    return iterations


def _get_reboot_jobs():
    jobs = Job.load_all()
    reboot_jobs = []
    for job in jobs:
        if job.methods and 'reboot_perf_v2_optimized' in job.methods:
            reboot_jobs.append(job.job_id)
            continue
        if job.execution_queue:
            for item in job.execution_queue:
                if item.get('method') == 'reboot_perf_v2_optimized':
                    reboot_jobs.append(job.job_id)
                    break
    return reboot_jobs


def main(job_ids):
    if not job_ids:
        print("Usage: python3 fix_missing_reboot_perf_results.py <job_id> [<job_id> ...] or --all")
        return 1

    if len(job_ids) == 1 and job_ids[0] == '--all':
        job_ids = _get_reboot_jobs()

    all_results = TestResult.load_all()
    existing = set()
    for r in all_results:
        existing.add((r.job_id, r.iteration, r.method))

    total_added = 0
    total_updated = 0
    for job_id in job_ids:
        job = Job.get_job(job_id)
        if not job:
            print(f"⚠️  Job not found: {job_id}")
            continue

        log_path = os.path.join("logs", "jobs", job_id, "execution.log")
        parsed = parse_execution_log(log_path)
        if not parsed:
            print(f"⚠️  No parsable iterations found in {log_path}")
            continue

        for iteration, info in sorted(parsed.items()):
            key = (job_id, iteration, "reboot_perf_v2_optimized")
            if key in existing:
                # Update screenshots if missing
                for r in all_results:
                    if r.job_id == job_id and r.iteration == iteration and r.method == "reboot_perf_v2_optimized":
                        has_screens = bool(r.screenshots)
                        if not has_screens and info.get("screenshots"):
                            r.screenshots = ", ".join(info.get("screenshots"))
                            TestResult.save_all(all_results)
                            total_updated += 1
                        break
                continue

            timestamp = None
            if info.get("timestamp"):
                try:
                    dt = datetime.strptime(info["timestamp"], "%Y-%m-%d %H:%M:%S")
                    timestamp = dt.replace(tzinfo=timezone.utc).isoformat()
                except Exception:
                    timestamp = None

            result = TestResult(
                iteration=iteration,
                phase="Reboot_perf_v2_optimized Execution",
                status=info.get("status", "FAILED"),
                details="Recovered from execution log",
                screenshots=", ".join(info.get("screenshots") or []),
                logs="",
                device_ip=job.device_ip,
                method="reboot_perf_v2_optimized",
                timestamp=timestamp,
                job_id=job_id,
                performance_seconds=info.get("performance_seconds"),
                optional_checks=None,
                build_info=None,
            )
            TestResult.add(result)
            Job.update_iteration_result(job_id, iteration, "passed" if info.get("status") == "PASSED" else "failed")
            total_added += 1

        print(f"✅ {job_id}: added {len([i for i in parsed if (job_id, i, 'reboot_perf_v2_optimized') not in existing])} missing results")

    print(f"✅ Total results added: {total_added}")
    print(f"✅ Total results updated with screenshots: {total_updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
