# Nextlink Internet Policy - Router Configuration Standards

## Overview
This document establishes standardized policies for Nextlink router deployments across all RouterOS versions (v6 and v7) and router models (CCR2004, CCR1036, and future models). The policy ensures consistent, secure, and maintainable configurations regardless of hardware or software version.

**Key Principles:**
- Universal port assignment standards across all router models
- Consistent naming conventions for easy identification
- Standardized security policies and user management
- Scalable network architecture supporting both MPLS and non-MPLS deployments
- Version-agnostic configuration templates

---

## STANDARDIZED PORT ASSIGNMENT POLICY

### Universal Port Assignment Rules
```
ETHERNET PORTS:
ether1           = MANAGEMENT (ALWAYS - No exceptions)
ether5-12        = LOCAL SERVICES (RPC, Switch, Customer access)

SFP+ PORTS:
sfp-sfpplus1-2   = SWITCHES (Ports 1-2)
sfp-sfpplus4+    = BACKHAUL LINKS (Starting from port 4)
sfp-sfpplus6     = LTE GEAR (If present at site)
sfp-sfpplus6-8   = TARANA GEAR (If present at site)
sfp-sfpplus9+    = ADDITIONAL BACKHAULS (If more than 2 backhauls)
```

### Port Assignment Logic
1. **Management**: Always `ether1` - never change this
2. **Local Services**: Use `ether5-12` for RPC, local switches, customer access
3. **SFP+ Switches**: Always ports 1-2 for high-speed switching
4. **Backhauls**: Start from port 4, use next available ports
5. **LTE Gear**: Port 6 (if site has LTE equipment)
6. **Tarana Gear**: Ports 6-8 (if site has Tarana equipment)
7. **Multiple Backhauls**: Use ports 9+ for additional backhauls

### Site-Specific Considerations
- **LTE Sites**: Reserve port 6 for LTE gear
- **Tarana Sites**: Reserve ports 6-8 for Tarana equipment
- **High-Capacity Sites**: Plan for multiple backhauls using ports 9+
- **Management**: Always maintain `ether1` for out-of-band management

### Ethernet Port Usage Guidelines
**CCR1036 Ethernet Ports (ether1-ether12):**
- **ether1**: Management connection (ALWAYS)
- **ether5**: RPC services (Remote Procedure Call)
- **ether6**: Local switch connections
- **ether7-12**: Customer access and local services

**CCR2004 Ethernet Ports (ether1-ether4):**
- **ether1**: Management connection (ALWAYS)
- **ether2-4**: Local services and customer access

**Important Notes:**
- CCR1036 has 3x more Ethernet ports than CCR2004
- Ethernet ports are typically used for local services and customer access
- SFP+ ports are used for high-speed backhaul connections
- **ether1 is ALWAYS for management access** - never use for backhaul or customer traffic
- Management connection provides out-of-band access for troubleshooting

### Router Model Compatibility
- **CCR2004**: 12 SFP+ ports + 4 Ethernet ports (ether1-ether4)
- **CCR1036**: 12 SFP+ ports + 12 Ethernet ports (ether1-ether12)
- **Future Models**: Port assignment logic remains consistent regardless of port count

---

## ROUTEROS VERSION AND MODEL COMPATIBILITY

### RouterOS Version Differences

**RouterOS v6 (Legacy) - Non-MPLS Configuration:**
- Uses `/routing ospf interface` and `/routing ospf network`
- BGP connections use `remote-address` and `remote-as` parameters
- OSPF uses `router-id` and `area` parameters
- No MPLS/LDP configuration
- Standard bridge interfaces for customer access

**RouterOS v6 (Legacy) - MPLS Configuration:**
- Uses `/routing ospf` and `/routing bgp` commands
- BGP connections use `remote-address` and `remote-as` parameters
- OSPF uses `router-id` and `area` parameters
- MPLS uses `/mpls ldp` configuration
- VPLS uses `/interface vpls` with `cisco-static-id`

**RouterOS v7 (Current) - MPLS Configuration:**
- Uses `/routing bgp instance` and `/routing bgp connection`
- BGP connections use `remote.address` and `remote.as` parameters
- OSPF uses `/routing ospf instance` and `/routing ospf area`
- MPLS uses `/mpls ldp` with enhanced features
- VPLS configuration remains similar but with improved syntax

**RouterOS v7 (Current) - Non-MPLS Configuration:**
- Uses `/routing ospf instance` and `/routing ospf interface-template`
- BGP connections use `remote.address` and `remote.as` parameters
- OSPF uses `/routing ospf instance` and `/routing ospf area`
- No MPLS/LDP configuration
- Enhanced bridge and DHCP features

