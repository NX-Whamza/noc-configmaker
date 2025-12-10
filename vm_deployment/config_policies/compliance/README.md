# Compliance Policy Reference

This directory contains compliance-related policies and references.

## Available References

### Python Modules
- `nextlink_compliance_reference.py` - RFC-09-10-25 compliance blocks
- `nextlink_enterprise_reference.py` - Standard enterprise configuration blocks
- `nextlink_standards.py` - NextLink standards and constants

These are automatically loaded by the backend and available via the policy API.

## Compliance Standards

### RFC-09-10-25
All RouterOS configurations must comply with RFC-09-10-25 standards including:
- Firewall rules
- IP services configuration
- NTP settings
- SNMP configuration
- System logging
- DNS servers

The compliance reference module (`nextlink_compliance_reference.py`) provides:
- Standard compliance blocks
- Validation functions
- Automatic compliance enforcement

## Accessing Compliance

The backend automatically loads compliance references. Access via:
- `GET /api/get-config-policy/compliance-reference`
- `GET /api/get-config-policies?category=compliance`

## Integration

Compliance is automatically applied to:
- Non-MPLS Enterprise configs
- MPLS Enterprise configs
- Config upgrades/translations

No manual intervention needed - compliance is enforced automatically.

