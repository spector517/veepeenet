# pylint: disable=too-many-lines
from io import BytesIO
from pathlib import Path
from time import sleep
from unittest.mock import MagicMock
from zipfile import ZipFile

import pytest
from pytest_mock import MockFixture

from app.model.xray import Xray
from app.utils import (
    gen_xray_private_key,
    gen_xray_password,
    is_xray_service_running,
    get_xray_service_uptime,
    restart_xray_service,
    enable_xray_service,
    disable_xray_service,
    get_vless_client_url,
    is_valid_vless_client_url,
    ufw_open_port,
    detect_ssh_port,
    detect_current_ipv4,
    write_text_file,
    is_xray_distrib_installed,
    install_xray_distrib,
    install_geo_data,
    is_xray_service_installed,
    install_xray_service,
    stop_xray_service,
    start_xray_service,
    run_command,
    detect_veepeenet_versions,
    is_xray_service_enabled,
    remove_duplicates,
    get_new_items,
    get_existing_items,
    set_value,
)


@pytest.fixture(name='valid_xray_config_with_clients_path')
def fixture_valid_xray_config_with_clients_path() -> Path:
    return Path('tests/resources/valid_xray_config_with_clients.json')


def _make_xray_zip(xray_binary: bytes) -> bytes:
    buf = BytesIO()
    with ZipFile(buf, mode='w') as zf:
        zf.writestr('xray', xray_binary)
    return buf.getvalue()


def _make_streaming_mock(data: bytes, chunk_size: int = 1024 * 1024) -> MagicMock:
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)] or [b'']
    mock_response = MagicMock()
    mock_response.iter_content.return_value = iter(chunks)
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestGenXrayPrivateKey:

    def test_gen_xray_private_key_success(self, mocker):
        expected_key = 'aAbBcCdDeEfF123456789gGhHiIjJkKlL=='
        mock_run_command = mocker.patch(
            'app.utils.run_command', return_value=(0, f'PrivateKey: {expected_key}', ''))

        result = gen_xray_private_key()

        assert result == expected_key
        mock_run_command.assert_called_once_with('xray x25519')

    def test_gen_xray_private_key_command_failure(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(1, '', 'Error message'))

        with pytest.raises(RuntimeError, match='Error generating private key') as exc_info:
            gen_xray_private_key()

        error_text = str(exc_info.value)
        assert 'code:1' in error_text
        assert 'Error message' in error_text

    def test_gen_xray_private_key_unexpected_output(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(0, 'Unexpected output', ''))

        with pytest.raises(RuntimeError) as exc_info:
            gen_xray_private_key()

        assert 'Unexpected stdout' in str(exc_info.value)


class TestGenXrayPassword:

    def test_gen_xray_password_success(self, mocker):
        private_key = 'aAbBcCdDeEfF123456789gGhHiIjJkKlL=='
        expected_pass = 'xXyYzZ987654321aBcDeFgHiJkLmNoOpP=='
        mock_run_command = mocker.patch(
            'app.utils.run_command', return_value=(0, f'Password: {expected_pass}', ''))

        result = gen_xray_password(private_key)

        assert result == expected_pass
        mock_run_command.assert_called_once_with(f'xray x25519 -i {private_key}')

    def test_gen_xray_password_command_failure(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(1, '', 'Error message'))

        with pytest.raises(RuntimeError, match='Error generating password') as exc_info:
            gen_xray_password('test_key')

        error_text = str(exc_info.value)
        assert 'Error message' in error_text

    def test_gen_xray_password_unexpected_output(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(0, 'Unexpected output', ''))

        with pytest.raises(RuntimeError) as exc_info:
            gen_xray_password('test_key')

        assert 'Unexpected stdout' in str(exc_info.value)


