/**
 * Phase 3 Modal UI - Complete JavaScript Handlers
 * Comprehensive handlers for all modal interactions, form submissions, and data persistence
 * 
 * Architecture:
 * - ModalManager: Central orchestrator for all modal operations
 * - FormHandler: Form submission and validation
 * - APIClient: Backend communication
 * - UIStateManager: Client-side state management
 * - AccessibilityManager: WCAG 2.1 AA compliance
 */

// ============================================================
// API CLIENT - Backend Communication
// ============================================================

class APIClient {
    constructor() {
        this.baseURL = '/api';
        this.timeout = 30000;
    }

    async request(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            timeout: options.timeout || this.timeout,
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.message || 
                    `HTTP ${response.status}: ${response.statusText}`
                );
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${method} ${endpoint}):`, error);
            throw error;
        }
    }

    get(endpoint, options = {}) {
        return this.request('GET', endpoint, null, options);
    }

    post(endpoint, data, options = {}) {
        return this.request('POST', endpoint, data, options);
    }

    put(endpoint, data, options = {}) {
        return this.request('PUT', endpoint, data, options);
    }

    delete(endpoint, options = {}) {
        return this.request('DELETE', endpoint, null, options);
    }
}

// ============================================================
// FORM HANDLER - Validation & Submission
// ============================================================

class FormHandler {
    constructor(formId) {
        this.form = document.getElementById(formId);
        this.formId = formId;
        this.validators = {};
    }

    addValidator(fieldName, validator) {
        this.validators[fieldName] = validator;
    }

    validate() {
        if (!this.form) return false;

        let isValid = true;
        const fields = this.form.querySelectorAll('[name]');

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const fieldName = field.name;
        const value = field.value.trim();

        // Required field validation
        if (field.hasAttribute('required') && !value) {
            this.showFieldError(field, 'This field is required');
            return false;
        }

        // Custom validator
        if (this.validators[fieldName]) {
            try {
                this.validators[fieldName](value);
                this.clearFieldError(field);
                return true;
            } catch (error) {
                this.showFieldError(field, error.message);
                return false;
            }
        }

        this.clearFieldError(field);
        return true;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        const feedback = field.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.textContent = message;
            feedback.style.display = 'block';
        }
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const feedback = field.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.style.display = 'none';
        }
    }

    getFormData() {
        if (!this.form) return null;

        const formData = new FormData(this.form);
        const data = {};

        // Convert FormData to object
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values (arrays)
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key]];
                }
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }

        return data;
    }

    clearForm() {
        if (this.form) {
            this.form.reset();
            this.form.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
            });
        }
    }
}

// ============================================================
// MODAL MANAGER - Central Orchestrator
// ============================================================

class ModalManager {
    constructor() {
        this.modals = {};
        this.currentModal = null;
        this.api = new APIClient();
        this.formHandlers = {};
        this.initialize();
    }

    initialize() {
        console.log('🚀 Initializing Modal Manager...');
        
        // Initialize all modal instances
        const modalElements = document.querySelectorAll('.modal');
        modalElements.forEach(modalEl => {
            const modalId = modalEl.id;
            this.modals[modalId] = new bootstrap.Modal(modalEl, {
                backdrop: modalEl.dataset.backdrop !== 'false',
                keyboard: modalEl.dataset.keyboard !== 'false',
                focus: true
            });

            // Add event listeners
            modalEl.addEventListener('show.bs.modal', () => this.onModalShow(modalId));
            modalEl.addEventListener('hide.bs.modal', () => this.onModalHide(modalId));
        });

        // Register form handlers
        this.registerFormHandlers();

        // Initialize accessibility features
        this.initializeAccessibility();

        console.log(`✅ Modal Manager initialized with ${Object.keys(this.modals).length} modals`);
    }

    registerFormHandlers() {
        // Device Management Form
        const deviceForm = new FormHandler('deviceManagementForm');
        deviceForm.addValidator('device_name', (value) => {
            if (value.length < 2) throw new Error('Device name must be at least 2 characters');
        });
        deviceForm.addValidator('ssh_host', (value) => {
            if (!this.isValidIPOrHostname(value)) throw new Error('Invalid IP address or hostname');
        });
        deviceForm.addValidator('ssh_username', (value) => {
            if (value.length < 1) throw new Error('SSH username is required');
        });
        deviceForm.addValidator('ssh_password', (value) => {
            if (value.length < 1) throw new Error('SSH password is required');
        });
        this.formHandlers['deviceManagementForm'] = deviceForm;

        // Login Form
        const loginForm = new FormHandler('loginForm');
        loginForm.addValidator('email', (value) => {
            if (!this.isValidEmail(value)) throw new Error('Please enter a valid email address');
        });
        loginForm.addValidator('password', (value) => {
            if (value.length < 6) throw new Error('Password must be at least 6 characters');
        });
        this.formHandlers['loginForm'] = loginForm;

        // Execution Context Form
        const contextForm = new FormHandler('executionContextForm');
        contextForm.addValidator('method_rationale', (value) => {
            if (value.length < 10) throw new Error('Please provide detailed rationale (at least 10 characters)');
        });
        this.formHandlers['executionContextForm'] = contextForm;

        // Method Execution Form
        const methodForm = new FormHandler('methodExecutionForm');
        methodForm.addValidator('method', (value) => {
            if (!value) throw new Error('Please select a method');
        });
        this.formHandlers['methodExecutionForm'] = methodForm;

        // Sequence Management Form
        const sequenceForm = new FormHandler('sequenceManagementForm');
        sequenceForm.addValidator('sequence_name', (value) => {
            if (value.length < 3) throw new Error('Sequence name must be at least 3 characters');
            if (!/^[a-zA-Z0-9_-]+$/.test(value)) throw new Error('Sequence name can only contain alphanumeric, underscore, and hyphen');
        });
        sequenceForm.addValidator('rationale', (value) => {
            if (value.length < 20) throw new Error('Please provide detailed rationale (at least 20 characters)');
        });
        this.formHandlers['sequenceManagementForm'] = sequenceForm;
    }

    registerFormHandlers() {
        // Initialize form handlers for each modal form
        const forms = ['deviceManagementForm', 'loginForm', 'executionContextForm', 'methodExecutionForm', 'sequenceManagementForm'];
        
        forms.forEach(formId => {
            const formEl = document.getElementById(formId);
            if (formEl) {
                const handler = new FormHandler(formId);
                
                // Add field-level validation on blur
                formEl.querySelectorAll('input, textarea, select').forEach(field => {
                    field.addEventListener('blur', () => handler.validateField(field));
                });

                this.formHandlers[formId] = handler;
            }
        });
    }

    initializeAccessibility() {
        // Add keyboard navigation support
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentModal) {
                this.closeModal(this.currentModal);
            }
        });

        // Focus management for modals
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('shown.bs.modal', () => {
                const firstInput = modal.querySelector('input, textarea, select, button');
                if (firstInput) firstInput.focus();
            });
        });
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    isValidIPOrHostname(value) {
        const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
        const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
        return ipRegex.test(value) || hostnameRegex.test(value);
    }

    async showModal(modalId, options = {}) {
        if (!this.modals[modalId]) {
            console.error(`Modal ${modalId} not found`);
            return false;
        }

        try {
            this.currentModal = modalId;
            
            // Pre-populate modal data if provided
            if (options.data) {
                await this.populateModalData(modalId, options.data);
            }

            this.modals[modalId].show();
            return true;
        } catch (error) {
            console.error(`Error showing modal ${modalId}:`, error);
            this.showError('Failed to open modal');
            return false;
        }
    }

    closeModal(modalId) {
        if (this.modals[modalId]) {
            this.modals[modalId].hide();
            this.currentModal = null;
        }
    }

    toggleModal(modalId) {
        if (this.currentModal === modalId) {
            this.closeModal(modalId);
        } else {
            this.showModal(modalId);
        }
    }

    async populateModalData(modalId, data) {
        // Populate form fields with data
        const modal = document.getElementById(modalId);
        if (!modal) return;

        Object.keys(data).forEach(key => {
            const field = modal.querySelector(`[name="${key}"], [id="${key}"]`);
            if (field) {
                if (field.type === 'checkbox') {
                    field.checked = data[key];
                } else if (field.type === 'radio') {
                    document.querySelector(`[name="${key}"][value="${data[key]}"]`).checked = true;
                } else {
                    field.value = data[key];
                    field.textContent = data[key]; // For read-only divs
                }
            }
        });
    }

    onModalShow(modalId) {
        console.log(`📂 Opening modal: ${modalId}`);
        document.body.style.overflow = 'hidden';
    }

    onModalHide(modalId) {
        console.log(`📌 Closing modal: ${modalId}`);
        document.body.style.overflow = '';
        
        // Clear form data on close
        const form = document.querySelector(`#${modalId} form`);
        if (form) {
            form.reset();
        }
    }

    showSuccess(message, duration = 3000) {
        this.showAlert(message, 'success', duration);
    }

    showError(message, duration = 5000) {
        this.showAlert(message, 'danger', duration);
    }

    showWarning(message, duration = 4000) {
        this.showAlert(message, 'warning', duration);
    }

    showAlert(message, type = 'info', duration = 3000) {
        const alertId = `alert-${Date.now()}`;
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        const alertContainer = document.getElementById('alertContainer') || (() => {
            const container = document.createElement('div');
            container.id = 'alertContainer';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
            return container;
        })();

        alertContainer.insertAdjacentHTML('beforeend', alertHTML);

        if (duration > 0) {
            setTimeout(() => {
                const alertEl = document.getElementById(alertId);
                if (alertEl) alertEl.remove();
            }, duration);
        }
    }
}

