import sys

import common
import xray

xray.XRAY_CONF_PATH = 'res/etc/xray'

common.CONFIG_PATH = 'output/config.json'
common.RESULT_LOG_PATH = 'output/result.json'
sys.argv.append('--check')

xray.main()
