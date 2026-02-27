## ADDED Requirements

### Requirement: AppConfig model hierarchy
The system SHALL provide a typed Pydantic v2 model hierarchy consisting of `AppConfig`, `AcmeConfig`, `AzureConfig`, `GatewayConfig`, and `DomainConfig` that represents the full structure of the YAML configuration file.

#### Scenario: Valid complete config is accepted
- **WHEN** a YAML file contains all required fields with valid values
- **THEN** `parse_config()` returns a fully-typed `AppConfig` instance with no errors

### Requirement: ACME configuration model
The system SHALL define an `AcmeConfig` Pydantic v2 model with a required `email` field that validates RFC 5322 email address format.

#### Scenario: Valid email is accepted
- **WHEN** `acme_email` is a properly-formatted email address (e.g., `user@example.com`)
- **THEN** `AcmeConfig` instantiates without error

#### Scenario: Invalid email raises ConfigError
- **WHEN** `acme_email` contains a string that is not a valid email address
- **THEN** `parse_config()` raises `ConfigError` with a message identifying the invalid field

### Requirement: Azure configuration model
The system SHALL define an `AzureConfig` Pydantic v2 model with required fields: `subscription_id` (UUID format), `resource_group` (non-empty string), and `auth_method` (restricted to valid enum values).

#### Scenario: Valid UUID subscription_id is accepted
- **WHEN** `subscription_id` is a valid UUID string (e.g., `123e4567-e89b-12d3-a456-426614174000`)
- **THEN** `AzureConfig` instantiates without error

#### Scenario: Non-UUID subscription_id raises ConfigError
- **WHEN** `subscription_id` is a string that does not conform to UUID format
- **THEN** `parse_config()` raises `ConfigError` with a message identifying the offending field

#### Scenario: Valid auth_method values are accepted
- **WHEN** `auth_method` is one of `default`, `service_principal`, or `managed_identity`
- **THEN** `AzureConfig` instantiates without error

#### Scenario: Invalid auth_method raises ConfigError
- **WHEN** `auth_method` is set to an unsupported string value
- **THEN** `parse_config()` raises `ConfigError` with a message identifying the invalid value

#### Scenario: Missing required Azure fields raise ConfigError
- **WHEN** `subscription_id` or `resource_group` is absent from the YAML
- **THEN** `parse_config()` raises `ConfigError` naming the missing field

### Requirement: auth_method enum
The system SHALL define an `AuthMethod` enum with exactly three members: `default`, `service_principal`, and `managed_identity`.

#### Scenario: All valid auth_method strings map to enum members
- **WHEN** `auth_method` is `"default"`, `"service_principal"`, or `"managed_identity"`
- **THEN** the field deserializes to the corresponding `AuthMethod` enum member

### Requirement: GatewayConfig model
The system SHALL define a `GatewayConfig` Pydantic v2 model with a required `name` field (non-empty string) and a required `domains` list of `DomainConfig` objects (non-empty list).

#### Scenario: Valid gateway config is accepted
- **WHEN** a gateway entry has a non-empty `name` and at least one domain entry
- **THEN** `GatewayConfig` instantiates without error

### Requirement: DomainConfig model
The system SHALL define a `DomainConfig` Pydantic v2 model with required fields: `domain` (FQDN format), and `cert_store` (restricted to `CertStore` enum values).

#### Scenario: Valid FQDN domain is accepted
- **WHEN** `domain` is a valid fully-qualified domain name (e.g., `example.com`, `sub.example.com`)
- **THEN** `DomainConfig` instantiates without error

#### Scenario: Invalid domain format raises ConfigError
- **WHEN** `domain` does not conform to FQDN format (e.g., contains spaces or invalid characters)
- **THEN** `parse_config()` raises `ConfigError` identifying the invalid domain

#### Scenario: Valid cert_store value is accepted
- **WHEN** `cert_store` is `"agw_direct"`
- **THEN** `DomainConfig` instantiates without error

#### Scenario: Invalid cert_store value raises ConfigError
- **WHEN** `cert_store` is set to any value other than `"agw_direct"`
- **THEN** `parse_config()` raises `ConfigError` identifying the invalid value

### Requirement: CertStore enum
The system SHALL define a `CertStore` enum with a single member: `agw_direct`. Key Vault support is deferred to Phase 2.

#### Scenario: Only agw_direct is a valid cert_store
- **WHEN** `cert_store` is `"agw_direct"`
- **THEN** it deserializes to `CertStore.agw_direct` without error

### Requirement: parse_config public function
The system SHALL expose a `parse_config(path: Path) -> AppConfig` public function in `src/az_acme_tool/config.py` that reads a YAML file at the given path, validates it against the model hierarchy, and returns an `AppConfig` instance.

#### Scenario: Successful parse returns AppConfig
- **WHEN** the YAML file at `path` is valid and contains all required fields
- **THEN** `parse_config()` returns an `AppConfig` object with all fields populated

#### Scenario: File not found raises ConfigError
- **WHEN** the file at `path` does not exist
- **THEN** `parse_config()` raises `ConfigError` with a message indicating the missing file

#### Scenario: Malformed YAML raises ConfigError
- **WHEN** the file at `path` contains invalid YAML syntax
- **THEN** `parse_config()` raises `ConfigError` with a message describing the parse failure

#### Scenario: Missing required top-level fields raise ConfigError
- **WHEN** `acme_email`, `subscription_id`, or `resource_group` is absent
- **THEN** `parse_config()` raises `ConfigError` naming the missing field

### Requirement: ConfigError exception class
The system SHALL define a `ConfigError` exception class in `src/az_acme_tool/config.py` that is raised for all configuration validation and loading failures, with a human-readable message identifying the problematic field or value.

#### Scenario: ConfigError carries descriptive message
- **WHEN** `parse_config()` raises `ConfigError`
- **THEN** the exception message explicitly names the field or value that caused the error

### Requirement: Default config path
The system SHALL use `~/.config/az-acme-tool/config.yaml` as the default configuration file path when no explicit path is provided by the caller.

#### Scenario: Default path is used when none specified
- **WHEN** `parse_config()` is called without an explicit path (or with the default)
- **THEN** the function attempts to read from `~/.config/az-acme-tool/config.yaml`
