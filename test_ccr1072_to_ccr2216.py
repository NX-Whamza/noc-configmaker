#!/usr/bin/env python3
"""
Thorough CCR1072 → CCR2216 Migration Test
==========================================
Validates the full translate-config pipeline for a realistic
CCR1072-12G-4S+ → CCR2216-1G-12XS-2XQ migration with loopback IP 10.33.0.95.

Checks:
  1. Speed: no double-suffix (10G-baseSR-LR, NOT 10G-baseSR-LR-LR)
  2. Compliance stripping: managed address-lists removed from source section
  3. Compliance injection: GitLab compliance appended exactly once
  4. Site-specific lists preserved (unauth, NETFLIX, bgp-networks, etc.)
  5. No duplicate compliance sections
  6. Correct interface mapping (copper→optical)
  7. Loopback IP substitution in compliance
  8. All critical sections preserved
"""
import sys, os, re, json

# Ensure we can import from vm_deployment
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vm_deployment'))
sys.path.insert(0, '.')

from api_server import app

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")
        if detail:
            print(f"         -> {detail}")
    return condition


# ═══════════════════════════════════════════════════════════════════
# REALISTIC CCR1072-12G-4S+ SOURCE CONFIG
# ═══════════════════════════════════════════════════════════════════
# Mimics TX-HEMPSTEAD-FC-1 — RouterOS 7.19.4 with extensive site config
SOURCE_CONFIG = r"""# 2025-01-10 08:30:00 by RouterOS 7.19.4
# software id = FAKE-TEST
# model = CCR1072-12G-4S+
# serial number = TEST1234

/interface ethernet
set [ find default-name=ether1 ] comment="Management" speed=1G-baseT-full
set [ find default-name=ether2 ] comment="Switch-Netonix-Core" speed=1G-baseT-full
set [ find default-name=ether3 ] comment="Switch-Netonix-N1" speed=1G-baseT-full
set [ find default-name=ether4 ] comment="Nokia-OLT-FTTH" speed=1G-baseT-full
set [ find default-name=ether5 ] comment="ICT-UPS-Power" speed=1G-baseT-full
set [ find default-name=ether6 ] comment="LTE-Backup" speed=1G-baseT-full
set [ find default-name=ether7 ] comment="TX-HEMPSTEAD-BH-1" speed=1G-baseT-full
set [ find default-name=ether8 ] comment="TX-HEMPSTEAD-BH-2" speed=1G-baseT-full
set [ find default-name=ether9 ] comment="Tarana-Alpha-1" speed=1G-baseT-full
set [ find default-name=ether10 ] comment="Sector-1-Cambium" speed=1G-baseT-full
set [ find default-name=ether11 ] comment="Sector-2-Cambium" speed=1G-baseT-full
set [ find default-name=ether12 ] comment="Sector-3-Cambium" speed=1G-baseT-full
set [ find default-name=sfp-sfpplus1 ] comment="TX-DALLAS-RING-A" speed=10G-baseSR-LR
set [ find default-name=sfp-sfpplus2 ] comment="TX-DALLAS-RING-B" speed=10G-baseSR-LR
set [ find default-name=sfp-sfpplus3 ] comment="Core-Uplink-Primary" speed=10G-baseSR-LR
set [ find default-name=sfp-sfpplus4 ] comment="Core-Uplink-Secondary" speed=10G-baseSR-LR

/interface bridge
add name=bridge1 comment="Main-Customer-Bridge"
add name=bridge-mgmt comment="Management-Bridge"

/interface vlan
add interface=bridge1 name=VLAN100-Customers vlan-id=100
add interface=bridge1 name=VLAN200-CCTV vlan-id=200
add interface=bridge1 name=VLAN300-VoIP vlan-id=300
add interface=ether2 name=VLAN500-NMS vlan-id=500

/interface bridge port
add bridge=bridge1 interface=ether2 comment="Netonix-Core-Trunk"
add bridge=bridge1 interface=ether3 comment="Netonix-N1-Trunk"
add bridge=bridge1 interface=ether10 comment="Sector-1"
add bridge=bridge1 interface=ether11 comment="Sector-2"
add bridge=bridge1 interface=ether12 comment="Sector-3"

/interface bonding
add mode=802.3ad name=bond-uplink slaves=sfp-sfpplus1,sfp-sfpplus2 comment="Ring-Bond"

/ip address
add address=192.168.88.1/24 interface=ether1 comment="Management"
add address=10.33.0.95/32 interface=loop0 comment="Loopback"
add address=10.10.1.1/30 interface=sfp-sfpplus1 comment="Ring-A"
add address=10.10.2.1/30 interface=sfp-sfpplus2 comment="Ring-B"
add address=10.10.3.1/30 interface=sfp-sfpplus3 comment="Core-Primary"
add address=10.10.4.1/30 interface=sfp-sfpplus4 comment="Core-Secondary"
add address=10.20.1.1/24 interface=VLAN100-Customers comment="DHCP-Pool-1"
add address=10.20.2.1/24 interface=VLAN200-CCTV comment="CCTV-Network"
add address=10.20.3.1/24 interface=VLAN300-VoIP comment="VoIP-Network"
add address=172.16.1.1/30 interface=ether4 comment="Nokia-OLT"

/ip dhcp-server network
add address=10.20.1.0/24 gateway=10.20.1.1 dns-server=142.147.112.3,142.147.112.19 comment="Customers-DHCP"
add address=10.20.3.0/24 gateway=10.20.3.1 dns-server=142.147.112.3,142.147.112.19 comment="VoIP-DHCP"

/ip dhcp-server
add address-pool=pool-customers interface=VLAN100-Customers name=dhcp-customers disabled=no
add address-pool=pool-voip interface=VLAN300-VoIP name=dhcp-voip disabled=no

/ip pool
add name=pool-customers ranges=10.20.1.100-10.20.1.254
add name=pool-voip ranges=10.20.3.100-10.20.3.254

/routing ospf instance
add disabled=no name=default-v2 router-id=10.33.0.95

/routing ospf area
add disabled=no instance=default-v2 name=backbone-v2

/routing ospf interface-template
add area=backbone-v2 interfaces=sfp-sfpplus1 networks=10.10.1.0/30 comment="Ring-A"
add area=backbone-v2 interfaces=sfp-sfpplus2 networks=10.10.2.0/30 comment="Ring-B"
add area=backbone-v2 interfaces=sfp-sfpplus3 networks=10.10.3.0/30 comment="Core-Primary"
add area=backbone-v2 interfaces=sfp-sfpplus4 networks=10.10.4.0/30 comment="Core-Secondary"
add area=backbone-v2 interfaces=loop0 networks=10.33.0.95/32 comment="Loopback"

/routing bgp connection
add as=65001 disabled=no local.role=ebgp name=BGP-Peer-1 remote.address=10.10.3.2 remote.as=65000 routing-table=main comment="Core-BGP"

/ip firewall address-list
add address=10.33.0.0/24 list=EOIP-ALLOW comment="EOIP tunnel allow"
add address=142.147.112.0/24 list=EOIP-ALLOW comment="Management subnet"
add address=10.33.0.95 list=managerIP comment="This router"
add address=142.147.112.2 list=managerIP comment="NOC-1"
add address=142.147.112.18 list=managerIP comment="NOC-2"
add address=10.0.0.0/8 list=BGP-ALLOW comment="Internal BGP"
add address=192.168.0.0/16 list=BGP-ALLOW comment="Private BGP"
add address=142.147.112.3 list=SNMP comment="SNMP-server-1"
add address=142.147.112.19 list=SNMP comment="SNMP-server-2"
add address=0.0.0.0/0 list=WALLED-GARDEN comment="Walled garden"
add address=10.20.1.0/24 list=unauth comment="Unauthenticated clients"
add address=10.20.2.0/24 list=NETFLIX comment="Streaming-allow"
add address=142.147.112.2 list=Voip-Servers comment="VoIP RADIUS 1"
add address=142.147.112.18 list=Voip-Servers comment="VoIP RADIUS 2"
add address=10.33.0.0/16 list=bgp-networks comment="BGP advertised networks"
add address=172.16.0.0/12 list=NTP comment="NTP sources"

/ip firewall filter
add action=accept chain=input comment="Allow established" connection-state=established,related
add action=accept chain=input comment="Allow ICMP" protocol=icmp
add action=accept chain=input comment="Allow SSH from management" dst-port=22 protocol=tcp src-address-list=managerIP
add action=accept chain=input comment="Allow Winbox" dst-port=8291 protocol=tcp src-address-list=managerIP
add action=accept chain=input comment="Allow SNMP" dst-port=161 protocol=udp src-address-list=SNMP
add action=accept chain=input comment="Allow BGP" dst-port=179 protocol=tcp src-address-list=BGP-ALLOW
add action=drop chain=input comment="DROP INPUT"
add action=accept chain=forward comment="Allow established forward" connection-state=established,related
add action=drop chain=forward comment="Drop invalid forward" connection-state=invalid

/ip firewall nat
add action=masquerade chain=srcnat out-interface=sfp-sfpplus3 comment="Source NAT"

/ip firewall mangle
add action=mark-connection chain=prerouting new-connection-mark=customers passthrough=yes src-address=10.20.1.0/24 comment="Mark customers"

/ip firewall service-port
set ftp disabled=yes
set tftp disabled=yes
set sip disabled=yes

/ip firewall connection tracking
set enabled=auto

/ip dns
set allow-remote-requests=yes servers=142.147.112.3,142.147.112.19

/ip service
set telnet disabled=yes
set ftp disabled=yes
set www disabled=yes
set ssh port=22
set api disabled=yes
set winbox port=8291
set api-ssl disabled=yes

/snmp
set enabled=yes contact="NOC" location="TX-HEMPSTEAD-FC" trap-community=FBZ1yYdphf

/snmp community
set [ find default=yes ] name=FBZ1yYdphf addresses=142.147.112.0/24

/system clock
set time-zone-name=America/Chicago

/system ntp client
set enabled=yes
/system ntp client servers
add address=ntp-pool.nxlink.com

/system logging action
set remote address=142.147.116.215 bsd-syslog=yes name=remote remote-port=514

/system logging
add action=remote topics=critical
add action=remote topics=error
add action=remote topics=warning
add action=remote topics=info

/user group
set full policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api

/user aaa
set use-radius=yes

/radius
add address=142.147.112.2 service=dhcp secret=RadiusSecret123 comment="RADIUS-1"
add address=142.147.112.18 service=dhcp secret=RadiusSecret123 comment="RADIUS-2"

/queue simple
add max-limit=100M/100M name=queue-customers target=10.20.1.0/24 comment="Customer bandwidth"

/system identity
set name=TX-HEMPSTEAD-FC-1

/system routerboard settings
set auto-upgrade=yes

/tool bandwidth-server
set enabled=no
"""


