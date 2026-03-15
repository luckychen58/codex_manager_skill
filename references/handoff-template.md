# Handoff Template

Use this file when creating a new `HANDOFF.md` or repairing a sparse one.
Keep the handoff short and specific. Aim for roughly 40-150 lines.

## Core Rules

- Scope one handoff to one active project.
- Use absolute paths for projects, key files, and output artifacts.
- Record concrete commands and outcomes instead of vague summaries.
- End with the exact resume prompt to use in a fresh session.
- Prefer summary sections. Add chronological notes only if the task is large enough to need a separate log.

## Recommended Headings

- `## Current Project`
- `## Objective`
- `## Current Status`
- `## Key Files`
- `## Verification`
- `## Open Issues or Risks`
- `## Next Steps`
- `## Resume Command`

Common Chinese equivalents such as `当前在做的项目`, `项目目标`, `核心实现状态`, `关键文件`, `已做过的验证`, `需要注意的点`, `建议下一步`, and `换账号后怎么继续` are also fine.

## Starter Template

```md
# Handoff

## Current Project
- Project directory: `C:\path\to\repo`
- Main artifact or output: `...`

## Objective
- ...

## Current Status
- Working:
- Pending:

## Key Files
- `C:\path\to\file.ext`: purpose

## Verification
- Ran `...`: result

## Open Issues or Risks
- ...

## Next Steps
1. ...
2. ...

## Resume Command
`继续根据 C:\path\to\HANDOFF.md 工作`
```

## Resume Checklist

1. Read `HANDOFF.md`.
2. Check current repository or workspace changes.
3. Open the project directory and the key files listed above.
4. Start with item 1 in `Next Steps`.
