# Cloud Deployment Quick Start

## TL;DR
Deploy Flask app to cloud server, create SSH tunnel to lab, users access via VPN.

## Quick Setup (5 Steps)

### 1. On Cloud Server - Clone & Install
```bash
git clone https://github.com/viswaPatneedi/lrqa-middleware-testing-dashboard.git
cd lrqa-middleware-testing-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Tunnel
```bash
# Edit tunnel config
nano setup_lab_tunnel.sh

# Update these lines:
LAB_GATEWAY_HOST="your-lab-gateway-ip"    # e.g., 71.230.73.95
LAB_GATEWAY_PORT="60201"                   # Your SSH port
LAB_GATEWAY_USER="pi"
SSH_KEY_FILE="$HOME/.ssh/id_rsa_lab"
```

### 3. Start Tunnel
```bash
# Test tunnel
./setup_lab_tunnel.sh

# Or install as service (recommended)
sudo ./setup_tunnel_service.sh
```

### 4. Set Environment & Run
```bash
export TUNNEL_MODE=true
export FLASK_SERVER_HOST=$(hostname -I | awk '{print $1}')  # Or your hostname
python app.py
```

### 5. Access Dashboard
```
1. Connect to company VPN
2. Browse to: http://your-server-ip:5000
3. Test connection to devices
4. Click "View" to see device screens
```

## Files Created

- **config_deployment.py** - Deployment mode configuration
- **setup_lab_tunnel.sh** - SSH tunnel setup script
- **setup_tunnel_service.sh** - Systemd service installer
- **CLOUD_DEPLOYMENT_GUIDE.md** - Full deployment documentation

## Key Environment Variables

```bash
TUNNEL_MODE=true                          # Enable cloud deployment mode
FLASK_SERVER_HOST=flask.company.com       # Your Flask server hostname/IP
```

## Tunnel Port Mappings

| Device IP    | SSH Port  | VNC Port |
|-------------|-----------|----------|
| 10.0.0.250  | 10250     | 5800     |
| 10.0.0.101  | 10101     | 5801     |
| 10.0.0.195  | 10195     | 5802     |
| 10.0.0.249  | 10249     | 5803     |
| 10.0.0.238  | 10238     | 5804     |
| IR Blaster  | -         | 5033     |

## Quick Commands

```bash
# Check tunnel status
sudo systemctl status lab-tunnel

# View tunnel logs
sudo journalctl -u lab-tunnel -f

# Restart tunnel
sudo systemctl restart lab-tunnel

# Test device connection
ssh -p 10250 root@localhost

# Test VNC
curl -I http://localhost:5800/
```

## Troubleshooting

**Can't connect to devices?**
```bash
sudo systemctl status lab-tunnel
ss -tuln | grep 10250
```

**VNC not loading?**
```bash
echo $FLASK_SERVER_HOST  # Must be set!
ss -tuln | grep 5800
```

**Tunnel disconnects?**
```bash
sudo journalctl -u lab-tunnel -n 50
# Check SSH key authentication is working
```

## Architecture

```
User → VPN → Flask Server → SSH Tunnel → Lab Gateway → Devices
```

---

**Full documentation:** See [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)
