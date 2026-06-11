# v2.0 Multi-Location Deployment Architecture

## Executive Overview

The Desk-Automation v2.0 platform is designed for **secure, distributed deployment** across multiple geographic locations with centralized data management. Each Docker instance in a location can independently function while synchronizing with a global database, ensuring no single point of failure and enabling collaborative multi-team operations.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         GLOBAL ARCHITECTURE v2.0                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────┐        │
│   │                    CENTRALIZED LAYER                           │        │
│   │  ┌─────────────────────────────────────────────────────────┐  │        │
│   │  │ Master Database (PostgreSQL + Replication)            │  │        │
│   │  │ - Devices (location-tagged)                           │  │        │
│   │  │ - Methods & Sequences                                │  │        │
│   │  │ - Log Patterns & System Commands                    │  │        │
│   │  │ - Execution History (30-day retention)              │  │        │
│   │  │ - Audit Logs (immutable)                            │  │        │
│   │  │ - Staging/Approval Workflows                        │  │        │
│   │  └─────────────────────────────────────────────────────────┘  │        │
│   │                                                                 │        │
│   │  ┌─────────────────────────────────────────────────────────┐  │        │
│   │  │ GitHub Repository (Private)                           │  │        │
│   │  │ - main: Production-ready code                        │  │        │
│   │  │ - staging: R&D branch                                │  │        │
│   │  │ - Public keys for image signing                      │  │        │
│   │  │ - Version tags (v2.0.1, v2.0.2, ...)               │  │        │
│   │  └─────────────────────────────────────────────────────────┘  │        │
│   │                                                                 │        │
│   │  ┌─────────────────────────────────────────────────────────┐  │        │
│   │  │ Secrets Vault (AWS Secrets Manager / HashiCorp Vault)  │  │        │
│   │  │ - Database credentials                                │  │        │
│   │  │ - API keys (Anthropic Claude, etc.)                  │  │        │
│   │  │ - JWT signing keys                                    │  │        │
│   │  │ - SSH keys (no passwords exposed)                     │  │        │
│   │  └─────────────────────────────────────────────────────────┘  │        │
│   │                                                                 │        │
│   │  ┌─────────────────────────────────────────────────────────┐  │        │
│   │  │ Docker Registry (Private / ECR, Harbor, etc.)         │  │        │
│   │  │ - desk-automation:v2.0.1 (signed + encrypted)        │  │        │
│   │  │ - desk-automation:v2.0.2 (signed + encrypted)        │  │        │
│   │  └─────────────────────────────────────────────────────────┘  │        │
│   │                                                                 │        │
│   └──────────────────────────────────────────────────────────────┘        │
│                                   ▲▲▲                                      │
│                   HTTPS (JWT + TLS 1.3 encryption)                         │
│      ┌────────────┬──────────────┬──────────────┬────────────┐            │
│      ▼            ▼              ▼              ▼            ▼            │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│   │ UK       │ │ INDIA    │ │ INDIA    │ │ Future   │ │ Future   │       │
│   │ PRIMARY  │ │ NORTH    │ │ SOUTH    │ │ Location │ │ Location │       │
│   │ Location │ │ Location │ │ Location │ │ (TBD)    │ │ (TBD)    │       │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture - Per Location

### **Location: UK**

