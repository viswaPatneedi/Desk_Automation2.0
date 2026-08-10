#!/usr/bin/env python3
"""
GDF IR Command Test Process Implementation
For GDF_RACK devices using ECATS REST API
Handles IR key presses for XUMO (PR1_T2) and SKYSTREAM (LC103) devices
"""

import requests
import time
from datetime import datetime, timezone
from methods.method_utils import log_message, create_execution_log_path
from services.gdf_auth_service import get_gdf_auth_service


def determine_keyset(device_type):
    """
    Determine keySet based on device type
    
    Args:
        device_type: Device type string (e.g., 'XUMO', 'SKYSTREAM')
    
    Returns:
        str: KeySet identifier (PR1_T2 for XUMO, LC103 for SKYSTREAM)
    """
    if not device_type:
        return 'PR1_T2'  # Default to XUMO
    
    device_type_upper = device_type.upper()
    
    # Check for SKYSTREAM devices
    if 'SKY' in device_type_upper or 'STREAM' in device_type_upper:
        return 'LC103'
    else:
        return 'PR1_T2'  # Default to XUMO


def send_gdf_ir_command(mac_address, ir_key, keyset, api_endpoint=None, timeout=10):
    """
    Send single IR command via GDF API with SSO authentication
    
    Args:
        mac_address: Device MAC address (e.g., '38:54:39:76:8E:90')
        ir_key: IR key to send (e.g., 'HOME', 'POWER')
        keyset: KeySet identifier (PR1_T2 or LC103)
        api_endpoint: GDF API base URL (optional, uses auth service)
        timeout: Request timeout in seconds
    
    Returns:
        Tuple: (success: bool, response_status: int, message: str)
    """
    try:
        # Get authenticated GDF service
        gdf_auth = get_gdf_auth_service()
        
        # Ensure we're authenticated
        if not gdf_auth.is_authenticated:
            log_message(f"[GDF API] Authenticating with GDF SSO...")
            success, msg, _ = gdf_auth.login_with_credentials()
            if not success:
                log_message(f"❌ GDF SSO authentication failed: {msg}")
                return (False, 401, f"Authentication failed: {msg}")
        
        log_message(f"[GDF API] Sending key '{ir_key}' via GDF ECATS (SSO authenticated)...")
        
        # Use authenticated service to send IR command
        success, status_code, response = gdf_auth.send_ir_command(mac_address, ir_key, keyset)
        
        if success:
            return (True, status_code, response)
        else:
            return (False, status_code, response)
    
    except Exception as e:
        log_message(f"❌ Unexpected error sending IR key '{ir_key}': {e}")
        import traceback
        log_message(f"   Traceback: {traceback.format_exc()}")
        return (False, 0, f"Unexpected error: {str(e)[:100]}")


