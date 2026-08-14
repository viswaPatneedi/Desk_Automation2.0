/**
 * Lock Status Monitor - Displays real-time device lock status for running jobs
 * Usage: Include this script in job execution templates and call initLockStatusMonitor(jobId)
 */

class LockStatusMonitor {
    constructor(jobId, options = {}) {
        this.jobId = jobId;
        this.checkInterval = options.checkInterval || 30000; // Check every 30 seconds
        this.warningThreshold = options.warningThreshold || 600; // 10 minutes in seconds
        this.criticalThreshold = options.criticalThreshold || 300; // 5 minutes in seconds
        this.containerId = options.containerId || 'lock-status-indicator';
        this.onWarning = options.onWarning || null;
        this.onCritical = options.onCritical || null;
        this.onLostLock = options.onLostLock || null;
        
        this.monitorInterval = null;
        this.lastStatus = null;
    }
    
    /**
     * Start monitoring lock status
     */
    start() {
        console.log(`[LOCK-MONITOR] Starting lock status monitor for job ${this.jobId}`);
        
        // Initial check
        this.checkLockStatus();
        
        // Set up periodic checks
        this.monitorInterval = setInterval(() => this.checkLockStatus(), this.checkInterval);
    }
    
    /**
     * Stop monitoring lock status
     */
    stop() {
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
            console.log(`[LOCK-MONITOR] Stopped lock status monitor for job ${this.jobId}`);
        }
    }
    
    /**
     * Check current lock status from API
     */
    async checkLockStatus() {
        try {
            const response = await fetch(`/api/jobs/${this.jobId}/lock-status`);
            if (!response.ok) {
                console.warn(`[LOCK-MONITOR] API error: ${response.status}`);
                return;
            }
            
            const data = await response.json();
            if (!data.success) {
                console.warn(`[LOCK-MONITOR] API returned error: ${data.error}`);
                return;
            }
            
            this.updateDisplay(data);
            this.handleStatusChange(data);
        } catch (error) {
            console.error(`[LOCK-MONITOR] Error checking lock status: ${error}`);
        }
    }
    
    /**
     * Update UI display based on lock status
     */
    updateDisplay(status) {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.warn(`[LOCK-MONITOR] Container ${this.containerId} not found`);
            return;
        }
        
        if (!status.locked) {
            container.style.display = 'none';
            return;
        }
        
        // Device is locked - check if it's our lock
        if (!status.locked_by_job) {
            // Another job has the lock
            container.innerHTML = `
                <div class="alert alert-warning alert-dismissible fade show" role="alert">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <strong>Device Lock Info:</strong> Currently locked by another job
                    <small class="d-block mt-2">User: ${status.locked_by_user}</small>
                    <small>Lock expires: ${status.time_remaining_formatted}</small>
                </div>
            `;
            container.style.display = 'block';
            return;
        }
        
        // This job holds the lock
        let alertClass = 'alert-info';
        let icon = 'bi-lock';
        let warningMsg = '';
        
        if (status.critical) {
            alertClass = 'alert-danger';
            icon = 'bi-exclamation-circle-fill';
            warningMsg = '<strong style="color: #d32f2f;">[WARN] CRITICAL: Lock expires very soon!</strong><br>';
        } else if (status.warning) {
            alertClass = 'alert-warning';
            icon = 'bi-exclamation-triangle-fill';
            warningMsg = '<strong>[WARN] Warning: Lock expiring soon</strong><br>';
        }
        
        container.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert" style="margin-bottom: 1rem;">
                <i class="bi ${icon}" style="margin-right: 0.5rem;"></i>
                <div style="display: inline-block; vertical-align: middle;">
                    ${warningMsg}
                    <small>
                        <i class="bi bi-clock"></i>
                        Device lock time remaining: <strong>${status.time_remaining_formatted}</strong>
                    </small>
                    <br>
                    <small style="color: #666;">
                        Expires at: ${status.estimated_completion}
                    </small>
                </div>
                ${status.critical ? `
                    <div style="margin-top: 0.5rem;">
                        <button class="btn btn-sm btn-primary" onclick="extendJobLock('${this.jobId}')">
                            <i class="bi bi-arrow-clockwise"></i> Extend Lock
                        </button>
                    </div>
                ` : ''}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        container.style.display = 'block';
    }
    
    /**
     * Handle status changes (warnings, critical, lost lock)
     */
    handleStatusChange(status) {
        // Check if lock was lost
        if (this.lastStatus && this.lastStatus.locked && !status.locked) {
            console.error(`[LOCK-MONITOR] CRITICAL: Device lock lost for job ${this.jobId}!`);
            if (this.onLostLock) {
                this.onLostLock(status);
            }
            this.showNotification('Device Lock Lost', 'ERROR', 'Device lock was lost during job execution!');
        }
        
        // Check if transitioned to critical
        if ((!this.lastStatus || !this.lastStatus.critical) && status.critical) {
            console.warn(`[LOCK-MONITOR] CRITICAL lock threshold reached for job ${this.jobId}`);
            if (this.onCritical) {
                this.onCritical(status);
            }
            this.showNotification('Lock Expiring Soon', 'WARNING', `Device lock will expire in ${status.time_remaining_formatted}`);
        }
        
        // Check if transitioned to warning
        if ((!this.lastStatus || !this.lastStatus.warning) && status.warning && !status.critical) {
            console.warn(`[LOCK-MONITOR] WARNING lock threshold reached for job ${this.jobId}`);
            if (this.onWarning) {
                this.onWarning(status);
            }
        }
        
        this.lastStatus = status;
    }
    
    /**
     * Show browser notification
     */
    showNotification(title, type, message) {
        // Try browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: type === 'ERROR' ? '[BLOCKED]' : '[WARN]'
            });
        }
        
        // Console log
        console.log(`[LOCK-MONITOR] ${type}: ${message}`);
    }
}

