// ============================================================================
// Android eBPF Profiler - Frontend JavaScript
// ============================================================================

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = 'http://localhost:5000/api';
const REFRESH_INTERVAL = 5000;

// State management
const state = {
    selectedDevice: null,
    devices: [],
    activeTraces: [],
    completedTraces: [],
    scripts: [],
    refreshTimer: null
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Android eBPF Profiler loaded');
    initializeApp();
});

function initializeApp() {
    console.log('Initializing app...');
    
    // Delay slightly to ensure DOM is fully ready
    setTimeout(() => {
        console.log('Starting app initialization...');
        setupNavigation();
        checkBackendHealth();
        refreshDevices();
        loadScripts();
        setupAutoRefresh();
        console.log('App initialized successfully');
    }, 100);
}

// ============================================================================
// Navigation & Section Management
// ============================================================================

function setupNavigation() {
    // Activate first nav item
    const navItems = document.querySelectorAll('.nav-item');
    if (navItems.length > 0) {
        navItems[0].classList.add('active');
    }
}

function switchSection(sectionId) {
    // Hide all sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => section.classList.remove('active'));
    
    // Show selected section
    const selectedSection = document.getElementById(`section-${sectionId}`);
    if (selectedSection) {
        selectedSection.classList.add('active');
    }
    
    // Update nav items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => item.classList.remove('active'));
    
    const activeNav = document.querySelector(`[onclick*="${sectionId}"]`);
    if (activeNav) {
        activeNav.classList.add('active');
    }
}

// ============================================================================
// API Communication
// ============================================================================

async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };
        
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: response.statusText }));
            throw new Error(error.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        showToast(`Error: ${error.message}`, 'error');
        throw error;
    }
}

async function checkBackendHealth() {
    try {
        const response = await apiCall('/health');
        console.log('✅ Backend is healthy:', response);
    } catch (error) {
        console.error('❌ Backend health check failed');
        showToast('Backend is not responding', 'error');
    }
}

// ============================================================================
// Device Management
// ============================================================================

async function refreshDevices() {
    try {
        showToast('Refreshing devices...', 'info');
        const response = await apiCall('/devices');
        state.devices = response.devices || [];
        
        console.log('📱 Devices:', state.devices);
        renderDevices();
        
        if (state.devices.length > 0) {
            showToast(`Found ${state.devices.length} device(s)`, 'success');
        } else {
            showToast('No devices connected', 'warning');
        }
    } catch (error) {
        console.error('Error refreshing devices:', error);
    }
}

