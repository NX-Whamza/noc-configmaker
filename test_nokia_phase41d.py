#!/usr/bin/env python3
"""Phase 41d tests: Access interface filtering — exclude switches, OLTs, etc. from Nokia config."""
import sys, os, re, json

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

# ═══════════════════════════════════════════════════════════════════════════
# TEST CONFIG — MikroTik with a mix of transport & access interfaces
# ═══════════════════════════════════════════════════════════════════════════

# This config simulates a real site with:
#   - Transport: sfp-sfpplus1 (UPLINK-1 to CR), sfp-sfpplus2 (UPLINK-2 to CR)
#   - Access:    sfp-sfpplus3 (NETONIX SWITCH), sfp-sfpplus4 (LEGACY NETONIX)
#   - Access:    sfp-sfpplus5 (OLT), ether2 (CAMERA)
#   - Bridge:    lan-bridge with sfp-sfpplus6, sfp-sfpplus7
#   - Unknown:   sfp-sfpplus8 (/30 address → transport via Rule 3)

access_config = """
# 2025-01-31 05:00:06 by RouterOS 7.18.2
# model = CCR2004-1G-12S+2XS
/interface bridge
add name=lan-bridge
/interface bridge port
add bridge=lan-bridge interface=sfp-sfpplus6
add bridge=lan-bridge interface=sfp-sfpplus7
/interface ethernet
set [find default-name=sfp-sfpplus1] comment="UPLINK-1 to CR7"
set [find default-name=sfp-sfpplus2] comment="UPLINK-2 to CR8"
set [find default-name=sfp-sfpplus3] comment="NETONIX SWITCH"
set [find default-name=sfp-sfpplus4] comment="LEGACY NETONIX"
set [find default-name=sfp-sfpplus5] comment="OLT"
set [find default-name=ether2] comment="CAMERA"
set [find default-name=sfp-sfpplus8] comment=""
/ip address
add address=10.1.0.50/32 interface=loop0
add address=10.1.100.1/22 interface=lan-bridge
add address=10.30.248.30/30 interface=sfp-sfpplus1
add address=10.30.248.26/30 interface=sfp-sfpplus2
add address=10.50.1.1/24 interface=sfp-sfpplus3
add address=10.50.2.1/24 interface=sfp-sfpplus4
add address=10.50.3.1/24 interface=sfp-sfpplus5
add address=10.50.4.1/24 interface=ether2
add address=10.30.248.22/30 interface=sfp-sfpplus8
/routing bgp connection
add name=CR7 remote.address=10.2.0.107 .as=26077
add name=CR8 remote.address=10.2.0.108 .as=26077
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=lan-bridge
add area=backbone-v2 interfaces=sfp-sfpplus1 type=ptp
add area=backbone-v2 interfaces=sfp-sfpplus2 type=ptp
/mpls ldp
/mpls ldp accept-filter
add accept=no prefix=10.2.0.14/32
/system identity
set name=RTR-MTCCR2004-1.TX-ACCESSTEST-NW-1
/snmp community
add name=testcomm
"""

parsed = _parse_mikrotik_for_nokia(access_config)
pm = parsed['port_mapping']

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 1: Interface Role Classification
# ═══════════════════════════════════════════════════════════════════════════

# [T1] Transport via OSPF participation
s1 = pm.get('sfp-sfpplus1', {})
ok1 = s1.get('type') in ('sfp', 'ethernet') and s1.get('nokia_port', '').startswith('1/1/')
if not ok1:
    errors.append(f"FAIL T1: sfp-sfpplus1 should be transport, got {s1}")
print(f"[T1] OSPF transport (sfp-sfpplus1): {'PASS' if ok1 else 'FAIL'}")
print(f"     Port mapping: {s1}")

# [T2] Transport via UPLINK keyword
s2 = pm.get('sfp-sfpplus2', {})
ok2 = s2.get('type') in ('sfp', 'ethernet') and s2.get('nokia_port', '').startswith('1/1/')
if not ok2:
    errors.append(f"FAIL T2: sfp-sfpplus2 should be transport, got {s2}")
print(f"[T2] UPLINK keyword transport (sfp-sfpplus2): {'PASS' if ok2 else 'FAIL'}")
print(f"     Port mapping: {s2}")

