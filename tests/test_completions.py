from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockFixture
from typer import Context

from app.controller.completions import (
    complete_client_name,
    complete_route_name,
    complete_outbound_name,
    complete_vless_outbound_name,
)
from app.controller.common import load_config

CONFIG_PATH = Path('tests/resources/completions_xray_config.json')
CONFIG_EMPTY_PATH = Path('tests/resources/valid_xray_config.json')


def _ctx() -> Context:
    return MagicMock(spec=Context)


class TestCompleteClientName:

    def test_returns_matching_client(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_client_name(_ctx(), [], 'c1'))
        assert results == ['c1.client']

    def test_empty_incomplete_returns_all_clients(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_client_name(_ctx(), [], ''))
        assert results == ['c1.client']

    def test_no_match_returns_empty(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_client_name(_ctx(), [], 'zzz'))
        assert not results

    def test_no_clients_returns_empty(self, mocker: MockFixture):
        config = load_config(CONFIG_EMPTY_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_client_name(_ctx(), [], ''))
        assert not results

    def test_load_error_returns_empty(self, mocker: MockFixture):
        mocker.patch('app.controller.completions.load_config', side_effect=FileNotFoundError)

        results = list(complete_client_name(_ctx(), [], ''))
        assert not results


class TestCompleteRouteName:

    def test_returns_matching_route(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_route_name(_ctx(), [], 'protocol'))
        assert 'protocol' in results

    def test_empty_incomplete_returns_all_routes(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_route_name(_ctx(), [], ''))
        assert len(results) == len(config.routing.rules)

    def test_no_match_returns_empty(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_route_name(_ctx(), [], 'nonexistent_xyz'))
        assert not results

    def test_load_error_returns_empty(self, mocker: MockFixture):
        mocker.patch('app.controller.completions.load_config', side_effect=RuntimeError('fail'))

        results = list(complete_route_name(_ctx(), [], ''))
        assert not results


class TestCompleteOutboundName:

    def test_returns_all_outbound_tags_for_empty_incomplete(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = set(complete_outbound_name(_ctx(), [], ''))
        expected_tags = {
            o.get('tag') if isinstance(o, dict) else o.tag
            for o in config.outbounds
            if (o.get('tag') if isinstance(o, dict) else o.tag)
        }
        assert results == expected_tags

    def test_filters_by_prefix(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_outbound_name(_ctx(), [], 'vl'))
        assert results
        assert all(r.startswith('vl') for r in results)

    def test_no_match_returns_empty(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_outbound_name(_ctx(), [], 'zzz_not_existing'))
        assert not results

    def test_load_error_returns_empty(self, mocker: MockFixture):
        mocker.patch('app.controller.completions.load_config', side_effect=FileNotFoundError)

        results = list(complete_outbound_name(_ctx(), [], ''))
        assert not results


class TestCompleteVlessOutboundName:

    def test_returns_only_vless_outbounds(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_vless_outbound_name(_ctx(), [], ''))
        assert 'vless' in results
        assert 'direct' not in results
        assert 'blackhole' not in results

    def test_filters_vless_by_prefix(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_vless_outbound_name(_ctx(), [], 'vl'))
        assert results
        assert all(r.startswith('vl') for r in results)

    def test_non_vless_prefix_returns_empty(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_vless_outbound_name(_ctx(), [], 'direct'))
        assert not results

    def test_no_outbounds_match_prefix(self, mocker: MockFixture):
        config = load_config(CONFIG_PATH)
        mocker.patch('app.controller.completions.load_config', return_value=config)

        results = list(complete_vless_outbound_name(_ctx(), [], 'zzz'))
        assert not results

    def test_load_error_returns_empty(self, mocker: MockFixture):
        mocker.patch('app.controller.completions.load_config', side_effect=Exception('boom'))

        results = list(complete_vless_outbound_name(_ctx(), [], ''))
        assert not results
