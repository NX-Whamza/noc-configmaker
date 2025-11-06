# Policy Index - Complete Reference

This document provides a quick index of all available policies and references in the `config_policies/` directory.

## Quick Access

All policies are automatically loaded by the backend. Access via:
- **API**: `GET /api/get-config-policies`
- **By Category**: `GET /api/get-config-policies?category=nextlink`
- **Specific Policy**: `GET /api/get-config-policy/{policy-name}`

## Policy Categories

### 1. NextLink Policies (`nextlink/`)

| Policy Name | Key | Description |
|------------|-----|-------------|
| NextLink Internet Policy | `nextlink-internet-policy` | Complete NextLink router configuration standards including port assignments, RouterOS compatibility, MPLS/Non-MPLS configs, firewall, user management, and monitoring |

**Access**: `GET /api/get-config-policy/nextlink-internet-policy`

**Covers**:
- ✅ Port assignment standards (ether1=management, sfp-sfpplus1-2=switches, etc.)
- ✅ RouterOS v6 vs v7 compatibility
- ✅ MPLS network router configurations
- ✅ Non-MPLS network router configurations
- ✅ Firewall policy standards
- ✅ User management standards
- ✅ Monitoring & logging standards
- ✅ Service configuration standards

### 2. LIPAN-SW Policies (`lipan-sw/`)

| Policy Name | Key | Description |
|------------|-----|-------------|
| LIPAN-SW Config Policy | `lipan-sw-config-policy` | RouterOS 7.x LIPAN-SW baseline configuration template with site-specific parameterization |

**Access**: `GET /api/get-config-policy/lipan-sw-config-policy`

**Covers**:
- ✅ Input schema (device_name, loopback, scopes, etc.)
- ✅ Loopback IP usage (10+ locations)
- ✅ CPE, Unauth, CGNAT scopes
- ✅ Bridge3000 management IPs
- ✅ Tower link configurations
- ✅ DHCP scopes and pools
- ✅ RADIUS server configuration
- ✅ Validation checklist

### 3. Compliance References (`compliance/`)

| Reference Name | Key | Type | Description |
|---------------|-----|------|-------------|
| Compliance Reference | `compliance-reference` | Python Module | RFC-09-10-25 compliance blocks and standards |
| Enterprise Reference | `enterprise-reference` | Python Module | Standard enterprise configuration blocks |

**Access**: 
- `GET /api/get-config-policy/compliance-reference`
- `GET /api/get-config-policy/enterprise-reference`

**Python Modules**:
- `nextlink_compliance_reference.py` - Auto-loaded
- `nextlink_enterprise_reference.py` - Auto-loaded
- `nextlink_standards.py` - Available via imports

## Policy Loading

The backend automatically:
1. **Scans recursively** for all `.md` files in `config_policies/`
2. **Loads Python modules** for compliance/enterprise references
3. **Organizes by category** (subdirectory name)
4. **Creates unique keys** as `category-policy-name`

## Categories Summary

| Category | Count | Policies |
|----------|-------|----------|
| `nextlink` | 1 | nextlink-internet-policy |
| `lipan-sw` | 1 | lipan-sw-config-policy |
| `compliance` | 1 | compliance-reference (Python module) |
| `reference` | 1 | enterprise-reference (Python module) |

## Policy Usage in LLM Prompts

When generating configurations, include ALL relevant policies:

```python
# Load all policies
policies = CONFIG_POLICIES

# NextLink standards
nextlink = policies.get('nextlink-internet-policy', {})
# LIPAN-SW template
lipan = policies.get('lipan-sw-config-policy', {})
# Compliance
compliance = policies.get('compliance-reference', {})

system_prompt = f"""
You are a RouterOS configuration generator. Follow these policies:

1. NEXTLINK INTERNET POLICY:
{nextlink.get('content', '')[:5000]}...

2. LIPAN-SW CONFIGURATION POLICY:
{lipan.get('content', '')[:5000]}...

3. COMPLIANCE REFERENCE:
{compliance.get('content', '')}

Generate configurations that follow ALL these policies consistently.
"""
```

## Consistency Guarantee

✅ **All policies in one place** - `config_policies/`  
✅ **Automatic loading** - Backend finds everything  
✅ **No policies missed** - Recursive scanning  
✅ **Organized by category** - Easy to find  
✅ **API accessible** - Programmatic access  
✅ **Version controlled** - All in Git  

## Adding New Policies

1. Create subdirectory: `config_policies/your-category/`
2. Add policy file: `your-policy.md` (any name works)
3. Restart backend or: `POST /api/reload-config-policies`
4. Access via: `GET /api/get-config-policy/your-category-your-policy`

## Policy Priority

When multiple policies apply:
1. **NextLink Internet Policy** - Base standards (port assignments, naming, etc.)
2. **Category-specific policies** - LIPAN-SW, Tarana, etc.
3. **Compliance Reference** - RFC-09-10-25 enforcement
4. **Enterprise Reference** - Standard blocks

All must be satisfied - no conflicts allowed.

---

**Last Updated**: 2025-11-05  
**Total Policies**: 4 (2 markdown, 2 Python modules)  
**Categories**: 4 (nextlink, lipan-sw, compliance, reference)

