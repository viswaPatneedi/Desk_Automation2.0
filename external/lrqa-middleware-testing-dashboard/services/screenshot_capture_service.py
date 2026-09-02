#!/usr/bin/env python3
"""
Screenshot capture service for devices via R-Pi tunnel
Fetches screenshot from device and saves to local storage
"""

import requests
import os
import json
import time
import base64
import shlex
from datetime import datetime
from pathlib import Path

class ScreenshotCaptureService:
    """Captures screenshots from devices through R-Pi tunnel"""
    
    def __init__(self, app_root_dir):
        """Initialize screenshot service
        
        Args:
            app_root_dir: Root directory of Flask app
        """
        self.app_root = Path(app_root_dir)
        try:
            from methods.method_utils import get_execution_screenshots_dir
            screenshot_dir = get_execution_screenshots_dir()
        except ImportError:
            screenshot_dir = 'screenshots'
        self.screenshots_dir = Path(screenshot_dir)
        if not self.screenshots_dir.is_absolute():
            self.screenshots_dir = self.app_root / self.screenshots_dir
        self.screenshots_dir.mkdir(exist_ok=True)
        
    def capture_screenshot(self, device_ip, screenshot_port=5800, timeout=10, ssh=None):
        """Capture screenshot from device via tunnel
        
        Args:
            device_ip: Device IP address (e.g., 10.0.0.28)
            screenshot_port: Device screenshot port (default 5800)
            timeout: Request timeout in seconds
        
        Returns:
            dict with keys:
                - success: bool
                - screenshot_path: str (local path to saved screenshot)
                - device_ip: str
                - timestamp: str
                - size_bytes: int
                - error: str (optional)
        """
        timestamp = datetime.now().isoformat()
        
        print(f"\n[SCREENSHOT] Capturing from device {device_ip}...")
        
        try:
            if ssh:
                filename_prefix = f"screenshot_{device_ip.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                # VNC is reachable from the R-Pi network, not from the dashboard
                # host. Stream it from the persistent R-Pi session with a bounded
                # curl timeout, encoded safely for the SSH command response.
                command = (
                    f"curl --fail --silent --show-error --max-time {int(timeout)} "
                    f"http://{shlex.quote(device_ip)}:{int(screenshot_port)}/screenshot.png | base64 -w 0"
                )
                success, encoded_image, error = ssh.execute_rpi_command(command, timeout=timeout + 5)
                if not success or not encoded_image:
                    return {
                        'success': False,
                        'device_ip': device_ip,
                        'timestamp': timestamp,
                        'error': error or 'VNC screenshot capture through R-Pi failed'
                    }

                screenshot_path = self.screenshots_dir / f"{filename_prefix}.png"
                try:
                    with open(screenshot_path, 'wb') as screenshot_file:
                        screenshot_file.write(base64.b64decode(encoded_image))
                except Exception as error:
                    return {
                        'success': False,
                        'device_ip': device_ip,
                        'timestamp': timestamp,
                        'error': f'Invalid VNC screenshot response: {error}'
                    }

                return {
                    'success': True,
                    'screenshot_path': str(screenshot_path),
                    'filename': os.path.basename(screenshot_path),
                    'device_ip': device_ip,
                    'timestamp': timestamp,
                    'size_bytes': os.path.getsize(screenshot_path),
                    'content_type': 'image/png'
                }

            # Screenshot URL - uses forwarded port on localhost
            # The tunnel forwards 127.0.0.1:5800 → device_ip:5800
            screenshot_url = f"http://127.0.0.1:{screenshot_port}/screenshot.png"
            
            print(f"[SCREENSHOT] URL: http://{device_ip}:{screenshot_port}/screenshot.png")
            print(f"[SCREENSHOT] Fetching from tunnel forwarder: {screenshot_url}")
            
            # Fetch screenshot through forwarded port
            response = requests.get(screenshot_url, timeout=timeout)
            
            if response.status_code != 200:
                error = f"HTTP {response.status_code}"
                print(f"[SCREENSHOT] ERROR: {error}")
                return {
                    'success': False,
                    'device_ip': device_ip,
                    'timestamp': timestamp,
                    'error': error
                }
            
            # Verify it's an image
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type and 'png' not in content_type and 'jpeg' not in content_type:
                print(f"[SCREENSHOT] WARNING: Unexpected content-type: {content_type}")
            
            # Generate filename
            device_label = device_ip.replace('.', '_')
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshot_{device_label}_{timestamp_str}.png"
            filepath = self.screenshots_dir / filename
            
            # Save screenshot
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            size_bytes = len(response.content)
            
            print(f"[SCREENSHOT] SUCCESS: Screenshot saved")
            print(f"[SCREENSHOT] File: {filename}")
            print(f"[SCREENSHOT] Size: {size_bytes} bytes")
            print(f"[SCREENSHOT] Path: {filepath}")
            
            return {
                'success': True,
                'screenshot_path': str(filepath),
                'filename': filename,
                'device_ip': device_ip,
                'timestamp': timestamp,
                'size_bytes': size_bytes,
                'content_type': content_type
            }
        
        except requests.exceptions.Timeout:
            error = f"Request timeout after {timeout}s"
            print(f"[SCREENSHOT] ERROR: {error}")
            return {
                'success': False,
                'device_ip': device_ip,
                'timestamp': timestamp,
                'error': error
            }
        
        except requests.exceptions.ConnectionError as e:
            error = f"Connection error: {str(e)[:100]}"
            print(f"[SCREENSHOT] ERROR: {error}")
            print(f"[SCREENSHOT] Make sure tunnel is active on port {screenshot_port}")
            return {
                'success': False,
                'device_ip': device_ip,
                'timestamp': timestamp,
                'error': error
            }
        
        except Exception as e:
            error = f"Capture error: {str(e)[:100]}"
            print(f"[SCREENSHOT] ERROR: {error}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'device_ip': device_ip,
                'timestamp': timestamp,
                'error': error
            }
    
    def verify_screenshot(self, filepath):
        """Verify screenshot is a valid image file
        
        Args:
            filepath: Path to screenshot file
        
        Returns:
            dict with verification details
        """
        print(f"\n[SCREENSHOT] Verifying: {filepath}")
        
        try:
            path = Path(filepath)
            
            if not path.exists():
                print(f"[SCREENSHOT] ERROR: File does not exist")
                return {'valid': False, 'error': 'File not found'}
            
            # Check file size
            size = path.stat().st_size
            if size == 0:
                print(f"[SCREENSHOT] ERROR: File is empty")
                return {'valid': False, 'error': 'File is empty', 'size': 0}
            
            # Check PNG signature (first 8 bytes)
            with open(path, 'rb') as f:
                header = f.read(8)
            
            # PNG magic number: 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A
            png_magic = b'\x89PNG\r\n\x1a\n'
            
            if header == png_magic:
                print(f"[SCREENSHOT] VERIFIED: Valid PNG file")
                print(f"[SCREENSHOT] Size: {size} bytes")
                return {
                    'valid': True,
                    'size': size,
                    'format': 'PNG',
                    'filepath': str(path)
                }
            else:
                print(f"[SCREENSHOT] WARNING: File header doesn't match PNG signature")
                print(f"[SCREENSHOT] Header bytes: {header.hex()}")
                return {
                    'valid': False,
                    'error': 'Not a valid PNG file',
                    'size': size,
                    'header': header.hex()
                }
        
        except Exception as e:
            error = f"Verification error: {str(e)[:100]}"
            print(f"[SCREENSHOT] ERROR: {error}")
            return {'valid': False, 'error': error}
    
    def get_screenshots_dir(self):
        """Get screenshots directory path"""
        return str(self.screenshots_dir)
    
    def list_screenshots(self, device_ip=None):
        """List all captured screenshots
        
        Args:
            device_ip: Optional device IP filter
        
        Returns:
            list of screenshot files
        """
        if not self.screenshots_dir.exists():
            return []
        
        screenshots = sorted(self.screenshots_dir.glob('screenshot_*.png'), reverse=True)
        
        if device_ip:
            device_label = device_ip.replace('.', '_')
            screenshots = [s for s in screenshots if device_label in s.name]
        
        return [{'filename': s.name, 'path': str(s), 'size': s.stat().st_size} for s in screenshots]
