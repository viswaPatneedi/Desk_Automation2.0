# RDK Device Testing Application - Access Information

## Application URLs

### Local Access (from the Pi itself)
- http://localhost:8080
- http://127.0.0.1:8080

### LAN Access (from any device on the same network)
- **By mDNS Hostname**: http://rdke-deskdevices-testing.local:8080
- **By IP Address**: http://10.0.0.32:8080

**Recommended**: Use http://rdke-deskdevices-testing.local:8080 for easier access (works on macOS, Linux, and Windows with Bonjour installed)

**Note**: The `.local` suffix is required for mDNS hostname resolution. If the hostname doesn't work, use the IP address http://10.0.0.32:8080 directly.

## Service Management

The application runs as a systemd service and will start automatically on boot.

### Service Commands
```bash
# Check service status
sudo systemctl status device-testing.service

# Start the service
sudo systemctl start device-testing.service

# Stop the service
sudo systemctl stop device-testing.service

# Restart the service
sudo systemctl restart device-testing.service

# View service logs
sudo journalctl -u device-testing.service -f

# Disable auto-start on boot
sudo systemctl disable device-testing.service

# Enable auto-start on boot
sudo systemctl enable device-testing.service
```

## Network Configuration

- **Hostname**: rdke-deskdevices-testing
- **mDNS Name**: rdke-deskdevices-testing.local
- **IP Address**: 10.0.0.32
- **Port**: 8080
- **Accessible from**: Any device on the LAN (10.0.0.x network)

## Requirements

✅ Python virtual environment: `/home/pi/Desktop/viswa-desktop/Latest_Enhancement/Enhancement/venv`
✅ Tesseract OCR: Installed at `/usr/bin/tesseract`
✅ All Python packages: Installed in virtual environment
✅ Systemd service: Configured and enabled

## Troubleshooting

If the application is not accessible:

1. Check if service is running:
   ```bash
   sudo systemctl status device-testing.service
   ```

2. Check if port is open:
   ```bash
   ss -tlnp | grep :8080
   ```

3. View recent logs:
   ```bash
   sudo journalctl -u device-testing.service -n 50
   ```

4. Restart the service:
   ```bash
   sudo systemctl restart device-testing.service
   ```

## Files Location

- **Application**: `/home/pi/Desktop/viswa-desktop/Latest_Enhancement/Enhancement/app.py`
- **Service File**: `/etc/systemd/system/device-testing.service`
- **Virtual Environment**: `/home/pi/Desktop/viswa-desktop/Latest_Enhancement/Enhancement/venv`
- **Logs**: Use `journalctl` command above

---
**Last Updated**: November 19, 2025
