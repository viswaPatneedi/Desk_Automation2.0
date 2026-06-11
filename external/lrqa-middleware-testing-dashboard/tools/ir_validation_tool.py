#!/usr/bin/env python3
"""
IR Code Validation Tool
Validates IR codes by sending them and verifying device logs

Usage:
    python ir_validation_tool.py --device-ip 192.168.1.100 --validate HOME
    python ir_validation_tool.py --device-ip 192.168.1.100 --validate-all
"""

import paramiko
import socket
import json
import time
import argparse
import re
from typing import Dict, Optional, Tuple
from config.config_paths import IR_KEYCODES_FILE

class IRValidator:
    """Validates IR codes by checking device logs"""
    
    def __init__(self, device_ip: str, device_username: str = 'root', 
                 device_password: str = '', device_port: int = 10022,
                 itach_ip: str = '10.0.0.33', itach_port: int = 4998):
        self.device_ip = device_ip
        self.device_username = device_username
        self.device_password = device_password
        self.device_port = device_port
        self.itach_ip = itach_ip
        self.itach_port = itach_port
        self.ir_keycodes_file = IR_KEYCODES_FILE
        self.log_path = '/opt/logs/sky-messages.log'
    
    def load_ir_keycodes(self) -> Dict:
        """Load IR keycodes from configuration file"""
        try:
            with open(self.ir_keycodes_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"✗ Error loading {self.ir_keycodes_file}: {e}")
            return {}
    
    def connect_to_device(self) -> Optional[paramiko.SSHClient]:
        """Connect to device via SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.device_ip,
                port=self.device_port,
                username=self.device_username,
                password=self.device_password,
                timeout=10
            )
            print(f"✓ Connected to device at {self.device_ip}:{self.device_port}")
            return ssh
        except Exception as e:
            print(f"✗ Failed to connect to device: {e}")
            return None
    
    def send_ir_command(self, command: str) -> bool:
        """Send IR command to iTach device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.itach_ip, self.itach_port))
            
            sock.sendall(command.encode())
            response = sock.recv(1024).decode().strip()
            sock.close()
            
            return 'completeir' in response.lower()
        except Exception as e:
            print(f"✗ Error sending IR command: {e}")
            return False
    
    def get_recent_logs(self, ssh: paramiko.SSHClient, lines: int = 10) -> str:
        """Get recent logs from device"""
        try:
            command = f"tail -n {lines} {self.log_path} | grep -i 'keycode'"
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode()
            return output
        except Exception as e:
            print(f"✗ Error reading logs: {e}")
            return ""
    
    def validate_key(self, key_name: str, ssh: paramiko.SSHClient, 
                    ir_port: int = 1) -> Tuple[bool, str]:
        """
        Validate a specific IR key by sending it and checking logs
        
        Args:
            key_name: Name of the key to validate
            ssh: SSH connection to device
            ir_port: IR port number
        
        Returns:
            Tuple of (success, details)
        """
        # Load IR keycodes
        data = self.load_ir_keycodes()
        keycodes = data.get('keycodes', {})
        
        if key_name not in keycodes:
            return False, f"Key '{key_name}' not found in configuration"
        
        key_data = keycodes[key_name]
        command_template = key_data.get('command_template', '')
        validation = key_data.get('validation', {})
        
        if not command_template:
            return False, f"No command template for '{key_name}'"
        
        print(f"\n{'='*70}")
        print(f"🧪 Testing: {key_name}")
        print(f"{'='*70}")
        print(f"Description: {key_data.get('description', 'N/A')}")
        
        if validation:
            print(f"Expected HEX: {validation.get('hex_code', 'N/A')}")
            print(f"Expected Key: {validation.get('ethan_key', 'N/A')}")
        
        # Get baseline logs
        print(f"\n📋 Getting baseline logs...")
        baseline = self.get_recent_logs(ssh, lines=5)
        
        # Send IR command
        command = command_template.replace('{ir_port}', str(ir_port))
        print(f"📤 Sending IR command...")
        
        if not self.send_ir_command(command):
            return False, "Failed to send IR command"
        
        # Wait for device to process
        time.sleep(2)
        
        # Get new logs
        print(f"📋 Checking device logs...")
        new_logs = self.get_recent_logs(ssh, lines=20)
        
        # Find new entries
        new_entries = [line for line in new_logs.split('\n') 
                      if line and line not in baseline]
        
        if not new_entries:
            return False, "No new log entries found (IR signal may not have reached device)"
        
        print(f"\n📝 Recent Log Entries:")
        for entry in new_entries[-3:]:  # Show last 3 entries
            print(f"   {entry[:100]}...")
        
        # Validate against expected values
        if validation:
            expected_hex = validation.get('hex_code', '')
            expected_key = validation.get('ethan_key', '')
            
            success = False
            for entry in new_entries:
                if expected_hex in entry and expected_key in entry:
                    success = True
                    break
            
            if success:
                print(f"\n✅ VALIDATION PASSED")
                print(f"   Found expected HEX code: {expected_hex}")
                print(f"   Found expected key name: {expected_key}")
                return True, "Validation successful"
            else:
                print(f"\n⚠️  VALIDATION FAILED")
                print(f"   Expected HEX: {expected_hex}")
                print(f"   Expected Key: {expected_key}")
                print(f"   Check if the correct IR signal was received")
                return False, "Expected validation pattern not found in logs"
        else:
            print(f"\n✓ IR Signal Sent (No validation data configured)")
            return True, "IR command sent successfully (no validation)"
    
    def validate_all_keys(self, ir_port: int = 1):
        """Validate all keys in the configuration"""
        data = self.load_ir_keycodes()
        keycodes = data.get('keycodes', {})
        
        if not keycodes:
            print("✗ No IR keycodes found in configuration")
            return
        
        print(f"\n{'='*70}")
        print(f"IR CODE VALIDATION - ALL KEYS")
        print(f"{'='*70}")
        print(f"Device: {self.device_ip}")
        print(f"iTach: {self.itach_ip}")
        print(f"Total Keys: {len(keycodes)}")
        print(f"{'='*70}")
        
        # Connect to device
        ssh = self.connect_to_device()
        if not ssh:
            print("✗ Cannot proceed without device connection")
            return
        
        try:
            results = []
            for key_name in keycodes.keys():
                success, details = self.validate_key(key_name, ssh, ir_port)
                results.append({
                    'key': key_name,
                    'success': success,
                    'details': details
                })
                
                # Wait between tests (10 seconds for better log separation)
                print(f"⏱️  Waiting 10 seconds before next key test...")
                time.sleep(10)
            
            # Summary
            print(f"\n{'='*70}")
            print(f"VALIDATION SUMMARY")
            print(f"{'='*70}")
            
            passed = sum(1 for r in results if r['success'])
            failed = len(results) - passed
            
            print(f"\n📊 Results: {passed}/{len(results)} passed")
            print(f"   ✅ Passed: {passed}")
            print(f"   ❌ Failed: {failed}")
            
            if failed > 0:
                print(f"\n❌ Failed Keys:")
                for r in results:
                    if not r['success']:
                        print(f"   - {r['key']}: {r['details']}")
        
        finally:
            ssh.close()
    
    def list_keys_with_validation(self):
        """List all keys and their validation status"""
        data = self.load_ir_keycodes()
        keycodes = data.get('keycodes', {})
        
        if not keycodes:
            print("✗ No IR keycodes found")
            return
        
        print(f"\n{'='*70}")
        print(f"IR KEYCODES WITH VALIDATION INFO")
        print(f"{'='*70}")
        
        for key_name, key_data in keycodes.items():
            validation = key_data.get('validation', {})
            
            print(f"\n🔑 {key_name}")
            print(f"   Display: {key_data.get('display_name', 'N/A')}")
            print(f"   Description: {key_data.get('description', 'N/A')}")
            
            if validation:
                print(f"   ✅ Validation Configured:")
                print(f"      HEX Code: {validation.get('hex_code', 'N/A')}")
                print(f"      Ethan Key: {validation.get('ethan_key', 'N/A')}")
            else:
                print(f"   ⚠️  No validation data configured")


