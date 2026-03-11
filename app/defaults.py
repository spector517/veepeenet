# pylint: disable=line-too-long
from pathlib import Path

STATE_PENDING_TIMEOUT = 2

REALITY_HOST = 'microsoft.com'
REALITY_PORT = 443
VLESS_LISTEN_INTERFACE = '0.0.0.0'
VLESS_LISTEN_PORT = 443
VLESS_OUTBOUND_PORT = 443
VLESS_OUTBOUND_SPIDER_X = '/'
VLESS_OUTBOUND_FINGERPRINT = 'chrome'

XRAY_CONFIG_PATH = Path('/usr/local/etc/xray/config.json')
XRAY_BINARY_PATH = Path('/usr/local/bin/xray')
XRAY_SERVICE_UNIT_PATH = Path('/etc/systemd/system/xray.service')
XRAY_ERROR_LOG_PATH = Path('/var/log/xray/error.log')
XRAY_ACCESS_LOG_PATH = Path('/var/log/xray/access.log')

XRAY_DOWNLOAD_URL = 'https://github.com/XTLS/Xray-core/releases/download/'
XRAY_ARCHIVE_NAME = 'Xray-linux-64.zip'

XRAY_GEO_IP_DATA_PATH = Path('/usr/local/share/xray/geoip.dat')
XRAY_GEO_SITE_DATA_PATH = Path('/usr/local/share/xray/geosite.dat')
GEO_IP_URL = 'https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat'
GEO_SITE_URL = 'https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat'
