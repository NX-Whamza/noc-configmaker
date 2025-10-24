# Upgrade Output and IP Preservation Fix

## Problems Fixed:
1. **No visible output**: User couldn't see the translated config
2. **Missing IPs treated as "warnings"**: Should be CRITICAL FAILURES
3. **AI not preserving IPs**: Prompt wasn't strict enough

## Solutions Implemented:

### 1. Dedicated Upgrade Output Section
**New UI element right in the upgrade mode:**
- Large, visible textarea for translated config
- Copy to Clipboard button
- Download .rsc button
- Auto-scrolls into view when done
- 500px tall, easy to see

**Location:** Right below the "Start Upgrade" button

### 2. IP Preservation Validation
**New logic:**
- **0 missing IPs**: ✅ Success message
- **1-10 missing IPs**: ⚠️ Warning (partial failure)
- **>10 missing IPs**: ❌ CRITICAL FAILURE - stops and shows error

**Before:** "Upgrade complete with warnings. Missing IPs: [100 IPs]"
**After:** "CRITICAL FAILURE: 102 IP addresses lost in translation. AI failed to preserve network config. This is unusable."

### 3. Improved AI Prompt (api_server.py)
**New system prompt emphasis:**
```
🚨 CRITICAL RULES - ABSOLUTE REQUIREMENTS:
1. COPY EVERY IP ADDRESS EXACTLY: Every single IP address and subnet from the source config MUST appear in the output
   - /ip address add lines: COPY EXACTLY, only change interface= syntax if needed
   - /ip route entries: PRESERVE ALL gateways and destinations
   - OSPF neighbor IPs: MUST BE IDENTICAL
   - BGP peer IPs: MUST BE IDENTICAL
   - DNS server IPs: MUST BE IDENTICAL
   - DHCP server/pool IPs: MUST BE IDENTICAL
   - Firewall src-address/dst-address: MUST BE IDENTICAL

⚠️ YOUR OUTPUT WILL BE VALIDATED: If any IP is missing, the translation FAILS
```

### 4. New Functions Added
- `copyUpgradeOutput()`: Copy translated config to clipboard
- `downloadUpgradeOutput()`: Download as `upgraded-{device}-v{version}-{date}.rsc`

## How to Test:
1. Refresh browser (Ctrl+F5)
2. Upload a config file
3. Click "Start Upgrade"
4. **Output now appears RIGHT THERE** (no scrolling needed)
5. If >10 IPs missing: Gets CRITICAL FAILURE error
6. Click Copy or Download buttons to save result

## Why This Matters:
A RouterOS config with missing IPs is **completely unusable** - it will break the network. This change ensures:
- Translation failures are caught immediately
- Output is always visible and accessible
- User can easily save/copy the result
- AI is forced to be more careful about IP preservation

