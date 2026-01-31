#!/bin/bash

set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: You must run this script as root" >&2
  exit 1
fi

rm -rf /usr/local/lib/veepeenet
rm -f /usr/local/bin/xrayctl
rm -f /usr/local/bin/xray-migrate-1-to-2
mkdir -p /usr/local/lib/veepeenet

apt update
apt install -y python3.12-venv

python3 -m venv /usr/local/lib/veepeenet/venv
/usr/local/lib/veepeenet/venv/bin/pip3 install --upgrade pip
/usr/local/lib/veepeenet/venv/bin/pip3 install ./veepeenet*

ln -s /usr/local/lib/veepeenet/venv/bin/xrayctl /usr/local/bin/xrayctl
ln -s /usr/local/lib/veepeenet/venv/bin/xray-migrate-1-to-2 /usr/local/bin/xray-migrate-1-to-2

echo 'VeePeeNET successfully installed'
