import unittest
import mockito

import common


class TestCenterString(unittest.TestCase):

    def test_center_string_exact_length(self):
        self.assertEqual("Example", common.center_string("Example", 7), )

    def test_center_string_longer(self):
        self.assertEqual("Exam", common.center_string("Example", 4))

    def test_center_string_shorter(self):
        self.assertEqual("-Example--", common.center_string("Example", 10), )

    def test_center_string_custom_fill(self):
        self.assertEqual("*Example**", common.center_string("Example", 10, '*'))

    def test_center_string_odd_length(self):
        self.assertEqual("-Example-", common.center_string("Example", 9))

    def test_center_string_empty(self):
        self.assertEqual("-----", common.center_string("", 5))


class TestGetStatus(unittest.TestCase):

    def setUp(self):
        self.version_info = '1.0 build 23'
        self.service_name = 'xray'
        self.server_name = 'Xray'

    def test_get_status_with_clients(self):
        clients_strings = ['client1', 'client2']
        mockito.when(common).is_service_running(self.service_name).thenReturn(True)
        config = {
            'server': {
                'host': '127.0.0.1',
                'port': 8080
            }
        }
        expected_output = (
            '------------ VeePeeNET (1.0 build 23) -------------\n'
            'Xray server info:\n'
            '\tstatus: Running\n'
            '\taddress: 127.0.0.1:8080\n'
            '\tclients:\n'
            '\t\tclient1\n'
            '\t\tclient2\n'
            '---------------------------------------------------'
        )

        result = common.get_status(config, self.version_info, self.service_name,
                                   self.server_name, clients_strings)
        self.assertEqual(result, expected_output)

    def test_get_status_no_clients(self):
        mockito.when(common).is_service_running(self.service_name).thenReturn(False)
        config = {
            'server': {
                'host': '127.0.0.1',
                'port': 8080
            }
        }
        expected_output = (
            '------------ VeePeeNET (1.0 build 23) -------------\n'
            'Xray server info:\n'
            '\tstatus: Stopped\n'
            '\taddress: 127.0.0.1:8080\n'
            '\tclients:\n'
            '\t\tServer has no clients\n'
            '---------------------------------------------------'
        )

        result = common.get_status(config, self.version_info, self.service_name,
                                   self.server_name, [])
        self.assertEqual(result, expected_output)
