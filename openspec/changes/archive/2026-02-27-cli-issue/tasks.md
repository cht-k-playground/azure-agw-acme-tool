## 1. issue_command module

- [x] 1.1 Create `src/az_acme_tool/issue_command.py` with `IssueError` exception, `DomainTarget` dataclass (gateway_name, domain), and `_issue_single_domain()` stub raising `NotImplementedError`
- [x] 1.2 Implement `_resolve_targets(config, gateway_filter, domain_filter)` — returns list of `DomainTarget`; raises `IssueError` if `domain_filter` is set but no match found
- [x] 1.3 Implement `run_issue(config_path, gateway, domain, dry_run)` — loads config, resolves targets, iterates domains: dry-run prints plan, non-dry-run calls `_issue_single_domain()`, collects results, prints summary

## 2. CLI wiring

- [x] 2.1 Update `src/az_acme_tool/cli.py` `issue` command to call `run_issue()` instead of raising `NotImplementedError`

## 3. Tests

- [x] 3.1 Create `tests/test_issue_command.py` with fixtures: minimal `AppConfig` with two gateways/domains, `CliRunner`
- [x] 3.2 Test `--gateway` filter: assert only matching-gateway domains in work list
- [x] 3.3 Test `--domain` filter: assert only specified domain processed
- [x] 3.4 Test unknown `--domain`: assert non-zero exit code and error message
- [x] 3.5 Test `--dry-run`: assert planned output printed, `_issue_single_domain` not called
- [x] 3.6 Test summary output: assert summary line present after processing

## 4. Quality gates

- [x] 4.1 Run `ruff check src/az_acme_tool/issue_command.py src/az_acme_tool/cli.py tests/test_issue_command.py` — zero violations
- [x] 4.2 Run `mypy --strict src/az_acme_tool/issue_command.py src/az_acme_tool/cli.py` — zero errors
- [x] 4.3 Run `black --check --line-length 100 src/az_acme_tool/issue_command.py src/az_acme_tool/cli.py tests/test_issue_command.py` — no reformatting needed
- [x] 4.4 Run `pytest tests/test_issue_command.py --cov=az_acme_tool.issue_command --cov-report=term-missing` — coverage ≥80%
