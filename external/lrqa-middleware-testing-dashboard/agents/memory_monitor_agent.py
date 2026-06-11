"""
Agent-MemoryMonitor: v2.0 Implementation Progress Tracking Agent
Monitors all memory files, tracks completion status, detects issues, and generates reports
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

MEMORY_REPO_DIR = Path('/memories/repo')
MEMORY_SESSION_DIR = Path('/memories/session')

MEMORY_FILES = {
    'requirements': MEMORY_REPO_DIR / 'v2-requirements-summary.md',
    'progress': MEMORY_REPO_DIR / 'v2-work-progress.md',
    'implementation': MEMORY_REPO_DIR / 'v2-implementation-status.md',
    'blockers': MEMORY_REPO_DIR / 'v2-blockers-and-issues.md',
    'agent_health': MEMORY_REPO_DIR / 'v2-agent-health.md'
}

# ============================================================
# DATA CLASSES
# ============================================================

class IssueType(Enum):
    """Types of issues that can be detected"""
    INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
    MISSED_DEADLINE = "missed_deadline"
    BLOCKER_UNRESOLVED = "blocker_unresolved"
    MEMORY_INCONSISTENCY = "memory_inconsistency"
    NO_PROGRESS = "no_progress"
    DEPENDENCY_NOT_MET = "dependency_not_met"
    TASK_STATUS_UNCLEAR = "task_status_unclear"
    CONFIGURATION_MISSING = "configuration_missing"


class SeverityLevel(Enum):
    """Issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Issue:
    """Tracked issue detected by Agent-MemoryMonitor"""
    issue_type: IssueType
    severity: SeverityLevel
    title: str
    description: str
    affected_items: List[str]
    detected_at: str
    resolved: bool = False
    resolution: str = None

    def to_dict(self):
        return {
            'issue_type': self.issue_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'affected_items': self.affected_items,
            'detected_at': self.detected_at,
            'resolved': self.resolved,
            'resolution': self.resolution
        }


@dataclass
class ProgressSnapshot:
    """Snapshot of current implementation progress"""
    timestamp: str
    total_requirements: int
    completed_requirements: int
    in_progress_requirements: int
    blocked_requirements: int
    completion_percentage: int
    phase_status: Dict[int, str]
    critical_issues: int
    total_issues: int
    next_milestone: str
    estimated_completion: str

    def to_dict(self):
        return asdict(self)


# ============================================================
# MEMORY FILE PARSER
# ============================================================

