# UI Implementation Guide - Optional DeepSleep Feature

## 🎨 For Execution Queue UI/Dashboard

When users are dragging steps to the execution order, add a checkbox for this method:

---

## **Option 1: Checkbox in Method Card**

```html
<!-- In the execution queue builder -->
<div class="method-card method-maintenance-deepsleep-wakeup">
    <h3>Maintenance > DeepSleep > Wakeup</h3>
    
    <!-- Existing Parameters -->
    <div class="parameter-group">
        <label for="remote-type">Remote Type:</label>
        <select id="remote-type">
            <option value="">Auto-detect (from device name)</option>
            <option value="XUMO">XUMO</option>
            <option value="SKY">SKY</option>
        </select>
    </div>
    
    <div class="parameter-group">
        <label for="sleep-duration">Sleep Duration (minutes):</label>
        <input type="number" id="sleep-duration" min="10" max="600" value="60">
    </div>
    
    <!-- NEW: Optional DeepSleep Feature -->
    <div class="parameter-group checkbox">
        <label for="include-deepsleep">
            <input type="checkbox" id="include-deepsleep" checked>
            Include DeepSleep & Wakeup Phases (Steps 8-12)
        </label>
        <small class="help-text">
            ✓ Checked (default): Full workflow with deep sleep testing (~95 min)
            ✗ Unchecked: Maintenance only, skip deep sleep (~60 min)
        </small>
    </div>
</div>
```

---

## **Option 2: Toggle Switch (Modern UI)**

```html
<div class="method-card method-maintenance-deepsleep-wakeup">
    <h3>Maintenance > DeepSleep > Wakeup</h3>
    
    <!-- Existing Parameters -->
    <div class="parameter-group">
        <label for="remote-type">Remote Type:</label>
        <select id="remote-type">
            <option value="">Auto-detect (from device name)</option>
            <option value="XUMO">XUMO</option>
            <option value="SKY">SKY</option>
        </select>
    </div>
    
    <!-- NEW: Toggle for DeepSleep -->
    <div class="parameter-group toggle">
        <label>DeepSleep & Wakeup Phases</label>
        <div class="toggle-switch">
            <input type="checkbox" id="include-deepsleep" class="toggle" checked>
            <label for="include-deepsleep" class="toggle-label">
                <span class="toggle-on">ENABLED</span>
                <span class="toggle-off">DISABLED</span>
            </label>
        </div>
        <p class="duration-info">
            <span id="duration-estimate">Estimated duration: 95 minutes</span>
        </p>
    </div>
</div>
```

---

## **Option 3: Radio Buttons (Explicit Choice)**

```html
<div class="method-card method-maintenance-deepsleep-wakeup">
    <h3>Maintenance > DeepSleep > Wakeup</h3>
    
    <div class="parameter-group">
        <label>Execution Mode:</label>
        
        <div class="radio-option">
            <input type="radio" name="execution-mode" value="full" checked id="mode-full">
            <label for="mode-full">
                <strong>Full Workflow</strong><br>
                <small>Includes maintenance + deep sleep + wake-up testing</small><br>
                <small>⏱️ Duration: ~95 minutes</small><br>
                <small>📊 Provides: wakeup_time_seconds metric</small>
            </label>
        </div>
        
        <div class="radio-option">
            <input type="radio" name="execution-mode" value="maintenance-only" id="mode-maintenance">
            <label for="mode-maintenance">
                <strong>Maintenance Only</strong><br>
                <small>Quick maintenance cycle, skip deep sleep testing</small><br>
                <small>⏱️ Duration: ~60 minutes</small><br>
                <small>📊 Device remains in STANDBY after completion</small>
            </label>
        </div>
    </div>
    
    <!-- Other parameters -->
    <div class="parameter-group">
        <label for="remote-type">Remote Type:</label>
        <select id="remote-type">
            <option value="">Auto-detect (from device name)</option>
            <option value="XUMO">XUMO</option>
            <option value="SKY">SKY</option>
        </select>
    </div>
</div>
```

---

## **Option 4: Expandable Section (Information-Rich)**

