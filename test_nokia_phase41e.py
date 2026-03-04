#!/usr/bin/env python3
"""Phase 41e tests: Transport-only filtering - Tarana radios, VLAN parents, deny-by-default."""
import sys, os, re, json

os.environ['PYTHONIOENCODING'] = 'utf-8'

src = open('vm_deployment/api_server.py', encoding='utf-8').read()

# Mocks
ROUTERBOARD_INTERFACES = {
    'CCR2004-1G-12S+2XS': {'model': 'CCR2004-1G-12S+2XS', 'series': 'CCR', 'management_port': 'ether1'},
    'CCR2116-12G-4S+':    {'model': 'CCR2116-12G-4S+',    'series': 'CCR', 'management_port': 'ether1'},
}
_NOKIA_TZ_MAP = {
    'CST': {'zone': 'CST', 'dst': 'CDT', 'start': 'second sunday march 02:00', 'end': 'first sunday november 02:00'},
    'EST': {'zone': 'EST', 'dst': 'EDT', 'start': 'second sunday march 02:00', 'end': 'first sunday november 02:00'},
}
_NOKIA_DEFAULT_MGMT_ACL  = ['10.10.103.91/32', '192.168.128.0/21', '10.0.0.0/8']
_NOKIA_DEFAULT_NTP        = ['52.128.59.240', '52.128.59.241']
_NOKIA_DEFAULT_LDP_DENY   = ['10.2.0.14/32', '10.2.0.21/32']

# Extract helpers, parser, builder
helpers_start = src.index('_NOKIA_OOS_DEFAULT_MGMT_ACL')
helpers_end   = src.index('\ndef _parse_mikrotik_for_nokia(', helpers_start)
exec(compile(src[helpers_start:helpers_end], '<helpers>', 'exec'))

fn_start = src.index('def _parse_mikrotik_for_nokia(')
fn_end   = src.index('\ndef _build_nokia_config(', fn_start)
exec(compile(src[fn_start:fn_end], '<parser>', 'exec'))

fn2_start = src.index('def _build_nokia_config(')
fn2_end   = src.index("\n@app.route('/api/parse-mikrotik-for-nokia'", fn2_start)
exec(compile('import os\n' + src[fn2_start:fn2_end], '<builder>', 'exec'))

errors = []

# ===========================================================================
# REAL-WORLD TEST: Greenwood site config (simplified from user-provided)
# This has:
#   TRANSPORT: sfp-sfpplus4 (GREENWOOD, OSPF ptp), sfp-sfpplus5 (FORESTBURG, OSPF ptp)
#   TARANA RADIOS: sfp-sfpplus8 (Alpha 090), sfp-sfpplus10 (Beta 210), sfp-sfpplus11 (Gamma 330)
#   NETONIX: sfp-sfpplus1 (bridge member), sfp-sfpplus2 (bridge member, disabled)
#   VLAN parents: sfp-sfpplus8, sfp-sfpplus10, sfp-sfpplus11 (carry VLANs to bridges)
#   UNUSED: sfp-sfpplus3, sfp-sfpplus6, sfp-sfpplus7, sfp-sfpplus9, sfp-sfpplus12
# ===========================================================================

