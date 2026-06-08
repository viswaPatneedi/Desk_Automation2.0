#!/usr/bin/env python3
"""
IR Code Capture Tool for Global Cache iTach
Helps capture IR codes from physical remote and update ir_keycodes.json

Usage:
    python ir_code_capture.py --itach-ip 10.0.0.12 --capture
    python ir_code_capture.py --itach-ip 10.0.0.12 --test HOME
"""

import socket
import json
import time
import argparse
import sys
from typing import Dict, Optional

class IRCodeCapture:
    """Tool for capturing and managing IR codes from Global Cache iTach"""
    
    def __init__(self, itach_ip: str = '10.0.0.33', itach_port: int = 4998):
        self.itach_ip = itach_ip
        self.itach_port = itach_port
        self.ir_keycodes_file = 'ir_keycodes.json'
    
    def connect(self) -> Optional[socket.socket]:
        """Connect to iTach device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.itach_ip, self.itach_port))
            print(f"✓ Connected to iTach at {self.itach_ip}:{self.itach_port}")
            return sock
        except Exception as e:
            print(f"✗ Failed to connect to iTach: {e}")
            return None
    
    def send_command(self, sock: socket.socket, command: str) -> str:
        """Send command to iTach and get response"""
        try:
            sock.sendall(command.encode())
            response = sock.recv(1024).decode().strip()
            return response
        except Exception as e:
            print(f"✗ Error sending command: {e}")
            return ""
    
    def capture_ir_code(self, port: int = 1, timeout: int = 15) -> Optional[str]:
        """
        Capture IR code from iTach sensor.
        
        Args:
            port: IR port number (1, 2, or 3)
            timeout: Timeout in seconds to wait for IR signal
        
        Returns:
            Captured IR command string or None
        """
        sock = self.connect()
        if not sock:
            return None
        
        try:
            # Enable IR learning mode
            learn_command = f"get_IRL,1:{port}\r"
            print(f"\n🔴 LEARNING MODE ACTIVE - Port {port}")
            print(f"👉 Point your remote at the iTach IR sensor and press the button")
            print(f"⏱️  Waiting {timeout} seconds for IR signal...")
            print(f"💡 TIP: Press and hold the button for 1 second\n")
            
            sock.sendall(learn_command.encode())
            
            # Wait for IR signal - read in a loop to get complete response
            sock.settimeout(timeout)
            response_parts = []
            
            while True:
                try:
                    chunk = sock.recv(4096).decode()
                    if not chunk:
                        break
                    response_parts.append(chunk)
                    
                    # Check if we got the complete sendir command
                    full_response = ''.join(response_parts)
                    if 'sendir,' in full_response and '\r' in full_response:
                        # Got complete IR command
                        break
                    
                    # If just "IR Learner Enabled", keep waiting
                    if 'IR Learner Enabled' in chunk and 'sendir' not in chunk:
                        continue
                        
                except socket.timeout:
                    break
            
            full_response = ''.join(response_parts).strip()
            
            # Parse response
            if 'sendir,' in full_response:
                # Extract the sendir command
                lines = full_response.split('\n')
                for line in lines:
                    if line.strip().startswith('sendir,'):
                        sendir_line = line.strip()
                        print(f"✓ IR Code Captured Successfully!\n")
                        return sendir_line
                
                # Try to extract from full response
                import re
                match = re.search(r'(sendir,[\d,\s]+\r?)', full_response)
                if match:
                    print(f"✓ IR Code Captured Successfully!\n")
                    return match.group(1).strip()
                
                print("⚠️  Signal received but couldn't parse sendir command")
                print(f"Raw response: {full_response[:200]}...")
                return None
            elif 'IR Learner Enabled' in full_response and 'sendir' not in full_response:
                print(f"✗ No IR button was pressed during the capture window")
                print(f"💡 Make sure to press the button on your remote while learning mode is active")
                return None
            else:
                print(f"✗ Unexpected response: {full_response[:100]}")
                return None
        
        except socket.timeout:
            print(f"✗ Timeout: No IR signal received in {timeout} seconds")
            print(f"💡 Make sure your remote is pointed directly at the iTach sensor")
            return None
        except Exception as e:
            print(f"✗ Error during capture: {e}")
            return None
        finally:
            sock.close()
    
    def test_ir_code(self, key_name: str) -> bool:
        """
        Test an IR code from ir_keycodes.json
        
        Args:
            key_name: Name of the key to test (e.g., "HOME", "POWER")
        
        Returns:
            True if successful, False otherwise
        """
        # Load IR keycodes
        try:
            with open(self.ir_keycodes_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"✗ Error loading {self.ir_keycodes_file}: {e}")
            return False
        
        # Get key definition
        if key_name not in data.get('keycodes', {}):
            print(f"✗ Key '{key_name}' not found in {self.ir_keycodes_file}")
            print(f"Available keys: {', '.join(data.get('keycodes', {}).keys())}")
            return False
        
        key_data = data['keycodes'][key_name]
        command_template = key_data.get('command_template', '')
        
        if not command_template:
            print(f"✗ No command template found for '{key_name}'")
            return False
        
        # Replace placeholder with default port 1
        command = command_template.replace('{ir_port}', '1')
        
        # Send command
        sock = self.connect()
        if not sock:
            return False
        
        try:
            print(f"\n📤 Sending IR command for '{key_name}'...")
            print(f"Description: {key_data.get('description', 'N/A')}")
            
            response = self.send_command(sock, command)
            
            if 'completeir' in response.lower():
                print(f"✓ IR command sent successfully!")
                print(f"Response: {response}")
                return True
            else:
                print(f"⚠ Unexpected response: {response}")
                return False
        
        finally:
            sock.close()
    
    def add_or_update_key(self, key_name: str, ir_command: str, 
                         display_name: str = None, description: str = None) -> bool:
        """
        Add or update an IR key in ir_keycodes.json
        
        Args:
            key_name: Key identifier (e.g., "HOME", "POWER")
            ir_command: The sendir command string
            display_name: Human-readable name
            description: Key description
        
        Returns:
            True if successful, False otherwise
        """
        # Load existing data
        try:
            with open(self.ir_keycodes_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {
                "description": "IR Key Codes Configuration",
                "version": "1.0",
                "keycodes": {}
            }
        except Exception as e:
            print(f"✗ Error loading {self.ir_keycodes_file}: {e}")
            return False
        
        # Convert command to template format (replace port number with placeholder)
        import re
        command_template = re.sub(r'(sendir,1:)(\d+)', r'\1{ir_port}', ir_command)
        
        # Create key entry
        key_entry = {
            "name": key_name,
            "display_name": display_name or f"{key_name.title()} Key",
            "description": description or f"IR command for {key_name}",
            "command_template": command_template
        }
        
        # Update data
        if 'keycodes' not in data:
            data['keycodes'] = {}
        
        action = "Updated" if key_name in data['keycodes'] else "Added"
        data['keycodes'][key_name] = key_entry
        
        # Save to file
        try:
            with open(self.ir_keycodes_file, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"\n✓ {action} '{key_name}' in {self.ir_keycodes_file}")
            return True
        except Exception as e:
            print(f"✗ Error saving {self.ir_keycodes_file}: {e}")
            return False
    
    def interactive_capture(self):
        """Interactive mode for capturing multiple IR codes"""
        print("=" * 70)
        print("IR CODE CAPTURE TOOL - Interactive Mode")
        print("=" * 70)
        print(f"iTach Device: {self.itach_ip}:{self.itach_port}")
        print(f"Output File: {self.ir_keycodes_file}")
        print("=" * 70)
        
        while True:
            print("\n" + "=" * 70)
            key_name = input("\n📝 Enter key name (e.g., HOME, POWER, BACK) or 'quit' to exit: ").strip().upper()
            
            if key_name.lower() == 'quit':
                print("\n👋 Exiting capture tool. Goodbye!")
                break
            
            if not key_name:
                print("⚠ Key name cannot be empty")
                continue
            
            # Get optional metadata
            display_name = input(f"Display name (optional, press Enter to use '{key_name.title()} Key'): ").strip()
            description = input(f"Description (optional, press Enter to use default): ").strip()
            
            # Capture IR code
            print(f"\n🎯 Ready to capture IR code for '{key_name}'")
            ir_port = input("IR port number (1, 2, or 3) [default: 1]: ").strip() or "1"
            
            try:
                ir_port = int(ir_port)
                if ir_port not in [1, 2, 3]:
                    print("⚠ Invalid port. Using port 1.")
                    ir_port = 1
            except ValueError:
                print("⚠ Invalid port. Using port 1.")
                ir_port = 1
            
            ir_command = self.capture_ir_code(port=ir_port, timeout=15)
            
            if ir_command:
                # Show captured command
                print(f"\n📋 Captured Command:")
                print(f"   {ir_command[:80]}...")
                
                # Confirm save
                save = input("\n💾 Save this IR code? (y/n): ").strip().lower()
                
                if save == 'y':
                    success = self.add_or_update_key(
                        key_name=key_name,
                        ir_command=ir_command,
                        display_name=display_name or None,
                        description=description or None
                    )
                    
                    if success:
                        # Test the code
                        test = input("🧪 Test the captured code now? (y/n): ").strip().lower()
                        if test == 'y':
                            time.sleep(1)
                            self.test_ir_code(key_name)
                else:
                    print("⚠ IR code not saved")
            else:
                print("✗ Failed to capture IR code. Please try again.")
    
    def list_keys(self):
        """List all keys in ir_keycodes.json"""
        try:
            with open(self.ir_keycodes_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"✗ Error loading {self.ir_keycodes_file}: {e}")
            return
        
        keycodes = data.get('keycodes', {})
        
        if not keycodes:
            print(f"No IR codes found in {self.ir_keycodes_file}")
            return
        
        print("\n" + "=" * 70)
        print(f"IR CODES IN {self.ir_keycodes_file}")
        print("=" * 70)
        
        for key_name, key_data in keycodes.items():
            print(f"\n🔑 {key_name}")
            print(f"   Display: {key_data.get('display_name', 'N/A')}")
            print(f"   Description: {key_data.get('description', 'N/A')}")
            print(f"   Command: {key_data.get('command_template', 'N/A')[:60]}...")


def main():
    parser = argparse.ArgumentParser(
        description='IR Code Capture Tool for Global Cache iTach',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive capture mode
  python ir_code_capture.py --itach-ip 10.0.0.33 --capture
  
  # Test existing key
  python ir_code_capture.py --itach-ip 10.0.0.33 --test HOME
  
  # List all keys
  python ir_code_capture.py --list
  
  # Capture single key non-interactively
  python ir_code_capture.py --itach-ip 10.0.0.33 --capture-key MUTE --port 1
        """
    )
    
    parser.add_argument('--itach-ip', default='10.0.0.33', 
                       help='iTach device IP address (default: 10.0.0.33)')
    parser.add_argument('--itach-port', type=int, default=4998,
                       help='iTach device port (default: 4998)')
    parser.add_argument('--capture', action='store_true',
                       help='Start interactive capture mode')
    parser.add_argument('--capture-key', type=str,
                       help='Capture a specific key non-interactively')
    parser.add_argument('--port', type=int, default=1, choices=[1, 2, 3],
                       help='IR port number for capture (default: 1)')
    parser.add_argument('--test', type=str,
                       help='Test an existing key by name')
    parser.add_argument('--list', action='store_true',
                       help='List all keys in ir_keycodes.json')
    
    args = parser.parse_args()
    
    # Create capture tool
    tool = IRCodeCapture(itach_ip=args.itach_ip, itach_port=args.itach_port)
    
    # Execute requested action
    if args.list:
        tool.list_keys()
    
    elif args.test:
        tool.test_ir_code(args.test)
    
    elif args.capture:
        tool.interactive_capture()
    
    elif args.capture_key:
        print(f"🎯 Capturing IR code for '{args.capture_key}'")
        ir_command = tool.capture_ir_code(port=args.port, timeout=15)
        if ir_command:
            tool.add_or_update_key(
                key_name=args.capture_key.upper(),
                ir_command=ir_command
            )
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
