# RouterOS LIPAN-SW Baseline Configuration Policy

## Purpose
This policy defines the authoritative template for generating RouterOS 7.x configurations based on the LIPAN-SW baseline. The LLM backend uses this policy to generate site-specific configurations by substituting runtime-provided values while preserving the baseline structure and all static commands.

## Required Input Schema

All inputs must be provided as JSON, table, or natural language with unambiguous keys:

| Key | Type | Required | Description | Example |
| --- | --- | --- | --- | --- |
| `device_name` | string | ✅ Yes | Router identity (appears in `/system identity set name=`). Must follow format: `RTR-<MODEL>-<SITE>` | `RTR-MT2004-AR1.TX-CONFIG-POLICY-CN-1` |
| `time_zone` | string | ✅ Yes | IANA time-zone name for `/system clock set time-zone-name=`. | `America/Chicago` |
| `loopback` | object | ✅ Yes | `{ "ip": "x.x.x.x" }` — treated as a /32. This IP is used in MULTIPLE critical places (see below). | `{ "ip": "10.1.1.1" }` |
| `cpe_scope` | object | ✅ Yes | `{ "cidr": "a.b.c.d/yy", "pool_range": "start-end" }`. CPE/Tower gear network. | `{ "cidr": "10.10.10.0/24", "pool_range": "10.10.10.50-10.10.10.254" }` |
| `unauth_scope` | object | ✅ Yes | `{ "cidr": "a.b.c.d/yy", "pool_range": "start-end" }`. Unauthenticated guest network. | `{ "cidr": "10.100.10.0/24", "pool_range": "10.100.10.2-10.100.10.254" }` |
| `cgnat_private_scope` | object | ✅ Yes | `{ "cidr": "a.b.c.d/yy", "pool_range": "start-end" }`. CGNAT private pool range. | `{ "cidr": "100.64.0.0/22", "pool_range": "100.64.0.3-100.64.3.254" }` |
| `cgnat_public_ip` | string | ✅ Yes | Public CGNAT address (no mask, /32 implied). | `132.147.147.255` |
| `bridge3000_ips` | array | ✅ Yes | Each entry: `{ "label": "UNICORN MGMT", "cidr": "a.b.c.d/yy" }`. Management bridge IPs. | `[{ "label": "BRIDGE3000 MGMT", "cidr": "10.30.30.1/28" }]` |
| `dhcp_dns_servers` | array | ✅ Yes | DNS servers to apply to all DHCP scopes (typically two values). | `["4.2.2.2", "8.8.8.8"]` |
| `radius_servers` | array | ✅ Yes | Each entry: `{ "address": "ip", "secret": "string" }`. RADIUS server configuration. | `[{ "address": "142.147.112.8", "secret": "Nl22021234" }, { "address": "142.147.112.20", "secret": "Nl22021234" }]` |
| `tower_links` | array | ⚠️ Optional | Each entry: `{ "interface": "sfp-sfpplusN", "name": "TX-TOWER-NAME", "cidr": "a.b.c.d/yy", "local_ip": "x.x.x.x" }`. Tower uplink connections. | `[{ "interface": "sfp-sfpplus4", "name": "TX-NEXTTOWER-CN-1", "cidr": "10.20.20.0/29", "local_ip": "10.20.20.1" }]` |

**Note:** If additional DHCP scopes are supplied, follow the same structure as `cpe_scope`.

## Critical Parameter Usage Map

### Loopback IP (`loopback.ip`) - CRITICAL: Used in 10+ Places

The loopback IP address is the **MOST IMPORTANT** parameter. It must appear **identically** in ALL of these locations:

1. **Interface Address**
   - `/ip address add address={loopback.ip}/32 comment=loop0 interface=loop0 network={loopback.ip}`

2. **BGP Router ID**
   - `/routing bgp template set default ... router-id={loopback.ip}`

3. **OSPF Router ID**
   - `/routing ospf instance add ... router-id={loopback.ip}`

4. **BGP Connection Local Address**
   - `/routing bgp connection add ... local.address={loopback.ip}`

5. **OSPF Interface Template (Loopback)**
   - `/routing ospf interface-template add ... interfaces=loop0 networks={loopback.ip}/32`

