> Status: Draft (wizard-generated equivalent — manually seeded for jig itself)
>
> Changes to this file require explicit human approval. Do not modify via agent without confirmation.

# Conventions: jig

## Skill authoring

**Rule:** Every skill description follows: `<verb-led summary>. Use when <specific triggers>. Do not use for <common false positives>.`
**Why:** The description is a trigger, not a summary. Vague descriptions don't fire. Overly broad descriptions fire on irrelevant prompts.
**How to apply:** Write the description, then read it aloud. Does it start with a verb? Is the trigger clause specific enough to distinguish from 3 similar prompts you might type? Is the negative clause present?

**Rule:** One skill, one job. No mega-skills.
**Why:** Splitting improves triggering accuracy. Kitchen-sink skills are the most common failure mode (ECC).
**How to apply:** If a skill handles commits AND PRs AND branch naming AND changelogs, split it.

**Rule:** Every skill has a `## Gotchas` section.
**Why:** Gotchas accumulate failure points over time. They're the highest-signal content in a skill file.
**How to apply:** Add gotchas as you discover them, not upfront. A skill with no gotchas is either perfect or hasn't been used yet.

**Rule:** Stubs use `disable-model-invocation: true`.
**Why:** An unimplemented skill that auto-triggers is worse than no skill — it interrupts the user with a DRAFT warning.
**How to apply:** All skills without a corresponding implemented spec use `disable-model-invocation: true`.

## Hook authoring

**Rule:** Hooks use `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.sh` — never bare names.
**Why:** `bin/` PATH injection is Bash-tool only. Hook commands need the full path.
**How to apply:** Every hook command in `hooks.json` must start with `bash ${CLAUDE_PLUGIN_ROOT}/`.

**Rule:** Hook scripts use Python 3 for JSON parsing — never `jq`.
**Why:** `jq` is not installed by default on macOS. Python 3 is reliable everywhere.
**How to apply:** Use `python3 - <<'EOF' ... EOF` in hook scripts for JSON work.

**Rule:** Non-blocking hooks exit 0 with JSON stdout. Blocking hooks exit 2 with stderr message.
**Why:** Exit code 2 is the only blocking mechanism. Anything else either fails silently or errors noisily.
**How to apply:** `{ "continue": true, "additionalContext": "..." }` for informational hooks; `echo "reason" >&2 && exit 2` for gates.

**Rule:** All hooks are non-blocking in the starting move. Gates are introduced per spec.
**Why:** A premature block with no escape hatch is worse than no block.
**How to apply:** Wire the gate hooks; implement their blocking logic only when the corresponding spec slice is done.

## Agent authoring

**Rule:** Reviewer agent has read-only tools: `Read`, `Glob`, `Grep` only.
**Why:** Reviewers cannot be trusted not to modify the work they're reviewing.
**How to apply:** The `tools` list in `agents/reviewer.md` must never include `Write` or `Edit`.

**Rule:** Reviewer system prompt must include: "You are seeing this work for the first time."
**Why:** Breaks the implicit assumption of shared context.
**How to apply:** First paragraph of every reviewer invocation prompt.

## Document conventions

**Rule:** Every wizard-generated doc carries `Status: Draft (wizard-generated)` at the top.
**Why:** Distinguishes generated stubs from deliberate content.
**How to apply:** scaffold-init adds this marker. It flips to `Stable` after 3-5 reconciled specs via a `scaffold-stable` ADR.

**Rule:** Deferred decisions use the format: `> **Deferred — <reason>. Will be decided in the first <X>-touching spec.**`
**Why:** Explicit deferral is honest. Silent gaps get forgotten.
**How to apply:** Any time scaffold-init doesn't have enough signal to fill a section.

**Rule:** ADRs are immutable after acceptance.
**Why:** Editing history destroys the audit trail that makes ADRs valuable.
**How to apply:** New decision → new ADR with `Supersedes: ADR-NNNN`. Never edit an accepted ADR.
