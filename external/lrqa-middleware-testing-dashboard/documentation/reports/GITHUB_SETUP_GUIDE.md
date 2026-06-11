# GitHub Setup Guide: Desk-Automation-V2.0

## Step 1: Create the Repository

### Via GitHub Web UI
1. Go to **github.com** and log in as `viswaPatneedi`
2. Click **+** (top-right) → **New repository**
3. Configure:
   - **Repository name**: `Desk-Automation-V2.0`
   - **Description**: `Enterprise Device Automation Platform v2.0 - Multi-region deployment with AI agents`
   - **Visibility**: `Private` ✅
   - **Initialize**: Check "Add a README.md"
   - **License**: Apache 2.0 (with commercial restrictions added manually)
4. Click **Create repository**

### Via Command Line (Alternative)
```bash
# Create repo via GitHub CLI
gh repo create Desk-Automation-V2.0 \
  --private \
  --description "Enterprise Device Automation Platform v2.0" \
  --remote=origin \
  --source=. \
  --remote-name=origin
```

---

## Step 2: Add License & Protection Rules

### Add Commercial License to Repo
1. Create file: `LICENSE_COMMERCIAL.txt`
2. Content:
```
This software is subject to a PROPRIETARY LICENSE.

Unauthorized copying, selling, or permitting others to use this software 
is prohibited and subject to civil and criminal penalties.

For licensing inquiries, contact: [team email]
```

### Configure GitHub Branch Protection
1. Go to repo **Settings** → **Branches**
2. Add branch protection rule for **main**:
   - ✅ Require pull request reviews (1+ approvals)
   - ✅ Require branches to be up to date
   - ✅ Require status checks to pass
   - ✅ Enforce administrators rule
3. Add branch protection rule for **staging**:
   - ✅ Require pull request reviews (1 approval)
   - ⚠️ Allow force pushes (for cleanup if needed)

---

## Step 3: Clone & Set Up Branching

```bash
# Clone the new repo
git clone https://github.com/viswaPatneedi/Desk-Automation-V2.0.git
cd Desk-Automation-V2.0

# Create staging branch (based on main)
git checkout -b staging
git push -u origin staging

# Back to main
git checkout main
```

---

## Step 4: Add v1 Code to Repository

### Option A: Copy v1 Files (Recommended - Clean Start)
```bash
# From v1 directory
cp -r /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement/* \
      ./Desk-Automation-V2.0/

# Exclude unnecessary files
rm -rf Desk-Automation-V2.0/.git
rm -rf Desk-Automation-V2.0/__pycache__
rm -rf Desk-Automation-V2.0/iteration_logs/*
rm -rf Desk-Automation-V2.0/screenshots/*
rm -rf Desk-Automation-V2.0/device_logs/*

# Keep only template/reference screenshots
mkdir -p Desk-Automation-V2.0/reference_screenshots/
cp /path/to/v1/reference_screenshots/* Desk-Automation-V2.0/reference_screenshots/
```

### Option B: Migrate via Git History (Preserve Commits)
```bash
# Add v1 as remote
git remote add v1-source /home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement
git fetch v1-source

# Merge v1 history
git merge --allow-unrelated-histories v1-source/main -m "Initial v1.0 codebase import"

# Cleanup
git remote remove v1-source
```

---

## Step 5: Create Initial Commit Structure

```bash
git add .
git commit -m "Initial commit: v1.0 codebase imported

- Flask-based device management platform
- 29 device methods
- SSH device control
- Job queuing with lock management
- Multi-region support prepared
- Ready for v2.0 refactoring"

git push -u origin main
```

---

## Step 6: Set Up GitHub Actions for CI/CD

Create `.github/workflows/build-docker.yml`:

```yaml
name: Build & Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          docker build -t desk-automation:latest \
                       -f Dockerfile.prod \
                       -t desk-automation:${{ github.sha }} .
      
      - name: Login to Docker Registry
        run: echo "${{ secrets.DOCKER_REGISTRY_PASSWORD }}" | \
             docker login -u "${{ secrets.DOCKER_REGISTRY_USER }}" --password-stdin
      
      - name: Push to registry
        run: |
          docker push desk-automation:latest
          docker push desk-automation:${{ github.sha }}
      
      - name: Sign image
        run: |
          # GPG sign the image manifest
          docker manifest inspect desk-automation:${{ github.sha }}
```

---

## Step 7: Repository Structure for v2.0

```
Desk-Automation-V2.0/
├── .github/
│   ├── workflows/
│   │   ├── build-docker.yml         # Build images from main
│   │   └── test-staging.yml         # Run tests on staging
│   └── CODEOWNERS                   # Code review requirements
│
├── app.py                           # v1.0 entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── .gitignore                       # Exclude: .env, __pycache__, logs
│
├── models/                          # v1.0 models (keep as-is for now)
├── controllers/                     # v1.0 controllers
├── services/                        # v1.0 services
├── config_*.py                      # v1.0 configuration
├── method_*.py                      # v1.0 device methods
├── utils/                           # v1.0 utilities
├── templates/                       # v1.0 HTML templates
├── static/                          # v1.0 JS/CSS
│
├── Dockerfile                       # v1.0 Docker config
├── Dockerfile.prod                  # Production image (for main branch)
├── docker-compose.yml               # Compose for single location
├── docker-compose.multi-location.yml # Compose for multi-location
│
├── kubernetes/                      # K8s manifests (future)
│
├── reference_screenshots/           # Reference screens for AI training
│
├── docs/
│   ├── V2_REQUIREMENTS.md           # All 18 requirements
│   ├── GITHUB_SETUP_GUIDE.md        # This file
│   ├── ARCHITECTURE.md              # v2.0 architecture docs
│   ├── DEPLOYMENT_GUIDE.md          # Multi-location deployment
│   ├── AGENT_FRAMEWORK.md           # AI agents & skills
│   └── DATABASE_SCHEMA.md           # DB schema for v2.0
│
├── LICENSE                          # Apache 2.0
├── LICENSE_COMMERCIAL.txt           # Proprietary restrictions
├── README.md                        # Project overview
├── CHANGELOG.md                     # Version history
└── VERSION                          # Current version file
```

