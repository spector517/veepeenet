# VeePeeNET

Install and configure personal anti-censorship services ([WireGuard](https://www.wireguard.com) and [Xray](https://github.com/xtls/xray-core))

## Requirements

1. Ubuntu Server (22.04, 24.04)
2. Python 3.8+
3. Internet connection

## WireGuard

### Features

- Installing Wireguard VPN Server
- Creating, storing and changing VPN server configuration
- Adding and removing VPN server clients

### Installation
Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./install.sh wireguard)
    )
```


### Usage

#### Configure and add clients

```commandline
sudo wg-config --host my.domain.com --add-clients my_client1 my_client2 --output ./my_clients
```
Configure WireGuard server on host **my.domain.com**, create  client configuration files 
**my_client1** and **my_client2** and save it to path **./my_clients**

#### Remove clients

```commandline
sudo wg-config --remove-clients my_client2
```
Remove client **my_client2** configuration

#### Recreate configuration

```commandline
sudo wg-config --clean --host my.domain2.com --add-clients client1 client2 client3 --output ./my_clients
```
Remove current configuration and create new configuration

#### Get help

```commandline
sudo wg-config --help
```
Show help message

### Command line options

- ```--host``` The IP/DNS-name of current host. Using ```hostname -i``` if not specified.
It is recommended to specify manually.
- ```--port``` VPN service port. Default is 51820.
- ```--subnet``` Wireguard server subnet address. Default is: 10.9.0.1/24.
- ```--interface``` Name of Wireguard virtual network interface. Default is wg0.
- ```--dns``` Domain names servers. Default is 1.1.1.1 1.0.0.1.
- ```--add-clients``` List of Wireguard server clients names. Default - no generate clients configs.
- ```--remove-clients``` Removing clients list of Wireguard server. Non-existing clients names will be ignored.
- ```--output``` Path to output clients configs directory. Default is /usr/local/etc/veepeenet/wg/clients.
- ```--clean``` Remove existing config. Default is False.
- ```--check``` Dry run. Print changed files content to the console
- ```--no-ufw``` Do not use the Uncomplicated Firewall.

### Removing

Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./uninstall.sh wireguard)
    )
```

## Xray (Vless XTLS-Reality)

### Features

- Installing Xray
- Creating, storing and changing  XRAY server configuration
- Adding and removing XRAY server clients

### Installation
Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./install.sh xray)
    )
```

### Usage

#### Configure and add clients

```commandline
sudo xray-config --host my.domain.com --add-clients my_client1 my_client2
```

Configure XRAY server on host **my.domain.com**, create client configuration s
**my_client1** and **my_client2** and print share links

#### Remove clients

```commandline
sudo xray-config --remove-clients my_client2
```
Remove client **my_client2**

#### Recreate configuration

```commandline
sudo xray-config --clean --host my.domain2.com --add-clients client1 client2 client3 
```
Remove current configuration and create new configuration

#### Get help

```commandline
sudo xray-config --help
```
Show help message

### Command line options

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

### Removing

Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./uninstall.sh xray)
    )
```

## License
MIT
