import unittest

import mockito

import common
import wireguard


class ServerVersionTest(unittest.TestCase):

    def tearDown(self) -> None:
        mockito.unstub()

    def test_server_version__version_found(self):
        wg_version_string = 'wireguard-tools v1.0.20210914 - https://git.zx2c4.com/wireguard-tools/\n'

        mockito.when(common).run_command('wg --version').thenReturn((0, wg_version_string, None))

        actual_server_version = wireguard.get_server_version()

        expected_server_version = 'v1.0.20210914'
        self.assertEqual(expected_server_version, actual_server_version)

    def test_server_version__version_not_found(self):
        wg_version_string = 'wireguard-tools wrong version'
        mockito.when(common).run_command('wg --version').thenReturn((0, wg_version_string, None))

        actual_server_version = wireguard.get_server_version()

        expected_server_version = 'unknown'
        self.assertEqual(expected_server_version, actual_server_version)
