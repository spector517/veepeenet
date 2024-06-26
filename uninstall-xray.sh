#!/bin/bash

read -rp "This action delete ALL your Xray configurations! Are you sure? (Y/N): " confirm
if ! [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
  echo "WARN: Aborted."
  exit 0
fi

echo 'INFO: Removing VeePeeNET for Xray service configuration...'
rm -rf /usr/local/etc/veepeenet/xray
rm -rf /var/log/veepeenet/xray
rm -f /usr/local/lib/veepeenet/xray.py
rm -f /usr/local/bin/xray-config
rm -f /usr/local/lib/veepeenet/xray-config.sh
echo 'INFO: VeePeeNET for Xray service configuration is removed.'

if [[ -f '/etc/systemd/system/xray.service' ]]; then
  echo 'INFO: Removing Xray service...'
  if ! systemctl stop xray.service; then
    echo 'ERROR: Stop Xray service failed.' >&2
    exit 1
  fi
  rm '/etc/systemd/system/xray.service'
  systemctl daemon-reload
fi
rm -rf /usr/local/etc/xray
echo 'INFO: Xray service removed.'

echo "Removing Xray distrib..."
rm -rf /usr/local/share/xray
rm -rf /usr/local/bin/xray
echo "Xray distrib removed"