greenwood_config = """
# 2026-03-03 23:53:10 by RouterOS 7.11.2
# model = CCR2004-1G-12S+2XS
/interface bridge
add comment=DYNAMIC name=bridge1000
add comment=STATIC name=bridge2000
add comment="UNICORN MGMT" name=bridge3000
add name=lan-bridge priority=0x1
add name=loop0
add name=nat-public-bridge
/interface ethernet
set [ find default-name=sfp-sfpplus1 ] comment="Netonix Uplink #1"
set [ find default-name=sfp-sfpplus2 ] comment="Netonix Uplink #2" disabled=yes
set [ find default-name=sfp-sfpplus3 ] advertise=10M-half,10M-full,100M-half,100M-full,1000M-half,1000M-full
set [ find default-name=sfp-sfpplus4 ] auto-negotiation=no comment=GREENWOOD
set [ find default-name=sfp-sfpplus5 ] auto-negotiation=no comment=" TX-FORESTBURG-NW-1"
set [ find default-name=sfp-sfpplus6 ] advertise=10M-half,10M-full,100M-half,100M-full,1000M-half,1000M-full
set [ find default-name=sfp-sfpplus7 ] advertise=10M-half,10M-full,100M-half,100M-full,1000M-half,1000M-full
set [ find default-name=sfp-sfpplus8 ] auto-negotiation=no comment="Alpha 090"
set [ find default-name=sfp-sfpplus9 ] auto-negotiation=no
set [ find default-name=sfp-sfpplus10 ] comment="Beta 210"
set [ find default-name=sfp-sfpplus11 ] auto-negotiation=no comment="Gamma 330"
set [ find default-name=sfp-sfpplus12 ] advertise=10M-half,10M-full,100M-half,100M-full,1000M-half,1000M-full
set [ find default-name=sfp28-1 ] advertise=10M-half,10M-full
set [ find default-name=sfp28-2 ] advertise=10M-half,10M-full
/interface vlan
add interface=sfp-sfpplus8 name=vlan1000-sfp-sfpplus8 vlan-id=1000
add interface=sfp-sfpplus10 name=vlan1000-sfp-sfpplus10 vlan-id=1000
add interface=sfp-sfpplus11 name=vlan1000-sfp-sfpplus11 vlan-id=1000
add interface=sfp-sfpplus8 name=vlan2000-sfp-sfpplus8 vlan-id=2000
add interface=sfp-sfpplus10 name=vlan2000-sfp-sfpplus10 vlan-id=2000
add interface=sfp-sfpplus11 name=vlan2000-sfp-sfpplus11 vlan-id=2000
add interface=sfp-sfpplus8 name=vlan3000-sfp-sfpplus8 vlan-id=3000
add interface=sfp-sfpplus10 name=vlan3000-sfp-sfpplus10 vlan-id=3000
add interface=sfp-sfpplus11 name=vlan3000-sfp-sfpplus11 vlan-id=3000
/interface bridge port
add bridge=lan-bridge interface=sfp-sfpplus1
add bridge=lan-bridge interface=sfp-sfpplus2
add bridge=bridge3000 interface=vlan3000-sfp-sfpplus8
add bridge=bridge3000 interface=vlan3000-sfp-sfpplus11
add bridge=bridge3000 interface=vlan3000-sfp-sfpplus10
add bridge=lan-bridge interface=vlan1000-sfp-sfpplus8
add bridge=lan-bridge interface=vlan1000-sfp-sfpplus11
add bridge=lan-bridge interface=vlan1000-sfp-sfpplus10
add bridge=bridge2000 interface=vlan2000-sfp-sfpplus8
add bridge=bridge2000 interface=vlan2000-sfp-sfpplus11
add bridge=bridge2000 interface=vlan2000-sfp-sfpplus10
/ip address
add address=10.39.0.196 comment=loop0 interface=loop0 network=10.39.0.196
add address=10.47.124.1/22 comment="CPE/Tower Gear" interface=lan-bridge network=10.47.124.0
add address=10.147.124.1/22 comment=UNAUTH interface=lan-bridge network=10.147.124.0
add address=132.147.184.134 comment="CGNAT Public" interface=nat-public-bridge network=132.147.184.134
add address=100.81.80.1/22 comment="CGNAT Private" interface=lan-bridge network=100.81.80.0
add address=10.45.129.156/29 comment=GREENWOOD interface=sfp-sfpplus4 network=10.45.129.152
add address=10.246.4.105/29 comment="UNICORN MGMT" interface=bridge3000 network=10.246.4.104
add address=10.33.251.212/29 comment=" TX-FORESTBURG-NW-1" interface=sfp-sfpplus5 network=10.33.251.208
/routing bgp connection
add connect=yes listen=yes local.address=10.39.0.196 .role=ibgp multihop=yes name=CR7 remote.address=10.2.0.107 .as=26077
add connect=yes listen=yes local.address=10.39.0.196 .role=ibgp multihop=yes name=CR8 remote.address=10.2.0.108 .as=26077
/routing bgp template
set default as=26077
/routing ospf instance
add disabled=no name=default-v2 originate-default=never router-id=10.39.0.196
/routing ospf area
add disabled=no instance=default-v2 name=backbone-v2
/routing ospf interface-template
add area=backbone-v2 cost=10 disabled=no interfaces=loop0 networks=10.39.0.196/32 passive priority=1
add area=backbone-v2 cost=10 disabled=no interfaces=lan-bridge networks=10.47.124.0/22 priority=1
add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment=GREENWOOD cost=30 disabled=no interfaces=sfp-sfpplus4 networks=10.45.129.152/29 priority=1 type=ptp
add area=backbone-v2 comment="UNICORN MGMT" cost=10 disabled=no interfaces=bridge3000 networks=10.246.4.104/29 priority=1
add area=backbone-v2 comment="UNICORN MGMT" cost=10 disabled=no interfaces=bridge2000 networks=10.45.130.240/30 passive priority=1
add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment=" TX-FORESTBURG-NW-1" cost=10 disabled=no interfaces=sfp-sfpplus5 networks=10.33.251.208/29 priority=1 type=ptp
/mpls ldp
/mpls ldp accept-filter
add accept=no prefix=10.2.0.14/32
add accept=no prefix=10.2.0.107/32
add accept=no prefix=10.2.0.108/32
add accept=no prefix=10.17.0.10/32
/snmp community
add name=FBZ1yYdphf
/system identity
set name=RTR-CCR2004-1.TX-GREENWOOD-NO-1
"""