```
┌────────────────────────────────────────────────────────────────┐
│                    UK LOCATION DEPLOYMENT                       │
│                    (Primary / Test Location)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Docker Host: uk-automation-prod-1                            │
│  IP: 192.168.1.50  |  Region: eu-west-1                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Docker Container: desk-automation-v2.0.1               │   │
│  │ Image: private-registry/desk-automation:v2.0.1         │   │
│  │ Status: Running                                         │   │
│  │                                                         │   │
│  │ ┌──────────────────────────────────────────────────┐   │   │
│  │ │ Flask App (Port 11078)                           │   │   │
│  │ │ - Web UI (MVC)                                  │   │   │
│  │ │ - REST API                                      │   │   │
│  │ │ - User authentication                           │   │   │
│  │ │ - Job execution                                │   │   │
│  │ │ - WebSocket for real-time logs                 │   │   │
│  │ └──────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │ ┌──────────────────────────────────────────────────┐   │   │
│  │ │ Agent-DistributedDataSync (Daemon)              │   │   │
│  │ │ - Pull devices/methods from DB (every 30s)     │   │   │
│  │ │ - Push local changes back to DB                │   │   │
│  │ │ - Sync to GitHub when DB confirms             │   │   │
│  │ │ - Handle conflicts (3-way merge)              │   │   │
│  │ │ - Offline queue + recovery                     │   │   │
│  │ └──────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │ ┌──────────────────────────────────────────────────┐   │   │
│  │ │ Parent Agent Listener                            │   │   │
│  │ │ - Exposes /api/agent-status endpoint            │   │   │
│  │ │ - Reports to central Parent Agent               │   │   │
│  │ │ - Receives task assignments                     │   │   │
│  │ └──────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │ ┌──────────────────────────────────────────────────┐   │   │
│  │ │ Local SQLite Cache (20-min TTL)                 │   │   │
│  │ │ - Devices  (100+)                              │   │   │
│  │ │ - Methods  (29+)                               │   │   │
│  │ │ - Patterns (50+)                               │   │   │
│  │ │ - Sequences (20+)                              │   │   │
│  │ │ - Works offline until DB reconnects            │   │   │
│  │ └──────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │ ┌──────────────────────────────────────────────────┐   │   │
│  │ │ Mounted Volumes                                 │   │   │
│  │ │ - /app/iteration_logs (execution logs)         │   │   │
│  │ │ - /app/screenshots (device screenshots)        │   │   │
│  │ │ - /app/reference_screenshots (AI training)    │   │   │
│  │ │ - Mapped to local disk: 100GB+ SSD            │   │   │
│  │ └──────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │ Environment Variables:                                  │   │
│  │ - LOCATION=UK                                          │   │
│  │ - TEAM_ID=team-uk                                      │   │
│  │ - DB_URL=https://master-db.company.com               │   │
│  │ - JWT_TOKEN=<vault-injected>                          │   │
│  │ - ANTHROPIC_KEY=<vault-injected>                      │   │
│  │ - SYNC_INTERVAL=30                                    │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  External Connections:                                          │
│  ─────────────────────                                          │
│  1. HTTPS to Master DB: master-db.company.com:5432           │
│  2. Vault: vault.company.com:8200 (for secrets)             │
│  3. GitHub: github.com (for repo sync)                       │
│  4. Docker Registry: registry.company.com (for updates)      │
│  5. SSH to RDK Devices: 192.168.1.100-200 (port 10022)      │
│                                                                 │
│  Monitoring & Logs:                                            │
│  ──────────────────                                            │
│  - Container logs: docker logs desk-automation             │
│  - Agent status: /api/agent-status                         │
│  - Metrics: Prometheus endpoint :9090/metrics              │
│  - Sync logs: /app/logs/sync_agent.log                    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### **Location: India North**

```
┌────────────────────────────────────────────────────────────────┐
│              INDIA NORTH LOCATION DEPLOYMENT                    │
│           (Staging/Production Multi-Region)                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Docker Host: india-automation-staging-1                      │
│  IP: 10.0.50.100  |  Region: ap-south-1                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Docker Container: desk-automation-v2.0.1               │   │
│  │ Image: private-registry/desk-automation:v2.0.1         │   │
│  │ Status: Running                                         │   │
│  │                                                         │   │
│  │ Same structure as UK, with adjustments:                │   │
│  │ - Sync interval: 40s (due to higher latency)          │   │
│  │ - Retry timeout: 60s (vs 30s in UK)                   │   │
│  │ - Agent health check interval: 45s                    │   │
│  │ - Timeout for DB operations: 15s (vs 10s in UK)      │   │
│  │                                                         │   │
│  │ Environment Variables:                                  │   │
│  │ - LOCATION=INDIA_NORTH                                 │   │
│  │ - TEAM_ID=team-india-north                             │   │
│  │ - DB_LATENCY_ADJUSTED=true                             │   │
│  │ - SYNC_INTERVAL=40                                     │   │
│  │ - OPERATION_TIMEOUT=15                                 │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### **Location: India South**

