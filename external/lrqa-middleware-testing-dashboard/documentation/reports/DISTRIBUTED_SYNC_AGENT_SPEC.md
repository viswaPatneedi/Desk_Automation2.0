# AI Agent Specification: DistributedDataSync
## Sub-Agent for Multi-Location Docker Image Data Synchronization

### Agent Overview
**Name**: `Agent-DistributedDataSync`  
**Phase**: Phase 3 (Days 33-50 in acceleration plan)  
**Duration**: 8 days  
**Responsibility**: Manage bidirectional data sync between Docker instances in multiple locations and centralized database + GitHub repository  

---

## Core Mission

Enable Docker instances deployed in geographically distributed locations (UK, India North, India South, etc.) to:
1. **Pull** latest shared data (devices, methods, log patterns, sequences) from central DB
2. **Push** new/modified data back to central DB
3. **Sync** changes to GitHub repository
4. **Validate** all data before committing
5. **Handle conflicts** intelligently
6. **Audit trail** every change with full traceability
7. **Encrypt** all code and sensitive data
8. **Recover** gracefully when offline

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CENTRALIZED DATABASE                         │
│  (PostgreSQL - AWS RDS / Azure DB / Self-hosted)               │
│                                                                  │
│  Tables:                                                         │
│  - devices (team_id, location, region, device_ip, ...)        │
│  - methods (method_name, description, ...)                    │
│  - log_patterns (pattern_id, regex, team_id, ...)             │
│  - saved_sequences (seq_id, methods[], team_id, ...)          │
│  - system_commands (cmd_id, command, team_id, ...)            │
│  - data_sync_log (source_location, timestamp, data_id, ...)   │
│                                                                  │
│  Access: HTTPS + JWT + TLS 1.3                                │
└─────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │ Pull/Push (HTTPS)  │ Pull/Push (HTTPS) │ Pull/Push (HTTPS)
         │ Every 30s          │ Every 30s         │ Every 45s
         │                    │                   │
      ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
      │   Docker     │   │   Docker     │   │   Docker     │
      │  Instance    │   │  Instance    │   │  Instance    │
      │   Location   │   │   Location   │   │   Location   │
      │     UK       │   │ INDIA NORTH  │   │ INDIA SOUTH  │
      │              │   │              │   │              │
      │ Agent:       │   │ Agent:       │   │ Agent:       │
      │ DistSync     │   │ DistSync     │   │ DistSync     │
      │ (running)    │   │ (running)    │   │ (running)    │
      └──────────────┘   └──────────────┘   └──────────────┘
         TEAM-UK         TEAM-INDIA-N       TEAM-INDIA-S
         
         │ Live Data Cache (20 min TTL)
         │ Queue: Local changes waiting to push
         │ Credentials: From vault, never exposed
```

---

## DistributedDataSync Agent Architecture

### **Responsibilities**

```
┌─────────────────────────────────────────────────────────────────┐
│           Agent-DistributedDataSync (Stateful)                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1) PULL COORDINATOR                                     │   │
│  │    - Every 30s: Poll DB for new/updated data           │   │
│  │    - Filter by: team_id, location, timestamp > last   │   │
│  │    - Decompress and cache locally                      │   │
│  │    - Trigger UI refresh if changes detected           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2) PUSH COORDINATOR                                     │   │
│  │    - Monitor local changes (file watcher + DB hooks)   │   │
│  │    - Queue changes with timestamp and user info        │   │
│  │    - Validate schema + dependencies                    │   │
│  │    - Submit to DB with location + team metadata       │   │
│  │    - Track push status (pending/success/failed)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3) CONFLICT RESOLVER                                    │   │
│  │    - Detect conflicts (same data modified from 2+ loc)│   │
│  │    - Strategy 1: Timestamp (last-write-wins)          │   │
│  │    - Strategy 2: Admin approval (human decision)      │   │
│  │    - Strategy 3: Merge (combine both changes)         │   │
│  │    - Log conflict + resolution for audit             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4) REPO SYNC                                            │   │
│  │    - When DB change approved, push to GitHub          │   │
│  │    - Create branch: sync/location/data-type/timestamp │   │
│  │    - Commit message: auto-generated with context     │   │
│  │    - Create PR: request code owner approval          │   │
│  │    - Auto-merge if: tests pass + no conflicts        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 5) OFFLINE FALLBACK                                     │   │
│  │    - If DB unreachable: queue changes locally         │   │
│  │    - Retry with exponential backoff: 1s, 2s, 4s, 8s..│   │
│  │    - Local operations continue (app still works)      │   │
│  │    - Auto-sync when connection restored              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 6) AUDIT & COMPLIANCE                                  │   │
│  │    - Log every sync: source, target, data, timestamp  │   │
│  │    - Immutable sync log (append-only)                 │   │
│  │    - Compliance checks: no data loss, no duplicates   │   │
│  │    - Monthly audit report generation                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 7) DATA ENCRYPTION                                      │   │
│  │    - All transmissions: TLS 1.3 end-to-end            │   │
│  │    - Credentials: AWS Secrets Manager / HashiCorp Vault│   │
│  │    - Local cache: AES-256 encryption at rest          │   │
│  │    - PII masking: Passwords never stored              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases (8 Days)