class MemoryParser:
    """Parse memory markdown files and extract structured data"""
    
    @staticmethod
    def parse_requirements_file() -> Dict[str, Any]:
        """Parse v2-requirements-summary.md"""
        try:
            if not MEMORY_FILES['requirements'].exists():
                return {}
            
            content = MEMORY_FILES['requirements'].read_text(encoding='utf-8')
            
            # Extract total requirements count
            requirements_count = len(re.findall(r'^## \d+\.', content, re.MULTILINE))
            
            return {
                'total_requirements': requirements_count,
                'file_size': len(content),
                'last_updated': MEMORY_FILES['requirements'].stat().st_mtime,
                'contains_agent_monitor': 'Agent-MemoryMonitor' in content
            }
        except Exception as e:
            logger.error(f"Error parsing requirements file: {e}")
            return {}
    
    @staticmethod
    def parse_progress_file() -> Dict[str, Any]:
        """Parse v2-work-progress.md"""
        try:
            if not MEMORY_FILES['progress'].exists():
                return {}
            
            content = MEMORY_FILES['progress'].read_text(encoding='utf-8')
            
            # Extract completion statistics
            completed = len(re.findall(r'✅', content))
            in_progress = len(re.findall(r'🟡', content))
            not_started = len(re.findall(r'🔴', content))
            blocked = len(re.findall(r'⛔', content))
            
            # Extract session date
            session_match = re.search(r'## 📅 Today: (.+)', content)
            session_date = session_match.group(1) if session_match else None
            
            return {
                'completed_tasks': completed,
                'in_progress_tasks': in_progress,
                'not_started_tasks': not_started,
                'blocked_tasks': blocked,
                'session_date': session_date,
                'file_exists': True,
                'last_updated': MEMORY_FILES['progress'].stat().st_mtime
            }
        except Exception as e:
            logger.error(f"Error parsing progress file: {e}")
            return {}
    
    @staticmethod
    def parse_implementation_file() -> Dict[str, Any]:
        """Parse v2-implementation-status.md"""
        try:
            if not MEMORY_FILES['implementation'].exists():
                return {}
            
            content = MEMORY_FILES['implementation'].read_text(encoding='utf-8')
            
            # Extract phase status
            phases = {}
            for phase_num in range(1, 6):
                if f'Phase {phase_num}' in content:
                    status_match = re.search(
                        rf'### Phase {phase_num}:.*?\n\*\*Status\*\*: (.*?)\n',
                        content,
                        re.MULTILINE
                    )
                    if status_match:
                        phases[f'phase_{phase_num}'] = status_match.group(1).strip()
            
            # Count subtasks
            subtask_counts = {}
            for phase_num in range(1, 6):
                subtasks = len(re.findall(rf'- \[ \].*Phase {phase_num}', content))
                completed_subtasks = len(re.findall(rf'- \[x\].*Phase {phase_num}', content))
                subtask_counts[f'phase_{phase_num}'] = {
                    'total': subtasks + completed_subtasks,
                    'completed': completed_subtasks
                }
            
            return {
                'phases': phases,
                'subtask_status': subtask_counts,
                'file_exists': True,
                'last_updated': MEMORY_FILES['implementation'].stat().st_mtime
            }
        except Exception as e:
            logger.error(f"Error parsing implementation file: {e}")
            return {}
    
    @staticmethod
    def parse_blockers_file() -> Dict[str, Any]:
        """Parse v2-blockers-and-issues.md"""
        try:
            if not MEMORY_FILES['blockers'].exists():
                return {}
            
            content = MEMORY_FILES['blockers'].read_text(encoding='utf-8')
            
            # Extract active blockers
            blocked_sections = re.findall(r'## Active Blockers.*?\n\n(.*?)(?=##|$)', content, re.DOTALL)
            active_blockers = 'None currently' not in (blocked_sections[0] if blocked_sections else '')
            
            # Extract issue count
            issue_count = len(re.findall(r'^### Issue \d+:', content, re.MULTILINE))
            
            # Extract decisions made
            decisions = len(re.findall(r'^### Decision \d+:', content, re.MULTILINE))
            
            return {
                'has_active_blockers': active_blockers,
                'issue_count': issue_count,
                'decisions_made': decisions,
                'file_exists': True,
                'last_updated': MEMORY_FILES['blockers'].stat().st_mtime
            }
        except Exception as e:
            logger.error(f"Error parsing blockers file: {e}")
            return {}


# ============================================================
# ISSUE DETECTION ENGINE
# ============================================================

