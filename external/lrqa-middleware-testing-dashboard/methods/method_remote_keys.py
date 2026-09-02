#!/usr/bin/env python3
"""
Send Remote Keys Method
Handles multiple key presses, grouping consecutive keys for efficient keySimulator commands.
This method can be called multiple times in the same execution without conflicts.
"""
import paramiko
from methods.method_utils import get_execution_ssh_client
import time
import traceback
from typing import List, Dict, Tuple, Union

def get_supported_keycodes() -> Dict[str, str]:
    """Get mapping of key names to keySimulator codes"""
    return {
        '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
        'POWER': 'power', 'ALLPOWER': 'allpower', 'UP': 'up', 'DOWN': 'down', 'LEFT': 'left', 'RIGHT': 'right',
        'SELECT': 'select', 'ENTER': 'enter', 'EXIT': 'exit', 'CHUP': 'chup', 'CHDOWN': 'chdown',
        'VOLUP': 'volup', 'VOLDOWN': 'voldown', 'MUTE': 'mute', 'GUIDE': 'guide', 'INFO': 'info',
        'SETTINGS': 'settings', 'PAGEUP': 'pageup', 'PAGEDOWN': 'pagedown', 'FAVOURITE': 'favourite',
        'REWIND': 'rewind', 'FASTFWD': 'fastfwd', 'PLAY': 'play', 'STOP': 'stop', 'PAUSE': 'pause',
        'RECORD': 'record', 'BYPASS': 'bypass', 'TVVCR': 'tvvcr', 'REPLAY': 'replay', 'HELP': 'help',
        'CLEAR': 'clear', 'DELETE': 'delete', 'START': 'start', 'POUND': 'pound', 'OK': 'ok', 'STAR': 'star',
        'TVPOWER': 'tvpower', 'PREVIOUS': 'previous', 'NEXT': 'next', 'MENU': 'menu', 'HOME': 'home',
        'INPUTKEY': 'inputkey', 'LIVETV': 'livetv', 'MYDVR': 'mydvr', 'ONDEMAND': 'ondemand', 'STBMENU': 'stbmenu',
        'AUDIO': 'audio', 'FACTORY': 'factory', 'RFENABLE': 'rfenable', 'LIST': 'list', 'BACK': 'back',
        'SWAP': 'swap', 'PIPMOVE': 'pipmove', 'PIPTOGGLE': 'piptoggle', 'PIPCHDOWN': 'pipchdown', 'PIPCHUP': 'pipchup',
        'ACTIVATE': 'activate', 'DEACTIVATE': 'deactivate', 'DMCQUERY': 'dmcquery', 'OTRSTART': 'otrstart',
        'STRSTOP': 'strstop', 'PERIOD': 'period', 'PUSH2TALK': 'push2talk', 'KEYA': 'keya', 'KEYB': 'keyb',
        'KEYC': 'keyc', 'KEYD': 'keyd', 'SEARCH': 'search', 'LOWBAT': 'lowBat'
    }

def group_keys(keys: List[str]) -> List[Tuple[str, int]]:
    """
    Group consecutive identical keys and count repeats.
    Example: ['RIGHT', 'RIGHT', 'DOWN', 'DOWN', 'DOWN'] -> [('RIGHT', 2), ('DOWN', 3)]
    """
    if not keys:
        return []
    grouped = []
    prev = keys[0]
    count = 1
    for key in keys[1:]:
        if key == prev:
            count += 1
        else:
            grouped.append((prev, count))
            prev = key
            count = 1
    grouped.append((prev, count))
    return grouped

