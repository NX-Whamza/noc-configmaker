# TEXAS TOWER NON-MPLS CONFIG POLICY

## Purpose
Defines the standard RouterOS configuration pattern for Texas non-MPLS tower routers. The policy abstracts the LIPAN baseline so the generator can build site-specific configs while preserving bridge layout, DHCP scopes, Radius profile, firewall hardening, and compliance controls.

## Required Input Schema

| Key | Type | Required | Description | Example |
| --- | --- | --- | --- | --- |
| `device_name` | string | Yes | `/system identity set name=` (format `RTR-<MODEL>-<SITE>`). | `RTR-MT2004-AR1.TX-LIPAN-SW-1` |
| `time_zone` | string | Yes | IANA timezone for `/system clock set time-zone-name=`. | `America/Chicago` |
| `loopback.ip` | string | Yes | Loopback IPv4 (treated as /32). | `10.1.1.1` |
| `cpe_scope` | object | Yes | `{ "cidr": "a.b.c.d/yy", "pool_range": "start-end" }` for CPE customers. | `{ "cidr": "10.10.10.0/24", "pool_range": "10.10.10.50-10.10.10.254" }` |
| `unauth_scope` | object | Yes | Guest network with same structure as `cpe_scope`. | `{ "cidr": "10.100.10.0/24", "pool_range": "10.100.10.2-10.100.10.254" }` |
| `cgnat_private_scope` | object | Yes | CGNAT private pool definition. | `{ "cidr": "100.64.0.0/22", "pool_range": "100.64.0.3-100.64.3.254" }` |
| `cgnat_public_ip` | string | Yes | Public CGNAT address (no mask). | `132.147.147.255` |
| `bridge3000_ips` | array<object> | Yes | Management bridge entries `{ "label": "MGMT", "cidr": "a.b.c.d/yy" }`. | `[ { "label": "BRIDGE3000 MGMT", "cidr": "10.30.30.1/28" } ]` |
| `dhcp_dns_servers` | array<string> | Yes | DNS servers applied to DHCP networks. | `["4.2.2.2","8.8.8.8"]` |
| `radius_servers` | array<object> | Yes | Radius nodes `{ "address": "ip", "secret": "string" }`. | `[ {"address":"142.147.112.8","secret":"Nl22021234"} ]` |
| `tower_links` | array<object> | No | Tower uplinks `{ "interface": "sfp-sfpplus4", "name": "TX-TOWER", "cidr": "a.b.c.d/yy", "local_ip": "x.x.x.x" }`. | `[ {"interface":"sfp-sfpplus4","name":"TX-NEXTTOWER-CN-1","cidr":"10.20.20.0/29","local_ip":"10.20.20.1"} ]` |
| `additional_dhcp_scopes` | array<object> | No | Extra DHCP scopes matching `cpe_scope` structure. | `[ {"cidr":"10.200.10.0/24","pool_range":"10.200.10.10-10.200.10.200"} ]` |
| `firewall_overrides` | object | No | Supplemental address-lists or filter rules appended after compliance. | `{ "address_lists": [ {"list":"mgmt-allow","address":"192.0.2.0/24"} ] }` |

## Baseline Components

