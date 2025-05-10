import unittest
import uuid
import os.path
import json

import mockito

import common
import xray


class ProcessClientsTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    test_uuid = 'c1_uuid'
    config_path = os.path.join('xtls', 'res', 'config.json')
    config = {}

    def setUp(self) -> None:
        mockito.when(uuid).uuid4().thenReturn(self.test_uuid)
        with open(self.config_path, 'rt', encoding=common.ENCODING) as fd:
            self.config = json.loads(fd.read())

    def tearDown(self) -> None:
        mockito.unstub()

    @classmethod
    def tearDownClass(cls) -> None:
        common.RESULT = cls.original_result

    def test_gen_new_client__no_clients(self) -> None:
        self.config['clients'].clear()
        client_name = 'new_client'
        expected_client = {
            'name': client_name,
            'uuid': self.test_uuid,
            'short_id': '0001',
            'email': f'{client_name}@my.server.local',
            'import_url': (f'vless://{self.test_uuid}@my.server.local:443?flow=xtls-rprx-vision'
                           '&type=raw&security=reality&fp=chrome&sni=microsoft.com'
                           '&pbk=server_public_key&sid=0001&'
                           f'spx=%2F{client_name}#{client_name}@my.server.local')
        }
        self.assertEqual(expected_client, xray.generate_new_client(client_name, self.config))

    def test_gen_new_client__clients_exists(self) -> None:
        client_name = 'new_client'
        expected_client = {
            'name': client_name,
            'uuid': self.test_uuid,
            'short_id': '0002',
            'email': f'{client_name}@my.server.local',
            'import_url': (f'vless://{self.test_uuid}@my.server.local:443'
                           f'?flow=xtls-rprx-vision'
                           '&type=raw'
                           '&security=reality'
                           '&fp=chrome&sni=microsoft.com'
                           '&pbk=server_public_key&sid=0002'
                           f'&spx=%2F{client_name}#{client_name}@my.server.local')
        }
        self.assertEqual(expected_client, xray.generate_new_client(client_name, self.config))

    def test_actualize_clients(self) -> None:
        client_name = 'client1'
        host = 'new.server.local'
        port = '445'
        reality_host = 'yahoo.com'
        expected_clients = [{
            'name': client_name,
            'uuid': self.test_uuid,
            'short_id': '0001',
            'email': f'{client_name}@{host}',
            'import_url': (f'vless://c1_uuid@{host}:{port}?flow=xtls-rprx-vision'
                           f'&type=raw&security=reality&fp=chrome&sni={reality_host}'
                           '&pbk=server_public_key&sid=0001&'
                           f'spx=%2F{client_name}#{client_name}@{host}')
        }]
        server_config = self.config['server']
        server_config['host'] = host
        server_config['port'] = port
        server_config['reality_host'] = reality_host
        xray.actualize_existing_clients(self.config)
        self.assertEqual(expected_clients, self.config['clients'])

    def test_actualize_clients__no_clients(self) -> None:
        self.config['clients'].clear()
        xray.actualize_existing_clients(self.config)
        self.assertEqual([], self.config['clients'])
