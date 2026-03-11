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
  read -rp "This action delete ALL your Xray configurations and Xray distributive! Are you sure? (y/N): " confirm
  if ! [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "WARN: Aborted."
    exit 0
  fi
fi

rm -rf /usr/local/lib/veepeenet
rm -rf /usr/local/bin/xrayctl

if [[ -f '/etc/systemd/system/xray.service' ]]; then
  if ! systemctl stop xray.service; then
    echo 'ERROR: Stop Xray service failed.' >&2
    exit 1
  fi
  rm '/etc/systemd/system/xray.service'
  systemctl daemon-reload
fi
rm -rf /usr/local/etc/xray
rm -rf /usr/local/bin/xray
rm -rf /usr/local/share/xray

rm -f "$HOME/.bash_completions/xrayctl.sh"

if [[ -f "$HOME/.bashrc" ]]; then
  sed -i.bak "/source.*xrayctl\.sh/d" "$HOME/.bashrc"
  rm -f "$HOME/.bashrc.bak"
fi

echo 'VeePeeNET successfully uninstalled'
