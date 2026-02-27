## 1. Project Setup

- [ ] 1.1 Add `pydantic[email]>=2.0` and `pyyaml>=6.0` to `[project.dependencies]` in `pyproject.toml` and run `uv sync` to install them

## 2. Core Enums and Exception

- [ ] 2.1 Create `src/az_acme_tool/config.py` and define `ConfigError` exception class with a descriptive message attribute
- [ ] 2.2 Define `AuthMethod` enum with members `default`, `service_principal`, and `managed_identity`
- [ ] 2.3 Define `CertStore` enum with member `agw_direct`

## 3. Pydantic Models

- [ ] 3.1 Implement `AcmeConfig` Pydantic v2 model with `email: EmailStr` required field
- [ ] 3.2 Implement `AzureConfig` Pydantic v2 model with `subscription_id: uuid.UUID`, `resource_group: str`, and `auth_method: AuthMethod` fields, including field validators
- [ ] 3.3 Implement `DomainConfig` Pydantic v2 model with `domain: str` (FQDN regex validator) and `cert_store: CertStore` fields
- [ ] 3.4 Implement `GatewayConfig` Pydantic v2 model with `name: str` and `domains: list[DomainConfig]` fields (non-empty list validation)
- [ ] 3.5 Implement `AppConfig` Pydantic v2 model composing `AcmeConfig`, `AzureConfig`, and `gateways: list[GatewayConfig]`

## 4. parse_config Function

- [ ] 4.1 Implement `parse_config(path: Path) -> AppConfig` that reads and `yaml.safe_load()`s the file, raises `ConfigError` on `FileNotFoundError` and `yaml.YAMLError`
- [ ] 4.2 Wrap `pydantic.ValidationError` in `parse_config()` to re-raise as `ConfigError` with a message that names the failing field(s) extracted from `ValidationError.errors()`
- [ ] 4.3 Handle `None` result from `yaml.safe_load()` (empty file) by raising `ConfigError("Configuration file is empty")`
- [ ] 4.4 Set the function signature default for `path` to `Path("~/.config/az-acme-tool/config.yaml").expanduser()`

## 5. Unit Tests

- [ ] 5.1 Create `tests/test_config.py` with a fixture that writes a valid minimal YAML config to a `tmp_path` file
- [ ] 5.2 Write test: `parse_config()` with a fully valid YAML returns a correct `AppConfig` instance with all fields populated
- [ ] 5.3 Write test: missing `acme_email` raises `ConfigError` naming `acme_email`
- [ ] 5.4 Write test: missing `subscription_id` raises `ConfigError` naming `subscription_id`
- [ ] 5.5 Write test: missing `resource_group` raises `ConfigError` naming `resource_group`
- [ ] 5.6 Write test: non-UUID `subscription_id` raises `ConfigError`
- [ ] 5.7 Write test: invalid email in `acme_email` raises `ConfigError`
- [ ] 5.8 Write test: invalid `auth_method` value raises `ConfigError`
- [ ] 5.9 Write test: invalid `cert_store` value raises `ConfigError`
- [ ] 5.10 Write test: invalid FQDN in `domain` raises `ConfigError`
- [ ] 5.11 Write test: file not found raises `ConfigError`
- [ ] 5.12 Write test: malformed YAML raises `ConfigError`
- [ ] 5.13 Write test: empty YAML file raises `ConfigError("Configuration file is empty")`
- [ ] 5.14 Write test: all three valid `auth_method` values (`default`, `service_principal`, `managed_identity`) are accepted
- [ ] 5.15 Write test: `cert_store: agw_direct` is accepted and maps to `CertStore.agw_direct`

## 6. Quality Gates

- [ ] 6.1 Run `mypy --strict src/az_acme_tool/config.py` and fix all type errors
- [ ] 6.2 Run `ruff check src/az_acme_tool/config.py tests/test_config.py` and fix all lint errors
- [ ] 6.3 Run `black --line-length 100 src/az_acme_tool/config.py tests/test_config.py` to format
- [ ] 6.4 Run `pytest --cov=az_acme_tool tests/test_config.py` and confirm ≥80% line coverage for `config.py`