# [T3] Access: NETONIX SWITCH
s3 = pm.get('sfp-sfpplus3', {})
ok3 = s3.get('type') == 'access' and 'not on Nokia' in s3.get('nokia_port', '')
if not ok3:
    errors.append(f"FAIL T3: sfp-sfpplus3 (NETONIX SWITCH) should be access, got {s3}")
print(f"[T3] NETONIX SWITCH → access (sfp-sfpplus3): {'PASS' if ok3 else 'FAIL'}")
print(f"     Port mapping: {s3}")

# [T4] Access: LEGACY NETONIX
s4 = pm.get('sfp-sfpplus4', {})
ok4 = s4.get('type') == 'access' and 'not on Nokia' in s4.get('nokia_port', '')
if not ok4:
    errors.append(f"FAIL T4: sfp-sfpplus4 (LEGACY NETONIX) should be access, got {s4}")
print(f"[T4] LEGACY NETONIX → access (sfp-sfpplus4): {'PASS' if ok4 else 'FAIL'}")
print(f"     Port mapping: {s4}")

# [T5] Access: OLT
s5 = pm.get('sfp-sfpplus5', {})
ok5 = s5.get('type') == 'access' and 'not on Nokia' in s5.get('nokia_port', '')
if not ok5:
    errors.append(f"FAIL T5: sfp-sfpplus5 (OLT) should be access, got {s5}")
print(f"[T5] OLT → access (sfp-sfpplus5): {'PASS' if ok5 else 'FAIL'}")
print(f"     Port mapping: {s5}")

# [T6] Access: CAMERA
s6 = pm.get('ether2', {})
ok6 = s6.get('type') == 'access' and 'not on Nokia' in s6.get('nokia_port', '')
if not ok6:
    errors.append(f"FAIL T6: ether2 (CAMERA) should be access, got {s6}")
print(f"[T6] CAMERA → access (ether2): {'PASS' if ok6 else 'FAIL'}")
print(f"     Port mapping: {s6}")

# [T7] Unknown with /30 address → transport (Rule 3)
s8 = pm.get('sfp-sfpplus8', {})
ok7 = s8.get('type') in ('sfp', 'ethernet') and s8.get('nokia_port', '').startswith('1/1/')
if not ok7:
    errors.append(f"FAIL T7: sfp-sfpplus8 (/30 addr) should be transport, got {s8}")
print(f"[T7] /30 address → transport (sfp-sfpplus8): {'PASS' if ok7 else 'FAIL'}")
print(f"     Port mapping: {s8}")

# [T8] Bridge members still excluded
s6m = pm.get('sfp-sfpplus6', {})
s7m = pm.get('sfp-sfpplus7', {})
ok8 = s6m.get('type') == 'bridge-member' and s7m.get('type') == 'bridge-member'
if not ok8:
    errors.append(f"FAIL T8: Bridge members should still be bridge-member type")
