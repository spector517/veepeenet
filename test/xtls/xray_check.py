import sys

import common
import xray

xray.XRAY_CONF_PATH = 'res/etc/xray'

common.CONFIG_PATH = 'output/config.json'
common.RESULT_LOG_PATH = 'output/result.json'
common.META_FILE_PATH = 'res/meta.json'
sys.argv.append('--check')

xray.main()
