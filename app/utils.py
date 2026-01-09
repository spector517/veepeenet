from io import BytesIO
from re import findall, MULTILINE, search
from subprocess import run
from sys import getdefaultencoding
from os.path import exists, dirname
from os import makedirs, chmod, remove
from importlib.resources import files
from zipfile import ZipFile

from requests import get

from app.model.xray import Xray
from app.view import VersionsView

app_resources = files('app.resources')


def is_xray_distrib_installed(version: str) -> bool:
    run_result = run_command('xray --version')
    if run_result[0] != 0:
        return False
    version = version[1:] if version.startswith('v') else version
    return version in run_result[1]


def install_xray_distrib(zip_url: str, bin_path: str) -> None:
    if exists(bin_path):
        remove(bin_path)
    bin_dir = dirname(bin_path)
    makedirs(bin_dir, exist_ok=True)
    chmod(bin_dir, 0o755)
    distrib_bytes = get(zip_url).content
    with ZipFile(BytesIO(distrib_bytes)) as zip_file:
        with zip_file.open('xray') as xray_file, open(bin_path, 'wb') as xray_out_file:
            xray_out_file.write(xray_file.read())
    chmod(bin_path, 0o744)


def is_xray_service_installed(unit_path: str) -> bool:
    if not exists(unit_path):
        return False
    expected_unit_content = app_resources.joinpath('xray.service').read_text()
    with open(unit_path, 'rt', encoding=getdefaultencoding()) as fd:
        actual_unit_content = fd.read()
    return actual_unit_content == expected_unit_content


def install_xray_service(unit_path: str) -> None:
    unit_content = app_resources.joinpath('xray.service').read_text()
    write_text_file(unit_path, unit_content, mode=0o644)
    run_command('systemctl daemon-reload', check=True)


def gen_xray_private_key() -> str:
    gen_result = run_command('xray x25519')
    if gen_result[0] != 0:
        raise RuntimeError(
            'Error generating private key.',
            f' code:{gen_result[0]}, stdout:{gen_result[1]}, stderr:{gen_result[2]}')
    private_key = findall(r'(?<=PrivateKey: ).+$', gen_result[1], MULTILINE)
    if not private_key:
        raise RuntimeError('Error generating private key. Unexpected stdout')
    return private_key[0]


def gen_xray_password(private_key: str) -> str:
    gen_result = run_command(f'xray x25519 -i {private_key}')
    if gen_result[0] != 0:
        raise RuntimeError(
            'Error generating password.',
            f' code:{gen_result[0]}, stdout:{gen_result[1]}, stderr:{gen_result[2]}')
    password = findall(r'(?<=Password: ).+$', gen_result[1], MULTILINE)
    if not password:
        raise RuntimeError('Error generating password. Unexpected stdout')
    return password[0]


def is_xray_service_running() -> bool:
    return run_command('systemctl is-active xray -q')[0] == 0


def stop_xray_service() -> None:
    run_command('systemctl stop xray -q', check=True)


def start_xray_service() -> None:
    run_command('systemctl start xray -q', check=True)


def restart_xray_service() -> None:
    run_command('systemctl restart xray -q', check=True)


def is_xray_service_enabled() -> bool:
    return run_command('systemctl is-enabled xray -q')[0] == 0


def enable_xray_service() -> None:
    run_command('systemctl enable xray -q', check=True)


def disable_xray_service() -> None:
    run_command('systemctl disable xray -q', check=True)


def get_vless_client_url(client_name: str, xray_config: Xray) -> str | None:
    for i, client in enumerate(xray_config.inbounds[0].settings.clients):
        if client_name == client.email.split('@')[0]:
            return (f'vless://{client.id}@{xray_config.inbounds[0].listen}:'
                    f'{xray_config.inbounds[0].port}'
                    '?flow=xtls-rprx-vision'
                    '&type=raw'
                    '&security=reality'
                    '&fp=chrome'
                    f'&sni={xray_config.inbounds[0].stream_settings.reality_settings.server_names[0]}'
                    f'&pbk={gen_xray_password(
                        xray_config.inbounds[0].stream_settings.reality_settings.private_key
                    )}'
                    f'&sid={xray_config.inbounds[0].stream_settings.reality_settings.short_ids[i]}'
                    f'&spx=%2F{client_name}'
                    f'#{client.email}')
    return None


def ufw_open_port(open_port: int, open_port_protocol: str, ssh_port: int) -> None:
    run_command((f'ufw allow {open_port}/{open_port_protocol}'
                 f' && ufw allow {ssh_port}/tcp'
                 ' && yes | ufw enable'
                 ' && ufw reload'))


def detect_ssh_port(sshd_config_path: str) -> int | None:
    with open(sshd_config_path, 'rt', encoding=getdefaultencoding()) as fd:
        lines = fd.readlines()
        for line in lines:
            if line.strip().startswith('#'):
                continue
            if line.strip().startswith('Port'):
                return int(line.strip().split(' ')[-1])
        return None


def detect_current_ipv4() -> str | None:
    result = run_command('hostname -i', check=False)
    matcher = search(r'(?:\d{1,3}\.){3}\d{1,3}', result[1])
    return matcher.group(0) if matcher else None


def write_text_file(file_path: str, text: str, mode: int = 0) -> None:
    content_equals = False
    if not exists(file_path):
        makedirs(dirname(file_path), exist_ok=True)
    else:
        with open(file_path, 'rt', encoding=getdefaultencoding()) as fd:
            if fd.read() == text:
                content_equals = True

    if not content_equals:
        with open(file_path, 'wt', encoding=getdefaultencoding()) as fd:
            fd.write(text)
    if mode:
        chmod(file_path, mode)


def run_command(command: str, stdin: str = '', check: bool = False, timeout: int = 20_000) \
        -> tuple[int, str, str]:
    run_result = run(
        command,
        input=stdin.encode(getdefaultencoding()),
        capture_output=True,
        check=check,
        timeout=timeout,
        shell=True
    )
    return (run_result.returncode,
            run_result.stdout.decode(getdefaultencoding()).strip(),
            run_result.stderr.decode(getdefaultencoding()).strip())


def detect_veepeenet_versions() -> VersionsView:
    content = app_resources.joinpath('versions.json').read_text(getdefaultencoding())
    return VersionsView.model_validate_json(content)
