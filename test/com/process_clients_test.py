import os
import unittest

import common


class ProcessClientsTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    temp_dir = 'tmp'
    clients_dir = os.path.join(temp_dir, 'clients')
    clients = [
        {'name': 'client1'},
        {'name': 'client2'},
        {'name': 'client3'}
    ]

    @classmethod
    def tearDownClass(cls) -> None:
        common.RESULT = cls.original_result

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
