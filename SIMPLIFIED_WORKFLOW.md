# ✅ SIMPLIFIED: New Configs + Upgrades

## 🎯 Two Use Cases Only

### **USE CASE 1: NEW DEVICE CONFIG** 
**Scenario:** Setting up a brand new device
**Action:** Fill form → Generate → Deploy

### **USE CASE 2: UPGRADE EXISTING DEVICE**
**Scenario:** Migrating RB2011 (6.49.2) → CCR2004 (7.16.2)
**Action:** Paste old config → AI translates → Deploy

---

## 🚀 Simplified Implementation

### **Step 1: Add Two Buttons to Tower Tab**

```html
<!-- Replace the purple Nextlink section with this simple version -->
<div class="section" style="background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px;">
    <h3 style="margin-top: 0; color: #667eea;">🤖 AI-Powered Config Tools</h3>
    
    <!-- NEW DEVICE: Load template -->
    <div style="margin-bottom: 15px;">
        <strong>📋 New Device Setup:</strong>
        <button onclick="loadNextlinkTemplate()" style="margin-left: 10px;">
            Load Nextlink Defaults
        </button>
        <p style="font-size: 13px; color: #666; margin: 5px 0 0 0;">
            Auto-fills DNS, SNMP, VLANs. Then fill site-specific info.
        </p>
    </div>
    
    <!-- UPGRADE: Paste old config -->
    <div style="margin-bottom: 15px;">
        <strong>🔄 Upgrade Existing Device:</strong>
        <button onclick="showUpgradeModal()" style="margin-left: 10px;">
            Paste Old Config & Upgrade
        </button>
        <p style="font-size: 13px; color: #666; margin: 5px 0 0 0;">
            Paste /export from old device → AI translates to new device/version.
        </p>
    </div>
    
    <!-- VALIDATE: After generating -->
    <div>
        <strong>✅ After Generating:</strong>
        <button onclick="validateCurrentConfig()" style="margin-left: 10px;">
            AI Validate Config
        </button>
        <button onclick="suggestFixes()" style="margin-left: 5px;">
            AI Suggest Fixes
        </button>
    </div>
    
    <div id="ai_status" style="margin-top: 15px; padding: 10px; background: white; border-radius: 4px; display: none;"></div>
</div>
```

---

## 📝 JavaScript Functions (Simplified)

```javascript
// =====================================
// WORKFLOW 1: NEW DEVICE
// =====================================

function loadNextlinkTemplate() {
    // Auto-fill Nextlink standards
    document.getElementById('dns1').value = '8.8.8.8';
    document.getElementById('dns2').value = '8.8.4.4';
    // ... (keep existing code)
    
    alert('✅ Nextlink template loaded!\n\nNow fill:\n- Site Name\n- Router ID\n- Uplink IPs\n- ASN\n\nThen click Generate.');
}

// =====================================
// WORKFLOW 2: UPGRADE DEVICE
// =====================================

function showUpgradeModal() {
    const modal = `
        <div id="upgradeModal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 9999; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; padding: 30px; border-radius: 10px; max-width: 800px; width: 90%; max-height: 90vh; overflow: auto;">
                <h2 style="margin-top: 0;">🔄 Upgrade Device Configuration</h2>
                
                <div style="margin-bottom: 20px;">
                    <label style="font-weight: bold;">1. Paste Old Config (from /export):</label>
                    <textarea id="oldConfig" rows="10" style="width: 100%; font-family: monospace; margin-top: 5px;" placeholder="# jan/01/1970 00:00:00 by RouterOS 6.49.2&#10;/system identity&#10;set name=OldRouter&#10;..."></textarea>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div>
                        <label style="font-weight: bold;">2. New Device Type:</label>
                        <select id="newDeviceType" style="width: 100%; margin-top: 5px;">
                            <option value="rb2011">RB2011</option>
                            <option value="ccr1036">CCR1036</option>
                            <option value="ccr2004" selected>CCR2004</option>
                            <option value="rb5009">RB5009</option>
                            <option value="ccr2216">CCR2216</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-weight: bold;">3. New RouterOS Version:</label>
                        <select id="newRouterOSVersion" style="width: 100%; margin-top: 5px;">
                            <option value="7.16.2" selected>7.16.2 (Stable)</option>
                            <option value="7.19.4">7.19.4 (Latest)</option>
                            <option value="7.11.2">7.11.2 (Legacy)</option>
                        </select>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button onclick="closeUpgradeModal()" style="background: #6c757d;">Cancel</button>
                    <button onclick="performUpgrade()" style="background: #4CAF50;">🤖 AI Upgrade Config</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modal);
}

