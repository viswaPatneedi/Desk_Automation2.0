# Results Consolidation Implementation Plan

## Current Issue
Saved sequence results are being displayed as **multiple individual method cards** instead of **1 consolidated card per iteration**.

Example:
- ❌ Current: Screen_validation PASSED, Send_remote_keys PASSED, Screen_validation PASSED, Send_remote_keys PASSED, ...
- ✅ Expected: Sequence: XUMOTV-FSR_ACTIVATION [ITR-1] with all methods grouped

## Root Cause Analysis
1. **Consolidation Logic Exists**: Code at lines 698-728 in `test_execution_service.py` consolidates results
2. **Condition Check**: `is_multi_method_sequence = len(execution_queue) > 1 and sequence_name`
3. **Debug Added**: Logging added to track when consolidation is/isn't triggered

## Fix Strategy

### Phase 1: Verify Consolidation is Working
- Run a saved sequence execution
- Check app log for `[DEBUG] Consolidating X method results` messages
- Verify results are saved as single "Sequence: XXX" entries, not individual methods

### Phase 2: Update Results UI Display
If consolidation works correctly but UI still shows multiple cards, need to:
1. Update `templates/results.html` to group results by phase when phase starts with "Sequence:"
2. Display all methods and their statuses within a single card
3. Organize screenshots by method name

### Phase 3: Enhanced Screenshot Organization
For saved sequences with multiple methods having screenshots:
```
RebootMethod Screenshot: Before/After
VoiceMethod Screenshot: After
ScreenValidation Screenshot: Screen1/Screen2
```

**Implementation**:
1. Store method name with each screenshot in details
2. Parse and organize in UI by method
3. Show captions like "Before/After" based on context

## Expected Behavior

### For Multi-Method Saved Sequence (3 iterations)
Display: 3 Cards (1 per iteration)
- **Card 1: XUMOTV-FSR_ACTIVATION [ITR-1]**
  - send_remote_keys: ✅ PASSED
  - voice_command: ✅ PASSED
  - screen_validation: ✅ PASSED
  - [Screenshots organized by method]

- **Card 2: XUMOTV-FSR_ACTIVATION [ITR-2]**
  - send_remote_keys: ✅ PASSED
  - ...

### For Single/Group Methods
Display: 1 Card per execution
- **Screen Validation Execution**
  - Status: ✅ PASSED
  - Screenshot: [image]

## Testing Checklist
- [ ] Execute saved sequence and verify logs show consolidation message
- [ ] Verify test_results_history.json shows 1 entry per iteration (not per method)
- [ ] Verify UI displays 1 card per iteration
- [ ] Verify screenshots are organized by method name
- [ ] Test with 3+ iteration sequence to confirm pattern

## Debug Commands

### Check Latest Results
```bash
python3 << 'EOF'
import json
with open('test_results_history.json') as f:
    results = json.load(f)
recent = sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
for r in recent:
    print(f"{r['phase']} - {r['method']} - {r['status']}")
