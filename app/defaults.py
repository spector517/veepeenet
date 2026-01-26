from pathlib import Path

REALITY_HOST = 'microsoft.com'
REALITY_PORT = 443
VLESS_LISTEN_PORT = 443
NO_UFW = False

XRAY_CONFIG_PATH = Path('/usr/local/etc/xray/config.json')
XRAY_BINARY_PATH = Path('/usr/local/bin/xray')
XRAY_SERVICE_UNIT_PATH = Path('/etc/systemd/system/xray.service')
XRAY_ERROR_LOG_PATH = Path('/var/log/xray/error.log')
XRAY_ACCESS_LOG_PATH = Path('/var/log/xray/access.log')

XRAY_DOWNLOAD_URL = 'https://github.com/XTLS/Xray-core/releases/download/'
XRAY_ARCHIVE_NAME = 'Xray-linux-64.zip'