```
Same structure as India North with:
- LOCATION=INDIA_SOUTH
- TEAM_ID=team-india-south
- Additional VPN tunnel for security (different ISP)
```

---

## Data Flow: Device Addition from Remote Location

### **Scenario: User at India North wants to add a new device**

```
Step 1: User adds device via Web UI (port 11078)
        ↓
        ┌─────────────────────────────────────────────────┐
        │ Flask Route: POST /api/v2/devices               │
        │ Controller: DeviceController.create_device()    │
        └─────────────────────────────────────────────────┘
        ↓
Step 2: Device data validated + saved to TEMP DB
        ┌─────────────────────────────────────────────────┐
        │ Model: Device (in-memory + local SQLite)        │
        │ Status: PENDING_APPROVAL                        │
        │ Metadata:                                       │
        │ - source_location: INDIA_NORTH                  │
        │ - source_team: team-india-north                │
        │ - timestamp: 2025-06-01T10:15:00Z              │
        │ - created_by: user-789                          │
        └─────────────────────────────────────────────────┘
        ↓
Step 3: Agent-DistributedDataSync detects change (file watcher)
        ┌─────────────────────────────────────────────────┐
        │ Agent validates device schema                   │
        │ Agent checks: Device IP not duplicate            │
        │ Agent verifies: SSH connectivity possible       │
        │ Agent queues: Push to master DB                │
        └─────────────────────────────────────────────────┘
        ↓
Step 4: Push to master DB via HTTPS
        ┌─────────────────────────────────────────────────┐
        │ API Call: POST /api/v2/sync/push               │
        │ Payload:                                        │
        │ {                                              │
        │   "data_type": "devices",                       │
        │   "operation": "create",                        │
        │   "data": {device object},                      │
        │   "source_location": "INDIA_NORTH",             │
        │   "source_team": "team-india-north",            │
        │   "timestamp": "2025-06-01T10:15:00Z",          │
        │   "user_id": "user-789"                         │
        │ }                                               │
        │                                                 │
        │ Response:                                       │
        │ {                                              │
        │   "status": "pending_approval",                │
        │   "pending_id": "push-98765"                    │
        │ }                                               │
        └─────────────────────────────────────────────────┘
        ↓
Step 5: Master DB stores in TEMP table (not yet committed)
        ┌─────────────────────────────────────────────────┐
        │ Table: pending_changes                          │
        │ - pending_id: push-98765                        │
        │ - change_type: device_create                    │
        │ - source_location: INDIA_NORTH                  │
        │ - data: {device object}                         │
        │ - status: awaiting_approval                     │
        │ - submitted_at: 2025-06-01T10:15:00Z           │
        │ - submitted_by: user-789                        │
        │ - approved_at: NULL                             │
        │ - approved_by: NULL                             │
        └─────────────────────────────────────────────────┘
        ↓
Step 6: Admin Dashboard notifies admins worldwide
        ┌─────────────────────────────────────────────────┐
        │ All locations receive: New device pending       │
        │ Approval UI shows:                              │
        │ - Device details                                │
        │ - Source location: India North                  │
        │ - User: user-789                                │
        │ - [APPROVE] [REJECT] [EDIT] buttons             │
        └─────────────────────────────────────────────────┘
        ↓
Step 7: Admin approves (example: Admin from UK)
        ┌─────────────────────────────────────────────────┐
        │ Flask Route: POST /api/v2/sync/approve         │
        │ Payload:                                        │
        │ {                                              │
        │   "pending_id": "push-98765",                   │
        │   "decision": "approve",                        │
        │   "approved_by": "admin-uk-1"                   │
        │ }                                               │
        └─────────────────────────────────────────────────┘
        ↓
Step 8: Master DB commits to PERMANENT table
        ┌─────────────────────────────────────────────────┐
        │ Table: devices                                  │
        │ INSERT device record                            │
        │ + Metadata fields:                              │
        │   - source_location: INDIA_NORTH                │
        │   - source_team: team-india-north               │
        │   - added_by: user-789                          │
        │   - approved_by: admin-uk-1                     │
        │   - approved_at: 2025-06-01T10:30:00Z          │
        │   - version: 1                                  │
        │   - last_modified: 2025-06-01T10:30:00Z        │
        │                                                 │
        │ Table: audit_log                                │
        │ INSERT audit record                             │
        └─────────────────────────────────────────────────┘
        ↓
Step 9: Master DB notifies Agent-DistributedDataSync
        ┌─────────────────────────────────────────────────┐
        │ Message: Device approved + committed            │
        │ Action: Queue for GitHub sync                   │
        └─────────────────────────────────────────────────┘
        ↓
Step 10: Agent-DistributedDataSync syncs to GitHub
        ┌─────────────────────────────────────────────────┐
        │ Branch: sync/india-north/device/20250601       │
        │ File: devices.json updated                      │
        │ Commit: "Add device from India North            │
        │          Approved by: admin-uk-1                │
        │          Mobile: 10.0.50.250"                   │
        │ PR created: Request staging review              │
        │ Auto-merge rules:                               │
        │ ✓ Tests pass                                    │
        │ ✓ No conflicts                                  │
        │ ✓ DBM approval confirmed                        │
        └─────────────────────────────────────────────────┘
        ↓
Step 11: All locations receive update
        ┌─────────────────────────────────────────────────┐
        │ Agent-DistributedDataSync poll detects new data │
        │ Next sync cycle (30s): Pull new device          │
        │ Local cache updated: New device available       │
        │ All users see new device in UI                  │
        │ Notification: "New device available via sync"   │
        └─────────────────────────────────────────────────┘
        ↓
Success! Device synced globally across all locations in ~1 minute
```