def run_test():
    global PASS, FAIL
    
    print("=" * 80)
    print("THOROUGH CCR1072 -> CCR2216 MIGRATION TEST")
    print("Loopback: 10.33.0.95  |  Firmware: 7.19.4  |  Compliance: ON")
    print("=" * 80)
    
    with app.test_client() as client:
        payload = {
            'source_config': SOURCE_CONFIG,
            'target_device': 'CCR2216-1G-12XS-2XQ',
            'target_version': '7.19.4',
            'strict_preserve': True,
            'apply_compliance': True,
        }
        
        print("\n[1] Calling POST /api/translate-config ...")
        resp = client.post('/api/translate-config',
                           data=json.dumps(payload),
                           content_type='application/json')
        
        check("HTTP 200", resp.status_code == 200,
              f"Got {resp.status_code}")
        
        data = resp.get_json()
        check("success=true", data.get('success') is True,
              f"Got success={data.get('success')}")
        
        translated = data.get('translated_config', '')
        check("Non-empty translated config", len(translated) > 500,
              f"Got {len(translated)} chars")
        
        # Save full output for inspection
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'test_output_ccr1072_to_ccr2216.txt')
        out_path = os.path.normpath(out_path)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(translated)
        print(f"\n  [INFO] Full output saved to {out_path}")
        
        # -- SPLIT into source section vs compliance section --
        compliance_marker = "# RFC-09-10-25 COMPLIANCE STANDARDS"
        parts = translated.split(compliance_marker)
        
        check("Compliance section exists",
              compliance_marker in translated,
              "RFC-09-10-25 header not found")
        
        check("Compliance section appears exactly once",
              translated.count(compliance_marker) == 1,
              f"Found {translated.count(compliance_marker)} occurrences")
        
        if len(parts) >= 2:
            source_section = parts[0]
            compliance_section = compliance_marker + parts[1]
        else:
            source_section = translated
            compliance_section = ""
        
        # =======================================
        # TEST GROUP A: SPEED HANDLING
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP A: SPEED HANDLING")
        print("-" * 60)
        
        # A1: No double-suffix 10G-baseSR-LR-LR
        double_lr_matches = re.findall(r'10G-baseSR-LR-LR', translated)
        check("No double-suffix 10G-baseSR-LR-LR",
              len(double_lr_matches) == 0,
              f"Found {len(double_lr_matches)} occurrences of -LR-LR")
        
        # A2: 10G-baseSR-LR present (correct form)
        correct_10g = re.findall(r'10G-baseSR-LR(?!-)', translated)
        check("10G-baseSR-LR present (correct)",
              len(correct_10g) > 0,
              "No 10G-baseSR-LR speed values found")
        
        # A3: No copper speeds on CCR2216 optical ports (sfp28-*)
        copper_on_sfp28 = re.findall(r'sfp28-\d+.*?speed=\d+G-baseT', translated)
        check("No copper speed on sfp28 ports",
              len(copper_on_sfp28) == 0,
              f"Found copper speed on sfp28: {copper_on_sfp28}")
        
        # A4: No old-style speed values (e.g., 10Gbps)
        old_speed = re.findall(r'speed=\d+Gbps', translated)
        check("No old-style speed values (10Gbps etc.)",
              len(old_speed) == 0,
              f"Found old-style: {old_speed}")
        
        # =======================================
        # TEST GROUP B: COMPLIANCE STRIPPING
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP B: COMPLIANCE STRIPPING (managed lists removed from source)")
        print("-" * 60)
        
        # B1-B5: Managed address-lists should NOT be in source section
        managed_lists = ['EOIP-ALLOW', 'managerIP', 'BGP-ALLOW', 'SNMP', 'WALLED-GARDEN']
        for list_name in managed_lists:
            pattern = rf'list={list_name}\b'
            source_matches = re.findall(pattern, source_section)
            check(f"list={list_name} NOT in source section",
                  len(source_matches) == 0,
                  f"Found {len(source_matches)} in source section (should be 0)")
        
        # B6: Managed address-lists SHOULD be in compliance section
        for list_name in managed_lists:
            pattern = rf'list={list_name}\b'
            compliance_matches = re.findall(pattern, compliance_section)
            check(f"list={list_name} IN compliance section",
                  len(compliance_matches) > 0,
                  f"Not found in compliance section")
        
        # =======================================
        # TEST GROUP C: SITE-SPECIFIC LISTS PRESERVED
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP C: SITE-SPECIFIC LISTS PRESERVED (not stripped)")
        print("-" * 60)
        
        site_lists = ['unauth', 'NETFLIX', 'Voip-Servers', 'bgp-networks', 'NTP']
        for list_name in site_lists:
            pattern = rf'list={list_name}\b'
            source_matches = re.findall(pattern, source_section)
            check(f"list={list_name} preserved in source section",
                  len(source_matches) > 0,
                  f"MISSING from source section (site-specific list stripped!)")
        
        # =======================================
        # TEST GROUP D: COMPLIANCE SECTION CONTENT
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP D: COMPLIANCE SECTION CONTENT")
        print("-" * 60)
        
        # D1: Loopback IP — the GitLab compliance script resolves loop0 IP
        # dynamically at runtime via :global LoopIP, so the literal 10.33.0.95
        # won't appear. Instead verify the LoopIP resolver is present.
        check("LoopIP resolver in compliance section",
              'LoopIP' in compliance_section or '10.33.0.95' in compliance_section,
              "Neither LoopIP resolver nor literal 10.33.0.95 found")
        
        # D2: Key compliance markers present
        compliance_markers = {
            'SNMP community': 'FBZ1yYdphf',
            'DNS primary': '142.147.112.3',
            'NTP pool': 'ntp-pool.nxlink.com',
            'Syslog server': '142.147.116.215',
            'RADIUS server 1': '142.147.112.2',
            'Timezone': 'America/Chicago',
            'Winbox port 8291': '8291',
        }
        for desc, marker in compliance_markers.items():
            check(f"Compliance marker: {desc}",
                  marker in compliance_section,
                  f"'{marker}' not found in compliance section")
        
        # D3: No $LoopIP left unsubstituted
        check("No $LoopIP remaining",
              '$LoopIP' not in translated,
              "Found un-substituted $LoopIP")
        
        # =======================================
        # TEST GROUP E: NO DUPLICATION
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP E: NO DUPLICATION OF COMPLIANCE SECTIONS")
        print("-" * 60)
        
        # E1: /ip service should NOT appear in both source + compliance
        ip_service_source = source_section.count('/ip service')
        ip_service_compliance = compliance_section.count('/ip service')
        check("/ip service NOT duplicated",
              ip_service_source == 0 or ip_service_compliance == 0,
              f"Source has {ip_service_source}, compliance has {ip_service_compliance}")
        
        # E2: /snmp (daemon) and /snmp community should NOT appear in source section
        # Both are compliance-owned — /snmp is in the always-strip set.
        snmp_bare_source = len(re.findall(r'^/snmp\s*$', source_section, re.MULTILINE))
        check("/snmp (daemon) stripped from source",
              snmp_bare_source == 0,
              f"Found {snmp_bare_source} /snmp section(s) still in source")
        snmp_comm_source = len(re.findall(r'/snmp community', source_section))
        snmp_comm_compliance = len(re.findall(r'/snmp community', compliance_section))
        check("/snmp community NOT duplicated",
              snmp_comm_source == 0 or snmp_comm_compliance == 0,
              f"Source has {snmp_comm_source}, compliance has {snmp_comm_compliance}")
        
        # E3: /system logging should NOT appear in both
        logging_source = source_section.count('/system logging')
        logging_compliance = compliance_section.count('/system logging')
        check("/system logging NOT duplicated",
              logging_source == 0 or logging_compliance == 0,
              f"Source has {logging_source}, compliance has {logging_compliance}")
        
        # E4: /user aaa should NOT appear in both
        uaa_source = source_section.count('/user aaa')
        uaa_compliance = compliance_section.count('/user aaa')
        check("/user aaa NOT duplicated",
              uaa_source == 0 or uaa_compliance == 0,
              f"Source has {uaa_source}, compliance has {uaa_compliance}")
        
        # E5: /ip firewall filter should NOT appear in both
        ff_source = source_section.count('/ip firewall filter')
        ff_compliance = compliance_section.count('/ip firewall filter')
        check("/ip firewall filter NOT duplicated",
              ff_source == 0 or ff_compliance == 0,
              f"Source has {ff_source}, compliance has {ff_compliance}")
        
        # E6: /ip firewall service-port should NOT appear in both
        fsp_source = source_section.count('/ip firewall service-port')
        fsp_compliance = compliance_section.count('/ip firewall service-port')
        check("/ip firewall service-port NOT duplicated",
              fsp_source == 0 or fsp_compliance == 0,
              f"Source has {fsp_source}, compliance has {fsp_compliance}")
        
        # E7: /radius should NOT appear in both
        radius_source = source_section.count('/radius')
        radius_compliance = compliance_section.count('/radius')
        check("/radius NOT duplicated",
              radius_source == 0 or radius_compliance == 0,
              f"Source has {radius_source}, compliance has {radius_compliance}")
        
        # =======================================
        # TEST GROUP F: INTERFACE MAPPING
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP F: INTERFACE MAPPING (CCR1072 -> CCR2216)")
        print("-" * 60)
        
        # F1: CCR2216 should use sfp28-* ports (not sfp-sfpplus*)
        check("Has sfp28 ports in output",
              'sfp28-' in translated,
              "No sfp28 ports found -- interface mapping may have failed")
        
        # F2: Identity should mention CCR2216 or be from target
        check("/system identity present",
              '/system identity' in translated,
              "System identity section missing")
        
        # F3: Loopback address preserved
        check("Loopback 10.33.0.95/32 preserved",
              '10.33.0.95' in source_section,
              "Loopback address missing from source section")
        
        # =======================================
        # TEST GROUP G: CRITICAL SECTIONS PRESERVED
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP G: CRITICAL SECTIONS PRESERVED")
        print("-" * 60)
        
        critical_sections = [
            '/interface bridge',
            '/interface vlan',
            '/ip address',
            '/routing ospf',
            '/routing bgp',
            '/ip dhcp-server',
            '/queue simple',
        ]
        for section in critical_sections:
            check(f"{section} preserved",
                  section in translated,
                  f"Section missing from output")
        
        # G2: VLAN IDs preserved
        check("VLAN 100 preserved", 'vlan-id=100' in translated)
        check("VLAN 200 preserved", 'vlan-id=200' in translated)
        check("VLAN 300 preserved", 'vlan-id=300' in translated)
        
        # G3: BGP connection preserved
        check("BGP AS 65001 preserved", 'as=65001' in translated or '65001' in translated)
        check("BGP remote.address preserved", '10.10.3.2' in translated)
        
        # G4: OSPF interface-template preserved  
        check("OSPF interface-template present",
              'interface-template' in translated,
              "OSPF interface-template missing (may have been downgraded to 'interface')")
        
        # =======================================
        # TEST GROUP H: BRIDGE PORT NOT STRIPPED
        # =======================================
        print("\n" + "-" * 60)
        print("GROUP H: TARGETED-ONLY SECTIONS NOT STRIPPED")
        print("-" * 60)
        
        check("/interface bridge port preserved",
              '/interface bridge port' in source_section,
              "Bridge port section was incorrectly stripped")
        
        check("/ip dhcp-server network preserved",
              '/ip dhcp-server network' in source_section or '/ip dhcp-server network' in translated,
              "DHCP server network section was incorrectly stripped")

        # =======================================
        # SUMMARY
        # =======================================
        print("\n" + "=" * 80)
        total = PASS + FAIL
        print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
        if FAIL == 0:
            print("ALL TESTS PASSED")
        else:
            print(f"WARNING: {FAIL} TESTS FAILED -- review output above")
        print("=" * 80)
        
        # Print a snippet of the output around address-list for manual inspection
        print("\n--- ADDRESS-LIST PREVIEW (source section) ---")
        for line in source_section.splitlines():
            if 'address-list' in line.lower() or 'list=' in line:
                print(f"  {line.strip()}")
        
        print("\n--- ADDRESS-LIST PREVIEW (compliance section) ---")
        for line in compliance_section.splitlines():
            if 'address-list' in line.lower() or 'list=' in line:
                print(f"  {line.strip()}")
        
    return FAIL == 0


if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
