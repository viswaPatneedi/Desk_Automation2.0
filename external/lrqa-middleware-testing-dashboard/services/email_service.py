"""
Email Service - Handles all email notifications
"""
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional, List
import time


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
        from config.config_email import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, EMAIL_ENABLED
      except Exception:
        SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, EMAIL_ENABLED = (
          'mailrelay.comcast.com', 25, '', '', True
        )

      self.smtp_server = os.environ.get('SMTP_SERVER', SMTP_SERVER)
      self.smtp_port = int(os.environ.get('SMTP_PORT', SMTP_PORT))
      self.sender_email = os.environ.get('SENDER_EMAIL', SENDER_EMAIL)
      self.sender_password = os.environ.get('SENDER_PASSWORD', SENDER_PASSWORD)
      # Port 25 relay needs no password; authenticated SMTP (587) does
      self.enabled = bool(EMAIL_ENABLED and self.sender_email and
                          (self.smtp_port != 587 or self.sender_password))
      
      # Threading lock to ensure thread-safe operations
      self._lock = threading.Lock()
    
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
        
        Sends email in a background thread to avoid blocking job completion.
        
        Includes:
          - Device name and IP
          - Method(s) executed  
          - Iterations (completed/total)
          - Pass/Failed status
          - Execution duration
          - Log file attachments
        """
        # Send in background thread to not block job completion
        thread = threading.Thread(
            target=self._send_execution_results_email_async,
            args=(recipient_email, job_data, log_file_paths),
            daemon=True
        )
        thread.start()
        
        # Return immediately - email is being sent in background
        return True, "Email queued for delivery (sending in background)"
    
    def _send_execution_results_email_async(self, recipient_email: str, job_data: dict, 
                                           log_file_paths: List[str] = None):
        """
        Async implementation of send_execution_results_email
        Runs in a background thread
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
                    
                    <!-- ✅ ENHANCEMENT 3: Performance Metrics -->
                    {self.generate_performance_metrics_html(job_data)}
                    
                    <!-- ✅ ENHANCEMENT 1: AI Analysis Section -->
                    {self._generate_ai_analysis_html(job_data)}
                    
                    <!-- ✅ ENHANCEMENT 2: Validation Warnings -->
                    {self._generate_validation_warnings_html(job_data)}
                    
                    <!-- ✅ ENHANCEMENT 5: Progress Timeline -->
                    {self._generate_progress_timeline_html(job_data)}
                    
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
            
            # Send email in async thread (this method is already running in a thread)
            success, message = self._send_email(msg, recipient_email)
            
            if success:
                print(f"✅ [ASYNC] Execution results email sent to {recipient_email}")
            else:
                print(f"❌ [ASYNC] Failed to send email to {recipient_email}: {message}")
        
        except Exception as e:
            print(f"❌ [ASYNC] Error sending execution results email: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_email(self, msg: MIMEMultipart, recipient: str) -> tuple:
        """Internal method to send email via SMTP with retry logic"""
        if not self.enabled:
            print(f"⚠️ Email not configured. Would have sent to: {recipient}")
            print(f"   Subject: {msg['Subject']}")
            return False, "Email not configured"
        
        # Retry configuration
        max_retries = 3
        retry_delays = [2, 5, 10]  # seconds between retries
        timeout_seconds = 30  # Increased from 10 to 30 seconds for more stable connection
        
        for attempt in range(max_retries):
            try:
                print(f"📧 [ATTEMPT {attempt + 1}/{max_retries}] Connecting to {self.smtp_server}:{self.smtp_port} (timeout={timeout_seconds}s)")
                
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout_seconds) as server:
                    # Only use STARTTLS and authentication for secure SMTP (port 587)
                    # Mail relay servers (port 25) typically don't require authentication
                    if self.smtp_port == 587:
                        print(f"📧 Starting TLS encryption...")
                        server.starttls()
                        if self.sender_password:
                            print(f"📧 Authenticating with {self.sender_email}...")
                            server.login(self.sender_email, self.sender_password)
                    
                    print(f"📧 Sending message to {recipient}...")
                    server.send_message(msg)
                
                print(f"✅ Email sent successfully to {recipient}")
                print(f"   Server: {self.smtp_server}:{self.smtp_port}")
                return True, "Email sent successfully"
            
            except (OSError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
                # Network/connection errors - retry
                error_msg = f"Connection error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}"
                print(f"⚠️  {error_msg}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    print(f"⏳ Retrying in {wait_time} seconds...")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    return False, error_msg
            
            except smtplib.SMTPAuthenticationError as e:
                error_msg = f"SMTP Authentication failed: {e}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            except smtplib.SMTPException as e:
                error_msg = f"SMTP error: {e}"
                print(f"❌ {error_msg}")
                return False, error_msg
            
            except Exception as e:
                error_msg = f"Unexpected error sending email: {type(e).__name__}: {e}"
                print(f"❌ {error_msg}")
                return False, error_msg
        
        return False, "Failed to send email after all retry attempts"
    
    def send_custom_html_email(self, subject: str, html_content: str, recipient_email: str = None) -> tuple:
        """Send a custom HTML email (for recovery reports, etc.)"""
        try:
            # Use configured sender email if recipient not specified
            if not recipient_email:
                recipient_email = self.sender_email
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'LRQA Testing Dashboard <{self.sender_email}>'
            msg['To'] = recipient_email
            
            # Create plain text version
            text = f"Email body: see HTML version"
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            return self._send_email(msg, recipient_email)
        except Exception as e:
            print(f"Error sending custom email: {e}")
            return False, str(e)
    
    def test_smtp_connection(self) -> tuple:
        """
        Test SMTP connection without sending an email
        Useful for diagnosing configuration issues
        
        Returns:
            (success: bool, message: str)
        """
        print("\n" + "="*60)
        print("SMTP CONNECTION TEST")
        print("="*60)
        
        if not self.enabled:
            msg = "Email service is disabled (missing SENDER_EMAIL or SENDER_PASSWORD)"
            print(f"⚠️  {msg}")
            return False, msg
        
        print(f"Testing connection to: {self.smtp_server}:{self.smtp_port}")
        print(f"Auth Email: {self.sender_email}")
        print(f"Timeout: 30 seconds")
        print("-"*60)
        
        try:
            print("Establishing connection...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                print(f"✅ Connected to {self.smtp_server}:{self.smtp_port}")
                
                if self.smtp_port == 587:
                    print("Starting TLS encryption...")
                    server.starttls()
                    print("✅ TLS enabled")
                    
                    if self.sender_password:
                        print(f"Authenticating with {self.sender_email}...")
                        server.login(self.sender_email, self.sender_password)
                        print("✅ Authentication successful")
                
                print("\n✅ SMTP connection test PASSED")
                print("="*60 + "\n")
                return True, "SMTP connection successful"
        
        except smtplib.SMTPAuthenticationError as e:
            msg = f"SMTP Authentication failed: {e}\n❌ Check your email credentials (SENDER_EMAIL, SENDER_PASSWORD)"
            print(f"\n❌ {msg}")
            print("="*60 + "\n")
            return False, msg
        
        except TimeoutError as e:
            msg = f"Connection timeout: {e}\n❌ Cannot reach {self.smtp_server}:{self.smtp_port}\nCheck network connectivity and firewall settings"
            print(f"\n❌ {msg}")
            print("="*60 + "\n")
            return False, msg
        
        except smtplib.SMTPException as e:
            msg = f"SMTP error: {e}"
            print(f"\n❌ {msg}")
            print("="*60 + "\n")
            return False, msg
        
        except Exception as e:
            msg = f"Connection failed: {type(e).__name__}: {e}"
            print(f"\n❌ {msg}")
            print("="*60 + "\n")
            return False, msg
    
    # ============================================================
    # ENHANCEMENT 1: AI-POWERED FAILURE ANALYSIS
    # ============================================================
    def analyze_execution_failure_with_ai(self, job_data: dict, log_content: str = "") -> dict:
        """
        Use Claude/Gemini API to analyze failed executions and generate insights
        
        Returns:
          {
            'root_cause': 'Most likely cause of failure',
            'recommendations': ['Action 1', 'Action 2'],
            'severity': 'critical|warning|info',
            'error_pattern': 'Common pattern if detected'
          }
        """
        try:
            import google.generativeai as genai
        except ImportError:
            genai = None
        
        if not genai:
            return {'error': 'AI analysis not available'}
        
        try:
            # Prepare failure context
            failure_context = f"""
Execution Analysis Request:

Device: {job_data.get('device_name', 'Unknown')}
Status: {job_data.get('status', 'unknown')}
Methods: {', '.join(job_data.get('methods', []))}
Failed Iterations: {job_data.get('failed_iterations', 'N/A')}
Error Message: {job_data.get('error_message', 'No error details')}

Recent Logs:
{log_content[:1000] if log_content else 'No logs available'}

Please provide:
1. Root cause analysis (1-2 sentences)
2. 3 recommended actions to fix this
3. Severity level (critical/warning/info)
4. Any error patterns detected
            """
            
            # Call Gemini API
            genai.configure(api_key=os.environ.get('GOOGLE_API_KEY', ''))
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(failure_context)
            
            # Parse response
            analysis_text = response.text
            
            # Extract structured data
            result = {
                'root_cause': self._extract_section(analysis_text, 'Root cause', 'analysis'),
                'recommendations': self._extract_list(analysis_text, 'recommended'),
                'severity': 'warning',  # Default
                'error_pattern': self._extract_section(analysis_text, 'pattern', 'analysis')
            }
            
            return result
        except Exception as e:
            print(f"[AI ANALYSIS] Error analyzing failure: {e}")
            return {'error': str(e)}
    
    def _extract_section(self, text: str, keyword: str, context_type: str = "line") -> str:
        """Extract relevant section from AI analysis"""
        lines = text.split('\n')
        for line in lines:
            if keyword.lower() in line.lower():
                return line.strip()
        return "Unable to extract analysis"
    
    def _extract_list(self, text: str, keyword: str) -> list:
        """Extract list items from AI analysis"""
        lines = text.split('\n')
        items = []
        capture = False
        for line in lines:
            if keyword.lower() in line.lower():
                capture = True
                continue
            if capture:
                if line.strip().startswith(('1.', '2.', '3.', '-', '•')):
                    items.append(line.strip().lstrip('12345.-• '))
                elif line.strip() == '':
                    break
        return items[:3]  # Return top 3
    
    # ============================================================
    # ENHANCEMENT 2: EXECUTION VALIDATION
    # ============================================================
    def validate_execution_before_email(self, job_data: dict) -> dict:
        """
        Validate execution outcomes before sending email
        
        Returns:
          {
            'is_valid': bool,
            'validation_checks': {...},
            'warnings': [],
            'data_integrity': 'healthy|degraded|corrupted'
          }
        """
        validation_result = {
            'is_valid': True,
            'validation_checks': {},
            'warnings': [],
            'data_integrity': 'healthy'
        }
        
        try:
            # Check 1: Data completeness
            required_fields = ['job_id', 'device_name', 'status', 'start_time', 'end_time']
            missing_fields = [f for f in required_fields if not job_data.get(f)]
            validation_result['validation_checks']['data_completeness'] = len(missing_fields) == 0
            if missing_fields:
                validation_result['warnings'].append(f"Missing fields: {', '.join(missing_fields)}")
            
            # Check 2: Status validity
            valid_statuses = ['completed', 'failed', 'cancelled', 'interrupted']
            status_valid = job_data.get('status') in valid_statuses
            validation_result['validation_checks']['status_valid'] = status_valid
            if not status_valid:
                validation_result['warnings'].append(f"Unknown status: {job_data.get('status')}")
            
            # Check 3: Iterations consistency
            total_iterations = job_data.get('iterations', 0)
            completed_iterations = job_data.get('iterations_completed', 0)
            consistency_ok = completed_iterations <= total_iterations
            validation_result['validation_checks']['iteration_consistency'] = consistency_ok
            if not consistency_ok:
                validation_result['warnings'].append("Iteration count inconsistency detected")
                validation_result['data_integrity'] = 'degraded'
            
            # Check 4: Timestamp validity
            try:
                from datetime import datetime
                start = datetime.fromisoformat(job_data.get('start_time', '').replace('Z', '+00:00'))
                end = datetime.fromisoformat(job_data.get('end_time', '').replace('Z', '+00:00'))
                timestamp_valid = end >= start
                validation_result['validation_checks']['timestamp_valid'] = timestamp_valid
                if not timestamp_valid:
                    validation_result['warnings'].append("End time before start time")
            except:
                validation_result['validation_checks']['timestamp_valid'] = False
                validation_result['warnings'].append("Invalid timestamp format")
            
            # Overall decision
            validation_result['is_valid'] = all(validation_result['validation_checks'].values())
            
            if validation_result['warnings']:
                print(f"[VALIDATION] {len(validation_result['warnings'])} warnings: {validation_result['warnings']}")
            
            return validation_result
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['data_integrity'] = 'corrupted'
            validation_result['warnings'].append(f"Validation error: {str(e)}")
            return validation_result
    
    # ============================================================
    # ENHANCEMENT 3: PERFORMANCE METRICS & FORMATTING
    # ============================================================
    def generate_performance_metrics_html(self, job_data: dict) -> str:
        """
        Generate visual performance metrics for email
        Include ASCII charts and progress indicators
        """
        try:
            iterations = job_data.get('iterations', 0)
            completed = job_data.get('iterations_completed', 0)
            passed = job_data.get('passed_count', 0)
            failed = job_data.get('failed_count', 0)
            
            # Calculate percentages
            completion_pct = (completed / iterations * 100) if iterations > 0 else 0
            success_pct = (passed / completed * 100) if completed > 0 else 0
            
            # Build progress bar
            bar_length = 30
            filled = int(bar_length * completion_pct / 100)
            progress_bar = '█' * filled + '░' * (bar_length - filled)
            
            # Build success bar
            success_filled = int(bar_length * success_pct / 100)
            success_bar = '✓' * success_filled + '✗' * (bar_length - success_filled)
            
            html = f"""
            <h3 style="color: #4b5563; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 30px;">
              📈 Performance Metrics
            </h3>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
              <tr>
                <td style="padding: 15px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold; width: 40%;">
                  ⏳ Completion Rate
                </td>
                <td style="padding: 15px; border: 1px solid #e5e7eb;">
                  <div style="background: #e5e7eb; border-radius: 20px; padding: 5px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #3b82f6 0%, #10b981 100%); width: {completion_pct}%; height: 25px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">
                      {completion_pct:.1f}%
                    </div>
                  </div>
                  <span style="font-size: 12px; color: #6b7280;">{completed} / {iterations} iterations</span>
                </td>
              </tr>
              
              <tr>
                <td style="padding: 15px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                  ✅ Success Rate
                </td>
                <td style="padding: 15px; border: 1px solid #e5e7eb;">
                  <div style="background: #e5e7eb; border-radius: 20px; padding: 5px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #10b981 0%, #059669 100%); width: {success_pct}%; height: 25px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">
                      {success_pct:.1f}%
                    </div>
                  </div>
                  <span style="font-size: 12px; color: #6b7280;">{passed} passed, {failed} failed</span>
                </td>
              </tr>
            </table>
            
            <div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin: 20px 0; font-family: monospace; font-size: 12px; line-height: 1.8;">
              <div><strong>Completion:</strong> {progress_bar} {completion_pct:.0f}%</div>
              <div><strong>Success:</strong> {success_bar} {success_pct:.0f}%</div>
            </div>
            """
            
            return html
        except Exception as e:
            print(f"[METRICS] Error generating metrics: {e}")
            return ""
    
    # ============================================================
    # ENHANCEMENT 4: SMART NOTIFICATION FILTERING
    # ============================================================
    def should_send_notification(self, job_data: dict, config: dict = None) -> tuple:
        """
        Determine if email should be sent based on execution type and configured rules
        
        Returns: (should_send: bool, reason: str)
        
        Default rules:
        - Always send on failures
        - Send on completion only if EMAIL_ON_COMPLETION enabled
        - Skip routine tests if SUPPRESS_ROUTINE_NOTIFICATIONS enabled
        - Track as important event if involved device is frequently failing
        """
        config = config or {}
        should_send = True
        reason = ""
        
        status = job_data.get('status', 'unknown')
        
        # Rule 1: Always send on failure
        if status == 'failed':
            reason = "Sent automatically - execution failed"
            return True, reason
        
        # Rule 2: Check completion notification setting
        from config.config_email import EMAIL_ON_COMPLETION
        if status == 'completed' and not EMAIL_ON_COMPLETION:
            reason = "Notification skipped - EMAIL_ON_COMPLETION disabled"
            return False, reason
        
        # Rule 3: Suppress routine tests (optional)
        suppress_routine = config.get('SUPPRESS_ROUTINE', False)
        if suppress_routine and job_data.get('is_routine_test', False):
            reason = "Notification skipped - routine test suppression enabled"
            return False, reason
        
        # Rule 4: Mark important if high failure rate on device
        device_name = job_data.get('device_name', '')
        failed_count = job_data.get('failed_count', 0)
        total_iterations = job_data.get('iterations', 1)
        failure_rate = (failed_count / total_iterations) if total_iterations > 0 else 0
        
        if failure_rate > 0.5:  # >50% failure rate = important
            job_data['is_important_event'] = True
            reason += " [⚠️ HIGH FAILURE RATE on " + device_name + "]"
        
        return should_send, reason
    
    # ============================================================
    # ENHANCEMENT 5: ADVANCED PROGRESS TRACKING
    # ============================================================
    def track_execution_progress(self, job_data: dict, tracking_history: dict = None) -> dict:
        """
        Track execution progress over time for real-time monitoring
        
        Returns progress timeline with:
        - Iteration-by-iteration results
        - Time elapsed
        - Estimated time remaining
        - Performance trend
        """
        tracking_history = tracking_history or {}
        
        try:
            job_id = job_data.get('job_id', 'unknown')
            current_iteration = job_data.get('current_iteration', 0)
            total_iterations = job_data.get('iterations', 0)
            start_time = job_data.get('start_time', '')
            current_time = datetime.now(datetime.timezone.utc).isoformat()
            
            # Calculate time metrics
            try:
                from datetime import datetime as dt, timezone
                start_dt = dt.fromisoformat(start_time.replace('Z', '+00:00'))
                current_dt = dt.fromisoformat(current_time.replace('Z', '+00:00'))
                elapsed = (current_dt - start_dt).total_seconds()
                
                # Estimate remaining time
                if current_iteration > 0:
                    avg_per_iteration = elapsed / current_iteration
                    remaining = avg_per_iteration * (total_iterations - current_iteration)
                else:
                    remaining = 0
                    
            except:
                elapsed = 0
                remaining = 0
            
            progress_snapshot = {
                'timestamp': current_time,
                'iteration': f"{current_iteration}/{total_iterations}",
                'elapsed_seconds': elapsed,
                'estimated_remaining_seconds': remaining,
                'iteration_results': job_data.get('iteration_results', {})
            }
            
            # Store in history
            if job_id not in tracking_history:
                tracking_history[job_id] = []
            tracking_history[job_id].append(progress_snapshot)
            
            return {
                'current_progress': progress_snapshot,
                'progress_history': tracking_history.get(job_id, [])
            }
        except Exception as e:
            print(f"[PROGRESS TRACKING] Error: {e}")
            return {'error': str(e)}
    
    # ============================================================
    # HELPER METHODS FOR EMAIL HTML GENERATION
    # ============================================================
    def _generate_ai_analysis_html(self, job_data: dict) -> str:
        """Generate AI analysis section for email"""
        try:
            ai_analysis = job_data.get('ai_analysis', {})
            if not ai_analysis or 'error' in ai_analysis:
                return ""
            
            recommendations = ai_analysis.get('recommendations', [])
            if not recommendations:
                return ""
            
            rec_html = "".join([f"<li style=\"margin: 8px 0; color: #374151;\">{rec}</li>" for rec in recommendations[:3]])
            
            html = f"""
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
              <h3 style="color: #92400e; margin-top: 0; font-size: 16px;">🤖 AI-Powered Analysis</h3>
              <p style="color: #78350f; margin: 10px 0;"><strong>Root Cause:</strong> {ai_analysis.get('root_cause', 'Analysis unavailable')}</p>
              <p style="color: #78350f; margin: 10px 0;"><strong>Recommendations:</strong></p>
              <ul style="color: #78350f; margin: 10px 0;">{rec_html}</ul>
            </div>
            """
            return html
        except Exception as e:
            print(f"[EMAIL] Error generating AI analysis HTML: {e}")
            return ""
    
    def _generate_validation_warnings_html(self, job_data: dict) -> str:
        """Generate validation warnings section"""
        try:
            validation = self.validate_execution_before_email(job_data)
            warnings = validation.get('warnings', [])
            
            if not warnings:
                return ""
            
            warning_items = "".join([f"<li style=\"margin: 5px 0; color: #dc2626;\">⚠️ {w}</li>" for w in warnings])
            
            html = f"""
            <div style="background: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; border-radius: 4px;">
              <h3 style="color: #7f1d1d; margin-top: 0; font-size: 16px;">⚠️ Data Integrity Warnings</h3>
              <p style="color: #7f1d1d; font-size: 13px; margin: 0;"><strong>Status:</strong> {validation.get('data_integrity', 'unknown').upper()}</p>
              <ul style="color: #7f1d1d; margin: 10px 0; font-size: 13px;">{warning_items}</ul>
            </div>
            """
            return html
        except Exception as e:
            print(f"[EMAIL] Error generating warnings HTML: {e}")
            return ""
    
    def _generate_progress_timeline_html(self, job_data: dict) -> str:
        """Generate progress timeline section"""
        try:
            progress_info = job_data.get('progress_info', {})
            if 'error' in progress_info or not progress_info:
                return ""
            
            current_progress = progress_info.get('current_progress', {})
            elapsed = current_progress.get('elapsed_seconds', 0)
            remaining = current_progress.get('estimated_remaining_seconds', 0)
            
            elapsed_str = self._format_duration(elapsed)
            remaining_str = self._format_duration(remaining)
            
            html = f"""
            <h3 style="color: #4b5563; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 30px;">
              ⏱️ Execution Timeline
            </h3>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
              <tr>
                <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold; width: 35%;">
                  ⏱️ Time Elapsed
                </td>
                <td style="padding: 12px; border: 1px solid #e5e7eb;">
                  <strong>{elapsed_str}</strong>
                </td>
              </tr>
              <tr>
                <td style="padding: 12px; background: #f3f4f6; border: 1px solid #e5e7eb; font-weight: bold;">
                  🕐 Est. Remaining
                </td>
                <td style="padding: 12px; border: 1px solid #e5e7eb;">
                  <strong>{remaining_str}</strong>
                </td>
              </tr>
            </table>
            """
            return html
        except Exception as e:
            print(f"[EMAIL] Error generating progress HTML: {e}")
            return ""
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable format"""
        try:
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                secs = int(seconds % 60)
                return f"{minutes}m {secs}s"
            else:
                hours = int(seconds / 3600)
                minutes = int((seconds % 3600) / 60)
                return f"{hours}h {minutes}m"
        except:
            return "N/A"
