## Why

The tool has no structured configuration layer — all config values are either hardcoded or passed ad-hoc. A validated, typed configuration schema is the foundational prerequisite for every other feature (ACME issuance, Azure gateway integration, certificate renewal), because all downstream modules depend on having a single authoritative, validated `AppConfig` object at startup.

## What Changes

- Introduce Pydantic v2 model hierarchy: `AppConfig`, `AcmeConfig`, `AzureConfig`, `GatewayConfig`, `DomainConfig`
- Add `cert_store` enum (`agw_direct` only; Key Vault deferred to Phase 2)
- Add `auth_method` enum (`default | service_principal | managed_identity`)
- Implement `parse_config(path: Path) -> AppConfig` public function that loads and validates a YAML file
- Define custom `ConfigError` exception class for all configuration-related failures
- Set default config path to `~/.config/az-acme-tool/config.yaml`
- Add `pydantic>=2.0` and `pyyaml` to `[project.dependencies]` in `pyproject.toml`
- Write unit tests covering all validation rules with ≥80% line coverage

## Capabilities

### New Capabilities

- `config-schema`: Typed Pydantic v2 configuration models, validation rules (email, UUID, FQDN, domain formats), `parse_config()` public API, and `ConfigError` exception — forming the configuration layer consumed by all other modules

### Modified Capabilities

<!-- No existing specs require modification; this is the initial foundational layer -->

## Impact

- **New module**: `src/az_acme_tool/config.py`
- **New tests**: `tests/test_config.py`
- **`pyproject.toml`**: Add `pydantic>=2.0` and `pyyaml>=6.0` to `[project.dependencies]`
- No existing source code is broken; no breaking changes to consumers (none exist yet)
