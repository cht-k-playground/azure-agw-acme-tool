## Context

`run_issue` in `src/az_acme_tool/issue_command.py` currently iterates `targets` serially:

```python
for target in targets:
    try:
        _issue_single_domain(target, config)
        click.echo(f"[OK] {target.domain} on {target.gateway_name}")
        succeeded += 1
    except Exception as exc:
        click.echo(f"[FAILED] ...", err=True)
        failed += 1
```

Each call to `_issue_single_domain` performs ~9 blocking network round-trips (Azure ARM + ACME CA + polling), so a 5-domain batch takes roughly 5× the per-domain time. A transient ACME or Azure error today already gets caught per-domain — failure isolation already exists in spirit — but the wall-clock cost of waiting on each domain in series is the real pain point.

**Constraints**
- `_issue_single_domain`, `AzureGatewayClient`, and `AcmeClient` are all synchronous and use blocking I/O (Azure SDK has no first-party asyncio variant for `azure-mgmt-network`/`azure-mgmt-web`; `acme.client.ClientV2` is sync).
- ROADMAP `issue-flow-batch` mandates `max_workers=3` and the summary line `Total: N | Succeeded: S | Failed: F | Duration: Xs`.
- `cli-renew` currently calls `_issue_single_domain` directly inside its own loop — it is intentionally **out of scope**.
- Cross-cutting constraints from `ROADMAP.md` apply: `mypy --strict`, `ruff` clean, ≥80% coverage, no secrets in logs.

## Goals / Non-Goals

**Goals:**
- Parallelize the per-domain ACME pipeline in `run_issue` with a bounded worker pool.
- Isolate failures so one domain cannot abort the rest of the batch.
- Emit a richer summary line with totals and wall-clock duration.
- Preserve all existing CLI behavior: `--gateway`, `--domain`, `--dry-run`, exit codes.

