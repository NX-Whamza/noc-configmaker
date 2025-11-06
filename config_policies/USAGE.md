# Config Policy Usage Guide

## Overview

The config policy system allows the LLM backend to generate RouterOS configurations based on structured policies. This ensures consistency, accuracy, and eliminates manual errors.

## Unified Policy Structure

```
config_policies/
├── README.md                    # Main documentation
├── USAGE.md                     # This file
├── nextlink/                    # NextLink policies
│   └── nextlink-internet-policy.md
├── lipan-sw/                    # LIPAN-SW policies
│   └── lipan-sw-config-policy.md
├── compliance/                  # Compliance references
│   └── README.md
└── examples/                    # Generated example configs
    └── LIPAN-CONFIG-POLICY-CN-1.rsc
```

## Using Policies in Backend

### 1. Load Policies (Automatic on Startup)

The backend automatically loads all policies from `config_policies/` on startup. You'll see:

```
[POLICIES] Loading configuration policies from: config_policies
[POLICIES] Loaded: lipan-sw from lipan-sw-config-policy.md
[POLICIES] Loaded 1 policies: lipan-sw
```

### 2. Access Policies via API

**List all policies:**
```bash
GET http://localhost:5000/api/get-config-policies
```

**Get specific policy:**
```bash
GET http://localhost:5000/api/get-config-policy/lipan-sw
```

**Reload policies (after editing):**
```bash
POST http://localhost:5000/api/reload-config-policies
```

### 3. Use Policy in LLM Prompts

When generating configurations, include the policy in your system prompt:

```python
# Load policy
policy = CONFIG_POLICIES.get('lipan-sw', {})
policy_content = policy.get('content', '')

# Build system prompt
system_prompt = f"""
You are a RouterOS configuration generator. Follow this policy exactly:

{policy_content}

Generate a configuration based on the provided site-specific inputs.
"""

# Provide site-specific inputs
user_prompt = f"""
Generate a RouterOS 7.x configuration with these parameters:

{json.dumps(site_params, indent=2)}
"""
```

## Example: Generating LIPAN-SW Config

### Input Schema

```json
{
  "device_name": "RTR-MT2004-AR1.TX-CONFIG-POLICY-CN-1",
  "time_zone": "America/Chicago",
  "loopback": { "ip": "10.1.1.1" },
  "cpe_scope": {
    "cidr": "10.10.10.0/24",
    "pool_range": "10.10.10.50-10.10.10.254"
  },
  "unauth_scope": {
    "cidr": "10.100.10.0/24",
    "pool_range": "10.100.10.2-10.100.10.254"
  },
  "cgnat_private_scope": {
    "cidr": "100.64.0.0/22",
    "pool_range": "100.64.0.3-100.64.3.254"
  },
  "cgnat_public_ip": "132.147.147.255",
  "bridge3000_ips": [
    { "label": "BRIDGE3000 MGMT", "cidr": "10.30.30.1/28" }
  ],
  "dhcp_dns_servers": ["4.2.2.2", "8.8.8.8"],
  "radius_servers": [
    { "address": "142.147.112.8", "secret": "Nl22021234" },
    { "address": "142.147.112.20", "secret": "Nl22021234" }
  ],
  "tower_links": [
    {
      "interface": "sfp-sfpplus4",
      "name": "TX-NEXTTOWER-CN-1",
      "cidr": "10.20.20.0/29",
      "local_ip": "10.20.20.1"
    },
    {
      "interface": "sfp-sfpplus5",
      "name": "TX-NEXTTOWER-CN-3",
      "cidr": "10.5.5.0/29",
      "local_ip": "10.5.5.4"
    }
  ]
}
```

### Expected Output

The LLM will generate a complete RouterOS configuration (.rsc file) with:
- All loopback IP references (10+ places) correctly set
- All scopes properly configured (CPE, Unauth, CGNAT)
- Tower links with correct IP allocation
- DHCP pools and networks matching CIDR ranges
- OSPF templates for all networks
- Firewall address lists properly configured
- RADIUS servers using loopback as source

## Adding New Policies

1. Create policy directory: `config_policies/your-policy-name/`
2. Create policy file: `your-policy-name-config-policy.md`
3. Follow the structure of `lipan-sw-config-policy.md`:
   - Purpose
   - Required Input Schema
   - Parameter Usage Map
   - Baseline Structure Preservation
   - Output Expectations
   - Validation Checklist
   - Example Usage
4. Restart backend or call `/api/reload-config-policies`

## Policy Best Practices

1. **Be Specific**: Clearly define where each parameter appears
2. **Be Complete**: List ALL locations where loopback IP is used
3. **Include Validation**: Provide checklist for LLM to verify output
4. **Provide Examples**: Show exact input/output format
5. **Document Dependencies**: Explain relationships between parameters

## Troubleshooting

**Policy not loading?**
- Check file naming: `{policy-name}-config-policy.md`
- Verify directory structure matches expected format
- Check backend logs for loading errors

**Policy not being used?**
- Verify policy is loaded: `GET /api/get-config-policies`
- Check policy name matches what you're requesting
- Ensure policy content is included in LLM prompt

**Generated config has errors?**
- Review validation checklist in policy
- Verify all required inputs are provided
- Check loopback IP appears in all required locations
- Validate CIDR calculations (gateway, network, pool ranges)

