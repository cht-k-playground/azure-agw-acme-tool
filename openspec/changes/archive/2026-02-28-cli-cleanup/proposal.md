## Why

During the ACME HTTP-01 challenge flow, temporary path-based routing rules are created on Azure Application Gateway with the prefix `acme-challenge-`. If the CLI process is interrupted or a challenge fails, these rules may be left behind as orphaned entries. A dedicated `cleanup` command is needed to identify and remove these stale rules safely.

## What Changes

- Add a new `cleanup` CLI command to `src/az_acme_tool/cli.py`
- Implement `cleanup_command.py` module with the cleanup orchestration logic
- The command scans all AGW URL path maps for rules prefixed with `acme-challenge-`
- Without `--all`: displays a numbered list of found rules and prompts for individual confirmation before removal
- With `--all`: removes all matching rules without prompting
- Outputs each removed rule name to stdout
- Exits with code 0 even when no orphaned rules are found (prints informational message)

## Capabilities

### New Capabilities

- `cli-cleanup`: The `az-acme-tool cleanup` command that identifies and removes orphaned ACME challenge routing rules from Azure Application Gateway

### Modified Capabilities

- `azure-gateway-client`: Add `list_acme_challenge_rules(gateway_name: str) -> list[str]` method to enumerate all URL path map rules with the `acme-challenge-` prefix

## Impact

- New file: `src/az_acme_tool/cleanup_command.py`
- New file: `tests/test_cleanup_command.py`
- Modified: `src/az_acme_tool/cli.py` (register `cleanup` command)
- Modified: `src/az_acme_tool/azure_gateway.py` (add `list_acme_challenge_rules` method)
- Modified: `tests/test_azure_gateway.py` (add tests for new method)
- Dependencies: `azure-gateway-client` (already implemented)
