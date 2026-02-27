## Why

The CLI currently scatters `--config` and `--verbose` flags across individual subcommands, making the interface inconsistent with Click best practices and requiring users to repeat flags for every invocation. Additionally, Azure Application Gateway management requires the `azure-mgmt-web` SDK which is not yet listed as a dependency.

## What Changes

- Move `--config` (config file path) to the root `main` group with a sensible default (`~/.config/az-acme-tool/config.yaml`)
- Move `--verbose` to the root `main` group and remove it from the `issue` subcommand
- Remove `--email`, `--ca-url`, and `--account-key` flags from the `init` command (these belong in the config file, not as CLI flags)
- Rename `--format` to `--output` on the `status` command for consistency with CLI conventions
- Remove per-subcommand `--config` flags from `issue`, `renew`, `status`, and `cleanup`
- Add `azure-mgmt-web>=3.0` to `[project.dependencies]` in `pyproject.toml`

## Capabilities

### New Capabilities

- `cli-root-options`: Root Click group accepts `--config` and `--verbose`, passing them via context object to all subcommands

### Modified Capabilities

- (none — no existing spec files cover CLI flag layout)

## Impact

- `src/az_acme_tool/cli.py`: All commands rewritten (stubs only, no logic)
- `pyproject.toml`: New dependency added