class TestIsXrayRunning:

    def test_is_xray_running_true(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        result = is_xray_service_running()

        assert result is True
        mock_run_command.assert_called_once_with('systemctl is-active xray -q')

    def test_is_xray_running_false(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(1, '', ''))

        result = is_xray_service_running()

        assert result is False


class TestGetXrayServiceUptime:

    _STATUS_TEMPLATE = (
        '● xray.service - Xray Service\n'
        '     Loaded: loaded (/etc/systemd/system/xray.service; enabled)\n'
        '     Active: active (running) since Mon 2026-03-02 10:00:00 UTC; {uptime} ago\n'
        '   Main PID: 1234 (xray)\n'
    )

    def test_returns_uptime_hours_minutes(self, mocker):
        stdout = self._STATUS_TEMPLATE.format(uptime='2h 30min')
        mocker.patch('app.utils.run_command', return_value=(0, stdout, ''))

        result = get_xray_service_uptime()

        assert result == '2h 30min'

    def test_returns_uptime_days(self, mocker):
        stdout = self._STATUS_TEMPLATE.format(uptime='3 days 4h 5min')
        mocker.patch('app.utils.run_command', return_value=(0, stdout, ''))

        result = get_xray_service_uptime()

        assert result == '3 days 4h 5min'

    def test_returns_uptime_seconds(self, mocker):
        stdout = self._STATUS_TEMPLATE.format(uptime='45s')
        mocker.patch('app.utils.run_command', return_value=(0, stdout, ''))

        result = get_xray_service_uptime()

        assert result == '45s'

    def test_returns_none_when_active_line_missing(self, mocker):
        stdout = (
            '● xray.service - Xray Service\n'
            '     Loaded: loaded (/etc/systemd/system/xray.service; enabled)\n'
            '     Active: inactive (dead)\n'
        )
        mocker.patch('app.utils.run_command', return_value=(0, stdout, ''))

        result = get_xray_service_uptime()

        assert result is None

    def test_returns_none_when_stdout_empty(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(1, '', ''))

        result = get_xray_service_uptime()

        assert result is None

    def test_calls_correct_command(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        get_xray_service_uptime()

        mock_run_command.assert_called_once_with('systemctl status xray --no-pager -l')


class TestRestartXrayService:

    def test_restart_xray_service_success(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        restart_xray_service()

        mock_run_command.assert_called_once_with('systemctl restart xray -q', check=True)


class TestIsXrayServiceEnabled:

    def test_is_xray_service_enabled_true(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        result = is_xray_service_enabled()

        assert result is True
        mock_run_command.assert_called_once_with('systemctl is-enabled xray -q')

    def test_is_xray_service_enabled_false(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(1, '', ''))

        result = is_xray_service_enabled()

        assert result is False


class TestEnableXrayService:

    def test_enable_xray_service_success(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        enable_xray_service()

        mock_run_command.assert_called_once_with('systemctl enable xray -q', check=True)


class TestDisableXrayService:

    def test_disable_xray_service_success(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        disable_xray_service()

        mock_run_command.assert_called_once_with('systemctl disable xray -q', check=True)


class TestGetVlessClientUrl:

    def test_get_vless_client_url_success(
            self, mocker: MockFixture, valid_xray_config_with_clients_path: Path):
        mocker.patch('app.utils.gen_xray_password', return_value='random-password-1')
        expected_client_url = (
            'vless://random-uuid-1@0.0.0.0:443?flow=xtls-rprx-vision'
            '&type=raw'
            '&security=reality'
            '&fp=chrome'
            '&sni=yahoo.com'
            '&pbk=random-password-1'
            '&sid=0001'
            '&spx=%2Fc1.client'
            '#c1.client@0.0.0.0'
        )
        xray_config_content = valid_xray_config_with_clients_path.read_text(
            encoding='utf-8')

        actual_url = get_vless_client_url(
            'c1.client', Xray.model_validate_json(xray_config_content))

        assert actual_url == expected_client_url

    def test_get_vless_client_url_not_found(self, valid_xray_config_with_clients_path: Path):
        xray_config_content = valid_xray_config_with_clients_path.read_text(
            encoding='utf-8')

        actual_url = get_vless_client_url(
            'nonexistent_client', Xray.model_validate_json(xray_config_content))

        assert actual_url is None


class TestIsValidVlessClientUrl:

    def test_is_valid_vless_client_url_valid(self):
        valid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abcdef='
            '&sid=0001&spx=%2Fclient%2Fpath#client@domain.com'
        )

        result = is_valid_vless_client_url(valid_url)

        assert result is True

    def test_is_valid_vless_client_url_valid_long_sid(self):
        valid_url = (
            'vless://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee@192.168.1.1:8443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=example.com&pbk=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
            '&sid=abcdef0123456789&spx=%2Ftest#test@example.com'
        )

        result = is_valid_vless_client_url(valid_url)

        assert result is True

    def test_is_valid_vless_client_url_missing_flow_param(self):
        invalid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:443'
            '?type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abcd='
            '&sid=0001&spx=%2Fclient#client@domain.com'
        )

        result = is_valid_vless_client_url(invalid_url)

        assert result is False

    def test_is_valid_vless_client_url_missing_security_param(self):
        invalid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:443'
            '?flow=xtls-rprx-vision&type=raw&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abcd='
            '&sid=0001&spx=%2Fclient#client@domain.com'
        )

        result = is_valid_vless_client_url(invalid_url)

        assert result is False

    def test_is_valid_vless_client_url_invalid_uuid(self):
        invalid_url = (
            'vless://not-a-valid-uuid@example.com:443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abcd='
            '&sid=0001&spx=%2Fclient#client@domain.com'
        )

        result = is_valid_vless_client_url(invalid_url)

        assert result is False

    def test_is_valid_vless_client_url_invalid_port(self):
        invalid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:99999'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abcd='
            '&sid=0001&spx=%2Fclient#client@domain.com'
        )

        result = is_valid_vless_client_url(invalid_url)

        assert result is False

    def test_is_valid_vless_client_url_short_pbk(self):
        invalid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=short'
            '&sid=0001&spx=%2Fclient#client@domain.com'
        )

        result = is_valid_vless_client_url(invalid_url)

        assert result is False

    def test_is_valid_vless_client_url_missing_sid(self):
        valid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abdfcd='
            '&spx=%2Fclient#client@domain.com'
        )

        result = is_valid_vless_client_url(valid_url)

        assert result is True

    def test_is_valid_vless_client_url_empty_string(self):
        result = is_valid_vless_client_url('')

        assert result is False

    def test_is_valid_vless_client_url_missing_fragment(self):
        invalid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@example.com:443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=yahoo.com&pbk=abcdefghijklmnopqrstuvwxyz0123456789abcd='
            '&sid=0001&spx=%2Fclient'
        )

        result = is_valid_vless_client_url(invalid_url)

        assert result is False

    def test_is_valid_vless_client_url_pbk_with_padding(self):
        valid_url = (
            'vless://550e8400-e29b-41d4-a716-446655440000@10.0.0.1:443'
            '?flow=xtls-rprx-vision&type=raw&security=reality&fp=chrome'
            '&sni=test.com&pbk=aaaabbbbccccddddeeeeffffgggghhhh123456acefg='
            '&sid=abcd&spx=%2Fpath#name@host.com'
        )

        result = is_valid_vless_client_url(valid_url)

        assert result is True


