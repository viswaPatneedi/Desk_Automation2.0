# Phase 5: Security & Encryption - Comprehensive Guide

## Overview

Phase 5 implements comprehensive security measures for the v2.0 application:
- **Code Encryption**: PyArmor-based obfuscation and encryption
- **Docker Image Security**: GPG signing and verification
- **Secrets Management**: HashiCorp Vault integration
- **Compliance & Audit**: Security hardening and audit trails

**Timeline**: 3-5 days  
**Completion Date**: June 14-16, 2026  
**Priority**: 🔴 CRITICAL (before production deployment)

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               SECURITY LAYERS                               │
└─────────────────────────────────────────────────────────────┘

┌─ Layer 1: Code Protection ─────────────────────────────────┐
│                                                             │
│  Source Code (v2.0/*.py)                                  │
│         ↓                                                   │
│  [PyArmor Encryption]                                     │
│  ├─ Obfuscation (remove symbols)                          │
│  ├─ Code Encryption (string encryption)                   │
│  ├─ Checksum verification                                 │
│  └─ Tamper detection                                       │
│         ↓                                                   │
│  Protected Code (.pyarmor/protected/*.pyc)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─ Layer 2: Container Security ─────────────────────────────┐
│                                                             │
│  Docker Build (Dockerfile)                                │
│  ├─ Use minimal base image (python:3.12-slim)             │
│  ├─ No credentials in image                               │
│  ├─ Production-only dependencies                          │
│  └─ Non-root user execution                               │
│         ↓                                                   │
│  Docker Image (lrqa-app:v2.0)                             │
│         ↓                                                   │
│  [GPG Signing]                                            │
│  └─ Image signature: image.sig (GPG sign)                │
│         ↓                                                   │
│  Signed Image (pushed to registry)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─ Layer 3: Secrets Management ─────────────────────────────┐
│                                                             │
│  Runtime Environment                                      │
│  ├─ NO credentials in .env files                          │
│  ├─ NO API keys in environment                            │
│  ├─ NO passwords in code                                  │
│         ↓                                                   │
│  [HashiCorp Vault]                                        │
│  ├─ Centralized secret storage                           │
│  ├─ Authentication via AppRole/JWT                       │
│  ├─ Automatic rotation                                    │
│  └─ Audit trail for all access                           │
│         ↓                                                   │
│  Runtime Secret Injection                                │
│         ↓                                                   │
│  Protected Application                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─ Layer 4: Network Security ────────────────────────────────┐
│                                                             │
│  ├─ TLS 1.3 for all connections (in-transit)             │
│  ├─ mTLS between services                                 │
│  ├─ VPN for multi-location connections                   │
│  ├─ Firewall rules (allow only needed ports)             │
│  └─ OAuth 2.0 for API authentication                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─ Layer 5: Audit & Monitoring ──────────────────────────────┐
│                                                             │
│  ├─ CloudWatch/ELK for logging                            │
│  ├─ Structured JSON logging                               │
│  ├─ Security event tracking                               │
│  ├─ Compliance audit trails                               │
│  └─ Anomaly detection                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Code Encryption with PyArmor

### Installation

```bash
# Install PyArmor
pip install pyarmor

# Verify installation
pyarmor --version
```

### PyArmor Configuration

Create `.pyarmor.cfg`:

```ini
[pyarmor]
# Protect mode: advanced (requires license) or basic
mode = basic

# Generate license file
license_type = non-commercial

# Obfuscation options
enable_rjit = 0
enable_jit = 0
obf_code = 1
obf_import = 1
obf_func_name = 1
obf_module_name = 1
obf_license = 1

# Anti-debugging
anti_debug = 1

# Extra options
enable_console = 0
```

### Encryption Workflow

```bash
# 0. Prepare clean source (no credentials!)
# Ensure all credentials come from Vault at runtime

# 1. Create pyarmor project
pyarmor create --type webapi --output .pyarmor agents/

# 2. Add source files
cd .pyarmor
pyarmor add agents/orchestrator_agent.py
pyarmor add agents/distributed_sync_agent.py
pyarmor add agents/github_sync_agent.py
# ... add all critical modules

# 3. Encrypt
pyarmor download

# 4. Verify encryption
ls -la dist/  # Should see .pyc files, not .py

# 5. Test in isolated environment
# Run tests to ensure functionality after encryption
pytest tests/ -v

# 6. Generate license (if using commercial mode)
# pyarmor licenses -x after:2026-12-31 default

# 7. Archive encrypted code
tar -czf agents.encrypted.tar.gz dist/
```

### Docker Integration

Update `Dockerfile`:

```dockerfile
# Stage 1: Encryption
FROM python:3.12-slim as builder

WORKDIR /build

# Copy source
COPY agents/ /build/agents/
COPY requirements.txt /build/

# Install PyArmor
RUN pip install pyarmor --no-cache-dir

# Encrypt code
COPY .pyarmor.cfg /build/
RUN pyarmor create --type webapi --output /encrypted . && \
    cd /encrypted && \
    pyarmor add agents/ && \
    pyarmor download && \
    rm -rf __pycache__

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Copy encrypted code from builder
COPY --from=builder /encrypted/dist /app/agents

# Copy application (non-agent code)
COPY app.py .
COPY config/ config/
COPY controllers/ controllers/
COPY models/ models/
COPY services/ services/
COPY static/ static/
COPY templates/ templates/

# Install dependencies (no dev tools)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Run application
CMD ["python", "app.py"]
```

### Verification

```bash
# Verify encryption worked
# 1. Source should NOT be readable
strings dist/agents/orchestrator_agent.py* | grep -q "def " && echo "FAILED: Code still readable!" || echo "✅ Code encrypted"

# 2. Runtime should work
docker build -t lrqa-app:v2.0-encrypted .

# 3. Test functionality
docker run --rm lrqa-app:v2.0-encrypted python -c "from agents import OrchestratorAgent; print('✅ Import successful')"
```

---

## 2. Docker Image Signing with GPG

### GPG Setup

```bash
# Generate GPG key (if not exists)
gpg --batch --generate-key <<EOF
Key-Type: RSA
Key-Length: 4096
Name-Real: Desk Automation Signing
Name-Email: signing@example.com
Expire-Date: 0
%no-protection
EOF

# Export public key
gpg --export --armor > public-key.asc

# Export secret key (KEEP SECURE!)
gpg --export-secret-keys --armor > secret-key.asc
```

### Image Signing Workflow

```bash
# 1. Build image
docker build -t lrqa-app:v2.0 .

# 2. Save image to tar
docker save lrqa-app:v2.0 > image.tar

# 3. Sign image tar
gpg --detach-sign --armor image.tar
# Output: image.tar.asc

# 4. Verify signature
gpg --verify image.tar.asc image.tar

# 5. Push to registry (with signature)
# Upload both image.tar and image.tar.asc to registry
docker push lrqa-app:v2.0
# Also store: image.tar.asc in registry metadata

# 6. On deployment: Verify before loading
docker load < image.tar
# Verify: gpg --verify image.tar.asc image.tar (must succeed)
```

### CI/CD Integration (GitHub Actions)

```yaml
name: Build, Sign, and Push

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build-sign-push:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker
        uses: docker/setup-buildx-action@v2
      
      - name: Build image
        run: |
          docker build -t lrqa-app:${{ github.sha }} .
          docker tag lrqa-app:${{ github.sha }} lrqa-app:latest
      
      - name: Save image
        run: docker save lrqa-app:latest > image.tar
      
      - name: Import GPG key
        run: |
          echo "${{ secrets.GPG_PRIVATE_KEY }}" | gpg --import
      
      - name: Sign image
        run: gpg --detach-sign --armor image.tar
      
      - name: Verify signature
        run: gpg --verify image.tar.asc image.tar
      
      - name: Push to registry
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login -u "${{ secrets.REGISTRY_USER }}" --password-stdin
          docker push lrqa-app:latest
          # Also push signature
          aws s3 cp image.tar.asc s3://registry-metadata/${{ github.sha }}/
```

---

## 3. Secrets Management with HashiCorp Vault

### Vault Setup

```bash
# Install Vault CLI
brew install vault  # macOS
# or
wget https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip

# Start Vault (development mode)
vault server -dev

# Initialize (production)
vault operator init
vault operator unseal

# Auth
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='your-root-token'
vault status
```

### Secret Configuration

Create `config/vault_config.py`:

```python
import os
import hvac
from typing import Dict

class VaultClient:
    """Manages secrets from HashiCorp Vault"""
    
    def __init__(self):
        self.client = hvac.Client(
            url=os.getenv('VAULT_ADDR', 'http://vault:8200'),
            token=os.getenv('VAULT_TOKEN')
        )
    
    def get_secret(self, path: str, key: str = None) -> str:
        """Retrieve secret from Vault"""
        response = self.client.secrets.kv.v2.read_secret_version(path)
        secret = response['data']['data']
        
        if key:
            return secret.get(key)
        return secret
    
    def get_db_credentials(self) -> Dict:
        """Get database credentials"""
        return self.client.secrets.kv.v2.read_secret_version('lrqa/db/central')['data']['data']
    
    def get_github_token(self) -> str:
        """Get GitHub API token"""
        return self.get_secret('lrqa/github', 'api_token')
    
    def get_api_keys(self) -> Dict:
        """Get all API keys"""
        return self.client.secrets.kv.v2.read_secret_version('lrqa/api/keys')['data']['data']

# Initialize global vault client
vault = VaultClient()
```

### Store Secrets in Vault

```bash
# Database credentials
vault kv put lrqa/db/central \
  host="db.example.com" \
  port="5432" \
  database="lrqa_v2_central" \
  user="sync_user" \
  password="secure-password-here"

# GitHub credentials
vault kv put lrqa/github \
  api_token="ghp_xxxxxxxxxxxxxxxxxxxx" \
  repo="viswaPatneedi/lrqa-middleware-testing-dashboard" \
  branch="main"

# API Keys
vault kv put lrqa/api/keys \
  anthropic_api_key="sk-ant-xxxxxxxxxxxx" \
  claude_model="claude-3-opus-20240229"

# Email service
vault kv put lrqa/email \
  smtp_host="smtp.example.com" \
  smtp_port="587" \
  smtp_user="alerts@example.com" \
  smtp_password="email-password"
```

### Application Integration

Update `app.py`:

```python
from config.vault_config import vault

# Initialize with Vault secrets
app.config['DATABASE_URL'] = f"postgresql://{get_db_creds()}"

def get_db_creds():
    """Get database credentials from Vault"""
    creds = vault.get_db_credentials()
    return f"{creds['user']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"

# During runtime, refresh secrets periodically
@app.before_request
def refresh_secrets():
    """Refresh secrets every hour"""
    if 'last_secret_refresh' not in g:
        g.last_secret_refresh = time.time()
    
    if time.time() - g.last_secret_refresh > 3600:
        creds = vault.get_db_credentials()
        # Update connection pool with new credentials
        g.last_secret_refresh = time.time()
```

### Docker Deployment with Vault

```docker
# Dockerfile with Vault integration

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt hvac

# Copy application
COPY . .

# Vault authentication via AppRole
ENV VAULT_ADDR=http://vault:8200
ENV VAULT_ROLE_ID=${VAULT_ROLE_ID}
ENV VAULT_SECRET_ID=${VAULT_SECRET_ID}

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD python -c "import hvac; hvac.Client(url='http://vault:8200').auth.approle.login('test')" || exit 1

# Run with secret injection
ENTRYPOINT ["python"]
CMD ["app.py"]
```

---

## 4. Development & Production Separation

### Development Configuration

```bash
# .env.development (DO NOT commit credentials!)
DEBUG=True
FLASK_ENV=development

# Use mock/test services
VAULT_ENABLED=False
DATABASE_URL=sqlite:///dev.db
API_KEYS_FILE=config/test_keys.json

# Limited logging
LOG_LEVEL=DEBUG
```

### Production Configuration

```bash
# .env.production (only in CI/CD, pulled from secrets manager)
DEBUG=False
FLASK_ENV=production

# Use real services
VAULT_ENABLED=True
VAULT_ADDR=https://vault.example.com:8200
VAULT_ROLE_ID=${VAULT_ROLE_ID}  # From secrets
VAULT_SECRET_ID=${VAULT_SECRET_ID}  # From secrets

# Production logging
LOG_LEVEL=WARNING
STRUCTURED_LOGGING=True
```

---

## 5. Security Hardening Checklist

### Code Security
- [ ] No hardcoded credentials in source
- [ ] All API keys from Vault
- [ ] SQL parameterized queries (prevent SQLi)
- [ ] Input validation (prevent XSS)
- [ ] No debug mode in production
- [ ] PyArmor encryption enabled
- [ ] Code obfuscation enabled
- [ ] Tamper detection active

### Container Security
- [ ] Non-root user execution
- [ ] Minimal base image
- [ ] Security scanning (Snyk, Trivy)
- [ ] Image signed with GPG
- [ ] No secrets in Dockerfile
- [ ] Health checks configured
- [ ] Resource limits set (CPU, memory)

### Database Security
- [ ] Encryption at rest (pgcrypto, TDE)
- [ ] SSL connections (sslmode=require)
- [ ] Role-based access control
- [ ] Audit logging enabled
- [ ] Regular backups encrypted
- [ ] Credentials rotated monthly

### API Security
- [ ] HTTPS only (TLS 1.3)
- [ ] OAuth 2.0 / JWT authentication
- [ ] Rate limiting by IP/user
- [ ] CORS configured properly
- [ ] API key rotation monthly
- [ ] Request signing (optional)

### Monitoring & Audit
- [ ] Structured JSON logging
- [ ] Centralized log aggregation
- [ ] Security event alerts
- [ ] Monthly security audit
- [ ] Penetration testing (quarterly)
- [ ] Compliance scanning (GDPR, SOC2)

---

## 6. Testing Security

### Unit Tests for Security

```python
def test_no_credentials_in_config():
    """Verify no credentials in config files"""
    for file in glob("config/*.py"):
        content = open(file).read()
        assert "password" not in content.lower()
        assert "api_key" not in content.lower()
        assert "secret" not in content.lower()

def test_sql_injection_prevention():
    """Test parameterized queries"""
    # Should use parameterized queries
    result = db.execute("SELECT * FROM users WHERE email = %s", [user_email])
    # NOT: f"SELECT * FROM users WHERE email = '{user_email}'"

def test_xss_prevention():
    """Test HTML escaping"""
    from markupsafe import escape
    user_input = "<script>alert('xss')</script>"
    assert escape(user_input) == "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"
```

### Security Scanning

```bash
# OWASP Dependency Check
dependency-check.sh --scan .

# Snyk scanning
snyk test

# Trivy Docker image scanning
trivy image lrqa-app:v2.0

# Bandit (Python security)
bandit -r agents/ controllers/ models/ services/
```

---

## 7. Compliance & Audit

### GDPR Compliance Checklist
- [ ] Data minimization (collect only needed data)
- [ ] Purpose limitation (use only for stated purpose)
- [ ] Storage limitation (delete after 30 days minimum)
- [ ] Integrity & confidentiality (encryption)
- [ ] User rights (export, delete, rectify)
- [ ] Audit trail (all data operations logged)
- [ ] Privacy policy updated
- [ ] Data Processing Agreement (DPA) signed

### SOC 2 Type II Compliance
- [ ] Access controls (authentication, authorization)
- [ ] Change management (code review, testing)
- [ ] Monitoring (logging, alerting)
- [ ] Incident response (procedures documented)
- [ ] Data retention (policies implemented)
- [ ] Business continuity (backup, recovery)

---

## 8. Deployment Checklist

### Pre-Deployment
- [ ] All security tests passing
- [ ] Code encrypted with PyArmor
- [ ] Container image signed
- [ ] Secrets configured in Vault
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Security audit passed
- [ ] Load testing completed

### Go-Live
- [ ] Blue-green deployment active
- [ ] Rolling updates started
- [ ] Monitoring dashboard active
- [ ] Alert rules configured
- [ ] On-call team briefed
- [ ] Rollback plan tested
- [ ] Stakeholders notified

### Post-Deployment
- [ ] System stable (no errors)
- [ ] Performance acceptable
- [ ] Security monitoring active
- [ ] Daily health checks
- [ ] Weekly security reviews
- [ ] Monthly full audit

---

## 9. Incident Response

### Security Incident Escalation
```
Level 1: Internal (1-5 people affected)
├─ Acknowledge within 1 hour
├─ Investigate in parallel
└─ Update within 4 hours

Level 2: Internal (5-50 people affected)
├─ Acknowledge within 30 minutes
├─ Incident commander appointed
├─ CEO notification
└─ Update every 2 hours

Level 3: Major (50+ people affected)
├─ Acknowledge immediately
├─ Full incident response team
├─ Public communication prepared
└─ Update every 1 hour
```

---

## 10. Phase 5 Implementation Tasks

### Days 1-2: Code Encryption
- [ ] Install PyArmor
- [ ] Create PyArmor configuration
- [ ] Encrypt agent code
- [ ] Update Dockerfile for encryption
- [ ] Test encrypted build
- [ ] Document encryption process

### Days 2-3: Docker Signing & Registry
- [ ] Generate GPG signing key
- [ ] Implement image signing workflow
- [ ] Setup Docker registry (private)
- [ ] Configure image push/pull
- [ ] Setup registry security
- [ ] Document image verification

### Days 3-4: Vault Integration
- [ ] Setup HashiCorp Vault (or AWS Secrets Manager)
- [ ] Create secret storage structure
- [ ] Migrate all credentials to Vault
- [ ] Implement secret retrieval in app
- [ ] Configure automatic rotation
- [ ] Test secret refresh

### Days 4-5: Security Testing & Documentation
- [ ] Run security scanning tools
- [ ] Perform penetration testing
- [ ] Document security architecture
- [ ] Create security runbook
- [ ] Setup monitoring & alerting
- [ ] Finalize compliance checklist

---

## Success Metrics

| Item | Target | Status |
|------|--------|--------|
| Code Encryption | 100% of agents | 🔄 In Progress |
| Image Signing | 100% of images | 🔄 In Progress |
| Secrets in Vault | 100% of credentials | 🔄 In Progress |
| Security Tests | 100% passing | 🔄 In Progress |
| GDPR Compliance | 100% | 🔄 In Progress |
| SOC 2 Type II | In progress | 🔄 In Progress |

---

## Next Steps

After Phase 5 Completion:
1. **Production Deployment**: Blue-green rollout across locations
2. **Monitoring & Observability**: Setup comprehensive monitoring
3. **Incident Response**: Team training and drills
4. **Documentation**: User & admin guides
5. **Support**: 24/7 operations handoff

