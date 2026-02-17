import os
from netaddr import IPNetwork
from jinja2 import Environment, FileSystemLoader


###################################
###          Constants          ###
###################################

DEVICE_TYPES = {
    "MT1009": {
        "port_count": 8,
        "config_template": "mt_1009_tower_config.rsc",
        "port_map_template": "mt_1009_tower_port_map.txt",
    },
    "MT1036": {
        "port_count": 12,
        "config_template": "mt_1036_tower_config.rsc",
        "port_map_template": "mt_1036_tower_port_map.txt",
    },
    "MT1072": {
        "port_count": 8,
        "config_template": "mt_1072_tower_config.rsc",
        "port_map_template": "mt_1072_tower_port_map.txt",
    },
    "MT2004": {
        "port_count": 12,
        "config_template": "mt_2004_tower_config.rsc",
        "port_map_template": "mt_2004_tower_port_map.txt",
    },
    "MT2216": {
        "port_count": 12,
        "config_template": "mt_2216_tower_config.rsc",
        "port_map_template": "mt_2216_tower_port_map.txt",
    },
}

TARANA_SECTORS = [
    {"name": "Alpha", "port": "sfp-sfpplus8", "address_offset": 2},
    {"name": "Beta", "port": "sfp-sfpplus9", "address_offset": 3},
    {"name": "Gamma", "port": "sfp-sfpplus10", "address_offset": 4},
    {"name": "Delta", "port": "sfp-sfpplus6", "address_offset": 5},
]


###################################
###        Config Paths         ###
###################################

CONFIG_TEMPLATE_PATH = os.getenv("BASE_CONFIG_PATH") + "/Router/Tower/config/"
PORT_MAP_TEMPLATE_PATH = os.getenv("BASE_CONFIG_PATH") + "/Router/Tower/port_map/"


def normalize_port_name(p):
    if p is None:
        return p
    s = str(p).strip()
    if not s:
        return s
    if s.startswith("sfp"):
        return s
    if s.startswith("28-"):
        return "sfp" + s
    if s.isdigit():
        return "sfp-sfpplus" + s
    return s


