# KANSAS OUT-OF-STATE MPLS CONFIG POLICY

## Purpose
Provides the RouterOS baseline for Kansas MPLS/VPLS aggregation routers. The policy generalizes the KS-BENTON example so the generator can produce dynamic configs that maintain bridge layout, VPLS mesh, MPLS/LDP behaviour, DHCP options, compliance hardening, and optional BGP peers.

## Required Input Schema

| Key | Type | Required | Description | Example |
| --- | --- | --- | --- | --- |
| `device_name` | string | Yes | `/system identity set name=` (format `RTR-<MODEL>-<SITE>`). | `RTR-MT1036-AR1.KS-BENTON-SW-1` |
| `routeros_version` | string | Yes | Target RouterOS version (prefer 7.x). | `7.19.4` |
| `loopback.ip` | string | Yes | Loopback IPv4; treated as /32. | `10.248.0.53` |
| `syslog.ip` | string | Yes | Remote syslog collector. | `142.147.116.215` |
| `switch_uplinks` | array<object> | Yes | Ordered list `{ "port": "ether1", "comment": "Netonix Uplink #1" }`. | `[ {"port":"ether1","comment":"Netonix Uplink #1"}, {"port":"ether2","comment":"Netonix Uplink #2"} ]` |
| `backhauls` | array<object> | Yes | Backhaul entries `{ "port": "ether5", "cidr": "x.x.x.x/yy", "comment": "REMOTE-SITE" }`. | `[ {"port":"ether5","cidr":"10.248.3.6/30","comment":"KS-FURLEY-CN-1"} ]` |
| `sfp_overrides` | array<object> | No | Port overrides `{ "port": "sfp3", "auto_negotiation": false, "mtu": 9200 }`. | `[ {"port":"sfp3","auto_negotiation":false} ]` |
| `vpls.domains` | array<object> | Yes | Domain VPLS `{ "name": "vpls1000-bng-ks", "bridge": "bridge1000", "peer": "10.249.0.200", "static_id": 1248 }`. | `[ {"name":"vpls1000-bng-ks","bridge":"bridge1000","peer":"10.249.0.200","static_id":1248} ]` |
| `vpls.mesh_links` | array<object> | No | Additional mesh peers (dual BNG) `{ "name": "vpls-bng1", "bridge": "vpls-bridge", "peer": "10.248.0.3", "static_id": 3 }`. | `[ {"name":"vpls-bng1","bridge":"vpls-bridge","peer":"10.248.0.3","static_id":3} ]` |
| `mpls.ldp` | object | Yes | `{ "lsr_id": "loopback.ip", "transport_addresses": ["loopback.ip"], "mpls_mtu": 9000, "accept_filters": { "deny": [ ... ], "permit": [ ... ] } }`. | see example |
| `dns.servers` | array<string> | Yes | Compliance DNS pair. | `["142.147.112.3","142.147.112.19"]` |
| `snmp.community` | string | Yes | Compliance SNMP community. | `FBZ1yYdphf` |
| `dhcp.option43_hex` | string | No | Hex payload for Option 43 (omit if unused). | `0x011768747470733a2f2f7573732e6e786c696e6b2e636f6d2f` |
| `dhcp.additional_scopes` | array<object> | No | Extra DHCP scopes `{ "name": "bridge800", "cidr": "x.x.x.x/yy", "pool": "start-end", "gateway": "x.x.x.x" }`. | `[ {"name":"bridge800","cidr":"10.248.8.0/24","pool":"10.248.8.10-10.248.8.200","gateway":"10.248.8.1"} ]` |
| `bgp` | object | No | `{ "asn": 26077, "router_id": "loopback.ip", "peers": [ {"name":"BNG-KS","remote_as":26077,"remote_address":"10.248.0.3","md5":"secret"} ] }`. | see example |
| `firewall.overrides` | object | No | Additional address-lists/filters appended after compliance. | `{ "address_lists": [ {"list":"mgmt-allow","address":"192.0.2.0/24"} ] }` |

## Baseline Components

## Port Role Standards
- Reference 
extlink-internet-policy.md for universal port assignments:
  - ether1 and ether2 act as management-facing switch uplinks and may join the VPLS mesh (pls-bridge).
  - ether5 and higher are reserved for tower/backhaul connectivity and should be labelled sequentially.
  - Reserve sfp-sfpplus6 for LTE gear and sfp-sfpplus6-8 for Tarana deployments when present.
  - Maintain descriptive comment= fields on every port so audits confirm role compliance.
- Ensure bridge membership reflects the statewide design (vendor bridges 600/800 vs Nextlink bridges 1000/2000/3000/4000).

## Critical Parameter Usage Map

### Loopback (`loopback.ip`)
- `/ip address add address={loopback.ip}/32 interface=loop0 network={loopback.ip}`
- `/routing ospf instance add name=default-v2 router-id={loopback.ip}`
- `/system logging action add name=syslog remote={syslog.ip} src-address={loopback.ip}`
- `/mpls ldp add lsr-id={loopback.ip} transport-addresses={loopback.ip}`

