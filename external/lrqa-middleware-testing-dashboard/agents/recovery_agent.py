"""
Agent-Recovery: Failure Recovery & Retry Agent
Handles execution failures, recovery strategies, and intelligent retry logic
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

# ============================================================
# DATA CLASSES & ENUMS
# ============================================================

class FailureType(Enum):
    """Types of failures that can occur"""
    DEVICE_UNREACHABLE = "device_unreachable"
    SSH_CONNECTION_FAILED = "ssh_connection_failed"
    COMMAND_TIMEOUT = "command_timeout"
    INVALID_COMMAND = "invalid_command"
    DEVICE_LOCKED = "device_locked"
    SCREEN_VALIDATION_FAILED = "screen_validation_failed"
    PARTIAL_EXECUTION = "partial_execution"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies available"""
    IMMEDIATE_RETRY = "immediate_retry"           # Retry immediately
    EXPONENTIAL_BACKOFF = "exponential_backoff"   # Wait with exponential backoff
    MANUAL_INTERVENTION = "manual_intervention"   # Wait for manual action
    DEVICE_REBOOT = "device_reboot"              # Reboot device and retry
    SKIP_ITERATIONS = "skip_iterations"          # Skip failed iteration, continue
    ABORT = "abort"                              # Abort job


@dataclass
class FailureRecord:
    """Record of a failure"""
    job_id: str
    device_id: str
    failure_type: str
    error_message: str
    timestamp: str
    iteration: int = 0
    attempt: int = 1
    result: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'device_id': self.device_id,
            'failure_type': self.failure_type,
            'error_message': self.error_message,
            'timestamp': self.timestamp,
            'iteration': self.iteration,
            'attempt': self.attempt,
            'result': self.result
        }


@dataclass
class RecoveryPlan:
    """Recovery plan for a failure"""
    job_id: str
    failure_record: FailureRecord
    strategy: str
    retry_count_max: int = 3
    retry_delay_seconds: int = 5
    should_reboot: bool = False
    skip_failed_iteration: bool = False
    estimated_recovery_time: int = 0
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'strategy': self.strategy,
            'retry_count_max': self.retry_count_max,
            'retry_delay_seconds': self.retry_delay_seconds,
            'should_reboot': self.should_reboot,
            'skip_failed_iteration': self.skip_failed_iteration,
            'estimated_recovery_time': self.estimated_recovery_time
        }


# ============================================================
# FAILURE ANALYZER
# ============================================================

