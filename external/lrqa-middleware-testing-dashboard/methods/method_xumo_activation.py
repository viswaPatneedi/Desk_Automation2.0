#!/usr/bin/env python3
"""
XUMO Activation Method
Fetches activation code from device and runs automated activation via Selenium.
This method can be called as part of test execution workflow.

NOTE: Browser automation requires compatible browser setup:
- ARM64 (Raspberry Pi): Requires Firefox + geckodriver or Playwright
- x86_64 (Cloud): Works with Chrome/Chromium + chromedriver
- See XUMO_ACTIVATION_SETUP.md for detailed setup instructions
"""

import os
import sys
import subprocess
import traceback
import platform
from typing import Dict
from methods.method_fetch_activation_code import fetch_xumo_activation_code

def activate_xumo(device_ip: str, port: int = 10022, username: str = "root", password: str = "") -> Dict:
    """
    Activate XUMO device by fetching code and running auto_activate_xumo.py script.
    
    This method:
    1. Fetches activation code from device via SSH
    2. Runs Selenium-based activation script (requires browser setup)
    3. Returns success/failure status
    
    Args:
        device_ip: IP address of the XUMO device
        port: SSH port (default: 10022)
        username: SSH username (default: "root")
        password: SSH password (default: "")
    
    Returns:
        Dict with fields:
            - success (bool): Activation succeeded or failed
            - message (str): Detailed result message
            - activation_code (str): The code that was used
            - script_output (str): Output from activation script
            - browser_error (bool): True if error was browser-related
    
    Example:
        result = activate_xumo("10.0.0.126")
        if result['success']:
            print(f"Activated with code: {result['activation_code']}")
        elif result.get('browser_error'):
            print("Browser setup issue - see XUMO_ACTIVATION_SETUP.md")
    """
    
    try:
        # Step 1: Pre-flight check - Verify internet connectivity
        print(f"\n🔍 Pre-flight check: Testing internet connectivity...")
        try:
            import urllib.request
            urllib.request.urlopen('https://www.xumo.com', timeout=10)
            print(f"✅ Internet connectivity confirmed - xumo.com is reachable")
        except Exception as conn_err:
            print(f"❌ Internet connectivity issue: {conn_err}")
            print(f"⚠️  Cannot reach www.xumo.com - activation will likely fail")
            print(f"💡 Please check:")
            print(f"   • Raspberry Pi internet connection")
            print(f"   • Network firewall settings")
            print(f"   • DNS resolution (try: ping www.xumo.com)")
            return {
                "success": False,
                "message": f"Pre-flight check failed: Cannot reach xumo.com - {str(conn_err)}",
                "activation_code": None,
                "script_output": f"Internet connectivity test failed: {str(conn_err)}",
                "browser_error": False
            }
        
        # Step 2: Fetch activation code from device
        print(f"📱 Fetching activation code from device {device_ip}...")
        code_result = fetch_xumo_activation_code(device_ip, port, username, password)
        
        if not code_result['success']:
            return {
                "success": False,
                "message": f"Failed to fetch activation code: {code_result['message']}",
                "activation_code": None,
                "script_output": None,
                "browser_error": False
            }
        
        activation_code = code_result['activation_code']
        print(f"✅ Fetched activation code: {activation_code}")
        print(f"   Expiry: {code_result.get('expiry', 'N/A')}")
        
        # Step 3: Run activation script
        print(f"🌐 Running XUMO activation script...")
        print(f"   Platform: {platform.system()} / {platform.machine()}")
        
        # Try Playwright version first (better ARM support), fallback to Selenium
        playwright_script = os.path.join(os.path.dirname(__file__), "auto_activate_xumo_playwright.py")
        selenium_script = os.path.join(os.path.dirname(__file__), "auto_activate_xumo.py")
        
        if os.path.exists(playwright_script):
            script_path = playwright_script
            print(f"   Using Playwright version (better ARM64 support)")
        elif os.path.exists(selenium_script):
            script_path = selenium_script
            print(f"   Using Selenium version")
        else:
            return {
                "success": False,
                "message": f"No activation script found (tried playwright and selenium versions)",
                "activation_code": activation_code,
                "script_output": None,
                "browser_error": True
            }
        
        # Run the activation script with the fetched code
        # Note: This requires playwright or selenium/browser setup
        try:
            # Stream output in real-time instead of capturing at end
            process = subprocess.Popen(
                [sys.executable, script_path, "--code", activation_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            script_output_lines = []
            
            # Read and print output line by line for real-time logging
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.rstrip()
                    print(line)  # This goes to log_service in real-time
                    script_output_lines.append(line)
            
            # Wait for process to complete
            return_code = process.wait(timeout=120)
            script_output = '\n'.join(script_output_lines)
            
            # Check for browser-related errors
            browser_error_indicators = [
                "No supported browser found",
                "Exec format error",
                "Failed to setup browser driver",
                "geckodriver",
                "chromedriver",
                "cannot execute binary file",
                "Missing X server"
            ]
            
            is_browser_error = any(indicator in script_output for indicator in browser_error_indicators)
            
            if return_code == 0:
                return {
                    "success": True,
                    "message": f"✅ XUMO activation completed successfully with code {activation_code}",
                    "activation_code": activation_code,
                    "script_output": script_output,
                    "browser_error": False
                }
            else:
                error_message = f"Activation script failed with exit code {return_code}"
                
                if is_browser_error:
                    error_message += "\n⚠️  Browser setup issue detected. See XUMO_ACTIVATION_SETUP.md for solutions."
                    
                    # Add platform-specific hint
                    arch = platform.machine().lower()
                    if 'arm' in arch or 'aarch64' in arch:
                        error_message += "\n💡 ARM Platform: Playwright now installed - should work!"
                    else:
                        error_message += "\n💡 x86_64 Platform: Install chromium-browser and try again"
                
                return {
                    "success": False,
                    "message": error_message,
                    "activation_code": activation_code,
                    "script_output": script_output,
                    "browser_error": is_browser_error
                }
                
        except subprocess.TimeoutExpired as e:
            # Process timed out, try to kill it
            try:
                process.kill()
                remaining_output = process.stdout.read()
                if remaining_output:
                    print(remaining_output)
            except:
                pass
            
            return {
                "success": False,
                "message": "Activation script timed out after 2 minutes",
                "activation_code": activation_code,
                "script_output": '\n'.join(script_output_lines) + "\n[TIMEOUT]",
                "browser_error": False
            }
        except FileNotFoundError:
            return {
                "success": False,
                "message": "Python executable not found or selenium not installed",
                "activation_code": activation_code,
                "script_output": None,
                "browser_error": False
            }
            
    except Exception as e:
        error_msg = str(e)
        is_browser_error = any(term in error_msg.lower() for term in ['browser', 'driver', 'selenium', 'geckodriver', 'chromedriver'])
        
        return {
            "success": False,
            "message": f"Error during XUMO activation: {error_msg}\n{traceback.format_exc()}",
            "activation_code": None,
            "script_output": None,
            "browser_error": is_browser_error
        }


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python method_xumo_activation.py <device_ip>")
        print("\nExample: python method_xumo_activation.py 10.0.0.126")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    
    print(f"\n=== XUMO Activation ===")
    print(f"Device: {device_ip}")
    print("=" * 50)
    
    result = activate_xumo(device_ip)
    
    print("\n=== Result ===")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    
    if result['activation_code']:
        print(f"Activation Code: {result['activation_code']}")
    
    if result['script_output']:
        print(f"\n=== Script Output ===")
        print(result['script_output'])
