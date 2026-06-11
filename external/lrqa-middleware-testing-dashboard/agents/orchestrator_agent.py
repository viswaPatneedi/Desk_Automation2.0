"""
Orchestrator Agent: Main coordinator for v2.0 AI Agent Framework
Manages all sub-agents (MemoryMonitor, ETA-DeviceLock, ScreenAnalyzer, etc.)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum
import json
from pathlib import Path

from agents.memory_monitor_agent import (
    AgentMemoryMonitor,
    get_memory_monitor,
    start_memory_monitor,
    stop_memory_monitor
)

logger = logging.getLogger(__name__)

# ============================================================
# AGENT REGISTRY & LIFECYCLE
# ============================================================

class AgentType(Enum):
    """Types of AI agents in v2.0 framework"""
    MEMORY_MONITOR = "memory_monitor"
    ETA_DEVICE_LOCK = "eta_device_lock"
    SCREEN_ANALYZER = "screen_analyzer"
    JOB_ORCHESTRATOR = "job_orchestrator"
    RECOVERY_AGENT = "recovery_agent"
    AUDIT_LOGGER = "audit_logger"


class AgentStatus(Enum):
    """Agent lifecycle states"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class OrchestratorAgent:
    """
    Master coordinator for all v2.0 AI agents
    
    Responsibilities:
    - Initialize and manage sub-agent lifecycle
    - Coordinate communication between agents
    - Monitor health and performance
    - Handle graceful shutdown
    - Provide unified status interface
    - Manage agent configuration
    
    Architecture:
    ```
    OrchestratorAgent (Parent)
    ├── Agent-MemoryMonitor (Progress tracking)
    ├── Agent-ETA-DeviceLock (Timing & locks)
    ├── Agent-ScreenAnalyzer (Screen validation via Claude Vision)
    ├── Agent-JobOrchestrator (Test job coordination)
    ├── Agent-Recovery (Failure recovery)
    └── Agent-AuditLogger (Compliance logging)
    ```
    """
    
    def __init__(self):
        self.name = "OrchestratorAgent"
        self.instance_id = datetime.now(timezone.utc).isoformat()
        self.agents: Dict[str, Optional[Any]] = {
            'memory_monitor': None,
            'eta_device_lock': None,
            'screen_analyzer': None,
            'job_orchestrator': None,
            'recovery': None,
            'audit_logger': None
        }
        self.agent_status: Dict[str, AgentStatus] = {
            agent_id: AgentStatus.IDLE for agent_id in self.agents
        }
        self.config = self._load_config()
        self.is_running = False
        
        logger.info(f"✅ {self.name} initialized (ID: {self.instance_id})")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration"""
        return {
            'enable_memory_monitor': True,
            'enable_eta_device_lock': True,
            'enable_screen_analyzer': True,
            'enable_job_orchestrator': True,
            'enable_recovery': True,
            'enable_audit_logger': True,
            'scan_interval': 300,  # 5 minutes
            'health_check_interval': 60,  # 1 minute
            'log_level': 'INFO'
        }
    
    # ============================================================
    # LIFECYCLE MANAGEMENT
    # ============================================================
    
    def start(self) -> bool:
        """Start the orchestrator and all enabled agents"""
        if self.is_running:
            logger.warning(f"⚠️  {self.name} is already running")
            return False
        
        logger.info(f"🚀 Starting {self.name}...")
        
        try:
            # Start MemoryMonitor first (tracks all other agents)
            if self.config['enable_memory_monitor']:
                self._start_agent('memory_monitor')
            
            # Start other critical agents
            if self.config['enable_eta_device_lock']:
                self._start_agent('eta_device_lock')
            
            if self.config['enable_job_orchestrator']:
                self._start_agent('job_orchestrator')
            
            # Start monitoring agents
            if self.config['enable_screen_analyzer']:
                self._start_agent('screen_analyzer')
            
            if self.config['enable_recovery']:
                self._start_agent('recovery')
            
            if self.config['enable_audit_logger']:
                self._start_agent('audit_logger')
            
            self.is_running = True
            logger.info(f"✅ {self.name} started successfully")
            self._log_startup_summary()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting {self.name}: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop all agents gracefully"""
        if not self.is_running:
            logger.warning(f"⚠️  {self.name} is not running")
            return False
        
        logger.info(f"⛔ Stopping {self.name}...")
        
        try:
            # Stop agents in reverse order
            for agent_id in reversed(list(self.agents.keys())):
                self._stop_agent(agent_id)
            
            self.is_running = False
            logger.info(f"✅ {self.name} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping {self.name}: {e}")
            return False
    
    def pause(self) -> bool:
        """Pause all agents without stopping"""
        if not self.is_running:
            logger.warning(f"⚠️  Cannot pause - {self.name} is not running")
            return False
        
        logger.info(f"⏸️  Pausing all agents...")
        
        for agent_id in self.agents:
            self.agent_status[agent_id] = AgentStatus.PAUSED
        
        logger.info("✅ All agents paused")
        return True
    
    def resume(self) -> bool:
        """Resume all paused agents"""
        logger.info(f"▶️  Resuming all agents...")
        
        for agent_id in self.agents:
            if self.agent_status[agent_id] == AgentStatus.PAUSED:
                self.agent_status[agent_id] = AgentStatus.RUNNING
        
        logger.info("✅ All agents resumed")
        return True
    
    def _start_agent(self, agent_id: str) -> bool:
        """Start a specific agent"""
        try:
            if agent_id == 'memory_monitor':
                self.agents['memory_monitor'] = start_memory_monitor()
                self.agent_status['memory_monitor'] = AgentStatus.RUNNING
                logger.info(f"✅ Started Agent-MemoryMonitor")
                return True
            
            elif agent_id == 'eta_device_lock':
                logger.info(f"🔄 Agent-ETA-DeviceLock initialization pending (Phase 2)")
                self.agent_status['eta_device_lock'] = AgentStatus.IDLE
                return True
            
            elif agent_id == 'screen_analyzer':
                logger.info(f"🔄 Agent-ScreenAnalyzer initialization pending (Phase 2)")
                self.agent_status['screen_analyzer'] = AgentStatus.IDLE
                return True
            
            elif agent_id == 'job_orchestrator':
                logger.info(f"🔄 Agent-JobOrchestrator initialization pending (Phase 2)")
                self.agent_status['job_orchestrator'] = AgentStatus.IDLE
                return True
            
            elif agent_id == 'recovery':
                logger.info(f"🔄 Agent-Recovery initialization pending (Phase 3)")
                self.agent_status['recovery'] = AgentStatus.IDLE
                return True
            
            elif agent_id == 'audit_logger':
                logger.info(f"🔄 Agent-AuditLogger initialization pending (Phase 3)")
                self.agent_status['audit_logger'] = AgentStatus.IDLE
                return True
            
            else:
                logger.warning(f"⚠️  Unknown agent: {agent_id}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error starting {agent_id}: {e}")
            self.agent_status[agent_id] = AgentStatus.ERROR
            return False
    
    def _stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent"""
        try:
            if agent_id == 'memory_monitor':
                stop_memory_monitor()
                self.agents['memory_monitor'] = None
                self.agent_status['memory_monitor'] = AgentStatus.STOPPED
                logger.info(f"✅ Stopped Agent-MemoryMonitor")
                return True
            
            else:
                self.agent_status[agent_id] = AgentStatus.STOPPED
                return True
        
        except Exception as e:
            logger.error(f"❌ Error stopping {agent_id}: {e}")
            return False
    
    # ============================================================
    # STATUS REPORTING
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator and all agents status"""
        return {
            'orchestrator': {
                'name': self.name,
                'instance_id': self.instance_id,
                'is_running': self.is_running,
                'started_at': self.instance_id
            },
            'agents': {
                agent_id: self.agent_status[agent_id].value
                for agent_id in self.agents
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status with agent-specific information"""
        status = self.get_status()
        
        # Add agent-specific details
        if self.agents['memory_monitor']:
            status['memory_monitor_details'] = (
                self.agents['memory_monitor'].get_status()
            )
        
        return status
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health check report for all agents"""
        
        health = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'orchestrator_health': 'healthy' if self.is_running else 'stopped',
            'agents': {}
        }
        
        # Check each agent
        for agent_id, agent in self.agents.items():
            agent_health = {
                'status': self.agent_status[agent_id].value,
                'healthy': self.agent_status[agent_id] in [
                    AgentStatus.RUNNING,
                    AgentStatus.IDLE
                ]
            }
            
            # Add agent-specific health info
            if agent_id == 'memory_monitor' and agent:
                agent_health['monitoring_active'] = agent.is_running
                agent_health['issues_count'] = len(agent.issues)
                agent_health['progress_history'] = len(agent.progress_history)
            
            health['agents'][agent_id] = agent_health
        
        health['overall_health'] = all(
            agent_health['healthy'] 
            for agent_health in health['agents'].values()
        )
        
        return health
    
    # ============================================================
    # REPORTING & EXPORTS
    # ============================================================
    
    def get_full_report(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator report"""
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'orchestrator_status': self.get_status(),
            'health_report': self.get_health_report(),
            'agent_reports': {}
        }
        
        # Include MemoryMonitor report
        if self.agents['memory_monitor']:
            report['agent_reports']['memory_monitor'] = (
                self.agents['memory_monitor'].get_detailed_report()
            )
        
        return report
    
    def export_report(self, file_path: str = 'orchestrator_report.json') -> Optional[str]:
        """Export full report to JSON"""
        try:
            report = self.get_full_report()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            logger.info(f"✅ Report exported to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Error exporting report: {e}")
            return None
    
    # ============================================================
    # UTILITIES
    # ============================================================
    
    def _log_startup_summary(self):
        """Log startup summary of enabled agents"""
        logger.info("=" * 60)
        logger.info("v2.0 AI AGENT FRAMEWORK - STARTUP SUMMARY")
        logger.info("=" * 60)
        
        for agent_id, status in self.agent_status.items():
            emoji = "✅" if status == AgentStatus.RUNNING else "🔄"
            logger.info(f"{emoji} {agent_id}: {status.value}")
        
        logger.info("=" * 60)
    
    def get_agent_count(self) -> int:
        """Get count of configured agents"""
        return len(self.agents)
    
    def get_running_agent_count(self) -> int:
        """Get count of running agents"""
        return sum(
            1 for status in self.agent_status.values()
            if status == AgentStatus.RUNNING
        )


# ============================================================
# GLOBAL ORCHESTRATOR INSTANCE
# ============================================================

_ORCHESTRATOR = None

def get_orchestrator() -> OrchestratorAgent:
    """Get or create global orchestrator instance"""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = OrchestratorAgent()
    return _ORCHESTRATOR


def start_orchestrator() -> OrchestratorAgent:
    """Start the orchestrator"""
    orchestrator = get_orchestrator()
    orchestrator.start()
    return orchestrator


def stop_orchestrator():
    """Stop the orchestrator"""
    if _ORCHESTRATOR:
        _ORCHESTRATOR.stop()


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """Run orchestrator from command line"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='v2.0 Orchestrator Agent')
    parser.add_argument('--start', action='store_true', help='Start the orchestrator')
    parser.add_argument('--stop', action='store_true', help='Stop the orchestrator')
    parser.add_argument('--status', action='store_true', help='Get orchestrator status')
    parser.add_argument('--health', action='store_true', help='Get health report')
    parser.add_argument('--report', action='store_true', help='Get full report')
    parser.add_argument('--export', metavar='FILE', help='Export report to JSON')
    parser.add_argument('--pause', action='store_true', help='Pause all agents')
    parser.add_argument('--resume', action='store_true', help='Resume all agents')
    
    args = parser.parse_args()
    
    orchestrator = get_orchestrator()
    
    if args.start:
        print("🚀 Starting Orchestrator Agent...")
        orchestrator.start()
        print("✅ Orchestrator started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⛔ Stopping orchestrator...")
            orchestrator.stop()
    
    elif args.stop:
        print("⛔ Stopping Orchestrator Agent...")
        orchestrator.stop()
        print("✅ Stopped")
    
    elif args.status:
        orchestrator.start()  # Ensure agents are initialized
        print(json.dumps(orchestrator.get_status(), indent=2))
        orchestrator.stop()
    
    elif args.health:
        orchestrator.start()
        print(json.dumps(orchestrator.get_health_report(), indent=2))
        orchestrator.stop()
    
    elif args.report:
        orchestrator.start()
        print(json.dumps(orchestrator.get_full_report(), indent=2))
        orchestrator.stop()
    
    elif args.export:
        orchestrator.start()
        file_path = orchestrator.export_report(args.export)
        print(f"✅ Report exported to {file_path}")
        orchestrator.stop()
    
    elif args.pause:
        orchestrator.pause()
        print("✅ All agents paused")
    
    elif args.resume:
        orchestrator.resume()
        print("✅ All agents resumed")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
