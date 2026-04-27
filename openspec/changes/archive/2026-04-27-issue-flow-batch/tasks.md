## 1. Refactor `run_issue` for parallel execution

- [x] 1.1 Add module-level constant `_MAX_BATCH_WORKERS = 3` and import `concurrent.futures` + `time` in `src/az_acme_tool/issue_command.py`
- [x] 1.2 Split `run_issue` into a serial dry-run branch (preserving the existing `for target in targets:` print loop) and a parallel non-dry-run branch
- [x] 1.3 In the parallel branch, wrap the worker pool with `with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_BATCH_WORKERS) as executor:` so cleanup is guaranteed on every exit path
- [x] 1.4 Submit one future per `DomainTarget` via `executor.submit(_issue_single_domain, target, config)`; keep a `dict[Future, DomainTarget]` to map futures back to their targets
- [x] 1.5 Iterate completions with `concurrent.futures.as_completed(futures)`; for each future call `.result()` inside `try / except Exception`. On success print `[OK] {domain} on {gateway}` and increment `succeeded`; on failure print `[FAILED] {domain} on {gateway}: {exc}` (stderr), append `(target, exc)` to a `failures` list, and increment `failed`
- [x] 1.6 Measure wall-clock duration: `start = time.monotonic()` immediately before the executor block; `duration = time.monotonic() - start` after the consumer loop drains
- [x] 1.7 Replace the existing `Summary: ...` line with `Total: {total} | Succeeded: {succeeded} | Failed: {failed} | Duration: {duration:.1f}s`
- [x] 1.8 When `failed > 0`, print a `Failed domains:` block listing `  - {domain} on {gateway}: {exc}` in submission order (i.e. the order of `targets`), then `raise IssueError(f"{failed} domain(s) failed to issue certificates.")` to preserve the non-zero exit code

## 2. Tests

- [x] 2.1 Add `TestIssueBatchParallelism.test_max_three_in_flight` in `tests/test_issue_command.py` — patch `_issue_single_domain` with a function that records concurrent entries via a shared `threading.Lock`-guarded counter and a small `time.sleep`; invoke `run_issue` with 5 targets and assert the maximum observed concurrency is ≤ 3
- [x] 2.2 Add `TestIssueBatchFailureIsolation.test_other_domains_continue_on_one_failure` — patch `_issue_single_domain` to raise for domain B in `[A, B, C, D, E]`; assert all five domains were called exactly once and `[FAILED]` line for B appears in output
- [x] 2.3 Add `TestIssueBatchSummary.test_summary_line_format` — patch `_issue_single_domain` (1 success, 1 failure); assert stdout contains a line matching the regex `^Total: 2 \| Succeeded: 1 \| Failed: 1 \| Duration: \d+\.\d+s$`
- [x] 2.4 Add `TestIssueBatchSummary.test_failed_domains_block_lists_each_failure` — assert the `Failed domains:` block contains a line for the failing domain with both the domain name and the exception message
- [x] 2.5 Add `TestIssueBatchSummary.test_dry_run_remains_serial` — assert that with `--dry-run` and 5 domains, output lines appear in `_resolve_targets` order and `_issue_single_domain` is never called
- [x] 2.6 Update or remove obsolete assertions in existing `TestIssueSummary` tests that match the old `Summary: ...` format

## 3. Quality checks

- [x] 3.1 Run `ruff check src/ tests/` and fix any lint issues
- [x] 3.2 Run `mypy --strict src/` and fix any type errors
- [x] 3.3 Run `python -m pytest tests/ --cov=src/az_acme_tool --cov-report=term-missing` and confirm ≥80% line coverage and that all tests pass
