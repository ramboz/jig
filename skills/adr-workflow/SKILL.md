---
name: adr-workflow
description: >
  Scaffold, accept, index, and link Architectural Decision Records (ADRs).
  Use when the user says "write an ADR", "record this decision", "resolve
  [deferred item] with an ADR", "supersede ADR-NNNN", or otherwise wants to
  capture a hard-to-reverse decision in `docs/adrs/`. Also use when a
  refinement-todo entry needs to be marked RESOLVED with a link back to the
  ADR. Do NOT use for ad-hoc design discussion that hasn't crystallized into
  a decision yet — wait until the choice is firm.
user-invocable: true
---

> Spec 005 created this skill from scratch. The mechanics live in `adr.py`;
> Claude owns the judgment (what the decision actually says).

## What this skill does

Codifies the ADR lifecycle that ADR-0001 and ADR-0002 were written by hand to
exercise. Four deterministic operations:

- **`new`** — scaffold `docs/adrs/NNNN-<slug>.md` from the template, with
  auto-numbering and a slug-collision check.
- **`accept`** — flip Status from `Proposed (YYYY-MM-DD)` to
  `Accepted (YYYY-MM-DD)`. Atomic write.
- **`index`** — regenerate the `## Index` section of `docs/adrs/README.md`
  from the actual ADR files present. Idempotent.
- **`resolve-todo`** — strike through a `### Decision: ...` heading in
  `docs/refinement-todo.md` and append `**Resolved by:** [ADR-NNNN: ...](...)`.

The script does file mutation deterministically. Claude is responsible for
the prose inside the ADR (Context, Options Considered, Recommended Decision,
Consequences, Open questions).

## How to use

### 1. Author a new ADR

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/adr-workflow/adr.py" new <slug> \
  --title "<Title>"
```

Run from the project root (the script looks for `./docs/adrs/`). The slug is
kebab-case (`my-decision`). `--title` is optional — defaults to the
title-cased slug.

Then Claude fills in Context / Options Considered / Recommended Decision /
Consequences. Keep it tight: one decision per ADR.

### 2. Accept the ADR

Once the prose is settled and the human (or the workflow gate) approves:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/adr-workflow/adr.py" accept <NNNN>
```

This flips `Proposed (date)` to `Accepted (date)`. Refuses if the Status is
already Accepted (ADRs are immutable; supersede instead — see below).

### 3. Regenerate the index

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/adr-workflow/adr.py" index docs/adrs
```

Reads every `NNNN-*.md` (skipping `README.md`) and rewrites only the
`## Index` section of `docs/adrs/README.md`. Everything else in the README
(header, format spec, "When to write" section) is preserved. Re-running on a
current README is a no-op.

### 4. Resolve a deferred decision

If the new ADR resolves a `### Decision: ...` entry in
`docs/refinement-todo.md`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/adr-workflow/adr.py" \
  resolve-todo <NNNN> "<heading fragment>"
```

The fragment is a case-insensitive substring (same lenient style as
`workflow.py`'s slice fragment). The helper:

- wraps the heading line in `~~strikethrough~~`,
- appends ` — RESOLVED YYYY-MM-DD`,
- wraps the first `**Deferred:**` line in strikethrough,
- appends a `**Resolved by:** [ADR-NNNN: ...](adrs/...)` line at the end of
  the section.

Refuses (exit 2) if the fragment is ambiguous, the section is already struck
through, or the ADR hasn't been Accepted yet.

## Immutability rule

**Never edit an Accepted ADR.** The Nygard convention treats ADRs as
historical record — if the decision changes, write a new ADR that supersedes
the old one. The `supersede` subcommand is deferred to slice 005-02; until
then, the manual recipe is:

1. `adr.py new <new-slug>` for the new decision.
2. In the new ADR's Status block, add a line: `Supersedes ADR-NNNN`.
3. In the old ADR's Status block, change to `Superseded by ADR-NNNN (date)`
   — this is the **one** edit allowed on an accepted ADR.

If a user asks to "supersede ADR-NNNN", explain that the explicit
`supersede` subcommand is a future slice (005-02) and walk them through the
manual recipe above.

## End-to-end example (full lifecycle)

```bash
# 1. Identify the deferred decision in docs/refinement-todo.md.
#    Fragment: "scaffold-stable" (matches "### Decision: scaffold-stable …").

# 2. Scaffold the ADR.
python3 .../adr.py new scaffold-stable --title "scaffold-stable trigger"
# → docs/adrs/0003-scaffold-stable.md

# 3. Claude edits the file: fills Context, Options, Recommended, Consequences.

# 4. Accept.
python3 .../adr.py accept 0003
# → flips Proposed → Accepted (today).

# 5. Regen the index.
python3 .../adr.py index docs/adrs

# 6. Mark the refinement-todo entry resolved.
python3 .../adr.py resolve-todo 0003 "scaffold-stable"
```

## Gotchas

- **Auto-numbering does not fill gaps.** If `0001` and `0003` exist (no
  `0002`), the next new ADR is `0004`. The gap is preserved as historical
  record.
- **Slug collisions refuse regardless of number.** `0001-foo.md` exists →
  `adr.py new foo` exits 2. Either pick a different slug or write a
  superseding ADR.
- **resolve-todo touches only three lines.** Heading, first `**Deferred:**`
  line, and one new `**Resolved by:**` line appended at the section end.
  Other fields (`**Resolution trigger:**`, `**Mitigation idea:**`,
  `**Watch-list:**`, etc.) are left intact. If a section needs more
  intricate updates, edit it by hand.
- **Index description extraction may produce ugly first lines.** The helper
  takes the first non-empty paragraph from `## Context`, truncating at the
  first sentence-ending punctuation when the paragraph is multi-line or
  >120 chars. If the first sentence references a markdown link or starts
  with a long preamble, the resulting bullet line will read oddly — edit
  the ADR's first Context sentence to be index-friendly.
- **The helper does NOT spawn a Task or commit anything.** It only mutates
  files. Claude is responsible for orchestration (e.g. running
  `workflow.py status-board` afterward, writing commit messages,
  invoking the reviewer subagent).
- **Substring matching mirrors `workflow.py`.** `0001-01` does not collide
  with `0001` since ADR numbers are matched as exact 4-digit prefixes,
  not free-form substrings (unlike slice fragments).

## Reconciliation checklist

After using this skill in a real session:

- [ ] Did the index regen produce sensible descriptions? If not, edit the
      ADR's first Context sentence and re-run `adr.py index`.
- [ ] Was the refinement-todo entry actually resolved by this ADR, or did
      a partial overlap make `resolve-todo` apply to the wrong section?
      Verify before committing.
- [ ] Did the human approve the Recommended Decision before `accept`? If
      not, walk back to the Proposed state by editing the Status line
      (this is the one situation where editing a not-yet-Accepted ADR
      is fine — it's not yet immutable).
