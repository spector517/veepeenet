from functools import wraps
from os import getuid
from pathlib import Path
from time import sleep
from typing import Callable, Any, Literal
from urllib.parse import urljoin

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typer import Exit

from app.defaults import (
    XRAY_BINARY_PATH,
    XRAY_SERVICE_UNIT_PATH,
    XRAY_ARCHIVE_NAME,
    XRAY_DOWNLOAD_URL,
    XRAY_ERROR_LOG_PATH,
    XRAY_CONFIG_PATH,
    XRAY_CONFIG_BACKUP_PATH,
    XRAY_API_HOST,
    XRAY_API_PORT,
    STATE_PENDING_TIMEOUT,
    STYLE_REGULAR,
    STYLE_VALUE,
    STYLE_WARN,
    STYLE_OK,
    EXIT_NOT_ROOT,
    EXIT_NO_CONFIG,
)
from app.model.veepeenet import VeePeeNetStats
from app.model.vless_inbound import VlessInbound
from app.model.xray import Xray
from app.utils import (
    detect_veepeenet_versions,
    get_xray_distrib_version,
    is_xray_service_running,
    stop_xray_service,
    install_xray_distrib,
    write_text_file,
    is_xray_service_installed,
    install_xray_service,
    is_xray_service_enabled,
    disable_xray_service,
    enable_xray_service,
    start_xray_service,
    restart_xray_service,
    reset_failed_xray_service,
    validate_xray_config,
    backup_config,
    restore_config,
    get_xray_service_journal,
    query_xray_stats,
)
from app.controller.data import StatsData

stdout_console = Console()
stderr_console = Console(stderr=True)

def print_error(message: str | Text) -> None:
    stderr_console.print(
        Panel(message, title='Error', title_align='left', border_style='red')
    )


