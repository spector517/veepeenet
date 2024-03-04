import argparse
import json
import os
import shutil
import unittest

import common
import wireguard


class ConfigTest(unittest.TestCase):
    temp_dir = 'tmp'
    encoding = 'UTF-8'
    config_path = os.path.join(temp_dir, 'config.json')
    clients_dir_path = os.path.join(temp_dir, 'test_clients')
    no_ufw = False
    original_result = common.RESULT.copy()
    original_check_mode = common.CHECK_MODE
    original_config_path = common.CONFIG_PATH
    original_clients_dir = common.DEFAULT_CLIENTS_DIR

    @classmethod
    def setUpClass(cls) -> None:
        common.CHECK_MODE = True
        common.CONFIG_PATH = cls.config_path
        common.DEFAULT_CLIENTS_DIR = cls.clients_dir_path

    @classmethod
    def tearDownClass(cls) -> None:
        # FIXME Why cls.original_result is not empty?
        common.RESULT = cls.original_result
        common.CHECK_MODE = cls.original_check_mode
        common.CONFIG_PATH = cls.original_config_path
        common.DEFAULT_CLIENTS_DIR = cls.original_clients_dir

    def setUp(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.mkdir(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_load_config__no_config_no_args(self) -> None:
        config_path = 'non-existing-config.json'
        namespace = argparse.Namespace(host=None, port=0, subnet=None, interface=None, dns=None,
                                       output=None, no_ufw=False)
        expected_config = {
            'clients_dir': common.DEFAULT_CLIENTS_DIR,
            'no_ufw': False,
            'server': {
                'host': 'hostname -i',
                'port': wireguard.DEFAULT_WIREGUARD_PORT,
                'subnet': wireguard.DEFAULT_WIREGUARD_SUBNET,
                'interface': wireguard.DEFAULT_WIREGUARD_INTERFACE,
                'dns': common.DEFAULT_DNS,
                'private_key': 'wg genkey',
                'public_key': 'wg pubkey'
            },
            'clients': common.DEFAULT_CLIENTS
        }
        self.assertEqual(expected_config, wireguard.load_config(config_path, namespace))

    def test_load_config__no_config_args_exists(self) -> None:
        config_path = 'non-existing-config.json'
        arguments = {
            'host': '123.123.123.123',
            'port': 1010,
            'subnet': '10.5.0.1/24',
            'interface': 'wg7',
            'dns': ['8.8.8.8', '8.8.4.4'],
            'output': self.clients_dir_path,
            'no_ufw': True
        }
        namespace = argparse.Namespace(**arguments)
        expected_config = {
            'clients_dir': self.clients_dir_path,
            'no_ufw': True,
            'server': {
                'host': arguments['host'],
                'port': arguments['port'],
                'subnet': arguments['subnet'],
                'interface': arguments['interface'],
                'dns': arguments['dns'],
                'private_key': 'wg genkey',
                'public_key': 'wg pubkey'
            },
            'clients': common.DEFAULT_CLIENTS
        }
        actual_cofig = wireguard.load_config(config_path, namespace)
        self.assertEqual(expected_config, actual_cofig)

    def test_load_config__config_exists_no_args(self) -> None:
        config = {
            'clients_dir': self.clients_dir_path,
            'no_ufw': True,
            'server': {
                'host': '123.123.123.123',
                'port': 1010,
                'subnet': '10.5.0.1/24',
                'interface': 'wg7',
                'dns': ['8.8.8.8', '8.8.4.4'],
                'private_key': 'server_private_key',
                'public_key': 'server_public_key'
            },
            'clients': [{
                'name': 'client_name',
                'ip': 'client_ip',
                'public_key': 'client_public_key',
                'private_key': 'client_private_key'
            }]
        }
        namespace = argparse.Namespace(host=None, port=0, subnet=None, interface=None, dns=None,
                                       output=None, no_ufw=False)
        with open(self.config_path, 'wt', encoding=self.encoding) as fd:
            fd.write(json.dumps(config))
        expected_config = config
        self.assertEqual(expected_config, wireguard.load_config(self.config_path, namespace))

    def test_load_config__mixed(self) -> None:
        config = {
            'clients_dir': self.clients_dir_path,
            'no_ufw': False,
            'server': {
                'host': '123.123.123.123',
                'dns': ['8.8.8.8', '8.8.4.4'],
                'private_key': 'server_private_key',
                'public_key': 'server_public_key'
            },
            'clients': [{
                'name': 'client_name',
                'ip': 'client_ip',
                'public_key': 'client_public_key',
                'private_key': 'client_private_key'
            }]
        }
        with open(self.config_path, 'wt', encoding=self.encoding) as fd:
            fd.write(json.dumps(config))
        namespace = argparse.Namespace(host=None, port=0, subnet='11.5.0.1/24', interface='wg2',
                                       dns=None, output=self.clients_dir_path, no_ufw=True)
        expected_config = config
        expected_config.update({
            'clients_dir': self.clients_dir_path,
            'no_ufw': True
        })
        expected_config['server'].update({
            'port': wireguard.DEFAULT_WIREGUARD_PORT,
            'subnet': namespace.subnet,
            'interface': namespace.interface
        })
        self.assertEqual(expected_config, wireguard.load_config(self.config_path, namespace))

    def test_clean_configuration__config_and_clients_dir_not_exists(self) -> None:
        common.clean_configuration(self.config_path, self.clients_dir_path)

        self.assertFalse(os.path.exists(self.config_path))
        self.assertFalse(os.path.exists(self.clients_dir_path))

    def test_clean_configuration__config_and_clients_dir_exists(self) -> None:
        with open(self.config_path, 'wt', encoding=self.encoding) as fd:
            fd.write("some config data")
        os.mkdir(self.clients_dir_path)
        test_clients_configs = ['test_client_1.conf', 'test_client_2.conf']
        for client_name in test_clients_configs:
            with open(os.path.join(self.clients_dir_path, client_name),
                      'wt', encoding=self.encoding) as fd:
                fd.write(f"{client_name} test data")

        common.clean_configuration(self.config_path, self.clients_dir_path)

        self.assertFalse(os.path.exists(self.config_path))
        self.assertFalse(os.path.exists(self.clients_dir_path))
