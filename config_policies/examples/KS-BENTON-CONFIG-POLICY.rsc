/interface bridge
add comment=IDEATEK-MGMT name=bridge600 port-cost-mode=short protocol-mode=none
add comment=IDEATEK-CUST name=bridge800 port-cost-mode=short protocol-mode=none
add comment=DYNAMIC name=bridge1000 port-cost-mode=short protocol-mode=none
add comment=STATIC name=bridge2000 port-cost-mode=short protocol-mode=none
add comment=INFRA name=bridge3000 port-cost-mode=short protocol-mode=none
add comment=CPE name=bridge4000 port-cost-mode=short protocol-mode=none
add name=loop0 port-cost-mode=short
add name=vpls-bridge port-cost-mode=short
/interface ethernet
set [ find default-name=ether1 ] comment="Netonix Uplink #1" l2mtu=9212
set [ find default-name=ether2 ] comment="Netonix Uplink #2" l2mtu=9212
set [ find default-name=ether5 ] comment=KS-FURLEY-CN-1 l2mtu=9212 mtu=9198
set [ find default-name=ether6 ] comment=KS-ANDOVER-NE-1 l2mtu=9212 mtu=9198
set [ find default-name=sfp3 ] auto-negotiation=no
/interface vpls
add arp=enabled cisco-static-id=3 disabled=no mac-address=02:64:23:28:8D:A5 mtu=1500 name=vpls-bng1 peer=10.248.0.3 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=3 disabled=no mac-address=02:E4:E1:1B:AD:97 mtu=1500 name=vpls-bng2 peer=10.248.0.4 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=600 comment=VPLS600-BNG-KS-NET disabled=no mac-address=02:E1:1C:F7:B9:02 mtu=1500 name=vpls600-bng-ks-net peer=10.248.0.1 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=800 comment=VPLS800-BNG-KS-NET disabled=no mac-address=02:AD:DE:A9:3D:23 mtu=1500 name=vpls800-bng-ks-net peer=10.248.0.1 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=1248 comment=VPLS1000-BNG-KS disabled=no mac-address=02:6B:71:F2:41:EE mtu=1500 name=vpls1000-bng-ks peer=10.249.0.200 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=2248 comment=VPLS2000-BNG-KS disabled=no mac-address=02:6A:5D:D4:7C:0F mtu=1500 name=vpls2000-bng-ks peer=10.249.0.200 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=3248 comment=VPLS3000-BNG-KS disabled=no mac-address=02:4D:75:77:21:9F mtu=1500 name=vpls3000-bng-ks peer=10.249.0.200 pw-l2mtu=1580 pw-type=raw-ethernet
add arp=enabled cisco-static-id=4248 comment=VPLS4000-BNG-KS disabled=no mac-address=02:AC:67:CE:AB:A3 mtu=1500 name=vpls4000-bng-ks peer=10.249.0.200 pw-l2mtu=1580 pw-type=raw-ethernet
/interface lte apn
set [ find default=yes ] ip-type=ipv4 use-network-apn=no
/ip dhcp-server option
add code=43 name=opt43 value=0x011768747470733a2f2f7573732e6e786c696e6b2e636f6d2f
/ip smb users
set [ find default=yes ] disabled=yes
/port
set 0 name=serial0
set 1 name=serial1
/routing bgp template
set default as=26077 disabled=no output.network=bgp-networks router-id=10.248.0.53
/routing ospf instance
add disabled=no name=default-v2 router-id=10.248.0.53
/routing ospf area
add disabled=yes instance=default-v2 name=backbone-v2
add area-id=0.0.0.248 disabled=no instance=default-v2 name=area248-v2
/snmp community
set [ find default=yes ] read-access=no
add addresses=::/0 name=FBZ1yYdphf
/system logging action
set 1 disk-file-count=3 disk-lines-per-file=10000
add name=syslog remote=142.147.116.215 src-address=10.248.0.53 target=remote
/user group
set read policy=local,telnet,ssh,read,test,winbox,sniff,!ftp,!reboot,!write,!policy,!password,!web,!sensitive,!api,!romon,!rest-api
/interface bridge port
add bridge=vpls-bridge ingress-filtering=no interface=ether1 internal-path-cost=10 path-cost=10
add bridge=vpls-bridge ingress-filtering=no interface=ether2 internal-path-cost=10 path-cost=10
add bridge=vpls-bridge edge=yes horizon=1 ingress-filtering=no interface=vpls-bng1 internal-path-cost=10 path-cost=10
add bridge=vpls-bridge edge=yes horizon=1 ingress-filtering=no interface=vpls-bng2 internal-path-cost=10 path-cost=10
add bridge=bridge600 edge=yes horizon=1 ingress-filtering=no interface=vpls600-bng-ks-net internal-path-cost=10 path-cost=10
add bridge=bridge800 edge=yes horizon=1 ingress-filtering=no interface=vpls800-bng-ks-net internal-path-cost=10 path-cost=10
add bridge=bridge1000 edge=yes horizon=1 ingress-filtering=no interface=vpls1000-bng-ks internal-path-cost=10 path-cost=10
add bridge=bridge2000 edge=yes horizon=1 ingress-filtering=no interface=vpls2000-bng-ks internal-path-cost=10 path-cost=10
add bridge=bridge3000 edge=yes horizon=1 ingress-filtering=no interface=vpls3000-bng-ks internal-path-cost=10 path-cost=10
add bridge=bridge4000 edge=yes horizon=1 ingress-filtering=no interface=vpls4000-bng-ks internal-path-cost=10 path-cost=10
/ip neighbor discovery-settings
set discover-interface-list=!dynamic
/ip settings
set max-neighbor-entries=8192
/ipv6 settings
set disable-ipv6=yes max-neighbor-entries=8192 soft-max-neighbor-entries=8191
/interface ovpn-server server
add auth=sha1,md5 mac-address=FE:B7:C3:7B:56:4F name=ovpn-server1
/ip address
add address=10.248.0.53 comment=loop0 interface=loop0 network=10.248.0.53
add address=10.248.3.68/29 comment=KS-FURLEY-CN-1 interface=ether5 network=10.248.3.64
add address=10.248.3.41/29 comment=KS-ANDOVER-NE-1 interface=ether6 network=10.248.3.40
/ip dhcp-server option sets
add name=optset options=opt43
/ip dns
set servers=142.147.112.3,142.147.112.19
/ip firewall address-list
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
set sip disabled=yes
/ip ipsec profile
set [ find default=yes ] dpd-interval=2m dpd-maximum-failures=5
/ip service
set www disabled=yes port=1234
set ftp disabled=yes port=5021
set telnet disabled=yes port=5023
set api disabled=yes
set api-ssl disabled=yes
/ip smb shares
set [ find default=yes ] directory=/pub
/mpls interface
add disabled=no input=yes interface=all mpls-mtu=9000
/mpls ldp
add disabled=no lsr-id=10.248.0.53 transport-addresses=10.248.0.53
/mpls ldp accept-filter
add accept=no disabled=no prefix=10.2.0.14/32
add accept=no disabled=no prefix=10.2.0.21/32
add accept=no disabled=no prefix=10.2.0.107/32
add accept=no disabled=no prefix=10.2.0.108/32
add accept=no disabled=no prefix=10.17.0.10/32
add accept=no disabled=no prefix=10.17.0.11/32
add accept=no disabled=no prefix=10.30.0.9/32
add accept=no disabled=no prefix=10.240.0.3/32
add accept=no disabled=no prefix=10.243.0.9/32
add accept=no disabled=no prefix=10.248.0.220/32
add accept=no disabled=no prefix=10.249.0.220/32
add accept=no disabled=no prefix=10.0.0.87/32
add accept=no disabled=no prefix=10.9.0.88/32
add accept=no disabled=no prefix=10.254.247.9/32
add accept=yes disabled=no prefix=10.2.0.10/32
add accept=yes disabled=no prefix=10.0.0.0/24
add accept=yes disabled=no prefix=10.0.1.0/24
add accept=yes disabled=no prefix=10.1.0.0/24
add accept=yes disabled=no prefix=10.2.0.0/24
add accept=yes disabled=no prefix=10.3.0.0/24
add accept=yes disabled=no prefix=10.4.0.0/24
add accept=yes disabled=no prefix=10.4.3.0/24
add accept=yes disabled=no prefix=10.5.0.0/24
add accept=yes disabled=no prefix=10.6.0.0/24
add accept=yes disabled=no prefix=10.7.0.0/24
add accept=yes disabled=no prefix=10.7.250.0/24
add accept=yes disabled=no prefix=10.7.254.0/24
add accept=yes disabled=no prefix=10.8.0.0/24
add accept=yes disabled=no prefix=10.9.0.0/24
add accept=yes disabled=no prefix=10.9.1.0/24
add accept=yes disabled=no prefix=10.9.2.0/24
add accept=yes disabled=no prefix=10.10.0.0/24
add accept=yes disabled=no prefix=10.11.0.0/24
add accept=yes disabled=no prefix=10.12.0.0/24
add accept=yes disabled=no prefix=10.2.0.0/24
add accept=yes disabled=no prefix=10.13.0.0/24
add accept=yes disabled=no prefix=10.14.0.0/24
add accept=yes disabled=no prefix=10.15.0.0/24
add accept=yes disabled=no prefix=10.16.0.0/24
add accept=yes disabled=no prefix=10.17.0.0/24
add accept=yes disabled=no prefix=10.17.16.0/24
add accept=yes disabled=no prefix=10.17.18.0/24
add accept=yes disabled=no prefix=10.17.31.0/24
add accept=yes disabled=no prefix=10.17.48.0/24
add accept=yes disabled=no prefix=10.18.0.0/24
add accept=yes disabled=no prefix=10.18.2.0/24
add accept=yes disabled=no prefix=10.19.0.0/24
add accept=yes disabled=no prefix=10.21.0.0/24
add accept=yes disabled=no prefix=10.22.0.0/24
add accept=yes disabled=no prefix=10.25.0.0/24
add accept=yes disabled=no prefix=10.26.0.0/24
add accept=yes disabled=no prefix=10.27.0.0/24
add accept=yes disabled=no prefix=10.30.0.0/24
add accept=yes disabled=no prefix=10.3.0.0/24
add accept=yes disabled=no prefix=10.32.0.0/24
add accept=yes disabled=no prefix=10.33.0.0/24
add accept=yes disabled=no prefix=10.34.0.0/24
add accept=yes disabled=no prefix=10.35.0.0/24
add accept=yes disabled=no prefix=10.36.0.0/24
add accept=yes disabled=no prefix=10.37.0.0/24
add accept=yes disabled=no prefix=10.39.0.0/24
add accept=yes disabled=no prefix=10.45.252.0/24
add accept=yes disabled=no prefix=10.47.0.0/24
add accept=yes disabled=no prefix=10.53.252.0/22
add accept=yes disabled=no prefix=10.254.243.0/24
add accept=yes disabled=no prefix=10.243.0.0/24
add accept=yes disabled=no prefix=10.54.0.0/22
add accept=yes disabled=no prefix=10.250.0.0/24
add accept=yes disabled=no prefix=10.250.40.0/22
add accept=yes disabled=no prefix=10.241.0.0/24
add accept=yes disabled=no prefix=10.241.64.0/22
add accept=yes disabled=no prefix=10.254.42.0/24
add accept=yes disabled=no prefix=10.254.245.0/24
add accept=yes disabled=no prefix=10.42.0.0/24
add accept=yes disabled=no prefix=10.42.12.0/24
add accept=yes disabled=no prefix=10.42.192.0/22
add accept=yes disabled=no prefix=10.254.249.0/24
add accept=yes disabled=no prefix=10.249.0.0/24
add accept=yes disabled=no prefix=10.249.7.0/24
add accept=yes disabled=no prefix=10.249.180.0/22
add accept=yes disabled=no prefix=10.254.247.0/24
add accept=yes disabled=no prefix=10.247.0.0/24
add accept=yes disabled=no prefix=10.247.13.0/24
add accept=yes disabled=no prefix=10.247.72.0/24
add accept=yes disabled=no prefix=10.247.147.0/24
add accept=yes disabled=no prefix=10.247.187.0/24
add accept=yes disabled=no prefix=10.247.64.0/22
add accept=yes disabled=no prefix=10.254.248.0/24
add accept=yes disabled=no prefix=10.248.0.0/24
add accept=yes disabled=no prefix=10.248.32.0/24
add accept=yes disabled=no prefix=10.248.36.0/24
add accept=yes disabled=no prefix=10.248.86.0/24
add accept=yes disabled=no prefix=10.248.208.0/22
add accept=no disabled=no prefix=0.0.0.0/0
/mpls ldp advertise-filter
add advertise=no disabled=no prefix=10.2.0.14/32
add advertise=no disabled=no prefix=10.2.0.21/32
add advertise=no disabled=no prefix=10.2.0.107/32
add advertise=no disabled=no prefix=10.2.0.108/32
add advertise=no disabled=no prefix=10.17.0.10/32
add advertise=no disabled=no prefix=10.17.0.11/32
add advertise=no disabled=no prefix=10.30.0.9/32
add advertise=no disabled=no prefix=10.240.0.3/32
add advertise=no disabled=no prefix=10.243.0.9/32
add advertise=no disabled=no prefix=10.248.0.220/32
add advertise=no disabled=no prefix=10.249.0.220/32
add advertise=no disabled=no prefix=10.254.247.9/32
add advertise=no disabled=no prefix=10.0.0.87/32
add advertise=no disabled=no prefix=10.9.0.88/32
add advertise=yes disabled=no prefix=10.2.0.10/32
add advertise=yes disabled=no prefix=10.0.0.0/24
add advertise=yes disabled=no prefix=10.0.1.0/24
add advertise=yes disabled=no prefix=10.1.0.0/24
add advertise=yes disabled=no prefix=10.2.0.0/24
add advertise=yes disabled=no prefix=10.3.0.0/24
add advertise=yes disabled=no prefix=10.4.0.0/24
add advertise=yes disabled=no prefix=10.4.3.0/24
add advertise=yes disabled=no prefix=10.5.0.0/24
add advertise=yes disabled=no prefix=10.6.0.0/24
add advertise=yes disabled=no prefix=10.7.0.0/24
add advertise=yes disabled=no prefix=10.7.250.0/24
add advertise=yes disabled=no prefix=10.7.254.0/24
add advertise=yes disabled=no prefix=10.8.0.0/24
add advertise=yes disabled=no prefix=10.9.0.0/24
add advertise=yes disabled=no prefix=10.9.1.0/24
add advertise=yes disabled=no prefix=10.9.2.0/24
add advertise=yes disabled=no prefix=10.10.0.0/24
add advertise=yes disabled=no prefix=10.11.0.0/24
add advertise=yes disabled=no prefix=10.12.0.0/24
add advertise=yes disabled=no prefix=10.2.0.0/24
add advertise=yes disabled=no prefix=10.13.0.0/24
add advertise=yes disabled=no prefix=10.14.0.0/24
add advertise=yes disabled=no prefix=10.15.0.0/24
add advertise=yes disabled=no prefix=10.16.0.0/24
add advertise=yes disabled=no prefix=10.17.0.0/24
add advertise=yes disabled=no prefix=10.17.16.0/24
add advertise=yes disabled=no prefix=10.17.18.0/24
add advertise=yes disabled=no prefix=10.17.31.0/24
add advertise=yes disabled=no prefix=10.17.48.0/24
add advertise=yes disabled=no prefix=10.18.0.0/24
add advertise=yes disabled=no prefix=10.18.2.0/24
add advertise=yes disabled=no prefix=10.19.0.0/24
add advertise=yes disabled=no prefix=10.21.0.0/24
add advertise=yes disabled=no prefix=10.22.0.0/24
add advertise=yes disabled=no prefix=10.25.0.0/24
add advertise=yes disabled=no prefix=10.26.0.0/24
add advertise=yes disabled=no prefix=10.27.0.0/24
add advertise=yes disabled=no prefix=10.30.0.0/24
add advertise=yes disabled=no prefix=10.3.0.0/24
add advertise=yes disabled=no prefix=10.32.0.0/24
add advertise=yes disabled=no prefix=10.33.0.0/24
add advertise=yes disabled=no prefix=10.34.0.0/24
add advertise=yes disabled=no prefix=10.35.0.0/24
add advertise=yes disabled=no prefix=10.36.0.0/24
add advertise=yes disabled=no prefix=10.37.0.0/24
add advertise=yes disabled=no prefix=10.39.0.0/24
add advertise=yes disabled=no prefix=10.45.252.0/24
add advertise=yes disabled=no prefix=10.47.0.0/24
add advertise=yes disabled=no prefix=10.53.252.0/22
add advertise=yes disabled=no prefix=10.254.243.0/24
add advertise=yes disabled=no prefix=10.243.0.0/24
add advertise=yes disabled=no prefix=10.54.0.0/22
add advertise=yes disabled=no prefix=10.250.0.0/24
add advertise=yes disabled=no prefix=10.250.40.0/22
add advertise=yes disabled=no prefix=10.241.0.0/24
add advertise=yes disabled=no prefix=10.241.64.0/22
add advertise=yes disabled=no prefix=10.254.42.0/24
add advertise=yes disabled=no prefix=10.254.245.0/24
add advertise=yes disabled=no prefix=10.42.0.0/24
add advertise=yes disabled=no prefix=10.42.12.0/24
add advertise=yes disabled=no prefix=10.42.192.0/22
add advertise=yes disabled=no prefix=10.254.249.0/24
add advertise=yes disabled=no prefix=10.249.0.0/24
add advertise=yes disabled=no prefix=10.249.7.0/24
add advertise=yes disabled=no prefix=10.249.180.0/22
add advertise=yes disabled=no prefix=10.254.247.0/24
add advertise=yes disabled=no prefix=10.247.0.0/24
add advertise=yes disabled=no prefix=10.247.13.0/24
add advertise=yes disabled=no prefix=10.247.72.0/24
add advertise=yes disabled=no prefix=10.247.147.0/24
add advertise=yes disabled=no prefix=10.247.187.0/24
add advertise=yes disabled=no prefix=10.247.64.0/22
add advertise=yes disabled=no prefix=10.254.248.0/24
add advertise=yes disabled=no prefix=10.248.0.0/24
add advertise=yes disabled=no prefix=10.248.32.0/24
add advertise=yes disabled=no prefix=10.248.36.0/24
add advertise=yes disabled=no prefix=10.248.86.0/24
add advertise=yes disabled=no prefix=10.248.208.0/22
add advertise=no disabled=no prefix=0.0.0.0/0
/mpls ldp interface
add disabled=no interface=ether5
add disabled=no interface=ether6
/radius
add address=142.147.112.2 secret=Nl22021234 service=dhcp src-address=10.248.0.53 timeout=5s
add address=142.147.112.18 secret=Nl22021234 service=dhcp src-address=10.248.0.53 timeout=5s
/routing bfd configuration
add disabled=no interfaces=all min-rx=200ms min-tx=200ms multiplier=5
/routing bgp connection
add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address=10.248.0.53 .role=ibgp multihop=yes name=CR7 remote.address=10.2.0.107 .as=26077 .port=179 tcp-md5-key=nvla8Z templates=default
add cisco-vpls-nlri-len-fmt=auto-bits connect=yes listen=yes local.address=10.248.0.53 .role=ibgp multihop=yes name=CR8 remote.address=10.2.0.108 .as=26077 .port=179 tcp-md5-key=nvla8Z templates=default
/routing ospf interface-template
add area=area248-v2 disabled=no interfaces=loop0 networks=10.248.0.53 priority=1
add area=area248-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM cost=10 disabled=no interfaces=ether5 networks=10.248.3.64/29 priority=1 type=ptp use-bfd=no
add area=area248-v2 auth=md5 auth-id=1 auth-key=m8M5JwvdYM cost=10 disabled=no interfaces=ether6 networks=10.248.3.40/29 priority=1 type=ptp use-bfd=no
/snmp
set enabled=yes trap-community=FBZ1yYdphf
/system clock
set time-zone-name=America/Chicago
/system identity
set name=RTR-MT1036-AR1.KS-BENTON-SW-1
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
set note="COMPLIANCE SCRIPT LAST RUN ON 2025-10-28 05:39:40"
/system ntp client
set enabled=yes
/system ntp client servers
add address=ntp-pool.nxlink.com
/system routerboard settings
set auto-upgrade=yes