// ============================================================
// DEVICE MANAGEMENT MODAL HANDLERS
// ============================================================

async function testSSHConnection() {
    const button = document.getElementById('testConnectionBtn');
    const host = document.getElementById('sshHost').value;
    const port = document.getElementById('sshPort').value;
    const username = document.getElementById('sshUsername').value;

    if (!host || !port || !username) {
        modalManager.showError('Please fill in SSH Host, Port, and Username');
        return;
    }

    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Testing...';

    try {
        const result = await modalManager.api.post('/devices/test-connection', {
            ssh_host: host,
            ssh_port: port,
            ssh_username: username
        });

        if (result.success) {
            modalManager.showSuccess(`✅ SSH Connection successful! (Response time: ${result.response_time}ms)`);
        } else {
            modalManager.showError(`❌ SSH Connection failed: ${result.error}`);
        }
    } catch (error) {
        modalManager.showError(`Connection test error: ${error.message}`);
    } finally {
        button.disabled = false;
        button.innerHTML = 'Test Connection';
    }
}

async function saveDevice() {
    const form = modalManager.formHandlers['deviceManagementForm'];
    
    if (!form.validate()) {
        modalManager.showError('Please fix the errors in the form');
        return;
    }

    const data = form.getFormData();
    const button = document.getElementById('saveDeviceBtn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    try {
        const endpoint = data.device_id ? `/devices/${data.device_id}` : '/devices/add';
        const method = data.device_id ? 'put' : 'post';

        const result = await modalManager.api[method](endpoint, data);

        if (result.success) {
            modalManager.showSuccess(`✅ Device ${data.device_id ? 'updated' : 'added'} successfully!`);
            form.clearForm();
            modalManager.closeModal('deviceManagementAddModal');

            // Refresh device list
            if (window.refreshDeviceList) {
                window.refreshDeviceList();
            }
        } else {
            modalManager.showError(`Failed to save device: ${result.error}`);
        }
    } catch (error) {
        modalManager.showError(`Error saving device: ${error.message}`);
    } finally {
        button.disabled = false;
        button.innerHTML = 'Save Device';
    }
}