def error_handler(
        default_message: str | None = None, default_code: int = -1) -> Callable[..., Any]:

    def wrapper_func(func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(func)
        def wrapper(*args: list[Any] | None, **kwargs: dict[Any, Any] | None) -> Any | None:
            try:
                return func(*args, **kwargs)
            except Exit:
                raise
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                if '_debug' in kwargs and kwargs['_debug']:
                    raise
                print_error(Text(f'{default_message or "Unknown error"}: {e}', STYLE_REGULAR))
                raise Exit(code=default_code) from e

        return wrapper

    return wrapper_func


def check_distrib(
        bin_path: Path = XRAY_BINARY_PATH,
        unit_path: Path = XRAY_SERVICE_UNIT_PATH,
        archive_name: str = XRAY_ARCHIVE_NAME,
) -> None:
    versions = detect_veepeenet_versions()
    was_stopped = False

    if not get_xray_distrib_version():
        stdout_console.print(Text('Xray distribution is not installed', STYLE_WARN))
        with stdout_console.status(Text('Installing Xray distribution', STYLE_REGULAR)):
            url = urljoin(XRAY_DOWNLOAD_URL, f'{versions.xray_version}/{archive_name}')
            install_xray_distrib(url, bin_path)
            write_text_file(XRAY_ERROR_LOG_PATH, "")
        stdout_console.print(Text.assemble(
            ('Xray distribution ', STYLE_OK),
            (versions.xray_version, STYLE_VALUE),
            (' installed', STYLE_OK)
        ))

    if not is_xray_service_installed(unit_path):
        stdout_console.print(Text('Required Xray service is not installed', STYLE_WARN))
        if is_xray_service_running():
            stop_service()
            was_stopped = True
        with stdout_console.status(Text('Installing Xray service', STYLE_REGULAR)):
            install_xray_service(unit_path)
        stdout_console.print(Text('Xray service installed', STYLE_OK))

    if was_stopped:
        start_service()


def check_root() -> None:
    if getuid() != 0:
        print_error(Text('This command must be run as root', STYLE_REGULAR))
        raise Exit(code=EXIT_NOT_ROOT)


def check_xray_config(xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    if not xray_config_path.exists():
        print_error('Xray config file not found, please run the `xrayctl config` command first')
        raise Exit(code=EXIT_NO_CONFIG)


def load_config(xray_config_path: Path) -> Xray:
    config_content = xray_config_path.read_text('utf-8')
    return Xray.model_validate_json(config_content, by_alias=True)


def save_config(config: Xray, xray_config_path: Path) -> None:
    write_text_file(
        xray_config_path,
        config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)


def get_vless_inbound(xray_config: Xray) -> VlessInbound:
    inbound = xray_config.get_vless_inbound()
    if inbound:
        return inbound
    raise ValueError('Vless inbound not found in config')


def start_service() -> None:
    if is_xray_service_running():
        stdout_console.print(Text.assemble(
            ('Xray service is ', STYLE_REGULAR),
            ('already running', STYLE_WARN)))
        return

    _test_config_or_fail()

    with stdout_console.status(Text('Starting service', STYLE_REGULAR)):
        _update_config()
        start_xray_service()
        sleep(STATE_PENDING_TIMEOUT)
        if not is_xray_service_enabled():
            enable_xray_service()
    if is_xray_service_running():
        backup_config(XRAY_CONFIG_PATH, XRAY_CONFIG_BACKUP_PATH)
        stdout_console.print(Text('Service started', STYLE_OK))
    else:
        _handle_service_failure('start', False)


def stop_service() -> None:
    if not is_xray_service_running():
        stdout_console.print(Text.assemble(
            ('Xray service is ', STYLE_REGULAR),
            ('already stopped', STYLE_WARN)))
        return
    _store_runtime_stats()
    with stdout_console.status(Text('Stopping service', STYLE_REGULAR)):
        stop_xray_service()
        sleep(STATE_PENDING_TIMEOUT)
        if is_xray_service_running():
            raise RuntimeError('Failed to stop service')
        if is_xray_service_enabled():
            disable_xray_service()
    stdout_console.print(Text('Service stopped', STYLE_WARN))


def restart_service() -> None:
    _test_config_or_fail()
    was_running = is_xray_service_running()
    _store_runtime_stats()

    with stdout_console.status(Text('Restarting service', STYLE_REGULAR)):
        _update_config()
        restart_xray_service()
        sleep(STATE_PENDING_TIMEOUT)
    if is_xray_service_running():
        if not is_xray_service_enabled():
            enable_xray_service()
        backup_config(XRAY_CONFIG_PATH, XRAY_CONFIG_BACKUP_PATH)
        stdout_console.print(Text('Service restarted', STYLE_OK))
    else:
        _handle_service_failure('restart', was_running)


def get_runtime_stats(reset: bool = False) -> VeePeeNetStats:
    veepeenet_stats = VeePeeNetStats()

    if not is_xray_service_running():
        return veepeenet_stats

    stats = query_xray_stats(XRAY_API_HOST, XRAY_API_PORT, reset=reset)
    for stat in stats:
        stats_data =  StatsData.from_api(stat)
        if stats_data:
            veepeenet_stats += stats_data.to_model()

    return veepeenet_stats


def get_stored_stats(xray_config: Xray) -> VeePeeNetStats:
    if xray_config.veepeenet:
        return xray_config.veepeenet.stats
    return VeePeeNetStats()


def _store_runtime_stats() -> None:
    if not is_xray_service_running():
        return

    config = load_config(XRAY_CONFIG_PATH)
    runtime_stats = get_runtime_stats()
    stored_stats = get_stored_stats(config)
    stored_stats += runtime_stats

    save_config(config, XRAY_CONFIG_PATH)
    get_runtime_stats(reset=True)

def _test_config_or_fail() -> None:
    success, output = validate_xray_config(XRAY_CONFIG_PATH)
    if not success:
        print_error(Text.assemble(
            ('Xray config test failed:\n', STYLE_REGULAR),
            (output, 'dim')))
        raise RuntimeError(f'Xray config test failed: {output}')

def _handle_service_failure(action: Literal['start', 'restart'], was_running: bool) -> None:
    journal = get_xray_service_journal()
    if journal:
        stderr_console.print(Panel(
            Text(journal, 'dim'),
            title='Service journal',
            title_align='left',
            border_style='red'))
    if XRAY_CONFIG_BACKUP_PATH.exists():
        restore_config(XRAY_CONFIG_PATH, XRAY_CONFIG_BACKUP_PATH)
        stderr_console.print(Text('Configuration restored from backup', STYLE_WARN))
        if was_running:
            with stdout_console.status(
                    Text('Starting service from restored config', STYLE_REGULAR)):
                reset_failed_xray_service()
                start_xray_service()
                sleep(STATE_PENDING_TIMEOUT)
            if is_xray_service_running():
                backup_config(XRAY_CONFIG_PATH, XRAY_CONFIG_BACKUP_PATH)
                stdout_console.print(Text.assemble(
                    ('Service ', STYLE_WARN),
                    ('started', STYLE_OK),
                    (' with restored configuration', STYLE_WARN)))
                return
    else:
        stderr_console.print(Text('No backup available to restore', STYLE_WARN))
    raise RuntimeError(f'Failed to {action} service')

def _update_config() -> None:
    config = load_config(XRAY_CONFIG_PATH)
    save_config(config, XRAY_CONFIG_PATH)
