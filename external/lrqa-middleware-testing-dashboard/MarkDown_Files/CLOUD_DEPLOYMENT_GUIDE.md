# Cloud/VPN Deployment Guide

This guide explains how to deploy the Flask Device Testing Dashboard to a cloud server or company network server, accessible only via VPN, while maintaining connectivity to your lab devices through SSH tunnels.

## Architecture Overview

```
┌─────────────────┐     VPN Connection    ┌──────────────────┐
│  User's Laptop  │─────────────────────→ │  Company VPN     │
└─────────────────┘                        └──────────────────┘
                                                     │
                                                     ↓
                                          ┌──────────────────┐
                                          │  Flask Server    │
                                          │  (Cloud/Company) │
                                          └──────────────────┘
                                                     │
                                            SSH Tunnel (Persistent)
                                                     │
                                                     ↓
                                          ┌──────────────────┐
                                          │  Lab Gateway     │
                                          │  (Raspberry Pi)  │
                                          └──────────────────┘
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ↓                ↓                ↓
                              ┌─────────┐     ┌─────────┐     ┌─────────┐
                              │ Device  │     │ Device  │     │ Device  │
                              │ 10.0.0  │     │ 10.0.0  │     │ 10.0.0  │
                              └─────────┘     └─────────┘     └─────────┘
```

## Benefits

✅ **Secure Access** - No public exposure, VPN-only access  
✅ **Remote Control** - Control lab devices from anywhere with VPN  
✅ **Team Collaboration** - Multiple team members can access simultaneously  
✅ **Centralized Logs** - All test results stored on cloud server  
✅ **VNC Viewing** - Live device screens accessible through tunnels  

---

## Deployment Steps

### Phase 1: Prepare Cloud/Company Server

#### 1.1 Server Requirements
- Linux server (Ubuntu 20.04+ recommended)
- Python 3.8+
- Access to company VPN network
- Ability to create outbound SSH connections

#### 1.2 Clone Repository on Server
```bash
ssh your-user@flask-server
cd /opt  # or your preferred directory
git clone https://github.com/viswaPatneedi/lrqa-middleware-testing-dashboard.git
cd lrqa-middleware-testing-dashboard
```

#### 1.3 Install Dependencies
```bash
# Install system packages
sudo apt update
sudo apt install -y python3-pip python3-venv git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

#### 1.4 Configure Environment Variables
```bash
# Create environment configuration file
cat > .env << 'EOF'
# Deployment Mode
TUNNEL_MODE=true
FLASK_SERVER_HOST=your-flask-server-hostname  # e.g., flask.company.com or 10.61.187.7

# Flask Configuration
SECRET_KEY=your-secure-random-secret-key-change-this
FLASK_ENV=production

# Optional: Email notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@company.com
SENDER_PASSWORD=your-app-password
EOF

# Load environment variables
source .env
export $(cat .env | xargs)
```

---

### Phase 2: Configure SSH Tunnel to Lab

#### 2.1 Setup SSH Key Authentication (Recommended)
On the Flask server:
```bash
# Generate SSH key pair (if not exists)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_lab -N ""

# Copy public key to lab gateway
ssh-copy-id -i ~/.ssh/id_rsa_lab.pub -p YOUR_LAB_PORT pi@your-lab-gateway-ip
```

#### 2.2 Configure Tunnel Script
Edit `setup_lab_tunnel.sh`:
```bash
nano setup_lab_tunnel.sh
```

Update these variables:
```bash
LAB_GATEWAY_HOST="your-lab-gateway-ip"      # e.g., "71.230.73.95" or "lab.yourdomain.com"
LAB_GATEWAY_PORT="60201"                     # Your lab gateway SSH port
LAB_GATEWAY_USER="pi"                        # SSH username
SSH_KEY_FILE="$HOME/.ssh/id_rsa_lab"        # Path to SSH key
```

Verify device mappings match your `devices.json`:
```bash
# SSH Tunnels for device access
SSH_TUNNELS=(
    "-R 10250:10.0.0.250:10022"    # Element-A4K-DESK
    "-R 10101:10.0.0.101:10022"    # WestingHouse-4K-DESK
    "-R 10195:10.0.0.195:10022"    # SHARP-DEVICE-DESK
    "-R 10249:10.0.0.249:10022"    # ES1-DESK-LAVANYA
    "-R 10238:10.0.0.238:10022"    # SKY-XIONE-UK-DEVICE
)