// ============================================================
// AUTHENTICATION MODAL HANDLERS
// ============================================================

async function submitLogin() {
    const form = modalManager.formHandlers['loginForm'];
    
    if (!form.validate()) {
        modalManager.showError('Please fix the errors in the form');
        return;
    }

    const data = form.getFormData();
    const button = document.getElementById('loginSubmitBtn');
    const btnText = document.getElementById('loginBtnText');
    const spinner = document.getElementById('loginBtnSpinner');

    button.disabled = true;
    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';

    try {
        const result = await modalManager.api.post('/auth/login', data);

        if (result.success) {
            modalManager.showSuccess('✅ Login successful!');
            form.clearForm();
            
            // Redirect after brief delay
            setTimeout(() => {
                window.location.href = result.redirect_url || '/';
            }, 1000);
        } else {
            modalManager.showError(`Login failed: ${result.error}`);
            document.getElementById('loginErrorText').textContent = result.error;
            document.getElementById('loginErrorAlert').style.display = 'block';
        }
    } catch (error) {
        modalManager.showError(`Login error: ${error.message}`);
    } finally {
        button.disabled = false;
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
    }
}

function showForgotPasswordModal() {
    modalManager.closeModal('authLoginModal');
    modalManager.showModal('authForgotPasswordModal');
}

