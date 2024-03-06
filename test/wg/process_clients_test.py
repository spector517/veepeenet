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

    def test_get_existing_clients__clients_exists(self) -> None:
        config = {'clients': self.clients}
        expected_existing_clients = self.clients
        self.assertEqual(expected_existing_clients,
                         common.get_existing_clients(config))

    def test_get_existing_clients__no_clients_exists(self) -> None:
        config = {}
        self.assertEqual([], common.get_existing_clients(config))

    def test_get_new_clients_names__clients_exists(self) -> None:
        existing_clients = self.clients
        passed_client_names = ['client1', 'client4']
        self.assertEqual(['client4'],
                         common.get_new_clients_names(passed_client_names, existing_clients))

    def test_get_new_clients_names__no_clients_exists(self) -> None:
        existing_clients = []
        passed_client_names = ['client1', 'client2']
        self.assertEqual(passed_client_names.sort(),
                         common.get_new_clients_names(passed_client_names,
                                                      existing_clients).sort())

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

    def test_get_clients_after_removing__no_clients_to_remove(self) -> None:
        existing_clients = self.clients
        clients_names_to_remove = []
        actulal_clients = common.get_clients_after_removing(existing_clients,
                                                            clients_names_to_remove)
        self.assertEqual(existing_clients, actulal_clients)

    def test_get_clients_after_removing__clients_to_remove_exists(self) -> None:
        existing_clients = self.clients
        clients_names_to_remove = [self.clients[1]['name'], self.clients[0]['name']]
        expected_clients_list = [self.clients[2]]
        actual_clients_list = common.get_clients_after_removing(existing_clients,
                                                                clients_names_to_remove)
        self.assertEqual(expected_clients_list, actual_clients_list)

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
