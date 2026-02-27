## 1. init_command module

- [x] 1.1 Create `src/az_acme_tool/init_command.py` with `InitError` exception class, `_ACME_DIRECTORY_URL` constant, `_DEFAULT_KEY_PATH` constant, and `_CONFIG_TEMPLATE` string
- [x] 1.2 Implement `run_init(config_path: str, config_template: bool) -> None` — template branch: print `_CONFIG_TEMPLATE` to stdout and return
- [x] 1.3 Implement registration branch in `run_init`: generate RSA-2048 key, write to `_DEFAULT_KEY_PATH` with `0o600`, call `AcmeClient.register_account()`, print key path + account URL
- [x] 1.4 Add overwrite guard: if key file already exists, call `click.confirm()` before overwriting; skip ACME registration if user declines

## 2. CLI wiring

- [x] 2.1 Update `src/az_acme_tool/cli.py` `init` command to call `run_init(obj["config"], config_template)` instead of raising `NotImplementedError`

## 3. Tests

- [x] 3.1 Create `tests/test_init_command.py` with `CliRunner` fixture and mock for `AcmeClient.register_account`
- [x] 3.2 Test `--config-template`: assert stdout contains required YAML keys, assert no file created, assert exit code 0
- [x] 3.3 Test default path (new key): assert key file created with `0o600`, assert `register_account` called once, assert account URL in output
- [x] 3.4 Test overwrite guard — `n` response: assert existing key unchanged and `register_account` not called
- [x] 3.5 Test overwrite guard — `y` response: assert key overwritten and `register_account` called
- [x] 3.6 Test `AcmeError` propagation: assert non-zero exit code and error message in output

## 4. Quality gates

- [x] 4.1 Run `ruff check src/az_acme_tool/init_command.py src/az_acme_tool/cli.py tests/test_init_command.py` — zero violations
- [x] 4.2 Run `mypy --strict src/az_acme_tool/init_command.py src/az_acme_tool/cli.py` — zero errors
- [x] 4.3 Run `black --check --line-length 100 src/az_acme_tool/init_command.py src/az_acme_tool/cli.py tests/test_init_command.py` — no reformatting needed
- [x] 4.4 Run `pytest tests/test_init_command.py --cov=az_acme_tool.init_command --cov-report=term-missing` — coverage ≥80%
