---
status: DONE
skill: adr-workflow
tier: 1
---

# Spec 005: adr-workflow (Tier 1)

## Overview

Introduce `adr-workflow` — the first Tier 1 skill — to codify how ADRs are
written, accepted, indexed, and linked back to the deferred decisions they
resolve. Today the steps are entirely manual: pick a number, copy the section
shape from a prior ADR, edit `docs/decisions/README.md`'s Index by hand, and
(when applicable) strike through the matching entry in `docs/refinement-todo.md`
with a "Resolved by:" link. Two ADRs in, the pattern is clear enough to
codify without locking in premature design.

This is the first skill that is **not** a Tier 0 stub promotion — it's net
new. We are creating `skills/adr-workflow/` from scratch.

## Why now

- **The pattern is dogfooded.** ADR-0001 (scaffold-stable trigger) and ADR-0002
  (contracts stays deferred) were both written by hand, with identical shape
  (Status / Context / Decision Options Considered / Recommended Decision /
  Consequences / Open questions). The format spec in `docs/decisions/README.md`
  matches what was actually written. There is nothing left to discover about
  what an ADR looks like in jig.
- **The refinement-todo integration is a real value lever.** ADR-0001's
  resolution of the "scaffold-stable trigger" deferred item required
  strikethrough-editing the heading in `docs/refinement-todo.md` and appending
  a `**Resolved by:**` line by hand. Easy to forget; easy to mis-link. The
  helper can do this deterministically.
- **ADR-0002 explicitly named `adr-workflow` as unspecced.** That ADR
  deferred the broader `contracts` skill in part because
  "Breaking-change detection (paired with `adr-workflow`, also unspecced)"
  was unreachable without an ADR pipeline. Closing that gap unblocks
  future work without re-opening the contracts deferral.
- **Tier 1 work has to start somewhere.** Of the four Tier 1 candidates
  (`tdd-loop`, `local-dev-parity`, `pr-review`, `adr-workflow`), this one
  has the most dogfood signal, the cleanest scope, and the highest
  integration value with existing Tier 0 surface (refinement-todo +
  reconciliation flow).

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| P — Path | New-ADR vs. supersede-existing-ADR vs. amend (forbidden — ADRs immutable). | New-ADR is the only path this slice covers. Supersede is a separate slice (005-02, deferred). |
| I — Interface | One helper script (`adr.py`) + SKILL.md, or split into multiple helpers? | One helper, four subcommands. Matches the `scaffold.py` / `memory.py` / `workflow.py` / `review.py` pattern. |
| D — Data | Inline ADR skeleton in `adr.py`, or external template file under `templates/docs/decisions/`? | External template file. Matches how other docs are templated; lets users tweak the skeleton in their own projects without touching the helper. |
| R — Rules | Status state machine (Proposed → Accepted; Accepted → Superseded). Immutability after Accepted. Auto-numbering. | This slice enforces the Proposed → Accepted transition and the numbering. Supersede is deferred to 005-02. |
| S — Spike | None required — two existing ADRs document the full target shape. | — |

## Out of scope for spec 005 (any slice)

- Hook-based gate that blocks merges/commits without an ADR for boundary
  changes. (Different concern; belongs in `contracts` when promoted, or a
  dedicated review-gate slice.)
- Auto-detecting which deferred-decision section a new ADR resolves. (User
  passes the heading explicitly — heuristic detection is premature.)
- ADR templating for non-Nygard formats (e.g. MADR, Y-statements).

---

## Slice 005-01 — adr-helper

**STATUS: DONE**

**Goal:** `adr.py` helper that scaffolds a new ADR file from a template,
accepts (status-transitions) it, regenerates `docs/decisions/README.md`'s Index,
and resolves a matching entry in `docs/refinement-todo.md`. New
`skills/adr-workflow/SKILL.md` with active frontmatter (no
`disable-model-invocation`) wires it into the auto-trigger surface.

**DoR:**
- No prior slice dependency — this is the first slice of a new skill.
- ✅ `docs/decisions/` exists with README.md + two reference ADRs (0001, 0002).
- ✅ `docs/refinement-todo.md` exists with one already-resolved entry
  (the scaffold-stable trigger) demonstrating the target strikethrough
  format.
- ✅ Format spec in `docs/decisions/README.md` names the required sections.

**Acceptance Criteria:**

