import argparse
import json
import os.path
import re
import urllib.request
import subprocess

import common

XRAY_VERSION = '1.8.8'
TMP_DIR = '/tmp/xray'
XRAY_INSTALLER_SCRIPT_URL = 'https://github.com/XTLS/Xray-install/raw/main/install-release.sh'
XRAY_CONF_PATH = '/usr/local/etc/xray/config.json'
XRAY_PROTOCOL = 'tcp'

DEFAULT_XRAY_PORT = 443
DEFAULT_REALITY_HOST = 'microsoft.com'
DEFAULT_REALITY_PORT = 443

common.RESULT_LOG_PATH = os.path.expanduser('~/.veepeenet/xray/result.json')
common.CONFIG_PATH = os.path.expanduser('~/.veepeenet/xray/config.json')


def main():
    arguments = parse_arguments()
    common.CHECK_MODE = arguments.check
    if arguments.clean:
        common.clean_configuration(common.CONFIG_PATH)
    if not is_xray_installed(XRAY_VERSION):
        install_xray(XRAY_VERSION)
    config = load_config(common.CONFIG_PATH, arguments)

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

    common.restart_service('xray')
    common.write_text_file(common.RESULT_LOG_PATH, json.dumps(common.RESULT, indent=2))
    for client in config['clients']:
        print(dump_client(client))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Configure the XRAY (XTLS-Reality) server',
        epilog='VeePeeNet. Make the Internet free =)'
    )
    parser.add_argument(
        '--host',
        help='The IP/DNS-name of current host. Default is Calculate automatically if not specify.'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=0,
        help=f'The VPN service port. Default is {DEFAULT_XRAY_PORT}'
    )
    parser.add_argument(
        '--reality-host',
        help=f'The IP/DNS-name of current host. Default is {DEFAULT_REALITY_HOST}'
    )
    parser.add_argument(
        '--reality-port',
        type=int,
        default=0,
        help=f'The VPN service port. Default is {DEFAULT_REALITY_PORT}'
    )
    parser.add_argument(
        '--add-clients',
        nargs='+',
        default=[],
        metavar='CLIENT',
        help='List of Wireguard server clients names. Default - no generate clients configs.'
    )
    parser.add_argument(
        '--remove-clients',
        nargs='+',
        default=[],
        metavar='CLIENT',
        help=('Removing clients list of XRAY server.'
              ' Non-existing clients names will be ignored.')
    )
    parser.add_argument(
        '--no-ufw',
        action='store_true',
        help='Do not use the Uncomplicated Firefall'
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
    return parser.parse_args()


@common.handle_result
def is_xray_installed(xray_version: str) -> bool:
    try:
        res = common.run_command('xray --version')
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    found_versions = re.findall(r'(?<=Xray\s)[0-9.]+', res[1])
    return found_versions[0] == xray_version if found_versions else False


@common.handle_result
def install_xray(xray_version: str, tmp_dir: str = TMP_DIR) -> None:
    response = urllib.request.urlopen(XRAY_INSTALLER_SCRIPT_URL,
                                      timeout=common.RUN_COMMAND_TIMEOUT)
    if response.getcode() != 200:
        raise RuntimeError(f'Invalid  http-code ({response.getcode()})')
    script = response.read().decode(common.ENCODING)
    script_path = os.path.join(tmp_dir, 'install-release.sh')

    common.write_text_file(script_path, script, 0o700)
    try:
        common.run_command(f'{script_path} install --version {xray_version}')
    except(subprocess.CalledProcessError, subprocess.TimeoutExpired) as ex:
        raise RuntimeError(f'Installation error: {ex}')


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
def generate_new_client(new_client_name: str, config: dict) -> dict:
    existing_numbers = [int(client['short_id']) for client in config['clients']]
    short_id = f'{common.generate_unique_number(range(1, 100), existing_numbers):04}'
    uuid = common.generate_uuid()
    host = config['server']['host']
    port = config['server']['port']
    reality_host = config['server']['reality_host']
    public_key = config['server']['public_key']
    return {
        'name': new_client_name,
        'uuid': uuid,
        'short_id': short_id,
        'email': f'{new_client_name}@{host}',
        'import_url': (f'vless://{uuid}@{host}:{port}'
                       '?flow=xtls-rprx-vision'
                       '&type=tcp'
                       '&security=reality'
                       '&fp=chrome'
                       f'&sni={reality_host}'
                       f'&pbk={public_key}'
                       f'&sid={short_id}'
                       f'&spx=%2F#{new_client_name}@{host}')
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
                'tag': 'vless_tls',
                'settings': {
                    'clients': clients,
                    'decryption': 'none'
                },
                'streamSettings': {
                    'network': 'tcp',
                    'security': 'reality',
                    'realitySettings': {
                        'show': False,
                        'dest': f"{config['server']['reality_host']}:{config['server']['port']}",
                        'xver': 0,
                        'serverNames': [config['server']['reality_host']],
                        'privateKey': config['server']['private_key'],
                        'minClientVer': '',
                        'maxClientVer': '',
                        'maxTimeDiff': 0,
                        'shortIds': [client['short_id'] for client in config['clients']]
                    }
                },
                'sniffing': {
                    'enabled': True,
                    'destOverride': ['http', 'tls', 'quic']
                }
            }
        ],
        'outbounds': [
            {
                'protocol': 'freedom',
                'tag': 'direct'
            }
        ]
    }
    return json.dumps(xray_config, indent=2)


@common.handle_result
def dump_client(client: dict) -> str:
    return f"{client['name']}: {client['import_url']}"


if __name__ == '__main__':
    main()
