#!/bin/bash

### Install Wireguard part
if ! apt list --installed | grep wireguard | grep -q installed; then
  echo 'INFO: Wireguard service is not installed, installing...'
  apt update && apt install -y wireguard
  echo 'INFO: Wireguard service installed.'
else
  echo 'INFO: Wireguard service is already installed'
fi

### Install VeePeeNET part
if [[ -d '/etc/veepeenet/wg' ]] || [[ -d '/etc/veepeenet/wg' ]] || [[ -d '/var/log/veepeenet/wg' ]]; then
  echo 'INFO: Updating VeePeeNET for Wireguard service configuration...'
else
  echo 'INFO: Installing VeePeeNET for Wireguard service configuration...'
fi

mkdir -p \
  /usr/local/lib/veepeenet \
  /usr/local/etc/veepeenet/wg \
  /var/log/veepeenet/wg \

cp ./common.py /usr/local/lib/veepeenet
cp ./wireguard.py /usr/local/lib/veepeenet

cat > /usr/local/lib/veepeenet/wg-config.sh << EOF
#!/bin/bash
/usr/bin/python3 /usr/local/lib/veepeenet/wireguard.py "\$@"
EOF
chmod u+x /usr/local/lib/veepeenet/wg-config.sh

rm -f /usr/local/bin/wg-config
ln -s /usr/local/lib/veepeenet/wg-config.sh /usr/local/bin/wg-config

echo 'INFO: VeePeeNet for Wireguard service configuration is ready.'