parsed = _parse_mikrotik_for_nokia(greenwood_config)
pm = parsed['port_mapping']

# ===========================================================================
# TEST GROUP 1: Tarana Radios Excluded
# ===========================================================================

# [T1] Alpha 090 (sfp-sfpplus8) - Tarana radio -> NOT on Nokia
s8 = pm.get('sfp-sfpplus8', {})
ok1 = s8.get('type') == 'access' and 'not on Nokia' in s8.get('nokia_port', '')
if not ok1:
    errors.append(f"FAIL T1: sfp-sfpplus8 (Alpha 090) should be access, got {s8}")
print(f"[T1] Alpha 090 -> excluded: {'PASS' if ok1 else 'FAIL'}")
print(f"     Role: {s8.get('role', '?')}")

# [T2] Beta 210 (sfp-sfpplus10) - Tarana radio -> NOT on Nokia
s10 = pm.get('sfp-sfpplus10', {})
ok2 = s10.get('type') == 'access' and 'not on Nokia' in s10.get('nokia_port', '')
if not ok2:
    errors.append(f"FAIL T2: sfp-sfpplus10 (Beta 210) should be access, got {s10}")
print(f"[T2] Beta 210 -> excluded: {'PASS' if ok2 else 'FAIL'}")
print(f"     Role: {s10.get('role', '?')}")

# [T3] Gamma 330 (sfp-sfpplus11) - Tarana radio -> NOT on Nokia
s11 = pm.get('sfp-sfpplus11', {})
ok3 = s11.get('type') == 'access' and 'not on Nokia' in s11.get('nokia_port', '')
if not ok3:
    errors.append(f"FAIL T3: sfp-sfpplus11 (Gamma 330) should be access, got {s11}")
print(f"[T3] Gamma 330 -> excluded: {'PASS' if ok3 else 'FAIL'}")
print(f"     Role: {s11.get('role', '?')}")

# ===========================================================================
# TEST GROUP 2: VLAN Parent Detection
# ===========================================================================

# [T4] sfp-sfpplus8 is parent of vlan1000/2000/3000 -> detected as VLAN parent
ok4 = 'VLAN parent' in s8.get('role', '')
if not ok4:
    errors.append(f"FAIL T4: sfp-sfpplus8 should show VLAN parent role, got {s8.get('role')}")
print(f"[T4] VLAN parent detected (sfp-sfpplus8): {'PASS' if ok4 else 'FAIL'}")

# [T5] sfp-sfpplus10 is parent of VLANs -> detected as VLAN parent
ok5 = 'VLAN parent' in s10.get('role', '')
if not ok5:
    errors.append(f"FAIL T5: sfp-sfpplus10 should show VLAN parent role, got {s10.get('role')}")
print(f"[T5] VLAN parent detected (sfp-sfpplus10): {'PASS' if ok5 else 'FAIL'}")

# ===========================================================================
# TEST GROUP 3: Transport Interfaces Survive
# ===========================================================================

# [T6] GREENWOOD (sfp-sfpplus4, OSPF ptp) -> transport on Nokia
s4 = pm.get('sfp-sfpplus4', {})
ok6 = s4.get('type') in ('sfp', 'ethernet') and s4.get('nokia_port', '').startswith('1/1/')
if not ok6:
    errors.append(f"FAIL T6: sfp-sfpplus4 (GREENWOOD) should be transport, got {s4}")