# VNC Tunnels for device viewing
VNC_TUNNELS=(
    "-R 5800:10.0.0.250:5800"      # Element-A4K-DESK VNC
    "-R 5801:10.0.0.101:5800"      # WestingHouse-4K-DESK VNC
    "-R 5802:10.0.0.195:5800"      # SHARP-DEVICE-DESK VNC
    "-R 5803:10.0.0.249:5800"      # ES1-DESK-LAVANYA VNC
    "-R 5804:10.0.0.238:5800"      # SKY-XIONE-UK-DEVICE VNC
)
```

#### 2.3 Test Tunnel Manually
```bash
./setup_lab_tunnel.sh
```

This will run in foreground. Press Ctrl+C to stop.  
Check if ports are listening:
```bash
# In another terminal on Flask server
ss -tuln | grep -E '10250|10101|10195|10249|10238|5800|5801|5802|5803|5804'
```

#### 2.4 Install as Persistent Service
```bash
sudo ./setup_tunnel_service.sh
```

Follow prompts to start the service. The tunnel will now:
- Start automatically on server boot
- Restart automatically if connection drops
- Run in background persistently

Check service status:
```bash
sudo systemctl status lab-tunnel
sudo journalctl -u lab-tunnel -f  # View live logs
```

---

### Phase 3: Update Application Configuration

#### 3.1 Update devices.json
The `devices.json` file can remain as-is with original device IPs. The application will automatically apply tunnel mode transformations when `TUNNEL_MODE=true`.

Current format (keep as-is):
```json
[
    {
        "ip": "10.0.0.250",
        "name": "Element-A4K-DESK",
        "port": 10022,
        "vnc_url": "http://10.0.0.250:5800/"
    }
]
```

The app automatically transforms this to use `localhost` with mapped ports when in tunnel mode.

#### 3.2 Verify Deployment Configuration
The app will print deployment info on startup:
```bash
python app.py
```

Look for:
```
============================================================
DEPLOYMENT CONFIGURATION
============================================================
Mode: TUNNEL (Cloud/VPN)
Flask Server Host: flask.company.com

VNC Port Mappings:
  10.0.0.250 → flask.company.com:5800
  10.0.0.101 → flask.company.com:5801
  ...

SSH Port Mappings:
  10.0.0.250:10022 → localhost:10250
  10.0.0.101:10022 → localhost:10101
  ...
============================================================
```

---

### Phase 4: Run Flask Application

#### 4.1 Test Run
```bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables
export TUNNEL_MODE=true
export FLASK_SERVER_HOST=your-flask-server-hostname

# Run application
python app.py
```

Access at: `http://your-flask-server-ip:5000`

#### 4.2 Production Deployment (systemd)

Create Flask service:
```bash
sudo nano /etc/systemd/system/flask-dashboard.service
```

Content:
```ini
[Unit]
Description=Flask Device Testing Dashboard
After=network.target lab-tunnel.service
Requires=lab-tunnel.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/lrqa-middleware-testing-dashboard
Environment="PATH=/opt/lrqa-middleware-testing-dashboard/venv/bin"
Environment="TUNNEL_MODE=true"
Environment="FLASK_SERVER_HOST=your-flask-server-hostname"
ExecStart=/opt/lrqa-middleware-testing-dashboard/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable flask-dashboard
sudo systemctl start flask-dashboard
sudo systemctl status flask-dashboard
```

#### 4.3 Setup Nginx Reverse Proxy (Optional)

For HTTPS and better security:
```bash
sudo apt install nginx

sudo nano /etc/nginx/sites-available/flask-dashboard
```

