---
description: "Generate a GitHub release description from git commits, code diffs, and an optional task list between two revisions"
agent: "agent"
argument-hint: "<from_rev>..<to_rev> [task list]"
---

# Generate GitHub Release Notes

Generate a polished GitHub release description in **English**, formatted as **Markdown**.

## Inputs

1. **Revision range** (optional): The user provides a range like `v1.0..v1.1` or `abc123..def456`. If no range is provided, compare the current `HEAD` against the `main` branch (i.e. `main..HEAD`).
2. **Task list** (optional): A list of completed tasks/issues. If provided, incorporate them into the release notes. If not provided, derive all information solely from commits and code changes.

## Steps

1. **Collect commits**: Run `git log --oneline --no-merges <range>` in the terminal to get the commit list.
2. **Collect changes**: Run `git diff --stat <range>` and `git diff <range>` to understand what actually changed in the code. For large diffs, use `git diff --stat <range>` first for an overview, then selectively inspect key files.
3. **Analyze**: Cross-reference commit messages with actual code diffs. Identify:
   - New features
   - Bug fixes
   - Breaking changes
   - Improvements / refactors
   - Dependency updates
   - Documentation changes
4. **Compose release notes** following the output format below.

## Output Format

```markdown
## What's Changed

### ✨ Features
- Feature description (#issue if applicable)

### 🐛 Bug Fixes
- Fix description (#issue if applicable)

### 🔧 Improvements
- Improvement description

### 📦 Dependencies
- Dependency update description

**Full Changelog**: `<from_rev>...<to_rev>`
```

## Rules

- Omit any section that has no entries (e.g. skip "Breaking Changes" if there are none).
- Write human-readable descriptions — don't just copy commit messages verbatim. Summarize and group related commits.
- If a task list is provided, link items to the corresponding changes where possible.
- Keep descriptions concise but informative.
- Output ONLY the release notes Markdown — no explanations or commentary around it.