/**
 * Initialize lock status monitor for a job
 */
function initLockStatusMonitor(jobId, options = {}) {
    const monitor = new LockStatusMonitor(jobId, options);
    monitor.start();
    
    // Store reference globally for access
    window.lockStatusMonitors = window.lockStatusMonitors || {};
    window.lockStatusMonitors[jobId] = monitor;
    
    return monitor;
}

/**
 * Stop lock status monitor for a job
 */
function stopLockStatusMonitor(jobId) {
    if (window.lockStatusMonitors && window.lockStatusMonitors[jobId]) {
        window.lockStatusMonitors[jobId].stop();
        delete window.lockStatusMonitors[jobId];
    }
}

/**
 * Request permission for browser notifications (call once on page load)
 */
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

/**
 * Extend device lock for a job (stub - implement based on your backend)
 */
async function extendJobLock(jobId) {
    console.log(`[LOCK-EXTEND] Requesting lock extension for job ${jobId}`);
    
    try {
        // TODO: Implement lock extension endpoint
        const response = await fetch(`/api/jobs/${jobId}/extend-lock`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`[OK] Lock extended until: ${data.new_expiration}`);
            // Refresh lock status display
            if (window.lockStatusMonitors && window.lockStatusMonitors[jobId]) {
                window.lockStatusMonitors[jobId].checkLockStatus();
            }
        } else {
            alert(`[ERROR] Failed to extend lock: ${data.error}`);
        }
    } catch (error) {
        alert(`[ERROR] Error extending lock: ${error}`);
    }
}

/**
 * Get current lock status for a job
 */
async function getJobLockStatus(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/lock-status`);
        return await response.json();
    } catch (error) {
        console.error(`[LOCK-MONITOR] Error fetching lock status: ${error}`);
        return null;
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        LockStatusMonitor,
        initLockStatusMonitor,
        stopLockStatusMonitor,
        requestNotificationPermission,
        extendJobLock,
        getJobLockStatus
    };
}
