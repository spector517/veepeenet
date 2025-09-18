# VeePeeNET

Install and configure personal anti-censorship service [Xray](https://github.com/xtls/xray-core)

## Requirements

1. Ubuntu Server (22.04, 24.04)
2. Python 3.10+
3. Internet connection

## Features

- Installing Xray
- Creating, storing and changing  XRAY server configuration
- Adding and removing XRAY server clients

## Installation
Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./install-xray.sh)
    )
```

## Usage

### Configure and add clients

```commandline
sudo xray-config --host my.domain.com --add-clients my_client1 my_client2
```

Configure XRAY server on host **my.domain.com**, create client configuration s
**my_client1** and **my_client2** and print share links

### Remove clients

```commandline
sudo xray-config --remove-clients my_client2
```
Remove client **my_client2**

### Recreate configuration

```commandline
sudo xray-config --clean --host my.domain2.com --add-clients client1 client2 client3 
```
Remove current configuration and create new configuration

### Get help

```commandline
sudo xray-config --help
```
Show help message

## Command line options

- ```--host``` The IP/DNS-name of current host. Using ```hostname -i``` if not specified.
It is recommended to specify manually.
- ```--port``` The XRAY server port. Default is 443
- ```--reality-host``` The reality host for active probing. Default is microsoft.com
- ```--reality-port``` The reality port for active probing. Default is 443
- ```--add-clients``` List of XRAY server clients names. Default - no generate clients configs.
- ```--remove-clients``` Removing clients list of XRAY server. Non-existing clients names will be ignored.
- ```--clean``` Remove existing config. Default is False.
- ```--check``` Dry run. Print changed files content to the console.
- ```--no-ufw``` Do not use the Uncomplicated Firewall
- ```--status``` Show Xray server information

## Removing

Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./uninstall-xray.sh)
    )
```

# License
MIT