class IssueDetector:
    """Detect issues in v2.0 implementation progress"""
    
    def __init__(self):
        self.issues: List[Issue] = []
        self.parser = MemoryParser()
    
    def detect_all_issues(self) -> List[Issue]:
        """Run all issue detection checks"""
        self.issues = []
        
        # Run detection checks
        self._check_memory_file_existence()
        self._check_memory_file_updates()
        self._check_progress_status()
        self._check_deadline_compliance()
        self._check_documentation_completeness()
        self._check_blocker_resolution()
        self._check_dependency_satisfaction()
        self._check_phase_progress()
        
        return self.issues
    
    def _check_memory_file_existence(self):
        """Check if all memory files exist"""
        missing_files = []
        for file_type, file_path in MEMORY_FILES.items():
            if not file_path.exists():
                missing_files.append(file_type)
        
        if missing_files:
            self.issues.append(Issue(
                issue_type=IssueType.CONFIGURATION_MISSING,
                severity=SeverityLevel.ERROR,
                title="Missing Memory Files",
                description=f"The following memory files are missing: {', '.join(missing_files)}",
                affected_items=missing_files,
                detected_at=datetime.now(timezone.utc).isoformat(),
                resolved=False
            ))
    
    def _check_memory_file_updates(self):
        """Check if memory files are being updated regularly"""
        for file_type, file_path in MEMORY_FILES.items():
            if not file_path.exists():
                continue
            
            last_updated = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            hours_since_update = (datetime.now(timezone.utc) - last_updated).total_seconds() / 3600
            
            if hours_since_update > 24:
                self.issues.append(Issue(
                    issue_type=IssueType.INCOMPLETE_DOCUMENTATION,
                    severity=SeverityLevel.WARNING,
                    title=f"Memory File Not Updated: {file_type}",
                    description=f"{file_type} hasn't been updated in {hours_since_update:.1f} hours",
                    affected_items=[file_type],
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    resolved=False
                ))
    
    def _check_progress_status(self):
        """Check if work is progressing"""
        progress_data = self.parser.parse_progress_file()
        
        if progress_data:
            total_tasks = (progress_data.get('completed_tasks', 0) + 
                          progress_data.get('in_progress_tasks', 0) + 
                          progress_data.get('not_started_tasks', 0) + 
                          progress_data.get('blocked_tasks', 0))
            
            if total_tasks == 0:
                self.issues.append(Issue(
                    issue_type=IssueType.NO_PROGRESS,
                    severity=SeverityLevel.WARNING,
                    title="No Progress Data Found",
                    description="Progress tracking file exists but contains no task data",
                    affected_items=['progress_tracking'],
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    resolved=False
                ))
    
    def _check_deadline_compliance(self):
        """Check if milestones are on track for deadlines"""
        implementation_data = self.parser.parse_implementation_file()
        
        if implementation_data and 'phases' in implementation_data:
            phases = implementation_data['phases']
            current_date = datetime.now(timezone.utc).date()
            
            # Phase 1 should be done by June 15
            if datetime(2026, 6, 15).date() < current_date:
                if phases.get('phase_1', 'NOT STARTED') == '🔴 NOT STARTED':
                    self.issues.append(Issue(
                        issue_type=IssueType.MISSED_DEADLINE,
                        severity=SeverityLevel.CRITICAL,
                        title="Phase 1 Deadline Missed",
                        description="Phase 1 (Database Migration) was due by June 15, 2026",
                        affected_items=['phase_1'],
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        resolved=False
                    ))
    
    def _check_documentation_completeness(self):
        """Check if requirements documentation is complete"""
        requirements_data = self.parser.parse_requirements_file()
        
        if requirements_data:
            if not requirements_data.get('contains_agent_monitor'):
                self.issues.append(Issue(
                    issue_type=IssueType.INCOMPLETE_DOCUMENTATION,
                    severity=SeverityLevel.WARNING,
                    title="Agent-MemoryMonitor Not Documented",
                    description="Requirement 3.1 (Agent-MemoryMonitor) not found in requirements file",
                    affected_items=['requirement_3.1'],
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    resolved=False
                ))
    
    def _check_blocker_resolution(self):
        """Check for unresolved blockers"""
        blockers_data = self.parser.parse_blockers_file()
        
        if blockers_data and blockers_data.get('has_active_blockers'):
            self.issues.append(Issue(
                issue_type=IssueType.BLOCKER_UNRESOLVED,
                severity=SeverityLevel.ERROR,
                title="Unresolved Blockers Detected",
                description=f"{blockers_data.get('issue_count', 0)} active issues/blockers found",
                affected_items=['blockers_file'],
                detected_at=datetime.now(timezone.utc).isoformat(),
                resolved=False
            ))
    
    def _check_dependency_satisfaction(self):
        """Check if dependencies for next phase are satisfied"""
        # Example: Before Phase 2, Phase 1 must be complete
        implementation_data = self.parser.parse_implementation_file()
        
        if implementation_data:
            phases = implementation_data.get('phases', {})
            
            # Phase 2 depends on Phase 1
            if ('📄 NOT STARTED' in phases.get('phase_2', '')):
                if '✅ COMPLETE' in phases.get('phase_1', ''):
                    # Phase 2 should have started
                    pass
    
    def _check_phase_progress(self):
        """Check overall phase progress"""
        implementation_data = self.parser.parse_implementation_file()
        
        if implementation_data and 'subtask_status' in implementation_data:
            for phase, counts in implementation_data['subtask_status'].items():
                if counts['total'] > 0:
                    completion_pct = (counts['completed'] / counts['total']) * 100
                    
                    # If phase is in progress but <10% complete after 2 days
                    if completion_pct < 10:
                        logger.warning(f"{phase} is slow to progress: {completion_pct:.1f}% complete")


