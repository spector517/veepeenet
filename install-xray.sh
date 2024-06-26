#!/bin/bash

### Install Xray Project part
mkdir -p \
  /usr/local/etc/xray \
  /usr/local/share/xray \
  /var/log/xray \

if [[ -f '/etc/systemd/system/xray.service' ]]; then
  Xray_SERVICE_ALREADY_INSTALLED=1
  echo 'INFO: Xray service already installed'
else
  Xray_SERVICE_ALREADY_INSTALLED=0
  echo 'INFO: Xray is not installed'
fi

if [[ $Xray_SERVICE_ALREADY_INSTALLED -eq 1 ]]; then
  if ! systemctl -q is-active xray.service; then
    echo 'WARN: Xray service is not running'
  else
    echo 'INFO: Stopping Xray service...'
    if ! systemctl stop xray.service; then
      echo 'ERROR: Stop Xray service failed.' >&2
      exit 1
    fi
    echo 'INFO: Xray service stopped.'
  fi
fi

cp ./Xray-linux-64/geoip.dat /usr/local/share/xray
cp ./Xray-linux-64/geosite.dat /usr/local/share/xray
cp ./Xray-linux-64/xray /usr/local/bin
chmod 755 /usr/local/bin/xray
cp ./xray.service /etc/systemd/system
chmod 644 /etc/systemd/system/xray.service
systemctl daemon-reload

if [[ $Xray_SERVICE_ALREADY_INSTALLED -eq 1 ]]; then
  echo 'INFO: Xray service updated'
else
  systemctl enable xray.service
  echo 'INFO: Xray service installed and enabled for startup'
fi
if [[ -f '/usr/local/etc/xray/config.json' ]]; then
  echo 'INFO: Starting Xray service...'
  systemctl start xray.service
  sleep 2s
  if ! systemctl -q is-active xray.service; then
    echo 'ERROR: Failed to start Xray service.' >&2
    exit 1
  fi
  echo 'INFO: Xray service started.'
else
  echo 'WARN: /usr/local/etc/xray/config.json not found, skip starting service'
fi

### Install VeePeeNET part
if [[ -d '/usr/local/lib/veepeenet' ]] || [[ -d '/etc/veepeenet/xray' ]]  || [[ -d '/var/log/veepeenet/xray' ]]; then
  echo 'INFO: Updating VeePeeNET for Xray service configuration...'
else
  echo 'INFO: Installing VeePeeNET for Xray service configuration...'
fi

mkdir -p \
  /usr/local/lib/veepeenet \
  /usr/local/etc/veepeenet/xray \
  /var/log/veepeenet/xray \

cp ./common.py /usr/local/lib/veepeenet
cp ./xray.py /usr/local/lib/veepeenet

cat > /usr/local/lib/veepeenet/xray-config.sh << EOF
#!/bin/bash
/usr/bin/python3 /usr/local/lib/veepeenet/xray.py "\$@"
EOF
chmod 744 /usr/local/lib/veepeenet/xray-config.sh

rm -f /usr/local/bin/xray-config
ln -s /usr/local/lib/veepeenet/xray-config.sh /usr/local/bin/xray-config

echo 'INFO: VeePeeNET for Xray service is ready.'
