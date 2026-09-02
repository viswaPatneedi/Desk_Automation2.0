#!/usr/bin/env python3
"""
Base Image Capture Method
Captures screenshots from device and stores them in reference_screens folder with custom names.
These images can be used later for screen-to-screen comparison with layout and text validation.
"""

import os
import sys
import time
import paramiko
from methods.method_utils import get_execution_ssh_client
from datetime import datetime, timezone
from typing import Dict, List
from utils.screenshot_utils import take_and_analyze_screenshot
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback

# Reference screens directory
REFERENCE_SCREENS_DIR = os.path.join(os.path.dirname(__file__), "reference_screens")

# Ensure reference screens directory exists
os.makedirs(REFERENCE_SCREENS_DIR, exist_ok=True)


def capture_base_image(
    device_ip: str,
    screen_name: str,
    port: int = 10022,
    username: str = "root",
    password: str = "",
    log_callback=None
) -> Dict:
    """
    Capture screenshot from device and save as reference base image.
    
    This method:
    1. Connects to device via SSH
    2. Activates ScreenCapture plugin
    3. Captures current screen
    4. Saves to reference_screens folder with provided name
    5. Returns success/failure status with file path
    
    Args:
        device_ip: IP address of the device
        screen_name: Name to save the image as (e.g., "home_screen", "login_page")
        port: SSH port (default: 10022)
        username: SSH username (default: "root")
        password: SSH password
        log_callback: Optional function for logging
    
    Returns:
        Dict with fields:
            - success (bool): Capture succeeded or failed
            - message (str): Detailed result message
            - image_path (str): Full path to saved image file
            - screen_name (str): Name of the captured screen
            - timestamp (str): ISO format timestamp
    
    Example:
        result = capture_base_image("10.0.0.126", "xumo_home_screen")
        if result['success']:
            print(f"Image saved: {result['image_path']}")
    """
    
    def log(message):
        """Helper to log messages"""
        print(message)
        if log_callback:
            log_callback(message)
    
    ssh = None
    
    try:
        # Sanitize screen name for filename
        safe_screen_name = screen_name.replace(' ', '_').replace('/', '_')
        safe_screen_name = ''.join(c for c in safe_screen_name if c.isalnum() or c in ('_', '-'))
        
        if not safe_screen_name:
            return {
                "success": False,
                "message": "Invalid screen name provided",
                "image_path": None,
                "screen_name": screen_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        log(f"📸 Capturing base image for: {screen_name}")
        log(f"   Device: {device_ip}")
        log(f"   Target folder: reference_screens/")
        
        # Step 1: Connect via SSH
        log("\n[STEP 1/2] 🔌 Connecting to device...")
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        log("   ✅ SSH connection established")
        
        # Step 2: Capture screenshot using the same method as reboot
        log("\n[STEP 2/2] 📷 Capturing and downloading screenshot...")
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"{safe_screen_name}_{timestamp_str}"
        
        # Use take_and_analyze_screenshot which handles activation, capture, and download
        screenshot_result = take_and_analyze_screenshot(
            ssh=ssh,
            screenshot_name=screenshot_name,
            device_ip=device_ip,
            log_callback=log,
            screenshot_folder=REFERENCE_SCREENS_DIR,
            after_reboot=False
        )
        
        ssh.close()
        
        if screenshot_result and screenshot_result.get('success'):
            local_path = screenshot_result.get('local_path')
            log(f"   ✅ Screenshot captured successfully")
            log(f"   📁 Saved to: {local_path}")
            
            # Get file size
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                log(f"   📊 File size: {file_size / 1024:.2f} KB")
            else:
                file_size = 0
            
            return {
                "success": True,
                "message": f"✅ Base image captured successfully: {screenshot_name}.png",
                "image_path": local_path,
                "screen_name": screen_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "file_size": file_size
            }
        else:
            error_msg = screenshot_result.get('error', 'Unknown error') if screenshot_result else 'Screenshot failed'
            return {
                "success": False,
                "message": f"Screenshot capture failed: {error_msg}",
                "image_path": None,
                "screen_name": screen_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    except paramiko.AuthenticationException:
        error_msg = "SSH authentication failed - check credentials"
        log(f"\n❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "image_path": None,
            "screen_name": screen_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except paramiko.SSHException as e:
        error_msg = f"SSH connection error: {str(e)}"
        log(f"\n❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "image_path": None,
            "screen_name": screen_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        log(f"\n❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "image_path": None,
            "screen_name": screen_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    finally:
        if ssh:
            try:
                ssh.close()
            except:
                pass


def list_base_images() -> List[Dict]:
    """
    List all captured base images in reference_screens folder.
    
    Returns:
        List of dicts with image information:
            - filename: Name of the image file
            - path: Full path to image
            - size: File size in bytes
            - created: Creation timestamp
    """
    images = []
    
    if not os.path.exists(REFERENCE_SCREENS_DIR):
        return images
    
    for filename in sorted(os.listdir(REFERENCE_SCREENS_DIR)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filepath = os.path.join(REFERENCE_SCREENS_DIR, filename)
            stat = os.stat(filepath)
            
            images.append({
                "filename": filename,
                "path": filepath,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
    
    return images


# Example usage and testing
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python method_capture_base_image.py <device_ip> <screen_name>")
        print("\nExample: python method_capture_base_image.py 10.0.0.126 xumo_home_screen")
        print("\nThis will capture the current screen and save it as a reference image")
        print("in the reference_screens/ folder for later comparison.")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    screen_name = sys.argv[2]
    
    print(f"\n=== Base Image Capture ===")
    print(f"Device: {device_ip}")
    print(f"Screen Name: {screen_name}")
    print("=" * 50)
    
    result = capture_base_image(device_ip, screen_name)
    
    print("\n=== Result ===")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    
    if result['image_path']:
        print(f"Image Path: {result['image_path']}")
    
    if result['success']:
        print("\n✅ Base image captured successfully!")
        print("\nYou can now use this image for screen validation:")
        print(f"  Screen name: {screen_name}")
        print(f"  Image file: {os.path.basename(result['image_path'])}")
    else:
        print("\n❌ Failed to capture base image")
