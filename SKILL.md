---
name: codex-manager
description: "Manage Codex coding-session continuity by externalizing project state into handoff files and explicit resume commands. Use when work may span multiple Codex accounts or sessions, especially after quota exhaustion, account switching, thread restarts, handoff requests, or prompts about resuming previous development from `HANDOFF.md`."
---

# Codex Manager

## Overview

Persist enough workspace state that a fresh Codex session can resume development without relying on live chat history.
Treat `HANDOFF.md` as the source of truth whenever quota limits, account switching, or long-running work make conversation context unreliable.

## Workflow

1. Inspect the workspace state first.
- Look for a root `HANDOFF.md`.
- If it exists, read it before planning.
- Reconcile it with the current file tree, `git status`, and any changed files before trusting it.

2. Create or refresh the handoff early.
- If the task is likely to span multiple exchanges, create or update `HANDOFF.md` before substantial edits.
- Use [references/handoff-template.md](references/handoff-template.md) when creating a new handoff or repairing an inconsistent one.
- Prefer one handoff per active project. In multi-project workspaces, name the target project explicitly and include its absolute path.

3. Checkpoint during development.
- Update `HANDOFF.md` after each substantive milestone, before risky refactors, and before ending a turn when work is unfinished.
- Record exact file paths, commands, validations, blockers, and next steps.
- Keep summaries brief but concrete. The next session should know where to start in under one minute.

4. Make resumption explicit.
- Include an exact resume prompt such as `Continue based on C:\path\to\HANDOFF.md` or `Continue modifying <project>; read HANDOFF.md first`.
- State the project directory and the first file or command to inspect after resuming.

5. Validate recoverability before claiming the task is safe to resume.
- Run `python scripts/validate_handoff.py <path-to-handoff>` from this skill directory after creating or heavily editing the handoff.
- Fix missing sections or empty content before telling the user that switching accounts is safe.

6. Use the automation helpers when the user wants less manual ceremony.
- Run `python scripts/codex_manager.py snapshot --workspace <workspace> --project <project>` to refresh `HANDOFF.md` in one command.
- Run `python scripts/codex_manager.py watch-cliproxy --workspace <workspace> --project <project>` to poll `CLIProxyAPI` and auto-refresh the handoff when watched credentials become unavailable or hit quota-like cooldown states.
- Run `python scripts/codex_manager.py manage-cliproxy --workspace <workspace> --project <project>` to keep one `CLIProxyAPI` auth pinned as the active account and automatically switch to the next healthy account when the current one hits quota-like failures.
- The watcher expects a management key in `CLIPROXY_MANAGEMENT_KEY` unless `--management-key` is provided explicitly.

## Recommended Handoff Contents

- Current project: absolute path and artifact or output targets when relevant.
- Objective: what the user wants now, not generic background.
- Current status: what already works and what is still unfinished.
- Key files: absolute paths with one-line purpose.
- Verification: commands already run and their outcomes.
- Open issues or risks: blockers, assumptions, or unverified areas.
- Next steps: ordered, concrete actions.
- Resume command: the exact prompt to use in a new session.

## Resume Rules

- Read `HANDOFF.md` first in a fresh session.
- Re-check repository state before continuing, because files may have changed since the handoff was written.
- Update stale sections instead of blindly following them.
- If the handoff and the workspace disagree, trust the workspace after confirming the difference, then rewrite the handoff.

## Guardrails

- Do not promise seamless live-chat continuity across accounts. Promise recoverability from workspace artifacts instead.
- Pair this skill with external quota-routing or account-switch tooling when automatic credential failover is required.
- Do not leave the next session guessing which project, file, or command comes first.
- Do not bury critical state in long prose. Prefer compact bullets with exact paths and commands.
- Do not overwrite a user's preferred handoff style if it already captures the required information. Normalize only when clarity is missing.
- Use `SESSION_LOG.md` only for large chronological histories. Keep `HANDOFF.md` summary-first.

## Resources

- Read [references/handoff-template.md](references/handoff-template.md) when drafting or repairing a handoff.
- Run `scripts/codex_manager.py snapshot` for a one-command handoff refresh.
- Run `scripts/codex_manager.py watch-cliproxy` when using `CLIProxyAPI` and wanting automatic handoff refresh on quota-triggered account failover.
- Run `scripts/codex_manager.py manage-cliproxy` when you want an actual account switch manager that promotes the next healthy auth by priority.
- Run `scripts/validate_handoff.py` to catch missing handoff sections before ending a session.
