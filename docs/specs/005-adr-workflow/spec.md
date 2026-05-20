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

**STATUS: DONE**

> Reframed 2026-05-20 (post-ADR-0005). The pre-pivot version of this
> slice was scoped to **internal module-boundary edits** (per ADR-0002's
> Option A/C framing). ADR-0005 superseded that — `contracts` is now an
> **external-interface** concern (OpenAPI / JSON Schema / AsyncAPI /
> `.proto` / GraphQL SDL). This slice mirrors the reframe: detect edits
> to **external-interface contract-artifact files** and nudge the author
> toward an ADR if the change is breaking. Internal Python imports
> remain out of scope per ADR-0005.

**Goal:** Ship a `PostToolUse` hook
(`hooks/scripts/jig-boundary-change-warn.sh`) on `Edit|Write|MultiEdit`
that fires when the touched `file_path` matches a canonical
external-interface contract-artifact filename and emits a soft
`additionalContext` nudge pointing the author at `/jig:adr-workflow new`
and the surface-appropriate breaking-change ecosystem tool. Always
non-blocking. Mirrors `jig-post-edit-verify.sh`'s soft-warn shape
(slice 027-01).

**DoR:**
- ✅ `contracts` skill is active (spec 022 DONE) and the canonical
  per-surface artifact table is the source for the filename-pattern list
  ([skills/contracts/SKILL.md](../../../skills/contracts/SKILL.md)
  "Per-surface artifact recommendations" §).
- ✅ `adr-workflow` skill is active (slice 005-01 DONE) — the hook's
  nudge points users at `/jig:adr-workflow new <slug>`.
- ✅ `PostToolUse` `Edit|Write|MultiEdit` + soft-`additionalContext`
  pattern proven by `jig-post-edit-verify.sh` (slice 027-01). The new
  hook adopts the same shape, opt-out env-var convention, and 5s
  timeout.
