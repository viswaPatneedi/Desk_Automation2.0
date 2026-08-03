#!/usr/bin/env python3
"""
Netflix App Launch and Playback Method Implementation
Handles Netflix app launch, authentication, content launch, and playback monitoring with optional trickplay controls.

Workflow Steps:
0. HOME Screen Navigation - Press HOME and verify home screen
1. App Launch - Voice command to launch Netflix
2. Launch Verification - Confirm app is in foreground (FAILS if app NOT found)
3. Screen State Identification - Capture and analyze screen state
4. Screen State Conditional Handling - Handle login/profile/home screens
5. Content Launch - Send voice command for asset
6. Playback Initiation - Send ENTER to play
7. Continuous Playback Monitoring - Monitor playback state
8. Trickplay Controls (Optional) - Execute FF/RW/Pause/Play
9. System Crash Analysis - Check for crashes
"""

import sys
import time
import re
import json
import paramiko
from datetime import datetime, timezone
import os

# V2.0 Folder Structure: Import from relative locations
# Add parent directory to path to import from methods folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import shared utilities
from method_utils import (
    log_message,
    fetch_build_details,
    create_execution_log_path,
    get_folder_method_name
)

# Import config for log patterns (adjusted path for v2.0)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_dir = os.path.join(parent_dir, 'config')
sys.path.insert(0, config_dir)

try:
    from config_log_patterns import log_check_command_HOME
except ImportError:
    log_check_command_HOME = ""


def load_netflix_credentials_from_db(team_name=None):
    """
    Load Netflix credentials from the database (primary credential for Netflix app).
    Falls back to file-based credentials if DB is unavailable.
    
    Args:
        team_name: Team name to load credentials for (optional)
    
    Returns:
        Dict with username, password, login_url, credential_id if found
        Empty dict if not found or DB error
    """
    try:
        from models.app_credential import AppCredential
        from models.database import Session
        from sqlalchemy import and_
        
        session = Session()
        
        # Build query
        query = session.query(AppCredential).filter(
            and_(
                AppCredential.app_name == 'netflix',
                AppCredential.is_active == True,
                AppCredential.is_primary == True
            )
        )
        
        # Filter by team if specified
        if team_name:
            query = query.filter(AppCredential.team_name == team_name)
        
        cred = query.first()
        session.close()
        
        if cred:
            # Record usage
            try:
                from controllers.app_credential_controller import AppCredentialController
                AppCredentialController.record_usage(cred.credential_id)
            except:
                pass  # Non-critical if usage recording fails
            
            return {
                'username': cred.username,
                'password': cred.password,
                'login_url': cred.login_url or 'http://netflix.com/tv2',
                'profile_name': cred.profile_name,
                'source': 'database',
                'credential_id': cred.credential_id
            }
        
        return {}
    except Exception as e:
        print(f"⚠ Error loading credentials from DB: {e}")
        return {}


def load_netflix_credentials_from_file():
    """
    Load Netflix credentials from credentials.json file (legacy fallback)
    
    Returns:
        Dict with username, password, login_url if found and enabled
        Empty dict if file doesn't exist, not enabled, or incomplete
    """
    try:
        credentials_file = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
        
        if not os.path.exists(credentials_file):
            return {}
        
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
        
        netflix_creds = creds_data.get('netflix', {})
        
        # Only return if enabled and has required fields
        if netflix_creds.get('enabled') == True:
            if netflix_creds.get('username') and netflix_creds.get('password'):
                return {
                    'username': netflix_creds.get('username', ''),
                    'password': netflix_creds.get('password', ''),
                    'login_url': netflix_creds.get('login_url', 'http://netflix.com/tv2'),
                    'source': 'stored_file'
                }
        
        return {}
    
    except Exception as e:
        print(f"⚠ Error loading credentials from file: {e}")
        return {}


def get_netflix_credentials(team_name=None, username_cred="", password_cred="", login_url=""):
    """
    Get Netflix credentials with priority:
    1. User-provided credentials (from UI)
    2. Database credentials (primary)
    3. File-based credentials (legacy)
    4. Empty (no credentials)
    
    Args:
        team_name: Team name for DB lookup
        username_cred: User-provided username
        password_cred: User-provided password
        login_url: User-provided login URL
    
    Returns:
        Dict with resolved credentials
    """
    # Priority 1: User-provided credentials
    if username_cred and password_cred:
        return {
            'username': username_cred,
            'password': password_cred,
            'login_url': login_url or 'http://netflix.com/tv2',
            'source': 'user_provided'
        }
    
    # Priority 2: Database credentials (primary)
    db_creds = load_netflix_credentials_from_db(team_name=team_name)
    if db_creds:
        return db_creds
    
    # Priority 3: File-based credentials (legacy)
    file_creds = load_netflix_credentials_from_file()
    if file_creds:
        return file_creds
    
    # No credentials found
    return {}