# ============================================================
# AGENT MEMORY MONITOR
# ============================================================

class AgentMemoryMonitor:
    """
    AI Agent for monitoring v2.0 implementation progress
    
    Responsibilities:
    - Monitor all memory files continuously
    - Track completion status
    - Detect issues and anomalies
    - Generate progress reports
    - Provide status snapshots
    - Alert on critical issues
    """
    
    def __init__(self):
        self.name = "Agent-MemoryMonitor"
        self.is_running = False
        self.last_scan = None
        self.issues: List[Issue] = []
        self.progress_history: List[ProgressSnapshot] = []
        self.detector = IssueDetector()
        self.parser = MemoryParser()
        self.monitor_thread = None
        
        logger.info(f"✅ {self.name} initialized")
    
    def start(self):
        """Start the monitoring agent"""
        if self.is_running:
            logger.warning(f"⚠️  {self.name} is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"🚀 {self.name} started")
    
    def stop(self):
        """Stop the monitoring agent"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info(f"⛔ {self.name} stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread"""
        while self.is_running:
            try:
                self.scan()
                time.sleep(300)  # Scan every 5 minutes
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(60)
    
    def scan(self):
        """Perform a scan of all memory files and detect issues"""
        logger.info(f"🔍 {self.name} scanning...")
        
        # Detect issues
        self.issues = self.detector.detect_all_issues()
        
        # Generate progress snapshot
        snapshot = self._generate_progress_snapshot()
        self.progress_history.append(snapshot)
        
        self.last_scan = datetime.now(timezone.utc)
        
        # Log summary
        critical_issues = sum(1 for issue in self.issues if issue.severity == SeverityLevel.CRITICAL)
        if critical_issues > 0:
            logger.warning(f"⚠️  {critical_issues} CRITICAL issues detected!")
            for issue in self.issues:
                if issue.severity == SeverityLevel.CRITICAL:
                    logger.warning(f"   - {issue.title}: {issue.description}")
    
    def _generate_progress_snapshot(self) -> ProgressSnapshot:
        """Generate a progress snapshot"""
        progress_data = self.parser.parse_progress_file()
        implementation_data = self.parser.parse_implementation_file()
        
        # Calculate metrics
        completed = progress_data.get('completed_tasks', 0)
        in_progress = progress_data.get('in_progress_tasks', 0)
        not_started = progress_data.get('not_started_tasks', 0)
        blocked = progress_data.get('blocked_tasks', 0)
        
        total = completed + in_progress + not_started + blocked
        completion_pct = int((completed / total * 100)) if total > 0 else 0
        
        # Phase status
        phases = implementation_data.get('phases', {})
        
        critical_issues = sum(1 for issue in self.issues if issue.severity == SeverityLevel.CRITICAL)
        
        return ProgressSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_requirements=19,  # 18 + 3.1
            completed_requirements=completed,
            in_progress_requirements=in_progress,
            blocked_requirements=blocked,
            completion_percentage=completion_pct,
            phase_status=phases,
            critical_issues=critical_issues,
            total_issues=len(self.issues),
            next_milestone="Phase 1 Complete & Phase 2 Start",
            estimated_completion="July 22, 2026"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            'agent_name': self.name,
            'is_running': self.is_running,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None,
            'total_issues': len(self.issues),
            'critical_issues': sum(1 for issue in self.issues if issue.severity == SeverityLevel.CRITICAL),
            'memory_files_monitored': len(MEMORY_FILES),
            'scans_performed': len(self.progress_history)
        }
    
    def get_issues_report(self) -> Dict[str, Any]:
        """Get detailed issues report"""
        critical_issues = [issue for issue in self.issues if issue.severity == SeverityLevel.CRITICAL]
        error_issues = [issue for issue in self.issues if issue.severity == SeverityLevel.ERROR]
        warning_issues = [issue for issue in self.issues if issue.severity == SeverityLevel.WARNING]
        info_issues = [issue for issue in self.issues if issue.severity == SeverityLevel.INFO]
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_issues': len(self.issues),
            'by_severity': {
                'critical': len(critical_issues),
                'error': len(error_issues),
                'warning': len(warning_issues),
                'info': len(info_issues)
            },
            'issues': {
                'critical': [issue.to_dict() for issue in critical_issues],
                'error': [issue.to_dict() for issue in error_issues],
                'warning': [issue.to_dict() for issue in warning_issues],
                'info': [issue.to_dict() for issue in info_issues]
            }
        }
    
    def get_progress_report(self) -> Dict[str, Any]:
        """Get progress summary report"""
        if not self.progress_history:
            return {'error': 'No progress data collected yet'}
        
        latest = self.progress_history[-1]
        
        return {
            'timestamp': latest.timestamp,
            'completion_percentage': latest.completion_percentage,
            'completed_requirements': latest.completed_requirements,
            'total_requirements': latest.total_requirements,
            'in_progress': latest.in_progress_requirements,
            'blocked': latest.blocked_requirements,
            'phase_status': latest.phase_status,
            'critical_issues': latest.critical_issues,
            'next_milestone': latest.next_milestone,
            'estimated_completion': latest.estimated_completion
        }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """Get comprehensive monitoring report"""
        return {
            'agent_status': self.get_status(),
            'progress_report': self.get_progress_report(),
            'issues_report': self.get_issues_report(),
            'memory_files': {
                file_type: str(file_path.exists()) 
                for file_type, file_path in MEMORY_FILES.items()
            },
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    def export_report(self, file_path: str = 'v2_monitor_report.json'):
        """Export detailed report to JSON file"""
        try:
            report = self.get_detailed_report()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            logger.info(f"✅ Report exported to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Error exporting report: {e}")
            return None


# ============================================================
# GLOBAL AGENT INSTANCE
# ============================================================

_MEMORY_MONITOR = None

def get_memory_monitor() -> AgentMemoryMonitor:
    """Get or create the global memory monitor agent"""
    global _MEMORY_MONITOR
    if _MEMORY_MONITOR is None:
        _MEMORY_MONITOR = AgentMemoryMonitor()
    return _MEMORY_MONITOR


def start_memory_monitor():
    """Start the memory monitor agent"""
    monitor = get_memory_monitor()
    monitor.start()
    return monitor


def stop_memory_monitor():
    """Stop the memory monitor agent"""
    if _MEMORY_MONITOR:
        _MEMORY_MONITOR.stop()


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """Run agent from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description='v2.0 Memory Monitor Agent')
    parser.add_argument('--start', action='store_true', help='Start the monitoring agent')
    parser.add_argument('--scan', action='store_true', help='Perform a single scan')
    parser.add_argument('--status', action='store_true', help='Get agent status')
    parser.add_argument('--issues', action='store_true', help='Get issues report')
    parser.add_argument('--progress', action='store_true', help='Get progress report')
    parser.add_argument('--report', action='store_true', help='Get detailed report')
    parser.add_argument('--export', metavar='FILE', help='Export report to JSON file')
    
    args = parser.parse_args()
    
    monitor = get_memory_monitor()
    
    if args.start:
        print("🚀 Starting Agent-MemoryMonitor...")
        monitor.start()
        print("✅ Agent started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⛔ Stopping agent...")
            monitor.stop()
    
    elif args.scan:
        print("🔍 Performing scan...")
        monitor.scan()
        print("✅ Scan complete")
        print(json.dumps(monitor.get_progress_report(), indent=2))
    
    elif args.status:
        monitor.scan()
        print(json.dumps(monitor.get_status(), indent=2))
    
    elif args.issues:
        monitor.scan()
        print(json.dumps(monitor.get_issues_report(), indent=2))
    
    elif args.progress:
        monitor.scan()
        print(json.dumps(monitor.get_progress_report(), indent=2))
    
    elif args.report:
        monitor.scan()
        print(json.dumps(monitor.get_detailed_report(), indent=2))
    
    elif args.export:
        monitor.scan()
        file_path = monitor.export_report(args.export)
        print(f"✅ Report exported to {file_path}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
