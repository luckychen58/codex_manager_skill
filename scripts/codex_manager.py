#!/usr/bin/env python3
"""Codex session continuity helpers for handoff snapshots and quota-triggered saves."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HANDOFF_ENCODING = "utf-8-sig"


SECTION_ALIASES = {
    "project": {
        "current project",
        "project",
        "current workspace",
        "当前在做的项目",
        "当前项目",
    },
    "objective": {
        "objective",
        "goal",
        "project objective",
        "项目目标",
        "当前目标",
    },
    "status": {
        "current status",
        "status",
        "changes completed",
        "implementation status",
        "core implementation status",
        "核心实现状态",
        "当前状态",
        "最近完成",
        "已完成改动",
    },
    "key_files": {
        "key files",
        "files",
        "关键文件",
    },
    "verification": {
        "verification",
        "checks",
        "validation",
        "已做过的验证",
        "验证",
    },
    "risks": {
        "open issues or risks",
        "open issues",
        "risks",
        "notes",
        "需要注意的点",
        "风险",
        "注意事项",
    },
    "next_steps": {
        "next steps",
        "suggested next steps",
        "如果要继续做，建议下一步",
        "下一步",
        "建议下一步",
    },
    "resume": {
        "resume command",
        "resume",
        "how to continue after switching accounts",
        "换账号后怎么继续",
        "恢复命令",
        "继续方式",
    },
}

DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
}

QUOTA_KEYWORDS = (
    "quota",
    "rate limit",
    "too many requests",
    "insufficient",
    "429",
    "cooldown",
    "exhaust",
)


def normalize_heading(text: str) -> str:
    text = text.strip().strip("`").strip(":")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def parse_sections(content: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for raw_line in content.splitlines():
        match = re.match(r"^##+\s+(.*\S)\s*$", raw_line)
        if match:
            current_heading = normalize_heading(match.group(1))
            sections.setdefault(current_heading, [])
            continue

        if current_heading is not None:
            sections[current_heading].append(raw_line.rstrip())

    result: dict[str, str] = {}
    for heading, lines in sections.items():
        block = "\n".join(lines).strip()
        if block:
            result[heading] = block
    return result


def canonical_section(heading: str) -> str | None:
    for key, aliases in SECTION_ALIASES.items():
        if heading in aliases:
            return key
    return None


def load_existing_sections(handoff_path: Path) -> dict[str, str]:
    if not handoff_path.is_file():
        return {}
    content = handoff_path.read_text(encoding=HANDOFF_ENCODING)
    parsed = parse_sections(content)
    existing: dict[str, str] = {}
    for heading, block in parsed.items():
        key = canonical_section(heading)
        if key and block and key not in existing:
            existing[key] = block
    return existing


def run_command(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def detect_git_root(project_dir: Path) -> Path | None:
    code, output = run_command(["git", "rev-parse", "--show-toplevel"], project_dir)
    if code != 0 or not output:
        return None
    return Path(output.splitlines()[-1]).resolve()


def git_branch(project_dir: Path) -> str | None:
    code, output = run_command(["git", "branch", "--show-current"], project_dir)
    if code != 0 or not output:
        return None
    return output.splitlines()[-1].strip() or None


def git_status(project_dir: Path, max_lines: int) -> list[str]:
    code, output = run_command(["git", "status", "--short", "--branch"], project_dir)
    if code != 0 or not output:
        return []
    lines = output.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(output.splitlines()) - max_lines} more lines)"]
    return lines


def git_changed_files(project_dir: Path) -> list[str]:
    code, output = run_command(["git", "status", "--short"], project_dir)
    if code != 0 or not output:
        return []
    files: list[str] = []
    for line in output.splitlines():
        item = line[3:].strip()
        if item:
            files.append(item)
    return files


def recent_files(project_dir: Path, limit: int) -> list[Path]:
    files: list[Path] = []
    for root, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORES]
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.name.startswith(".") and file_path.name not in {"HANDOFF.md", "SESSION_LOG.md"}:
                continue
            try:
                if not file_path.is_file():
                    continue
                files.append(file_path)
            except OSError:
                continue

    files.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)
    return files[:limit]


def markdown_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def markdown_numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def combine_blocks(*blocks: str) -> str:
    cleaned = [block.strip() for block in blocks if block and block.strip()]
    return "\n\n".join(cleaned)


def render_code_block(lines: list[str]) -> str:
    if not lines:
        return ""
    return "```text\n" + "\n".join(lines) + "\n```"


def default_resume_command(handoff_path: Path) -> str:
    return (
        f"`Continue based on {handoff_path}; treat it as the current HANDOFF.md and resume "
        "the active development task.`"
    )


def normalize_resume_command(existing_resume: str | None, handoff_path: Path) -> str:
    if existing_resume:
        lowered = existing_resume.lower()
        if "handoff.md" in lowered:
            return existing_resume
    return default_resume_command(handoff_path)


def snapshot_now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def build_snapshot(
    workspace: Path,
    project_dir: Path,
    handoff_path: Path,
    project_name: str | None,
    objective: str | None,
    artifact: str | None,
    key_files: list[str],
    next_steps: list[str],
    risks: list[str],
    status_lines: list[str],
    trigger_note: str | None,
    max_recent_files: int,
    max_git_lines: int,
) -> str:
    existing = load_existing_sections(handoff_path)
    git_root = detect_git_root(project_dir)
    git_dir = git_root or project_dir
    branch = git_branch(git_dir)
    status_output = git_status(git_dir, max_git_lines)
    changed_files = git_changed_files(git_dir)
    recent = recent_files(project_dir, max_recent_files)
    timestamp = snapshot_now()

    effective_project_name = project_name or project_dir.name
    current_project_items = [
        f"Workspace: `{workspace}`",
        f"Project directory: `{project_dir}`",
        f"Project name: `{effective_project_name}`",
        f"Snapshot updated: `{timestamp}`",
    ]
    if artifact:
        current_project_items.append(f"Main artifact or output: `{artifact}`")
    if git_root:
        current_project_items.append(f"Git root: `{git_root}`")

    effective_objective = objective or existing.get("objective") or "- Confirm the active objective before continuing."

    if status_lines:
        effective_status = markdown_bullets(status_lines)
    elif "status" in existing:
        effective_status = existing["status"]
    else:
        auto_status = []
        if branch:
            auto_status.append(f"Active branch: `{branch}`")
        auto_status.append(f"Working tree changes detected: `{len(changed_files)}`")
        if changed_files:
            auto_status.append("Top changed files: " + ", ".join(f"`{item}`" for item in changed_files[:5]))
        if trigger_note:
            auto_status.append(f"Most recent trigger: {trigger_note}")
        effective_status = markdown_bullets(auto_status)

    if key_files:
        effective_key_files = markdown_bullets([f"`{Path(item).resolve()}`" if Path(item).exists() else f"`{item}`" for item in key_files])
    elif "key_files" in existing:
        effective_key_files = existing["key_files"]
    else:
        auto_files = []
        for item in recent:
            auto_files.append(f"`{item.resolve()}`: recently modified")
        effective_key_files = markdown_bullets(auto_files) if auto_files else "- Add key files before switching accounts."

    verification_auto = [
        f"Refreshed handoff snapshot at `{timestamp}`.",
    ]
    if branch:
        verification_auto.append(f"Git branch at snapshot time: `{branch}`.")
    verification_auto.append(f"Changed files detected: `{len(changed_files)}`.")
    if trigger_note:
        verification_auto.append(f"Snapshot trigger: {trigger_note}.")
    effective_verification = combine_blocks(existing.get("verification", ""), markdown_bullets(verification_auto))

    if risks:
        effective_risks = markdown_bullets(risks)
    else:
        effective_risks = existing.get("risks", "- Reconfirm the objective and next action if the project has moved since this snapshot.")

    if next_steps:
        effective_next_steps = markdown_numbered(next_steps)
    else:
        effective_next_steps = existing.get(
            "next_steps",
            markdown_numbered(
                [
                    f"Read `{handoff_path}` first.",
                    "Inspect the changed files and recent files listed below.",
                    "Continue from the highest-priority unfinished development task.",
                ]
            ),
        )

    effective_resume = normalize_resume_command(existing.get("resume"), handoff_path)

    snapshot_items = [
        f"Watched project directory: `{project_dir}`",
        f"Recent file sample size: `{len(recent)}`",
    ]
    if trigger_note:
        snapshot_items.append(f"Trigger source: {trigger_note}")
    snapshot_block = markdown_bullets(snapshot_items)
    if status_output:
        snapshot_block = combine_blocks(snapshot_block, "Git status:", render_code_block(status_output))
    if recent:
        snapshot_block = combine_blocks(
            snapshot_block,
            "Recently modified files:",
            markdown_bullets([f"`{item.resolve()}`" for item in recent]),
        )

    parts = [
        "# Handoff",
        "",
        "## Current Project",
        markdown_bullets(current_project_items),
        "",
        "## Objective",
        effective_objective,
        "",
        "## Current Status",
        effective_status,
        "",
        "## Key Files",
        effective_key_files,
        "",
        "## Verification",
        effective_verification,
        "",
        "## Auto Snapshot",
        snapshot_block,
        "",
        "## Open Issues or Risks",
        effective_risks,
        "",
        "## Next Steps",
        effective_next_steps,
        "",
        "## Resume Command",
        effective_resume,
        "",
    ]
    return "\n".join(parts)


def write_snapshot(args: argparse.Namespace, trigger_note: str | None = None) -> Path:
    workspace = Path(args.workspace).expanduser().resolve()
    project_dir = Path(args.project or args.workspace).expanduser().resolve()
    handoff_path = Path(args.handoff or (workspace / "HANDOFF.md")).expanduser().resolve()

    handoff_text = build_snapshot(
        workspace=workspace,
        project_dir=project_dir,
        handoff_path=handoff_path,
        project_name=args.project_name,
        objective=args.objective,
        artifact=args.artifact,
        key_files=args.key_file or [],
        next_steps=args.next_step or [],
        risks=args.risk or [],
        status_lines=args.status_line or [],
        trigger_note=trigger_note,
        max_recent_files=args.max_recent_files,
        max_git_lines=args.max_git_lines,
    )

    if args.dry_run:
        print(handoff_text)
    else:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(handoff_text, encoding=HANDOFF_ENCODING)
        print(f"Updated handoff: {handoff_path}")
        print(default_resume_command(handoff_path))
    return handoff_path


def management_headers(management_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if management_key:
        headers["X-Management-Key"] = management_key
    return headers


def get_management_key(args: argparse.Namespace) -> str | None:
    if args.management_key:
        return args.management_key
    if args.management_key_env:
        return os.environ.get(args.management_key_env)
    return os.environ.get("CLIPROXY_MANAGEMENT_KEY") or os.environ.get("MANAGEMENT_PASSWORD")


def fetch_auth_files(base_url: str, management_key: str | None) -> list[dict]:
    payload = management_request(base_url, management_key, "/v0/management/auth-files")
    files = payload.get("files", [])
    if not isinstance(files, list):
        raise ValueError("management response did not contain a files list")
    return [item for item in files if isinstance(item, dict)]


def management_request(
    base_url: str,
    management_key: str | None,
    path: str,
    method: str = "GET",
    payload: dict | None = None,
    expect_json: bool = True,
) -> dict | bytes:
    endpoint = base_url.rstrip("/") + path
    headers = management_headers(management_key)
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(endpoint, headers=headers, data=data, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read()
    if not expect_json:
        return body
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def download_auth_file(base_url: str, management_key: str | None, name: str) -> dict:
    query = urllib.parse.urlencode({"name": name})
    raw = management_request(
        base_url,
        management_key,
        f"/v0/management/auth-files/download?{query}",
        expect_json=False,
    )
    if not isinstance(raw, (bytes, bytearray)):
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def patch_auth_priority(base_url: str, management_key: str | None, name: str, priority: int) -> None:
    management_request(
        base_url,
        management_key,
        "/v0/management/auth-files/fields",
        method="PATCH",
        payload={"name": name, "priority": int(priority)},
    )


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def candidate_priority_from_payload(payload: dict) -> int:
    for container_name in ("metadata", "attributes"):
        container = payload.get(container_name)
        if isinstance(container, dict):
            value = container.get("priority")
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass
    value = payload.get("priority")
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    return 0


def candidate_display_name(candidate: dict) -> str:
    for key in ("email", "account", "name", "id"):
        value = str(candidate.get(key) or "").strip()
        if value:
            return value
    return "unknown"


def candidate_sort_key(candidate: dict) -> tuple:
    return (-int(candidate.get("priority") or 0), candidate_display_name(candidate).lower())


def enrich_auth_files(args: argparse.Namespace, auth_files: list[dict], provider: str, management_key: str | None) -> list[dict]:
    candidates: list[dict] = []
    for auth_file in auth_files:
        provider_name = str(auth_file.get("provider") or auth_file.get("type") or "").strip().lower()
        if provider_name != provider:
            continue
        candidate = dict(auth_file)
        name = str(candidate.get("name") or candidate.get("id") or "").strip()
        candidate["provider"] = provider_name
        candidate["name"] = name
        candidate["priority"] = 0
        if name.endswith(".json"):
            downloaded = download_auth_file(args.base_url, management_key, name)
            candidate["priority"] = candidate_priority_from_payload(downloaded)
        candidates.append(candidate)
    candidates.sort(key=candidate_sort_key)
    return candidates


def candidate_problem_reasons(candidate: dict, now: datetime | None = None) -> list[str]:
    reasons: list[str] = []
    if bool(candidate.get("disabled")):
        reasons.append("disabled")

    status = str(candidate.get("status") or "").strip().lower()
    if status in {"disabled", "pending", "refreshing"}:
        reasons.append(f"status={status}")
    elif status == "error":
        reasons.append("status=error")

    if bool(candidate.get("unavailable")):
        reasons.append("unavailable")

    next_retry_after = candidate.get("next_retry_after")
    parsed_retry = parse_timestamp(next_retry_after)
    compare_now = now or datetime.now().astimezone()
    if parsed_retry and parsed_retry > compare_now:
        reasons.append(f"next_retry_after={next_retry_after}")

    status_message = str(candidate.get("status_message") or "").strip()
    lowered_message = status_message.lower()
    if status_message and any(keyword in lowered_message for keyword in QUOTA_KEYWORDS):
        reasons.append(f"status_message={status_message}")

    return reasons


def candidate_is_healthy(candidate: dict, now: datetime | None = None) -> bool:
    return len(candidate_problem_reasons(candidate, now=now)) == 0


def resolve_state_path(args: argparse.Namespace, provider: str) -> Path:
    if args.state_file:
        return Path(args.state_file).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    return workspace / ".codex-manager" / f"switch-state-{provider}.json"


def load_switch_state(state_path: Path, provider: str) -> dict:
    if state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
    else:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    loaded.setdefault("provider", provider)
    loaded.setdefault("selected_name", "")
    loaded.setdefault("selected_id", "")
    loaded.setdefault("managed", {})
    loaded.setdefault("history", [])
    loaded.setdefault("last_unavailable_signature", "")
    loaded.setdefault("last_switch_reason", "")
    return loaded


def save_switch_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")


def find_candidate(candidates: list[dict], name: str) -> dict | None:
    for candidate in candidates:
        if str(candidate.get("name") or "").strip() == name:
            return candidate
    return None


def select_next_candidate(candidates: list[dict], current_name: str) -> dict | None:
    healthy = [candidate for candidate in candidates if candidate_is_healthy(candidate)]
    if not healthy:
        return None
    if not current_name:
        return healthy[0]

    current_index = None
    for index, candidate in enumerate(candidates):
        if str(candidate.get("name") or "").strip() == current_name:
            current_index = index
            break

    if current_index is None:
        return healthy[0]

    for offset in range(1, len(candidates) + 1):
        candidate = candidates[(current_index + offset) % len(candidates)]
        if candidate_is_healthy(candidate):
            return candidate
    return None


def ensure_managed_record(state: dict, candidate: dict) -> dict:
    managed = state.setdefault("managed", {})
    name = str(candidate.get("name") or "").strip()
    record = managed.get(name)
    if not isinstance(record, dict):
        record = {
            "original_priority": int(candidate.get("priority") or 0),
            "id": str(candidate.get("id") or ""),
            "provider": str(candidate.get("provider") or ""),
            "email": str(candidate.get("email") or ""),
        }
        managed[name] = record
    return record


def append_switch_history(state: dict, entry: dict) -> None:
    history = state.setdefault("history", [])
    history.append(entry)
    if len(history) > 20:
        del history[:-20]


def apply_selected_candidate(
    args: argparse.Namespace,
    management_key: str,
    state: dict,
    current_candidate: dict | None,
    selected_candidate: dict,
    reason: str,
) -> str:
    selected_name = str(selected_candidate.get("name") or "").strip()
    previous_name = str(state.get("selected_name") or "").strip()
    ensure_managed_record(state, selected_candidate)

    if previous_name and previous_name != selected_name:
        previous_record = state.get("managed", {}).get(previous_name)
        if isinstance(previous_record, dict):
            restore_priority = int(previous_record.get("original_priority", 0) or 0)
            patch_auth_priority(args.base_url, management_key, previous_name, restore_priority)

    target_priority = int(args.selected_priority)
    if int(selected_candidate.get("priority") or 0) != target_priority:
        patch_auth_priority(args.base_url, management_key, selected_name, target_priority)
        selected_candidate["priority"] = target_priority

    switched_at = snapshot_now()
    state["selected_name"] = selected_name
    state["selected_id"] = str(selected_candidate.get("id") or "")
    state["last_switch_reason"] = reason
    state["last_unavailable_signature"] = ""
    append_switch_history(
        state,
        {
            "at": switched_at,
            "from": previous_name,
            "to": selected_name,
            "reason": reason,
        },
    )

    previous_label = candidate_display_name(current_candidate) if current_candidate else "none"
    selected_label = candidate_display_name(selected_candidate)
    return f"Switched {args.provider_name} from {previous_label} to {selected_label} because {reason}"


def maybe_snapshot_on_unavailable(args: argparse.Namespace, state: dict, reason: str, signature: str) -> None:
    if state.get("last_unavailable_signature") == signature:
        return
    state["last_unavailable_signature"] = signature
    if args.snapshot_on_unavailable:
        write_snapshot(args, trigger_note=reason)


def manage_cliproxy(args: argparse.Namespace) -> int:
    provider = args.provider_name.strip().lower()
    management_key = get_management_key(args)
    if not management_key:
        print(
            "ERROR: Missing management key. Set CLIPROXY_MANAGEMENT_KEY or pass --management-key.",
            file=sys.stderr,
        )
        return 1

    state_path = resolve_state_path(args, provider)
    state = load_switch_state(state_path, provider)
    print(f"Managing CLIProxyAPI provider '{provider}' via {args.base_url.rstrip('/')}")
    print(f"Switch state file: {state_path}")

    while True:
        try:
            auth_files = fetch_auth_files(args.base_url, management_key)
            candidates = enrich_auth_files(args, auth_files, provider, management_key)
            if not candidates:
                print(f"No auth files found for provider '{provider}'.", file=sys.stderr)
                if args.once:
                    return 1
                time.sleep(args.poll_seconds)
                continue

            current_name = str(state.get("selected_name") or "").strip()
            current_candidate = find_candidate(candidates, current_name) if current_name else None

            if current_candidate and candidate_is_healthy(current_candidate):
                ensure_managed_record(state, current_candidate)
                target_priority = int(args.selected_priority)
                if int(current_candidate.get("priority") or 0) != target_priority:
                    patch_auth_priority(args.base_url, management_key, current_name, target_priority)
                    current_candidate["priority"] = target_priority
                    print(f"Pinned current auth '{candidate_display_name(current_candidate)}' to priority {target_priority}.")
                save_switch_state(state_path, state)
                if args.once:
                    print(f"Current auth remains healthy: {candidate_display_name(current_candidate)}")
                    return 0
                time.sleep(args.poll_seconds)
                continue

            reason = "initial selection"
            if current_candidate:
                problems = candidate_problem_reasons(current_candidate)
                if problems:
                    reason = "; ".join(problems)
            elif current_name:
                reason = f"previously selected auth '{current_name}' is no longer present"

            next_candidate = select_next_candidate(candidates, current_name)
            if next_candidate is None:
                unavailable_reasons = []
                for candidate in candidates:
                    candidate_reason = candidate_problem_reasons(candidate)
                    unavailable_reasons.append(
                        f"{candidate_display_name(candidate)} -> {', '.join(candidate_reason) if candidate_reason else 'not eligible'}"
                    )
                message = f"No healthy {provider} auth available. " + " | ".join(unavailable_reasons)
                signature = json.dumps(unavailable_reasons, ensure_ascii=True)
                maybe_snapshot_on_unavailable(args, state, message, signature)
                save_switch_state(state_path, state)
                print(message, file=sys.stderr)
                if args.once:
                    return 1
                time.sleep(args.poll_seconds)
                continue

            switch_message = apply_selected_candidate(args, management_key, state, current_candidate, next_candidate, reason)
            print(switch_message)
            if args.snapshot_on_switch:
                write_snapshot(args, trigger_note=switch_message)
            save_switch_state(state_path, state)
            if args.once:
                return 0

        except urllib.error.HTTPError as exc:
            print(f"Management API error: HTTP {exc.code}", file=sys.stderr)
            if args.once:
                return 1
        except urllib.error.URLError as exc:
            print(f"Management API connection error: {exc.reason}", file=sys.stderr)
            if args.once:
                return 1
        except KeyboardInterrupt:
            print("Stopped switch manager.")
            return 0
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            print(f"Switch manager error: {exc}", file=sys.stderr)
            if args.once:
                return 1

        time.sleep(args.poll_seconds)


def auth_trigger_reason(auth_file: dict, providers: set[str]) -> str | None:
    provider = str(auth_file.get("provider") or auth_file.get("type") or "").strip().lower()
    if providers and provider not in providers:
        return None

    status = str(auth_file.get("status") or "").strip().lower()
    status_message = str(auth_file.get("status_message") or "").strip()
    message_lower = status_message.lower()
    unavailable = bool(auth_file.get("unavailable"))
    next_retry_after = auth_file.get("next_retry_after")

    reasons: list[str] = []
    if unavailable:
        reasons.append("unavailable")
    if status == "error":
        reasons.append("status=error")
    if next_retry_after:
        reasons.append(f"next_retry_after={next_retry_after}")
    if any(keyword in message_lower for keyword in QUOTA_KEYWORDS):
        reasons.append(f"status_message={status_message}")

    if not reasons:
        return None

    name = str(auth_file.get("name") or auth_file.get("id") or provider or "auth")
    return f"{provider}:{name} -> " + "; ".join(reasons)


def watch_cliproxy(args: argparse.Namespace) -> int:
    providers = {item.strip().lower() for item in (args.provider or ["codex"]) if item.strip()}
    management_key = get_management_key(args)
    if not management_key:
        print(
            "ERROR: Missing management key. Set CLIPROXY_MANAGEMENT_KEY or pass --management-key.",
            file=sys.stderr,
        )
        return 1

    last_signature: str | None = None
    last_trigger_at = 0.0
    print(f"Watching {args.base_url.rstrip('/')}/v0/management/auth-files for providers: {', '.join(sorted(providers))}")

    while True:
        try:
            auth_files = fetch_auth_files(args.base_url, management_key)
            reasons = []
            for auth_file in auth_files:
                reason = auth_trigger_reason(auth_file, providers)
                if reason:
                    reasons.append(reason)

            if reasons:
                signature = json.dumps(sorted(reasons), ensure_ascii=True)
                now = time.time()
                if signature != last_signature or now - last_trigger_at >= args.cooldown_seconds:
                    trigger_note = "CLIProxyAPI quota watcher: " + " | ".join(reasons)
                    write_snapshot(args, trigger_note=trigger_note)
                    last_signature = signature
                    last_trigger_at = now
                    if args.once:
                        return 0
                else:
                    print("Trigger detected but still inside cooldown window; skipping duplicate snapshot.")
            else:
                last_signature = None

        except urllib.error.HTTPError as exc:
            print(f"Management API error: HTTP {exc.code}", file=sys.stderr)
            if args.once:
                return 1
        except urllib.error.URLError as exc:
            print(f"Management API connection error: {exc.reason}", file=sys.stderr)
            if args.once:
                return 1
        except KeyboardInterrupt:
            print("Stopped quota watcher.")
            return 0
        except Exception as exc:  # pragma: no cover - defensive logging for runtime use
            print(f"Watcher error: {exc}", file=sys.stderr)
            if args.once:
                return 1

        time.sleep(args.poll_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex session continuity helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_snapshot_args(target: argparse.ArgumentParser) -> None:
        target.add_argument("--workspace", required=True, help="Workspace root directory")
        target.add_argument("--project", help="Active project directory; defaults to workspace")
        target.add_argument("--handoff", help="Output handoff path; defaults to <workspace>/HANDOFF.md")
        target.add_argument("--project-name", help="Optional project label")
        target.add_argument("--objective", help="Current objective summary")
        target.add_argument("--artifact", help="Main artifact or output path")
        target.add_argument("--key-file", action="append", help="Key file path (repeatable)")
        target.add_argument("--next-step", action="append", help="Next step item (repeatable)")
        target.add_argument("--risk", action="append", help="Risk or blocker item (repeatable)")
        target.add_argument("--status-line", action="append", help="Current status line (repeatable)")
        target.add_argument("--max-recent-files", type=int, default=8, help="Max recent files to include")
        target.add_argument("--max-git-lines", type=int, default=20, help="Max git status lines to embed")
        target.add_argument("--dry-run", action="store_true", help="Print the handoff without writing it")

    snapshot_parser = subparsers.add_parser("snapshot", help="Refresh HANDOFF.md for the active workspace")
    add_common_snapshot_args(snapshot_parser)

    watch_parser = subparsers.add_parser("watch-cliproxy", help="Watch CLIProxyAPI auth status and snapshot on quota-like failures")
    add_common_snapshot_args(watch_parser)
    watch_parser.add_argument("--base-url", default="http://127.0.0.1:8317", help="CLIProxyAPI base URL")
    watch_parser.add_argument("--management-key", help="CLIProxyAPI management key")
    watch_parser.add_argument(
        "--management-key-env",
        default="CLIPROXY_MANAGEMENT_KEY",
        help="Environment variable that stores the management key",
    )
    watch_parser.add_argument("--provider", action="append", help="Provider to watch, default: codex")
    watch_parser.add_argument("--poll-seconds", type=int, default=20, help="Polling interval in seconds")
    watch_parser.add_argument("--cooldown-seconds", type=int, default=300, help="Minimum seconds between duplicate snapshots")
    watch_parser.add_argument("--once", action="store_true", help="Exit after the first trigger or first error")

    manage_parser = subparsers.add_parser(
        "manage-cliproxy",
        help="Promote one CLIProxyAPI auth as the active account and switch to the next healthy account when needed",
    )
    add_common_snapshot_args(manage_parser)
    manage_parser.add_argument("--base-url", default="http://127.0.0.1:8317", help="CLIProxyAPI base URL")
    manage_parser.add_argument("--management-key", help="CLIProxyAPI management key")
    manage_parser.add_argument(
        "--management-key-env",
        default="CLIPROXY_MANAGEMENT_KEY",
        help="Environment variable that stores the management key",
    )
    manage_parser.add_argument(
        "--provider-name",
        default="codex",
        help="Provider to manage, default: codex",
    )
    manage_parser.add_argument("--selected-priority", type=int, default=1000, help="Priority assigned to the active auth")
    manage_parser.add_argument("--state-file", help="Persistent manager state path")
    manage_parser.add_argument("--poll-seconds", type=int, default=20, help="Polling interval in seconds")
    manage_parser.add_argument(
        "--snapshot-on-switch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh HANDOFF.md whenever the active auth changes",
    )
    manage_parser.add_argument(
        "--snapshot-on-unavailable",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh HANDOFF.md when all managed auths become unavailable",
    )
    manage_parser.add_argument("--once", action="store_true", help="Evaluate once, switch if needed, then exit")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "snapshot":
        write_snapshot(args)
        return 0
    if args.command == "watch-cliproxy":
        return watch_cliproxy(args)
    if args.command == "manage-cliproxy":
        return manage_cliproxy(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
