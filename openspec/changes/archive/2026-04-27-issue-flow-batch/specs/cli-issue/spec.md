## ADDED Requirements

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

## MODIFIED Requirements

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
