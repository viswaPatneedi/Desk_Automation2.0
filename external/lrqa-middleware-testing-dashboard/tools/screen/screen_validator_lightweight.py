#!/usr/bin/env python3
"""
Lightweight Screen Validation using OpenCV + ImageHash
Alternative to SAM-CD for ARM64/Raspberry Pi compatibility
"""

import os
import cv2
import numpy as np
from PIL import Image
import imagehash
from skimage.metrics import structural_similarity as ssim
from typing import Dict, Tuple, Optional
import json
from datetime import datetime

class LightweightScreenValidator:
    """
    Screen validation using lightweight image comparison methods:
    1. Perceptual Hash (pHash) - Fast similarity check
    2. SSIM - Structural similarity
    3. Template Matching - Region-based validation
    """
    
    def __init__(self, reference_dir: str = "reference_screens", excluded_folders: list = None, app_name: str = None):
        self.reference_dir = reference_dir
        self.app_name = app_name  # App-specific filtering (e.g., "Netflix", "Disney")
        self.excluded_folders = excluded_folders if excluded_folders else []
        self.references = {}
        self.load_references()
        
        # Thresholds for validation
        self.PHASH_THRESHOLD = 10  # Hamming distance (lower = more similar)
        self.SSIM_THRESHOLD = 0.65  # Structural similarity (0-1, higher = more similar) - RAISED from 0.60
        self.TEMPLATE_THRESHOLD = 0.60  # Template match confidence - RAISED from 0.55
        
        # Screen-specific configurations for layout-based matching
        self.SCREEN_CONFIGS = {
            'HomeScreen': {
                'use_layout_matching': True,
                'key_regions': [
                    {'name': 'top_left_logo', 'roi': (0, 0, 300, 100)},      # XUMO TV logo
                    {'name': 'top_right_time', 'roi': (1600, 0, 1920, 100)}, # Time display
                    {'name': 'bottom_apps', 'roi': (0, 900, 1920, 1080)},    # Apps & inputs area
                ],
                'threshold_override': 0.50  # Lower threshold for layout matching
            },
            'NetflixProfileScreen': {
                'use_layout_matching': True,
                'key_regions': [
                    {'name': 'netflix_logo', 'roi': (50, 50, 400, 200)},      # Netflix logo top-left
                    {'name': 'profile_title', 'roi': (600, 250, 1320, 400)},  # "Choose a Profile" text center
                    {'name': 'profile_icons', 'roi': (300, 400, 1620, 900)},  # Profile icons grid area
                ],
                'threshold_override': 0.55  # Moderate threshold for profile variations
            },
            'NetflixLoginScreen_v1': {
                'use_layout_matching': True,
                'key_regions': [
                    {'name': 'netflix_logo', 'roi': (50, 50, 400, 200)},      # Netflix logo top-left
                    {'name': 'login_form', 'roi': (600, 300, 1320, 800)},     # Login form center area
                    {'name': 'sign_in_button', 'roi': (700, 650, 1220, 750)}, # Sign in button
                ],
                'threshold_override': 0.55
            },
            'NetflixLoginScreen_v2': {
                'use_layout_matching': True,
                'key_regions': [
                    {'name': 'netflix_logo', 'roi': (50, 50, 400, 200)},      # Netflix logo top-left
                    {'name': 'login_form', 'roi': (600, 300, 1320, 800)},     # Login form center area
                    {'name': 'sign_in_button', 'roi': (700, 650, 1220, 750)}, # Sign in button
                ],
                'threshold_override': 0.55
            },
            'NetflixAssetScreen': {
                'use_layout_matching': True,
                'key_regions': [
                    {'name': 'netflix_logo', 'roi': (25, 60, 150, 120)},      # Netflix logo top-left area
                    {'name': 'asset_title', 'roi': (50, 105, 800, 200)},      # Asset title (e.g., "STRANGER THINGS") left side
                    {'name': 'asset_info', 'roi': (50, 160, 900, 280)},       # Asset metadata (year, genre, rating) area
                    {'name': 'play_button', 'roi': (50, 410, 500, 520)},      # Play/Resume button area
                    {'name': 'asset_description', 'roi': (50, 230, 1100, 370)} # Description text area
                ],
                'threshold_override': 0.58  # Moderate threshold for asset details variations
            },
            'NetflixAssetSearchScreen': {
                'use_layout_matching': True,
                'key_regions': [
                    {'name': 'search_bar', 'roi': (300, 70, 900, 150)},       # Search input area with search results text
                    {'name': 'search_results', 'roi': (300, 130, 1500, 850)}, # Grid of asset thumbnails
                    {'name': 'asset_tiles', 'roi': (400, 140, 1400, 800)}     # Asset result tiles area
                ],
                'threshold_override': 0.60  # Moderate threshold for search results variations
            }
        }
        
    def load_references(self):
        """Load all reference images from reference directory, including subdirectories"""
        if not os.path.exists(self.reference_dir):
            print(f"⚠️  Reference directory not found: {self.reference_dir}")
            return
        
        # If app_name is specified, load only from that app's folder
        reference_base = self.reference_dir
        if self.app_name:
            app_folder = os.path.join(self.reference_dir, self.app_name)
            if os.path.exists(app_folder):
                reference_base = app_folder
                print(f"📁 Loading {self.app_name} references from: {app_folder}")
            else:
                print(f"⚠️  App-specific folder not found: {app_folder}")
                print(f"   Falling back to full reference directory: {self.reference_dir}")
        else:
            print(f"📁 Loading references from: {self.reference_dir}")
        
        if self.excluded_folders:
            print(f"   Excluding folders: {', '.join(self.excluded_folders)}")
        
        # Folders to exclude from loading (default + user-specified)
        excluded_folders = ['Unused_Images', 'Unused_Images_DO_NOT_MERGE', 'backup', 'old']
        excluded_folders.extend(self.excluded_folders)
        
        # Walk through directory and subdirectories
        for root, dirs, files in os.walk(reference_base):
            # Skip excluded folders
            dirs[:] = [d for d in dirs if not any(excl.lower() in d.lower() for excl in excluded_folders)]
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(root, filename)
                    
                    # Calculate relative path from reference_base
                    rel_path = os.path.relpath(image_path, reference_base)
                    
                    # Create screen name from relative path
                    # Example: FactoryReset/screen1.png -> FactoryReset_screen1
                    screen_name = os.path.splitext(rel_path)[0].replace(os.sep, '_')
                    
                    try:
                        # Load with OpenCV
                        img_cv = cv2.imread(image_path)
                        # Load with PIL for hash
                        img_pil = Image.open(image_path)
                        
                        self.references[screen_name] = {
                            'path': image_path,
                            'cv_image': img_cv,
                            'pil_image': img_pil,
                            'phash': imagehash.phash(img_pil),
                            'shape': img_cv.shape
                        }
                        print(f"✓ Loaded reference: {screen_name} (from {rel_path})")
                    except Exception as e:
                        print(f"✗ Failed to load {filename}: {e}")
                    
        print(f"\n📊 Loaded {len(self.references)} reference screens")
        
    def compute_phash_similarity(self, img1_path: str, img2_path: str) -> int:
        """
        Compute perceptual hash distance (0 = identical, higher = more different)
        """
        try:
            hash1 = imagehash.phash(Image.open(img1_path))
            hash2 = imagehash.phash(Image.open(img2_path))
            return hash1 - hash2  # Hamming distance
        except Exception as e:
            print(f"❌ pHash error: {e}")
            return 999
            
    def compute_ssim(self, img1_path: str, img2_path: str) -> float:
        """
        Compute Structural Similarity Index (0-1, 1 = identical)
        """
        try:
            # Load images in grayscale
            img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return 0.0
                
            # Resize to same dimensions if needed
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
                
            # Compute SSIM
            score, _ = ssim(img1, img2, full=True)
            return score
        except Exception as e:
            print(f"❌ SSIM error: {e}")
            return 0.0
            
    def template_match(self, screenshot_path: str, template_path: str, 
                       roi: Optional[Tuple[int, int, int, int]] = None) -> float:
        """
        Template matching in specific region of interest
        roi: (x, y, width, height)
        """
        try:
            img = cv2.imread(screenshot_path)
            template = cv2.imread(template_path)
            
            if img is None or template is None:
                return 0.0
                
            # Apply ROI if specified
            if roi:
                x, y, w, h = roi
                img = img[y:y+h, x:x+w]
                
            # Resize template if needed
            if img.shape[:2] != template.shape[:2]:
                template = cv2.resize(template, (img.shape[1], img.shape[0]))
                
            # Convert to grayscale
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Perform template matching
            result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            return max_val
        except Exception as e:
            print(f"❌ Template match error: {e}")
            return 0.0
            
    def validate_screen(self, screenshot_path: str, expected_screen: str,
                       method: str = "hybrid") -> Dict:
        """
        Validate screenshot against expected screen reference
        
        Args:
            screenshot_path: Path to captured screenshot
            expected_screen: Name of expected screen (e.g., "NetflixHome")
            method: "phash", "ssim", "template", or "hybrid" (default)
            
        Returns:
            Dict with validation results
        """
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'screenshot': screenshot_path,
            'expected_screen': expected_screen,
            'is_match': False,
            'confidence': 0.0,
            'method': method,
            'details': {}
        }
        
        # Helper function to normalize screen names for flexible matching
        def normalize_screen_name(name):
            """Remove underscores, hyphens, spaces and convert to lowercase for comparison"""
            return name.replace('_', '').replace('-', '').replace(' ', '').lower()
        
        def extract_number_prefix(name):
            """Extract leading number from name (e.g., '7-FactoryReset...' -> '7')"""
            import re
            # Try to find a number at start or after folder prefix
            match = re.search(r'(\d+)', name)
            return match.group(1) if match else None
        
        # Try to find reference with flexible matching
        ref = None
        matched_key = None
        normalized_expected = normalize_screen_name(expected_screen)
        expected_number = extract_number_prefix(expected_screen)
        
        # First try exact match
        if expected_screen in self.references:
            ref = self.references[expected_screen]
            matched_key = expected_screen
        else:
            # Try flexible matching with multiple strategies
            best_match = None
            best_match_score = 0
            
            for ref_key in self.references.keys():
                normalized_ref = normalize_screen_name(ref_key)
                ref_number = extract_number_prefix(ref_key)
                
                # Strategy 1: Exact normalized match
                if normalized_ref == normalized_expected:
                    ref = self.references[ref_key]
                    matched_key = ref_key
                    print(f"📋 Matched '{expected_screen}' to '{ref_key}' (exact normalized)")
                    break
                
                # Strategy 2: Reference ends with expected (handles folder prefixes)
                if normalized_ref.endswith(normalized_expected):
                    ref = self.references[ref_key]
                    matched_key = ref_key
                    print(f"📋 Matched '{expected_screen}' to '{ref_key}' (suffix match)")
                    break
                
                # Strategy 3: Check if expected screen name is contained in reference
                # This handles cases where folder name adds prefixes
                if normalized_expected in normalized_ref:
                    # Calculate overlap ratio
                    overlap_ratio = len(normalized_expected) / len(normalized_ref)
                    if overlap_ratio > best_match_score:
                        best_match_score = overlap_ratio
                        best_match = ref_key
                
                # Strategy 4: Same number prefix ONLY if containment also matches
                # This prevents false matches like "1-FACTORYRESET" matching "NetflixLogin_v1"
                if expected_number and expected_number == ref_number:
                    # Only consider this a match if there's also significant term overlap
                    # Remove numbers and check if expected terms appear in ref
                    expected_no_num = normalized_expected.replace(expected_number, '')
                    ref_no_num = normalized_ref.replace(ref_number, '')
                    
                    # Check if most of the expected (without number) is in the ref
                    if len(expected_no_num) > 3 and expected_no_num in ref_no_num:
                        score = 0.90  # Higher score for number + content match
                        if score > best_match_score:
                            best_match_score = score
                            best_match = ref_key
                    # Also check reverse: if ref content matches expected content
                    elif len(ref_no_num) > 3 and ref_no_num in expected_no_num:
                        score = 0.85  # Slightly lower score for reverse match
                        if score > best_match_score:
                            best_match_score = score
                            best_match = ref_key
            
            # If we found a good similarity match (>35% for numbered screens, >50% otherwise), use it
            min_threshold = 0.35 if expected_number else 0.50
            if not ref and best_match and best_match_score > min_threshold:
                ref = self.references[best_match]
                matched_key = best_match
                print(f"📋 Matched '{expected_screen}' to '{best_match}' (similarity: {best_match_score:.0%})")
        
        # Check if reference exists
        if not ref:
            result['error'] = f"Reference '{expected_screen}' not found. Available: {list(self.references.keys())[:10]}"
            print(f"❌ {result['error']}")
            return result
        
        try:
            # Check if screen has special layout-based matching config
            if expected_screen in self.SCREEN_CONFIGS:
                config = self.SCREEN_CONFIGS[expected_screen]
                
                if config.get('use_layout_matching', False):
                    # Use layout-based validation for screens with dynamic content
                    print(f"🔍 Using layout-based matching for {expected_screen}")
                    
                    # Load images
                    screenshot_img = cv2.imread(screenshot_path)
                    reference_img = cv2.imread(ref['path'])
                    
                    if screenshot_img is None or reference_img is None:
                        raise Exception("Failed to load images for layout matching")
                    
                    # Validate each key region
                    region_scores = []
                    for region in config.get('key_regions', []):
                        region_name = region['name']
                        x1, y1, x2, y2 = region['roi']
                        
                        # Extract ROI from both images
                        screenshot_roi = screenshot_img[y1:y2, x1:x2]
                        reference_roi = reference_img[y1:y2, x1:x2]
                        
                        # Convert to grayscale for template matching
                        screenshot_gray = cv2.cvtColor(screenshot_roi, cv2.COLOR_BGR2GRAY)
                        reference_gray = cv2.cvtColor(reference_roi, cv2.COLOR_BGR2GRAY)
                        
                        # Resize if needed
                        if screenshot_gray.shape != reference_gray.shape:
                            reference_gray = cv2.resize(reference_gray, 
                                                       (screenshot_gray.shape[1], screenshot_gray.shape[0]))
                        
                        # Calculate SSIM for this region
                        from skimage.metrics import structural_similarity
                        region_score = structural_similarity(screenshot_gray, reference_gray)
                        region_scores.append(region_score)
                        
                        print(f"  📍 {region_name}: {region_score:.2%}")
                        result['details'][f'region_{region_name}'] = region_score
                    
                    # Calculate average score across all regions
                    if region_scores:
                        result['confidence'] = sum(region_scores) / len(region_scores)
                        threshold = config.get('threshold_override', self.SSIM_THRESHOLD)
                        result['details']['layout_threshold'] = threshold
                        
                        if result['confidence'] >= threshold:
                            result['is_match'] = True
                            result['method_used'] = "Layout-Based Matching"
                        
                        status = "✓ MATCH" if result['is_match'] else "✗ NO MATCH"
                        print(f"{status} | {expected_screen} | Layout Confidence: {result['confidence']:.2%}")
                        return result
            
            # Standard validation (full-screen comparison)
            if method == "phash" or method == "hybrid":
                # Perceptual hash comparison (fast)
                phash_dist = self.compute_phash_similarity(screenshot_path, ref['path'])
                result['details']['phash_distance'] = phash_dist
                result['details']['phash_threshold'] = self.PHASH_THRESHOLD
                
                if phash_dist <= self.PHASH_THRESHOLD:
                    result['is_match'] = True
                    result['confidence'] = max(0, 1 - (phash_dist / 20))  # Normalize to 0-1
                    result['method_used'] = "pHash"
                    
            if (method == "ssim" or method == "hybrid") and not result['is_match']:
                # Structural similarity (accurate)
                ssim_score = self.compute_ssim(screenshot_path, ref['path'])
                result['details']['ssim_score'] = ssim_score
                result['details']['ssim_threshold'] = self.SSIM_THRESHOLD
                
                if ssim_score >= self.SSIM_THRESHOLD:
                    result['is_match'] = True
                    result['confidence'] = ssim_score
                    result['method_used'] = "SSIM"
                    
            if (method == "template" or method == "hybrid") and not result['is_match']:
                # Template matching (region-based)
                match_score = self.template_match(screenshot_path, ref['path'])
                result['details']['template_score'] = match_score
                result['details']['template_threshold'] = self.TEMPLATE_THRESHOLD
                
                if match_score >= self.TEMPLATE_THRESHOLD:
                    result['is_match'] = True
                    result['confidence'] = match_score
                    result['method_used'] = "Template Match"
                    
            # Final confidence calculation for hybrid
            if method == "hybrid":
                scores = []
                if 'phash_distance' in result['details']:
                    scores.append(max(0, 1 - (result['details']['phash_distance'] / 20)))
                if 'ssim_score' in result['details']:
                    scores.append(result['details']['ssim_score'])
                if 'template_score' in result['details']:
                    scores.append(result['details']['template_score'])
                    
                if scores:
                    result['confidence'] = max(scores)
                    
            # Log result
            status = "✓ MATCH" if result['is_match'] else "✗ NO MATCH"
            print(f"{status} | {expected_screen} | Confidence: {result['confidence']:.2%}")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Validation error: {e}")
            
        return result
    
    def validate_against_reference(self, screenshot_path: str, reference_path: str,
                                   method: str = "hybrid") -> Dict:
        """
        Validate screenshot against a custom reference image
        
        Args:
            screenshot_path: Path to captured screenshot
            reference_path: Path to custom reference image
            method: "phash", "ssim", "template", or "hybrid" (default)
            
        Returns:
            Dict with validation results including is_match and confidence
        """
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'screenshot': screenshot_path,
            'reference': reference_path,
            'is_match': False,
            'confidence': 0.0,
            'method': method,
            'details': {}
        }
        
        try:
            # Perform validation using specified method(s)
            if method == "phash" or method == "hybrid":
                # Perceptual hash (fast)
                phash_dist = self.compute_phash_similarity(screenshot_path, reference_path)
                result['details']['phash_distance'] = phash_dist
                result['details']['phash_threshold'] = self.PHASH_THRESHOLD
                
                if phash_dist <= self.PHASH_THRESHOLD:
                    result['is_match'] = True
                    result['confidence'] = max(0, 1 - (phash_dist / 20))
                    result['method_used'] = "pHash"
                    
            if (method == "ssim" or method == "hybrid") and not result['is_match']:
                # Structural similarity
                ssim_score = self.compute_ssim(screenshot_path, reference_path)
                result['details']['ssim_score'] = ssim_score
                result['details']['ssim_threshold'] = self.SSIM_THRESHOLD
                
                if ssim_score >= self.SSIM_THRESHOLD:
                    result['is_match'] = True
                    result['confidence'] = ssim_score
                    result['method_used'] = "SSIM"
                    
            if (method == "template" or method == "hybrid") and not result['is_match']:
                # Template matching
                match_score = self.template_match(screenshot_path, reference_path)
                result['details']['template_score'] = match_score
                result['details']['template_threshold'] = self.TEMPLATE_THRESHOLD
                
                if match_score >= self.TEMPLATE_THRESHOLD:
                    result['is_match'] = True
                    result['confidence'] = match_score
                    result['method_used'] = "Template Match"
                    
            # Final confidence for hybrid
            if method == "hybrid":
                scores = []
                if 'phash_distance' in result['details']:
                    scores.append(max(0, 1 - (result['details']['phash_distance'] / 20)))
                if 'ssim_score' in result['details']:
                    scores.append(result['details']['ssim_score'])
                if 'template_score' in result['details']:
                    scores.append(result['details']['template_score'])
                    
                if scores:
                    result['confidence'] = max(scores)
                    
            # Log result
            status = "✓ MATCH" if result['is_match'] else "✗ NO MATCH"
            ref_name = os.path.basename(reference_path)
            print(f"{status} | {ref_name} | Confidence: {result['confidence']:.2%}")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Validation error: {e}")
            
        return result
        
    def find_best_match(self, screenshot_path: str) -> Dict:
        """
        Find best matching reference screen from all available references
        """
        best_match = None
        best_score = 0.0
        
        for screen_name in self.references:
            result = self.validate_screen(screenshot_path, screen_name, method="hybrid")
            if result['confidence'] > best_score:
                best_score = result['confidence']
                best_match = screen_name
                
        return {
            'screenshot': screenshot_path,
            'best_match': best_match,
            'confidence': best_score,
            'threshold_met': best_score >= self.SSIM_THRESHOLD
        }
        
    def copy_sam_references(self, sam_dir: str = "SAM-CD-2GB/SAM-CD_2GB/ocrfailures"):
        """
        Copy reference images from SAM-CD folder to reference_screens directory
        """
        if not os.path.exists(sam_dir):
            print(f"❌ SAM-CD directory not found: {sam_dir}")
            return
            
        os.makedirs(self.reference_dir, exist_ok=True)
        
        copied = 0
        for filename in os.listdir(sam_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and not filename.startswith('.'):
                src = os.path.join(sam_dir, filename)
                dst = os.path.join(self.reference_dir, filename)
                
                try:
                    import shutil
                    shutil.copy2(src, dst)
                    print(f"✓ Copied: {filename}")
                    copied += 1
                except Exception as e:
                    print(f"✗ Failed to copy {filename}: {e}")
                    
        print(f"\n📋 Copied {copied} reference images to {self.reference_dir}")
        
        # Reload references
        self.load_references()


# Command-line usage
if __name__ == "__main__":
    import sys
    
    validator = LightweightScreenValidator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Setup:    python screen_validator_lightweight.py --setup")
        print("  Validate: python screen_validator_lightweight.py <screenshot> <expected_screen>")
        print("  Find:     python screen_validator_lightweight.py --find <screenshot>")
        sys.exit(1)
        
    if sys.argv[1] == "--setup":
        # Copy references from SAM-CD
        validator.copy_sam_references()
        
    elif sys.argv[1] == "--find":
        # Find best match
        if len(sys.argv) < 3:
            print("❌ Please provide screenshot path")
            sys.exit(1)
        result = validator.find_best_match(sys.argv[2])
        print(f"\n🔍 Best Match: {result['best_match']} ({result['confidence']:.2%})")
        
    else:
        # Validate against expected screen
        if len(sys.argv) < 3:
            print("❌ Please provide screenshot path and expected screen name")
            sys.exit(1)
            
        screenshot = sys.argv[1]
        expected = sys.argv[2]
        
        result = validator.validate_screen(screenshot, expected)
        print(f"\n{'='*50}")
        print(f"Match: {result['match']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(json.dumps(result['details'], indent=2))
