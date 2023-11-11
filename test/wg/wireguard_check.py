import sys

import wireguard

wireguard.WIREGUARD_CONF_DIR = 'res/etc/wireguard'
wireguard.ROUTE_FILE_PATH = 'res/proc/net/route'
wireguard.UFW_BEFORE_RULES_PATH = 'res/etc/ufw/before.rules.modified'
wireguard.SYSCTL_FILE_PATH = 'res/etc/sysctl.conf'
wireguard.FORWARD_POLICY_FILE = 'res/etc/default/ufw'

wireguard.CONFIG_PATH = 'output/config.json'
wireguard.DEFAULT_CLIENTS_DIR = 'output/clients'
wireguard.RESULT_LOG_PATH = 'output/result.json'
sys.argv.append('--check')

wireguard.main()
