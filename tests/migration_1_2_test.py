from json import dumps as json_dump
from pathlib import Path

from pytest import fixture, raises

from app.migration_1_2 import migrate_xray_config


@fixture(name='xray_v1_config_path')
def fixture_xray_v1_config_path() -> Path:
    return Path('tests/resources/xray_v1_config.json')

@fixture(name='xray_v1_config_migrated_config_path')
def fixture_xray_v1_migrated_config_path() -> Path:
    return Path('tests/resources/xray_v1_migrated_to_v2_config.json')

@fixture(name='invalid_xray_config_path')
def fixture_invalid_xray_config_path() -> Path:
    return Path('tests/resources/invalid_xray_config.json')

@fixture(name='tmp_result_path')
def fixture_tmp_result_path() -> Path:
    return Path('tests/resources/_tmp_result.json')


class TestMigration12:

    def test_migrate_xray_config(
            self, xray_v1_config_path: Path,
            xray_v1_config_migrated_config_path: Path,
            tmp_result_path: Path
    ):
        expected_content = xray_v1_config_migrated_config_path.read_text('utf-8')

        try:
            tmp_result_path.unlink(missing_ok=True)
            migrate_xray_config('126.6.6.6', xray_v1_config_path, tmp_result_path)
            actual_content = tmp_result_path.read_text('utf-8')
        finally:
            tmp_result_path.unlink(missing_ok=True)

        assert actual_content == expected_content

    def test_migrate_xray_config_not_found(self, tmp_result_path: Path):
        non_existent_path = Path('tests/resources/non_existent_config.json')

        try:
            tmp_result_path.unlink(missing_ok=True)
            with raises(FileNotFoundError):
                migrate_xray_config('126.6.6.6', non_existent_path, tmp_result_path)
        finally:
            tmp_result_path.unlink(missing_ok=True)

    def test_migrate_xray_config_invalid(
            self, invalid_xray_config_path: Path, tmp_result_path: Path):
        try:
            tmp_result_path.unlink(missing_ok=True)
            with raises(Exception):
                migrate_xray_config('126.6.6.6', invalid_xray_config_path, tmp_result_path)
        finally:
            tmp_result_path.unlink(missing_ok=True)

    def test_migrate_xray_config_mismatch_clients_and_short_ids(self, tmp_result_path: Path):
        tmp_config = Path('tests/resources/_tmp_mismatch_config.json')

        mismatch_config = {
            "inbounds": [
                {
                    "port": 443,
                    "protocol": "vless",
                    "tag": "vless-inbound",
                    "settings": {
                        "clients": [
                            {
                                "id": "cc92829e-79dd-4b8d-b456-01948c1801f0",
                                "email": "client1@0.0.0.0",
                                "flow": "xtls-rprx-vision"
                            },
                            {
                                "id": "7d623932-5967-4bf6-a692-7652fa7964cf",
                                "email": "client2@0.0.0.0",
                                "flow": "xtls-rprx-vision"
                            }
                        ],
                        "decryption": "none"
                    },
                    "streamSettings": {
                        "network": "raw",
                        "security": "reality",
                        "realitySettings": {
                            "dest": "yahoo.com:443",
                            "serverNames": ["yahoo.com"],
                            "privateKey": "private-key",
                            "shortIds": ["0001", "1245", "5678"]
                        }
                    }
                }
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "tag": "direct-outbound"
                }
            ]
        }

        try:
            tmp_config.write_text(json_dump(mismatch_config), encoding='utf-8')
            tmp_result_path.unlink(missing_ok=True)

            with raises(ValueError, match="Number of clients does not match number of short IDs"):
                migrate_xray_config('126.6.6.6', tmp_config, tmp_result_path)
        finally:
            tmp_config.unlink(missing_ok=True)
            tmp_result_path.unlink(missing_ok=True)