### Router Model Specifications
**CCR2004-12G-4S:**
- 12x SFP+ ports (sfp-sfpplus1 through sfp-sfpplus12)
- 4x 1G Ethernet ports (ether1 through ether4)
- High-performance routing with hardware acceleration
- Suitable for core infrastructure and high-capacity sites

**CCR1036-12G-4S:**
- 12x SFP+ ports (sfp-sfpplus1 through sfp-sfpplus12)
- 12x 1G Ethernet ports (ether1 through ether12)
- Lower cost alternative with good performance
- Suitable for customer access and smaller sites
- **Note**: CCR1036 has more Ethernet ports than CCR2004

### Configuration Migration Strategy
When upgrading from RouterOS v6 to v7:
1. **BGP Configuration**: Update connection syntax from `remote-address` to `remote.address`
2. **OSPF Configuration**: Migrate from single instance to multiple instances
3. **MPLS Configuration**: Update LDP syntax and interface assignments
4. **VPLS Configuration**: Maintain existing VPLS tunnels with updated syntax
5. **Firewall Rules**: Ensure compatibility with new firewall engine

### Port Assignment Across Models
All router models follow the same port assignment logic:
- **ether1**: Management (universal across all models)
- **ether5-12**: Local services (RPC, switches, customer access)
- **sfp-sfpplus1-2**: Switches (ports 1-2)
- **sfp-sfpplus4+**: Backhaul links (starting from port 4)
- **sfp-sfpplus6**: LTE gear (if present)
- **sfp-sfpplus6-8**: Tarana gear (if present)
- **sfp-sfpplus9+**: Additional backhauls

### Real-World Configuration Analysis
Based on analysis of production configurations:

**CCR1036 MPLS Configuration (KS-ANDALE-CN-1):**
- **Management**: `x.x.x.x/32` (loopback)
- **Backhaul Links**: `x.x.x.x/29` and `x.x.x.x/29`
- **VPLS Tunnels**: Multiple VPLS interfaces for customer services
- **MPLS/LDP**: Full MPLS infrastructure with LDP
- **BGP**: iBGP connections to core routers (CR7, CR8)

**CCR1036 Non-MPLS Configuration (BARWELL):**
- **Management**: `x.x.x.x/32` (loopback)
- **Customer Networks**: `x.x.x.x/22`, `x.x.x.x/22`, `x.x.x.x/22`
- **CGN**: `x.x.x.x` (public IP for NAT)
- **DHCP**: Multiple pools for different customer types
- **BGP**: Customer route advertisement
- **Ethernet Usage**: 
  - `ether1`: Management (ALWAYS - out-of-band management)
  - `ether5`: RPC services
  - `ether6`: Local switch
  - `ether7`: Customer access
  - `ether12`: Customer access

### Key Differences Between MPLS and Non-MPLS
1. **MPLS Routers**: Focus on inter-site connectivity with VPLS tunnels
2. **Non-MPLS Routers**: Focus on customer access with DHCP and NAT
3. **Port Usage**: MPLS routers use more backhaul ports, Non-MPLS use more customer-facing ports
4. **Services**: MPLS routers provide VPLS services, Non-MPLS provide internet access

### Non-MPLS Router Configuration (RouterOS v6)
**Based on CCR1036 BARWELL configuration:**

**OSPF Configuration (RouterOS v6):**
```routeros
/routing ospf instance
set [ find default=yes ] router-id=x.x.x.x

/routing ospf interface
add authentication=md5 authentication-key=m8M5JwvdYM comment="BACKHAUL" interface=ether1 network-type=point-to-point

/routing ospf network
add area=backbone comment=loop0 network=x.x.x.x/32
add area=backbone comment="CPE/Tower Gear" network=x.x.x.x/22
add area=backbone comment="BACKHAUL" network=x.x.x.x/29
```

**BGP Configuration (RouterOS v6):**
```routeros
/routing bgp instance
set default as=26077 router-id=x.x.x.x

/routing bgp peer
add in-filter=bgr-a-bgp-in-filter multihop=yes name=CR7 remote-address=x.x.x.x remote-as=26077 tcp-md5-key=m8M5JwvdYM ttl=default update-source=loop0
add in-filter=bgr-b-bgp-in-filter multihop=yes name=CR8 remote-address=x.x.x.x remote-as=26077 tcp-md5-key=m8M5JwvdYM ttl=default update-source=loop0
```

**Key Differences:**
- **No MPLS/LDP configuration** - Direct customer access
- **No VPLS tunnels** - Standard bridge interfaces
- **DHCP pools** for customer assignment
- **NAT configuration** for internet access
- **Customer-specific routing** via BGP

---

## MPLS NETWORK ROUTERS (Core Infrastructure)

### Device Naming Convention
**MPLS Network Routers:**
```
RTR-{MODEL}-{NUMBER}.{STATE}-{LOCATION}-{TYPE}-{NUMBER}
Examples:
- RTR-MTCCR2004-1.IL-WYOMIN-SW-1
- RTR-CCR1036-1.KS-ANDALE-CN-1
```

