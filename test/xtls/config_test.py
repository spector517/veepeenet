import unittest
import argparse
import os.path
import json

import mockito

import common
import xray


class ConfigTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    hostname = '192.168.1.101'
    private_key = 'iL90SiQVSG4TzYyvLsOKP9unFSalPlagjE7_-tmX5XE_2'
    public_key = 'nVvbwNvhA7iiS77f2UkFR5h4lZxAnkryO7ZkkqK1eyo_2'
    config_path = os.path.join('xtls', 'res', 'config.json')

    @classmethod
    def tearDownClass(cls) -> None:
        common.RESULT = cls.original_result

    def setUp(self) -> None:
        gen_keys_stdout = (
            f'Private key: {self.private_key}\n'
            f'Public key: {self.public_key}\n'
        )
        mockito.when(common).run_command('hostname -i').thenReturn((0, self.hostname, None))
        mockito.when(common).run_command('xray x25519').thenReturn((0, gen_keys_stdout, None))

    def tearDown(self) -> None:
        mockito.unstub()

    def test_load_config__no_config_no_args(self) -> None:
        config_path = 'non-existing-config.json'
        namespace = argparse.Namespace(host=None, port=0, reality_host=None,
                                       reality_port=0, no_ufw=False)
        expected_config = {
            'no_ufw': False,
            'server': {
                'host': self.hostname,
                'port': xray.DEFAULT_XRAY_PORT,
                'reality_host': xray.DEFAULT_REALITY_HOST,
                'reality_port': xray.DEFAULT_REALITY_PORT,
                'private_key': self.private_key,
                'public_key': self.public_key
            },
            'clients': common.DEFAULT_CLIENTS
        }
        self.assertEqual(expected_config, xray.load_config(config_path, namespace))

    def test_load_config__no_config_args_exists(self) -> None:
        config_path = 'non-existing-config.json'
        arguments = {
            'host': '123.123.123.123',
            'port': 1010,
            'reality_host': 'reality.com',
            'reality_port': 8443,
            'no_ufw': True
        }
        namespace = argparse.Namespace(**arguments)
        expected_config = {
            'no_ufw': arguments['no_ufw'],
            'server': {
                'host': arguments['host'],
                'port': arguments['port'],
                'reality_host': arguments['reality_host'],
                'reality_port': arguments['reality_port'],
                'private_key': self.private_key,
                'public_key': self.public_key
            },
            'clients': common.DEFAULT_CLIENTS
        }
        actual_cofig = xray.load_config(config_path, namespace)
        self.assertEqual(expected_config, actual_cofig)

    def test_load_config__config_exists_no_args(self) -> None:
        namespace = argparse.Namespace(host=None, port=0, reality_host=None,
                                       reality_port=0, no_ufw=False)
        with open(self.config_path, 'rt', encoding=common.ENCODING) as fd:
            expected_config = json.loads(fd.read())
        self.assertEqual(expected_config, xray.load_config(self.config_path, namespace))

    def test_load_config__mixed(self) -> None:
        changed_port = 9090
        changed_reality_port = 8443
        changed_no_ufw = True
        namespace = argparse.Namespace(host=None, port=changed_port, reality_host=None,
                                       reality_port=changed_reality_port, no_ufw=changed_no_ufw)
        with open(self.config_path, 'rt', encoding=common.ENCODING) as fd:
            expected_config = json.loads(fd.read())
        expected_config['server'].update(
            {'port': changed_port, 'reality_port': changed_reality_port})
        expected_config.update({'no_ufw': changed_no_ufw})
        self.assertEqual(expected_config, xray.load_config(self.config_path, namespace))
