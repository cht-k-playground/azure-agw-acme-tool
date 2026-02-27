## ADDED Requirements

### Requirement: Expiry threshold check
The system SHALL, for each domain target, derive the expected certificate name using the `{domain_sanitized}-cert` convention (dots replaced with hyphens) and query its expiry from the Application Gateway via `AzureGatewayClient.list_certificates()`. If the certificate's remaining validity exceeds the `--days` threshold (default 30), the domain SHALL be skipped and a skip message SHALL be printed to stdout.

#### Scenario: Domain skipped when certificate has more than threshold days remaining
- **WHEN** `az-acme-tool renew` is invoked with default `--days 30` and a domain's certificate has 35 days remaining
- **THEN** the domain SHALL be skipped and stdout SHALL contain a message indicating the skip reason (days remaining and threshold)

#### Scenario: Domain renewed when certificate is within threshold
- **WHEN** `az-acme-tool renew` is invoked with default `--days 30` and a domain's certificate has 25 days remaining
- **THEN** the renewal flow SHALL be triggered for that domain

### Requirement: Force flag bypasses threshold
The system SHALL, when `--force` is provided, trigger renewal for all domain targets regardless of their certificate's remaining validity.

#### Scenario: Force flag renews certificate with more than threshold days remaining
- **WHEN** `az-acme-tool renew --force` is invoked and a domain's certificate has 35 days remaining
- **THEN** the renewal flow SHALL be triggered for that domain

### Requirement: Custom days threshold
The system SHALL accept a `--days <n>` option (integer, default 30) that sets the renewal threshold in days.

#### Scenario: Custom threshold applied
- **WHEN** `az-acme-tool renew --days 60` is invoked and a domain's certificate has 55 days remaining
- **THEN** the renewal flow SHALL be triggered for that domain (55 < 60)

#### Scenario: Custom threshold skips certificate above threshold
- **WHEN** `az-acme-tool renew --days 60` is invoked and a domain's certificate has 65 days remaining
- **THEN** the domain SHALL be skipped

### Requirement: Gateway and domain filters
The system SHALL accept `--gateway <name>` and `--domain <fqdn>` options that filter which domains are processed, using the same semantics as the `issue` command.

#### Scenario: Gateway filter limits scope
- **WHEN** `az-acme-tool renew --gateway my-agw` is invoked
- **THEN** only domains belonging to the gateway named `my-agw` SHALL be considered for renewal

#### Scenario: Domain filter limits scope
- **WHEN** `az-acme-tool renew --domain www.example.com` is invoked
- **THEN** only `www.example.com` SHALL be considered for renewal

#### Scenario: Unknown domain causes non-zero exit
- **WHEN** `az-acme-tool renew --domain nonexistent.example.com` is invoked and that domain does not exist in the config
- **THEN** the command SHALL exit with a non-zero exit code and the error message SHALL reference the unknown domain

### Requirement: Missing certificate graceful skip
The system SHALL, when a domain's expected certificate is not found on the Application Gateway (e.g., never issued), log a warning and skip that domain rather than aborting the entire batch.

#### Scenario: Missing certificate results in skip with warning
- **WHEN** `az-acme-tool renew` is invoked and a domain's expected certificate does not exist on the gateway
- **THEN** the domain SHALL be skipped, a warning SHALL be printed to stderr, and processing SHALL continue for remaining domains

### Requirement: Renew summary output
The system SHALL print a summary after processing all domains, indicating how many were renewed, skipped, and failed.

#### Scenario: Summary printed after completion
- **WHEN** `az-acme-tool renew` completes processing one or more domains
- **THEN** stdout SHALL contain a summary line with the total number of domains processed, renewed, skipped, and failed
