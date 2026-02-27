## Context

The CLI (`src/az_acme_tool/cli.py`) currently duplicates `--config` and `--verbose` across every subcommand, violating Click conventions and the project's own CLI design constraints (AGENTS.md §4). The `init` subcommand also accepts configuration values (`--email`, `--ca-url`, `--account-key`) that should come from the config file. The `azure-mgmt-web` SDK is needed for future Application Gateway certificate attachment but is missing from `pyproject.toml`.

## Goals / Non-Goals

**Goals:**
- Centralise `--config` and `--verbose` on the root `main` Click group
- Pass config path and verbosity to subcommands via `ctx.obj` (Click context dict)
- Strip config-value flags (`--email`, `--ca-url`, `--account-key`) from `init`
- Rename `--format` → `--output` on `status` for CLI convention consistency
- Add `azure-mgmt-web>=3.0` to `pyproject.toml` dependencies
- All functions remain stubs (`raise NotImplementedError`)

**Non-Goals:**
- Implementing any actual logic in any command
- Changing command names or adding new commands
- Modifying tests (no logic to test)

## Decisions

**Click context object for shared options**
Use `@click.pass_context` on `main` with `ctx.ensure_object(dict)` to store `config` and `verbose`, and `@click.pass_obj` on subcommands to receive the dict. This is the idiomatic Click pattern for shared state and avoids a global variable or a custom class.

Alternative considered: a custom dataclass passed as `ctx.obj`. Rejected as unnecessary complexity for two fields at stub stage.

**`init --config-template` stays flag-only**
The `--config-template` flag on `init` prints a template without reading any config, so it does not need config path access. The subcommand still receives `obj` via `@click.pass_obj` (it just won't use it until logic is implemented).

**`--output` over `--format` on `status`**
`--format` is a Python built-in name; using `--output` with `output_format` as the Python variable avoids shadowing and aligns with common CLI tools (e.g., `kubectl -o`).

## Risks / Trade-offs

- **Breaking change to callers of `issue`/`renew`/`status`/`cleanup`**: Any scripts passing `--config` to subcommands will break. Mitigation: this is a stub phase; no callers exist yet.
- **`azure-mgmt-web` version floor**: `>=3.0` may pull a newer version than intended. Mitigation: pin tighter when implementing the feature that uses it.

## Migration Plan

1. Rewrite `cli.py` in-place (stubs only).
2. Insert `azure-mgmt-web>=3.0` after `azure-mgmt-network>=25.0` in `pyproject.toml`.
3. Run `mypy --strict src/` and `ruff check src/` to verify no regressions.
4. No rollback complexity — all commands still raise `NotImplementedError`.
