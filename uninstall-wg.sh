#!/bin/bash

read -rp "This action delete ALL your WireGuard configurations! Are you sure? (Y/N): " confirm
if ! [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
  echo "WARN: Aborted."
  exit 0
fi

echo 'INFO: Removing VeePeeNET for WireGuard service configuration...'
rm -rf /usr/local/etc/veepeenet/wg
rm -rf /var/log/veepeenet/wg
rm -f /usr/local/lib/veepeenet/wireguard.py
rm -f /usr/local/bin/wg-config
rm -f /usr/local/lib/veepeenet/wg-config.sh
echo 'INFO: VeePeeNET for WireGuard service configuration is removed.'

if apt list --installed | grep wireguard | grep -q installed; then
  echo 'INFO: Removing WireGuard service...'
  if ! systemctl stop wg-quick@*; then
    echo 'ERROR: Stop WireGuard service failed.' >&2
    exit 1
  fi
  apt remove -y wireguard wireguard-tools
  echo 'INFO: WireGuard service removed.'
fi
