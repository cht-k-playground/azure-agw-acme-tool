## Context

Three tests in `tests/test_cli.py` were written when `init`, `issue`, and `status` were stubs that raised `NotImplementedError`. Those commands are now fully implemented (archived changes: `cli-init`, `cli-issue`, `cli-status`). The tests now fail because the commands no longer raise that error.

## Goals / Non-Goals

**Goals:**
- Make the test suite green by replacing the three stale `NotImplementedError` assertions with correct smoke tests.
- Ensure the new tests are meaningful: they verify the commands handle a missing config file gracefully (non-zero exit code, error message).

**Non-Goals:**
- Comprehensive integration testing of `init`, `issue`, or `status` — those are covered by their own dedicated test files.
- Any production source changes.

## Decisions

**Decision: Replace with missing-config smoke tests**
Each stale test is replaced with a test that invokes the command with a non-existent config path and asserts:
1. Exit code is non-zero (command failed gracefully).
2. The output contains an error message (not a Python traceback).

This is the minimal meaningful replacement: it confirms the command is wired up and handles errors without crashing.

**Type checking / linting constraints:**
- `mypy --strict` and `ruff` must pass after the change.
- `black --line-length 100` formatting required.

## Risks / Trade-offs

- [Risk] New smoke tests may be too permissive (any non-zero exit passes). → Mitigation: also assert that the error output contains a recognisable error string (e.g., "Error:" or "not found").