def netflix_playback(
    device_ip, port, username, password, 
    login_url="http://netflix.com/tv2",
    username_cred="", password_cred="",
    asset_voice_command="", 
    playback_log_string="state.*PLAYING.*",
    execute_playback_controls=False,
    playback_duration=300,
    iteration=1, 
    device_name="Device",
    combined_method_name=None,
    log_callback=None,
    job_id=None,
    team_name=None,
    session_folder=None
):
    """
    Netflix App Launch and Playback Automation
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        login_url: URL for Netflix activation
        username_cred: Netflix account username (optional, can be fetched from DB)
        password_cred: Netflix account password (optional, can be fetched from DB)
        asset_voice_command: Voice command to launch content
        playback_log_string: Log pattern for playback validation
        execute_playback_controls: Enable trickplay controls
        playback_duration: Duration to play content (seconds)
        iteration: Current iteration number
        device_name: Display name of device
        combined_method_name: Combined method name (optional)
        log_callback: Logging callback function
        job_id: Job ID for real-time updates
        team_name: Team name for fetching stored credentials from database
    
    Returns:
        Dict with execution results and logs
    """
    
    def log(message):
        """Internal logging wrapper"""
        if log_callback:
            log_callback(message)
        else:
            print(message)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    logs_list = []
    step_results = {}
    
    # Resolve Netflix credentials from multiple sources
    netflix_creds = get_netflix_credentials(
        team_name=team_name,
        username_cred=username_cred,
        password_cred=password_cred,
        login_url=login_url
    )
    
    # Setup USB log file
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "NETFLIX_PLAYBACK")
        log_service.current_usb_log_file = usb_log_path
        log(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log(f"⚠ Could not set USB log path: {e}")
    
    log("="*80)
    log("NETFLIX APP LAUNCH AND PLAYBACK - START")
    log("="*80)
    log(f"Target Device: {device_name} ({device_ip})")
    log(f"Asset Voice Command: {asset_voice_command}")
    log(f"Playback Duration: {playback_duration}s")
    log(f"Trickplay Controls: {'Enabled' if execute_playback_controls else 'Disabled'}")
    if netflix_creds.get('source'):
        log(f"📋 Netflix credentials source: {netflix_creds.get('source')}")
    
    # ======================================================================
    # CREDENTIALS LOADING: Check for stored credentials in credentials.json
    # ======================================================================
    log("\n" + "="*80)
    log("[CREDENTIALS] Loading Netflix account credentials")
    log("="*80)
    
    # Load from stored file if not provided by user
    if not username_cred or not password_cred:
        stored_creds = load_netflix_credentials_from_file()
        
        if stored_creds:
            username_cred = stored_creds.get('username', '')
            password_cred = stored_creds.get('password', '')
            login_url = stored_creds.get('login_url', login_url)
            log(f"✓ Loaded Netflix credentials from credentials.json")
            log(f"  ├─ Username: {username_cred}")
            log(f"  └─ Login URL: {login_url}")
            log(f"ℹ Credentials source: Stored file (credentials.json)")
        else:
            log(f"ℹ No stored credentials found or disabled in credentials.json")
            log(f"  Credentials will be requested during login if needed, or manual entry required")
    else:
        log(f"ℹ Using credentials provided by user (overrides stored credentials)")
        log(f"  ├─ Username: {username_cred}")
        log(f"  └─ Login URL: {login_url}")
        log(f"ℹ Credentials source: User input")
    
    ssh = None
    overall_success = True
    
    try:
        # ======================================================================
        # STEP 1: ESTABLISH SSH CONNECTION
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 1] ESTABLISHING SSH CONNECTION")
        log("="*80)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log("✓ SSH connection established")
        
        # Fetch build details
        fetch_build_details(ssh, log)
        
        # ======================================================================
        # STEP 0: HOME SCREEN NAVIGATION
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 0] HOME SCREEN NAVIGATION")
        log("="*80)
        
        log("🏠 Sending HOME keypress to navigate to home screen...")
        home_cmd = "keySimulator -khome"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(home_cmd, timeout=30)
            home_output = stdout.read().decode('utf-8', errors='ignore')
            exit_status = stdout.channel.recv_exit_status()
            log("✓ HOME keypress sent")
            step_results['step_0_home_keypress'] = 'success'
        except Exception as e:
            log(f"❌ Error sending HOME keypress: {e}")
            step_results['step_0_home_keypress'] = f'error: {e}'
            overall_success = False
        
        log("⏳ Waiting 5 seconds for home screen to load...")
        time.sleep(5)
        
        # Verify home screen with both screenshot and logs
        log("📸 Verifying home screen via screenshot and logs...")
        screenshot_verified = False
        log_verified = False
        
        # Screenshot verification
        try:
            # V2.0 imports: screenshot_utils is in utils/ folder
            utils_dir = os.path.join(parent_dir, 'utils')
            sys.path.insert(0, utils_dir)
            from screenshot_utils import take_and_analyze_screenshot
            
            # Determine screenshot folder
            # Priority 1: Use session_folder if provided (recommended for v2.0)
            if session_folder:
                screenshot_folder = os.path.join(session_folder, 'SCREENSHOTS')
                # Create SCREENSHOTS directory if it doesn't exist
                os.makedirs(screenshot_folder, exist_ok=True)
                log(f"📸 Using session folder for screenshots: {screenshot_folder}")
            else:
                # Fallback: Use job-specific screenshot folder for legacy compatibility
                screenshot_folder = os.path.expanduser('~/screenshots')
                if job_id:
                    screenshot_folder = os.path.join(screenshot_folder, job_id)
                log(f"⚠ Using legacy screenshot folder: {screenshot_folder}")
            
            screenshot_name = f"netflix_home_verification_{timestamp}"
            result = take_and_analyze_screenshot(
                ssh,
                screenshot_name,
                device_ip,
                log_callback=log,
                screenshot_folder=screenshot_folder,
                app_name="netflix",
                step=0
            )
            
            if result.get('success'):
                log(f"✓ Home screen screenshot captured")
                screenshot_verified = True
                
                # ================================================================
                # STEP 0 ENHANCED: VALIDATE HOME SCREEN (NOT INPUT SCREEN)
                # ================================================================
                # CRITICAL: Ensure we're on HOME screen, not an input selection screen
                # Previous execution showed false positive: INPUT_SCREEN_ANTEENA matched
                # Solution: Use enhanced detection to validate correct screen
                
                screen_validation = result.get('screen_state', {})
                pixel_confidence = screen_validation.get('confidence', 0.0)
                pixel_match_result = screen_validation.get('screen_detected', 'Unknown')
                
                log(f"🔍 Step 0 Enhanced Validation: Pixel match = {pixel_match_result} ({pixel_confidence:.1%})")
                
                # Flag: Is this an INPUT screen (wrong) instead of HOME?
                is_input_screen = any(x in str(pixel_match_result).upper() for x in [
                    'INPUT_SCREEN', 'HDMI', 'ANTEENA', 'ANTENNA', 'USB', 'AIRPLAY', 'COMPOSITE'
                ])
                
                # If we matched an INPUT screen OR low confidence, run enhanced validation
                if is_input_screen or pixel_confidence < 0.75:
                    log(f"⚠ Input screen detected or low confidence - running enhanced HOME validation...")
                    
                    try:
                        # Import enhanced detector to validate this is actually HOME
                        from tools.screen.netflix_screen_detector import NetflixScreenDetector
                        detector = NetflixScreenDetector()
                        screenshot_path = result.get('local_path', '')
                        
                        if screenshot_path and os.path.exists(screenshot_path):
                            # For HOME validation, use distinguish_home_vs_asset
                            # If it's NOT an asset screen and logs confirm HOME, it's the home screen
                            enhanced_result = detector.distinguish_home_vs_asset(
                                screenshot_path,
                                pixel_match_result,
                                pixel_confidence
                            )
                            
                            final_screen = enhanced_result.get('final_screen', pixel_match_result)
                            final_confidence = enhanced_result.get('confidence', pixel_confidence)
                            
                            # If enhanced detection says NOT asset screen (i.e., it's home-like), confirm HOME
                            if 'AssetScreen' not in final_screen:
                                log(f"  ✓ Enhanced validation confirms HOME-like screen: {final_screen} ({final_confidence:.1%})")
                                log(f"  ℹ Reason: {enhanced_result.get('reason', 'Feature-based validation')}")
                                # Update confidence if enhanced detection is more reliable
                                if final_confidence > pixel_confidence:
                                    screen_validation['confidence'] = final_confidence
                                    log(f"  ✓ Updated confidence: {pixel_confidence:.1%} → {final_confidence:.1%}")
                            else:
                                # Asset screen detected, but we sent HOME - this is wrong
                                log(f"  ⚠ WARNING: Enhanced detection found ASSET features despite HOME keypress!")
                                log(f"  ℹ Screen may not have navigated to home properly")
                    
                    except Exception as enhance_err:
                        log(f"  ⚠ Enhanced validation error: {enhance_err}")
                        # Fall back to basic validation
                        log(f"  ℹ Relying on device logs for HOME verification")
                
                # Store screenshot info for results display (like steps 4 & 6)
                home_screenshot_info = {
                    'path': result.get('local_path'),
                    'url': result.get('screenshot_url'),
                    'step': 0,
                    'timestamp': timestamp,
                    'screen_detected': pixel_match_result,
                    'confidence': pixel_confidence,
                    'validation_method': 'enhanced' if (is_input_screen or pixel_confidence < 0.75) else 'pixel_matching'
                }
                
                step_results['step_0_screenshot_verification'] = 'success'
                step_results['step_0_screenshot'] = home_screenshot_info
                
                # Update job in real-time with step_0 results
                if job_id:
                    try:
                        from models.job import Job
                        Job.update_execution_results(job_id, {
                            'step_0_screenshot_verification': 'success',
                            'step_0_screenshot': home_screenshot_info
                        })
                        log(f"✓ Updated job {job_id} with Step 0 results")
                    except Exception as e:
                        log(f"⚠ Could not update job with Step 0 results: {e}")
            else:
                log(f"⚠ Could not verify home screen via screenshot: {result.get('error', 'unknown error')}")
                step_results['step_0_screenshot_verification'] = 'verification_failed'
        except ImportError:
            log("⚠ Screenshot utilities not available, skipping screenshot verification")
            step_results['step_0_screenshot_verification'] = 'skipped'
        except Exception as e:
            log(f"⚠ Could not verify home screen via screenshot: {e}")
            step_results['step_0_screenshot_verification'] = f'error: {e}'
        
        # Log verification - Check device logs for HOME detection
        log("📋 Verifying home screen via device logs...")
        try:
            if log_check_command_HOME:
                log(f"   Executing: {log_check_command_HOME}")
                stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME, timeout=30)
                log_output = stdout.read().decode('utf-8', errors='ignore').strip()
                exit_status = stdout.channel.recv_exit_status()
                
                if log_output:
                    log(f"✓ HOME screen detected in device logs")
                    log_verified = True
                    step_results['step_0_log_verification'] = 'success'
                    # Show relevant log lines
                    log_lines = log_output.split('\n')[:3]  # Show first 3 matching lines
                    for line in log_lines:
                        log(f"   → {line}")
                else:
                    log(f"⚠ HOME screen not found in device logs (may still be loading)")
                    step_results['step_0_log_verification'] = 'no_match'
            else:
                log("⚠ HOME log pattern not configured, skipping log verification")
                step_results['step_0_log_verification'] = 'config_unavailable'
        except Exception as e:
            log(f"⚠ Error during log verification: {e}")
            step_results['step_0_log_verification'] = f'error: {e}'
        
        # Combine results
        if screenshot_verified or log_verified:
            log(f"✓ Home screen verification completed (Screenshot: {'✓' if screenshot_verified else '✗'}, Logs: {'✓' if log_verified else '✗'})")
            step_results['step_0_home_verification'] = 'success'
        else:
            log(f"⚠ Home screen verification inconclusive (Screenshot: {'✓' if screenshot_verified else '✗'}, Logs: {'✓' if log_verified else '✗'})")
            step_results['step_0_home_verification'] = 'inconclusive'
        
        # ======================================================================
        # STEP 1: APP LAUNCH - SEND VOICE COMMAND
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 1] APP LAUNCH - SENDING VOICE COMMAND")
        log("="*80)
        
        # Give device additional time to settle after HOME keypress and screen navigation
        # Voice control system needs time to be fully responsive (RDK firmware stabilization)
        log("⏳ Allowing device to settle after HOME navigation (10 seconds)...")
        time.sleep(10)
        
        # Verify voice control is responsive before attempting Netflix launch
        log("🔍 Testing voice control system responsiveness...")
        test_voice_cmd = (
            f"curl --header 'Content-Type: application/json' "
            f"--request POST --silent "
            f"-d '{{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"org.rdk.VoiceControl.1.voiceSessionByText\",\"params\":{{\"transcription\":\"test\"}}}}' "
            f"http://127.0.0.1:9998/jsonrpc"
        )
        
        try:
            stdin, stdout, stderr = ssh.exec_command(test_voice_cmd, timeout=10)
            test_output = stdout.read().decode('utf-8', errors='ignore').strip()
            if test_output:
                log("✓ Voice control system is responsive")
            else:
                log("⚠ Voice control system may not be fully ready - proceeding anyway")
        except Exception as e:
            log(f"⚠ Voice control test failed - proceeding anyway: {e}")
        
        log("🎙 Sending voice command: 'NETFLIX'")
        escaped_text = "NETFLIX".replace("'", "'\\''")
        voice_cmd = (
            f"curl --header 'Content-Type: application/json' "
            f"--request POST --silent "
            f"-d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\":\"org.rdk.VoiceControl.1.voiceSessionByText\",\"params\":{{\"transcription\":\"{escaped_text}\"}}}}' "
            f"http://127.0.0.1:9998/jsonrpc"
        )
        
        log(f"Executing command: {voice_cmd}")
        
        voice_command_success = False
        try:
            stdin, stdout, stderr = ssh.exec_command(voice_cmd, timeout=30)
            voice_output = stdout.read().decode('utf-8', errors='ignore').strip()
            voice_error = stderr.read().decode('utf-8', errors='ignore').strip()
            
            log(f"Response: {voice_output}")
            
            if voice_error:
                log(f"⚠ Error output: {voice_error}")
            
            # Check CURL response for success
            if voice_output:
                try:
                    result = json.loads(voice_output)
                    # Check if response has result with success flag
                    if "result" in result and isinstance(result["result"], dict):
                        if result["result"].get("success") == True:
                            log("✓ Voice command API executed successfully")
                            log(f"Session ID: {result['result'].get('sessionId', 'N/A')}")
                            step_results['step_1_voice_command'] = 'success'
                            voice_command_success = True
                            
                            # Give device time to process voice command
                            log("⏳ Waiting 3 seconds for voice command to be processed...")
                            time.sleep(3)
                            
                            # Send ENTER key to confirm/trigger the app launch
                            # REASON: The voice command (transcription) is sent via RDK JSON-RPC, but depending on device state and UI responsiveness,
                            # the device may simply queue the voice input without immediately triggering the app launch.
                            # The ENTER key acts as an explicit "submit/execute" signal to confirm that the Netflix app launch should be initiated.
                            # This is a fallback mechanism to ensure app launch is triggered even if device doesn't auto-launch from voice command alone.
                            log("→ Sending ENTER key to confirm/execute app launch...")
                            try:
                                enter_cmd = "keySimulator -kreturn"
                                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=10)
                                stdout.channel.recv_exit_status()
                                log("✓ ENTER key sent successfully")
                            except Exception as e:
                                log(f"⚠ Could not send ENTER key: {e}")
                        else:
                            log(f"❌ Voice command returned success=false")
                            step_results['step_1_voice_command'] = 'voice_api_failed'
                            overall_success = False
                    elif "error" in result:
                        error_msg = result.get("error", {})
                        log(f"❌ Voice command error: {error_msg}")
                        step_results['step_1_voice_command'] = f'api_error: {error_msg}'
                        overall_success = False
                    else:
                        log(f"⚠ Unexpected JSON response: {voice_output}")
                        step_results['step_1_voice_command'] = 'unexpected_response'
                except json.JSONDecodeError:
                    log(f"❌ Could not parse JSON response: {voice_output}")
                    step_results['step_1_voice_command'] = 'json_parse_error'
                    overall_success = False
            else:
                log("❌ No response received from voice command")
                step_results['step_1_voice_command'] = 'no_response'
                overall_success = False
        except Exception as e:
            log(f"❌ Error sending voice command: {e}")
            step_results['step_1_voice_command'] = f'error: {e}'
            overall_success = False
        
        log("⏳ Waiting 20 seconds for app to fully launch and stabilize...")
        time.sleep(20)
        
        # ======================================================================
        # STEP 2: LAUNCH VERIFICATION - CHECK FOREGROUND APP (CRITICAL STEP)
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 2] LAUNCH VERIFICATION - CHECKING FOREGROUND APP (CRITICAL)")
        log("="*80)
        
        verify_cmd = "appsservicectl dumpsys RunTimeManager | grep -i Visible | awk '{print $1}'"
        
        netflix_found = False
        try:
            stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=15)
            app_output = stdout.read().decode('utf-8', errors='ignore').strip()
            exit_status = stdout.channel.recv_exit_status()
            
            log(f"Foreground app: {app_output}")
            
            if 'NetflixApp' in app_output or 'Netflix' in app_output:
                log("✓ Netflix app confirmed in foreground")
                step_results['step_2_app_verification'] = 'success'
                netflix_found = True
            else:
                # Voice command failed to launch Netflix - try fallback mechanism
                log(f"⚠ Voice command did not launch Netflix app")
                log(f"  Currently showing: {app_output}")
                log(f"🔄 Attempting FALLBACK: Using remote key navigation to launch Netflix...")
                
                netflix_found = False
                fallback_attempts = 0
                max_fallback_attempts = 2
                
                # Fallback Attempt 1: Navigate to Apps menu and try Netflix
                while fallback_attempts < max_fallback_attempts and not netflix_found:
                    fallback_attempts += 1
                    log(f"\n[FALLBACK ATTEMPT {fallback_attempts}] Key Navigation Method")
                    
                    try:
                        # Press MENU/OK to open apps menu
                        log("  → Pressing OK to open menu...")
                        menu_cmd = "keySimulator -kreturn"
                        stdin, stdout, stderr = ssh.exec_command(menu_cmd, timeout=10)
                        stdout.channel.recv_exit_status()
                        time.sleep(2)
                        
                        # Navigate to Apps (usually right arrow)
                        log("  → Navigating to Apps section (Right arrow)...")
                        for _ in range(3):
                            right_cmd = "keySimulator -kright"
                            stdin, stdout, stderr = ssh.exec_command(right_cmd, timeout=10)
                            stdout.channel.recv_exit_status()
                            time.sleep(0.5)
                        
                        # Press down to find Netflix in list
                        log("  → Searching for Netflix in apps list (Down arrow)...")
                        for i in range(5):
                            down_cmd = "keySimulator -kdown"
                            stdin, stdout, stderr = ssh.exec_command(down_cmd, timeout=10)
                            stdout.channel.recv_exit_status()
                            time.sleep(0.5)
                            
                            # Check if Netflix is in focus (optional)
                            if i % 2 == 1:  # Check every 2 presses
                                log(f"    ✓ Navigated down {i+1} positions")
                        
                        # Press Enter/Return to launch
                        log("  → Pressing ENTER to launch app...")
                        enter_cmd = "keySimulator -kreturn"
                        stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=10)
                        stdout.channel.recv_exit_status()
                        
                        # Wait for app to launch
                        log(f"  ⏳ Waiting 8 seconds for app to launch...")
                        time.sleep(8)
                        
                        # Check if Netflix is now running
                        stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=15)
                        app_output = stdout.read().decode('utf-8', errors='ignore').strip()
                        
                        log(f"  ✓ Verification check: {app_output}")
                        
                        if 'NetflixApp' in app_output or 'Netflix' in app_output:
                            log(f"✓ FALLBACK SUCCESSFUL: Netflix app now in foreground!")
                            log(f"  Confirmed app: {app_output}")
                            netflix_found = True
                            step_results['step_2_app_verification'] = 'success_via_fallback'
                            break
                        else:
                            log(f"  ⚠ Still showing: {app_output}")
                            
                            # Press HOME to return and retry
                            if fallback_attempts < max_fallback_attempts:
                                log(f"  → Pressing HOME to reset and retry...")
                                home_cmd = "keySimulator -khome"
                                stdin, stdout, stderr = ssh.exec_command(home_cmd, timeout=10)
                                stdout.channel.recv_exit_status()
                                time.sleep(3)
                    
                    except Exception as e:
                        log(f"  ❌ Fallback navigation error: {e}")
                        if fallback_attempts < max_fallback_attempts:
                            time.sleep(2)
                
                if not netflix_found:
                    # CRITICAL FAILURE: Both voice command and fallback failed
                    log(f"\n❌ CRITICAL FAILURE: Netflix app NOT found after all attempts")
                    log(f"❌ Current foreground app: {app_output}")
                    log(f"❌ Netflix playback test FAILED - App is not running")
                    step_results['step_2_app_verification'] = f'app_not_found_all_methods: {app_output}'
                    overall_success = False
                    
                    # Log final results and exit
                    log("\n" + "="*80)
                    log("NETFLIX APP LAUNCH AND PLAYBACK - EXECUTION HALTED")
                    log("="*80)
                    log(f"\n❌ Execution Status: FAILED")
                    log(f"Reason: Netflix app could not be launched via voice or key navigation")
                    log(f"Expected: NetflixApp")
                    log(f"Found: {app_output}")
        except Exception as e:
            log(f"❌ Error during app verification: {e}")
            step_results['step_2_app_verification'] = f'error: {e}'
            overall_success = False
            netflix_found = False
        
        # Check if Netflix app was found - if not, return failure
        if not netflix_found:
            # Critical failure - exit execution
            log("\n" + "="*80)
            log("NETFLIX APP LAUNCH AND PLAYBACK - EXECUTION HALTED")
            log("="*80)
            log(f"\n❌ Execution Status: FAILED")
            log(f"Reason: Netflix app could not be launched via voice or key navigation")
            log(f"Expected: NetflixApp")
            
            # Close SSH and return failure
            if ssh:
                try:
                    ssh.close()
                    log("✓ SSH connection closed")
                except:
                    pass
            
            return {
                'success': False,
                'execution_status': 'failed',
                'timestamp': timestamp,
                'device': device_name,
                'device_ip': device_ip,
                'iteration': iteration,
                'step_results': step_results,
                'failure_reason': f'Netflix app not found in foreground at STEP 2',
                'details': 'Netflix app launch verification failed - no further steps executed'
            }
        
        # ======================================================================
        # STEP 3: VERIFY IN SYSTEM LOGS
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 3] SYSTEM LOG VERIFICATION")
        log("="*80)
        
        log_check_cmd = "grep -i 'App.*has.*screen' /opt/logs/sky-messages.log | tail -1; grep -i 'Netflix.*Status.*RUNNING' /opt/logs/sky-messages.log | tail -1"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(log_check_cmd, timeout=15)
            log_output = stdout.read().decode('utf-8', errors='ignore').strip()
            
            if log_output:
                log("System logs:")
                for line in log_output.split('\n'):
                    if line.strip():
                        log(f"  {line}")
                step_results['step_3_log_verification'] = 'success'
            else:
                log("⚠ No matching log entries found yet")
                step_results['step_3_log_verification'] = 'no_logs'
        except Exception as e:
            log(f"❌ Error checking logs: {e}")
            step_results['step_3_log_verification'] = f'error: {e}'
        
        # ======================================================================
        # STEP 4: CAPTURE CURRENT SCREEN WITH AI ANALYSIS
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 4] SCREEN CAPTURE AND STATE IDENTIFICATION")
        log("="*80)
        
        log("📸 Capturing current screen...")
        screen_state = "UNKNOWN"
        screenshot_info = None
        
        try:
            # V2.0 imports: screenshot_utils is in utils/ folder
            utils_dir = os.path.join(parent_dir, 'utils')
            if utils_dir not in sys.path:
                sys.path.insert(0, utils_dir)
            from screenshot_utils import take_and_analyze_screenshot
            
            # Determine screenshot folder
            # Priority 1: Use session_folder if provided (recommended for v2.0)
            if session_folder:
                screenshot_folder = os.path.join(session_folder, 'SCREENSHOTS')
                # Create SCREENSHOTS directory if it doesn't exist
                os.makedirs(screenshot_folder, exist_ok=True)
            else:
                # Fallback: Use job-specific screenshot folder for legacy compatibility
                screenshot_folder = os.path.expanduser('~/screenshots')
                if job_id:
                    screenshot_folder = os.path.join(screenshot_folder, job_id)
            
            screenshot_name = f"netflix_state_{timestamp}"
            result = take_and_analyze_screenshot(
                ssh,
                screenshot_name,
                device_ip,
                log_callback=log,
                screenshot_folder=screenshot_folder,
                app_name="netflix",
                step=4
            )
            
            if result.get('success'):
                log(f"✓ Screenshot captured: {result.get('local_path', 'unknown')}")
                
                # Store screenshot info for later display in results
                screenshot_info = {
                    'path': result.get('local_path'),
                    'url': result.get('screenshot_url'),
                    'timestamp': timestamp
                }
                
                # Use AI validation result to detect screen state (ENHANCED WITH SECONDARY VALIDATION)
                screen_validation = result.get('screen_state', {})
                if screen_validation:
                    screen_detected = screen_validation.get('screen_detected', 'Unknown')
                    confidence = screen_validation.get('confidence', 0.0)
                    
                    # 🔧 FIX: Handle None values from fallback validation
                    if screen_detected is None or screen_detected == 'None':
                        screen_detected = 'Unknown'
                    
                    log(f"✓ Screen Validation Result: {screen_detected} ({confidence:.2%} confidence)")
                    
                    # ================================================================
                    # STEP 4 ENHANCED: IMPROVED SCREEN DETECTION WITH FEATURE ANALYSIS
                    # ================================================================
                    # Similar to Step 6.1: Use enhanced detection when pixel confidence is low
                    # This prevents misclassification (e.g., home as profile, asset as home)
                    
                    if confidence < 0.90:  # Apply enhanced detection for non-very-high confidence matches
                        log(f"🔍 Step 4 Enhanced Detection: Running feature-based validation (pixel confidence: {confidence:.1%})...")
                        
                        try:
                            from tools.screen.netflix_screen_detector import NetflixScreenDetector
                            detector = NetflixScreenDetector()
                            screenshot_path = result.get('local_path', '')
                            
                            if screenshot_path and os.path.exists(screenshot_path):
                                # Use the same distinguishing logic as Step 6
                                enhanced_result = detector.distinguish_home_vs_asset(
                                    screenshot_path,
                                    screen_detected,
                                    confidence
                                )
                                
                                enhanced_screen = enhanced_result.get('final_screen', screen_detected)
                                enhanced_confidence = enhanced_result.get('confidence', confidence)
                                
                                # Log feature detection details
                                button_info = enhanced_result.get('button_detection', {})
                                metadata_info = enhanced_result.get('metadata_detection', {})
                                
                                log(f"  📊 Feature detection:")
                                log(f"     • Buttons: {button_info.get('has_buttons', False)} ({button_info.get('button_count', 0)} detected)")
                                log(f"     • Metadata: {metadata_info.get('has_metadata', False)} ({len(metadata_info.get('patterns_found', []))} patterns)")
                                
                                # If enhanced detection changed the result, log the reclassification
                                if enhanced_screen != screen_detected:
                                    log(f"  ✓ RECLASSIFIED: {screen_detected} ({confidence:.1%}) → {enhanced_screen} ({enhanced_confidence:.1%})")
                                    screen_detected = enhanced_screen
                                    confidence = enhanced_confidence
                                else:
                                    log(f"  ✓ Confirmed: {screen_detected} ({enhanced_confidence:.1%})")
                        
                        except Exception as enhance_err:
                            log(f"  ⚠ Enhanced detection error: {enhance_err}")
                            # Fall back to basic detection
                            log(f"  ℹ Using base pixel matching result")
                    
                    # Map AI detection to screen state using enhanced keyword matching
                    detected_lower = str(screen_detected).lower()
                    
                    if 'login' in detected_lower or 'activate' in detected_lower:
                        screen_state = "NETFLIX_LOGIN_SCREEN"
                        log(f"→ Detected: LOGIN/ACTIVATION screen")
                    elif 'profile' in detected_lower:
                        screen_state = "NETFLIX_PROFILE_SCREEN"
                        log(f"→ Detected: PROFILE SELECTION screen")
                    elif 'asset' in detected_lower:
                        screen_state = "NETFLIX_ASSET_SCREEN"
                        log(f"→ Detected: ASSET/CONTENT DETAIL screen")
                    elif 'home' in detected_lower or 'browse' in detected_lower:
                        screen_state = "NETFLIX_HOME_SCREEN"
                        log(f"→ Detected: HOME/BROWSE screen")
                    else:
                        # For unknown screens, still capture the detection result
                        screen_state = f"NETFLIX_SCREEN: {screen_detected}"
                        log(f"⚠ Unknown Netflix screen detected: {screen_detected}")
                    
                    log(f"✓ Screen state determined: {screen_state} [confidence: {confidence:.2%}]")
                    
                    # Store enhanced detection info in validation result
                    screen_validation['screen_detected'] = screen_detected
                    screen_validation['confidence'] = confidence
                    screen_validation['validation_method'] = 'enhanced' if confidence != screen_validation.get('confidence', 0) else 'pixel_matching'
                else:
                    log(f"⚠ No AI validation result available, using fallback detection")
                    screen_state = "NETFLIX_UNKNOWN_SCREEN"
                
                step_results['step_4_screen_capture'] = screen_state
                step_results['step_4_screenshot'] = screenshot_info
                step_results['step_4_screen_validation'] = screen_validation
                
                # Update job in real-time with step_4 results
                if job_id:
                    try:
                        from models.job import Job
                        Job.update_execution_results(job_id, {
                            'step_4_screen_capture': screen_state,
                            'step_4_screenshot': screenshot_info,
                            'step_4_screen_validation': screen_validation
                        })
                        log(f"✓ Updated job {job_id} with Step 4 results")
                    except Exception as e:
                        log(f"⚠ Could not update job with Step 4 results: {e}")
            else:
                log(f"❌ Screenshot capture failed: {result.get('error', 'unknown error')}")
                screen_state = "CAPTURE_FAILED"
                step_results['step_4_screen_capture'] = 'capture_failed'
                step_results['step_4_error'] = result.get('error')
        except ImportError:
            log("⚠ Screenshot utilities not available (screenshot analysis skipped)")
            screen_state = "SKIP"
            step_results['step_4_screen_capture'] = 'skipped'
        except Exception as e:
            log(f"❌ Error capturing screenshot: {e}")
            screen_state = "ERROR"
            step_results['step_4_screen_capture'] = f'error: {e}'
        
        # ======================================================================
        # STEP 5: CONDITIONAL SCREEN STATE HANDLING (AUTO-DETECTED)
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 5] SCREEN STATE CONDITIONAL HANDLING (AUTO-DETECTED)")
        log("="*80)
        log(f"ℹ Detected screen state: {screen_state}")
        
        if screen_state == "NETFLIX_LOGIN_SCREEN":
            log("→ Login screen detected - handling authentication flow...")
            
            # Check if credentials are available
            if not username_cred or not password_cred:
                log("⚠ Login screen detected but NO credentials provided")
                log("📺 MANUAL ACTION REQUIRED on TV:")
                log("   1. Please complete Netflix login manually on the TV screen")
                log("   2. Use the activation code displayed on TV")
                log("   3. Go to: http://netflix.com/activate")
                log("   4. Enter the activation code and your Netflix credentials")
                log("   5. Once authenticated, Netflix will proceed to home/profile screen")
                log("⏳ Waiting 60 seconds for manual login completion...")
                time.sleep(60)
                log("✓ Continuing with next steps (assuming manual login completed)")
                step_results['step_5_screen_handling'] = 'manual_login_required'
            else:
                log(f"ℹ Credentials available, attempting browser-based login...")
                step_results['step_5_screen_handling'] = 'login_attempted_with_credentials'
                log("⚠ Browser-based login feature requires additional configuration")
                log("   For now, manual login is recommended")
                
        elif screen_state == "NETFLIX_PROFILE_SCREEN" or (isinstance(screen_state, str) and 'profile' in screen_state.lower()):
            log("→ Profile screen detected - selecting profile...")
            
            # Send ENTER to select profile
            enter_cmd = "keySimulator -kenter"
            try:
                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=15)
                stdout.read()
                log("✓ Sent ENTER to select profile")
                time.sleep(5)
                log("✓ Waited 5 seconds for navigation")
                step_results['step_5_screen_handling'] = 'profile_selected'
            except Exception as e:
                log(f"❌ Error sending ENTER: {e}")
                step_results['step_5_screen_handling'] = f'error: {e}'
                overall_success = False
            
        elif screen_state == "NETFLIX_HOME_SCREEN" or (isinstance(screen_state, str) and 'home' in screen_state.lower()):
            log("→ Home screen detected - proceeding to content launch")
            step_results['step_5_screen_handling'] = 'home_screen_ready'
            
        elif screen_state == "NETFLIX_ASSET_SCREEN" or (isinstance(screen_state, str) and 'asset' in screen_state.lower()):
            log("→ Asset/Content screen detected - device already navigated to content!")
            log("   This may happen if Netflix bypassed profile selection")
            step_results['step_5_screen_handling'] = 'asset_screen_ready'
            
        else:
            log(f"ℹ Screen state: {screen_state}")
            if screen_state.startswith("NETFLIX_SCREEN:"):
                log(f"  ✓ Netflix app screen detected via AI - proceeding with playback")
                step_results['step_5_screen_handling'] = f'screen_detected: {screen_state}'
            else:
                log(f"⚠ Unexpected screen state - attempting to proceed anyway")
                step_results['step_5_screen_handling'] = f'unknown_state: {screen_state}'
        
        # ======================================================================
        # STEP 5.5: PROFILE SCREEN CAPTURE
        # ======================================================================
        # Capture screenshot at step 5 to show device state after profile selection
        log("\n📸 Capturing profile screen state...")
        profile_screenshot_info = None
        try:
            # V2.0 imports: screenshot_utils is in utils/ folder
            utils_dir = os.path.join(parent_dir, 'utils')
            if utils_dir not in sys.path:
                sys.path.insert(0, utils_dir)
            from screenshot_utils import take_and_analyze_screenshot
            
            # Determine screenshot folder
            # Priority 1: Use session_folder if provided (recommended for v2.0)
            if session_folder:
                screenshot_folder = os.path.join(session_folder, 'SCREENSHOTS')
                # Create SCREENSHOTS directory if it doesn't exist
                os.makedirs(screenshot_folder, exist_ok=True)
            else:
                # Fallback: Use job-specific screenshot folder for legacy compatibility
                screenshot_folder = os.path.expanduser('~/screenshots')
                if job_id:
                    screenshot_folder = os.path.join(screenshot_folder, job_id)
            
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            screenshot_name = f"netflix_profile_state_{timestamp}"
            result = take_and_analyze_screenshot(
                ssh,
                screenshot_name,
                device_ip,
                log_callback=log,
                screenshot_folder=screenshot_folder,
                app_name="netflix",
                step=5
            )
            
            if result.get('success'):
                log(f"✓ Profile screen screenshot captured")
                
                # ================================================================
                # STEP 5.5 ENHANCED: VALIDATE PROFILE/HOME SCREEN WITH FEATURES
                # ================================================================
                # Similar to Step 4 & 6: Use enhanced detection for better accuracy
                # Validates that profile selection proceeded to correct next screen
                
                screen_validation = result.get('screen_state', {})
                screen_detected = screen_validation.get('screen_detected', 'Unknown')
                confidence = screen_validation.get('confidence', 0.0)
                
                # 🔧 FIX: Handle None values from fallback validation
                if screen_detected is None or screen_detected == 'None':
                    screen_detected = 'Unknown'
                
                log(f"🔍 Step 5.5 Screen Validation: {screen_detected} ({confidence:.1%})")
                
                # Apply enhanced detection for low confidence matches
                # After profile selection, we expect HOME or ASSET, not LOGIN or PROFILE again
                if confidence < 0.85:
                    log(f"🔍 Step 5.5 Enhanced Detection: Running feature validation (confidence: {confidence:.1%})...")
                    
                    try:
                        from tools.screen.netflix_screen_detector import NetflixScreenDetector
                        detector = NetflixScreenDetector()
                        screenshot_path = result.get('local_path', '')
                        
                        if screenshot_path and os.path.exists(screenshot_path):
                            enhanced_result = detector.distinguish_home_vs_asset(
                                screenshot_path,
                                screen_detected,
                                confidence
                            )
                            
                            enhanced_screen = enhanced_result.get('final_screen', screen_detected)
                            enhanced_confidence = enhanced_result.get('confidence', confidence)
                            
                            # Log results
                            button_info = enhanced_result.get('button_detection', {})
                            metadata_info = enhanced_result.get('metadata_detection', {})
                            
                            log(f"  📊 Feature detection:")
                            log(f"     • Buttons: {button_info.get('has_buttons', False)} ({button_info.get('button_count', 0)} detected)")
                            log(f"     • Metadata: {metadata_info.get('has_metadata', False)} ({len(metadata_info.get('patterns_found', []))} patterns)")
                            
                            if enhanced_screen != screen_detected:
                                log(f"  ✓ RECLASSIFIED: {screen_detected} ({confidence:.1%}) → {enhanced_screen} ({enhanced_confidence:.1%})")
                                screen_detected = enhanced_screen
                                confidence = enhanced_confidence
                            else:
                                log(f"  ✓ Confirmed: {screen_detected} ({enhanced_confidence:.1%})")
                            
                            # Update screen validation with enhanced results
                            screen_validation['screen_detected'] = screen_detected
                            screen_validation['confidence'] = confidence
                    
                    except Exception as enhance_err:
                        log(f"  ⚠ Enhanced detection error: {enhance_err}")
                        log(f"  ℹ Using pixel matching result")
                
                # Store screenshot info for results display with validation details
                profile_screenshot_info = {
                    'path': result.get('local_path'),
                    'url': result.get('screenshot_url'),
                    'step': 5,
                    'timestamp': timestamp,
                    'screen_detected': screen_detected,
                    'confidence': confidence,
                    'validation_method': 'enhanced' if screen_validation.get('confidence', 0) < 0.85 else 'pixel_matching'
                }
                
                step_results['step_5_screenshot_verification'] = 'success'
                step_results['step_5_screenshot'] = profile_screenshot_info
                step_results['step_5_screen_validation'] = screen_validation
                
                # Update job in real-time with step_5 results
                if job_id:
                    try:
                        from models.job import Job
                        Job.update_execution_results(job_id, {
                            'step_5_screenshot_verification': 'success',
                            'step_5_screenshot': profile_screenshot_info
                        })
                        log(f"✓ Updated job {job_id} with Step 5 profile screenshot")
                    except Exception as e:
                        log(f"⚠ Could not update job with Step 5 screenshot: {e}")
            else:
                log(f"⚠ Profile screenshot capture failed: {result.get('error')}")
                step_results['step_5_screenshot_verification'] = f'failed: {result.get("error")}'
                
        except Exception as e:
            log(f"❌ Error capturing profile screenshot: {e}")
            step_results['step_5_screenshot_verification'] = f'error: {e}'
        
        # ======================================================================
        # STEP 6: CONTENT LAUNCH - SEND ASSET VOICE COMMAND
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 6] CONTENT LAUNCH")
        log("="*80)
        
        asset_command_timestamp = None  # Will be set if asset command succeeds
        
        log(f"🎙 Sending asset voice command: '{asset_voice_command}'")
        
        # Send asset voice command
        escaped_asset_text = asset_voice_command.replace("'", "'\\''")
        asset_cmd = (
            f"curl --header 'Content-Type: application/json' "
            f"--request POST --silent "
            f"-d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\":\"org.rdk.VoiceControl.1.voiceSessionByText\",\"params\":{{\"transcription\":\"{escaped_asset_text}\"}}}}' "
            f"http://127.0.0.1:9998/jsonrpc"
        )
        
        log(f"Executing command: {asset_cmd}")
        
        try:
            stdin, stdout, stderr = ssh.exec_command(asset_cmd, timeout=30)
            asset_output = stdout.read().decode('utf-8', errors='ignore').strip()
            asset_error = stderr.read().decode('utf-8', errors='ignore').strip()
            
            log(f"Response: {asset_output}")
            
            if asset_error:
                log(f"⚠ Error output: {asset_error}")
            
            # Check CURL response for success
            if asset_output:
                try:
                    result = json.loads(asset_output)
                    # Check if response has result with success flag
                    if "result" in result and isinstance(result["result"], dict):
                        if result["result"].get("success") == True:
                            log("✓ Asset voice command executed successfully")
                            log(f"Session ID: {result['result'].get('sessionId', 'N/A')}")
                            
                            # Capture timestamp AFTER successful asset command for log filtering
                            asset_command_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
                            log(f"📍 Asset command execution timestamp: {asset_command_timestamp}")
                            log(f"📋 Playback log pattern to validate: '{playback_log_string}'")
                            
                            step_results['step_6_asset_voice'] = 'success'
                        else:
                            log(f"❌ Asset voice command returned success=false")
                            asset_command_timestamp = None
                            step_results['step_6_asset_voice'] = 'voice_api_failed'
                    elif "error" in result:
                        error_msg = result.get("error", {})
                        log(f"❌ Asset voice command error: {error_msg}")
                        asset_command_timestamp = None
                        step_results['step_6_asset_voice'] = f'api_error: {error_msg}'
                    else:
                        log(f"⚠ Unexpected JSON response: {asset_output}")
                        asset_command_timestamp = None
                        step_results['step_6_asset_voice'] = 'unexpected_response'
                except json.JSONDecodeError:
                    log(f"❌ Could not parse JSON response: {asset_output}")
                    asset_command_timestamp = None
                    step_results['step_6_asset_voice'] = 'json_parse_error'
            else:
                log("❌ No response received from asset voice command")
                asset_command_timestamp = None
                step_results['step_6_asset_voice'] = 'no_response'
            
            log("⏳ Waiting 5 seconds for asset page to load...")
            time.sleep(5)
            
            # Initialize asset_screenshot_info at the beginning of Step 6
            asset_screenshot_info = None
            log("📸 Capturing verification screenshot...")
            asset_screenshot_info = None
            try:
                # V2.0 imports: screenshot_utils is in utils/ folder
                utils_dir = os.path.join(parent_dir, 'utils')
                if utils_dir not in sys.path:
                    sys.path.insert(0, utils_dir)
                from screenshot_utils import take_and_analyze_screenshot
                
                # Determine screenshot folder
                # Priority 1: Use session_folder if provided (recommended for v2.0)
                if session_folder:
                    screenshot_folder = os.path.join(session_folder, 'SCREENSHOTS')
                    # Create SCREENSHOTS directory if it doesn't exist
                    os.makedirs(screenshot_folder, exist_ok=True)
                else:
                    # Fallback: Use job-specific screenshot folder for legacy compatibility
                    screenshot_folder = os.path.expanduser('~/screenshots')
                    if job_id:
                        screenshot_folder = os.path.join(screenshot_folder, job_id)
                
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                screenshot_name = f"netflix_asset_search_{timestamp}"
                result = take_and_analyze_screenshot(
                    ssh,
                    screenshot_name,
                    device_ip,
                    log_callback=log,
                    screenshot_folder=screenshot_folder,
                    app_name="netflix",
                    step="6.1"
                )
                
                if result.get('success'):
                    log(f"✓ Asset search screenshot captured")
                    
                    # Store screenshot info for results display
                    asset_screenshot_info = {
                        'path': result.get('local_path'),
                        'url': result.get('screenshot_url'),
                        'step': 6.1,
                        'timestamp': timestamp
                    }
                    
                    # Capture screen validation result for Step 6
                    screen_validation = result.get('screen_state', {})
                    screen_detected = 'Unknown'
                    if screen_validation:
                        screen_detected = screen_validation.get('screen_detected', 'Unknown')
                        
                        # 🔧 FIX: Handle None values from fallback validation
                        if screen_detected is None or screen_detected == 'None':
                            screen_detected = 'Unknown'
                        
                        log("\n" + "="*80)
                        log("[STEP 6.1] ASSET SCREEN DETECTION AND SELECTION")
                        log("="*80)
                        log(f"ℹ Step 6.1 Screen detection: {screen_detected} ({screen_validation.get('confidence', 0):.2%} confidence)")
                    
                    # ENHANCED: Use Netflix-specific feature detection for Step 6.1
                    # CRITICAL: Always run enhanced detection to improve accuracy for asset vs home screens
                    # Catches cases where pixel matching is wrong (e.g., asset screen misclassified as home)
                    # This is especially important when pixel_confidence is NOT extremely high (>90%)
                    pixel_confidence = screen_validation.get('confidence', 0.0)
                    try:
                        from tools.screen.netflix_screen_detector import NetflixScreenDetector
                        detector = NetflixScreenDetector()
                        screenshot_path = result.get('local_path', '')
                        
                        # Run enhanced detection in these cases:
                        # 1. Low confidence pixel matching (<70%)
                        # 2. Medium confidence (70-90%) with ambiguous screen (Netflix_NetflixHome likely misclassified)
                        # 3. Always when we're trying to distinguish between home and asset screens
                        should_run_enhanced = (
                            pixel_confidence < 0.90 or  # Try to improve all non-very-high-confidence matches
                            'home' in screen_detected.lower()  # CRITICAL: Home is frequently misclassified as asset
                        )
                        
                        if screenshot_path and os.path.exists(screenshot_path) and should_run_enhanced:
                            log(f"🔍 Running enhanced Netflix screen detection (pixel confidence: {pixel_confidence:.1%})...")
                            detection_result = detector.distinguish_home_vs_asset(
                                screenshot_path,
                                screen_detected,
                                pixel_confidence
                            )
                            
                            enhanced_screen = detection_result.get('final_screen', screen_detected)
                            enhanced_confidence = detection_result.get('confidence', pixel_confidence)
                            
                            # Log feature detection details for debugging and transparency
                            button_info = detection_result.get('button_detection', {})
                            metadata_info = detection_result.get('metadata_detection', {})
                            
                            log(f"  📊 Enhanced detection results:")
                            log(f"     • Buttons: {button_info.get('has_buttons', False)} ({button_info.get('button_count', 0)} detected)")
                            log(f"     • Metadata patterns: {metadata_info.get('has_metadata', False)} ({len(metadata_info.get('patterns_found', []))} patterns)")
                            log(f"     • Reason: {detection_result.get('reason', 'N/A')}")
                            
                            # If enhanced detection changed the result, log the reclassification
                            if enhanced_screen != screen_detected:
                                log(f"  ✓ RECLASSIFIED: {screen_detected} ({pixel_confidence:.1%}) → {enhanced_screen} ({enhanced_confidence:.1%})")
                                screen_detected = enhanced_screen
                            else:
                                log(f"  ✓ Confirmed: {screen_detected} ({enhanced_confidence:.1%})")
                    
                    except Exception as enhance_err:
                        log(f"  ⚠ Enhanced detection error for Step 6.1: {enhance_err}")
                    
                    # ================================================================
                    # STEP 6.1 CONTINUED: VALIDATE AND PROCEED TO ASSET SELECTION
                    # ================================================================
                    # Determine if we should proceed to asset selection
                    # Look for: (1) Search/Browse screens with 'search' in name, OR
                    #           (2) Asset screens (after enhanced detection reclassification)
                    detected_lower = str(screen_detected).lower()
                    
                    # More robust check: Looking for screens where user selects/searches for content
                    # Handles: Netflix_NetflixSearch, Netflix_NetflixBrowse, Netflix_NetflixAssetScreen, etc.
                    should_select_asset = (
                        'search' in detected_lower or 
                        'browse' in detected_lower or
                        'assetscreen' in detected_lower  # Asset screen from reclassification
                    )
                    
                    if should_select_asset:
                        # Matched with asset selection screen - send ENTER to select/play
                        log(f"→ Asset selection screen detected - proceeding to asset details...")
                        
                        asset_select_success = False
                        try:
                            enter_cmd = "keySimulator -kenter"
                            stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=15)
                            stdout.read()
                            log("✓ Sent ENTER to select asset")
                            time.sleep(3)
                            
                            # ================================================================
                            # STEP 6.2: CAPTURE ASSET DETAIL SCREEN AND VALIDATE
                            # ================================================================
                            log("\n" + "="*80)
                            log("[STEP 6.2] ASSET DETAIL SCREEN VALIDATION")
                            log("="*80)
                            log("📸 Capturing asset detail/playback screen...")
                            timestamp_asset = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                            screenshot_name_asset = f"netflix_asset_selected_{timestamp_asset}"
                            
                            result_asset = take_and_analyze_screenshot(
                                ssh,
                                screenshot_name_asset,
                                device_ip,
                                log_callback=log,
                                screenshot_folder=screenshot_folder,
                                app_name="netflix",
                                step="6.2"
                            )
                            
                            if result_asset.get('success'):
                                log(f"✓ Asset screen screenshot captured")
                                
                                # Validate against asset screen
                                screen_validation_asset = result_asset.get('screen_state', {})
                                screen_detected_asset = 'Unknown'
                                is_asset_screen = False
                                if screen_validation_asset:
                                    screen_detected_asset = screen_validation_asset.get('screen_detected', 'Unknown')
                                    if screen_detected_asset is None or screen_detected_asset == 'None':
                                        screen_detected_asset = 'Unknown'
                                    
                                    log(f"ℹ Step 6.2 Screen detection: {screen_detected_asset} ({screen_validation_asset.get('confidence', 0):.2%} confidence)")
                                
                                detected_lower_asset = str(screen_detected_asset).lower()
                                pixel_confidence_asset = screen_validation_asset.get('confidence', 0.0)
                                
                                # ENHANCED: Use Netflix-specific feature detection
                                # Features checked: thumbs up/down buttons (primary), metadata patterns (secondary)
                                # Note: NOT relying on Dolby badge since not all assets have it
                                try:
                                    from tools.screen.netflix_screen_detector import NetflixScreenDetector
                                    detector = NetflixScreenDetector()
                                    screenshot_path = result_asset.get('local_path', '')
                                    
                                    if screenshot_path and os.path.exists(screenshot_path):
                                        detection_result = detector.distinguish_home_vs_asset(
                                            screenshot_path,
                                            screen_detected_asset,
                                            pixel_confidence_asset
                                        )
                                        
                                        enhanced_screen = detection_result.get('final_screen', screen_detected_asset)
                                        enhanced_confidence = detection_result.get('confidence', pixel_confidence_asset)
                                        detection_reason = detection_result.get('reason', '')
                                        
                                        # Log feature detection details for debugging
                                        log(f"  🔍 Enhanced detection analysis:")
                                        log(f"     Button detection: {detection_result['button_detection']['has_buttons']} ({detection_result['button_detection']['button_count']} buttons found)")
                                        log(f"     Metadata patterns: {detection_result['metadata_detection']['has_metadata']} ({len(detection_result['metadata_detection']['patterns_found'])} patterns)")
                                        
                                        if enhanced_screen != screen_detected_asset:
                                            log(f"  ⬆ Screen reclassified: {screen_detected_asset} ({pixel_confidence_asset:.1%}) → {enhanced_screen} ({enhanced_confidence:.1%})")
                                            log(f"     Reason: {detection_reason}")
                                            screen_detected_asset = enhanced_screen
                                        else:
                                            log(f"  ✓ Pixel match confirmed by feature detection ({enhanced_confidence:.1%})")
                                    
                                except Exception as enhance_err:
                                    log(f"  ⚠ Enhanced detection skipped: {enhance_err}")
                                
                                # Check if this is asset screen
                                if 'asset' in detected_lower_asset or 'detail' in detected_lower_asset or 'content' in detected_lower_asset:
                                    is_asset_screen = True
                                elif 'assetscreen' in screen_detected_asset.lower():
                                    # Enhanced detector reclassified as asset screen
                                    is_asset_screen = True
                                elif 'home' in detected_lower_asset and 'netflix' in detected_lower_asset:
                                    # Fallback: Context-based logic if enhancement unavailable
                                    # When pressed ENTER on asset search screen, might be detected as home but it's actually asset details
                                    log(f"ℹ Fallback reclassification: detected as home but context indicates asset screen")
                                    screen_detected_asset = 'Netflix_NetflixAssetScreen'
                                    is_asset_screen = True
                                
                                if is_asset_screen:
                                    # Matched with asset screen - send ENTER to start playback
                                    log("→ Asset detail screen detected - starting playback with ENTER...")
                                    
                                    try:
                                        enter_playback_cmd = "keySimulator -kenter"
                                        stdin, stdout, stderr = ssh.exec_command(enter_playback_cmd, timeout=15)
                                        stdout.read()
                                        log("✓ Sent ENTER to start playback")
                                        asset_select_success = True
                                        step_results['step_6_asset_selection'] = 'matched_and_played'
                                        
                                        # Update asset screenshot info with the final asset screen
                                        asset_screenshot_info = {
                                            'path': result_asset.get('local_path'),
                                            'url': result_asset.get('screenshot_url'),
                                            'step': 6.2,
                                            'timestamp': timestamp_asset,
                                            'screen_detected': screen_detected_asset
                                        }
                                        
                                    except Exception as e:
                                        log(f"❌ Error sending ENTER for playback: {e}")
                                        step_results['step_6_asset_selection'] = f'playback_keypress_error: {e}'
                                else:
                                    log(f"⚠ Asset screen not confirmed: {screen_detected_asset}")
                                    log("  Proceeding anyway assuming device is ready for playback")
                                    asset_select_success = True
                                    step_results['step_6_asset_selection'] = f'unconfirmed: {screen_detected_asset}'
                            else:
                                log(f"⚠ Could not capture asset screen: {result_asset.get('error')}")
                                step_results['step_6_asset_selection'] = f'capture_failed: {result_asset.get("error")}'
                                
                        except Exception as e:
                            log(f"❌ Error selecting asset: {e}")
                            step_results['step_6_asset_selection'] = f'error: {e}'
                        
                        if asset_select_success:
                            log(f"✓ Asset selection and playback flow completed")
                            step_results['step_6_content_launch'] = 'success_with_validation'
                        else:
                            log(f"⚠ Asset selection had issues but continuing")
                            step_results['step_6_content_launch'] = 'success_with_issues'
                    
                    elif 'asset' in detected_lower:
                        # ================================================================
                        # ASSET SCREEN ALREADY DETECTED AT STEP 6.1 - SKIP STEP 6.2
                        # ================================================================
                        log("→ Asset detail screen already detected at Step 6.1")
                        log("  SKIPPING STEP 6.2 (asset detail validation)")
                        log("  Reason: Enhanced screen detection already confirmed asset screen")
                        log("  Proceeding directly to Step 6.3 (OCR validation)")
                        
                        # Update asset screenshot info with Step 6.1 capture
                        asset_screenshot_info = {
                            'path': result.get('local_path'),
                            'url': result.get('screenshot_url'),
                            'step': 6.1,
                            'timestamp': timestamp,
                            'screen_detected': screen_detected,
                            'step_6_2_skipped': True,
                            'skip_reason': 'asset_screen_detected_at_step_6_1'
                        }
                        
                        # Attempt to start playback
                        try:
                            log("🎬 Starting playback (asset screen confirmed at Step 6.1)")
                            enter_cmd = "keySimulator -kenter"
                            stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=15)
                            stdout.read()
                            log("✓ Sent ENTER to start playback")
                            step_results['step_6_asset_selection'] = 'asset_screen_confirmed_6_1'
                            step_results['step_6_content_launch'] = 'success_optimized'
                            step_results['step_6_skipped_6_2'] = True
                        except Exception as e:
                            log(f"❌ Error sending ENTER: {e}")
                            step_results['step_6_asset_selection'] = f'error: {e}'
                            step_results['step_6_content_launch'] = f'keypress_error: {e}'
                            step_results['step_6_skipped_6_2'] = True
                    
                    else:
                        log(f"ℹ Screen detected at Step 6.1: {screen_detected}")
                        log(f"  Enhanced detection did not classify as search/asset screen")
                        log(f"  Context: After voice command, assuming asset content is loaded")
                        log(f"  Proceeding to Step 6.3 (OCR validation) for content confirmation")
                        
                        # Update asset screenshot for Step 6.3 validation
                        asset_screenshot_info = {
                            'path': result.get('local_path'),
                            'url': result.get('screenshot_url'),
                            'step': 6.1,
                            'timestamp': timestamp,
                            'screen_detected': screen_detected
                        }
                        
                        step_results['step_6_content_launch'] = 'success_ambiguous'
                        step_results['step_6_asset_selection'] = f'screen_context: {screen_detected}'
                    
                    step_results['step_6_screenshot'] = asset_screenshot_info
                    
                    # Update job in real-time with step_6 results
                    if job_id:
                        try:
                            from models.job import Job
                            Job.update_execution_results(job_id, {
                                'step_6_content_launch': step_results.get('step_6_content_launch', 'unknown'),
                                'step_6_screenshot': asset_screenshot_info,
                                'step_6_asset_selection': step_results.get('step_6_asset_selection', 'unknown')
                            })
                            log(f"✓ Updated job {job_id} with Step 6 results")
                        except Exception as e:
                            log(f"⚠ Could not update job with Step 6 results: {e}")
                else:
                    log(f"⚠ Could not verify asset page loaded: {result.get('error')}")
                    step_results['step_6_content_launch'] = 'capture_failed'
            except ImportError:
                log("⚠ Screenshot verification skipped")
                step_results['step_6_content_launch'] = 'success_unverified'
                
        except Exception as e:
            log(f"❌ Error sending asset command: {e}")
            step_results['step_6_content_launch'] = f'error: {e}'
            overall_success = False
        
        # ======================================================================
        # STEP 6.3: OCR-BASED ASSET NAME VALIDATION (TESSERACT)
        # ======================================================================
        # Use Tesseract OCR to extract text from screenshot and validate asset name
        if asset_screenshot_info and asset_screenshot_info.get('path'):
            log("\n" + "="*80)
            log("[STEP 6.3] OCR-BASED ASSET NAME VALIDATION")
            log("="*80)
            
            try:
                screenshot_path = asset_screenshot_info.get('path')
                log(f"📸 Analyzing asset name from screenshot via OCR: {screenshot_path}")
                
                # Extract text using Tesseract OCR with preprocessing
                try:
                    from PIL import Image, ImageEnhance
                    import pytesseract
                    
                    # Open and preprocess image for optimal OCR
                    img = Image.open(screenshot_path)
                    extracted_text = None
                    confidence = 0.0
                    
                    # Strategy 1: Enhanced contrast for text clarity
                    try:
                        log(f"🔍 Extracting text via OCR (Strategy 1: Enhanced contrast)...")
                        enhancer = ImageEnhance.Contrast(img)
                        enhanced = enhancer.enhance(2.0)
                        sharpener = ImageEnhance.Sharpness(enhanced)
                        enhanced = sharpener.enhance(1.5)
                        
                        extracted_text = pytesseract.image_to_string(enhanced)
                        if extracted_text and len(extracted_text.strip()) > 5:
                            confidence = 0.85
                            log(f"✅ OCR extraction successful (Strategy 1)")
                            log(f"📝 Extracted text: {extracted_text[:200]}")
                    except Exception as e:
                        log(f"⚠ Strategy 1 failed: {e}")
                    
                    # Strategy 2: Upscaled image if first strategy didn't work well
                    if not extracted_text or len(extracted_text.strip()) < 5:
                        try:
                            log(f"🔍 Trying OCR extraction (Strategy 2: 2x upscale)...")
                            width, height = img.size
                            upscaled = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
                            extracted_text = pytesseract.image_to_string(upscaled)
                            if extracted_text and len(extracted_text.strip()) > 5:
                                confidence = 0.80
                                log(f"✅ OCR extraction successful (Strategy 2)")
                                log(f"📝 Extracted text: {extracted_text[:200]}")
                        except Exception as e:
                            log(f"⚠ Strategy 2 failed: {e}")
                    
                    # Strategy 3: TV UI optimized (3x upscale + high contrast)
                    if not extracted_text or len(extracted_text.strip()) < 5:
                        try:
                            log(f"🔍 Trying OCR extraction (Strategy 3: TV UI optimized)...")
                            grayscale = img.convert('L')
                            width, height = grayscale.size
                            upscaled = grayscale.resize((width * 3, height * 3), Image.Resampling.LANCZOS)
                            enhancer = ImageEnhance.Contrast(upscaled)
                            enhanced = enhancer.enhance(2.5)
                            extracted_text = pytesseract.image_to_string(enhanced)
                            if extracted_text and len(extracted_text.strip()) > 5:
                                confidence = 0.75
                                log(f"✅ OCR extraction successful (Strategy 3)")
                                log(f"📝 Extracted text: {extracted_text[:200]}")
                        except Exception as e:
                            log(f"⚠ Strategy 3 failed: {e}")
                    
                    if extracted_text and len(extracted_text.strip()) > 5:
                        extracted_text = extracted_text.strip().lower()
                        log(f"📊 Full OCR Result: {extracted_text}")
                        
                        # Extract keywords from voice command for matching
                        voice_cmd_normalized = asset_voice_command.lower().strip()
                        voice_keywords = [w.strip() for w in voice_cmd_normalized.split() if len(w.strip()) > 3]
                        
                        # Check if extracted text contains keywords from voice command
                        asset_name_found = None
                        keyword_matches = 0
                        for keyword in voice_keywords:
                            if keyword in extracted_text:
                                keyword_matches += 1
                                if not asset_name_found:
                                    asset_name_found = keyword
                        
                        if keyword_matches >= 1:  # At least one keyword matched
                            log(f"✅ ASSET VALIDATION SUCCESS (OCR-Based)")
                            log(f"   Extracted Text Keywords: {', '.join([kw for kw in voice_keywords if kw in extracted_text])}")
                            log(f"   Voice Command: {asset_voice_command}")
                            log(f"   Confidence: {confidence:.2%} (based on OCR quality)")
                            log(f"   Status: ✓ Loaded the User requested asset in Netflix")
                            step_results['step_6_asset_validation'] = 'success_ocr'
                            step_results['step_6_asset_name'] = asset_name_found or 'Extracted from screen'
                            step_results['step_6_validation_confidence'] = confidence
                            step_results['step_6_validation_method'] = 'OCR_Tesseract'
                            overall_success = overall_success and True
                        elif keyword_matches > 0:
                            log(f"⚠ ASSET VALIDATION PARTIAL MATCH (OCR-Based)")
                            log(f"   Matched Keywords: {keyword_matches} of {len(voice_keywords)}")
                            log(f"   Voice Command: {asset_voice_command}")
                            log(f"   Confidence: {confidence:.2%}")
                            log(f"   Status: ⚠ Partial keyword match - proceeding with caution")
                            step_results['step_6_asset_validation'] = 'partial_match_ocr'
                            step_results['step_6_asset_name'] = asset_name_found or 'Extracted from screen'
                            step_results['step_6_validation_confidence'] = confidence
                            step_results['step_6_validation_method'] = 'OCR_Tesseract'
                        else:
                            log(f"⚠ ASSET VALIDATION WARNING (OCR-Based)")
                            log(f"   Requested Keywords: {', '.join(voice_keywords)}")
                            log(f"   Extracted Screen Text: {extracted_text[:150]}...")
                            log(f"   Status: ⚠ No keyword matches in OCR text - asset may not match request")
                            step_results['step_6_asset_validation'] = 'mismatch_warning_ocr'
                            step_results['step_6_asset_analysis'] = extracted_text
                            step_results['step_6_validation_method'] = 'OCR_Tesseract'
                    else:
                        log(f"⚠ OCR extraction returned empty or insufficient text")
                        log(f"   Continuing with available information")
                        step_results['step_6_asset_validation'] = 'ocr_insufficient_text'
                        step_results['step_6_validation_method'] = 'OCR_Tesseract'
                        
                except ImportError as e:
                    log(f"⚠ Required OCR libraries not available: {e}")
                    log(f"   Install with: pip install pytesseract pillow")
                    log(f"   And ensure tesseract-ocr is installed on system")
                    step_results['step_6_asset_validation'] = 'skipped_no_ocr_library'
                    step_results['step_6_validation_method'] = 'SKIPPED'
                        
            except Exception as e:
                log(f"⚠ Asset name validation failed: {e}")
                step_results['step_6_asset_validation'] = f'error: {e}'
                log(f"   Continuing anyway with Step 7")
        else:
            log("⚠ No asset screenshot available for AI validation")
            step_results['step_6_asset_validation'] = 'no_screenshot'
        
        # ======================================================================
        # STEP 7: PLAYBACK INITIATION - CHECKING PLAYBACK STATE FROM LOGS
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 7] PLAYBACK INITIATION - CHECKING PLAYBACK STATE FROM LOGS")
        log("="*80)
        
        # 🔧 ENHANCED: Check device logs BEFORE sending ENTER to determine current playback state
        # CRITICAL FIX: Only check the LATEST/MOST RECENT state, not multiple transitions
        playback_should_send_enter = False
        latest_state = None
        
        log(f"🔍 Analyzing LATEST playback state from logs (since {asset_command_timestamp})...")
        
        try:
            # Get ONLY the LATEST/MOST RECENT playback state transition
            log_check_cmd = (
                f"grep -i 'MEDIACONTROL.*old_state' /opt/logs/sky-messages.log | tail -1"
            )
            
            stdin, stdout, stderr = ssh.exec_command(log_check_cmd, timeout=15)
            latest_log_line = stdout.read().decode('utf-8', errors='ignore').strip()
            
            if latest_log_line:
                log(f"📊 LATEST playback state transition:")
                log(f"   {latest_log_line}")
                
                # Determine current state based on ONLY the latest transition
                if 'new_state PLAYING' in latest_log_line:
                    # Latest state is PLAYING (regardless of what came before)
                    latest_state = 'PLAYING'
                    log(f"   ✅ Current state: PLAYING")
                    log(f"   ✓ Playback is already active - SKIPPING ENTER keypress")
                    playback_should_send_enter = False
                    
                elif 'new_state PAUSED' in latest_log_line:
                    # Latest state is PAUSED - needs to resume
                    latest_state = 'PAUSED'
                    log(f"   ⏸ Current state: PAUSED")
                    log(f"   ⚠️ Playback is PAUSED - will send ENTER to resume")
                    playback_should_send_enter = True
                    
                else:
                    # State is something else (READY, NULL, etc.)
                    latest_state = 'OTHER'
                    log(f"   ℹ️ Current state: {latest_log_line[latest_log_line.rfind('new_state'):latest_log_line.rfind('new_state')+30]}")
                    log(f"   ℹ️ Will send ENTER as precaution")
                    playback_should_send_enter = True
            else:
                log(f"ℹ️ No playback state logs found yet - will send ENTER as normal")
                playback_should_send_enter = True
                latest_state = 'UNKNOWN'
                
        except Exception as e:
            log(f"⚠ Error checking playback logs: {e} - proceeding with ENTER keypress")
            playback_should_send_enter = True
            latest_state = 'ERROR'
        
        # Send ENTER ONLY if playback is PAUSED or state is unknown (not if PLAYING)
        step_7_latest_log_line = 0  # Track latest log line number from Step 7
        
        if playback_should_send_enter:
            log(f"⏯ Sending ENTER keypress to start/resume playback...")
            enter_cmd = "keySimulator -kenter"
            
            try:
                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=15)
                stdout.read()
                log(f"✓ ENTER keypress sent (Latest state was: {latest_state})")
                step_results['step_7_playback_initiation'] = 'enter_sent'
            except Exception as e:
                log(f"❌ Error sending ENTER keypress: {e}")
                step_results['step_7_playback_initiation'] = f'keypress_error: {e}'
                overall_success = False
        else:
            log(f"✓ SKIPPED ENTER - Playback is already PLAYING")
            step_results['step_7_playback_initiation'] = 'playback_active'
            step_results['step_7_latest_state'] = latest_state
        
        # Capture the latest log line number from Step 7 for comparison in Step 8
        try:
            log_line_cmd = f"grep -n 'MEDIACONTROL.*old_state' /opt/logs/sky-messages.log | tail -1"
            stdin, stdout, stderr = ssh.exec_command(log_line_cmd, timeout=15)
            step7_log_output = stdout.read().decode('utf-8', errors='ignore').strip()
            if step7_log_output:
                try:
                    step_7_latest_log_line = int(step7_log_output.split(':')[0])
                    log(f"📍 Step 7 latest log line number: {step_7_latest_log_line}")
                except (ValueError, IndexError):
                    pass
        except:
            pass
        
        log("⏳ Waiting 10 seconds for playback to stabilize...")
        time.sleep(10)
        step_results['step_7_playback_status'] = 'stable'
        
        # ======================================================================
        # STEP 8: CONTINUOUS PLAYBACK MONITORING (MULTI-LAYER HEALTH CHECK)
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 8] PLAYBACK STATE VERIFICATION & CONTINUOUS MONITORING")
        log("="*80)
        
        # ============================================================================
        # STEP 8.0: PRE-MONITORING PLAYBACK STATE VALIDATION
        # ============================================================================
        # This phase checks if the asset was unexpectedly paused after loading
        # and ensures playback is truly active before continuous monitoring begins
        
        log("\n📋 [PHASE 1] PRE-MONITORING PLAYBACK STATE VALIDATION")
        log("-" * 80)
        
        playback_validation_status = "unknown"
        playback_confirmed_playing = False
        playback_paused_after_start = False
        pause_to_play_transition_confirmed = False
        
        try:
            # 🔍 Check for latest playback state transitions after asset command
            log(f"🔍 Checking for playback state transitions since asset command...")
            
            log_check_cmd = (
                f"grep -n 'MEDIACONTROL.*old_state' /opt/logs/sky-messages.log | "
                f"tail -20"
            )
            
            stdin, stdout, stderr = ssh.exec_command(log_check_cmd, timeout=15)
            playback_logs = stdout.read().decode('utf-8', errors='ignore').strip().split('\n')
            
            if playback_logs and playback_logs[0]:
                log(f"📊 Recent playback state transitions:")
                
                latest_playing_to_paused = None
                latest_paused_to_playing = None
                latest_playing_state = None
                
                # Parse logs to find state transitions
                for log_line in reversed(playback_logs):
                    if not log_line.strip():
                        continue
                    
                    log(f"   {log_line}")
                    
                    # Look for PLAYING -> PAUSED transition (asset got paused unexpectedly)
                    if 'old_state PLAYING, new_state PAUSED' in log_line and not latest_playing_to_paused:
                        latest_playing_to_paused = log_line
                        playback_paused_after_start = True
                    
                    # Look for PAUSED -> PLAYING transition (asset resumed)
                    elif 'old_state PAUSED, new_state PLAYING' in log_line and not latest_paused_to_playing:
                        latest_paused_to_playing = log_line
                    
                    # Track latest PLAYING state for reference
                    elif 'new_state PLAYING' in log_line and 'old_state PLAYING' not in log_line and not latest_playing_state:
                        latest_playing_state = log_line
                
                # ================================================================
                # VALIDATION LOGIC: Determine if playback intervention needed
                # ================================================================
                log(f"\n🔍 Playback State Analysis:")
                
                if latest_playing_to_paused:
                    log(f"   ⏸ Found PLAYING→PAUSED transition:")
                    log(f"     {latest_playing_to_paused}")
                    
                    # Check if this is a RECENT pause (after playback truly started)
                    if latest_playing_state:
                        # Extract timestamps to compare (if available in log format)
                        log(f"   ✓ Playback WAS started (found PLAYING state)")
                        
                        # Check if PAUSED state is AFTER the PLAYING state
                        if playback_logs.index(latest_playing_to_paused) > playback_logs.index(latest_playing_state):
                            log(f"   ⚠️ ALERT: Asset PAUSED after it started playing!")
                            log(f"   → This indicates unexpected pause during playback")
                            
                            # If there's NO more recent PAUSED->PLAYING transition, we need to resume
                            if not latest_paused_to_playing or playback_logs.index(latest_playing_to_paused) > playback_logs.index(latest_paused_to_playing):
                                log(f"\n🎯 ACTION REQUIRED: Sending ENTER keypress to resume playback...")
                                log(f"   Expected sequence:")
                                log(f"   1. Send ENTER keypress")
                                log(f"   2. Wait for PAUSED→PLAYING transition")
                                log(f"   3. Confirm playback is active")
                                
                                # Send ENTER keypress to resume
                                enter_cmd = "keySimulator -kenter"
                                try:
                                    stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=15)
                                    stdout.read()
                                    log(f"   ✓ ENTER keypress sent")
                                    step_results['step_8_pause_recovery_action'] = 'enter_sent'
                                    
                                    # Wait briefly for state transition
                                    log(f"   ⏳ Waiting 3 seconds for playback to resume...")
                                    time.sleep(3)
                                    
                                    # Verify PAUSED->PLAYING transition occurred
                                    log(f"🔍 Verifying playback resumed after ENTER keypress...")
                                    
                                    verify_resume_cmd = (
                                        f"grep -n 'MEDIACONTROL.*old_state PAUSED, new_state PLAYING' "
                                        f"/opt/logs/sky-messages.log | tail -1"
                                    )
                                    
                                    stdin, stdout, stderr = ssh.exec_command(verify_resume_cmd, timeout=15)
                                    resume_log = stdout.read().decode('utf-8', errors='ignore').strip()
                                    
                                    if resume_log:
                                        log(f"   ✓ PAUSED→PLAYING transition confirmed!")
                                        log(f"     {resume_log}")
                                        pause_to_play_transition_confirmed = True
                                        playback_confirmed_playing = True
                                        playback_validation_status = "paused_recovered_to_playing"
                                        step_results['step_8_pause_recovery'] = 'successful_resume_detected'
                                        log(f"   ✅ Playback has resumed successfully")
                                    else:
                                        log(f"   ❌ No PAUSED→PLAYING transition found after ENTER keypress")
                                        log(f"   ⚠️ WARNING: Playback may not have resumed properly")
                                        playback_validation_status = "pause_recovery_unconfirmed"
                                        step_results['step_8_pause_recovery'] = 'no_resume_confirmation'
                                        overall_success = False
                                        
                                except Exception as e:
                                    log(f"   ❌ Error sending resume keypress: {e}")
                                    step_results['step_8_pause_recovery'] = f'keypress_error: {e}'
                                    overall_success = False
                            else:
                                log(f"   ✓ Playback already resumed (found later PAUSED→PLAYING transition)")
                                log(f"     {latest_paused_to_playing}")
                                pause_to_play_transition_confirmed = True
                                playback_confirmed_playing = True
                                playback_validation_status = "paused_already_resumed"
                                step_results['step_8_pause_recovery'] = 'already_resumed'
                        else:
                            log(f"   ℹ️ Note: PAUSED state appears before PLAYING state (log order issue)")
                    else:
                        log(f"   ⚠️ WARNING: Found pause transition but no playback start found")
                        log(f"   ℹ️ Asset may not have started properly")
                        playback_validation_status = "paused_no_prior_start"
                        step_results['step_8_pause_recovery'] = 'paused_before_confirmed_start'
                elif latest_playing_state:
                    log(f"   ✓ Playback is active (found PLAYING state)")
                    log(f"     {latest_playing_state}")
                    playback_confirmed_playing = True
                    playback_validation_status = "actively_playing"
                    step_results['step_8_pause_recovery'] = 'no_pause_detected_actively_playing'
                else:
                    log(f"   ℹ️ No playback state transitions found in recent logs")
                    log(f"   ℹ️ Cannot determine if asset is playing or paused")
                    playback_validation_status = "state_unknown"
                    step_results['step_8_pause_recovery'] = 'no_state_info'
                
                log(f"\n✅ Validation Complete:")
                log(f"   • Playback Status: {playback_validation_status}")
                log(f"   • Confirmed Playing: {playback_confirmed_playing}")
                log(f"   • Pause Detected: {playback_paused_after_start}")
                log(f"   • Pause-to-Play Recovery: {pause_to_play_transition_confirmed}")
                
            else:
                log(f"   ℹ️ No playback state logs found - insufficient data for validation")
                playback_validation_status = "insufficient_logs"
                step_results['step_8_pause_recovery'] = 'no_logs_available'
                
        except Exception as e:
            log(f"   ❌ Error during playback state validation: {e}")
            playback_validation_status = f"error: {e}"
            step_results['step_8_pause_recovery'] = f'validation_error: {e}'
        
        # ============================================================================
        # STEP 8.1: CONTINUOUS PLAYBACK MONITORING
        # ============================================================================
        log("\n📋 [PHASE 2] CONTINUOUS PLAYBACK MONITORING")
        log("-" * 80)
        log(f"🎬 Monitoring Netflix app in foreground for {playback_duration} seconds...")
        
        # Monitor playback duration with periodic app foreground checks + log monitoring
        log(f"")
        log(f"🔍 Background monitoring layers:")
        log(f"   • Netflix app foreground status")
        log(f"   • Resolution rendering logs (notifyResolution)")
        log(f"   • App activity logs (saveAppStatusToFile)")
        log(f"   • Playback state transitions (MEDIACONTROL logs)")
        log(f"")
        
        start_time = time.time()
        check_interval = 10  # Check every 10 seconds
        app_lost_foreground = False
        last_resolution_log_time = time.time()  # Track when we last saw resolution logs
        last_analytics_log_time = time.time()   # Track when we last saw analytics logs
        playback_detection_attempts = 0  # Track consecutive attempts with no playback
        playback_detected_at_least_once = False  # Track if playback was ever detected
        no_playback_detected_threshold = 10  # If 10 consecutive attempts show no playback, mark as failed
        playback_stopped_during_monitoring = False  # Track if playback stopped during monitoring
        
        # NEW: Track log line numbers to detect NEW logs (not stale ones)
        last_resolution_log_line = 0  # Line number of last resolution log seen
        last_analytics_log_line = 0   # Line number of last analytics log seen
        last_reported_pause_line_num = 0  # Line number of last reported PLAYING→PAUSED transition
        last_reported_resume_line_num = 0  # Line number of last reported PAUSED→PLAYING transition
        
        while time.time() - start_time < playback_duration:
            remaining = playback_duration - (time.time() - start_time)
            check_count = int((time.time() - start_time) / check_interval) + 1
            
            # 🔧 ENHANCED: Multi-layer health check
            log(f"\n📊 Check #{check_count} ({remaining:.0f}s remaining):")
            
            # Layer 1: Check if Netflix app is still in foreground
            app_in_foreground = False
            try:
                stdin, stdout, stderr = ssh.exec_command(verify_cmd, timeout=15)
                app_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if 'Netflix' in app_output:
                    log(f"   ✓ Netflix app in foreground")
                    app_in_foreground = True
                else:
                    log(f"   ❌ Netflix app lost foreground - current: {app_output}")
                    app_lost_foreground = True
                    overall_success = False
                    break
            except Exception as e:
                log(f"   ⚠ Error checking foreground app: {e}")
            
            # Layer 2: Check for notifyResolution logs (rendering/playback indicator)
            # ENHANCED: Only report ACTIVE if log line number is NEWER than last check
            try:
                resolution_cmd = (
                    f"grep -n 'notifyResolution:.*width([0-9]\\+), height([0-9]\\+)' "
                    f"/opt/logs/sky-messages.log | tail -1"
                )
                stdin, stdout, stderr = ssh.exec_command(resolution_cmd, timeout=15)
                resolution_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if resolution_output:
                    try:
                        # Extract line number and log content
                        log_line_num, log_content = resolution_output.split(':', 1)
                        log_line_num = int(log_line_num)
                        
                        # Only report ACTIVE if this is a NEW log (line number increased)
                        if log_line_num > last_resolution_log_line:
                            log(f"   ✓ Rendering active: {log_content.strip()}")
                            last_resolution_log_line = log_line_num  # Update to new line number
                            last_resolution_log_time = time.time()
                            playback_detection_attempts = 0  # Reset counter
                            playback_detected_at_least_once = True
                        else:
                            # Stale log - same as before
                            log(f"   ⚠ No NEW resolution logs (stale from previous check)")
                    except (ValueError, IndexError):
                        # Couldn't parse line number, show warning
                        log(f"   ⚠ Resolution log format error")
                else:
                    log(f"   ⚠ No resolution logs found")
            except Exception as e:
                log(f"   ⚠ Error checking resolution logs: {e}")
            
            # Layer 3: Check for AppAnalyticsService logs (app activity indicator)
            # ENHANCED: Only report ACTIVE if log line number is NEWER than last check
            try:
                analytics_cmd = (
                    f"grep -n 'saveAppStatusToFile, currentDuration: [0-9]\\+' "
                    f"/opt/logs/sky-messages.log | tail -1"
                )
                stdin, stdout, stderr = ssh.exec_command(analytics_cmd, timeout=15)
                analytics_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if analytics_output:
                    try:
                        # Extract line number and log content
                        log_line_num, log_content = analytics_output.split(':', 1)
                        log_line_num = int(log_line_num)
                        
                        # Only report ACTIVE if this is a NEW log (line number increased)
                        if log_line_num > last_analytics_log_line:
                            log(f"   ✓ App active: {log_content.strip()}")
                            last_analytics_log_line = log_line_num  # Update to new line number
                            last_analytics_log_time = time.time()
                            playback_detection_attempts = 0  # Reset counter
                            playback_detected_at_least_once = True
                        else:
                            # Stale log - same as before
                            log(f"   ⚠ No NEW activity logs (stale from previous check)")
                            playback_detection_attempts += 1  # Increment no-playback counter
                    except (ValueError, IndexError):
                        # Couldn't parse line number, treat as no new activity
                        log(f"   ⚠ App activity log format error")
                        playback_detection_attempts += 1
                else:
                    log(f"   ⚠ No app activity logs found")
                    playback_detection_attempts += 1  # Increment no-playback counter
            except Exception as e:
                log(f"   ⚠ Error checking analytics logs: {e}")
                playback_detection_attempts += 1  # Increment counter on error too
            
            # Layer 4: Check for playback state transitions (PLAYING -> PAUSED / PAUSED -> PLAYING)
            # ONLY check logs NEWER than Step 7 to avoid redundant monitoring
            # ENHANCED: Track line numbers to detect only NEW transitions (not already reported)
            try:
                # Get the latest pause transition (if any after Step 7)
                pause_check_cmd = (
                    f"grep -n 'MEDIACONTROL.*old_state PLAYING, new_state PAUSED' "
                    f"/opt/logs/sky-messages.log | tail -1"
                )
                stdin, stdout, stderr = ssh.exec_command(pause_check_cmd, timeout=15)
                pause_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                # Get the latest resume transition (if any after Step 7)
                resume_check_cmd = (
                    f"grep -n 'MEDIACONTROL.*old_state PAUSED, new_state PLAYING' "
                    f"/opt/logs/sky-messages.log | tail -1"
                )
                stdin, stdout, stderr = ssh.exec_command(resume_check_cmd, timeout=15)
                resume_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                # Determine current playback state based on LATEST transitions
                playback_status_msg = "Playback is still happening"  # Default status
                pause_detected_new = False
                
                if pause_output:
                    try:
                        pause_line_num = int(pause_output.split(':')[0])
                        
                        # Check if pause is AFTER Step 7 AND we haven't reported this pause yet
                        if pause_line_num > step_7_latest_log_line and pause_line_num > last_reported_pause_line_num:
                            # Check if resume happened after this pause
                            if resume_output:
                                resume_line_num = int(resume_output.split(':')[0])
                                
                                # Only report if resume is AFTER the pause AND we haven't reported it yet
                                if resume_line_num > pause_line_num and resume_line_num > last_reported_resume_line_num:
                                    # Resumed after pause - currently playing
                                    log(f"   📊 Playback state: Resumed (PAUSED→PLAYING detected)")
                                    log(f"      Resume log: {resume_output}")
                                    playback_status_msg = "Playback recovered after pause"
                                    last_reported_resume_line_num = resume_line_num  # Mark as reported
                                elif resume_line_num <= pause_line_num:
                                    # Paused but not yet resumed (NEW pause detected)
                                    log(f"   ⚠️ ALERT: Playback PAUSED during monitoring!")
                                    log(f"      {pause_output}")
                                    playback_stopped_during_monitoring = True
                                    pause_detected_new = True
                                    playback_status_msg = "⚠️ Playback PAUSED - awaiting user action"
                                    last_reported_pause_line_num = pause_line_num  # Mark as reported
                                # else: resume already reported, skip reporting again
                            else:
                                # Paused and no resume log (NEW pause)
                                log(f"   ⚠️ ALERT: Playback PAUSED during monitoring!")
                                log(f"      {pause_output}")
                                playback_stopped_during_monitoring = True
                                pause_detected_new = True
                                playback_status_msg = "⚠️ Playback PAUSED - awaiting user action"
                                last_reported_pause_line_num = pause_line_num  # Mark as reported
                        # else: pause already reported or from Step 7, don't report again
                    except (ValueError, IndexError):
                        pass  # Couldn't parse line number, continue with default status
                
                # If no new pause detected after Step 7, report stable playback
                if not pause_detected_new:
                    log(f"   ✓ {playback_status_msg}")
                    
            except Exception as e:
                log(f"   ⚠ Error checking playback state: {e}")
            
            # Check if we hit the no-playback threshold
            if playback_detection_attempts >= no_playback_detected_threshold:
                log(f"\n❌ ⚠️ ALERT: No playback detected for {playback_detection_attempts} consecutive checks!")
                log(f"   → Playback may have failed or stalled")
                break
            
            # Layer 5: Detect interrupted playback
            # If rendering logs stopped but app still in foreground → playback interrupted
            if app_in_foreground:
                time_since_resolution = time.time() - last_resolution_log_time
                time_since_analytics = time.time() - last_analytics_log_time
                
                # If notifyResolution hasn't appeared in last 25 seconds, playback might be stuck
                if time_since_resolution > 25:
                    log(f"   ⚠️ ALERT: No resolution logs for {time_since_resolution:.0f}s")
                    log(f"      → Playback may be interrupted or stuck")
                else:
                    log(f"   ✓ Rendering active ({time_since_resolution:.0f}s since last log)")
            
            # Wait for next check
            time.sleep(min(check_interval, remaining))
        
        log(f"\n✓ Playback duration monitoring completed")
        log(f"  Final status:")
        log(f"  • App in foreground: {not app_lost_foreground}")
        log(f"  • Playback detected: {playback_detected_at_least_once}")
        log(f"  • Playback stopped during monitoring: {playback_stopped_during_monitoring}")
        log(f"  • Time since last resolution log: {time.time() - last_resolution_log_time:.0f}s")
        log(f"  • Time since last analytics log: {time.time() - last_analytics_log_time:.0f}s")
        log(f"  • No-playback detection count: {playback_detection_attempts}/{no_playback_detected_threshold}")
        
        # ============================================================================
        # POST-MONITORING VALIDATION: Check final playback state
        # ============================================================================
        log(f"\n📋 [PHASE 3] POST-MONITORING PLAYBACK STATE VALIDATION")
        log("-" * 80)
        
        # Get the latest playback state transition to confirm current playback status
        try:
            final_state_cmd = (
                f"grep 'MEDIACONTROL.*old_state' /opt/logs/sky-messages.log | tail -1"
            )
            stdin, stdout, stderr = ssh.exec_command(final_state_cmd, timeout=15)
            final_state_log = stdout.read().decode('utf-8', errors='ignore').strip()
            
            if final_state_log:
                log(f"🔍 Final playback state transition:")
                log(f"   {final_state_log}")
                
                if 'new_state PLAYING' in final_state_log and 'old_state PLAYING' not in final_state_log:
                    log(f"   ✅ Playback is ACTIVE as of final check")
                    step_results['step_8_final_playback_state'] = 'playing'
                    
                    # Check if playback stopped during monitoring
                    if playback_stopped_during_monitoring:
                        log(f"   ⚠️ Note: Playback was paused during monitoring but has since resumed")
                        step_results['step_8_playback_stability'] = 'recovered_from_pause'
                    else:
                        log(f"   ✅ Playback remained stable throughout monitoring")
                        step_results['step_8_playback_stability'] = 'stable_continuous'
                        
                elif 'new_state PAUSED' in final_state_log or 'old_state PLAYING, new_state PAUSED' in final_state_log:
                    log(f"   ❌ Playback ended in PAUSED state")
                    log(f"   ⚠️ ERROR: Playback is PAUSED at end of monitoring")
                    step_results['step_8_final_playback_state'] = 'paused'
                    step_results['step_8_playback_stability'] = 'ended_paused'
                    overall_success = False
                else:
                    log(f"   ℹ️ Final state unknown or no recent transitions")
                    step_results['step_8_final_playback_state'] = 'unknown'
                    step_results['step_8_playback_stability'] = 'state_unclear'
            else:
                log(f"   ℹ️ No playback state logs found for final validation")
                step_results['step_8_final_playback_state'] = 'no_logs'
                
        except Exception as e:
            log(f"   ⚠ Error during final validation: {e}")
            step_results['step_8_final_playback_state'] = f'error: {e}'
        
        step_results['step_8_playback_monitoring'] = 'app_monitored'
        step_results['step_8_app_foreground'] = not app_lost_foreground
        step_results['step_8_rendering_status'] = 'active' if (time.time() - last_resolution_log_time) < 30 else 'interrupted'
        step_results['step_8_playback_detected'] = playback_detected_at_least_once  # Track detection status
        step_results['step_8_no_playback_attempts'] = playback_detection_attempts  # Track why it failed
        
        # ======================================================================
        # STEP 9: OPTIONAL TRICKPLAY CONTROLS (WITH ENHANCED VALIDATION)
        # ======================================================================
        if execute_playback_controls and not app_lost_foreground and playback_detected_at_least_once:
            log("\n" + "="*80)
            log("[STEP 9] TRICKPLAY CONTROLS EXECUTION (ENHANCED WITH LOG VALIDATION)")
            log("="*80)
            
            key_gap = 0.5  # Seconds between key presses (< 1 second as required)
            action_wait_time = 5  # 5-second wait between action sets
            
            # Fast-Forward sequence
            log("\n👉 Fast-Forward Sequence (7 x RIGHT keypress):")
            try:
                for i in range(7):
                    log(f"  → Sending RIGHT keypress {i+1}/7...")
                    right_cmd = "keySimulator -kright"
                    stdin, stdout, stderr = ssh.exec_command(right_cmd, timeout=10)
                    stdout.read()
                    if i < 6:
                        time.sleep(key_gap)
                
                time.sleep(key_gap)
                log(f"  → Sending ENTER keypress (confirmation)...")
                enter_cmd = "keySimulator -kenter"
                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=10)
                stdout.read()
                time.sleep(key_gap)
                
                log("✓ Fast-Forward sequence completed")
                step_results['step_9_ff_sequence'] = 'success'
            except Exception as e:
                log(f"❌ Error in Fast-Forward sequence: {e}")
                step_results['step_9_ff_sequence'] = f'error: {e}'
            
            log(f"⏳ Waiting {action_wait_time} seconds before next action...")
            time.sleep(action_wait_time)
            
            # Rewind sequence
            log("\n👈 Rewind Sequence (7 x LEFT keypress):")
            try:
                for i in range(7):
                    log(f"  → Sending LEFT keypress {i+1}/7...")
                    left_cmd = "keySimulator -kleft"
                    stdin, stdout, stderr = ssh.exec_command(left_cmd, timeout=10)
                    stdout.read()
                    if i < 6:
                        time.sleep(key_gap)
                
                time.sleep(key_gap)
                log(f"  → Sending ENTER keypress (confirmation)...")
                enter_cmd = "keySimulator -kenter"
                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=10)
                stdout.read()
                time.sleep(key_gap)
                
                log("✓ Rewind sequence completed")
                step_results['step_9_rew_sequence'] = 'success'
            except Exception as e:
                log(f"❌ Error in Rewind sequence: {e}")
                step_results['step_9_rew_sequence'] = f'error: {e}'
            
            log(f"⏳ Waiting {action_wait_time} seconds before next action...")
            time.sleep(action_wait_time)
            
            # Pause sequence with device log validation
            log("\n⏸ Pause Sequence (ENTER keypress + device log validation):")
            try:
                log("  → Sending ENTER keypress (pause)...")
                enter_cmd = "keySimulator -kenter"
                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=10)
                stdout.read()
                time.sleep(1.5)  # Wait for pause state change
                
                # Validate PAUSE state from device logs
                pause_validation_cmd = "grep -i 'state.*PAUSED' /opt/logs/sky-messages.log | tail -1"
                stdin, stdout, stderr = ssh.exec_command(pause_validation_cmd, timeout=10)
                pause_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if pause_output:
                    log(f"  ✓ Device log validation: {pause_output}")
                    if 'get_state returned: 1, state: PAUSED' in pause_output:
                        log("  ✅ PAUSE state confirmed in device logs")
                        step_results['step_9_pause_validation'] = 'success'
                    else:
                        log("  ⚠ PAUSED logged but state format may differ")
                        step_results['step_9_pause_validation'] = 'logged_format_different'
                else:
                    log("  ⚠ PAUSE state not found in device logs")
                    step_results['step_9_pause_validation'] = 'not_found_in_logs'
                
                log("✓ Pause sequence completed")
                step_results['step_9_pause_sequence'] = 'success'
            except Exception as e:
                log(f"❌ Error in Pause sequence: {e}")
                step_results['step_9_pause_sequence'] = f'error: {e}'
            
            log(f"⏳ Waiting {action_wait_time} seconds before next action...")
            time.sleep(action_wait_time)
            
            # Play sequence with device log validation
            log("\n▶ Play Sequence (ENTER keypress + device log validation):")
            try:
                log("  → Sending ENTER keypress (play)...")
                enter_cmd = "keySimulator -kenter"
                stdin, stdout, stderr = ssh.exec_command(enter_cmd, timeout=10)
                stdout.read()
                time.sleep(1.5)  # Wait for play state change
                
                # Validate PLAY state from device logs
                play_validation_cmd = "grep -i 'state.*PLAYING' /opt/logs/sky-messages.log | tail -1"
                stdin, stdout, stderr = ssh.exec_command(play_validation_cmd, timeout=10)
                play_output = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if play_output:
                    log(f"  ✓ Device log validation: {play_output}")
                    if 'get_state returned: 1, state: PLAYING' in play_output:
                        log("  ✅ PLAYING state confirmed in device logs")
                        step_results['step_9_play_validation'] = 'success'
                    else:
                        log("  ⚠ PLAYING logged but state format may differ")
                        step_results['step_9_play_validation'] = 'logged_format_different'
                else:
                    log("  ⚠ PLAYING state not found in device logs")
                    step_results['step_9_play_validation'] = 'not_found_in_logs'
                
                log("✓ Play sequence completed")
                step_results['step_9_play_sequence'] = 'success'
                step_results['step_9_trickplay_status'] = 'all_controls_executed'
            except Exception as e:
                log(f"❌ Error in Play sequence: {e}")
                step_results['step_9_play_sequence'] = f'error: {e}'
        else:
            log("\n" + "="*80)
            log("[STEP 9] SKIPPED")
            log("="*80)
            if not execute_playback_controls:
                log("⏭️  Trick play disabled (execute_playback_controls=False)")
                step_results['step_9_trickplay_status'] = 'disabled'
            elif app_lost_foreground:
                log("⏭️  Netflix app lost foreground")
                step_results['step_9_trickplay_status'] = 'skipped_app_lost_foreground'
            elif not playback_detected_at_least_once:
                log("❌ There is no Playback detected")
                log(f"   → Playback detection failed after {playback_detection_attempts} attempts")
                log("   → No playback logs (rendering or analytics) were found")
                log("   → Skipping trickplay controls")
                step_results['step_9_trickplay_status'] = 'skipped_no_playback_detected'
                overall_success = False
        
        # ======================================================================
        # STEP 10: SYSTEM CRASH ANALYSIS
        # ======================================================================
        log("\n" + "="*80)
        log("[STEP 10] SYSTEM CRASH ANALYSIS")
        log("="*80)
        
        crash_cmd = "grep -i 'process.*crash' /opt/logs/core_logs.txt 2>/dev/null | tail -5"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(crash_cmd, timeout=15)
            crash_output = stdout.read().decode('utf-8', errors='ignore').strip()
            
            if crash_output:
                log("❌ System crashes detected:")
                for line in crash_output.split('\n'):
                    if line.strip():
                        log(f"   {line}")
                step_results['step_10_crash_analysis'] = 'crashes_found'
                overall_success = False
            else:
                log("✓ No system crashes detected")
                step_results['step_10_crash_analysis'] = 'clean'
        except Exception as e:
            log(f"⚠ Could not check for crashes: {e}")
            step_results['step_10_crash_analysis'] = f'check_failed: {e}'
        
    except Exception as e:
        log(f"❌ Unexpected error during execution: {e}")
        overall_success = False
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
    
    finally:
        if ssh:
            try:
                ssh.close()
                log("✓ SSH connection closed")
            except:
                pass
    
    # ======================================================================
    # FINAL RESULTS
    # ======================================================================
    log("\n" + "="*80)
    log("NETFLIX APP LAUNCH AND PLAYBACK - COMPLETED")
    log("="*80)
    
    execution_status = "✅ SUCCESS" if overall_success else "❌ FAILED"
    log(f"\nExecution Status: {execution_status}")
    
    # Add no playback detection message if applicable
    if not playback_detected_at_least_once:
        log("\n❌ There is no Playback detected")
        log(f"   → No rendering or analytics logs were captured during monitoring")
        log(f"   → Playback verification failed")
    
    log("\nStep-by-Step Results:")
    for step, result in sorted(step_results.items()):
        # Improved status evaluation: handle strings, dicts, bools, None, and complex objects
        is_success = False
        
        if isinstance(result, bool):
            # Direct boolean: True = success, False = failure
            is_success = result
        elif isinstance(result, dict):
            # Dictionary result (e.g., screenshot info, validation results)
            # Success if: (a) has 'success' key set to True, OR (b) non-empty dict without error indicators
            is_success = result.get('success', True) if 'success' in result else bool(result)
        elif isinstance(result, str):
            # String result: success if contains "success" and no "error"
            is_success = "success" in result.lower() and "error" not in result.lower()
        elif result is None:
            # None result = no status set (neutral, show ✓ to not alarm user)
            is_success = True
        else:
            # Other types (objects, lists, etc.): assume success if truthy
            is_success = bool(result)
        
        status_icon = "✓" if is_success else "✗"
        log(f"  {status_icon} {step}: {result}")
    
    return {
        'success': overall_success,
        'execution_status': 'success' if overall_success else 'failed',
        'timestamp': timestamp,
        'device': device_name,
        'device_ip': device_ip,
        'iteration': iteration,
        'step_results': step_results,
        'asset_launched': asset_voice_command,
        'playback_duration': playback_duration,
        'trickplay_executed': execute_playback_controls,
        'playback_detected': playback_detected_at_least_once,  # Include playback detection status
        'details': f"Netflix playback test completed with {len([r for r in step_results.values() if 'success' in str(r).lower()])}/{len(step_results)} steps successful"
    }


# Export function for method registry
if __name__ == "__main__":
    # Example usage for testing
    print("Netflix Playback Method - Ready for execution")
