#!/usr/bin/env python3
"""
Navigate to Tiles Method Implementation
Navigate through sections and tiles on EPG widget using curl commands to verify focused tile
"""

import sys
import time
import re
import paramiko
from datetime import datetime, timezone
from difflib import SequenceMatcher

# Import shared utilities
from method_utils import (
    log_message,
    fetch_build_details,
    create_execution_log_path,
    get_folder_method_name
)

def calculate_similarity(a, b):
    """
    Calculate string similarity as a percentage (0-100)
    Uses SequenceMatcher to find matching ratio
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100

def fetch_focused_tile(ssh, flux_server_ip_port, log_message_func):
    """
    Fetch the currently focused tile name using curl command
    
    Args:
        ssh: SSH client connection
        flux_server_ip_port: Flux Server IP:port (e.g., "100.64.11.2:8023")
        log_message_func: Logging function
    
    Returns:
        str: Focused tile name or None if error
    """
    try:
        curl_cmd = f'curl -s http://{flux_server_ip_port}/qobject/%2Fglobal-nav-scene%2Fqms-gadget%2Fsection-view-gl-item?property=focusedCurrentLinearTitle'
        stdin, stdout, stderr = ssh.exec_command(curl_cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        
        # Clean output: remove command prompt and extra whitespace
        # Example output: "Apps & inputsroot@apache-4k:~#"
        # We need to extract just the tile name
        focused_tile = output.replace('root@apache-4k:~#', '').strip()
        
        if focused_tile:
            return focused_tile
        else:
            log_message_func("⚠ Empty response from curl command")
            return None
    
    except Exception as e:
        log_message_func(f"⚠ Error fetching focused tile: {e}")
        return None

def send_key(ssh, key_command, key_name, log_message_func):
    """
    Send a remote key press to the device
    
    Args:
        ssh: SSH client connection
        key_command: Command to send (e.g., "keySimulator -kdown")
        key_name: Display name for logging
        log_message_func: Logging function
    
    Returns:
        bool: True if successful
    """
    try:
        stdin, stdout, stderr = ssh.exec_command(key_command, timeout=5)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            log_message_func(f"✓ Sent key: {key_name}")
            return True
        else:
            log_message_func(f"⚠ Key command exited with status {exit_status}: {key_name}")
            return False
    except Exception as e:
        log_message_func(f"⚠ Error sending key {key_name}: {e}")
        return False

def navigate_to_tiles(device_ip, port, username, password, flux_server_ip_port, section, tile_to_navigate, 
                     iteration=1, device_name="Device", combined_method_name=None):
    """
    Navigate to specific section and tile on EPG widget
    
    Args:
        device_ip: Device IP address
        port: SSH port
        username: SSH username
        password: SSH password
        flux_server_ip_port: Flux Server IP:port from Activate_Flux method (e.g., "100.64.11.2:8023")
        section: Section name to navigate to (e.g., "Apps", "APPS")
        tile_to_navigate: Tile name to navigate to (e.g., "prime video")
        iteration: Current iteration number
        device_name: Display name of device
        combined_method_name: Name for combined method execution (optional)
    
    Returns:
        Dict with iteration, success status, details, and final focused tile
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    logs_list = []
    
    # Clean device name for filename
    safe_device_name = device_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Validate inputs
    if not flux_server_ip_port:
        log_message("❌ ERROR: Flux Server IP:port not provided")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": "Flux Server IP:port is required. Run Activate_Flux method first.",
            "final_focused_tile": None
        }
    
    if not section or not section.strip():
        log_message("❌ ERROR: Section name is required")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": "Section name is required",
            "final_focused_tile": None
        }
    
    if not tile_to_navigate or not tile_to_navigate.strip():
        log_message("❌ ERROR: Tile name is required")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": "Tile name is required",
            "final_focused_tile": None
        }
    
    # Set USB log file path for this execution
    try:
        from services.log_service import LogService
        log_service = LogService()
        usb_log_path = create_execution_log_path(device_ip, device_name, iteration, "NAVIGATE_TO_TILES")
        log_service.current_usb_log_file = usb_log_path
        log_message(f"💾 USB execution log: {usb_log_path}")
    except Exception as e:
        log_message(f"⚠ Could not set USB log path: {e}")
    
    log_message("="*80)
    log_message("NAVIGATE TO TILES - START")
    log_message("="*80)
    log_message(f"Flux Server: {flux_server_ip_port}")
    log_message(f"Target Section: {section}")
    log_message(f"Target Tile: {tile_to_navigate}")
    
    try:
        # STEP 1: CONNECT TO DEVICE
        log_message("\n[STEP 1] Connecting to device...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        log_message("✓ Connected to device successfully")
        
        # Fetch build details from device
        fetch_build_details(ssh, log_message)
        
        # STEP 2: NAVIGATE TO SECTION
        log_message(f"\n[STEP 2] Navigating to section: '{section}'...")
        
        section_found = False
        max_key_presses = 15  # Limit navigation attempts
        key_press_count = 0
        current_section = None
        
        while key_press_count < max_key_presses and not section_found:
            # Get current focused item
            current_section = fetch_focused_tile(ssh, flux_server_ip_port, log_message)
            
            if not current_section:
                log_message(f"⚠ Could not fetch current focused tile (attempt {key_press_count + 1}/{max_key_presses})")
                time.sleep(0.5)
                send_key(ssh, "keySimulator -kdown", "DOWN", log_message)
                key_press_count += 1
                continue
            
            # Check if current section matches target section (case-insensitive)
            similarity = calculate_similarity(current_section, section)
            log_message(f"  Current: '{current_section}' (Similarity: {similarity:.1f}%)")
            
            if similarity >= 70:
                log_message(f"✓ Found matching section: '{current_section}'")
                section_found = True
                break
            
            # Send down key to navigate
            send_key(ssh, "keySimulator -kdown", "DOWN", log_message)
            key_press_count += 1
            time.sleep(0.3)
        
        if not section_found:
            log_message(f"❌ Section '{section}' not found after {key_press_count} attempts")
            ssh.close()
            return {
                "iteration": iteration,
                "logs": logs_list,
                "success": False,
                "details": f"Section '{section}' not found after {key_press_count} navigation attempts",
                "final_focused_tile": current_section
            }
        
        # STEP 3: ENTER SECTION
        log_message(f"\n[STEP 3] Entering section by pressing ENTER...")
        send_key(ssh, "keySimulator -kenter", "ENTER", log_message)
        time.sleep(1.0)  # Wait for section to load
        
        # STEP 4: NAVIGATE TO TILE
        log_message(f"\n[STEP 4] Navigating to tile: '{tile_to_navigate}'...")
        
        tile_found = False
        max_tile_attempts = 20  # Limit tile navigation attempts
        tile_attempt_count = 0
        current_tile = None
        
        while tile_attempt_count < max_tile_attempts and not tile_found:
            # Get current focused tile
            current_tile = fetch_focused_tile(ssh, flux_server_ip_port, log_message)
            
            if not current_tile:
                log_message(f"⚠ Could not fetch current tile (attempt {tile_attempt_count + 1}/{max_tile_attempts})")
                time.sleep(0.5)
                send_key(ssh, "keySimulator -kright", "RIGHT", log_message)
                tile_attempt_count += 1
                continue
            
            # Check if current tile matches target tile (using 70% similarity)
            similarity = calculate_similarity(current_tile, tile_to_navigate)
            log_message(f"  Current: '{current_tile}' (Similarity: {similarity:.1f}%)")
            
            if similarity >= 70:
                log_message(f"✓ Found matching tile: '{current_tile}' (Match: {similarity:.1f}%)")
                tile_found = True
                break
            
            # Send right key to navigate to next tile
            send_key(ssh, "keySimulator -kright", "RIGHT", log_message)
            tile_attempt_count += 1
            time.sleep(0.3)
        
        if not tile_found:
            log_message(f"❌ Tile '{tile_to_navigate}' not found after {tile_attempt_count} attempts")
            log_message(f"  Last focused tile was: '{current_tile}'")
            ssh.close()
            return {
                "iteration": iteration,
                "logs": logs_list,
                "success": False,
                "details": f"Tile '{tile_to_navigate}' not found after {tile_attempt_count} navigation attempts",
                "final_focused_tile": current_tile
            }
        
        # Close SSH connection
        ssh.close()
        
        # FINAL RESULT
        log_message("\n" + "="*80)
        log_message("✓ NAVIGATE TO TILES - PASSED")
        log_message(f"✓ Successfully navigated to section '{section}' and tile '{current_tile}'")
        log_message("="*80)
        
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": True,
            "details": f"Successfully navigated to section and tile '{current_tile}'",
            "final_focused_tile": current_tile,
            "section_found": section_found,
            "tile_found": tile_found,
            "section_attempts": key_press_count,
            "tile_attempts": tile_attempt_count,
            "timestamp": timestamp
        }
    
    except paramiko.SSHException as ssh_error:
        log_message(f"❌ SSH Error: {ssh_error}")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": f"SSH connection failed: {str(ssh_error)}",
            "final_focused_tile": None
        }
    
    except Exception as e:
        import traceback
        log_message(f"❌ Error during tile navigation: {e}")
        log_message(f"Full traceback:\n{traceback.format_exc()}")
        return {
            "iteration": iteration,
            "logs": logs_list,
            "success": False,
            "details": f"Execution error: {str(e)}",
            "final_focused_tile": None
        }


# Allow script to be executed standalone for testing
if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: python method_navigate_to_tiles.py <device_ip> <port> <username> <password> <flux_server_ip_port> <section> <tile> [iteration] [device_name]")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    flux_server_ip_port = sys.argv[5]
    section = sys.argv[6]
    tile = sys.argv[7]
    iteration = int(sys.argv[8]) if len(sys.argv) > 8 else 1
    device_name = sys.argv[9] if len(sys.argv) > 9 else "Device"
    
    result = navigate_to_tiles(device_ip, port, username, password, flux_server_ip_port, section, tile, iteration, device_name)
    print("\n" + "="*80)
    print("EXECUTION RESULT")
    print("="*80)
    print(f"Success: {result['success']}")
    print(f"Details: {result['details']}")
    print(f"Final Focused Tile: {result['final_focused_tile']}")
    print(f"Iteration: {result['iteration']}")
