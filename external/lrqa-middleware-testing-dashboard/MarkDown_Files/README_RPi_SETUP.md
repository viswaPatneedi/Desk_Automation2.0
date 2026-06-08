# Raspberry Pi Server Setup Guide

## USB Stick Setup (Required)

### 1. Prepare USB Stick
```bash
# Connect USB stick to Raspberry Pi
# Format as FAT32 or exFAT with label "Lexar"

# Create Enhancement-output folder
sudo mkdir -p /media/pi/Lexar/Enhancement-output
sudo chown -R pi:pi /media/pi/Lexar/Enhancement-output
```

### 2. Verify USB Mount
```bash
# Check if USB is mounted
ls /media/pi/Lexar

# Check mount point
df -h | grep Lexar
```

### 3. Folder Structure
All test outputs are saved to USB in organized session folders:
```
/media/pi/Lexar/Enhancement-output/
└── <METHOD>_<DEVICE>_<IP>_<ITERATIONS>_ITR_<TIMESTAMP>/
    ├── SCREENSHOTS/
    │   ├── ITR-1/BEFORE/
    │   ├── ITR-1/AFTER/
    │   └── ...
    ├── EXECUTION_LOGS/
    └── DEVICE_LOGS/
        ├── ITR-1/
        └── ...
```

See `USB_FOLDER_STRUCTURE.md` for complete details.

---

## Quick Start - Manual Method

### 1. Transfer Files to Raspberry Pi
```bash
# On your Windows machine, use WinSCP, rsync, or scp:
scp -r Enhancement/ pi@<RPi_IP>:/home/pi/Device-Connect/New/
```

### 2. SSH into Raspberry Pi
```bash
ssh pi@<RPi_IP>
```

### 3. Install Dependencies
```bash
cd /home/pi/Device-Connect/New/Enhancement
chmod +x setup_rpi_server.sh
./setup_rpi_server.sh
```

### 4. Find Your Raspberry Pi's IP Address
```bash
hostname -I
# Example output: 192.168.1.100
```

### 5. Start the Server
```bash
# Option A: Manual start (for testing)
cd /home/pi/Device-Connect/New/Enhancement
source venv/bin/activate
python app.py

# Option B: Start as service (runs automatically)
sudo systemctl start device-test-server
```

### 6. Access from Any Device on LAN
Open a browser on any device connected to the same network:
```
http://192.168.1.100:5000
```
*(Replace with your actual Raspberry Pi IP)*

---

## Production Setup (Recommended)

For better performance and stability, use Gunicorn:

### Install Gunicorn
```bash
source venv/bin/activate
pip install gunicorn
```

### Run with Gunicorn
```bash
chmod +x run_production.sh
./run_production.sh
```

### Update Systemd Service for Gunicorn
Edit the service file:
```bash
sudo nano /etc/systemd/system/device-test-server.service
```

Change `ExecStart` line to:
```
ExecStart=/home/pi/Device-Connect/New/Enhancement/run_production.sh
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart device-test-server
```

---

## Troubleshooting

### Check if server is running
```bash
sudo systemctl status device-test-server
```

### View live logs
```bash
sudo journalctl -u device-test-server -f
```

### Check which process is using port 5000
```bash
sudo netstat -tulpn | grep 5000
```

### Test local connection on RPi
```bash
curl http://localhost:5000
```

### Firewall issues
```bash
# Check firewall status
sudo ufw status

# Allow port 5000
sudo ufw allow 5000/tcp
```

### Can't access from other devices?

1. **Verify RPi IP address:**
   ```bash
   hostname -I
   ```

2. **Check if Flask is listening on 0.0.0.0:**
   ```bash
   sudo netstat -tulpn | grep 5000
   # Should show: 0.0.0.0:5000 (not 127.0.0.1:5000)
   ```

3. **Test from RPi itself:**
   ```bash
   curl http://<RPi_IP>:5000
   ```

4. **Disable RPi firewall temporarily (testing only):**
   ```bash
   sudo ufw disable
   ```

---

## Auto-Start on Boot

Service is already configured to start on boot. To verify:
```bash
sudo systemctl is-enabled device-test-server
# Should output: enabled
```

To disable auto-start:
```bash
sudo systemctl disable device-test-server
```

To re-enable:
```bash
sudo systemctl enable device-test-server
```

---

## Accessing from Mobile Devices

On your phone/tablet browser, navigate to:
```
http://<RASPBERRY_PI_IP>:5000
```

Example:
```
http://192.168.1.100:5000
```

**Tip:** Create a bookmark for quick access!

---

## Security Considerations

### For Internal LAN Only (Current Setup)
- Server is accessible to anyone on your local network
- No authentication required
- **Do NOT expose port 5000 to the internet**

### To Add Basic Authentication (Optional)

Install Flask-HTTPAuth:
```bash
pip install Flask-HTTPAuth
```

Add to `app.py`:
```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

users = {
    "admin": "your_password_here"
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

# Add @auth.login_required decorator to routes:
@app.route('/')
@auth.login_required
def index():
    return render_template('index.html')
```

---

## Performance Tuning

### Increase Gunicorn Workers
Edit `run_production.sh` and change `--workers 4` to match CPU cores:
```bash
# Check CPU cores
nproc
# Set workers = (2 × cores) + 1
```

### Monitor Resource Usage
```bash
# CPU and memory
htop

# Disk usage
df -h

# Check USB stick if mounted
ls -la /media/pi/Lexar
```

---

## Updating the Application

```bash
cd /home/pi/Device-Connect/New/Enhancement
sudo systemctl stop device-test-server
git pull  # if using git
# Or upload new files via SCP
sudo systemctl start device-test-server
```

---

## Static IP Setup (Recommended)

To prevent IP address changes:

### Edit dhcpcd.conf
```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:
```
interface eth0  # or wlan0 for WiFi
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Reboot:
```bash
sudo reboot
```

---

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Start server | `sudo systemctl start device-test-server` |
| Stop server | `sudo systemctl stop device-test-server` |
| Restart server | `sudo systemctl restart device-test-server` |
| Check status | `sudo systemctl status device-test-server` |
| View logs | `sudo journalctl -u device-test-server -f` |
| Get IP address | `hostname -I` |
| Test locally | `curl http://localhost:5000` |

---

## Need Help?

Check logs for errors:
```bash
sudo journalctl -u device-test-server --no-pager -n 100
```
