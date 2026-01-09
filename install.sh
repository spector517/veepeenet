#!/bin/bash

set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: You must run this script as root" >&2
  exit 1
fi

rm -rf /usr/local/lib/veepeenet
rm -rf /usr/local/bin/xrayctl
mkdir -p /usr/local/lib/veepeenet

python3 -m venv /usr/local/lib/veepeenet/venv
/usr/local/lib/veepeenet/venv/bin/pip3 install ./veepeenet*

ln -s /usr/local/lib/veepeenet/venv/bin/xrayctl /usr/local/bin/xrayctl

echo 'VeePeeNET successfully installed'
