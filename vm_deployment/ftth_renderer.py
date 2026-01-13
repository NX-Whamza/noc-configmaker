from pathlib import Path
import ipaddress
import os
import re
from datetime import datetime

TEMPLATE_PATH = Path(__file__).parent / "ftth_template.rsc"

MPLS_ACCEPT_FILTERS = [
    "add accept=no disabled=no prefix=10.2.0.14/32",
    "add accept=no disabled=no prefix=10.2.0.21/32",
    "add accept=no disabled=no prefix=10.2.0.107/32",
    "add accept=no disabled=no prefix=10.2.0.108/32",
    "add accept=no disabled=no prefix=10.17.0.10/32",
    "add accept=no disabled=no prefix=10.17.0.11/32",
    "add accept=no disabled=no prefix=10.30.0.9/32",
    "add accept=no disabled=no prefix=10.240.0.3/32",
    "add accept=no disabled=no prefix=10.243.0.9/32",
    "add accept=no disabled=no prefix=10.248.0.220/32",
    "add accept=no disabled=no prefix=10.249.0.220/32",
    "add accept=no disabled=no prefix=10.0.0.87/32",
    "add accept=no disabled=no prefix=10.9.0.88/32",
    "add accept=no disabled=no prefix=10.254.247.9/32",
    "add accept=yes disabled=no prefix=10.2.0.10/32",
    "add accept=yes disabled=no prefix=10.0.0.0/24",
    "add accept=yes disabled=no prefix=10.0.1.0/24",
    "add accept=yes disabled=no prefix=10.1.0.0/24",
    "add accept=yes disabled=no prefix=10.2.0.0/24",
    "add accept=yes disabled=no prefix=10.3.0.0/24",
    "add accept=yes disabled=no prefix=10.4.0.0/24",
    "add accept=yes disabled=no prefix=10.4.3.0/24",
    "add accept=yes disabled=no prefix=10.5.0.0/24",
    "add accept=yes disabled=no prefix=10.6.0.0/24",
    "add accept=yes disabled=no prefix=10.7.0.0/24",
    "add accept=yes disabled=no prefix=10.7.250.0/24",
    "add accept=yes disabled=no prefix=10.7.254.0/24",
    "add accept=yes disabled=no prefix=10.8.0.0/24",
    "add accept=yes disabled=no prefix=10.9.0.0/24",
    "add accept=yes disabled=no prefix=10.9.1.0/24",
    "add accept=yes disabled=no prefix=10.9.2.0/24",
    "add accept=yes disabled=no prefix=10.10.0.0/24",
    "add accept=yes disabled=no prefix=10.11.0.0/24",
    "add accept=yes disabled=no prefix=10.12.0.0/24",
    "add accept=yes disabled=no prefix=10.2.0.0/24",
    "add accept=yes disabled=no prefix=10.13.0.0/24",
    "add accept=yes disabled=no prefix=10.14.0.0/24",
    "add accept=yes disabled=no prefix=10.15.0.0/24",
    "add accept=yes disabled=no prefix=10.16.0.0/24",
    "add accept=yes disabled=no prefix=10.17.0.0/24",
    "add accept=yes disabled=no prefix=10.17.16.0/24",
    "add accept=yes disabled=no prefix=10.17.18.0/24",
    "add accept=yes disabled=no prefix=10.17.31.0/24",
    "add accept=yes disabled=no prefix=10.17.48.0/24",
    "add accept=yes disabled=no prefix=10.18.0.0/24",
    "add accept=yes disabled=no prefix=10.18.2.0/24",
    "add accept=yes disabled=no prefix=10.19.0.0/24",
    "add accept=yes disabled=no prefix=10.21.0.0/24",
    "add accept=yes disabled=no prefix=10.22.0.0/24",
    "add accept=yes disabled=no prefix=10.25.0.0/24",
    "add accept=yes disabled=no prefix=10.26.0.0/24",
    "add accept=yes disabled=no prefix=10.27.0.0/24",
    "add accept=yes disabled=no prefix=10.30.0.0/24",
    "add accept=yes disabled=no prefix=10.3.0.0/24",
    "add accept=yes disabled=no prefix=10.32.0.0/24",
    "add accept=yes disabled=no prefix=10.33.0.0/24",
    "add accept=yes disabled=no prefix=10.34.0.0/24",
    "add accept=yes disabled=no prefix=10.35.0.0/24",
    "add accept=yes disabled=no prefix=10.36.0.0/24",
    "add accept=yes disabled=no prefix=10.37.0.0/24",
    "add accept=yes disabled=no prefix=10.39.0.0/24",
    "add accept=yes disabled=no prefix=10.45.252.0/24",
    "add accept=yes disabled=no prefix=10.47.0.0/24",
    "add accept=yes disabled=no prefix=10.53.252.0/22",
    "add accept=yes disabled=no prefix=10.254.243.0/24",
    "add accept=yes disabled=no prefix=10.243.0.0/24",
    "add accept=yes disabled=no prefix=10.54.0.0/22",
    "add accept=yes disabled=no prefix=10.250.0.0/24",
    "add accept=yes disabled=no prefix=10.250.40.0/22",
    "add accept=yes disabled=no prefix=10.241.0.0/24",
    "add accept=yes disabled=no prefix=10.241.64.0/22",
    "add accept=yes disabled=no prefix=10.254.42.0/24",
    "add accept=yes disabled=no prefix=10.254.245.0/24",
    "add accept=yes disabled=no prefix=10.42.0.0/24",
    "add accept=yes disabled=no prefix=10.42.12.0/24",
    "add accept=yes disabled=no prefix=10.42.192.0/22",
    "add accept=yes disabled=no prefix=10.254.249.0/24",
    "add accept=yes disabled=no prefix=10.249.0.0/24",
    "add accept=yes disabled=no prefix=10.249.7.0/24",
    "add accept=yes disabled=no prefix=10.249.180.0/22",
    "add accept=yes disabled=no prefix=10.254.247.0/24",
    "add accept=yes disabled=no prefix=10.247.0.0/24",
    "add accept=yes disabled=no prefix=10.247.13.0/24",
    "add accept=yes disabled=no prefix=10.247.72.0/24",
    "add accept=yes disabled=no prefix=10.247.147.0/24",
    "add accept=yes disabled=no prefix=10.247.187.0/24",
    "add accept=yes disabled=no prefix=10.247.64.0/22",
    "add accept=yes disabled=no prefix=10.254.248.0/24",
    "add accept=yes disabled=no prefix=10.248.0.0/24",
    "add accept=yes disabled=no prefix=10.248.32.0/24",
    "add accept=yes disabled=no prefix=10.248.36.0/24",
    "add accept=yes disabled=no prefix=10.248.86.0/24",
    "add accept=yes disabled=no prefix=10.248.208.0/22",
    "add accept=no disabled=no prefix=0.0.0.0/0",
]


