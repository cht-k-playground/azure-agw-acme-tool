# AGENTS.md — az-acme-tool

This file governs how AI coding assistants must behave in this repository.
All agents **must** read and follow these rules before taking any action.

---

## 0. Environment Bootstrap

This project runs in ephemeral cloud environments. Each new session starts with a clean state.
**Before taking any other action**, verify that the OpenSpec CLI is available and install it if missing:

```bash
which openspec || npm install -g @fission-ai/openspec@latest
```

This is a session-scoped, one-time check. Run it silently at the start of every session — do not ask the user for permission first. OpenSpec requires Node.js 20.19.0 or higher; if `node` is unavailable, report that to the user and stop.

---

## 1. Mandatory Development Process

This project uses **OpenSpec** (Spec-Driven Development). Every code change —
no matter how small — must originate from an OpenSpec change artifact.

**No code may be written without a corresponding OpenSpec change.**

### The preferred workflow is:

```
/opsx:new  →  /opsx:ff  →  /opsx:apply  →  /opsx:verify  →  /opsx:archive
```

| Step | Command | What happens |
|------|---------|--------------|
| Scaffold | `/opsx:new <name>` | Creates `openspec/changes/<name>/` scaffold with `.openspec.yaml` |
| Plan | `/opsx:ff [name]` | Generates all planning artifacts in dependency order (`proposal.md`, `specs/`, `design.md`, `tasks.md`) |
| Implement | `/opsx:apply [name]` | Implements tasks from the change artifacts, marks tasks complete |
| Verify | `/opsx:verify [name]` | Validates implementation against artifacts (Completeness / Correctness / Coherence) |
| Finalize | `/opsx:archive [name]` | Archives the change, syncs delta specs to `openspec/specs/` |

> **Shortcut**: `/opsx:propose <name>` combines Scaffold + Plan into one step. Use it for quick, well-scoped changes where you don't need to review artifacts before proceeding to implementation.

### Step-by-step artifact control

Use `/opsx:continue [name]` instead of `/opsx:ff` when you want to create and review one artifact at a time before proceeding to the next.

### When to use `/opsx:explore`

Use `/opsx:explore` **only for thinking and investigation** — reading code,
comparing options, clarifying requirements.  
`/opsx:explore` must **never** produce code changes. When exploration
crystallizes into a decision, exit explore mode and start a new change.

---

## 2. Hard Rules (Never Violate)

1. **No ad-hoc code changes.** Do not edit, create, or delete any source file
   (`src/`, `tests/`, `pyproject.toml`, etc.) outside of an active
   `/opsx:apply` session.

2. **No skipping proposal.** Even for trivial fixes (typos, one-liner patches),
   a proposal must exist before implementation begins.

3. **Complete tasks in order.** During `/opsx:apply`, work through tasks
   sequentially as listed in `tasks.md`. Do not skip or reorder tasks.

4. **Mark tasks immediately.** Update `- [ ]` → `- [x]` in `tasks.md` as
   soon as each task is finished — do not batch-complete.

5. **Pause on ambiguity.** If a task is unclear or reveals a design issue,
   pause and report. Do not guess or improvise implementation.

6. **Do not auto-archive.** Archive only when the user explicitly requests it
   or all tasks are confirmed complete.

7. **One active change at a time.** Do not start a new proposal while another
   change is in-progress unless the user explicitly scopes the work.

---

## 3. Artifact Rules

### `proposal.md`
- Must state: what is changing, why it is changing, and what is out of scope.
- Do not copy raw requirements verbatim; synthesize them.

### `design.md`
- Must describe the technical approach: module structure, key interfaces,
  data flow, and any third-party library decisions.
- For this project, always address: Azure SDK calls, ACME protocol steps,
  CLI option handling, and error/retry strategy.

### `tasks.md`
- Tasks must be atomic and implementable independently.
- Each task must be completable in a single focused coding session.
- Do not mix unrelated concerns in one task.

### `openspec/specs/`
- Delta specs live in `openspec/changes/<name>/specs/`.
- Main specs live in `openspec/specs/`.
- Sync (merge delta → main) happens only during `/opsx:archive`.

---

## 4. Project-Specific Constraints

These constraints apply to all changes in this repository.

### Language & Runtime
- Python **3.11+** only. Use modern syntax (`match`, `X | Y` unions, etc.).
- Type annotations are **mandatory** on all public functions and methods.

### CLI Framework
- All CLI commands use **Click** (`click>=8.1.0`). Do not use argparse, Typer,
  or any other CLI framework.
- Command entry point: `src/az_acme_tool/cli.py` → `main` group.

