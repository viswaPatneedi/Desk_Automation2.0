# Phase 4: Distributed Data Synchronization Architecture

## Overview
Phase 4 implements distributed data synchronization (Requirement 16) enabling multiple Docker instances in remote locations to bidirectionally sync data with the centralized PostgreSQL database and GitHub repository.

**Timeline**: 7-10 days  
**Target Completion**: June 16-19, 2026  
**Complexity**: High (conflict resolution, distributed consensus)

---

## Phase 4 Goals

### Primary Goals ✅
1. **Bidirectional Sync**: Docker instances ↔ PostgreSQL DB ↔ GitHub Repo
2. **Multi-Location Support**: UK primary + India (North/South) regions
3. **Conflict Resolution**: Timestamp-based + admin approval hybrid
4. **Data Validation**: Schema compliance before DB/repo commit
5. **Audit Trail**: Complete change history with source location metadata
6. **Fallback Mechanism**: Local queue with exponential backoff when DB unreachable
7. **Location Awareness**: All data changes tagged with origin location

### Secondary Goals 🎯
1. **Performance**: Sync latency <5 seconds for single location
2. **Reliability**: 99.9% uptime for sync infrastructure
3. **Security**: Encrypted data in transit, no credentials exposed
4. **Monitoring**: Real-time sync status dashboard
5. **Rollback**: Ability to revert failed syncs

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GLOBAL ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────┘

Remote Locations:
  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
  │  UK Primary      │   │  India North     │   │  India South     │
  │  Docker Instance │   │  Docker Instance │   │  Docker Instance │
  │  + App v2.0      │   │  + App v2.0      │   │  + App v2.0      │
  │                  │   │                  │   │                  │
  │ Local Queue:     │   │ Local Queue:     │   │ Local Queue:     │
  │ - Devices        │   │ - Devices        │   │ - Devices        │
  │ - Methods        │   │ - Methods        │   │ - Methods        │
  │ - Sequences      │   │ - Sequences      │   │ - Sequences      │
  │ - Logs/Commands  │   │ - Logs/Commands  │   │ - Logs/Commands  │
  └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  Agent-DistributedDataSync │
                    │  (Orchestrator Thread)     │
                    │  - Monitors all instances  │
                    │  - Validates data          │
                    │  - Resolves conflicts      │
                    │  - Audits changes          │
                    └─────────────┬──────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
        ┌─────▼──────────┐              ┌──────▼─────────────┐
        │   PostgreSQL   │              │ GitHub Repository  │
        │   Centralized  │              │  (via API)         │
        │   Database     │              │                    │
        │  - source_db   │              │ - Code committed   │
        │  - audit_logs  │              │ - Changes pushed   │
        │  - data_sync   │              │ - Tags created     │
        └────────────────┘              └────────────────────┘

Local Fallback (when DB unreachable):
  Docker Instance maintains local queue
  → Retry with exponential backoff (2^n seconds, max 5 min)
  → Auto-sync when DB comes online
```

---

## Data Flow Diagram

### 1. Change Creation (Local Instance)
```
User Action (UI Modal)
    ↓
Flask Controller validates input
    ↓
Create change in LOCAL CACHE (SQLite backup)
    ↓
Queue change for sync with metadata:
  - change_id (UUID)
  - entity_type (device/method/sequence/command/pattern)
  - operation (CREATE/UPDATE/DELETE)
  - payload (full data)
  - source_location (UK/India-North/India-South)
  - timestamp (UTC)
  - user_id, team_id
    ↓
Return to user (immediate feedback)
```

### 2. Sync to Central DB
```
Agent-DistributedDataSync polls local queue (every 5 seconds)
    ↓
For each queued change:
  1. Validate schema compliance
  2. Check for conflicts with central DB
  3. If no conflict: push to PostgreSQL
  4. If conflict: apply merge strategy
  5. Record in audit_logs with source metadata
    ↓
On success: remove from local queue, create GitHub commit
On failure: retry with exponential backoff
```

### 3. Sync to GitHub Repository
```
PostgreSQL receives validated change
    ↓
Agent-DistributedDataSync generates commit message:
  [SYNC] DEVICES: Added/Updated/Deleted
  Location: UK Primary
  Change ID: abc-123
  Timestamp: 2026-06-09T14:30:00Z
    ↓