1. **`adr.py new <slug> [--title "<Title>"]`** creates
   `docs/decisions/NNNN-<slug>.md` where:
   - `NNNN` is auto-numbered: max existing `NNNN-*.md` index + 1, zero-padded
     to 4 digits. (`0001`, `0002` exist → next is `0003`.)
   - File contains the standard sections in order: `# ADR-NNNN: <Title>`,
     `## Status`, `## Context`, `## Decision Options Considered`,
     `## Recommended Decision`, `## Consequences`, `## Open questions`.
   - `Status` body is `Proposed (YYYY-MM-DD)` using today's date.
   - All other section bodies are empty placeholders (`_TODO_` or
     section-appropriate stub text).
   - If `--title` is omitted, the title defaults to a Title-Cased version
     of the slug (`my-decision` → `My Decision`).
   - Refuses with exit 2 if the slug is already taken (any existing
     `NNNN-<slug>.md`, regardless of number).
   - Prints the created path to stdout. Exit 0.

2. **`adr.py accept <NNNN>`** flips the Status from `Proposed (YYYY-MM-DD)`
   to `Accepted (YYYY-MM-DD)` (today's date), in
   `docs/decisions/NNNN-<slug>.md`.
   - Locates the ADR by `NNNN-` prefix (zero-padded match) — refuses with
     exit 2 if no match or multiple matches.
   - Refuses with exit 2 if Status is not currently `Proposed` (covers
     already-Accepted and Superseded).
   - Writes back atomically (`.tmp` + `os.replace`) to avoid torn writes —
     applies the same shared pattern the refinement-todo entry calls for.
   - Prints the modified path to stdout. Exit 0.

3. **`adr.py index <adrs-dir>`** regenerates the `## Index` section of
   `<adrs-dir>/README.md` from the actual `NNNN-*.md` files present:
   - One line per ADR: `- [ADR-NNNN: <Title>](NNNN-<slug>.md) — <one-line
     description from first Context paragraph> (<YYYY-MM-DD>, <Status>)`.
   - Sort order: ascending by `NNNN`.
   - Preserves all content outside the `## Index` section (header, format
     spec, "When to write" section, etc.).
   - Idempotent: re-running on an already-current README is a no-op.
   - Refuses with exit 2 if README.md has no `## Index` heading.

4. **`adr.py resolve-todo <NNNN> <heading-fragment>`** updates
   `docs/refinement-todo.md`:
   - Locates a section heading (`### Decision: ...` or similar) that
     contains `<heading-fragment>` (case-insensitive substring match,
     same matching style as `workflow.py`'s slice fragment).
   - Wraps that heading line in `~~strikethrough~~` and appends
     ` — RESOLVED YYYY-MM-DD` (today's date).
   - Wraps the section body's first `**Deferred:** ...` line in
     strikethrough as well (preserves the original text for history).
   - Appends a new line at the end of the section body:
     `**Resolved by:** [ADR-NNNN: <Title>](adrs/NNNN-<slug>.md).`
   - Refuses with exit 2 if: heading fragment matches zero or multiple
     sections; the ADR isn't yet Accepted; refinement-todo.md is missing;
     or the section is already struck through.
   - Atomic write back. Exit 0.

5. **`skills/adr-workflow/SKILL.md`** is created with:
   - Active frontmatter (no `disable-model-invocation: true`).
   - A `description` that auto-triggers on prompts like "write an ADR",
     "record this decision", "resolve [deferred item] with an ADR",
     "supersede ADR-NNNN" (the last triggers an explanation that
     supersede is a future slice).
   - Body sections: What this skill does / How to use (new / accept /
     index / resolve-todo, each with the bash invocation) / Immutability
     rule (no editing accepted ADRs — supersede instead) / Gotchas.

6. **`templates/docs/decisions/adr-0000-template.md`** is added, holding the
   skeleton `adr.py new` clones. The helper substitutes `{{NUMBER}}`,
   `{{TITLE}}`, `{{DATE}}` placeholders. This keeps the skeleton tweakable
   without re-shipping `adr.py`.

7. **Tests** in `skills/adr-workflow/test_adr.py` cover:
   - `NewTests` — auto-numbering, slug conflict refusal, title default,
     explicit title, file shape (all six sections present, in order),
     today's date in Status.
   - `AcceptTests` — happy path, Proposed → Accepted; refusal on
     missing ADR, ambiguous prefix, already-Accepted.
   - `IndexTests` — regen happy path (two ADRs), idempotency, preserves
     non-Index content, refusal on missing `## Index`.
   - `ResolveTodoTests` — happy path strikes through heading + first
     Deferred line, appends Resolved-by; refusal on ambiguous fragment,
     missing fragment, ADR-not-Accepted, already-struck-through.
   - `SkillSurfaceTests` — SKILL.md frontmatter has no
     `disable-model-invocation`; SKILL.md body references all four
     subcommands by name; template file exists at expected path.

**DoD** (same shape as 003-01 / 004-01):
- [x] All 7 ACs pass; full test suite green (existing + new). **46 new tests; 191 total; no regressions.**
- [x] Implementer test coverage including auto-number boundary
      (last existing ADR is `0099-*` → next is `0100`). **Covered by `NewTests.test_boundary_auto_number`.**
- [x] Reviewed by `reviewer` subagent. The reviewer prompt for this
      slice will itself be built by `review.py` (dogfood). **Done — prompt built by `review.py`; verdict: pass.**
- [x] Deviation log produced under this slice heading. **See below.**
- [x] Reconciliation review pass.
- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] `docs/refinement-todo.md` left untouched by this slice (no new
      decisions deferred unless a real one surfaces during implementation). **Confirmed — only the sandbox copy was edited during dogfood; the real file is byte-identical to its pre-slice state.**

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice. A
user with a deferred decision in `refinement-todo.md` can: run
`adr.py new` → edit the file → run `adr.py accept` → run `adr.py index`
→ run `adr.py resolve-todo`. Each step is user-visible; the final state
is a written, accepted, indexed ADR with the deferred item resolved.
No layer-only phase ("just the file creation, indexing comes later").

### Deviation log (after reconciliation)

The original spec is preserved above.

**Dogfood-driven course corrections:**

1. **`\s` regex anchor consumed the line terminator.** First cut of `cmd_accept` used `\s*$` to anchor the Status line, but `\s` matches `\n`, so the substitution glued `Accepted (2026-05-12)## Context` together. Surfaced by the dogfood pass (sandbox ADR's `## Context` heading disappeared off the next line). Fixed in-place by switching to `[ \t]*$`. Same bug bit `cmd_index`'s `## Index` matcher on first attempt — same fix. Added `AcceptTests.test_accept_preserves_section_separator` as a regression guard. **This is the third occurrence in this repo of a Python regex `\s*$` pattern that should have been `[ \t]*$`** — the implementer already flagged the next watch site (`_extract_status_and_date` uses `\s+` in a locator role, which is currently safe but would be more defensible as `[ \t]+`). Watch-list item, not a slice-blocker.

**Design choices logged:**

2. **Substring matching duplicated, NOT extracted.** This slice is the third caller of the lenient-substring-match pattern that started in `workflow.py find_slice_section` and was replicated in `review.py find_slice_label`. Spec 004-01's deviation log (design choice #1) explicitly named "first time a third helper needs this lookup" as the trigger to extract `skills/_common/parsing.py`. **That trigger has fired.** However: the three call sites match three different header shapes (`## Slice X — Y` for workflow.py, the same for review.py, `### Decision: X` for adr.py), and the regexes diverge accordingly. The shared abstraction would be the *pattern* (case-insensitive substring against a list of headings), not the function. Extracting today would be premature — the call sites use different regexes, so the abstraction would be a thin wrapper around `[h for h in headings if fragment.lower() in h.lower()]` plus `len() == 1` guards, which is short enough that duplicating it is honest. **Decision: duplicate again. Re-evaluate when slice 005-02 (supersede) lands and a *fourth* caller appears with a similar shape.** Logged in inbox.md as a watch-item.

3. **Slug validation added beyond the spec.** `cmd_new` rejects slugs that don't match `^[a-z0-9][a-z0-9-]*$` with exit 2. The spec didn't require slug validation, but invalid slugs would create broken filenames (paths with spaces, leading hyphens, uppercase). Defensive guard. Tested in `NewTests`.

4. **Extra realism test for `index`.** `IndexTests.test_index_handles_real_adrs_in_repo` copies the real `adr-0001-scaffold-stable.md` and `adr-0002-contracts-stays-deferred.md` into a temp dir and asserts the index regen produces well-formed bullets with truncated descriptions. Not strictly required by AC #3, but plan.md's "Risks" section flagged that real-world Context paragraphs would produce ugly descriptions if not truncated; this test pins the truncation behavior against actual jig fixtures.

**Reviewer-flagged minor notes (accepted as-is):**

5. **`_extract_description` code comment is misleading** (`adr.py:267-273` per reviewer). The comment says "Walk char-by-char to avoid false positives inside `e.g.`" but the truncation will still split at `e.g.` whenever a space follows. The runtime behavior is correct (it's a truncation aid, not a sentence boundary detector) and documented in SKILL.md gotchas. Comment-only fix; deferred — not worth a slice. Watch-list.

6. **`_extract_status_and_date` will mis-report a Superseded ADR's date** (`adr.py:227-229` per reviewer). The structured regex matches `Proposed (date)` and `Accepted (date)` but fails on `Superseded by ADR-NNNN (date)`; the fallback `line.split()[0]` then returns just `"Superseded"` with no date. AC #4's Accepted-only gate makes this irrelevant for slice 005-01, but the index bullet for a future Superseded ADR would read `(Superseded)` with no date. **Filed under slice 005-02 (supersede) DoR** — when 005-02 lands it must extend `_extract_status_and_date` to recognize the Superseded shape, and the test fixture should include a Superseded ADR.

7. **Dead `if target.exists()` branch** (`adr.py:137-138` per reviewer). Defensive double-check after auto-numbering + slug-collision refusal; unreachable in practice. Harmless. Could be downgraded to `assert` or removed during 005-02 work. Not a defect.

**Forward-leaning additions:**

- SKILL.md "Gotchas" section enumerates the three behaviors users might trip over: ugly auto-extracted descriptions, the strikethrough-detection contract, and the immutability rule (no editing accepted ADRs — supersede instead, which is currently 005-02 DRAFT).
- CLAUDE.md skills table promotes `/jig:adr-workflow` to active (auto + explicit invocable).

**Doc updates from this slice:**

- `templates/docs/decisions/adr-0000-template.md`: new file, holds the ADR skeleton with `{{NUMBER}}`/`{{TITLE}}`/`{{DATE}}` placeholders.
- `skills/adr-workflow/SKILL.md`: net-new file (not a stub promotion). Frontmatter active; description triggers on "ADR", "decision", "resolve", "supersede".
- `skills/adr-workflow/adr.py` + `test_adr.py`: net-new helper + 46 tests.
- `docs/specs/README.md`: regenerated by `workflow.py status-board`.
- `CLAUDE.md`: hot-cache "Active specs" + Skills table updated. Incidental janitorial fix: dropped a stale `002-memory-layer: STATUS DRAFT — slice 002-01 (explicit-sync) queued` bullet that contradicted the `002-memory-layer: **complete**` entry two lines above. Flagged by the reconciliation reviewer.
- `docs/inbox.md`: new entry parking the "third-caller extraction trigger fired but premature" decision (so future-self has the breadcrumb when 005-02 lands).
- No `architecture.md` changes (helper colocated with its skill — same precedent as `scaffold.py` / `memory.py` / `workflow.py` / `review.py`).
- No new ADR required.
- No `learnings.md` entry (the `\s` regex bug is the third occurrence; if it recurs once more it's worth elevating).

---

## Slice 005-02 — supersede

**STATUS: DEFERRED** _(deferred; not part of this session)_

**Goal:** `adr.py supersede <old-NNNN> <new-NNNN>` flips the old ADR's
Status to `Superseded by ADR-NNNN (YYYY-MM-DD)` and inserts a
`Supersedes ADR-NNNN` line into the new ADR's Status block.

Deferred because: zero supersedes have happened in jig so far. The
shape is guessable from the Nygard convention, but waiting for a real
supersede event keeps us from codifying the wrong thing.

**Resolution trigger:** First time a real superseding ADR is needed
in jig OR in a target project.

---

## Slice 005-03 — boundary-change-detection

**STATUS: DEFERRED** _(deferred)_

**Goal:** Hook or helper that surfaces "you changed a module boundary
without writing an ADR." Pairs with the `contracts` skill once it
promotes.

Deferred because: blocked on `contracts` promotion (ADR-0002), and
jig has no module boundaries to enforce today. Listed here so future
readers see the scope envelope.

**Resolution trigger:** `contracts` skill becomes active.
