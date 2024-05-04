import unittest
import urllib.request
import subprocess

import mockito

import common
import xray


class InstallTest(unittest.TestCase):
    original_result = common.RESULT.copy()
    xray_version = '1.8.8'

    @classmethod
    def tearDownClass(cls) -> None:
        common.RESULT = cls.original_result

    def setUp(self) -> None:
        mockito.when(common).write_text_file(...).thenReturn(None)
        mockito.when(common).run_command(...).thenReturn((0, None, None))

    def tearDown(self) -> None:
        mockito.unstub()

    def test_is_xray_installed__installed(self) -> None:
        installed_stdout = (
            f'Xray {self.xray_version} (Xray, Penetrates Everything.) 1c83759 (go1.22.0 linux/amd64)'
            'A unified platform for anti-censorship.'
        )
        mockito.when(common).run_command('xray --version').thenReturn((0, installed_stdout, None))
        self.assertTrue(xray.is_xray_installed(self.xray_version))

    def test_is_xray_installed__not_installed(self) -> None:
        installed_stdout = 'xray: command not found'
        mockito.when(common).run_command('xray --version').thenReturn((0, installed_stdout, None))
        self.assertFalse(xray.is_xray_installed(self.xray_version))

    def test_is_xray_installed__different_versions(self) -> None:
        installed_stdout = (
            'Xray 1.8.7 (Xray, Penetrates Everything.) 1c83759 (go1.22.0 linux/amd64)'
            'A unified platform for anti-censorship.'
        )
        mockito.when(common).run_command('xray --version').thenReturn((0, installed_stdout, None))
        self.assertFalse(xray.is_xray_installed(self.xray_version))

    def test_install_xray__success(self) -> None:
        script_content = b'script_content'
        tmp_dir = '/tmp'
        script_path = f'{tmp_dir}/install-release.sh'
        response_mock = mockito.mock({'getcode': lambda: 200,
                                       'read': lambda: script_content})
        mockito.when(urllib.request).urlopen(xray.XRAY_INSTALLER_SCRIPT_URL,
                                             timeout=common.RUN_COMMAND_TIMEOUT).thenReturn(response_mock)
        xray.install_xray(self.xray_version, tmp_dir)
        mockito.verify(urllib.request, times=1).urlopen(xray.XRAY_INSTALLER_SCRIPT_URL,
                                                        timeout=common.RUN_COMMAND_TIMEOUT)
        mockito.verify(common).write_text_file(script_path, script_content.decode(common.ENCODING), 0o700)
        mockito.verify(common).run_command(f'{script_path} install --version {self.xray_version}')

    def test_install_xray__invalid_http_code(self) -> None:
        response_mock = mockito.mock({'getcode': lambda: 404,
                                      'read': lambda: ''})
        mockito.when(urllib.request).urlopen(xray.XRAY_INSTALLER_SCRIPT_URL,
                                             timeout=common.RUN_COMMAND_TIMEOUT).thenReturn(response_mock)
        with self.assertRaises(RuntimeError):
            xray.install_xray(self.xray_version, '')

    def test_install_xray__installation_error(self) -> None:
        script_content = b'script_content'
        tmp_dir = '/tmp'
        script_path = f'{tmp_dir}/install-release.sh'
        response_mock = mockito.mock({'getcode': lambda: 200,
                                      'read': lambda: script_content})
        mockito.when(urllib.request).urlopen(xray.XRAY_INSTALLER_SCRIPT_URL,
                                             timeout=common.RUN_COMMAND_TIMEOUT).thenReturn(response_mock)
        xray.install_xray(self.xray_version, tmp_dir)
        mockito.verify(urllib.request, times=1).urlopen(xray.XRAY_INSTALLER_SCRIPT_URL,
                                                        timeout=common.RUN_COMMAND_TIMEOUT)
        mockito.verify(common).write_text_file(script_path, script_content.decode(common.ENCODING), 0o700)
        mockito.when(common).run_command(
            f'{script_path} install --version {self.xray_version}').thenRaise(
            subprocess.CalledProcessError(127, ''))
        with self.assertRaises(RuntimeError):
            xray.install_xray(self.xray_version, tmp_dir)
