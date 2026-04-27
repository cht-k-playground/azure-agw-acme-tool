# cli-issue Specification

## Purpose
TBD - created by syncing change cli-issue. Update Purpose after archive.

## Requirements

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
The system SHALL print a summary line after processing all domains in the format `Total: <N> | Succeeded: <S> | Failed: <F> | Duration: <X>s`, where `Duration` is the wall-clock time of the batch in seconds with one decimal place. When at least one domain failed, the command SHALL exit with a non-zero exit code.

#### Scenario: Summary line printed after completion
- **WHEN** `az-acme-tool issue` completes processing one or more domains
- **THEN** stdout SHALL contain a single line matching the regex `^Total: \d+ \| Succeeded: \d+ \| Failed: \d+ \| Duration: \d+\.\d+s$`

#### Scenario: Counts add up
- **WHEN** the summary line is emitted
- **THEN** `Succeeded + Failed` SHALL equal `Total`

#### Scenario: Non-zero exit on any failure
- **WHEN** one or more domains fail
- **THEN** the process SHALL exit with a non-zero exit code

### Requirement: Bounded parallel domain processing
The system SHALL process domains concurrently using a `concurrent.futures.ThreadPoolExecutor` with **at most 3** in-flight workers when `--dry-run` is not set. The dry-run code path SHALL remain serial.

#### Scenario: At most three domains processed concurrently
- **WHEN** `az-acme-tool issue` is invoked with five domains and a tracking instrument records concurrent entries into `_issue_single_domain`
- **THEN** the maximum observed concurrency SHALL be ≤ 3

#### Scenario: Dry-run remains serial
- **WHEN** `az-acme-tool issue --dry-run` is invoked with five domains
- **THEN** `_issue_single_domain` SHALL NOT be called and the planned-step lines SHALL be printed in the order produced by `_resolve_targets`

### Requirement: Failure isolation across the batch
The system SHALL isolate per-domain failures so that an exception raised by one domain does not interrupt processing of any other domain in the same batch.

#### Scenario: Other domains continue when one fails
- **WHEN** `_issue_single_domain` raises `AcmeError` for domain B in a batch of `[A, B, C, D, E]`
- **THEN** every other domain SHALL still have `_issue_single_domain` invoked exactly once

#### Scenario: Failure detail surfaced in summary
- **WHEN** one or more domains fail
- **THEN** stdout SHALL include a `Failed domains:` block listing each failure as `<domain> on <gateway>: <error message>`
