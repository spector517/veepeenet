import unittest

import mockito

import common
import xray


class ServerVersionTest(unittest.TestCase):

    def test_server_version__version_found(self):
        xray_version_string = (
            'Xray 1.8.24 (Xray, Penetrates Everything.) 6baad79 (go1.23.0 linux/amd64)\n'
            'A unified platform for anti-censorship.\n'
        )
        mockito.when(common).run_command('xray --version').thenReturn((0, xray_version_string, None))

        actual_server_version = xray.get_server_version()

        expected_server_version = '1.8.24'
        self.assertEqual(expected_server_version, actual_server_version)

    def test_server_version__version_not_found(self):
        xray_version_string = 'Xray wrong version'
        mockito.when(common).run_command('xray --version').thenReturn((0, xray_version_string, None))

        actual_server_version = xray.get_server_version()

        expected_server_version = 'unknown'
        self.assertEqual(expected_server_version, actual_server_version)
