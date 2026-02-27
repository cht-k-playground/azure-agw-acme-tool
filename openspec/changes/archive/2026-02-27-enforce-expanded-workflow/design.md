## Context

This project enforces OpenSpec Expanded Mode (spec-driven schema). The governance documents `AGENTS.md` and `ROADMAP.md` contain references to `/opsx:propose` — a `core`-profile shortcut that combines scaffold and planning into a single step. This shortcut is incompatible with the Expanded Mode workflow mandated by this project, where each artifact (`proposal.md`, `specs/`, `design.md`, `tasks.md`) is created and reviewed in dependency order before implementation begins.

These residual references risk misleading agents or contributors into using the wrong workflow entry point.

---

## Goals / Non-Goals

**Goals**
- Remove `/opsx:propose` as a recommended or default starting point from all governance documents.
- Ensure `AGENTS.md` and `ROADMAP.md` consistently describe the five-step Expanded Mode workflow: `/opsx:new → /opsx:ff → /opsx:apply → /opsx:verify → /opsx:archive`.

**Non-Goals**
- No runtime behaviour changes.
- No changes to source code, tests, or `pyproject.toml`.
- No changes to the OpenSpec schema configuration (`.openspec.yaml`).

---

## Decisions

1. **Retain `/opsx:propose` in the slash command reference table** in `AGENTS.md`, but annotate it as a `core`-profile shortcut not used in this project. This keeps the table a complete command reference without endorsing the shortcut as a workflow entry point.

2. **Replace `/opsx:propose` in Section 6 and Section 7** of `AGENTS.md` with the explicit two-step equivalent `/opsx:new <name>` + `/opsx:ff`, making the "Just Fix" guidance unambiguous and consistent with Expanded Mode.

3. **Replace all three occurrences of `/opsx:propose` in `ROADMAP.md`** with the explicit `/opsx:new → /opsx:ff` pattern so that usage instructions match the mandated workflow.

---

## Risks / Trade-offs

No technical risks. The only risk is an incomplete replacement leaving residual references — mitigated by the `tasks.md` checklist, which identifies each specific location to update.
