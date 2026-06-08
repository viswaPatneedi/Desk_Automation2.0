"""
Screen Validation Service using SAM-CD (Change Detection)

This service integrates the SAM-CD-2GB change detection model to validate
whether captured screenshots match expected screen states (HOME, Netflix, YouTube, etc.)
"""

import os
import sys
import shutil
from pathlib import Path

# Add SAM-CD module to path
SAM_CD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SAM-CD-2GB', 'SAM-CD_2GB')
sys.path.insert(0, SAM_CD_PATH)
sys.path.insert(0, os.path.join(SAM_CD_PATH, 'segment_anything'))

from main import end_to_end_ic, compare_screens, scale_image_to_512_if_needed


class ScreenValidationService:
    """Service for validating device screens using AI-powered change detection"""
    
    def __init__(self):
        """Initialize the screen validation service with model paths"""
        self.sam_cd_base = SAM_CD_PATH
        self.model_path = os.path.join(self.sam_cd_base, 'stanet_bam_workdir', 'stanet_bam_256x256_40k_levircd.py')
        self.weights_path = os.path.join(self.sam_cd_base, 'stanet_bam_workdir', 'best_mIoU_iter_40000.pth')
        self.classes = ('unchanged', 'changed')
        self.palette = [[0, 0, 0], [255, 255, 255]]
        
        # Reference images directory (to be created per device)
        self.reference_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reference_screens')
        os.makedirs(self.reference_base, exist_ok=True)
        
    def validate_screen(self, screenshot_path, expected_screen, device_name=None, 
                       change_ratio=0.0005, use_aspect_ratio=True, region=None):
        """
        Validate if a screenshot matches the expected screen state
        
        Args:
            screenshot_path (str): Path to the captured screenshot
            expected_screen (str): Screen identifier (e.g., 'HOME', 'NETFLIX', 'YOUTUBE_SIGNIN')
            device_name (str): Device name for device-specific reference images
            change_ratio (float): Threshold for change detection (lower = more similar)
            use_aspect_ratio (bool): Whether to maintain aspect ratio during comparison
            region (list): Optional [x1, x2, y1, y2] for region-of-interest comparison
            
        Returns:
            dict: {
                'is_valid': bool,
                'screen_matched': str or None,
                'change_ratio': float or None,
                'method_used': str
            }
        """
        if not os.path.exists(screenshot_path):
            return {
                'is_valid': False,
                'screen_matched': None,
                'change_ratio': None,
                'method_used': None,
                'error': f"Screenshot not found: {screenshot_path}"
            }
        
        # Get reference image path
        reference_path = self._get_reference_image(expected_screen, device_name)
        
        if not reference_path:
            return {
                'is_valid': False,
                'screen_matched': None,
                'change_ratio': None,
                'method_used': 'direct',
                'error': f"No reference image found for screen: {expected_screen}"
            }
        
        try:
            # Use end-to-end comparison (tries multiple methods)
            is_match = end_to_end_ic(
                current_screen=screenshot_path,
                reference=reference_path,
                model_path=self.model_path,
                weights_path=self.weights_path,
                ar=use_aspect_ratio,
                region=region
            )
            
            return {
                'is_valid': is_match,
                'screen_matched': expected_screen if is_match else None,
                'change_ratio': None,  # end_to_end_ic doesn't return ratio
                'method_used': 'end_to_end'
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'screen_matched': None,
                'change_ratio': None,
                'method_used': 'end_to_end',
                'error': str(e)
            }
    
    def validate_screen_direct(self, screenshot_path, reference_image_path, 
                              change_ratio=0.0005, region=None):
        """
        Direct comparison between screenshot and a specific reference image
        
        Args:
            screenshot_path (str): Path to captured screenshot
            reference_image_path (str): Path to reference image
            change_ratio (float): Threshold for change detection
            region (list): Optional [x1, x2, y1, y2] for ROI comparison
            
        Returns:
            dict: Validation result with change ratio
        """
        if not os.path.exists(screenshot_path):
            return {'is_valid': False, 'error': 'Screenshot not found'}
        
        if not os.path.exists(reference_image_path):
            return {'is_valid': False, 'error': 'Reference image not found'}
        
        try:
            is_match = compare_screens(
                current_screen_path=screenshot_path,
                reference_input=reference_image_path,
                model=self.model_path,
                weights=self.weights_path,
                classes=self.classes,
                palette=self.palette,
                ratio=change_ratio,
                region=region
            )
            
            return {
                'is_valid': is_match,
                'screen_matched': os.path.basename(reference_image_path),
                'method_used': 'direct',
                'change_ratio_threshold': change_ratio
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'method_used': 'direct'
            }
    
    def validate_screen_against_multiple(self, screenshot_path, reference_dir, 
                                        change_ratio=0.0005, region=None):
        """
        Compare screenshot against multiple reference images in a directory
        
        Args:
            screenshot_path (str): Path to captured screenshot
            reference_dir (str): Directory containing reference images
            change_ratio (float): Threshold for change detection
            region (list): Optional [x1, x2, y1, y2] for ROI comparison
            
        Returns:
            dict: Validation result indicating which reference matched (if any)
        """
        if not os.path.exists(screenshot_path):
            return {'is_valid': False, 'error': 'Screenshot not found'}
        
        if not os.path.isdir(reference_dir):
            return {'is_valid': False, 'error': 'Reference directory not found'}
        
        try:
            is_match = compare_screens(
                current_screen_path=screenshot_path,
                reference_input=reference_dir,
                model=self.model_path,
                weights=self.weights_path,
                classes=self.classes,
                palette=self.palette,
                ratio=change_ratio,
                region=region
            )
            
            return {
                'is_valid': is_match,
                'reference_dir': reference_dir,
                'method_used': 'multiple',
                'change_ratio_threshold': change_ratio
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'method_used': 'multiple'
            }
    
    def _get_reference_image(self, screen_name, device_name=None):
        """
        Get reference image path for a given screen
        
        Args:
            screen_name (str): Screen identifier
            device_name (str): Optional device-specific reference
            
        Returns:
            str or None: Path to reference image if found
        """
        # Normalize screen name for matching (remove common suffixes)
        normalized_name = screen_name.replace('_SCREEN', '').replace('_Screen', '')
        
        # Generate alternative name formats for flexible matching
        alternative_names = [
            screen_name,  # Original name
            normalized_name,  # Without _SCREEN suffix
            screen_name.replace('_', ''),  # No underscores
            normalized_name.replace('_', ''),  # No underscores, no suffix
        ]
        
        # Helper function to normalize for comparison (removes special chars, converts to lowercase)
        def normalize_for_comparison(name):
            return name.replace('_', '').replace('-', '').replace(' ', '').lower()
        
        # Try device-specific reference first
        if device_name:
            device_ref_dir = os.path.join(self.reference_base, device_name)
            if os.path.isdir(device_ref_dir):
                for name in alternative_names:
                    for ext in ['.png', '.jpg', '.jpeg']:
                        ref_path = os.path.join(device_ref_dir, f"{name}{ext}")
                        if os.path.exists(ref_path):
                            return ref_path
        
        # Try all subdirectories in reference base (for organized folders like FactoryReset-XUMO-TV)
        try:
            normalized_search = normalize_for_comparison(screen_name)
            
            for subdir in os.listdir(self.reference_base):
                subdir_path = os.path.join(self.reference_base, subdir)
                if os.path.isdir(subdir_path):
                    # Case-insensitive and flexible search within subdirectory
                    for filename in os.listdir(subdir_path):
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            name_without_ext = os.path.splitext(filename)[0]
                            normalized_filename = normalize_for_comparison(name_without_ext)
                            
                            # Check if normalized names match
                            if normalized_filename == normalized_search:
                                print(f"[SCREEN VALIDATION] Matched '{screen_name}' to '{filename}' in {subdir}/")
                                return os.path.join(subdir_path, filename)
        except Exception as e:
            print(f"Warning: Error searching subdirectories: {e}")
        
        # Try generic reference (root level)
        for name in alternative_names:
            for ext in ['.png', '.jpg', '.jpeg']:
                ref_path = os.path.join(self.reference_base, f"{name}{ext}")
                if os.path.exists(ref_path):
                    return ref_path
        
        return None
    
    def add_reference_image(self, screen_name, image_path, device_name=None):
        """
        Add a new reference image for a screen state
        
        Args:
            screen_name (str): Screen identifier
            image_path (str): Path to the reference image
            device_name (str): Optional device-specific reference
            
        Returns:
            dict: Result of the operation
        """
        if not os.path.exists(image_path):
            return {'success': False, 'error': 'Source image not found'}
        
        try:
            # Determine destination directory
            if device_name:
                dest_dir = os.path.join(self.reference_base, device_name)
            else:
                dest_dir = self.reference_base
            
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy and rename reference image
            ext = os.path.splitext(image_path)[1]
            dest_path = os.path.join(dest_dir, f"{screen_name}{ext}")
            shutil.copy2(image_path, dest_path)
            
            return {
                'success': True,
                'reference_path': dest_path,
                'screen_name': screen_name,
                'device_name': device_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_reference_images(self, device_name=None):
        """
        List all available reference images
        
        Args:
            device_name (str): Optional filter by device
            
        Returns:
            list: List of available reference screens
        """
        references = []
        
        if device_name:
            search_dir = os.path.join(self.reference_base, device_name)
        else:
            search_dir = self.reference_base
        
        if not os.path.isdir(search_dir):
            return references
        
        for file in os.listdir(search_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                screen_name = os.path.splitext(file)[0]
                references.append({
                    'screen_name': screen_name,
                    'file_path': os.path.join(search_dir, file),
                    'device_name': device_name
                })
        
        return references
    
    def cleanup_temp_files(self):
        """Clean up temporary mask and output directories created during comparison"""
        temp_patterns = ['_masks', '_masks-outputs', '_masks_from_blurry', 'resized_current_screen.png']
        
        for pattern in temp_patterns:
            if pattern.endswith('.png'):
                # Single file
                if os.path.exists(pattern):
                    os.remove(pattern)
            else:
                # Directories matching pattern
                for root, dirs, files in os.walk(self.sam_cd_base):
                    for dir_name in dirs:
                        if pattern in dir_name:
                            try:
                                shutil.rmtree(os.path.join(root, dir_name))
                            except:
                                pass


# Singleton instance
_screen_validation_service = None

def get_screen_validation_service():
    """Get or create the singleton ScreenValidationService instance"""
    global _screen_validation_service
    if _screen_validation_service is None:
        _screen_validation_service = ScreenValidationService()
    return _screen_validation_service