---

## Data Consistency & Conflict Handling

### **Three-Way Merge Resolution**

When two locations modify the same device simultaneously:

```
Time:  10:15 UTC (UK)              10:16 UTC (India North)
       Device: "TV-50-inch"        Device: "TV-50-inch"
       Version: 1                  Version: 1
       
       UK modifies: SSH port → 10023    India modifies: Location → TV-Lab-2
       
       Conflict Detection:
       ├─ Same object_id
       ├─ Different versions (both v1 + local mods)
       ├─ Non-overlapping fields (SSH vs Location)
       
       Resolution: MERGE (automatic)
       ├─ SSH port: 10023 (from UK)
       ├─ Location: TV-Lab-2 (from India North)
       ├─ Version: 2 (incremented)
       ├─ Merged timestamp: 2025-06-01T10:16:05Z
       ├─ Audit: "Merged changes from UK + India North"
       
       Result: Both changes accepted ✅
```

### **Conflicting Field Resolution**

When two locations modify the same field:

```
Time:  10:15 UTC (UK)              10:16 UTC (India North)
       Device: "TV-50-inch"        Device: "TV-50-inch"
       
       UK modifies: Name → "TV-50-NEW"
       India modifies: Name → "NEW-TV-50"
       
       Conflict: Overlapping field
       
       Resolution Strategies:
       1. Last-Write-Wins (auto)
          → India North: 10:16 > UK: 10:15
          → Result: Name = "NEW-TV-50"
          → Log: "Conflict resolved using timestamp"
       
       2. Manual Approval (if enabled)
          → Admin selects: UK or India version
          → Log: "Conflict resolved by admin-uk-1"
       
       3. Rename (if IDs conflict)
          → TV-50-inch-UK
          → TV-50-inch-INDIA
```

---

## Deployment Workflow - From main Branch to Production