**Non-MPLS Network Routers:**
```
RTR-{MODEL}-{LOCATION}{NUMBER}
Examples:
- RTR-CCR2004-KENNEDALE1
- RTR-CCR1036-BARWELL
```

**Naming Components:**
- **RTR**: Router prefix (always)
- **MODEL**: Router model (CCR2004, CCR1036, etc.)
- **NUMBER**: Router instance number
- **STATE**: Two-letter state code (IL, TX, KS, etc.)
- **LOCATION**: City or site name
- **TYPE**: Router type (SW=Switch, CN=Customer Network, etc.)

### Network Architecture
- **Loopback IP**: `{MPLS_MGMT_NETWORK}.{ROUTER_ID}/32` (MPLS core network)
- **Management Network**: `{MPLS_MGMT_NETWORK}.0/24`
- **Customer Networks**: `{MPLS_CUSTOMER_NETWORK}.0/24` (Point-to-point links)
- **Infrastructure**: `{MPLS_INFRA_NETWORK}.0/24` (Backhaul links)
- **MPLS/VPLS**: Full MPLS infrastructure with VPLS tunnels

### Interface Configuration Standards

#### Ethernet Ports - Standardized Assignment
```routeros
# PORT ASSIGNMENT POLICY
# ether1 = Management (ALWAYS)
# sfp-sfpplus1-2 = Switches (Ports 1-2)
# sfp-sfpplus4+ = Backhaul links (starting from port 4)
# sfp-sfpplus6 = LTE gear (if present)
# sfp-sfpplus6-8 = Tarana gear (if present)
# Additional backhauls = Next available ports after port 4

/interface ethernet
# Management port (ALWAYS ether1)
set [find default-name=ether1] comment="MANAGEMENT" 

# Switches (Ports 1-2)
set [find default-name=sfp-sfpplus1] auto-negotiation=no comment="SWITCH-1" speed=1G-baseT-full
set [find default-name=sfp-sfpplus2] auto-negotiation=no comment="SWITCH-2" speed=1G-baseT-full

# Backhaul links (starting from port 4)
set [find default-name=sfp-sfpplus4] auto-negotiation=no comment="BACKHAUL-1" speed=1G-baseT-full
set [find default-name=sfp-sfpplus5] auto-negotiation=no comment="BACKHAUL-2" speed=1G-baseT-full

# LTE gear (if present)
set [find default-name=sfp-sfpplus6] auto-negotiation=no comment="LTE-GEAR" speed=1G-baseT-full

# Tarana gear (if present, ports 6-8)
set [find default-name=sfp-sfpplus7] auto-negotiation=no comment="TARANA-1" speed=1G-baseT-full
set [find default-name=sfp-sfpplus8] auto-negotiation=no comment="TARANA-2" speed=1G-baseT-full

# Additional backhauls (if more than 2)
set [find default-name=sfp-sfpplus9] auto-negotiation=no comment="BACKHAUL-3" speed=1G-baseT-full
set [find default-name=sfp-sfpplus10] auto-negotiation=no comment="BACKHAUL-4" speed=1G-baseT-full
```

#### Bridge Configuration
```routeros
# Standard bridge setup
/interface bridge
add comment=DYNAMIC name=bridge1000 protocol-mode=none
add comment=STATIC name=bridge2000 protocol-mode=none
add comment=STATIC2 disabled=yes name=bridge2001 protocol-mode=none
add comment=INFRA name=bridge3000 protocol-mode=none
add comment=CPE name=bridge4000 protocol-mode=none
add comment=m-VPLS name=bridge999247 protocol-mode=mstp region-name=IL-MSTP region-revision=1 vlan-filtering=yes
add comment=LOOPBACK name=loop0
```

#### VLAN Configuration
```routeros
# Standard VLAN setup
/interface vlan
add comment=VLAN1000-DYNAMIC interface=sfp-sfpplus1 name=vlan1000 vlan-id=1000
add comment=VLAN2000-STATIC interface=sfp-sfpplus1 name=vlan2000 vlan-id=2000
add comment=VLAN2001-STATIC2 disabled=yes interface=sfp-sfpplus1 name=vlan2001 vlan-id=2001
add comment=VLAN3000-INFRA interface=sfp-sfpplus1 name=vlan3000 vlan-id=3000
add comment=VLAN4000-CPE interface=sfp-sfpplus1 name=vlan4000 vlan-id=4000
```

### IP Address Assignment

