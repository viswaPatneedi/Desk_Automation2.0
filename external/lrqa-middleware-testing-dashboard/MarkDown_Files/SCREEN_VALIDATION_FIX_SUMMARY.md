# Screen Validation Fix - Summary Report

## Issues Diagnosed

### 1. **Reference Screenshots Not Being Used**
   - ❌ **Problem**: The method checked if `reference_screens/InputScreens_XUMO-TV/` existed but never actually compared captured screenshots with reference images
   - ✅ **Fix**: Implemented `validate_input_tile_with_reference()` function that uses `LightweightScreenValidator` for actual comparison

### 2. **No Actual Tile Detection/Validation**
   - ❌ **Problem**: The method assumed tiles were valid if screenshots were captured, without comparing against references
   - ✅ **Fix**: Added reference-based validation with confidence scoring (hybrid method combining pHash, SSIM, template matching)

### 3. **EXPECTED_INPUT_TILES Scope Error**
   - ❌ **Problem**: Exception handler tried to reference `EXPECTED_INPUT_TILES` which wasn't in scope, causing "cannot access local variable" error
   - ✅ **Fix**: Defined `default_tiles` list in exception handler to prevent scope issues

### 4. **Missing Job Configuration**
   - ❌ **Problem**: Job configs had empty `expected_screen` and `screen_name` fields
   - ✅ **Recommendation**: Add `"expected_screen": "InputScreens_XUMO-TV"` and `"screen_name": "InputScreens_XUMO-TV"` to job configs

## Changes Made

### File: `method_navigate_inputs_xumo.py`

#### Added Imports
```python
try:
    from screen_validator_lightweight import LightweightScreenValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
```

#### Added Helper Function
- `validate_input_tile_with_reference()` - Validates captured screenshot against reference image
  - Maps input names to reference filenames
  - Handles filename quirks (e.g., "ANTEENA" typo)
  - Uses hybrid validation method
  - Returns match status with confidence percentage

#### Updated Step 3: Reference Validation
- Now logs whether comparison will be used
- Sets `use_reference_comparison` flag

#### Updated Step 4: Tile Detection & Validation
- For each tile, if reference comparison available:
  - Calls validation function
  - Sets status to `matched_reference` or `validation_failed`
  - Logs detailed results
- Stores validation details per tile

#### Updated Step 6: Results
- Returns detailed validation info including:
  - `validation_details`: Per-tile status
  - `reference_comparison_used`: Boolean flag
  - Full tiles_summary

#### Fixed Exception Handler
- Properly defines `default_tiles` to avoid scope errors
- Includes traceback logging for debugging
- Safely closes SSH connection

### File: `NAVIGATE_INPUTS_XUMO_VALIDATION_GUIDE.md` (New)
- Complete documentation of validation process
- Troubleshooting guide for common issues
- Configuration examples
- Testing commands
- Performance metrics
- Future enhancements

## Job IDs Tested

### Job 1: `5756368e-2a0f-4cc9-bed8-f3fec76799c8`
- **Device**: HISENSE-X3 (10.0.0.2)
- **Status**: Completed ✅
- **Expected**: All 100 iterations should now validate properly with reference screens

### Job 2: `43f12778-7c1c-4663-ac41-3f206b44308c`
- **Device**: PIONEER-UHD (10.0.0.110)
- **Status**: Failed (was failing before)
- **Expected**: Should now show detailed validation failures per tile

## Reference Screenshots Location
```
reference_screens/InputScreens_XUMO-TV/
├── INPUT_SCREEN_ANTEENA.png          (ANTENNA - note typo)
├── INPUT_SCREEN_HDMI_1.png           (HDMI 1)
├── INPUT_SCREEN_HDMI_2.png           (HDMI 2)
├── INPUT_SCREEN_HDMI_3.png           (HDMI 3)
├── INPUT_SCREEN_COMPOSITE.png        (COMPOSITE)
├── INPUT_SCREEN_AIRPLAY.png          (AIRPLAY)
├── INPUT_SCREEN_USB.png              (USB)
└── INPUT_SCREEN_SCREEN-MIRRORING.png (SCREEN MIRRORING)
```

## Validation Algorithm

### Hybrid Validation Method
1. **Perceptual Hash (pHash)**
   - Threshold: Hamming distance < 10
   - Fast initial filter
   
