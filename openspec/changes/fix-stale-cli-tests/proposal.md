## Why

Three tests in `tests/test_cli.py` assert that `init`, `issue`, and `status` subcommands raise `NotImplementedError`. These commands have since been implemented (archived changes: `cli-init`, `cli-issue`, `cli-status`), so the tests now fail because the commands no longer raise that error. The test suite must be green before any new work proceeds.

## What Changes

- Remove the three stale `NotImplementedError` assertions for `init`, `issue`, and `status` in `tests/test_cli.py`.
- Replace them with lightweight smoke tests that verify each command exits without an unexpected crash when invoked with minimal/mock inputs.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `cli-root-options`: The CLI test coverage for `init`, `issue`, and `status` subcommands is updated to reflect their implemented state (no requirement-level change, only test correctness).

## Impact

- `tests/test_cli.py` — three test functions updated.
- No production source changes.
- No new dependencies.
