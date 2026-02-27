## Why

The `issue` command stub in `cli.py` currently raises `NotImplementedError`. This is the central orchestration command that ties together config parsing, gateway filtering, and the ACME certificate issuance pipeline. Phase 1-C requires this command before the end-to-end flow (`issue-flow-core`) can be built. This change implements the filtering, dry-run, and orchestration skeleton so downstream changes can implement the actual 14-step ACME flow.

## What Changes

- New module `src/az_acme_tool/issue_command.py` with `run_issue()` orchestration function and `IssueError` exception
- `run_issue()` handles: config loading, gateway/domain filtering, dry-run mode (log planned steps, no Azure/ACME calls), and per-domain result collection
- The actual 14-step ACME pipeline is stubbed as a call to `_issue_single_domain()` which raises `NotImplementedError` — this will be replaced by `issue-flow-core`
- Update `cli.py` `issue` command to delegate to `run_issue()` instead of raising `NotImplementedError`
- New test file `tests/test_issue_command.py` covering all acceptance criteria (filtering logic, dry-run, unknown domain error)

## Capabilities

### New Capabilities

- `cli-issue`: The `issue` CLI command — config-driven gateway/domain filtering, dry-run mode, and orchestration entry point

### Modified Capabilities

_(none)_

## Impact

- **Modified**: `src/az_acme_tool/cli.py` — replace `issue` stub
- **New file**: `src/az_acme_tool/issue_command.py`
- **New file**: `tests/test_issue_command.py`
- **No new runtime dependencies**
