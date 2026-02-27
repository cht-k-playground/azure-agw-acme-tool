## Context

The tool currently has no configuration layer. Every downstream feature (ACME certificate issuance, Azure Application Gateway integration, renewal scheduling) needs a shared, validated configuration object at startup. Without a typed schema, every module would need to re-validate the same raw YAML data independently, leading to inconsistent error handling and maintenance overhead.

This change introduces the single source of truth for runtime configuration: a Pydantic v2 model hierarchy loaded and validated once via `parse_config()`.

## Goals / Non-Goals

**Goals:**
- Define all configuration models (`AppConfig`, `AcmeConfig`, `AzureConfig`, `GatewayConfig`, `DomainConfig`) using Pydantic v2
- Implement field-level validation for email format, UUID format, FQDN format, and enum membership
- Expose a single public entrypoint: `parse_config(path: Path) -> AppConfig`
- Define `ConfigError` as the unified exception for all config failures
- Set the default config path to `~/.config/az-acme-tool/config.yaml`
- Achieve ≥80% line coverage in `tests/test_config.py`
- Pass `mypy --strict`, `ruff`, and `black --line-length 100`

**Non-Goals:**
- Key Vault cert store support (deferred to Phase 2)
- CLI flag parsing or config file path resolution (handled by the CLI layer)
- Config file creation or migration tooling
- Hot-reload or watch-mode configuration
- Azure SDK calls (this module is pure data validation only)

## Decisions

### Decision 1: Pydantic v2 over dataclasses or attrs

**Choice**: Pydantic v2  
**Rationale**: Pydantic v2 provides built-in YAML/dict deserialization, field-level validators with rich error messages, strict type coercion, and model inheritance — all without boilerplate. The project already mandates `pydantic>=2.0`. The `ValidationError` → `ConfigError` translation is a one-liner wrapper.  
**Alternatives considered**:
- `dataclasses` + manual validation: high boilerplate, no schema enforcement
- `attrs + cattrs`: similar to Pydantic but less ergonomic for custom validators and not already mandated

### Decision 2: Single `config.py` module

**Choice**: All models, enums, the `parse_config()` function, and `ConfigError` live in `src/az_acme_tool/config.py`  
**Rationale**: The configuration schema is small and cohesive. Splitting into sub-modules (`models.py`, `validators.py`, `loader.py`) adds indirection without benefit at this stage. Co-location makes the public API surface obvious.  
**Alternatives considered**:
- `config/` package: premature for the current scope; can be refactored in Phase 2 if Key Vault adds complexity

### Decision 3: `pyyaml` for YAML parsing

**Choice**: `pyyaml>=6.0` with `yaml.safe_load()`  
**Rationale**: `pyyaml` is the de-facto standard, already widely available in the Python ecosystem. `safe_load()` avoids arbitrary object deserialization (security constraint). The parsed dict is passed directly to Pydantic for validation.  
**Alternatives considered**:
- `ruamel.yaml`: supports YAML 1.2 and round-trip editing, but adds complexity not needed here
- `tomllib`: TOML only, not applicable

### Decision 4: UUID validation via `pydantic.UUID4` type or regex

**Choice**: Use `pydantic.UUID4` field type (or `uuid.UUID` with Pydantic coercion) rather than a regex  
**Rationale**: Pydantic's built-in UUID type validates RFC 4122 format precisely and produces clear error messages. A regex would need to be maintained and tested independently.

### Decision 5: FQDN validation via regex field validator

**Choice**: Custom `@field_validator` using a conservative FQDN regex  
**Rationale**: Pydantic v2 does not have a built-in FQDN type. A regex validator on `domain` fields is the idiomatic approach. The regex will accept labels of 1–63 alphanumeric/hyphen characters separated by dots, with a TLD of at least 2 characters.  
**Pattern**: `^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$`

### Decision 6: `ConfigError` wraps Pydantic `ValidationError`

**Choice**: Catch `pydantic.ValidationError` and `yaml.YAMLError` inside `parse_config()`, re-raise as `ConfigError` with a human-readable message  
**Rationale**: Callers should not need to import `pydantic` or `yaml` to handle config errors. A single `ConfigError` exception type keeps the public API clean. The message will include the failing field name(s) extracted from `ValidationError.errors()`.

### Decision 7: Email validation via `pydantic.EmailStr`

**Choice**: Use `pydantic[email]` which provides `EmailStr` type  
**Rationale**: `EmailStr` uses the `email-validator` library for RFC-compliant validation. This avoids maintaining a custom email regex and provides better error messages.  
**Dependency addition**: `pydantic[email]` (pulls in `email-validator>=2.0`)

## Risks / Trade-offs

- **[Risk] `email-validator` adds a transitive dependency** → Mitigation: it is a lightweight, well-maintained library with no native code; the risk is low. Alternative: use a simple regex if adding the dependency is undesirable, but accuracy degrades.
- **[Risk] UUID4 vs UUID (any version)** → Mitigation: Use `uuid.UUID` (not `UUID4`) so that UUID versions 1–5 are all accepted — Azure subscription IDs are typically UUID4 but the spec only requires UUID format compliance.
- **[Risk] FQDN regex may reject edge-case valid domains** → Mitigation: The regex is conservative and covers all standard domain names. Wildcard domains (e.g., `*.example.com`) are out of scope for Phase 1.
- **[Risk] `yaml.safe_load` returns `None` for empty files** → Mitigation: `parse_config()` will check for `None` result and raise `ConfigError("Configuration file is empty")`.

## Migration Plan

This is a net-new module with no existing code to migrate. Deployment steps:
1. Add `pydantic[email]>=2.0` and `pyyaml>=6.0` to `[project.dependencies]` in `pyproject.toml`
2. Implement `src/az_acme_tool/config.py`
3. Implement `tests/test_config.py`
4. Run `uv sync` to install new dependencies
5. Verify `mypy --strict src/`, `ruff check src/`, `black --check --line-length 100 src/`
6. Run `pytest --cov=az_acme_tool tests/test_config.py` and confirm ≥80% coverage

Rollback: remove `config.py` and `tests/test_config.py`; revert `pyproject.toml` dependency additions.

## Open Questions

- None. All design decisions are resolved for Phase 1 scope.
