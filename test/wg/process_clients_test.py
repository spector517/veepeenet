import os
import shutil
import unittest

import common
import wireguard


class ProcessClientsTest(unittest.TestCase):
    temp_dir = 'tmp'
    clients_dir = os.path.join(temp_dir, 'clients')
    clients = [
        {'name': 'client1', 'ip': '10.9.0.2'},
        {'name': 'client2', 'ip': '10.9.0.3'},
        {'name': 'client3', 'ip': '10.9.0.4'}
    ]
    original_check_mode = common.CHECK_MODE
    original_result = common.RESULT.copy()

    @classmethod
    def setUpClass(cls) -> None:
        common.CHECK_MODE = True

    @classmethod
    def tearDownClass(cls) -> None:
        common.RESULT = cls.original_result
        common.CHECK_MODE = cls.original_check_mode

    def setUp(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.mkdir(self.temp_dir)
        shutil.copytree('wg/res/clients', self.clients_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_passed_client_names__clients_exists(self) -> None:
        client_name = 'new_client'
        existing_clients = self.clients
        expected_new_client_config = {
            'name': client_name,
            'ip': '10.9.0.5',
            'private_key': 'wg genkey',
            'public_key': 'wg pubkey'
        }
        self.assertEqual(expected_new_client_config,
                         wireguard.generate_new_client(client_name,
                                                       existing_clients,
                                                       '10.9.0.0/24'))

    def test_passed_client_names__no_clients_exists(self) -> None:
        client_name = 'new_client'
        existing_clients = []
        expected_new_client_config = {
            'name': client_name,
            'ip': '10.9.0.2',
            'private_key': 'wg genkey',
            'public_key': 'wg pubkey'
        }
        self.assertEqual(expected_new_client_config,
                         wireguard.generate_new_client(client_name,
                                                       existing_clients,
                                                       '10.9.0.0/24'))

    def test_remove_clients_configs__clients_dir_not_exists(self) -> None:
        shutil.rmtree(self.clients_dir)
        clients_names_to_remove = [self.clients[1]['name'], self.clients[0]['name']]
        wireguard.remove_clients_configs(clients_names_to_remove, self.clients_dir)
        for client_name in clients_names_to_remove:
            self.assertFalse(os.path.exists(os.path.join(self.clients_dir, f'{client_name}.conf')))

    def test_remove_clients_configs__clients_dir_exists(self) -> None:
        clients_names_to_remove = [self.clients[0]['name'], self.clients[2]['name']]
        wireguard.remove_clients_configs(clients_names_to_remove, self.clients_dir)
        for client in self.clients:
            client_name = client['name']
            client_conf_path = os.path.join(self.clients_dir, f'{client_name}.conf')
            if client_name in clients_names_to_remove:
                self.assertFalse(os.path.exists(client_conf_path))
            else:
                self.assertTrue(os.path.exists(client_conf_path))
