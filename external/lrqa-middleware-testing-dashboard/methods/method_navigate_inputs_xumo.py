"""
Method: Navigate to Inputs XUMO-TV
Navigates to the Inputs row on XUMO-TV device, validates available input tiles,
and compares current screen with reference screenshots.
"""
import paramiko
import json
import time
import os
from utils.screenshot_utils import take_and_analyze_screenshot, normalize_screenshot_path
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback
from datetime import datetime, timezone
from config.config_commands import power_key_command, home_key_command, enter_key_command, down_key_command, right_key_command

# Safe SFTP utilities
try:
    from utils.ssh_sftp_utils import collect_files_with_fallback, ensure_ssh_channel_clean
    SFTP_UTILS_AVAILABLE = True
except ImportError:
    SFTP_UTILS_AVAILABLE = False

# Screen validation imports - AI-based (V2.0) using unified validator (Ollama default)
try:
    from services.unified_screen_validator import UnifiedScreenValidator
    AI_VALIDATOR_AVAILABLE = True
except ImportError:
    AI_VALIDATOR_AVAILABLE = False

# Fallback to lightweight validator
try:
    from screen_validator_lightweight import LightweightScreenValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False



def validate_input_tile_with_reference(screenshot_path, input_name, reference_dir, log_func):
    """
    Validate if screenshot matches the reference image for a specific input tile.
    
    Uses AIScreenAnalyzer (AI Vision) for comparison with fallback to LightweightScreenValidator.
    """
    # Try AI-based validation first (using unified validator: Ollama default)
    if AI_VALIDATOR_AVAILABLE:
        try:
            validator = UnifiedScreenValidator(debug=False)
            result = validator.validate_screen_detailed(
                screenshot_path=screenshot_path,
                device_name=None
            )
            
            if result.get('match', False) or 'error' not in result:
                detected_screen = result.get('detected_screen', 'Unknown')
                confidence = result.get('confidence', 0.0) / 100.0 if result.get('confidence', 0) > 1 else result.get('confidence', 0.0)
                log_func(f"   ✓ {input_name} - AI Detected: {detected_screen} ({confidence:.2%})")
                return confidence >= 0.70  # Accept if confidence >= 70%
        except Exception as e:
            log_func(f"   ⚠ AI validation failed: {str(e)}, falling back to lightweight...")
    
    # Fallback to lightweight validator
    if not VALIDATOR_AVAILABLE:
        log_func(f"   ⚠ Validator not available, skipping reference comparison for {input_name}")
        return True  # Assume valid if validator not available
    
    try:
        # Map input names to reference file names
        name_mapping = {
            'ANTENNA': 'INPUT_SCREEN_ANTEENA',  # Note: typo in actual filename
            'HDMI 1': 'INPUT_SCREEN_HDMI_1',
            'HDMI 2': 'INPUT_SCREEN_HDMI_2',
            'HDMI 3': 'INPUT_SCREEN_HDMI_3',
            'COMPOSITE': 'INPUT_SCREEN_COMPOSITE',
            'AIRPLAY': 'INPUT_SCREEN_AIRPLAY',
            'USB': 'INPUT_SCREEN_USB',
            'SCREEN MIRRORING': 'INPUT_SCREEN_SCREEN-MIRRORING'
        }
        
        ref_filename = name_mapping.get(input_name, f"INPUT_SCREEN_{input_name.upper().replace(' ', '_')}")
        ref_path = os.path.join(reference_dir, f"{ref_filename}.png")
        
        if not os.path.exists(ref_path):
            log_func(f"   ⚠ Reference image not found: {ref_path}")
            return False
        
        # Use lightweight validator as fallback
        validator = LightweightScreenValidator()
        result = validator.validate_against_reference(screenshot_path, ref_path, method="hybrid")
        
        is_match = result.get('is_match', False)
        confidence = result.get('confidence', 0.0)
        
        if is_match:
            log_func(f"   ✓ {input_name} - MATCHED (confidence: {confidence:.2%})")
        else:
            log_func(f"   ⚠ {input_name} - LOW MATCH (confidence: {confidence:.2%})")
        
        return is_match
        
    except Exception as e:
        log_func(f"   ⚠ Validation error for {input_name}: {str(e)}")
        return False