- ✅ Scaffold-mode parity touchpoints are known and finite (per slice
  027-01's deviation log §4): `scripts/verify_install.py`
  `_EXPECTED_HOOK_SCRIPTS`, `skills/scaffold-init/test_scaffold_mode.py`
  `EXPECTED_HOOK_SCRIPTS` + `EXPECTED_HOOK_EVENTS`, plus the
  hook-count callouts in `docs/architecture.md` (×3), `README.md` (×1),
  and `docs/memory/glossary.md` (×1).

**Acceptance Criteria:**

1. **`hooks/scripts/jig-boundary-change-warn.sh`** is created (Python 3
   inline body, same shape as the other six hook scripts) and registered
   in `hooks/hooks.json` as a `PostToolUse` hook with matcher
   `Edit|Write|MultiEdit` and `timeout: 5`. Co-located with the existing
   `jig-post-edit-verify` registration (sibling entry or sibling hook in
   the same `hooks` array — implementer's choice).

2. **Canonical artifact patterns** (basename match, case-insensitive)
   trigger the nudge. The list is hard-coded in the script (slice 1; a
   project-configurable list is a deferred follow-up — see below):
   - `openapi.yaml`, `openapi.yml`, `openapi.json`
   - `asyncapi.yaml`, `asyncapi.yml`, `asyncapi.json`
   - `*.proto`
   - `*.graphql`, `*.graphqls`
   - `*.schema.json` (the infix `.schema` is load-bearing —
     `package.json` must NOT match)

   Patterns are taken verbatim from the
   [contracts skill's per-surface table](../../../skills/contracts/SKILL.md).
   If contracts grows the table later, this list grows with it (manual
   sync; the dependency is intentional and noted in the hook's header
   comment).

3. **Nudge text** carries four parts, in order:
   - The artifact basename that was edited.
   - A pointer at `/jig:adr-workflow new <slug>` for capturing the
     rationale if this is a breaking change.
   - A surface-specific pointer at the breaking-change tool from the
     contracts skill table (`*.proto` → `buf breaking`; OpenAPI →
     `redocly diff` / OpenAPI breaking-change ruleset for `spectral`;
     `*.graphql` → `graphql-inspector diff`; `*.schema.json` →
     JSON-Schema diff against the base ref; AsyncAPI → AsyncAPI parser
     diff). The mapping is hard-coded alongside the filename patterns.
   - A reminder that the nudge is informational, not a gate.

   Exact wording is implementer's choice; AC #6 pins the load-bearing
   substrings each test fixture must observe.

4. **Opt-out via `JIG_BOUNDARY_CHECK=0`.** Same convention as
   `JIG_POST_EDIT_VERIFY=0` (slice 027-01). When set, hook exits 0
   immediately with no output.

5. **Non-matching paths exit silently.** Files whose basename does not
   match any pattern (`README.md`, `src/foo.py`, `package.json`, etc.)
   produce no output, exit 0. Non-`Edit|Write|MultiEdit` tools likewise
   produce no output, exit 0. Missing `file_path` produces no output,
   exit 0 (mirrors slice 027-01 robustness).

6. **Tests** in `scripts/test_boundary_change_warn.py` (parallels
   `scripts/test_post_edit_verify.py` shape):
   - **Match matrix:** each of the canonical filenames in AC #2 (at
     least one per surface row — `openapi.yaml`, `foo.proto`,
     `schema.graphql`, `event.schema.json`, `asyncapi.yml`) triggers a
     nudge containing both `/jig:adr-workflow new` AND the
     surface-specific tool name from AC #3.
   - **Case-insensitive:** `OpenAPI.YAML` triggers; `FOO.PROTO`
     triggers.
   - **Non-matching files:** `README.md`, `src/foo.py`, `package.json`
     (NOT `*.schema.json`), `pyproject.toml` produce no output, exit 0.
   - **Non-edit tools:** `Read`, `Bash`, `Glob`, `Task` produce no
     output, exit 0 even on a matching `file_path`.
   - **Opt-out:** `JIG_BOUNDARY_CHECK=0` produces no output on a
     matching file.
   - **Never blocks:** when a nudge fires, stdout is valid JSON with
     `continue: true` and no `block` / `permissionDecision` field;
     exit code is 0.
   - **Surface-tool routing:** `.proto` mentions `buf breaking`;
     `*.graphql` mentions `graphql-inspector`; OpenAPI mentions
     `redocly` or `spectral`; `*.schema.json` mentions a JSON-Schema
     diff tool. (Pins AC #3's load-bearing substrings.)

7. **Scaffold-mode parity.** The new hook is added to:
   - `scripts/verify_install.py` `_EXPECTED_HOOK_SCRIPTS`.
   - `scripts/test_verify_install.py` (whatever fixture-list mirrors
     `_EXPECTED_HOOK_SCRIPTS`).
   - `skills/scaffold-init/test_scaffold_mode.py` `EXPECTED_HOOK_SCRIPTS`
     and `EXPECTED_HOOK_EVENTS` (the latter already includes
     `PostToolUse`, so the addition is hook-name-only).

8. **Doc + hook-count callouts swept.** The "six hooks" / "six jig
   hooks" / "6 hooks" callouts at the five sites already enumerated
   in the DoR are bumped to seven (no other documentation rewrites —
   per the slice's anti-horizontal-phasing posture):
   - `docs/architecture.md:30`, `docs/architecture.md:52` (mermaid
     subgraph title), `docs/architecture.md:71` (hook-spine summary
     paragraph — also extend the "inject `additionalContext`" list to
     include `boundary-change-warn`).
   - `docs/architecture.md:98`, `docs/memory/glossary.md:53`,
     `README.md:103`.

9. **`skills/adr-workflow/SKILL.md`** gains a short "Boundary-change
   nudge" subsection (paragraph, not a full how-to) that explains when
   the hook fires, names the `JIG_BOUNDARY_CHECK=0` opt-out, and points
   the reader at the `contracts` skill for the surface-tool map. Format
   mirrors how other skill SKILL.md files document their own hooks
   (e.g., `spec-workflow/SKILL.md`'s spec-gate section).

**DoD** (same shape as 005-01 / 027-01):
- [x] All 9 ACs pass; full test suite green (no regressions). **34 new tests; 1240 total; no regressions.**
- [x] Implementer test coverage exercises each AC with at least one
      fixture. The pattern-matching matrix in AC #6 is covered
      exhaustively per surface (at least one fixture per row of the
      contracts skill table).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`. **Compliance pass via `jig:reviewer` + craft pass via
      `general-purpose` with `review.py pr-review` prompt — both PASS.**
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading. **See below.**
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation (likely candidates: configurable
      surface list per project, real breaking-change detection vs.
      filename-matching heuristic, hook chattiness if it false-positives
      too often). **No new entries — the three likely candidates were
      already named in the slice's "Follow-up slices" section at DRAFT
      time, with explicit resolution triggers; none required
      refinement-todo entries. One new craft-reviewer observation
      (PATTERNS-table dedup) landed in `docs/inbox.md` instead, since
      it's a deferred-decision *candidate*, not a deferred decision
      yet.**

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column carries the new hook-count + surface tools covered.
- [x] `CLAUDE.md` hygiene per spec 025-01 rule: this slice does not
      close spec 005 (005-02 remains DEFERRED with its own resolution
      trigger), so leave the Active-specs entry shape unchanged. No
      new Skills-table row is needed — the hook is registered under
      the existing `adr-workflow` skill row. **Confirmed: CLAUDE.md's
      Active specs section already read `_(none — see docs/specs/README.md
      for the status board)_` pre-slice, so no compression action was
      possible; status-board Notes column carries the load-bearing
      per-slice invariants per the convention.**

**Anti-horizontal-phasing check:** End-to-end observable value in one
slice — the next time anyone (in jig itself, or in a scaffold-installed
project) edits an `openapi.yaml`, a `*.proto`, a `*.schema.json`, a
`*.graphql`, or an `asyncapi.yaml`, they immediately see an
`additionalContext` line in the same turn suggesting they consider an
ADR if the change is breaking, plus the surface-appropriate tool to
confirm whether it is. No intermediate state; no follow-up slice
required to make it useful.

### Follow-up slices (deferred — re-open via `workflow.py new` or as 005-04…)

- **Project-configurable surface list.** Read user-declared surfaces
  from `scaffold.json` (or a dedicated `.jig/boundary-patterns` file)
  so the hook also fires on non-canonical artifacts (e.g., the bespoke
  `env-contract.md` triple from aso-shallow-validator). **Resolution
  trigger:** first project that ships a non-canonical contract artifact
  and wants the same nudge, OR three concrete "I declared a surface in
  vision-elicitation Appendix A but the hook doesn't see it" complaints.
- **Real breaking-change detection.** Subprocess out to `buf breaking`
  / `graphql-inspector diff` / OpenAPI diff against the base ref so the
  hook only fires when the change is actually breaking (not on every
  artifact edit). **Resolution trigger:** first noisy false-positive in
  jig's own dogfood that demonstrates filename-matching alone is too
  aggressive, OR a downstream user reports the nudge fatigue.
- **`adr.py boundary-check` helper.** On-demand audit subcommand
  surfacing all contract-artifact files touched since a base ref that
  lack an accompanying ADR. **Resolution trigger:** first slice that
  needs to audit a git range broader than a single Edit/Write/MultiEdit
  call (e.g., a multi-day branch, a CI pre-merge check).

### Clarifications

_Pass 1 — 2026-05-20 — `/jig:clarify` against slice 005-03._

#### Q1: How should the new hook reach projects that were scaffolded BEFORE this slice lands? Their `.claude/settings.json` won't include the new hook.
_(category: Non-functional Requirements)_

Manual opt-in via copy-machinery.

#### Q2: What should the inline Python body do if it crashes on malformed input (broken stdin JSON, unexpected schema, etc.)?
_(category: Edge Cases & Failure Modes)_

Silent — mirror jig-post-edit-verify (027-01).

#### Q3: Should the hook fire on Write of a NEW artifact file (the project's first OpenAPI / proto / schema), or only on edits to existing ones?
_(category: Edge Cases & Failure Modes)_

Fire on both new-file Write and Edit.

#### Q4: Jig has no contract artifacts of its own — no `openapi.yaml`, no `*.proto`. How should this slice be dogfooded in jig itself?
_(category: Scope & Boundaries)_

Accept "first fires in downstream projects".

#### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Clear |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Resolved |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Mermaid diagram restructured beyond the spec's "title bump" wording.**
   AC #8 enumerated five doc-callout sweeps and named the line-71 paragraph as
   the spot where the `additionalContext` injector list grows. The mermaid
   diagram (line 52+) was named only for its **subgraph title** bump
   ("6 → 7 hooks"). The implementer also added a new `h6` node + arrow for
   `jig-boundary-change-warn` and promoted the existing Stop hook from `h6`
   to `h7`, on the rationale that leaving the diagram showing six nodes
   while the title reads "7 hooks" would have created a worse inconsistency
   than the small structural extension. The spec's "inject `additionalContext`
   list now includes boundary-change-warn" instruction only makes sense if
   the new hook is also visible in the diagram. **Not a blocker; flagged here
   so a future reader sees the diagram structural change was deliberate, not
   an over-reach.**

2. **Co-located hook entry in the same `Edit|Write|MultiEdit` matcher.**
   AC #1 left this as implementer's choice (sibling matcher block vs.
   co-located inside the existing matcher's `hooks` array). The implementer
   picked **co-located** to keep the PostToolUse section visually tight and
   mirror how Claude Code's documented hook registration groups hooks by
   matcher. The craft reviewer endorsed this choice as "the right call —
   same matcher pattern, same timeout, two hooks fire in declared order with
   no duplication of the matcher object."

3. **AC #3 part 4 wording — chose "informational, not a gate."** AC #6's
   `NeverBlocksTests.test_nudge_mentions_informational_not_gate` was the
   pinned-substring contract: any of `"informational"`, `"not a gate"`,
   `"non-blocking"`, or `"nudge"` would satisfy the test. The implementer
   used "This nudge is informational, not a gate." — covering both
   `"informational"` AND `"not a gate"` AND `"nudge"`. Future wording
   changes remain compatible with the contract.

4. **Line-number drift in AC #8.** Spec AC #8 referenced
   `docs/architecture.md:71` and `docs/architecture.md:98` as sweep sites.
   The actual landed lines are `:73` and `:100` — a two-line drift caused by
   the slice's own additions earlier in `architecture.md` (the new `h6` node
   + arrow). Substantive content is at the correct sites; the drift is a
   spec-text-vs-actual-file hygiene artifact, not a functional gap.
   **Compliance reviewer flagged.**

5. **DoD checkbox temporal inconsistency.** Between the IN_PROGRESS → REVIEWED
   transition (which auto-ticks "Implementation review passed" per slice
   003-04) and the actual independent-review pass, the "Reviewed by `reviewer`
   subagent" box was unticked while "Implementation review passed" was
   ticked. The two boxes refer to the same review; the transition's auto-tick
   is what created the temporal gap. Both boxes are now ticked (post-review).
   **Compliance reviewer flagged.** This is a known auto-tick / manual-tick
   ordering quirk, not a slice defect — same shape every post-003-04 slice
   inherits. Not worth a separate fix.

6. **Silent-on-crash posture trades observability for non-disruption.**
   Clarification Q2 pinned `except Exception: pass` (mirroring
   `jig-post-edit-verify`). A real implementation bug in the hook can go
   unnoticed in a session — the hook just exits 0 silently. Tests pin
   `stderr == ""` on malformed input to lock the posture in. This is the
   chosen design; calling it out so a future operator who hits hook-internal
   weirdness knows to opt out via `JIG_BOUNDARY_CHECK=0` and re-run with
   the script body inline for debugging. **Compliance reviewer flagged.**

7. **Forward-leaning negative tests beyond AC #6.** The implementer added
   `test_arbitrary_json_does_not_trigger` (using `config.json`) to pin the
   load-bearing `.schema` infix invariant — explicit verification that the
   pattern `*.schema.json` does not collapse to `*.json`. AC #6 enumerated
   `package.json` as the canonical negative case; the implementer
   generalized. The craft reviewer also noted the case-insensitive coverage
   uses both `OpenAPI.YAML` (mixed) AND `FOO.PROTO` (fully upper), catching
   both fnmatch and `lower()` bugs. **Compliance reviewer flagged as
   positive addition.**

8. **Stale "five jig hooks" comment in `skills/scaffold-init/scaffold.py:660`
   swept in this slice.** The craft reviewer flagged this as out-of-slice
   but worth a 1-char fix while the slice was already touching the hook
   count. The DoR's enumerated five sites were the docs (architecture.md,
   glossary.md, README.md) — the scaffold.py docstring was not on the
   list. Fixed in this slice (changed to "the jig hooks ... (the set
   discovered by globbing `plugin/hooks/scripts/jig-*.sh`, not a hard-coded
   count)") so future hook additions don't recreate the drift. **In-scope
   janitorial pickup, not a slice scope expansion.**

9. **PATTERNS-table duplication observation deferred.** The craft reviewer
   pointed out that the PATTERNS table duplicates OpenAPI/AsyncAPI tool-string
   rows three times each (one per encoding: yaml/yml/json). A dict-of-suffix
   plus a `openapi.*` / `asyncapi.*` generic pattern would halve the table
   and make contracts-skill sync easier when a new format lands. The
   implementer kept the explicit six-row form on the rationale that
   duplication is honest when the hook's header comment already names the
   manual contracts-sync as intentional. **Deferred-decision candidate:
   re-evaluate when AsyncAPI gets a 4th encoding or OpenAPI 3.2 adds a new
   file extension.** Logged in `docs/inbox.md`.

10. **Nudge string length nit deferred.** The craft reviewer flagged the
    ~280-char nudge string as "a wall in tool output" and suggested a
    two-line `basename\nadvice` variant (mirroring `jig-post-edit-verify`'s
    multi-warning format). Cosmetic; the actual rendering in the agent
    transcript depends on the consumer's display, and the spec contract is
    substring-based, not visual. Deferred until a real session shows the
    one-line form is unreadable.

11. **Test substring tightening nit deferred.**
    `test_schema_json_triggers_json_schema_diff` asserts lowercased `"schema"`
    and `"diff"` substrings, which would also pass for a (hypothetical)
    "OpenAPI schema diff" tool string. The craft reviewer suggested
    `assertIn("JSON Schema diff", ctx)`. Defer: the surface label in the
    nudge already disambiguates ("JSON Schema" surface vs. OpenAPI surface
    in the same nudge text would be a different bug entirely). Test
    coverage is already exhaustive.

12. **Dogfood deferred to first downstream-project fire.** Per Clarification
    Q4, jig has no contract artifacts of its own; the static review
    confirms correctness but cannot confirm the hook fires end-to-end in a
    real session. First real-world fire (the next time anyone edits an
    `openapi.yaml` / `*.proto` / `schema.graphql` / `*.schema.json` in a
    project running jig) is the dogfood signal. **No remediation needed;
    pinned here so the deviation log captures what's NOT tested at the
    boundary.**

#### Doc updates from this slice

- `docs/architecture.md` — hook-count "six → seven" at four sites
  (lines 30, 52, 73, 100); mermaid subgraph extended with `h6`
  (`jig-boundary-change-warn`) + `additionalContext` arrow; `h7` is now
  the Stop hook (`jig-task-capture`).
- `docs/memory/glossary.md` — hook-count "six → seven" at line 53.
- `README.md` — hook-count "six → seven" at line 103.
- `skills/adr-workflow/SKILL.md` — new "Boundary-change nudge" subsection
  (paragraph + opt-out env var + pointer to the contracts SKILL.md per-
  surface table).
- `skills/scaffold-init/scaffold.py:660` — stale "five jig hooks" docstring
  bumped to "the jig hooks ... globbing `jig-*.sh`" (count-free).
- `docs/refinement-todo.md` — no new entries. All deferred items named in
  the slice's "Follow-up slices" section were already named at DRAFT time;
  none of the implementation surprises added new ones.
- `docs/inbox.md` — one new entry for the PATTERNS-table dedup observation
  (deviation log #9).
