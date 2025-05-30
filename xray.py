import argparse
import json
import os.path
import re
from typing import List
from urllib.parse import quote

import common

TMP_DIR = '/tmp/xray'
XRAY_CONF_PATH = '/usr/local/etc/xray/config.json'
XRAY_PROTOCOL = 'tcp'
SERVICE_NAME = 'xray'

DEFAULT_XRAY_PORT = 443
DEFAULT_REALITY_HOST = 'microsoft.com'
DEFAULT_REALITY_PORT = 443

common.RESULT_LOG_PATH = '/var/log/veepeenet/xray/log.json'
common.CONFIG_PATH = '/usr/local/etc/veepeenet/xray/config.json'
common.SERVER_NAME = 'Xray'


def main():
    version_info = common.get_version_info()
    arguments = parse_arguments(version_info)
    common.CHECK_MODE = arguments.check
    if arguments.clean:
        common.clean_configuration(common.CONFIG_PATH)
    config = load_config(common.CONFIG_PATH, arguments)

    if arguments.status:
        print(common.get_status(config, version_info, SERVICE_NAME,
                                get_server_version(), get_clients_strings(config)))
        return

    actualize_existing_clients(config)
    existing_clients = common.get_existing_clients(config)
    new_clients_names = common.get_new_clients_names(arguments.add_clients, existing_clients)
    for new_client_name in new_clients_names:
        new_client = generate_new_client(new_client_name, config)
        existing_clients.append(new_client)
    config['clients'] = common.get_clients_after_removing(config['clients'],
                                                          arguments.remove_clients)

    common.write_text_file(common.CONFIG_PATH, common.dump_config(config), 0o600)
    common.write_text_file(XRAY_CONF_PATH, dump_xray(config))

    if not arguments.no_ufw:
        ssh_port = common.get_ssh_port_number(common.SSHD_CONFIG_PATH)
        common.configure_ufw(config['server']['port'], ssh_port, XRAY_PROTOCOL)

    common.restart_service(SERVICE_NAME)
    common.write_text_file(common.RESULT_LOG_PATH, json.dumps(common.RESULT, indent=2))
    print(common.get_status(config, version_info, SERVICE_NAME,
                            get_server_version(), get_clients_strings(config)))


def parse_arguments(version_info: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='xray-config',
        description=(f'VeePeeNET ({version_info})'
                     f' Configure the {common.SERVER_NAME} (XTLS-Reality) server.'),
        epilog='VeePeeNET. Make the Internet free =)'
    )
    parser.add_argument(
        '--host',
        help=('The IP/DNS-name of current host. Default is Calculate automatically if not specify.'
              ' It is recommended to specify manually')
    )
    parser.add_argument(
        '--port',
        type=int,
        default=0,
        help=(f'The {common.SERVER_NAME} server port.'
              f' Default is {DEFAULT_XRAY_PORT}')
    )
    parser.add_argument(
        '--reality-host',
        help=f'The reality host for active probing. Default is {DEFAULT_REALITY_HOST}'
    )
    parser.add_argument(
        '--reality-port',
        type=int,
        default=0,
        help=f'The reality port for active probing. Default is {DEFAULT_REALITY_PORT}'
    )
    parser.add_argument(
        '--add-clients',
        nargs='+',
        default=[],
        metavar='CLIENT',
        help=(f'List of {common.SERVER_NAME} server clients names.'
               'Default - no generate clients configs.')
    )
    parser.add_argument(
        '--remove-clients',
        nargs='+',
        default=[],
        metavar='CLIENT',
        help=(f'Removing clients list of {common.SERVER_NAME} server.'
              ' Non-existing clients names will be ignored.')
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
        help='Dry run. Print changed files content to the console'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help=f'Show {common.SERVER_NAME} server information'
    )
    return parser.parse_args()


