from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import ValidationError
from pytest import fixture, raises
from pytest_mock import MockFixture
from typer import Exit

from app.controller.common import load_config
from app.controller.commands.clients import disable, enable, get_clients_view
from app.controller.commands.configure import config, _select_version
from app.controller.commands.outbound import remove
from app.controller.commands.routing import add_rule, change_rule, get_routing_view, set_rule_priority
from app.controller.commands.state import status, reset_stats, store_stats
from app.defaults import (
    DISABLED_CLIENTS_RULE_NAME,
    DISABLED_CLIENTS_RULE_PRIORITY,
    EXIT_CLIENTS_ERROR,
    EXIT_ROUTING_CLIENT_NOT_FOUND,
    EXIT_ROUTING_INVALID_PRIORITY,
)
from app.model.api import Stats
from app.model.routing import Rule
from app.model.veepeenet import VeePeeNetStats, TrafficStats
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
        load_stats_mock = mocker.patch('app.controller.common.load_stats')

        from app.controller.common import _store_runtime_stats # type: ignore # pylint: disable=import-outside-toplevel
        _store_runtime_stats()

        load_stats_mock.assert_not_called()

    def test_saves_accumulated_stats_when_running(self, mocker: MockFixture):
        from app.controller.common import _store_runtime_stats # type: ignore # pylint: disable=import-outside-toplevel

        mocker.patch('app.controller.common.is_xray_service_running', return_value=True)
        mocker.patch('app.controller.common.load_stats', return_value=VeePeeNetStats())
        save_mock = mocker.patch('app.controller.common.save_stats')
        runtime_stats = VeePeeNetStats(
            client={'c1.client': TrafficStats(uplink=100, downlink=200)}
        )
        runtime_mock = mocker.patch(
            'app.controller.common.get_runtime_stats', return_value=runtime_stats)

        _store_runtime_stats()

        runtime_mock.assert_called_once_with(reset=True)
        save_mock.assert_called_once()
        saved_stats = save_mock.call_args[0][0]
        assert saved_stats.client.get('c1.client') is not None
        assert saved_stats.client['c1.client'].uplink == 100
        assert saved_stats.client['c1.client'].downlink == 200


class TestStoreStatsCommand:

    def test_saves_runtime_stats_from_api(self, mocker: MockFixture):
        check_root_mock = mocker.patch('app.controller.commands.state.check_root')
        mocker.patch(
            'app.controller.commands.state.query_xray_stats',
            return_value=[
                Stats(name='user>>>alice.123@0.0.0.0>>>traffic>>>uplink', value=100),
                Stats(name='inbound>>>vless-inbound>>>traffic>>>downlink', value=200),
            ])
        mocker.patch(
            'app.controller.commands.state.get_stored_stats',
            return_value=VeePeeNetStats(
                client={'alice': TrafficStats(uplink=5, downlink=0)}))
        save_mock = mocker.patch('app.controller.commands.state.save_stats')

        store_stats()

        check_root_mock.assert_called_once()
        save_mock.assert_called_once()
        saved_stats = save_mock.call_args[0][0]
        assert saved_stats.client['alice'].uplink == 105
        assert saved_stats.inbound['vless-inbound'].downlink == 200

    def test_does_nothing_when_api_has_no_stats(self, mocker: MockFixture):
        mocker.patch('app.controller.commands.state.check_root')
        mocker.patch('app.controller.commands.state.query_xray_stats', return_value=[])
        stored_mock = mocker.patch('app.controller.commands.state.get_stored_stats')
        save_mock = mocker.patch('app.controller.commands.state.save_stats')

        store_stats()

        stored_mock.assert_not_called()
        save_mock.assert_not_called()

    def test_raises_when_not_root(self, mocker: MockFixture):
        mocker.patch(
            'app.controller.commands.state.check_root',
            side_effect=Exit(code=1))
        query_mock = mocker.patch('app.controller.commands.state.query_xray_stats')

        with raises(Exit) as exc_info:
            store_stats(_debug=True)

        assert exc_info.value.exit_code == 1
        query_mock.assert_not_called()


