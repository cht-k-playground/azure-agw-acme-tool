## Context

The `az-acme-tool` CLI creates temporary path-based routing rules on Azure Application Gateway during the ACME HTTP-01 challenge flow. These rules are named with the prefix `acme-challenge-` followed by the sanitized domain and a Unix timestamp (e.g., `acme-challenge-www-example-com-1709030400`). If the CLI process is interrupted mid-flow (e.g., network failure, SIGINT), these rules may remain on the gateway indefinitely.

The `cleanup` command stub already exists in `src/az_acme_tool/cli.py` (line 133–144) but raises `NotImplementedError`. The `AzureGatewayClient` in `src/az_acme_tool/azure_gateway.py` already has `delete_routing_rule()` referenced in the ROADMAP but the current implementation does not include a method to list URL path map rules. The current gateway client only exposes `list_certificates`, `get_certificate_expiry`, and `update_listener_certificate`.

**Constraints:**
- Python 3.11+, Click CLI framework, `mypy --strict`, `ruff`, `black --line-length 100`
- All Azure SDK calls must handle `HttpResponseError` explicitly
- No new runtime dependencies needed (uses existing `azure-mgmt-network`)

## Goals / Non-Goals

**Goals:**
- Implement `cleanup_command.py` with `run_cleanup()` function
- Add `list_acme_challenge_rules(gateway_name: str) -> list[str]` to `AzureGatewayClient` — scans URL path maps for rules prefixed with `acme-challenge-`
- Wire the existing `cleanup` CLI stub to call `run_cleanup()`
- Interactive mode (no `--all`): numbered list + per-rule confirmation prompt
- Batch mode (`--all`): remove all matching rules without prompting
- Graceful empty-state: print "No orphaned ACME challenge rules found." and exit 0

**Non-Goals:**
- Discovering orphaned backend pools or HTTP settings (only routing rules)
- Cross-subscription or cross-resource-group cleanup
- Dry-run mode for cleanup (not in ROADMAP spec)

## Decisions

### Decision 1: Where to scan for orphaned rules

**Choice**: Scan `url_path_maps` on the Application Gateway for `path_rules` whose names start with `acme-challenge-`.

**Rationale**: The ROADMAP spec states "透過名稱前綴 `acme-challenge-` 識別每個 AGW URL path maps 中的孤立規則". URL path maps are the correct location — path-based routing rules are stored as `path_rules` within `url_path_maps` on the AGW resource.

**Alternative considered**: Scanning `request_routing_rules` — rejected because path-based rules are nested under URL path maps, not at the top-level routing rules list.

### Decision 2: `list_acme_challenge_rules` return type

**Choice**: Return `list[str]` of rule names (not full rule objects).

**Rationale**: The `cleanup` command only needs rule names to display to the user and to pass to `delete_routing_rule()`. Returning full objects would expose internal Azure SDK types to the command layer unnecessarily.

### Decision 3: `delete_routing_rule` implementation

**Choice**: Add `delete_routing_rule(rule_name: str) -> None` to `AzureGatewayClient` that removes the named path rule from all URL path maps and calls `begin_create_or_update` to persist the change.

**Rationale**: The ROADMAP spec for `azure-gateway-client` lists `delete_routing_rule(gateway_name: str, rule_name: str) -> None` as a public method. Since the client is already scoped to a single gateway (gateway_name is set at construction), the method signature is `delete_routing_rule(rule_name: str) -> None`.

### Decision 4: Interactive confirmation UX

**Choice**: Use `click.confirm()` for per-rule prompts in interactive mode.

**Rationale**: Consistent with the `init` command's overwrite confirmation pattern. `click.confirm()` handles `y/n` input cleanly and is testable via `CliRunner` with `input=`.

### Decision 5: Linter rule suppressions

**Choice**: No linter rules will be disabled.

**Rationale**: The implementation is straightforward and does not require any suppression.

## Risks / Trade-offs

- [Risk] AGW `begin_create_or_update` is called once per deleted rule, which is slow for many orphaned rules → Mitigation: Batch all deletions into a single `begin_create_or_update` call after removing all target path rules from the in-memory gateway object.
- [Risk] Concurrent modification — another process modifies the AGW between `_get_gateway()` and `begin_create_or_update` → Mitigation: ARM will reject with a conflict error; `AzureGatewayError` will surface the message to the user.
- [Risk] `url_path_maps` or `path_rules` may be `None` → Mitigation: Use `or []` guards throughout.

## Migration Plan

1. Add `list_acme_challenge_rules()` and `delete_routing_rule()` to `AzureGatewayClient`
2. Create `cleanup_command.py` with `run_cleanup()`
3. Update `cli.py` cleanup stub to call `run_cleanup()`
4. Add tests for all new code
5. No migration needed — purely additive change