### **Days 1-2: Architecture & Setup**
- Design data sync protocol
- Create API endpoints for pull/push
- Set up environment variables for regional endpoints
- Create docker-compose with sync agent sidecar

### **Days 3-4: Pull Coordinator**
- Implement periodic DB polling (30s interval)
- Create local cache layer (Redis or SQLite)
- Add data decompress and format conversion
- Implement UI refresh triggers

### **Days 5-6: Push Coordinator**
- Implement file watcher for local changes
- Create push queue + status tracking
- Add schema validation before push
- Implement retry logic with exponential backoff

### **Days 7-8: Conflict Resolution & Repo Sync**
- Implement conflict detection (3-way merge)
- Build admin approval workflow
- Create GitHub sync (branch → PR → merge)
- End-to-end testing across all scenarios

---

## API Endpoints (New in v2.0)

### **Pull Data from Central DB**
```
GET /api/v2/sync/pull
Headers:
  - Authorization: Bearer {JWT_TOKEN}
  - X-Location: UK
  - X-Team-ID: team-uk
  - X-Last-Sync: 2025-06-01T10:30:00Z

Response:
{
  "devices": [...],
  "methods": [...],
  "log_patterns": [...],
  "saved_sequences": [...],
  "timestamp": "2025-06-01T10:35:00Z",
  "status": "success"
}
```

### **Push Local Data to Central DB**
```
POST /api/v2/sync/push
Headers:
  - Authorization: Bearer {JWT_TOKEN}
  - X-Location: UK
  - X-Team-ID: team-uk
  - X-Source-Agent: Agent-DistributedDataSync

Body:
{
  "data_type": "devices",
  "operations": [
    {
      "operation": "create",
      "data": {...device object...},
      "intent": "Adding new test device in UK lab",
      "user_id": "user-123"
    }
  ],
  "timestamp": "2025-06-01T10:33:15Z"
}

Response:
{
  "status": "pending_approval",  # or "success" or "conflict"
  "pending_id": "push-12345",
  "requires_approval": true,
  "conflict_details": null
}
```

### **Resolve Conflicts**
```
POST /api/v2/sync/resolve-conflict
Headers:
  - Authorization: Bearer {JWT_TOKEN}
  - X-Admin-User: true

Body:
{
  "conflict_id": "conflict-98765",
  "resolution_strategy": "merge",  # or "timestamp", "manual"
  "approved_by": "admin-user-1",
  "notes": "Merged both device updates"
}
```

---

## Data Types & Sync Scope

### **Devices**
```json
{
  "device_ip": "10.0.0.250",
  "device_name": "Element-4K-UK-Lab1",
  "location": "UK",
  "team_id": "team-uk",
  "added_by": "user-123",
  "added_at": "2025-06-01T09:15:00Z",
  "ssh_port": 10022,
  "ir_config": {...},
  "last_modified": "2025-06-01T10:20:00Z",
  "sync_status": "synced"
}
```

### **Methods**
```json
{
  "method_name": "reboot",
  "description": "Standard device reboot",
  "team_id": "team-uk",
  "created_by": "user-456",
  "parameters": [...],
  "timeout_seconds": 300,
  "sync_status": "synced"
}
```

### **Log Patterns**
```json
{
  "pattern_id": "pattern-001",
  "pattern_regex": "QMS HOME_TILES complete",
  "pattern_description": "HOME screen detection",
  "team_id": "team-india-n",
  "location": "INDIA-NORTH",
  "priority": 1,
  "created_by": "user-789",
  "sync_status": "synced"
}
```

### **Saved Sequences**
```json
{
  "sequence_id": "seq-daily-check",
  "sequence_name": "Daily Sanity Check",
  "team_id": "team-uk",
  "methods": [
    {"method": "reboot", "iterations": 1},
    {"method": "screen_validation", "iterations": 1}
  ],
  "created_by": "user-123",
  "intent_note": "Verify standard boot and HOME screen",
  "sync_status": "synced"
}
```

---

## Conflict Resolution Examples

### **Scenario 1: Device Modified in Two Locations**
```
Location UK modified device "Element-4K-UK-Lab1" at 10:20 UTC
Location UK-STAGING modified same device at 10:21 UTC
Conflict detected!

Resolution Options:
1. Last-Write-Wins: UK-STAGING version accepted (newer)
2. Manual: Admin reviews both versions, selects one
3. Merge: Combine changes (if non-conflicting fields)

Result: UK-STAGING version stored, notification sent to UK
```