function showRegisterModal() {
    modalManager.closeModal('authLoginModal');
    modalManager.showModal('authRegisterModal');
}

// ============================================================
// EXECUTION CONTEXT MODAL HANDLERS
// ============================================================

async function captureExecutionContext(deviceId, methodId) {
    try {
        // Fetch device and method info
        const [deviceResult, methodResult] = await Promise.all([
            modalManager.api.get(`/devices/${deviceId}`),
            modalManager.api.get(`/methods/${methodId}`)
        ]);

        if (!deviceResult.success || !methodResult.success) {
            modalManager.showError('Failed to load device or method information');
            return;
        }

        const device = deviceResult.data;
        const method = methodResult.data;

        // Populate execution context modal
        await modalManager.populateModalData('executionContextCaptureModal', {
            executionDeviceId: deviceId,
            executionMethodId: methodId,
            contextDeviceName: device.device_name,
            contextDeviceType: device.device_type,
            contextSSHHost: device.ssh_host,
            contextDeviceLocation: device.location || 'Not specified',
            contextMethodName: method.name,
            contextMethodDescription: method.description,
            contextUser: getCurrentUser(),
            contextTeam: getCurrentTeam(),
            contextTimestamp: getCurrentUTCTimestamp()
        });

        modalManager.showModal('executionContextCaptureModal');
    } catch (error) {
        modalManager.showError(`Error capturing execution context: ${error.message}`);
    }
}

