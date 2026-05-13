from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import ValidationError
from pytest import fixture, raises
from pytest_mock import MockFixture
from typer import Exit

from app.controller.common import load_config
from app.controller.commands.configure import config, _select_version
from app.controller.commands.outbound import remove
from app.controller.commands.state import status
from app.model.veepeenet import VeePeeNetStats
from app.model.xray import Xray


@fixture(name='valid_config_path')
def fixture_valid_config_path() -> Path:
    return Path('tests/resources/valid_xray_config.json')


@fixture(name='invalid_config_path')
def fixture_invalid_config_path() -> Path:
    return Path('tests/resources/invalid_xray_config.json')


@fixture(name='non_existent_config_path')
def fixture_non_existent_config_path() -> Path:
    return Path('tests/resources/non_existent_config.json')


@fixture(name='initial_config_path')
def fixture_initial_config_path() -> Path:
    return Path('tests/resources/initial_xray_config.json')


class TestLoadConfig:

    def test_load_config_success(self, valid_config_path: Path):
        load_config(valid_config_path)

    def test_load_config_validation_errors(self, invalid_config_path: Path):
        with raises(ValidationError):
            load_config(invalid_config_path)

    def test_load_config_file_not_found(self, non_existent_config_path: Path):
        with raises(FileNotFoundError):
            load_config(non_existent_config_path)


class TestCreateConfig:

    def test_create_config(self,
                           initial_config_path: Path,
                           non_existent_config_path: Path,
                           tmp_path: Path,
                           mocker: MockFixture):

        mocker.patch(
            'app.controller.commands.configure.gen_xray_private_key',
            return_value='very-secret-key')
        mocker.patch('app.controller.commands.configure.uuid4', return_value='some-uuid')
        save_config_mock = mocker.patch('app.controller.commands.configure.save_config')
        mocker.patch('app.controller.commands.configure.check_root')
        mocker.patch('app.controller.commands.configure.check_distrib')
        mocker.patch(
            'app.controller.commands.configure.XRAY_CONFIG_PATH', non_existent_config_path)
        mocker.patch(
            'app.controller.commands.configure.XRAY_LOGS_PATH', tmp_path / 'logs')
        mocker.patch(
            'app.controller.commands.configure.XRAY_CONFIG_BACKUP_PATH', tmp_path / 'backup.json')

        with open(initial_config_path, 'rt', encoding='utf-8') as config_file:
            expected_xray_config_content = config_file.read()

        config('1.1.1.1', 8443, 'example.com', 443)

        save_config_mock.assert_called_once()
        actual_xray_config = save_config_mock.call_args[0][0]
        actual_xray_config_content = actual_xray_config.model_dump_json(
            by_alias=True, exclude_none=True, indent=2)

        assert actual_xray_config_content == expected_xray_config_content

    def test_create_config_with_name(self,
                                     non_existent_config_path: Path,
                                     tmp_path: Path,
                                     mocker: MockFixture):

        mocker.patch(
            'app.controller.commands.configure.gen_xray_private_key',
            return_value='very-secret-key')
        mocker.patch('app.controller.commands.configure.uuid4', return_value='some-uuid')
        save_config_mock = mocker.patch('app.controller.commands.configure.save_config')
        mocker.patch('app.controller.commands.configure.check_root')
        mocker.patch('app.controller.commands.configure.check_distrib')
        mocker.patch(
            'app.controller.commands.configure.XRAY_CONFIG_PATH', non_existent_config_path)
        mocker.patch(
            'app.controller.commands.configure.XRAY_LOGS_PATH', tmp_path / 'logs')
        mocker.patch(
            'app.controller.commands.configure.XRAY_CONFIG_BACKUP_PATH', tmp_path / 'backup.json')

        config('1.1.1.1', 8443, 'example.com', 443, name='My Server')

        save_config_mock.assert_called_once()
        actual_xray_config = save_config_mock.call_args[0][0]

        assert actual_xray_config.veepeenet.name == 'My Server'


