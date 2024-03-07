import json
import unittest

import common


class DumpTest(unittest.TestCase):
    config_path = 'com/res/config.json'
    original_result = common.RESULT.copy()

    @classmethod
    def tearDownClass(cls):
        common.RESULT = cls.original_result

    def setUp(self) -> None:
        with open(self.config_path, 'rt', encoding=common.ENCODING) as fd:
            self.config_str = fd.read()
        self.config = json.loads(self.config_str)

    def test_dump_config(self) -> None:
        self.assertEqual(self.config_str.strip(), common.dump_config(self.config).strip())
