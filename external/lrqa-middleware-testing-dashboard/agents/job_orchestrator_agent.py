"""
Agent-JobOrchestrator: Test Job Execution Coordinator
Manages test job execution, coordinates between agents, and orchestrates workflow
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)

# ============================================================
# DATA CLASSES & ENUMS
# ============================================================

class JobState(Enum):
    """Job execution states"""
    PENDING = "pending"
    QUEUED = "queued"
    ACQUIRING_LOCK = "acquiring_lock"
    LOCKED = "locked"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionPhase(Enum):
    """Phases during job execution"""
    PRE_EXECUTION = "pre_execution"
    DEVICE_LOCK = "device_lock"
    TEST_EXECUTION = "test_execution"
    SCREEN_VALIDATION = "screen_validation"
    RESULT_PROCESSING = "result_processing"
    CLEANUP = "cleanup"


@dataclass
class JobExecution:
    """Execution record for a job"""
    job_id: str
    device_id: str
    method: str
    iterations: int
    state: str
    current_phase: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'device_id': self.device_id,
            'method': self.method,
            'iterations': self.iterations,
            'state': self.state,
            'current_phase': self.current_phase,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration_seconds': self.duration_seconds,
            'error': self.error,
            'result': self.result
        }


# ============================================================
# JOB QUEUE MANAGER
# ============================================================

class JobQueueManager:
    """Manage job execution queue"""
    
    def __init__(self):
        self.pending_jobs: List[Dict[str, Any]] = []
        self.executing_jobs: Dict[str, JobExecution] = {}
        self.completed_jobs: List[JobExecution] = []
        self.lock = threading.Lock()
    
    def add_job(self, device_id: str, method: str, iterations: int = 1, priority: int = 5) -> str:
        """
        Add a job to the queue
        
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        with self.lock:
            self.pending_jobs.append({
                'job_id': job_id,
                'device_id': device_id,
                'method': method,
                'iterations': iterations,
                'priority': priority,
                'added_at': datetime.now(timezone.utc).isoformat()
            })
        
        logger.info(f"📋 Job added to queue: {job_id} ({method} on {device_id})")
        return job_id
    
    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """Get next job from queue (sorted by priority)"""
        with self.lock:
            if not self.pending_jobs:
                return None
            
            # Sort by priority (highest first)
            self.pending_jobs.sort(key=lambda x: x['priority'], reverse=True)
            job = self.pending_jobs.pop(0)
            
            return job
    
    def start_execution(self, job_id: str, device_id: str, method: str, iterations: int) -> JobExecution:
        """Mark job as executing"""
        execution = JobExecution(
            job_id=job_id,
            device_id=device_id,
            method=method,
            iterations=iterations,
            state=JobState.EXECUTING.value,
            current_phase=ExecutionPhase.DEVICE_LOCK.value,
            started_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.lock:
            self.executing_jobs[job_id] = execution
        
        logger.info(f"▶️  Execution started: {job_id}")
        return execution
    
    def update_execution(
        self,
        job_id: str,
        state: JobState = None,
        phase: ExecutionPhase = None,
        error: str = None
    ):
        """Update job execution state"""
        with self.lock:
            if job_id not in self.executing_jobs:
                return
            
            exec_info = self.executing_jobs[job_id]
            
            if state:
                exec_info.state = state.value
            if phase:
                exec_info.current_phase = phase.value
            if error:
                exec_info.error = error
    
    def complete_execution(
        self,
        job_id: str,
        success: bool,
        result: Dict[str, Any] = None,
        error: str = None
    ) -> JobExecution:
        """Mark job as completed"""
        with self.lock:
            if job_id not in self.executing_jobs:
                logger.warning(f"No executing job found: {job_id}")
                return None
            
            execution = self.executing_jobs.pop(job_id)
            
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            execution.state = JobState.COMPLETED.value if success else JobState.FAILED.value
            execution.current_phase = ExecutionPhase.CLEANUP.value
            execution.result = result
            if error:
                execution.error = error
            
            # Calculate duration
            start = datetime.fromisoformat(execution.started_at)
            end = datetime.fromisoformat(execution.completed_at)
            execution.duration_seconds = int((end - start).total_seconds())
            
            self.completed_jobs.append(execution)
        
        status = "✅ COMPLETED" if success else "❌ FAILED"
        logger.info(f"{status}: {job_id} ({execution.duration_seconds}s)")
        
        return execution
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        with self.lock:
            return {
                'pending_jobs': len(self.pending_jobs),
                'executing_jobs': len(self.executing_jobs),
                'completed_jobs': len(self.completed_jobs),
                'total_processed': len(self.completed_jobs),
                'average_duration': self._get_average_duration()
            }
    
    def _get_average_duration(self) -> Optional[int]:
        """Calculate average job duration"""
        if not self.completed_jobs:
            return None
        
        total = sum(j.duration_seconds for j in self.completed_jobs if j.duration_seconds)
        return int(total / len(self.completed_jobs)) if total else None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        with self.lock:
            if job_id in self.executing_jobs:
                return {'status': 'executing', **self.executing_jobs[job_id].to_dict()}
            
            for job in self.completed_jobs:
                if job.job_id == job_id:
                    return {'status': 'completed', **job.to_dict()}
        
        return None


# ============================================================
# AGENT-JOB-ORCHESTRATOR
# ============================================================

class AgentJobOrchestrator:
    """
    AI Agent for test job execution orchestration
    
    Responsibilities:
    - Queue and manage jobs
    - Coordinate between other agents (Lock, ScreenAnalyzer)
    - Orchestrate execution workflow
    - Track job progress and completion
    - Handle job cancellation and retry
    """
    
    def __init__(self):
        self.name = "Agent-JobOrchestrator"
        self.is_running = False
        self.queue_manager = JobQueueManager()
        self.monitor_thread = None
        self.execution_callbacks: Dict[str, Any] = {}
        
        logger.info(f"✅ {self.name} initialized")
    
    def start(self):
        """Start the agent"""
        if self.is_running:
            logger.warning(f"⚠️  {self.name} is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"🚀 {self.name} started")
    
    def stop(self):
        """Stop the agent"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info(f"⛔ {self.name} stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Monitor queue (but don't execute - let callers execute jobs)
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(20)
    
    def submit_job(
        self,
        device_id: str,
        method: str,
        iterations: int = 1,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Submit a job for execution
        
        Args:
            device_id: Target device
            method: Method to execute
            iterations: Number of iterations
            priority: Job priority (1-10)
        
        Returns:
            Job submission info with job_id
        """
        try:
            job_id = self.queue_manager.add_job(device_id, method, iterations, priority)
            
            return {
                'success': True,
                'job_id': job_id,
                'device_id': device_id,
                'method': method,
                'iterations': iterations,
                'status': 'queued',
                'queued_at': datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Error submitting job: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Get next job from queue
        
        Returns:
            Next job to execute or None
        """
        return self.queue_manager.get_next_job()
    
    def start_job_execution(self, job_id: str, device_id: str, method: str, iterations: int) -> Dict[str, Any]:
        """
        Mark job as starting execution
        
        This should be called when the job is about to start running
        """
        try:
            execution = self.queue_manager.start_execution(job_id, device_id, method, iterations)
            
            return {
                'success': True,
                'job_id': job_id,
                'state': execution.state,
                'started_at': execution.started_at
            }
        
        except Exception as e:
            logger.error(f"❌ Error starting execution: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_job_progress(
        self,
        job_id: str,
        phase: str,
        progress_percent: int = None
    ) -> Dict[str, Any]:
        """
        Update job progress
        
        Args:
            job_id: Job identifier
            phase: Current execution phase
            progress_percent: Progress as percentage (0-100)
        
        Returns:
            Update status
        """
        try:
            phase_enum = ExecutionPhase[phase.upper()]
            self.queue_manager.update_execution(job_id, phase=phase_enum)
            
            return {
                'success': True,
                'job_id': job_id,
                'phase': phase,
                'progress': progress_percent
            }
        
        except Exception as e:
            logger.error(f"❌ Error updating job progress: {e}")
            return {'success': False, 'error': str(e)}
    
    def complete_job(
        self,
        job_id: str,
        success: bool,
        result: Dict[str, Any] = None,
        error: str = None
    ) -> Dict[str, Any]:
        """
        Mark job as completed
        
        Args:
            job_id: Job identifier
            success: Whether job succeeded
            result: Execution result
            error: Error message if failed
        
        Returns:
            Completion info
        """
        try:
            execution = self.queue_manager.complete_execution(job_id, success, result, error)
            
            if not execution:
                return {'success': False, 'error': 'Job not found'}
            
            return {
                'success': True,
                'job_id': job_id,
                'final_state': execution.state,
                'duration_seconds': execution.duration_seconds,
                'result': execution.result
            }
        
        except Exception as e:
            logger.error(f"❌ Error completing job: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get current status of a job"""
        status = self.queue_manager.get_job_status(job_id)
        
        if not status:
            return {'error': f'Job not found: {job_id}'}
        
        return status
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return self.queue_manager.get_queue_status()
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status"""
        queue_status = self.get_queue_status()
        
        return {
            'agent_name': self.name,
            'is_running': self.is_running,
            'queue': queue_status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a pending or executing job"""
        try:
            execution = self.queue_manager.complete_execution(
                job_id, False, error="Job cancelled by user"
            )
            
            if execution:
                return {'success': True, 'job_id': job_id, 'cancelled': True}
            else:
                return {'success': False, 'error': 'Job not found'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================
# GLOBAL AGENT INSTANCE
# ============================================================

_JOB_ORCHESTRATOR_AGENT = None

def get_job_orchestrator_agent() -> AgentJobOrchestrator:
    """Get or create the global JobOrchestrator agent"""
    global _JOB_ORCHESTRATOR_AGENT
    if _JOB_ORCHESTRATOR_AGENT is None:
        _JOB_ORCHESTRATOR_AGENT = AgentJobOrchestrator()
    return _JOB_ORCHESTRATOR_AGENT


def start_job_orchestrator_agent():
    """Start the JobOrchestrator agent"""
    agent = get_job_orchestrator_agent()
    agent.start()
    return agent


def stop_job_orchestrator_agent():
    """Stop the JobOrchestrator agent"""
    if _JOB_ORCHESTRATOR_AGENT:
        _JOB_ORCHESTRATOR_AGENT.stop()


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI interface for agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent-JobOrchestrator')
    parser.add_argument('--start', action='store_true', help='Start the agent')
    parser.add_argument('--status', action='store_true', help='Get agent status')
    parser.add_argument('--queue', action='store_true', help='Get queue status')
    
    args = parser.parse_args()
    
    agent = get_job_orchestrator_agent()
    
    if args.start:
        print("🚀 Starting Agent-JobOrchestrator...")
        agent.start()
        print("✅ Agent started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⛔ Stopping agent...")
            agent.stop()
    
    elif args.status:
        import json
        agent.start()
        print(json.dumps(agent.get_agent_status(), indent=2))
        agent.stop()
    
    elif args.queue:
        import json
        agent.start()
        print(json.dumps(agent.get_queue_status(), indent=2))
        agent.stop()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
