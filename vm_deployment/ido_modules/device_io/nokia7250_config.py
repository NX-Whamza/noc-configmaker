import os
import ipaddress
import yaml
from jinja2 import Environment, FileSystemLoader
import pprint
import argparse

def ipaddr(value, query='', version=None, alias='ipaddr'):
    if not value:
        return False
    
    try:
        if isinstance(value, str):
            try:
                network = ipaddress.ip_network(value, strict=False)
            except ValueError:
                try:
                    address = ipaddress.ip_address(value)
                    network = ipaddress.ip_network(f"{value}/32" if address.version == 4 else f"{value}/128", strict=False)
                except ValueError:
                    return False
            
            if query == 'address':
                return str(network.network_address)
            elif query == 'network':
                return str(network.network_address)
            elif query == 'netmask':
                return str(network.netmask)
            elif query == 'prefix':
                return network.prefixlen
            elif query == 'broadcast':
                return str(network.broadcast_address)
            elif query == 'host':
                return str(network.network_address)
            elif query == 'net':
                return str(network)
            elif query in ['', 'ipaddr']:
                return str(network)
            elif query == 'bool':
                return True
            else:
                try:
                    index = int(query)
                    hosts = list(network.hosts())
                    if hosts and -len(hosts) <= index < len(hosts):
                        return str(hosts[index])
                except (ValueError, IndexError):
                    pass
                return False
                
        elif isinstance(value, list):
            result = []
            for item in value:
                filtered = ipaddr(item, query, version, alias)
                if filtered:
                    result.append(filtered)
            return result
            
    except Exception:
        return False
    
    return False

def read_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)

def generate_router_config(template_file, params, output_folder, dev_type):
    dhcp_pools = {}
    dhcp_pools_list = []
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_file)))
    env.filters['ipaddr'] = ipaddr
    template = env.get_template(os.path.basename(template_file))
    
    params['dev_type'] = dev_type
    params['dhcp_pools'] = {}
    
    if 'other_ips' in params.keys():
        for other_ip in params['other_ips']:
            if other_ip['dhcp'] is True:
                print(f"Calculating DHCP pool {other_ip['pool']}")
                network = ipaddress.ip_network(other_ip['ip'], strict=False)
                hosts = list(network.hosts())
                if len(hosts) >= 2:
                    start_ip = str(hosts[1]) if len(hosts) > 2 else str(hosts[0])
                    end_ip = str(hosts[-2]) if len(hosts) > 2 else str(hosts[-1])
                else:
                    start_ip = str(hosts[0]) if hosts else str(network.network_address + 1)
                    end_ip = str(hosts[-1]) if hosts else str(network.broadcast_address - 1)
                ip_range = (f"{start_ip}-{end_ip}")
                
                if other_ip['pool'] not in dhcp_pools:
                    dhcp_pools[other_ip['pool']] = {'ranges': []}
                
                dhcp_pools[other_ip['pool']]['ranges'].append(ip_range)
        
        for name, inner_dict in dhcp_pools.items():
            temp_dict = {"name": name}
            temp_dict.update(inner_dict)
            dhcp_pools_list.append(temp_dict)
        
        params['dhcp_pools'] = dhcp_pools_list
    
    hostname = params.get('hostname') or params.get('router_name') or params.get('site_name') or 'RTR-7250'
    params['hostname'] = hostname

    print(f"Generating config for {hostname}")
    config = template.render(**params)
    
    config_filename = f"{dev_type}-{hostname}_config.rsc"
    config_path = os.path.join(output_folder, config_filename)
    
    with open(config_path, 'w') as config_file:
        config_file.write(config)
    
    print(f"Config saved to {config_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="bspeedy router config generator")
    parser.add_argument('-c',"--common_file", help='Common file')
    parser.add_argument('-i',"--input_file", help='input file')
    parser.add_argument('-t',"--template_file", help='template file')
    parser.add_argument('-o',"--output_folder", help='Output file path')
    parser.add_argument('-d',"--device_type", help='Device Type ie RTR-2004, or SWT-NP16')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    common_params = read_yaml(args.common_file)
    input_params = read_yaml(args.input_file)
    params = {**common_params, **input_params}
    
    template_file = args.template_file  
    output_folder = args.output_folder  
    
    generate_router_config(template_file, params, output_folder, args.device_type)