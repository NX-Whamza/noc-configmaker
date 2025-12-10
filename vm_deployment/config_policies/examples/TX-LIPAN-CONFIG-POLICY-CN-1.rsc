# 2025-11-05 16:58:06 by RouterOS 7.19.4
# software id = A9DD-SZ3P
#
# model = CCR2004-1G-12S+2XS
# serial number = HE308T8ETRA
/interface bridge add comment=STATIC name=bridge2000 port-cost-mode=short
/interface bridge add comment="MGMT" name=bridge3000 port-cost-mode=short
/interface bridge add comment=CPE name=bridge4000 port-cost-mode=short
/interface bridge add name=lan-bridge port-cost-mode=short priority=0x1
/interface bridge add name=loop0 port-cost-mode=short
/interface bridge add name=nat-public-bridge port-cost-mode=short
/interface ethernet set [ find default-name=sfp-sfpplus1 ] comment="Netonix Uplink #1"
/interface ethernet set [ find default-name=sfp-sfpplus2 ] comment="Netonix Uplink #2" disabled=yes
/interface ethernet set [ find default-name=sfp-sfpplus4 ] comment=TX-NEXTTOWER-CN-1
/interface ethernet set [ find default-name=sfp-sfpplus5 ] comment=TX-NEXTTOWER-CN-3
/interface ethernet set [ find default-name=sfp-sfpplus8 ] comment="SWT-CRS326 Uplink #1 - BONDED"
/interface ethernet set [ find default-name=sfp-sfpplus9 ] comment="SWT-CRS326 Uplink #2 - BONDED"
/interface ethernet set [ find default-name=sfp-sfpplus11 ] auto-negotiation=no speed=100M-baseT-full
/interface ethernet set [ find default-name=sfp-sfpplus12 ] auto-negotiation=no speed=100M-baseT-full
/interface bonding add lacp-user-key=1 mode=802.3ad name=bonding1 slaves=sfp-sfpplus8,sfp-sfpplus9 transmit-hash-policy=layer-2-and-3
/interface vlan add interface=bonding1 name=vlan1000-bonding1 vlan-id=1000
/interface vlan add interface=bonding1 name=vlan2000-bonding1 vlan-id=2000
/interface vlan add interface=bonding1 name=vlan3000-bonding1 vlan-id=3000
/interface vlan add interface=bonding1 name=vlan4000-bonding1 vlan-id=4000
/ip dhcp-server option add code=43 name=opt43 value=0x011768747470733a2f2f7573732e6e786c696e6b2e636f6d2f
/ip dhcp-server option sets add name=optset options=opt43
/ip pool add name=unauth ranges=10.100.10.2-10.100.10.254
/ip pool add name=cpe ranges=10.10.10.50-10.10.10.254
/ip pool add name=cust ranges=100.64.0.3-100.64.3.254
/ip dhcp-server add address-pool=cust interface=lan-bridge lease-time=1h name=server1 use-radius=yes
/ip smb users set [ find default=yes ] disabled=yes
/port set 0 name=serial0
/port set 1 name=serial1
/queue type set 9 pfifo-limit=50
/routing bgp template set default as=26077 disabled=no multihop=yes output.network=bgp-networks router-id=10.1.1.1 routing-table=main
/routing ospf instance add disabled=no name=default-v2 router-id=10.1.1.1
/routing ospf area add disabled=no instance=default-v2 name=backbone-v2
/snmp community set [ find default=yes ] read-access=no
/snmp community add addresses=::/0 name=FBZ1yYdphf
/system logging action set 1 disk-file-count=3 disk-lines-per-file=10000
/system logging action add name=syslog remote=142.147.116.215 src-address=10.1.1.1 target=remote
/user group set read policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
/interface bridge port add bridge=lan-bridge interface=sfp-sfpplus1 internal-path-cost=10 path-cost=10
/interface bridge port add bridge=lan-bridge interface=sfp-sfpplus2 internal-path-cost=10 path-cost=10
/interface bridge port add bridge=bridge4000 ingress-filtering=no interface=vlan4000-bonding1 internal-path-cost=10 path-cost=10
/interface bridge port add bridge=bridge3000 ingress-filtering=no interface=vlan3000-bonding1 internal-path-cost=10 path-cost=10
/interface bridge port add bridge=lan-bridge ingress-filtering=no interface=vlan1000-bonding1 internal-path-cost=10 path-cost=10
/interface bridge port add bridge=bridge2000 ingress-filtering=no interface=vlan2000-bonding1 internal-path-cost=10 path-cost=10
/ip neighbor discovery-settings set discover-interface-list=!dynamic
/interface ovpn-server server add mac-address=FE:D5:82:4E:5D:A4 name=ovpn-server1
/ip address add address=10.1.1.1 comment=loop0 interface=loop0 network=10.1.1.1
/ip address add address=10.10.10.1/24 comment="CPE/Tower Gear" interface=lan-bridge network=10.10.10.0
/ip address add address=10.100.10.1/24 comment=UNAUTH interface=lan-bridge network=10.100.10.0
/ip address add address=132.147.147.255 comment="CGNAT Public" interface=nat-public-bridge network=132.147.147.255
/ip address add address=100.64.0.1/22 comment="CGNAT Private" interface=lan-bridge network=100.64.0.0
/ip address add address=10.20.20.1/29 comment=TX-NEXTTOWER-CN-1 interface=sfp-sfpplus4 network=10.20.20.0
/ip address add address=10.5.5.4/29 comment=TX-NEXTTOWER-CN-3 interface=sfp-sfpplus5 network=10.5.5.0
/ip address add address=10.30.30.1/28 comment="BRIDGE3000 MGMT" interface=bridge3000 network=10.30.30.0
/ip dhcp-server network add address=10.10.10.0/24 dns-server=4.2.2.2,8.8.8.8 gateway=10.10.10.1 netmask=24
/ip dhcp-server network add address=10.100.10.0/24 dns-server=4.2.2.2,8.8.8.8 gateway=10.100.10.1 netmask=24
/ip dhcp-server network add address=100.64.0.0/22 dhcp-option-set=*1 dns-server=4.2.2.2,8.8.8.8 gateway=100.64.0.1 netmask=22
/ip dns set max-udp-packet-size=512 servers=4.2.2.2,8.8.8.8
/ip firewall address-list add address=10.100.10.0/24 comment=UNAUTH list=bgp-networks
/ip firewall address-list add address=132.147.147.255 comment=CGNAT_PUBLIC list=bgp-networks
/ip firewall address-list add address=100.64.0.0/22 comment=CGNAT_PRIVATE list=bgp-networks
/ip firewall address-list add address=142.147.112.3 list=NAT-EXEMPT-DST
/ip firewall address-list add address=142.147.112.19 list=NAT-EXEMPT-DST
/ip firewall address-list add address=107.178.15.0/27 list=NAT-EXEMPT-DST
/ip firewall address-list add address=107.178.5.97 list=NAT-EXEMPT-DST
/ip firewall address-list add address=52.128.59.240 list=NTP
/ip firewall address-list add address=52.128.59.241 list=NTP
/ip firewall address-list add address=52.128.59.242 list=NTP
/ip firewall address-list add address=52.128.59.243 list=NTP
/ip firewall address-list add address=10.0.0.0/8 list=EOIP-ALLOW
/ip firewall address-list add address=192.168.128.0/21 list=managerIP
/ip firewall address-list add address=107.178.5.97 list=managerIP
/ip firewall address-list add address=198.100.53.0/25 list=managerIP
/ip firewall address-list add address=143.55.62.143 list=managerIP
/ip firewall address-list add address=142.147.127.2 list=managerIP
/ip firewall address-list add address=132.147.132.6 list=managerIP
/ip firewall address-list add address=67.219.122.201 list=managerIP
/ip firewall address-list add address=10.249.1.26 list=managerIP
/ip firewall address-list add address=10.0.0.0/8 list=managerIP
/ip firewall address-list add address=10.0.0.0/8 list=BGP-ALLOW
/ip firewall address-list add address=143.55.35.47 list=SNMP
/ip firewall address-list add address=107.178.15.15 list=SNMP
/ip firewall address-list add address=107.178.15.162 list=SNMP
/ip firewall address-list add address=142.147.112.4 list=SNMP
/ip firewall address-list add address=142.147.124.26 list=SNMP
/ip firewall address-list add address=107.178.5.97 list=SNMP
/ip firewall address-list add address=52.128.51.70 list=SNMP
/ip firewall address-list add address=52.128.51.80 list=SNMP
/ip firewall address-list add address=67.219.126.240/28 list=SNMP
/ip firewall address-list add address=198.100.53.120 list=SNMP
/ip firewall address-list add address=143.55.62.143 list=SNMP
/ip firewall address-list add address=132.147.138.2 list=SNMP
/ip firewall address-list add address=132.147.138.0 list=SNMP
/ip firewall address-list add address=132.147.138.6 list=SNMP
/ip firewall address-list add address=132.147.138.23 list=SNMP
/ip firewall address-list add address=132.147.138.29 list=SNMP
/ip firewall address-list add address=132.147.138.30 list=SNMP
/ip firewall address-list add address=132.147.138.31 list=SNMP
/ip firewall address-list add address=143.55.37.40 list=SNMP
/ip firewall address-list add address=143.55.37.41 list=SNMP
/ip firewall address-list add address=132.147.132.24 list=SNMP
/ip firewall address-list add address=198.100.49.99 list=SNMP
/ip firewall address-list add address=132.147.132.26 list=SNMP
/ip firewall address-list add address=132.147.132.40 list=SNMP
/ip firewall address-list add address=204.11.183.126 list=SNMP
/ip firewall address-list add address=173.215.67.124 list=SNMP
/ip firewall address-list add address=132.147.138.3 list=SNMP
/ip firewall address-list add address=132.147.138.7 list=SNMP
/ip firewall address-list add address=132.147.138.21 list=SNMP
/ip firewall address-list add address=132.147.138.26 list=SNMP
/ip firewall address-list add address=142.147.112.3 list=WALLED-GARDEN
/ip firewall address-list add address=142.147.112.19 list=WALLED-GARDEN
/ip firewall address-list add address=107.178.15.27 list=WALLED-GARDEN
/ip firewall address-list add address=142.147.112.12 list=WALLED-GARDEN
/ip firewall address-list add address=132.147.147.56 list=WALLED-GARDEN
/ip firewall address-list add address=35.227.221.107 list=WALLED-GARDEN
/ip firewall address-list add address=172.66.155.116 list=WALLED-GARDEN
/ip firewall address-list add address=104.20.19.83 list=WALLED-GARDEN
/ip firewall filter add action=accept chain=input comment="ALLOW EST REL" connection-state=established,related,untracked
/ip firewall filter add action=accept chain=input comment="ALLOW MT NEIGHBOR" dst-port=5678 protocol=udp
/ip firewall filter add action=accept chain=input comment="ALLOW MAC TELNET" dst-port=20561 protocol=udp
/ip firewall filter add action=accept chain=input comment="ALLOW IGMP" protocol=igmp
/ip firewall filter add action=accept chain=input comment="ALLOW ICMP" protocol=icmp
/ip firewall filter add action=accept chain=input comment="ALLOW DHCPv4" dst-port=67 protocol=udp
/ip firewall filter add action=accept chain=input comment="ALLOW DHCPv6" dst-port=547 protocol=udp
/ip firewall filter add action=accept chain=input comment="ALLOW OSPF" protocol=ospf
/ip firewall filter add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=tcp
/ip firewall filter add action=accept chain=input comment="ALLOW LDP" dst-port=646 protocol=udp
/ip firewall filter add action=accept chain=input comment="ALLOW MANAGER IP" src-address-list=managerIP
/ip firewall filter add action=accept chain=input comment="ALLOW BGP" dst-port=179 protocol=tcp src-address-list=BGP-ALLOW
/ip firewall filter add action=accept chain=input comment="ALLOW EOIP" protocol=gre src-address-list=EOIP-ALLOW
/ip firewall filter add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=tcp src-address-list=SNMP
/ip firewall filter add action=accept chain=input comment="ALLOW SNMP" dst-port=161 protocol=udp src-address-list=SNMP
/ip firewall filter add action=drop chain=input comment="DROP INPUT"
/ip firewall filter add action=accept chain=forward comment="NTP Allow" dst-address-list=NTP dst-port=123 in-interface=lan-bridge protocol=udp
/ip firewall filter add action=accept chain=forward comment="NTP Allow" dst-address=10.0.0.1 dst-port=123 in-interface=lan-bridge protocol=udp
/ip firewall filter add action=drop chain=forward comment="Traceroute Drop" out-interface=lan-bridge protocol=icmp src-address=10.0.0.0/8
/ip firewall filter add action=drop chain=forward comment="Private Space Protect" dst-address=10.0.0.0/8 in-interface=lan-bridge
/ip firewall filter add action=accept chain=forward comment="BGP Accept" dst-address=10.0.0.0/8 dst-port=179 protocol=tcp src-address=10.0.0.0/8
/ip firewall filter add action=accept chain=forward comment="GRE Accept " dst-address=10.0.0.0/8 protocol=gre src-address=10.0.0.0/8
/ip firewall filter add action=drop chain=forward comment="unauth drop rule" dst-address-list=!WALLED-GARDEN src-address-list=unauth
/ip firewall filter add action=fasttrack-connection chain=forward connection-state=established,related,untracked hw-offload=yes
/ip firewall filter add action=accept chain=forward connection-state=established,related,untracked
/ip firewall nat add action=redirect chain=dstnat dst-address-type=local dst-port=5022 protocol=tcp to-ports=22
/ip firewall nat add action=dst-nat chain=dstnat comment="unauth proxy rule" dst-address-list=!WALLED-GARDEN dst-port=80 protocol=tcp src-address-list=unauth to-addresses=107.178.15.27 to-ports=3128
/ip firewall raw add action=drop chain=prerouting comment="DROP BAD UDP" port=0 protocol=udp
/ip firewall service-port set sip disabled=yes
/ip ipsec profile set [ find default=yes ] dpd-interval=2m dpd-maximum-failures=5
/ip service set www disabled=yes port=1234
/ip service set ftp disabled=yes port=5021
/ip service set telnet disabled=yes port=5023
/ip service set api disabled=yes
/ip service set api-ssl disabled=yes
/ip smb shares set [ find default=yes ] directory=/pub
/mpls ldp accept-filter add accept=no disabled=no prefix=10.2.0.14/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.2.0.21/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.2.0.107/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.2.0.108/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.17.0.10/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.17.0.11/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.30.0.9/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.240.0.3/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.243.0.9/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.248.0.220/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.249.0.220/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.0.0.87/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.9.0.88/32
/mpls ldp accept-filter add accept=no disabled=no prefix=10.254.247.9/32
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.2.0.10/32
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.0.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.0.1.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.1.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.2.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.3.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.4.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.4.3.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.5.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.6.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.7.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.7.250.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.7.254.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.8.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.9.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.9.1.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.9.2.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.10.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.11.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.12.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.2.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.13.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.14.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.15.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.16.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.17.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.17.16.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.17.18.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.17.31.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.17.48.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.18.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.18.2.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.19.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.21.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.22.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.25.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.26.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.27.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.30.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.3.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.32.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.33.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.34.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.35.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.36.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.37.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.39.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.45.252.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.47.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.53.252.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.254.243.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.243.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.54.0.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.250.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.250.40.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.241.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.241.64.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.254.42.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.254.245.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.42.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.42.12.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.42.192.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.254.249.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.249.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.249.7.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.249.180.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.254.247.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.247.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.247.13.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.247.72.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.247.147.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.247.187.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.247.64.0/22
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.254.248.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.248.0.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.248.32.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.248.36.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.248.86.0/24
/mpls ldp accept-filter add accept=yes disabled=no prefix=10.248.208.0/22
/mpls ldp accept-filter add accept=no disabled=no prefix=0.0.0.0/0
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.2.0.14/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.2.0.21/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.2.0.107/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.2.0.108/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.17.0.10/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.17.0.11/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.30.0.9/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.240.0.3/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.243.0.9/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.248.0.220/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.249.0.220/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.254.247.9/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.0.0.87/32
/mpls ldp advertise-filter add advertise=no disabled=no prefix=10.9.0.88/32
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.2.0.10/32
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.0.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.0.1.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.1.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.2.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.3.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.4.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.4.3.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.5.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.6.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.7.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.7.250.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.7.254.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.8.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.9.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.9.1.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.9.2.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.10.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.11.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.12.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.2.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.13.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.14.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.15.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.16.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.17.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.17.16.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.17.18.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.17.31.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.17.48.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.18.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.18.2.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.19.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.21.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.22.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.25.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.26.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.27.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.30.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.3.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.32.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.33.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.34.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.35.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.36.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.37.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.39.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.45.252.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.47.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.53.252.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.254.243.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.243.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.54.0.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.250.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.250.40.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.241.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.241.64.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.254.42.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.254.245.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.42.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.42.12.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.42.192.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.254.249.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.249.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.249.7.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.249.180.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.254.247.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.247.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.247.13.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.247.72.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.247.147.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.247.187.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.247.64.0/22
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.254.248.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.248.0.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.248.32.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.248.36.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.248.86.0/24
/mpls ldp advertise-filter add advertise=yes disabled=no prefix=10.248.208.0/22
/mpls ldp advertise-filter add advertise=no disabled=no prefix=0.0.0.0/0
/radius add address=142.147.112.8 secret=Nl22021234 service=dhcp src-address=10.1.1.1 timeout=5s
/radius add address=142.147.112.20 secret=Nl22021234 service=dhcp src-address=10.1.1.1 timeout=5s
/routing bgp connection add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address=10.1.1.1 .role=ibgp multihop=yes name=CR7 remote.address=10.2.0.107 .as=26077 .port=179 tcp-md5-key=m8M5JwvdYM templates=default
/routing bgp connection add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address=10.1.1.1 .role=ibgp multihop=yes name=CR8 remote.address=10.2.0.108 .as=26077 .port=179 tcp-md5-key=m8M5JwvdYM templates=default
/routing filter rule add chain=bgr-a-bgp-in-filter disabled=no rule="if (dst in 0.0.0.0/0 && dst-len == 32 && protocol bgp && bgp-communities includes 26077:86) { set blackhole yes; accept; }"
/routing filter rule add chain=bgr-a-bgp-in-filter disabled=no rule="if (dst in 0.0.0.0/0 && dst-len == 0 && protocol bgp) { set bgp-local-pref 500; accept; }"
/routing filter rule add chain=bgr-a-bgp-in-filter disabled=no rule="if (dst in 0.0.0.0/0 && dst-len >= 0 && protocol bgp) { accept; }"
/routing filter rule add chain=bgr-b-bgp-in-filter disabled=no rule="if (dst in 0.0.0.0/0 && dst-len == 32 && protocol bgp && bgp-communities includes 26077:86) { set blackhole yes; accept; }"
/routing filter rule add chain=bgr-b-bgp-in-filter disabled=no rule="if (dst in 0.0.0.0/0 && dst-len == 0 && protocol bgp) { set bgp-local-pref 500; accept; }"
/routing filter rule add chain=bgr-b-bgp-in-filter disabled=no rule="if (dst in 0.0.0.0/0 && dst-len >= 0 && protocol bgp) { accept; }"
/routing ospf interface-template add area=backbone-v2 cost=10 disabled=no interfaces=loop0 networks=10.1.1.1/32 passive priority=1
/routing ospf interface-template add area=backbone-v2 cost=10 disabled=no interfaces=lan-bridge networks=10.10.10.0/24 passive priority=1
/routing ospf interface-template add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment=TX-NEXTTOWER-CN-1 cost=10 disabled=no interfaces=sfp-sfpplus4 networks=10.20.20.0/29 priority=1 type=ptp
/routing ospf interface-template add area=backbone-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM comment=TX-NEXTTOWER-CN-3 cost=10 disabled=no interfaces=sfp-sfpplus5 networks=10.5.5.0/29 priority=1 type=ptp
/routing ospf interface-template add area=backbone-v2 comment="BRIDGE3000 MGMT" cost=10 disabled=no interfaces=bridge3000 networks=10.30.30.0/28 passive priority=1
/snmp set enabled=yes location="32.4859085083, -98.1351928711" src-address=10.1.1.1 trap-community=*1
/system clock set time-zone-name=America/Chicago
/system identity set name=RTR-MT2004-AR1.TX-CONFIG-POLICY-CN-1
/system logging set 0 action=echo
/system logging add action=syslog topics=critical
/system logging add action=syslog topics=error
/system logging add action=syslog topics=warning
/system logging add action=disk topics=critical
/system logging add action=disk topics=error
/system logging add action=disk topics=warning
/system logging add topics=critical
/system logging add topics=error
/system logging add topics=warning
/system note set note="COMPLIANCE SCRIPT LAST RUN ON 2025-11-05 03:19:15"
/system ntp client set enabled=yes
/system ntp client servers add address=ntp-pool.nxlink.com
/system routerboard settings set auto-upgrade=yes enter-setup-on=delete-key
/tool romon set enabled=yes