```html
<div class="method-card method-maintenance-deepsleep-wakeup">
    <h3>Maintenance > DeepSleep > Wakeup</h3>
    
    <div class="parameter-group">
        <label for="remote-type">Remote Type:</label>
        <select id="remote-type">
            <option value="">Auto-detect (from device name)</option>
            <option value="XUMO">XUMO</option>
            <option value="SKY">SKY</option>
        </select>
    </div>
    
    <!-- Expandable DeepSleep Options -->
    <details class="advanced-options">
        <summary>
            <strong>⚙️ DeepSleep Options</strong>
            <span class="default-badge">Optional - Controls steps 8-12</span>
        </summary>
        
        <div class="details-content">
            <div class="info-box">
                <p><strong>Default Behavior:</strong> Full workflow (all 12 steps)</p>
                <p><strong>Option 1:</strong> Skip deep sleep testing</p>
                <p><strong>Saves:</strong> ~15-20 minutes execution time</p>
            </div>
            
            <div class="parameter-group checkbox">
                <label for="include-deepsleep">
                    <input type="checkbox" id="include-deepsleep" checked>
                    Execute Deep Sleep & Wakeup Phases (Steps 8-12)
                </label>
            </div>
            
            <div class="parameter-group">
                <label for="sleep-duration">DeepSleep Duration (minutes):</label>
                <input type="number" id="sleep-duration" min="10" max="600" value="60">
                <small>Only applicable when deep sleep phases are enabled</small>
            </div>
        </div>
    </details>
</div>
```

---

## **JavaScript Handler**

```javascript
// Handle checkbox/toggle changes
document.getElementById('include-deepsleep').addEventListener('change', function(e) {
    const isChecked = e.target.checked;
    const sleepDurationInput = document.getElementById('sleep-duration');
    
    // Update UI based on checkbox state
    if (isChecked) {
        // Full workflow
        document.getElementById('duration-estimate').textContent = 
            'Estimated duration: 95 minutes (maintenance + deep sleep)';
        sleepDurationInput.disabled = false;
        
        // Show wakeup time metric info
        console.log('Full workflow - will provide wakeup_time_seconds');
    } else {
        // Maintenance only
        document.getElementById('duration-estimate').textContent = 
            'Estimated duration: 60 minutes (maintenance only)';
        sleepDurationInput.disabled = true;
        
        // Notify about final state
        console.log('Maintenance only - device will remain in STANDBY');
    }
});

// Build execution queue from UI
function buildExecutionQueue() {
    return [
        {
            "method": "maintenance_deepsleep_wakeup",
            "remote_type": document.getElementById('remote-type').value || undefined,
            "sleep_duration_minutes": parseInt(document.getElementById('sleep-duration').value) || 60,
            "execute_deepsleep_wakeup": document.getElementById('include-deepsleep').checked  // ← Key parameter
        }
    ];
}
```

---

## **Help Text / Tooltips**

```
Checkbox Label: "Include DeepSleep & Wakeup Phases"

Tooltip/Help Text:
═══════════════════════════════════════════════════════════
When ENABLED (✓ Default):
  • Runs full workflow: maintenance + deep sleep + wake-up
  • Total duration: 60-95 minutes
  • Device ends in ON state
  • Provides wakeup_time_seconds metric
  
When DISABLED (✗):
  • Runs maintenance cycle only
  • Skips 15-minute deep sleep wait
  • Skips IR wake-up testing
  • Total duration: ~45-65 minutes
  • Device ends in STANDBY state
  • Faster execution for quick maintenance
═══════════════════════════════════════════════════════════
```

---

## **Status Display During Execution**

```html
<!-- Show what's being executed -->
<div class="execution-status">
    <h4>Maintenance > DeepSleep > Wakeup - Iteration 1</h4>
    
    <div class="status-section">
        <h5>Configuration:</h5>
        <ul>
            <li>Remote Type: SKY</li>
            <li>Deep Sleep Enabled: ✓</li>
            <li>Sleep Duration: 60 minutes</li>
        </ul>
    </div>
    
    <div class="status-section">
        <h5>Execution Progress:</h5>
        <div class="step-list">
            <div class="step completed">✓ [1-2] Check maintenance status</div>
            <div class="step completed">✓ [3] Put device in STANDBY</div>
            <div class="step completed">✓ [4-5] Maintenance cycle polling</div>
            <div class="step completed">✓ [6-7] Reboot and STANDBY verification</div>
            <div class="step in-progress">⏳ [8-12] Deep Sleep & Wakeup (0/15 min)</div>
        </div>
    </div>
    
    <div class="status-section">
        <h5>Results (when complete):</h5>
        <ul>
            <li>Maintenance: ✓ PASSED</li>
            <li>Deep Sleep: ✓ Verified</li>
            <li>Wakeup Time: 45.3 seconds ← Key Metric</li>
        </ul>
    </div>
</div>
```