@common.handle_result
def load_config(
        config_path: str, arguments: argparse.Namespace) -> dict:
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'rt', encoding=common.ENCODING) as fd:
            config.update(json.loads(fd.read()))
    server_private_key = common.get_config_value(config, 'private_key', 'server')
    server_public_key = common.get_config_value(config, 'public_key', 'server')
    if not server_public_key or not server_private_key:
        server_private_key, server_public_key = generate_server_keys()
    config.update({
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
                or DEFAULT_XRAY_PORT,
            'reality_host':
                arguments.reality_host
                or common.get_config_value(config, 'reality_host', 'server')
                or DEFAULT_REALITY_HOST,
            'reality_port':
                int(arguments.reality_port)
                or common.get_config_value(config, 'reality_port', 'server')
                or DEFAULT_REALITY_PORT,
            'private_key': server_private_key,
            'public_key': server_public_key
        },
        'clients':
            (config['clients'] if 'clients' in config and config['clients']
             else common.DEFAULT_CLIENTS)
    })
    return config


@common.handle_result
def get_server_version() -> str:
    stdout = common.run_command('xray --version')[1]
    found_version = re.findall(r'(?<=Xray\s)[\d.]+', stdout)
    return found_version[0] if found_version else 'unknown'


@common.handle_result
def get_clients_strings(config: dict) -> List[str]:
    return [dump_client(client) for client in config['clients']]


@common.handle_result
def generate_server_keys() -> tuple:
    if common.CHECK_MODE:
        return '', ''
    command_result = common.run_command('xray x25519')
    if command_result[0] != 0:
        raise RuntimeError(f'Keys generation error. Code {command_result[0]}')
    keys = re.findall(r'(?<=\skey:\s).+$', command_result[1], re.MULTILINE)
    if len(keys) != 2:
        raise RuntimeError(f'Keys generation error. Keys not found. Stdout: {command_result[1]}')
    return keys[0], keys[1]


@common.handle_result
def actualize_existing_clients(config: dict) -> None:
    for i, client in enumerate(config['clients']):
        config['clients'][i] = get_client_config(
            client['name'], client['uuid'], client['short_id'], config['server'])


@common.handle_result
def generate_new_client(new_client_name: str, config: dict) -> dict:
    existing_numbers = [int(client['short_id']) for client in config['clients']]
    short_id = f'{common.generate_unique_number(range(1, 100), existing_numbers):04}'
    uuid = common.generate_uuid()
    return get_client_config(new_client_name, uuid, short_id, config['server'])


def get_client_config(name: str, uuid: str, short_id: str, server_config: dict) -> dict:
    return {
        'name': name,
        'uuid': uuid,
        'short_id': short_id,
        'email': f"{name}@{server_config['host']}",
        'import_url': (f"vless://{uuid}@{server_config['host']}:{server_config['port']}"
                       '?flow=xtls-rprx-vision'
                       '&type=raw'
                       '&security=reality'
                       '&fp=chrome'
                       f"&sni={server_config['reality_host']}"
                       f"&pbk={server_config['public_key']}"
                       f'&sid={short_id}'
                       f"&spx={quote('/' + name, safe='')}"
                       f"#{name}@{server_config['host']}")
    }

@common.handle_result
def dump_xray(config: dict) -> str:
    clients = [{'id': client['uuid'], 'email': client['email'], 'flow': 'xtls-rprx-vision'}
               for client in config['clients']]
    xray_config = {
        'inbounds': [
            {
                'port': config['server']['port'],
                'protocol': 'vless',
                'tag': 'vless-inbound',
                'settings': {
                    'clients': clients,
                    'decryption': 'none'
                },
                'streamSettings': {
                    'network': 'raw',
                    'security': 'reality',
                    'realitySettings': {
                        'dest': f"{config['server']['reality_host']}:{config['server']['port']}",
                        'serverNames': [config['server']['reality_host']],
                        'privateKey': config['server']['private_key'],
                        'shortIds': [client['short_id'] for client in config['clients']]
                    }
                }
            }
        ],
        'outbounds': [
            {
                'protocol': 'freedom',
                'tag': 'direct-outbound'
            }
        ]
    }
    return json.dumps(xray_config, indent=2)


@common.handle_result
def dump_client(client: dict) -> str:
    return f"{client['name']}: {client['import_url']}"


if __name__ == '__main__':
    main()
