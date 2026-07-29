#!/usr/bin/env python3
"""
Netflix-Specific Screen Detector
Distinguishes between Netflix screens using feature detection
- NetflixHome: Navigation menu + featured content carousel
- NetflixAssetScreen: Asset metadata + interactive controls (thumbs up/down, play button)
- NetflixAssetSearchScreen: Search results grid with asset tiles

Key insight: Asset screens have INTERACTIVE CONTROL BUTTONS (thumbs up/down icons)
which are NOT present on home screens - this is the primary distinguishing feature
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import Dict, Tuple, Optional

class NetflixScreenDetector:
    """
    Enhanced Netflix screen detection using:
    1. BUTTON REGION detection (thumbs up/down, bookmarks) - PRIMARY
    2. METADATA PATTERN analysis (year formats, ratings) - SECONDARY
    3. TEXT ANALYSIS in key regions - TERTIARY
    """
    
    def __init__(self):
        # Thresholds
        self.BUTTON_DETECTION_THRESHOLD = 0.3  # Confidence for button detection
        self.METADATA_PATTERN_THRESHOLD = 0.4  # Confidence for metadata patterns
        self.TEXT_EXTRACTION_THRESHOLD = 0.7   # Confidence for OCR-based detection
        
        # Color ranges for UI element detection (adjust for different themes)
        # Thumbs up/down icons typically have distinct colors/shapes
        self.ICON_COLOR_RANGES = {
            'thumbs_region': {  # Region where thumbs icons typically appear
                'x_range': (0.03, 0.5),   # 3% to 50% from left
                'y_range': (0.35, 0.65)   # 35% to 65% from top
            },
            'play_button_region': {  # Play/Resume button area
                'x_range': (0.03, 0.35),
                'y_range': (0.35, 0.5)
            },
            'metadata_region': {  # Year, ratings, episode info area
                'x_range': (0.03, 0.9),
                'y_range': (0.12, 0.35)
            }
        }
    
    def detect_button_region(self, image_path: str) -> Dict:
        """
        PRIMARY FEATURE: Detect presence of interactive buttons (thumbs up/down)
        These are ONLY on asset screens, never on home screens
        
        CRITICAL FIX: Tightened thresholds to reduce false positives
        - Stricter area bounds: focus on icon-sized contours only (~200-1500 pixels)
        - Stricter circularity: thumbs icons are round (0.6-1.2 range)
        - Additional check: contours must not be too elongated
        
        Returns dict with:
            - has_buttons: bool (True if buttons detected)
            - confidence: float (0-1)
            - button_count: int (number of buttons found)
            - details: str (debugging info)
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'has_buttons': False, 'confidence': 0.0, 'button_count': 0, 'details': 'Failed to load image'}
            
            height, width = img.shape[:2]
            
            # Define button region in pixels
            button_roi = self.ICON_COLOR_RANGES['thumbs_region']
            x_start = int(width * button_roi['x_range'][0])
            x_end = int(width * button_roi['x_range'][1])
            y_start = int(height * button_roi['y_range'][0])
            y_end = int(height * button_roi['y_range'][1])
            
            # Extract button region
            roi = img[y_start:y_end, x_start:x_end]
            
            # Convert to grayscale and apply edge detection
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Use Canny edge detection to find button shapes
            # Increased thresholds to reduce noise from text/metadata edges
            edges = cv2.Canny(gray, 100, 200)
            
            # Morphological operations to reduce noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            # Find contours (potential buttons)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours - MUCH STRICTER CRITERIA
            valid_buttons = []
            
            # CRITICAL: Tightened area thresholds to focus only on actual icon-sized contours
            # Thumbs icons are typically 40-60 pixels in diameter = ~1200-2800 pixels area
            min_area = 250     # Minimum - exclude very small artifacts
            max_area = 3000    # Maximum - exclude large UI elements
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # STRICT AREA FILTER
                if not (min_area < area < max_area):
                    continue
                
                # Check circularity (thumbs icons are round, NOT elongated)
                perimeter = cv2.arcLength(contour, True)
                if perimeter <= 0:
                    continue
                
                circularity = 4 * np.pi * area / (perimeter ** 2)
                
                # STRICT CIRCULARITY: Thumbs up/down are quite circular (0.6+ range)
                # Reject elongated shapes, text edges, and flat lines
                if circularity < 0.65:  # Too elongated - reject
                    continue
                if circularity > 1.15:  # Impossible (max is 1.0 for perfect circle, allow small overshoot due to noise)
                    continue
                
                # CHECK BOUNDING BOX: Make sure contour isn't stretched
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # Thumbs icons should be roughly square-ish (not wildly stretched)
                # Accept if aspect ratio between 0.7 and 1.4
                if not (0.7 < aspect_ratio < 1.4):
                    continue
                
                # If we got here, this looks like an actual button icon
                valid_buttons.append({
                    'area': area,
                    'circularity': circularity,
                    'aspect_ratio': aspect_ratio
                })
            
            # Analyze button detection
            button_count = len(valid_buttons)
            
            # Asset screens have exactly 2-3 thumbs buttons (down, up, maybe double-up)
            # Don't accept more than 5 (safety margin for UI variations)
            has_buttons = 2 <= button_count <= 5
            
            # Confidence based on button count
            # 2-3 buttons = high confidence, more buttons = lower confidence
            if button_count == 2 or button_count == 3:
                confidence = 0.90  # Perfect - expected count
            elif button_count == 4 or button_count == 5:
                confidence = 0.75  # Possible, but slight doubt
            else:
                confidence = 0.0
                has_buttons = False
            
            return {
                'has_buttons': has_buttons,
                'confidence': confidence,
                'button_count': button_count,
                'details': f'Found {button_count} buttons (strict filtering applied; circularity check: 0.65-1.15)'
            }
        
        except Exception as e:
            return {'has_buttons': False, 'confidence': 0.0, 'button_count': 0, 'details': f'Error: {str(e)}'}
    
    def detect_metadata_patterns(self, image_path: str) -> Dict:
        """
        SECONDARY FEATURE: Detect metadata patterns (year, ratings, episode info)
        These patterns are characteristic of asset detail screens
        
        Returns dict with:
            - has_metadata: bool
            - confidence: float (0-1)
            - patterns_found: list of detected patterns
        """
        try:
            img = Image.open(image_path)
            height, width = img.size[1], img.size[0]
            
            # Extract metadata region
            meta_roi = self.ICON_COLOR_RANGES['metadata_region']
            left = int(width * meta_roi['x_range'][0])
            top = int(height * meta_roi['y_range'][0])
            right = int(width * meta_roi['x_range'][1])
            bottom = int(height * meta_roi['y_range'][1])
            
            meta_region = img.crop((left, top, right, bottom))
            
            # OCR extraction from metadata region (with preprocessing)
            enhancer = __import__('PIL.ImageEnhance', fromlist=['Contrast']).Contrast(meta_region)
            enhanced = enhancer.enhance(2.0)
            text = pytesseract.image_to_string(enhanced)
            
            patterns_found = []
            confidence = 0.0
            
            # Look for year pattern (e.g., "2026", "2025", "2024")
            import re
            year_pattern = r'\b(20\d{2})\b'
            years = re.findall(year_pattern, text)
            if years:
                patterns_found.append(f'year:{years[0]}')
                confidence += 0.25
            
            # Look for rating pattern (e.g., "PG-13", "R", "TV-14", etc.)
            rating_pattern = r'\b(G|PG|PG-13|R|NC-17|TV-Y|TV-Y7|TV-G|TV-14|TV-MA)\b'
            ratings = re.findall(rating_pattern, text, re.IGNORECASE)
            if ratings:
                patterns_found.append(f'rating:{ratings[0]}')
                confidence += 0.25
            
            # Look for episode/season info pattern
            episode_pattern = r'\b(\d+)\s*(?:episodes?|eps?|episode|ep\.)\b'
            episodes = re.findall(episode_pattern, text, re.IGNORECASE)
            if episodes:
                patterns_found.append(f'episodes:{episodes[0]}')
                confidence += 0.25
            
            # Look for genre-like keywords (action, drama, comedy, sci-fi, etc.)
            genre_keywords = [
                'action', 'drama', 'comedy', 'sci-fi', 'horror', 'romance', 'thriller',
                'adventure', 'fantasy', 'mystery', 'documentary', 'animation'
            ]
            text_lower = text.lower()
            for genre in genre_keywords:
                if genre in text_lower:
                    patterns_found.append(f'genre:{genre}')
                    confidence += 0.1
                    break  # Count only first genre
            
            # Look for duration pattern (2h 30m, etc.) - often on asset screens
            duration_pattern = r'(\d+)\s*h\s*(\d+)\s*m'
            durations = re.findall(duration_pattern, text)
            if durations:
                patterns_found.append(f'duration:{durations[0][0]}h{durations[0][1]}m')
                confidence += 0.15
            
            # Cap confidence at 1.0
            confidence = min(1.0, confidence)
            has_metadata = len(patterns_found) >= 2  # At least 2 patterns needed
            
            return {
                'has_metadata': has_metadata,
                'confidence': confidence,
                'patterns_found': patterns_found,
                'extracted_text': text[:200] if text else ''  # First 200 chars for debugging
            }
        
        except Exception as e:
            return {'has_metadata': False, 'confidence': 0.0, 'patterns_found': [], 'details': f'Error: {str(e)}'}
    
    def distinguish_home_vs_asset(self, image_path: str, pixel_match_result: str, pixel_confidence: float) -> Dict:
        """
        MAIN DECISION LOGIC:
        Determine if screen is Home or Asset based on feature detection
        
        Args:
            image_path: Path to screenshot
            pixel_match_result: Result from pixel matching (e.g., "Netflix_NetflixHome")
            pixel_confidence: Confidence from pixel matching (0-1)
        
        Returns:
            {
                'final_screen': str (corrected screen name),
                'confidence': float (final confidence),
                'reason': str (explanation of decision),
                'button_detection': dict,
                'metadata_detection': dict,
                'validation_method': str
            }
        """
        
        # Run feature detection
        button_result = self.detect_button_region(image_path)
        metadata_result = self.detect_metadata_patterns(image_path)
        
        final_screen = pixel_match_result
        final_confidence = pixel_confidence
        validation_method = 'PIXEL_MATCHING_PRIMARY'
        reason = ''
        
        # DECISION TREE:
        # If pixel match says "NetflixHome" BUT we detect buttons/metadata -> it's actually AssetScreen
        if ('NetflixHome' in pixel_match_result or 'NetflixHome' == pixel_match_result) and pixel_confidence < 0.80:
            
            # Check for asset screen indicators
            feature_score = 0.0
            feature_reasons = []
            
            # WEIGHT 1: Button detection (strongest indicator)
            if button_result['has_buttons']:
                feature_score += button_result['confidence'] * 0.6  # 60% weight
                feature_reasons.append(f"buttons_detected({button_result['button_count']})")
            
            # WEIGHT 2: Metadata detection (strong indicator)
            if metadata_result['has_metadata']:
                feature_score += metadata_result['confidence'] * 0.4  # 40% weight
                feature_reasons.append(f"metadata_detected({len(metadata_result['patterns_found'])}patterns)")
            
            # If combined feature score is high enough, override pixel match
            if feature_score > 0.45:  # 45% feature score threshold
                final_screen = 'Netflix_NetflixAssetScreen'
                final_confidence = min(0.95, feature_score + 0.15)  # Add pixel match bonus
                validation_method = 'FEATURE_DETECTION_OVERRIDE'
                reason = f'Pixel matched "{pixel_match_result}" ({pixel_confidence:.1%}), but feature detection found {", ".join(feature_reasons)} → Reclassified as AssetScreen'
            else:
                reason = f'Pixel matched "{pixel_match_result}" ({pixel_confidence:.1%}); features present but below threshold'
        
        # NEW: If pixel match says "NetflixLogin" BUT we detect asset features -> it's actually AssetScreen
        # This handles cases where UI layouts are similar and loader misclassifies
        elif ('login' in pixel_match_result.lower() or 'login' in pixel_match_result.lower()) and pixel_confidence < 0.70:
            
            feature_score = 0.0
            feature_reasons = []
            
            # Check for asset screen indicators
            if button_result['has_buttons']:
                feature_score += button_result['confidence'] * 0.6
                feature_reasons.append(f"buttons_detected({button_result['button_count']})")
            
            if metadata_result['has_metadata']:
                feature_score += metadata_result['confidence'] * 0.4
                feature_reasons.append(f"metadata_detected({len(metadata_result['patterns_found'])}patterns)")
            
            # If we found asset features, this is likely asset not login
            if feature_score > 0.40:  # Lower threshold for login->asset override (40% vs 45% for home)
                final_screen = 'Netflix_NetflixAssetScreen'
                final_confidence = min(0.95, feature_score + 0.10)
                validation_method = 'FEATURE_DETECTION_OVERRIDE'
                reason = f'Pixel matched "{pixel_match_result}" ({pixel_confidence:.1%}), but detected asset features {", ".join(feature_reasons)} → Reclassified as AssetScreen (login screen false positive)'
            else:
                reason = f'Pixel matched "{pixel_match_result}" ({pixel_confidence:.1%}) - no strong asset features found'
        
        # If pixel match says "NetflixAssetScreen" but no features detected -> validate with OCR
        elif ('NetflixAssetScreen' in pixel_match_result or 'NetflixAssetScreen' == pixel_match_result) and pixel_confidence < 0.70:
            if not button_result['has_buttons'] and not metadata_result['has_metadata']:
                reason = f'Pixel matched AssetScreen ({pixel_confidence:.1%}) but features weak → Recommend OCR validation'
                validation_method = 'PIXEL_MATCH_LOW_CONFIDENCE_NEEDS_OCR'
            else:
                reason = f'Pixel matched AssetScreen ({pixel_confidence:.1%}); features confirm'
        
        # If pixel confidence is low on any match -> recommend OCR
        if pixel_confidence < 0.60:
            validation_method = 'LOW_CONFIDENCE_RECOMMEND_OCR'
            reason += f' [Confidence {pixel_confidence:.1%} low - OCR recommended]'
        
        return {
            'final_screen': final_screen,
            'confidence': final_confidence,
            'reason': reason,
            'button_detection': button_result,
            'metadata_detection': metadata_result,
            'validation_method': validation_method
        }
