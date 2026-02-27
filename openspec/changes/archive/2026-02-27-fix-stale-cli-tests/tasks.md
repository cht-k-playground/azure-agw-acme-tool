## 1. Fix Stale Tests

- [x] 1.1 In `tests/test_cli.py`, replace `test_init_subcommand_raises_not_implemented` with a smoke test that invokes `init` with a missing config path and asserts non-zero exit code and an error message in the output
- [x] 1.2 In `tests/test_cli.py`, replace `test_issue_subcommand_raises_not_implemented` with a smoke test that invokes `issue` with a missing config path and asserts non-zero exit code and an error message in the output
- [x] 1.3 In `tests/test_cli.py`, replace `test_status_subcommand_raises_not_implemented` with a smoke test that invokes `status` with a missing config path and asserts non-zero exit code and an error message in the output

## 2. Verify

- [x] 2.1 Run `pytest tests/test_cli.py -v` and confirm all tests pass (0 failures)
- [x] 2.2 Run `pytest --tb=short -q` and confirm the full suite passes
- [x] 2.3 Run `ruff check tests/test_cli.py` and fix any warnings
- [x] 2.4 Run `mypy --strict tests/test_cli.py` and fix any type errors
