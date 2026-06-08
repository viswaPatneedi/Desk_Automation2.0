# AI-Powered Screen Validation Integration Guide

## Overview

The SAM-CD-2GB (Segment Anything Model - Change Detection) integration provides AI-powered screenshot validation to verify if devices reach expected screen states after operations like reboot, deepsleep, wake-up, etc.

## What It Does

Instead of relying solely on OCR text detection, this system:
- **Compares screenshots** with reference images using deep learning
- **Detects visual changes** at the pixel level using STANet-BAM model
- **Validates screen states** (HOME, Netflix, YouTube, etc.)
- **Multiple comparison methods**: Direct, SAM mask-based, and smoothed comparison
- **Region-based validation**: Can focus on specific screen areas

## Architecture

```
SAM-CD-2GB/
├── stanet_bam_workdir/          # Pre-trained model weights
├── segment_anything/             # SAM segmentation
└── main.py                       # Change detection logic

services/
└── screen_validation_service.py  # Service wrapper

config_screen_validation.py       # Configuration
screen_validation_utils.py        # Integration utilities
reference_screens/                # Reference images (to be created)
    ├── HOME.png
    ├── NETFLIX_HOME.png
    ├── YOUTUBE_SIGNIN.png
    └── [device_name]/            # Device-specific references
        └── HOME.png
```

## Setup Steps

### 1. Install Dependencies

The SAM-CD model requires OpenMMLab toolkits:

```bash
cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement
source venv/bin/activate

# Install OpenMMLab packages
pip install -U openmim
mim install mmengine
mim install "mmcv>=2.0.0"
mim install "mmpretrain>=1.0.0rc7"
pip install "mmsegmentation>=1.2.2"
pip install "mmdet>=3.0.0"

# Additional requirements
pip install matplotlib numpy packaging prettytable
```

### 2. Create Reference Images Directory

```bash
mkdir -p reference_screens
```

### 3. Capture Reference Screenshots

For each screen state you want to validate, capture a reference screenshot:

**Example: Capture HOME screen reference**
```python
from screen_validation_utils import create_reference_from_screenshot

# After device successfully boots to HOME screen
create_reference_from_screenshot(
    screenshot_path="/path/to/good_home_screen.png",
    screen_name="HOME",
    device_name="Element-A4K-DESK"  # Optional: device-specific
)
```

**Recommended reference screens:**
- `HOME` - Main home screen
- `NETFLIX_HOME` - Netflix home/browsing
- `NETFLIX_SIGNIN` - Netflix login
- `YOUTUBE_HOME` - YouTube home
- `YOUTUBE_SIGNIN` - YouTube login
- `PRIME_HOME` - Prime Video home
- `DISNEY_HOME` - Disney+ home
- `BOOT_SCREEN` - Boot/loading screen

### 4. Configure Screen Validation

Edit `config_screen_validation.py` to customize:

```python
SCREEN_VALIDATION_CONFIG = {
    'enabled': True,  # Enable/disable AI validation
    'change_ratio_threshold': 0.0005,  # Lower = stricter
    'use_aspect_ratio': True,
    'cleanup_temp_files': True,
}

# Adjust per-screen thresholds
SCREEN_DEFINITIONS = {
    'HOME': {
        'change_ratio': 0.0005,  # Very strict
        'region': None,  # Full screen
    },
    'NETFLIX_HOME': {
        'change_ratio': 0.001,  # Slightly relaxed (dynamic content)
        'region': [0, 100, 0, 512],  # Focus on menu area
    },
}
```

## Integration Examples

### Example 1: Integrate into Reboot Script

Add to your `Device-Reboot-DeepSleep-Wakeup_Updated_A4K.py`:

```python
from screen_validation_utils import validate_device_screen_after_method

# After capturing screenshot following reboot
screenshot_path = f"{device_folder}/ITR-{iteration}/after_reboot.png"

# Validate using AI
validation = validate_device_screen_after_method(
    screenshot_path=screenshot_path,
    method_name='reboot',  # Expects 'HOME' screen
    device_name=device_name,
    logger=logger
)

if validation['validated']:
    logger.log("✓ AI validation: Device reached HOME screen")
    iteration_passed = True
else:
    logger.log("✗ AI validation: Device did NOT reach expected screen")
    logger.log(f"   Details: {validation['details']}")
    iteration_passed = False
```

### Example 2: Validate Specific Screen

```python
from screen_validation_utils import validate_screenshot_ai

# Validate Netflix home screen
result = validate_screenshot_ai(
    screenshot_path="screenshots/netflix_check.png",
    expected_screen="NETFLIX_HOME",
    device_name="Element-A4K-DESK"
)

if result['validated']:
    print("✓ Device is on Netflix home screen")
else:
    print("✗ Not on Netflix home screen")
```