#### Core Network
```routeros
# Loopback (Router ID)
/ip address
add address={MPLS_MGMT_NETWORK}.{ROUTER_ID} interface=loop0 network={MPLS_MGMT_NETWORK}.{ROUTER_ID}

# Point-to-point links (Backhaul starting from port 4)
add address={CUSTOMER_NETWORK}.{BACKHAUL_IP}/29 comment="{BACKHAUL_NAME}-1" interface=sfp-sfpplus4 network={CUSTOMER_NETWORK}.{BACKHAUL_NETWORK}
add address={CUSTOMER_NETWORK}.{BACKHAUL_IP}/29 comment="{BACKHAUL_NAME}-2" interface=sfp-sfpplus5 network={CUSTOMER_NETWORK}.{BACKHAUL_NETWORK}
add address={CUSTOMER_NETWORK}.{BACKHAUL_IP}/29 comment="{BACKHAUL_NAME}-3" interface=sfp-sfpplus9 network={CUSTOMER_NETWORK}.{BACKHAUL_NETWORK}
add address={CUSTOMER_NETWORK}.{BACKHAUL_IP}/30 comment="{BACKHAUL_NAME}-4" interface=sfp-sfpplus10 network={CUSTOMER_NETWORK}.{BACKHAUL_NETWORK}
```

### Routing Protocol Standards

#### **OSPF Configuration**
```routeros
/routing ospf instance
add disabled=no name=default-v2 router-id=10.247.0.146

/routing ospf area
add disabled=no instance=default-v2 name=area0

/routing ospf interface-template
add area=area0 cost=10 disabled=no interfaces=loop0 networks=10.247.0.146/32 passive priority=1
add area=area0 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment="IL-TOULON-SW-1" cost=10 disabled=no interfaces=sfp-sfpplus5 networks=10.247.99.56/29 priority=1 type=ptp
add area=area0 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment="IL-PRINCE-NO-1" cost=10 disabled=no interfaces=sfp-sfpplus4 networks=10.247.99.72/29 priority=1 type=ptp
add area=area0 auth=md5 auth-key=m8M5JwvdYM comment="IL-PRINCEV-WE-1" cost=30 disabled=no interfaces=sfp-sfpplus6 networks=10.247.99.80/29 priority=1 type=ptp
add area=area0 auth=md5 auth-key=m8M5JwvdYM comment="RB4011 ROUTER UPLINK" cost=10 disabled=no interfaces=sfp-sfpplus10 networks=10.247.132.28/30 priority=1 type=ptp
```

### **MPLS Configuration**
```routeros
/mpls interface
add disabled=no input=yes interface=all mpls-mtu=1600

/mpls ldp
add afi=ip disabled=no hop-limit=255 lsr-id=10.247.0.146 path-vector-limit=255 transport-addresses=10.247.0.146 vrf=main

# Accept/Advertise filters for Illinois networks
/mpls ldp accept-filter
add prefix=10.254.247.0/24
add prefix=10.247.0.0/24
add prefix=10.247.13.0/24
add prefix=10.247.72.0/24
add prefix=10.247.147.0/24
add prefix=10.247.187.0/24
add prefix=10.247.64.0/22
add prefix=10.254.42.0/24
add prefix=10.254.245.0/24
add prefix=10.42.0.0/24
add prefix=10.42.12.0/24
add prefix=10.42.192.0/22
add prefix=10.254.249.0/24
add prefix=10.249.0.0/24
add prefix=10.249.7.0/24
add prefix=10.249.180.0/22
add accept=no
```

---

## 🏢 **NON-MPLS NETWORK ROUTERS** (Customer Access Networks)

### **Device Naming Convention**
```
RTR-CCR2004-{LOCATION}{NUMBER}
Example: RTR-CCR2004-KENNEDALE1
```

### **Network Architecture**
- **Loopback IP**: `{NON_MPLS_MGMT_NETWORK}.{ROUTER_ID}/32` (Customer access network)
- **Management Network**: `{NON_MPLS_MGMT_NETWORK}.0/24`
- **Customer Networks**: `{NON_MPLS_CUSTOMER_NETWORK}.0/22` (CPE/Tower Gear)
- **Backhaul Networks**: `{NON_MPLS_BACKHAUL_NETWORK_1}.0/24`, `{NON_MPLS_BACKHAUL_NETWORK_2}.0/24`, `{NON_MPLS_BACKHAUL_NETWORK_3}.0/24`
- **CGN Networks**: `{CGN_NETWORK}.0/22` (Carrier-Grade NAT)
- **No MPLS**: Direct customer access without MPLS/VPLS

### **Interface Configuration Standards**

