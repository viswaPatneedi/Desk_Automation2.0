# Comcast Mail Relay Email Configuration Guide

## ✅ Configuration Updated!

The application has been configured to use **Comcast Mail Relay** by default for email notifications.

## Configuration Details

### Comcast Mail Relay Settings
```bash
SMTP_SERVER=mailrelay.comcast.com
SMTP_PORT=25
SENDER_EMAIL=viswachaithanya_patneedi@comcast.com
SENDER_PASSWORD=  # Not required for mail relay
```

### Key Features
- ✅ **No Authentication Required**: Internal mail relay doesn't need password
- ✅ **Port 25**: Standard SMTP port (no TLS encryption needed for internal relay)
- ✅ **Internal Use**: Works within Comcast network
- ✅ **Automatic Email Notifications**: Test results sent after job completion

## Updated Files

The following files have been updated to use Comcast mail relay:

1. **`.env.example`** - Updated with Comcast defaults (Option 1)
2. **`Dockerfile`** - Changed default SMTP to mailrelay.comcast.com
3. **`docker-compose.yml`** - Updated environment variables
4. **`app.py`** - Updated email service instructions
5. **`services/email_service.py`** - Modified to work without authentication for port 25
6. **`setup_email.sh`** - Updated Comcast option for mail relay

## Quick Setup Options

### Option 1: Using Environment Variables (Recommended)

```bash
# Set environment variables
export SMTP_SERVER='mailrelay.comcast.com'
export SMTP_PORT='25'
export SENDER_EMAIL='viswachaithanya_patneedi@comcast.com'
export SENDER_PASSWORD=''  # Empty for mail relay

# Start the application
python app.py
```

### Option 2: Using .env File

```bash
# Create .env file
cp .env.example .env

# The .env file is already configured with Comcast mail relay
# Just start the application
python app.py
```

### Option 3: Using setup_email.sh Script

```bash
# Run the interactive setup script
./setup_email.sh

# Choose option 2 for Comcast
# Follow the prompts
```

### Option 4: Docker Deployment

```bash
# The Docker image is already configured with Comcast defaults
# Just start the container
docker-compose up -d

# Or with explicit environment variables
docker run -d \
  -p 5000:5000 \
  -e SMTP_SERVER="mailrelay.comcast.com" \
  -e SMTP_PORT="25" \
  -e SENDER_EMAIL="viswachaithanya_patneedi@comcast.com" \
  --name rdk-testing \
  rdk-testing-dashboard:latest
```

## Testing Email Configuration

### Test 1: Using Python Test Script

```bash
# Run the Comcast mail relay test script
python test_comcast_mailrelay.py

# Enter recipient email when prompted
# Check inbox for test email
```

### Test 2: From Application

1. Start the application: `python app.py`
2. Check startup logs for email service status:
   ```
   ✅ Email Service: ENABLED
      SMTP Server: mailrelay.comcast.com:25
      Sender Email: viswachaithanya_patneedi@comcast.com
   ```
3. Run a test execution and check if email is received

### Test 3: Password Reset Email

1. Go to: http://localhost:5000/forgot-password
2. Enter your NTID and registered email
3. Check your inbox for the 6-digit verification code

## Email Types Supported

### 1. Password Reset Email
- **Trigger**: User requests password reset
- **Content**: 6-digit verification code (expires in 10 minutes)
- **Recipient**: User's registered email

### 2. Test Execution Results Email
- **Trigger**: Automatically sent after test execution completes
- **Content**: 
  - Device name and IP
  - Test methods executed
  - Pass/Fail status
  - Execution duration
  - Log file attachments
- **Recipient**: User who triggered the execution

## Technical Details

### Mail Relay vs SMTP Authentication

**Mail Relay (mailrelay.comcast.com:25)**
- ✅ No password required
- ✅ Works within Comcast internal network
- ✅ Port 25 (plain SMTP, no TLS)
- ✅ Simpler configuration
- ❌ May only work on Comcast network

