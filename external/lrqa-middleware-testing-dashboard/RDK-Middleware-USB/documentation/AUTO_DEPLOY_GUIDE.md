# Automatic Deployment System

## Overview
This system automatically syncs your R-Pi with GitHub changes, allowing you to develop on your laptop and have changes automatically deployed to your R-Pi.

## Workflow

```
Laptop (Development)  →  GitHub  →  R-Pi (Auto-Deploy)
     ↓                      ↓              ↓
  git push             (repository)    git pull + restart
```

## Setup Instructions

### 1️⃣ On R-Pi (One-Time Setup)

```bash
# Navigate to your project
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

# Run the setup script
chmod +x setup_auto_deploy.sh
./setup_auto_deploy.sh
```

**What this does:**
- Creates a systemd timer that checks GitHub every 5 minutes
- Automatically pulls new changes when detected
- Restarts your application service with the new code
- Keeps everything in your venv
- Preserves local data files (JSON logs, etc.)

### 2️⃣ On Your Laptop (Development)

```bash
# Clone the repository (first time only)
git clone https://github.com/viswaPatneedi/lrqa-middleware-testing-dashboard.git
cd lrqa-middleware-testing-dashboard

# Configure git (if not already done)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Make changes to your code
# ... edit files ...

# Commit and push
git add .
git commit -m "Your change description"
git push origin main
```

**Within 5 minutes**, your R-Pi will:
1. Detect the new changes
2. Pull them from GitHub
3. Update dependencies if needed
4. Restart the application automatically

## Monitoring & Management

### Check Auto-Deploy Status
```bash
# Check if timer is running
systemctl status auto-deploy.timer

# Check last deployment
systemctl status auto-deploy.service

# View real-time logs
journalctl -u auto-deploy.service -f

# View deployment history
tail -f ~/Desktop/viswa/Latest_Enhancement/Enhancement/auto_deploy.log
```

### Manual Deployment Trigger
```bash
# Force immediate deployment check
sudo systemctl start auto-deploy.service
```

### Stop/Start Auto-Deploy
```bash
# Temporarily stop (restarts on reboot)
sudo systemctl stop auto-deploy.timer

# Permanently disable
sudo systemctl disable auto-deploy.timer

# Re-enable
sudo systemctl enable auto-deploy.timer
sudo systemctl start auto-deploy.timer
```

## How It Works

### Auto-Deploy Script (`auto_deploy.sh`)
1. Fetches latest commits from GitHub
2. Compares local vs remote commit hashes
3. If different:
   - Stashes local changes (preserves data files)
   - Pulls new code
   - Reapplies stashed changes
   - Updates Python dependencies
   - Restarts application service
4. Logs everything to `auto_deploy.log`

### Systemd Timer
- **First Check**: 2 minutes after boot
- **Regular Checks**: Every 5 minutes
- **Low Resource Impact**: Only runs when there are changes

## Configuration

### Change Check Interval

Edit the timer file:
```bash
sudo nano /etc/systemd/system/auto-deploy.timer
```

Change `OnUnitActiveSec=5min` to your desired interval:
- `1min` - Check every minute (aggressive)
- `5min` - Check every 5 minutes (default, recommended)
- `15min` - Check every 15 minutes (conservative)

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart auto-deploy.timer
```

### Change Service Name

If your systemd service has a different name, edit `auto_deploy.sh`:
```bash
nano auto_deploy.sh
# Change: SERVICE_NAME="device-testing.service"
# To:     SERVICE_NAME="your-service-name.service"
```

## Troubleshooting

### Changes not syncing?
```bash
# Check timer is running
systemctl status auto-deploy.timer

# Check for errors
journalctl -u auto-deploy.service -n 50

# View deployment log
tail -50 ~/Desktop/viswa/Latest_Enhancement/Enhancement/auto_deploy.log

# Manually trigger
sudo systemctl start auto-deploy.service
```

### Git authentication issues?
```bash
# If using HTTPS, ensure credentials are cached
git config --global credential.helper store
git pull  # Enter credentials once

# Or switch to SSH keys (recommended)
```

### Service not restarting?
```bash
# Check service name matches
systemctl list-units --type=service | grep -i device

# Update SERVICE_NAME in auto_deploy.sh if different
```

### Merge conflicts?
```bash
# The script auto-stashes local changes
# If conflicts occur, resolve manually:
cd ~/Desktop/viswa/Latest_Enhancement/Enhancement
git status
git stash list
git stash drop  # If you don't need stashed changes
```

## Best Practices

### 1. Data File Management
The auto-deploy script preserves your local data files (JSON logs, device configs) by stashing them before pulling. But for critical data:
- Keep backups of `devices.json`, `jobs.json`, etc.
- Or exclude them from git entirely (already in `.gitignore`)

### 2. Testing Before Push
```bash
# On laptop, test locally if possible
# Or push to a test branch first
git checkout -b test-feature
git push origin test-feature

# Merge to main only after testing
```

### 3. Monitoring Deployments
Set up a cron job to email you deployment summaries:
```bash
# Add to crontab
0 9 * * * tail -20 ~/Desktop/viswa/Latest_Enhancement/Enhancement/auto_deploy.log | mail -s "Daily Deployment Report" your@email.com
```

### 4. Service Dependencies
If your application depends on external services (email, database), ensure they're available before restart. Modify `auto_deploy.sh` to add health checks.

## Laptop Development Setup

### Recommended IDE Setup
1. **VS Code** with extensions:
   - Python
   - GitLens
   - Remote - SSH (to edit directly on R-Pi if needed)

2. **Local Testing** (optional):
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python app.py
   ```

### Git Workflow
```bash
# Daily workflow
git pull origin main          # Start with latest
# ... make changes ...
git add .
git commit -m "Description"
git push origin main          # R-Pi auto-deploys within 5 min

# Feature branches (optional)
git checkout -b feature-name
# ... work on feature ...
git push origin feature-name
# Create PR on GitHub, merge to main
```

## Security Notes

- The R-Pi needs read access to your GitHub repo
- If repo is private, ensure R-Pi has valid credentials
- Consider using deploy keys (SSH) for better security
- The systemd service runs as user `pi` (not root)

## Disabling Auto-Deploy

If you need to work directly on R-Pi without auto-sync:
```bash
# Disable timer
sudo systemctl stop auto-deploy.timer
sudo systemctl disable auto-deploy.timer

# Re-enable later
sudo systemctl enable auto-deploy.timer
sudo systemctl start auto-deploy.timer
```

## Support

For issues or questions:
1. Check deployment logs: `tail -f auto_deploy.log`
2. Check system logs: `journalctl -u auto-deploy.service -f`
3. Verify git status: `git status` and `git log`
