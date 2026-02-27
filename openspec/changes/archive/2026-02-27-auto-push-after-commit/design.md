# Design: auto-push-after-commit

## Context

Cloud agent sessions are ephemeral. Local commits that are not pushed to the remote are permanently lost when the session ends. `AGENTS.md` Section 2 contains "Hard Rules" — invariants that agents must never violate. There is currently no rule requiring commits to be pushed immediately after creation.

## Goals

Add one new Hard Rule to Section 2 of `AGENTS.md`.

## Non-Goals

- No source code changes.
- No changes to `pyproject.toml`, test files, or any file under `src/`.

## Decision

Append the new rule as item 10 in the existing numbered list in Section 2. The rule text shall be:

> **Push immediately after every commit.** After every `git commit`, the agent MUST immediately run `git push` to the remote tracking branch. This applies to all commits in this project, since development always occurs on cloud agents and local commits are permanently lost when the session ends.

This placement keeps all hard rules together and maintains the sequential numbering scheme already established in Section 2.

## Risks

None — this is a documentation-only change.
