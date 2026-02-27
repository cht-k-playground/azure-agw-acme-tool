## ADDED Requirements

### Requirement: Root group exposes --config and --verbose
The `main` Click group SHALL accept `--config` (default `~/.config/az-acme-tool/config.yaml`) and `--verbose` (boolean flag) options and store them in the Click context object so all subcommands can access them.

#### Scenario: Default config path used when --config not supplied
- **WHEN** the user invokes any subcommand without specifying `--config`
- **THEN** the context object SHALL contain `config = "~/.config/az-acme-tool/config.yaml"`

#### Scenario: Custom config path forwarded to subcommand
- **WHEN** the user invokes `az-acme-tool --config /tmp/my.yaml <subcommand>`
- **THEN** the context object SHALL contain `config = "/tmp/my.yaml"`

#### Scenario: Verbose flag forwarded to subcommand
- **WHEN** the user invokes `az-acme-tool --verbose <subcommand>`
- **THEN** the context object SHALL contain `verbose = True`

### Requirement: init accepts only --config-template flag
The `init` subcommand SHALL accept only the `--config-template` boolean flag and SHALL NOT accept `--email`, `--ca-url`, or `--account-key` flags.

#### Scenario: --config-template flag accepted
- **WHEN** the user invokes `az-acme-tool init --config-template`
- **THEN** the command SHALL be invoked with `config_template = True`

#### Scenario: Removed flags are rejected
- **WHEN** the user invokes `az-acme-tool init --email foo@example.com`
- **THEN** Click SHALL reject the invocation with an error about an unrecognised option

### Requirement: issue subcommand does not accept --config or --verbose
The `issue` subcommand SHALL accept `--gateway`, `--domain`, and `--dry-run` only. `--config` and `--verbose` SHALL be removed from `issue`.

#### Scenario: issue flags accepted
- **WHEN** the user invokes `az-acme-tool issue --gateway gw1 --domain example.com --dry-run`
- **THEN** the command SHALL be invoked with the corresponding parameters set

### Requirement: status uses --output instead of --format
The `status` subcommand SHALL accept `--output` (choices: `table`, `json`, `yaml`) with Python variable name `output_format`. The old `--format` flag SHALL not exist.

#### Scenario: --output accepted
- **WHEN** the user invokes `az-acme-tool status --output json`
- **THEN** the command SHALL be invoked with `output_format = "json"`

### Requirement: azure-mgmt-web listed as project dependency
`pyproject.toml` SHALL list `azure-mgmt-web>=3.0` in `[project.dependencies]`.

#### Scenario: Dependency present after change
- **WHEN** `pyproject.toml` is inspected
- **THEN** `azure-mgmt-web>=3.0` SHALL appear in the `dependencies` list, immediately after `azure-mgmt-network>=25.0`
