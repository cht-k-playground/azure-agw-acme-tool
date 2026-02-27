## 1. Rewrite cli.py stubs

- [x] 1.1 Add `--config` and `--verbose` options to the root `main` group; use `@click.pass_context` and store both in `ctx.obj`
- [x] 1.2 Rewrite `init` command: keep only `--config-template` flag, remove `--email`/`--ca-url`/`--account-key`; decorate with `@click.pass_obj`
- [x] 1.3 Rewrite `issue` command: keep `--gateway`, `--domain`, `--dry-run`; remove `--config` and `--verbose`; decorate with `@click.pass_obj`
- [x] 1.4 Rewrite `renew` command: keep `--days`, `--force`; remove `--config`; decorate with `@click.pass_obj`
- [x] 1.5 Rewrite `status` command: rename `--format` to `--output` (Python var `output_format`); remove `--config`; decorate with `@click.pass_obj`
- [x] 1.6 Rewrite `cleanup` command: keep `--all`; remove `--config`; decorate with `@click.pass_obj`
- [x] 1.7 Ensure all type annotations are complete and `mypy --strict`-compatible (import `Any` from `typing`)

## 2. Update pyproject.toml

- [x] 2.1 Insert `azure-mgmt-web>=3.0` immediately after `azure-mgmt-network>=25.0` in `[project.dependencies]`
