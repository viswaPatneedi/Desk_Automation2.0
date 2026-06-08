# Password Reset Feature - Configuration Guide

## Overview
The password reset feature allows users to securely reset their passwords using email verification with a 6-digit code.

## How It Works

1. **User initiates reset**: User clicks "Forgot Password?" on login page
2. **Enter credentials**: User provides NTID and email address
3. **Email verification**: System validates NTID/email match and sends 6-digit code
4. **Code verification**: User enters the 6-digit code (valid for 10 minutes)
5. **Password reset**: User sets a new password with confirmation
6. **Login**: User logs in with new password

## Email Configuration

### Development Mode (Default)
By default, the application runs in development mode where:
- Email sending is simulated
- Verification codes are printed to the console
- No SMTP configuration needed

When a reset is requested, check the terminal/console for output like:
```
============================================================
PASSWORD RESET CODE FOR user@comcast.com: 123456
Code expires in 10 minutes
============================================================
```

### Production Mode (SMTP Email)
To enable actual email sending, configure these environment variables:

```bash
export SMTP_SERVER="smtp.gmail.com"           # Your SMTP server
export SMTP_PORT="587"                        # SMTP port (usually 587 for TLS)
export SENDER_EMAIL="noreply@comcast.com"     # Sender email address
export SENDER_PASSWORD="your-app-password"    # Email password or app password
```

#### Gmail Configuration Example:
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the app password in `SENDER_PASSWORD`

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="your-16-char-app-password"
```

#### Comcast/Corporate SMTP:
Contact your IT department for:
- SMTP server address
- SMTP port
- Authentication credentials
- Allowed sender addresses

## Security Features

1. **NTID + Email Validation**: Both must match to receive code
2. **Time-limited codes**: Codes expire after 10 minutes
3. **One-time use**: Codes are deleted after successful password reset
4. **No user enumeration**: Error messages don't reveal if account exists
5. **Password requirements**: Minimum 8 characters enforced
6. **Session-based flow**: Reset process tracked via Flask sessions

## Testing the Feature

### Test in Development Mode:
1. Start the application
2. Navigate to http://10.0.0.32:8080/login
3. Click "Forgot Password?"
4. Enter valid NTID and email (must exist in users.json)
5. Check terminal for the 6-digit code
6. Enter the code on verification page
7. Set a new password
8. Login with new password

### Test User:
```
NTID: vpatne290
Email: viswachaithanya_patneedi@comcast.com
```

## Files Modified

- `templates/login.html`: Added "Forgot Password?" link
- `templates/forgot_password.html`: New - NTID/Email entry form
- `templates/verify_code.html`: New - 6-digit code verification
- `templates/reset_password.html`: New - New password entry form
- `app.py`: Added routes and email sending logic
- `models/user.py`: Added `set_password()` and `save()` methods

## Routes

- `GET/POST /forgot-password`: Request password reset
- `GET/POST /verify-reset-code`: Verify 6-digit code
- `GET/POST /reset-password`: Set new password

## Troubleshooting

### Code not received in email:
1. Check console for development mode output
2. Verify SMTP environment variables are set correctly
3. Check email spam/junk folder
4. Verify sender email is allowed by SMTP server

### "Code expired" error:
- Codes expire after 10 minutes
- Request a new code from the forgot password page

### "Invalid code" error:
- Double-check the 6-digit code
- Codes are case-sensitive (numbers only)
- Request a new code if needed

### User not found:
- Ensure NTID and email exactly match what's in users.json
- Check for typos or extra spaces
- NTID is case-sensitive

## Future Enhancements

Potential improvements:
- Rate limiting to prevent abuse
- Email template customization
- SMS verification option
- Password strength requirements (complexity rules)
- Password history (prevent reuse)
- Account lockout after failed attempts
