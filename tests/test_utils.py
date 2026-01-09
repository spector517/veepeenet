import pytest
from pytest_mock import MockFixture
from unittest.mock import mock_open, MagicMock
from sys import getdefaultencoding
from app.utils import (
    gen_xray_private_key,
    gen_xray_password,
    is_xray_service_running,
    restart_xray_service,
    enable_xray_service,
    disable_xray_service,
    get_vless_client_url,
    ufw_open_port,
    detect_ssh_port,
    detect_current_ipv4,
    write_text_file,
    is_xray_distrib_installed,
    install_xray_distrib,
    is_xray_service_installed,
    install_xray_service,
    stop_xray_service,
    start_xray_service,
    run_command,
    detect_veepeenet_versions,
    is_xray_service_enabled,
)
from app.model.xray import Xray


@pytest.fixture
def valid_xray_config_with_clients_path() -> str:
    return 'tests/resources/valid_xray_config_with_clients.json'


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
        expected_password = 'xXyYzZ987654321aBcDeFgHiJkLmNoOpP=='
        mock_run_command = mocker.patch(
            'app.utils.run_command', return_value=(0, f'Password: {expected_password}', ''))

        result = gen_xray_password(private_key)

        assert result == expected_password
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

    def test_get_vless_client_url_success(self, mocker: MockFixture, valid_xray_config_with_clients_path: str):
        mocker.patch('app.utils.gen_xray_password', return_value='random-password-1')
        expected_client_url = (
            'vless://random-uuid-1@0.0.0.0:443?flow=xtls-rprx-vision'
            '&type=raw'
            '&security=reality'
            '&fp=chrome'
            '&sni=yahoo.com'
            '&pbk=random-password-1'
            '&sid=0001'
            '&spx=%2Fc1'
            '#c1@0.0.0.0'
        )
        with open(valid_xray_config_with_clients_path, 'rt', encoding=getdefaultencoding()) as f:
            xray_config_content = f.read()

        actual_url = get_vless_client_url(
            'c1', Xray.model_validate_json(xray_config_content))

        assert actual_url == expected_client_url


    def test_get_vless_client_url_not_found(self, valid_xray_config_with_clients_path: str):
        with open(valid_xray_config_with_clients_path, 'rt', encoding=getdefaultencoding()) as f:
            xray_config_content = f.read()

        actual_url = get_vless_client_url(
            'nonexistent_client', Xray.model_validate_json(xray_config_content))

        assert actual_url is None


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

    def test_detect_ssh_port_found(self, mocker):
        sshd_config_content = (
            '# This is a comment\n'
            'Port 2222\n'
            'PermitRootLogin no\n'
        )
        mock_open_func = mocker.patch('builtins.open', mock_open(read_data=sshd_config_content))

        result = detect_ssh_port('/etc/ssh/sshd_config')

        assert result == 2222
        mock_open_func.assert_called_once_with(
            '/etc/ssh/sshd_config', 'rt', encoding='utf-8'
        )

    def test_detect_ssh_port_default_port(self, mocker):
        sshd_config_content = (
            '# This is a comment\n'
            'Port 22\n'
            'PermitRootLogin no\n'
        )
        mocker.patch('builtins.open', mock_open(read_data=sshd_config_content))

        result = detect_ssh_port('/etc/ssh/sshd_config')

        assert result == 22

    def test_detect_ssh_port_not_found(self, mocker):
        sshd_config_content = (
            '# This is a comment\n'
            'PermitRootLogin no\n'
            'PasswordAuthentication no\n'
        )
        mocker.patch('builtins.open', mock_open(read_data=sshd_config_content))

        result = detect_ssh_port('/etc/ssh/sshd_config')

        assert result is None

    def test_detect_ssh_port_commented_line(self, mocker):
        sshd_config_content = (
            '# Port 2222\n'
            'Port 22\n'
        )
        mocker.patch('builtins.open', mock_open(read_data=sshd_config_content))

        result = detect_ssh_port('/etc/ssh/sshd_config')

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

    def test_write_text_file_new_file(self, mocker):
        mocker.patch('app.utils.exists', return_value=False)
        mock_makedirs = mocker.patch('app.utils.makedirs')
        mock_open_func = mocker.patch('builtins.open', mock_open())
        mock_chmod = mocker.patch('app.utils.chmod')

        write_text_file('/tmp/test.txt', 'test content')

        mock_makedirs.assert_called_once()
        mock_open_func.assert_called_once_with('/tmp/test.txt', 'wt', encoding='utf-8')
        mock_chmod.assert_not_called()

    def test_write_text_file_existing_same_content(self, mocker):
        mocker.patch('app.utils.exists', return_value=True)
        mocker.patch('builtins.open', mock_open(read_data='test content'))
        mock_makedirs = mocker.patch('app.utils.makedirs')
        mock_chmod = mocker.patch('app.utils.chmod')

        write_text_file('/tmp/test.txt', 'test content')

        mock_makedirs.assert_not_called()
        mock_chmod.assert_not_called()

    def test_write_text_file_existing_different_content(self, mocker):
        mocker.patch('app.utils.exists', return_value=True)
        mock_open_func = mocker.patch(
            'builtins.open',
            mock_open(read_data='old content')
        )
        mock_chmod = mocker.patch('app.utils.chmod')

        write_text_file('/tmp/test.txt', 'new content')

        calls = mock_open_func.call_args_list
        write_call = [c for c in calls if c[0][1] == 'wt']
        assert len(write_call) > 0
        mock_chmod.assert_not_called()

    def test_write_text_file_with_chmod(self, mocker):
        mocker.patch('app.utils.exists', return_value=False)
        mocker.patch('app.utils.makedirs')
        mocker.patch('builtins.open', mock_open())
        mock_chmod = mocker.patch('app.utils.chmod')

        write_text_file('/tmp/test.txt', 'test content', mode=0o644)

        mock_chmod.assert_called_once_with('/tmp/test.txt', 0o644)

    def test_write_text_file_with_directory_creation(self, mocker):
        mocker.patch('app.utils.exists', return_value=False)
        mock_makedirs = mocker.patch('app.utils.makedirs')
        mocker.patch('builtins.open', mock_open())
        mocker.patch('app.utils.chmod')

        write_text_file('/tmp/nested/dir/test.txt', 'content')

        mock_makedirs.assert_called_once()
        call_args = mock_makedirs.call_args
        assert '/tmp/nested/dir' in call_args[0][0]


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
        mock_exists = mocker.patch('app.utils.exists', return_value=False)
        mock_remove = mocker.patch('app.utils.remove')
        mocker.patch('app.utils.dirname', return_value='/usr/local/bin')
        mock_makedirs = mocker.patch('app.utils.makedirs')
        mock_chmod = mocker.patch('app.utils.chmod')
        mock_get = mocker.patch('app.utils.get')
        mock_zipfile = mocker.patch('app.utils.ZipFile')

        mock_response = MagicMock()
        mock_response.content = b'zip_content'
        mock_get.return_value = mock_response

        mock_xray_file = MagicMock()
        mock_xray_file.read.return_value = b'xray_binary'
        mock_zip_instance = MagicMock()
        mock_zip_instance.__enter__.return_value.open.return_value.__enter__.return_value = mock_xray_file
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        mocker.patch('builtins.open', mock_open())

        install_xray_distrib('http://example.com/xray.zip', '/usr/local/bin/xray')

        mock_exists.assert_called_once_with('/usr/local/bin/xray')
        mock_remove.assert_not_called()
        mock_makedirs.assert_called_once()
        assert mock_chmod.call_count == 2

    def test_install_xray_distrib_existing_file(self, mocker):
        mocker.patch('app.utils.exists', return_value=True)
        mock_remove = mocker.patch('app.utils.remove')
        mocker.patch('app.utils.dirname', return_value='/usr/local/bin')
        mocker.patch('app.utils.makedirs')
        mocker.patch('app.utils.chmod')
        mock_get = mocker.patch('app.utils.get')
        mock_zipfile = mocker.patch('app.utils.ZipFile')

        mock_response = MagicMock()
        mock_response.content = b'zip_content'
        mock_get.return_value = mock_response

        mock_xray_file = MagicMock()
        mock_xray_file.read.return_value = b'xray_binary'
        mock_zip_instance = MagicMock()
        mock_zip_instance.__enter__.return_value.open.return_value.__enter__.return_value = mock_xray_file
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        mocker.patch('builtins.open', mock_open())

        install_xray_distrib('http://example.com/xray.zip', '/usr/local/bin/xray')

        mock_remove.assert_called_once_with('/usr/local/bin/xray')