function closeUpgradeModal() {
    const modal = document.getElementById('upgradeModal');
    if (modal) modal.remove();
}

async function performUpgrade() {
    const oldConfig = document.getElementById('oldConfig').value;
    const newDevice = document.getElementById('newDeviceType').value;
    const newVersion = document.getElementById('newRouterOSVersion').value;
    
    if (!oldConfig) {
        alert('❌ Please paste your old config first!');
        return;
    }
    
    // Show loading
    showAIStatus('⏳ AI is upgrading your config... (30-60 seconds)');
    
    try {
        // Call AI backend
        const response = await fetch('http://localhost:5000/api/translate-config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                source_config: oldConfig,
                target_device: newDevice,
                target_version: newVersion
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show upgraded config
            document.getElementById('output').textContent = data.translated_config;
            
            // Show validation
            const validation = data.validation;
            if (validation.missing_ips.length > 0) {
                showAIStatus(`⚠️ Warning: Missing IPs: ${validation.missing_ips.join(', ')}`, 'warning');
            } else {
                showAIStatus('✅ Config upgraded successfully! Review below.', 'success');
            }
            
            closeUpgradeModal();
            
            // Scroll to output
            document.getElementById('output').scrollIntoView({ behavior: 'smooth' });
        } else {
            throw new Error(data.error || 'Translation failed');
        }
        
    } catch (error) {
        showAIStatus(`❌ Error: ${error.message}\n\nMake sure:\n1. API server is running (python api_server.py)\n2. API key has credits`, 'error');
    }
}

// =====================================
// WORKFLOW 3: VALIDATE GENERATED CONFIG
// =====================================

