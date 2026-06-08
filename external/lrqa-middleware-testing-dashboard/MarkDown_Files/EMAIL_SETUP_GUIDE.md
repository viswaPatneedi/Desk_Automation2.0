# Email Notification Setup Guide

## Overview
The LRQA MW Testing Dashboard now supports automated email notifications for:
1. **Password Reset OTP Codes** - Sends verification codes when users request password resets
2. **Test Execution Results** - Sends detailed results with log attachments when tests complete

## Email Configuration

### Gmail SMTP Settings
- **SMTP Server**: `smtp.gmail.com`
- **Port**: `587`
- **Email**: `cperdkemiddleware@gmail.com`
- **Authentication**: Requires Gmail App Password

### Quick Setup

#### Option 1: Interactive Configuration (Recommended)
```bash
./configure_gmail_smtp.sh
```

This script will:
- Prompt for your Gmail app password
- Configure environment variables
- Set up systemd service for production

#### Option 2: Manual Configuration
```bash
export SMTP_SERVER='smtp.gmail.com'
export SMTP_PORT='587'
export SENDER_EMAIL='cperdkemiddleware@gmail.com'
export SENDER_PASSWORD='your-16-char-app-password'
```

#### Option 3: Systemd Service (Production)
```bash
sudo mkdir -p /etc/systemd/system/device-testing.service.d
sudo nano /etc/systemd/system/device-testing.service.d/email.conf
```

Add:
```ini
[Service]
Environment="SMTP_SERVER=smtp.gmail.com"
Environment="SMTP_PORT=587"
Environment="SENDER_EMAIL=cperdkemiddleware@gmail.com"
Environment="SENDER_PASSWORD=your-app-password"
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart device-testing
```

## Gmail App Password Setup

### Step 1: Enable 2-Step Verification
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Sign in with `cperdkemiddleware@gmail.com`
3. Find **"2-Step Verification"** and turn it ON
4. Follow the prompts to set it up with your phone

### Step 2: Create App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Sign in if prompted
3. Select **"Mail"** as the app
4. Select **"Other (Custom name)"** as the device
5. Enter: **"LRQA Testing Dashboard"**
6. Click **Generate**
7. Copy the **16-character password** (e.g., `abcd efgh ijkl mnop`)
8. Remove spaces when using: `abcdefghijklmnop`

## Features

### 1. Password Reset Emails
When a user requests a password reset:
- **Recipient**: User's registered email
- **Subject**: "Password Reset Code - LRQA MW Testing Dashboard"
- **Content**: 6-digit verification code
- **Expiry**: Code expires in 10 minutes
- **Format**: HTML email with plain text fallback

### 2. Execution Results Emails
When a test execution completes:
- **Recipient**: User who triggered the execution
- **Subject**: "Test Execution Complete - [Device Name]"
- **Content**:
  - Job ID and status (✅ Completed / ❌ Failed)
  - Device name and IP
  - Sequence name (if applicable)
  - Methods executed (in order with → separator)
  - Number of iterations
  - Execution duration
  - Completion timestamp
- **Attachments**: 
  - Job execution logs
  - Iteration logs (up to 5MB total)

## Testing Email Configuration

### Test SMTP Connection
```bash
python3 test_smtp_connection.py
```

This will:
1. Connect to SMTP server
2. Enable TLS encryption
3. Authenticate with credentials
4. Send a test email to yourself
5. Confirm all tests passed

### Test Password Reset Email
1. Go to the login page
2. Click "Forgot Password?"
3. Enter your NTID and email
4. Check your inbox for the verification code

### Test Execution Results Email
1. Run any test execution from the dashboard
2. Wait for execution to complete
3. Check your inbox for the results email with attachments

## Troubleshooting

### Email Not Sending
1. **Check configuration**:
   ```bash
   ./check_email_config.sh
   ```

2. **Verify app password**:
   - Make sure you're using the 16-character app password, not your regular Gmail password
   - Remove any spaces from the app password

3. **Test SMTP connection**:
   ```bash
   python3 test_smtp_connection.py
   ```

4. **Check application logs**:
   ```bash
   tail -f logs/app.log
   ```

### Common Errors

#### "Authentication failed (535)"
- Using regular password instead of app password
- App password is incorrect
- 2-Step Verification not enabled

#### "Connection timeout"
- Firewall blocking port 587
- Network connectivity issue
- SMTP server address incorrect

#### "Email not configured (dev mode)"
- `SENDER_PASSWORD` environment variable not set
- Emails will be logged to console instead

## Email Service Architecture

### Files Modified/Created
1. **services/email_service.py** - New email service with methods:
   - `send_password_reset_email()` - Password reset functionality
   - `send_execution_results_email()` - Test results with attachments
   - `_send_email()` - Internal SMTP handler

2. **app.py** - Updated `send_reset_email()` to use email service

3. **services/test_execution_service.py** - Added:
   - `_send_completion_email()` - Sends email on job completion/failure
   - Integration points in job completion and error handling

### Email Flow

#### Password Reset:
```
User requests reset → Generate OTP code → Send email → User enters code → Password reset
```

#### Execution Results:
```
Test completes → Job status updated → Collect logs → Send email with attachments → User receives notification
```

## Security Notes

- **Never commit passwords to git** - Environment variables only
- **App passwords are safer** - Limited scope, can be revoked
- **Email in production** - Use systemd environment files with restricted permissions:
  ```bash
  sudo chmod 600 /etc/systemd/system/device-testing.service.d/email.conf
  ```

## User Email Resolution

Emails are sent to the registered email address of the user who:
- **Password Reset**: The user requesting the reset
- **Execution Results**: The user who triggered the test execution (identified by `job.user_id`)

Users must register with a valid `@comcast.com` or `@cable.comcast.com` email address.

## Development Mode

If `SENDER_PASSWORD` is not configured:
- Emails will not be sent via SMTP
- Password reset codes will be printed to console
- Execution completion will be logged but no email sent
- Useful for development without email credentials

## Production Checklist

- [ ] Gmail App Password created
- [ ] Environment variables configured in systemd service
- [ ] SMTP connection tested successfully
- [ ] Test password reset email received
- [ ] Test execution results email received with attachments
- [ ] Service restarted: `sudo systemctl restart device-testing`
- [ ] Email configuration file permissions secured: `chmod 600`

## Support

For issues with email configuration:
1. Check console output for detailed error messages
2. Review SMTP test results
3. Verify Gmail app password is correct
4. Ensure 2-Step Verification is enabled
5. Contact IT if corporate firewall blocks SMTP

---
**Last Updated**: December 17, 2025
**Email Configured**: cperdkemiddleware@gmail.com