6. **System Logging Source Address**
   - `/system logging action add ... src-address={loopback.ip}`

7. **RADIUS Source Address** (ALL radius servers)
   - `/radius add ... src-address={loopback.ip}`

8. **SNMP Source Address**
   - `/snmp set ... src-address={loopback.ip}`

9. **Queue Tree (if present)**
   - Any queue-tree rules referencing loopback

10. **Any other routing/management references**

**VALIDATION RULE:** Every occurrence of the loopback IP in the baseline template must be replaced with the provided `loopback.ip` value. The loopback IP must NEVER be used for any other interface address.

### Device Name (`device_name`)

Replace `/system identity set name=` with the provided device name. Preserve the exact format but update the site identifier.

**Example:** 
- Baseline: `/system identity set name=RTR-MT2004-AR1.TX-LIPAN-SW-1`
- Generated: `/system identity set name={device_name}`

### Time Zone (`time_zone`)

Substitute the value in `/system clock set time-zone-name=`. Must be a valid IANA timezone identifier.

**Example:**
- `/system clock set time-zone-name={time_zone}`

### CPE Scope (`cpe_scope`)

This network provides connectivity for CPE/Tower gear. Apply the CIDR and pool range to:

1. **Interface Address**
   - `/ip address add address={cpe_scope.cidr} comment="CPE/Tower Gear" interface=lan-bridge network={calculated_network}`

2. **DHCP Pool**
   - `/ip pool add name=cpe ranges={cpe_scope.pool_range}`

3. **DHCP Server Network**
   - `/ip dhcp-server network add address={cpe_scope.cidr} dns-server={dhcp_dns_servers} gateway={gateway_ip} netmask={netmask}`
   - Gateway IP = first IP in the CIDR (e.g., 10.10.10.0/24 → gateway = 10.10.10.1)

4. **OSPF Interface Template**
   - `/routing ospf interface-template add ... interfaces=lan-bridge networks={cpe_scope.cidr} ...`

### Unauth Scope (`unauth_scope`)

This network provides unauthenticated guest access. Apply to:

1. **Interface Address**
   - `/ip address add address={unauth_scope.cidr} comment=UNAUTH interface=lan-bridge network={calculated_network}`

2. **DHCP Pool**
   - `/ip pool add name=unauth ranges={unauth_scope.pool_range}`

3. **DHCP Server Network**
   - `/ip dhcp-server network add address={unauth_scope.cidr} dns-server={dhcp_dns_servers} gateway={gateway_ip} netmask={netmask}`

4. **Firewall Address List (BGP Networks)**
   - `/ip firewall address-list add address={unauth_scope.cidr} comment=UNAUTH list=bgp-networks`

### CGNAT Private Scope (`cgnat_private_scope`)

This network provides CGNAT private addressing. Apply to:

1. **Interface Address**
   - `/ip address add address={cgnat_private_scope.cidr} comment="CGNAT Private" interface=lan-bridge network={calculated_network}`

2. **DHCP Pool**
   - `/ip pool add name=cust ranges={cgnat_private_scope.pool_range}`

3. **DHCP Server Network** (with option set)
   - `/ip dhcp-server network add address={cgnat_private_scope.cidr} dhcp-option-set=*1 dns-server={dhcp_dns_servers} gateway={gateway_ip} netmask={netmask}`

4. **Firewall Address List (BGP Networks)**
   - `/ip firewall address-list add address={cgnat_private_scope.cidr} comment=CGNAT_PRIVATE list=bgp-networks`

### CGNAT Public IP (`cgnat_public_ip`)

This is the public IP used for NAT. Apply to:

1. **Interface Address** (on nat-public-bridge, no mask needed)
   - `/ip address add address={cgnat_public_ip} comment="CGNAT Public" interface=nat-public-bridge network={cgnat_public_ip}`

2. **Firewall Address List**
   - `/ip firewall address-list add address={cgnat_public_ip} comment=CGNAT_PUBLIC list=bgp-networks`

### Bridge3000 IPs (`bridge3000_ips`)

Management bridge IPs. For each entry in the array:

1. **Interface Address**
   - `/ip address add address={entry.cidr} comment={entry.label} interface=bridge3000 network={calculated_network}`

