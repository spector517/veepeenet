# AGENTS.md

## Project Overview

VeePeeNET is a CLI tool (`xrayctl`) for managing an [Xray](https://github.com/xtls/xray-core) VLESS Reality proxy server on Ubuntu. Python 3.12+, built with **Typer** (CLI), **Pydantic** (models), and **Rich** (terminal UI). Installed system-wide into a venv at `/usr/local/lib/veepeenet/`.

## Architecture

```
app/cli.py          — Typer app + sub-typers (clients, routing, outbounds)
app/main.py         — Entrypoint; imports all command modules to register them
app/model/          — Pydantic models mirroring Xray JSON config structure
app/controller/     — Command implementations + shared helpers
app/view.py         — Pydantic view-models with rich_repr() for terminal output
app/utils.py        — OS/network helpers (systemctl, file I/O, Xray binary ops)
app/defaults.py     — Hardcoded paths and default values
```

**Data flow:** CLI command → `controller/commands/*.py` → loads Xray JSON config via `common.load_config()` → deserializes into `model/xray.Xray` (Pydantic) → mutates model → serializes back with `model_dump_json(by_alias=True, exclude_none=True, indent=2)` → writes to `/usr/local/etc/xray/config.json`.

**Command registration pattern:** Commands are registered by side-effect imports in `app/main.py`. Each `controller/commands/*.py` file decorates functions with `@app.command()` or sub-typer decorators (`@clients.command()`, `@routing.command()`, `@outbounds.command()`) imported from `app/cli`.

## Model Conventions

- All models extend `XrayModel` (`app/model/base.py`) which uses `to_camel` alias generator, `populate_by_name=True`, and `extra='allow'` — this preserves unknown Xray config fields during round-trip serialization.
- Use **Python snake_case** field names in code; Pydantic auto-converts to **camelCase** for JSON via aliases.
- Outbound types are discriminated unions via `Field(discriminator='protocol')` — see `app/model/xray.py:Outbound`.
- Required outbounds (`FreedomOutbound`, `BlackholeOutbound`, `DnsOutbound`) are auto-injected during serialization by `Xray._ensure_required_outbounds`.

## Controller Conventions

- Every command function must be wrapped with `@error_handler(default_message=..., default_code=...)` for consistent error reporting.
- Commands requiring root access call `check_root()` first; commands needing an existing config call `check_xray_config()`.
- Client identity is encoded in email field format: `{name}.{short_id}@{host}` — parsed/built via `ClientData.from_model()` / `ClientData.to_model()`.
- Routing rule priority is encoded in the tag: `{name}.{priority}` — parsed/built via `RuleData`.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
pylint app/

# Build distribution
python -m build
```

Tests mock OS-level calls (`systemctl`, `xray` binary, file I/O) via `pytest-mock`. Test fixtures use JSON configs in `tests/resources/`. Each test file tests one module — naming: `test_{module}.py` or `tests/test_commands_{submodule}.py` for command modules.

## Key Files

- `app/resources/versions.json` — bundled version metadata (veepeenet + xray version), updated at release time
- `app/resources/xray.service` — systemd unit template installed to `/etc/systemd/system/xray.service`
- `install.sh` / `uninstall.sh` — system-level install/remove scripts (run as root)
- `deploy-playbook.yml` — Ansible playbook for remote deployment
- `release.jenkinsfile` / `deploy.jenkinsfile` — CI/CD pipelines

