# codex-manager

`codex-manager` is a Codex skill for resumable development across long sessions, account switches, and quota interruptions.

It does not preserve live chat history across accounts. Instead, it makes sessions recoverable by keeping project state in `HANDOFF.md` and providing script helpers for snapshotting, validation, and `CLIProxyAPI`-driven account failover.

## What It Solves

- Keep development resumable when a Codex session is interrupted
- Refresh `HANDOFF.md` from the workspace in one command
- Validate that a handoff is complete before switching accounts
- Watch `CLIProxyAPI` and auto-save handoff state on quota-like failures
- Promote the next healthy `codex` auth automatically when the current one becomes unavailable

## Install

Clone this repository into your Codex skills directory:

```powershell
git clone https://github.com/luckychen58/codex_manager_skill.git C:\Users\Administrator\.codex\skills\codex-manager
```

If you already have the folder, pull updates inside it:

```powershell
git -C C:\Users\Administrator\.codex\skills\codex-manager pull
```

## Use In Codex

Ask Codex to use the skill during development:

```text
Use $codex-manager for this project and keep HANDOFF.md updated
```

When you switch to a new account or a new session:

```text
Continue based on C:\path\to\HANDOFF.md
```

## Scripts

Run commands from the skill directory or call the scripts by absolute path.

### 1. Refresh a handoff snapshot

```powershell
python scripts/codex_manager.py snapshot --workspace C:\path\to\workspace --project C:\path\to\project
```

### 2. Validate that the handoff is resumable

```powershell
python scripts/validate_handoff.py C:\path\to\workspace\HANDOFF.md
```

### 3. Watch `CLIProxyAPI` and auto-save when quota-like failures appear

```powershell
$env:CLIPROXY_MANAGEMENT_KEY='your-management-key'
python scripts/codex_manager.py watch-cliproxy --workspace C:\path\to\workspace --project C:\path\to\project
```

### 4. Auto-manage `codex` auth priority and switch to the next healthy account

```powershell
$env:CLIPROXY_MANAGEMENT_KEY='your-management-key'
python scripts/codex_manager.py manage-cliproxy --workspace C:\path\to\workspace --project C:\path\to\project
```

One-shot evaluation is also supported:

```powershell
python scripts/codex_manager.py manage-cliproxy --workspace C:\path\to\workspace --project C:\path\to\project --once
```

## Recommended Workflow

1. Start work with `$codex-manager`.
2. Keep `HANDOFF.md` updated at milestones.
3. Before switching accounts, refresh or validate the handoff.
4. In the new session, resume from `HANDOFF.md`.

## Repository Layout

- `SKILL.md`: the skill behavior and guardrails
- `references/handoff-template.md`: handoff template
- `scripts/codex_manager.py`: snapshot, watch, and account-switch manager
- `scripts/validate_handoff.py`: handoff completeness checker

## Boundary

- This skill improves recoverability, not live chat continuity.
- Automatic account switching depends on `CLIProxyAPI` management access.
- The next session should always re-check the actual workspace before trusting an older handoff.
