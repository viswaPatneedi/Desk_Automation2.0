# Cloud Deployment Implementation Summary

## What Was Done

The Flask Device Testing Dashboard now supports cloud/VPN deployment with automatic SSH tunnel management and dynamic VNC URL generation. Users can access the dashboard via company VPN while the application securely connects to lab devices through persistent SSH tunnels.

## Files Created

### 1. Configuration Files
- **config_deployment.py** - Central configuration for deployment modes
  - Manages TUNNEL_MODE flag
  - VNC and SSH port mappings
  - Dynamic URL generation functions
  - Helper functions for connection parameters

### 2. Setup Scripts
- **setup_lab_tunnel.sh** - SSH tunnel creation script
  - Configurable device and VNC port forwards
  - IR blaster tunnel support
  - Connection testing
  - Can run standalone or as systemd service

- **setup_tunnel_service.sh** - Systemd service installer
  - Creates persistent tunnel service
  - Auto-restart on failure
  - Boot-time startup
  - Easy enable/disable/status commands

- **start_cloud_mode.sh** - Flask app launcher for cloud mode
  - Environment variable setup
  - Pre-flight tunnel checks
  - Virtual environment activation
  - User-friendly startup messages

### 3. Documentation
- **CLOUD_DEPLOYMENT_GUIDE.md** - Comprehensive deployment guide
  - Architecture overview
  - Step-by-step setup instructions
  - Troubleshooting section
  - Security considerations
  - Maintenance procedures

- **CLOUD_DEPLOYMENT_QUICKSTART.md** - Quick reference
  - 5-step quick setup
  - Command cheatsheet
  - Port mapping table
  - Common troubleshooting commands

## Files Modified

### 1. models/device.py
**Changes:**
- Added `from config_deployment import get_vnc_url, get_device_connection_params, TUNNEL_MODE`
- Added `original_ip` attribute to track device's actual IP
- Changed `vnc_url` to `_vnc_url` (private) and created `vnc_url` property
- Property dynamically generates VNC URL based on deployment mode
- `from_dict()` now applies tunnel mode connection parameters when TUNNEL_MODE=true

**Impact:**
- Transparent VNC URL generation - no manual URL updates needed
- Automatic IP/port transformation in tunnel mode
- Backward compatible with local mode

### 2. app.py
**Changes:**
- Added `from config_deployment import print_deployment_info`
- Added `print_deployment_info()` call at startup
- Displays deployment mode and port mappings on app start

**Impact:**
- Clear visibility into active deployment mode
- Easy verification of configuration
- Helps troubleshooting connection issues

### 3. devices.json
**Changes:**
- Updated all `vnc_url` fields to use device IPs with port 5800
- Format: `http://<device_ip>:5800/`
- Removed public IP references (71.230.73.95)

**Impact:**
- VNC URLs now use device IPs directly in local mode
- Automatically transformed to use Flask server hostname in tunnel mode
- All devices now have VNC URLs (including ES1 and SKY devices)

## How It Works

### Local Mode (Default)
```bash
# No environment variables needed
python app.py
```
- Devices accessed directly at their 10.0.0.x IPs
- VNC URLs point to device IPs with port 5800
- Normal operation, no tunneling

### Cloud/Tunnel Mode
```bash
export TUNNEL_MODE=true
export FLASK_SERVER_HOST=flask.company.com
python app.py

# Or use helper script
./start_cloud_mode.sh
```
- SSH tunnel must be running (setup_lab_tunnel.sh or lab-tunnel.service)
- Devices accessed at localhost with mapped ports
- VNC URLs point to Flask server hostname with mapped ports
- Transparent to users - UI looks identical

## Port Mappings

| Device           | Original IP | SSH Port | Tunnel Port | VNC Original | VNC Tunnel |
|-----------------|-------------|----------|-------------|--------------|------------|
| Element-A4K     | 10.0.0.250  | 10022    | 10250       | 5800         | 5800       |
| WestingHouse    | 10.0.0.101  | 10022    | 10101       | 5800         | 5801       |
| SHARP           | 10.0.0.195  | 10022    | 10195       | 5800         | 5802       |
| ES1-LAVANYA     | 10.0.0.249  | 10022    | 10249       | 5800         | 5803       |
| SKY-XIONE       | 10.0.0.238  | 10022    | 10238       | 5800         | 5804       |
| IR Blaster      | 10.0.0.33   | 4998     | 5033        | N/A          | N/A        |

## Deployment Workflow

### For Cloud/VPN Deployment:

1. **On Flask Server:**
   ```bash
   # Clone repo
   git clone <repo>
   cd lrqa-middleware-testing-dashboard
   
   # Configure tunnel
   nano setup_lab_tunnel.sh  # Update LAB_GATEWAY_* variables
   
   # Install tunnel service
   sudo ./setup_tunnel_service.sh
   
   # Start Flask app
   export TUNNEL_MODE=true
   export FLASK_SERVER_HOST=$(hostname)
   python app.py
   ```

2. **Users:**
   ```bash
   # Connect to company VPN
   # Browse to http://flask-server:5000
   # Use dashboard normally
   ```

### For Local Deployment:
```bash
# No changes needed - works as before
python app.py
```

## Key Features

✅ **Automatic Mode Detection** - TUNNEL_MODE env var controls behavior  
✅ **Dynamic VNC URLs** - Generated based on deployment mode  
✅ **Transparent Device Access** - App code unchanged, works in both modes  
✅ **Persistent Tunnels** - Systemd service with auto-restart  
✅ **Easy Troubleshooting** - Clear status messages and logging  
✅ **Backward Compatible** - Local mode works exactly as before  
✅ **Secure** - VPN-only access, SSH key authentication  

## Testing

### Test Local Mode
```bash
unset TUNNEL_MODE
python app.py
# Test device connection
# Click VNC View - should open http://10.0.0.250:5800/
```

### Test Cloud Mode
```bash
export TUNNEL_MODE=true
export FLASK_SERVER_HOST=localhost  # For testing locally
./setup_lab_tunnel.sh &  # Start tunnel in background
python app.py
# Test device connection - should use localhost:10250
# Click VNC View - should open http://localhost:5800/
```

## Next Steps for Production Deployment

1. **Deploy to Cloud Server** - Follow CLOUD_DEPLOYMENT_GUIDE.md
2. **Configure SSH Keys** - For secure tunnel authentication
3. **Setup Nginx** - For HTTPS and reverse proxy
4. **Enable Email Service** - For test notifications
5. **User Training** - How to connect via VPN and use dashboard

## Security Notes

- Flask app only accessible via company VPN
- SSH tunnel uses key authentication (recommended)
- No public exposure of devices or Flask app
- All traffic encrypted through SSH tunnel
- VPN provides access control and audit trail

## Troubleshooting Quick Reference

```bash
# Check deployment mode
python -c "from config_deployment import *; print_deployment_info()"

# Check tunnel status
sudo systemctl status lab-tunnel

# Check ports
ss -tuln | grep -E '10250|5800'

# Test device SSH
ssh -p 10250 root@localhost

# Test VNC
curl -I http://localhost:5800/

# View logs
sudo journalctl -u lab-tunnel -f
```

## Rollback

To rollback to local-only mode:
1. Stop tunnel: `sudo systemctl stop lab-tunnel`
2. Unset env vars: `unset TUNNEL_MODE FLASK_SERVER_HOST`
3. Restart app: `python app.py`

All changes are non-breaking and backward compatible.

---

**Implementation Date:** January 9, 2026  
**Status:** ✅ Complete and tested  
**Deployment:** Ready for production
