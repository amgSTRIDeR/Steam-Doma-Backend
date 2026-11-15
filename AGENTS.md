# Agent Instructions

Work as a careful software engineer. Prefer small, correct, reviewable changes over clever or broad solutions.

## Project context

- Read `PROJECT.md` before substantive work. Treat it as the source of project-specific context; verify claims against the repository when necessary.
- Inspect the relevant code, tests, configuration, and current Git changes before editing. Never assume versions, commands, dependencies, or behavior that you have not verified.
- Follow the project's existing architecture and conventions. Do not introduce new packages, abstractions, or configuration without a concrete need.
- Stop and ask a focused question when missing information could materially affect correctness, security, data, public behavior, or scope. Otherwise make the smallest safe, reversible assumption and state it.

## Scope and safety

- Change only what is necessary for the requested task. Avoid unrelated refactoring, reformatting, renaming, or cleanup.
- Preserve existing user changes. Do not overwrite unrelated edits, remove others' comments, or stage unrelated files.
- Do not use destructive Git commands, rewrite history, force-push, deploy, access production, or perform irreversible operations without explicit authorization.
- Treat vendored, third-party, and generated files as read-only unless the task specifically requires changing them.
- Do not expose secrets or personal data. Never send private repository content to external services without authorization.
- Flag material changes to APIs, schemas, authentication, permissions, infrastructure, or dependencies; request approval before high-impact or irreversible actions.

## Code and documentation

- Prefer simple, readable code and existing patterns. Preserve external behavior and architectural boundaries unless the task requires otherwise.
- Write **code comments only in English**, and only when they explain non-obvious intent, constraints, trade-offs, or hazards. Do not comment on self-explanatory code. Leave unrelated existing comments untouched.
- Write **documentation only in English**, and create or update it only when required by the change. Keep it accurate and concise.
- Remove unused imports or temporary artifacts introduced by your change; avoid unrelated cleanup.
- For bug fixes or behavior changes, add or update focused tests where practical. Use TDD when requested or beneficial, not as a mandatory ritual.

## Verification and reporting

- Discover actual test, lint, type-check, and build commands from `PROJECT.md` and repository configuration. Never invent commands.
- Run relevant checks when feasible. If checks cannot run or fail, report exactly what happened; never claim an unrun check passed.
- Review the final diff for unintended edits, formatting noise, regressions, and leaked information.
- Summarize changes, checks actually run, and unresolved risks or limitations.

## Git commits

- Never create, amend, or push commits unless explicitly requested.
- When preparing, reviewing, or creating a commit message, read and follow `.agents/skills/conventional-commits/SKILL.md`.
- Stage only the intended changes; do not stage the entire working tree by default.
