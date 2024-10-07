import sys

import common
import wireguard

wireguard.WIREGUARD_CONF_DIR = 'res/etc/wireguard'
common.ROUTE_FILE_PATH = 'res/proc/net/route'
common.UFW_BEFORE_RULES_PATH = 'res/etc/ufw/before.rules.modified'
common.SYSCTL_FILE_PATH = 'res/etc/sysctl.conf'
common.FORWARD_POLICY_FILE = 'res/etc/default/ufw'
common.META_FILE_PATH = 'res/meta.json'

common.CONFIG_PATH = 'output/config.json'
common.DEFAULT_CLIENTS_DIR = 'output/clients'
common.RESULT_LOG_PATH = 'output/result.json'
sys.argv.append('--check')

wireguard.main()
