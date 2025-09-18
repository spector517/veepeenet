#!/bin/bash

set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: You must run this script as root" >&2
  exit 1
fi

QUIET=0
if [[ "$1" == "-q" ]]; then
  QUIET=1
fi

if [[ $QUIET -eq 0 ]]; then
  read -rp "This action delete ALL your Xray configurations and Xray distributive! Are you sure? (Y/N): " confirm
  if ! [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "WARN: Aborted."
    exit 0
  fi
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

echo "INFO: Removing Xray distrib..."
rm -rf /usr/local/bin/xray
echo "INFO: Xray distrib removed"
