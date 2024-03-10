import os
import shutil
import unittest

import common


class WriteTextFileTest(unittest.TestCase):
    temp_dir = 'tmp'
    encoding = 'UTF-8'
    content = 'test test test'
    file_path = os.path.join(temp_dir, 'test.txt')

    def setUp(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.mkdir(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_write_file_no_exists(self):
        common.write_text_file(self.file_path, self.content)
        with open(self.file_path, 'rt', encoding=self.encoding) as fd:
            actual_content = fd.read()
        self.assertEqual(self.content, actual_content)

    def test_write__file_exists_content_equals(self):
        self.__create_test_file()
        modify_time = os.path.getmtime(self.file_path)

        common.write_text_file(self.file_path, self.content)

        self.assertEqual(modify_time, os.path.getmtime(self.file_path))

    def test_write__file_exists_content_non_equals(self):
        other_content = f'{self.content} changed'
        self.__create_test_file()
        modify_time = os.path.getmtime(self.file_path)

        common.write_text_file(self.file_path, other_content)

        self.assertNotEqual(modify_time, os.path.getmtime(self.file_path))

    def test_write__file_exists_content_non_equals_mode_not_provided(self):
        other_content = f'{self.content} changed'
        self.__create_test_file()
        os.chmod(self.file_path, 0o700)

        common.write_text_file(self.file_path, other_content)

        self.assertTrue(os.access(self.file_path, os.R_OK))
        self.assertTrue(os.access(self.file_path, os.W_OK))
        self.assertTrue(os.access(self.file_path, os.X_OK))

    def test_write__file_exists_content_non_equals_mode_provided(self):
        other_content = f'{self.content} changed'
        self.__create_test_file()
        os.chmod(self.file_path, 0o700)

        common.write_text_file(self.file_path, other_content, 0o600)

        self.assertTrue(os.access(self.file_path, os.R_OK))
        self.assertTrue(os.access(self.file_path, os.W_OK))
        self.assertFalse(os.access(self.file_path, os.X_OK))

    def test_write__file_exists_content_equals_mode_provided(self):
        self.__create_test_file()
        os.chmod(self.file_path, 0o700)

        common.write_text_file(self.file_path, self.content, 0o600)

        self.assertTrue(os.access(self.file_path, os.R_OK))
        self.assertTrue(os.access(self.file_path, os.W_OK))
        self.assertFalse(os.access(self.file_path, os.X_OK))

    def __create_test_file(self) -> None:
        with open(self.file_path, 'wt', encoding=self.encoding) as fd:
            fd.write(self.content)
