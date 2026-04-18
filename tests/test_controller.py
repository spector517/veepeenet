from pathlib import Path

from pydantic import ValidationError
from pytest import fixture, raises
from pytest_mock import MockFixture

from app.controller.common import load_config
from app.controller.commands.configure import config
from app.controller.commands.outbound import remove
from app.defaults import EXIT_OUTBOUND_IN_USE, EXIT_OUTBOUND_NOT_FOUND
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

        with raises(SystemExit) as exc_info:
            remove('vless')

        assert exc_info.value.code == EXIT_OUTBOUND_IN_USE
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

        with raises(SystemExit) as exc_info:
            remove('nonexistent')

        assert exc_info.value.code == EXIT_OUTBOUND_NOT_FOUND
        save_config_mock.assert_not_called()
