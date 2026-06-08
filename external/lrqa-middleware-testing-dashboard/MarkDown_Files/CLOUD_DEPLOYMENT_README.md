# Cloud/VPN Deployment Files

This directory contains files for deploying the Flask Device Testing Dashboard to a cloud server or company network server, accessible via VPN.

## Quick Links

- 📖 **[Full Deployment Guide](CLOUD_DEPLOYMENT_GUIDE.md)** - Complete step-by-step instructions
- ⚡ **[Quick Start Guide](CLOUD_DEPLOYMENT_QUICKSTART.md)** - Get started in 5 steps
- 📝 **[Implementation Summary](CLOUD_DEPLOYMENT_SUMMARY.md)** - Technical details and changes

## Files Overview

### Configuration
- `config_deployment.py` - Deployment mode configuration and dynamic URL generation

### Setup Scripts
- `setup_lab_tunnel.sh` - Create SSH tunnel to lab devices
- `setup_tunnel_service.sh` - Install tunnel as systemd service
- `start_cloud_mode.sh` - Start Flask app in cloud/tunnel mode

### Documentation
- `CLOUD_DEPLOYMENT_GUIDE.md` - Comprehensive deployment guide
- `CLOUD_DEPLOYMENT_QUICKSTART.md` - Quick reference and commands
- `CLOUD_DEPLOYMENT_SUMMARY.md` - Implementation details and changelog
- `CLOUD_DEPLOYMENT_README.md` - This file

## Usage Modes

### Local Mode (Default)
```bash
python app.py
```
Direct device access, no tunneling.

### Cloud/VPN Mode
```bash
export TUNNEL_MODE=true
export FLASK_SERVER_HOST=your-server-hostname
python app.py
```
Access via SSH tunnels, VPN-only access.

## Quick Start

1. **Edit tunnel configuration:**
   ```bash
   nano setup_lab_tunnel.sh
   # Update LAB_GATEWAY_HOST, LAB_GATEWAY_PORT, LAB_GATEWAY_USER
   ```

2. **Install tunnel service:**
   ```bash
   sudo ./setup_tunnel_service.sh
   ```

3. **Start application:**
   ```bash
   ./start_cloud_mode.sh
   ```

4. **Access dashboard:**
   - Connect to VPN
   - Browse to `http://your-server:5000`

## Architecture

```
User (VPN) → Flask Server → SSH Tunnel → Lab Gateway → Devices
```

## Port Mappings

| Service | Original | Tunnel |
|---------|----------|--------|
| Device SSH | 10.0.0.x:10022 | localhost:102xx |
| Device VNC | 10.0.0.x:5800 | localhost:580x |
| IR Blaster | 10.0.0.33:4998 | localhost:5033 |

## Environment Variables

```bash
TUNNEL_MODE=true|false          # Enable/disable tunnel mode
FLASK_SERVER_HOST=hostname      # Flask server hostname for VNC URLs
```

## Support

- 📖 Read the [Full Guide](CLOUD_DEPLOYMENT_GUIDE.md) for detailed instructions
- 🐛 Check [Troubleshooting](CLOUD_DEPLOYMENT_GUIDE.md#troubleshooting) section
- 🔍 View service logs: `sudo journalctl -u lab-tunnel -f`

## Security

✅ VPN-only access  
✅ SSH key authentication  
✅ No public exposure  
✅ Encrypted tunnels  

See [Security Considerations](CLOUD_DEPLOYMENT_GUIDE.md#security-considerations) for more.