class TestUpdateXrayVersionSelection:

    def test_select_version_finds_prerelease_when_explicit(self, mocker: MockFixture):
        get_releases_mock = mocker.patch(
            'app.controller.commands.configure._get_xray_releases',
            return_value=['v2.0.0', 'v2.0.0-beta', 'v1.9.0'],
        )

        result = _select_version('2.0.0-beta', limit=9)

        assert result == 'v2.0.0-beta'
        get_releases_mock.assert_called_once_with(100, include_prerelease=True)

    def test_select_version_without_explicit_version_keeps_stable_filter(self, mocker: MockFixture):
        mocker.patch(
            'app.controller.commands.configure.stdout_console.print',
        )
        get_releases_mock = mocker.patch(
            'app.controller.commands.configure._get_xray_releases',
            return_value=['v2.0.0', 'v1.9.0'],
        )
        mocker.patch('app.controller.commands.configure.Prompt.ask', return_value='1')

        result = _select_version(None, limit=9)

        assert result == 'v2.0.0'
        get_releases_mock.assert_called_once_with(9)

    def test_select_version_raises_when_prerelease_is_missing(self, mocker: MockFixture):
        mocker.patch(
            'app.controller.commands.configure._get_xray_releases',
            return_value=['v2.0.0', 'v1.9.0'],
        )
        mocker.patch('app.controller.commands.configure.print_error')

        with raises(Exit) as exc_info:
            _select_version('2.0.0-beta', limit=9)

        assert exc_info.value.exit_code == 14