### Example 3: Batch Validation

```python
from screen_validation_utils import batch_validate_screenshots

# Validate all screenshots in an iteration folder
results = batch_validate_screenshots(
    screenshot_dir="execution_outputs/10.0.0.172_Element-A4K-DESK/ITR-5",
    expected_screen="HOME",
    device_name="Element-A4K-DESK"
)

print(f"Validated: {results['validated']}/{results['total']}")
```

### Example 4: Integration with Existing Screenshot Capture

Replace or enhance existing screenshot validation:

```python
# Existing code
screenshot_url = f"http://{device_ip}:9998/screenshot"
response = requests.get(screenshot_url, timeout=10)

if response.status_code == 200:
    screenshot_path = f"{iteration_folder}/home_screen.png"
    with open(screenshot_path, 'wb') as f:
        f.write(response.content)
    
    # OLD: OCR-based validation
    # ocr_result = check_ocr_text(screenshot_path)
    
    # NEW: AI-based validation
    validation = validate_screenshot_ai(
        screenshot_path=screenshot_path,
        expected_screen="HOME",
        device_name=device_name,
        logger=logger
    )
    
    if validation['validated']:
        logger.log("✓ Device is on HOME screen (AI validated)")
        # Continue with success logic
    else:
        logger.log("⚠ Device may not be on HOME screen")
        # Fallback to OCR or handle as failure
```

## Configuration Reference

### Change Ratio Thresholds

- `0.0001` - Extremely strict (almost identical)
- `0.0005` - Very strict (recommended for static screens like HOME)
- `0.001` - Moderate (good for screens with some dynamic content)
- `0.005` - Relaxed (for highly dynamic screens)
- `0.01` - Very relaxed

### Region of Interest (ROI)

Focus validation on specific screen areas:

```python
region = [x1, x2, y1, y2]  # Pixel coordinates after 512x512 resize
region = [0, 100, 0, 512]  # Top 100 pixels (header/menu area)
region = [200, 312, 200, 312]  # Center square
region = None  # Full screen (default)
```

### Device-Specific Overrides

```python
DEVICE_SCREEN_OVERRIDES = {
    'Element-A4K-DESK': {
        'HOME': {
            'change_ratio': 0.0008,  # Device-specific threshold
        }
    },
}
```

## Utility Functions

### List Available References

```python
from screen_validation_utils import list_available_references

refs = list_available_references(device_name="Element-A4K-DESK")
# Returns: [{'screen_name': 'HOME', 'file_path': '...', 'device_name': '...'}]
```

### Create Reference from Screenshot

```python
from screen_validation_utils import create_reference_from_screenshot

result = create_reference_from_screenshot(
    screenshot_path="good_screenshot.png",
    screen_name="HOME",
    device_name="Element-A4K-DESK"
)
```

## Troubleshooting

### Dependencies Missing

```bash
# Install all required packages
pip install -U openmim
mim install mmengine mmcv mmpretrain mmsegmentation mmdet
```

### Model Weights Not Found

Ensure the model files exist:
```bash
ls -la SAM-CD-2GB/SAM-CD_2GB/stanet_bam_workdir/
# Should see: best_mIoU_iter_40000.pth
```

### No Reference Images

Create reference images first:
```python
create_reference_from_screenshot(
    screenshot_path="known_good_home.png",
    screen_name="HOME"
)
```

### Validation Always Fails

- Check change ratio threshold (try increasing)
- Verify reference image matches device resolution/aspect ratio
- Check if reference image is for correct screen state
- Try batch validation to see patterns

### Temporary Files Not Cleaned

```python
from services.screen_validation_service import get_screen_validation_service
validator = get_screen_validation_service()
validator.cleanup_temp_files()
```

## Performance Considerations

- **First run**: Slower due to model loading (~10-15 seconds)
- **Subsequent runs**: Faster (~3-5 seconds per validation)
- **Memory**: Requires ~2GB RAM for model
- **CPU vs GPU**: Works on CPU (GPU not required but faster if available)

## Best Practices

1. **Build reference library gradually**: Capture references as you encounter known-good screens
2. **Use device-specific references**: Different devices may render screens differently
3. **Start with strict thresholds**: Adjust upward if needed
4. **Combine with OCR**: Use AI for primary validation, OCR as fallback
5. **Test thresholds**: Validate against known-good and known-bad screenshots
6. **Region-based for dynamic content**: Use ROI for screens with changing content (video thumbnails, etc.)

## Next Steps

1. Install dependencies
2. Create reference_screens directory
3. Capture reference screenshots for key screens
4. Test validation with known screenshots
5. Integrate into device testing scripts
6. Monitor and adjust thresholds as needed