class TestIsXrayServiceInstalled:

    def test_is_xray_service_installed_true(self, mocker):
        expected_content = '[Unit]\nDescription=Xray Service\n'
        mocker.patch('app.utils.exists', return_value=True)
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = expected_content
        mocker.patch('builtins.open', mock_open(read_data=expected_content))

        result = is_xray_service_installed('/etc/systemd/system/xray.service')

        assert result is True

    def test_is_xray_service_installed_file_not_exists(self, mocker):
        mock_exists = mocker.patch('app.utils.exists', return_value=False)

        result = is_xray_service_installed('/etc/systemd/system/xray.service')

        assert result is False
        mock_exists.assert_called_once_with('/etc/systemd/system/xray.service')

    def test_is_xray_service_installed_different_content(self, mocker):
        expected_content = '[Unit]\nDescription=Xray Service\n'
        actual_content = '[Unit]\nDescription=Different Service\n'
        mocker.patch('app.utils.exists', return_value=True)
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = expected_content
        mocker.patch('builtins.open', mock_open(read_data=actual_content))

        result = is_xray_service_installed('/etc/systemd/system/xray.service')

        assert result is False


class TestInstallXrayService:
    def test_install_xray_service_success(self, mocker):
        service_content = '[Unit]\nDescription=Xray Service\n'
        mock_app_resources = mocker.patch(
            'app.utils.app_resources.joinpath'
        ).return_value
        mock_app_resources.read_text.return_value = service_content
        mock_write_text_file = mocker.patch('app.utils.write_text_file')
        mock_run_command = mocker.patch('app.utils.run_command', return_value=(0, '', ''))

        install_xray_service('/etc/systemd/system/xray.service')

        mock_write_text_file.assert_called_once_with(
            '/etc/systemd/system/xray.service',
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


class TestDetectVeepeeenetVersions:

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