def _sanitize_tag(value: str, default: str) -> str:
    raw = (value or '').strip()
    if not raw:
        return default
    tag = re.sub(r'[^A-Za-z0-9]+', '-', raw).strip('-').upper()
    return tag or default


def _group_tag_from_name(name: str, fallback: str) -> str:
    upper = (name or '').upper()
    if 'MF2-1' in upper:
        return 'MF2-1'
    if 'MF2-2' in upper:
        return 'MF2-2'
    return fallback


def _fmt_comment(value: str) -> str:
    if value is None:
        return ''
    val = str(value)
    if ' ' in val or '"' in val:
        val = val.replace('"', '')
        return f"\"{val}\""
    return val


def _ftth_quote(value: str) -> str:
    if value is None:
        return "\"\""
    return "\"" + str(value).replace("\"", "") + "\""


def _ftth_user_passwords():
    return {
        'root': os.getenv('FTTH_USER_ROOT_PASSWORD', 'CHANGE_ME'),
        'deployment': os.getenv('FTTH_USER_DEPLOYMENT_PASSWORD', 'CHANGE_ME'),
        'infra': os.getenv('FTTH_USER_INFRA_PASSWORD', 'CHANGE_ME'),
        'ido': os.getenv('FTTH_USER_IDO_PASSWORD', 'CHANGE_ME'),
        'sts': os.getenv('FTTH_USER_STS_PASSWORD', 'CHANGE_ME'),
        'eng': os.getenv('FTTH_USER_ENG_PASSWORD', 'CHANGE_ME'),
        'noc': os.getenv('FTTH_USER_NOC_PASSWORD', 'CHANGE_ME'),
        'comeng': os.getenv('FTTH_USER_COMENG_PASSWORD', 'CHANGE_ME'),
        'devops': os.getenv('FTTH_USER_DEVOPS_PASSWORD', 'CHANGE_ME'),
        'acq': os.getenv('FTTH_USER_ACQ_PASSWORD', 'CHANGE_ME'),
        'admin': os.getenv('FTTH_ADMIN_PASSWORD', 'CHANGE_ME'),
    }


