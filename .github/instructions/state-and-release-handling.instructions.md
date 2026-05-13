---
description: "Use when editing state/status output, traffic statistics, reset-stats, Xray release selection, restart-required detection, JSON config comparison, or README updates for these behaviors. Covers app/controller/common.py, app/controller/commands/state.py, app/controller/commands/configure.py, app/utils.py, app/view.py, app/model/veepeenet.py, tests, and README files."
name: "State And Release Handling"
applyTo:
  - "app/controller/common.py"
  - "app/controller/commands/state.py"
  - "app/controller/commands/configure.py"
  - "app/utils.py"
  - "app/view.py"
  - "app/model/veepeenet.py"
  - "app/model/xray.py"
  - "tests/test_controller.py"
  - "tests/test_utils.py"
  - "tests/test_view.py"
  - "README.md"
  - "README.en.md"
---
# State, Stats, And Release Handling

- Treat traffic statistics as two layers: persisted counters in `veepeenet.stats` and live counters from the Xray API. Status views should display the sum of both, not one source alone.
- `reset-stats` is a dual reset. It must clear `veepeenet.stats` in the config and, when Xray is running, also reset live API counters through `reset_xray_stats()`.
- Before `stop` and `restart`, preserve runtime counters by calling `_store_runtime_stats()` so traffic is not lost across service transitions.
- For restart-required detection, compare parsed JSON structures with `is_json_content_same(...)`, not raw file bytes. Ignore top-level `veepeenet` when the intent is to detect config changes that require an Xray restart.
- Explicit Xray version selection is broader than release listing. `update-xray --version ...` should query enough GitHub releases and include prereleases so tags like beta/rc can still be resolved.
- Keep user-facing docs aligned when these behaviors change. `README.md` is the primary Russian document; `README.en.md` should be updated alongside it when command semantics or examples change.
- Prefer focused regression tests in `tests/test_controller.py`, `tests/test_utils.py`, and `tests/test_view.py` for stats accumulation/reset, prerelease version lookup, and structural JSON comparison.