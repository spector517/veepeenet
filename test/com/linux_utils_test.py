import unittest

import common


class LinuxUtilsTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    sshd_config_path = 'com/res/etc/ssh/sshd_config'
    sshd_config_path_22_port = 'com/res/etc/ssh/sshd_config.22_port'
    sshd_config_custom_port = 'com/res/etc/ssh/sshd_config.custom_port'

    @classmethod
    def tearDownClass(cls):
        common.RESULT = cls.original_result

    def test_get_ssh_port_number_default_port(self) -> None:
        expected_port = 22
        actual_port = common.get_ssh_port_number(self.sshd_config_path)
        self.assertEqual(expected_port, actual_port)

    def test_get_ssh_port_number_22_port(self) -> None:
        expected_port = 22
        actual_port = common.get_ssh_port_number(self.sshd_config_path_22_port)
        self.assertEqual(expected_port, actual_port)

    def test_get_ssh_port_number_custom_port(self) -> None:
        expected_port = 2222
        actual_port = common.get_ssh_port_number(self.sshd_config_custom_port)
        self.assertEqual(expected_port, actual_port)