def main():
    parser = argparse.ArgumentParser(
        description='IR Code Validation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single key
  python ir_validation_tool.py --device-ip 192.168.1.100 --device-password mypass --validate HOME
  
  # Validate all keys
  python ir_validation_tool.py --device-ip 192.168.1.100 --device-password mypass --validate-all
  
  # List keys with validation info
  python ir_validation_tool.py --list
        """
    )
    
    parser.add_argument('--device-ip', required=False,
                       help='Device IP address')
    parser.add_argument('--device-username', default='root',
                       help='Device SSH username (default: root)')
    parser.add_argument('--device-password', default='',
                       help='Device SSH password')
    parser.add_argument('--device-port', type=int, default=10022,
                       help='Device SSH port (default: 10022)')
    parser.add_argument('--itach-ip', default='10.0.0.33',
                       help='iTach IP address (default: 10.0.0.33)')
    parser.add_argument('--itach-port', type=int, default=4998,
                       help='iTach port (default: 4998)')
    parser.add_argument('--ir-port', type=int, default=1, choices=[1, 2, 3],
                       help='IR port number (default: 1)')
    parser.add_argument('--validate', type=str,
                       help='Validate a specific key by name')
    parser.add_argument('--validate-all', action='store_true',
                       help='Validate all keys')
    parser.add_argument('--list', action='store_true',
                       help='List all keys with validation info')
    
    args = parser.parse_args()
    
    # Create validator
    validator = IRValidator(
        device_ip=args.device_ip or '',
        device_username=args.device_username,
        device_password=args.device_password,
        device_port=args.device_port,
        itach_ip=args.itach_ip,
        itach_port=args.itach_port
    )
    
    # Execute requested action
    if args.list:
        validator.list_keys_with_validation()
    
    elif args.validate:
        if not args.device_ip:
            print("✗ --device-ip is required for validation")
            return
        
        ssh = validator.connect_to_device()
        if ssh:
            try:
                success, details = validator.validate_key(args.validate, ssh, args.ir_port)
                print(f"\n{'='*70}")
                if success:
                    print(f"✅ RESULT: {details}")
                else:
                    print(f"❌ RESULT: {details}")
            finally:
                ssh.close()
    
    elif args.validate_all:
        if not args.device_ip:
            print("✗ --device-ip is required for validation")
            return
        
        validator.validate_all_keys(ir_port=args.ir_port)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
