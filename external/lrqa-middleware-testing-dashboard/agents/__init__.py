"""
v2.0 AI Agent Framework

Multi-agent system for automated device testing and management:
- OrchestratorAgent: Master coordinator
- Agent-MemoryMonitor: Progress tracking and issue detection
- Agent-ETA-DeviceLock: Device lock and timing management
- Agent-ScreenAnalyzer: Screen validation using Claude Vision
- Agent-JobOrchestrator: Job execution coordination
- Agent-Recovery: Failure recovery and restart logic
- Agent-DistributedSync: Multi-location data synchronization
- Agent-PyArmor: Code encryption and obfuscation
- Agent-DockerSigning: GPG image signing and verification
- Agent-VaultSecrets: HashiCorp Vault secrets management
"""

from agents.orchestrator_agent import (
    OrchestratorAgent,
    AgentStatus,
    AgentType,
    get_orchestrator,
    start_orchestrator,
    stop_orchestrator
)

from agents.memory_monitor_agent import (
    AgentMemoryMonitor,
    IssueDetector,
    MemoryParser,
    ProgressSnapshot,
    Issue,
    IssueType,
    SeverityLevel,
    get_memory_monitor,
    start_memory_monitor,
    stop_memory_monitor
)

from agents.eta_device_lock_agent import (
    AgentETADeviceLock,
    DeviceLockManager,
    ETACalculator,
    get_eta_device_lock_agent,
    start_eta_device_lock_agent,
    stop_eta_device_lock_agent
)

from agents.screen_analyzer_agent import (
    AgentScreenAnalyzer,
    ScreenAnalyzerWrapper,
    ScreenAnalysisType,
    get_screen_analyzer_agent,
    start_screen_analyzer_agent,
    stop_screen_analyzer_agent
)

from agents.job_orchestrator_agent import (
    AgentJobOrchestrator,
    JobQueueManager,
    JobState,
    ExecutionPhase,
    get_job_orchestrator_agent,
    start_job_orchestrator_agent,
    stop_job_orchestrator_agent
)

from agents.recovery_agent import (
    AgentRecovery,
    FailureAnalyzer,
    RecoveryExecutor,
    FailureType,
    RecoveryStrategy,
    get_recovery_agent,
    start_recovery_agent,
    stop_recovery_agent
)

from agents.distributed_sync_agent import (
    AgentDistributedSync,
    SyncManager,
    SyncValidator,
    ConflictResolver,
    AuditLogger,
    LocalSyncCache,
    SyncChange,
    SyncEventType,
    EntityType,
    OperationType,
    ConflictType
)

from agents.pyarmor_encryption_agent import (
    PyArmorAgent,
    EncryptionConfig,
    EncryptionMode,
    EncryptionError
)

from agents.docker_signing_agent import (
    DockerImageSigningAgent,
    GPGConfig,
    GPGError
)

from config.vault_config import (
    VaultClient,
    VaultClientConfig,
    get_vault_client,
    get_db_credentials,
    get_github_token,
    get_api_keys
)

__all__ = [
    # Orchestrator
    'OrchestratorAgent',
    'AgentStatus',
    'AgentType',
    'get_orchestrator',
    'start_orchestrator',
    'stop_orchestrator',
    
    # Memory Monitor
    'AgentMemoryMonitor',
    'IssueDetector',
    'MemoryParser',
    'ProgressSnapshot',
    'Issue',
    'IssueType',
    'SeverityLevel',
    'get_memory_monitor',
    'start_memory_monitor',
    'stop_memory_monitor',
    
    # ETA & Device Lock
    'AgentETADeviceLock',
    'DeviceLockManager',
    'ETACalculator',
    'get_eta_device_lock_agent',
    'start_eta_device_lock_agent',
    'stop_eta_device_lock_agent',
    
    # Screen Analyzer
    'AgentScreenAnalyzer',
    'ScreenAnalyzerWrapper',
    'ScreenAnalysisType',
    'get_screen_analyzer_agent',
    'start_screen_analyzer_agent',
    'stop_screen_analyzer_agent',
    
    # Job Orchestrator
    'AgentJobOrchestrator',
    'JobQueueManager',
    'JobState',
    'ExecutionPhase',
    'get_job_orchestrator_agent',
    'start_job_orchestrator_agent',
    'stop_job_orchestrator_agent',
    
    # Recovery
    'AgentRecovery',
    'FailureAnalyzer',
    'RecoveryExecutor',
    'FailureType',
    'RecoveryStrategy',
    'get_recovery_agent',
    'start_recovery_agent',
    'stop_recovery_agent',
    
    # Distributed Sync
    'AgentDistributedSync',
    'SyncManager',
    'SyncValidator',
    'ConflictResolver',
    'AuditLogger',
    'LocalSyncCache',
    'SyncChange',
    'SyncEventType',
    'EntityType',
    'OperationType',
    'ConflictType',
    
    # Security - Code Encryption
    'PyArmorAgent',
    'EncryptionConfig',
    'EncryptionMode',
    'EncryptionError',
    
    # Security - Docker Signing
    'DockerImageSigningAgent',
    'GPGConfig',
    'GPGError',
    
    # Security - Secrets Management
    'VaultClient',
    'VaultClientConfig',
    'get_vault_client',
    'get_db_credentials',
    'get_github_token',
    'get_api_keys',
]

__version__ = '1.0.0'
__description__ = 'v2.0 AI Agent Framework for Device Testing Automation'
