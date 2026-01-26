# VeePeeNET

Install and configure personal anti-censorship service [Xray](https://github.com/xtls/xray-core)

## Requirements

1. Ubuntu Server (24.04+)
2. Python 3.12+
3. Internet connection

## Features

- Installing Xray
- Creating and changing XRAY server configuration (VLESS with Reality)
- Adding and removing XRAY server clients

## Installation
Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./install.sh)
    )
```

## Usage

### Configure and add clients

Configure XRAY server on host **my.domain.com**:
```commandline
sudo xrayctl config --host my.domain.com
```

Create client configurations:
**my_client1** and **my_client2** and print share links
```commandline
sudo xrayctl add-clients my_client1 my_client2
```

Start Xray service first time:
```commandline
sudo xrayctl start
```

### Remove clients

Remove client **my_client2**:
```commandline
sudo xrayctl remove-clients my_client2
```

### Recreate configuration

Remove current configuration and create new configuration. All client will be removed:
```commandline
sudo xrayctl config --host my.domain.com --clean
```

Add new clients again:
```commandline
sudo xrayctl add-clients new_client1
```

Restart Xray service to apply changes:
```commandline
sudo xrayctl restart
```

### Get help

Show rich help message:
```commandline
sudo xrayctl --help
```

## Commands

### Initialize Xray VLESS server with Reality
```
xrayctl config [OPTIONS]
```

#### Options
| Option         | Type    | Description                                                                                              |
|----------------|---------|----------------------------------------------------------------------------------------------------------|
| --host         | TEXT    | Public interface of server. Using `hostname -i` if not specified. It is recommended to specify manually. |
| --port         | INTEGER | Inbound port. [default: 443]                                                                             |
| --reality-host | TEXT    | Reality host. [default: microsoft.com]                                                                   |
| --reality-port | INTEGER | Reality port. [default: 443]                                                                             |
| --clean        | FLAG    | Override current configuration (All clients will be removed) [default: no-clean]                         |

### Show Xray service status
```
xrayctl status [OPTIONS]
```

#### Options

| Option | Type | Description         |
|--------|------|---------------------|
| --json | FLAG | Show in JSON-format |

#### Examples
```commandline
xrayctl status
```
```
----------- VeePeeNET v2.0.0 build 0 -----------
Xray server info:
	version: v25.12.8
	status: Stopped
	address: example.com:443
	reality_address: microsoft.com:443
	clients:
		Server has no clients
---------------------------------------------------
```

```commandline
xrayctl status --json
```
```
{
  "veepeenet_version": "v2.0.0",
  "veepeenet_build": 0,
  "xray_version": "v25.12.8",
  "server_status": "Stopped",
  "server_host": "example.com",
  "server_port": 443,
  "reality_address": "microsoft.com:443",
  "clients": []
}
```

### Add clients to Xray server
```commandline
xrayctl add-clients CLIENT_NAMES...
```
If a client with the same name already exists, it will be ignored.

### Remove clients
Clients with names that do not exist on the server will be ignored.
```commandline
xrayctl remove-clients CLIENT_NAMES...
```

### Start, stop or restart Xray server
```commandline
xrayctl start
```
```commandline
xrayctl stop
```
```commandline
xrayctl restart
```

## Removing

Run simple command:
```commandline
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/latest/download/veepeenet.tar.gz \
        && tar -xf veepeenet.tar.gz && (cd veepeenet-* && sudo ./uninstall.sh)
    )
```

# License
MIT
