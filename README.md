# VeePeeNET

Install and configure personal anti-censorship service [Xray](https://github.com/xtls/xray-core)

## Requirements

1. Ubuntu Server 24.04+ (amd64) 
2. Internet connection

## Features

- Installing Xray
- Creating and changing Xray server configuration (Vless with Reality)
- Adding and removing Xray server clients
- Managing outbound Vless connections
- Flexible routing rules management
- Geodata updates for geoip/geosite based routing

## Installation
Download and install the `.deb` package:
```text
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
        && curl -LO https://github.com/spector517/veepeenet/releases/download/v2.4.2/veepeenet_2.4.2_amd64.deb \
        && sudo apt install -y ./veepeenet_2.4.2_amd64.deb
    )
```

## Usage

### Configure and add clients

Configure Xray server on host **my.domain.com**:
```commandline
sudo xrayctl config --host my.domain.com
```
The `host` may be a **public** IP address or a domain name. 
It is recommended to specify it manually, as the automatic detection may not work correctly in some environments (e.g. behind NAT).

Create client configurations
**my_client1** and **my_client2** and print share links:
```commandline
sudo xrayctl clients add my_client1 my_client2
```

Start Xray service for the first time:
```commandline
sudo xrayctl start
```

### Remove clients

Remove client **my_client2**:
```commandline
sudo xrayctl clients remove my_client2
```

### List clients

Show all clients with share links:
```commandline
sudo xrayctl clients list
```

Show clients in JSON format:
```commandline
sudo xrayctl clients list --json
```

### Recreate configuration

Remove current configuration and create new configuration. All clients will be removed:
```commandline
sudo xrayctl config --host my.domain.com --clean
```

Add new clients again:
```commandline
sudo xrayctl clients add new_client1
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

### GUI client
You can use [Happ](https://www.happ.su/main) GUI client to connect to the server. Just import the generated share link and connect.
Or you can use any other client recommended by [Xray project](https://github.com/XTLS/Xray-core/blob/main/README.md#gui-clients)

## Commands

### Configure Xray Vless server with Reality
```
sudo xrayctl config [OPTIONS]
```

#### Options
| Option          | Type    | Description                                                                                              |
| --------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| --host          | TEXT    | Public interface of server. Using `hostname -i` if not specified. It is recommended to specify manually. |
| --port          | INTEGER | Inbound port. [default: 443]                                                                             |
| --reality-host  | TEXT    | Reality host. [default: microsoft.com]                                                                   |
| --reality-port  | INTEGER | Reality port. [default: 443]                                                                             |
| --reality-names | TEXT    | Available Reality server names. [default: Reality host]                                                  |
| --name          | TEXT    | Human-readable server name (used after # in client links).                                               |
| --clean         | FLAG    | Override current configuration (All clients will be removed) [default: no-clean]                         |

### Update geodata
```
sudo xrayctl update-geodata
```
Updates `geoip.dat` and `geosite.dat` files used for geo-based routing rules.

### Update Xray distribution
```
sudo xrayctl update-xray [OPTIONS]
```
Updates Xray distribution to a selected or latest version. Shows a list of available releases from GitHub and allows you to choose which version to install.

#### Options

| Option    | Type    | Description                                         |
| --------- | ------- | --------------------------------------------------- |
| --version | TEXT    | Target version (e.g. v1.8.24 or 1.8.24)             |
| --list    | FLAG    | List available versions and exit                    |
| --limit   | INTEGER | Number of versions to show with --list [default: 9] |
| --json    |         | Show --list output in JSON format                   |

### Show Xray service status
```
sudo xrayctl status [OPTIONS]
```

#### Options

| Option | Type | Description         |
| ------ | ---- | ------------------- |
| --json | FLAG | Show in JSON-format |

#### Examples
```commandline
sudo xrayctl status
```
```
┌ [My Server] Xray server information ──────────────┐
│ status: stopped (disabled)                        │
│ uptime: n/a                                       │
│ xray_version: v25.12.8                            │
│ address: example.com:443                          │
│ reality_address: microsoft.com:443                │
│ reality_names: microsoft.com                      │
│ clients: Server has no clients                    │
│ rules: No routing rules configured                │
│ outbounds: freedom, blackhole                     │
└───────────────────────────────VeePeeNET 2.4.2─────┘
```

```commandline
sudo xrayctl status --json
```
```json
{
  "veepeenet_version": "2.4.2",
  "veepeenet_build": 0,
  "xray_version": "v25.12.8",
  "server_status": "stopped",
  "enabled": false,
  "restart_required": false,
  "server_host": "example.com",
  "server_port": "443",
  "reality_address": "microsoft.com:443",
  "reality_names": ["microsoft.com"],
  "clients": {
    "clients": []
  },
  "routing": {},
  "outbounds": [
    {"name": "freedom"},
    {"name": "blackhole"},
    {"name": "dns"}
  ],
  "server_name": "My Server"
}
```

### Start, stop or restart Xray server
```commandline
sudo xrayctl start
```
```commandline
sudo xrayctl stop
```
```commandline
sudo xrayctl restart
```

---

### Clients management

#### Add clients
```commandline
sudo xrayctl clients add CLIENT_NAMES...
```
If a client with the same name already exists, it will be ignored.

#### Remove clients
Clients with names that do not exist on the server will be ignored.
```commandline
sudo xrayctl clients remove CLIENT_NAMES...
```

#### List clients
```text
sudo xrayctl clients list [OPTIONS]
```

| Option | Type | Description         |
| ------ | ---- | ------------------- |
| --json | FLAG | Show in JSON-format |

---

### Outbounds management

#### Add Vless outbound
```text
sudo xrayctl outbounds add NAME [OPTIONS]
```

| Option        | Type    | Description                                             |
| ------------- | ------- | ------------------------------------------------------- |
| --address     | TEXT    | Outbound address (IP or domain name) **(required)**     |
| --uuid        | TEXT    | Vless client identifier **(required)**                  |
| --sni         | TEXT    | Server name of target server **(required)**             |
| --short-id    | TEXT    | One of short_id of target server **(required)**         |
| --password    | TEXT    | Public key of target server **(required)**              |
| --spider-x    | TEXT    | Initial path and parameters for the spider [default: /] |
| --port        | INTEGER | Vless outbound port [default: 443]                      |
| --fingerprint | TEXT    | Browser TLS Client Hello fingerprint [default: chrome]  |
| --interface   | TEXT    | Send through interface [default: 0.0.0.0]               |

#### Add Vless outbound from URL
```text
sudo xrayctl outbounds add-from-url 'URL' [OPTIONS]
```

| Option      | Type | Description                                        |
| ----------- | ---- | -------------------------------------------------- |
| --name      | TEXT | Outbound name (uses URL fragment if not specified) |
| --interface | TEXT | Send through interface [default: 0.0.0.0]          |

#### Remove Vless outbound
```commandline
sudo xrayctl outbounds remove NAME
```

#### Change Vless outbound
```text
sudo xrayctl outbounds change NAME [OPTIONS]
```

| Option        | Type    | Description                                            |
| ------------- | ------- | ------------------------------------------------------ |
| --address     | TEXT    | Outbound address (IP or domain name)                   |
| --uuid        | TEXT    | Vless client identifier                                |
| --sni         | TEXT    | Server name of target server                           |
| --password    | TEXT    | Public key of target server                            |
| --short-id    | TEXT    | One of short_id of target server                       |
| --spider-x    | TEXT    | Initial path and parameters for the spider             |
| --port        | INTEGER | Vless outbound port                                    |
| --fingerprint | TEXT    | Browser TLS Client Hello fingerprint [default: chrome] |
| --interface   | TEXT    | Send through interface [default: 0.0.0.0]              |
| --new-name    | TEXT    | New outbound name                                      |

#### Set default outbound
```commandline
sudo xrayctl outbounds set-default NAME
```
Moves the specified outbound to the first position, making it the default.

---

### Routing management

#### List routing rules
```text
sudo xrayctl routing list [OPTIONS]
```

| Option | Type | Description         |
| ------ | ---- | ------------------- |
| --json | FLAG | Show in JSON-format |

##### Example
```commandline
xrayctl routing list
```
```
┌──────────────────────────────────────────┐
│ Domain strategy: AsIs                    │
└──────────────────────────────────────────┘
┌ Rule #10 block-ads --> blackhole ────────┐
│ name: block-ads                          │
│ domains: geosite:category-ads-all        │
└──────────────────────────────────────────┘
┌ Rule #20 bypass-ru --> freedom ──────────┐
│ name: bypass-ru                          │
│ domains: geosite:category-gov-ru         │
│ ips: geoip:ru                            │
└──────────────────────────────────────────┘
```

#### Add routing rule
```text
xrayctl routing add-rule NAME [OPTIONS]
```

| Option     | Type    | Description                                                        |
| ---------- | ------- | ------------------------------------------------------------------ |
| --outbound | TEXT    | Outbound name to which the rule will direct traffic **(required)** |
| --domain   | TEXT    | List of domain patterns to match (e.g. "domain:example.com")       |
| --ip       | TEXT    | List of IPs or IP ranges to match (e.g. "123.123.123.123")         |
| --ports    | TEXT    | Port or port range to match (e.g. "53,443,60-89")                  |
| --protocol | TEXT    | List of protocols to match: http, tls, quic or bittorrent          |
| --priority | INTEGER | Priority of the rule (lower value means higher priority)           |

At least one condition (`--domain`, `--ip`, `--ports`, `--protocol`) must be specified.

#### Remove routing rule
```commandline
sudo xrayctl routing remove-rule NAME
```

#### Rename routing rule
```commandline
sudo xrayctl routing rename-rule NAME --new-name NEW_NAME
```

#### Change rule priority
```commandline
sudo xrayctl routing set-priority NAME --priority VALUE
```

#### Change rule conditions
```text
sudo xrayctl routing change-rule NAME ACTION [OPTIONS]
```

Where `ACTION` is either `put` (add values) or `del` (remove values).

| Option     | Type | Description                                                    |
| ---------- | ---- | -------------------------------------------------------------- |
| --domain   | TEXT | List of domain patterns to add/remove                          |
| --ip       | TEXT | List of IPs or IP ranges to add/remove                         |
| --ports    | TEXT | Port or port range to add/remove                               |
| --protocol | TEXT | List of protocols to add/remove: http, tls, quic or bittorrent |

#### Set domain strategy
```commandline
sudo xrayctl routing set-domain-strategy STRATEGY
```
Where `STRATEGY` is one of the available routing domain strategy values (e.g. `AsIs`, `IPIfNonMatch`, `IPOnDemand`).

#### Change rule outbound
```commandline
sudo xrayctl routing change-outbound NAME --outbound OUTBOUND_NAME
```
Changes the outbound to which the specified rule directs traffic.

## Removing

```commandline
sudo apt remove veepeenet
```

# License
MIT
