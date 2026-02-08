"""
NextLink Enterprise Configuration Reference
This file contains standard configurations that should be included in all Non-MPLS Enterprise configs.
The backend AI can reference this file to auto-fill standard sections without hardcoding.
"""

# Standard User Groups
STANDARD_USER_GROUPS = """
/user group
add name=ENG policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api
add name=NOC policy=local,telnet,ssh,ftp,reboot,read,write,test,winbox,password,sniff,sensitive,!policy,!web,!api,!romon,!rest-api
add name=LTE policy=local,telnet,ssh,reboot,read,write,test,winbox,password,sniff,sensitive,!ftp,!policy,!web,!api,!romon,!rest-api
add name=DEVOPS policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api
add name=VOIP policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=STS policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=TECHSUPPORT policy=local,telnet,read,test,winbox,sniff,!ssh,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=INFRA policy=local,telnet,reboot,read,write,test,winbox,!ssh,!ftp,!policy,!password,!web,!sniff,!sensitive,!api,!romon,!rest-api
add name=INSTALL policy=local,telnet,reboot,read,write,test,winbox,!ssh,!ftp,!policy,!password,!web,!sniff,!sensitive,!api,!romon,!rest-api
add name=COMENG policy=local,telnet,ssh,reboot,read,write,test,winbox,sniff,!ftp,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
add name=INTEGRATIONS policy=local,telnet,ssh,ftp,reboot,read,write,policy,test,winbox,password,web,sniff,sensitive,api,romon,rest-api
add name=IDO policy=local,telnet,ssh,reboot,read,write,test,winbox,password,sniff,sensitive,!ftp,!policy,!web,!api,!romon,!rest-api
add name=CALLCENTER-WRITE policy=local,telnet,ssh,read,write,test,winbox,sniff,!ftp,!reboot,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
"""

# Standard Firewall Address Lists
STANDARD_FIREWALL_ADDRESS_LISTS = {
    'ACS': [
        '67.219.119.0/24',
        '142.147.121.0/24'
    ],
    'EOIP-ALLOW': [
        '10.0.0.0/8'
    ],
    'managerIP': [
        '192.168.128.0/21',
        '107.178.5.97',
        '198.100.53.0/25',
        '143.55.62.143',
        '143.55.37.42',
        '143.55.37.43',
        '142.147.127.2',
        '132.147.147.67',
        '132.147.147.68',
        '132.147.132.6',
        '132.147.132.96',
        '132.147.132.97',
        '132.147.132.205',
        '67.219.122.201',
        '132.147.138.52',
        '132.147.138.53',
        '132.147.138.54'
    ],
    'BGP-ALLOW': [
        '10.0.0.0/8'
    ],
    'SNMP': [
        '143.55.35.47',
        '107.178.15.15',
        '107.178.15.162',
        '142.147.112.4',
        '142.147.124.26',
        '107.178.5.97',
        '67.219.126.240/28',
        '198.100.53.120',
        '143.55.62.143',
        '132.147.138.2',
        '132.147.138.0',
        '132.147.138.6',
        '132.147.138.23',
        '132.147.138.29',
        '132.147.138.30',
        '132.147.138.31',
        '132.147.132.40',
        '143.55.37.40',
        '143.55.37.41',
        '132.147.132.24',
        '198.100.49.99',
        '132.147.132.26',
        '204.11.183.126',
        '173.215.67.124',
        '132.147.138.3',
        '132.147.138.7',
        '132.147.138.21',
        '132.147.138.26',
        '107.178.15.21',
        '132.147.137.109',
        '216.169.149.171',
        '52.128.51.80',
        '52.128.51.70'
    ]
}

# Standard Firewall Filter Rules
STANDARD_FIREWALL_FILTER_RULES = """
/ip firewall filter
add action=accept chain=input comment="ALLOW EST REL" connection-state=established,related,untracked
add action=accept chain=input comment="ALLOW MT NEIGHBOR" dst-port=5678 protocol=udp
add action=accept chain=input comment="ALLOW MAC TELNET" dst-port=20561 protocol=udp
add action=accept chain=input comment="ALLOW IGMP" protocol=igmp
add action=accept chain=input comment="ALLOW ICMP" protocol=icmp
add action=accept chain=input comment="ALLOW DHCPv4" dst-port=67 protocol=udp
add action=accept chain=input comment="ALLOW DHCPv6" dst-port=547 protocol=udp
add action=accept chain=input comment="ALLOW OVPN" dst-port=1194 protocol=udp
add action=accept chain=input comment="ALLOW OVPN" dst-port=1194 protocol=tcp
add action=accept chain=input comment="ALLOW OSPF" protocol=ospf
add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=tcp
add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=udp
add action=accept chain=input comment="ALLOW MANAGER IP" src-address-list=managerIP
add action=accept chain=input comment="ALLOW BGP" dst-port=179 protocol=tcp src-address-list=BGP-ALLOW
add action=accept chain=input comment="ALLOW EOIP" protocol=gre src-address-list=EOIP-ALLOW
add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=udp src-address-list=SNMP
add action=drop chain=input comment="DROP INPUT"
"""