class TestOutboundRemove:

    @fixture(name='valid_config')
    def fixture_valid_config(self):
        return load_config(Path('tests/resources/valid_xray_config.json'))

    def test_remove_outbound_used_in_routing_fails(
            self, valid_config: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.outbound.check_root')
        mocker.patch('app.controller.commands.outbound.check_xray_config')
        mocker.patch('app.controller.commands.outbound.load_config', return_value=valid_config)
        save_config_mock = mocker.patch('app.controller.commands.outbound.save_config')

        with raises(BaseException):
            remove('vless')

        save_config_mock.assert_not_called()

    def test_remove_outbound_not_in_routing_succeeds(
            self, valid_config: Xray, mocker: MockFixture):
        rules = valid_config.routing and valid_config.routing.rules or []
        valid_config.routing.rules = [ # type: ignore
            r for r in rules if r.outbound_tag != 'vless'
        ]
        mocker.patch('app.controller.commands.outbound.check_root')
        mocker.patch('app.controller.commands.outbound.check_xray_config')
        mocker.patch('app.controller.commands.outbound.load_config', return_value=valid_config)
        save_config_mock = mocker.patch('app.controller.commands.outbound.save_config')

        remove('vless')

        save_config_mock.assert_called_once()

    def test_remove_outbound_not_found(
            self, valid_config: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.outbound.check_root')
        mocker.patch('app.controller.commands.outbound.check_xray_config')
        mocker.patch('app.controller.commands.outbound.load_config', return_value=valid_config)
        save_config_mock = mocker.patch('app.controller.commands.outbound.save_config')

        with raises(BaseException):
            remove('nonexistent')

        save_config_mock.assert_not_called()


class TestCollectAndSaveStats:

    def test_does_nothing_if_service_not_running(self, mocker: MockFixture):
        mocker.patch('app.controller.common.is_xray_service_running', return_value=False)
        load_config_mock = mocker.patch('app.controller.common.load_config')

        from app.controller.common import _store_runtime_stats # type: ignore # pylint: disable=import-outside-toplevel
        _store_runtime_stats()

        load_config_mock.assert_not_called()

    def test_saves_accumulated_stats_when_running(self, mocker: MockFixture):
        from app.model.veepeenet import TrafficStats # pylint: disable=import-outside-toplevel
        from app.controller.common import _store_runtime_stats # type: ignore # pylint: disable=import-outside-toplevel

        config_path = Path('tests/resources/valid_xray_config_with_clients.json')
        xray_config = load_config(config_path)

        mocker.patch('app.controller.common.is_xray_service_running', return_value=True)
        mocker.patch('app.controller.common.XRAY_CONFIG_PATH', config_path)
        mocker.patch('app.controller.common.load_config', return_value=xray_config)
        save_mock = mocker.patch('app.controller.common.save_config')
        runtime_stats = VeePeeNetStats(
            client={'c1.client': TrafficStats(uplink=100, downlink=200)}
        )
        mocker.patch('app.controller.common.get_runtime_stats', return_value=runtime_stats)

        _store_runtime_stats()

        save_mock.assert_called_once()
        saved_config: Xray = save_mock.call_args[0][0]
        assert saved_config.veepeenet is not None
        assert saved_config.veepeenet.stats.client.get('c1.client') is not None
        assert saved_config.veepeenet.stats.client['c1.client'].uplink == 100
        assert saved_config.veepeenet.stats.client['c1.client'].downlink == 200


class TestStatusRestartRequired:

    @fixture(name='valid_config_for_status')
    def fixture_valid_config_for_status(self) -> Xray:
        return load_config(Path('tests/resources/valid_xray_config.json'))

    def test_status_does_not_require_restart_for_same_json_content(
            self, valid_config_for_status: Xray, mocker: MockFixture):
        server_view = MagicMock()
        server_view.model_dump_json.return_value = '{}'
        server_view.rich_repr.return_value = 'server-view'

        mocker.patch('app.controller.commands.state.check_xray_config')
        mocker.patch('app.controller.commands.state.check_distrib')
        mocker.patch('app.controller.commands.state.load_config', return_value=valid_config_for_status)
        mocker.patch(
            'app.controller.commands.state.get_vless_inbound',
            return_value=valid_config_for_status.get_vless_inbound())
        mocker.patch(
            'app.controller.commands.state.detect_veepeenet_versions',
            return_value=SimpleNamespace(veepeenet_version='v2.5.0', veepeenet_build=1))
        mocker.patch('app.controller.commands.state.get_xray_distrib_version', return_value='1.8.0')
        mocker.patch('app.controller.commands.state.is_xray_service_running', return_value=True)
        mocker.patch('app.controller.commands.state.is_xray_service_enabled', return_value=True)
        mocker.patch('app.controller.commands.state.get_xray_service_uptime', return_value='1h')
        mocker.patch(
            'app.controller.commands.state.get_stored_stats',
            return_value=VeePeeNetStats())
        mocker.patch(
            'app.controller.commands.state.get_runtime_stats',
            return_value=VeePeeNetStats())
        mocker.patch('app.controller.commands.state.get_routing_view', return_value=MagicMock())
        mocker.patch('app.controller.commands.state.get_clients_view', return_value=MagicMock())
        mocker.patch(
            'app.controller.commands.state.get_outbounds_view',
            return_value=SimpleNamespace(outbounds=[]))
        compare_mock = mocker.patch(
            'app.controller.commands.state.is_json_content_same',
            return_value=True)
        server_view_ctor = mocker.patch(
            'app.controller.commands.state.ServerView',
            return_value=server_view)
        print_mock = mocker.patch('app.controller.commands.state.stdout_console.print')

        status()

        assert server_view_ctor.call_args.kwargs['restart_required'] is False
        compare_mock.assert_called_once()
        assert compare_mock.call_args.kwargs == {'exclude_top_level_keys': {'veepeenet'}}
        print_mock.assert_called_once_with('server-view')

    def test_status_requires_restart_for_different_json_content(
            self, valid_config_for_status: Xray, mocker: MockFixture):
        server_view = MagicMock()
        server_view.model_dump_json.return_value = '{}'
        server_view.rich_repr.return_value = 'server-view'

        mocker.patch('app.controller.commands.state.check_xray_config')
        mocker.patch('app.controller.commands.state.check_distrib')
        mocker.patch('app.controller.commands.state.load_config', return_value=valid_config_for_status)
        mocker.patch(
            'app.controller.commands.state.get_vless_inbound',
            return_value=valid_config_for_status.get_vless_inbound())
        mocker.patch(
            'app.controller.commands.state.detect_veepeenet_versions',
            return_value=SimpleNamespace(veepeenet_version='v2.5.0', veepeenet_build=1))
        mocker.patch('app.controller.commands.state.get_xray_distrib_version', return_value='1.8.0')
        mocker.patch('app.controller.commands.state.is_xray_service_running', return_value=False)
        mocker.patch('app.controller.commands.state.is_xray_service_enabled', return_value=False)
        mocker.patch(
            'app.controller.commands.state.get_stored_stats',
            return_value=VeePeeNetStats())
        mocker.patch(
            'app.controller.commands.state.get_runtime_stats',
            return_value=VeePeeNetStats())
        mocker.patch('app.controller.commands.state.get_routing_view', return_value=MagicMock())
        mocker.patch('app.controller.commands.state.get_clients_view', return_value=MagicMock())
        mocker.patch(
            'app.controller.commands.state.get_outbounds_view',
            return_value=SimpleNamespace(outbounds=[]))
        compare_mock = mocker.patch(
            'app.controller.commands.state.is_json_content_same',
            return_value=False)
        server_view_ctor = mocker.patch(
            'app.controller.commands.state.ServerView',
            return_value=server_view)
        mocker.patch('app.controller.commands.state.stdout_console.print')

        status()

        assert server_view_ctor.call_args.kwargs['restart_required'] is True
        compare_mock.assert_called_once()
        assert compare_mock.call_args.kwargs == {'exclude_top_level_keys': {'veepeenet'}}
