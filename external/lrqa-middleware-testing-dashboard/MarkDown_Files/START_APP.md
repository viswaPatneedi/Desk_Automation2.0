# Application Startup Guide

## Quick Start (With Email Notifications)

**Recommended method** - Automatically enables email notifications:

```bash
./start_with_email.sh
```

This will:
- ✅ Load email configuration (SMTP settings)
- ✅ Start the Flask application on port 8080
- ✅ Enable automatic email notifications after test executions
- ✅ Run in background with logs in `app.log`

## Access URLs
- **Local**: http://localhost:8080
- **Network**: http://10.0.0.32:8080

## Email Configuration
The application sends automatic emails for:
1. **Test Execution Results** - Sent when jobs complete (success/failure)
2. **Password Reset Codes** - Sent when users request password resets

Email settings (already configured):
- SMTP Server: smtp.gmail.com:587
- Sender: cperdkemiddleware@gmail.com
- Authentication: Gmail App Password

## Monitoring

### View Logs
```bash
tail -f app.log
```

### Check Application Status
```bash
ps aux | grep "python.*app.py"
```

### Stop Application
```bash
pkill -f "python.*app.py"
```

## Troubleshooting

### Email Not Working?
Check if email service is enabled in startup logs:
```bash
grep "EMAIL SERVICE" app.log
```

Should show: `✅ Email Service: ENABLED`

If showing `⚠️ Email Service: DISABLED`, the environment variables weren't loaded. Use `./start_with_email.sh` instead of `python3 app.py`.

### Port Already in Use?
Stop existing processes:
```bash
pkill -f "python.*app.py"
sleep 2
./start_with_email.sh
```

### Check Email Configuration
```bash
./check_email_config.sh
```

## Alternative Startup Methods

### Without Email (Not Recommended)
```bash
python3 app.py
```
⚠️ Email notifications will be disabled

### With Custom Settings
```bash
export SMTP_SERVER='smtp.gmail.com'
export SMTP_PORT='587'
export SENDER_EMAIL='your-email@gmail.com'
export SENDER_PASSWORD='your-app-password'
python3 app.py
```

## Production Deployment

For systemd service with email enabled, see: `EMAIL_SETUP_GUIDE.md`
