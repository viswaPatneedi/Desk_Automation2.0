"""IR Blaster Configuration and Utility Functions

Provides IR blaster configuration management and IR code generation.
Configuration is stored in devices.json, IR codes in ir_keycodes.json.
"""

import json
import os
import socket
from config.config_paths import IR_KEYCODES_FILE

def get_ir_config_for_device(device_name):
    """Get complete IR blaster configuration from devices.json"""
    try:
        from models.device import Device
        print(f"[DEBUG] Looking for device: '{device_name}'")
        device = Device.find_by_name(device_name)
        if device:
            print(f"[DEBUG] Found device: {device.name}")
            print(f"[DEBUG] IR config: {device.ir_config}")
            return device.ir_config
        else:
            print(f"[DEBUG] Device '{device_name}' not found")
            # List available devices
            all_devices = Device.load_all()
            print(f"[DEBUG] Available devices: {[d.name for d in all_devices]}")
            return None
    except Exception as e:
        print(f"[DEBUG ERROR] Exception in get_ir_config_for_device: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def load_ir_keycodes():
    """Load IR keycodes from JSON file"""
    try:
        if os.path.exists(IR_KEYCODES_FILE):
            with open(IR_KEYCODES_FILE, 'r') as f:
                return json.load(f)
        else:
            print(f"⚠ IR keycodes file not found: {IR_KEYCODES_FILE}")
            return {}
    except Exception as e:
        print(f"Error loading IR keycodes: {e}")
        return {}

def generate_ir_code(command_type, ir_port, remote_type=None):
    """Generate IR code dynamically from ir_keycodes.json"""
    keycodes_data = load_ir_keycodes()

    codes_section = keycodes_data
    if isinstance(keycodes_data, dict) and 'remotes' in keycodes_data:
        remotes = keycodes_data.get('remotes', {})
        selected_remote = (remote_type or '').upper()
        if selected_remote and selected_remote in remotes:
            codes_section = remotes[selected_remote].get('keycodes', {})
        else:
            # Default fallback remote
            codes_section = remotes.get('XUMO_PR3', {}).get('keycodes', {})
    elif isinstance(keycodes_data, dict) and 'keycodes' in keycodes_data:
        codes_section = keycodes_data['keycodes']

    # Get command template from JSON
    cmd_upper = command_type.upper()
    if cmd_upper in codes_section:
        command_template = codes_section[cmd_upper].get('command_template', '')
        if command_template:
            # Support both {IR_PORT} and {ir_port} placeholders
            ir_code = command_template.replace('{IR_PORT}', str(ir_port))
            ir_code = ir_code.replace('{ir_port}', str(ir_port))
            return ir_code

    return None

def send_ir_command(ir_code, itach_ip='10.0.0.12', itach_port=4998, log_callback=None):
    """Send IR command via iTach with improved error handling and timeout management"""
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)
    
    sock = None
    try:
        log(f"[IR SEND] Connecting to iTach at {itach_ip}:{itach_port}...")
        log(f"[IR SEND] IR Code: {ir_code[:80]}..." if len(ir_code) > 80 else f"[IR SEND] IR Code: {ir_code}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # Increased from 5 to 10 seconds for slower networks
        
        log(f"[IR SEND] Attempting connection...")
        sock.connect((itach_ip, itach_port))
        log(f"[IR SEND] Connected! Sending command...")
        
        # Send IR code
        sock.sendall(ir_code.encode('utf-8'))
        log(f"[IR SEND] Command sent, waiting for response...")
        
        # Receive response with timeout handling
        try:
            response_data = b''
            while True:
                chunk = sock.recv(256)
                if not chunk:
                    break  # Connection closed by iTach
                response_data += chunk
                # Check if we have a complete response (iTach ends with \r\n)
                if b'\r\n' in response_data or len(response_data) > 1024:
                    break
        except socket.timeout:
            # If we got some data, use it; otherwise treat as error
            if response_data:
                log(f"[IR SEND] Partial response received due to timeout")
            else:
                log(f"❌ TIMEOUT: No response received from iTach after 10 seconds. Device may be powered off or unreachable.")
                return False
        
        response = response_data.decode('utf-8', errors='ignore').strip()
        
        if response:
            log(f"✓ IR command sent successfully. iTach Response: {response}")
            
            # Check for error responses from iTach
            if 'ERR' in response or 'err' in response:
                log(f"⚠ iTach returned error response: {response}")
                return False
        else:
            log(f"⚠ IR command sent but no response from iTach (may still have been successful)")
        
        return True
        
    except socket.timeout as e:
        log(f"❌ Timeout during iTach connection/communication ({itach_ip}:{itach_port}): {e}")
        return False
    except ConnectionRefusedError as e:
        log(f"❌ Connection refused by iTach ({itach_ip}:{itach_port}): Device may not be running on that port")
        return False
    except socket.error as e:
        log(f"❌ Socket error while sending IR command: {e}")
        log(f"    iTach IP: {itach_ip}, Port: {itach_port}")
        log(f"    Verify iTach is powered on and network is reachable")
        return False
    except Exception as e:
        log(f"❌ Unexpected error while sending IR: {e}")
        import traceback
        log(f"[ERROR-TRACE] {traceback.format_exc()}")
        return False
    finally:
        # Ensure socket is always closed
        if sock:
            try:
                sock.close()
            except:
                pass  # Ignore errors during cleanup


# ============================================================
# DEVICE TYPE TO REMOTE TYPE MAPPING
# ============================================================

# Mapping of device types to their corresponding remote control types
DEVICE_TYPE_TO_REMOTE_TYPE = {
    'XUMO': 'XUMO_PR3',
    'xumo': 'XUMO_PR3',
    'SKY STREAM': 'SKY_LC103',
    'sky stream': 'SKY_LC103',
    'SKY_STREAM': 'SKY_LC103',
    'sky_stream': 'SKY_LC103',
    'SKY': 'SKY_LC103',
    'sky': 'SKY_LC103'
}

# Default keys for each remote type (if user doesn't specify)
DEFAULT_IR_KEYS = {
    'XUMO_PR3': ['HOME', 'POWER'],
    'SKY_LC103': ['HOME', 'POWER']
}


def get_remote_type_for_device_type(device_type):
    """
    Get the remote type based on device type.
    
    Args:
        device_type: Device type (e.g., 'XUMO', 'SKY STREAM')
    
    Returns:
        Remote type (e.g., 'XUMO_PR3', 'SKY_LC103') or None if not found
    """
    if not device_type:
        return None
    
    # Try direct mapping first
    if device_type in DEVICE_TYPE_TO_REMOTE_TYPE:
        return DEVICE_TYPE_TO_REMOTE_TYPE[device_type]
    
    # Try case-insensitive mapping
    device_type_lower = device_type.lower().strip()
    for key, value in DEVICE_TYPE_TO_REMOTE_TYPE.items():
        if key.lower() == device_type_lower:
            return value
    
    return None


def get_default_keys_for_device_type(device_type):
    """
    Get the default IR keys for a device type.
    
    Args:
        device_type: Device type (e.g., 'XUMO', 'SKY STREAM')
    
    Returns:
        List of default keys or empty list if not found
    """
    remote_type = get_remote_type_for_device_type(device_type)
    if remote_type and remote_type in DEFAULT_IR_KEYS:
        return DEFAULT_IR_KEYS[remote_type]
    return []