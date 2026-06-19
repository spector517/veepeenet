# AGENTS.md

## Project Overview

VeePeeNET is a CLI tool (`xrayctl`) for managing a [Xray](https://github.com/xtls/xray-core) VLESS Reality proxy server on Ubuntu. Python 3.12+, built with **Typer** (CLI), **Pydantic** (models), **Rich** (terminal UI), **requests** (HTTP), and **xxhash** (short ID generation). Installed system-wide into a venv at `/usr/local/lib/veepeenet/`.

**User docs:** `README.md` is the primary Russian README; `README.en.md` is the English mirror. When changing user-facing CLI behavior or examples, keep both aligned and prefer linking to the README instead of duplicating large sections here.

**Entry points** (defined in `pyproject.toml`):
- `xrayctl` → `app.main:typer_app` — main CLI
- `xray-migrate-1-to-2` → `app.migration_1_2:main` — one-shot v1→v2 config migration

## Architecture

```
app/cli.py                    — Typer app + sub-typers (clients, routing, outbounds)
app/main.py                   — Entrypoint; imports all command modules to register them
app/model/                    — Pydantic models mirroring Xray JSON config structure
app/controller/common.py      — Shared helpers (load/save config, error_handler, service control, runtime stats)
app/controller/data.py        — Data transfer objects: ClientData, RuleData, StatsData (bridge between Pydantic models and domain logic)
app/controller/completions.py — Shell autocompletion callbacks for client/route/outbound names
app/controller/commands/      — Command implementations (one file per command group)
app/view.py                   — Pydantic view-models with rich_repr() (full) and rich_repr_short() (inline) for terminal output
app/utils.py                  — OS/network helpers (systemctl, file I/O, Xray binary ops)
app/defaults.py               — Hardcoded paths, default values, style constants, exit codes
app/migration_1_2.py          — Standalone v1→v2 config migration script
```

**Data flow:** CLI command → `controller/commands/*.py` → loads Xray JSON config via `common.load_config()` → deserializes into `model/xray.Xray` (Pydantic) → mutates model → serializes back with `model_dump_json(by_alias=True, exclude_none=True, indent=2)` → writes to `/usr/local/etc/xray/config.json`.

**Traffic stats flow:** live Xray API stats are parsed in `controller/data.py:StatsData`, accumulated into `/usr/local/etc/veepeenet/stats.json` by `controller/common.py`, and displayed by `state.status()` as **stored + runtime** totals. `reset-stats` clears persisted stats and, when the service is running, also resets live counters via the Xray API.

**Command registration pattern:** Commands are registered by side effects imports in `app/main.py`. Each `controller/commands/*.py` file decorates functions with `@app.command()` or sub-typer decorators (`@clients.command()`, `@routing.command()`, `@outbounds.command()`) imported from `app/cli`.

## Model Conventions

- All models extend `XrayModel` (`app/model/base.py`) which uses `to_camel` alias generator, `populate_by_name=True`, and `extra='allow'` — this preserves unknown Xray config fields during round-trip serialization.
- Use **Python snake_case** field names in code; Pydantic auto-converts to **camelCase** for JSON via aliases.
- Outbound types are discriminated unions via `Field(discriminator='protocol')` — see `app/model/xray.py:Outbound`.
- `Xray.inbounds` and `Xray.outbounds` also accept plain `dict` entries — unknown protocol types are preserved as-is during round-trip.
- Required outbounds (`FreedomOutbound`, `BlackholeOutbound`, `DnsOutbound`) are auto-injected during serialization by `Xray._ensure_required_outbounds`.
- `Xray._ensure_required_outbounds` also auto-populates missing `api`, `policy`, and `stats` sections during serialization. Do not remove or bypass this in save paths, or traffic accounting and Xray API access will silently disappear from rewritten configs.
- `Xray._fill_veepeenet` (`model_validator(mode='after')`) auto-creates the `veepeenet` config section from the VLESS inbound's `listen` field if absent; raises `ValueError` if no VLESS inbound is found — so configs without a VLESS inbound cannot be loaded.
- **Serialization standard** — save: `model.model_dump_json(by_alias=True, exclude_none=True, indent=2)`; load: `Model.model_validate_json(content, by_alias=True)`. Both `by_alias=True` calls are required — omitting them breaks camelCase round-trips.
- `Sniffing` is included in `VlessInbound` by default: `enabled=False`, `routeOnly=True`, `destOverride=['http','tls','quic']` — do not remove it to preserve the field on save.
- `Log.loglevel` normalizes `'off'` → `'none'` automatically (Xray uses `none`, not `off`).
- `TrafficStats` and `VeePeeNetStats` store cumulative `client`, `inbound`, and `outbound` traffic counters in `/usr/local/etc/veepeenet/stats.json`. `TrafficStats.__iadd__` and `VeePeeNetStats.__iadd__` are additive merges, so status output should combine persisted and runtime stats rather than replacing one with the other.
- `Rule` model exposes only a subset of Xray RuleObject fields: `tag`, `outboundTag`, `protocol`, `port`, `domain`, `ip`. Other Xray fields (`network`, `sourceIP`, `user`, `inboundTag`, etc.) are preserved via `extra='allow'` but not typed — do not add them as typed fields without extending the model.

## Controller Conventions

- Every command function must be wrapped with `@error_handler(default_message=..., default_code=...)` for consistent error reporting.
- Every command accepts a hidden `_debug: Annotated[bool, Option('--debug', hidden=True)] = False` parameter — when `True`, `error_handler` re-raises exceptions instead of pretty-printing them.
- Commands requiring root access call `check_root()` first; commands needing an existing config call `check_xray_config()`. Commands interacting with the running service (`config`, `status`, `start`, `stop`, `restart`) also call `check_distrib()` which auto-installs the Xray binary and systemd unit if missing.
- Exit codes in `defaults.py` are grouped by command module: 1–2 general, 10–14 configure, 20 clients, 30–33 state, 40–47 outbound, 50–59 routing. New command groups should allocate the next tens range (next available: 60+).
- **`app/controller/data.py`** — three dataclasses that bridge Pydantic models and domain logic; always use these instead of manipulating model fields directly:
  - `ClientData` — parses/builds client identity from email (`{name}.{short_id}@{host}`); `short_id` defaults to `xxhash.xxh64(name).hexdigest()`; UUID is deterministic: `uuid5(namespace, name)` where `namespace` comes from the `veepeenet` config section. Has a custom `__init__` (not generated by `@dataclass`). Key methods: `from_model(client, index)`, `to_model()`, `get_name_by_email(email)`.
  - `RuleData` — encodes/decodes routing rule tag (`{name}.{priority}`); fallback priority is `(index+1)*10` when the tag cannot be parsed as `name.int`. Key methods: `from_model(rule, number)`, `to_model()`.
  - `StatsData` — parses Xray API stats strings (`subject>>>name>>>traffic>>>direction`); `from_api()` returns `None` for malformed or unknown entries. Nested `SubjectType` and `DirectionType` are `StrEnum`s with a `from_name()` factory. Key methods: `from_api(stats)`, `to_model()`.
- **State/statistics helpers in `app/controller/common.py`** — `get_runtime_stats(reset=False)` reads live counters from the Xray API, `get_stored_stats()` reads persisted counters from `/usr/local/etc/veepeenet/stats.json`, `_store_runtime_stats()` persists live counters before stop/restart, and `clear_stats()` resets the stats file plus live API stats when the service is running.
- **Config change detection** — `state.status()` uses `utils.is_json_content_same()` instead of raw file comparison. When checking `restart_required`, compare parsed JSON structures and ignore the top-level `veepeenet` key so field order and accumulated stats do not produce false positives.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests 
pytest tests -v --tb=short

# Run tests
pytest

# Run linter
pylint app/

# Lint Ansible playbooks
ansible-lint deploy-playbook.yml

# Run tests with coverage
pytest --cov=app

# Build distribution
python -m build
```

Tests mock OS-level calls (`systemctl`, `xray` binary, file I/O) via `pytest-mock`. Test fixtures use JSON configs in `tests/resources/`. Each test file tests one module — naming: `test_{module}.py` (e.g. `test_utils.py`, `test_controller.py`, `test_completions.py`). Exception: `migration_1_2_test.py`. No `conftest.py` — fixtures are defined inline in each test file. Related tests are grouped in `class Test*:` (e.g. `class TestLoadConfig:`, `class TestCreateConfig:`).

**Test fixture files (`tests/resources/`):**

| File | Purpose |
|------|---------|
| `initial_xray_config.json` | Minimal config — VLESS inbound only, no clients |
| `valid_xray_config.json` | Full valid config — no clients, all required fields |
| `valid_xray_config_with_clients.json` | Full config with 2 clients — used for client list/remove tests |
| `completions_xray_config.json` | Config for autocompletion callback tests |
| `invalid_xray_config.json` | Schema violations — for error handling tests |
| `xray_v1_config.json` | Old v1 format — migration source |
| `xray_v1_migrated_to_v2_config.json` | Expected v2 result after migration |

**Key mock patterns:**
```python
# Subprocess commands
mocker.patch('app.utils.run_command', return_value=(0, 'stdout', 'stderr'))
# File writes (assert no disk I/O)
mocker.patch('app.utils.write_text_file')
# Streaming HTTP responses
mock_response.iter_content.return_value = iter([chunk1, chunk2])
```

**Pylint config** (`.pylintrc`): max line length **111**. Disabled rules: `C0114`, `C0115`, `C0116` (module/class/function docstrings), `R0903` (too-few-public-methods), `R0913`, `R0917` (argument counts). Do not add docstrings to existing undocumented code.

## Key Files

- `app/resources/versions.json` — bundled version metadata (veepeenet + xray version), updated at release time
- `app/resources/xray.service` — systemd unit template installed to `/etc/systemd/system/xray.service`
- `app/model/types.py` — type aliases: `FingerprintType` (tls fingerprints), `RuleProtocolType` (`http|tls|quic|bittorrent`), `RoutingDomainStrategyType` (`AsIs|IPIfNonMatch|IPOnDemand`)
- `README.md` / `README.en.md` — end-user docs for the CLI; Russian README is the primary version and currently documents traffic statistics and `reset-stats`
- `app/defaults.py` — all constants; see table below
- `debian/` — Debian packaging scripts (`postinst`, `prerm`, `postrm`) for `.deb` distribution; installs into venv at `/usr/local/lib/veepeenet/`
- `deploy-playbook.yml` — Ansible playbook for remote deployment
- `release.jenkinsfile` / `deploy.jenkinsfile` — CI/CD pipelines

**System paths (from `app/defaults.py`):**

| Constant | Path |
|----------|------|
| `XRAY_CONFIG_PATH` | `/usr/local/etc/xray/config.json` |
| `XRAY_CONFIG_BACKUP_PATH` | `/usr/local/etc/xray/config.json.bak` |
| `XRAY_BINARY_PATH` | `/usr/local/bin/xray` |
| `XRAY_SERVICE_UNIT_PATH` | `/etc/systemd/system/xray.service` |
| `XRAY_LOGS_PATH` / `XRAY_ERROR_LOG_PATH` | `/var/log/xray/` / `/var/log/xray/error.log` |
| `XRAY_GEO_IP_DATA_PATH` | `/usr/local/share/xray/geoip.dat` |
| `XRAY_GEO_SITE_DATA_PATH` | `/usr/local/share/xray/geosite.dat` |

**Default config values:** Reality host `microsoft.com:443`, VLESS listen `0.0.0.0:443`, fingerprint `chrome`, spiderX `/`.

## CLI Command Reference

20 commands across 5 modules. All require root; service commands also auto-install the Xray binary if missing.

| Module | Command | Purpose |
|--------|---------|---------|
| configure.py | `config [--host] [--port] [--reality-host] [--reality-port] [--reality-names] [--name] [--clean]` | Create/update VLESS inbound; auto-detects public IPv4 if `--host` omitted |
| configure.py | `update-geodata` | Downloads `geoip.dat` + `geosite.dat` from v2ray-rules-dat |
| configure.py | `update-xray [--list] [--limit N] [--version X] [--json]` | Install/update Xray binary; auto-selects latest if no version given; explicit `--version` lookup fetches a wider release window and includes prereleases |
| state.py | `status [--json]` | Full server view: process state, versions, merged stored+runtime traffic stats, clients/rules/outbounds, restart-required flag |
| state.py | `start` / `stop` / `restart` | Manage systemd service; validates config before start; auto-restores backup on failure |
| state.py | `reset-stats` | Clear persisted traffic stats; if Xray is running, also reset live API counters |
| clients.py | `clients add <names...>` | Add clients; generates short_id via xxhash, adds to inbound + reality shortIds |
| clients.py | `clients remove <names...>` | Remove clients by name |
| clients.py | `clients list` | Show names + VLESS links |
| outbound.py | `outbounds add <name> --address <ip> --uuid <uuid> --sni <sni> --short-id <hex> --password <pbk>` | Create VLESS outbound |
| outbound.py | `outbounds add-from-url <url> [--name]` | Parse VLESS client URL → call add |
| outbound.py | `outbounds remove <name>` | Delete; fails if outbound is used in routing |
| outbound.py | `outbounds set-default <name>` | Move outbound to position 0 (used for direct connection) |
| outbound.py | `outbounds set-outbound <name>` | Modify existing outbound settings |
| outbound.py | `outbounds list` | Show all outbounds (VLESS shown with full details) |
| routing.py | `routing add-rule <name> --outbound <out> [--domain D...] [--ip I...] [--ports P] [--protocol P...] [--priority N]` | Create rule; at least one condition required |
| routing.py | `routing remove-rule <name>` / `rename-rule <name> --new-name X` | Rule lifecycle |
| routing.py | `routing set-priority <name> --priority N` | Change priority (re-encodes tag) |
| routing.py | `routing change-rule-conditions` | Update domains/ips/ports/protocols/outbound for existing rule |
| routing.py | `routing set-domain-strategy <strategy>` | Set `routing.domainStrategy`: `AsIs` \| `IPIfNonMatch` \| `IPOnDemand` |
| routing.py | `routing change-outbound <name> --outbound <new>` | Reassign rule to different outbound |

## Xray Config Structure

VeePeeNET manages the Xray config at `/usr/local/etc/xray/config.json`. The config has this top-level structure:

```json
{
  "log": { "loglevel": "warning" },
  "dns": { "servers": [...] },
  "inbounds": [{ "protocol": "vless", ... }],
  "outbounds": [{ "protocol": "freedom" }, { "protocol": "blackhole" }, { "protocol": "dns" }, ...],
  "routing": { "domainStrategy": "AsIs", "rules": [...] },
  "veepeenet": { "host": "0.0.0.0", "namespace": "<uuid>", "name": "optional" }
}
```

### VLESS Inbound (`inbounds[0]`, protocol `vless`)

Key fields in `settings.clients[]` (mapped to `Client` model):

| Field | Description |
|-------|-------------|
| `id` | UUID — deterministic: `uuid5(veepeenet.namespace, client_name)` |
| `email` | Identity codec: `{name}.{short_id}@{host}` — parsed by `ClientData` |
| `flow` | `""` (no XTLS) or `"xtls-rprx-vision"` (recommended) or `"xtls-rprx-vision-udp443"` |
| `level` | User level for policies (default `0`) |

Reality settings in `streamSettings.realitySettings` (inbound):

| Field | Required | Description |
|-------|----------|-------------|
| `privateKey` | ✅ | X25519 private key; generated via `xray x25519` |
| `shortIds` | ✅ | List of allowed client shortIds (16-char hex each); sync with `clients` list |
| `serverNames` | ✅ | Allowed SNI values (e.g. `["microsoft.com"]`); no wildcards |
| `target` | ✅ | Redirect target for unauthenticated traffic (e.g. `"microsoft.com:443"`) |

Client-side Reality (`streamSettings.realitySettings` on outbound):

| Field | Description |
|-------|-------------|
| `password` | X25519 public key (server's `privateKey` → `xray x25519 -i <private>`) |
| `shortId` | One entry from server's `shortIds` |
| `serverName` | One entry from server's `serverNames` |
| `fingerprint` | TLS fingerprint (e.g. `"chrome"`) — required |
| `spiderX` | Spider crawl start path (default `"/"`) |

### Routing Rules (`routing.rules[]`)

Each `Rule` model field maps to Xray `RuleObject`:

| VeePeeNET field | Xray field | Description |
|-----------------|------------|-------------|
| `tag` | `outboundTag` / `ruleTag` | Encoded as `{name}.{priority}`; lower priority = evaluated first |
| `domain` | `domain` | Domains: `"baidu.com"`, `"geosite:cn"`, `"regexp:..."`, `"full:..."` |
| `ip` | `ip` | IPs/CIDRs: `"10.0.0.0/8"`, `"geoip:cn"` |
| `port` | `port` | Port(s): `"53"`, `"443"`, `"1000-2000"`, `"53,443"` |
| `protocol` | `protocol` | `"http"` \| `"tls"` \| `"quic"` \| `"bittorrent"` |
| `outbound_tag` | `outboundTag` | Target outbound tag (e.g. `"freedom"`, `"blackhole"`, or custom) |

### Required Outbounds (auto-injected by `Xray._ensure_required_outbounds`)

These three outbounds are always present in the serialized config even if absent in the loaded model:

| Protocol | Tag | Purpose |
|----------|-----|---------|
| `freedom` | `freedom` | Direct internet access; **blocks private/reserved IPs by default** (Xray security feature) |
| `blackhole` | `blackhole` | Drop traffic (returns `none` response) |
| `dns` | `dns` | DNS proxy outbound |

### VLESS URI Format

VLESS links generated by `get_vless_client_url()` follow this format:

```
vless://{uuid}@{host}:{port}?security=reality&encryption=none&flow={flow}&sni={sni}&pbk={public_key}&sid={short_id}&spx={spider_x}&type=tcp&fp={fingerprint}#{fragment}
```

## View Models (`app/view.py`)

9 Pydantic view-models; all implement `rich_repr()` (full panel) and `rich_repr_short()` (inline):

| View | Purpose |
|------|---------|
| `ClientView` | Single client: name + VLESS URL |
| `ClientsView` | List of clients |
| `RuleView` | Rule: name, domains, ips, ports, protocols, outbound, priority |
| `RoutingView` | All rules + domain strategy |
| `OutboundView` | VLESS outbound: name, address, uuid, sni, short_id, password, spider_x, port, fingerprint |
| `OutboundsView` | All VLESS outbounds |
| `ServerView` | Full status: versions, service state, enabled, uptime, host/port, reality addr/names, clients, routing, outbounds, restart_required; border color = green (running) / yellow (restart needed) / red (stopped) |
| `VersionsView` | veepeenet_version, veepeenet_build, xray_version |
| `XrayReleasesView` | GitHub releases list |

## Utilities (`app/utils.py`)

Key helpers grouped by domain:

**Xray binary:** `gen_xray_private_key()` → `gen_xray_password(key)` — calls `xray x25519` / `xray x25519 -i <key>`. `validate_xray_config(path)` → runs `xray run -test -config`.

**VLESS URL:** `get_vless_client_url(client_name, config)` → full VLESS link. `is_valid_vless_client_url(url)` → regex validation.

**System:** `detect_current_ipv4()` → `hostname -i`. `detect_ssh_port(sshd_config_path)` → parses `/etc/ssh/sshd_config`. `ufw_open_port()` → UFW rules.

**Service:** `get_xray_service_uptime()` parses `systemctl status`. `get_xray_service_journal(lines=20)` for failure diagnostics.

**Config backup:** `backup_config()` / `restore_config()` — used by `restart` to roll back on validation failure.

**Config comparison:** `is_json_content_same(path1, path2, exclude_top_level_keys=None)` — structural JSON comparison used for restart-required detection; prefer this over byte-for-byte file comparison for serialized configs.

**Stats API:** `query_xray_stats(host, port, reset=False)` returns raw Xray API stats, `reset_xray_stats(host, port)` resets live counters.

**Releases API:** `get_xray_github_releases(limit=10, include_prerelease=False)` excludes prereleases by default; pass `include_prerelease=True` for explicit version lookup flows.

## Custom Agents

`.github/agents/xray-expert.agent.md` — Invoke via `@xray-expert` when generating or validating Xray JSON config fields. Uses only the official Xray docs at https://xtls.github.io/llms-full.txt; refuses to invent fields.

**Key Xray config facts (verified by `@xray-expert`):**
- `freedom` outbound **blocks private/reserved IPs by default** when used with VLESS inbound — add `finalRules` to override.
- Routing `RuleObject` does **not** have a `type` field in Xray docs — do not add it.
- Reality `shortId` is hex, even-byte length, auto-padded to 16 chars with zeros.
- `flow: xtls-rprx-vision` blocks UDP 443 (QUIC); use `xtls-rprx-vision-udp443` to allow QUIC.
- VLESS inbound `settings.decryption` must be `"none"` (required explicit value).