Content:
```nginx
server {
    listen 80;
    server_name your-flask-server-hostname;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE for log streaming
    location /stream/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/flask-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Testing the Deployment

### Test Checklist

#### 1. Connect to VPN
```bash
# Connect to your company VPN first
```

#### 2. Access Flask Dashboard
```
http://your-flask-server-hostname:5000
```

#### 3. Test Device Connection
- Click "Test Connection" for each device
- Should see: ✅ Connection successful

#### 4. Test Device Control
- Select a device
- Choose a method (e.g., Reboot)
- Execute test
- Verify logs are streaming

#### 5. Test VNC Viewing
- Click "View" button next to device MAC address
- VNC viewer should open in new tab
- Should display live device screen

---

## Troubleshooting

### Issue: Cannot Connect to Devices

**Check tunnel status:**
```bash
sudo systemctl status lab-tunnel
sudo journalctl -u lab-tunnel -n 50
```

**Check if ports are listening:**
```bash
ss -tuln | grep -E '10250|10101|10195'
```

**Test SSH manually:**
```bash
ssh -p 10250 root@localhost  # Should connect to 10.0.0.250
```

### Issue: VNC View Not Loading

**Check VNC tunnel ports:**
```bash
ss -tuln | grep -E '5800|5801|5802'
```

**Test VNC URL manually:**
```bash
curl -I http://localhost:5800/  # Should return 200 OK
```

**Verify FLASK_SERVER_HOST is set:**
```bash
echo $FLASK_SERVER_HOST  # Should show your server hostname
```

### Issue: Tunnel Keeps Disconnecting

**Check lab gateway is reachable:**
```bash
ping your-lab-gateway-ip
```

**Increase SSH timeout settings:**
Edit `setup_lab_tunnel.sh`:
```bash
SSH_CMD="$SSH_CMD -o ServerAliveInterval=30"
SSH_CMD="$SSH_CMD -o ServerAliveCountMax=10"
```

**Check firewall rules:**
```bash
sudo ufw status  # On Flask server
sudo iptables -L  # Check for blocking rules
```

---

## Switching Between Local and Cloud Mode

### Local Mode (Direct Device Access)
```bash
export TUNNEL_MODE=false
python app.py
```

### Cloud/Tunnel Mode
```bash
export TUNNEL_MODE=true
export FLASK_SERVER_HOST=your-flask-server-hostname
python app.py
```

The application automatically adapts device connections and VNC URLs based on the mode.

---

## Security Considerations

### 1. SSH Key Authentication
✅ **DO**: Use SSH keys instead of passwords  
❌ **DON'T**: Store passwords in scripts

### 2. Firewall Rules
✅ **DO**: Allow only VPN traffic to Flask server  
❌ **DON'T**: Expose Flask port publicly

### 3. HTTPS
✅ **DO**: Use Nginx with SSL/TLS in production  
❌ **DON'T**: Use HTTP in production environments

### 4. User Authentication
✅ **DO**: Enable Flask-Login for user management  
❌ **DON'T**: Allow anonymous access in production

---

## Maintenance

### Viewing Logs
```bash
# Tunnel logs
sudo journalctl -u lab-tunnel -f

# Flask app logs
sudo journalctl -u flask-dashboard -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restarting Services
```bash
# Restart tunnel
sudo systemctl restart lab-tunnel

# Restart Flask app
sudo systemctl restart flask-dashboard

# Restart Nginx
sudo systemctl restart nginx
```

### Updating Application
```bash
cd /opt/lrqa-middleware-testing-dashboard
git pull
sudo systemctl restart flask-dashboard
```

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review service logs
3. Verify network connectivity
4. Ensure VPN is connected
5. Contact system administrator

---

## Summary

You've successfully deployed the Flask Device Testing Dashboard to a cloud/company server with:

✅ Secure VPN-only access  
✅ Persistent SSH tunnels to lab devices  
✅ Dynamic VNC URL generation  
✅ Automatic service restart on failure  
✅ Production-ready systemd services  

Users can now access the dashboard via company VPN and control lab devices remotely!