---

## **Results Display**

```
MAINTENANCE > DEEPSLEEP > WAKEUP - RESULTS
════════════════════════════════════════════════════════════

Configuration:
  Mode: Full Workflow (steps 1-12)  ← or "Maintenance Only (steps 1-7)"
  Remote Type: SKY
  Device: 10.0.0.126

Key Results:
  ✓ Maintenance Cycle: COMPLETED
  ✓ Deep Sleep: VERIFIED
  ✓ Wake-up Response: 45.3 seconds ← Only shown for full workflow
  
Status: SUCCESS
Duration: 92 minutes (1h 32m)
════════════════════════════════════════════════════════════
```

---

## **CSS Styles (Bootstrap Example)**

```css
.parameter-group.checkbox {
    margin-top: 15px;
    padding: 10px;
    background-color: #f8f9fa;
    border-left: 3px solid #007bff;
}

.parameter-group.checkbox input[type="checkbox"] {
    margin-right: 8px;
    cursor: pointer;
}

.parameter-group.checkbox label {
    cursor: pointer;
    font-weight: 500;
    margin: 0;
}

.help-text {
    display: block;
    margin-top: 8px;
    color: #6c757d;
    font-size: 0.875rem;
}

.toggle-switch {
    display: flex;
    align-items: center;
    margin: 10px 0;
}

.toggle-switch .toggle-label {
    display: inline-flex;
    background-color: #ddd;
    border-radius: 20px;
    padding: 2px;
    cursor: pointer;
    width: 100px;
}

.toggle-switch .toggle-on,
.toggle-switch .toggle-off {
    flex: 1;
    text-align: center;
    padding: 5px;
    font-size: 0.875rem;
    font-weight: bold;
}

.toggle-switch input:checked ~ .toggle-label .toggle-on {
    background-color: #28a745;
    color: white;
}

.toggle-switch input:not(:checked) ~ .toggle-label .toggle-off {
    background-color: #dc3545;
    color: white;
}

.duration-info {
    font-size: 0.875rem;
    color: #6c757d;
    margin-top: 5px;
}

.radio-option {
    margin: 15px 0;
    padding: 12px;
    border: 1px solid #dee2e6;
    border-radius: 5px;
    cursor: pointer;
}

.radio-option input[type="radio"] {
    margin-right: 10px;
    cursor: pointer;
}

.radio-option:hover {
    background-color: #f8f9fa;
}

.advanced-options {
    margin-top: 15px;
    padding: 10px;
    border: 1px solid #dee2e6;
    border-radius: 5px;
}

.advanced-options summary {
    cursor: pointer;
    font-weight: 500;
    padding: 5px;
}

.advanced-options summary:hover {
    background-color: #f8f9fa;
}

.details-content {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid #dee2e6;
}

.info-box {
    background-color: #e7f3ff;
    border-left: 4px solid #0066cc;
    padding: 10px;
    margin-bottom: 15px;
    border-radius: 3px;
    font-size: 0.9rem;
}

.default-badge {
    background-color: #0066cc;
    color: white;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.75rem;
    margin-left: 10px;
}
```

---

## **Summary**

Choose the UI option that best fits your dashboard:

| Option | Best For | Complexity |
|--------|----------|-----------|
| **Checkbox** | Simple, clean, familiar | Low |
| **Toggle Switch** | Modern, visual feedback | Medium |
| **Radio Buttons** | Explicit choice, detailed info | Medium |
| **Expandable Section** | Information-rich, advanced users | High |

**Recommended**: Start with **Option 1 (Checkbox)** for simplicity, upgrade to **Option 4 (Expandable)** for advanced features.

---

**Status**: Ready for UI Implementation  
**Parameter Name**: `execute_deepsleep_wakeup`  
**Default Value**: `true`  
**Required**: No