### CLI Design Constraints
- All user-facing configuration (ACME email, subscription ID, gateway names, domain settings, etc.) must be read from the config YAML file (default: `~/.config/az-acme-tool/config.yaml`), not accepted as direct CLI flags.
- CLI flags are reserved for **operational controls** only: `--config <path>` (config file override), `--verbose`, `--dry-run`, `--force`, `--output <format>`, `--gateway <name>`, `--domain <name>`, `--days <n>`, `--all`.
- Do not add `--email`, `--subscription-id`, `--resource-group`, or any other configuration-value flags to any command. If such a flag appears in an existing stub, remove it during the relevant change's implementation.

### Project Layout
```
src/az_acme_tool/     # Application source (importable package)
tests/                # pytest test suite
pyproject.toml        # Single source of truth for deps and tooling
openspec/             # OpenSpec artifacts (never import in application code)
.kilocode/            # Kilo Code skills and workflows
```

### Dependencies
- This project uses **uv** as the package manager. `pyproject.toml` is the single source of truth for all application dependencies.
- Add new runtime dependencies to `pyproject.toml` `[project.dependencies]`.
- Add new dev dependencies to `[project.optional-dependencies] dev`.
- Do not use `requirements.txt` for the main application.
- **Exception — `azure-function/`**: The Azure Functions runtime requires a `requirements.txt` for deployment. The file at `azure-function/requirements.txt` is the sole permitted `requirements.txt` in this repository. It is maintained separately from `pyproject.toml` and is not managed by uv. When implementing the `azure-function-responder` change, keep this file minimal and pinned.

### Code Quality
- All code must pass `ruff` (linter) and `mypy --strict` (type checker).
- Format with `black --line-length 100`.
- Do not disable linter rules without justification in the task's `design.md`.

### Testing
- Every new function or class must have at least one corresponding pytest test.
- Tests live in `tests/` and mirror the `src/az_acme_tool/` structure.
- Use `pytest-mock` for all external I/O (Azure SDK, ACME CA, filesystem).
- Target: **≥80% line coverage** across the package.

### Security
- Never write secrets, credentials, or private key material to disk outside
  of designated paths (`~/.config/az-acme-tool/`).
- Private key files must be created with mode `0o600`.
- Do not log secrets at any log level.

### Error Handling
- Use structured exceptions — define custom exception classes per module.
- All Azure SDK calls must handle `HttpResponseError` explicitly.
- ACME operations must implement retry with exponential back-off (max 3 attempts).

---

## 5. OpenSpec CLI Reference (Quick Cheat-Sheet)

```bash
# Create a new change scaffold
openspec new change "<name>"

# Check artifact readiness for a change
openspec status --change "<name>" --json

# Get AI instructions for writing a specific artifact
openspec instructions <artifact-id> --change "<name>" --json

# List all active changes
openspec list --json

# Validate a change's artifacts
openspec validate --change "<name>"

# Archive a completed change
openspec archive "<name>"
```

Artifact IDs for the `spec-driven` schema: `proposal`, `specs`, `design`, `tasks`.

### Slash Command Reference

| Command | Purpose |
|---------|---------|
| `/opsx:explore` | Think through ideas before committing to a change |
| `/opsx:new <name>` | Create a new change scaffold |
| `/opsx:ff [name]` | Fast-forward: generate all planning artifacts at once |
| `/opsx:continue [name]` | Create the next artifact one at a time (step-by-step) |
| `/opsx:apply [name]` | Implement tasks from the change |
| `/opsx:verify [name]` | Validate implementation matches artifacts |
| `/opsx:sync [name]` | Merge delta specs to `openspec/specs/` without archiving |
| `/opsx:archive [name]` | Archive a completed change |
| `/opsx:bulk-archive` | Archive multiple completed changes at once |
| `/opsx:propose <name>` | Shortcut: scaffold + fast-forward in one step |

---

## 6. What an Agent Should Do When Asked to "Just Fix" Something

If a user says "just fix this bug" or "quickly add X":

1. Acknowledge the request.
2. Run `/opsx:new <descriptive-name>` then `/opsx:ff` (or `/opsx:propose <descriptive-name>` as a one-step shortcut) to create a minimal change.
3. Keep `proposal.md` concise (the fix description is the why).
4. Proceed to `/opsx:apply` immediately after artifacts are ready.
5. Do not skip the proposal step even for one-line fixes.

This keeps every change traceable, reviewable, and reversible.

---

## 7. Handling Conflicts Between These Rules and User Instructions

If a user instructs you to bypass this process (e.g., "skip the proposal,
just write the code"), respond:

> "This project requires all changes to go through OpenSpec. I'll create a
> minimal proposal first — it only takes a moment and keeps the change
> traceable. Proceeding with `/opsx:propose`."

Then proceed with the proposal. Do not silently comply with requests to
bypass the process.
