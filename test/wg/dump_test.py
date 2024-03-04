import json
import os
import unittest

import common
import wireguard


class DumpTest(unittest.TestCase):
    encoding = 'UTF-8'
    config_path = 'wg/res/config.json'
    clients_dir_path = 'wg/res/clients'
    clients_names = ['client1', 'client2', 'client3']
    server_conf_path = 'wg/res/etc/wireguard/wg0.conf'
    original_result = common.RESULT.copy()

    @classmethod
    def tearDownClass(cls):
        wireguard.RESULT = cls.original_result

    def setUp(self) -> None:
        with open(self.config_path, 'rt', encoding=self.encoding) as fd:
            self.config_str = fd.read()
        self.config = json.loads(self.config_str)

    def test_dump_config(self) -> None:
        self.assertEqual(self.config_str.strip(), wireguard.dump_config(self.config).strip())

    def test_dump_server(self) -> None:
        with open(self.server_conf_path, 'rt', encoding=self.encoding) as fd:
            server_config_str = fd.read()
        self.assertEqual(server_config_str.strip(), wireguard.dump_server(self.config).strip())

    def test_dump_clients(self) -> None:
        clients_configs = {}
        for client_name in self.clients_names:
            with open(os.path.join(self.clients_dir_path, f'{client_name}.conf'),
                      'rt', encoding=self.encoding) as fd:
                clients_configs.update({client_name: fd.read()})
        self.assertEqual(clients_configs, wireguard.dump_clients(self.config))
