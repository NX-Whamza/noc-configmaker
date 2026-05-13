(function () {
    const API_BASE = ((typeof AI_API_BASE !== 'undefined' ? AI_API_BASE : window.AI_API_BASE) || '/api').replace(/\/+$/, '');

    /*
     * Config Search presets
     *
     * Admin/developer maintenance:
     * - Add a preset by adding one object to CONFIG_SEARCH_PRESETS.
     * - Remove a preset by deleting its object from this list.
     * - The preset dropdown is generated from this list, so no other UI code
     *   needs to change for normal preset additions/removals.
     *
     * vendor/type/model should match values returned by PostgreSQL search options.
     * If a value is not present in the current database options, the UI leaves
     * that filter as "Any" and logs a console warning instead of breaking.
     */
    const CONFIG_SEARCH_PRESETS = [
        {
            id: 'mikrotik-default-routes',
            label: 'Default Routes on MikroTiks',
            searchText: 'disabled=no distance=1 dst-address=0.0.0.0/0',
            hostnamePrefix: 'RTR-',
            vendor: 'MIKROTIK',
            type: '',
            model: '',
            requiredTexts: ['/routing ospf'],
            scope: 'latest',
            caseSensitive: false,
        },
    ];

    const state = {
        initialized: false,
        copyToastTimer: null,
        requiredTexts: [],
        missingTexts: [],
        optionValues: { vendors: [], types: [], models: [] },
        pendingPreset: null,
        advancedOpen: false,
        lastHadResults: false,
    };

    function $(id) {
        return document.getElementById(id);
    }

    function getHeaders() {
        const headers = {};
        const token = localStorage.getItem('auth_token');
        if (token) headers.Authorization = `Bearer ${token}`;
        return headers;
    }

    async function apiFetchWithTimeout(url, options = {}, timeoutMs = 90000) {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
        try {
            return await window.fetch(url, {
                ...options,
                headers: {
                    ...getHeaders(),
                    ...(options.headers || {}),
                },
                signal: controller.signal,
            });
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        }[char]));
    }

    function formatTimestamp(value) {
        if (!value) return '-';
        let date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            const numeric = Number(value);
            date = new Date(numeric > 1e12 ? numeric : numeric * 1000);
        }
        if (Number.isNaN(date.getTime())) return String(value);
        return new Intl.DateTimeFormat(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        }).format(date);
    }

    function setUnimusView(view) {
        const isSearch = view === 'search';
        $('unimusBcBackupSection')?.classList.toggle('unimus-bc-hidden', isSearch);
        $('unimusBcSearchSection')?.classList.toggle('unimus-bc-hidden', !isSearch);
        $('unimusBcBackupTab')?.classList.toggle('is-active', !isSearch);
        $('unimusBcConfigSearchTab')?.classList.toggle('is-active', isSearch);
        $('unimusBcBackupTab')?.setAttribute('aria-selected', isSearch ? 'false' : 'true');
        $('unimusBcConfigSearchTab')?.setAttribute('aria-selected', isSearch ? 'true' : 'false');
    }

    function populateSelect(id, values, emptyLabel) {
        const select = $(id);
        if (!select) return;
        const current = select.value;
        select.innerHTML = `<option value="">${escapeHtml(emptyLabel)}</option>${(values || []).map((value) => (
            `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`
        )).join('')}`;
        if ([...select.options].some((option) => option.value === current)) select.value = current;
    }

    function populatePresets() {
        const select = $('unimusConfigPresetSelect');
        if (!select) return;
        select.innerHTML = '<option value="">No preset</option>' + CONFIG_SEARCH_PRESETS.map((preset) => (
            `<option value="${escapeHtml(preset.id)}">${escapeHtml(preset.label || preset.name || preset.id)}</option>`
        )).join('');
    }

    function setSearchSource() {
        const title = $('unimusConfigSearchSourceTitle');
        const text = $('unimusConfigSearchSourceText');
        if (!title || !text) return;
        title.textContent = 'PostgreSQL';
        text.textContent = 'Uses the read-only helper function on the Unimus database.';
    }

    function resolveOptionValue(values, requested) {
        const wanted = String(requested || '').trim();
        if (!wanted) return '';
        return values.find((value) => String(value).toLowerCase() === wanted.toLowerCase()) || '';
    }

    async function loadSearchOptions() {
        try {
            const response = await apiFetchWithTimeout(`${API_BASE}/unimus-backup-configs/config-search-options`, {}, 30000);
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
            state.optionValues = {
                vendors: Array.isArray(payload.vendors) ? payload.vendors : [],
                types: Array.isArray(payload.types) ? payload.types : [],
                models: Array.isArray(payload.models) ? payload.models : [],
            };
            populateSelect('unimusConfigVendorFilter', state.optionValues.vendors, 'Any vendor');
            populateSelect('unimusConfigTypeFilter', state.optionValues.types, 'Any type');
            populateSelect('unimusConfigModelFilter', state.optionValues.models, 'Any model');
            setSearchSource();
            if (state.pendingPreset) {
                applyPreset(state.pendingPreset);
                state.pendingPreset = null;
            }
        } catch (error) {
            console.warn('[UNIMUS CONFIG SEARCH] Failed to load advanced filter options:', error);
            setStatus(`PostgreSQL config search failed: ${error.message || 'Unable to load filter options.'}`, 'error');
        }
    }

    function setAdvancedOpen(open) {
        state.advancedOpen = !!open;
        const panel = $('unimusConfigAdvancedPanel');
        const toggle = $('unimusConfigAdvancedToggle');
        panel?.classList.toggle('unimus-bc-hidden', !state.advancedOpen);
        if (toggle) {
            toggle.textContent = state.advancedOpen ? 'Advanced Search ▴' : 'Advanced Search ▾';
            toggle.setAttribute('aria-expanded', state.advancedOpen ? 'true' : 'false');
        }
    }

    function hasAdvancedFilters() {
        return Boolean(
            String($('unimusConfigHostnamePrefix')?.value || '').trim()
            || String($('unimusConfigVendorFilter')?.value || '').trim()
            || String($('unimusConfigTypeFilter')?.value || '').trim()
            || String($('unimusConfigModelFilter')?.value || '').trim()
            || String($('unimusConfigPresetSelect')?.value || '').trim()
            || state.requiredTexts.length
            || state.missingTexts.length
        );
    }

    function syncAdvancedVisibility() {
        if (hasAdvancedFilters()) setAdvancedOpen(true);
    }

    function renderRequiredChips() {
        const wrap = $('unimusConfigRequiredChips');
        if (!wrap) return;
        wrap.innerHTML = state.requiredTexts.map((text) => `
            <span class="unimus-cs-filter-chip unimus-cs-removable-chip" title="${escapeHtml(text)}">
                <span>${escapeHtml(text)}</span>
                <button type="button" aria-label="Remove ${escapeHtml(text)}" data-required-remove="${escapeHtml(text)}">×</button>
            </span>
        `).join('');
        syncAdvancedVisibility();
    }

    function addRequiredText(raw) {
        const text = String(raw || '').trim();
        if (!text) return false;
        if (state.requiredTexts.some((item) => item.toLowerCase() === text.toLowerCase())) return false;
        state.requiredTexts.push(text);
        const input = $('unimusConfigRequiredInput');
        if (input) input.value = '';
        renderRequiredChips();
        return true;
    }

    function removeRequiredText(text) {
        const target = String(text || '').toLowerCase();
        state.requiredTexts = state.requiredTexts.filter((item) => item.toLowerCase() !== target);
        renderRequiredChips();
    }

    function renderMissingChips() {
        const wrap = $('unimusConfigMissingChips');
        if (!wrap) return;
        wrap.innerHTML = state.missingTexts.map((text) => `
            <span class="unimus-cs-filter-chip unimus-cs-removable-chip" title="${escapeHtml(text)}">
                <span>${escapeHtml(text)}</span>
                <button type="button" aria-label="Remove ${escapeHtml(text)}" data-missing-remove="${escapeHtml(text)}">×</button>
            </span>
        `).join('');
        syncAdvancedVisibility();
    }

    function addMissingText(raw) {
        const text = String(raw || '').trim();
        if (!text) return false;
        if (state.missingTexts.some((item) => item.toLowerCase() === text.toLowerCase())) return false;
        state.missingTexts.push(text);
        const input = $('unimusConfigMissingInput');
        if (input) input.value = '';
        renderMissingChips();
        return true;
    }

    function removeMissingText(text) {
        const target = String(text || '').toLowerCase();
        state.missingTexts = state.missingTexts.filter((item) => item.toLowerCase() !== target);
        renderMissingChips();
    }

    function applyPreset(presetOrId) {
        const preset = typeof presetOrId === 'string' ? CONFIG_SEARCH_PRESETS.find((item) => item.id === presetOrId) : presetOrId;
        if (!preset) return;
        const vendorValue = resolveOptionValue(state.optionValues.vendors, preset.vendor);
        const typeValue = resolveOptionValue(state.optionValues.types, preset.type || preset.deviceType);
        const modelValue = resolveOptionValue(state.optionValues.models, preset.model);
        if (
            (preset.vendor && !state.optionValues.vendors.length)
            || ((preset.type || preset.deviceType) && !state.optionValues.types.length)
            || (preset.model && !state.optionValues.models.length)
        ) {
            state.pendingPreset = preset;
            return;
        }
        if (preset.vendor && !vendorValue) {
            console.warn(`[UNIMUS CONFIG SEARCH] Preset "${preset.label || preset.id}" vendor "${preset.vendor}" is not available in PostgreSQL options; leaving vendor as Any.`);
        }
        if ((preset.type || preset.deviceType) && !typeValue) {
            console.warn(`[UNIMUS CONFIG SEARCH] Preset "${preset.label || preset.id}" type "${preset.type || preset.deviceType}" is not available in PostgreSQL options; leaving type as Any.`);
        }
        if (preset.model && !modelValue) {
            console.warn(`[UNIMUS CONFIG SEARCH] Preset "${preset.label || preset.id}" model "${preset.model}" is not available in PostgreSQL options; leaving model as Any.`);
        }
        $('unimusConfigSearchInput').value = preset.searchText || '';
        $('unimusConfigHostnamePrefix').value = preset.hostnamePrefix || '';
        $('unimusConfigVendorFilter').value = vendorValue || '';
        $('unimusConfigTypeFilter').value = typeValue || '';
        $('unimusConfigModelFilter').value = modelValue || '';
        $('unimusConfigCaseSensitive').checked = !!preset.caseSensitive;
        state.requiredTexts = [];
        state.missingTexts = [];
        (preset.requiredTexts || []).forEach((text) => addRequiredText(text));
        (preset.missingTexts || []).forEach((text) => addMissingText(text));
        renderMissingChips();
        setScope(preset.scope || 'latest');
        setAdvancedOpen(true);
    }

    function renderSnippet(snippet) {
        const lines = Array.isArray(snippet.lines) ? snippet.lines : [];
        return `
            <div class="unimus-cs-snippet">
                <div class="unimus-cs-snippet-header">Lines ${escapeHtml(snippet.start_line)}-${escapeHtml(snippet.end_line)}</div>
                <div class="unimus-cs-snippet-body">
                    ${lines.map((line) => `
                        <div class="unimus-cs-snippet-line ${line.is_match ? 'is-match' : ''}">
                            <span class="unimus-cs-line-number">${escapeHtml(line.line_number)}</span>
                            <span class="unimus-cs-line-text">${escapeHtml(line.text)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    async function copyTextWithFallback(text) {
        const value = String(text || '');
        if (!value) return false;
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
            return true;
        }
        const textarea = document.createElement('textarea');
        textarea.value = value;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        let copied = false;
        try {
            copied = document.execCommand('copy');
        } finally {
            textarea.remove();
        }
        return copied;
    }

    function showCopyToast(event) {
        let toast = document.querySelector('.unimus-cs-copy-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'unimus-cs-copy-toast';
            toast.textContent = 'Copied to clipboard!';
            document.body.appendChild(toast);
        }
        const x = Math.min(Math.max(event.clientX, 90), window.innerWidth - 90);
        const y = Math.min(Math.max(event.clientY, 45), window.innerHeight - 20);
        toast.style.left = `${x}px`;
        toast.style.top = `${y}px`;
        toast.classList.add('is-visible');
        window.clearTimeout(state.copyToastTimer);
        state.copyToastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 1400);
    }

    function updateCollapseToggle() {
        const toggle = $('unimusConfigCollapseToggle');
        if (!toggle) return;
        const resultCards = [...document.querySelectorAll('#unimusConfigSearchResults .unimus-cs-host-card')];
        const hasResults = resultCards.length > 0;
        const anyOpen = resultCards.some((card) => card.open);
        state.lastHadResults = hasResults;
        toggle.classList.toggle('unimus-bc-hidden', !hasResults);
        toggle.disabled = !hasResults;
        toggle.textContent = anyOpen ? 'Collapse All' : 'Expand All';
        toggle.setAttribute('aria-pressed', anyOpen ? 'true' : 'false');
    }

    function copyLink(value, label = value) {
        const safeValue = escapeHtml(value);
        return `<a href="#" class="unimus-cs-copy-link" data-unimus-copy="${safeValue}">${escapeHtml(label)}</a>`;
    }

    function metaItem(label, content) {
        if (!content) return '';
        return `<span class="unimus-cs-meta-item">${label ? `<span class="unimus-cs-meta-label">${escapeHtml(label)}:</span> ` : ''}${content}</span>`;
    }

    function renderHostSubtitle(host, hostAddress) {
        const items = [
            hostAddress ? copyLink(hostAddress) : '',
            host.vendor ? escapeHtml(host.vendor) : '',
            host.device_type ? escapeHtml(host.device_type) : '',
            host.model ? escapeHtml(host.model) : '',
        ].filter(Boolean);
        if (!items.length) return '<span>No address</span>';
        return items.map((item) => `<span class="unimus-cs-meta-item">${item}</span>`).join('');
    }

    function renderActiveFilters(filters) {
        const wrap = $('unimusConfigActiveFilters');
        if (!wrap) return;
        const chips = [];
        const active = filters || currentFilters();
        chips.push(active.latest_only ? 'Latest backups' : 'All backups');
        if (active.hostname_prefix) chips.push(active.hostname_prefix);
        if (active.vendor) chips.push(active.vendor);
        if (active.device_type) chips.push(active.device_type);
        if (active.model) chips.push(active.model);
        if (active.case_sensitive) chips.push('Case sensitive');
        state.requiredTexts.forEach((text) => chips.push(`Required: ${text}`));
        state.missingTexts.forEach((text) => chips.push(`Missing: ${text}`));
        wrap.innerHTML = chips.map((chip) => `<span class="unimus-cs-filter-chip">${escapeHtml(chip)}</span>`).join('');
    }

    function renderResults(results) {
        const hostCount = results.length;
        const backupCount = results.reduce((total, host) => total + (host.backups || []).length, 0);
        $('unimusConfigSearchResults').innerHTML = results.length ? results.map((host) => {
            const backups = Array.isArray(host.backups) ? host.backups : [];
            const hostName = host.description || host.address || host.device_id || 'Unknown host';
            const hostAddress = host.address || '';
            return `
                <details class="unimus-cs-host-card">
                    <summary class="unimus-cs-host-header">
                        <span class="unimus-cs-disclosure">›</span>
                        <div class="unimus-cs-host-title">
                            <h3>${copyLink(hostName)}</h3>
                            <div class="unimus-cs-host-subtitle">${renderHostSubtitle(host, hostAddress)}</div>
                        </div>
                        <div class="unimus-cs-host-badges">
                            <span class="unimus-cs-badge">${escapeHtml(backups.length)} backup${backups.length === 1 ? '' : 's'}</span>
                            <span class="unimus-cs-badge">${escapeHtml(host.match_count || 0)} match${Number(host.match_count || 0) === 1 ? '' : 'es'}</span>
                        </div>
                    </summary>
                    <div class="unimus-cs-host-body">
                        <div class="unimus-cs-host-meta">
                            ${metaItem('Host IP', hostAddress ? copyLink(hostAddress) : '')}
                            ${metaItem('Host Name', copyLink(hostName))}
                            ${metaItem('Latest backup', escapeHtml(host.latest_backup_time_iso ? formatTimestamp(host.latest_backup_time_iso) : '-'))}
                        </div>
                        <div class="unimus-cs-backup-list">
                            ${backups.map((backup) => `
                                <section class="unimus-cs-backup-card">
                                    <div class="unimus-cs-backup-header">
                                        <div>
                                            <div class="unimus-cs-backup-title">Backup ${escapeHtml(backup.backup_id)}</div>
                                            <div class="unimus-cs-backup-subtitle">${escapeHtml(formatTimestamp(backup.backup_create_time_iso || backup.backup_create_time))}</div>
                                        </div>
                                        <div class="unimus-cs-badge">${escapeHtml(backup.match_count || 0)} hit${Number(backup.match_count || 0) === 1 ? '' : 's'}</div>
                                    </div>
                                    <div class="unimus-cs-snippets">
                                        ${(backup.snippets || []).map((snippet) => renderSnippet(snippet)).join('')}
                                    </div>
                                </section>
                            `).join('')}
                        </div>
                    </div>
                </details>
            `;
        }).join('') : `
            <div class="unimus-cs-empty">
                <div>
                    <strong>No matching configs found.</strong>
                    <p>Try a broader search term, remove a required-text chip, or switch to All Backups.</p>
                </div>
            </div>
        `;
        $('unimusSearchCountBadge').textContent = `${hostCount} HOST${hostCount === 1 ? '' : 'S'} • ${backupCount} BACKUP${backupCount === 1 ? '' : 'S'}`;
        updateCollapseToggle();
    }

    function setScope(scope) {
        const resolved = scope === 'all' ? 'all' : 'latest';
        const select = $('unimusConfigScopeSelect');
        if (select) select.value = resolved;
        $('unimusConfigSearchButton').dataset.scope = resolved;
        return resolved;
    }

    function getScope() {
        return $('unimusConfigScopeSelect')?.value || $('unimusConfigSearchButton').dataset.scope || 'latest';
    }

    function setStatus(message, kind = '') {
        const el = $('unimusConfigSearchStatus');
        const textEl = $('unimusConfigSearchStatusText');
        if (!el) return;
        if (textEl) textEl.textContent = message || '';
        el.classList.remove('unimus-bc-hidden', 'is-success', 'is-error');
        if (!message) {
            el.classList.add('unimus-bc-hidden');
            return;
        }
        if (kind === 'success') el.classList.add('is-success');
        if (kind === 'error') el.classList.add('is-error');
        if (kind !== 'success') {
            $('unimusConfigCollapseToggle')?.classList.add('unimus-bc-hidden');
            $('unimusConfigActiveFilters').innerHTML = '';
        }
    }

    function currentFilters() {
        return {
            search_text: String($('unimusConfigSearchInput')?.value || '').trim(),
            latest_only: getScope() === 'latest',
            case_sensitive: !!$('unimusConfigCaseSensitive')?.checked,
            vendor: String($('unimusConfigVendorFilter')?.value || '').trim(),
            device_type: String($('unimusConfigTypeFilter')?.value || '').trim(),
            model: String($('unimusConfigModelFilter')?.value || '').trim(),
            hostname_prefix: String($('unimusConfigHostnamePrefix')?.value || '').trim(),
            required_texts: [...state.requiredTexts],
            missing_texts: [...state.missingTexts],
        };
    }

    async function runSearch() {
        const filters = currentFilters();
        const hasAdvancedFilter = Boolean(filters.vendor || filters.device_type || filters.model || filters.hostname_prefix);
        const hasTextChip = Boolean(filters.required_texts.length || filters.missing_texts.length);
        if (!hasTextChip && !hasAdvancedFilter && filters.search_text.length < 3) {
            setStatus('Search is too broad. Enter at least 3 search characters, add a Required or Missing text chip, or choose an advanced filter.', 'error');
            return;
        }
        const params = new URLSearchParams({
            q: filters.search_text,
            latest_only: filters.latest_only ? '1' : '0',
            case_sensitive: filters.case_sensitive ? '1' : '0',
        });
        [
            ['vendor', filters.vendor],
            ['device_type', filters.device_type],
            ['model', filters.model],
            ['hostname_prefix', filters.hostname_prefix],
        ].forEach(([key, value]) => {
            if (value) params.set(key, value);
        });
        filters.required_texts.forEach((text) => params.append('requiredTexts', text));
        filters.missing_texts.forEach((text) => params.append('missingTexts', text));

        const btn = $('unimusConfigSearchButton');
        btn.disabled = true;
        btn.textContent = 'Searching...';
        setStatus('Searching PostgreSQL...', '');
        $('unimusConfigSearchResults').innerHTML = '';
        updateCollapseToggle();
        try {
            const response = await apiFetchWithTimeout(`${API_BASE}/unimus-backup-configs/config-search?${params.toString()}`);
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
            setSearchSource();
            renderResults(Array.isArray(payload.results) ? payload.results : []);
            const modeLabel = payload.latest_only ? 'latest backups' : 'all backups';
            setStatus(`Found ${payload.host_count || 0} host(s) and ${payload.backup_count || 0} backup(s) across ${modeLabel}.`, 'success');
            renderActiveFilters(filters);
        } catch (error) {
            const message = error?.name === 'AbortError'
                ? 'PostgreSQL config search failed: request timed out before PostgreSQL returned a result.'
                : `PostgreSQL config search failed: ${error.message || 'Search failed.'}`;
            setStatus(message, 'error');
            $('unimusConfigSearchResults').innerHTML = '';
            updateCollapseToggle();
        } finally {
            btn.disabled = false;
            btn.textContent = 'Search';
        }
    }

    function bindEvents() {
        document.querySelectorAll('[data-unimus-bc-view]').forEach((button) => {
            button.addEventListener('click', () => setUnimusView(button.dataset.unimusBcView));
        });
        $('unimusConfigSearchButton').dataset.scope = 'latest';
        setScope('latest');

        $('unimusConfigSearchButton').addEventListener('click', runSearch);
        $('unimusConfigSearchInput').addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                runSearch();
            }
        });
        $('unimusConfigScopeSelect')?.addEventListener('change', () => syncAdvancedVisibility());
        $('unimusConfigPresetSelect')?.addEventListener('change', (event) => {
            const id = event.target.value;
            if (id) applyPreset(id);
        });
        $('unimusConfigAdvancedToggle')?.addEventListener('click', () => setAdvancedOpen(!state.advancedOpen));
        ['unimusConfigHostnamePrefix', 'unimusConfigVendorFilter', 'unimusConfigTypeFilter', 'unimusConfigModelFilter'].forEach((id) => {
            $(id)?.addEventListener('change', syncAdvancedVisibility);
            $(id)?.addEventListener('input', syncAdvancedVisibility);
        });
        $('unimusConfigRequiredAdd')?.addEventListener('click', () => addRequiredText($('unimusConfigRequiredInput')?.value));
        $('unimusConfigRequiredInput')?.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                addRequiredText(event.target.value);
            }
        });
        $('unimusConfigMissingAdd')?.addEventListener('click', () => addMissingText($('unimusConfigMissingInput')?.value));
        $('unimusConfigMissingInput')?.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                addMissingText(event.target.value);
            }
        });
        $('unimusConfigRequiredChips')?.addEventListener('click', (event) => {
            const button = event.target.closest('[data-required-remove]');
            if (!button) return;
            removeRequiredText(button.getAttribute('data-required-remove'));
        });
        $('unimusConfigMissingChips')?.addEventListener('click', (event) => {
            const button = event.target.closest('[data-missing-remove]');
            if (!button) return;
            removeMissingText(button.getAttribute('data-missing-remove'));
        });
        $('unimusConfigCollapseToggle')?.addEventListener('click', () => {
            const resultCards = [...document.querySelectorAll('#unimusConfigSearchResults .unimus-cs-host-card')];
            const shouldOpen = !resultCards.some((card) => card.open);
            resultCards.forEach((card) => {
                card.open = shouldOpen;
            });
            updateCollapseToggle();
        });
        $('unimusConfigSearchResults').addEventListener('click', async (event) => {
            const copyTarget = event.target.closest('[data-unimus-copy]');
            if (!copyTarget) return;
            event.preventDefault();
            event.stopPropagation();
            try {
                const copied = await copyTextWithFallback(copyTarget.dataset.unimusCopy || copyTarget.textContent);
                if (copied) showCopyToast(event);
            } catch (error) {
                console.warn('[UNIMUS CONFIG SEARCH] Failed to copy value:', error);
            }
        });
        $('unimusConfigSearchResults').addEventListener('toggle', (event) => {
            if (event.target.classList?.contains('unimus-cs-host-card')) updateCollapseToggle();
        }, true);
    }

    function init() {
        if (state.initialized) return;
        if (!$('unimusBcSearchSection')) return;
        state.initialized = true;
        populatePresets();
        bindEvents();
        setAdvancedOpen(false);
        setSearchSource();
        loadSearchOptions();
        $('unimusConfigSearchResults').innerHTML = `
            <div class="unimus-cs-empty">
                <div>
                    <strong>Search Unimus configs from PostgreSQL.</strong>
                    <p>Latest backups is the default. Add required text filters when a backup must contain multiple strings.</p>
                </div>
            </div>
        `;
        updateCollapseToggle();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
