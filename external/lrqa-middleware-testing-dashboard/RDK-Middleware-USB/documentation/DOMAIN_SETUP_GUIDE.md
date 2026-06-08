# Domain Name Setup Guide for RDK Testing Dashboard

This guide covers setting up domain-based access for the RDK Testing Dashboard instead of using IP addresses.

## Table of Contents
1. [DNS Configuration](#dns-configuration)
2. [Non-Kubernetes Setup (Nginx)](#non-kubernetes-setup)
3. [Kubernetes Setup (Ingress)](#kubernetes-setup)
4. [Local Testing](#local-testing)
5. [SSL/TLS Setup](#ssltls-setup)

---

## DNS Configuration

### Option 1: Public Domain (Recommended for Production)

If you own a domain (e.g., `yourdomain.com`):

1. **Log into your DNS provider** (GoDaddy, Cloudflare, Namecheap, etc.)

2. **Add an A record**:
   ```
   Type: A
   Name: rdk-testing (or subdomain of your choice)
   Value: YOUR_SERVER_IP (e.g., 192.168.1.100)
   TTL: 3600 (1 hour)
   ```

3. **Wait for DNS propagation** (5 minutes to 48 hours, usually ~10 minutes)

4. **Verify DNS**:
   ```bash
   # Check if domain resolves to your IP
   nslookup rdk-testing.yourdomain.com
   dig rdk-testing.yourdomain.com
   ```

### Option 2: Local Network Domain (Internal Use)

For local network access only:

1. **Configure your router's DNS** or local DNS server
2. Add entry: `rdk-testing.local -> YOUR_RASPBERRY_PI_IP`
3. Or use mDNS: `rdk-testing.local` (if Avahi/Bonjour enabled)

### Option 3: Hosts File (Testing Only)

For quick local testing without DNS:

**Linux/Mac** (`/etc/hosts`):
```bash
sudo nano /etc/hosts
# Add this line:
192.168.1.100  rdk-testing.yourdomain.com
```

**Windows** (`C:\Windows\System32\drivers\etc\hosts`):
```
# Open as Administrator and add:
192.168.1.100  rdk-testing.yourdomain.com
```

---

## Non-Kubernetes Setup (Nginx Reverse Proxy)

### Automated Setup

Use the provided script:

```bash
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement
./setup_domain.sh
```

The script will:
- Install Nginx if not present
- Configure reverse proxy
- Optionally setup SSL with Let's Encrypt
- Enable the site

### Manual Setup

1. **Install Nginx**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y nginx
   ```

2. **Create Nginx configuration**:
   ```bash
   sudo nano /etc/nginx/sites-available/rdk-testing
   ```

   Add the configuration from `nginx/rdk-testing.conf` (update domain name)

3. **Enable the site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/rdk-testing /etc/nginx/sites-enabled/
   sudo rm /etc/nginx/sites-enabled/default  # Remove default site
   ```

4. **Test and restart**:
   ```bash
   sudo nginx -t
   sudo systemctl restart nginx
   sudo systemctl enable nginx
   ```

5. **Access your application**:
   ```
   http://rdk-testing.yourdomain.com
   ```

---

## Kubernetes Setup (Ingress)

### Prerequisites

- Kubernetes cluster with Ingress controller installed
- Domain DNS pointing to your cluster's ingress IP

### Install Ingress Controller (if not already installed)

**Nginx Ingress Controller**:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/cloud/deploy.yaml
```

**Or for bare-metal**:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/baremetal/deploy.yaml
```

### Configure Ingress

1. **Update the ingress manifest**:
   ```bash
   nano kubernetes/ingress.yaml
   ```

   Change the host:
   ```yaml
   spec:
     rules:
     - host: rdk-testing.yourdomain.com  # Your domain here
   ```

2. **Apply the ingress**:
   ```bash
   kubectl apply -f kubernetes/ingress.yaml
   ```

3. **Get ingress IP**:
   ```bash
   kubectl get ingress -n rdk-testing
   # Or for LoadBalancer service
   kubectl get svc -n ingress-nginx
   ```

4. **Update DNS** to point to the ingress IP

5. **Access your application**:
   ```
   http://rdk-testing.yourdomain.com
   ```

---

## Local Testing

### Using hosts file

Before DNS propagates or for private networks:

1. **Find your server IP**:
   ```bash
   hostname -I
   # or
   ip addr show
   ```

2. **Edit hosts file**:
   
   **Linux/Mac**:
   ```bash
   sudo nano /etc/hosts
   ```
   
   **Windows** (as Administrator):
   ```
   notepad C:\Windows\System32\drivers\etc\hosts
   ```

3. **Add entry**:
   ```
   192.168.1.100  rdk-testing.yourdomain.com
   ```

4. **Test**:
   ```bash
   ping rdk-testing.yourdomain.com
   curl http://rdk-testing.yourdomain.com
   ```

### Using local domain

For Raspberry Pi with Avahi (mDNS):

```bash
# Install Avahi if not present
sudo apt-get install avahi-daemon

# Access using .local domain
http://pi-desktop.local:5000
# or configure custom hostname
```

---

## SSL/TLS Setup

### Option 1: Let's Encrypt (Free, Automated)

**For Nginx (Non-Kubernetes)**:

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate and auto-configure nginx
sudo certbot --nginx -d rdk-testing.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Setup auto-renewal (usually pre-configured)
sudo systemctl enable certbot.timer
```

**For Kubernetes with cert-manager**:

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Update ingress.yaml with TLS and annotation
# Then apply: kubectl apply -f kubernetes/ingress.yaml
```

### Option 2: Self-Signed Certificate (Development)

```bash
# Generate certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/rdk-testing.key \
  -out /etc/ssl/certs/rdk-testing.crt \
  -subj "/CN=rdk-testing.yourdomain.com"

# Update nginx configuration to use certificate
sudo nano /etc/nginx/sites-available/rdk-testing
# Uncomment HTTPS server block and update paths

# Restart nginx
sudo systemctl restart nginx
```

---

## Verification

### Test Domain Access

```bash
# Check DNS resolution
nslookup rdk-testing.yourdomain.com
dig rdk-testing.yourdomain.com

# Test HTTP connection
curl -I http://rdk-testing.yourdomain.com

# Test HTTPS (if SSL enabled)
curl -I https://rdk-testing.yourdomain.com

# Check from browser
# Open: http://rdk-testing.yourdomain.com
```

### Common Issues

**1. Domain doesn't resolve**:
- Check DNS records in your provider
- Wait for DNS propagation (up to 48h)
- Use `dig` or `nslookup` to verify
- Try flushing DNS cache: `sudo systemd-resolve --flush-caches`

**2. Connection refused**:
- Check if nginx is running: `sudo systemctl status nginx`
- Check if Flask app is running: `sudo systemctl status rdk-testing.service`
- Check firewall: `sudo ufw status`
- Check nginx logs: `sudo tail -f /var/log/nginx/error.log`

**3. SSL certificate issues**:
- Ensure domain points to your server
- Check certbot logs: `sudo journalctl -u certbot`
- Verify certificate: `sudo certbot certificates`
- Check nginx SSL config: `sudo nginx -t`

**4. 502 Bad Gateway**:
- Flask app not running or crashed
- Check app logs: `sudo journalctl -u rdk-testing.service -f`
- Verify proxy_pass URL in nginx config

---

## Port Configuration

### Open Required Ports

```bash
# For HTTP
sudo ufw allow 80/tcp

# For HTTPS
sudo ufw allow 443/tcp

# For SSH (if needed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

### Check Open Ports

```bash
# Check what's listening
sudo netstat -tulpn | grep LISTEN

# Or with ss
sudo ss -tulpn | grep LISTEN
```

---

## Production Recommendations

1. **Use a real domain** from a registrar (GoDaddy, Namecheap, Cloudflare)
2. **Enable SSL/TLS** with Let's Encrypt (free)
3. **Configure firewall** to only allow 80, 443, and SSH
4. **Setup monitoring** for certificate expiry
5. **Use CloudFlare** for DDoS protection and CDN (optional)
6. **Regular backups** of SSL certificates and configurations
7. **Monitor logs** for security issues

---

## Quick Commands Reference

```bash
# Check nginx status
sudo systemctl status nginx

# Restart nginx
sudo systemctl restart nginx

# Test nginx config
sudo nginx -t

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Renew SSL certificate
sudo certbot renew

# Check SSL expiry
sudo certbot certificates

# Get server IP
hostname -I

# Check DNS
nslookup your-domain.com
dig your-domain.com

# Test domain access
curl -I http://your-domain.com
curl -I https://your-domain.com
```

---

## Support

For domain-specific issues:
1. Verify DNS propagation: https://dnschecker.org
2. Check SSL status: https://www.ssllabs.com/ssltest/
3. Review nginx documentation: https://nginx.org/en/docs/
4. Let's Encrypt docs: https://letsencrypt.org/docs/