class FailureAnalyzer:
    """Analyze failures and determine recovery strategies"""
    
    # Retry configuration by failure type
    RETRY_CONFIG = {
        FailureType.DEVICE_UNREACHABLE.value: {
            'max_retries': 5,
            'strategy': RecoveryStrategy.EXPONENTIAL_BACKOFF.value,
            'base_delay': 10,
            'should_reboot': True
        },
        FailureType.SSH_CONNECTION_FAILED.value: {
            'max_retries': 3,
            'strategy': RecoveryStrategy.EXPONENTIAL_BACKOFF.value,
            'base_delay': 5,
            'should_reboot': False
        },
        FailureType.COMMAND_TIMEOUT.value: {
            'max_retries': 2,
            'strategy': RecoveryStrategy.IMMEDIATE_RETRY.value,
            'base_delay': 0,
            'should_reboot': False
        },
        FailureType.DEVICE_LOCKED.value: {
            'max_retries': 4,
            'strategy': RecoveryStrategy.EXPONENTIAL_BACKOFF.value,
            'base_delay': 3,
            'should_reboot': False
        },
        FailureType.SCREEN_VALIDATION_FAILED.value: {
            'max_retries': 2,
            'strategy': RecoveryStrategy.IMMEDIATE_RETRY.value,
            'base_delay': 2,
            'should_reboot': False
        },
        FailureType.PARTIAL_EXECUTION.value: {
            'max_retries': 3,
            'strategy': RecoveryStrategy.SKIP_ITERATIONS.value,
            'base_delay': 5,
            'should_reboot': False
        },
        FailureType.UNKNOWN.value: {
            'max_retries': 1,
            'strategy': RecoveryStrategy.MANUAL_INTERVENTION.value,
            'base_delay': 0,
            'should_reboot': False
        }
    }
    
    def analyze_failure(
        self,
        job_id: str,
        device_id: str,
        error_message: str,
        iteration: int = 0,
        current_attempt: int = 1
    ) -> Tuple[FailureRecord, RecoveryPlan]:
        """
        Analyze failure and determine recovery strategy
        
        Returns:
            Tuple of (FailureRecord, RecoveryPlan)
        """
        # Classify failure type
        failure_type = self._classify_failure(error_message)
        
        # Create failure record
        failure_record = FailureRecord(
            job_id=job_id,
            device_id=device_id,
            failure_type=failure_type,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            iteration=iteration,
            attempt=current_attempt
        )
        
        # Get retry config
        config = self.RETRY_CONFIG.get(failure_type, self.RETRY_CONFIG['unknown'])
        
        # Determine if we should continue retrying
        should_retry = current_attempt <= config['max_retries']
        
        # Calculate delay
        if config['strategy'] == RecoveryStrategy.EXPONENTIAL_BACKOFF.value:
            delay = config['base_delay'] * (2 ** (current_attempt - 1))
        else:
            delay = config['base_delay']
        
        # Create recovery plan
        recovery_plan = RecoveryPlan(
            job_id=job_id,
            failure_record=failure_record,
            strategy=config['strategy'] if should_retry else RecoveryStrategy.ABORT.value,
            retry_count_max=config['max_retries'],
            retry_delay_seconds=int(delay),
            should_reboot=config['should_reboot'] and current_attempt > 1,
            estimated_recovery_time=int(delay)
        )
        
        logger.info(
            f"📊 Failure analyzed: {failure_type} → Strategy: {recovery_plan.strategy} "
            f"(retry in {delay}s)"
        )
        
        return failure_record, recovery_plan
    
    def _classify_failure(self, error_message: str) -> str:
        """Classify error message to failure type"""
        error_lower = error_message.lower()
        
        if any(x in error_lower for x in ['unreachable', 'no route', 'network unreachable']):
            return FailureType.DEVICE_UNREACHABLE.value
        
        elif any(x in error_lower for x in ['ssh', 'connection refused', 'connection reset']):
            return FailureType.SSH_CONNECTION_FAILED.value
        
        elif any(x in error_lower for x in ['timeout', 'timed out']):
            return FailureType.COMMAND_TIMEOUT.value
        
        elif any(x in error_lower for x in ['invalid command', 'command not found']):
            return FailureType.INVALID_COMMAND.value
        
        elif any(x in error_lower for x in ['locked', 'lock', 'in use']):
            return FailureType.DEVICE_LOCKED.value
        
        elif any(x in error_lower for x in ['screen', 'validation', 'visual', 'element']):
            return FailureType.SCREEN_VALIDATION_FAILED.value
        
        elif any(x in error_lower for x in ['partial', 'incomplete', 'partial execution']):
            return FailureType.PARTIAL_EXECUTION.value
        
        return FailureType.UNKNOWN.value


# ============================================================
# RECOVERY EXECUTOR
# ============================================================