#### **Ethernet Ports - Standardized Assignment**
```routeros
# PORT ASSIGNMENT POLICY (Same for all networks)
# ether1 = Management (ALWAYS)
# sfp-sfpplus1-2 = Switches (Ports 1-2)
# sfp-sfpplus4+ = Backhaul links (starting from port 4)
# sfp-sfpplus6 = LTE gear (if present)
# sfp-sfpplus6-8 = Tarana gear (if present)
# Additional backhauls = Next available ports after port 4

/interface ethernet
# Management port (ALWAYS ether1)
set [find default-name=ether1] comment="MANAGEMENT" 

# Switches (Ports 1-2)
set [find default-name=sfp-sfpplus1] auto-negotiation=no comment="SWITCH-1" speed=1G-baseT-full
set [find default-name=sfp-sfpplus2] auto-negotiation=no comment="SWITCH-2" speed=1G-baseT-full

# Backhaul links (starting from port 4)
set [find default-name=sfp-sfpplus4] auto-negotiation=no comment="BACKHAUL-1" speed=1G-baseT-full
set [find default-name=sfp-sfpplus5] auto-negotiation=no comment="BACKHAUL-2" speed=1G-baseT-full

# LTE gear (if present)
set [find default-name=sfp-sfpplus6] auto-negotiation=no comment="LTE-GEAR" speed=1G-baseT-full

# Tarana gear (if present, ports 6-8)
set [find default-name=sfp-sfpplus7] auto-negotiation=no comment="TARANA-1" speed=1G-baseT-full
set [find default-name=sfp-sfpplus8] auto-negotiation=no comment="TARANA-2" speed=1G-baseT-full

# Additional backhauls (if more than 2)
set [find default-name=sfp-sfpplus9] auto-negotiation=no comment="BACKHAUL-3" speed=1G-baseT-full
set [find default-name=sfp-sfpplus10] auto-negotiation=no comment="BACKHAUL-4" speed=1G-baseT-full
```

#### Bridge Configuration
```routeros
# Non-MPLS bridge setup
/interface bridge
add name=bridge2000
add name=bridge3000
add name=bridge4000
add fast-forward=no name=lan-bridge priority=0x1
add fast-forward=no name=loop0
add name=nat-public-bridge
```

#### VLAN Configuration
```routeros
# Non-MPLS VLAN setup
/interface vlan
add interface=sfp-sfpplus4 name=vlan1000-sfp-sfpplus4 vlan-id=1000
add interface=sfp-sfpplus4 name=vlan2000-sfp-sfpplus4 vlan-id=2000
add interface=sfp-sfpplus4 name=vlan3000-sfp-sfpplus4 vlan-id=3000
add interface=sfp-sfpplus4 name=vlan4000-sfp-sfpplus4 vlan-id=4000
```

### IP Address Assignment

#### Core Network
```routeros
# Non-MPLS loopback
/ip address
add address={NON_MPLS_MGMT_NETWORK}.{ROUTER_ID} comment=Loopback interface=loop0 network={NON_MPLS_MGMT_NETWORK}.{ROUTER_ID}

# Customer networks (on lan-bridge)
add address={CUSTOMER_NETWORK_1}.1/22 comment="CPE/Tower Gear" interface=lan-bridge network={CUSTOMER_NETWORK_1}.0
add address={CUSTOMER_NETWORK_2}.1/22 comment="New CPE Range" interface=lan-bridge network={CUSTOMER_NETWORK_2}.0
add address={CUSTOMER_NETWORK_3}.1/22 comment=Unauth interface=lan-bridge network={CUSTOMER_NETWORK_3}.0
add address={CGN_NETWORK}.1/22 comment="CGN Private" interface=lan-bridge network={CGN_NETWORK}.0

# Backhaul links (starting from port 4)
add address={BACKHAUL_NETWORK_1}.{BACKHAUL_IP}/29 comment="{BACKHAUL_NAME}-1" interface=sfp-sfpplus4 network={BACKHAUL_NETWORK_1}.{BACKHAUL_NETWORK}
add address={BACKHAUL_NETWORK_2}.{BACKHAUL_IP}/29 comment="{BACKHAUL_NAME}-2" interface=sfp-sfpplus5 network={BACKHAUL_NETWORK_2}.{BACKHAUL_NETWORK}
add address={BACKHAUL_NETWORK_3}.{BACKHAUL_IP}/29 comment="{BACKHAUL_NAME}-3" interface=sfp-sfpplus9 network={BACKHAUL_NETWORK_3}.{BACKHAUL_NETWORK}

# Public IPs (if needed)
add address={PUBLIC_IP} comment="CGN Public" interface=nat-public-bridge network={PUBLIC_IP}
```

### **DHCP Configuration**

#### **IP Pools**
```routeros
/ip pool
add name=cpe ranges=10.1.108.50-10.1.111.254
add name=unauth ranges=10.111.60.2-10.111.63.254
add name=cust ranges=100.72.60.3-100.72.63.254

/ip dhcp-server
add address-pool=cust interface=lan-bridge lease-time=1h name=server1 use-radius=yes

/ip dhcp-server network
add address=10.1.108.0/22 dns-server=142.147.112.3,142.147.112.19 gateway=10.1.108.1 netmask=22
add address=10.11.60.0/22 comment="New CPE Range" dns-server=142.147.112.3,142.147.112.19 gateway=10.11.60.1 netmask=22
add address=10.111.60.0/22 dns-server=142.147.112.3,142.147.112.19 gateway=10.111.60.1 netmask=22
add address=100.72.60.0/22 dhcp-option-set=optset dns-server=142.147.112.3,142.147.112.19 gateway=100.72.60.1 netmask=22
```