print(f"[T6] GREENWOOD -> transport: {'PASS' if ok6 else 'FAIL'}")
print(f"     Port: {s4.get('nokia_port', '?')}")

# [T7] TX-FORESTBURG-NW-1 (sfp-sfpplus5, OSPF ptp) -> transport on Nokia
s5 = pm.get('sfp-sfpplus5', {})
ok7 = s5.get('type') in ('sfp', 'ethernet') and s5.get('nokia_port', '').startswith('1/1/')
if not ok7:
    errors.append(f"FAIL T7: sfp-sfpplus5 (FORESTBURG) should be transport, got {s5}")
print(f"[T7] FORESTBURG -> transport: {'PASS' if ok7 else 'FAIL'}")
print(f"     Port: {s5.get('nokia_port', '?')}")

# [T8] Only 2 transport ports (sfp4 and sfp5) get 1/1/X assignments
transport_ports = [(k, v['nokia_port']) for k, v in pm.items() if v.get('nokia_port', '').startswith('1/1/')]
ok8 = len(transport_ports) == 2
if not ok8:
    errors.append(f"FAIL T8: Expected exactly 2 transport ports, got {len(transport_ports)}: {transport_ports}")
print(f"[T8] Exactly 2 transport ports: {'PASS' if ok8 else 'FAIL'} ({transport_ports})")

# ===========================================================================
# TEST GROUP 4: Deny-by-Default (Unknown Interfaces Excluded)
# ===========================================================================

# sfp-sfpplus3 has NO comment, NO OSPF, NO /30 -> unknown -> excluded
s3 = pm.get('sfp-sfpplus3', {})
ok9 = s3.get('type') == 'access' and 'not on Nokia' in s3.get('nokia_port', '')
if not ok9:
    # sfp-sfpplus3 might not appear at all if it has no comment AND no IP
    # That's also acceptable - it just doesn't exist in port_mapping
    ok9 = 'sfp-sfpplus3' not in pm
    if not ok9:
        errors.append(f"FAIL T9: sfp-sfpplus3 (no comment) should be excluded, got {s3}")
print(f"[T9] Unknown iface excluded: {'PASS' if ok9 else 'FAIL'}")

# sfp-sfpplus6, sfp-sfpplus7 also unknown -> excluded
ok10a = pm.get('sfp-sfpplus6', {}).get('type') == 'access' or 'sfp-sfpplus6' not in pm
ok10b = pm.get('sfp-sfpplus7', {}).get('type') == 'access' or 'sfp-sfpplus7' not in pm
ok10 = ok10a and ok10b
if not ok10:
    errors.append(f"FAIL T10: Unknown sfp6/sfp7 should be excluded")
print(f"[T10] Other unknowns excluded: {'PASS' if ok10 else 'FAIL'}")

# ===========================================================================
# TEST GROUP 5: Bridge Members Still Handled
# ===========================================================================

# sfp-sfpplus1 is bridge member of lan-bridge
s1 = pm.get('sfp-sfpplus1', {})
ok11 = s1.get('type') == 'bridge-member'
if not ok11:
    errors.append(f"FAIL T11: sfp-sfpplus1 should be bridge-member, got {s1}")
print(f"[T11] Netonix bridge member: {'PASS' if ok11 else 'FAIL'}")

# ===========================================================================
# TEST GROUP 6: Nokia Output Verification
# ===========================================================================

nokia_out = _build_nokia_config(parsed, {'state_code': 'TX'})

# [T12] Only GREENWOOD and FORESTBURG in Nokia router interfaces
ok12a = 'GREENWOOD' in nokia_out
ok12b = 'FORESTBURG' in nokia_out
ok12c = 'Alpha' not in nokia_out
ok12d = 'Beta' not in nokia_out
ok12e = 'Gamma' not in nokia_out
ok12f = 'Netonix' not in nokia_out
ok12 = ok12a and ok12b and ok12c and ok12d and ok12e and ok12f
if not ok12:
    fails = []
    if not ok12a: fails.append('GREENWOOD missing')
    if not ok12b: fails.append('FORESTBURG missing')
    if not ok12c: fails.append('Alpha 090 found')
    if not ok12d: fails.append('Beta 210 found')
    if not ok12e: fails.append('Gamma 330 found')
    if not ok12f: fails.append('Netonix found')
    errors.append(f"FAIL T12: Nokia output issues: {', '.join(fails)}")