class RecoveryExecutor:
    """Execute recovery actions"""
    
    def __init__(self):
        self.active_recoveries: Dict[str, Dict[str, Any]] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
    
    def execute_recovery(self, recovery_plan: RecoveryPlan) -> Dict[str, Any]:
        """
        Execute a recovery plan
        
        Returns:
            Recovery execution result
        """
        job_id = recovery_plan.job_id
        
        with self.lock:
            if job_id in self.active_recoveries:
                return {'error': f'Recovery already in progress for {job_id}'}
            
            self.active_recoveries[job_id] = {
                'plan': recovery_plan.to_dict(),
                'started_at': datetime.now(timezone.utc).isoformat(),
                'status': 'in_progress'
            }
        
        strategy = recovery_plan.strategy
        
        logger.info(f"🔧 Executing recovery: {strategy}")
        
        result = {
            'job_id': job_id,
            'strategy': strategy,
            'status': 'started',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if strategy == RecoveryStrategy.IMMEDIATE_RETRY.value:
            result.update(self._immediate_retry(recovery_plan))
        
        elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF.value:
            result.update(self._exponential_backoff(recovery_plan))
        
        elif strategy == RecoveryStrategy.DEVICE_REBOOT.value:
            result.update(self._device_reboot(recovery_plan))
        
        elif strategy == RecoveryStrategy.SKIP_ITERATIONS.value:
            result.update(self._skip_iterations(recovery_plan))
        
        elif strategy == RecoveryStrategy.MANUAL_INTERVENTION.value:
            result.update(self._manual_intervention(recovery_plan))
        
        elif strategy == RecoveryStrategy.ABORT.value:
            result.update(self._abort(recovery_plan))
        
        # Record result
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        with self.lock:
            if job_id in self.active_recoveries:
                self.active_recoveries[job_id]['status'] = 'completed'
                self.recovery_history.append(result)
        
        return result
    
    def _immediate_retry(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Immediate retry without delay"""
        return {
            'action': 'immediate_retry',
            'retry_in_seconds': 0,
            'instructions': 'Retry immediately without delay'
        }
    
    def _exponential_backoff(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Retry with exponential backoff"""
        delay = plan.retry_delay_seconds
        
        return {
            'action': 'exponential_backoff',
            'retry_in_seconds': delay,
            'retry_count_remaining': max(0, plan.retry_count_max - plan.failure_record.attempt),
            'instructions': f'Wait {delay}s then retry'
        }
    
    def _device_reboot(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Reboot device and retry"""
        return {
            'action': 'device_reboot',
            'device_id': plan.failure_record.device_id,
            'reboot_wait_seconds': 30,
            'instructions': 'Reboot device, wait 30s, then retry'
        }
    
    def _skip_iterations(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Skip failed iteration and continue with next"""
        return {
            'action': 'skip_iterations',
            'skip_count': 1,
            'iteration': plan.failure_record.iteration,
            'instructions': f'Skip iteration {plan.failure_record.iteration}, continue with next'
        }
    
    def _manual_intervention(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Wait for manual intervention"""
        return {
            'action': 'manual_intervention',
            'status': 'waiting',
            'instructions': 'Manual intervention required. Check device and retry manually.'
        }
    
    def _abort(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Abort the job"""
        return {
            'action': 'abort',
            'status': 'aborted',
            'reason': 'Max retries exceeded',
            'instructions': 'Job aborted. Manual review recommended.'
        }
    
    def get_recovery_history(self, job_id: str = None) -> List[Dict[str, Any]]:
        """Get recovery history"""
        with self.lock:
            if job_id:
                return [r for r in self.recovery_history if r.get('job_id') == job_id]
            return self.recovery_history
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        with self.lock:
            history = self.recovery_history
        
        if not history:
            return {'total_recoveries': 0, 'success_rate': 0}
        
        successful = sum(1 for r in history if r.get('status') == 'completed')
        
        return {
            'total_recoveries': len(history),
            'successful': successful,
            'success_rate': (successful / len(history) * 100) if history else 0,
            'by_strategy': self._stats_by_strategy(history)
        }
    
    def _stats_by_strategy(self, history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count recoveries by strategy"""
        stats = {}
        for record in history:
            strategy = record.get('strategy', 'unknown')
            stats[strategy] = stats.get(strategy, 0) + 1
        return stats


# ============================================================
# AGENT-RECOVERY
# ============================================================

class AgentRecovery:
    """
    AI Agent for failure recovery and intelligent retry
    
    Responsibilities:
    - Detect and classify failures
    - Generate recovery plans
    - Execute recovery strategies
    - Track recovery success rates
    - Learn from failure patterns
    """
    
    def __init__(self):
        self.name = "Agent-Recovery"
        self.is_running = False
        self.failure_analyzer = FailureAnalyzer()
        self.recovery_executor = RecoveryExecutor()
        self.monitor_thread = None
        self.failure_patterns: Dict[str, int] = {}
        
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
                # Monitor active recoveries
                time.sleep(15)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(30)
    
    def handle_failure(
        self,
        job_id: str,
        device_id: str,
        error_message: str,
        iteration: int = 0,
        current_attempt: int = 1
    ) -> Dict[str, Any]:
        """
        Handle a job failure with automatic recovery
        
        Args:
            job_id: Job identifier
            device_id: Device that failed
            error_message: Error message
            iteration: Iteration number (if multi-iteration)
            current_attempt: Current retry attempt number
        
        Returns:
            Recovery plan and execution result
        """
        try:
            # Analyze failure
            failure_record, recovery_plan = self.failure_analyzer.analyze_failure(
                job_id=job_id,
                device_id=device_id,
                error_message=error_message,
                iteration=iteration,
                current_attempt=current_attempt
            )
            
            # Track failure pattern
            failure_type = failure_record.failure_type
            self.failure_patterns[failure_type] = self.failure_patterns.get(failure_type, 0) + 1
            
            # Execute recovery
            recovery_result = self.recovery_executor.execute_recovery(recovery_plan)
            
            return {
                'success': True,
                'failure': failure_record.to_dict(),
                'recovery_plan': recovery_plan.to_dict(),
                'recovery_result': recovery_result
            }
        
        except Exception as e:
            logger.error(f"❌ Error handling failure: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_recovery_history(self, job_id: str = None) -> List[Dict[str, Any]]:
        """Get recovery history for a job or all jobs"""
        return self.recovery_executor.get_recovery_history(job_id)
    
    def get_failure_patterns(self) -> Dict[str, int]:
        """Get failure patterns detected"""
        return dict(sorted(
            self.failure_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        ))
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status"""
        stats = self.recovery_executor.get_recovery_stats()
        
        return {
            'agent_name': self.name,
            'is_running': self.is_running,
            'recovery_stats': stats,
            'failure_patterns': self.get_failure_patterns(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_recommendations(self) -> List[str]:
        """Get recommendations based on failure patterns"""
        recommendations = []
        patterns = self.get_failure_patterns()
        
        for failure_type, count in patterns.items():
            if failure_type == FailureType.DEVICE_UNREACHABLE.value and count > 2:
                recommendations.append(f"⚠️  Frequent device unreachable errors ({count}). Check network connectivity.")
            
            elif failure_type == FailureType.SSH_CONNECTION_FAILED.value and count > 2:
                recommendations.append(f"⚠️  Frequent SSH failures ({count}). Check SSH service on devices.")
            
            elif failure_type == FailureType.COMMAND_TIMEOUT.value and count > 3:
                recommendations.append(f"⚠️  Frequent timeouts ({count}). Consider increasing timeout values.")
            
            elif failure_type == FailureType.SCREEN_VALIDATION_FAILED.value and count > 3:
                recommendations.append(f"⚠️  Frequent screen validation failures ({count}). Review element definitions.")
            
            elif failure_type == FailureType.DEVICE_LOCKED.value and count > 2:
                recommendations.append(f"⚠️  Device lock conflicts ({count}). Check concurrent job scheduling.")
        
        if not recommendations:
            recommendations.append("✅ System operating normally. No issues detected.")
        
        return recommendations


# ============================================================
# GLOBAL AGENT INSTANCE
# ============================================================

_RECOVERY_AGENT = None

def get_recovery_agent() -> AgentRecovery:
    """Get or create the global Recovery agent"""
    global _RECOVERY_AGENT
    if _RECOVERY_AGENT is None:
        _RECOVERY_AGENT = AgentRecovery()
    return _RECOVERY_AGENT


def start_recovery_agent():
    """Start the Recovery agent"""
    agent = get_recovery_agent()
    agent.start()
    return agent


def stop_recovery_agent():
    """Stop the Recovery agent"""
    if _RECOVERY_AGENT:
        _RECOVERY_AGENT.stop()


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI interface for agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent-Recovery')
    parser.add_argument('--start', action='store_true', help='Start the agent')
    parser.add_argument('--status', action='store_true', help='Get agent status')
    parser.add_argument('--recommendations', action='store_true', help='Get recommendations')
    
    args = parser.parse_args()
    
    agent = get_recovery_agent()
    
    if args.start:
        print("🚀 Starting Agent-Recovery...")
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
    
    elif args.recommendations:
        agent.start()
        print("\n📋 Recovery Recommendations:\n")
        for rec in agent.get_recommendations():
            print(f"  {rec}")
        print()
        agent.stop()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