class TestClearStats:

    def test_resets_only_stats_file_if_service_not_running(self, mocker: MockFixture):
        mocker.patch('app.controller.common.is_xray_service_running', return_value=False)
        reset_mock = mocker.patch('app.controller.common.reset_xray_stats')
        save_mock = mocker.patch('app.controller.common.save_stats')
        print_mock = mocker.patch('app.controller.common.stdout_console.print')

        from app.controller.common import clear_stats # pylint: disable=import-outside-toplevel
        clear_stats()

        reset_mock.assert_not_called()
        save_mock.assert_called_once()
        saved_stats = save_mock.call_args[0][0]
        assert saved_stats == VeePeeNetStats()
        print_mock.assert_called_once()

    def test_resets_stats_file_and_api_if_service_running(self, mocker: MockFixture):
        mocker.patch('app.controller.common.is_xray_service_running', return_value=True)
        reset_mock = mocker.patch('app.controller.common.reset_xray_stats', return_value=True)
        save_mock = mocker.patch('app.controller.common.save_stats')

        from app.controller.common import clear_stats # pylint: disable=import-outside-toplevel
        clear_stats()

        reset_mock.assert_called_once()
        save_mock.assert_called_once()
        saved_stats = save_mock.call_args[0][0]
        assert saved_stats == VeePeeNetStats()

    def test_raises_if_api_reset_fails(self, mocker: MockFixture):
        mocker.patch('app.controller.common.is_xray_service_running', return_value=True)
        mocker.patch('app.controller.common.reset_xray_stats', return_value=False)
        save_mock = mocker.patch('app.controller.common.save_stats')

        from app.controller.common import clear_stats # pylint: disable=import-outside-toplevel
        with raises(RuntimeError, match='Failed to reset Xray API stats'):
            clear_stats()

        save_mock.assert_not_called()


class TestResetStatsCommand:

    def test_runs_checks_and_clears_stats(self, mocker: MockFixture):
        check_root_mock = mocker.patch('app.controller.commands.state.check_root')
        check_xray_config_mock = mocker.patch('app.controller.commands.state.check_xray_config')
        check_distrib_mock = mocker.patch('app.controller.commands.state.check_distrib')
        clear_stats_mock = mocker.patch('app.controller.commands.state.clear_stats')

        reset_stats()

        check_root_mock.assert_called_once()
        check_xray_config_mock.assert_called_once()
        check_distrib_mock.assert_called_once()
        clear_stats_mock.assert_called_once()


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