Use PyGithub API to:
  1. Create branch: sync/change-id
  2. Modify files in sync branch
  3. Create pull request with metadata
  4. Auto-merge if non-conflicting
  5. Tag release version: v2.0.sync-timestamp
    ↓
Update central repository with all location changes
```

### 4. Pull Latest Data (on startup)
```
Flask app starts
    ↓
Agent-DistributedDataSync triggers full sync check:
  1. GET all devices, methods, sequences from central DB
  2. Compare with local cache
  3. Identify new/modified items
  4. Download and merge latest
    ↓
Display to user: "Synced 5 devices, 3 methods, 2 sequences from UK primary"
```

---

## Data Sync Entities

### Data Types to Sync
```
1. DEVICES
   - Device metadata (name, IP, type, location)
   - SSH credentials (encrypted in transit)
   - Status and health info
   - Associated methods

2. METHODS
   - Method definitions (name, description, parameters)
   - System commands and parameters
   - Success/failure criteria
   - ETA information

3. SAVED_SEQUENCES
   - Sequence definition (name, methods, iterations)
   - Method rationale and intent
   - Sharing settings (private/team/public)
   - Version history

4. SYSTEM_COMMANDS
   - Custom command definitions
   - Approval status and staging
   - Parameter templates

5. LOG_PATTERNS
   - Log parsing rules
   - Success/failure patterns
   - Location-specific patterns

6. USERS
   - User profiles and credentials
   - Team assignments
   - Role and permissions
```

---

## Conflict Resolution Strategy

### Conflict Types

#### Type 1: Timestamp-Based Conflicts (80% of cases)
```
Scenario: Same device modified in UK and India simultaneously

Resolution:
1. Last-write-wins: Compare modification timestamps
2. Keep the version with latest timestamp
3. Archive alternative version in audit_logs
4. Log decision: "RESOLVED_TIMESTAMP: Kept India version (2026-06-09T14:35:00Z)"

Example:
  UK modified device 10.0.0.61 at 14:30:00Z
  India modified device 10.0.0.61 at 14:32:00Z
  → Keep India version, archive UK version
```

#### Type 2: Breaking Changes (5% of cases)
```
Scenario: Method deleted in one location, used in sequence in another

Resolution:
1. Flag as CONFLICT_REQUIRES_APPROVAL
2. Send alert to admin with details
3. Admin reviews both versions
4. Admin chooses resolution:
   a) Keep method (safe)
   b) Delete method + cascade delete sequences (risky)
   c) Deprecate method (middle ground)
5. Apply chosen resolution
6. Notify all locations of decision

Example:
  India deleted method "voice_command"
  UK has sequence "daily_test" using "voice_command"
  → Require admin approval before deletion
```

#### Type 3: Schema Violations (3% of cases)
```
Scenario: Invalid data format in Docker push

Resolution:
1. Reject change with specific error: "required field 'port' missing"
2. Sync agent notifies location admin with fix instructions
3. Local instance retries after fix is applied
4. Log rejection with validation rules violated

Example:
  Device missing 'port' field
  → Reject: "Port must be integer between 1-65535"
  → Retry after correction
```

#### Type 4: Duplicate Data (2% of cases)
```
Scenario: Same device added in two locations with same IP

Resolution:
1. Detect duplicate by IP address + team + location
2. Merge metadata (combine values)
3. Keep single version with best metadata
4. Archive duplicate in audit_logs with merge details
5. Notify both locations of merge

Example:
  UK device: 10.0.0.61, SSH port 10022, active
  India device: 10.0.0.61, SSH port 22, inactive
  → Merge to single device with port 10022 (keep more specific)