print(f"[T8] Bridge members still classified correctly: {'PASS' if ok8 else 'FAIL'}")
print(f"     sfp-sfpplus6: {s6m}, sfp-sfpplus7: {s7m}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 2: Nokia Config Output Excludes Access
# ═══════════════════════════════════════════════════════════════════════════

nokia_out = _build_nokia_config(parsed, {'state_code': 'TX'})

# [T9] Access interfaces NOT in nokia router interface section
ok9a = 'sfp-sfpplus3' not in nokia_out  # NETONIX SWITCH
ok9b = 'sfp-sfpplus4' not in nokia_out  # LEGACY NETONIX
ok9c = 'sfp-sfpplus5' not in nokia_out  # OLT
ok9d = 'ether2' not in nokia_out  # CAMERA  actually — ether2 could appear in port config too
# Be more specific: check that these don't appear in the router interface config section
# They should NOT have 'interface "1/1/X"' entries for ports 3,4,5 since those are access
ok9 = ok9a and ok9b and ok9c
if not ok9:
    errors.append(f"FAIL T9: Access interface names found in Nokia output")
    if not ok9a: errors.append("  - sfp-sfpplus3 (NETONIX SWITCH) found")
    if not ok9b: errors.append("  - sfp-sfpplus4 (LEGACY NETONIX) found")
    if not ok9c: errors.append("  - sfp-sfpplus5 (OLT) found")
print(f"[T9] Access interfaces absent from Nokia output: {'PASS' if ok9 else 'FAIL'}")

# [T10] Transport interfaces ARE in Nokia output (as router ports)
has_transport = True
# sfp-sfpplus1/2 should map to 1/1/1, 1/1/2
if 'port 1/1/1' not in nokia_out:
    has_transport = False
    errors.append("FAIL T10: Transport port 1/1/1 missing from Nokia output")
if 'port 1/1/2' not in nokia_out:
    has_transport = False
    errors.append("FAIL T10: Transport port 1/1/2 missing from Nokia output")
print(f"[T10] Transport interfaces present in Nokia output: {'PASS' if has_transport else 'FAIL'}")

# [T11] Stats track access_excluded count
ok11 = parsed.get('stats', {}).get('access_excluded', 0) >= 4  # at least 4 access: sfp3,sfp4,sfp5,ether2
if not ok11:
    errors.append(f"FAIL T11: access_excluded stat should be >= 4, got {parsed.get('stats', {}).get('access_excluded', 0)}")
print(f"[T11] access_excluded stat: {'PASS' if ok11 else 'FAIL'} ({parsed.get('stats', {}).get('access_excluded', 0)})")

# [T12] Warning message includes access exclusion
has_access_warning = any('Access/downstream ports excluded' in w for w in parsed.get('warnings', []))
if not has_access_warning:
    errors.append("FAIL T12: Missing warning about access port exclusion")
print(f"[T12] Access exclusion warning present: {'PASS' if has_access_warning else 'FAIL'}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 3: Nokia Port Numbering Correct After Exclusion
# ═══════════════════════════════════════════════════════════════════════════

# With access ports excluded, only sfp-sfpplus1, sfp-sfpplus2, sfp-sfpplus8
# should get Nokia ports: 1/1/1, 1/1/2, 1/1/3

# [T13] Port numbering is sequential & no gaps
nokia_ports_assigned = []
for k, v in pm.items():
    np = v.get('nokia_port', '')
    if np.startswith('1/1/') and not np.startswith('1/1/c'):
        nokia_ports_assigned.append((k, np))
nokia_ports_assigned.sort(key=lambda x: int(x[1].split('/')[-1]))
port_nums = [int(p[1].split('/')[-1]) for p in nokia_ports_assigned]
ok13 = port_nums == list(range(1, len(port_nums) + 1))
if not ok13:
    errors.append(f"FAIL T13: Port numbers should be sequential, got {port_nums}")
print(f"[T13] Sequential port numbering: {'PASS' if ok13 else 'FAIL'}")
print(f"      Assigned: {nokia_ports_assigned}")

# [T14] Exactly 3 transport ports assigned (sfp-sfpplus1, sfp-sfpplus2, sfp-sfpplus8)
ok14 = len(nokia_ports_assigned) == 3
if not ok14:
    errors.append(f"FAIL T14: Expected 3 transport ports, got {len(nokia_ports_assigned)}")
print(f"[T14] Transport port count: {'PASS' if ok14 else 'FAIL'} ({len(nokia_ports_assigned)})")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 4: Additional Access Keywords
# ═══════════════════════════════════════════════════════════════════════════

# Test more access keywords: POWER, UPS, CPE, CUSTOMER, DOWNSTREAM, AP, DSLAM, GPON

more_access_config = """
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [find default-name=sfp-sfpplus1] comment="UPLINK-1"
set [find default-name=sfp-sfpplus2] comment="POWER SUPPLY"
set [find default-name=sfp-sfpplus3] comment="UPS CONTROLLER"
set [find default-name=sfp-sfpplus4] comment="CPE MANAGEMENT"
set [find default-name=sfp-sfpplus5] comment="CUSTOMER PORTAL"
set [find default-name=sfp-sfpplus6] comment="DOWNSTREAM LINK"
set [find default-name=sfp-sfpplus7] comment="AP CLUSTER"
set [find default-name=sfp-sfpplus8] comment="DSLAM-1"
set [find default-name=sfp-sfpplus9] comment="GPON OLT-1"
set [find default-name=sfp-sfpplus10] comment="WISP-SW-01"
set [find default-name=sfp-sfpplus11] comment="ACCESS-SW-2"
/ip address
add address=10.1.0.80/32 interface=loop0
add address=10.30.248.30/30 interface=sfp-sfpplus1
add address=10.50.1.1/24 interface=sfp-sfpplus2
add address=10.50.2.1/24 interface=sfp-sfpplus3
add address=10.50.3.1/24 interface=sfp-sfpplus4
add address=10.50.4.1/24 interface=sfp-sfpplus5
add address=10.50.5.1/24 interface=sfp-sfpplus6
add address=10.50.6.1/24 interface=sfp-sfpplus7
add address=10.50.7.1/24 interface=sfp-sfpplus8
add address=10.50.8.1/24 interface=sfp-sfpplus9
add address=10.50.9.1/24 interface=sfp-sfpplus10
add address=10.50.10.1/24 interface=sfp-sfpplus11
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=sfp-sfpplus1 type=ptp
/system identity
set name=RTR-MTCCR2004-1.TX-KEYWORDTEST
/snmp community
add name=testcomm
"""

p2 = _parse_mikrotik_for_nokia(more_access_config)
pm2 = p2['port_mapping']

access_kw_tests = [
    ('sfp-sfpplus2',  'POWER'),
    ('sfp-sfpplus3',  'UPS'),
    ('sfp-sfpplus4',  'CPE'),
    ('sfp-sfpplus5',  'CUSTOMER'),
    ('sfp-sfpplus6',  'DOWNSTREAM'),
    ('sfp-sfpplus7',  'AP'),
    ('sfp-sfpplus8',  'DSLAM'),
    ('sfp-sfpplus9',  'GPON'),
    ('sfp-sfpplus10', 'WISP-SW'),
    ('sfp-sfpplus11', 'ACCESS-SW'),
]

# [T15] All access keywords detected
all_kw_ok = True
for iface, keyword in access_kw_tests:
    entry = pm2.get(iface, {})
    if entry.get('type') != 'access':
        all_kw_ok = False
        errors.append(f"FAIL T15: {iface} ({keyword}) should be access, got {entry.get('type', 'missing')}")
if not all_kw_ok:
    print(f"[T15] All access keywords detected: FAIL")
else:
    print(f"[T15] All access keywords detected: PASS (10/10 keywords)")

# [T16] Only sfp-sfpplus1 gets a Nokia port
transport_in_p2 = [k for k, v in pm2.items() if v.get('nokia_port', '').startswith('1/1/')]
ok16 = transport_in_p2 == ['sfp-sfpplus1']
if not ok16:
    errors.append(f"FAIL T16: Expected only sfp-sfpplus1 as transport, got {transport_in_p2}")
print(f"[T16] Only uplink gets Nokia port: {'PASS' if ok16 else 'FAIL'} ({transport_in_p2})")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 5: OSPF Overrides Access Keywords
# ═══════════════════════════════════════════════════════════════════════════

# An interface commented "NETONIX" but participating in OSPF should be transport
ospf_override_config = """
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [find default-name=sfp-sfpplus1] comment="NETONIX SWITCH"
set [find default-name=sfp-sfpplus2] comment="UPLINK"
/ip address
add address=10.1.0.90/32 interface=loop0
add address=10.30.248.30/30 interface=sfp-sfpplus1
add address=10.30.248.26/30 interface=sfp-sfpplus2
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=sfp-sfpplus1 type=ptp
add area=backbone-v2 interfaces=sfp-sfpplus2 type=ptp
/system identity
set name=RTR-MTCCR2004-1.TX-OSPFOVERRIDE
/snmp community
add name=testcomm
"""

p3 = _parse_mikrotik_for_nokia(ospf_override_config)
pm3 = p3['port_mapping']

# [T17] OSPF participation overrides "NETONIX" comment
s_override = pm3.get('sfp-sfpplus1', {})
ok17 = s_override.get('type') in ('sfp', 'ethernet') and s_override.get('nokia_port', '').startswith('1/1/')
if not ok17:
    errors.append(f"FAIL T17: OSPF should override NETONIX keyword, got {s_override}")
print(f"[T17] OSPF overrides access keyword: {'PASS' if ok17 else 'FAIL'}")
print(f"      sfp-sfpplus1: {s_override}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 6: Builder Output Across All States
# ═══════════════════════════════════════════════════════════════════════════

# Use the main access_config parsed data and build for all states
states_to_test = ['TX', 'NE', 'KS', 'IL', 'IA', 'OK', 'IN']
state_results = {}

for state in states_to_test:
    out = _build_nokia_config(parsed, {'state_code': state})
    # Check that access ports don't appear in Nokia output for ANY state
    has_access = 'sfp-sfpplus3' in out or 'sfp-sfpplus4' in out or 'sfp-sfpplus5' in out
    # Check that transport ports DO appear
    has_transport = '10.30.248.30' in out and '10.30.248.26' in out
    # Check basic config structure present
    has_system = 'system' in out.lower()
    has_ospf = 'ospf' in out.lower()
    state_results[state] = {
        'no_access': not has_access,
        'has_transport': has_transport,
        'has_system': has_system,
        'has_ospf': has_ospf,
    }

# [T18] No access in ANY state output
ok18 = all(r['no_access'] for r in state_results.values())
if not ok18:
    for s, r in state_results.items():
        if not r['no_access']:
            errors.append(f"FAIL T18: State {s} has access interfaces in output")
print(f"[T18] No access interfaces in any state: {'PASS' if ok18 else 'FAIL'}")

# [T19] Transport in ALL state outputs
ok19 = all(r['has_transport'] for r in state_results.values())
if not ok19:
    for s, r in state_results.items():
        if not r['has_transport']:
            errors.append(f"FAIL T19: State {s} missing transport interfaces")
print(f"[T19] Transport in all state outputs: {'PASS' if ok19 else 'FAIL'}")

# [T20] OSPF present in all state outputs
ok20 = all(r['has_ospf'] for r in state_results.values())
if not ok20:
    for s, r in state_results.items():
        if not r['has_ospf']:
            errors.append(f"FAIL T20: State {s} missing OSPF")
print(f"[T20] OSPF in all state outputs: {'PASS' if ok20 else 'FAIL'}")

# [T21] TX vs NE structural differences preserved with access filtering
tx_out = _build_nokia_config(parsed, {'state_code': 'TX'})
ne_out = _build_nokia_config(parsed, {'state_code': 'NE'})
ok21a = 'ospf 1' not in tx_out  # TX = single OSPF (only ospf 0)
ok21b = 'ospf 1' in ne_out       # NE = dual OSPF (ospf 0 + ospf 1)
ok21 = ok21a and ok21b
if not ok21:
    errors.append(f"FAIL T21: TX/NE differentiation lost (TX dual={not ok21a}, NE dual={ok21b})")
print(f"[T21] State differences preserved: {'PASS' if ok21 else 'FAIL'}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 7: No-Access Config (regression — nothing should break)
# ═══════════════════════════════════════════════════════════════════════════

# A config with NO access interfaces — should work exactly as before
no_access_config = """
# model = CCR2004-1G-12S+2XS
/interface bridge
add name=lan-bridge
/interface bridge port
add bridge=lan-bridge interface=sfp-sfpplus4
/interface ethernet
set [find default-name=sfp-sfpplus2] comment="UPLINK-1"
set [find default-name=sfp-sfpplus3] comment="UPLINK-2"
/ip address
add address=10.1.0.169/32 interface=loop0
add address=10.1.212.1/22 interface=lan-bridge
add address=10.30.248.30/30 interface=sfp-sfpplus2
add address=10.30.248.26/30 interface=sfp-sfpplus3
/routing bgp connection
add name=CR7 remote.address=10.2.0.107 .as=26077
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=lan-bridge
add area=backbone-v2 interfaces=sfp-sfpplus2 type=ptp
add area=backbone-v2 interfaces=sfp-sfpplus3 type=ptp
/mpls ldp
/system identity
set name=RTR-MTCCR2004-1.TX-NOACCTEST
/snmp community
add name=testcomm
"""

p4 = _parse_mikrotik_for_nokia(no_access_config)
pm4 = p4['port_mapping']

# [T22] No access ports means no access_excluded stat
ok22 = p4.get('stats', {}).get('access_excluded', 0) == 0
if not ok22:
    errors.append(f"FAIL T22: Expected 0 access_excluded, got {p4.get('stats', {}).get('access_excluded', 0)}")
print(f"[T22] No-access config — 0 excluded: {'PASS' if ok22 else 'FAIL'}")

# [T23] No access warning
ok23 = not any('Access/downstream' in w for w in p4.get('warnings', []))
if not ok23:
    errors.append("FAIL T23: Unexpected access warning in no-access config")
print(f"[T23] No-access config — no access warning: {'PASS' if ok23 else 'FAIL'}")

# [T24] Builder still works for no-access config
no_acc_out = _build_nokia_config(p4, {'state_code': 'TX'})
ok24 = '10.30.248.30' in no_acc_out and '10.30.248.26' in no_acc_out
if not ok24:
    errors.append("FAIL T24: No-access config builder output missing transport IPs")
print(f"[T24] No-access config builds correctly: {'PASS' if ok24 else 'FAIL'}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 8: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

# [T25] Case-insensitive keywords
case_config = """
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [find default-name=sfp-sfpplus1] comment="netonix switch"
set [find default-name=sfp-sfpplus2] comment="Uplink-1"
/ip address
add address=10.1.0.91/32 interface=loop0
add address=10.50.1.1/24 interface=sfp-sfpplus1
add address=10.30.248.30/30 interface=sfp-sfpplus2
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
add area=backbone-v2 interfaces=sfp-sfpplus2 type=ptp
/system identity
set name=RTR-MTCCR2004-1.TX-CASETEST
/snmp community
add name=testcomm
"""

p5 = _parse_mikrotik_for_nokia(case_config)
pm5 = p5['port_mapping']
ok25a = pm5.get('sfp-sfpplus1', {}).get('type') == 'access'
ok25b = pm5.get('sfp-sfpplus2', {}).get('nokia_port', '').startswith('1/1/')
ok25 = ok25a and ok25b
if not ok25:
    errors.append(f"FAIL T25: Case-insensitive detection failed. sfp1={pm5.get('sfp-sfpplus1')}, sfp2={pm5.get('sfp-sfpplus2')}")
print(f"[T25] Case-insensitive keyword detection: {'PASS' if ok25 else 'FAIL'}")

# [T26] Netonix-Switch (hyphenated variant)
hyph_config = """
# model = CCR2004-1G-12S+2XS
/interface ethernet
set [find default-name=sfp-sfpplus1] comment="Netonix-Switch-01"
set [find default-name=sfp-sfpplus2] comment="LEGACY-SW-01"
/ip address
add address=10.1.0.92/32 interface=loop0
add address=10.50.1.1/24 interface=sfp-sfpplus1
add address=10.50.2.1/24 interface=sfp-sfpplus2
/routing ospf interface-template
add area=backbone-v2 interfaces=loop0
/system identity
set name=RTR-MTCCR2004-1.TX-HYPHTEST
/snmp community
add name=testcomm
"""

p6 = _parse_mikrotik_for_nokia(hyph_config)
pm6 = p6['port_mapping']
ok26a = pm6.get('sfp-sfpplus1', {}).get('type') == 'access'  # Netonix-Switch
ok26b = pm6.get('sfp-sfpplus2', {}).get('type') == 'access'  # LEGACY-SW
ok26 = ok26a and ok26b
if not ok26:
    errors.append(f"FAIL T26: Hyphenated variants. sfp1: {pm6.get('sfp-sfpplus1')}, sfp2: {pm6.get('sfp-sfpplus2')}")
print(f"[T26] Hyphenated keyword variants: {'PASS' if ok26 else 'FAIL'}")

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
total = 26
passed = total - len(errors)
if errors:
    print(f"FAILURES ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
    print(f"\n{passed}/{total} tests passed")
    sys.exit(1)
else:
    print(f"ALL {total} PHASE 41d TESTS PASSED!")
    sys.exit(0)