### Switch Uplinks (`switch_uplinks`)
- `/interface ethernet set [ find default-name={port} ] comment={comment} l2mtu=9212`
- If uplinks participate in mesh bridging, `/interface bridge port add bridge=vpls-bridge interface={port}`

### Backhauls (`backhauls`)
- Configure interface comments and MTUs.
- `/ip address add address={cidr} interface={port} network={calculated_network} comment={comment}`
- Include any required firewall or routing references per site standards.

### VPLS (`vpls.domains`, `vpls.mesh_links`)
- Create VPLS interfaces with provided names, peers, static IDs, and optional comments.
- Attach each interface to the specified bridge using `/interface bridge port` with `ingress-filtering=no edge=yes horizon=1`.

### MPLS / LDP (`mpls.ldp`)
- `/mpls interface add interface=all mpls-mtu={mpls_mtu}` (include `input=yes` if ROS 6 compatibility required).
- `/mpls ldp add lsr-id={lsr_id} transport-addresses={transport_addresses} hop-limit=255 distribute-for-default=no`
- Apply deny filters first, then permit filters, using the supplied prefix lists.

### DNS & Syslog (`dns.servers`, `syslog.ip`)
- `/ip dns set servers={dns.servers[0]},{dns.servers[1]}`
- Syslog action uses `src-address={loopback.ip}` and `remote={syslog.ip}`.

### SNMP (`snmp.community`)
- Remove default community, then add new community with global access unless a tighter scope is provided..

### Firewall Overrides (`firewall.overrides`)
- Append extra address-lists or filter rules **after** compliance blocks, avoiding duplication with existing entries.

## Firewall Baseline
- Incorporate the statewide firewall posture in addition to RFC-09-10-25 compliance:
  - Input chain allows established/related/untracked traffic, MikroTik discovery (UDP 5678), MAC Telnet (UDP 20561), IGMP/ICMP, DHCPv4/v6, OSPF, LDP, manager IP list, BGP (TCP 179), and SNMP before dropping remaining input packets.
  - Forward chain permits BGP and GRE between 10.0.0.0/8 networks, fasttracks established/related/untracked sessions, then drops traffic from the `unauth` list that is not in the walled garden.
  - NAT rules include SSH redirect (TCP 5022 to 22) and unauth proxy redirection (TCP 80 to 107.178.15.27:3128) in addition to site-specific NAT.
  - Raw table drops malformed UDP port 0 to match compliance expectations.
- Any custom overrides supplied in `firewall.overrides` should append after these baseline rules without duplication.

## Compliance Requirements
- Include RFC-09-10-25 settings for IP services, firewall address-lists, filter baseline, NAT/RAW adjustments, SNMP cleanup, NTP client, and system watchdog/routerboard configuration.
- Ensure SSH redirect, unauth proxy, and drop rules are present once.
- Use compliance DNS servers exactly as provided (142.147.112.3 and 142.147.112.19).

## Output Assembly Order
1. `/interface bridge` definitions (600/800/1000/2000/3000/4000, vpls-bridge, loop0)
2. `/interface ethernet` role assignments and SFP overrides
3. `/interface vpls` definitions (mesh plus domain-specific)
4. Optional bonding/VLAN sections if inputs require them
5. `/interface bridge port` mappings for uplinks and VPLS interfaces
6. `/ip address` entries (loopback, backhauls, VLANs)
7. DHCP option/pool/network configuration (only if supplied)
8. `/ip dns`, `/system logging action`, `/ip service`
9. `/routing ospf` (and `/routing bgp` if needed)
10. `/mpls interface`, `/mpls ldp`, `/mpls ldp accept-filter`
11. `/ip firewall address-list`, `/ip firewall filter`, `/ip firewall nat`, `/ip firewall raw`
12. `/snmp community`, `/system logging`, `/system watchdog`, `/system routerboard settings`

## Validation Checklist
- Loopback IP appears in address, OSPF router ID, syslog action, LDP configuration, and optional BGP peers.
- Switch uplinks have supplied comments and join `vpls-bridge` when required.
- Backhaul networks use correct `network=` derived from CIDR math.
- VPLS entries exist for each domain and mesh link with matching static IDs and bridge assignments.
- MPLS LDP accept-filters apply all deny prefixes before permits.
- DNS servers set to the compliance pair.
- Compliance blocks (services, firewall, SNMP, NTP) included exactly once.
- Optional BGP peers match provided remote AS, address, and security settings.
- DHCP option 43 and additional scopes appear only when inputs request them.

## Generation Instructions (LLM)
1. Read inputs conforming to the schema above.
2. Generate the RouterOS configuration following the Output Assembly Order.
3. Prefer RouterOS 7.x syntax; emit legacy constructs only if `routeros_version` demands it.
4. Enforce compliance, port roles, and avoid duplicate commands (normalization will also deduplicate).
5. Output plain RouterOS CLI with one command per line, preserving necessary `comment=` annotations.