```
Step 1: Code stabilized on staging branch
        All 18 requirements implemented
        Unit tests + E2E tests passing
        ↓
Step 2: Create PR: staging → main
        Title: "v2.0 Release - All requirements complete"
        Reviewers: 2 senior engineers
        ↓
Step 3: Code review on main branch
        Check: No breaking changes
        Check: Database migrations work
        Check: Zero data loss scenarios
        Check: Agent frameworks tested
        ↓
Step 4: Merge to main (once approved)
        git merge staging → main
        git tag -a v2.0.1
        ↓
Step 5: GitHub Actions triggered automatically
        ├─ Build Dockerfile.prod
        ├─ Run tests
        ├─ Encrypt code (PyArmor)
        ├─ Sign image (GPG)
        ├─ Push to registry: desk-automation:v2.0.1
        ├─ Create GitHub release notes
        └─ Notify deployment team
        ↓
Step 6: Staging deployment (UK Test Lab)
        ├─ Pull image: desk-automation:v2.0.1
        ├─ Verify signature
        ├─ Deploy to test location
        ├─ Run 24-hour smoke tests
        ├─ Monitor agents + data sync
        └─ Require sign-off before production
        ↓
Step 7: Production deployment (Rolling)
        Sequence:
        1. UK Primary (2-hour window)
           - Blue-green deployment
           - Monitor metrics + errors
           - Rollback if issues
        
        2. India North (next day)
           - Same blue-green approach
           - Monitor sync from India
        
        3. India South (next day)
           - Complete rollout
        ↓
Success! v2.0.1 live in all locations
```

---

## Disaster Recovery & Rollback

### **Quick Rollback to Previous Version**

```bash
# If v2.0.1 has critical issues
docker pull private-registry/desk-automation:v2.0.0
docker stop desk-automation
docker rm desk-automation
docker run -d desk-automation:v2.0.0  # Start previous version

# Data is safe: No changes to permanent DB made (pending approval system)
# Agent-DistributedDataSync pauses sync during rollback
# All pending changes queued, reprocessed after upgrade
```

---

## Security Model

```
┌─────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Layer 1: Transport Security                            │
│ ├─ HTTPS TLS 1.3 for all API calls                    │
│ ├─ Certificate pinning via Docker                      │
│ └─ Zero exposed HTTP endpoints                         │
│                                                         │
│ Layer 2: Authentication                                │
│ ├─ JWT tokens (location + team scoped)                │
│ ├─ Token expiry: 1 hour                               │
│ ├─ Token refresh: Silent via Flask-Session             │
│ └─ Multi-factor: Via Vault integration                │
│                                                         │
│ Layer 3: Authorization                                 │
│ ├─ RBAC: Admin, Manager, User roles                   │
│ ├─ Team-level isolation: Data only visible to team   │
│ ├─ Location-level override: Super-admins only         │
│ └─ Audit: All actions logged with who/what/when       │
│                                                         │
│ Layer 4: Data Encryption                              │
│ ├─ At-Rest: AES-256 encryption in DB                  │
│ ├─ In-Transit: TLS 1.3                                │
│ ├─ Secrets: Vault managed + injected at runtime      │
│ └─ Passwords: Never stored (hashed SHA-256)           │
│                                                         │
│ Layer 5: Code Security                                │
│ ├─ Encrypted Docker images (PyArmor)                  │
│ ├─ GPG signed images (verification required)          │
│ ├─ Private GitHub repository                          │
│ ├─ Code obfuscation in production                     │
│ └─ No credentials in Docker images                    │
│                                                         │
│ Layer 6: Network Security                             │
│ ├─ VPN tunnels for inter-location communication      │
│ ├─ Firewalls: Only needed ports exposed              │
│ ├─ IP whitelisting: Master DB accepts only known IPs │
│ └─ Rate limiting: 100 req/sec per Docker instance    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Success Metrics (Post-Deployment)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Availability** | 99.9% | Uptime monitoring via health check |
| **Sync Latency** | < 2 min | Device data available in all locations within 2 min of approval |
| **Data Accuracy** | 100% | Zero data loss across sync cycles |
| **Conflict Resolution** | 99% auto | 99% of conflicts auto-resolved, < 1% require admin |
| **Deployment Time** | < 5 min | Pull image → ready to run in < 5 minutes |
| **Team Productivity** | +30% | Parallel device testing across locations |

---

## Quick Reference: Deployment Checklist

- [ ] Master DB running and accessible
- [ ] Secrets stored in Vault
- [ ] GitHub repo initialized (main + staging)
- [ ] Docker registry set up (private)
- [ ] SSL certificates installed
- [ ] Network verified (HTTPS connectivity from all locations)
- [ ] Admin accounts created in each location
- [ ] Agents initialized and syncing
- [ ] Backup procedures tested
- [ ] Rollback procedures tested
- [ ] Monitoring dashboards configured
- [ ] On-call rotations established