class MTTowerConfig:
    def __init__(self, **params):
        try:
            self.router_type = params["router_type"]
            if self.router_type not in DEVICE_TYPES:
                raise ValueError(f"Invalid router type: {self.router_type}.")
            self.router_params = DEVICE_TYPES[self.router_type]

            # Validate backhauls
            self.backhauls = params["backhauls"]
            if not self.backhauls:
                raise ValueError("No backhauls provided.")
            for backhaul in self.backhauls:
                if not all((
                    backhaul.get("name"),
                    backhaul.get("subnet"),
                    backhaul.get("master") is not None,
                    backhaul.get("port") is not None,
                    backhaul.get("bandwidth"),
                )):
                    raise ValueError(f"Invalid backhaul params: {backhaul}.")

            self.loopback_subnet = IPNetwork(params["loopback_subnet"])
            self.gateway = IPNetwork(params["backhauls"][0]["subnet"])
            self.cpe_subnet = IPNetwork(params["cpe_subnet"])
            self.unauth_subnet = IPNetwork(params["unauth_subnet"])
            self.cgn_priv_subnet = IPNetwork(params["cgn_priv"])
            self.cgn_pub = params["cgn_pub"]
            self.tower_name = params["tower_name"]
            self.latitude = params["latitude"]
            self.longitude = params["longitude"]
            self.state_code = params["state_code"]
            self.asn = params["asn"]
            self.peer_1_address = params["peer_1_address"]
            self.peer_1_name = params["peer_1_name"]
            self.peer_2_address = params["peer_2_address"]
            self.peer_2_name = params["peer_2_name"]

            self.is_6ghz = params.get("is_6ghz", False)

            self.is_326 = params.get("is_326", False)
            if self.is_326:
                self.crs_326_mgmt_subnet = IPNetwork(params["326_mgmt_subnet"])

            self.is_tachyon = params.get("is_tachyon", False)

            if self.is_6ghz or self.is_tachyon:
                self.six_ghz_subnet = IPNetwork(params["6ghz_subnet"])

            self.enable_contractor_login = params.get("enable_contractor_login", False)

            self.is_tarana = params.get("is_tarana", False)
            if self.is_tarana:
                self.tarana_subnet = IPNetwork(params["tarana_subnet"])
                self.tarana_sector_count = int(params["tarana_sector_count"])
                self.tarana_sector_start = int(params["tarana_sector_start"])

        except KeyError as err:
            raise ValueError(f"Missing parameter: {err}")

        # Configure jinja environment
        self.jinja_env = Environment(
            loader=FileSystemLoader([CONFIG_TEMPLATE_PATH, PORT_MAP_TEMPLATE_PATH])
        )
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True

    def get_tarana_sectors(self):
        azimuths = [
            (int(360 / self.tarana_sector_count + 0.5) * x + self.tarana_sector_start)
            % 360
            for x in range(self.tarana_sector_count)
        ]

        return [
            {
                "name": TARANA_SECTORS[i]["name"],
                "port": TARANA_SECTORS[i]["port"],
                "address_offset": TARANA_SECTORS[i]["address_offset"],
                "azimuth": azimuths[i],
            }
            for i in range(self.tarana_sector_count)
        ]

    def get_base_params(self, params=None):
        if not params:
            params = {}

        params["tower_name"] = self.tower_name
        params["loopback"] = self.loopback_subnet
        params["loopback_net"] = self.loopback_subnet.network
        params["router_type"] = self.router_type
        params["asn"] = self.asn
        params["peer1_name"] = self.peer_1_name
        params["peer1"] = self.peer_1_address
        params["peer2_name"] = self.peer_2_name
        params["peer2"] = self.peer_2_address
        params["cgn_pub"] = self.cgn_pub
        params["cgn_priv"] = self.cgn_priv_subnet
        params["gps"] = f"{self.latitude}, {self.longitude}"
        params["state_code"] = self.state_code

        params["unauth_ip"] = str(self.unauth_subnet.network + 1)
        params["unauth_ip_sub"] = self.unauth_subnet.prefixlen
        params["unauth_net"] = self.unauth_subnet
        params["unauth_range_low"] = str(self.unauth_subnet.network + 2)
        params["unauth_range_high"] = str(self.unauth_subnet.network + 1022)

        params["gateway_ip"] = str(self.gateway.network + 1)
        params["cgn_priv_ip"] = str(self.cgn_priv_subnet.network + 1)
        params["cgn_priv_range_low"] = str(self.cgn_priv_subnet.network + 3)
        params["cgn_priv_range_high"] = str(self.cgn_priv_subnet.network + 1022)
        params["cgn_priv_net"] = self.cgn_priv_subnet
        params["cgn_priv_sub"] = self.cgn_priv_subnet.prefixlen
        params["enable_contractor_login"] = self.enable_contractor_login

        params["is_326"] = self.is_326
        params["is_tarana"] = self.is_tarana
        params["is_tachyon"] = self.is_tachyon
        params["is_6ghz"] = self.is_6ghz

        return params

    def get_backhaul_params(self, params=None, num=None):
        if not params:
            params = {}
    
        params["backhauls"] = []
    
        for backhaul in [self.backhauls[num]] if num else self.backhauls:
            addr_offset = 1 if backhaul["master"] else 4
            bh_net = IPNetwork(backhaul["subnet"])
            link_side_1 = self.tower_name if backhaul["master"] else backhaul["name"]
            link_side_2 = backhaul["name"] if backhaul["master"] else self.tower_name
    
            params["backhauls"].append({
                "bhname": backhaul["name"],
                "bhip": str(bh_net.network + addr_offset),
                "interface_bandwidth": backhaul["bandwidth"],
                "port": normalize_port_name(backhaul["port"]),
                "bhip_sub": bh_net.prefixlen,
                "bhsubnet": str(bh_net),
                "masterbh_int": str(bh_net.network + 1),
                "masterbh": str(bh_net.network + 2),
                "slavebh": str(bh_net.network + 3),
                "slavebh_int": str(bh_net.network + 4),
                "link_side_1": link_side_1,
                "link_side_2": link_side_2,
            })
    
        return params

    def get_tarana_params(self, params=None):
        if not params:
            params = {}

        params["tarana_network"] = str(self.tarana_subnet.network)
        params["tarana_gateway"] = str(self.tarana_subnet.network + 1)
        params["tarana_netmask_bits"] = str(self.tarana_subnet.netmask.netmask_bits())
        params["tarana_sectors"] = self.get_tarana_sectors()

        return params

    def get_6ghz_params(self, params=None):
        if not params:
            params = {}

        params["six_ghz_network"] = self.six_ghz_subnet.network
        params["six_ghz_address"] = self.six_ghz_subnet

        return params

    def get_326_params(self, params=None):
        if not params:
            params = {}

        params["crs_326_mgmt_network"] = self.crs_326_mgmt_subnet.network
        params["crs_326_mgmt_mask_bits"] = (
            self.crs_326_mgmt_subnet.netmask.netmask_bits()
        )
        params["crs_326_mgmt_address"] = self.crs_326_mgmt_subnet

        return params

    def get_tachyon_params(self, params=None):
        if not params:
            params = {}

        params["six_ghz_address"] = self.six_ghz_subnet.ip
        params["six_ghz_network"] = self.six_ghz_subnet
        params["six_ghz_cpe_address"] = self.six_ghz_subnet

        return params

    def get_cpe_params(self, params=None):
        if not params:
            params = {}

        params["cpe_net"] = self.cpe_subnet
        params["cpe_ip"] = str(self.cpe_subnet.network + 1)
        params["cpe_ip_sub"] = self.cpe_subnet.prefixlen
        params["cpe_address"] = self.cpe_subnet.ip
        params["cpe_network"] = self.cpe_subnet.network
        params["cpe_gateway"] = self.cpe_subnet.network + 1
        params["cpe_range_low"] = str(self.cpe_subnet.network + 50)
        params["cpe_range_high"] = str(self.cpe_subnet.network + 1022)
        params["vlan_4000_cpe_range_low"] = str(self.cpe_subnet.network + 50)
        params["vlan_4000_cpe_range_high"] = str(self.cpe_subnet.network + 254)
        params["cpe_mask_bits"] = self.cpe_subnet.netmask.netmask_bits()
        params["cpe_mask"] = str(self.cpe_subnet.netmask)
        params["cpe_ups"] = str(self.cpe_subnet.network + 2)
        params["cpe_wps"] = str(self.cpe_subnet.network + 5)
        params["cpe_switch"] = str(self.cpe_subnet.network + 6)
        params["cpe_ap_low"] = str(self.cpe_subnet.network + 10)
        params["cpe_ap_high"] = str(self.cpe_subnet.network + 49)

        return params

    def generate_config(self):
        params = self.get_base_params()
        params = self.get_backhaul_params(params)
        params = self.get_cpe_params(params)
        if self.is_tarana:
            params = self.get_tarana_params(params)
        if self.is_6ghz and not self.is_tachyon:
            params = self.get_6ghz_params(params)
        if self.is_tachyon:
            params = self.get_tachyon_params(params)
        if self.is_326:
            params = self.get_326_params(params)

        template = self.jinja_env.get_template(
            DEVICE_TYPES[self.router_type]["config_template"]
        )

        config_text = template.render(params)

        return config_text

    def generate_port_map(self):
        params = self.get_base_params()
        params = self.get_backhaul_params(params)
        params = self.get_cpe_params(params)

        template = self.jinja_env.get_template(
            DEVICE_TYPES[self.router_type]["port_map_template"]
        )

        port_map_text = template.render(params)

        return port_map_text
