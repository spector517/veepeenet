from sys import getdefaultencoding

from pydantic import ValidationError
from pytest import fixture, raises
from pytest_mock import MockFixture

from app.controller import load_config, config


@fixture
def valid_config_path() -> str:
    return 'tests/resources/valid_xray_config.json'


@fixture
def invalid_config_path() -> str:
    return 'tests/resources/invalid_xray_config.json'


@fixture
def non_existent_config_path() -> str:
    return 'tests/resources/non_existent_config.json'


@fixture
def initial_config_path() -> str:
    return 'tests/resources/initial_xray_config.json'


class TestLoadConfig:

    def test_load_config_success(self,  valid_config_path: str):
        load_config(valid_config_path)

    def test_load_config_validation_errors(self, invalid_config_path: str):
        with raises(ValidationError):
            load_config(invalid_config_path)

    def test_load_config_file_not_found(self, non_existent_config_path: str):
        with raises(FileNotFoundError):
            load_config(non_existent_config_path)


class TestCreateConfig:

    def test_create_config(self, initial_config_path: str, mocker: MockFixture):
        mocker.patch('app.controller.gen_xray_private_key', return_value='very-secret-key')
        from app.controller import create_config
        with open(initial_config_path, 'rt', encoding=getdefaultencoding()) as config_file:
            expected_xray_config_content = config_file.read()

        actual_xray_config = create_config('0.0.0.0', 8443, 'example.com', 443)
        actual_xray_config_content = actual_xray_config.model_dump_json(
            by_alias=True, indent=2, exclude_none=True)

        assert actual_xray_config_content == expected_xray_config_content