print(f"[T12] Nokia output correct: {'PASS' if ok12 else 'FAIL'}")

# [T13] Only port 1/1/1 and 1/1/2 in Nokia output (not 1/1/3+)
has_port_3 = 'port 1/1/3' in nokia_out
ok13 = 'port 1/1/1' in nokia_out and 'port 1/1/2' in nokia_out and not has_port_3
if not ok13:
    errors.append(f"FAIL T13: Expected only port 1/1/1 and 1/1/2, port 1/1/3 present: {has_port_3}")
print(f"[T13] Correct port count in Nokia: {'PASS' if ok13 else 'FAIL'}")

# [T14] OSPF has both transport interfaces
ok14a = 'interface "GREENWOOD"' in nokia_out
ok14b = 'interface "TX-FORESTBURG-NW-1"' in nokia_out
ok14 = ok14a and ok14b
if not ok14:
    errors.append(f"FAIL T14: OSPF missing transport interfaces")
print(f"[T14] OSPF has transport ifaces: {'PASS' if ok14 else 'FAIL'}")

# ===========================================================================
# TEST GROUP 7: All NATO/Greek Alphabet Tarana Names
# ===========================================================================

# Build a config with many Tarana name variations
tarana_names = [
    'Alpha 090', 'Beta 210', 'Gamma 330', 'Delta 450',
    'Echo 570', 'Foxtrot 690', 'Golf 810', 'Hotel 930',
    'Kilo 100', 'Lima 200', 'Mike 300', 'November 400',
    'Oscar 500', 'Papa 600', 'Romeo 700', 'Sierra 800',
    'Tango 900', 'Victor 50', 'Whiskey 60', 'Zulu 70',
]

tarana_ifaces = []
tarana_ip_lines = []
for i, name in enumerate(tarana_names):
    iface = f'sfp-sfpplus{i+2}'
    tarana_ifaces.append(f'set [ find default-name={iface} ] comment="{name}"')
    tarana_ip_lines.append(f'add address=10.50.{i}.1/24 interface={iface}')

tarana_config = f"""
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [ find default-name=sfp-sfpplus1 ] comment="UPLINK-1"
{chr(10).join(tarana_ifaces)}
/ip address
add address=10.1.0.95/32 interface=loop0
add address=10.30.248.30/30 interface=sfp-sfpplus1
{chr(10).join(tarana_ip_lines)}
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=sfp-sfpplus1 type=ptp
/system identity
set name=RTR-MTCCR2004-1.TX-TARANATEST
/snmp community
add name=testcomm
"""

p_tarana = _parse_mikrotik_for_nokia(tarana_config)
pm_tarana = p_tarana['port_mapping']

# [T15] All Tarana NATO names detected as access
tarana_all_ok = True
for i, name in enumerate(tarana_names):
    iface = f'sfp-sfpplus{i+2}'
    entry = pm_tarana.get(iface, {})
    if entry.get('type') != 'access':
        tarana_all_ok = False
        errors.append(f"FAIL T15: {iface} ({name}) should be access, got {entry.get('type', 'MISSING')}")
if not tarana_all_ok:
    print(f"[T15] All NATO Tarana names detected: FAIL")
else:
    print(f"[T15] All NATO Tarana names detected: PASS ({len(tarana_names)}/{len(tarana_names)})")

# [T16] Only sfp-sfpplus1 (UPLINK-1) gets Nokia port
transport_tarana = [k for k, v in pm_tarana.items() if v.get('nokia_port', '').startswith('1/1/')]
ok16 = transport_tarana == ['sfp-sfpplus1']
if not ok16:
    errors.append(f"FAIL T16: Only sfp-sfpplus1 should be transport, got {transport_tarana}")
print(f"[T16] Only uplink on Nokia: {'PASS' if ok16 else 'FAIL'} ({transport_tarana})")

# ===========================================================================
# TEST GROUP 8: VLAN Parent Override (VLAN parent + OSPF)
# ===========================================================================

