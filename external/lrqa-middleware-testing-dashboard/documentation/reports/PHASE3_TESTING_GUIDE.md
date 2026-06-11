# Phase 3 Modal UI - Testing & Debugging Guide

This guide provides comprehensive testing procedures for the Phase 3 Modal UI System. Follow these steps to verify that all modals are working correctly in a production-ready state.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run Flask app
python app.py

# 3. Open browser to localhost:5000
# Navigate to the modal testing page

# 4. Run test suite
pytest tests/test_modals.py -v

# 5. Check logs
tail -f iteration_logs/*.log
```

---

## Manual Testing Checklist

### Phase 3a: Page Load & Component Initialization

#### ✓ Modal Manager Initialization
- [ ] Open browser developer console (F12)
- [ ] Check for "Phase 3 Modal UI System initialized" message
- [ ] Check that `window.modalManager` is defined and accessible
- [ ] Verify no JavaScript errors in console

**Expected Output**:
```
✅ Phase 3 Modal UI System initialized
✅ All 9 modals registered
✅ Form handlers attached
✅ API client configured
```

#### ✓ CSS Asset Loading
- [ ] Open browser DevTools → Network tab
- [ ] Verify `/static/css/modals.css` loads successfully (200 status)
- [ ] Verify `/static/js/modal-handlers.js` loads successfully (200 status)
- [ ] Check that styles apply (dark theme visible)
- [ ] Check for CSS errors in Console

#### ✓ Bootstrap Modal Library
- [ ] Verify Bootstrap 5 modal library is available
- [ ] Test that `new bootstrap.Modal()` works in console
- [ ] Check that modal animations are smooth

**Test in Console**:
```javascript
// Should return an object
console.log(window.bootstrap);

// Should return true
console.log(window.modalManager !== undefined);

// Should return 9
console.log(Object.keys(window.modalManager.modals).length);
```

---

### Phase 3b: Device Management Modal

#### ✓ Open Device Management Modal
- [ ] Click "Add Device" button (or trigger from navigation)
- [ ] Modal appears with smooth animation (scale + translateY)
- [ ] Modal header displays "Add Device"
- [ ] Modal has proper dark theme styling
- [ ] Close button (X) appears in header
- [ ] ESC key closes the modal

#### ✓ Device Form Validation
Test each field with invalid input:

1. **Device Name Field**
   - [ ] Empty name shows error: "Device name is required"
   - [ ] Valid name (e.g., "TestDevice-01") passes validation
   - [ ] Spaces and hyphens allowed

2. **SSH Host Field**
   - [ ] Empty host shows error: "SSH host is required"
   - [ ] Invalid IP "999.999.999.999" shows error
   - [ ] Invalid hostname "invalid..host" shows error
   - [ ] Valid IP "192.168.1.100" passes
   - [ ] Valid hostname "test-device.local" passes

3. **SSH Port Field**
   - [ ] Empty port shows error: "Port is required"
   - [ ] Non-numeric input shows error
   - [ ] Port < 1 shows error: "Port must be between 1 and 65535"
   - [ ] Port > 65535 shows error
   - [ ] Valid port "10022" passes

4. **SSH Username Field**
   - [ ] Empty username shows error: "Username is required"
   - [ ] Valid username "root" passes

5. **SSH Password Field**
   - [ ] Empty password shows error: "Password is required"
   - [ ] Valid password passes

#### ✓ SSH Connection Test
- [ ] Click "Test Connection" button
- [ ] Modal shows loading state (spinner or disabled button)
- [ ] With valid credentials: Shows "✅ SSH connection test successful" with response time
- [ ] With invalid host: Shows "❌ Connection failed: Name or service not known"
- [ ] With invalid credentials: Shows "❌ SSH authentication failed"
- [ ] Timeout (10+ seconds): Shows "⚠️ Connection test timeout"
- [ ] Response time displayed (e.g., "Response time: 245ms")

#### ✓ Device Save
- [ ] Fill all fields with valid data
- [ ] Click "Save Device" button
- [ ] Modal shows loading state
- [ ] Success: "✅ Device added successfully"
- [ ] Modal closes automatically
- [ ] New device appears in device list

---

### Phase 3c: Login Modal

#### ✓ Open Login Modal
- [ ] Page shows login modal on first load (if not authenticated)
- [ ] Modal displays "Login" header
- [ ] Email and password fields visible
- [ ] "Remember me" checkbox present
- [ ] "Forgot Password?" link present
- [ ] "Login" and "Cancel" buttons present

#### ✓ Login Form Validation
- [ ] Empty email shows error: "Email is required"
- [ ] Invalid email "not-an-email" shows error: "Enter valid email"
- [ ] Valid email "test@example.com" passes
- [ ] Empty password shows error: "Password is required"
- [ ] Password field obscures input (type="password")

#### ✓ Login Submission
- [ ] Enter valid credentials
- [ ] Click "Login" button
- [ ] Modal shows loading state
- [ ] Success: "✅ Login successful" message
- [ ] Page redirects or closes modal
- [ ] User remains logged in after page refresh

#### ✓ Login Error Handling
- [ ] Enter invalid email/password
- [ ] Click "Login" button
- [ ] Shows error: "❌ Invalid email or password"
- [ ] Modal stays open for retry
- [ ] No sensitive data logged

#### ✓ Remember Me Feature
- [ ] Check "Remember me" checkbox
- [ ] Login successfully
- [ ] Close browser completely
- [ ] Reopen application
- [ ] Should be logged in (if session not expired)

---

### Phase 3d: Execution Context Modal

#### ✓ Open Execution Context Modal
- [ ] After selecting a device and method
- [ ] Modal displays "Capture Execution Context"
- [ ] Device name pre-populated
- [ ] Method name pre-populated
- [ ] User info automatically filled
- [ ] Timestamp shows current UTC time

#### ✓ Execution Context Form Fields
- [ ] Device field shows selected device
- [ ] Method field shows selected method
- [ ] User field shows current user email
- [ ] Timestamp field shows UTC format: "2024-01-15T14:30:45.123Z"
- [ ] "Method Rationale" text area is required
- [ ] "Execution Notes" text area is optional

#### ✓ Form Validation
- [ ] Leave "Method Rationale" empty
- [ ] Click "Save Context" button
- [ ] Error shows: "Method rationale is required"
- [ ] Enter rationale: "Testing soft boot after factory reset"
- [ ] Click "Save Context"
- [ ] Success: "✅ Execution context captured"
- [ ] Shows execution ID (e.g., "exec_1705334445000")

#### ✓ Context Immutability
- [ ] Device/method/user fields are read-only (cannot edit)
- [ ] Only rationale and notes can be edited
- [ ] Prevents accidental modification of execution context

---

### Phase 3e: Method Execution Modal

#### ✓ Open Method Execution Modal
- [ ] Page shows method list
- [ ] Click on a method (e.g., "Soft Boot")
- [ ] Modal opens with "Execute Method" header
- [ ] Method name displayed
- [ ] Device selector populated

#### ✓ Method Parameters
- [ ] Method displays all available parameters
- [ ] Parameter descriptions are visible
- [ ] Default values pre-filled
- [ ] User can modify parameter values
- [ ] Parameter validation works (e.g., timeout in seconds must be numeric)

#### ✓ ETA Calculation
- [ ] ETA displays estimated execution time
- [ ] ETA updates when parameters change (e.g., timeout increased)
- [ ] ETA format: Human-readable (e.g., "~5 minutes 30 seconds")

#### ✓ Execute Method
- [ ] All required parameters filled
- [ ] Click "Execute" button
- [ ] Modal triggers execution context capture
- [ ] Execution starts with progress indicators
- [ ] Real-time log streaming updates Modal
- [ ] Execution completes with results

---

### Phase 3f: Sequence Management Modal

#### ✓ Open Sequence Create Modal
- [ ] Click "Create Sequence" button
- [ ] Modal displays "Create Sequence" header
- [ ] All form fields visible and empty

#### ✓ Sequence Form Fields
1. **Sequence Name**
   - [ ] Required field
   - [ ] Format: "Sequence_Name_v1" (alphanumeric + underscore)
   - [ ] Invalid name "Sequence!@#" shows error
   - [ ] Valid name "Test_Boot_Sequence_v1" passes

2. **Description**
   - [ ] Optional field
   - [ ] Supports rich text (up to 500 chars)

3. **Rationale**
   - [ ] Required field (key for v2 Requirement 10)
   - [ ] Example: "This sequence tests multiple boot methods in specific order"
   - [ ] Shows error if empty when saving

4. **Methods**
   - [ ] Multi-select dropdown
   - [ ] Can select multiple methods
   - [ ] Shows selected methods as chips/tags

5. **Visibility**
   - [ ] Options: "Private", "Team", "Public"
   - [ ] Default: "Team"
   - [ ] Affects who can see/execute sequence

6. **Readonly Flag**
   - [ ] Checkbox for making sequence immutable after creation
   - [ ] Helpful for production sequences

7. **Tags**
   - [ ] Optional comma-separated tags
   - [ ] Example: "boot-test, regression, critical"

#### ✓ Sequence Validation
- [ ] Try saving with empty name: "Sequence name is required"
- [ ] Try saving with empty rationale: "Sequence rationale is required"
- [ ] Fill all required fields
- [ ] Click "Save Sequence"
- [ ] Success: "✅ Sequence saved successfully"
- [ ] Returns sequence ID

#### ✓ Load Sequence for Editing
- [ ] Click "Edit" on existing sequence
- [ ] Modal opens with "Edit Sequence" header
- [ ] All fields pre-populated with existing data
- [ ] Can modify any field
- [ ] Click "Update Sequence"
- [ ] Success: "✅ Sequence updated successfully"

---

### Phase 3g: Error Handling & Recovery

#### ✓ Network Error Handling
- [ ] Disconnect internet
- [ ] Try to add device
- [ ] Shows error: "❌ Network error. Please check your connection."
- [ ] Reconnect internet
- [ ] Try again: Should work

#### ✓ Timeout Handling
- [ ] In slow network conditions
- [ ] Trigger action (e.g., add device)
- [ ] Wait > 10 seconds
- [ ] Shows: "⚠️ Request timeout"
- [ ] Can retry

#### ✓ Session Expiry
- [ ] Login and wait for session timeout (usually 30 min)
- [ ] Try to perform protected action (add device)
- [ ] Shows: "❌ Your session has expired. Please login again."
- [ ] Can complete action after re-login

#### ✓ Server Error Handling
- [ ] Server returns 500 error
- [ ] Modal shows: "❌ Server error. Please contact support."
- [ ] Includes error ID for support reference
- [ ] User can retry

---

### Phase 3h: Accessibility Testing

#### ✓ Keyboard Navigation
- [ ] Open any modal
- [ ] Press TAB: Focus moves through all interactive elements
- [ ] Press ENTER: Activates buttons and form submission
- [ ] Press SPACE: Checks checkboxes
- [ ] Press ESC: Closes modal
- [ ] Focus is visible (blue outline or highlight)

#### ✓ Screen Reader Testing (NVDA/JAWS/VoiceOver)
- [ ] Open device modal
- [ ] Screen reader announces "Modal dialog"
- [ ] Radio buttons announced correctly
- [ ] Form labels associated with inputs
- [ ] Error messages announced
- [ ] Success messages announced

#### ✓ Color Contrast
- [ ] All text meets WCAG AA standard (4.5:1 for normal text)
- [ ] Check in DevTools → Accessibility → Color Contrast Ratio
- [ ] Dark theme background (#111827) + white text (#ffffff) = 15.6:1 ✓

#### ✓ Focus Indicators
- [ ] Focus visible on all interactive elements
- [ ] No focus trap (user can navigate out of modal)
- [ ] Focus returns to trigger button when modal closes

#### ✓ Reduced Motion
- [ ] Enable "Prefers reduced motion" in OS settings
- [ ] Open modal: No animation, instant appear
- [ ] All interactions still work

---

### Phase 3i: Performance Testing

#### ✓ Page Load Time
- [ ] Open DevTools → Performance tab
- [ ] Measure page load time
- [ ] Should complete in < 3 seconds
- [ ] modals.css loads in < 100ms
- [ ] modal-handlers.js loads in < 200ms

#### ✓ First Modal Open
- [ ] Measure time from click to modal visible
- [ ] Should be < 200ms
- [ ] Animation smooth (60fps)

#### ✓ Form Submission Time
- [ ] Add device (with valid SSH connection)
- [ ] Measure from click to success message
- [ ] Should be < 2 seconds (excluding network time)

#### ✓ Memory Usage
- [ ] Open browser DevTools Memory tab
- [ ] Baseline memory: ~50MB
- [ ] Open device modal: < 55MB
- [ ] Close modal: Returns to baseline
- [ ] Repeat 10 times: No memory leak
- [ ] Final memory should be same as baseline

#### ✓ CPU Usage
- [ ] Monitor CPU during modal interactions
- [ ] No sustained high CPU usage
- [ ] Animations use GPU (smooth)
- [ ] Form validation instant (no lag)

---

### Phase 3j: Browser Compatibility

#### ✓ Chrome/Chromium (Latest)
- [ ] All modals appear correctly
- [ ] Forms validate and submit
- [ ] Animations smooth
- [ ] Dark theme renders correctly
- [ ] Responsive layout works

#### ✓ Firefox (Latest)
- [ ] Modals functional
- [ ] Scrollbar styled correctly (Firefox-specific)
- [ ] Focus indicators visible
- [ ] Forms work normally

#### ✓ Safari (Latest)
- [ ] Modals functional
- [ ] No CSS compatibility issues
- [ ] Touch interactions work (iPad)
- [ ] Focus visible on keyboard navigation

#### ✓ Edge (Latest)
- [ ] Same as Chrome (Chromium-based)

---

### Phase 3k: Mobile/Responsive Testing

#### ✓ Mobile Layout (< 576px)
- [ ] Modal adjusts to fit screen
- [ ] Keyboard doesn't cover form fields
- [ ] Buttons large enough for touch (48px minimum)
- [ ] Scrolling works for long forms
- [ ] No horizontal scroll

#### ✓ Tablet Layout (577px - 768px)
- [ ] Modal takes appropriate width
- [ ] Form spacing comfortable
- [ ] Touch interactions work

#### ✓ Desktop Layout (> 768px)
- [ ] Modal centered on screen
- [ ] Proper sizing (800px typical)
- [ ] All fields visible without scrolling

#### ✓ Device Testing
- [ ] iPhone (latest)
- [ ] Android phone (Chrome)
- [ ] iPad (latest)
- [ ] Android tablet (Chrome)

---

## Automated Testing

### Unit Tests

```bash
# Run all tests
pytest tests/test_modals.py -v

# Run specific test class
pytest tests/test_modals.py::TestDeviceAPI -v

# Run specific test
pytest tests/test_modals.py::TestDeviceAPI::test_add_device -v

# Show print statements
pytest tests/test_modals.py -v -s

# Stop on first failure
pytest tests/test_modals.py -x
```

### Integration Tests

```bash
# Run integration tests only
pytest tests/test_modals.py::TestFullWorkflow -v

# Run with coverage
pytest tests/test_modals.py --cov=controllers --cov=utils
```

---

## Debugging

### Browser Console Debugging

```javascript
// Check ModalManager status
console.log(window.modalManager);

// Log all registered modals
Object.keys(window.modalManager.modals).forEach(key => {
    console.log(`${key}: ${window.modalManager.modals[key].isVisible() ? 'visible' : 'hidden'}`);
});

// Test API client
window.modalManager.api.get('/api/devices/test_device_id')
    .then(result => console.log('Success:', result))
    .catch(error => console.error('Error:', error));

// Test form validation
window.modalManager.formHandlers['deviceForm'].validate();

// Show device modal programmatically
window.modalManager.showModal('deviceManagementModal');

// Hide all modals
window.modalManager.closeAllModals();
```

### Server-Side Debugging

```python
# Enable debug logging in app.py
app.config['DEBUG'] = True

# Check Flask logs
tail -f iteration_logs/*.log

# Monitor database queries
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    print("QUERY: %s [%s]" % (statement, params))
```

### Network Debugging

```javascript
// Intercept all API requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
    console.log('API Request:', args[0], args[1]);
    return originalFetch.apply(this, args)
        .then(response => {
            console.log('API Response:', response.url, response.status);
            return response;
        });
};
```

---

## Known Issues & Workarounds

### Issue: Modal doesn't appear
- **Check**: ModalManager initialized? `console.log(window.modalManager)`
- **Fix**: Ensure `modal-handlers.js` loaded before `DOMContentLoaded`
- **Workaround**: Manually call `modalManager.showModal('modalId')`

### Issue: Form validation not working
- **Check**: FormHandler attached? Check element IDs match
- **Fix**: Verify form element has correct `id` attribute
- **Workaround**: Run `modalManager.formHandlers['formId'].validate()` manually

### Issue: SSH connection test timeout
- **Check**: Network connectivity to device SSH port
- **Fix**: Verify SSH port is open (default 10022)
- **Workaround**: Increase timeout in modal_routes.py (default 10 seconds)

### Issue: Dark theme not applied
- **Check**: modals.css loaded? Check Network tab
- **Fix**: Clear browser cache (Ctrl+Shift+Delete)
- **Workaround**: Manually apply CSS by adding `<link rel="stylesheet" href="/static/css/modals.css">`

---

## Production Deployment Checklist

- [ ] All tests pass: `pytest tests/test_modals.py -v`
- [ ] No JavaScript console errors
- [ ] No JavaScript console warnings
- [ ] All 9 modals functional
- [ ] SSH connection testing works
- [ ] Forms validate correctly
- [ ] User feedback (success/error) clear
- [ ] Mobile responsive
- [ ] Keyboard navigation works
- [ ] Screen reader accessible
- [ ] Performance acceptable (< 200ms modal open)
- [ ] Session management working
- [ ] Error handling comprehensive
- [ ] Logging enabled and monitored
- [ ] Database migrations applied
- [ ] Static files cached correctly
- [ ] HTTPS enabled in production

---

## Support & Escalation

### Issues to Report
1. Any JavaScript console errors
2. API endpoints returning unexpected status codes
3. Form validation not working on specific browsers
4. Performance issues (> 200ms modal open)
5. Accessibility failures (keyboard, screen reader)

### Support Contact
- **Development Team**: Check iteration_logs/ for detailed logs
- **Database Issues**: Check PostgreSQL connection string in config_database.py
- **SSH Issues**: Check config_commands.py for timeout values

---

**Last Updated**: 2024-01-15
**Version**: Phase 3 v1.0
**Status**: Production Ready
