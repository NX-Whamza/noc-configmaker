# Policy Index - Complete Reference

Quick reference to every policy in `config_policies/`. The backend auto-loads these and exposes them via the policy APIs.

## API Recap
- List all policies: `GET /api/get-config-policies`
- Filter by category: `GET /api/get-config-policies?category=nextlink`
- Fetch specific policy: `GET /api/get-config-policy/<policy-key>`
- Reload after edits: `POST /api/reload-config-policies`

## Nextlink Policies (`nextlink/`)

| Policy | Key | Description |
| --- | --- | --- |
| Nextlink Internet Policy | `nextlink-internet-policy` | Global standards: port assignments, MPLS vs non-MPLS expectations, firewall/security posture, naming conventions. |
| Texas Tower Non-MPLS Policy | `nextlink-texas-in-statepolicy` | Texas non-MPLS tower baseline derived from the LIPAN template (DHCP, Radius, CGNAT scopes). |
| Illinois Out-of-State MPLS Policy | `nextlink-illinois-out-of-state-mpls-config-policy` | Illinois MPLS aggregation routers using MSTP (`bridge9990`) and VPLS domain mapping. |
| Kansas Out-of-State MPLS Policy | `nextlink-kansas-out-of-state-mpls-config-policy` | Kansas MPLS aggregation routers with vendor bridges 600/800 and VPLS mesh. |

## Compliance References
- `nextlink_compliance_reference.py` – RFC-09-10-25 compliance blocks (services, firewall, SNMP, NTP, MPLS LDP filters).
- `nextlink_enterprise_reference.py` – Standard enterprise configuration blocks.
- `nextlink_standards.py` – Shared constants (port naming, VLAN conventions, etc.).

## Examples (`examples/`)
- `TX-LIPAN-CONFIG-POLICY-CN-1.rsc`
- `IL-HUMBOLDT-NE-1-CONFIG-POLICY.rsc`
- `KS-BENTON-CONFIG-POLICY.rsc`

These exports illustrate the expected output shape for each policy but are not loaded automatically.