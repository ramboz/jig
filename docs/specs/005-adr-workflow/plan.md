# Plan: Slice 005-01 — adr-helper

## Approach

Same shape as `workflow.py` / `memory.py` / `scaffold.py` / `review.py`:
deterministic Python 3 helper for the bits that don't need judgment
(file creation, status flips, index regen, refinement-todo edits),
SKILL.md for when/why to invoke and what to do with the result.

Four subcommands, one helper:

- `new <slug> [--title T]` — creates `docs/decisions/NNNN-<slug>.md` from the
  template under `templates/docs/decisions/adr-0000-template.md`. NNNN
  auto-incremented.
- `accept <NNNN>` — flips the Status line atomically.
- `index <adrs-dir>` — regenerates the `## Index` section. Same
  "preserve everything outside the managed section" pattern as
  `workflow.py status-board`.
- `resolve-todo <NNNN> <heading-fragment>` — strikethrough + Resolved-by
  link in refinement-todo.md. Substring matching on heading text
  (same lenient style as `workflow.py`'s slice fragment).

## `adr.py` CLI surface

```bash
python3 adr.py new <slug> [--title "<Title>"]
python3 adr.py accept <NNNN>
python3 adr.py index <adrs-dir>
python3 adr.py resolve-todo <NNNN> "<heading fragment>"
```

All subcommands:
- Exit 0 on success, 2 on user errors (not-found, ambiguous, illegal
  transition, slug collision).
- Print the modified path to stdout.
- Write atomically via `.tmp` + `os.replace`.

## Template file

```
templates/docs/decisions/adr-0000-template.md
```

Holds placeholders: `{{NUMBER}}`, `{{TITLE}}`, `{{DATE}}`. The helper
substitutes them in `new`. Skeleton mirrors the two existing ADRs
exactly (same six sections, in the same order).

## Auto-numbering

`new` scans `docs/decisions/*.md` (excluding `README.md`), extracts the
leading 4-digit prefix, takes max + 1. Zero ADRs → starts at `0001`.
Two existing (`0001`, `0002`) → `0003`. A gap (e.g. only `0001` and
`0003` present) → still max + 1 = `0004`; gaps are not filled.

## Slug collision

If any existing `NNNN-<slug>.md` matches the requested slug
(regardless of number), refuse with exit 2. Forces the user to either
choose a new slug or supersede the existing ADR.

## Index regen anatomy

Read `<adrs-dir>/README.md`. Find the `## Index` heading. Replace
everything between it and the next `## ` heading (or EOF). For each
`NNNN-*.md` file:
- Extract title from the `# ADR-NNNN: <Title>` line.
- Extract status + date from the `## Status` body (first non-empty line).
- Extract description: first non-empty paragraph from the `## Context`
  section. Strip to one line, truncate at ~120 chars if needed.

Emit:

```
- [ADR-NNNN: <Title>](NNNN-<slug>.md) — <description> (<YYYY-MM-DD>, <Status>)
```

Sort ascending by `NNNN`. Idempotency: re-running emits identical bytes.

## Refinement-todo edit anatomy

Read `docs/refinement-todo.md`. Find a `### Decision: ...` (or `### ...`)
heading whose text contains the user-supplied fragment (case-insensitive
substring). Refuse on zero or multiple matches.

Edit the section:
1. Replace the heading line `### Decision: Foo` with
   `### ~~Decision: Foo~~ — RESOLVED YYYY-MM-DD`.
2. Find the first `**Deferred:**` line in the section body; wrap its
   text in `~~...~~`.
3. Insert a new line at the end of the section (before the next `## `
   or `### ` heading, or EOF):
   `**Resolved by:** [ADR-NNNN: <Title>](adrs/NNNN-<slug>.md).`

If the heading is already strikethroughed (`### ~~...~~`), refuse —
the section was already resolved, and a second pass would corrupt
the format.

## Files to create

| Path | Purpose |
|---|---|
| `skills/adr-workflow/SKILL.md` | Active skill, no `disable-model-invocation`. |
| `skills/adr-workflow/adr.py` | Helper. |
| `skills/adr-workflow/test_adr.py` | Unit tests. |
| `templates/docs/decisions/adr-0000-template.md` | ADR skeleton. |

## Files to modify

| Path | Change |
|---|---|
| `docs/specs/005-adr-workflow/spec.md` | DRAFT → IN_PROGRESS → DONE (via `workflow.py transition`). |
| `docs/specs/README.md` | Regen via `workflow.py status-board`. |
| `CLAUDE.md` | Add 005 to Active specs hot-cache; add adr-workflow to skills table. |

## Coupling note

`adr.py` will want the same lenient-substring-match heading lookup
that `workflow.py` and `review.py` use. Per ADR-0002 + slice 004-01
deviation log: **duplicate, don't abstract**. Three callers now (the
exact trigger the deviation log named), so this is the moment to
consider extraction — but the heading text shape differs enough
(`## Slice X — Y` vs. `### Decision: Foo`) that the regex isn't
identical. Duplicate the *pattern*, not the *function*.