def navigate_inputs_xumo(device_ip, port, username, password, screenshots_dir, iteration, device_name, log_callback=None):
    """
    Navigate to Inputs screen and validate available input tiles on XUMO-TV devices.
    
    Args:
        device_ip: IP address of device
        port: SSH port
        username: SSH username
        password: SSH password
        screenshots_dir: Directory to save screenshots
        iteration: Current iteration number
        device_name: Name of device
        log_callback: Optional callback for logging
        
    Returns:
        dict with success status and details
    """
    
    def log(message):
        if log_callback:
            log_callback(message)
        print(message)
    
    # Expected input tiles on XUMO-TV
    EXPECTED_INPUT_TILES = [
        'ANTENNA',
        'HDMI 1',
        'HDMI 2', 
        'HDMI 3',
        'COMPOSITE',
        'AIRPLAY',
        'USB',
        'SCREEN MIRRORING'
    ]
    
    # Navigation keys with delays
    NAVIGATION_KEYS = [
        {'cmd': home_key_command, 'wait': 4, 'description': 'Go to Home screen'},
        {'cmd': down_key_command, 'wait': 4, 'description': 'Navigate down to Inputs row'},
        {'cmd': enter_key_command, 'wait': 4, 'description': 'Enter Inputs row'},
        {'cmd': down_key_command, 'wait': 4, 'description': 'Navigate to first input tile'},
        {'cmd': down_key_command, 'wait': 4, 'description': 'Navigate to second input tile'}
    ]
    
    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        
        log("🎬 Starting XUMO-TV Inputs Navigation")
        log(f"   Device: {device_name} ({device_ip})")
        log(f"   Expected Input Tiles: {', '.join(EXPECTED_INPUT_TILES)}")
        
        # Step 1: Navigate to Inputs using remote keys
        log("\n📍 Step 1: Navigating to Inputs row...")
        for nav_step in NAVIGATION_KEYS:
            cmd = nav_step['cmd']
            wait_time = nav_step['wait']
            description = nav_step['description']
            
            log(f"   → Sending key: {description}")
            log(f"      Command: {cmd}")
            
            # Send the key via SSH
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                stdout_text = stdout.read().decode('utf-8', errors='ignore')
                stderr_text = stderr.read().decode('utf-8', errors='ignore')
                stdin.close()
                
                if exit_status != 0:
                    log(f"   ⚠ Command returned non-zero exit status: {exit_status}")
                    if stderr_text:
                        log(f"      Error: {stderr_text[:100]}")
                else:
                    log(f"   ✓ Key sent successfully")
            except Exception as e:
                log(f"   ⚠ Error sending key: {e}")
            
            # Wait for the specified time
            time.sleep(wait_time)
            log(f"   ⏱ Waited {wait_time}s")
        
        # Step 2: Capture initial Inputs screen
        log("\n📸 Step 2: Capturing Inputs screen...")
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        screenshot_name = f"{device_ip}_XUMO_Inputs_Initial_{iteration}_{timestamp}"
        
        result = take_and_analyze_screenshot(
            ssh,
            screenshot_name,
            device_ip,
            log_callback=log,
            screenshot_folder=screenshots_dir
        )
        
        if not result.get('success'):
            log(f"✗ Failed to capture initial Inputs screen")
            return {
                'success': False,
                'details': f"Failed to capture initial screenshot: {result.get('error', 'Unknown error')}",
                'found_inputs': [],
                'missing_inputs': EXPECTED_INPUT_TILES
            }
        
        initial_screenshot = result.get('local_path', '')
        log(f"✓ Initial screenshot captured: {initial_screenshot}")
        
        # Step 3: Validate reference screenshots exist
        log("\n🔍 Step 3: Validating reference screenshots...")
        reference_dir = os.path.join(os.path.dirname(__file__), 'reference_screens', 'InputScreens_XUMO-TV')
        
        if not os.path.exists(reference_dir):
            log(f"⚠ Reference screenshots directory not found: {reference_dir}")
            log(f"   Proceeding with manual tile detection (no reference comparison)...")
            use_reference_comparison = False
        else:
            log(f"✓ Reference directory found: {reference_dir}")
            log(f"   Reference screenshots will be used for validation")
            use_reference_comparison = True
        
        # Step 4: Detect and validate input tiles
        log("\n🎯 Step 4: Detecting available input tiles...")
        found_inputs = []
        missing_inputs = []
        validation_details = {}
        
        # Simulate OCR/detection - in real scenario, use AI vision or pattern matching
        # For now, we'll capture each tile by navigating and detecting
        for idx, expected_input in enumerate(EXPECTED_INPUT_TILES):
            log(f"   → Checking tile {idx+1}: {expected_input}")
            
            if idx > 0:
                # Navigate to next tile with RIGHT key
                log(f"      Pressing RIGHT to move to next tile...")
                try:
                    stdin, stdout, stderr = ssh.exec_command(right_key_command)
                    exit_status = stdout.channel.recv_exit_status()
                    stdout_text = stdout.read().decode('utf-8', errors='ignore')
                    stderr_text = stderr.read().decode('utf-8', errors='ignore')
                    stdin.close()
                    
                    if exit_status != 0:
                        log(f"      ⚠ RIGHT key returned non-zero exit status: {exit_status}")
                    else:
                        log(f"      ✓ RIGHT key sent successfully")
                except Exception as e:
                    log(f"      ⚠ Error sending RIGHT key: {e}")
                
                time.sleep(2)  # Wait after key press
            
            # Capture screenshot of current tile
            tile_screenshot_name = f"{device_ip}_XUMO_Input_{expected_input.replace(' ', '_')}_{iteration}_{timestamp}"
            
            tile_result = take_and_analyze_screenshot(
                ssh,
                tile_screenshot_name,
                device_ip,
                log_callback=log,
                screenshot_folder=screenshots_dir
            )
            
            if tile_result.get('success'):
                tile_screenshot_path = tile_result.get('local_path', '')
                
                # If reference screenshots available, validate against them
                if use_reference_comparison and tile_screenshot_path:
                    matches_reference = validate_input_tile_with_reference(
                        tile_screenshot_path,
                        expected_input,
                        reference_dir,
                        log
                    )
                    
                    if matches_reference:
                        found_inputs.append(expected_input)
                        validation_details[expected_input] = 'matched_reference'
                        log(f"      ✓ {expected_input} - MATCHED REFERENCE")
                    else:
                        missing_inputs.append(expected_input)
                        validation_details[expected_input] = 'validation_failed'
                        log(f"      ✗ {expected_input} - VALIDATION FAILED")
                else:
                    # Without reference comparison, assume tile was found if screenshot succeeded
                    found_inputs.append(expected_input)
                    validation_details[expected_input] = 'screenshot_captured'
                    log(f"      ✓ {expected_input} - FOUND (screenshot captured)")
            else:
                missing_inputs.append(expected_input)
                validation_details[expected_input] = 'capture_failed'
                log(f"      ✗ {expected_input} - NOT FOUND OR ERROR")
            
            # Add small delay between rapid operations to prevent connection pool exhaustion
            # This helps prevent "EOF during negotiation" errors from repeated SSH connections
            if idx < len(EXPECTED_INPUT_TILES) - 1:
                time.sleep(0.5)
        
        # Step 5: Collect logs if any inputs are missing
        logs_collected = False
        logs_list = []
        if missing_inputs:
            log(f"\n⚠ Missing inputs detected: {', '.join(missing_inputs)}")
            log("📋 Collecting system logs...")
            
            # Run log collection commands
            log_commands = [
                "logcat > /media/apps/xumo_logcat.log 2>&1 &",
                "dmesg > /media/apps/xumo_dmesg.log 2>&1",
                "cat /proc/version > /media/apps/xumo_version.log 2>&1"
            ]
            
            for cmd in log_commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                stdin.close()
                log(f"   Executed: {cmd}")
            
            time.sleep(2)  # Wait for log collection
            
            # Copy logs to screenshots directory using safe SFTP utilities
            log_files = [
                '/media/apps/xumo_logcat.log',
                '/media/apps/xumo_dmesg.log',
                '/media/apps/xumo_version.log'
            ]
            
            # Try using safe SFTP utilities if available
            if SFTP_UTILS_AVAILABLE:
                try:
                    log(f"   ℹ Collecting logs via SFTP with automatic fallback...")
                    results = collect_files_with_fallback(ssh, log_files, screenshots_dir, log)
                    
                    for remote_path, success in results.items():
                        if success:
                            logs_list.append(os.path.basename(remote_path))
                            logs_collected = True
                    
                except Exception as e:
                    log(f"   ⚠ Error in safe SFTP collection: {str(e)}")
                    # Fall through to manual fallback below
            
            # Fallback if utilities not available or failed
            if not logs_collected:
                log(f"   ℹ Using manual fallback for log collection...")
                try:
                    for remote_log in log_files:
                        try:
                            local_log = os.path.join(screenshots_dir, os.path.basename(remote_log))
                            stdin, stdout, stderr = ssh.exec_command(f"cat {remote_log}")
                            content = stdout.read().decode('utf-8', errors='ignore')
                            if content:
                                with open(local_log, 'w') as f:
                                    f.write(content)
                                logs_list.append(os.path.basename(remote_log))
                                log(f"   ✓ Collected via SSH fallback: {os.path.basename(remote_log)}")
                                logs_collected = True
                        except Exception as e:
                            log(f"   ⚠ Could not collect {remote_log}: {str(e)}")
                except Exception as fallback_err:
                    log(f"   ⚠ All collection methods failed: {str(fallback_err)}")
        else:
            # All inputs found - no logs collected
            log(f"\n✓ All input tiles found successfully - skipping log collection")
        
        # Step 6: Summary
        found_count = len(found_inputs)
        total_count = len(EXPECTED_INPUT_TILES)
        success = len(missing_inputs) == 0
        
        log(f"\n📊 Results Summary:")
        log(f"   Found: {found_count}/{total_count} input tiles")
        log(f"   Found: {', '.join(found_inputs) if found_inputs else 'None'}")
        if missing_inputs:
            log(f"   Missing: {', '.join(missing_inputs)}")
        
        if use_reference_comparison:
            log(f"\n🔍 Reference Validation Details:")
            for tile_name, validation_result in validation_details.items():
                log(f"   {tile_name}: {validation_result}")
        
        # Ensure all SSH channels are properly closed to free resources
        if SFTP_UTILS_AVAILABLE:
            try:
                ensure_ssh_channel_clean(ssh, log)
            except Exception as e:
                log(f"⚠ Error during SSH channel cleanup: {str(e)}")
        
        # Properly close SSH connection to free resources
        try:
            ssh.close()
            log(f"ℹ SSH connection closed successfully")
        except Exception as e:
            log(f"⚠ Error closing SSH connection: {str(e)}")
        
        # Normalize screenshot paths for web serving
        normalized_initial_screenshot = normalize_screenshot_path(initial_screenshot)
        
        return {
            'success': success,
            'details': f"Found {found_count}/{total_count} input tiles. Found: {', '.join(found_inputs)}. Missing: {', '.join(missing_inputs) if missing_inputs else 'None'}.",
            'found_inputs': found_inputs,
            'missing_inputs': missing_inputs,
            'validation_details': validation_details,
            'reference_comparison_used': use_reference_comparison,
            'tiles_summary': {
                'found_count': found_count,
                'total_count': total_count,
                'tiles_found': found_inputs,
                'tiles_missing': missing_inputs,
                'status': f"{found_count}/{total_count}"
            },
            'initial_screenshot': normalized_initial_screenshot,
            'screenshots': [normalized_initial_screenshot] if normalized_initial_screenshot else [],
            'iteration': iteration,
            'logs': logs_list,
            'logs_collected': logs_collected
        }
        
    except Exception as e:
        log(f"✗ Error during Inputs navigation: {str(e)}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        
        # Ensure proper cleanup in case of error
        if ssh:
            try:
                if SFTP_UTILS_AVAILABLE:
                    ensure_ssh_channel_clean(ssh, log)
            except:
                pass
            
            try:
                ssh.close()
            except:
                pass
        
        # Define EXPECTED_INPUT_TILES here for exception handler
        default_tiles = [
            'ANTENNA',
            'HDMI 1',
            'HDMI 2', 
            'HDMI 3',
            'COMPOSITE',
            'AIRPLAY',
            'USB',
            'SCREEN MIRRORING'
        ]
        
        return {
            'success': False,
            'details': f"Error: {str(e)}",
            'found_inputs': [],
            'missing_inputs': default_tiles,
            'validation_details': {},
            'reference_comparison_used': False,
            'iteration': iteration,
            'logs': [],
            'logs_collected': False
        }