**Gmail SMTP (smtp.gmail.com:587)**
- ✅ Works from anywhere with internet
- ✅ Encrypted (STARTTLS)
- ❌ Requires app-specific password
- ❌ More complex setup

### How the Application Handles Both

The `email_service.py` now intelligently handles both configurations:

```python
# Port 587 → Use STARTTLS and authentication (Gmail)
# Port 25  → Plain SMTP, no auth (Mail Relay)

if self.smtp_port == 587:
    server.starttls()
    if self.sender_password:
        server.login(self.sender_email, self.sender_password)
```

## Troubleshooting

### Email Service Shows as Disabled

**Check:**
```bash
# Verify environment variables are set
env | grep SMTP
env | grep SENDER

# Should show:
# SMTP_SERVER=mailrelay.comcast.com
# SMTP_PORT=25
# SENDER_EMAIL=viswachaithanya_patneedi@comcast.com
```

**Solution:**
```bash
export SENDER_EMAIL='viswachaithanya_patneedi@comcast.com'
python app.py
```

### Connection Refused Error

**Possible Causes:**
1. Not on Comcast internal network
2. Firewall blocking port 25
3. Mail relay server address incorrect

**Solution:**
```bash
# Test connectivity
telnet mailrelay.comcast.com 25

# If fails, check network/firewall
# Or switch to Gmail SMTP (option 1 in setup_email.sh)
```

### Emails Not Being Received

**Check:**
1. Spam/Junk folder
2. Email address is correct
3. Application logs for send confirmation
4. Run test script: `python test_comcast_mailrelay.py`

### Switch Back to Gmail

If you need to use Gmail SMTP instead:

```bash
# Option 1: Environment variables
export SMTP_SERVER='smtp.gmail.com'
export SMTP_PORT='587'
export SENDER_EMAIL='cperdkemiddleware@gmail.com'
export SENDER_PASSWORD='your-app-password'

# Option 2: Run setup script
./setup_email.sh
# Choose option 1 for Gmail

# Option 3: Edit .env file
nano .env
# Change SMTP settings to Gmail
```

## Production Deployment

### For Docker/Cloud Deployment

The Docker image is pre-configured with Comcast mail relay. To use in production:

```bash
# Docker Compose
docker-compose up -d

# Kubernetes
kubectl set env deployment/rdk-testing \
  SMTP_SERVER=mailrelay.comcast.com \
  SMTP_PORT=25 \
  SENDER_EMAIL=viswachaithanya_patneedi@comcast.com

# AWS ECS (task definition)
"environment": [
  {"name": "SMTP_SERVER", "value": "mailrelay.comcast.com"},
  {"name": "SMTP_PORT", "value": "25"},
  {"name": "SENDER_EMAIL", "value": "viswachaithanya_patneedi@comcast.com"}
]
```

### Network Requirements

For Comcast mail relay to work:
- ✅ Application must run within Comcast internal network
- ✅ Outbound port 25 must be open
- ✅ No authentication credentials needed

If deploying outside Comcast network, use Gmail SMTP (port 587) instead.

## Verification Checklist

- [ ] Environment variables set correctly
- [ ] Application starts without email errors
- [ ] Email service shows as ENABLED in startup logs
- [ ] Test email sends successfully (`test_comcast_mailrelay.py`)
- [ ] Password reset emails are received
- [ ] Test execution result emails are received
- [ ] Emails don't go to spam folder

## Support

For issues or questions:
1. Check application logs: `sudo journalctl -u device-testing.service -f`
2. Run test script: `python test_comcast_mailrelay.py`
3. Verify network connectivity to mailrelay.comcast.com
4. Check EMAIL_SERVICE_STATUS.md for additional troubleshooting

---

**Updated**: January 14, 2026  
**Default Configuration**: Comcast Mail Relay (mailrelay.comcast.com:25)  
**Sender**: viswachaithanya_patneedi@comcast.com
