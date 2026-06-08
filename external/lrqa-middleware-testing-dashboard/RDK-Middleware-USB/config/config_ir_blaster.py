"""IR Blaster Configuration and Utility Functions

Provides IR blaster configuration management and IR code generation.
Configuration is stored in devices.json, IR codes in ir_keycodes.json.
"""

import json
import os
import socket
from config_paths import IR_KEYCODES_FILE

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
    """Send IR command via iTach"""
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)
    
    try:
        log(f"[IR SEND] Connecting to iTach at {itach_ip}:{itach_port}...")
        log(f"[IR SEND] IR Code: {ir_code[:80]}..." if len(ir_code) > 80 else f"[IR SEND] IR Code: {ir_code}")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            log(f"[IR SEND] Attempting connection...")
            sock.connect((itach_ip, itach_port))
            log(f"[IR SEND] Connected! Sending command...")
            sock.sendall(ir_code.encode('utf-8'))
            log(f"[IR SEND] Command sent, waiting for response...")
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            log(f"✓ IR command sent successfully. iTach Response: {response.strip()}")
            
            # Check for error responses from iTach
            if 'ERR' in response:
                log(f"⚠ iTach returned error response: {response.strip()}")
                return False
            
            return True
    except socket.timeout as e:
        log(f"❌ Timeout connecting to iTach ({itach_ip}:{itach_port}): {e}")
        return False
    except socket.error as e:
        log(f"❌ Socket error while sending IR command: {e}")
        log(f"    iTach IP: {itach_ip}, Port: {itach_port}")
        log(f"    Please verify iTach is powered on and network is reachable")
        return False
    except Exception as e:
        log(f"❌ Unexpected error while sending IR: {e}")
        return False