---
status: DONE
dependencies: []
last_verified: 2026-06-25
---

## Slice 083-01 — Convention + seed file + reconcile prompt

**Goal:** Introduce `docs/decisions/lightweight-decisions.md` as a browsable
home for small shipped decisions that fall outside spec slices, add it to the
decisions README, and add a reconcile-checklist prompt that converts informal
review feedback into durable records.

**DoR:**
- ✅ `docs/decisions/` directory already exists in all jig-scaffolded projects.
- ✅ `docs/workflow.md` reconciliation rules section identified (line ~275).
- ✅ No existing lightweight-decisions file or mention of the concept in workflow.md.

**Acceptance Criteria:**

1. **Seed file created.** `docs/decisions/lightweight-decisions.md` exists
   with a header, routing heuristic, and at least one example entry using the
   template fields: Date, Short title, Decision, Context, Scope, Commit.

2. **README updated.** `docs/decisions/README.md` mentions lightweight decisions
   and links to the new file, with a one-line explanation of how they differ from ADRs.

3. **Reconcile prompt added.** `docs/workflow.md` Reconciliation rules section
   gains a checklist item prompting writers to capture non-spec decisions
   (UI strings, visual choices, translation corrections, scoped brand/icon calls)
   in `docs/decisions/lightweight-decisions.md`.

4. **Routing heuristic documented.** The lightweight-decisions file or README
   records the heuristic distinguishing lightweight decisions from ADRs
   (scope-local + would-be-undone-without-a-record, vs. module-boundary /
   cross-cutting / architectural).

---

### Deviation log

- **SKILL.md also updated** — The compliance reviewer (medium confidence) flagged that `skills/spec-workflow/SKILL.md` is the operative checklist that agents walk, not just `docs/workflow.md`. The spec's phrasing ("Reconciliation checklist") was ambiguous; both surfaces were updated. This is an expansion, not a deviation from ACs.
- **Ordering differs between workflow.md and SKILL.md** — Lightweight decisions bullet appears at position 2 in `workflow.md` (prose document, no strict sequence) and position 3 in `SKILL.md` (gated checklist, after Reconciliation sweep). Deliberate: the two documents have different structures and reader expectations.
- **Commit SHA annotated as reservation** — Seed entry's Commit field updated to clarify `bdf0187` is the reservation SHA, with "(implementation SHA TBD)" to avoid future reader confusion.

### Reconciliation sweep

| Surface | Status | Notes |
|---|---|---|
| `docs/decisions/lightweight-decisions.md` | updated | created (seed file) |
| `docs/decisions/README.md` | updated | added entry + routing heuristic |
| `docs/workflow.md` | updated | reconcile-checklist item added (position 2 in prose list) |
| `skills/spec-workflow/SKILL.md` | updated | reconcile-checklist bullet added (position 3, after Reconciliation sweep) |
| `CLAUDE.md` primer | no-op | no load-bearing cross-ref needed at this scale |
| `docs/memory/glossary.md` | no-op | lightweight decisions is browsable; no glossary term needed yet |
| `docs/refinement-todo.md` | no-op | open questions remain in spec.md per pilot plan |

## Amendments

### 2026-06-25 — Opus re-review (during 083-02/03 build)

A second-pass review of this slice (after switching to Opus) corrected two
items in the live `docs/decisions/lightweight-decisions.md` prose. These are
inline corrections to a working file (not this closed record), per ADR-0010:

- **Seed entry replaced.** The original seed was a *meta* decision (about the
  file's own flat-list structure) — self-referential and not representative of
  the convention's purpose (UI/product calls). Replaced with a clearly-marked
  *illustrative* example (onboarding CTA copy), since jig itself is a CLI/plugin
  with no UI and no real lightweight decisions of its own.
- **Routing heuristic tightened** to match OQ4 verbatim (the two-part
  module-boundary / would-be-undone test) and the `Commit` field reframed as
  explicitly optional / retroactive (OQ2 resolution).

The "Commit SHA annotated as reservation" deviation-log item above is therefore
superseded — the annotated seed entry it described was replaced wholesale.
