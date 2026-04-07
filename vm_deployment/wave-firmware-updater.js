(function () {
    'use strict';

    const waveState = {
        devices: [],
        taskId: null,
        taskStream: null,
        taskPollInterval: null,
        isProcessing: false,
        initComplete: false,
        fileId: null,
        fileName: null
    };

    let waveApiOverride = null;

    function waveGetUsername() {
        if (typeof getUsername === 'function') return getUsername();
        if (window.currentUser && typeof window.currentUser === 'string') return window.currentUser;
        if (window.currentUser && typeof window.currentUser === 'object') {
            return window.currentUser.username || window.currentUser.email || '';
        }
        return '';
    }

    function waveEscapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getApiRoot() {
        return ((typeof AI_API_BASE !== 'undefined' ? AI_API_BASE : window.AI_API_BASE) || '/api').replace(/\/+$/, '');
    }

    function getWaveApiBase() {
        if (waveApiOverride) return waveApiOverride;
        return `${getApiRoot()}/wave-fw`;
    }

    function getWaveCandidateBases() {
        const bases = [];
        const originBase = `${window.location.origin}/api/wave-fw`;
        const apiBase = getWaveApiBase();
        const isFile = window.location.protocol === 'file:' || window.location.origin === 'null';
        bases.push(originBase);
        if (apiBase && apiBase !== originBase) bases.push(apiBase);
        if (isFile) bases.push('http://localhost:5000/api/wave-fw');
        return Array.from(new Set(bases.filter(Boolean)));
    }

    async function waveFetch(path, options) {
        const bases = getWaveCandidateBases();
        let lastError = null;
        for (const base of bases) {
            try {
                const response = await fetch(`${base}${path}`, options);
                if (response.ok) waveApiOverride = base;
                if (![403, 404, 405].includes(response.status) || base === bases[bases.length - 1]) {
                    return response;
                }
            } catch (err) {
                lastError = err;
            }
        }
        throw lastError || new Error('Wave FW API unavailable');
    }

    async function parseJson(response) {
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            return { error: `Unexpected response (${response.status})` };
        }
        try {
            return await response.json();
        } catch (err) {
            return { error: `Invalid JSON response (${response.status})` };
        }
    }

    function normalizeStatus(status) {
        if (!status) return 'pending';
        const lower = String(status).toLowerCase();
        if (['completed', 'done', 'ok'].includes(lower)) return 'success';
        if (['failed', 'fail'].includes(lower)) return 'error';
        if (lower === 'running') return 'processing';
        return lower;
    }

    function statusIcon(status) {
        return {
            pending: '.',
            processing: '~',
            verifying: 'V',
            success: 'OK',
            error: 'X',
            aborted: 'A'
        }[status] || '?';
    }

    // ── Log helpers ──────────────────────────────────────────────────────────

    const _recentLogKeys = new Set();
    function addLog(message, type = 'info', meta = {}) {
        const logBox = document.getElementById('waveFwLogBox');
        if (!logBox) return;
        const dedupeKey = `${type}:${message}`;
        if (_recentLogKeys.has(dedupeKey)) return;
        _recentLogKeys.add(dedupeKey);
        setTimeout(() => _recentLogKeys.delete(dedupeKey), 500);
        const date = meta && meta.ts ? new Date(meta.ts) : new Date();
        const time = Number.isNaN(date.getTime()) ? '--:--:--' : date.toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `aviat-log-entry log-${type}`;
        entry.innerHTML = `<span class="aviat-log-time">[${time}]</span> ${waveEscapeHtml(message)}`;
        logBox.appendChild(entry);
        logBox.scrollTop = logBox.scrollHeight;
    }

    function clearLog() {
        const logBox = document.getElementById('waveFwLogBox');
        if (!logBox) return;
        logBox.innerHTML = '<div class="aviat-log-entry"><span class="aviat-log-time">[--:--:--]</span> Log cleared.</div>';
    }

    // ── UI state ─────────────────────────────────────────────────────────────

    function syncInteractiveState() {
        const disabled = waveState.isProcessing;
        [
            'waveFwDiscoverBtn',
            'waveFwUploadBtn',
            'waveFwFileInput',
            'waveFwSelectAllBtn',
            'waveFwDeselectAllBtn'
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = disabled;
        });
    }

    function setRunState(isProcessing) {
        waveState.isProcessing = !!isProcessing;
        const runBtn = document.getElementById('waveFwRunBtn');
        const abortBtn = document.getElementById('waveFwAbortBtn');
        if (runBtn) runBtn.disabled = waveState.isProcessing;
        if (abortBtn) {
            abortBtn.disabled = !waveState.isProcessing;
            abortBtn.title = waveState.isProcessing
                ? 'Request abort for the current Wave FW task.'
                : 'No Wave FW task is currently running.';
        }
        syncInteractiveState();
        updateDeviceList();
    }

    function updateStats() {
        const statsBar = document.getElementById('waveFwStatsBar');
        if (!statsBar) return;
        if (waveState.devices.length === 0) {
            statsBar.style.display = 'none';
            return;
        }
        statsBar.style.display = 'flex';
        const total = waveState.devices.length;
        const pending = waveState.devices.filter(d => normalizeStatus(d.status) === 'pending').length;
        const processing = waveState.devices.filter(d => normalizeStatus(d.status) === 'processing').length;
        const success = waveState.devices.filter(d => normalizeStatus(d.status) === 'success').length;
        const error = waveState.devices.filter(d => normalizeStatus(d.status) === 'error').length;
        const statTotal = document.getElementById('waveFwStatTotal');
        const statPending = document.getElementById('waveFwStatPending');
        const statProcessing = document.getElementById('waveFwStatProcessing');
        const statSuccess = document.getElementById('waveFwStatSuccess');
        const statError = document.getElementById('waveFwStatError');
        if (statTotal) statTotal.textContent = total;
        if (statPending) statPending.textContent = pending;
        if (statProcessing) statProcessing.textContent = processing;
        if (statSuccess) statSuccess.textContent = success;
        if (statError) statError.textContent = error;
    }

    function updateDeviceList() {
        const listCard = document.getElementById('waveFwDeviceListCard');
        const list = document.getElementById('waveFwDeviceList');
        if (!listCard || !list) return;

        if (waveState.devices.length === 0) {
            listCard.style.display = 'none';
            return;
        }
        listCard.style.display = 'block';
        updateStats();

        list.innerHTML = waveState.devices.map(device => {
            const status = normalizeStatus(device.status);
            const ip = waveEscapeHtml(device.ip || '');
            const name = waveEscapeHtml(device.name || device.hostname || device.ip || '');
            const model = waveEscapeHtml(device.model || device.device_type || '');
            const version = waveEscapeHtml(device.version || device.current_version || '');
            const targetVersion = waveEscapeHtml(device.target_version || '');
            const activeBank = waveEscapeHtml(device.active_bank || '');
            const backupBank = waveEscapeHtml(device.backup_bank || '');
            const detail = device.detail ? `<div style="margin-top:6px;color:var(--text-color-secondary);font-size:12px;">${waveEscapeHtml(device.detail)}</div>` : '';
            const checked = device.selected !== false ? 'checked' : '';
            return `
                <div class="aviat-queue-item">
                    <div style="display:flex;align-items:flex-start;gap:10px;">
                        <input type="checkbox" class="wave-fw-device-checkbox" data-ip="${ip}"
                            ${checked} ${waveState.isProcessing ? 'disabled' : ''}
                            onchange="waveFwToggleDevice('${ip}', this.checked)">
                        <div>
                            <span class="aviat-status-badge ${status}">${statusIcon(status)}</span>
                            <strong>${name}</strong>
                            ${ip !== name ? `<span style="color:var(--text-color-secondary);font-size:12px;"> (${ip})</span>` : ''}
                            <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">
                                ${model ? `<span class="aviat-pill">${model}</span>` : ''}
                                ${version ? `<span class="aviat-pill">Current: ${version}</span>` : ''}
                                ${targetVersion ? `<span class="aviat-pill">Target: ${targetVersion}</span>` : ''}
                                ${activeBank ? `<span class="aviat-pill">Active: ${activeBank}</span>` : ''}
                                ${backupBank ? `<span class="aviat-pill">Backup: ${backupBank}</span>` : ''}
                            </div>
                            ${detail}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    window.waveFwToggleDevice = function (ip, checked) {
        const device = waveState.devices.find(d => d.ip === ip);
        if (device) device.selected = checked;
    };

    // ── Discover ─────────────────────────────────────────────────────────────

    async function discoverDevices() {
        if (waveState.isProcessing) return;
        addLog('Querying UISP for Wave devices...', 'info');
        const discoverBtn = document.getElementById('waveFwDiscoverBtn');
        if (discoverBtn) discoverBtn.disabled = true;
        try {
            const response = await waveFetch('/discover', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ requested_by: waveGetUsername() })
            });
            const data = await parseJson(response);
            if (!response.ok) throw new Error(data.error || `Discover failed (${response.status})`);
            const devices = Array.isArray(data.devices) ? data.devices : [];
            waveState.devices = devices.map(d => ({ ...d, selected: true, status: d.status || 'pending' }));
            updateDeviceList();
            addLog(`Discovered ${devices.length} Wave device(s)`, 'info');
            if (devices.length === 0) addLog('No Wave devices found. Check UISP credentials and connectivity.', 'warning');
        } catch (err) {
            addLog(`Discover failed: ${err.message}`, 'error');
        } finally {
            if (discoverBtn && !waveState.isProcessing) discoverBtn.disabled = false;
        }
    }

    // ── File upload ───────────────────────────────────────────────────────────

    function updateFileBadge() {
        const badge = document.getElementById('waveFwFileBadge');
        if (!badge) return;
        if (waveState.fileId && waveState.fileName) {
            badge.textContent = waveState.fileName;
            badge.style.display = '';
        } else {
            badge.textContent = '';
            badge.style.display = 'none';
        }
    }

    async function uploadFirmwareFile() {
        const input = document.getElementById('waveFwFileInput');
        if (!input || !input.files || input.files.length === 0) {
            addLog('Select a firmware .bin file first.', 'warning');
            return;
        }
        const file = input.files[0];
        if (!file.name.toLowerCase().endsWith('.bin')) {
            addLog('Firmware file must be a .bin file.', 'warning');
            return;
        }
        addLog(`Uploading ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)...`, 'info');
        const uploadBtn = document.getElementById('waveFwUploadBtn');
        if (uploadBtn) uploadBtn.disabled = true;
        waveState.fileId = null;
        waveState.fileName = null;
        updateFileBadge();
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('requested_by', waveGetUsername());
            const bases = getWaveCandidateBases();
            let response = null;
            let lastError = null;
            for (const base of bases) {
                try {
                    response = await fetch(`${base}/upload`, { method: 'POST', body: formData });
                    if (response.ok || ![403, 404, 405].includes(response.status)) {
                        waveApiOverride = base;
                        break;
                    }
                } catch (err) {
                    lastError = err;
                }
            }
            if (!response) throw lastError || new Error('Upload endpoint unavailable');
            const data = await parseJson(response);
            if (!response.ok) throw new Error(data.error || `Upload failed (${response.status})`);
            waveState.fileId = data.file_id;
            waveState.fileName = file.name;
            updateFileBadge();
            addLog(`Firmware uploaded successfully: ${file.name} (ID: ${data.file_id})`, 'success');
        } catch (err) {
            addLog(`Upload failed: ${err.message}`, 'error');
        } finally {
            if (uploadBtn && !waveState.isProcessing) uploadBtn.disabled = false;
        }
    }

    // ── Run / Abort ───────────────────────────────────────────────────────────

    async function runUpgrade() {
        if (waveState.isProcessing) return;
        if (!waveState.fileId) {
            addLog('Upload a firmware file before running the upgrade.', 'warning');
            return;
        }
        const selectedDevices = waveState.devices.filter(d => d.selected !== false);
        if (selectedDevices.length === 0) {
            addLog('Select at least one device to upgrade.', 'warning');
            return;
        }
        const deviceIds = selectedDevices.map(d => d.ip || d.id).filter(Boolean);
        addLog(`Starting Wave FW upgrade for ${deviceIds.length} device(s)...`, 'info');

        waveState.taskId = null;
        setRunState(true);
        selectedDevices.forEach(d => { d.status = 'processing'; d.detail = 'Queued'; });
        updateDeviceList();

        try {
            const response = await waveFetch('/upgrade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: waveState.fileId,
                    device_ids: deviceIds,
                    requested_by: waveGetUsername()
                })
            });
            const data = await parseJson(response);
            if (!response.ok) throw new Error(data.error || `Upgrade failed (${response.status})`);
            waveState.taskId = data.task_id || data.taskId || null;
            if (waveState.taskId) {
                monitorTask(waveState.taskId);
            } else {
                setRunState(false);
            }
        } catch (err) {
            selectedDevices.forEach(d => { d.status = 'error'; d.detail = err.message; });
            updateDeviceList();
            setRunState(false);
            addLog(`Upgrade failed: ${err.message}`, 'error');
        }
    }

    async function abortCurrentTask() {
        if (!waveState.taskId) {
            addLog('No active Wave FW task to abort.', 'warning');
            return;
        }
        try {
            const response = await waveFetch(`/abort/${encodeURIComponent(waveState.taskId)}`, { method: 'POST' });
            const data = await parseJson(response);
            if (!response.ok) throw new Error(data.error || `Abort failed (${response.status})`);
            addLog('Wave FW abort requested', 'warning');
            const abortBtn = document.getElementById('waveFwAbortBtn');
            if (abortBtn) abortBtn.disabled = true;
        } catch (err) {
            addLog(`Wave FW abort failed: ${err.message}`, 'error');
        }
    }

    // ── Task monitoring ───────────────────────────────────────────────────────

    function applyEventPayload(payload) {
        if (!payload) return;
        if (payload.message) addLog(payload.message, payload.level || 'info', { ts: payload.ts });
        if (Array.isArray(payload.results)) {
            payload.results.forEach(r => {
                const device = waveState.devices.find(d => d.ip === (r.ip || r.host));
                if (device) Object.assign(device, r);
            });
            updateDeviceList();
        }
        if (payload.device || payload.result) {
            const r = payload.device || payload.result;
            const device = waveState.devices.find(d => d.ip === (r.ip || r.host));
            if (device) Object.assign(device, r);
            updateDeviceList();
        }
    }

    function startTaskStream(taskId) {
        if (waveState.taskStream) {
            try { waveState.taskStream.close(); } catch (err) {}
        }
        if (typeof EventSource === 'undefined') return;
        let eventSource;
        // SSE stream endpoint uses token auth via query param
        try {
            const token = window._nexusAuthToken || (typeof getAuthToken === 'function' ? getAuthToken() : '');
            const streamUrl = token
                ? `${getWaveApiBase()}/stream/${encodeURIComponent(taskId)}?token=${encodeURIComponent(token)}`
                : `${getWaveApiBase()}/stream/${encodeURIComponent(taskId)}`;
            eventSource = new EventSource(streamUrl);
        } catch (err) {
            addLog(`Wave FW stream failed to start: ${err.message}`, 'warning');
            return;
        }
        waveState.taskStream = eventSource;
        eventSource.onmessage = function (event) {
            try {
                applyEventPayload(JSON.parse(event.data));
            } catch (err) {
                addLog('Wave FW stream parse failed.', 'warning');
            }
        };
        eventSource.onerror = function () {
            if (waveState.taskStream === eventSource) {
                eventSource.close();
                waveState.taskStream = null;
            }
        };
    }

    function stopTaskWatchers() {
        if (waveState.taskPollInterval) {
            clearInterval(waveState.taskPollInterval);
            waveState.taskPollInterval = null;
        }
        if (waveState.taskStream) {
            try { waveState.taskStream.close(); } catch (err) {}
            waveState.taskStream = null;
        }
    }

    async function pollTaskStatus(taskId) {
        try {
            const response = await waveFetch(`/status/${taskId}`);
            const data = await parseJson(response);
            if (!response.ok) throw new Error(data.error || `Status poll failed (${response.status})`);
            applyEventPayload(data);
            const status = String(data.status || '').toLowerCase();
            if (['completed', 'success', 'failed', 'error', 'aborted'].includes(status) || data.done === true) {
                stopTaskWatchers();
                waveState.taskId = null;
                setRunState(false);
                const logType = (status === 'completed' || status === 'success') ? 'success' : (status === 'aborted' ? 'warning' : 'error');
                addLog(`Wave FW task ${status}`, logType);
            }
        } catch (err) {
            addLog(`Status monitor error: ${err.message}`, 'warning');
        }
    }

    function monitorTask(taskId) {
        stopTaskWatchers();
        startTaskStream(taskId);
        setRunState(true);
        waveState.taskPollInterval = setInterval(() => {
            pollTaskStatus(taskId);
        }, 2500);
    }

    // ── Select / deselect all ─────────────────────────────────────────────────

    function selectAll() {
        waveState.devices.forEach(d => { d.selected = true; });
        updateDeviceList();
    }

    function deselectAll() {
        waveState.devices.forEach(d => { d.selected = false; });
        updateDeviceList();
    }

    // ── Controls ──────────────────────────────────────────────────────────────

    function bindControls() {
        const bindings = [
            ['waveFwDiscoverBtn', 'click', discoverDevices],
            ['waveFwUploadBtn', 'click', uploadFirmwareFile],
            ['waveFwRunBtn', 'click', runUpgrade],
            ['waveFwAbortBtn', 'click', abortCurrentTask],
            ['waveFwSelectAllBtn', 'click', selectAll],
            ['waveFwDeselectAllBtn', 'click', deselectAll],
            ['waveFwClearLogBtn', 'click', clearLog]
        ];
        bindings.forEach(([id, eventName, handler]) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(eventName, handler);
        });

        const fileInput = document.getElementById('waveFwFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', () => {
                if (fileInput.files && fileInput.files.length > 0) {
                    // Auto-upload on file selection
                    uploadFirmwareFile();
                }
            });
        }
    }

    async function initWaveUpdater() {
        if (waveState.initComplete) return;
        waveState.initComplete = true;
        updateFileBadge();
        updateDeviceList();
        setRunState(false);
        bindControls();
        addLog('Ubiquiti Wave firmware updater ready.', 'info');
    }

    window.getWaveApiBase = getWaveApiBase;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initWaveUpdater().catch(err => {
                console.error('[WaveFW] Failed to initialize updater', err);
            });
        }, { once: true });
    } else {
        initWaveUpdater().catch(err => {
            console.error('[WaveFW] Failed to initialize updater', err);
        });
    }
}());
