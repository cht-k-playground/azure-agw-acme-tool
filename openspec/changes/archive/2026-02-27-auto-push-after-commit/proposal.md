# auto-push-after-commit

## Why

This project runs on ephemeral cloud agent environments where every session starts with a clean state. If a commit is made locally but never pushed, the work is permanently lost when the session ends. A rule enforcing push-after-commit ensures all committed changes are immediately visible to collaborators and are not silently stranded in a transient agent session.

## What Changes

- **`AGENTS.md`**: Add a new Hard Rule (item 10) to Section 2 stating that every `git commit` must be immediately followed by `git push` to the remote tracking branch.

## Capabilities

### New Capabilities

- `agent-git-workflow`: Governs the required git push behaviour after every commit in this project.

### Modified Capabilities

None. No existing spec-level requirements change.

## Impact

- `AGENTS.md` — Section 2 gains one new rule (item 10).
- No source code, tests, or `pyproject.toml` changes.
