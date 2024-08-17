import argparse
import json
import os
import textwrap
from typing import List

import common

WIREGUARD_CONF_DIR = '/etc/wireguard'
WIREGUARD_PROTOCOL = 'udp'
SERVER_NAME = 'WireGuard'

DEFAULT_WIREGUARD_PORT = 51820
DEFAULT_WIREGUARD_INTERFACE = 'wg0'
DEFAULT_WIREGUARD_SUBNET = '10.9.0.1/24'

common.RESULT_LOG_PATH = '/var/log/veepeenet/wg/result.json'
common.CONFIG_PATH = '/usr/local/etc/veepeenet/wg/config.json'
common.DEFAULT_CLIENTS_DIR = '/usr/local/etc/veepeenet/wg/clients'


def main():
    version_info = common.get_version_info()
    arguments = parse_arguments(version_info)
    common.CHECK_MODE = arguments.check
    if arguments.clean:
        common.clean_configuration(common.CONFIG_PATH, common.DEFAULT_CLIENTS_DIR)
    config = load_config(common.CONFIG_PATH, arguments)
    service_name = f"wg-quick@{config['server']['interface']}"

    if arguments.status:
        print(common.get_status(config, version_info, service_name,
                                SERVER_NAME, get_clients_strings(config)))
        return

    existing_clients = common.get_existing_clients(config)
    new_clients_names = common.get_new_clients_names(arguments.add_clients, existing_clients)
    subnet = config['server']['subnet']
    for new_client_name in new_clients_names:
        new_client = generate_new_client(new_client_name, existing_clients, subnet)
        existing_clients.append(new_client)
    config['clients'] = common.get_clients_after_removing(config['clients'],
                                                          arguments.remove_clients)

    common.write_text_file(common.CONFIG_PATH, common.dump_config(config), 0o600)
    server_dump = dump_server(config)
    common.write_text_file(
        os.path.join(WIREGUARD_CONF_DIR, f"{config['server']['interface']}.conf"),
        server_dump
    )
    for client_name, client_conf in dump_clients(config).items():
        common.write_text_file(os.path.join(config['clients_dir'], f'{client_name}.conf'),
                               client_conf, 0o600)
    remove_clients_configs(arguments.remove_clients, config['clients_dir'])

    edit_sysctl(common.SYSCTL_FILE_PATH)
    apply_sysctl_conf()
    if not arguments.no_ufw:
        default_interface = common.get_default_interface(common.ROUTE_FILE_PATH)
        subnet = get_server_subnet(subnet)
        edit_ufw_rule_before(common.UFW_BEFORE_RULES_PATH, default_interface, subnet)
        edit_ufw_forward_policy(common.FORWARD_POLICY_FILE)
        ssh_port = common.get_ssh_port_number(common.SSHD_CONFIG_PATH)
        common.configure_ufw(config['server']['port'], ssh_port, WIREGUARD_PROTOCOL)

    common.restart_service(service_name)
    common.enable_service(service_name)
    common.write_text_file(common.RESULT_LOG_PATH, json.dumps(common.RESULT, indent=2))
    print(common.get_status(config, version_info, service_name,
                            SERVER_NAME, get_clients_strings(config)))


