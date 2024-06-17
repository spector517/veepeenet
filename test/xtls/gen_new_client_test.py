import unittest
import uuid
import os.path
import json

import mockito

import common
import xray


class GenNewClientTest(unittest.TestCase):
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
                           '&type=tcp&security=reality&fp=chrome&sni=microsoft.com'
                           '&pbk=server_public_key&sid=0001&'
                           f'spx=%2F#{client_name}@my.server.local')
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
                           '&type=tcp'
                           '&security=reality'
                           '&fp=chrome&sni=microsoft.com'
                           '&pbk=server_public_key&sid=0002'
                           f'&spx=%2F#{client_name}@my.server.local')
        }
        self.assertEqual(expected_client, xray.generate_new_client(client_name, self.config))
