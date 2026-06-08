"""
Email Service - Handles all email notifications
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional, List


class EmailService:
    """
    Centralized Email Service - Automatically sends emails during execution
    
    **UNIFIED CONFIGURATION:** All email types use the SAME SMTP settings
    Environment Variables:
      - SMTP_SERVER: SMTP server address (default: smtp.gmail.com)
      - SMTP_PORT: SMTP port (default: 587)
      - SENDER_EMAIL: Sender email address
      - SENDER_PASSWORD: App-specific password (required for Gmail)
    
    Email Types:
      1. Password Reset Email - send_password_reset_email()
      2. Execution Results Email - send_execution_results_email()
         (Automatically triggered after each execution completes)
    
    This service is integrated with test_execution_service and runs
    automatically when jobs complete. No manual triggering required.
    """
    
    def __init__(self):
      # SINGLE EMAIL CONFIGURATION - Shared by all email types
      try:
        from config_email import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, EMAIL_ENABLED
      except Exception:
        SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, EMAIL_ENABLED = (
          'smtp.gmail.com', 587, '', '', True
        )

      self.smtp_server = os.environ.get('SMTP_SERVER', SMTP_SERVER)
      self.smtp_port = int(os.environ.get('SMTP_PORT', SMTP_PORT))
      self.sender_email = os.environ.get('SENDER_EMAIL', SENDER_EMAIL)
      self.sender_password = os.environ.get('SENDER_PASSWORD', SENDER_PASSWORD)
      # Enable email only when Gmail SMTP is fully configured
      self.enabled = bool(EMAIL_ENABLED and self.sender_email and self.sender_password)
    
    def send_password_reset_email(self, recipient_email: str, code: str, name: str) -> tuple:
        """Send password reset email with 6-digit code"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Password Reset Code - LRQA MW Testing Dashboard'
            msg['From'] = f'LRQA Testing Dashboard <{self.sender_email}>'
            msg['To'] = recipient_email
            
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #4b5563;">Password Reset Request</h2>
                  <p>Hello {name},</p>
                  <p>You requested to reset your password for the LRQA MW Testing Dashboard.</p>
                  <p>Your verification code is:</p>
                  <div style="background: #f3f4f6; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                    <h1 style="color: #1f2937; letter-spacing: 8px; margin: 0; font-size: 36px;">{code}</h1>
                  </div>
                  <p style="color: #dc2626; font-weight: bold;">This code will expire in 10 minutes.</p>
                  <p>If you didn't request this password reset, please ignore this email.</p>
                  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                  <p style="color: #6b7280; font-size: 12px;">
                    LRQA MW Testing Dashboard<br>
                    This is an automated message, please do not reply.
                  </p>
                </div>
              </body>
            </html>
            """
            
            text = f"""
            Password Reset Request
            
            Hello {name},
            
            You requested to reset your password for the LRQA MW Testing Dashboard.
            Your verification code is: {code}
            
            This code will expire in 10 minutes.
            
            ---
            LRQA MW Testing Dashboard
            """
            
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            return self._send_email(msg, recipient_email)
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False, str(e)
    
    def send_execution_results_email(self, recipient_email: str, job_data: dict, 
                                    log_file_paths: List[str] = None) -> tuple:
        """
        Send test execution results email - AUTOMATICALLY TRIGGERED after execution
        
        Includes:
          - Device name and IP
          - Method(s) executed  
          - Iterations (completed/total)
          - Pass/Failed status
          - Execution duration
          - Log file attachments
        """
        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f'Test Execution Complete - {job_data.get("device_name", "Device")}'
            msg['From'] = f'LRQA Testing Dashboard <{self.sender_email}>'
            msg['To'] = recipient_email
            
            # Extract job information
            job_id = job_data.get('job_id', 'Unknown')
            device_name = job_data.get('device_name', 'Unknown Device')
            device_ip = job_data.get('device_ip', 'Unknown IP')
            methods = job_data.get('methods', [])
            status = job_data.get('status', 'unknown')
            start_time = job_data.get('start_time', '')
            end_time = job_data.get('end_time', '')
            iterations = job_data.get('iterations', 0)
            iterations_completed = job_data.get('iterations_completed', iterations)
            sequence_name = job_data.get('sequence_name')
            
            # Format methods list
            if isinstance(methods, list):
                methods_str = ' → '.join(methods[:3])  # Show first 3
                if len(methods) > 3:
                    methods_str += f' + {len(methods) - 3} more'
            else:
                methods_str = str(methods)
            
            # Format execution time
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = end_dt - start_dt
                duration_str = str(duration).split('.')[0]  # Remove microseconds
            except:
                duration_str = "N/A"
            
            # Determine Pass/Fail status
            is_passed = status == "completed"
            is_failed = status == "failed"
            status_icon = "✅" if is_passed else ("❌" if is_failed else "⏸️")
            status_color = "#10b981" if is_passed else ("#ef4444" if is_failed else "#f59e0b")
            status_text = "PASSED" if is_passed else ("FAILED" if is_failed else "CANCELLED")
            
            # Process iteration results
            iteration_results = job_data.get('iteration_results', {})
            passed_count = sum(1 for result in iteration_results.values() if result == 'passed')
            failed_count = sum(1 for result in iteration_results.values() if result == 'failed')
            failed_iterations = [num for num, result in sorted(iteration_results.items(), key=lambda x: int(x[0])) if result == 'failed']
            
            # Build iteration status HTML
            iteration_status_html = ""
            if iteration_results:
                iteration_status_html = f"""
                <h3 style="color: #4b5563; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 30px;">
                  🔄 Iteration Results
                </h3>
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                  <tr>
                    <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold; width: 35%;">
                      ✅ Passed
                    </td>
                    <td style="padding: 12px; border: 1px solid #e5e7eb;">
                      <strong style="color: #10b981; font-size: 18px;">{passed_count} / {iterations}</strong>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                      ❌ Failed
                    </td>
                    <td style="padding: 12px; border: 1px solid #e5e7eb;">
                      <strong style="color: #ef4444; font-size: 18px;">{failed_count} / {iterations}</strong>
                    </td>
                  </tr>
                  {f'''<tr>
                    <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                      ⚠️ Failed Iterations
                    </td>
                    <td style="padding: 12px; border: 1px solid #e5e7eb;">
                      <span style="color: #ef4444; font-weight: bold;">{', '.join(failed_iterations)}</span>
                    </td>
                  </tr>''' if failed_iterations else ''}
                </table>
                """
            
            # Build HTML body
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 700px; margin: 0 auto; padding: 20px; background: #f9fafb;">
                  <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #1f2937; margin-top: 0;">
                      {status_icon} Test Execution Report
                    </h2>
                    
                    <div style="background: {status_color}; color: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                      <h1 style="margin: 0; font-size: 36px; font-weight: bold;">{status_text}</h1>
                      <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">Execution Result</p>
                    </div>
                    
                    <h3 style="color: #4b5563; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">📊 Execution Summary</h3>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold; width: 35%;">
                          🆔 Job ID
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          <code style="background: #f9fafb; padding: 4px 8px; border-radius: 4px; font-size: 13px;">{job_id}</code>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                          📱 Device
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          <strong>{device_name}</strong><br/>
                          <span style="color: #6b7280; font-size: 13px;">IP: {device_ip}</span>
                        </td>
                      </tr>
                      {'<tr><td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">📋 Sequence</td><td style="padding: 12px; border: 1px solid #e5e7eb;"><strong>' + sequence_name + '</strong></td></tr>' if sequence_name else ''}
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                          🎯 Method(s)
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          {methods_str}
                        </td>
                      </tr>
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                          🔄 Iterations
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          <strong>{iterations_completed} / {iterations}</strong> completed
                        </td>
                      </tr>
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                          ⏱️ Duration
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          {duration_str}
                        </td>
                      </tr>
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                          {status_icon} Result
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          <strong style="color: {status_color}; font-size: 16px;">{status_text}</strong>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                          📅 Completed At
                        </td>
                        <td style="padding: 12px; border: 1px solid #e5e7eb;">
                          {end_time.replace('T', ' ').split('.')[0] if end_time else 'N/A'}
                        </td>
                      </tr>
                    </table>
                    
                    {iteration_status_html}
                    
                    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; border-radius: 4px;">
                      <p style="margin: 0; color: #1e40af;">
                        <strong>📋 Note:</strong> Detailed execution logs are attached to this email.
                      </p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                    
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">
                      LRQA MW Testing Dashboard<br>
                      Automated Test Execution System<br>
                      This is an automated message, please do not reply.
                    </p>
                  </div>
                </div>
              </body>
            </html>
            """
            
            # Plain text version
            text = f"""
{'='*60}
TEST EXECUTION REPORT
{'='*60}

{status_icon} RESULT: {status_text}

{'-'*60}
EXECUTION SUMMARY
{'-'*60}

Job ID:           {job_id}
Device:           {device_name} ({device_ip})
{'Sequence:         ' + sequence_name if sequence_name else ''}
Method(s):        {methods_str}
Iterations:       {iterations_completed} / {iterations} completed
Duration:         {duration_str}
Result:           {status_text}
Completed At:     {end_time.replace('T', ' ').split('.')[0] if end_time else 'N/A'}

{'-'*60}

Detailed execution logs are attached to this email.

{'='*60}
LRQA MW Testing Dashboard - Automated Test Execution System
This email was sent automatically after execution completed.
{'='*60}
            """
            
            # Attach text and HTML parts
            msg_alternative = MIMEMultipart('alternative')
            msg_alternative.attach(MIMEText(text, 'plain'))
            msg_alternative.attach(MIMEText(html, 'html'))
            msg.attach(msg_alternative)
            
            # Attach log files if provided
            if log_file_paths:
                for log_file_path in log_file_paths:
                    if os.path.exists(log_file_path):
                        try:
                            with open(log_file_path, 'rb') as f:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(f.read())
                                encoders.encode_base64(part)
                                filename = os.path.basename(log_file_path)
                                part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                                msg.attach(part)
                        except Exception as e:
                            print(f"Warning: Could not attach log file {log_file_path}: {e}")
            
            return self._send_email(msg, recipient_email)
        
        except Exception as e:
            print(f"Error sending execution results email: {e}")
            return False, str(e)
    
    def _send_email(self, msg: MIMEMultipart, recipient: str) -> tuple:
        """Internal method to send email via SMTP"""
        if not self.enabled:
            print(f"⚠️ Email not configured. Would have sent to: {recipient}")
            print(f"   Subject: {msg['Subject']}")
            return True, "Email not configured (dev mode)"
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                # Only use STARTTLS and authentication for secure SMTP (port 587)
                # Mail relay servers (port 25) typically don't require authentication
                if self.smtp_port == 587:
                    server.starttls()
                    if self.sender_password:
                        server.login(self.sender_email, self.sender_password)
                
                server.send_message(msg)
            
            print(f"✅ Email sent successfully to {recipient}")
            print(f"   Server: {self.smtp_server}:{self.smtp_port}")
            return True, "Email sent successfully"
        
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error sending email: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