# If a VLAN parent ALSO participates in OSPF, OSPF wins (Rule 1 > Rule 2)
vlan_ospf_config = """
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [ find default-name=sfp-sfpplus1 ] comment="UPLINK-1"
/interface vlan
add interface=sfp-sfpplus1 name=vlan100-sfp-sfpplus1 vlan-id=100
/ip address
add address=10.1.0.96/32 interface=loop0
add address=10.30.248.30/30 interface=sfp-sfpplus1
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=sfp-sfpplus1 type=ptp
/system identity
set name=RTR-MTCCR2004-1.TX-VLANOSPF
/snmp community
add name=testcomm
"""

p_vo = _parse_mikrotik_for_nokia(vlan_ospf_config)
pm_vo = p_vo['port_mapping']

# [T17] OSPF overrides VLAN parent classification
s_vo = pm_vo.get('sfp-sfpplus1', {})
ok17 = s_vo.get('type') in ('sfp', 'ethernet') and s_vo.get('nokia_port', '').startswith('1/1/')
if not ok17:
    errors.append(f"FAIL T17: OSPF should override VLAN parent, got {s_vo}")
print(f"[T17] OSPF overrides VLAN parent: {'PASS' if ok17 else 'FAIL'}")

# ===========================================================================
# TEST GROUP 9: All 7 States with Greenwood Config
# ===========================================================================

states = ['TX', 'NE', 'KS', 'IL', 'IA', 'OK', 'IN']
all_states_ok = True
for state in states:
    out = _build_nokia_config(parsed, {'state_code': state})
    # Transport IPs present
    has_greenwood = '10.45.129.156' in out
    has_forestburg = '10.33.251.212' in out
    # No Tarana
    no_alpha = 'Alpha' not in out
    no_beta = 'Beta' not in out
    no_gamma = 'Gamma' not in out
    if not (has_greenwood and has_forestburg and no_alpha and no_beta and no_gamma):
        all_states_ok = False
        errors.append(f"FAIL T18: State {state} issue: GW={has_greenwood} FB={has_forestburg} noA={no_alpha} noB={no_beta} noG={no_gamma}")

print(f"[T18] All 7 states correct: {'PASS' if all_states_ok else 'FAIL'}")

# ===========================================================================
# TEST GROUP 10: UNICORN MGMT keyword
# ===========================================================================

# bridge3000 has comment "UNICORN MGMT" and is a bridge with OSPF -> stays as bridge/VPLS
# But if a physical interface had "UNICORN MGMT" comment it should be access (MGMT keyword)
mgmt_kw_config = """
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [ find default-name=sfp-sfpplus1 ] comment="UPLINK-1"
set [ find default-name=sfp-sfpplus2 ] comment="UNICORN MGMT"
/ip address
add address=10.1.0.97/32 interface=loop0
add address=10.30.248.30/30 interface=sfp-sfpplus1
add address=10.246.4.105/29 interface=sfp-sfpplus2
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=sfp-sfpplus1 type=ptp
/system identity
set name=RTR-MTCCR2004-1.TX-MGMTTEST
/snmp community
add name=testcomm
"""

p_mgmt = _parse_mikrotik_for_nokia(mgmt_kw_config)
pm_mgmt = p_mgmt['port_mapping']

# [T19] UNICORN MGMT -> access (MGMT keyword match)
s_mgmt = pm_mgmt.get('sfp-sfpplus2', {})
ok19 = s_mgmt.get('type') == 'access'
if not ok19:
    errors.append(f"FAIL T19: sfp-sfpplus2 (UNICORN MGMT) should be access, got {s_mgmt}")
print(f"[T19] MGMT keyword -> excluded: {'PASS' if ok19 else 'FAIL'}")

# [T20] Transport still works alongside MGMT exclusion
s_uplink = pm_mgmt.get('sfp-sfpplus1', {})
ok20 = s_uplink.get('nokia_port', '').startswith('1/1/')
if not ok20:
    errors.append(f"FAIL T20: sfp-sfpplus1 should be transport, got {s_uplink}")
print(f"[T20] Transport alongside MGMT: {'PASS' if ok20 else 'FAIL'}")

# ===========================================================================
# SUMMARY
# ===========================================================================

print("\n" + "=" * 60)
total = 20
passed = total - len(errors)
if errors:
    print(f"FAILURES ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
    print(f"\n{passed}/{total} tests passed")
    sys.exit(1)
else:
    print(f"ALL {total} PHASE 41e TESTS PASSED!")
    sys.exit(0)
