#!/usr/bin/env python3
"""Validate whether a HANDOFF.md file is detailed enough for session recovery."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_GROUPS = {
    "project": {
        "current project",
        "project",
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


def normalize_heading(text: str) -> str:
    text = text.strip().strip("`").strip(":")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def parse_sections(content: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in content.splitlines():
        match = re.match(r"^##+\s+(.*\S)\s*$", line)
        if match:
            current_heading = normalize_heading(match.group(1))
            sections.setdefault(current_heading, [])
            continue

        if current_heading is not None:
            sections[current_heading].append(line)

    return sections


def find_group(sections: dict[str, list[str]], aliases: set[str]) -> tuple[str | None, list[str] | None]:
    for heading, lines in sections.items():
        if heading in aliases:
            return heading, lines
    return None, None


def has_meaningful_content(lines: list[str] | None) -> bool:
    if not lines:
        return False
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in {"-", "*"}:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a HANDOFF.md file.")
    parser.add_argument("handoff", help="Path to the handoff markdown file")
    args = parser.parse_args()

    handoff_path = Path(args.handoff).expanduser().resolve()
    if not handoff_path.is_file():
        print(f"ERROR: File not found: {handoff_path}")
        return 1

    content = handoff_path.read_text(encoding="utf-8-sig")
    sections = parse_sections(content)

    errors: list[str] = []
    warnings: list[str] = []

    for group_name, aliases in REQUIRED_GROUPS.items():
        heading, lines = find_group(sections, aliases)
        if heading is None:
            errors.append(f"Missing required section group: {group_name}")
            continue
        if not has_meaningful_content(lines):
            errors.append(f"Section is empty: {heading}")

    project_heading, project_lines = find_group(sections, REQUIRED_GROUPS["project"])
    if project_heading and has_meaningful_content(project_lines):
        joined = "\n".join(project_lines)
        if not re.search(r"[A-Za-z]:\\", joined):
            warnings.append("Project section does not appear to contain a Windows absolute path.")

    resume_heading, resume_lines = find_group(sections, REQUIRED_GROUPS["resume"])
    if resume_heading and has_meaningful_content(resume_lines):
        resume_text = "\n".join(resume_lines)
        if "HANDOFF.md" not in resume_text and "handoff.md" not in resume_text.lower():
            warnings.append("Resume section does not mention HANDOFF.md explicitly.")

    if errors:
        print(f"INVALID: {handoff_path}")
        for item in errors:
            print(f"- {item}")
        if warnings:
            print("Warnings:")
            for item in warnings:
                print(f"- {item}")
        return 1

    print(f"VALID: {handoff_path}")
    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