### **BGP Configuration** (Non-MPLS Networks)
```routeros
/routing bgp template
set default as=26077 disabled=no output.network=bgp-networks router-id=10.1.0.45

/routing bgp connection
add as=26077 cisco-vpls-nlri-len-fmt=auto-bits connect=yes disabled=no listen=yes local.address=10.1.0.45 .role=ibgp multihop=yes name=CR7 output.network=bgp-networks remote.address=10.2.0.107/32 .as=26077 .port=179 router-id=10.1.0.45 routing-table=main tcp-md5-key=m8M5JwvdYM templates=default
add as=26077 connect=yes disabled=no listen=yes local.address=10.1.0.45 .role=ibgp multihop=yes name=CR8 output.network=bgp-networks remote.address=10.2.0.108/32 .as=26077 .port=179 router-id=10.1.0.45 routing-table=main tcp-md5-key=m8M5JwvdYM templates=default
```

**Note**: Non-MPLS networks use BGP for customer route advertisement, while MPLS networks rely on OSPF + MPLS for internal routing.

---

## 🔥 **FIREWALL POLICY STANDARDS**

### **Address Lists**
```routeros
# Management IPs
/ip firewall address-list
add address=192.168.128.0/21 list=managerIP
add address=107.178.5.97 list=managerIP
add address=198.100.53.0/25 list=managerIP
add address=143.55.62.143 list=managerIP
add address=142.147.127.2 list=managerIP
add address=132.147.132.6 list=managerIP
add address=67.219.122.201 list=managerIP
add address=10.249.1.26 list=managerIP

# SNMP Monitoring
add address=107.178.15.15 list=SNMP
add address=107.178.15.162 list=SNMP
add address=142.147.112.4 list=SNMP
add address=142.147.124.26 list=SNMP
add address=107.178.5.97 list=SNMP
add address=67.219.126.240/28 list=SNMP
add address=198.100.53.120 list=SNMP
add address=198.100.49.99 list=SNMP

# BGP Peers
add address=10.0.0.0/8 list=BGP-ALLOW
add address=10.0.0.0/8 list=EOIP-ALLOW

# Netflix Traffic Management
add address=69.53.224.0/19 list=NETFLIX
add address=108.175.32.0/20 list=NETFLIX
add address=192.173.64.0/18 list=NETFLIX
add address=198.38.96.0/19 list=NETFLIX
add address=198.45.48.0/20 list=NETFLIX
add address=208.75.76.0/22 list=NETFLIX
```

### **Filter Rules**
```routeros
# Input Chain
/ip firewall filter
add action=accept chain=input comment="ALLOW EST REL" connection-state=established,related,untracked
add action=accept chain=input comment="ALLOW MT NEIGHBOR" dst-port=5678 protocol=udp
add action=accept chain=input comment="ALLOW MAC TELNET" dst-port=20561 protocol=udp
add action=accept chain=input comment="ALLOW IGMP" protocol=igmp
add action=accept chain=input comment="ALLOW ICMP" protocol=icmp
add action=accept chain=input comment="ALLOW DHCPv4" dst-port=67 protocol=udp
add action=accept chain=input comment="ALLOW DHCPv6" dst-port=547 protocol=udp
add action=accept chain=input comment="ALLOW OVPN" dst-port=1194 protocol=udp
add action=accept chain=input comment="ALLOW OVPN" dst-port=1194 protocol=tcp
add action=accept chain=input comment="ALLOW OSPF" protocol=ospf
add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=tcp
add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=udp
add action=accept chain=input comment="ALLOW MANAGER IP" src-address-list=managerIP
add action=accept chain=input comment="ALLOW BGP" dst-port=179 protocol=tcp src-address-list=BGP-ALLOW
add action=accept chain=input comment="ALLOW EOIP" protocol=gre src-address-list=EOIP-ALLOW
add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=udp src-address-list=SNMP
add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=tcp src-address-list=SNMP
add action=drop chain=input comment="DROP INPUT"
```

---

## 👥 **USER MANAGEMENT STANDARDS**

