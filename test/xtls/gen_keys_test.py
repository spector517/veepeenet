import unittest

import mockito

import common
import xray


class GenKeysTest(unittest.TestCase):
    original_result = common.RESULT.copy()

    @classmethod
    def tearDownClass(cls) -> None:
        common.RESULT = cls.original_result

    def tearDown(self) -> None:
        mockito.unstub()

    def test_generate_server_keys_success(self) -> None:
        private_key = 'iL90SiQVSG4TzYyvLsOKP9unFSalPlagjE7_-tmX5XE'
        public_key = 'nVvbwNvhA7iiS77f2UkFR5h4lZxAnkryO7ZkkqK1eyo'
        gen_keys_stdout = (
            f'Private key: {private_key}\n'
            f'Public key: {public_key}\n'
        )
        mockito.when(common).run_command('xray x25519').thenReturn((0, gen_keys_stdout, None))
        self.assertEqual((private_key, public_key), xray.generate_server_keys())

    def test_generate_server_keys__error_code(self) -> None:
        mockito.when(common).run_command('xray x25519').thenReturn((127, None, None))
        with self.assertRaises(RuntimeError):
            xray.generate_server_keys()

    def test_generate_server_keys__invalid_stdout(self) -> None:
        gen_keys_stdout = 'some unexpected out'
        mockito.when(common).run_command('xray x25519').thenReturn((127, gen_keys_stdout, None))
        with self.assertRaises(RuntimeError):
            xray.generate_server_keys()