---

## Step 8: Branching Strategy & Workflow

### **Main Branch** (Production)
- ✅ Code is tested, stable, production-ready
- ✅ Only receives PRs from staging
- ✅ Every commit tagged with version (v2.0.1, v2.0.2, etc.)
- ✅ Docker images built from main tags
- ✅ Deployed to production locations

### **Staging Branch** (R&D)
- 🔬 All v2.0 development happens here
- 🔬 Agents conduct R&D, implement requirements
- 🔬 CI/CD runs basic tests, doesn't deploy
- 🔬 Multiple PRs merged daily during development
- ✅ Once stabilized (all 18 requirements done), create PR to main
- ✅ Main branch review required (code quality, no data loss, agent correctness)

### **Feature Branches** (Temporary)
- From: **staging**
- Naming: `feat/requirement-{number}-description`
- Examples:
  - `feat/requirement-03-ai-agents-framework`
  - `feat/requirement-16-distributed-data-sync`
  - `feat/requirement-06-eta-device-lock`
- PR to: **staging** (1 reviewer)
- Delete after merge

### **Hotfix Branches** (If Needed)
- From: **main**
- Naming: `hotfix/issue-description`
- PR to: **main** + **staging** (to stay in sync)

---

## Step 9: Workflow Example - Agent-CodeArchitect Work

```bash
# Day 1: Create feature branch
git checkout staging
git pull origin staging
git checkout -b feat/requirement-01-mvc-refactor

# Throughout Week 1: Make commits
git commit -m "MVC: Move controllers to new structure"
git commit -m "MVC: Create modal popup component library"
git commit -m "MVC: Update imports across codebase"

# Push incrementally
git push origin feat/requirement-01-mvc-refactor

# Create PR when ready
# Title: "[R1] MVC Architecture Refactor"
# Description: 
#   - Cleaned controller hierarchy
#   - Built modal component library
#   - Updated all imports
#   - Tested: No breaking changes

# Once approved & merged to staging
git checkout staging
git pull origin staging
git branch -D feat/requirement-01-mvc-refactor
```

---

## Step 10: Docker Image Deployment Workflow

### **From Main Branch to Multi-Location**

```bash
# Tag a version in main
git tag -a v2.0.1 -m "Release v2.0.1

- Completed MVC refactor
- Database schema implemented
- Parent agent framework ready"

git push origin v2.0.1

# CI/CD automatically:
# 1. Builds Dockerfile.prod
# 2. Creates image: desk-automation:v2.0.1
# 3. Encrypts code (PyArmor)
# 4. Signs image with GPG
# 5. Pushes to private registry
# 6. Creates release notes
```

### **Deploy to Locations**

```bash
# Location: UK
docker pull private-registry/desk-automation:v2.0.1
docker run -e LOCATION=UK -e TEAM=team-uk \
           -e DB_URL=https://master.db.company.com \
           private-registry/desk-automation:v2.0.1

# Location: India North
docker pull private-registry/desk-automation:v2.0.1
docker run -e LOCATION=INDIA_NORTH -e TEAM=team-india-n \
           -e DB_URL=https://master.db.company.com \
           private-registry/desk-automation:v2.0.1

# AI DistributedDataSync agent automatically:
# - Registers this location with central DB
# - Starts syncing devices, patterns, methods from DB
# - Monitors for local changes
# - Pushes new data back to DB + GitHub repo
```

---

## Step 11: Memory & Documentation

Create `docs/GITHUB_WORKFLOW_MEMORY.md` to track:
- Who created which branches
- What each agent delivered
- PR reviews and approvals
- Issues and resolutions
- Version release dates

---

## Step 12: Access & Security

### GitHub Settings
- **Collaborators**: Add team members with appropriate roles
- **Secrets** (Settings → Secrets):
  - `DOCKER_REGISTRY_USER`: Your registry username
  - `DOCKER_REGISTRY_PASSWORD`: Registry password
  - `GPG_PRIVATE_KEY`: For signing images
  - `DOCKER_REGISTRY_URL`: Private registry URL

### Branch Protection
- Main: Requires 2 approvals
- Staging: Requires 1 approval
- Enforce require branches to be up to date

---

## Summary

| Step | Status | By When |
|------|--------|---------|
| 1. Create repo | ⏳ | Today |
| 2. Add licenses | ⏳ | Today |
| 3. Clone & branch | ⏳ | Today |
| 4. Add v1 code | ⏳ | Today |
| 5. Initial commit | ⏳ | Today |
| 6. GitHub Actions | ⏳ | Day 2 |
| 7-12. Complete setup | ⏳ | Day 2 |
| **Ready for Agents** | ✅ | Day 3 |

Once complete, the repository is ready for Phase 1 agents to begin v2.0 development!