If during implementation the three call sites converge on a truly
shared signature, **stop and write an ADR** before extracting —
that's the surface-area `contracts` is meant to govern, and pulling
on it here triggers the resolution-trigger for ADR-0002.

## Test strategy

`NewTests`:
- Empty `docs/decisions/` → first ADR numbered `0001`.
- Existing `0001`, `0002` → next is `0003`.
- Gap (`0001`, `0003`) → next is `0004` (max + 1, no gap fill).
- Boundary: existing `0099` → next is `0100`.
- Slug collision (any number) → exit 2.
- File contains all six sections, in order.
- `Status` is `Proposed (today's date)`.
- Default title is Title-Cased slug; `--title` overrides.

`AcceptTests`:
- Happy path: Status flips Proposed → Accepted with today's date.
- Missing NNNN → exit 2.
- Multiple matches → exit 2.
- Already Accepted → exit 2.
- Atomic: writes via `.tmp` + replace.

`IndexTests`:
- Regen on empty `docs/decisions/` (only README) → no index entries.
- Regen with two ADRs → two entries, sorted.
- Re-running on current README → byte-identical (idempotent).
- Preserves Header, Format, "When to write" sections.
- Missing `## Index` heading → exit 2.

`ResolveTodoTests`:
- Happy path: heading and Deferred line wrapped; Resolved-by appended.
- Unique fragment substring match.
- Zero matches → exit 2.
- Multiple matches → exit 2.
- ADR not Accepted → exit 2.
- Already struck through → exit 2.
- Missing refinement-todo.md → exit 2.

`SkillSurfaceTests`:
- SKILL.md frontmatter: no `disable-model-invocation`; `user-invocable: true`.
- SKILL.md body references each of the four subcommands by name.
- Description string contains trigger phrases ("ADR", "decision",
  "resolve", "supersede").
- Template file exists at `templates/docs/decisions/adr-0000-template.md`.

## Dogfood plan

After tests pass:
1. Use `adr.py new tdd-loop-prerequisite --title "..."` against a
   throwaway sandbox dir to verify the actual end-to-end flow (don't
   pollute real `docs/decisions/`).
2. Build the implementation-review prompt via `review.py implementation`
   feeding into the reviewer subagent.
3. Reconcile.
4. Build the reconciliation-review prompt via `review.py reconciliation`.

## Risks

- **Refinement-todo format is fuzzy.** The two existing entries use
  slightly different shapes — `**Deferred:** ...` is consistent but
  `**Mitigation idea:**`, `**Watch-list:**`, etc., vary. The
  resolve-todo subcommand only touches the heading + first Deferred
  line + appended Resolved-by. Anything else stays untouched. Document
  this scope in SKILL.md gotchas.
- **Description-extraction in `index` may produce ugly first lines.**
  Existing ADR-0001's first Context paragraph is multi-line and
  references file paths. Fallback: if the first paragraph is over
  120 chars or contains `[link](url)` markdown, truncate at the
  first sentence-ending punctuation. Document in gotchas.
- **Auto-numbering race.** Two parallel `adr.py new` invocations
  could both pick the same number. Out of scope — single-user CLI.

## Out of scope

- `supersede` subcommand → slice 005-02.
- Hook integration (block-on-missing-ADR) → spec 005 future slice or
  a `contracts` slice.
- Auto-detecting which refinement-todo entry an ADR resolves →
  user passes explicitly.
- Non-Nygard ADR formats (MADR, Y-statements) → out of scope.