@common.handle_result
def parse_arguments(version_info: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='wg-config',
        description=f'VeePeeNET ({version_info}). Configure the {SERVER_NAME} VPN.',
        epilog='VeePeeNET. Make the Internet free =)'
    )
    parser.add_argument(
        '--host',
        help='The IP/DNS-name of current host. Calculate automatically if not specify.'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=0,
        help=f'The VPN service port. Default is {DEFAULT_WIREGUARD_PORT}'
    )
    parser.add_argument(
        '--subnet',
        help=f'{SERVER_NAME} server subnet address. Default is {DEFAULT_WIREGUARD_SUBNET}.'
    )
    parser.add_argument(
        '--interface',
        help=(f'Name of {SERVER_NAME} virtual network interface. '
              f'Default is {DEFAULT_WIREGUARD_INTERFACE}.')
    )
    parser.add_argument(
        '--dns',
        nargs='+',
        help=f'Domain names servers. Default is {" ".join(common.DEFAULT_DNS)}.'
    )
    parser.add_argument(
        '--add-clients',
        nargs='+',
        default=[],
        metavar='CLIENT',
        help=f'List of {SERVER_NAME} server clients names. Default - no generate clients configs.'
    )
    parser.add_argument(
        '--remove-clients',
        nargs='+',
        default=[],
        metavar='CLIENT',
        help=(f'Removing clients list of {SERVER_NAME} server.'
              ' Non-existing clients names will be ignored.')
    )
    parser.add_argument(
        '--output',
        metavar='CLIENTS_CONF_DIR',
        help=f'Path to output clients configs directory. Default is {common.DEFAULT_CLIENTS_DIR}'
    )
    parser.add_argument(
        '--no-ufw',
        action='store_true',
        help='Do not use the Uncomplicated Firewall'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Remove existing config. Default is False'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        default=False,
        help='Dry run. Print changed files content to the console'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help=f'Show {SERVER_NAME} server information'
    )
    return parser.parse_args()


@common.handle_result
def load_config(
        config_path: str, arguments: argparse.Namespace) -> dict:
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'rt', encoding=common.ENCODING) as fd:
            config.update(json.loads(fd.read()))
    server_private_key = (common.get_config_value(config, 'private_key', 'server')
                          or generate_private_key())
    server_public_key = (common.get_config_value(config, 'public_key', 'server')
                         or generate_public_key(server_private_key))
    config.update({
        'clients_dir':
            arguments.output
            or common.get_config_value(config, 'clients_dir')
            or common.DEFAULT_CLIENTS_DIR,
        'no_ufw':
            arguments.no_ufw
            or common.get_config_value(config, 'no_ufw')
            or common.DEFAULT_NO_UFW,
        'server': {
            'host':
                arguments.host
                or common.get_config_value(config, 'host', 'server')
                or common.get_current_host_ip(),
            'port':
                int(arguments.port)
                or common.get_config_value(config, 'port', 'server')
                or DEFAULT_WIREGUARD_PORT,
            'subnet':
                arguments.subnet
                or common.get_config_value(config, 'subnet', 'server')
                or DEFAULT_WIREGUARD_SUBNET,
            'interface':
                arguments.interface
                or common.get_config_value(config, 'interface', 'server')
                or DEFAULT_WIREGUARD_INTERFACE,
            'dns':
                arguments.dns
                or common.get_config_value(config, 'dns', 'server')
                or common.DEFAULT_DNS,
            'private_key': server_private_key,
            'public_key': server_public_key
        },
        'clients':
            (config['clients'] if 'clients' in config and config['clients']
             else common.DEFAULT_CLIENTS)
    })
    return config


@common.handle_result
def get_clients_strings(config: dict) -> List[str]:
    return [f"{client['name']}: {config['clients_dir']}/{client['name']}.conf"
            for client in config['clients']]


@common.handle_result
def generate_new_client(client_name: str, existing_clients: list, subnet: str) -> dict:
    existing_clients_ips = [existing_client['ip'] for existing_client in existing_clients]
    sub_ip = [int(ip.split('.')[-1]) for ip in existing_clients_ips]
    unique_number = common.generate_unique_number(range(2, 255), sub_ip)
    ip = '.'.join(subnet.split('.')[0:-1]) + f'.{unique_number}'
    private_key = generate_private_key()
    public_key = generate_public_key(private_key)
    return {
        'name': client_name,
        'ip': ip,
        'public_key': public_key,
        'private_key': private_key
    }


