# pylint: disable=too-many-lines
from pathlib import Path
from sys import getdefaultencoding
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockFixture

from app.model.xray import Xray
from app.utils import (
    gen_xray_private_key,
    gen_xray_password,
    is_xray_service_running,
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
    get_short_id,
    set_value,
)


@pytest.fixture(name='valid_xray_config_with_clients_path')
def fixture_valid_xray_config_with_clients_path() -> Path:
    return Path('tests/resources/valid_xray_config_with_clients.json')


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

        with pytest.raises(RuntimeError) as exc_info:
            gen_xray_private_key()

        assert 'Error generating private key' in str(exc_info.value)
        assert 'code:1' in str(exc_info.value)

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

        with pytest.raises(RuntimeError) as exc_info:
            gen_xray_password('test_key')

        assert 'Error generating password' in str(exc_info.value)

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

    def test_enable_xray_service_success(self, mocker):
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
        with open(valid_xray_config_with_clients_path, 'rt', encoding=getdefaultencoding()) as f:
            xray_config_content = f.read()

        actual_url = get_vless_client_url(
            'c1.client', Xray.model_validate_json(xray_config_content))

        assert actual_url == expected_client_url

    def test_get_vless_client_url_not_found(self, valid_xray_config_with_clients_path: Path):
        with open(valid_xray_config_with_clients_path, 'rt', encoding=getdefaultencoding()) as f:
            xray_config_content = f.read()

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

    def test_detect_ssh_port_found(self):
        sshd_config_content = (
            '# This is a comment\n'
            'Port 2222\n'
            'PermitRootLogin no\n'
        )
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = sshd_config_content

        result = detect_ssh_port(mock_path)

        assert result == 2222
        mock_path.read_text.assert_called_once_with(encoding=getdefaultencoding())

    def test_detect_ssh_port_default_port(self):
        sshd_config_content = (
            '# This is a comment\n'
            'Port 22\n'
            'PermitRootLogin no\n'
        )
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = sshd_config_content

        result = detect_ssh_port(mock_path)

        assert result == 22

    def test_detect_ssh_port_not_found(self):
        sshd_config_content = (
            '# This is a comment\n'
            'PermitRootLogin no\n'
            'PasswordAuthentication no\n'
        )
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = sshd_config_content

        result = detect_ssh_port(mock_path)

        assert result is None

    def test_detect_ssh_port_commented_line(self):
        sshd_config_content = (
            '# Port 2222\n'
            'Port 22\n'
        )
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = sshd_config_content

        result = detect_ssh_port(mock_path)

        assert result == 22


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

    def test_write_text_file_new_file(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'test.txt'

            write_text_file(file_path, 'test content')

            assert file_path.exists()
            assert file_path.read_text(encoding=getdefaultencoding()) == 'test content'

    def test_write_text_file_existing_same_content(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'test.txt'
            file_path.write_text('test content', encoding=getdefaultencoding())
            original_stat = file_path.stat()

            sleep(0.01)

            write_text_file(file_path, 'test content')

            new_stat = file_path.stat()
            assert original_stat.st_mtime == new_stat.st_mtime
            assert file_path.read_text(encoding=getdefaultencoding()) == 'test content'

    def test_write_text_file_existing_different_content(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'test.txt'
            file_path.write_text('old content', encoding=getdefaultencoding())

            write_text_file(file_path, 'new content')

            assert file_path.read_text(encoding=getdefaultencoding()) == 'new content'

    def test_write_text_file_with_chmod(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'test.txt'

            write_text_file(file_path, 'test content', mode=0o644)

            assert file_path.exists()
            file_mode = file_path.stat().st_mode & 0o777
            assert file_mode == 0o644

    def test_write_text_file_with_directory_creation(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'nested' / 'dir' / 'test.txt'

            write_text_file(file_path, 'content')

            assert file_path.exists()
            assert file_path.parent.exists()
            assert file_path.read_text(encoding=getdefaultencoding()) == 'content'

    def test_write_text_file_with_nested_directory_and_chmod(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'nested' / 'dir' / 'test.txt'

            write_text_file(file_path, 'content', mode=0o755)

            assert file_path.exists()
            file_mode = file_path.stat().st_mode & 0o777
            assert file_mode == 0o755
            assert file_path.read_text(encoding=getdefaultencoding()) == 'content'


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

    def test_install_xray_distrib_new_file(self, mocker):
        mock_bin_path = MagicMock(spec=Path)
        mock_bin_path.unlink.side_effect = FileNotFoundError()
        mock_bin_path.parent.mkdir = MagicMock()
        mock_bin_path.write_bytes = MagicMock()
        mock_bin_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        mock_response.content = b'zip_content'
        mock_get.return_value = mock_response

        mock_xray_file = MagicMock()
        mock_xray_file.read.return_value = b'xray_binary'
        mock_zipfile = mocker.patch('app.utils.ZipFile')
        mock_zip_instance = MagicMock()
        open_return_value = mock_zip_instance.__enter__.return_value.open.return_value.__enter__
        open_return_value.return_value = mock_xray_file
        mock_zipfile.return_value = mock_zip_instance

        install_xray_distrib('http://example.com/xray.zip', mock_bin_path)

        mock_bin_path.parent.mkdir.assert_called_once_with(parents=True, mode=0o755, exist_ok=True)
        mock_bin_path.write_bytes.assert_called_once_with(b'xray_binary')
        mock_bin_path.chmod.assert_called_once_with(0o744)
        mock_get.assert_called_once_with('http://example.com/xray.zip', timeout=20_000)

    def test_install_xray_distrib_existing_file(self, mocker):
        mock_bin_path = MagicMock(spec=Path)
        mock_bin_path.unlink = MagicMock()
        mock_bin_path.parent.mkdir = MagicMock()
        mock_bin_path.write_bytes = MagicMock()
        mock_bin_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        mock_response.content = b'zip_content'
        mock_get.return_value = mock_response

        mock_xray_file = MagicMock()
        mock_xray_file.read.return_value = b'xray_binary'
        mock_zipfile = mocker.patch('app.utils.ZipFile')
        mock_zip_instance = MagicMock()
        open_return_value = mock_zip_instance.__enter__.return_value.open.return_value.__enter__
        open_return_value.return_value = mock_xray_file
        mock_zipfile.return_value = mock_zip_instance

        install_xray_distrib('http://example.com/xray.zip', mock_bin_path)

        mock_bin_path.parent.mkdir.assert_called_once_with(parents=True, mode=0o755, exist_ok=True)
        mock_bin_path.write_bytes.assert_called_once_with(b'xray_binary')
        mock_bin_path.chmod.assert_called_once_with(0o744)


class TestInstallGeoData:

    def test_install_geo_data_success(self, mocker):
        mock_geo_data_path = MagicMock(spec=Path)
        mock_geo_data_path.parent.mkdir = MagicMock()
        mock_geo_data_path.write_bytes = MagicMock()
        mock_geo_data_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        mock_response.content = b'geodata_content'
        mock_get.return_value = mock_response

        install_geo_data('http://example.com/geoip.dat', mock_geo_data_path)

        mock_geo_data_path.parent.mkdir.assert_called_once_with(
            parents=True, mode=0o755, exist_ok=True)
        mock_get.assert_called_once_with('http://example.com/geoip.dat', timeout=20_000)
        mock_geo_data_path.write_bytes.assert_called_once_with(b'geodata_content')
        mock_geo_data_path.chmod.assert_called_once_with(0o655)

    def test_install_geo_data_creates_parent_directory(self, mocker):
        mock_geo_data_path = MagicMock(spec=Path)
        mock_geo_data_path.parent.mkdir = MagicMock()
        mock_geo_data_path.write_bytes = MagicMock()
        mock_geo_data_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        mock_response.content = b'geodata'
        mock_get.return_value = mock_response

        install_geo_data('http://example.com/geosite.dat', mock_geo_data_path)

        mock_geo_data_path.parent.mkdir.assert_called_once_with(
            parents=True, mode=0o755, exist_ok=True)

    def test_install_geo_data_with_real_path(self, mocker):
        with TemporaryDirectory() as temp_dir:
            geo_data_path = Path(temp_dir) / 'geodata' / 'geoip.dat'

            mock_get = mocker.patch('app.utils.get_request')
            mock_response = MagicMock()
            test_content = b'test_geodata_content'
            mock_response.content = test_content
            mock_get.return_value = mock_response

            install_geo_data('http://example.com/geoip.dat', geo_data_path)

            assert geo_data_path.exists()
            assert geo_data_path.read_bytes() == test_content
            assert geo_data_path.parent.exists()

    def test_install_geo_data_sets_correct_permissions(self, mocker):
        with TemporaryDirectory() as temp_dir:
            geo_data_path = Path(temp_dir) / 'geoip.dat'

            mock_get = mocker.patch('app.utils.get_request')
            mock_response = MagicMock()
            mock_response.content = b'geodata'
            mock_get.return_value = mock_response

            install_geo_data('http://example.com/geoip.dat', geo_data_path)

            file_mode = geo_data_path.stat().st_mode & 0o777
            assert file_mode == 0o655

    def test_install_geo_data_url_parameter(self, mocker):
        mock_geo_data_path = MagicMock(spec=Path)
        mock_geo_data_path.parent.mkdir = MagicMock()
        mock_geo_data_path.write_bytes = MagicMock()
        mock_geo_data_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        mock_response.content = b'geodata'
        mock_get.return_value = mock_response

        test_url = 'http://example.com/custom_geodata.dat'
        install_geo_data(test_url, mock_geo_data_path)

        mock_get.assert_called_once_with(test_url, timeout=20_000)

    def test_install_geo_data_overwrites_existing_file(self, mocker):
        with TemporaryDirectory() as temp_dir:
            geo_data_path = Path(temp_dir) / 'geoip.dat'

            # Create an existing file
            old_content = b'old_geodata'
            geo_data_path.write_bytes(old_content)

            mock_get = mocker.patch('app.utils.get_request')
            mock_response = MagicMock()
            new_content = b'new_geodata_content'
            mock_response.content = new_content
            mock_get.return_value = mock_response

            install_geo_data('http://example.com/geoip.dat', geo_data_path)

            assert geo_data_path.read_bytes() == new_content

    def test_install_geo_data_with_empty_content(self, mocker):
        mock_geo_data_path = MagicMock(spec=Path)
        mock_geo_data_path.parent.mkdir = MagicMock()
        mock_geo_data_path.write_bytes = MagicMock()
        mock_geo_data_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        mock_response.content = b''
        mock_get.return_value = mock_response

        install_geo_data('http://example.com/geoip.dat', mock_geo_data_path)

        mock_geo_data_path.write_bytes.assert_called_once_with(b'')
        mock_geo_data_path.chmod.assert_called_once_with(0o655)

    def test_install_geo_data_large_content(self, mocker):
        mock_geo_data_path = MagicMock(spec=Path)
        mock_geo_data_path.parent.mkdir = MagicMock()
        mock_geo_data_path.write_bytes = MagicMock()
        mock_geo_data_path.chmod = MagicMock()

        mock_get = mocker.patch('app.utils.get_request')
        mock_response = MagicMock()
        large_content = b'x' * (10 * 1024 * 1024)  # 10 MB
        mock_response.content = large_content
        mock_get.return_value = mock_response

        install_geo_data('http://example.com/geoip.dat', mock_geo_data_path)

        mock_geo_data_path.write_bytes.assert_called_once_with(large_content)


class TestIsXrayServiceInstalled:

    def test_is_xray_service_installed_true(self, mocker):
        expected_content = '[Unit]\nDescription=Xray Service\n'
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = expected_content
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = expected_content

        result = is_xray_service_installed(mock_path)

        assert result is True
        mock_path.read_text.assert_called_once_with(encoding=getdefaultencoding())

    def test_is_xray_service_installed_file_not_exists(self):
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.side_effect = FileNotFoundError()

        result = is_xray_service_installed(mock_path)

        assert result is False

    def test_is_xray_service_installed_different_content(self, mocker):
        expected_content = '[Unit]\nDescription=Xray Service\n'
        actual_content = '[Unit]\nDescription=Different Service\n'
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = actual_content
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = expected_content

        result = is_xray_service_installed(mock_path)

        assert result is False


class TestInstallXrayService:
    def test_install_xray_service_success(self, mocker):
        service_content = '[Unit]\nDescription=Xray Service\n'
        mock_path = MagicMock(spec=Path)
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = service_content
        mock_write_text_file = mocker.patch('app.utils.write_text_file')
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        install_xray_service(mock_path)

        mock_write_text_file.assert_called_once_with(
            mock_path,
            service_content,
            mode=0o644
        )
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


class TestGetShortId:

    def test_get_short_id_default_range(self):
        existing_short_ids = [1, 2, 3, 4, 5]

        result = get_short_id(existing_short_ids)

        assert result == 6

    def test_get_short_id_empty_existing_ids(self):
        existing_short_ids = []

        result = get_short_id(existing_short_ids)

        assert result == 1

    def test_get_short_id_with_gaps(self):
        existing_short_ids = [1, 3, 5, 7]

        result = get_short_id(existing_short_ids)

        assert result == 2

    def test_get_short_id_custom_range(self):
        existing_short_ids = [100, 101, 102]

        result = get_short_id(existing_short_ids, interval=range(100, 200))

        assert result == 103

    def test_get_short_id_custom_range_with_gap(self):
        existing_short_ids = [50, 52, 54]

        result = get_short_id(existing_short_ids, interval=range(50, 60))

        assert result == 51

    def test_get_short_id_custom_range_first_available(self):
        existing_short_ids = [11, 12, 13]

        result = get_short_id(existing_short_ids, interval=range(10, 20))

        assert result == 10

    def test_get_short_id_no_available_ids(self):
        existing_short_ids = list(range(100))

        with pytest.raises(ValueError) as exc_info:
            get_short_id(existing_short_ids, interval=range(100))

        assert 'No available short ID found' in str(exc_info.value)
        assert 'range(0, 100)' in str(exc_info.value)

    def test_get_short_id_large_range(self):
        existing_short_ids = [0, 1, 2]

        result = get_short_id(existing_short_ids, interval=range(1000))

        assert result == 3

    def test_get_short_id_returns_first_available(self):
        existing_short_ids = [1, 3, 4, 5, 6]

        result = get_short_id(existing_short_ids)

        assert result == 2

    def test_get_short_id_high_numbers(self):
        existing_short_ids = [9999]

        result = get_short_id(existing_short_ids)

        assert result == 1

    def test_get_short_id_with_unsorted_existing_ids(self):
        existing_short_ids = [5, 2, 8, 1, 3]

        result = get_short_id(existing_short_ids, interval=range(1, 10))

        assert result == 4

    def test_get_short_id_all_in_range_taken(self):
        existing_short_ids = list(range(1, 6))

        with pytest.raises(ValueError) as exc_info:
            get_short_id(existing_short_ids, interval=range(1, 6))

        assert 'No available short ID found' in str(exc_info.value)


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
