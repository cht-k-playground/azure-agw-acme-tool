## 1. Extend AzureGatewayClient

- [x] 1.1 Add `list_acme_challenge_rules(self) -> list[str]` method to `AzureGatewayClient` in `src/az_acme_tool/azure_gateway.py` — scans all `url_path_maps` for path rules prefixed with `acme-challenge-` and returns their names
- [x] 1.2 Add `delete_routing_rule(self, rule_name: str) -> None` method to `AzureGatewayClient` — removes the named path rule from all URL path maps and calls `begin_create_or_update` to persist the change; raises `AzureGatewayError` if rule not found or API call fails
- [x] 1.3 Add unit tests for `list_acme_challenge_rules` in `tests/test_azure_gateway.py` — covering: rules found, empty result, and `AzureGatewayError` on API failure
- [x] 1.4 Add unit tests for `delete_routing_rule` in `tests/test_azure_gateway.py` — covering: successful deletion, rule not found error, and `AzureGatewayError` on API failure

## 2. Implement cleanup_command module

- [x] 2.1 Create `src/az_acme_tool/cleanup_command.py` with `CleanupError` exception class and `run_cleanup(config_path: str, cleanup_all: bool) -> None` function
- [x] 2.2 Implement `run_cleanup` logic: load config, instantiate `AzureGatewayClient`, call `list_acme_challenge_rules()`, handle empty case (print "No orphaned ACME challenge rules found." and return), then either prompt per-rule (interactive) or delete all (batch)
- [x] 2.3 Create `tests/test_cleanup_command.py` with unit tests covering: no rules found, `--all` removes all rules without prompting, interactive mode with `y` confirms deletion, interactive mode with `n` skips deletion, and `CleanupError` on Azure failure

## 3. Wire CLI stub

- [x] 3.1 Update the `cleanup` command in `src/az_acme_tool/cli.py` to import and call `run_cleanup` from `cleanup_command`, replacing the `raise NotImplementedError` stub; handle `CleanupError` with `click.echo` + `sys.exit(1)`
- [x] 3.2 Add CLI integration tests in `tests/test_cli.py` for the `cleanup` command — covering: `--all` flag, no-rules message, and error handling

## 4. Quality checks

- [x] 4.1 Run `ruff check src/ tests/` and fix any linting issues
- [x] 4.2 Run `mypy --strict src/` and fix any type errors
- [x] 4.3 Run `python -m pytest tests/ --cov=src/az_acme_tool --cov-report=term-missing` and confirm ≥80% line coverage
