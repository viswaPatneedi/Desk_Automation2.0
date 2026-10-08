#!/usr/bin/env python3
"""
Base Image Capture Method
Captures screenshots from device and stores them in reference_screens folder with custom names.
These images can be used later for screen-to-screen comparison with layout and text validation.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List
from PIL import Image
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot

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
    
    Captures the current frame from the device's VNC HTTP screenshot endpoint
    and saves it to reference_screens using the provided screen name.
    
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
    
    try:
        # Sanitize screen name for filename
        safe_screen_name = screen_name.strip()
        if safe_screen_name.lower().endswith('.png'):
            safe_screen_name = safe_screen_name[:-4]
        safe_screen_name = safe_screen_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
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
        
        log("\n[STEP 1/1] 📷 Capturing current screen over VNC HTTP...")
        screenshot_result = take_vnc_screenshot(
            device_ip=device_ip,
            screenshot_folder=REFERENCE_SCREENS_DIR,
            device_name=safe_screen_name,
            iteration=0,
            vnc_port=5800,
            log_callback=log,
            validate_image=False,
            context=None
        )

        if screenshot_result and screenshot_result.get('success'):
            captured_path = screenshot_result.get('local_path')
            final_path = os.path.join(REFERENCE_SCREENS_DIR, f"{safe_screen_name}.png")
            with Image.open(captured_path) as image:
                image.verify()
            if os.path.abspath(captured_path) != os.path.abspath(final_path):
                os.replace(captured_path, final_path)
            local_path = final_path
            log("   ✅ Screenshot captured successfully")
            log(f"   📁 Saved to: {local_path}")
            
            # Get file size
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                log(f"   📊 File size: {file_size / 1024:.2f} KB")
            else:
                file_size = 0
            
            return {
                "success": True,
                "message": f"✅ Base image captured successfully: {safe_screen_name}.png",
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
