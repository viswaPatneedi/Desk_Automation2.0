"""
Method: Capture Current Screen
Prompts user for image name, captures screenshot, saves to USB session folder.
"""
import paramiko
from methods.method_utils import get_execution_ssh_client
from utils.screenshot_utils import take_and_analyze_screenshot
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback
import os

def capture_current_screen(device_ip, port, username, password, image_name, screenshots_dir, iteration, device_name, log_callback=None):
    def log(message):
        if log_callback:
            log_callback(message)
    
    # Ensure screenshots_dir exists
    os.makedirs(screenshots_dir, exist_ok=True)
    
    try:
        # Connect via SSH
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        
        # Compose screenshot file name using user-provided image_name and context
        safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_')
        screenshot_file_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_{image_name}"
        
        log(f"📸 Capturing screenshot with name: {image_name}")
        log(f"   File will be saved as: {screenshot_file_name}.png")
        
        # Capture screenshot
        result = take_and_analyze_screenshot(
            ssh,
            screenshot_file_name,
            device_ip,
            log_callback=log_callback,
            screenshot_folder=screenshots_dir
        )
        ssh.close()
        
        # Return path and status
        screenshot_path = result.get('local_path', '')
        success = result.get('success', False)
        
        if success and screenshot_path:
            log(f"✓ Screenshot captured successfully")
            log(f"   Path: {screenshot_path}")
            return {
                'success': True,
                'screenshot_path': screenshot_path,
                'usb_folder': screenshots_dir,
                'details': f"Screenshot saved as {screenshot_file_name}.png",
                'image_name': image_name
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            log(f"✗ Screenshot capture failed: {error_msg}")
            return {
                'success': False,
                'screenshot_path': '',
                'usb_folder': screenshots_dir,
                'details': f"Failed to capture screenshot: {error_msg}",
                'image_name': image_name
            }
    except Exception as e:
        log(f"✗ Error capturing screenshot: {str(e)}")
        return {
            'success': False,
            'screenshot_path': '',
            'usb_folder': screenshots_dir,
            'details': f"Error: {str(e)}",
            'image_name': image_name
        }