```

---

## Agent-DistributedDataSync Implementation

### Core Components

#### 1. SyncManager Class (Main Orchestrator)
```python
class SyncManager:
    """Manages distributed data synchronization"""
    
    def __init__(self):
        self.sync_intervals = {
            'local_queue_poll': 5,      # Poll local changes every 5s
            'full_sync_check': 300,     # Full sync every 5 minutes
            'health_check': 60,         # Health check every 1 minute
        }
        self.conflict_handlers = {}
        self.location_id = os.getenv('LOCATION_ID', 'UK_PRIMARY')
        self.db_session = get_db_session()
        
    def start_sync_daemon(self):
        """Start background sync thread"""
        # Monitor local queue and sync changes
        
    def poll_local_queue(self):
        """Check for changes in local queue"""
        # Get all unsync'd changes from local SQLite
        # Validate and push to central DB
        
    def push_change_to_db(self, change):
        """Push a single change to PostgreSQL"""
        # Validate schema
        # Check for conflicts
        # Insert or update in PostgreSQL
        # Log in audit_logs
        
    def pull_latest_data(self):
        """Pull latest data from central DB"""
        # Compare local cache with central DB
        # Download new/modified items
        # Merge into local SQLite
        
    def push_to_github(self, change):
        """Push validated change to GitHub repo"""
        # Create commit via PyGithub API
        # Tag release version
```

#### 2. ConflictResolver Class
```python
class ConflictResolver:
    """Handles conflict resolution between locations"""
    
    def resolve_conflict(self, local, remote, entity_type):
        """
        Resolve conflict based on strategy
        
        Args:
            local: Local version of entity
            remote: Central DB version
            entity_type: Type of entity (device, method, etc.)
        
        Returns:
            (resolved_version, conflict_type, resolution_strategy)
        """
        
    def resolve_timestamp_based(self, local, remote):
        """Resolve using timestamp for last-write-wins"""
        
    def resolve_schema_violation(self, local, entity_type):
        """Validate and fix schema violations"""
        
    def resolve_breaking_change(self, local, remote):
        """Require admin approval for breaking changes"""
        
    def resolve_duplicate(self, local, remote):
        """Merge duplicate entries"""
```

#### 3. SyncValidator Class
```python
class SyncValidator:
    """Validates data before synchronization"""
    
    def validate_schema(self, entity_type, payload):
        """Check schema compliance"""
        
    def validate_constraints(self, entity_type, payload):
        """Check database constraints"""
        
    def validate_dependencies(self, entity_type, payload):
        """Check for breaking changes"""
        
    def validate_no_data_loss(self, operation, entity_id):
        """Ensure no data is lost during sync"""
```

#### 4. AuditLogger Class
```python
class AuditLogger:
    """Logs all sync activities for audit trail"""
    
    def log_sync_event(self, event_type, entity_type, details):
        """
        Log sync event with full context
        
        Args:
            event_type: PUSHED, PULLED, CONFLICT, RESOLVED, FAILED
            entity_type: device, method, sequence, etc.
            details: Full context including locations, timestamps, users
        """
        
    def log_conflict_resolution(self, conflict_details, resolution):
        """Log how a conflict was resolved"""
```

---

## Configuration & Deployment

### Environment Variables
```bash
# .env configuration for each Docker instance

# Location metadata
LOCATION_ID=UK_PRIMARY              # UK_PRIMARY, INDIA_NORTH, INDIA_SOUTH
LOCATION_NAME=United Kingdom        
LOCATION_REGION=EMEA
LOCATION_TIMEZONE=UTC

# Central database connection
CENTRAL_DB_HOST=db.example.com
CENTRAL_DB_PORT=5432
CENTRAL_DB_NAME=lrqa_v2_central
CENTRAL_DB_USER=sync_user           # Limited permissions
CENTRAL_DB_PASSWORD=***             # Vault-managed

# GitHub integration
GITHUB_API_TOKEN=***                # Vault-managed
GITHUB_REPO=viswaPatneedi/lrqa-middleware-testing-dashboard
GITHUB_BRANCH=main

# Sync configuration
SYNC_QUEUE_POLL_INTERVAL=5          # seconds
SYNC_RETRY_MAX_BACKOFF=300          # 5 minutes
SYNC_ENABLE_AUTO_SYNC=true
SYNC_CONFLICT_RESOLUTION=HYBRID     # TIMESTAMP_ONLY or HYBRID

