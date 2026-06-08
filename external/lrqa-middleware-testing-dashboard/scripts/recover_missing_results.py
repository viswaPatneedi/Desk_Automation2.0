import os
import json
from datetime import datetime, timezone

RESULTS_FILE = '../test_results_history.json'
LOGS_BASE = '../logs/jobs/'

def parse_execution_log(log_path):
    # Simple parser: looks for job info and result summary
    job_id = os.path.basename(log_path)
    device_ip = None
    iteration = 1
    phase = 'Recovered Execution'
    status = 'UNKNOWN'
    details = ''
    screenshots = ''
    logs = ''
    method = ''
    timestamp = datetime.now(timezone.utc).isoformat()
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'Job ID:' in line:
                job_id = line.split('Job ID:')[1].strip()
            if 'Device:' in line:
                device_ip = line.split('(')[-1].split(')')[0].strip()
            if 'Iterations:' in line:
                iteration = int(line.split('Iterations:')[1].split('completed')[0].strip().split('/')[0])
            if 'Method(s):' in line:
                method = line.split('Method(s):')[1].strip()
            if 'Result:' in line:
                status = line.split('Result:')[1].strip().upper()
            if 'Completed At:' in line:
                timestamp = line.split('Completed At:')[1].strip()
            if 'Execution Result' in line:
                details = line.strip()
    return {
        'iteration': iteration,
        'phase': phase,
        'status': status,
        'details': details,
        'screenshots': screenshots,
        'logs': logs,
        'device_ip': device_ip,
        'method': method,
        'timestamp': timestamp,
        'date': timestamp[:10],
        'job_id': job_id,
    }

def recover_results():
    # Scan all job log folders
    for job_folder in os.listdir(LOGS_BASE):
        log_dir = os.path.join(LOGS_BASE, job_folder)
        log_file = os.path.join(log_dir, 'execution.log')
        if os.path.exists(log_file):
            recovered = parse_execution_log(log_file)
            # Check if already present
            with open(RESULTS_FILE, 'r+') as f:
                data = json.load(f)
                exists = any(r.get('job_id') == recovered['job_id'] for r in data)
                if not exists:
                    print(f"Recovering missing result for job_id={recovered['job_id']}")
                    data.append(recovered)
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2)
                else:
                    print(f"Result already exists for job_id={recovered['job_id']}")

if __name__ == '__main__':
    recover_results()