class TestUfwOpenPort:

    def test_ufw_open_port_and_ssh_port(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        ufw_open_port(8443, 'udp', ssh_port=2222)

        expected_command = (
            'ufw allow 8443/udp && ufw allow 2222/tcp && yes | ufw enable && ufw reload'
        )
        mock_run_command.assert_called_once_with(expected_command)

    def test_ufw_open_port_tcp_protocol(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        ufw_open_port(443, 'tcp', ssh_port=22)

        expected_command = (
            'ufw allow 443/tcp && ufw allow 22/tcp && yes | ufw enable && ufw reload'
        )
        mock_run_command.assert_called_once_with(expected_command)

    def test_ufw_open_port_with_different_ports(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        ufw_open_port(9001, 'udp', ssh_port=2200)

        expected_command = (
            'ufw allow 9001/udp && ufw allow 2200/tcp && yes | ufw enable && ufw reload'
        )
        mock_run_command.assert_called_once_with(expected_command)


class TestDetectSshPort:

    def test_detect_ssh_port_found(self, tmp_path: Path):
        sshd_config = tmp_path / 'sshd_config'
        sshd_config.write_text(
            '# This is a comment\nPort 2222\nPermitRootLogin no\n',
            encoding='utf-8',
        )

        result = detect_ssh_port(sshd_config)

        assert result == 2222

    def test_detect_ssh_port_default_port(self, tmp_path: Path):
        sshd_config = tmp_path / 'sshd_config'
        sshd_config.write_text(
            '# This is a comment\nPort 22\nPermitRootLogin no\n',
            encoding='utf-8',
        )

        result = detect_ssh_port(sshd_config)

        assert result == 22

    def test_detect_ssh_port_not_found(self, tmp_path: Path):
        sshd_config = tmp_path / 'sshd_config'
        sshd_config.write_text(
            '# This is a comment\nPermitRootLogin no\nPasswordAuthentication no\n',
            encoding='utf-8',
        )

        result = detect_ssh_port(sshd_config)

        assert result is None

    def test_detect_ssh_port_commented_line(self, tmp_path: Path):
        sshd_config = tmp_path / 'sshd_config'
        sshd_config.write_text(
            '# Port 2222\nPort 22\n',
            encoding='utf-8',
        )

        result = detect_ssh_port(sshd_config)

        assert result == 22

    def test_detect_ssh_port_not_confused_by_port_forwarding(self, tmp_path: Path):
        sshd_config = tmp_path / 'sshd_config'
        sshd_config.write_text(
            'AllowTcpForwarding yes\nPermitTunnel no\nPort 2222\n',
            encoding='utf-8',
        )

        result = detect_ssh_port(sshd_config)

        assert result == 2222


class TestDetectCurrentIpv4:

    def test_detect_current_ipv4_success(self, mocker):
        mock_run_command = mocker.patch(
            'app.utils.run_command', return_value=(0, '192.168.1.100', ''))

        result = detect_current_ipv4()

        assert result == '192.168.1.100'
        mock_run_command.assert_called_once_with('hostname -i', check=False)

    def test_detect_current_ipv4_with_multiple_ips(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(0, '192.168.1.100 10.0.0.5', ''))

        result = detect_current_ipv4()

        assert result == '192.168.1.100'

    def test_detect_current_ipv4_not_found(self, mocker):
        mocker.patch('app.utils.run_command', return_value=(0, 'hostname', ''))

        result = detect_current_ipv4()

        assert result is None


class TestWriteTextFile:

    def test_write_text_file_new_file(self, tmp_path: Path):
        file_path = tmp_path / 'test.txt'

        write_text_file(file_path, 'test content')

        assert file_path.exists()
        assert file_path.read_text(encoding='utf-8') == 'test content'

    def test_write_text_file_existing_same_content(self, tmp_path: Path):
        file_path = tmp_path / 'test.txt'
        file_path.write_text('test content', encoding='utf-8')
        original_mtime = file_path.stat().st_mtime

        sleep(0.01)
        write_text_file(file_path, 'test content')

        assert file_path.stat().st_mtime == original_mtime
        assert file_path.read_text(encoding='utf-8') == 'test content'

    def test_write_text_file_existing_different_content(self, tmp_path: Path):
        file_path = tmp_path / 'test.txt'
        file_path.write_text('old content', encoding='utf-8')

        write_text_file(file_path, 'new content')

        assert file_path.read_text(encoding='utf-8') == 'new content'

    def test_write_text_file_with_chmod(self, tmp_path: Path):
        file_path = tmp_path / 'test.txt'

        write_text_file(file_path, 'test content', mode=0o644)

        assert file_path.exists()
        assert file_path.stat().st_mode & 0o777 == 0o644

    def test_write_text_file_with_directory_creation(self, tmp_path: Path):
        file_path = tmp_path / 'nested' / 'dir' / 'test.txt'

        write_text_file(file_path, 'content')

        assert file_path.exists()
        assert file_path.parent.exists()
        assert file_path.read_text(encoding='utf-8') == 'content'

    def test_write_text_file_with_nested_directory_and_chmod(self, tmp_path: Path):
        file_path = tmp_path / 'nested' / 'dir' / 'test.txt'

        write_text_file(file_path, 'content', mode=0o755)

        assert file_path.exists()
        assert file_path.stat().st_mode & 0o777 == 0o755
        assert file_path.read_text(encoding='utf-8') == 'content'


class TestIsXrayDistribInstalled:

    def test_is_xray_distrib_installed_success(self, mocker):
        mock_run_command = mocker.patch(
            'app.utils.run_command',
            return_value=(0, 'Xray 1.8.0 (installed)', '')
        )

        result = is_xray_distrib_installed('1.8.0')

        assert result is True
        mock_run_command.assert_called_once_with('xray --version')

    def test_is_xray_distrib_installed_with_v_prefix(self, mocker):
        mocker.patch(
            'app.utils.run_command',
            return_value=(0, 'Xray 1.8.0 (installed)', '')
        )

        result = is_xray_distrib_installed('v1.8.0')

        assert result is True

    def test_is_xray_distrib_installed_not_found(self, mocker):
        mocker.patch(
            'app.utils.run_command',
            return_value=(0, 'Xray 1.7.0 (installed)', '')
        )

        result = is_xray_distrib_installed('1.8.0')

        assert result is False

    def test_is_xray_distrib_installed_command_failure(self, mocker):
        mocker.patch(
            'app.utils.run_command',
            return_value=(1, '', 'xray: command not found')
        )

        result = is_xray_distrib_installed('1.8.0')

        assert result is False


class TestInstallXrayDistrib:

    def test_install_xray_distrib_creates_binary(self, mocker, tmp_path: Path):
        bin_path = tmp_path / 'usr' / 'local' / 'bin' / 'xray'
        xray_binary = b'xray_binary_content'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(_make_xray_zip(xray_binary))

        install_xray_distrib('http://example.com/xray.zip', bin_path)

        assert bin_path.exists()
        assert bin_path.read_bytes() == xray_binary
        assert bin_path.stat().st_mode & 0o777 == 0o744
        mock_get.assert_called_once_with('http://example.com/xray.zip', timeout=20, stream=True)

    def test_install_xray_distrib_creates_parent_directories(self, mocker, tmp_path: Path):
        bin_path = tmp_path / 'deep' / 'nested' / 'xray'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(_make_xray_zip(b'binary'))

        install_xray_distrib('http://example.com/xray.zip', bin_path)

        assert bin_path.parent.exists()

    def test_install_xray_distrib_overwrites_existing_binary(self, mocker, tmp_path: Path):
        bin_path = tmp_path / 'xray'
        bin_path.write_bytes(b'old_binary')
        new_binary = b'new_xray_binary'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(_make_xray_zip(new_binary))

        install_xray_distrib('http://example.com/xray.zip', bin_path)

        assert bin_path.read_bytes() == new_binary


class TestInstallGeoData:

    def test_install_geo_data_success(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'geoip.dat'
        test_content = b'geodata_content'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(test_content)

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.exists()
        assert geo_data_path.read_bytes() == test_content
        mock_get.assert_called_once_with('http://example.com/geoip.dat', timeout=20, stream=True)
        assert geo_data_path.stat().st_mode & 0o777 == 0o644

    def test_install_geo_data_creates_parent_directory(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'new_dir' / 'geoip.dat'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(b'geodata')

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.parent.exists()

    def test_install_geo_data_with_real_path(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'geodata' / 'geoip.dat'
        test_content = b'test_geodata_content'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(test_content)

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.exists()
        assert geo_data_path.read_bytes() == test_content
        assert geo_data_path.parent.exists()

    def test_install_geo_data_sets_correct_permissions(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'geoip.dat'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(b'geodata')

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.stat().st_mode & 0o777 == 0o644

    def test_install_geo_data_url_parameter(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'custom.dat'
        test_url = 'http://example.com/custom_geodata.dat'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(b'geodata')

        install_geo_data(test_url, geo_data_path)

        mock_get.assert_called_once_with(test_url, timeout=20, stream=True)

    def test_install_geo_data_overwrites_existing_file(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'geoip.dat'
        geo_data_path.write_bytes(b'old_geodata')
        new_content = b'new_geodata_content'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(new_content)

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.read_bytes() == new_content

    def test_install_geo_data_with_empty_content(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'geoip.dat'

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(b'')

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.read_bytes() == b''

    def test_install_geo_data_large_content(self, mocker, tmp_path: Path):
        geo_data_path = tmp_path / 'geoip.dat'
        large_content = b'x' * (10 * 1024 * 1024)  # 10 MB

        mock_get = mocker.patch('app.utils.get_request')
        mock_get.return_value = _make_streaming_mock(large_content)

        install_geo_data('http://example.com/geoip.dat', geo_data_path)

        assert geo_data_path.read_bytes() == large_content


class TestIsXrayServiceInstalled:

    def test_is_xray_service_installed_true(self, mocker, tmp_path: Path):
        service_content = '[Unit]\nDescription=Xray Service\n'
        unit_path = tmp_path / 'xray.service'
        unit_path.write_text(service_content, encoding='utf-8')
        mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value.read_text.return_value = service_content

        result = is_xray_service_installed(unit_path)

        assert result is True

    def test_is_xray_service_installed_file_not_exists(self, tmp_path: Path):
        unit_path = tmp_path / 'nonexistent.service'

        result = is_xray_service_installed(unit_path)

        assert result is False

    def test_is_xray_service_installed_different_content(self, mocker, tmp_path: Path):
        expected_content = '[Unit]\nDescription=Xray Service\n'
        actual_content = '[Unit]\nDescription=Different Service\n'
        unit_path = tmp_path / 'xray.service'
        unit_path.write_text(actual_content, encoding='utf-8')
        mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value.read_text.return_value = expected_content

        result = is_xray_service_installed(unit_path)

        assert result is False


class TestInstallXrayService:

    def test_install_xray_service_success(self, mocker, tmp_path: Path):
        service_content = '[Unit]\nDescription=Xray Service\n'
        unit_path = tmp_path / 'xray.service'
        mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value.read_text.return_value = service_content
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        install_xray_service(unit_path)

        assert unit_path.exists()
        assert unit_path.read_text(encoding='utf-8') == service_content
        assert unit_path.stat().st_mode & 0o777 == 0o644
        mock_run_command.assert_called_once_with('systemctl daemon-reload', check=True)


class TestStopXrayService:

    def test_stop_xray_service_success(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        stop_xray_service()

        mock_run_command.assert_called_once_with('systemctl stop xray -q', check=True)


class TestStartXrayService:

    def test_start_xray_service_success(self, mocker):
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        start_xray_service()

        mock_run_command.assert_called_once_with('systemctl start xray -q', check=True)


class TestRunCommand:

    def test_run_command_success(self, mocker):
        mock_subprocess_run = mocker.patch('app.utils.run')
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b'output'
        mock_result.stderr = b''
        mock_subprocess_run.return_value = mock_result

        result = run_command('echo "test"')

        assert result[0] == 0
        assert result[1] == 'output'
        assert result[2] == ''
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert call_args[1]['shell'] is True
        assert call_args[1]['capture_output'] is True

    def test_run_command_with_stdin(self, mocker):
        mock_subprocess_run = mocker.patch('app.utils.run')
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b'output'
        mock_result.stderr = b''
        mock_subprocess_run.return_value = mock_result

        result = run_command('cat', stdin='test input')

        assert result[0] == 0
        call_args = mock_subprocess_run.call_args
        assert call_args[1]['input'] == b'test input'

    def test_run_command_failure(self, mocker):
        mock_subprocess_run = mocker.patch('app.utils.run')
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b''
        mock_result.stderr = b'error message'
        mock_subprocess_run.return_value = mock_result

        result = run_command('invalid_command')

        assert result[0] == 1
        assert result[2] == 'error message'

    def test_run_command_with_check_true(self, mocker):
        mock_subprocess_run = mocker.patch('app.utils.run')
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b''
        mock_result.stderr = b''
        mock_subprocess_run.return_value = mock_result

        run_command('ls', check=True)

        call_args = mock_subprocess_run.call_args
        assert call_args[1]['check'] is True

    def test_run_command_with_timeout(self, mocker):
        mock_subprocess_run = mocker.patch('app.utils.run')
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b''
        mock_result.stderr = b''
        mock_subprocess_run.return_value = mock_result

        run_command('sleep 10', timeout=5)

        call_args = mock_subprocess_run.call_args
        assert call_args[1]['timeout'] == 5


class TestDetectVeepeenetVersions:

    def test_detect_veepeenet_versions_success(self, mocker):
        versions_json = '{"app": "1.0.0", "xray": "1.8.0"}'
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = versions_json

        mock_versions_view = MagicMock()
        mock_validate = mocker.patch(
            'app.utils.VersionsView.model_validate_json',
            return_value=mock_versions_view
        )

        result = detect_veepeenet_versions()

        assert result == mock_versions_view
        mock_app_resources.read_text.assert_called_once_with('utf-8')
        mock_validate.assert_called_once_with(versions_json)


class TestRemoveDuplicates:

    def test_remove_duplicates_empty_list(self):
        result = remove_duplicates([])

        assert not result

    def test_remove_duplicates_no_duplicates(self):
        source = [1, 2, 3, 4, 5]

        result = remove_duplicates(source)

        assert result == [1, 2, 3, 4, 5]

    def test_remove_duplicates_with_duplicates(self):
        source = [1, 2, 2, 3, 3, 3, 4, 5, 5]

        result = remove_duplicates(source)

        assert result == [1, 2, 3, 4, 5]

    def test_remove_duplicates_all_same(self):
        source = [5, 5, 5, 5, 5]

        result = remove_duplicates(source)

        assert result == [5]

    def test_remove_duplicates_strings(self):
        source = ['a', 'b', 'a', 'c', 'b', 'd']

        result = remove_duplicates(source)

        assert result == ['a', 'b', 'c', 'd']

    def test_remove_duplicates_mixed_types(self):
        source = [1, 'a', 1, 'a', 2, 'b']

        result = remove_duplicates(source)

        assert result == [1, 'a', 2, 'b']


class TestGetNewItems:

    def test_get_new_items_no_new_items(self):
        old = [1, 2, 3]
        new = [1, 2, 3]

        result = get_new_items(old, new)

        assert not result

    def test_get_new_items_all_new(self):
        old = [1, 2, 3]
        new = [4, 5, 6]

        result = get_new_items(old, new)

        assert result == [4, 5, 6]

    def test_get_new_items_mixed(self):
        old = [1, 2, 3]
        new = [2, 3, 4, 5]

        result = get_new_items(old, new)

        assert result == [4, 5]

    def test_get_new_items_empty_old(self):
        old = []
        new = [1, 2, 3]

        result = get_new_items(old, new)

        assert result == [1, 2, 3]

    def test_get_new_items_empty_new(self):
        old = [1, 2, 3]
        new = []

        result = get_new_items(old, new)

        assert not result

    def test_get_new_items_both_empty(self):
        old = []
        new = []

        result = get_new_items(old, new)

        assert not result

    def test_get_new_items_strings(self):
        old = ['a', 'b', 'c']
        new = ['b', 'c', 'd', 'e']

        result = get_new_items(old, new)

        assert result == ['d', 'e']

    def test_get_new_items_preserves_order(self):
        old = [1, 2]
        new = [5, 1, 3, 2, 4]

        result = get_new_items(old, new)

        assert result == [5, 3, 4]


class TestGetExistingItems:

    def test_get_existing_items_all_exist(self):
        old = [1, 2, 3]
        new = [1, 2, 3]

        result = get_existing_items(old, new)

        assert result == [1, 2, 3]

    def test_get_existing_items_none_exist(self):
        old = [1, 2, 3]
        new = [4, 5, 6]

        result = get_existing_items(old, new)

        assert not result

    def test_get_existing_items_partial(self):
        old = [1, 2, 3]
        new = [2, 3, 4, 5]

        result = get_existing_items(old, new)

        assert result == [2, 3]

    def test_get_existing_items_empty_old(self):
        old = []
        new = [1, 2, 3]

        result = get_existing_items(old, new)

        assert not result

    def test_get_existing_items_empty_new(self):
        old = [1, 2, 3]
        new = []

        result = get_existing_items(old, new)

        assert not result

    def test_get_existing_items_both_empty(self):
        old = []
        new = []

        result = get_existing_items(old, new)

        assert not result

    def test_get_existing_items_strings(self):
        old = ['a', 'b', 'c']
        new = ['b', 'c', 'd', 'e']

        result = get_existing_items(old, new)

        assert result == ['b', 'c']

    def test_get_existing_items_preserves_order(self):
        old = [1, 2, 3, 4, 5]
        new = [5, 1, 3, 2, 4]

        result = get_existing_items(old, new)

        assert result == [5, 1, 3, 2, 4]

    def test_get_existing_items_duplicates_in_new(self):
        old = [1, 2, 3]
        new = [1, 2, 1, 3, 2]

        result = get_existing_items(old, new)

        assert result == [1, 2, 1, 3, 2]


class TestSetValue:

    def test_set_value_change_existing_attribute(self):
        class TestObject:
            attr = 'old_value'

        obj = TestObject()
        result = set_value(obj, 'attr', 'new_value')

        assert result is True
        assert obj.attr == 'new_value'

    def test_set_value_no_change_same_value(self):
        class TestObject:
            attr = 'value'

        obj = TestObject()
        result = set_value(obj, 'attr', 'value')

        assert result is False
        assert obj.attr == 'value'

    def test_set_value_attribute_not_found(self):
        class TestObject:
            pass

        obj = TestObject()
        with pytest.raises(AttributeError) as exc_info:
            set_value(obj, 'nonexistent_attr', 'value')

        assert 'has no attribute' in str(exc_info.value)
        assert 'nonexistent_attr' in str(exc_info.value)

    def test_set_value_with_int_attribute(self):
        class TestObject:
            count = 5

        obj = TestObject()
        result = set_value(obj, 'count', 10)

        assert result is True
        assert obj.count == 10

    def test_set_value_with_int_no_change(self):
        class TestObject:
            count = 5

        obj = TestObject()
        result = set_value(obj, 'count', 5)

        assert result is False
        assert obj.count == 5

    def test_set_value_with_none_value(self):
        class TestObject:
            attr = 'value'

        obj = TestObject()
        result = set_value(obj, 'attr', None)

        assert result is False
        assert obj.attr == 'value'

    def test_set_value_from_none_to_value(self):
        class TestObject:
            attr = None

        obj = TestObject()
        result = set_value(obj, 'attr', 'new_value')

        assert result is True
        assert obj.attr == 'new_value'

    def test_set_value_with_list_attribute(self):
        class TestObject:
            items = [1, 2, 3]

        obj = TestObject()
        result = set_value(obj, 'items', [4, 5, 6])

        assert result is True
        assert obj.items == [4, 5, 6]

    def test_set_value_with_same_list(self):
        class TestObject:
            items = [1, 2, 3]

        obj = TestObject()
        result = set_value(obj, 'items', [1, 2, 3])

        assert result is False
        assert obj.items == [1, 2, 3]

    def test_set_value_with_dict_attribute(self):
        class TestObject:
            config = {'key': 'value'}

        obj = TestObject()
        result = set_value(obj, 'config', {'key': 'new_value'})

        assert result is True
        assert obj.config == {'key': 'new_value'}

    def test_set_value_with_boolean_attribute(self):
        class TestObject:
            enabled = True

        obj = TestObject()
        result = set_value(obj, 'enabled', False)

        assert result is True
        assert obj.enabled is False

    def test_set_value_with_boolean_no_change(self):
        class TestObject:
            enabled = True

        obj = TestObject()
        result = set_value(obj, 'enabled', True)

        assert result is False
        assert obj.enabled is True

    def test_set_value_with_zero_value(self):
        class TestObject:
            count = 5

        obj = TestObject()
        result = set_value(obj, 'count', 0)

        assert result is True
        assert obj.count == 0

    def test_set_value_with_empty_string(self):
        class TestObject:
            name = 'John'

        obj = TestObject()
        result = set_value(obj, 'name', '')

        assert result is True
        assert obj.name == ''

    def test_set_value_with_empty_string_no_change(self):
        class TestObject:
            name = ''

        obj = TestObject()
        result = set_value(obj, 'name', '')

        assert result is False
        assert obj.name == ''

    def test_set_value_with_multiple_attributes(self):
        class TestObject:
            attr1 = 'value1'
            attr2 = 'value2'

        obj = TestObject()
        result1 = set_value(obj, 'attr1', 'new_value1')
        result2 = set_value(obj, 'attr2', 'value2')

        assert result1 is True
        assert result2 is False
        assert obj.attr1 == 'new_value1'
        assert obj.attr2 == 'value2'

    def test_set_value_with_nested_object_attribute(self):
        class InnerObject:
            value = 'inner'

        class TestObject:
            inner = InnerObject()

        obj = TestObject()
        new_inner = InnerObject()
        new_inner.value = 'new_inner'
        result = set_value(obj, 'inner', new_inner)

        assert result is True
        assert obj.inner == new_inner
        assert obj.inner.value == 'new_inner'