2. **SSIM (Structural Similarity)**
   - Threshold: 0.60 (60% similarity)
   - Analyzes structural similarities
   
3. **Template Matching**
   - Threshold: 0.55 (55% confidence)
   - Region-based matching

**Final Decision**: Match if any method scores high enough

## Status Codes in Results

### validation_details Values
- `matched_reference`: ✓ Screenshot matched reference with confidence ≥ 60%
- `validation_failed`: ✗ Screenshot captured but confidence < 60%
- `capture_failed`: ⚠ Failed to capture screenshot
- `screenshot_captured`: ℹ Screenshot successful (no reference available)

## Execution Flow Example

```log
🎬 Starting XUMO-TV Inputs Navigation
   Device: PIONEER-UHD (10.0.0.110)
   Expected Input Tiles: ANTENNA, HDMI 1, HDMI 2, HDMI 3, COMPOSITE, AIRPLAY, USB, SCREEN MIRRORING

📍 Step 1: Navigating to Inputs row...
   → Sending key: Go to Home screen
   ✓ Key sent successfully
   ⏱ Waited 4s
   ... (repeat for other navigation keys)

📸 Step 2: Capturing Inputs screen...
✓ Initial screenshot captured

🔍 Step 3: Validating reference screenshots...
✓ Reference directory found: /path/to/reference_screens/InputScreens_XUMO-TV
   Reference screenshots will be used for validation

🎯 Step 4: Detecting available input tiles...
   → Checking tile 1: ANTENNA
      ✓ ANTENNA - MATCHED (confidence: 96.5%)
   → Checking tile 2: HDMI 1
      ✓ HDMI 1 - MATCHED (confidence: 94.2%)
   ... (repeat for each tile)

📊 Results Summary:
   Found: 8/8 input tiles
   Found: ANTENNA, HDMI 1, HDMI 2, HDMI 3, COMPOSITE, AIRPLAY, USB, SCREEN MIRRORING

🔍 Reference Validation Details:
   ANTENNA: matched_reference
   HDMI 1: matched_reference
   HDMI 2: matched_reference
   ...
```

## Next Steps

1. **Verify Fix**: Re-run jobs with updated method
   ```bash
   # Check if iterate jobs with new method
   curl -X POST http://localhost:5000/run_job \
     -H "Content-Type: application/json" \
     -d '{"sequence_name": "REBOOT-INPUTROW-VALIDATION-XUMOTV", "iterations": 5}'
   ```

2. **Monitor Results**: Check execution logs for validation details

3. **Capture Missing References** (if needed):
   ```python
   from method_capture_base_image import capture_base_image
   # Capture any missing reference screenshots
   ```

4. **Tune Confidence Thresholds**: Adjust in `screen_validator_lightweight.py` if needed
   - Lower threshold (0.50) = more lenient
   - Higher threshold (0.70) = more strict

## Files Modified
- ✅ `method_navigate_inputs_xumo.py` - Added validation logic, fixed exception handling
- ✅ `NAVIGATE_INPUTS_XUMO_VALIDATION_GUIDE.md` - New comprehensive guide (created)

## Files Unchanged
- `results_controller.py` - Previous fix already implemented
- `results_cards.html` - Previous fix already implemented  
- `screen_validator_lightweight.py` - No changes needed
- `screenshot_utils.py` - No changes needed

## Tests Recommended

1. **Run Single Job with Validation Debug**
   ```bash
   python -c "
   from method_navigate_inputs_xumo import navigate_inputs_xumo
   result = navigate_inputs_xumo(
       '10.0.0.110', 10022, 'root', 'password',
       'screenshots', 1, 'TEST-DEVICE', print
   )
   print(f'Validation Details: {result[\"validation_details\"]}')
   print(f'Reference Used: {result[\"reference_comparison_used\"]}')
   "
   ```

2. **Check Reference Directory Exists**
   ```bash
   ls -la reference_screens/InputScreens_XUMO-TV/
   ```

3. **Verify Validator Available**
   ```bash
   python -c "from screen_validator_lightweight import LightweightScreenValidator; print('✓ OK')"
   ```

---

**Status**: ✅ Ready for Testing  
**Fix Applied**: 2026-02-25  
**Affected Jobs**: All navigate_inputs_xumo executions
