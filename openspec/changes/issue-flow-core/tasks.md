## 1. Extend config schema

- [ ] 1.1 Add `directory_url: str` and `account_key_path: Path` required fields to `AcmeConfig` in `src/az_acme_tool/config.py`
- [ ] 1.2 Add `acme_function_name: str` required field to `GatewayConfig` in `src/az_acme_tool/config.py`
- [ ] 1.3 Update `tests/test_config.py` to cover the new required fields — add tests for: valid config with all new fields, `ConfigError` when `directory_url` is missing, `ConfigError` when `account_key_path` is missing, `ConfigError` when `acme_function_name` is missing

## 2. Extend AzureGatewayClient

- [ ] 2.1 Add `upload_ssl_certificate(self, cert_name: str, pfx_data: bytes, password: str) -> None` to `AzureGatewayClient` in `src/az_acme_tool/azure_gateway.py` — base64-encodes pfx_data, adds/replaces the named SSL certificate on the gateway, calls `begin_create_or_update`; password must never be logged; raises `AzureGatewayError` on `HttpResponseError`
- [ ] 2.2 Add `add_routing_rule(self, rule_name: str, domain: str, backend_fqdn: str) -> None` to `AzureGatewayClient` — creates a URL path map with a path rule for `/.well-known/acme-challenge/*` pointing to a new backend pool targeting `backend_fqdn` (HTTPS port 443, `pickHostNameFromBackendAddress: true`); calls `begin_create_or_update`; raises `AzureGatewayError` on `HttpResponseError`
- [ ] 2.3 Add `get_listeners_by_cert_name(self, cert_name: str) -> list[str]` to `AzureGatewayClient` — scans all HTTP listeners for those whose `ssl_certificate` ARM ID ends with `/{cert_name}`; returns list of listener names (empty list if none found); raises `AzureGatewayError` on `HttpResponseError`
- [ ] 2.4 Add unit tests for `upload_ssl_certificate` in `tests/test_azure_gateway.py` — covering: successful upload, password not logged, `AzureGatewayError` on API failure
- [ ] 2.5 Add unit tests for `add_routing_rule` in `tests/test_azure_gateway.py` — covering: successful creation with correct path pattern, `AzureGatewayError` on API failure
- [ ] 2.6 Add unit tests for `get_listeners_by_cert_name` in `tests/test_azure_gateway.py` — covering: listeners found, empty result, `AzureGatewayError` on API failure

## 3. Implement _issue_single_domain

- [ ] 3.1 Replace the `NotImplementedError` stub in `_issue_single_domain()` in `src/az_acme_tool/issue_command.py` with the full 14-step ACME pipeline: (1) load config fields, (2) `AcmeClient.register_account()`, (3) `new_order([domain])`, (4) `get_http01_challenge(order, domain)`, (5) `update_function_app_settings(acme_function_name, {"ACME_CHALLENGE_RESPONSE": key_auth})`, (6) `add_routing_rule(rule_name, domain, backend_fqdn)` in try block, (7) `answer_challenge(challb)`, (8) `poll_until_valid(order)`, (9) `finalize_order(order, csr_pem)`, (10) `download_certificate(order)`, (11) `pem_to_pfx(cert_pem, key_pem, password)`, (12) `upload_ssl_certificate(cert_name, pfx_data, password)`, (13) `get_listeners_by_cert_name(old_cert_name)` + `update_listener_certificate()` for each, (14) `delete_routing_rule(rule_name)` in finally block
- [ ] 3.2 Generate a random PFX password using `secrets.token_urlsafe(32)` — never log or write to disk
- [ ] 3.3 Generate a domain-specific RSA private key for the certificate using `cryptography` and build the CSR using `cert_converter.generate_csr([domain], key_pem)`
- [ ] 3.4 Add unit tests for `_issue_single_domain` in `tests/test_issue_command.py` — covering: all 14 steps called in order with correct arguments, `delete_routing_rule` called in finally even when step 7 raises, PFX password not in log output

## 4. Quality checks

- [ ] 4.1 Run `ruff check src/ tests/` and fix any linting issues
- [ ] 4.2 Run `mypy --strict src/` and fix any type errors
- [ ] 4.3 Run `python -m pytest tests/ --cov=src/az_acme_tool --cov-report=term-missing` and confirm ≥80% line coverage