2. **OSPF Interface Template**
   - `/routing ospf interface-template add ... comment={entry.label} ... interfaces=bridge3000 networks={entry.cidr} ...`

**IMPORTANT:** The number of OSPF interface-templates for bridge3000 must match the number of entries in `bridge3000_ips`.

### DHCP DNS Servers (`dhcp_dns_servers`)

Apply uniformly to every `/ip dhcp-server network add` entry. Format as comma-separated list in the `dns-server=` parameter.

**Example:**
- `dns-server=4.2.2.2,8.8.8.8`

**Note:** Maintain option sets (e.g., `dhcp-option-set=*1`) when present in the baseline for CGNAT scopes.

### RADIUS Servers (`radius_servers`)

For each entry in the array, create a `/radius add` line:

```
/radius add address={entry.address} secret={entry.secret} service=dhcp src-address={loopback.ip} timeout=5s
```

**CRITICAL:** Every radius server MUST use `loopback.ip` as the `src-address`. Never use any other IP address.

### Tower Links (`tower_links`) - NEW

Tower uplink connections to other sites. For each entry:

1. **Interface Comment**
   - `/interface ethernet set [ find default-name={entry.interface} ] comment={entry.name}`

2. **Interface Address**
   - `/ip address add address={entry.local_ip}/{subnet_mask} comment={entry.name} interface={entry.interface} network={calculated_network}`
   - **IP Allocation Rule:** The local IP should be positioned to leave room for backhaul radios:
     - For a /29 subnet (8 IPs total):
       - Remote gateway: `.1` (reserved)
       - Radio 1: `.2`
       - Radio 2: `.3`
       - Local router: `.4` or higher
     - Example: `10.5.5.0/29` → local IP should be `10.5.5.4` (leaving .1-.3 for remote/radios)

3. **OSPF Interface Template** (Point-to-Point with MD5 auth)
   - `/routing ospf interface-template add area=backbone-v2 auth=md5 auth-id=1 auth-key={auth_key} comment={entry.name} cost=10 disabled=no interfaces={entry.interface} networks={entry.cidr} priority=1 type=ptp`
   - **Auth Key:** Use the standard MD5 key from baseline (typically `m8M5JwvdYM`)

## Baseline Structure Preservation

The following sections must be preserved EXACTLY as they appear in the baseline (unless parameterized):

1. **Interface Bridges** - All bridge definitions (bridge2000, bridge3000, bridge4000, lan-bridge, loop0, nat-public-bridge)
2. **Interface Ethernet Settings** - Port comments, speed settings, auto-negotiation
3. **Bonding Interfaces** - If present, preserve bonding configurations
4. **VLAN Interfaces** - All VLAN definitions
5. **DHCP Server Options** - Option 43 and option sets
6. **Port Configuration** - Serial port names
7. **Queue Types** - pfifo-limit settings
8. **BGP Template** - Structure (router-id parameterized)
9. **OSPF Instance** - Structure (router-id parameterized)
10. **OSPF Area** - backbone-v2 area definition
11. **SNMP Community** - Community settings (except src-address)
12. **System Logging Actions** - Disk logging actions
13. **User Groups** - All user group definitions
14. **IP Neighbor Discovery** - Settings
15. **OVPN Server** - MAC address and server config
16. **Firewall Rules** - All filter, NAT, and raw rules (preserve structure)
17. **IP Services** - Service port configurations
18. **IPSec Profiles** - Profile settings
19. **SMB Shares** - Directory settings
20. **MPLS LDP** - All accept-filter and advertise-filter rules
21. **BGP Connections** - Connection definitions (local.address parameterized)
22. **Routing Filter Rules** - BGP in-filter rules
23. **System NTP** - NTP client settings
24. **System Routerboard** - Auto-upgrade settings
25. **Tool ROMON** - ROMON settings

## Output Expectations

1. **RouterOS CLI Format**
   - Produce commands compatible with `/import file-name=`
   - One command per line
   - Preserve comment structure

2. **Ordering**
   - Maintain the exact section ordering from the baseline
   - Only change parameterized values
   - Preserve all static commands

3. **Derived Values**
   - Calculate gateways from CIDR (first IP in subnet)
   - Calculate network addresses from CIDR
   - Calculate netmasks from CIDR prefix length

