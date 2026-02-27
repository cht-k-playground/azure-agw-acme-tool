## ADDED Requirements

### Requirement: Gateway filter
The system SHALL, when `--gateway <name>` is provided, process only domains belonging to the gateway whose `name` matches the provided value. Domains on other gateways SHALL be silently skipped.

#### Scenario: Only matching-gateway domains processed
- **WHEN** `az-acme-tool issue --gateway my-agw` is invoked and the config contains two gateways
- **THEN** only the domains under the gateway named `my-agw` SHALL be included in the work list

### Requirement: Domain filter
The system SHALL, when `--domain <fqdn>` is provided, process only the single domain matching that value across all (or filtered) gateways.

#### Scenario: Only matching domain processed
- **WHEN** `az-acme-tool issue --domain www.example.com` is invoked and the config contains multiple domains
- **THEN** only `www.example.com` SHALL be processed

#### Scenario: Unknown domain causes non-zero exit
- **WHEN** `az-acme-tool issue --domain nonexistent.example.com` is invoked and that domain does not exist in the config
- **THEN** the command SHALL exit with a non-zero exit code and the error message SHALL reference the unknown domain

### Requirement: Dry-run mode
The system SHALL, when `--dry-run` is provided, print the planned issuance steps for each domain without making any Azure SDK or ACME CA calls.

#### Scenario: Dry-run prints planned steps
- **WHEN** `az-acme-tool issue --dry-run` is invoked
- **THEN** stdout SHALL contain a line indicating the planned action for each configured domain and the process SHALL exit with code 0

#### Scenario: No SDK calls in dry-run mode
- **WHEN** `az-acme-tool issue --dry-run` is invoked
- **THEN** no Azure SDK methods and no ACME CA methods SHALL be called

### Requirement: Issue summary output
The system SHALL print a summary after processing all domains, indicating how many succeeded and how many failed.

#### Scenario: Summary printed after completion
- **WHEN** `az-acme-tool issue` completes processing one or more domains
- **THEN** stdout SHALL contain a summary line with the total number of domains processed