def send_remote_keys(device_ip: str, key_sequence: Union[str, List[str]], 
                     port: int = 10022, username: str = "root", password: str = "", key_delay: float = 2.0,
                     ssh_client=None) -> Dict:
    """
    Send remote control keys to a device via SSH.
    
    This method can be called multiple times in the same execution without conflicts.
    Each call creates a new SSH connection and executes the provided keys independently.
    
    Args:
        device_ip: IP address of the target device
        key_sequence: Comma-separated string of keys (e.g., "RIGHT,RIGHT,DOWN") or list of keys
        port: SSH port (default: 10022)
        username: SSH username (default: "root")
        password: SSH password (default: "")
        key_delay: Custom delay in seconds between key presses (default: 2.0s)
                   - Use 1-2s for navigation keys
                   - Use 2-4s for action keys (OK, SELECT, ENTER)
    
    Returns:
        Dict with 'success' (bool) and 'message' (str) fields
    
    Examples:
        # From API with string
        result = send_remote_keys("10.0.0.126", "RIGHT,RIGHT,DOWN,SELECT")
        
        # From queue service with list with custom delay
        result = send_remote_keys("10.0.0.126", ["RIGHT", "RIGHT", "DOWN"], key_delay=1.5)
        
        # Multiple calls in same execution (no conflicts)
        send_remote_keys("10.0.0.126", "HOME,DOWN,SELECT", key_delay=2.5)
        send_remote_keys("10.0.0.126", "BACK", key_delay=1.0)
    """
    # Parse input - handle both string and list formats
    if isinstance(key_sequence, str):
        keys = [k.strip().upper() for k in key_sequence.split(",") if k.strip()]
    elif isinstance(key_sequence, list):
        keys = [k.upper() for k in key_sequence if k]
    else:
        return {"success": False, "message": "Invalid key_sequence format. Expected string or list."}
    
    if not keys:
        return {"success": False, "message": "No keys provided."}
    
    keycodes = get_supported_keycodes()
    grouped = group_keys(keys)
    
    # Validate all keys first
    for key, _ in grouped:
        if key not in keycodes:
            return {"success": False, "message": f"Unsupported key: {key}. Check supported keys list."}
    
    ssh = ssh_client
    owns_ssh_connection = ssh_client is None
    try:
        if owns_ssh_connection:
            ssh = get_execution_ssh_client()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        
        executed_keys = []
        for key, repeat in grouped:
            # Map OK to ENTER since OK key doesn't work with keySimulator
            if key == 'OK':
                keycode = keycodes['ENTER']
                display_key = 'OK→ENTER'
            else:
                keycode = keycodes[key]
                display_key = key
            
            cmd = f"keySimulator -k{keycode} -r{repeat}"
            
            stdin, stdout, stderr = ssh.exec_command(cmd)
            error_msg = stderr.read().decode('utf-8', errors='ignore').strip()
            if error_msg:
                return {"success": False, "message": f"Failed to send key {key}: {error_msg}"}
            
            executed_keys.append(f"{display_key}x{repeat}" if repeat > 1 else display_key)
            
            # Use custom key_delay with adjustments for action keys
            # OK and SELECT typically need more time as they trigger actions
            if key in ['OK', 'SELECT', 'ENTER']:
                action_delay = key_delay * 1.5 if key_delay >= 1.0 else key_delay + 2.0
                time.sleep(action_delay)  # Longer delay for action keys
            else:
                time.sleep(key_delay)  # Standard delay for navigation keys
        
        return {
            "success": True, 
            "message": f"Successfully sent keys: {', '.join(executed_keys)}"
        }
    
    except paramiko.AuthenticationException:
        return {"success": False, "message": f"Authentication failed for {device_ip}"}
    except paramiko.SSHException as e:
        return {"success": False, "message": f"SSH error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}\n{traceback.format_exc()}"}
    finally:
        # Always close SSH connection to prevent resource leaks
        if ssh and owns_ssh_connection:
            try:
                ssh.close()
            except:
                pass

# Backward compatibility wrapper for old signature
def send_remote_keys_legacy(device_ip: str, port: int, username: str, password: str, keys: List[str]) -> Dict:
    """Legacy function signature for backward compatibility"""
    return send_remote_keys(device_ip, keys, port, username, password)

# Example usage and testing
if __name__ == "__main__":
    # Test with string format (API style)
    print("Test 1: String format")
    result = send_remote_keys("10.0.0.126", "RIGHT,RIGHT,RIGHT,DOWN,DOWN")
    print(f"Result: {result}")
    
    # Test with list format (queue service style)
    print("\nTest 2: List format")
    result = send_remote_keys("10.0.0.126", ["HOME", "DOWN", "SELECT"])
    print(f"Result: {result}")
    
    # Test multiple calls (simulating same execution)
    print("\nTest 3: Multiple calls in sequence")
    result1 = send_remote_keys("10.0.0.126", "MENU")
    print(f"Call 1: {result1}")
    time.sleep(1)
    result2 = send_remote_keys("10.0.0.126", "DOWN,SELECT")
    print(f"Call 2: {result2}")
