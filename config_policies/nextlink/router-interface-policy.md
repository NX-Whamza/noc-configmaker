# Router Interface Assignment Policy
**Version**: 1.0  
**Last Updated**: November 27, 2024  
**Scope**: All Nextlink RouterOS v7 Deployments

---

## Overview

This policy establishes **universal interface assignment standards** across all MikroTik CCR router models to ensure consistency, maintainability, and ease of troubleshooting across the Nextlink network.

**Key Principle**: Regardless of router model, interface assignments follow the same logical pattern.

---

## Supported Router Models

| Model | SFP+ Ports | Ethernet Ports | Notes |
|-------|------------|----------------|-------|
| **CCR2004-1G-12S+2XS** | 14 (sfp28-1 to sfp28-14) | 1 (ether1) | Primary production router |
| **CCR1036-12G-4S** | 12 (sfp-sfpplus1 to sfp-sfpplus12) | 12 (ether1 to ether12) | Legacy/secondary router |
| **CCR2116-12G-4S+** | 16 (sfp-sfpplus1 to sfp-sfpplus16) | 12 (ether1 to ether12) | High-performance router |
| **CCR2216-1G-12XS-2XQ** | 14 (sfp28-1 to sfp28-14) | 1 (ether1) | Next-gen high-density |

---

## Universal Interface Assignments

### Management Port (ALL Models)
- **ether1**: ALWAYS reserved for management/out-of-band access
- **NEVER** use ether1 for customer traffic or backhaul
- This is the "safe" port for emergency access

### SFP+ Port Assignments (CCR2004/2216)

#### High-Speed Backhaul (sfp28-1 to sfp28-3)
```routeros
# Primary uplinks to core/aggregation routers
sfp28-1  -> Core Router #1 (Primary backhaul)
sfp28-2  -> Core Router #2 (Redundant backhaul)
sfp28-3  -> Local aggregation/MPLS neighbor
```

#### Tower/Site Connections (sfp28-4 to sfp28-7)
```routeros
# Connections to tower routers or remote sites
sfp28-4  -> Tower/Site #1 (10G fiber)
sfp28-5  -> Tower/Site #2 (10G fiber)
sfp28-6  -> Tower/Site #3 (10G fiber)
sfp28-7  -> Tower/Site #4 (10G fiber)
```

#### Local Switch Uplinks (sfp28-8 to sfp28-11)
```routeros
# Bonded or individual connections to access switches
sfp28-8  -> Local Switch #1 (Often bonded with sfp28-9)
sfp28-9  -> Local Switch #1 (Often bonded with sfp28-8)
sfp28-10 -> Local Switch #2
sfp28-11 -> Local Switch #3
```

#### Management/Specialty (sfp28-12 to sfp28-14)
```routeros
sfp28-12 -> Out-of-band management network
sfp28-13 -> Reserved/spare
sfp28-14 -> Reserved/spare (100G on 2XS models)
```

### SFP+ Port Assignments (CCR1036/2116)

#### High-Speed Backhaul (sfp-sfpplus1 to sfp-sfpplus3)
```routeros
sfp-sfpplus1  -> Core Router #1 (Primary backhaul)
sfp-sfpplus2  -> Core Router #2 (Redundant backhaul)
sfp-sfpplus3  -> Local aggregation/MPLS neighbor
```

#### Tower/Site Connections (sfp-sfpplus4 to sfp-sfpplus7)
```routeros
sfp-sfpplus4  -> Tower/Site #1
sfp-sfpplus5  -> Tower/Site #2
sfp-sfpplus6  -> Tower/Site #3
sfp-sfpplus7  -> Tower/Site #4
```

#### Local Switch Uplinks (sfp-sfpplus8 to sfp-sfpplus11)
```routeros
sfp-sfpplus8  -> Local Switch #1 (bonded pair)
sfp-sfpplus9  -> Local Switch #1 (bonded pair)
sfp-sfpplus10 -> Local Switch #2
sfp-sfpplus11 -> Local Switch #3
```

#### Additional Ports (sfp-sfpplus12+)
```routeros
sfp-sfpplus12 -> Management/spare
sfp-sfpplus13 -> Reserved (CCR2116 only)
sfp-sfpplus14 -> Reserved (CCR2116 only)
sfp-sfpplus15 -> Reserved (CCR2116 only)
sfp-sfpplus16 -> Reserved (CCR2116 only)
```

### Ethernet Port Assignments

#### CCR2004/2216 (1 Ethernet Port)
```routeros
ether1 -> Management ONLY (VLAN 3000)
```