### **Scenario 2: New Device Added in Multiple Locations**
```
UK added device "TestDevice-1" at 10:15 UTC
India added device "TestDevice-1" at 10:16 UTC
Conflict: Same name, different configs

Resolution:
1. Rename one: "TestDevice-1-UK", "TestDevice-1-India"
2. Merge: Combine both into one comprehensive config
3. Admin: Choose which to keep

Result: Two devices created, sync log updated, both teams notified
```

---

## Skills This Agent Uses

1. **`skill-db-sync-pull`** - Fetch data from central DB
2. **`skill-db-sync-push`** - Submit changes to central DB
3. **`skill-conflict-detector`** - Identify conflicting changes
4. **`skill-conflict-resolver`** - Apply resolution strategy
5. **`skill-github-repo-sync`** - Create PRs to GitHub
6. **`skill-data-validator`** - Verify schema compliance
7. **`skill-offline-queue`** - Queue changes when DB unavailable
8. **`skill-encryption-manager`** - Encrypt/decrypt sensitive data
9. **`skill-audit-logger`** - Log all sync operations
10. **`skill-health-monitor`** - Check sync agent status

---

## Success Criteria (DOD - Definition of Done)

✅ **Functional**
- Pull data from DB every 30s without errors
- Push new data with validation + approval workflow
- Detect and resolve conflicts (3+ scenarios tested)
- Sync changes to GitHub with proper PR workflow
- Handle offline scenarios with queue + retry

✅ **Performance**
- Sync latency: < 2 seconds for 100 devices
- Pull operation: < 1 second
- Push operation: < 2 seconds
- Queue processing: 10+ items/sec

✅ **Reliability**
- 99.9% data sync success rate
- Zero data loss during multi-location sync
- Proper error recovery and notifications
- Audit trail 100% complete

✅ **Security**
- All transactions TLS 1.3 encrypted
- JWT token validation on every call
- Secrets never logged or exposed
- PII masking in audit logs

✅ **Testing**
- E2E tests: Single location push/pull ✅
- E2E tests: Multi-location concurrent sync ✅
- E2E tests: Conflict resolution (3 scenarios) ✅
- E2E tests: Offline + recovery ✅
- E2E tests: GitHub PR workflow ✅

---

## Docker Integration

### **In Dockerfile.prod**
```dockerfile
# Add DistributedDataSync agent
COPY services/distributed_sync_agent.py /app/services/
COPY services/db_sync_coordinator.py /app/services/
COPY services/conflict_resolver.py /app/services/

# Start agent as background service
CMD ["python", "-c", "
import threading
from services.distributed_sync_agent import DistributedDataSyncAgent

agent = DistributedDataSyncAgent()
agent_thread = threading.Thread(target=agent.start, daemon=True)
agent_thread.start()

# Then start Flask app
import app
app.run(...)
"]
```

### **Environment Variables per Location**
```bash
# For UK deployment
LOCATION=UK
TEAM_ID=team-uk
DB_SYNC_URL=https://master-db.company.com
DB_SYNC_INTERVAL=30  # seconds
SYNC_ENABLED=true

# For India North deployment
LOCATION=INDIA_NORTH
TEAM_ID=team-india-north
DB_SYNC_URL=https://master-db.company.com
DB_SYNC_INTERVAL=30  # seconds (regional tuning possible)
SYNC_ENABLED=true
```

---

## Monitoring & Alerts

### **Parent Agent Visibility**
Agent-DistributedDataSync reports to Parent Agent:
- `sync_status`: "healthy" | "warning" | "error"
- `last_successful_pull`: timestamp
- `last_successful_push`: timestamp
- `pending_pushes`: count
- `pending_conflicts`: count
- `queue_size`: items waiting
- `db_connection`: "connected" | "offline"

```python
parent_agent.report_status({
    'agent_id': 'Agent-DistributedDataSync',
    'status': 'healthy',
    'last_pull': '2025-06-01T10:35:00Z',
    'last_push': '2025-06-01T10:33:15Z',
    'pending_pushes': 2,
    'metrics': {
        'pull_latency_ms': 180,
        'push_latency_ms': 1200,
        'conflict_count': 0
    }
})
```

### **Alerts to Parent**
- ⚠️ DB connection lost (offline mode activated)
- ⚠️ Conflict detected (awaiting resolution)
- ⚠️ Sync queue backup (> 50 items)
- ⚠️ Failed push attempt (retrying)
- ✅ Major sync completed (all data synced)

---

## Testing Strategy

### **Unit Tests**
```python
# Test pull coordinator
def test_pull_new_devices():
    agent = DistributedDataSyncAgent()
    devices = agent.pull_devices()
    assert len(devices) > 0
    assert all(d['sync_status'] == 'synced' for d in devices)

# Test push queu