async function saveExecutionContext() {
    const form = modalManager.formHandlers['executionContextForm'];
    
    if (!form.validate()) {
        modalManager.showError('Please provide the method rationale');
        return;
    }

    const data = form.getFormData();
    const button = document.getElementById('captureContextBtn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Capturing Context...';

    try {
        const result = await modalManager.api.post('/executions/capture-context', data);

        if (result.success) {
            modalManager.showSuccess('✅ Execution context captured successfully!');
            form.clearForm();
            modalManager.closeModal('executionContextCaptureModal');

            // Trigger actual execution
            if (window.startExecution) {
                window.startExecution(result.execution_id);
            }
        } else {
            modalManager.showError(`Failed to capture context: ${result.error}`);
        }
    } catch (error) {
        modalManager.showError(`Error capturing context: ${error.message}`);
    } finally {
        button.disabled = false;
        button.innerHTML = 'Capture Context & Execute';
    }
}

function getCurrentUser() {
    // Get from page data attribute or session
    return document.body.dataset.currentUser || 'Unknown User';
}

function getCurrentTeam() {
    // Get from page data attribute or session
    return document.body.dataset.currentTeam || 'Default Team';
}

function getCurrentUTCTimestamp() {
    return new Date().toISOString();
}

// ============================================================
// METHOD EXECUTION MODAL HANDLERS
// ============================================================

async function showMethodExecutionModal(deviceId) {
    try {
        // Fetch device info
        const result = await modalManager.api.get(`/devices/${deviceId}`);
        
        if (!result.success) {
            modalManager.showError('Failed to load device information');
            return;
        }

        const device = result.data;
        document.getElementById('deviceExecutionName').textContent = device.device_name;
        document.getElementById('executionDeviceId').value = deviceId;

        modalManager.showModal('methodExecutionModal');
    } catch (error) {
        modalManager.showError(`Error opening method execution modal: ${error.message}`);
    }
}

function updateMethodParameters() {
    const method = document.getElementById('methodSelect').value;
    const paramsSection = document.getElementById('methodParametersSection');
    
    // Clear existing parameters
    paramsSection.innerHTML = '';

    if (!method) return;

    // Show method description
    const descSection = document.getElementById('methodDescriptionSection');
    descSection.style.display = 'block';

    // Add method-specific parameters
    if (method === 'system_command') {
        paramsSection.innerHTML = `
            <div class="mb-4">
                <h6 class="text-primary mb-3" style="color: #3b82f6; font-weight: 600; border-bottom: 2px solid #374151; padding-bottom: 10px;">
                    Command Parameters
                </h6>
                <label for="systemCommand" class="form-label" style="color: #d1d5db; font-weight: 500;">
                    System Command <span class="text-danger">*</span>
                </label>
                <input type="text" class="form-control" id="systemCommand" name="system_command" 
                       placeholder="e.g., /opt/script/check_status.sh" required
                       style="background: #1f2937; border: 1px solid #374151; color: #e5e7eb;">
            </div>
        `;
    } else if (method === 'voice_command') {
        paramsSection.innerHTML = `
            <div class="mb-4">
                <h6 class="text-primary mb-3" style="color: #3b82f6; font-weight: 600; border-bottom: 2px solid #374151; padding-bottom: 10px;">
                    Voice Command Parameters
                </h6>
                <label for="voiceCommand" class="form-label" style="color: #d1d5db; font-weight: 500;">
                    Voice Command <span class="text-danger">*</span>
                </label>
                <input type="text" class="form-control" id="voiceCommand" name="voice_command" 
                       placeholder="e.g., Hello Google, open Netflix" required
                       style="background: #1f2937; border: 1px solid #374151; color: #e5e7eb;">
            </div>
        `;
    }

    // Show ETA section
    document.getElementById('etaSection').style.display = 'block';
    calculateMethodETA();
}

function toggleSequenceName() {
    const checked = document.getElementById('saveAsSequence').checked;
    document.getElementById('sequenceNameSection').style.display = checked ? 'block' : 'none';
}

function calculateMethodETA() {
    const iterations = parseInt(document.getElementById('executionIterations').value) || 1;
    const waitBetween = parseInt(document.getElementById('waitBetweenIterations').value) || 0;
    
    // Estimated time per method (in seconds)
    const methodTimes = {
        'soft_boot': 30,
        'hard_boot': 45,
        'reboot': 60,
        'deep_sleep': 120,
        'standby': 15,
        'system_command': 10,
        'voice_command': 5,
        'capture_screenshot': 10,
        'capture_logs': 10
    };

    const method = document.getElementById('methodSelect').value;
    const methodTime = methodTimes[method] || 30;
    const totalTime = (methodTime + waitBetween) * iterations;

    document.getElementById('etaDisplay').textContent = formatDuration(totalTime);
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    const parts = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0) parts.push(`${secs}s`);

    return parts.join(' ') || '< 1s';
}

