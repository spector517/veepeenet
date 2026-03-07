from pathlib import Path

from pydantic import ValidationError
from pytest import fixture, raises
from pytest_mock import MockFixture

from app.controller.common import load_config
from app.controller.commands.configure import config


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

    def test_create_config(self, initial_config_path: Path, mocker: MockFixture):
        mocker.patch(
            'app.controller.commands.configure.gen_xray_private_key',
            return_value='very-secret-key')
        mocker.patch('app.controller.commands.configure.uuid4', return_value='some-uuid')
        write_text_file_mock = mocker.patch('app.controller.commands.configure.write_text_file')
        mocker.patch('app.controller.commands.configure.check_and_install')

        with open(initial_config_path, 'rt', encoding='utf-8') as config_file:
            expected_xray_config_content = config_file.read()

        config('1.1.1.1', 8443, 'example.com', 443)

        write_text_file_mock.assert_called_once()
        actual_xray_config_content = write_text_file_mock.call_args[0][1]

        assert actual_xray_config_content == expected_xray_config_content
