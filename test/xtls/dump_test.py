import json
import unittest
import os.path

import common
import xray


class DumpTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    config_path = os.path.join('xtls', 'res', 'config.json')
    xray_conf_path = os.path.join('xtls', 'res', 'etc', 'xray', 'config.json')
    test_config = {}
    test_xray_config = {}

    def setUp(self):
        with open(self.xray_conf_path, 'rt', encoding=common.ENCODING) as fd:
            self.test_xray_config = json.loads(fd.read())
        with open(self.config_path, 'rt', encoding=common.ENCODING) as fd:
            self.test_config = json.loads(fd.read())

    @classmethod
    def tearDownClass(cls):
        common.RESULT = cls.original_result

    def test_dump_xray(self):
        expected_xray_config_str = json.dumps(self.test_xray_config, indent=2)
        actual_xray_config_str = xray.dump_xray(self.test_config)
        self.assertEqual(expected_xray_config_str, actual_xray_config_str)

    def test_dump_client(self):
        client = self.test_config['clients'][0]
        expected_client_dump = ('client1: '
                                'vless://c1_uuid@my.server.local:443'
                                '?flow=xtls-rprx-vision'
                                '&type=tcp'
                                '&security=reality'
                                '&fp=chrome'
                                '&sni=microsoft.com'
                                '&pbk=server_public_key&sid=0001'
                                '&spx=%2F#client1@my.server.local')
        actual_client_dump = xray.dump_client(client)
        self.assertEqual(expected_client_dump, actual_client_dump)
