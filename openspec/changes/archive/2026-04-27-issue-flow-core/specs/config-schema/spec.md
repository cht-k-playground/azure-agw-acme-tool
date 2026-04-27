## ADDED Requirements

### Requirement: AcmeConfig directory_url field
The system SHALL add a required `directory_url: str` field to `AcmeConfig` in `src/az_acme_tool/config.py` that specifies the ACME CA directory URL (e.g., Let's Encrypt production or staging).

#### Scenario: parse_config succeeds with directory_url present
- **WHEN** the config YAML includes `acme.directory_url` as a non-empty string
- **THEN** `parse_config()` returns an `AppConfig` with `acme.directory_url` set to that value

#### Scenario: parse_config raises ConfigError when directory_url is missing
- **WHEN** the config YAML does not include `acme.directory_url`
- **THEN** `parse_config()` raises `ConfigError` with a message identifying the missing field

### Requirement: AcmeConfig account_key_path field
The system SHALL add a required `account_key_path: Path` field to `AcmeConfig` in `src/az_acme_tool/config.py` that specifies the filesystem path to the PEM-encoded ACME account private key.

#### Scenario: parse_config succeeds with account_key_path present
- **WHEN** the config YAML includes `acme.account_key_path` as a string path
- **THEN** `parse_config()` returns an `AppConfig` with `acme.account_key_path` as a `Path` object

#### Scenario: parse_config raises ConfigError when account_key_path is missing
- **WHEN** the config YAML does not include `acme.account_key_path`
- **THEN** `parse_config()` raises `ConfigError` with a message identifying the missing field

### Requirement: GatewayConfig acme_function_name field
The system SHALL add a required `acme_function_name: str` field to `GatewayConfig` in `src/az_acme_tool/config.py` that specifies the Azure Function App name used for HTTP-01 challenge responses.

#### Scenario: parse_config succeeds with acme_function_name present
- **WHEN** the config YAML includes `gateways[*].acme_function_name` as a non-empty string
- **THEN** `parse_config()` returns an `AppConfig` with `gateways[*].acme_function_name` set to that value

#### Scenario: parse_config raises ConfigError when acme_function_name is missing
- **WHEN** the config YAML does not include `acme_function_name` for a gateway
- **THEN** `parse_config()` raises `ConfigError` with a message identifying the missing field
