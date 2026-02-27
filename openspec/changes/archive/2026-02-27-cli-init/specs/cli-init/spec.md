## ADDED Requirements

### Requirement: Config template printing
The system SHALL, when `az-acme-tool init --config-template` is invoked, print a YAML configuration template to stdout containing placeholder values for all required fields (`acme.email`, `azure.subscription_id`, `azure.resource_group`, `azure.auth_method`, and at least one gateway entry). No Azure or ACME network calls SHALL be made and no files SHALL be written.

#### Scenario: Template printed to stdout
- **WHEN** `az-acme-tool init --config-template` is invoked
- **THEN** stdout SHALL contain the strings `acme_email`, `subscription_id`, `resource_group`, and `auth_method` as YAML keys, and the process SHALL exit with code 0

#### Scenario: No side effects in template mode
- **WHEN** `az-acme-tool init --config-template` is invoked
- **THEN** no files SHALL be created or modified and no network requests SHALL be made

### Requirement: ACME account key generation
The system SHALL generate an RSA-2048 private key and write it in PEM format to the account key path (`~/.config/az-acme-tool/account.key` by default) with file permissions `0o600`.

#### Scenario: Key file created with correct permissions
- **WHEN** `az-acme-tool init` is invoked and the key file does not exist
- **THEN** the key file SHALL exist after the command completes, contain a valid PEM-encoded RSA private key, and have file permissions `0o600`

#### Scenario: Key file content is valid RSA PEM
- **WHEN** the key file is written
- **THEN** its contents SHALL begin with `-----BEGIN RSA PRIVATE KEY-----` or `-----BEGIN PRIVATE KEY-----` (PKCS#8 format)

### Requirement: ACME account registration
The system SHALL register the generated key with the ACME CA and print the resulting account URL to the console.

#### Scenario: Account URL printed after registration
- **WHEN** `az-acme-tool init` completes successfully
- **THEN** the console output SHALL contain the ACME account URL and the path to the generated key file

#### Scenario: AcmeError causes non-zero exit
- **WHEN** `AcmeClient.register_account()` raises `AcmeError`
- **THEN** the command SHALL exit with a non-zero exit code and print an error message to stderr

### Requirement: Overwrite confirmation for existing key file
The system SHALL, when the account key file already exists, prompt the user for confirmation before overwriting it.

#### Scenario: Existing key not overwritten on 'n' response
- **WHEN** `az-acme-tool init` is invoked and the key file already exists, and the user answers `n` to the confirmation prompt
- **THEN** the existing key file SHALL NOT be modified and no ACME registration SHALL occur

#### Scenario: Existing key overwritten on 'y' response
- **WHEN** `az-acme-tool init` is invoked and the key file already exists, and the user answers `y` to the confirmation prompt
- **THEN** the key file SHALL be replaced and ACME registration SHALL proceed