**Non-Goals:**
- Reworking `_issue_single_domain` or any client class.
- Making `cli-renew` parallel (deferred).
- Exposing a `--concurrency` / `--max-workers` flag (ROADMAP fixes 3).
- Async/await refactor (sync libs make threads simpler).
- Cross-domain coordination (each domain's ACME order is independent).

## Decisions

### Decision 1: Threads over asyncio

**Choice**: `concurrent.futures.ThreadPoolExecutor(max_workers=3)`.

**Rationale**: Every dependency in the call chain (`azure-mgmt-network`, `azure-mgmt-web`, `acme.client.ClientV2`, `requests`) is synchronous. asyncio would require wrapping each call in `loop.run_in_executor`, which gives the same behavior as a thread pool with extra ceremony. Threads also let us reuse the existing `_issue_single_domain` function unchanged. The blocking I/O in each domain releases the GIL for the duration of network calls, so a 3-thread fan-out gives near-3× speedup for I/O-bound workloads.

**Alternative considered**: `asyncio` + `loop.run_in_executor` — rejected for added complexity with no benefit given sync libraries.

### Decision 2: Hardcoded `max_workers=3`

**Choice**: `_MAX_BATCH_WORKERS = 3` module-level constant. No CLI flag.

**Rationale**: ROADMAP acceptance criterion 1 fixes the cap at 3. ACME CAs (Let's Encrypt) also rate-limit aggressive concurrent orders; 3 is a conservative ceiling that avoids `urn:ietf:params:acme:error:rateLimited`. If a future change needs tunability, the constant becomes a `--max-workers` flag without disturbing the spec.

### Decision 3: `as_completed` for result collection

**Choice**: Submit one future per target, collect results via `concurrent.futures.as_completed(futures)`.

**Rationale**: Lets us print `[OK] ...` / `[FAILED] ...` lines as each domain finishes (responsive feedback) instead of waiting for the whole batch. The output ordering becomes non-deterministic by completion order, but every line is already prefixed with the domain name, so log readability is preserved.

**Alternative considered**: `executor.map` — rejected because it surfaces results in submission order, blocking on each in turn (which negates the responsiveness benefit), and re-raises the first exception (which breaks failure isolation unless we wrap each call).

### Decision 4: Failure isolation via per-future try/except

**Choice**: Each future's `.result()` is called inside a `try / except Exception` block in the consumer loop. Failures are collected into a `list[tuple[DomainTarget, Exception]]` for the summary.

**Rationale**: Exceptions raised inside `_issue_single_domain` are stored on the future; `.result()` re-raises them on the main thread, where we can catch and tally them without affecting other in-flight work. The existing per-domain `[FAILED] {domain}: {exc}` message is preserved.

### Decision 5: Duration measurement

**Choice**: `start = time.monotonic()` immediately before submitting futures; `duration = time.monotonic() - start` after the consumer loop drains. Format with `f"{duration:.1f}s"`.

**Rationale**: `time.monotonic()` is unaffected by wall-clock adjustments. `.1f` keeps the summary line readable (whole-second granularity is too coarse for fast batches; ms is too noisy).

### Decision 6: Dry-run stays serial

**Choice**: When `dry_run` is true, retain the existing serial `for target in targets:` print loop. The thread-pool path is taken only when `dry_run` is false.

**Rationale**: Dry-run does no I/O — it just prints planned steps. Parallelizing it would scramble output ordering for zero throughput benefit. Preserving the serial path also keeps the dry-run output deterministic for tests.

### Decision 7: Summary line + failure detail format

**Choice**:
```
Total: 5 | Succeeded: 3 | Failed: 2 | Duration: 12.4s

Failed domains:
  - www.example.com on agw-alpha: AcmeError: validation timed out
  - api.example.com on agw-alpha: AzureGatewayError: 429 Too Many Requests
```
Followed (when `failed > 0`) by `raise IssueError(f"{failed} domain(s) failed to issue certificates.")` to keep the existing non-zero exit code behavior.

**Rationale**: Matches ROADMAP acceptance criterion 3 verbatim for the summary line. The "Failed domains" block uses the existing `[FAILED] {domain} on {gateway}: {exc}` content, restated together so operators don't have to scroll back through interleaved output.

### Decision 8: Click `echo` thread safety

**Choice**: Continue calling `click.echo` directly from the consumer thread (the main thread, since `as_completed` runs there). Worker threads do **not** call `click.echo`.

**Rationale**: `click.echo` writes to `sys.stdout`, which Python guarantees thread-safe at the line level via the underlying `io.TextIOWrapper`. Routing all stdout through the consumer thread eliminates even that concern. Worker threads only run `_issue_single_domain`, which uses the `logging` module (already thread-safe).

## Risks / Trade-offs

- **[Risk]** Output ordering becomes non-deterministic across runs.
  → **Mitigation**: Every line carries the domain name; the trailing summary lists failures in deterministic order (sorted by submission order via the `targets` list).

- **[Risk]** ACME CA rate-limiting more likely with 3-way concurrency.
  → **Mitigation**: `_with_retry` in `AcmeClient` already implements exponential back-off (max 3 attempts). 3 concurrent orders is well below Let's Encrypt's published per-account/hour limits.

- **[Risk]** Azure ARM throttling (`HttpResponseError 429`) more likely with concurrent gateway operations on the same gateway.
  → **Mitigation**: Each `_issue_single_domain` call already runs against a single gateway via its own `AzureGatewayClient` instance; the Azure SDK retries 429s internally. If this becomes a problem in practice, future work can serialize per-gateway and parallelize across gateways.

- **[Risk]** A worker thread holding native resources (Azure HTTP session) could leak if the process is interrupted mid-batch.
  → **Mitigation**: Use `executor` as a context manager (`with ThreadPoolExecutor(...) as executor:`) so Python guarantees `shutdown(wait=True)` on exit, including exception paths.

- **[Trade-off]** Stack traces for failed domains are truncated to the exception's `str(exc)` form in the failure summary. Full tracebacks remain in the JSON Lines log file at DEBUG level.

## Migration Plan

1. Refactor `run_issue` to split the post-filter logic into a serial dry-run branch and a parallel non-dry-run branch.
2. Introduce `_MAX_BATCH_WORKERS = 3` module constant.
3. Move the per-domain success/failure counting into the `as_completed` consumer.
4. Replace the existing summary line with the new format.
5. Update `tests/test_issue_command.py` — keep existing behavioral tests, add four new tests (parallel cap, isolation, summary format, failure detail).
6. No data migration; no config changes; existing CLI flags unchanged.
