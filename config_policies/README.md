# Configuration Policy Directory

This directory contains **ALL** configuration policies, standards, and references for the NOC Config Maker backend. The backend automatically loads all policies from this directory structure.

## Directory Structure

```
config_policies/
├── README.md (this file)
├── USAGE.md (usage guide)
├── nextlink/
│   └── nextlink-internet-policy.md (NextLink Internet Policy)
├── lipan-sw/
│   └── lipan-sw-config-policy.md (LIPAN-SW configuration policy)
├── compliance/
│   └── README.md (compliance reference documentation)
└── examples/
    └── (generated example configs)
```

## Policy Categories

### 1. NextLink Policies (`nextlink/`)
- **nextlink-internet-policy.md**: Complete NextLink router configuration standards
  - Port assignment policies
  - RouterOS version compatibility
  - MPLS vs Non-MPLS configurations
  - Firewall standards
  - User management standards
  - Monitoring & logging

### 2. LIPAN-SW Policies (`lipan-sw/`)
- **lipan-sw-config-policy.md**: RouterOS 7.x LIPAN-SW baseline configuration
  - Input schema for site-specific configs
  - Loopback IP usage (10+ locations)
  - CPE, Unauth, CGNAT scopes
  - Tower link configurations
  - DHCP and RADIUS setup

### 3. Compliance References (`compliance/`)
- **Python Modules** (automatically loaded):
  - `nextlink_compliance_reference.py` - RFC-09-10-25 compliance blocks
  - `nextlink_enterprise_reference.py` - Standard enterprise blocks
  - `nextlink_standards.py` - Standards and constants

## Backend Integration

The backend (`api_server.py`) automatically:
1. **Loads all policies** on startup (recursively finds all .md files)
2. **Loads compliance references** from Python modules
3. **Provides API access** to all policies
4. **Organizes by category** for easy filtering

## API Endpoints

### List All Policies
```bash
GET /api/get-config-policies
```

### Get Specific Policy
```bash
GET /api/get-config-policy/{policy-name}
```

Examples:
- `GET /api/get-config-policy/nextlink-internet-policy`
- `GET /api/get-config-policy/lipan-sw-config-policy`
- `GET /api/get-config-policy/compliance-reference`

### Reload Policies
```bash
POST /api/reload-config-policies
```

## Policy Loading Rules

The backend finds policies by:
1. **Recursively scanning** `config_policies/` for all `.md` files
2. **Organizing by category** (subdirectory name)
3. **Creating unique keys** as `category-policy-name`
4. **Loading Python modules** for compliance/enterprise references

**Exclusions:**
- `README.md` and `USAGE.md` in root directory
- `examples/` directory
- `__pycache__/` directories

## Policy Naming Convention

Policies can be named:
- `{policy-name}.md`
- `{policy-name}-policy.md`
- `{policy-name}-config-policy.md`

All will be found and loaded. The category is determined by the subdirectory.

## Using Policies in LLM Prompts

When generating configurations, include relevant policies:

```python
# Load all relevant policies
nextlink_policy = CONFIG_POLICIES.get('nextlink-internet-policy', {})
lipan_policy = CONFIG_POLICIES.get('lipan-sw-config-policy', {})
compliance_ref = CONFIG_POLICIES.get('compliance-reference', {})

# Build comprehensive system prompt
system_prompt = f"""
You are a RouterOS configuration generator. Follow these policies:

1. NEXTLINK INTERNET POLICY:
{nextlink_policy.get('content', '')}

2. LIPAN-SW CONFIGURATION POLICY:
{lipan_policy.get('content', '')}

3. COMPLIANCE REFERENCE:
{compliance_ref.get('content', '')}

Generate a configuration that follows ALL these policies.
"""
```

## Adding New Policies

1. Create category directory: `config_policies/your-category/`
2. Add policy file: `your-category/your-policy.md`
3. Restart backend or call `/api/reload-config-policies`
4. Policy will be automatically loaded with key: `your-category-your-policy`

## Policy Categories Explained

- **nextlink/**: NextLink-specific standards and conventions
- **lipan-sw/**: LIPAN-SW baseline configuration templates
- **compliance/**: RFC-09-10-25 compliance standards and references
- **examples/**: Generated example configurations (reference only)

## Consistency Guarantee

By centralizing all policies in this directory:
- ✅ Backend automatically finds all policies
- ✅ No policies are missed
- ✅ Consistent structure across all policies
- ✅ Easy to add new policies
- ✅ Easy to update existing policies
- ✅ All policies accessible via API

## Version Control

All policies should be:
- Version controlled in Git
- Documented with version numbers
- Updated when standards change
- Reviewed before deployment

---

**This unified policy system ensures the LLM backend has access to ALL configuration standards and references, guaranteeing consistency across all generated configurations.**