def _net_details(cidr: str):
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = list(net.hosts())
    if not hosts:
        raise ValueError(f'No usable hosts in {cidr}')
    return net, hosts[0], hosts[-1]


def _pool_range(net: ipaddress.IPv4Network, start_offset: int):
    start_ip = ipaddress.ip_address(int(net.network_address) + start_offset)
    end_ip = list(net.hosts())[-1]
    return str(start_ip), str(end_ip)


def _strip_ftth_headers(config: str) -> str:
    """Remove human-readable headers/metadata from generated FTTH output."""
    drop_prefixes = (
        "FTTH BNG Configuration - ",
        "Generated:",
        "Deployment Type:",
        "Device:",
        "Location:",
        "Total configuration lines:",
        "Deployment:",
        "Please review",
        "CONFIGURATION COMPLETE",
        "==========",
        "#==========",
        "# FTTH BNG Configuration",
    )
    cleaned = []
    for line in config.splitlines():
        stripped = line.strip()
        if stripped.startswith(drop_prefixes):
            continue
        # Drop banner lines like "======" or "#==========SECTION=========="
        if re.match(r"^#?=+.*=+$", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def _normalize_ftth_output(config: str) -> str:
    """Normalize FTTH output to legacy RouterOS CLI section syntax."""
    # Normalize line endings first to make replacements reliable.
    normalized = config.replace("\r\n", "\n").replace("\r", "\n")
    replacements = [
        ("/interface/bridge/port", "/interface bridge port"),
        ("/interface/bridge", "/interface bridge"),
        ("/interface/ethernet", "/interface ethernet"),
        ("/interface/bonding", "/interface bonding"),
        ("/interface/vlan", "/interface vlan"),
        ("/ip/dhcp-server/network", "/ip dhcp-server network"),
        ("/ip/dhcp-server", "/ip dhcp-server"),
        ("/ip/firewall/address-list", "/ip firewall address-list"),
        ("/ip/firewall/nat", "/ip firewall nat"),
        ("/ip/firewall/filter", "/ip firewall filter"),
        ("/ip/firewall/mangle", "/ip firewall mangle"),
        ("/ip/firewall/raw", "/ip firewall raw"),
        ("/ip/firewall/service-port", "/ip firewall service-port"),
        ("/ip/address", "/ip address"),
        ("/ip/dns", "/ip dns"),
        ("/routing/ospf/interface-template", "/routing ospf interface-template"),
        ("/routing/ospf/area", "/routing ospf area"),
        ("/routing/ospf/instance", "/routing ospf instance"),
        ("/routing/bgp/connection", "/routing bgp connection"),
        ("/routing/bgp/template", "/routing bgp template"),
        ("/routing/bgp/instance", "/routing bgp instance"),
        ("/snmp/community", "/snmp community"),
        ("/system/ntp/client/servers", "/system ntp client servers"),
        ("/system/ntp/client", "/system ntp client"),
        ("/system/logging", "/system logging"),
        ("/system/identity", "/system identity"),
        ("/system/clock", "/system clock"),
        ("/system/note", "/system note"),
        ("/system/routerboard/settings", "/system routerboard settings"),
    ]

    for old, new in replacements:
        normalized = normalized.replace(old, new)
    return normalized


def render_ftth_config(data: dict) -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"FTTH template missing: {TEMPLATE_PATH}")

    router_identity = data.get('router_identity', 'RTR-MTCCR2216.FTTH-BNG')
    location = (data.get('location', '') or '').strip()
    if location:
        location = location.replace('"', '')
    else:
        location = '0,0'

    loopback_ip = data.get('loopback_ip', '')
    cpe_network = data.get('cpe_network', '')
    cgnat_private = data.get('cgnat_private', '')
    cgnat_public = data.get('cgnat_public', '')
    unauth_network = data.get('unauth_network', '')

    olt_network = data.get('olt_network', '') or data.get('olt_network_primary', '')
    olt_network_secondary = (
        data.get('olt_network_secondary')
        or data.get('olt_network2')
        or ''
    ).strip()
    olt_name = (data.get('olt_name', '') or '').strip() or (data.get('olt_name_primary', '') or '').strip() or 'OLT-MF2-1'
    olt_name_secondary = (data.get('olt_name_secondary', '') or '').strip()
    if olt_network_secondary and not olt_name_secondary:
        olt_name_secondary = 'OLT-MF2-2'

    routeros_version = (data.get('routeros_version', '') or '').strip()
    uplinks = data.get('uplinks', [])
    if not uplinks:
        uplinks = [{
            'port': data.get('uplink_port', 'sfp28-1'),
            'type': data.get('uplink_type', 'routed'),
            'ip': data.get('uplink_ip', ''),
            'speed': data.get('uplink_speed', 'auto'),
            'comment': data.get('uplink_comment', 'to-CORE'),
            'cost': data.get('uplink_cost', '10'),
            'mtu': data.get('uplink_mtu', '9000'),
            'l2mtu': data.get('uplink_l2mtu', '9212'),
            'auto_negotiation': data.get('uplink_auto_negotiation', False),
        }]

    if not all([loopback_ip, cpe_network, cgnat_private, cgnat_public, unauth_network, olt_network]):
        raise ValueError('Missing required IP allocation fields.')

    loopback = ipaddress.ip_interface(loopback_ip)
    cpe_net, cpe_first, _cpe_last = _net_details(cpe_network)
    cgnat_net, cgnat_first, _cgnat_last = _net_details(cgnat_private)
    unauth_net, unauth_first, _unauth_last = _net_details(unauth_network)
    cgnat_pub = ipaddress.ip_interface(cgnat_public)
    olt1_net, olt1_first, _olt1_last = _net_details(olt_network)
    olt2_net = olt2_first = None
    if olt_network_secondary:
        olt2_net, olt2_first, _olt2_last = _net_details(olt_network_secondary)

    cpe_pool_start, cpe_pool_end = _pool_range(cpe_net, 10)
    unauth_pool_start, unauth_pool_end = _pool_range(unauth_net, 10)
    cgnat_pool_start, cgnat_pool_end = _pool_range(cgnat_net, 3)

    group1_tag = _group_tag_from_name(olt_name, 'MF2-1')
    group2_tag = _group_tag_from_name(olt_name_secondary, 'MF2-2')

    uplink_lines = []
    uplink_ip_lines = []
    uplink_ospf_lines = []
    uplink_ldp_lines = []

    for uplink in uplinks:
        port = uplink.get('port', 'sfp28-1')
        comment = _fmt_comment(uplink.get('comment', 'UPLINK'))
        speed = uplink.get('speed', 'auto')
        mtu = uplink.get('mtu', '9000')
        l2mtu = uplink.get('l2mtu', '9212')
        auto_neg = uplink.get('auto_negotiation', False)
        parts = [f"set [ find default-name={port} ]"]
        if auto_neg is False:
            parts.append("auto-negotiation=no")
        if comment:
            parts.append(f"comment={comment}")
        if l2mtu:
            parts.append(f"l2mtu={l2mtu}")
        if mtu:
            parts.append(f"mtu={mtu}")
        if speed and speed != 'auto':
            parts.append(f"speed={speed}")
        uplink_lines.append(" ".join(parts))

        uplink_ip = uplink.get('ip', '')
        if uplink.get('type', 'routed') == 'routed' and uplink_ip:
            uplink_iface = ipaddress.ip_interface(uplink_ip)
            ospf_comment = _fmt_comment(uplink.get('comment', 'UPLINK'))
            ospf_comment_part = f" comment={ospf_comment}" if ospf_comment else ""
            uplink_ip_lines.append(
                f"add address={uplink_ip} comment={_fmt_comment(uplink.get('comment', 'UPLINK'))} interface={port} network={uplink_iface.network.network_address}"
            )
            uplink_ospf_lines.append(
                f"add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM{ospf_comment_part} cost=10 disabled=no interfaces={port} networks={uplink_iface.network.network_address}/{uplink_iface.network.prefixlen} priority=1 type=ptp"
            )
        uplink_ldp_lines.append(f"add disabled=no interface={port}")

    primary_uplink = uplinks[0].get('port', 'sfp28-1') if uplinks else 'sfp28-1'
    primary_mtu = uplinks[0].get('mtu', '9000') if uplinks else '9000'

    olt_ports = data.get('olt_ports', [])
    has_olt2_ports = any(str(p.get('group') or '1') == '2' for p in olt_ports)
    if has_olt2_ports and not olt_network_secondary:
        raise ValueError('OLT Network 2 is required when OLT LAG 2 ports are configured.')
    if has_olt2_ports and not olt_name_secondary:
        olt_name_secondary = 'OLT-MF2-2'
    olt_lines = []
    for port_cfg in olt_ports:
        port = port_cfg.get('port')
        if not port:
            continue
        group = str(port_cfg.get('group') or '1')
        base_name = olt_name_secondary if group == '2' and olt_name_secondary else olt_name
        comment = _fmt_comment(port_cfg.get('comment') or base_name)
        speed = port_cfg.get('speed', 'auto')
        parts = [f"set [ find default-name={port} ]"]
        if comment:
            parts.append(f"comment={comment}")
        if speed and speed != 'auto':
            parts.append(f"speed={speed}")
        olt_lines.append(" ".join(parts))

    if not olt_lines:
        olt1_comment = _fmt_comment(olt_name)
        olt_lines = [
            f"set [ find default-name=sfp28-3 ] comment={olt1_comment}",
            f"set [ find default-name=sfp28-4 ] comment={olt1_comment}",
            f"set [ find default-name=sfp28-5 ] comment={olt1_comment}",
            f"set [ find default-name=sfp28-6 ] comment={olt1_comment}",
        ]
        if olt_network_secondary or olt_name_secondary or has_olt2_ports:
            olt2_comment = _fmt_comment(olt_name_secondary or 'OLT-MF2-2')
            olt_lines.extend([
                f"set [ find default-name=sfp28-7 ] comment={olt2_comment}",
                f"set [ find default-name=sfp28-8 ] comment={olt2_comment}",
                f"set [ find default-name=sfp28-9 ] comment={olt2_comment}",
                f"set [ find default-name=sfp28-10 ] comment={olt2_comment}",
            ])

    olt2_bonding_line = ''
    olt2_vlan_lines = ''
    olt2_bridge_ports = ''
    olt2_ip_line = ''
    olt2_ospf_line = ''
    if (olt2_net and olt2_first) or has_olt2_ports:
        olt2_bonding_line = (
            f"add mode=802.3ad name=bonding3000-{group2_tag} "
            "slaves=sfp28-7,sfp28-8,sfp28-9,sfp28-10 transmit-hash-policy=layer-2-and-3"
        )
        olt2_vlan_lines = "\n".join([
            f"add interface=bonding3000-{group2_tag} name=vlan1000-{group2_tag} vlan-id=1000",
            f"add interface=bonding3000-{group2_tag} name=vlan2000-{group2_tag} vlan-id=2000",
            f"add interface=bonding3000-{group2_tag} name=vlan3000-{group2_tag} vlan-id=3000",
            f"add interface=bonding3000-{group2_tag} name=vlan4000-{group2_tag} vlan-id=4000",
        ])
        olt2_bridge_ports = "\n".join([
            f"add bridge=bridge1000 ingress-filtering=no interface=vlan1000-{group2_tag} internal-path-cost=10 path-cost=10",
            f"add bridge=bridge2000 interface=vlan2000-{group2_tag}",
            f"add bridge=bridge3000 interface=vlan3000-{group2_tag}",
            f"add bridge=bridge4000 ingress-filtering=no interface=vlan4000-{group2_tag} internal-path-cost=10 path-cost=10",
        ])
        if olt2_net and olt2_first:
            olt2_ip_line = (
                f"add address={olt2_first}/{olt2_net.prefixlen} comment={_fmt_comment(olt_name_secondary)} "
                f"interface=bridge3000 network={olt2_net.network_address}"
            )
            olt2_ospf_line = (
                f"add area=backbone-v2 comment={_fmt_comment(olt_name_secondary)} cost=10 disabled=no "
                f"interfaces=bridge3000 networks={olt2_net.network_address}/{olt2_net.prefixlen} priority=1"
            )

    if routeros_version == '7.20.2':
        bgp_instance_block = "\n".join([
            "/routing bgp instance",
            f"add as=26077 disabled=no name=bgp-instance-1 router-id={loopback.ip}",
        ])
        bgp_template_line = "set default as=26077 disabled=no output.network=bgp-networks"
        bgp_connection_lines = "\n".join([
            f"add cisco-vpls-nlri-len-fmt=auto-bits connect=yes disabled=no instance=bgp-instance-1 listen=yes "
            f"local.address={loopback.ip} .role=ibgp multihop=yes name=CR7 output.network=bgp-networks "
            f"remote.address=10.2.0.107/32 .as=26077 .port=179 routing-table=main templates=default",
            f"add cisco-vpls-nlri-len-fmt=auto-bits connect=yes disabled=no instance=bgp-instance-1 listen=yes "
            f"local.address={loopback.ip} .role=ibgp multihop=yes name=CR8 output.network=bgp-networks "
            f"remote.address=10.2.0.108/32 .as=26077 .port=179 routing-table=main templates=default",
        ])
    else:
        bgp_instance_block = ''
        bgp_template_line = f"set default as=26077 disabled=no output.network=bgp-networks router-id={loopback.ip}"
        bgp_connection_lines = "\n".join([
            f"add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address={loopback.ip} "
            f".role=ibgp multihop=yes name=CR7 remote.address=10.2.0.107 .as=26077 .port=179 templates=default",
            f"add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address={loopback.ip} "
            f".role=ibgp multihop=yes name=CR8 remote.address=10.2.0.108 .as=26077 .port=179 templates=default",
        ])

    user_passwords = _ftth_user_passwords()
    replacements = {
        "{{UPLINK_ETHERNET_LINES}}": "\n".join(uplink_lines),
        "{{OLT_ETHERNET_LINES}}": "\n".join(olt_lines),
        "{{UPLINK_PRIMARY_PORT}}": primary_uplink,
        "{{UPLINK_PRIMARY_MTU}}": str(primary_mtu),
        "{{OLT1_TAG}}": group1_tag,
        "{{OLT2_BONDING_LINE}}": olt2_bonding_line,
        "{{OLT2_VLAN_LINES}}": olt2_vlan_lines,
        "{{OLT2_BRIDGE_PORTS}}": olt2_bridge_ports,
        "{{OLT2_IP_LINE}}": olt2_ip_line,
        "{{OLT2_OSPF_LINE}}": olt2_ospf_line,
        "{{CGNAT_POOL_START}}": cgnat_pool_start,
        "{{CGNAT_POOL_END}}": cgnat_pool_end,
        "{{CPE_POOL_START}}": cpe_pool_start,
        "{{CPE_POOL_END}}": cpe_pool_end,
        "{{UNAUTH_POOL_START}}": unauth_pool_start,
        "{{UNAUTH_POOL_END}}": unauth_pool_end,
        "{{ROUTER_ID}}": str(loopback.ip),
        "{{CPE_GATEWAY}}": str(cpe_first),
        "{{CPE_PREFIX}}": str(cpe_net.prefixlen),
        "{{CPE_NETWORK_BASE}}": str(cpe_net.network_address),
        "{{LOOPBACK_IP}}": str(loopback.ip),
        "{{UNAUTH_GATEWAY}}": str(unauth_first),
        "{{UNAUTH_PREFIX}}": str(unauth_net.prefixlen),
        "{{UNAUTH_NETWORK_BASE}}": str(unauth_net.network_address),
        "{{CGNAT_GATEWAY}}": str(cgnat_first),
        "{{CGNAT_PREFIX}}": str(cgnat_net.prefixlen),
        "{{CGNAT_NETWORK_BASE}}": str(cgnat_net.network_address),
        "{{OLT1_IP}}": str(olt1_first),
        "{{OLT1_PREFIX}}": str(olt1_net.prefixlen),
        "{{OLT1_NETWORK_BASE}}": str(olt1_net.network_address),
        "{{CGNAT_PUBLIC}}": str(cgnat_pub.ip),
        "{{UPLINK_IP_LINES}}": "\n".join(uplink_ip_lines),
        "{{UPLINK_OSPF_LINES}}": "\n".join(uplink_ospf_lines),
        "{{UPLINK_LDP_LINES}}": "\n".join(uplink_ldp_lines),
        "{{MPLS_ACCEPT_FILTERS}}": "\n".join(MPLS_ACCEPT_FILTERS),
        "{{MPLS_ADVERTISE_FILTERS}}": "\n".join([line.replace('accept', 'advertise') for line in MPLS_ACCEPT_FILTERS]),
        "{{OLT1_NAME}}": _fmt_comment(olt_name),
        "{{ROUTER_IDENTITY}}": router_identity,
        "{{LOCATION}}": location,
        "{{SNMP_CONTACT}}": os.getenv('NEXTLINK_SNMP_CONTACT', 'noc@team.nxlink.com'),
        "{{GENERATED_AT}}": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "{{BGP_INSTANCE_BLOCK}}": bgp_instance_block,
        "{{BGP_TEMPLATE_LINE}}": bgp_template_line,
        "{{BGP_CONNECTION_LINES}}": bgp_connection_lines,
        "{{USER_ROOT_PASSWORD}}": _ftth_quote(user_passwords['root']),
        "{{USER_DEPLOYMENT_PASSWORD}}": _ftth_quote(user_passwords['deployment']),
        "{{USER_INFRA_PASSWORD}}": _ftth_quote(user_passwords['infra']),
        "{{USER_IDO_PASSWORD}}": _ftth_quote(user_passwords['ido']),
        "{{USER_STS_PASSWORD}}": _ftth_quote(user_passwords['sts']),
        "{{USER_ENG_PASSWORD}}": _ftth_quote(user_passwords['eng']),
        "{{USER_NOC_PASSWORD}}": _ftth_quote(user_passwords['noc']),
        "{{USER_COMENG_PASSWORD}}": _ftth_quote(user_passwords['comeng']),
        "{{USER_DEVOPS_PASSWORD}}": _ftth_quote(user_passwords['devops']),
        "{{USER_ACQ_PASSWORD}}": _ftth_quote(user_passwords['acq']),
        "{{USER_ADMIN_PASSWORD}}": _ftth_quote(user_passwords['admin']),
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    for key, value in replacements.items():
        template = template.replace(key, value)

    template = _strip_ftth_headers(template)
    return _normalize_ftth_output(template)
