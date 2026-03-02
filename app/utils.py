from importlib.resources import files
from pathlib import Path
from re import findall, MULTILINE, search, fullmatch
from subprocess import run
from tempfile import NamedTemporaryFile
from typing import Literal, TypeVar
from urllib.parse import quote_plus as safe_url_encode
from zipfile import ZipFile

from requests import get as get_request

from app.model.xray import Xray
from app.view import VersionsView

_T = TypeVar('_T')

_CHUNK_SIZE = 1024 * 1024  # 1 MB

app_resources = files('app.resources')


def is_xray_distrib_installed(version: str) -> bool:
    run_result = run_command('xray --version')
    if run_result[0] != 0:
        return False
    version = version[1:] if version.startswith('v') else version
    return version in run_result[1]


def install_xray_distrib(zip_url: str, bin_path: Path) -> None:
    bin_path.parent.mkdir(parents=True, mode=0o755, exist_ok=True)

    with NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
        tmp_zip_path = Path(tmp_zip.name)

    try:
        with get_request(zip_url, timeout=20, stream=True) as response:
            with open(tmp_zip_path, 'wb') as tmp_zip_file:
                for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                    tmp_zip_file.write(chunk)

        with ZipFile(tmp_zip_path) as zip_file:
            with zip_file.open('xray') as xray_file:
                with open(bin_path, 'wb') as out_file:
                    for chunk in iter(lambda: xray_file.read(_CHUNK_SIZE), b''):
                        out_file.write(chunk)
    finally:
        tmp_zip_path.unlink(missing_ok=True)

    bin_path.chmod(0o744)


def install_geo_data(geo_data_url: str, geo_data_path: Path) -> None:
    geo_data_path.parent.mkdir(parents=True, mode=0o755, exist_ok=True)

    with get_request(geo_data_url, timeout=20, stream=True) as response:
        with open(geo_data_path, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                out_file.write(chunk)

    geo_data_path.chmod(0o644)


def is_xray_service_installed(unit_path: Path) -> bool:
    try:
        actual_unit_content = unit_path.read_text(encoding='utf-8')
        expected_unit_content = app_resources.joinpath('xray.service').read_text()
        return expected_unit_content == actual_unit_content
    except FileNotFoundError:
        return False


def install_xray_service(unit_path: Path) -> None:
    unit_content = app_resources.joinpath('xray.service').read_text()
    write_text_file(unit_path, unit_content, mode=0o644)
    run_command('systemctl daemon-reload', check=True)


def gen_xray_private_key() -> str:
    gen_result = run_command('xray x25519')
    if gen_result[0] != 0:
        raise RuntimeError(
            f'Error generating private key.'
            f' code:{gen_result[0]}, stdout:{gen_result[1]}, stderr:{gen_result[2]}')
    private_key = findall(r'(?<=PrivateKey: ).+$', gen_result[1], MULTILINE)
    if not private_key:
        raise RuntimeError('Error generating private key. Unexpected stdout')
    return private_key[0]


def gen_xray_password(private_key: str) -> str:
    gen_result = run_command(f'xray x25519 -i {private_key}')
    if gen_result[0] != 0:
        raise RuntimeError(
            f'Error generating password.'
            f' code:{gen_result[0]}, stdout:{gen_result[1]}, stderr:{gen_result[2]}')
    password = findall(r'(?<=Password: ).+$', gen_result[1], MULTILINE)
    if not password:
        raise RuntimeError('Error generating password. Unexpected stdout')
    return password[0]


def is_xray_service_running() -> bool:
    return run_command('systemctl is-active xray -q')[0] == 0


def get_xray_service_uptime() -> str | None:
    result = run_command('systemctl status xray --no-pager -l')
    matched = search(r'Active:.*?;\s*(.+?)(?:\s+ago)?\s*$', result[1], MULTILINE)
    return (matched.group(1).strip()) if matched else None


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
        if client_name == '.'.join(client.email.split('@')[0].split('.')[:-1]):
            sni = xray_config.inbounds[0].stream_settings.reality_settings.server_names[0]
            password = gen_xray_password(
                xray_config.inbounds[0].stream_settings.reality_settings.private_key)
            spx = safe_url_encode(f'/{client_name}')
            return (f'vless://{client.id}@{xray_config.inbounds[0].listen}:'
                    f'{xray_config.inbounds[0].port}'
                    '?flow=xtls-rprx-vision'
                    '&type=raw'
                    '&security=reality'
                    '&fp=chrome'
                    f'&sni={sni}'
                    f'&pbk={password}'
                    f'&sid={xray_config.inbounds[0].stream_settings.reality_settings.short_ids[i]}'
                    f'&spx={spx}'
                    f'#{client_name}@{client.email.split('@')[-1]}')
    return None


def is_valid_vless_client_url(url: str) -> bool:
    return fullmatch(
        r'vless://[a-f0-9-]{36}@[\w.-]+:\d{1,5}'
        r'\?flow=xtls-rprx-vision&type=raw&security=reality&fp=[^&]+'
        r'&sni=[^&]+&pbk=[^&]{43}=?(?:&sid=[0-9a-f]{0,16})?'
        r'&spx=[^&]+#[^&]+', url) is not None


def ufw_open_port(
        open_port: int, open_port_protocol: Literal['tcp', 'udp'], ssh_port: int) -> None:
    run_command((f'ufw allow {open_port}/{open_port_protocol}'
                 f' && ufw allow {ssh_port}/tcp'
                 ' && yes | ufw enable'
                 ' && ufw reload'))


def detect_ssh_port(sshd_config_path: Path) -> int | None:
    for line in sshd_config_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith('Port'):
            return int(stripped.split(' ')[-1])
    return None


def detect_current_ipv4() -> str | None:
    result = run_command('hostname -i', check=False)
    matcher = search(r'(?:\d{1,3}\.){3}\d{1,3}', result[1])
    return matcher.group(0) if matcher else None


def write_text_file(file_path: Path, text: str, mode: int = 0) -> None:
    try:
        content = file_path.read_text(encoding='utf-8')
        if content != text:
            file_path.write_text(text, encoding='utf-8')
    except FileNotFoundError:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding='utf-8')
    if mode:
        file_path.chmod(mode)


def remove_duplicates(source: list[_T]) -> list[_T]:
    return list(dict.fromkeys(source))


def get_new_items(old: list[_T], new: list[_T]) -> list[_T]:
    return [item for item in new if item not in old]


def get_existing_items(old: list[_T], new: list[_T]) -> list[_T]:
    return [item for item in new if item in old]


def get_short_id(existing_short_ids: list[int], interval: range = range(1, 10000)) -> int:
    for i in interval:
        if i not in existing_short_ids:
            return i
    raise ValueError(f'No available short ID found in the given interval {interval}')


def set_value(obj: object, attr: str, value: object) -> bool:
    if hasattr(obj, attr):
        if getattr(obj, attr) != value and value is not None:
            setattr(obj, attr, value)
            return True
        return False
    raise AttributeError(f'Object {obj} has no attribute {attr}')


def run_command(command: str, stdin: str = '', check: bool = False, timeout: int = 20) \
        -> tuple[int, str, str]:
    run_result = run(
        command,
        input=stdin.encode('utf-8'),
        capture_output=True,
        check=check,
        timeout=timeout,
        shell=True
    )
    return (run_result.returncode,
            run_result.stdout.decode('utf-8').strip(),
            run_result.stderr.decode('utf-8').strip())


def detect_veepeenet_versions() -> VersionsView:
    content = app_resources.joinpath('versions.json').read_text('utf-8')
    return VersionsView.model_validate_json(content)