@common.handle_result
def edit_sysctl(sysctl_file_path: str, ip_version: int = 4) -> None:
    with open(sysctl_file_path, 'rt+', encoding=common.ENCODING) as fd:
        target_line = f'net.ipv{ip_version}.ip_forward = 1\n'
        lines = fd.readlines()
        if target_line in lines:
            return
        lines.append(target_line)
        fd.seek(0)
        if common.CHECK_MODE:
            print(f'{sysctl_file_path}:\n{"".join(lines)}\n')
            return
        fd.writelines(lines)


@common.handle_result
def dump_server(config: dict) -> str:
    dump = textwrap.dedent(f'''
        [Interface]
        Address = {config['server']['subnet']}
        PrivateKey = {config['server']['private_key']}
        ListenPort = {config['server']['port']}
    ''')
    for client in config['clients']:
        dump += textwrap.dedent(f'''
            [Peer]
            AllowedIPs = {client['ip']}/32
            PublicKey = {client['public_key']}
        ''')
    return dump.lstrip()


@common.handle_result
def dump_clients(config: dict) -> dict:
    clients_dumps = {}
    for client in config['clients']:
        clients_dumps.update({client['name']: textwrap.dedent(f'''
            [Interface]
            Address = {client['ip']}
            PrivateKey = {client['private_key']}
            DNS = {', '.join(config['server']['dns'])}

            [Peer]
            Endpoint = {config['server']['host']}:{config['server']['port']}
            AllowedIPs = 0.0.0.0/0
            PublicKey = {config['server']['public_key']}
        ''').lstrip()})
    return clients_dumps


@common.handle_result
def remove_clients_configs(clients_names: list, clients_dir_path: str) -> None:
    if not os.path.exists(clients_dir_path):
        return
    for client_name in clients_names:
        client_conf_path = os.path.join(clients_dir_path, f'{client_name}.conf')
        if os.path.exists(client_conf_path):
            os.remove(client_conf_path)


@common.handle_result
def get_server_subnet(subnet: str) -> str:
    return f"{'.'.join(subnet.split('.')[0:2])}.0.0/8"


@common.handle_result
def edit_ufw_rule_before(rules_file_path: str, interface: str, subnet: str) -> None:
    rule_header = '# BEGIN VEEPEENET WG VPN UFW RULES #\n'
    rule_footer = '# END VEEPEENET WG VPN UFW RULES #\n'
    rule_lines = [
        rule_header,
        '*nat\n',
        ':POSTROUTING ACCEPT [0:0]\n',
        f'-A POSTROUTING -s {subnet} -o {interface} -j MASQUERADE\n',
        'COMMIT\n',
        rule_footer
    ]
    with open(rules_file_path, 'rt+', encoding=common.ENCODING) as fd:
        rules_lines = fd.readlines()
        try:
            del rules_lines[rules_lines.index(rule_header):rules_lines.index(rule_footer) + 1]
        except ValueError:
            pass
        fd.seek(0)
        result_lines = rule_lines + rules_lines
        if common.CHECK_MODE:
            print(f'{rules_file_path}:\n{"".join(result_lines)}\n')
            return
        fd.writelines(result_lines)


@common.handle_result
def edit_ufw_forward_policy(policy_file_path: str) -> None:
    with open(policy_file_path, 'rt+', encoding=common.ENCODING) as fd:
        target_line = 'DEFAULT_FORWARD_POLICY="ACCEPT"\n'
        lines = fd.readlines()
        if target_line in lines:
            return
        for index, line in enumerate(lines):
            if line.startswith('DEFAULT_FORWARD_POLICY='):
                lines[index] = target_line
                fd.seek(0)
                if common.CHECK_MODE:
                    print(f'{policy_file_path}:\n{"".join(lines)}\n')
                    return
                fd.writelines(lines)
                break


@common.handle_result
def apply_sysctl_conf() -> None:
    common.run_command('sysctl -p')


@common.handle_result
def generate_public_key(private_key: str) -> str:
    return common.run_command('wg pubkey', private_key)[1]


@common.handle_result
def generate_private_key() -> str:
    return common.run_command('wg genkey')[1]


if __name__ == '__main__':
    main()
