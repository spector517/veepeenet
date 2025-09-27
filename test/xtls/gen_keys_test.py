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
        private_key = 'iCnxOZ80KI28or1VFYoVy81yATZxIMLqkdEyqeuNSHc'
        password = 'vVGaBN8TgepTPbRE62e9Kz5U8gNvtgeY2Y03lgTfsX0'
        hash32 = 'Ty4Q5ryEH6JAlr-sPZnsQzmf0g0EXQbW8luyhUsi7gQ'
        gen_keys_stdout = (
            f'PrivateKey: {private_key}\n'
            f'Password: {password}\n'
            f'Hash32: {hash32}\n'
        )
        mockito.when(common).run_command('xray x25519').thenReturn((0, gen_keys_stdout, None))
        self.assertEqual((private_key, password), xray.generate_server_keys())

    def test_generate_server_keys__error_code(self) -> None:
        mockito.when(common).run_command('xray x25519').thenReturn((127, None, None))
        with self.assertRaises(RuntimeError):
            xray.generate_server_keys()

    def test_generate_server_keys__invalid_stdout(self) -> None:
        gen_keys_stdout = 'some unexpected out'
        mockito.when(common).run_command('xray x25519').thenReturn((127, gen_keys_stdout, None))
        with self.assertRaises(RuntimeError):
            xray.generate_server_keys()
