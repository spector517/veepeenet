import os
import shutil
import unittest

import common
import wireguard


class LinuxUtilsTest(unittest.TestCase):
    temp_dir = 'tmp'
    encoding = 'UTF-8'
    network_interface = 'eth0'
    subnet = '10.9.0.0/8'
    ufw_rules_before_non_modified_path = 'wg/res/etc/ufw/before.rules'
    ufw_rules_before_path_modified_path = 'wg/res/etc/ufw/before.rules.modified'
    ip_version = 4
    sysctl_non_modified_path = 'wg/res/etc/sysctl.conf'
    sysctl_modified_path = 'wg/res/etc/sysctl.conf.modified'
    ufw_forward_policy_non_modified_path = 'wg/res/etc/default/ufw'
    ufw_forward_policy_modified_path = 'wg/res/etc/default/ufw.modified'
    sshd_config_path = 'wg/res/etc/ssh/sshd_config'
    sshd_config_path_22_port = 'wg/res/etc/ssh/sshd_config.22_port'
    sshd_config_custom_port = 'wg/res/etc/ssh/sshd_config.custom_port'
    original_result = common.RESULT.copy()

    @classmethod
    def tearDownClass(cls):
        common.RESULT = cls.original_result

    def setUp(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.mkdir(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_edit_ufw_rule_before__wg_rule_not_exists(self) -> None:
        self.__test_edit_system_file(
            wireguard.edit_ufw_rule_before,
            [self.network_interface, self.subnet],
            self.ufw_rules_before_non_modified_path,
            self.ufw_rules_before_path_modified_path
        )

    def test_edit_ufw_rule_before__wg_rule_exists(self) -> None:
        self.__test_edit_system_file(
            wireguard.edit_ufw_rule_before,
            [self.network_interface, self.subnet],
            self.ufw_rules_before_path_modified_path,
            self.ufw_rules_before_path_modified_path
        )

    def test_edit_sysctl__no_modified_config(self) -> None:
        self.__test_edit_system_file(
            wireguard.edit_sysctl,
            [self.ip_version],
            self.sysctl_non_modified_path,
            self.sysctl_modified_path
        )

    def test_edit_sysctl__modified_config(self) -> None:
        self.__test_edit_system_file(
            wireguard.edit_sysctl,
            [self.ip_version],
            self.sysctl_modified_path,
            self.sysctl_modified_path
        )

    def test_edit_ufw_forward_policy__non_modified_policy(self) -> None:
        self.__test_edit_system_file(
            wireguard.edit_ufw_forward_policy,
            [],
            self.ufw_forward_policy_non_modified_path,
            self.ufw_forward_policy_modified_path
        )

    def test_edit_ufw_forward_policy__modified_policy(self) -> None:
        self.__test_edit_system_file(
            wireguard.edit_ufw_forward_policy,
            [],
            self.ufw_forward_policy_modified_path,
            self.ufw_forward_policy_modified_path
        )

    def __test_edit_system_file(self,
                                func: callable,
                                args: list,
                                reference_file_path: str,
                                expected_file_path: str) -> None:
        actual_file_path = os.path.join(self.temp_dir, os.path.basename(reference_file_path))
        shutil.copy(reference_file_path, actual_file_path)

        func(actual_file_path, *args)

        with open(actual_file_path, 'rt', encoding=self.encoding) as fd:
            actual_content = fd.read()
        with open(expected_file_path, 'rt', encoding=self.encoding) as fd:
            expected_content = fd.read()
        self.assertEqual(expected_content, actual_content)

    def test_get_ssh_port_number_default_port(self) -> None:
        expected_port = 22
        actual_port = wireguard.get_ssh_port_number(self.sshd_config_path)
        self.assertEqual(expected_port, actual_port)

    def test_get_ssh_port_number_22_port(self) -> None:
        expected_port = 22
        actual_port = wireguard.get_ssh_port_number(self.sshd_config_path_22_port)
        self.assertEqual(expected_port, actual_port)

    def test_get_ssh_port_number_custom_port(self) -> None:
        expected_port = 2222
        actual_port = wireguard.get_ssh_port_number(self.sshd_config_custom_port)
        self.assertEqual(expected_port, actual_port)
