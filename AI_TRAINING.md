# Ollama AI Training for NOC Config Maker

## Overview
The local LLM (Ollama) is guided by strict system prompts and deterministic post‑processing logic in `api_server.py`. The AI copies configurations and the backend enforces RouterOS v7 syntax, device‑aware remapping, and safe block regrouping.

## What the AI must preserve
- All IP addresses/subnets and router‑id
- Interface names/assignments (remapped only when target device requires)
- Firewall rules and NAT logic (syntax may change; content preserved)
- VLAN IDs and VPLS identifiers
- User/groups and service settings

## Version/dialect normalization (v6 → v7)
- OSPF: `/routing ospf interface` → `/routing ospf interface-template`
  - `interface=` → `interfaces=`
  - network statements → `interface-template add … networks=`
  - `authentication=` → `auth=`, `authentication-key=` → `auth-key=`
  - `network-type=point-to-point` → `type=ptp`
  - Adds `auth-id=1` when `auth=md5`
  - Maps `interfaces=` from `/ip address add` network→interface pairs
- BGP: `/routing bgp peer` → `/routing bgp connection`
  - `remote-address=` → `remote.address=`; `remote-as=` → `remote.as=`; `tcp-md5-key=` → `tcp.md5.key=`; `update-source=` → `update.source=`
  - Removes `in-filter`/`out-filter` on v7 connections
  - Enforces `templates=default`, `routing-table=main`, `output.network=bgp-networks`
- Bridge VLAN: v7 ensures `vlan-filtering=yes` on bridges where applicable
- Interface names: target‑device aware (e.g., CCR2216 prefers `sfp28-*` for data; `ether1` mgmt‑only)

## MPLS/VPLS/LDP (v7)
- VPLS: canonical add lines include `cisco-static-id`, `peer`, `pw-type=raw-ethernet`, `pw-l2mtu`, `pw-control-word=disabled`, and keep `mtu`
- LDP: ensures one `/mpls ldp instance` has `lsr-id`, `transport-addresses`, `vrf=main`, `afi=ip`

## Block routing (dynamic)
Lines are classified by tokens and routed to correct headers. Examples:
- `/ip firewall address-list add address=… list=…`
- `/ip firewall nat add chain=srcnat|dstnat …`
- `/ip firewall filter add chain=input|forward|output action=…`
- `/ip firewall mangle add … (mark/DSCP/jump)`
- `/interface vlan add interface=… vlan-id=…`
- `/interface bridge port add bridge=… interface=…`
- `/interface vpls add …` (auto‑prefixed if header missing)
- OSPF interface‑template add (auto‑prefixed if header missing)

The backend de‑duplicates within each block, emits a single header per section, and ensures blank‑line separation between top‑level headers.

## Safety and gating
- Protocol blocks (BGP/OSPF/MPLS/VPLS) are processed only if present in source
- No injection of new protocols
- For very large configs or timeouts, AI is skipped and deterministic translation runs

## Correct service syntax (v7)
- DNS: `/ip dns set servers=…` (address‑list entries do not go under `/ip dns`)
- NTP: `/system/ntp/client set enabled=yes`; `/system/ntp/client/servers set server-1=… server-2=…`
- User groups: `/user/group set|add policy="…"`

## Devices supported (examples)
- RB5009 (RouterOS 7.x)
- CCR2004 (RouterOS 7.x)
- CCR2116 (RouterOS 7.x)
- CCR2216 (RouterOS 7.x)
- CCR1036/CCR1072 (RouterOS 6.x/7.x)

## Validation
- Counts IPs before/after; warns on losses
- Drops OSPF lines that cannot be mapped to an interface after network→interface resolution

## Tuning
- Prompts focus on “copy every line” + specific v7 deltas
- Post‑processing enforces spacing, unwrapping of line continuations, token normalization

No proprietary addresses, keys, or credentials are included in training or documentation.

