import os.path
import shutil
import unittest

import common

TEST_RETURN_VALUE = 'test_value'
TEST_ARGS = (1, '1', True)
TEST_KWARGS = {
    'arg1': 2,
    'arg2': False,
    'arg3': 'qwe'
}
EXCEPTION = Exception('Test exception')


class HandleResultTest(unittest.TestCase):
    tmp_dir = 'tmp'
    original_result = common.RESULT.copy()
    original_result_log_path = common.RESULT_LOG_PATH
    result_log_path = os.path.join(tmp_dir, 'result.json')

    @classmethod
    def setUpClass(cls):
        common.RESULT_LOG_PATH = cls.result_log_path
        # FIXME Why actions is not empty?
        common.RESULT['actions'].clear()
        del common.RESULT['meta']

    @classmethod
    def tearDownClass(cls):
        common.RESULT = cls.original_result
        common.RESULT_LOG_PATH = cls.original_result_log_path

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        common.RESULT['actions'].clear()
        common.RESULT['has_error'] = False

    def test_no_args_no_return_value_func(self):

        @common.handle_result
        def no_args_no_return_value_func() -> None:
            pass

        expected_result = {
            'has_error': False,
            'actions': [
                {
                    'name': 'no_args_no_return_value_func',
                    'args': '()',
                    'kwargs': '{}',
                    'result': 'None'
                }
            ]
        }
        no_args_no_return_value_func()
        self.assertDictEqual(expected_result, common.RESULT)

    def test_no_args_return_value_func(self):

        @common.handle_result
        def no_args_return_value_func() -> any:
            return TEST_RETURN_VALUE

        expected_result = {
            'has_error': False,
            'actions': [
                {
                    'name': 'no_args_return_value_func',
                    'args': '()',
                    'kwargs': '{}',
                    'result': f'{TEST_RETURN_VALUE}'
                }
            ]
        }
        no_args_return_value_func()
        self.assertDictEqual(expected_result, common.RESULT)

    def test_args_no_return_value_func(self):

        @common.handle_result
        def args_no_return_value_func(*args, **kwargs) -> None:
            pass

        expected_result = {
            'has_error': False,
            'actions': [
                {
                    'name': 'args_no_return_value_func',
                    'args': str(TEST_ARGS),
                    'kwargs': str(TEST_KWARGS),
                    'result': 'None'
                }
            ]
        }
        args_no_return_value_func(*TEST_ARGS, **TEST_KWARGS)
        self.assertDictEqual(expected_result, common.RESULT)

    def test_args_return_value_func(self):

        @common.handle_result
        def args_return_value_func(*args, **kwargs) -> any:
            return TEST_RETURN_VALUE

        expected_result = {
            'has_error': False,
            'actions': [
                {
                    'name': 'args_return_value_func',
                    'args': str(TEST_ARGS),
                    'kwargs': str(TEST_KWARGS),
                    'result': f'{TEST_RETURN_VALUE}'
                }
            ]
        }
        args_return_value_func(*TEST_ARGS, **TEST_KWARGS)
        self.assertDictEqual(expected_result, common.RESULT)

    def test_exception_func(self):

        @common.handle_result
        def exception_func(*args, **kwargs) -> any:
            raise EXCEPTION

        expected_result = {
            'has_error': True,
            'actions': [
                {
                    'name': 'exception_func',
                    'args': str(TEST_ARGS),
                    'kwargs': str(TEST_KWARGS),
                    'error': str(EXCEPTION)
                }
            ]
        }
        self.assertRaises(type(EXCEPTION), exception_func, *TEST_ARGS, **TEST_KWARGS)
        self.assertDictEqual(expected_result, common.RESULT)
