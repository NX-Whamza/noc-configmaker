from pathlib import Path
import ipaddress
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
    return fallback


def _fmt_comment(value: str) -> str:
    if value is None:
        return ''
    val = str(value)
    if ' ' in val or '"' in val:
        val = val.replace('"', '')
        return f"\"{val}\""
    return val


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


def render_ftth_config(data: dict) -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"FTTH template missing: {TEMPLATE_PATH}")

    router_identity = data.get('router_identity', 'RTR-MTCCR2216.FTTH-BNG')
    location = (data.get('location', '') or '').strip()
    if location:
        location = location.replace(' ', '')
    else:
        location = '0,0'

    loopback_ip = data.get('loopback_ip', '')
    cpe_network = data.get('cpe_network', '')
    cgnat_private = data.get('cgnat_private', '')
    cgnat_public = data.get('cgnat_public', '')
    unauth_network = data.get('unauth_network', '')

    olt_network = data.get('olt_network', '') or data.get('olt_network_primary', '')
    olt_name = (data.get('olt_name', '') or '').strip() or (data.get('olt_name_primary', '') or '').strip() or 'OLT-MF2-1'

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

    cpe_pool_start, cpe_pool_end = _pool_range(cpe_net, 10)
    unauth_pool_start, unauth_pool_end = _pool_range(unauth_net, 10)
    cgnat_pool_start, cgnat_pool_end = _pool_range(cgnat_net, 3)

    group1_tag = _group_tag_from_name(olt_name, 'MF2-1')

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
            uplink_ip_lines.append(
                f"add address={uplink_ip} comment={_fmt_comment(uplink.get('comment', 'UPLINK'))} interface={port} network={uplink_iface.network.network_address}"
            )
            uplink_ospf_lines.append(
                f"add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM cost=10 disabled=no interfaces={port} networks={uplink_iface.network.network_address}/{uplink_iface.network.prefixlen} priority=1 type=ptp"
            )
        uplink_ldp_lines.append(f"add disabled=no interface={port}")

    primary_uplink = uplinks[0].get('port', 'sfp28-1') if uplinks else 'sfp28-1'
    primary_mtu = uplinks[0].get('mtu', '9000') if uplinks else '9000'

    olt_ports = data.get('olt_ports', [])
    olt_lines = []
    for port_cfg in olt_ports:
        port = port_cfg.get('port')
        if not port:
            continue
        comment = _fmt_comment(port_cfg.get('comment') or olt_name)
        speed = port_cfg.get('speed', 'auto')
        parts = [f"set [ find default-name={port} ]"]
        if comment:
            parts.append(f"comment={comment}")
        if speed and speed != 'auto':
            parts.append(f"speed={speed}")
        olt_lines.append(" ".join(parts))

    replacements = {
        "{{UPLINK_ETHERNET_LINES}}": "\n".join(uplink_lines),
        "{{OLT_ETHERNET_LINES}}": "\n".join(olt_lines),
        "{{UPLINK_PRIMARY_PORT}}": primary_uplink,
        "{{UPLINK_PRIMARY_MTU}}": str(primary_mtu),
        "{{OLT1_TAG}}": group1_tag,
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
        "{{GENERATED_AT}}": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    for key, value in replacements.items():
        template = template.replace(key, value)

    return template
