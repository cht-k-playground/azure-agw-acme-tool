## 1. Core Module

- [x] 1.1 Create `src/az_acme_tool/renew_command.py` with `RenewError` exception class, `_domain_to_cert_name()` helper, and `run_renew()` public function
- [x] 1.2 Implement expiry lookup logic in `run_renew()`: instantiate `AzureGatewayClient` per gateway, call `list_certificates()`, derive cert name via `_domain_to_cert_name()`, and compare remaining days against threshold
- [x] 1.3 Implement skip logic: if remaining days > threshold (and not `--force`), print skip message and increment `skipped` counter
- [x] 1.4 Implement missing-certificate graceful skip: if cert not found in `list_certificates()` result, print warning to stderr and skip domain
- [x] 1.5 Implement renewal delegation: call `_issue_single_domain()` from `issue_command` for qualifying domains; catch exceptions and record failures
- [x] 1.6 Implement summary output: print `Total: N | Renewed: R | Skipped: S | Failed: F` after processing all domains

## 2. CLI Wiring

- [x] 2.1 Update `cli.py` `renew` command stub: add `--gateway` and `--domain` options, replace `raise NotImplementedError` with `run_renew()` call, and handle `RenewError` with `sys.exit(1)`

## 3. Tests

- [x] 3.1 Create `tests/test_renew_command.py` with fixtures for mock `AzureGatewayClient` and mock `_issue_single_domain`
- [x] 3.2 Test: domain skipped when certificate has more than threshold days remaining (default 30)
- [x] 3.3 Test: domain renewed when certificate is within threshold
- [x] 3.4 Test: `--force` flag triggers renewal regardless of remaining days
- [x] 3.5 Test: `--days 60` custom threshold applied correctly
- [x] 3.6 Test: missing certificate results in skip with warning (no `AzureGatewayError` propagation)
- [x] 3.7 Test: `--gateway` filter limits scope to matching gateway
- [x] 3.8 Test: `--domain` filter limits scope to matching domain
- [x] 3.9 Test: unknown `--domain` causes `RenewError` with non-zero exit
- [x] 3.10 Test: summary line printed with correct counts after mixed skip/renew/fail scenario

## 4. Quality Gates

- [x] 4.1 Run `ruff check src/az_acme_tool/renew_command.py tests/test_renew_command.py` — zero errors
- [x] 4.2 Run `mypy --strict src/az_acme_tool/renew_command.py` — zero errors
- [x] 4.3 Run `black --line-length 100 --check src/ tests/` — zero formatting issues
- [x] 4.4 Run `pytest --cov=az_acme_tool --cov-report=term-missing` — overall coverage ≥80%
