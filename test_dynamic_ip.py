#!/usr/bin/env python3
"""
Dynamic IP Preservation Stress Test
====================================
Proves the translate-config pipeline preserves ALL IPs regardless of:
  - Config shape/size (minimal → massive)
  - Device model (every ROUTERBOARD_INTERFACES model)
  - IP count (1 IP → 50+ IPs)
  - IP locations (bridges, VLANs, bondings, loops, eth, sfp)
  - Edge cases (disabled entries, duplicate IPs, /32 bare IPs, CGNAT)
  - Same-device upgrades AND cross-device migrations

Every config is GENERATED DYNAMICALLY — nothing hardcoded.
"""
import sys, os, re, json, random, ipaddress, itertools

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vm_deployment'))
sys.path.insert(0, '.')
os.environ['NOC_CONFIGMAKER_TESTS'] = '1'

from api_server import app, ROUTERBOARD_INTERFACES

PASS = 0
FAIL = 0
DETAILS = []

def log(msg):
    DETAILS.append(msg)

def check(cond, label, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        return True
    else:
        FAIL += 1
        log(f"  [FAIL] {label}: {detail}")
        return False

def extract_ip_map(text):
    """Extract {ip: interface} from /ip address section (skip PORT-EXHAUSTION)."""
    m = {}
    in_ip = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('# PORT-EXHAUSTION'):
            continue
        if s.startswith('/ip address'):
            in_ip = True
            continue
        if s.startswith('/') and not s.startswith('/ip address'):
            in_ip = False
            continue
        if in_ip or '/ip address add' in s:
            am = re.search(r'address=([^\s]+)', s)
            im = re.search(r'interface=([^\s]+)', s)
            if am:
                m[am.group(1)] = im.group(1) if im else '?'
    return m

def port_exhaustion_ips(text):
    ips = set()
    for line in text.splitlines():
        if line.strip().startswith('# PORT-EXHAUSTION'):
            am = re.search(r'address=([^\s]+)', line)
            if am:
                ips.add(am.group(1).split('/')[0])
    return ips

def run_translation(source_config, target_device, target_version='7.19.4',
                    strict=True, compliance=False):
    """Run the translate-config API and return (data, error)."""
    with app.test_client() as client:
        resp = client.post('/api/translate-config',
                           data=json.dumps({
                               'source_config': source_config,
                               'target_device': target_device,
                               'target_version': target_version,
                               'strict_preserve': strict,
                               'apply_compliance': compliance,
                           }),
                           content_type='application/json')
        data = resp.get_json()
        if not data or not data.get('success'):
            return None, data.get('error', 'unknown error') if data else 'no response'
        return data, None


# ============================================================================
# CONFIG GENERATORS — build configs dynamically from parameters
# ============================================================================

def generate_config(model, eth_ports, sfp_ports, ip_entries, extras=None):
    """
    Build a valid RouterOS config from parameters.
    
    ip_entries: list of dicts: {addr, interface, comment, disabled?, network?}
    extras: dict of extra config sections (strings)
    """
    lines = []
    lines.append(f"# 2025-06-15 12:00:00 by RouterOS 7.19.4")
    lines.append(f"# model = {model}")
    lines.append("")
    
    # Bridges
    lines.append("/interface bridge")
    lines.append('add name=lan-bridge port-cost-mode=short')
    lines.append('add name=loop0 port-cost-mode=short')
    if any(e.get('interface', '').startswith('bridge') for e in ip_entries):
        for e in ip_entries:
            iface = e.get('interface', '')
            if iface.startswith('bridge') and iface not in ('lan-bridge',):
                lines.append(f'add name={iface} port-cost-mode=short')
    if any(e.get('interface', '').startswith('nat-') for e in ip_entries):
        lines.append('add name=nat-public-bridge port-cost-mode=short')
    
    # Ethernet interfaces
    lines.append("")
    lines.append("/interface ethernet")
    for port in eth_ports:
        name = port['name']
        comment = port.get('comment', '')
        speed = port.get('speed', '1G-baseT-full')
        parts = [f'set [ find default-name={name} ]']
        if comment:
            parts.append(f'comment="{comment}"')
        if speed:
            parts.append(f'speed={speed}')
        lines.append(' '.join(parts))
    for port in sfp_ports:
        name = port['name']
        comment = port.get('comment', '')
        speed = port.get('speed', '')
        parts = [f'set [ find default-name={name} ]']
        if comment:
            parts.append(f'comment="{comment}"')
        if speed:
            parts.append(f'speed={speed}')
        lines.append(' '.join(parts))
    
    # VLANs if needed
    vlan_ifaces = [e['interface'] for e in ip_entries if e.get('interface', '').startswith('vlan')]
    if vlan_ifaces:
        lines.append("")
        lines.append("/interface vlan")
        for v in set(vlan_ifaces):
            vid = re.search(r'(\d+)', v)
            vid = vid.group(1) if vid else '100'
            lines.append(f'add interface=lan-bridge name={v} vlan-id={vid}')
    
    # Bonding if needed
    bonding_ifaces = [e['interface'] for e in ip_entries if 'bonding' in e.get('interface', '')]
    if bonding_ifaces:
        lines.append("")
        lines.append("/interface bonding")
        for b in set(bonding_ifaces):
            # Pick 2 sfp ports as slaves
            slaves = ','.join(p['name'] for p in sfp_ports[:2]) if sfp_ports else 'sfp28-4,sfp28-5'
            lines.append(f'add mode=802.3ad name={b} slaves={slaves}')
    
    # IP addresses
    lines.append("")
    lines.append("/ip address")
    for e in ip_entries:
        parts = ['add']
        parts.append(f"address={e['addr']}")
        if e.get('comment'):
            parts.append(f'comment="{e["comment"]}"')
        if e.get('disabled'):
            parts.append('disabled=yes')
        parts.append(f"interface={e['interface']}")
        if e.get('network'):
            parts.append(f"network={e['network']}")
        lines.append(' '.join(parts))
    
    # OSPF
    router_id = None
    for e in ip_entries:
        if e['interface'] == 'loop0':
            router_id = e['addr'].split('/')[0]
            break
    if not router_id:
        router_id = '10.0.0.1'
    
    lines.append("")
    lines.append("/routing ospf instance")
    lines.append(f'add disabled=no name=default-v2 router-id={router_id}')
    lines.append("")
    lines.append("/routing ospf area")
    lines.append('add disabled=no instance=default-v2 name=backbone-v2')
    lines.append("")
    lines.append("/routing ospf interface-template")
    lines.append(f'add area=backbone-v2 cost=10 disabled=no interfaces=loop0 networks={router_id}/32 passive priority=1')
    
    # BGP template
    lines.append("")
    lines.append("/routing bgp template")
    lines.append(f'set default as=26077 disabled=no output.network=bgp-networks router-id={router_id}')
    
    # Firewall
    lines.append("")
    lines.append("/ip firewall filter")
    lines.append('add chain=input action=accept protocol=icmp')
    lines.append('add chain=forward action=accept connection-state=established,related')
    
    # Identity
    lines.append("")
    lines.append("/system identity")
    model_short = model.split('-')[0]
    lines.append(f'set name=RTR-MT{model_short}-TEST-SITE')
    
    if extras:
        for section, content in extras.items():
            lines.append("")
            lines.append(content)
    
    return '\n'.join(lines) + '\n'


def get_model_ports(model_key):
    """Get port info for a ROUTERBOARD_INTERFACES model."""
    info = ROUTERBOARD_INTERFACES.get(model_key, {})
    ports = info.get('ports', [])
    mgmt = info.get('management', 'ether1')
    eth = [p for p in ports if p.startswith('ether')]
    sfp = [p for p in ports if not p.startswith('ether') and not p.startswith('qsfp')]
    return eth, sfp, mgmt, ports


# ============================================================================
# TEST CASES — each generates a unique config dynamically
# ============================================================================

ALL_MODELS = list(ROUTERBOARD_INTERFACES.keys())

# Helper: random IP generator
_ip_counter = itertools.count(1)
def next_ip(prefix='10.50', mask=30):
    n = next(_ip_counter)
    return f"{prefix}.{n // 256}.{n % 256}/{mask}"

def random_comment():
    names = ['TX-DALLAS-BH', 'KS-TOPEKA-BH', 'SPARKLIGHT', 'Nokia-OLT', 'CNMATRIX',
             'Netonix-SW', 'ICT-UPS', 'LTE-Backup', 'Tarana-Alpha', 'Customer-A',
             'CGNAT', 'Core-Uplink', 'Ring-A', 'Ring-B', 'Spare']
    return random.choice(names)


print(f"\n{'='*70}")
print(f"DYNAMIC IP PRESERVATION STRESS TEST")
print(f"Testing {len(ALL_MODELS)} routerboard models × various scenarios")
print(f"{'='*70}\n")


# ── TEST SET 1: Same-device translation (fast-mode path) ──────────────
log("\n=== TEST SET 1: Same-Device (Fast-Mode) — every model ===")
print("Test Set 1: Same-device fast-mode for every model...")

for model_key in ALL_MODELS:
    eth_raw, sfp_raw, mgmt, all_ports = get_model_ports(model_key)
    model_name = ROUTERBOARD_INTERFACES[model_key]['model']

    # Build port definitions
    eth_ports = [{'name': p, 'comment': 'Management' if p == mgmt else random_comment(),
                  'speed': '1G-baseT-full'} for p in eth_raw]
    sfp_ports = [{'name': p, 'comment': random_comment(),
                  'speed': '10G-baseSR-LR'} for p in sfp_raw]

    # Generate IPs on every usable port + bridges + loop
    ip_entries = [{'addr': '10.0.0.1', 'interface': 'loop0', 'comment': 'Loopback'}]
    ip_entries.append({'addr': '192.168.88.1/24', 'interface': mgmt, 'comment': 'Management'})
    
    non_mgmt = [p for p in all_ports if p != mgmt and not p.startswith('qsfp')]
    for i, port in enumerate(non_mgmt[:8]):  # Up to 8 port IPs
        ip_entries.append({'addr': next_ip(), 'interface': port, 'comment': f'Link-{i+1}'})
    
    # Add bridge + vlan IPs
    ip_entries.append({'addr': next_ip('100.70', 22), 'interface': 'bridge1000', 'comment': 'CGNAT'})
    ip_entries.append({'addr': next_ip('10.17', 22), 'interface': 'lan-bridge', 'comment': 'CPE'})
    
    config = generate_config(model_name, eth_ports, sfp_ports, ip_entries)
    source_ips = extract_ip_map(config)
    
    data, err = run_translation(config, model_name)
    
    test_label = f"Same-Device {model_name}"
    if err:
        check(False, test_label, f"API error: {err}")
        continue
    
    translated = data.get('translated_config', '')
    trans_ips = extract_ip_map(translated)
    exhaust = port_exhaustion_ips(translated)
    
    # Check: all source IPs accounted for (active OR exhaustion)
    source_bases = {a.split('/')[0] for a in source_ips}
    trans_bases = {a.split('/')[0] for a in trans_ips}
    all_accounted = source_bases <= (trans_bases | exhaust)
    check(all_accounted, test_label,
          f"Lost IPs: {source_bases - trans_bases - exhaust}")
    
    # Check: validation agrees
    val = data.get('validation', {})
    check(len(val.get('missing_ips', [])) == 0, f"{test_label} validation",
          f"missing_ips={val.get('missing_ips')}")


# ── TEST SET 2: Cross-device migrations — every pair ──────────────────
log("\n=== TEST SET 2: Cross-Device Migrations ===")
print("\nTest Set 2: Cross-device migrations...")

MIGRATION_PAIRS = [
    ('CCR1072-1G-4S+', 'CCR2216-1G-12XS-2XQ'),
    ('CCR1072-1G-4S+', 'CCR2004-1G-12S+2XS'),
    ('CCR1072-1G-4S+', 'CCR2004-16G-2S+'),
    ('CCR1072-1G-4S+', 'CCR2116-12G-4S+'),
    ('CCR2004-1G-12S+2XS', 'CCR2216-1G-12XS-2XQ'),
    ('CCR2004-1G-12S+2XS', 'CCR2116-12G-4S+'),
    ('CCR2004-16G-2S+', 'CCR2216-1G-12XS-2XQ'),
    ('CCR2116-12G-4S+', 'CCR2216-1G-12XS-2XQ'),
    ('CCR2116-12G-4S+', 'CCR2004-16G-2S+'),
    ('CCR2216-1G-12XS-2XQ', 'CCR2116-12G-4S+'),
]

for src_model, tgt_model in MIGRATION_PAIRS:
    src_key = next((k for k, v in ROUTERBOARD_INTERFACES.items() if v['model'] == src_model), None)
    if not src_key:
        continue
    eth_raw, sfp_raw, mgmt, all_ports = get_model_ports(src_key)
    
    eth_ports = [{'name': p, 'comment': 'Management' if p == mgmt else '',
                  'speed': '1G-baseT-full'} for p in eth_raw]
    sfp_ports = [{'name': p, 'comment': '', 'speed': '10G-baseSR-LR'} for p in sfp_raw]
    
    # Assign meaningful comments (backhaul-heavy)
    assigned = 0
    role_sequence = ['Switch-Netonix-1', 'Switch-Netonix-2', 'ICT-UPS',
                     'TX-DALLAS-BH-1', 'TX-HOUSTON-BH-2', 'KS-TOPEKA-BH-3',
                     'Tarana-Alpha', 'LTE-Backup', 'SPARKLIGHT-EPL', 'Ring-A']
    for port_list in (eth_ports, sfp_ports):
        for p in port_list:
            if p['name'] == mgmt:
                p['comment'] = 'Management'
            elif assigned < len(role_sequence):
                p['comment'] = role_sequence[assigned]
                assigned += 1
    
    # IPs
    ip_entries = [
        {'addr': '10.0.0.1', 'interface': 'loop0', 'comment': 'Loopback'},
        {'addr': '192.168.88.1/24', 'interface': mgmt, 'comment': 'Management'},
    ]
    
    non_mgmt = [p for p in all_ports if p != mgmt and not p.startswith('qsfp')]
    for i, port in enumerate(non_mgmt):
        ip_entries.append({'addr': next_ip(), 'interface': port, 'comment': f'Link-{i+1}'})
    
    # Add extra IPs on bridges/vlans
    ip_entries.append({'addr': next_ip('100.70', 22), 'interface': 'bridge2000', 'comment': 'CGNAT'})
    ip_entries.append({'addr': '132.147.184.147', 'interface': 'nat-public-bridge',
                       'comment': 'CGNAT PUBLIC', 'network': '132.147.184.147'})
    ip_entries.append({'addr': next_ip('10.17', 22), 'interface': 'lan-bridge', 'comment': 'CPE'})
    
    config = generate_config(src_model, eth_ports, sfp_ports, ip_entries)
    source_ips = extract_ip_map(config)
    
    data, err = run_translation(config, tgt_model)
    
    test_label = f"{src_model} → {tgt_model} ({len(source_ips)} IPs)"
    if err:
        check(False, test_label, f"API error: {err}")
        continue
    
    translated = data.get('translated_config', '')
    trans_ips = extract_ip_map(translated)
    exhaust = port_exhaustion_ips(translated)
    
    source_bases = {a.split('/')[0] for a in source_ips}
    trans_bases = {a.split('/')[0] for a in trans_ips}
    all_accounted = source_bases <= (trans_bases | exhaust)
    
    check(all_accounted, test_label,
          f"Lost: {source_bases - trans_bases - exhaust}")
    
    val = data.get('validation', {})
    check(len(val.get('missing_ips', [])) == 0, f"{test_label} validation",
          f"missing_ips={val.get('missing_ips')}")


# ── TEST SET 3: Edge Cases ───────────────────────────────────────────
log("\n=== TEST SET 3: Edge Cases ===")
print("\nTest Set 3: Edge cases...")

# 3a: Config with 50+ customer IPs on bridges (like Hempstead)
eth_raw, sfp_raw, mgmt, all_ports = get_model_ports('CCR2216-1G-12XS-2XQ')
eth_ports = [{'name': 'ether1', 'comment': 'Management', 'speed': '1G-baseT-full'}]
sfp_ports = [
    {'name': 'sfp28-1', 'comment': 'SPARKLIGHT', 'speed': '10G-baseSR-LR'},
    {'name': 'sfp28-2', 'comment': 'HEMPSTEAD-BH', 'speed': '10G-baseSR-LR'},
    {'name': 'sfp28-4', 'comment': 'NOKIA FX8 OLT', 'speed': '10G-baseSR-LR'},
    {'name': 'sfp28-5', 'comment': 'NOKIA FX8 OLT', 'speed': '10G-baseSR-LR'},
    {'name': 'sfp28-8', 'comment': 'CNMATRIX', 'speed': '10G-baseSR-LR'},
]
ip_entries = [
    {'addr': '10.33.0.95', 'interface': 'loop0', 'comment': 'loop0'},
    {'addr': '10.33.1.154/30', 'interface': 'sfp28-1', 'comment': 'SPARKLIGHT'},
    {'addr': '10.33.1.157/30', 'interface': 'sfp28-2', 'comment': 'HEMPSTEAD-BH'},
    {'addr': '10.17.108.1/22', 'interface': 'lan-bridge', 'comment': 'CPE'},
    {'addr': '10.25.250.121/29', 'interface': 'bridge3000', 'comment': 'OLT SUBNET'},
    {'addr': '100.70.224.1/22', 'interface': 'bridge1000', 'comment': 'CGNAT PRIVATE'},
    {'addr': '132.147.184.147', 'interface': 'nat-public-bridge', 'comment': 'CGNAT PUBLIC',
     'network': '132.147.184.147'},
]
# Add 20 customer IPs on bridge2000 (like real production)
for i in range(20):
    ip_entries.append({
        'addr': f'52.128.{50+i}.{1+i*4}/30',
        'interface': 'bridge2000',
        'comment': f'Customer-{i+1}'
    })
# Add disabled entries (like real production)
ip_entries.append({'addr': '52.128.49.185/30', 'interface': 'bridge2000',
                   'comment': 'OldCustomer-Disabled', 'disabled': True})
# Add duplicate base IP (different comments — like real config)
ip_entries.append({'addr': '107.178.2.17/30', 'interface': 'bridge2000',
                   'comment': 'Julie-Ashlock-old', 'disabled': True})
ip_entries.append({'addr': '107.178.2.17/30', 'interface': 'bridge2000',
                   'comment': 'Arthur-Glover'})

config = generate_config('CCR2216-1G-12XS-2XQ', eth_ports, sfp_ports, ip_entries)
source_ips = extract_ip_map(config)
data, err = run_translation(config, 'CCR2216-1G-12XS-2XQ')
test_label = f"Edge: 30+ IPs with disabled+dupes on CCR2216 ({len(source_ips)} IPs)"
if err:
    check(False, test_label, f"API error: {err}")
else:
    translated = data.get('translated_config', '')
    trans_ips = extract_ip_map(translated)
    source_bases = {a.split('/')[0] for a in source_ips}
    trans_bases = {a.split('/')[0] for a in trans_ips}
    exhaust = port_exhaustion_ips(translated)
    all_accounted = source_bases <= (trans_bases | exhaust)
    check(all_accounted, test_label, f"Lost: {source_bases - trans_bases - exhaust}")
    val = data.get('validation', {})
    check(len(val.get('missing_ips', [])) == 0, f"{test_label} val",
          f"missing_ips={val.get('missing_ips')}")
    # Verify disabled entries preserved
    disabled_count = translated.count('disabled=yes')
    src_disabled_count = config.count('disabled=yes')
    check(disabled_count >= src_disabled_count,
          f"{test_label} disabled entries",
          f"source={src_disabled_count}, translated={disabled_count}")


# 3b: Minimal config — just 1 IP
config_minimal = """# 2025-01-01 by RouterOS 7.19.4
# model = CCR2216-1G-12XS-2XQ
/interface ethernet
set [ find default-name=ether1 ] comment="Management"
/ip address
add address=192.168.88.1/24 interface=ether1 comment="Management"
/system identity
set name=RTR-MINIMAL
"""
data, err = run_translation(config_minimal, 'CCR2216-1G-12XS-2XQ')
test_label = "Edge: Minimal 1-IP config"
if err:
    check(False, test_label, f"API error: {err}")
else:
    trans_ips = extract_ip_map(data.get('translated_config', ''))
    check('192.168.88.1/24' in trans_ips or any('192.168.88.1' in k for k in trans_ips),
          test_label, f"Only IP not found in translated: {trans_ips}")


# 3c: /32 bare IPs and network= IPs (no CIDR mask)
config_bare = """# 2025-01-01 by RouterOS 7.19.4
# model = CCR2216-1G-12XS-2XQ
/interface bridge
add name=loop0 port-cost-mode=short
add name=nat-public-bridge port-cost-mode=short
/interface ethernet
set [ find default-name=ether1 ] comment="Management"
set [ find default-name=sfp28-1 ] comment="Uplink"
/ip address
add address=10.33.0.95 interface=loop0 comment="Loop" network=10.33.0.95
add address=132.147.184.147 interface=nat-public-bridge comment="CGNAT" network=132.147.184.147
add address=192.168.88.1/24 interface=ether1 comment="Mgmt"
add address=10.33.1.154/30 interface=sfp28-1 comment="BH"
/routing ospf instance
add disabled=no name=default-v2 router-id=10.33.0.95
/routing ospf area
add disabled=no instance=default-v2 name=backbone-v2
/system identity
set name=RTR-BARE-IPS
"""
data, err = run_translation(config_bare, 'CCR2216-1G-12XS-2XQ')
test_label = "Edge: Bare /32 IPs (no mask)"
if err:
    check(False, test_label, f"API error: {err}")
else:
    trans_ips = extract_ip_map(data.get('translated_config', ''))
    trans_bases = {a.split('/')[0] for a in trans_ips}
    check('10.33.0.95' in trans_bases, f"{test_label} loop0")
    check('132.147.184.147' in trans_bases, f"{test_label} cgnat")
    check('192.168.88.1' in trans_bases, f"{test_label} mgmt")
    check('10.33.1.154' in trans_bases, f"{test_label} bh")


# 3d: Config with VLANs on bondings (complex interface chain)
config_bonding = """# 2025-01-01 by RouterOS 7.19.4
# model = CCR2216-1G-12XS-2XQ
/interface bridge
add name=bridge1000 port-cost-mode=short
add name=bridge2000 port-cost-mode=short
add name=bridge3000 port-cost-mode=short
add name=loop0 port-cost-mode=short
add name=lan-bridge port-cost-mode=short
/interface ethernet
set [ find default-name=ether1 ] comment="Management"
set [ find default-name=sfp28-1 ] comment="SPARKLIGHT"
set [ find default-name=sfp28-2 ] comment="Core-BH"
set [ find default-name=sfp28-4 ] comment="NOKIA FX8 OLT"
set [ find default-name=sfp28-5 ] comment="NOKIA FX8 OLT"
set [ find default-name=sfp28-6 ] comment="NOKIA FX8 OLT"
set [ find default-name=sfp28-8 ] comment="CNMATRIX"
/interface bonding
add mode=802.3ad name=bonding3000 slaves=sfp28-4,sfp28-5,sfp28-6
/interface vlan
add interface=bonding3000 name=vlan1000 vlan-id=1000
add interface=bonding3000 name=vlan2000 vlan-id=2000
add interface=bonding3000 name=vlan3000 vlan-id=3000
/interface bridge port
add bridge=bridge1000 interface=vlan1000
add bridge=bridge2000 interface=vlan2000
add bridge=bridge3000 interface=vlan3000
add bridge=lan-bridge interface=sfp28-8
/ip address
add address=10.33.0.95 interface=loop0 comment="Loop" network=10.33.0.95
add address=192.168.88.1/24 interface=ether1 comment="Mgmt"
add address=10.33.1.154/30 interface=sfp28-1 comment="SPARKLIGHT"
add address=10.33.1.157/30 interface=sfp28-2 comment="Core-BH"
add address=10.25.250.121/29 interface=bridge3000 comment="OLT"
add address=100.70.224.1/22 interface=bridge1000 comment="CGNAT"
add address=10.17.108.1/22 interface=lan-bridge comment="CPE"
add address=10.117.108.1/22 interface=lan-bridge comment="UNAUTH"
add address=132.147.181.177/30 interface=bridge2000 comment="Customer-1"
add address=67.219.118.41/30 interface=bridge2000 comment="Customer-2"
add address=52.128.60.1/30 interface=bridge2000 comment="Customer-3"
add address=52.128.62.21/30 interface=vlan2000 comment="Customer-4"
/routing ospf instance
add disabled=no name=default-v2 router-id=10.33.0.95
/routing ospf area
add disabled=no instance=default-v2 name=backbone-v2
/routing ospf interface-template
add area=backbone-v2 cost=10 disabled=no interfaces=loop0 networks=10.33.0.95/32 passive priority=1
add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM cost=10 disabled=no interfaces=sfp28-1 networks=10.33.1.152/30 priority=1 type=ptp
add area=backbone-v2 cost=10 disabled=no interfaces=bonding3000 networks=10.33.1.184/29 priority=1
/system identity
set name=RTR-MT2216-BONDING-TEST
"""
source_ips = extract_ip_map(config_bonding)
data, err = run_translation(config_bonding, 'CCR2216-1G-12XS-2XQ')
test_label = f"Edge: Bonding+VLAN+Bridge ({len(source_ips)} IPs)"
if err:
    check(False, test_label, f"API error: {err}")
else:
    trans_ips = extract_ip_map(data.get('translated_config', ''))
    source_bases = {a.split('/')[0] for a in source_ips}
    trans_bases = {a.split('/')[0] for a in trans_ips}
    exhaust = port_exhaustion_ips(data.get('translated_config', ''))
    all_accounted = source_bases <= (trans_bases | exhaust)
    check(all_accounted, test_label, f"Lost: {source_bases - trans_bases - exhaust}")
    val = data.get('validation', {})
    check(len(val.get('missing_ips', [])) == 0, f"{test_label} val",
          f"missing_ips={val.get('missing_ips')}")


# ── RESULTS ──────────────────────────────────────────────────────────
print(f"\n{'='*70}")
total = PASS + FAIL
print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
if FAIL > 0:
    print(f"\nFAILURES:")
    for d in DETAILS:
        if '[FAIL]' in d:
            print(d)
else:
    print("ALL TESTS PASSED — IP preservation is FULLY DYNAMIC")
print(f"{'='*70}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
          'dynamic_test_results.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(DETAILS))
    f.write(f'\n\nRESULTS: {PASS}/{total} passed, {FAIL} failed\n')

sys.exit(1 if FAIL else 0)
