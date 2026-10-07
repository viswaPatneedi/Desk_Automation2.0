"""
Method: Capture Current Screen
Prompts user for image name, captures screenshot, saves to USB session folder.
Optionally runs OCR on the captured image so the extracted text can be used
by a later step (e.g. checking device logs for the captured text).
"""
import paramiko
from methods.method_utils import get_execution_ssh_client
from utils.screenshot_utils import take_and_analyze_screenshot
from tools.screen.screenshot_utils_vnc import take_vnc_screenshot_with_fallback
import os


def extract_text_from_local_image(image_path, log_callback=None):
    """OCR a locally saved screenshot file and return the extracted text."""
    def log(message):
        if log_callback:
            log_callback(message)

    try:
        import pytesseract
        from PIL import Image

        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img).strip()

        log(f"✓ Text extracted from captured screen ({len(text)} characters)")
        if text:
            log(f"   Extracted text: {text[:300]}{'...' if len(text) > 300 else ''}")
        return text
    except Exception as e:
        log(f"⚠ Failed to extract text from captured screen: {str(e)}")
        return ''


def capture_current_screen(device_ip, port, username, password, image_name, screenshots_dir, iteration, device_name, log_callback=None, extract_text=False):
    def log(message):
        if log_callback:
            log_callback(message)
    
    # Ensure screenshots_dir exists
    os.makedirs(screenshots_dir, exist_ok=True)
    
    try:
        # Connect via SSH (kept open only for the VNC->plugin fallback path)
        ssh = get_execution_ssh_client()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        
        # Compose screenshot file name using user-provided image_name and context
        safe_device_name = device_name.replace(' ', '-').replace('/', '_').replace('\\', '_')
        screenshot_file_name = f"{device_ip}_{safe_device_name}_Iteration-{iteration}_{image_name}"
        
        log(f"📸 Capturing screenshot with name: {image_name}")
        log(f"   File will be saved as: {screenshot_file_name}.png")
        
        # Same fast VNC-first capture (with plugin fallback) used by Reboot Performance V2 - Optimized
        result = take_vnc_screenshot_with_fallback(
            ssh=ssh,
            device_ip=device_ip,
            device_name=safe_device_name,
            iteration=iteration,
            screenshot_folder=screenshots_dir,
            log_callback=log_callback,
            fallback_to_plugin=True,
            context=image_name
        )
        ssh.close()
        
        # Return path and status
        screenshot_path = result.get('local_path', '')
        success = result.get('success', False)
        
        if success and screenshot_path:
            # Rename to the user-requested naming convention (drop the internal timestamp suffix)
            final_path = os.path.join(screenshots_dir, f"{screenshot_file_name}.png")
            try:
                if os.path.abspath(screenshot_path) != os.path.abspath(final_path):
                    os.replace(screenshot_path, final_path)
                    screenshot_path = final_path
            except OSError as rename_err:
                log(f"⚠ Could not rename screenshot to expected name: {rename_err}")
            
            log(f"✓ Screenshot captured successfully")
            log(f"   Path: {screenshot_path}")

            extracted_text = ''
            if extract_text:
                log(f"🔎 Fetching text from captured screen (OCR)...")
                extracted_text = extract_text_from_local_image(screenshot_path, log_callback)

            return {
                'success': True,
                'screenshot_path': screenshot_path,
                'usb_folder': screenshots_dir,
                'details': f"Screenshot saved as {screenshot_file_name}.png",
                'image_name': image_name,
                'extracted_text': extracted_text
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