# Standard Firewall Raw Rules
STANDARD_FIREWALL_RAW_RULES = """
/ip firewall raw
add action=drop chain=prerouting comment="DROP BAD UDP" port=0 protocol=udp
"""

# Standard IP Service Settings
STANDARD_IP_SERVICES = """
/ip service
set www-ssl disabled=no
set www disabled=yes port=1234
set ftp disabled=yes port=5021
set ssh port=5022
set telnet disabled=yes port=5023
set api disabled=yes
set api-ssl disabled=yes
"""

# Standard System Settings
STANDARD_SYSTEM_SETTINGS = """
/system clock
set time-zone-name=America/Chicago

/system routerboard settings
set auto-upgrade=yes
"""

# Standard System Logging
STANDARD_SYSTEM_LOGGING = """
/system logging
add action=syslog topics=critical
add action=syslog topics=error
add action=syslog topics=info
add action=syslog topics=warning
add disabled=yes topics=debug
add action=disk topics=critical
add action=disk topics=error
add action=disk topics=info
add topics=warning
"""

# Standard NTP Client
STANDARD_NTP_CLIENT = """
/system ntp client
set enabled=yes

/system ntp client servers
add address=ntp-pool.nxlink.com
"""

# Standard IP Neighbor Discovery
STANDARD_IP_NEIGHBOR_DISCOVERY = """
/ip neighbor discovery-settings
set discover-interface-list=!dynamic
"""

# Standard User AAA (RADIUS)
STANDARD_USER_AAA = """
/user aaa
set use-radius=yes
"""

# MPLS Base Bridges (for MPLS Enterprise)
MPLS_BASE_BRIDGES = """
/interface bridge
add comment=DYNAMIC name=bridge1000 protocol-mode=none
add comment=STATIC name=bridge2000 protocol-mode=none
add comment=INFRA name=bridge3000 protocol-mode=none
add comment=CPE name=bridge4000 protocol-mode=none
add comment=LOOPBACK name=loop0
"""

# MPLS IP Services (for MPLS Enterprise)
MPLS_IP_SERVICES = """
/ip service
set telnet disabled=yes port=5023
set ftp disabled=yes port=5021
set www disabled=yes port=1234
set ssh port=5022 address=""
set api disabled=yes
set api-ssl disabled=yes
set www-ssl disabled=no port=443
set winbox address=""
"""


def get_firewall_address_lists_block():
    """Generate firewall address-list block from standard lists"""
    lines = ["/ip firewall address-list"]
    for list_name, addresses in STANDARD_FIREWALL_ADDRESS_LISTS.items():
        for address in addresses:
            lines.append(f"add address={address} list={list_name}")
    return "\n".join(lines)


def get_all_standard_blocks():
    """Get all standard configuration blocks"""
    return {
        'user_groups': STANDARD_USER_GROUPS.strip(),
        'firewall_address_lists': get_firewall_address_lists_block(),
        'firewall_filter': STANDARD_FIREWALL_FILTER_RULES.strip(),
        'firewall_raw': STANDARD_FIREWALL_RAW_RULES.strip(),
        'ip_services': STANDARD_IP_SERVICES.strip(),
        'system_settings': STANDARD_SYSTEM_SETTINGS.strip(),
        'system_logging': STANDARD_SYSTEM_LOGGING.strip(),
        'ntp_client': STANDARD_NTP_CLIENT.strip(),
        'ip_neighbor_discovery': STANDARD_IP_NEIGHBOR_DISCOVERY.strip(),
        'user_aaa': STANDARD_USER_AAA.strip(),
        # MPLS-specific blocks
        'mpls_bridges': MPLS_BASE_BRIDGES.strip(),
        'mpls_ip_services': MPLS_IP_SERVICES.strip()
    }

