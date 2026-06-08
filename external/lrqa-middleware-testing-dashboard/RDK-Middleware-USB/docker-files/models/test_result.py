"""
TestResult Model - Represents a test execution result
Handles test result persistence and history management
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from utils.file_lock import FileLockManager
from config_paths import TEST_RESULTS_FILE

class TestResult:
    """Test result model for managing test execution results"""
    
    RETENTION_DAYS = 15  # Keep test results for 15 days
    
    def __init__(self, iteration: int, phase: str, status: str, details: str,
                 screenshots: str = "", logs: str = "", device_ip: str = "N/A",
                 method: str = "unknown", timestamp: Optional[str] = None,
                 job_id: Optional[str] = None, performance_seconds: Optional[float] = None,
                 optional_checks: Optional[Dict] = None, build_info: Optional[str] = None,
                 tiles_summary: Optional[Dict] = None, rdk_milestones_log: Optional[str] = None,
                 boot_type: Optional[str] = None):
        self.iteration = iteration
        self.phase = phase
        self.status = status
        self.details = details
        self.screenshots = screenshots
        self.logs = logs
        self.device_ip = device_ip
        self.method = method
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.date = datetime.fromisoformat(self.timestamp).strftime('%Y-%m-%d')
        self.job_id = job_id
        self.performance_seconds = performance_seconds
        self.optional_checks = optional_checks
        self.build_info = build_info
        self.tiles_summary = tiles_summary
        self.rdk_milestones_log = rdk_milestones_log
        self.boot_type = boot_type
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            'iteration': self.iteration,
            'phase': self.phase,
            'status': self.status,
            'details': self.details,
            'screenshots': self.screenshots,
            'logs': self.logs,
            'device_ip': self.device_ip,
            'method': self.method,
            'timestamp': self.timestamp,
            'date': self.date,
            'job_id': self.job_id,
            'performance_seconds': self.performance_seconds,
            'optional_checks': self.optional_checks,
            'build_info': self.build_info,
            'tiles_summary': self.tiles_summary,
            'rdk_milestones_log': self.rdk_milestones_log,
            'boot_type': self.boot_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TestResult':
        """Create test result from dictionary"""
        return cls(
            iteration=data['iteration'],
            phase=data['phase'],
            status=data['status'],
            details=data['details'],
            screenshots=data.get('screenshots', ''),
            logs=data.get('logs', ''),
            device_ip=data.get('device_ip', 'N/A'),
            method=data.get('method', 'unknown'),
            timestamp=data.get('timestamp'),
            job_id=data.get('job_id'),
            performance_seconds=data.get('performance_seconds'),
            optional_checks=data.get('optional_checks'),
            build_info=data.get('build_info'),
            tiles_summary=data.get('tiles_summary'),
            rdk_milestones_log=data.get('rdk_milestones_log'),
            boot_type=data.get('boot_type')
        )
    
    @staticmethod
    def load_all() -> List['TestResult']:
        """Load all test results from storage and clean up old data"""
        if not os.path.exists(TEST_RESULTS_FILE):
            return []
        
        try:
            with FileLockManager.locked_json_file(TEST_RESULTS_FILE, 'r+') as (f, data):
                all_results_data = data if isinstance(data, list) else []
                
                # Filter results within retention period
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=TestResult.RETENTION_DAYS)
                filtered_results = []
                
                for result_data in all_results_data:
                    result_date = result_data.get('timestamp', '')
                    if result_date:
                        try:
                            result_datetime = datetime.fromisoformat(result_date.replace('Z', '+00:00'))
                            if result_datetime >= cutoff_date:
                                filtered_results.append(TestResult.from_dict(result_data))
                        except:
                            pass
                
                # Save cleaned results back if we removed any
                if len(filtered_results) < len(all_results_data):
                    f.seek(0)
                    f.truncate()
                    json.dump([r.to_dict() for r in filtered_results], f, indent=2)
                
                return filtered_results
        except Exception as e:
            print(f"Error loading test results: {e}")
            return []
    
    @staticmethod
    def save_all(results: List['TestResult']) -> None:
        """Save all test results to storage"""
        try:
            results_data = [r.to_dict() for r in results]
            FileLockManager.safe_json_write(TEST_RESULTS_FILE, results_data, indent=2)
        except Exception as e:
            print(f"Error saving test results: {e}")
    
    @staticmethod
    def add(result: 'TestResult') -> None:
        """Add a new test result"""
        try:
            def _append_result(data):
                data_list = data if isinstance(data, list) else []
                data_list.append(result.to_dict())
                return data_list
            FileLockManager.atomic_json_update(TEST_RESULTS_FILE, _append_result)
            print(f"[DEBUG] TestResult.add: Successfully added result for job_id={result.job_id}, iteration={result.iteration}, device_ip={result.device_ip}")
        except Exception as e:
            print(f"[ERROR] TestResult.add: Failed to add result for job_id={result.job_id}, iteration={result.iteration}, device_ip={result.device_ip}: {e}")
    
    @staticmethod
    def clear_all() -> None:
        """Clear all test results"""
        with open(TEST_RESULTS_FILE, 'w') as f:
            json.dump([], f)
    
    @staticmethod
    def get_by_device(device_ip: str) -> List['TestResult']:
        """Get all results for a specific device"""
        all_results = TestResult.load_all()
        return [r for r in all_results if r.device_ip == device_ip]
    
    @staticmethod
    def get_by_method(method: str) -> List['TestResult']:
        """Get all results for a specific method"""
        all_results = TestResult.load_all()
        return [r for r in all_results if r.method == method]