## Port Role Standards
- Follow the universal port assignments defined in 
extlink-internet-policy.md:`n  - ether1 reserved for management/out-of-band access.
  - sfp-sfpplus1 and sfp-sfpplus2 provide switch uplinks.
  - sfp-sfpplus4+ handle tower/backhaul connectivity in ascending order.
  - Reserve sfp-sfpplus6 for LTE equipment and sfp-sfpplus6-8 for Tarana when deployed.
- Maintain descriptive comment= values for every interface so audits can verify role alignment.

## Critical Parameter Usage Map

### Loopback (`loopback.ip`)
- `/ip address add address={loopback.ip}/32 comment=loop0 interface=loop0 network={loopback.ip}`
- `/routing ospf instance set [ find default=yes ] router-id={loopback.ip}`
- `/routing bgp template set default router-id={loopback.ip}` (if BGP enabled)
- `/system logging action add name=syslog remote=<syslog-ip> src-address={loopback.ip}`
- `/radius add ... src-address={loopback.ip}` and `/snmp set ... src-address={loopback.ip}`

### DHCP Scopes
- For each scope (`cpe_scope`, `unauth_scope`, `cgnat_private_scope`, `additional_dhcp_scopes`):
  - Add interface address on the appropriate bridge.
  - Create `/ip pool` entries using `pool_range`.
  - Add `/ip dhcp-server network` entries with gateway (first usable IP), DNS from `dhcp_dns_servers`, and netmask derived from CIDR.
  - Include relevant CIDRs in firewall address-lists if required by the baseline.

### CGNAT Public IP (`cgnat_public_ip`)
- Applied in NAT rules that translate customer traffic to the public address.

### Management Addresses (`bridge3000_ips`)
- Iterate entries and add `/ip address add address={cidr} interface=bridge3000 comment={label}`.

### Radius Servers (`radius_servers`)
- `/radius add address={address} secret={secret} service=ppp,login,hotspot,wireless src-address={loopback.ip}` for each server.

### Tower Links (`tower_links`)
- Update interface comment: `/interface ethernet set [ find default-name={interface} ] comment={name}`.
- Assign tower addressing: `/ip address add address={cidr} comment={name} interface={interface} network={calculated_network}`.

### Firewall Overrides (`firewall_overrides`)
- Append any additional address-lists, filter rules, or NAT statements after compliance blocks while avoiding duplicates.

## Firewall Baseline
- Incorporate firewall rules defined in `nextlink-internet-policy.md` and RFC-09-10-25 compliance:
  - Input chain allows established/related/untracked, MT discovery (UDP 5678), MAC Telnet (UDP 20561), IGMP, ICMP, DHCPv4/v6, OSPF, LDP, manager IP list, BGP (TCP 179) and SNMP (UDP/TCP 161) before dropping the remainder.
  - Forward chain accepts BGP and GRE between 10.0.0.0/8 networks, fasttracks established/related traffic, then drops unauthenticated traffic not in the walled garden.
  - NAT rules include SSH redirect (local port 5022 to 22) and unauth proxy redirection (TCP 80 to 107.178.15.27:3128).
  - Raw table drops UDP port 0 to mitigate malformed traffic.
- Extend with optional overrides supplied via `firewall_overrides` after compliance blocks.

## Compliance Requirements
- Enforce RFC-09-10-25 settings: disable Telnet/FTP/WWW, configure SSH redirect, enable HTTPS, set DNS to compliance servers, and include the approved firewall address-lists (EOIP-ALLOW, managerIP, BGP-ALLOW, SNMP).
- Apply firewall filter baseline (input allows, forward fasttrack/unauth drop) and NAT/RAW adjustments (SSH redirect, unauth proxy, drop bad UDP).
- Include SNMP cleanup, NTP client configuration, and system watchdog/routerboard settings.
- Ensure compliance blocks appear exactly once; backend normalization will deduplicate if necessary.

## Output Assembly Order
1. `/system identity` and `/system clock`
2. `/interface bridge` definitions and `/interface ethernet` comments
3. Tower link configuration
4. `/ip address` assignments (loopback, bridges, tower links)
5. `/ip pool`, `/ip dhcp-server`, `/ip dhcp-server network`
6. `/radius`, `/snmp`, `/system logging action`
7. `/routing ospf` and optional `/routing bgp`
8. `/ip firewall address-list`, `/ip firewall filter`, `/ip firewall nat`, `/ip firewall raw`
9. Compliance service settings and remaining system directives

## Validation Checklist
- Loopback IP referenced in address, OSPF, logging, Radius, SNMP, and optional BGP.
- DHCP pools and networks align with provided CIDRs and ranges.
- CGNAT public IP appears in NAT entries as required.
- Radius servers use supplied secrets and loopback source address.
- Tower link interface comments and addresses match inputs without duplication.
- Compliance blocks (services, firewall, SNMP, NTP) are present exactly once.

## Generation Instructions (LLM)
1. Consume inputs matching the schema above.
2. Produce the RouterOS configuration following the Output Assembly Order.
3. Prefer RouterOS 7.x syntax; only emit legacy constructs if `routeros_version` mandates it.
4. Enforce compliance and avoid duplicate commands (normalization runs afterwards).
5. Output plain RouterOS CLI with one command per line and preserve required `comment=` annotations.