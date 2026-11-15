---
name: conventional-commits
description: Draft, check, or use Git commit messages following Conventional Commits 1.0.0. Use whenever the user asks for a commit message or a commit. Never create, amend, or push a commit without explicit authorization.
---

# Conventional Commits

This skill is self-contained. Apply the rules below directly; do not visit external websites to determine the commit message format.

## Message structure

```text
<type>[optional (scope)][optional !]: <description>

[optional body]

[optional footer(s)]
```

The subject starts with a **type**, followed by an optional **scope** in parentheses, an optional **`!`** for breaking changes, a **colon and single space**, and a **nonempty description**. Examples: `fix: correct timeout` and `feat(auth)!: replace login protocol`.

### Rules from Conventional Commits 1.0.0 (paraphrased)

1. **Type:** A type is required. Use `feat` for a new feature and `fix` for a bug fix. Other nouns are allowed as types; common choices include `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `style`, and `revert`. These additional types are conventions, not a mandated list.
2. **Scope:** Optional; place a noun identifying the affected area inside parentheses immediately after the type, e.g. `fix(parser): ...`.
3. **Description:** Required immediately after `: `. Summarize the change briefly.
4. **Body:** Optional; separate it from the subject with one blank line. It may contain multiple paragraphs to explain context or motivation.
5. **Footers:** Optional; separate them from the preceding text with one blank line. Use `Token: value` or `Token #value`. Multiword tokens use hyphens, e.g. `Reviewed-by: Alex`; footer values may span multiple lines until another valid footer starts.
6. **Breaking changes:** Mark an incompatible change with `!` immediately before the colon, a `BREAKING CHANGE: explanation` footer, or both. `BREAKING-CHANGE: explanation` is a valid equivalent footer token. If using `!` without a footer, the subject must describe the incompatible change. Breaking changes may accompany any type.
7. **Capitalization:** Treat ordinary type and footer tokens without case sensitivity when interpreting messages; the special `BREAKING CHANGE` marker must be uppercase. For consistency, this repository's suggested types are lowercase.
8. **Semantic versioning implications:** `fix` corresponds to PATCH; `feat` corresponds to MINOR; any breaking change corresponds to MAJOR. Other types do not imply a release bump on their own.

## House style (preferences, not specification requirements)

- Write commit messages in English.
- Write a short, imperative subject without a trailing period.
- Include a scope only if it adds useful context; never invent a scope.
- Put the *reason* or user-facing impact in the body when the subject is not enough.
- Keep each commit focused on one logical change. Split unrelated changes when practical.

## Workflow

1. Inspect the actual diff (prefer staged changes when preparing a commit). Do not invent changes or claim to have inspected files you have not read.
2. Identify the main change, choose the correct type and optional scope, and assess whether existing consumers must make incompatible changes.
3. Draft the subject and optional body/footer. Verify the grammar, blank lines, and any breaking-change declaration against the rules above.
4. If asked only to suggest or review a message, **do not run Git commands that modify history**.
5. If explicitly asked to commit, stage only authorized files and make the commit. Do not include unrelated user changes. Never push, amend, or rewrite history unless separately authorized.

## Examples

```text
feat(search): add result filtering
fix(cache): prevent stale reads
docs: clarify installation requirements
refactor(api): simplify request parsing
test(auth): cover expired tokens
```

Breaking change with a subject marker:

```text
feat(config)!: remove legacy options
```

Breaking change with a footer:

```text
feat(api): switch to cursor pagination

Use cursor tokens instead of numeric offsets.

BREAKING CHANGE: Clients must replace the offset parameter with cursor.
```

Non-breaking commit with a trailer:

```text
fix(queue): handle duplicate deliveries

Ignore events that have already been processed.

Refs: #142
```
