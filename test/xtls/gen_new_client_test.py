import unittest
import uuid
import os.path
import json

import mockito

import common
import xray


class GenNewClientTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    test_uuid = '83822097-c943-44b6-8674-8e80104714de'
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
            'email': f'{client_name}@192.168.1.101',
            'import_url': (f'vless://{self.test_uuid}@192.168.1.101:443?flow=xtls-rprx-vision'
                           '&type=tcp&security=reality&fp=chrome&sni=yahoo.com'
                           '&pbk=nVvbwNvhA7iiS77f2UkFR5h4lZxAnkryO7ZkkqK1eyo&sid=0001&'
                           f'spx=%2F#{client_name}@192.168.1.101')
        }
        self.assertEqual(expected_client, xray.generate_new_client(client_name, self.config))

    def test_gen_new_client__clients_exists(self) -> None:
        client_name = 'new_client'
        expected_client = {
            'name': client_name,
            'uuid': self.test_uuid,
            'short_id': '0003',
            'email': f'{client_name}@192.168.1.101',
            'import_url': (f'vless://{self.test_uuid}@192.168.1.101:443'
                           f'?flow=xtls-rprx-vision'
                           '&type=tcp'
                           '&security=reality'
                           '&fp=chrome&sni=yahoo.com'
                           '&pbk=nVvbwNvhA7iiS77f2UkFR5h4lZxAnkryO7ZkkqK1eyo&sid=0003'
                           f'&spx=%2F#{client_name}@192.168.1.101')
        }
        self.assertEqual(expected_client, xray.generate_new_client(client_name, self.config))