#### CCR1036/2116 (12 Ethernet Ports)
```routeros
ether1  -> Management ONLY (VLAN 3000)
ether2  -> Local services / CPE gear
ether3  -> Local services / CPE gear
ether4  -> Local services / CPE gear
ether5  -> RPC services
ether6  -> Local switch connection
ether7-12 -> Reserved / customer connections
```

---

## Bridge Assignments (Universal)

All routers use the same bridge structure:

```routeros
/interface bridge
add name=loop0 comment="Loopback" port-cost-mode=short
add name=lan-bridge comment="Main LAN" port-cost-mode=short priority=0x1
add name=bridge2000 comment="STATIC" port-cost-mode=short
add name=bridge3000 comment="MGMT" port-cost-mode=short
add name=bridge4000 comment="CPE" port-cost-mode=short
add name=nat-public-bridge comment="Public NAT IPs" port-cost-mode=short
```

---

## VLAN Standards

| VLAN | Purpose | Bridge | Ports |
|------|---------|--------|-------|
| 1000 | Main LAN | lan-bridge | Customer/CPE traffic |
| 2000 | Static IPs | bridge2000 | Business customers |
| 3000 | Management | bridge3000 | Network gear |
| 4000 | CPE | bridge4000 | CPE devices |

---

## Model-Specific Examples

### CCR2004-1G-12S+2XS Example
```routeros
# Management
/interface ethernet set [ find default-name=ether1 ] comment="MGMT ONLY - DO NOT USE FOR TRAFFIC"

# Backhaul
/interface ethernet set [ find default-name=sfp28-1 ] comment="Core-Router-1 Primary"
/interface ethernet set [ find default-name=sfp28-2 ] comment="Core-Router-2 Redundant"

# Towers
/interface ethernet set [ find default-name=sfp28-4 ] comment="TX-NEXTTOWER-CN-1"
/interface ethernet set [ find default-name=sfp28-5 ] comment="TX-NEXTTOWER-CN-2"

# Local Switches (Bonded)
/interface ethernet set [ find default-name=sfp28-8 ] comment="SWT-CRS326 Uplink #1 - BONDED"
/interface ethernet set [ find default-name=sfp28-9 ] comment="SWT-CRS326 Uplink #2 - BONDED"

/interface bonding add name=bonding1 slaves=sfp28-8,sfp28-9 mode=802.3ad

# VLANs on bonding
/interface vlan add interface=bonding1 name=vlan1000-bonding1 vlan-id=1000
/interface vlan add interface=bonding1 name=vlan2000-bonding1 vlan-id=2000
/interface vlan add interface=bonding1 name=vlan3000-bonding1 vlan-id=3000
/interface vlan add interface=bonding1 name=vlan4000-bonding1 vlan-id=4000
```

### CCR1036-12G-4S Example
```routeros
# Management
/interface ethernet set [ find default-name=ether1 ] comment="MGMT ONLY"

# Backhaul
/interface ethernet set [ find default-name=sfp-sfpplus1 ] comment="Core-Router-1 Primary"
/interface ethernet set [ find default-name=sfp-sfpplus2 ] comment="Core-Router-2 Redundant"

# Towers
/interface ethernet set [ find default-name=sfp-sfpplus4 ] comment="KS-TOWER-NE-1"
/interface ethernet set [ find default-name=sfp-sfpplus5 ] comment="KS-TOWER-SW-1"

# Local Switches
/interface ethernet set [ find default-name=sfp-sfpplus8 ] comment="Local-Switch Bonded #1"
/interface ethernet set [ find default-name=sfp-sfpplus9 ] comment="Local-Switch Bonded #2"

/interface bonding add name=bonding1 slaves=sfp-sfpplus8,sfp-sfpplus9 mode=802.3ad
```

### CCR2116-12G-4S+ Example
```routeros
# Management
/interface ethernet set [ find default-name=ether1 ] comment="MGMT ONLY"

# High-capacity backhaul (supports 25G with proper SFP28 modules)
/interface ethernet set [ find default-name=sfp-sfpplus1 ] comment="Core-25G-Primary"
/interface ethernet set [ find default-name=sfp-sfpplus2 ] comment="Core-25G-Redundant"

# Towers (supports 10G/25G)
/interface ethernet set [ find default-name=sfp-sfpplus4 ] comment="Tower-Alpha-25G"
/interface ethernet set [ find default-name=sfp-sfpplus5 ] comment="Tower-Beta-25G"
```

