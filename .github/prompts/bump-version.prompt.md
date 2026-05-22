---
description: "Update the VeePeeNET project version across all required files from 2.5.1 or v2.5.1 with automatic v-prefix handling"
argument-hint: "2.5.1 or v2.5.1"
agent: "agent"
---

# Bump Project Version

Update the VeePeeNET version across all required files in this workspace.

## Input

The user provides one version in the format `X.X.X` or `vX.X.X`, for example `2.5.1` or `v2.5.1`.

Immediately normalize it into two forms:

- `raw_version = X.X.X`
- `tag_version = vX.X.X`

If the input does not match one of these formats, stop and ask for a valid version.

## What To Update

1. Find the current project version in the workspace and determine which files must stay in sync.
2. Update at least these required locations:
   - [pyproject.toml](../../pyproject.toml): `version = "<raw_version>"`
   - [debian/control](../../debian/control): `Version: <raw_version>`
   - [app/resources/versions.json](../../app/resources/versions.json): `veepeenet_version = "<tag_version>"`
   - [README.md](../../README.md): release artifact links and VeePeeNET version examples
   - [README.en.md](../../README.en.md): release artifact links and VeePeeNET version examples
3. After that, search the repository and update other literal references to the VeePeeNET version only when they should match the project release version.

## Rules

- Determine the `v` prefix automatically from the usage site:
  - GitHub release tags and `veepeenet_version` in JSON: with `v`
  - Python package version, Debian package version, and `.deb` filename: without `v`
- Do not change Xray versions or other third-party versions.
- Do not change template variables where the version is already computed dynamically, such as `release_version`, `DISTRIB_VERSION`, `VEEPEENET_VERSION`, and similar placeholders.
- Do not change text just because it looks like a version if it is not a VeePeeNET version.
- Make minimal edits without unrelated refactoring.

## Verification

After editing, run a narrow verification:

1. Confirm that the required files were updated correctly.
2. Search again to make sure the old VeePeeNET version is gone from the required locations.
3. If you find ambiguous matches, do not change them silently. List them separately for the user.

## Response Format

Reply briefly with:

- how the input version was normalized into `raw_version` and `tag_version`
- which files were changed
- whether any ambiguous matches were skipped or left unchanged

Execute the task as workspace file edits, not as generic advice or instructions.