import unittest

import mockito

import common

COMMAND = 'hostname -i'

class DetectIPTest(unittest.TestCase):

    expected_ip = '206.126.0.29'
    stdout_lines_with_ip = [
        '206.126.0.29',
        'Some206.126.0.29some',
        'Some206.126.0.29',
        '206.126.0.29some',
        '206.126.0.29 e4c7:620c:cdab:82cc:1b8e:d74f:09e1:8720',
        'e4c7:620c:cdab:82cc:1b8e:d74f:09e1:8720\n206.126.0.29',
        'Some\n206.126.0.29some\n',
    ]
    stdout_lines_without_ip = [
        None,
        '',
        'qwe',
        'e4c7:620c:cdab:82cc:1b8e:d74f:09e1:8720',
        '127.0.0.1 fd1b:a5cf:9e74:1fa2:0000:0000:0000:0000'
    ]

    def tearDown(self) -> None:
        mockito.unstub()

    def test_ipv4_detection_success(self):
        for line in self.stdout_lines_with_ip:
            mockito.when(common).run_command(COMMAND, check=False).thenReturn((0, line, ''))
            self.assertEqual(self.expected_ip, common.detect_ipv4())

    def test_ipv4_detection_unsuccess(self):
        for line in self.stdout_lines_without_ip:
            mockito.when(common).run_command(COMMAND, check=False).thenReturn((0, line, ''))
            self.assertEqual(common.DEFAULT_SERVER_IP, common.detect_ipv4())

    def test_ipv4_detection_run_command_error(self):
        mockito.when(common).run_command(COMMAND, check=False).thenReturn((127, '', ''))
        self.assertEqual(common.DEFAULT_SERVER_IP, common.detect_ipv4())
