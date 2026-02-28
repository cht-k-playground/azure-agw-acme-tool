# cli-cleanup Specification

## Purpose
The `cleanup` CLI command identifies and removes orphaned ACME challenge routing rules from Azure Application Gateway URL path maps. These rules are created during the ACME HTTP-01 challenge flow and may be left behind if the CLI process is interrupted.

## Requirements

### Requirement: Cleanup command lists orphaned ACME challenge rules
The system SHALL provide a `cleanup` CLI command that scans all URL path maps on the configured Azure Application Gateway and identifies routing rules whose names begin with the prefix `acme-challenge-`.

#### Scenario: Rules found without --all flag
- **WHEN** the user runs `az-acme-tool cleanup` and orphaned rules exist
- **THEN** the command prints a numbered list of all found rule names and prompts the user to confirm removal of each rule individually before deleting it

#### Scenario: Rules found with --all flag
- **WHEN** the user runs `az-acme-tool cleanup --all` and orphaned rules exist
- **THEN** the command removes all matching rules without displaying any confirmation prompt and prints each removed rule name to stdout

#### Scenario: No orphaned rules found
- **WHEN** the user runs `az-acme-tool cleanup` (with or without `--all`) and no rules with the `acme-challenge-` prefix exist
- **THEN** the command prints "No orphaned ACME challenge rules found." and exits with code 0

#### Scenario: User declines individual rule removal
- **WHEN** the user runs `az-acme-tool cleanup` and responds "n" to a confirmation prompt for a specific rule
- **THEN** that rule is NOT deleted and the command continues to the next rule (if any)

#### Scenario: delete_routing_rule called only for acme-challenge- prefixed rules
- **WHEN** the cleanup command removes rules
- **THEN** `delete_routing_rule()` SHALL only be called for rules whose names begin with `acme-challenge-`

#### Scenario: Command exits with code 0 on success
- **WHEN** the cleanup command completes successfully (regardless of how many rules were removed)
- **THEN** the process exits with code 0