def execute_gdf_ir_test_process(device_mac, selected_keys, device_type, 
                                iteration=1, key_delay=0.5, 
                                gdf_api_endpoint=None, device_name="Device",
                                rpi_config=None, device_ip=None, device_username=None, device_password=None):
    """
    Execute IR Command Test for GDF_RACK devices via GDF ECATS API
    
    Args:
        device_mac: Device MAC address (e.g., '38:54:39:76:8E:90')
        selected_keys: List of IR keys to send
        device_type: Device type ('XUMO', 'SKYSTREAM', etc.)
        iteration: Current iteration number
        key_delay: Delay (sec) between key sends
        gdf_api_endpoint: GDF API base URL (optional)
        device_name: Device name for logging
    
    Returns:
        Dict: {'success': bool, 'message': str, 'iteration': int, 'details': list}
    """
    
    if not gdf_api_endpoint:
        gdf_api_endpoint = "https://app.catsprd.comcast.net/gdf/gateway/rest/settop"
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_mac, device_name, iteration, "GDF_IR_TEST")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message(f"\n{'='*70}")
    log_message(f"[GDF IR TEST] Starting GDF IR command test - Iteration {iteration}")
    log_message(f"{'='*70}")
    log_message(f"[GDF CONFIG] Device Name: {device_name}")
    log_message(f"[GDF CONFIG] Device MAC: {device_mac}")
    log_message(f"[GDF CONFIG] Device Type: {device_type}")
    log_message(f"[GDF CONFIG] Selected Keys: {', '.join(selected_keys)}")
    
    # Determine keySet
    keyset = determine_keyset(device_type)
    log_message(f"[GDF CONFIG] KeySet Determined: {keyset}")
    log_message(f"[GDF CONFIG] API Endpoint: {gdf_api_endpoint if gdf_api_endpoint else 'Using authenticated GDF service (SSO)'}")
    log_message(f"[GDF CONFIG] Key Delay: {key_delay}s")
    
    # Validate inputs
    if not selected_keys:
        log_message("❌ No IR keys specified")
        from app import add_html_result
        add_html_result(iteration, "IR-Test", "FAILED", "No IR keys provided", "", "", 
                      device_ip=device_mac, method="gdf_ir_test")
        return {
            "success": False,
            "message": "No IR keys provided",
            "iteration": iteration,
            "details": []
        }
    
    if not device_mac:
        log_message("❌ No MAC address provided for GDF API")
        from app import add_html_result
        add_html_result(iteration, "IR-Test", "FAILED", "GDF API requires device MAC address", "", "", 
                      device_ip="", method="gdf_ir_test")
        return {
            "success": False,
            "message": "GDF API requires device MAC address",
            "iteration": iteration,
            "details": []
        }
    
    # Send IR commands
    all_success = True
    failed_keys = []
    results = []
    
    for idx, ir_key in enumerate(selected_keys):
        log_message(f"\n[IR COMMAND {idx+1}/{len(selected_keys)}] Sending '{ir_key}' via GDF API...")
        
        success, status, response = send_gdf_ir_command(
            device_mac, ir_key, keyset, 
            api_endpoint=None, timeout=10
        )
        
        results.append({
            'key': ir_key,
            'success': success,
            'http_status': status,
            'response': response
        })
        
        if not success:
            all_success = False
            failed_keys.append(ir_key)
            from app import add_html_result
            add_html_result(iteration, f"IR-{ir_key}", "FAILED", f"GDF API error (HTTP {status})", "", "", 
                          device_ip=device_mac, method="gdf_ir_test")
        
        # Wait before next key (except after last key)
        if idx < len(selected_keys) - 1:
            log_message(f"[WAIT] Waiting {key_delay}s before next key...")
            time.sleep(key_delay)
    
    # Summary
    log_message(f"\n{'='*70}")
    log_message(f"[SUMMARY] Total Keys: {len(selected_keys)}")
    log_message(f"[SUMMARY] Successful: {len(selected_keys) - len(failed_keys)}")
    log_message(f"[SUMMARY] Failed: {len(failed_keys)}")
    
    if failed_keys:
        log_message(f"[SUMMARY] Failed keys: {', '.join(failed_keys)}")
        log_message(f"{'='*70}")
        from app import add_html_result
        add_html_result(iteration, "IR-Test", "FAILED", 
                      f"Failed to send {len(failed_keys)} key(s): {', '.join(failed_keys)}", 
                      "", "", device_ip=device_mac, method="gdf_ir_test")
        return {
            "success": False,
            "message": f"Failed to send keys: {', '.join(failed_keys)}",
            "iteration": iteration,
            "details": results
        }
    else:
        log_message("✓ All IR keys sent successfully via GDF API")
        
        # SSH VERIFICATION (Optional - if R-Pi config provided)
        verification_result = ""
        if rpi_config and device_ip and device_username and device_password:
            log_message(f"\n{'='*70}")
            log_message(f"[SSH VERIFICATION] Waiting 5-10 seconds for device to wake up...")
            time.sleep(7)  # Wait for device to respond
            
            log_message(f"[SSH VERIFICATION] Attempting to verify IR commands via device logs...")
            try:
                import paramiko
                from services.gdf_rack_tunnel_service import GDFRackTunnelService
                
                # Build lab device config
                lab_device_config = {
                    'lab_ip': device_ip,
                    'lab_port': 10022,
                    'lab_username': device_username,
                    'lab_password': device_password or '',
                    'device_name': device_name
                }
                
                # Establish tunnel
                tunnel = GDFRackTunnelService(rpi_config, lab_device_config)
                tunnel_success, tunnel_msg = tunnel.connect()
                
                if tunnel_success:
                    log_message(f"✓ {tunnel_msg}")
                    
                    # Connect via tunnel and check logs
                    ssh_client = tunnel.lab_ssh_client
                    
                    # Get last 50 lines of sky-messages.log and look for keycode evidence
                    log_message(f"[LOG CHECK] Retrieving device logs from /opt/logs/sky-messages.log...")
                    stdin, stdout, stderr = ssh_client.exec_command('tail -50 /opt/logs/sky-messages.log 2>/dev/null')
                    log_output = stdout.read().decode('utf-8', errors='ignore')
                    
                    # Look for keycode patterns
                    found_keycodes = []
                    for ir_key in selected_keys:
                        # Common keycode patterns in logs
                        patterns = [
                            f'keycode.*{ir_key}',
                            f'{ir_key}.*key',
                            f'IR.*{ir_key}',
                            ir_key
                        ]
                        
                        for pattern in patterns:
                            if ir_key.lower() in log_output.lower():
                                found_keycodes.append(ir_key)
                                break
                    
                    if found_keycodes:
                        verification_result = f"Verified {len(found_keycodes)} keycode(s) in device logs: {', '.join(found_keycodes)}"
                        log_message(f"✓ {verification_result}")
                        log_message(f"[LOG SAMPLE] {log_output[-500:]}")  # Show last 500 chars
                    else:
                        verification_result = "Device is reachable but keycodes not found in logs (device may not have logged the IR events)"
                        log_message(f"⚠ {verification_result}")
                    
                    # Cleanup
                    tunnel.disconnect()
                else:
                    verification_result = f"Could not establish tunnel for verification: {tunnel_msg}"
                    log_message(f"⚠ {verification_result}")
                    
            except Exception as e:
                verification_result = f"SSH verification error: {str(e)}"
                log_message(f"⚠ {verification_result}")
        else:
            log_message(f"[SSH VERIFICATION] No R-Pi config provided - skipping device log verification")
            verification_result = "SSH verification skipped (no R-Pi config)"
        
        log_message(f"{'='*70}")
        from app import add_html_result
        add_html_result(iteration, "IR-Test", "PASSED", 
                      f"All {len(selected_keys)} IR keys sent successfully via GDF ECATS API. {verification_result}", 
                      "", "", device_ip=device_mac, method="gdf_ir_test")
        return {
            "success": True,
            "message": f"All {len(selected_keys)} IR keys sent successfully via GDF API. {verification_result}",
            "iteration": iteration,
            "details": results,
            "verification": verification_result
        }