# Security
SYNC_ENCRYPT_IN_TRANSIT=true
SYNC_VALIDATE_SCHEMA=true
SYNC_REQUIRE_APPROVAL=false         # For breaking changes only
```

---

## Implementation Phases (7-10 days)

### Phase 4a: Core Infrastructure (Days 1-2)
- [ ] Create `agents/distributed_sync_agent.py` (700+ LOC)
- [ ] Implement SyncManager, ConflictResolver, SyncValidator
- [ ] Add local SQLite cache for offline queue
- [ ] Create audit_logs table in PostgreSQL
- [ ] Setup monitoring and status endpoints

### Phase 4b: Sync Mechanisms (Days 3-4)
- [ ] Implement poll_local_queue() and push_change_to_db()
- [ ] Implement pull_latest_data() on app startup
- [ ] Add conflict detection and resolution
- [ ] Implement retry with exponential backoff
- [ ] Add location metadata tagging

### Phase 4c: GitHub Integration (Days 5-6)
- [ ] Setup PyGithub API integration
- [ ] Implement push_to_github() with auto-merge
- [ ] Create release versioning (v2.0.sync-timestamp)
- [ ] Add commit message generation with metadata
- [ ] Test multi-location simulations

### Phase 4d: Testing & Documentation (Days 7-10)
- [ ] Unit tests for conflict resolution (50+ tests)
- [ ] Integration tests with mock PostgreSQL
- [ ] Multi-location simulation tests
- [ ] Performance benchmarks (<5s latency)
- [ ] PHASE4_IMPLEMENTATION_GUIDE.md
- [ ] PHASE4_DEPLOYMENT_GUIDE.md
- [ ] Operational runbook

---

## Risk Mitigation

### Risk 1: Network Partition (Central DB Unreachable)
**Impact**: High  
**Mitigation**:
- Local SQLite queue maintains up to 100 pending changes
- Exponential backoff retry: 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 300s
- Health check every 60 seconds
- Automatic fallback to local-only mode
- Auto-recovery when network restored

### Risk 2: Conflict Explosion (Many Simultaneous Changes)
**Impact**: Medium  
**Mitigation**:
- Rate limiting: max 10 sync operations per second
- Queue prioritization (breaking changes first)
- Admin approval workflow for conflicts
- Rolling back failed syncs atomically

### Risk 3: Data Corruption During Sync
**Impact**: Critical  
**Mitigation**:
- Pre-sync validation (schema, constraints, dependencies)
- Transactional commits (all-or-nothing)
- Automatic rollback on any error
- Backup before major sync operations
- Immutable audit trail

### Risk 4: Security Breach (Credentials Leaked)
**Impact**: Critical  
**Mitigation**:
- Encrypt all credentials in transit (TLS 1.3)
- Never store credentials in Docker image
- Use HashiCorp Vault for secrets management
- Vault integration for runtime secret injection
- Audit all credential access

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sync Latency | <5s | P95 push-to-DB time across 3 locations |
| Data Integrity | 100% | Zero data loss/corruption in sync tests |
| Conflict Resolution | 98% auto-resolve | % conflicts resolved without admin |
| Uptime | 99.9% | Availability of sync infrastructure |
| Audit Coverage | 100% | All sync events logged with full context |
| Security | 100% | Zero credential leaks, all encrypted |

---

## Deliverables

1. ✅ `agents/distributed_sync_agent.py` (700+ LOC)
   - SyncManager, ConflictResolver, SyncValidator, AuditLogger
   - Full CLI interface for testing

2. ✅ `models/database.py` updates
   - audit_logs table
   - data_sync_log table
   - Extended device/method/sequence models with sync metadata

3. ✅ `config/sync_config.py`
   - Sync intervals, retry strategies, conflict handlers
   - Location registry and routing rules

4. ✅ `utilities/local_sync_cache.py`
   - SQLite cache for offline queue
   - Local backup storage mechanisms

5. ✅ Documentation (1,500+ LOC)
   - PHASE4_ARCHITECTURE.md (this file)
   - PHASE4_IMPLEMENTATION_GUIDE.md
   - PHASE4_DEPLOYMENT_GUIDE.md
   - PHASE4_OPERATIONAL_RUNBOOK.md

---

## Next: Phase 5 (Security & Encryption)

After Phase 4 completion:
- **PyArmor Integration**: Encrypt Python code in Docker
- **Docker Image Signing**: GPG signature verification
- **Secrets Management**: HashiCorp Vault integration
- **Compliance**: Security audit and hardening