4. **Consistency**
   - Loopback IP must match everywhere
   - CIDR values must be consistent across address, pool, DHCP, OSPF, and firewall rules
   - Pool ranges must be within the CIDR subnet

5. **Comments**
   - Preserve all baseline comments
   - Add comments for clarity where parameterized values are used

## Validation Checklist

Before returning the configuration, verify:

1. ✅ **Loopback IP Consistency**
   - [ ] Loopback IP appears in ALL 10+ required locations
   - [ ] Loopback IP is NOT used for any other interface
   - [ ] Loopback IP is unique and not conflicting

2. ✅ **CIDR Alignment**
   - [ ] Gateway IP is the first IP in each CIDR subnet
   - [ ] Pool ranges are within their respective CIDR subnets
   - [ ] Network addresses match CIDR base

3. ✅ **DHCP Consistency**
   - [ ] Pool names match DHCP server network names (`cpe`, `unauth`, `cust`)
   - [ ] DNS servers are applied to all DHCP networks
   - [ ] Option sets are preserved where required

4. ✅ **OSPF Templates**
   - [ ] Bridge3000 OSPF templates match the count of `bridge3000_ips`
   - [ ] Tower link OSPF templates match the count of `tower_links`
   - [ ] All OSPF templates use correct network addresses

5. ✅ **Tower Links**
   - [ ] Local IPs are positioned correctly (not conflicting with remote/radios)
   - [ ] OSPF point-to-point templates are created for each link
   - [ ] Interface comments match tower link names

6. ✅ **Firewall Address Lists**
   - [ ] Unauth scope is in `bgp-networks` list
   - [ ] CGNAT private scope is in `bgp-networks` list
   - [ ] CGNAT public IP is in `bgp-networks` list with `CGNAT_PUBLIC` comment

7. ✅ **RADIUS Configuration**
   - [ ] All radius servers use `loopback.ip` as `src-address`
   - [ ] All radius servers have correct addresses and secrets

8. ✅ **Output Quality**
   - [ ] No unresolved placeholders or braces
   - [ ] All commands are valid RouterOS syntax
   - [ ] Config is ready for `/import` command

## Example Usage

```json
{
  "device_name": "RTR-MT2004-AR1.TX-CONFIG-POLICY-CN-1",
  "time_zone": "America/Chicago",
  "loopback": { "ip": "10.1.1.1" },
  "cpe_scope": { "cidr": "10.10.10.0/24", "pool_range": "10.10.10.50-10.10.10.254" },
  "unauth_scope": { "cidr": "10.100.10.0/24", "pool_range": "10.100.10.2-10.100.10.254" },
  "cgnat_private_scope": { "cidr": "100.64.0.0/22", "pool_range": "100.64.0.3-100.64.3.254" },
  "cgnat_public_ip": "132.147.147.255",
  "bridge3000_ips": [{ "label": "BRIDGE3000 MGMT", "cidr": "10.30.30.1/28" }],
  "dhcp_dns_servers": ["4.2.2.2", "8.8.8.8"],
  "radius_servers": [
    { "address": "142.147.112.8", "secret": "Nl22021234" },
    { "address": "142.147.112.20", "secret": "Nl22021234" }
  ],
  "tower_links": [
    { "interface": "sfp-sfpplus4", "name": "TX-NEXTTOWER-CN-1", "cidr": "10.20.20.0/29", "local_ip": "10.20.20.1" },
    { "interface": "sfp-sfpplus5", "name": "TX-NEXTTOWER-CN-3", "cidr": "10.5.5.0/29", "local_ip": "10.5.5.4" }
  ]
}
```

## Backend Integration

This policy is designed to be loaded by the LLM backend from the `config_policies/lipan-sw/` directory. The backend should:

1. Load this policy file when generating LIPAN-SW configurations
2. Validate input parameters against the schema
3. Apply the parameter usage map to generate the configuration
4. Run the validation checklist before returning the output
5. Report any validation failures with specific line numbers/reasons

## Version

- **Policy Version:** 1.0
- **Last Updated:** 2025-11-05
- **RouterOS Version:** 7.x
- **Baseline Reference:** LIPAN-SW-1.rsc

---

**Use this policy as the authoritative reference when generating site-specific RouterOS configurations.**

