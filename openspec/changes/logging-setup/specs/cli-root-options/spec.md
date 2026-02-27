## MODIFIED Requirements

### Requirement: Root group exposes --config and --verbose
The `main` Click group SHALL accept `--config` (default `~/.config/az-acme-tool/config.yaml`) and `--verbose` (boolean flag) options and store them in the Click context object so all subcommands can access them. The `main` group SHALL also call `setup_logging(verbose=verbose)` from `az_acme_tool.logging` as its first action after ensuring the context object exists, so that logging is configured before any subcommand executes.

#### Scenario: Default config path used when --config not supplied
- **WHEN** the user invokes any subcommand without specifying `--config`
- **THEN** the context object SHALL contain `config = "~/.config/az-acme-tool/config.yaml"`

#### Scenario: Custom config path forwarded to subcommand
- **WHEN** the user invokes `az-acme-tool --config /tmp/my.yaml <subcommand>`
- **THEN** the context object SHALL contain `config = "/tmp/my.yaml"`

#### Scenario: Verbose flag forwarded to subcommand
- **WHEN** the user invokes `az-acme-tool --verbose <subcommand>`
- **THEN** the context object SHALL contain `verbose = True`

#### Scenario: setup_logging called with verbose flag value
- **WHEN** `az-acme-tool --verbose <subcommand>` is invoked
- **THEN** `setup_logging(verbose=True)` SHALL have been called before the subcommand executes

#### Scenario: setup_logging called with verbose=False by default
- **WHEN** `az-acme-tool <subcommand>` is invoked without `--verbose`
- **THEN** `setup_logging(verbose=False)` SHALL have been called before the subcommand executes
