# AGENTS.md

## Project Overview

VeePeeNET is a CLI tool (`xrayctl`) for managing a [Xray](https://github.com/xtls/xray-core) VLESS Reality proxy server on Ubuntu. Python 3.12+, built with **Typer** (CLI), **Pydantic** (models), **Rich** (terminal UI), **requests** (HTTP), and **xxhash** (short ID generation). Installed system-wide into a venv at `/usr/local/lib/veepeenet/`.

**Entry points** (defined in `pyproject.toml`):
- `xrayctl` → `app.main:typer_app` — main CLI
- `xray-migrate-1-to-2` → `app.migration_1_2:main` — one-shot v1→v2 config migration

## Architecture

```
app/cli.py                    — Typer app + sub-typers (clients, routing, outbounds)
app/main.py                   — Entrypoint; imports all command modules to register them
app/model/                    — Pydantic models mirroring Xray JSON config structure
app/controller/common.py      — Shared helpers (load/save config, ClientData, RuleData, error_handler)
app/controller/completions.py — Shell autocompletion callbacks for client/route/outbound names
app/controller/commands/      — Command implementations (one file per command group)
app/view.py                   — Pydantic view-models with rich_repr() (full) and rich_repr_short() (inline) for terminal output
app/utils.py                  — OS/network helpers (systemctl, file I/O, Xray binary ops)
app/defaults.py               — Hardcoded paths, default values, style constants, exit codes
app/migration_1_2.py          — Standalone v1→v2 config migration script
```

**Data flow:** CLI command → `controller/commands/*.py` → loads Xray JSON config via `common.load_config()` → deserializes into `model/xray.Xray` (Pydantic) → mutates model → serializes back with `model_dump_json(by_alias=True, exclude_none=True, indent=2)` → writes to `/usr/local/etc/xray/config.json`.

**Command registration pattern:** Commands are registered by side effects imports in `app/main.py`. Each `controller/commands/*.py` file decorates functions with `@app.command()` or sub-typer decorators (`@clients.command()`, `@routing.command()`, `@outbounds.command()`) imported from `app/cli`.

## Model Conventions

- All models extend `XrayModel` (`app/model/base.py`) which uses `to_camel` alias generator, `populate_by_name=True`, and `extra='allow'` — this preserves unknown Xray config fields during round-trip serialization.
- Use **Python snake_case** field names in code; Pydantic auto-converts to **camelCase** for JSON via aliases.
- Outbound types are discriminated unions via `Field(discriminator='protocol')` — see `app/model/xray.py:Outbound`.
- Required outbounds (`FreedomOutbound`, `BlackholeOutbound`, `DnsOutbound`) are auto-injected during serialization by `Xray._ensure_required_outbounds`.
- `Xray._fill_veepeenet` (`model_validator(mode='after')`) auto-creates the `veepeenet` config section from the VLESS inbound's `listen` field if absent; raises `ValueError` if no VLESS inbound is found — so configs without a VLESS inbound cannot be loaded.
- **Serialization standard** — save: `model.model_dump_json(by_alias=True, exclude_none=True, indent=2)`; load: `Model.model_validate_json(content, by_alias=True)`. Both `by_alias=True` calls are required — omitting them breaks camelCase round-trips.

## Controller Conventions

- Every command function must be wrapped with `@error_handler(default_message=..., default_code=...)` for consistent error reporting.
- Every command accepts a hidden `_debug: Annotated[bool, Option('--debug', hidden=True)] = False` parameter — when `True`, `error_handler` re-raises exceptions instead of pretty-printing them.
- Commands requiring root access call `check_root()` first; commands needing an existing config call `check_xray_config()`. Commands interacting with the running service (`config`, `status`, `start`, `stop`, `restart`) also call `check_distrib()` which auto-installs the Xray binary and systemd unit if missing.
- Exit codes in `defaults.py` are grouped by command module: 1–2 general, 10–14 configure, 20 clients, 30–33 state, 40–47 outbound, 50–59 routing. New command groups should allocate the next tens range (next available: 60+).
- Client identity is encoded in email field format: `{name}.{short_id}@{host}` — parsed/built via `ClientData.from_model()` / `ClientData.to_model()`. Short IDs are generated via `xxhash.xxh64(name).hexdigest()`. Client UUIDs are deterministic: `uuid5(namespace, name)` where `namespace` is stored in the `veepeenet` config section.
- Routing rule priority is encoded in the tag: `{name}.{priority}` — parsed/built via `RuleData`.

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
- `debian/` — Debian packaging scripts (`postinst`, `prerm`, `postrm`) for `.deb` distribution; installs into venv at `/usr/local/lib/veepeenet/`
- `deploy-playbook.yml` — Ansible playbook for remote deployment
- `release.jenkinsfile` / `deploy.jenkinsfile` — CI/CD pipelines