function previewMethod() {
    const form = modalManager.formHandlers['methodExecutionForm'];
    const method = document.getElementById('methodSelect').value;
    const iterations = document.getElementById('executionIterations').value;
    const waitBetween = document.getElementById('waitBetweenIterations').value;

    const preview = `
Method: ${method}
Iterations: ${iterations}
Wait Between: ${waitBetween}s
Estimated Duration: ${document.getElementById('etaDisplay').textContent}
    `;

    modalManager.showAlert(preview, 'info', 0);
}

async function executeMethod() {
    const form = modalManager.formHandlers['methodExecutionForm'];
    
    if (!form.validate()) {
        modalManager.showError('Please fix the errors in the form');
        return;
    }

    const deviceId = document.getElementById('executionDeviceId').value;
    const methodId = document.getElementById('methodSelect').value;

    // Close method execution modal and open context capture
    modalManager.closeModal('methodExecutionModal');
    await captureExecutionContext(deviceId, methodId);
}

// ============================================================
// SEQUENCE MANAGEMENT MODAL HANDLERS
// ============================================================

async function saveSequenceDefinition() {
    const form = modalManager.formHandlers['sequenceManagementForm'];
    
    if (!form.validate()) {
        modalManager.showError('Please fix the errors in the form');
        return;
    }

    const data = form.getFormData();
    const button = document.getElementById('saveSequenceBtn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    try {
        const endpoint = data.editing_id ? `/sequences/${data.editing_id}` : '/sequences/create';
        const method = data.editing_id ? 'put' : 'post';

        const result = await modalManager.api[method](endpoint, data);

        if (result.success) {
            modalManager.showSuccess(`✅ Sequence ${data.editing_id ? 'updated' : 'created'} successfully!`);
            form.clearForm();
            modalManager.closeModal('sequenceManagementSaveModal');

            // Refresh sequence list
            if (window.refreshSequenceList) {
                window.refreshSequenceList();
            }
        } else {
            modalManager.showError(`Failed to save sequence: ${result.error}`);
        }
    } catch (error) {
        modalManager.showError(`Error saving sequence: ${error.message}`);
    } finally {
        button.disabled = false;
        button.innerHTML = 'Save Sequence';
    }
}

async function editSequence(sequenceId) {
    try {
        const result = await modalManager.api.get(`/sequences/${sequenceId}`);

        if (!result.success) {
            modalManager.showError('Failed to load sequence');
            return;
        }

        const sequence = result.data;
        
        // Populate form with sequence data
        await modalManager.populateModalData('sequenceManagementSaveModal', {
            editing_id: sequenceId,
            sequence_name: sequence.name,
            description: sequence.description,
            rationale: sequence.rationale,
            visibility: sequence.visibility,
            is_readonly: sequence.readonly,
            tags: sequence.tags
        });

        modalManager.showModal('sequenceManagementSaveModal');
    } catch (error) {
        modalManager.showError(`Error loading sequence: ${error.message}`);
    }
}

// ============================================================
// GLOBAL INITIALIZATION
// ============================================================

let modalManager;

document.addEventListener('DOMContentLoaded', () => {
    console.log('📦 Phase 3 Modal System initializing...');
    
    // Initialize modal manager
    modalManager = new ModalManager();

    // Add event listeners to dynamic elements
    document.querySelectorAll('[data-toggle="modal"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modalId = btn.dataset.target || btn.getAttribute('href');
            modalManager.showModal(modalId.replace('#', ''));
        });
    });

    // Add item click handlers for device/sequence lists
    document.querySelectorAll('[data-edit-device]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const deviceId = btn.dataset.editDevice;
            loadDeviceForEdit(deviceId);
        });
    });

    document.querySelectorAll('[data-edit-sequence]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const sequenceId = btn.dataset.editSequence;
            editSequence(sequenceId);
        });
    });

    console.log('✅ Phase 3 Modal System initialized successfully!');
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ModalManager,
        FormHandler,
        APIClient,
        modalManager
    };
}