async function validateCurrentConfig() {
    const config = document.getElementById('output').textContent;
    
    if (!config || config === 'Configuration will appear here...') {
        alert('❌ Generate a config first, then validate it!');
        return;
    }
    
    showAIStatus('⏳ AI is validating... (10-20 seconds)');
    
    try {
        const response = await fetch('http://localhost:5000/api/validate-config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                config: config,
                type: 'tower'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const validation = data.validation;
            const issues = validation.issues || [];
            
            if (issues.length === 0) {
                showAIStatus('✅ No issues found! Config looks good.', 'success');
            } else {
                let html = '<strong>⚠️ Issues Found:</strong><ul style="margin: 10px 0; padding-left: 20px;">';
                issues.forEach(issue => {
                    const color = issue.severity === 'error' ? '#f44336' : '#ff9800';
                    html += `<li style="color: ${color}; margin: 5px 0;">${issue.message}</li>`;
                });
                html += '</ul><button onclick="suggestFixes()" style="margin-top: 10px;">🔧 AI Suggest Fixes</button>';
                showAIStatus(html, 'warning');
            }
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        showAIStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// =====================================
// WORKFLOW 4: SUGGEST FIXES
// =====================================

async function suggestFixes() {
    const config = document.getElementById('output').textContent;
    
    showAIStatus('⏳ AI is analyzing and suggesting fixes... (20-30 seconds)');
    
    try {
        const response = await fetch('http://localhost:5000/api/suggest-fixes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                config: config,
                type: 'tower'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const fixes = data.fixes || [];
            
            if (fixes.length === 0) {
                showAIStatus('✅ No fixes needed!', 'success');
            } else {
                let html = '<strong>🔧 Suggested Fixes:</strong><ul style="margin: 10px 0; padding-left: 20px;">';
                fixes.forEach((fix, index) => {
                    html += `<li style="margin: 8px 0;">
                        <strong>${fix.issue}</strong><br>
                        <span style="font-size: 12px; color: #666;">Fix: ${fix.suggestion}</span><br>
                        <button onclick="applyFix(${index})" style="margin-top: 5px; font-size: 12px; padding: 4px 8px;">Apply Fix</button>
                    </li>`;
                });
                html += '</ul>';
                showAIStatus(html, 'info');
            }
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        showAIStatus(`❌ Error: ${error.message}`, 'error');
    }
}

function applyFix(fixIndex) {
    alert('🚧 Auto-fix coming soon! For now, manually apply the suggested change.');
}

// =====================================
// HELPER FUNCTIONS
// =====================================

function showAIStatus(message, type = 'info') {
    const statusDiv = document.getElementById('ai_status');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = message;
    
    const colors = {
        success: '#d4edda',
        error: '#f8d7da',
        warning: '#fff3cd',
        info: '#d1ecf1'
    };
    
    const textColors = {
        success: '#155724',
        error: '#721c24',
        warning: '#856404',
        info: '#0c5460'
    };
    
    statusDiv.style.background = colors[type] || colors.info;
    statusDiv.style.color = textColors[type] || textColors.info;
    statusDiv.style.border = `1px solid ${textColors[type]}`;
}
```

---

## 🔧 Add to `api_server.py`: Suggest Fixes Endpoint

```python
@app.route('/api/suggest-fixes', methods=['POST'])
def suggest_fixes():
    """
    Analyzes config and suggests specific fixes for detected issues
    """
    try:
        data = request.json
        config = data.get('config', '')
        config_type = data.get('type', 'tower')
        
        if not config:
            return jsonify({'error': 'No configuration provided'}), 400
        
        # First validate to get issues
        validation_result = validate_config_internal(config, config_type)
        issues = validation_result.get('issues', [])
        
        if not issues:
            return jsonify({
                'success': True,
                'fixes': []
            })
        
        # Build fix suggestion prompt
        issues_text = '\n'.join([f"- {issue['message']}" for issue in issues])
        
        system_prompt = """You are a Nextlink NOC configuration fix expert.
Given a list of config issues, provide specific, actionable fixes.

Return JSON format:
{
  "fixes": [
    {
      "issue": "description of problem",
      "suggestion": "specific fix to apply",
      "line": line number if known,
      "code": "exact code to add/change"
    }
  ]
}
"""
        
        user_prompt = f"""Configuration has these issues:

{issues_text}

Full configuration:
```
{config}
```

Provide specific fixes for each issue. Include exact commands to add or modify."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = call_openai_chat(messages, max_tokens=3000)
        
        try:
            fixes_data = json.loads(result)
        except:
            fixes_data = {"fixes": [{"issue": "General", "suggestion": result}]}
        
        return jsonify({
            'success': True,
            'fixes': fixes_data.get('fixes', [])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def validate_config_internal(config, config_type):
    """Internal validation function (reuse existing logic)"""
    # Copy logic from validate-config endpoint
    # Return dict with issues
    pass
```

---

## 📊 User Experience

### **New Device:**
```
1. Click "Load Nextlink Defaults" ✅
2. Fill site-specific fields
3. Click "Generate Configuration"
4. Click "AI Validate Config"
5. If issues → Click "AI Suggest Fixes"
6. Copy/Download → Deploy
```

### **Upgrade Device:**
```
1. Click "Paste Old Config & Upgrade" ✅
2. Paste /export from old device
3. Select new device/version
4. Click "AI Upgrade Config"
5. AI translates (6.x → 7.x)
6. Review upgraded config
7. Click "AI Validate Config"
8. Copy/Download → Deploy
```

---

## ✅ Summary

**Before (Complicated):**
- Separate translator tab
- Manual API key entry
- Confusing workflow
- Not clear what to do

**After (Simplified):**
- ✅ **2 clear workflows** (New vs Upgrade)
- ✅ **3 simple buttons** (Load Template, Upgrade, Validate)
- ✅ **AI backend handles complexity**
- ✅ **User just clicks buttons**

---

Want me to add these simplified functions to your HTML file now?