class TestRoutingPriorityValidation:

    @fixture(name='valid_config_for_routing')
    def fixture_valid_config_for_routing(self) -> Xray:
        return load_config(Path('tests/resources/valid_xray_config.json'))

    def test_add_rule_rejects_negative_priority(
            self, valid_config_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch('app.controller.commands.routing.load_config', return_value=valid_config_for_routing)
        save_mock = mocker.patch('app.controller.commands.routing.save_config')
        print_error_mock = mocker.patch('app.controller.commands.routing.print_error')

        with raises(Exit) as exc_info:
            add_rule('test', 'direct', domain=['domain:example.com'], priority=-1, _debug=True)

        assert exc_info.value.exit_code == EXIT_ROUTING_INVALID_PRIORITY
        save_mock.assert_not_called()
        print_error_mock.assert_called_once()

    def test_add_rule_rejects_priority_above_limit(
            self, valid_config_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch('app.controller.commands.routing.load_config', return_value=valid_config_for_routing)
        save_mock = mocker.patch('app.controller.commands.routing.save_config')

        with raises(Exit) as exc_info:
            add_rule('test', 'direct', domain=['domain:example.com'], priority=1_000_001, _debug=True)

        assert exc_info.value.exit_code == EXIT_ROUTING_INVALID_PRIORITY
        save_mock.assert_not_called()

    def test_add_rule_accepts_zero_priority(
            self, valid_config_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch('app.controller.commands.routing.load_config', return_value=valid_config_for_routing)
        mocker.patch('app.controller.commands.routing.install_geo_data')
        save_mock = mocker.patch('app.controller.commands.routing.save_config')
        mocker.patch('app.controller.commands.routing.stdout_console.print')

        add_rule('test', 'direct', domain=['domain:example.com'], priority=0)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        saved_rules = saved_config.routing.rules if saved_config.routing else []
        assert saved_rules is not None
        assert any(rule.tag == 'test.0' for rule in saved_rules)

    def test_add_rule_accepts_upper_boundary_priority(
            self, valid_config_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch('app.controller.commands.routing.load_config', return_value=valid_config_for_routing)
        mocker.patch('app.controller.commands.routing.install_geo_data')
        save_mock = mocker.patch('app.controller.commands.routing.save_config')
        mocker.patch('app.controller.commands.routing.stdout_console.print')

        add_rule('test', 'direct', domain=['domain:example.com'], priority=1_000_000)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        saved_rules = saved_config.routing.rules if saved_config.routing else []
        assert saved_rules is not None
        assert any(rule.tag == 'test.1000000' for rule in saved_rules)

    def test_set_rule_priority_rejects_negative_priority(
            self, valid_config_for_routing: Xray, mocker: MockFixture):
        valid_config_for_routing.routing.rules = [ # type: ignore[assignment]
            Rule(tag='test.10', outbound_tag='direct', domain=['domain:example.com'])
        ]
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch('app.controller.commands.routing.load_config', return_value=valid_config_for_routing)
        save_mock = mocker.patch('app.controller.commands.routing.save_config')

        with raises(Exit) as exc_info:
            set_rule_priority('test', -1, _debug=True)

        assert exc_info.value.exit_code == EXIT_ROUTING_INVALID_PRIORITY
        save_mock.assert_not_called()

    def test_set_rule_priority_rejects_priority_above_limit(
            self, valid_config_for_routing: Xray, mocker: MockFixture):
        valid_config_for_routing.routing.rules = [ # type: ignore[assignment]
            Rule(tag='test.10', outbound_tag='direct', domain=['domain:example.com'])
        ]
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch('app.controller.commands.routing.load_config', return_value=valid_config_for_routing)
        save_mock = mocker.patch('app.controller.commands.routing.save_config')

        with raises(Exit) as exc_info:
            set_rule_priority('test', 1_000_001, _debug=True)

        assert exc_info.value.exit_code == EXIT_ROUTING_INVALID_PRIORITY
        save_mock.assert_not_called()

    def test_get_routing_view_hides_service_rules(self, valid_config_for_routing: Xray):
        valid_config_for_routing.routing.rules = [ # type: ignore[assignment]
            Rule(tag='visible.10', outbound_tag='direct', domain=['domain:example.com']),
            Rule(tag='hidden.-1', outbound_tag='blackhole', protocol=['bittorrent']),
            Rule(tag='hidden.1000001', outbound_tag='dns', port='53'),
        ]

        view = get_routing_view(valid_config_for_routing)

        rules = view.model_dump()['rules'] or []
        assert len(rules) == 1
        assert rules[0]['name'] == 'visible'
        assert rules[0]['priority'] == 10


class TestRoutingClientCondition:

    @fixture(name='config_with_clients_for_routing')
    def fixture_config_with_clients_for_routing(self) -> Xray:
        return load_config(Path('tests/resources/valid_xray_config_with_clients.json'))

    def test_add_rule_with_client_succeeds(
            self, config_with_clients_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch(
            'app.controller.commands.routing.load_config',
            return_value=config_with_clients_for_routing)
        mocker.patch('app.controller.commands.routing.install_geo_data')
        save_mock = mocker.patch('app.controller.commands.routing.save_config')
        mocker.patch('app.controller.commands.routing.stdout_console.print')

        add_rule('client-rule', 'direct', client=['c1.client'], _debug=True)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        saved_rule = saved_config.routing.rules[-1] # type: ignore[index]
        assert saved_rule.user == ['c1.client.0001@0.0.0.0']

    def test_add_rule_with_unknown_client_fails(
            self, config_with_clients_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch(
            'app.controller.commands.routing.load_config',
            return_value=config_with_clients_for_routing)
        mocker.patch('app.controller.commands.routing.install_geo_data')
        save_mock = mocker.patch('app.controller.commands.routing.save_config')

        with raises(Exit) as exc_info:
            add_rule('client-rule', 'direct', client=['missing'], _debug=True)

        assert exc_info.value.exit_code == EXIT_ROUTING_CLIENT_NOT_FOUND
        save_mock.assert_not_called()

    def test_change_rule_put_client_adds_email(
            self, config_with_clients_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch(
            'app.controller.commands.routing.load_config',
            return_value=config_with_clients_for_routing)
        mocker.patch('app.controller.commands.routing.install_geo_data')
        save_mock = mocker.patch('app.controller.commands.routing.save_config')
        mocker.patch('app.controller.commands.routing.stdout_console.print')

        add_rule('client-rule', 'direct', domain=['domain:example.com'], _debug=True)
        save_mock.reset_mock()

        change_rule('client-rule', 'put', client=['c1.client'], _debug=True)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        saved_rule = saved_config.routing.rules[-1] # type: ignore[index]
        assert saved_rule.user == ['c1.client.0001@0.0.0.0']

    def test_change_rule_del_client_removes_email(
            self, config_with_clients_for_routing: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.routing.check_root')
        mocker.patch('app.controller.commands.routing.check_xray_config')
        mocker.patch(
            'app.controller.commands.routing.load_config',
            return_value=config_with_clients_for_routing)
        mocker.patch('app.controller.commands.routing.install_geo_data')
        save_mock = mocker.patch('app.controller.commands.routing.save_config')
        mocker.patch('app.controller.commands.routing.stdout_console.print')

        add_rule('client-rule', 'direct', client=['c1.client'], _debug=True)
        save_mock.reset_mock()

        change_rule('client-rule', 'del', client=['c1.client'], _debug=True)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        saved_rule = saved_config.routing.rules[-1] # type: ignore[index]
        assert saved_rule.user is None


class TestDisableEnableClients:

    @fixture(name='config_with_clients_for_clients_commands')
    def fixture_config_with_clients_for_clients_commands(self) -> Xray:
        config = load_config(Path('tests/resources/valid_xray_config_with_clients.json'))
        inbound = config.get_vless_inbound()
        if inbound and inbound.settings.clients:
            inbound.settings.clients[0].id = '12345678-1234-5678-1234-567812345678'
        return config

    def test_disable_creates_system_rule(
            self, config_with_clients_for_clients_commands: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.clients.check_root')
        mocker.patch('app.controller.commands.clients.check_xray_config')
        mocker.patch(
            'app.controller.commands.clients.load_config',
            return_value=config_with_clients_for_clients_commands)
        save_mock = mocker.patch('app.controller.commands.clients.save_config')
        mocker.patch('app.controller.commands.clients.stdout_console.print')

        disable(['c1.client'], _debug=True)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        disabled_rule = next(
            rule for rule in saved_config.routing.rules or []
            if rule.tag == f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}')
        assert disabled_rule.outbound_tag == 'blackhole'
        assert disabled_rule.user == ['c1.client.0001@0.0.0.0']

    def test_disable_unknown_client_fails_without_save(
            self, config_with_clients_for_clients_commands: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.clients.check_root')
        mocker.patch('app.controller.commands.clients.check_xray_config')
        mocker.patch(
            'app.controller.commands.clients.load_config',
            return_value=config_with_clients_for_clients_commands)
        mocker.patch('app.controller.commands.clients.print_error')
        save_mock = mocker.patch('app.controller.commands.clients.save_config')

        with raises(Exit) as exc_info:
            disable(['missing'], _debug=True)

        assert exc_info.value.exit_code == EXIT_CLIENTS_ERROR
        save_mock.assert_not_called()

    def test_enable_removes_rule_for_last_disabled_client(
            self, config_with_clients_for_clients_commands: Xray, mocker: MockFixture):
        config_with_clients_for_clients_commands.routing.rules.append( # type: ignore[union-attr]
            Rule(
                tag=f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}',
                outbound_tag='blackhole',
                user=['c1.client.0001@0.0.0.0'],
            ))
        mocker.patch('app.controller.commands.clients.check_root')
        mocker.patch('app.controller.commands.clients.check_xray_config')
        mocker.patch(
            'app.controller.commands.clients.load_config',
            return_value=config_with_clients_for_clients_commands)
        save_mock = mocker.patch('app.controller.commands.clients.save_config')
        mocker.patch('app.controller.commands.clients.stdout_console.print')

        enable(['c1.client'], _debug=True)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        assert all(
            rule.tag != f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}'
            for rule in saved_config.routing.rules or []
        )

    def test_enable_already_enabled_skips_without_save(
            self, config_with_clients_for_clients_commands: Xray, mocker: MockFixture):
        mocker.patch('app.controller.commands.clients.check_root')
        mocker.patch('app.controller.commands.clients.check_xray_config')
        mocker.patch(
            'app.controller.commands.clients.load_config',
            return_value=config_with_clients_for_clients_commands)
        save_mock = mocker.patch('app.controller.commands.clients.save_config')
        mocker.patch('app.controller.commands.clients.stdout_console.print')

        enable(['c1.client'], _debug=True)

        save_mock.assert_not_called()

    def test_get_clients_view_marks_disabled_clients(
            self, config_with_clients_for_clients_commands: Xray, mocker: MockFixture):
        config_with_clients_for_clients_commands.routing.rules.append( # type: ignore[union-attr]
            Rule(
                tag=f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}',
                outbound_tag='blackhole',
                user=['c1.client.0001@0.0.0.0'],
            ))
        mocker.patch('app.controller.commands.clients.get_vless_client_url', return_value='vless://test')

        view = get_clients_view(config_with_clients_for_clients_commands)

        assert view.clients[0].disabled is True

    def test_remove_client_drops_disabled_email_from_rule(
            self, config_with_clients_for_clients_commands: Xray, mocker: MockFixture):
        from app.controller.commands.clients import remove as remove_clients

        config_with_clients_for_clients_commands.routing.rules.append( # type: ignore[union-attr]
            Rule(
                tag=f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}',
                outbound_tag='blackhole',
                user=['c1.client.0001@0.0.0.0'],
            ))
        mocker.patch('app.controller.commands.clients.check_root')
        mocker.patch('app.controller.commands.clients.check_xray_config')
        mocker.patch(
            'app.controller.commands.clients.load_config',
            return_value=config_with_clients_for_clients_commands)
        save_mock = mocker.patch('app.controller.commands.clients.save_config')
        mocker.patch('app.controller.commands.clients.stdout_console.print')

        remove_clients(['c1.client'], _debug=True)

        save_mock.assert_called_once()
        saved_config = save_mock.call_args[0][0]
        assert all(
            rule.tag != f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}'
            for rule in saved_config.routing.rules or []
        )
