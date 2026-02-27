## Context

The `issue` command is the primary user-facing command for certificate issuance. It reads the config file, applies optional gateway/domain filters, and either logs the planned work (dry-run) or delegates to the actual 14-step ACME pipeline per domain.

The ROADMAP explicitly notes: "`azure-gateway-client` and `acme-client` are already complete — `cli-issue` must code against the real typed interfaces, not stubs or placeholders." However, the 14-step pipeline itself belongs to `issue-flow-core` (Phase 1-E). This change implements the orchestration layer: config loading, filtering, dry-run, and a placeholder `_issue_single_domain()` that `issue-flow-core` will replace.

Constraints: `mypy --strict`, `ruff`, `black --line-length 100`, ≥80% coverage, structured exceptions.

## Goals / Non-Goals

**Goals:**
- `--gateway` filter: process only gateways matching the given name
- `--domain` filter: process only the specified domain (fail with non-zero exit if not found in config)
- `--dry-run`: log each planned domain step without executing any Azure/ACME calls
- Per-domain result tracking: collect success/failure per domain and print a summary
- Clean delegation point: `_issue_single_domain()` stub raises `NotImplementedError` — replaced by `issue-flow-core`

**Non-Goals:**
- Implementing the actual ACME/Azure pipeline (that is `issue-flow-core`)
- Parallel/batch processing (that is `issue-flow-batch`)
- Renewal threshold logic (that is `cli-renew`)

## Decisions

### D1: `issue_command.py` with `run_issue()` entry point

Same thin-CLI pattern as `init_command.py`. `cli.py` remains a dispatcher. All logic is in the module, easily unit-testable without Click machinery.

### D2: Filter resolution produces a flat list of `(gateway_name, domain_str)` tuples

The config structure is nested (gateways → domains). Flattening to tuples before the main loop simplifies filtering logic and makes the dry-run log straightforward.

### D3: Unknown `--domain` is a hard error (non-zero exit)

ROADMAP acceptance criteria #4: if `--domain` is provided but not found in config, exit non-zero with clear message. This is implemented by checking the filtered list is non-empty after applying the domain filter.

### D4: `_issue_single_domain()` is a module-private stub

It receives `(gateway_name, domain, config, dry_run)` and currently raises `NotImplementedError`. `issue-flow-core` will replace it with the real 14-step logic. This keeps the contract explicit.

### D5: Dry-run uses `click.echo()` for planned steps

Each domain prints `[DRY-RUN] Would issue certificate for <domain> on <gateway>`. No Azure SDK or ACME calls are made.

## Risks / Trade-offs

- `_issue_single_domain()` stub: if called in non-dry-run mode it will raise `NotImplementedError`. This is intentional and temporary — the `issue` command is only fully functional after `issue-flow-core` lands.
- Coverage of the non-dry-run path: since `_issue_single_domain()` raises immediately, tests for the non-dry-run path use a mock, keeping actual coverage above 80%.