### **User Groups**
```routeros
/user group
add name=ENG policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api
add name=NOC policy=local,telnet,ssh,ftp,reboot,read,write,test,winbox,password,sniff,sensitive,!policy,!web,!api,!romon,!rest-api
add name=LTE policy=local,telnet,ssh,reboot,read,write,test,winbox,password,sniff,sensitive,!ftp,!policy,!web,!api,!romon,!rest-api
add name=DEVOPS policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api
add name=VOIP policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=STS policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=TECHSUPPORT policy=local,telnet,read,test,winbox,sniff,!ssh,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=INFRA policy=local,telnet,reboot,read,write,test,winbox,!ssh,!ftp,!policy,!password,!web,!sniff,!sensitive,!api,!romon,!rest-api
add name=INSTALL policy=local,telnet,reboot,read,write,test,winbox,!ssh,!ftp,!policy,!password,!web,!sniff,!sensitive,!api,!romon,!rest-api
add name=COMENG policy=local,telnet,ssh,reboot,read,write,test,winbox,sniff,!ftp,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=INTEGRATIONS policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api
add name=IDO policy=local,telnet,ssh,reboot,read,write,test,winbox,password,sniff,sensitive,!ftp,!policy,!web,!api,!romon,!rest-api
add name=CALLCENTER-WRITE policy=local,telnet,ssh,read,write,test,winbox,sniff,!ftp,!reboot,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
```

### **Standard Users**
```routeros
/user
add name=root password=CHANGE_ME group=full
add name=deployment password=CHANGE_ME group=full
add name=infra password=CHANGE_ME group=full
add name=ido password=CHANGE_ME group=full
add name=sts password=CHANGE_ME group=full
add name=eng password=CHANGE_ME group=full
add name=noc password=CHANGE_ME group=full
add name=comeng password=CHANGE_ME group=full
add name=devops password=CHANGE_ME group=full
add name=acq password=CHANGE_ME group=full
```

---

## 📊 **MONITORING & LOGGING STANDARDS**

### **SNMP Configuration**
```routeros
/snmp
set contact=noc@team.nxlink.com enabled=yes location=41.03258,-89.77633

/snmp community
set [find default=yes] read-access=no
add addresses=::/0,132.147.132.26/32,132.147.132.40/32 name=FBZ1yYdphf
```

### **System Logging**
```routeros
/system logging action
set 0 memory-lines=100
set 1 disk-lines-per-file=10000
add name=syslog remote=142.147.116.215 src-address=10.247.0.146 target=remote

/system logging
add action=syslog topics=critical
add action=syslog topics=error
add action=syslog topics=info
add action=syslog topics=warning
add action=disk topics=critical
add action=disk topics=error
add action=disk topics=info
add topics=warning
```

### **NTP Configuration**
```routeros
/system ntp client
set enabled=yes

/system ntp client servers
add address=ntp-pool.nxlink.com
```

---

## 🔧 **SERVICE CONFIGURATION STANDARDS**

### **Service Ports**
```routeros
/ip service
set telnet disabled=yes port=5023
set ftp disabled=yes port=5021
set www disabled=yes port=1234
set ssh port=5022
set www-ssl disabled=no
set api disabled=yes
set api-ssl disabled=yes
```

### **System Identity**
```routeros
/system identity
# MPLS Network naming
set name=RTR-MTCCR2004-1.{STATE}-{LOCATION}-{TYPE}-{NUMBER}

# Non-MPLS Network naming  
set name=RTR-CCR2004-{LOCATION}{NUMBER}
```

### **Clock Settings**
```routeros
/system clock
set time-zone-name=America/Chicago
```

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **Pre-Deployment**
- [ ] Verify device model (CCR2004-1G-12S+2XS)
- [ ] Confirm RouterOS version (7.16.1+)
- [ ] Validate network connectivity
- [ ] Check interface assignments

### **Post-Deployment**
- [ ] Verify OSPF/BGP adjacencies
- [ ] Test SNMP connectivity
- [ ] Validate firewall rules
- [ ] Confirm user access
- [ ] Test backup scripts
- [ ] Verify logging configuration

### **Documentation Requirements**
- [ ] Network diagram
- [ ] IP address assignments
- [ ] Interface descriptions
- [ ] Routing table verification
- [ ] User access matrix

---

## 📝 **NOTES**

### **Network Architecture Differences:**
- **MPLS Network routers** use `10.247.0.0/24` management network with full MPLS/VPLS infrastructure
- **Non-MPLS Network routers** use `10.1.0.0/24` management network with direct customer access
- **MPLS routers** focus on core infrastructure and inter-site connectivity
- **Non-MPLS routers** focus on customer access and local services

### **Routing Protocol Usage:**
- **MPLS Networks**: OSPF + MPLS/LDP for internal routing, VPLS for customer services
- **Non-MPLS Networks**: BGP for customer route advertisement, OSPF for local routing

### **Common Standards:**
- **OSPF authentication** uses MD5 with key `m8M5JwvdYM`
- **BGP authentication** uses TCP-MD5 with key `m8M5JwvdYM`
- **Radius servers** use secret `qmG%Q5k^C06%uLe*`
- **All routers** must have consistent user groups and SNMP communities
- **Backup scripts** run daily at 00:00 with FTP upload to `backup.nxlink.com`