function renderDevices() {
    const container = document.getElementById('devices-container');
    
    if (state.devices.length === 0) {
        container.innerHTML = `
            <div class="loading">
                📱 No devices connected. Please connect an Android device via ADB.
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.devices.map(device => `
        <div class="device-card ${state.selectedDevice?.device_id === device.device_id ? 'selected' : ''}" 
             onclick="selectDevice('${device.device_id}')">
            <div class="device-card-header">
                <div class="device-name">📱 ${device.model || 'Unknown Device'}</div>
                <span class="device-status ${device.state}">
                    ${device.state === 'device' ? '🟢 Connected' : '🔴 ' + device.state}
                </span>
            </div>
            <div class="device-info">
                <strong>ID:</strong> ${device.device_id}
            </div>
            <div class="device-info">
                <strong>Device:</strong> ${device.device_name || 'N/A'}
            </div>
            <div class="device-info">
                <strong>API Level:</strong> ${device.api_level || 'N/A'}
            </div>
            <div class="device-info">
                <strong>Kernel:</strong> ${device.kernel_version || 'N/A'}
            </div>
            ${device.state === 'device' ? `
                <div class="device-capabilities">
                    <div class="capability">
                        <span class="capability-status ${device.ebpf_supported ? 'ok' : 'fail'}"></span>
                        <span>eBPF Support: ${device.ebpf_supported ? 'Yes ✓' : 'No ✗'}</span>
                    </div>
                    <div class="capability">
                        <span class="capability-status ${device.root_access ? 'ok' : 'fail'}"></span>
                        <span>Root Access: ${device.root_access ? 'Yes ✓' : 'No ✗'}</span>
                    </div>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function selectDevice(deviceId) {
    const device = state.devices.find(d => d.device_id === deviceId);
    if (device && device.state !== 'device') {
        showToast('Device is not connected', 'error');
        return;
    }
    
    state.selectedDevice = device;
    renderDevices();
    showTracingSection();
    loadDeviceCapabilities(deviceId);
    showToast(`Selected device: ${device?.model || deviceId}`, 'success');
}

async function loadDeviceCapabilities(deviceId) {
    try {
        const response = await apiCall(`/devices/${deviceId}/info`);
        renderDeviceCapabilities(response);
    } catch (error) {
        console.error('Error loading capabilities:', error);
    }
}

function renderDeviceCapabilities(device) {
    const container = document.getElementById('capabilities-container');
    const section = document.getElementById('capabilities-section');
    
    const html = `
        <div class="capabilities-table">
            <div class="capability-card">
                <div class="capability-icon">🔗</div>
                <div class="capability-info">
                    <h4>Connection Status</h4>
                    <p>${device.state === 'device' ? '✅ Connected' : '❌ ' + device.state}</p>
                </div>
            </div>
            <div class="capability-card">
                <div class="capability-icon">⚙️</div>
                <div class="capability-info">
                    <h4>eBPF Support</h4>
                    <p>${device.ebpf_supported ? '✅ Supported' : '❌ Not supported'}</p>
                </div>
            </div>
            <div class="capability-card">
                <div class="capability-icon">🔐</div>
                <div class="capability-info">
                    <h4>Root Access</h4>
                    <p>${device.root_access ? '✅ Available' : '❌ Not available'}</p>
                </div>
            </div>
            <div class="capability-card">
                <div class="capability-icon">📱</div>
                <div class="capability-info">
                    <h4>Model</h4>
                    <p>${device.model || 'Unknown'}</p>
                </div>
            </div>
            <div class="capability-card">
                <div class="capability-icon">🖥️</div>
                <div class="capability-info">
                    <h4>API Level</h4>
                    <p>${device.api_level || 'Unknown'}</p>
                </div>
            </div>
            <div class="capability-card">
                <div class="capability-icon">💾</div>
                <div class="capability-info">
                    <h4>Kernel</h4>
                    <p>${device.kernel_version || 'Unknown'}</p>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    section.style.display = 'block';
}

// ============================================================================
// Tracing Control
// ============================================================================

function showTracingSection() {
    document.getElementById('tracing-section').style.display = 'block';
    document.getElementById('active-traces-section').style.display = 'block';
    document.getElementById('results-section').style.display = 'block';
}

async function loadScripts() {
    try {
        const response = await apiCall('/scripts');
        state.scripts = response.scripts || [];
        
        const select = document.getElementById('custom-script');
        if (!select) return; // Element might not exist yet
        
        select.innerHTML = state.scripts.map(script => `
            <option value="${script.name}">${script.name}</option>
        `).join('');
        
        if (state.scripts.length === 0) {
            select.innerHTML = '<option value="">No scripts available</option>';
        }
        
        renderAvailableScripts();
    } catch (error) {
        console.error('Error loading scripts:', error);
        // Don't crash - scripts are optional
    }
}

// ============================================================================
// Custom Script Management
// ============================================================================

function saveCustomScript() {
    const name = document.getElementById('script-name').value.trim();
    const content = document.getElementById('script-content').value.trim();
    
    if (!name) {
        showToast('Script name is required', 'error');
        return;
    }
    
    if (!content) {
        showToast('Script content is required', 'error');
        return;
    }
    
    if (name.length < 3) {
        showToast('Script name must be at least 3 characters', 'error');
        return;
    }
    
    // Save to localStorage for now (backend can save to server later)
    const customScripts = JSON.parse(localStorage.getItem('ebpf_custom_scripts') || '{}');
    customScripts[name] = {
        name: name,
        content: content,
        created: new Date().toISOString(),
        type: 'custom'
    };
    
    localStorage.setItem('ebpf_custom_scripts', JSON.stringify(customScripts));
    
    // Update state
    state.scripts.push({ name: name, type: 'custom' });
    
    // Clear form
    document.getElementById('script-name').value = '';
    document.getElementById('script-content').value = '';
    
    showToast(`✅ Script "${name}" saved successfully!`, 'success');
    renderAvailableScripts();
    loadScripts();
}

function renderAvailableScripts() {
    const container = document.getElementById('scripts-container');
    const customScripts = JSON.parse(localStorage.getItem('ebpf_custom_scripts') || '{}');
    
    const scripts = Object.values(customScripts);
    
    if (scripts.length === 0) {
        container.innerHTML = '<p class="no-results">No custom scripts yet. Create one above!</p>';
        return;
    }
    
    container.innerHTML = scripts.map(script => `
        <div class="script-card">
            <div class="script-header">
                <h4>${script.name}</h4>
                <small>${new Date(script.created).toLocaleDateString()}</small>
            </div>
            <div class="script-actions">
                <button class="btn btn-primary btn-sm" onclick="editCustomScript('${script.name}')">✏️ Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteCustomScript('${script.name}')">🗑️ Delete</button>
            </div>
        </div>
    `).join('');
}

function editCustomScript(name) {
    const customScripts = JSON.parse(localStorage.getItem('ebpf_custom_scripts') || '{}');
    const script = customScripts[name];
    
    if (script) {
        document.getElementById('script-name').value = script.name;
        document.getElementById('script-content').value = script.content;
        switchSection('scripts');
        showToast('Script loaded for editing', 'info');
    }
}

function deleteCustomScript(name) {
    if (!confirm(`Delete script "${name}"?`)) return;
    
    const customScripts = JSON.parse(localStorage.getItem('ebpf_custom_scripts') || '{}');
    delete customScripts[name];
    localStorage.setItem('ebpf_custom_scripts', JSON.stringify(customScripts));
    
    state.scripts = state.scripts.filter(s => s.name !== name);
    renderAvailableScripts();
    loadScripts();
    showToast(`Script "${name}" deleted`, 'success');
}

async function startSyscallTrace() {
    if (!validateDeviceSelected()) return;
    
    const duration = parseInt(document.getElementById('syscall-duration').value);
    const processName = document.getElementById('syscall-process').value;
    
    if (duration < 1 || duration > 300) {
        showToast('Duration must be between 1 and 300 seconds', 'error');
        return;
    }
    
    await executeTrace('syscall', {
        device_id: state.selectedDevice.device_id,
        duration: duration,
        process_name: processName
    });
}

async function startFileAccessTrace() {
    if (!validateDeviceSelected()) return;
    
    const duration = parseInt(document.getElementById('fileaccess-duration').value);
    
    if (duration < 1 || duration > 300) {
        showToast('Duration must be between 1 and 300 seconds', 'error');
        return;
    }
    
    await executeTrace('file-access', {
        device_id: state.selectedDevice.device_id,
        duration: duration
    });
}

async function startMemoryTrace() {
    if (!validateDeviceSelected()) return;
    
    const duration = parseInt(document.getElementById('memory-duration').value);
    
    if (duration < 1 || duration > 300) {
        showToast('Duration must be between 1 and 300 seconds', 'error');
        return;
    }
    
    await executeTrace('memory', {
        device_id: state.selectedDevice.device_id,
        duration: duration
    });
}

async function startCustomTrace() {
    if (!validateDeviceSelected()) return;
    
    const scriptName = document.getElementById('custom-script').value;
    const duration = parseInt(document.getElementById('custom-duration').value);
    
    if (!scriptName) {
        showToast('Please select a script', 'error');
        return;
    }
    
    if (duration < 1 || duration > 300) {
        showToast('Duration must be between 1 and 300 seconds', 'error');
        return;
    }
    
    await executeTrace('custom', {
        device_id: state.selectedDevice.device_id,
        script_name: scriptName,
        trace_name: `custom_${Date.now()}`,
        duration: duration
    });
}

async function executeTrace(traceType, params) {
    try {
        showToast(`Starting ${traceType} trace...`, 'info');
        
        const endpoint = `/traces/${traceType}`;
        const response = await apiCall(endpoint, {
            method: 'POST',
            body: JSON.stringify(params)
        });
        
        if (response.success) {
            showToast(`✅ Trace started successfully!`, 'success');
            
            // Add to active traces
            state.activeTraces.push({
                trace_id: response.trace_id,
                trace_name: response.trace_name,
                device_id: response.device_id,
                status: 'running',
                start_time: new Date().toISOString(),
                duration: params.duration
            });
            
            renderActiveTraces();
            
            // Monitor trace completion
            monitorTraceCompletion(response.trace_id, params.duration);
        } else {
            showToast(`Error: ${response.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error executing trace:', error);
    }
}

function monitorTraceCompletion(traceId, duration) {
    const monitoringInterval = setInterval(async () => {
        try {
            const response = await apiCall(`/traces/${traceId}`);
            
            if (response.status === 'completed') {
                clearInterval(monitoringInterval);
                
                // Move from active to completed
                state.activeTraces = state.activeTraces.filter(t => t.trace_id !== traceId);
                state.completedTraces.push({
                    ...response,
                    status: 'completed',
                    end_time: new Date().toISOString()
                });
                
                renderActiveTraces();
                showToast(`✅ Trace ${response.trace_name} completed!`, 'success');
                displayTraceResult(response.trace_id);
            }
        } catch (error) {
            console.error('Error monitoring trace:', error);
            clearInterval(monitoringInterval);
        }
    }, 2000);
    
    // Timeout after duration + 10 seconds
    setTimeout(() => clearInterval(monitoringInterval), (duration + 10) * 1000);
}

function renderActiveTraces() {
    const container = document.getElementById('active-traces-container');
    
    if (state.activeTraces.length === 0) {
        container.innerHTML = '<p class="no-traces">No active traces</p>';
        return;
    }
    
    container.innerHTML = state.activeTraces.map(trace => `
        <div class="trace-item">
            <div class="trace-info">
                <div class="trace-name">📊 ${trace.trace_name}</div>
                <div class="trace-meta">
                    Device: ${trace.device_id} | Status: <span class="spinner"></span> Running
                </div>
            </div>
            <div class="trace-actions">
                <button class="btn btn-secondary btn-sm" onclick="stopTrace('${trace.trace_id}')">⏹ Stop</button>
            </div>
        </div>
    `).join('');
}

async function displayTraceResult(traceId) {
    try {
        const trace = await apiCall(`/traces/${traceId}`);
        const summary = await apiCall(`/traces/${traceId}/summary`);
        const stats = await apiCall(`/traces/${traceId}/stats`);
        
        const container = document.getElementById('results-container');
        const resultHtml = `
            <div class="result-card fade-enter">
                <div class="result-header">
                    <div class="result-title">📈 ${trace.trace_name}</div>
                    <small>${new Date().toLocaleString()}</small>
                </div>
                <div class="result-stats">
                    <div class="stat">
                        <div class="stat-value">${summary.total_events || 0}</div>
                        <div class="stat-label">Total Events</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${summary.unique_pids || 0}</div>
                        <div class="stat-label">Processes</div>
                    </div>
                </div>
                <div class="result-summary">
                    <strong>Summary:</strong><br>
                    Event Types: ${Object.keys(summary.event_types || {}).length}<br>
                    Unique Processes: ${summary.unique_pids || 0}<br>
                    Unique Commands: ${summary.unique_comms || 0}
                </div>
                <div class="result-actions">
                    <button class="btn btn-primary btn-sm" onclick="downloadTrace('${traceId}')">⬇️ Download</button>
                    <button class="btn btn-secondary btn-sm" onclick="viewTraceDetails('${traceId}')">👁️ View Details</button>
                </div>
            </div>
        `;
        
        // Prepend to results
        const existingContent = container.innerHTML;
        if (existingContent.includes('no-results')) {
            container.innerHTML = resultHtml;
        } else {
            container.innerHTML = resultHtml + existingContent;
        }
    } catch (error) {
        console.error('Error displaying trace result:', error);
    }
}

async function downloadTrace(traceId) {
    try {
        showToast('Downloading trace...', 'info');
        const response = await fetch(`${API_BASE_URL}/traces/${traceId}/download`);
        
        if (!response.ok) {
            showToast('Download failed', 'error');
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `trace_${traceId}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast('Download complete!', 'success');
    } catch (error) {
        console.error('Error downloading trace:', error);
        showToast('Download failed', 'error');
    }
}

async function viewTraceDetails(traceId) {
    try {
        showToast('Loading details...', 'info');
        const stats = await apiCall(`/traces/${traceId}/stats`);
        
        // Create a detailed view modal or new window
        const detailsText = JSON.stringify(stats, null, 2);
        console.log('📊 Trace Statistics:', stats);
        showToast('Check console for detailed statistics', 'info');
    } catch (error) {
        console.error('Error viewing trace details:', error);
    }
}

function stopTrace(traceId) {
    // This would require backend support
    showToast('Stop trace not yet implemented', 'warning');
}

function validateDeviceSelected() {
    if (!state.selectedDevice) {
        showToast('Please select a device first', 'error');
        return false;
    }
    if (state.selectedDevice.state !== 'device') {
        showToast('Selected device is not connected', 'error');
        return false;
    }
    return true;
}

// ============================================================================
// UI Utilities
// ============================================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

function clearResults() {
    const container = document.getElementById('results-container');
    container.innerHTML = '<div class="no-results">No trace results yet</div>';
    state.completedTraces = [];
    showToast('Results cleared', 'info');
}

// ============================================================================
// Auto-refresh Setup
// ============================================================================

function setupAutoRefresh() {
    state.refreshTimer = setInterval(() => {
        if (state.selectedDevice) {
            loadDeviceCapabilities(state.selectedDevice.device_id);
        }
    }, REFRESH_INTERVAL);
}

// ============================================================================
// Input Validation Functions
// ============================================================================

function validateDeviceId(deviceId) {
    return typeof deviceId === 'string' && deviceId.trim().length > 0;
}

function validateDuration(duration) {
    const num = parseFloat(duration);
    return !isNaN(num) && num >= 1 && num <= 300;
}

function validateTraceName(name) {
    return typeof name === 'string' && name.trim().length > 0;
}

// ============================================================================
// Event Listeners and Exports
// ============================================================================

window.addEventListener('beforeunload', () => {
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
    }
});

// Expose functions to global scope for onclick handlers
window.refreshDevices = refreshDevices;
window.selectDevice = selectDevice;
window.startSyscallTrace = startSyscallTrace;
window.startFileAccessTrace = startFileAccessTrace;
window.startMemoryTrace = startMemoryTrace;
window.startCustomTrace = startCustomTrace;
window.downloadTrace = downloadTrace;
window.viewTraceDetails = viewTraceDetails;
window.stopTrace = stopTrace;
window.clearResults = clearResults;
window.validateDeviceId = validateDeviceId;
window.validateDuration = validateDuration;
window.validateTraceName = validateTraceName;
window.switchSection = switchSection;
window.saveCustomScript = saveCustomScript;
window.editCustomScript = editCustomScript;
window.deleteCustomScript = deleteCustomScript;
window.renderAvailableScripts = renderAvailableScripts;

console.log('✅ Frontend JavaScript loaded and ready');
