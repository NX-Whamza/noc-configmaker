# Config Policy Usage Guide

## Overview

The policy system lets the backend/LLM generate RouterOS configurations by combining structured Markdown policies with compliance references. Each policy describes required inputs, mapping rules, and validation expectations so the generator can produce consistent, audit-ready configs.

## Policy Layout

```
config_policies/
├── README.md (directory reference)
├── USAGE.md (this guide)
├── nextlink/
│   ├── texas-in-statepolicy.md              # Texas non-MPLS towers
│   ├── illinois-out-of-state-mpls-config-policy.md  # Illinois MPLS aggregation
│   ├── kansas-out-of-state-mpls-config-policy.md    # Kansas MPLS aggregation
│   └── nextlink-internet-policy.md           # Global standards & port roles
├── compliance/
│   └── README.md                            # Notes on compliance script & references
└── examples/                                # Sanitized RouterOS exports for context
```

## Using Policies in the Backend

1. **Loading:** Policies are auto-loaded on startup. After editing, run `POST /api/reload-config-policies` to refresh them.
2. **Discovery:** Use `GET /api/get-config-policies` to list available keys (e.g., `nextlink-texas-in-statepolicy`).
3. **Retrieval:** Use `GET /api/get-config-policy/<key>` to fetch a single policy or `GET /api/get-config-policy-bundle` to merge policy + compliance references.
4. **Prompting:** Feed the retrieved policy content into the LLM system prompt (alongside compliance blocks) before requesting generation or upgrades.

## Selecting the Right Policy

- **Texas towers (non-MPLS):** `nextlink-texas-in-statepolicy`
- **Illinois MPLS aggregation:** `nextlink-illinois-out-of-state-mpls-config-policy`
- **Kansas MPLS aggregation:** `nextlink-kansas-out-of-state-mpls-config-policy`
- **Global standards:** Always include `nextlink-internet-policy` as a reference for port roles, naming, and security posture.

## Compliance Integration

- The Python module `nextlink_compliance_reference.py` encapsulates the RFC-09-10-25 compliance script. Use the policy bundle endpoint to automatically add these blocks to prompts.
- The compliance script enforces service hardening, firewall ACLs, NAT/RAW order, SNMP/NTP settings, logging, and MPLS LDP filters. The backend should compare generated configs with these standards and insert missing sections.

## Example Prompt Flow (Pseudo-code)

```
policy_bundle = GET /api/get-config-policy-bundle?keys=nextlink-texas-in-statepolicy&include=compliance
system_prompt = "You are a RouterOS assistant..." + policy_bundle.content
user_prompt   = JSON payload with site inputs
LLM call      = { "messages": [ {"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt} ] }
```

## Version Control Reminders

- Policy Markdown files should be reviewed alongside any RouterOS change.
- Keep example exports updated when major policy revisions occur; they provide valuable training/test data.
- Document new state/role policies by adding them to `nextlink/` and referencing them in this guide.