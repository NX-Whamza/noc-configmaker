/interface bridge
add name=bridge1000
add name=bridge2000
add name=bridge3000
add name=bridge4000
add name=lan-bridge
add name=loop0
add name=nat-public-bridge
/interface ethernet
set [ find default-name=ether1 ] comment=ICT
set [ find default-name=qsfp28-1-1 ] disabled=yes
set [ find default-name=qsfp28-1-2 ] disabled=yes
set [ find default-name=qsfp28-1-3 ] disabled=yes
set [ find default-name=qsfp28-1-4 ] disabled=yes
set [ find default-name=qsfp28-2-1 ] disabled=yes
set [ find default-name=qsfp28-2-2 ] disabled=yes
set [ find default-name=qsfp28-2-3 ] disabled=yes
set [ find default-name=qsfp28-2-4 ] disabled=yes
{{UPLINK_ETHERNET_LINES}}
{{OLT_ETHERNET_LINES}}
set [ find default-name=sfp28-12 ] auto-negotiation=no comment=exfo speed=10G-baseSR-LR
/interface vlan
add disabled=yes interface={{UPLINK_PRIMARY_PORT}} mtu={{UPLINK_PRIMARY_MTU}} name=vlan1017 vlan-id=1017
/interface bonding
add mode=802.3ad name=bonding3000-{{OLT1_TAG}} slaves=sfp28-3,sfp28-4,sfp28-5,sfp28-6 transmit-hash-policy=layer-2-and-3
/interface vlan
add interface=bonding3000-{{OLT1_TAG}} name=vlan1000-{{OLT1_TAG}} vlan-id=1000
add interface=bonding3000-{{OLT1_TAG}} name=vlan2000-{{OLT1_TAG}} vlan-id=2000
add interface=bonding3000-{{OLT1_TAG}} name=vlan3000-{{OLT1_TAG}} vlan-id=3000
add interface=bonding3000-{{OLT1_TAG}} name=vlan4000-{{OLT1_TAG}} vlan-id=4000
/ip dhcp-server option
add code=43 name=opt43 value=0x011768747470733a2f2f7573732e6e786c696e6b2e636f6d2f
/ip dhcp-server option sets
add name=optset options=opt43
/ip pool
add name=cust ranges={{CGNAT_POOL_START}}-{{CGNAT_POOL_END}}
add name=cpe ranges={{CPE_POOL_START}}-{{CPE_POOL_END}}
add name=unauth ranges={{UNAUTH_POOL_START}}-{{UNAUTH_POOL_END}}
/port
set 0 name=serial0
/routing bgp template
set default as=26077 disabled=no output.network=bgp-networks router-id={{ROUTER_ID}}
/routing ospf instance
add disabled=no name=default-v2 router-id={{ROUTER_ID}}
/routing ospf area
add disabled=no instance=default-v2 name=backbone-v2
/snmp community
set [ find default=yes ] read-access=no
add addresses=::/0 name=FBZ1yYdphf
/system logging action
set 1 disk-file-count=3 disk-lines-per-file=10000
add name=syslog remote=142.147.116.215 src-address={{ROUTER_ID}} target=remote
/user group
set read policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
/interface bridge port
add bridge=bridge1000 ingress-filtering=no interface=vlan1000-{{OLT1_TAG}} internal-path-cost=10 path-cost=10
add bridge=bridge2000 interface=vlan2000-{{OLT1_TAG}}
add bridge=bridge3000 interface=vlan3000-{{OLT1_TAG}}
add bridge=bridge4000 ingress-filtering=no interface=vlan4000-{{OLT1_TAG}} internal-path-cost=10 path-cost=10
add bridge=lan-bridge interface=ether1
/ip neighbor discovery-settings
set discover-interface-list=!dynamic
/ip address
add address={{CPE_GATEWAY}}/{{CPE_PREFIX}} comment="CPE/Tower Gear" interface=lan-bridge network={{CPE_NETWORK_BASE}}
add address={{LOOPBACK_IP}} comment=loop0 interface=loop0 network={{LOOPBACK_IP}}
add address={{UNAUTH_GATEWAY}}/{{UNAUTH_PREFIX}} comment=UNAUTH interface=lan-bridge network={{UNAUTH_NETWORK_BASE}}
add address={{CGNAT_GATEWAY}}/{{CGNAT_PREFIX}} comment="CGNAT Private" interface=bridge1000 network={{CGNAT_NETWORK_BASE}}
add address={{OLT1_IP}}/{{OLT1_PREFIX}} comment={{OLT1_NAME}} interface=bridge3000 network={{OLT1_NETWORK_BASE}}
add address={{CGNAT_PUBLIC}} comment="CGNAT Public" interface=nat-public-bridge network={{CGNAT_PUBLIC}}
{{UPLINK_IP_LINES}}
/ip dhcp-server
add address-pool=cust dhcp-option-set=optset interface=bridge1000 lease-time=10m name=server1 use-radius=yes
/ip dhcp-server network
add address={{CPE_NETWORK_BASE}}/{{CPE_PREFIX}} dns-server=142.147.112.3,142.147.112.19 gateway={{CPE_GATEWAY}} netmask={{CPE_PREFIX}}
add address={{UNAUTH_NETWORK_BASE}}/{{UNAUTH_PREFIX}} dns-server=142.147.112.3,142.147.112.19 gateway={{UNAUTH_GATEWAY}} netmask={{UNAUTH_PREFIX}}
add address={{CGNAT_NETWORK_BASE}}/{{CGNAT_PREFIX}} dns-server=142.147.112.3,142.147.112.19 gateway={{CGNAT_GATEWAY}} netmask={{CGNAT_PREFIX}}
/ip dns
set servers=142.147.112.3,142.147.112.19
/ip firewall address-list
add address=142.147.112.3 list=NAT-EXEMPT-DST
add address=142.147.112.19 list=NAT-EXEMPT-DST
add address=107.178.15.0/27 list=NAT-EXEMPT-DST
add address=107.178.5.97 list=NAT-EXEMPT-DST
add address=69.53.224.0/19 list=NETFLIX
add address=108.175.32.0/20 list=NETFLIX
add address=192.173.64.0/18 list=NETFLIX
add address=198.38.96.0/19 list=NETFLIX
add address=198.45.48.0/20 list=NETFLIX
add address=208.75.76.0/22 list=NETFLIX
add address=24.220.183.0/24 list=NETFLIX
add address=216.168.119.0/24 list=NETFLIX
add address=23.246.0.0/20 list=NETFLIX
add address=173.246.157.0/24 list=NETFLIX
add address=37.77.184.0/23 list=NETFLIX
add address=64.140.112.0/24 list=NETFLIX
add address=66.97.254.0/24 list=NETFLIX
add address=185.2.223.0/24 list=NETFLIX
add address=107.178.15.4 list=Voip-Servers
add address={{UNAUTH_NETWORK_BASE}}/{{UNAUTH_PREFIX}} comment=UNAUTH list=bgp-networks
add address={{CGNAT_NETWORK_BASE}}/{{CGNAT_PREFIX}} comment=CGNAT_PRIVATE list=bgp-networks
add address={{CGNAT_PUBLIC}} comment=CGNAT_PUBLIC list=bgp-networks
add address=10.0.0.0/8 list=EOIP-ALLOW
add address=192.168.128.0/21 list=managerIP
add address=107.178.5.97 list=managerIP
add address=198.100.53.0/25 list=managerIP
add address=143.55.62.143 list=managerIP
add address=142.147.127.2 list=managerIP
add address=132.147.132.6 list=managerIP
add address=67.219.122.201 list=managerIP
add address=10.249.1.26 list=managerIP
add address=10.0.0.0/8 list=managerIP
add address=10.0.0.0/8 list=BGP-ALLOW
add address=143.55.35.47 list=SNMP
add address=107.178.15.15 list=SNMP
add address=107.178.15.162 list=SNMP
add address=142.147.112.4 list=SNMP
add address=142.147.124.26 list=SNMP
add address=107.178.5.97 list=SNMP
add address=52.128.51.70 list=SNMP
add address=52.128.51.80 list=SNMP
add address=67.219.126.240/28 list=SNMP
add address=198.100.53.120 list=SNMP
add address=143.55.62.143 list=SNMP
add address=132.147.138.2 list=SNMP
add address=132.147.138.0 list=SNMP
add address=132.147.138.6 list=SNMP
add address=132.147.138.23 list=SNMP
add address=132.147.138.29 list=SNMP
add address=132.147.138.30 list=SNMP
add address=132.147.138.31 list=SNMP
add address=143.55.37.40 list=SNMP
add address=143.55.37.41 list=SNMP
add address=132.147.132.24 list=SNMP
add address=198.100.49.99 list=SNMP
add address=132.147.132.26 list=SNMP
add address=132.147.132.40 list=SNMP
add address=204.11.183.126 list=SNMP
add address=173.215.67.124 list=SNMP
add address=132.147.138.3 list=SNMP
add address=132.147.138.7 list=SNMP
add address=132.147.138.21 list=SNMP
add address=132.147.138.26 list=SNMP
add address=142.147.112.3 list=WALLED-GARDEN
add address=142.147.112.19 list=WALLED-GARDEN
add address=107.178.15.27 list=WALLED-GARDEN
add address=142.147.112.12 list=WALLED-GARDEN
add address=132.147.147.56 list=WALLED-GARDEN
add address=35.227.221.107 list=WALLED-GARDEN
add address=172.66.155.116 list=WALLED-GARDEN
add address=104.20.19.83 list=WALLED-GARDEN
add address=132.147.175.10 list=managerIP
add address=132.147.175.14 list=managerIP
/ip firewall filter
add action=accept chain=input comment="ALLOW EST REL" connection-state=established,related,untracked
add action=accept chain=input comment="ALLOW MT NEIGHBOR" dst-port=5678 protocol=udp
add action=accept chain=input comment="ALLOW MAC TELNET" dst-port=20561 protocol=udp
add action=accept chain=input comment="ALLOW IGMP" protocol=igmp
add action=accept chain=input comment="ALLOW ICMP" protocol=icmp
add action=accept chain=input comment="ALLOW DHCPv4" dst-port=67 protocol=udp
add action=accept chain=input comment="ALLOW DHCPv6" dst-port=547 protocol=udp
add action=accept chain=input comment="ALLOW OSPF" protocol=ospf
add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=tcp
add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=udp
add action=accept chain=input comment="ALLOW MANAGER IP" src-address-list=managerIP
add action=accept chain=input comment="ALLOW BGP" dst-port=179 protocol=tcp src-address-list=BGP-ALLOW
add action=accept chain=input comment="ALLOW EOIP" protocol=gre src-address-list=EOIP-ALLOW
add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=tcp src-address-list=SNMP
add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=udp src-address-list=SNMP
add action=drop chain=input comment="DROP INPUT"
add action=accept chain=forward comment="NTP Allow" dst-address-list=NTP dst-port=123 in-interface=lan-bridge protocol=udp
add action=accept chain=forward comment="NTP Allow" dst-address=10.0.0.1 dst-port=123 in-interface=lan-bridge protocol=udp
add action=drop chain=forward comment="Traceroute Drop" out-interface=lan-bridge protocol=icmp src-address=10.0.0.0/8
add action=drop chain=forward comment="Private Space Protect" dst-address=10.0.0.0/8 in-interface=lan-bridge
add action=accept chain=forward comment="BGP Accept" dst-address=10.0.0.0/8 dst-port=179 protocol=tcp src-address=10.0.0.0/8
add action=accept chain=forward comment="GRE Accept " dst-address=10.0.0.0/8 protocol=gre src-address=10.0.0.0/8
add action=drop chain=forward comment="unauth drop rule" dst-address-list=!WALLED-GARDEN src-address-list=unauth
add action=fasttrack-connection chain=forward connection-state=established,related,untracked hw-offload=yes
add action=accept chain=forward connection-state=established,related,untracked
/ip firewall nat
add action=redirect chain=dstnat dst-address-type=local dst-port=5022 protocol=tcp to-ports=22
add action=dst-nat chain=dstnat comment="unauth proxy rule" dst-address-list=!WALLED-GARDEN dst-port=80 protocol=tcp src-address-list=unauth to-addresses=107.178.15.27 to-ports=3128
/ip firewall raw
add action=drop chain=prerouting comment="DROP BAD UDP" port=0 protocol=udp
/ip firewall service-port
set ftp disabled=yes
set tftp disabled=yes
set sip disabled=yes
/ip service
set www disabled=yes port=1234
set ftp disabled=yes port=5021
set telnet disabled=yes port=5023
set api disabled=yes
set api-ssl disabled=yes
/mpls interface
add disabled=no interface=all mpls-mtu=8900
/mpls ldp
add disabled=no lsr-id={{ROUTER_ID}} transport-addresses={{ROUTER_ID}}
/mpls ldp accept-filter
{{MPLS_ACCEPT_FILTERS}}
/mpls ldp advertise-filter
{{MPLS_ADVERTISE_FILTERS}}
/mpls ldp interface
{{UPLINK_LDP_LINES}}
/radius
add address=142.147.112.2 secret=Nl22021234 service=dhcp src-address={{ROUTER_ID}} timeout=5s
add address=142.147.112.18 secret=Nl22021234 service=dhcp src-address={{ROUTER_ID}} timeout=5s
/routing bgp connection
add as=26077 cisco-vpls-nlri-len-fmt=auto-bits connect=yes disabled=no listen=yes local.address={{ROUTER_ID}} local.role=ibgp multihop=yes name=CR7 output.network=bgp-networks remote.address=10.2.0.107/32 remote.as=26077 remote.port=179 router-id={{ROUTER_ID}} routing-table=main tcp-md5-key=m8M5JwvdYM templates=default
add as=26077 cisco-vpls-nlri-len-fmt=auto-bits connect=yes disabled=no listen=yes local.address={{ROUTER_ID}} local.role=ibgp multihop=yes name=CR8 output.network=bgp-networks remote.address=10.2.0.108/32 remote.as=26077 remote.port=179 router-id={{ROUTER_ID}} routing-table=main tcp-md5-key=m8M5JwvdYM templates=default
/routing ospf interface-template
add area=backbone-v2 comment=loop0 cost=10 disabled=no interfaces=loop0 networks={{LOOPBACK_IP}}/32 passive priority=1
add area=backbone-v2 comment="CPE/Tower Gear" cost=10 disabled=no interfaces=lan-bridge networks={{CPE_NETWORK_BASE}}/{{CPE_PREFIX}} priority=1
add area=backbone-v2 comment={{OLT1_NAME}} cost=10 disabled=no interfaces=bridge3000 networks={{OLT1_NETWORK_BASE}}/{{OLT1_PREFIX}} priority=1
{{UPLINK_OSPF_LINES}}
/snmp
set contact=noc@team.nxlink.com enabled=yes location={{LOCATION}} src-address={{ROUTER_ID}} trap-community=*1
/system clock
set time-zone-name=America/Chicago
/system identity
set name={{ROUTER_IDENTITY}}
/system logging
set 0 action=echo
add action=syslog topics=critical
add action=syslog topics=error
add action=syslog topics=warning
add action=disk topics=critical
add action=disk topics=error
add action=disk topics=warning
add topics=critical
add topics=error
add topics=warning
/system note
set note="COMPLIANCE SCRIPT LAST RUN ON {{GENERATED_AT}}" show-at-login=no
/system ntp client
set enabled=yes
/system ntp client servers
add address=ntp-pool.nxlink.com
/system routerboard settings
set auto-upgrade=yes enter-setup-on=delete-key
