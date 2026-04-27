## Why

`run_issue` currently processes domains serially. With multiple domains (typical enterprise deployments have 3–10 per gateway) the wall-clock time for a full `issue` run scales linearly, and a single ACME or Azure transient failure aborts the entire batch. Phase 1 cannot be considered complete until the orchestration layer can fan out across domains, isolate failures, and emit a usable batch summary.

## What Changes

- Replace the serial `for target in targets:` loop in `run_issue` (`src/az_acme_tool/issue_command.py`) with a `concurrent.futures.ThreadPoolExecutor`-based fan-out, capped at **3 concurrent workers**.
- Add **failure isolation**: when one domain raises, log the failure and continue processing the remaining domains.
- Replace the existing trailing summary (`Summary: N domain(s) — S succeeded, F failed.`) with a richer line:
  `Total: N | Succeeded: S | Failed: F | Duration: Xs`
  — followed, on failure, by a list of `<domain>: <error message>` entries.
- Wall-clock duration is measured from the start of the batch (after dry-run filter) until the last future resolves.
- `--dry-run` continues to execute serially (no Azure / ACME calls; parallelism would only complicate output ordering for no benefit).
- `cli-renew` is **out of scope** — its serial loop remains as-is for this change. Renew batching is deferred to a future change if needed.
- Add unit tests covering: parallelism cap (≤3 in-flight), failure isolation, summary line format, and per-failure detail.

## Capabilities

### New Capabilities

*(none — this change extends an existing capability)*

### Modified Capabilities

- `cli-issue`: replace the per-target serial loop with a bounded thread-pool fan-out, add failure isolation, and adopt the new summary line format.

## Impact

- Modified: `src/az_acme_tool/issue_command.py` — `run_issue` orchestration layer
- Modified: `tests/test_issue_command.py` — new tests for parallelism, isolation, summary
- Modified: `openspec/specs/cli-issue/spec.md` (via delta) — summary format and isolation requirements
- No new runtime dependencies (`concurrent.futures` is in the standard library)
- No changes to `_issue_single_domain`, `AzureGatewayClient`, `AcmeClient`, or config schema
- Backwards compatibility: existing CLI flags (`--gateway`, `--domain`, `--dry-run`) preserved unchanged