### CCR2216-1G-12XS-2XQ Example
```routeros
# Management
/interface ethernet set [ find default-name=ether1 ] comment="MGMT ONLY"

# 25G Backhaul (sfp28 ports support 25G)
/interface ethernet set [ find default-name=sfp28-1 ] comment="Core-25G-Primary"
/interface ethernet set [ find default-name=sfp28-2 ] comment="Core-25G-Redundant"

# High-density tower connections
/interface ethernet set [ find default-name=sfp28-4 ] comment="Tower-1-25G"
/interface ethernet set [ find default-name=sfp28-5 ] comment="Tower-2-25G"
/interface ethernet set [ find default-name=sfp28-6 ] comment="Tower-3-25G"
/interface ethernet set [ find default-name=sfp28-7 ] comment="Tower-4-25G"

# 100G uplinks (2XQ ports)
/interface ethernet set [ find default-name=qsfp28-1 ] comment="Metro-Core-100G"
```

---

## Speed Configuration

### RouterOS v7 Syntax
```routeros
# 10Gbps (correct)
/interface ethernet set [ find default-name=sfp28-1 ] speed=10Gbps

# 1Gbps (correct)
/interface ethernet set [ find default-name=ether1 ] speed=1Gbps

# 100Mbps (correct)
/interface ethernet set [ find default-name=ether2 ] auto-negotiation=no speed=100Mbps

# WRONG - Do not use duplex in v7
/interface ethernet set [ find default-name=sfp28-1 ] speed=10Gbps-duplex=full  # INCORRECT!
```

**Note**: In RouterOS v7, `speed=` only accepts the speed value. The `duplex=` parameter is deprecated and causes syntax errors.

---

## Migration Between Models

When replacing routers (e.g., CCR1036 → CCR2004):

### Port Mapping Table

| Logical Function | CCR1036 | CCR2004 | CCR2116 | CCR2216 |
|------------------|---------|---------|---------|---------|
| **Management** | ether1 | ether1 | ether1 | ether1 |
| **Core Uplink 1** | sfp-sfpplus1 | sfp28-1 | sfp-sfpplus1 | sfp28-1 |
| **Core Uplink 2** | sfp-sfpplus2 | sfp28-2 | sfp-sfpplus2 | sfp28-2 |
| **Aggregation** | sfp-sfpplus3 | sfp28-3 | sfp-sfpplus3 | sfp28-3 |
| **Tower 1** | sfp-sfpplus4 | sfp28-4 | sfp-sfpplus4 | sfp28-4 |
| **Tower 2** | sfp-sfpplus5 | sfp28-5 | sfp-sfpplus5 | sfp28-5 |
| **Tower 3** | sfp-sfpplus6 | sfp28-6 | sfp-sfpplus6 | sfp28-6 |
| **Tower 4** | sfp-sfpplus7 | sfp28-7 | sfp-sfpplus7 | sfp28-7 |
| **Switch Bond 1** | sfp-sfpplus8 | sfp28-8 | sfp-sfpplus8 | sfp28-8 |
| **Switch Bond 2** | sfp-sfpplus9 | sfp28-9 | sfp-sfpplus9 | sfp28-9 |
| **Local Switch** | sfp-sfpplus10 | sfp28-10 | sfp-sfpplus10 | sfp28-10 |

### Migration Checklist

- [ ] Document current interface assignments
- [ ] Map physical cables to logical functions
- [ ] Update comments with location/purpose
- [ ] Verify speed settings (10Gbps vs 10Gbps-duplex=full)
- [ ] Test bonding after cable moves
- [ ] Verify VLAN traffic on all bridges
- [ ] Update monitoring/documentation
- [ ] Update network diagrams

---

## Best Practices

1. **Always comment interfaces** with their purpose/destination
2. **Use consistent naming** across all sites
3. **Reserve ether1** for management - never production traffic
4. **Bond switch uplinks** (sfp28-8/9 or sfp-sfpplus8/9) for redundancy
5. **Document cable moves** during hardware replacements
6. **Test one port at a time** when migrating
7. **Use VLANs** for logical network separation
8. **Label physical cables** to match router comments

---

## Compliance Validation

Run this command to verify interface assignments:

```routeros
/interface ethernet print detail
/interface bonding print
/interface vlan print
```

Check for:
- ✅ All interfaces have descriptive comments
- ✅ Speed settings are correct (no -duplex=full in v7)
- ✅ Bonding is configured on switch uplinks
- ✅ VLANs are assigned to correct physical interfaces
- ✅ Management port (ether1) is not in production use

---

## Questions?

Contact: NOC Team (whamza@team.nxlink.com, agibson@team.nxlink.com)

