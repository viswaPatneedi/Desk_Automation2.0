# Phase 3 Modal UI - Developer Quick Reference

Quick reference guide for developers using the Phase 3 Modal UI System.

## Table of Contents
1. [Component Overview](#component-overview)
2. [JavaScript API](#javascript-api)
3. [Flask API](#flask-api)
4. [Form Handling](#form-handling)
5. [Common Tasks](#common-tasks)
6. [Troubleshooting](#troubleshooting)

---

## Component Overview

### Architecture Diagram
```
┌─ Modal System ─────────────────────┐
│                                     │
│  ┌─ ModalManager (Orchestrator)   │
│  │  • managesAll 9 modals          │
│  │  • Coordinate handlerse         │
│  └────────────────────────────────┘
│         │            │
│    ┌────▼─────┐  ┌──▼──────────┐
│    │ FormHandler│  │ APIClient   │
│    │(Validation)│  │ (HTTP Comm) │
│    └──────────    └─────────────┘
│   
│  Device Modal     Auth Modal
│  Execution Modal  Method Modal
│  Sequence Modal   etc...
│
└─────────────────────────────────────┘
```

### File Structure
```
static/
├── js/
│   └── modal-handlers.js        # Main JavaScript handlers (850+ lines)
├── css/
│   └── modals.css               # All modal styles (600+ lines)

controllers/
├── modal_routes.py              # Flask API endpoints (500+ lines)

utils/
├── modal_integration.py          # Flask integration utilities

templates/
├── modals/
│   ├── base/
│   │   ├── modal_base.html      # Wrapper template
│   │   ├── modal_header.html    # Header component
│   │   ├── modal_body.html      # Body component
│   │   └── modal_footer.html    # Footer component
│   ├── auth/
│   │   └── auth_login.html
│   ├── device_management/
│   │   └── device_management_add.html
│   ├── execution_context/
│   │   └── execution_context_capture.html
│   ├── method_execution/
│   │   └── method_execution_select.html
│   └── sequence_management/
│       └── sequence_create.html
```

---

## JavaScript API

### ModalManager Global Object

```javascript
// Access the global ModalManager
window.modalManager

// Properties
window.modalManager.modals              // All 9 modals
window.modalManager.formHandlers        // All form handlers
window.modalManager.api                 // API client instance
window.modalManager.alertContainer      // Alert display element
```

### Core Methods

#### Show/Hide Modals

```javascript
// Show a modal
window.modalManager.showModal('deviceManagementModal');
window.modalManager.showModal('authLoginModal');
window.modalManager.showModal('executionContextCaptureModal');

// Hide a specific modal
window.modalManager.closeModal('deviceManagementModal');

// Hide all modals
window.modalManager.closeAllModals();

// Check if modal is visible
window.modalManager.isModalVisible('deviceManagementModal');  // Returns true/false
```

#### Form Handling

```javascript
// Get form handler
const formHandler = window.modalManager.formHandlers['deviceForm'];

// Validate form
const isValid = formHandler.validate();  // Returns true/false

// Get form data
const formData = formHandler.getFormData();
// Returns: { device_name: 'Test', ssh_host: '192.168.1.1', ... }

// Clear form
formHandler.clear();

// Populate form with data
formHandler.populateForm({
    device_name: 'My Device',
    ssh_host: '192.168.1.100'
});

// Add custom error
formHandler.addError('fieldName', 'Custom error message');

// Clear errors
formHandler.clearErrors();
```

#### API Client

```javascript
// Access API client
const api = window.modalManager.api;

// GET request
api.get('/api/devices/device_123')
    .then(result => console.log(result))
    .catch(error => console.error(error));

// POST request
api.post('/api/devices', {
    device_name: 'NewDevice',
    ssh_host: '192.168.1.100'
})
    .then(result => console.log(result))
    .catch(error => console.error(error));

// PUT request
api.put('/api/devices/device_123', {
    device_name: 'UpdatedName'
})
    .then(result => console.log(result))
    .catch(error => console.error(error));

// DELETE request
api.delete('/api/devices/device_123')
    .then(result => console.log(result))
    .catch(error => console.error(error));
```

#### User Feedback

```javascript
// Show success message
window.modalManager.showSuccess('✅ Device added successfully!');

// Show error message
window.modalManager.showError('❌ Failed to add device');

// Show warning message
window.modalManager.showWarning('⚠️ Connection timeout');

// Show info message
window.modalManager.showInfo('ℹ️ Processing...');

// Clear all messages
window.modalManager.clearAlerts();
```

#### Device Operations

```javascript
// Test SSH connection
window.modalManager.testSSHConnection(host, port, username, password)
    .then(result => {
        console.log(`✅ Connected in ${result.response_time}ms`);
    })
    .catch(error => {
        console.error(`❌ ${error.message}`);
    });

// Save device
window.modalManager.saveDevice()
    .then(result => {
        console.log(`✅ Device saved: ${result.device_id}`);
        window.modalManager.closeModal('deviceManagementModal');
    });
```

#### Execution Context

```javascript
// Capture execution context
window.modalManager.captureExecutionContext(deviceId, methodId)
    .then(() => {
        // Context modal is shown
    });

// Save execution context
window.modalManager.saveExecutionContext()
    .then(result => {
        console.log(`✅ Execution ID: ${result.execution_id}`);
    });
```

#### Method Execution

```javascript
// Show method execution modal
window.modalManager.showMethodExecutionModal(methodId, deviceId);

// Update method parameters
window.modalManager.updateMethodParameters({ timeout: 30, retry_count: 3 });

// Calculate method ETA
const eta = window.modalManager.calculateMethodETA(methodId, parameters);
console.log(`Estimated time: ${eta}`);

// Execute method
window.modalManager.executeMethod()
    .then(result => {
        console.log(`✅ Execution started: ${result.execution_id}`);
    });
```

#### Sequence Management

```javascript
// Show sequence create modal
window.modalManager.showSequenceCreateModal();

// Load sequence for editing
window.modalManager.editSequence(sequenceId)
    .then(() => {
        // Sequence modal is shown with data
    });

// Save sequence definition
window.modalManager.saveSequenceDefinition()
    .then(result => {
        console.log(`✅ Sequence saved: ${result.sequence_id}`);
    });
```

---

## Flask API

### Authentication

All protected endpoints require user authentication.

```python
@modal_api.route('/api/devices', methods=['POST'])
@modal_login_required  # Requires authenticated user
def add_device():
    pass
```

### Endpoint Reference

#### Device Management

```
POST   /api/devices/test-connection
GET    /api/devices/<device_id>
POST   /api/devices
PUT    /api/devices/<device_id>
```

**Add Device Request**:
```json
{
    "device_name": "TestDevice",
    "device_type": "rdk_box",
    "ssh_host": "192.168.1.100",
    "ssh_port": "10022",
    "ssh_username": "root",
    "ssh_password": "password",
    "location": "Test Lab",
    "is_active": true
}
```

**Test SSH Connection Request**:
```json
{
    "ssh_host": "192.168.1.100",
    "ssh_port": "10022",
    "ssh_username": "root",
    "ssh_password": "password"
}
```

**Test SSH Connection Response**:
```json
{
    "success": true,
    "message": "SSH connection successful",
    "response_time": "245ms"
}
```

#### Authentication

```
POST   /api/auth/login
```

**Login Request**:
```json
{
    "email": "user@example.com",
    "password": "password",
    "remember_me": false
}
```

**Login Response**:
```json
{
    "success": true,
    "message": "Login successful",
    "redirect_url": "/"
}
```

#### Execution Context

```
POST   /api/executions/capture-context
```

**Capture Context Request**:
```json
{
    "device_id": "device_123",
    "method_id": "method_soft_boot",
    "method_rationale": "Testing soft boot after factory reset",
    "execution_notes": "Running with specific conditions"
}
```

**Capture Context Response**:
```json
{
    "success": true,
    "execution_id": "exec_1705334445000",
    "timestamp_utc": "2024-01-15T14:30:45.123Z"
}
```

#### Sequences

```
POST   /api/sequences/create
GET    /api/sequences/<sequence_id>
PUT    /api/sequences/<sequence_id>
```

**Create Sequence Request**:
```json
{
    "sequence_name": "Test_Sequence_v1",
    "description": "Test sequence for validation",
    "rationale": "This sequence tests multiple boot methods",
    "methods": ["soft_boot", "hard_boot"],
    "device_ids": ["device_123"],
    "visibility": "team",
    "is_readonly": false,
    "tags": "boot-test,regression"
}
```

---

## Form Handling

### Validator Types

```javascript
// email: Validates email format
const emailValidator = (value) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
};

// ipv4: Validates IPv4 address
const ipv4Validator = (value) => {
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    return ipRegex.test(value) && 
           value.split('.').every(part => parseInt(part) <= 255);
};

// hostname: Validates hostname format
const hostnameValidator = (value) => {
    return /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/.test(value);
};

// strongPassword: Validates password complexity
const strongPasswordValidator = (value) => {
    return value.length >= 8 &&
           /[A-Z]/.test(value) &&
           /[a-z]/.test(value) &&
           /[0-9]/.test(value);
};

// required: Validates field is not empty
const requiredValidator = (value) => {
    return value && value.trim() !== '';
};

// numeric: Validates numeric value
const numericValidator = (value) => {
    return !isNaN(value) && value !== '';
};

// minLength: Validates minimum length
const minLengthValidator = (value, minLength) => {
    return value.length >= minLength;
};

// maxLength: Validates maximum length
const maxLengthValidator = (value, maxLength) => {
    return value.length <= maxLength;
};
```

### Adding Custom Form Handlers

```javascript
// In modal-handlers.js, extend the formHandlers initialization:

this.formHandlers['customForm'] = new FormHandler('customForm', {
    customField: [
        { type: 'required', message: 'This field is required' },
        { type: 'custom', message: 'Custom validation failed', fn: (value) => {
            return value.startsWith('CUSTOM_');
        }}
    ]
});

// In your modal HTML:
<form id="customForm">
    <input type="text" id="customField" name="customField" />
    <button type="button" onClick="window.modalManager.formHandlers['customForm'].validate()">Validate</button>
</form>
```

---

## Common Tasks

### Task 1: Add a New Modal

1. **Create modal template** in `templates/modals/your_feature/`:
```html
<!-- templates/modals/your_feature/your_modal.html -->
{% include "modals/base/modal_base.html" %}
<div class="modal-content">
    {% include "modals/base/modal_header.html" %}
    <!-- Your modal body -->
</div>
```

2. **Register in ModalManager** (modal-handlers.js):
```javascript
this.modals['yourModalId'] = new bootstrap.Modal(
    document.getElementById('yourModalId')
);
```

3. **Add form handler** if needed (modal-handlers.js):
```javascript
this.formHandlers['yourForm'] = new FormHandler('yourForm', {
    field1: [{ type: 'required', message: 'Field1 required' }]
});
```

4. **Add API endpoint** (modal_routes.py):
```python
@modal_api.route('/api/your_endpoint', methods=['POST'])
@modal_login_required
def your_handler():
    data = request.get_json()
    # Your logic here
    return success_response({'status': 'ok'})
```

### Task 2: Add New API Endpoint

1. **Create endpoint** in `controllers/modal_routes.py`:
```python
@modal_api.route('/api/new_feature', methods=['POST'])
@modal_login_required
def new_feature():
    data = request.get_json()
    
    # Validation
    if not data.get('required_field'):
        return error_response('required_field is required', 400)
    
    # Logic
    result = do_something(data)
    
    # Log
    logger.info(f"✅ New feature executed: {result.id}")
    
    return success_response(result.to_dict())
```

2. **Call from JavaScript**:
```javascript
window.modalManager.api.post('/api/new_feature', {
    required_field: 'value'
})
    .then(result => {
        window.modalManager.showSuccess('✅ Feature executed!');
    })
    .catch(error => {
        window.modalManager.showError(`❌ ${error.message}`);
    });
```

### Task 3: Add Form Validation

1. **Add field to FormHandler** (modal-handlers.js):
```javascript
this.formHandlers['deviceForm'].rules['newField'] = [
    { type: 'required', message: 'Field is required' },
    { type: 'custom', message: 'Custom message', fn: (value) => {
        return value.length >= 3;
    }}
];
```

2. **Add input to HTML**:
```html
<input type="text" id="newField" name="newField" 
       data-validation="required" />
<div class="error-message" for="newField"></div>
```

3. **Validation triggers on blur**:
```javascript
document.getElementById('newField').addEventListener('blur', () => {
    window.modalManager.formHandlers['deviceForm'].validateField('newField');
});
```

---

## Troubleshooting

### Problem: Modal not appearing

```javascript
// Check 1: ModalManager exists?
console.log(window.modalManager);  // Should not be undefined

// Check 2: Modal element exists in DOM?
console.log(document.getElementById('modalId'));  // Should not be null

// Check 3: Bootstrap modal initialized?
console.log(window.modalManager.modals['modalId']);  // Should be a Modal object

// Solution: Manually show modal
window.modalManager.showModal('modalId');
```

### Problem: Form not validating

```javascript
// Check 1: Form handler registered?
console.log(window.modalManager.formHandlers['formId']);  // Should not be undefined

// Check 2: Form element IDs match configuration?
// Look in modal-handlers.js for form ID, compare with HTML

// Check 3: Fields have proper attributes?
// <input id="fieldName" name="fieldName" />

// Solution: Force validation
window.modalManager.formHandlers['formId'].validate();
```

### Problem: API request failing

```javascript
// Check NetworkTab in DevTools for:
// 1. Request URL correct?
// 2. Response status 200/201?
// 3. Response contains expected fields?

// Check server logs:
tail -f iteration_logs/*.log

// Common causes:
// - User not authenticated: 401
// - Missing required fields: 400
// - Resource not found: 404
// - Server error: 500
```

### Problem: Form data not saving to database

```python
# In Python, check:
# 1. Database connection working?
from app import db
db.session.execute('SELECT 1')

# 2. Model has required fields?
# Check Device model in models/

# 3. Commit changes?
db.session.add(device)
db.session.commit()

# 4. Check logs for errors?
logger.info(f"Device saved: {device.id}")
```

### Problem: Accessibility issues

```html
<!-- Ensure modals have ARIA labels -->
<div class="modal" id="myModal" role="dialog" 
     aria-labelledby="modalTitle"
     aria-hidden="true">
    <div class="modal-header">
        <h5 class="modal-title" id="modalTitle">Modal Title</h5>
    </div>
</div>

<!-- Ensure form labels linked to inputs -->
<label for="deviceName">Device Name:</label>
<input id="deviceName" type="text" />
```

---

## Performance Tips

1. **Lazy load modals**: Load modal content only when first opened
2. **Debounce form validation**: Don't validate on every keystroke
3. **Cache API responses**: Store device lists to reduce API calls
4. **Use async/await**: More readable than promise chains
5. **Monitor memory**: Check for memory leaks in long-running sessions

```javascript
// Good: Async/await
async function saveDevice() {
    try {
        const result = await window.modalManager.api.post('/api/devices', data);
        window.modalManager.showSuccess('✅ Saved');
    } catch (error) {
        window.modalManager.showError(`❌ ${error.message}`);
    }
}

// Avoid: Deep promise chains
window.modalManager.api.post('/api/devices', data)
    .then(result => {
        return window.modalManager.api.get(`/api/devices/${result.id}`);
    })
    .then(device => {
        return db.save(device);
    })
    .catch(error => {...});
```

---

## Version

**Phase 3 Modal UI System v1.0**
- JavaScript Handlers: 850+ lines
- Flask API: 500+ lines
- CSS Styling: 600+ lines
- HTML Templates: 1,525 lines
- **Total: 3,475+ lines of production code**

**Status**: ✅ Production Ready
**Last Updated**: 2024-01-15
