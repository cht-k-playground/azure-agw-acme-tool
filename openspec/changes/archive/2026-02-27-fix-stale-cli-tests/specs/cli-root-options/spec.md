## ADDED Requirements

### Requirement: CLI subcommand smoke tests reflect implemented state
The test suite SHALL verify that `init`, `issue`, and `status` subcommands do not raise `NotImplementedError` when invoked. Tests that previously asserted `NotImplementedError` for these commands SHALL be replaced with tests that confirm the commands are reachable and handle errors gracefully (e.g., missing config file produces a non-zero exit code rather than an unhandled exception).

#### Scenario: init subcommand does not raise NotImplementedError
- **WHEN** `az-acme-tool init` is invoked via the Click test runner with a missing config file
- **THEN** the command exits with a non-zero exit code and an error message, and does NOT raise `NotImplementedError`

#### Scenario: issue subcommand does not raise NotImplementedError
- **WHEN** `az-acme-tool issue` is invoked via the Click test runner with a missing config file
- **THEN** the command exits with a non-zero exit code and an error message, and does NOT raise `NotImplementedError`

#### Scenario: status subcommand does not raise NotImplementedError
- **WHEN** `az-acme-tool status` is invoked via the Click test runner with a missing config file
- **THEN** the command exits with a non-zero exit code and an error message, and does NOT raise `NotImplementedError`
