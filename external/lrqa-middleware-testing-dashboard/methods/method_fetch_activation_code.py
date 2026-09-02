#!/usr/bin/env python3
"""
Fetch XUMO Activation Code Method
Retrieves the one-time PIN activation code from a XUMO device via SSH.
"""

import paramiko
from methods.method_utils import get_execution_ssh_client
import json
import traceback
from typing import Dict, Optional

def fetch_xumo_activation_code(device_ip: str, port: int = 10022, 
                                username: str = "root", password: str = "") -> Dict:
    """
    Fetch XUMO activation code from device by executing curl command via SSH.
    
    This method connects to the device via SSH and runs:
    curl http://localhost:9005/as/ott
    
    Then parses the JSON response to extract the activation code from:
    ["oneTimePin"]["code"]
    
    Args:
        device_ip: IP address of the XUMO device
        port: SSH port (default: 10022)
        username: SSH username (default: "root")
        password: SSH password (default: "")
    
    Returns:
        Dict with fields:
            - success (bool): Whether code was fetched successfully
            - activation_code (str): The 6-digit activation code
            - expiry (int): Unix timestamp when code expires
            - uri (str): Activation URL
            - message (str): Status message
            - raw_response (str): Raw JSON response from device
    
    Example:
        result = fetch_xumo_activation_code("10.0.0.126")
        if result['success']:
            code = result['activation_code']
            print(f"Activation code: {code}")
    """
    
    ssh = None
    try:
        # Create SSH connection
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=15)
        
        # Execute curl command to fetch activation data
        curl_command = "curl -s http://localhost:9005/as/ott"
        stdin, stdout, stderr = ssh.exec_command(curl_command)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error_msg = stderr.read().decode('utf-8', errors='ignore').strip()
            return {
                "success": False,
                "activation_code": None,
                "expiry": None,
                "uri": None,
                "message": f"Failed to execute curl command: {error_msg}",
                "raw_response": None
            }
        
        # Read response
        raw_response = stdout.read().decode('utf-8', errors='ignore').strip()
        
        if not raw_response:
            return {
                "success": False,
                "activation_code": None,
                "expiry": None,
                "uri": None,
                "message": "Empty response from device",
                "raw_response": None
            }
        
        # Parse JSON response
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "activation_code": None,
                "expiry": None,
                "uri": None,
                "message": f"Failed to parse JSON response: {str(e)}",
                "raw_response": raw_response
            }
        
        # Extract oneTimePin data
        one_time_pin = data.get("oneTimePin")
        if not one_time_pin:
            return {
                "success": False,
                "activation_code": None,
                "expiry": None,
                "uri": None,
                "message": "'oneTimePin' not found in response",
                "raw_response": raw_response
            }
        
        activation_code = one_time_pin.get("code")
        expiry = one_time_pin.get("expiry")
        uri = one_time_pin.get("uri")
        
        if not activation_code:
            return {
                "success": False,
                "activation_code": None,
                "expiry": expiry,
                "uri": uri,
                "message": "'code' not found in oneTimePin section",
                "raw_response": raw_response
            }
        
        # Success
        return {
            "success": True,
            "activation_code": activation_code,
            "expiry": expiry,
            "uri": uri,
            "message": f"Successfully fetched activation code: {activation_code}",
            "raw_response": raw_response
        }
        
    except paramiko.AuthenticationException:
        return {
            "success": False,
            "activation_code": None,
            "expiry": None,
            "uri": None,
            "message": f"SSH authentication failed for {device_ip}",
            "raw_response": None
        }
    except paramiko.SSHException as e:
        return {
            "success": False,
            "activation_code": None,
            "expiry": None,
            "uri": None,
            "message": f"SSH error: {str(e)}",
            "raw_response": None
        }
    except Exception as e:
        return {
            "success": False,
            "activation_code": None,
            "expiry": None,
            "uri": None,
            "message": f"Error fetching activation code: {str(e)}\n{traceback.format_exc()}",
            "raw_response": None
        }
    finally:
        if ssh:
            try:
                ssh.close()
            except:
                pass


def get_activation_code_for_device(device_ip: str) -> Optional[str]:
    """
    Simplified wrapper to get just the activation code string.
    
    Args:
        device_ip: IP address of the XUMO device
    
    Returns:
        str: The activation code, or None if failed
    """
    result = fetch_xumo_activation_code(device_ip)
    if result['success']:
        return result['activation_code']
    else:
        print(f"Error: {result['message']}")
        return None


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python method_fetch_activation_code.py <device_ip>")
        print("\nExample: python method_fetch_activation_code.py 10.0.0.126")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    
    print(f"\n=== Fetching XUMO Activation Code ===")
    print(f"Device: {device_ip}")
    print("=" * 50)
    
    result = fetch_xumo_activation_code(device_ip)
    
    print("\n=== Result ===")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    
    if result['success']:
        print(f"\n✅ Activation Code: {result['activation_code']}")
        print(f"   Expiry: {result['expiry']}")
        print(f"   URI: {result['uri']}")
        print(f"\n📋 Raw Response:")
        print(result['raw_response'])
    else:
        print(f"\n❌ Failed to fetch activation code")
        if result['raw_response']:
            print(f"\n📋 Raw Response:")
            print(result['raw_response'])
