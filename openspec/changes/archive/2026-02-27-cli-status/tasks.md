## 1. status_command module

- [x] 1.1 Create `src/az_acme_tool/status_command.py` with `StatusError` exception, `CertStatusEntry` dataclass, and `_classify_status(days_remaining)` helper
- [x] 1.2 Implement `_collect_status(config)` — iterates gateways, creates `AzureGatewayClient`, calls `list_certificates()`, builds list of `CertStatusEntry`
- [x] 1.3 Implement `_render_table(entries)` — prints Rich table with columns: Gateway | Certificate | Expiry Date | Days Remaining | Status
- [x] 1.4 Implement `_render_json(entries)` — prints JSON array to stdout
- [x] 1.5 Implement `_render_yaml(entries)` — prints YAML to stdout
- [x] 1.6 Implement `run_status(config_path, output_format)` entry point

## 2. CLI wiring

- [x] 2.1 Update `src/az_acme_tool/cli.py` `status` command to call `run_status()` instead of raising `NotImplementedError`

## 3. Tests

- [x] 3.1 Create `tests/test_status_command.py` with mock `AzureGatewayClient` returning sample certificate data
- [x] 3.2 Test `_classify_status()`: 31 days → valid, 29 days → expiring_soon, -1 days → expired, 0 days → expired
- [x] 3.3 Test `--output json`: assert output is valid JSON with required fields
- [x] 3.4 Test `--output yaml`: assert output is valid YAML
- [x] 3.5 Test `--output table` (default): assert column headers present in output

## 4. Quality gates

- [x] 4.1 Run `ruff check src/az_acme_tool/status_command.py src/az_acme_tool/cli.py tests/test_status_command.py` — zero violations
- [x] 4.2 Run `mypy --strict src/az_acme_tool/status_command.py src/az_acme_tool/cli.py` — zero errors
- [x] 4.3 Run `black --check --line-length 100 src/az_acme_tool/status_command.py src/az_acme_tool/cli.py tests/test_status_command.py` — no reformatting needed
- [x] 4.4 Run `pytest tests/test_status_command.py --cov=az_acme_tool.status_command --cov-report=term-missing` — coverage ≥80%