This policy ensures consistent, secure, and maintainable router configurations across all Nextlink deployments, with clear distinctions between MPLS core infrastructure and customer access networks.

---

## ROUTEROS VERSION MIGRATION GUIDE

### RouterOS v6 to v7 Migration
When upgrading from RouterOS v6 to v7, the following syntax changes must be applied:

**BGP Configuration Migration:**
```routeros
# RouterOS v6 (Legacy)
/routing bgp peer
add name=CR7 remote-address=x.x.x.x remote-as=26077 tcp-md5-key=m8M5JwvdYM

# RouterOS v7 (Current) - Based on live CCR2004 configuration
/routing bgp template
set default as=26077 disabled=no multihop=yes output.network=bgp-networks router-id=x.x.x.x routing-table=main

/routing bgp connection
add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address=x.x.x.x .role=ibgp multihop=yes name=CR7 output.network=bgp-networks remote.address=x.x.x.x .as=26077 .port=179 router-id=x.x.x.x routing-table=main tcp-md5-key=m8M5JwvdYM templates=default
```

**OSPF Configuration Migration:**
```routeros
# RouterOS v6 (Legacy)
/routing ospf network
add area=backbone network=x.x.x.x/32

# RouterOS v7 (Current) - Based on live CCR2004 configuration
/routing ospf instance
add disabled=no name=default-v2 router-id=x.x.x.x

/routing ospf area
add disabled=no instance=default-v2 name=area0

/routing ospf interface-template
add area=area0 cost=10 disabled=no interfaces=loop0 networks=x.x.x.x/32 passive priority=1
add area=area0 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment="BACKHAUL-1" cost=10 disabled=no interfaces=sfp-sfpplus4 networks=x.x.x.x/29 priority=1 type=ptp
add area=area0 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment="BACKHAUL-2" cost=10 disabled=no interfaces=sfp-sfpplus5 networks=x.x.x.x/29 priority=1 type=ptp
```

**MPLS Configuration Migration:**
```routeros
# RouterOS v6 (Legacy)
/mpls ldp interface
add interface=sfp-sfpplus4

# RouterOS v7 (Current) - Based on live CCR2004 configuration
/mpls ldp interface
add comment="BACKHAUL-1" disabled=no interface=sfp-sfpplus4
add comment="BACKHAUL-2" disabled=no interface=sfp-sfpplus5
add comment="BACKHAUL-3" interface=sfp-sfpplus10
```

**Non-MPLS Configuration Migration:**
```routeros
# RouterOS v6 (Legacy) - Non-MPLS
/routing ospf interface
add authentication=md5 authentication-key=m8M5JwvdYM comment="BACKHAUL" interface=ether1 network-type=point-to-point

/routing ospf network
add area=backbone comment=loop0 network=x.x.x.x/32
add area=backbone comment="CPE/Tower Gear" network=x.x.x.x/22

# RouterOS v7 (Current) - Non-MPLS
/routing ospf instance
add disabled=no name=default-v2 router-id=x.x.x.x

/routing ospf area
add disabled=no instance=default-v2 name=area0

/routing ospf interface-template
add area=area0 cost=10 disabled=no interfaces=loop0 networks=x.x.x.x/32 passive priority=1
add area=area0 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment="BACKHAUL" cost=10 disabled=no interfaces=ether1 networks=x.x.x.x/29 priority=1 type=ptp
```

### Router Model Migration
When migrating between router models (CCR1036 to CCR2004, etc.):

1. **Port Assignment**: Maintain the same logical port assignments
2. **Performance**: Adjust queue configurations based on hardware capabilities
3. **Features**: Enable/disable features based on model specifications
4. **Licensing**: Ensure proper licensing for advanced features

### Configuration Validation
Before deploying any configuration:
1. **Syntax Check**: Validate RouterOS syntax for target version
2. **Port Mapping**: Verify port assignments match hardware
3. **Network Reachability**: Test connectivity to management networks
4. **Feature Compatibility**: Validate advanced features are supported

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Router model compatibility verified
- [ ] RouterOS version compatibility confirmed
- [ ] Network IP ranges allocated
- [ ] Port assignments planned
- [ ] Site-specific requirements identified

### Configuration
- [ ] Device naming convention applied
- [ ] Port assignments configured
- [ ] IP addresses assigned
- [ ] Routing protocols configured
- [ ] Security policies applied
- [ ] User groups created
- [ ] SNMP configured
- [ ] Backup scripts scheduled

### Post-Deployment
- [ ] Connectivity testing completed
- [ ] Performance monitoring enabled
- [ ] Backup verification successful
- [ ] Documentation updated
- [ ] Team training completed
