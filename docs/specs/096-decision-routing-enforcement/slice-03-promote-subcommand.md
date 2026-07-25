---
status: DONE
dependencies: [096-02]
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-03 — promote-subcommand

**Goal:** `decisions.py promote --title "<existing>"` moves a misfiled entry to
an Architectural Decision Record (ADR) via `adr.py new`, seeds that ADR from the
entry's own fields, and replaces the entry with a stub that links forward. The
correction stops being a manual job, which is what makes 096-01's and 096-02's
flags actionable rather than merely informative.

**DoR:**
- ✅ 096-02 is DONE — its entry parser and title-matching (the "real entry"
  notion, `_normalize`-keyed lookup, ambiguity handling) are what `promote`
  reuses to find and remove the entry it moves.
- ✅ `adr.py new <slug>` scaffolds an ADR and allocates its number, with
  `--no-push` / `--pr` / `--project-dir` (probed via `--help`). This slice calls
  that path rather than writing a second ADR writer.
- ✅ Nothing links a lightweight entry to an ADR today: `adr.py` has no
  lightweight-record awareness, `render_entry` (`decisions.py:218`) emits no
  back-reference field, and `docs/decisions/README.md:47-53` is hand-written
  prose outside the regenerated Index.

**Acceptance Criteria:**

1. **Promotion creates the ADR through `adr.py`.** `promote --title "<existing>"`
   invokes `adr.py new` — not a hand-rolled ADR writer — so numbering, the
   template, and the reservation path stay single-sourced. The slug defaults to a
   kebab-cased form of the entry title and is overridable with `--slug`.
2. **The ADR is seeded from the entry's own fields.** The entry's Decision,
   Context, and Scope land in the corresponding ADR sections rather than leaving
   an empty template for someone to retype — the fields already exist, and
   retyping is where content gets dropped.
3. **The entry is replaced by a forward-linking stub, not deleted.** The original
   `### <date> — <title>` heading stays addressable and its body becomes a
   pointer to the new ADR. A reader who follows an old reference to the entry
   must land on the record, not on a gap. Deleting it would break every existing
   link and erase the fact that the decision was once filed here.
4. **The ADR back-links to the entry it came from**, naming the original date, so
   the promotion is legible from both ends.
5. **Reservation flags pass through.** `--no-push` and `--pr` reach `adr.py new`
   unchanged, so promotion works on a feature branch without pushing to
   `origin/main`.
6. **Failure is atomic.** If `adr.py new` fails for any reason (unreachable
   template, reservation refused, network), `lightweight-decisions.md` is left
   **byte-identical** and the error is reported. A promotion that stubs the entry
   and then fails to create its target destroys the record.
7. **A missing or ambiguous `--title` refuses**, with the same matching rules and
   messages as 096-02 (AC4–AC6) — one title-matching contract across the helper.
8. **An already-promoted entry refuses.** Re-running `promote` on a stub exits
   non-zero naming the ADR it already points to, rather than creating a second
   ADR for one decision.
9. **The illustrative example and the `## Template` fence are not promotable** —
   same exclusion as 096-02 AC7.

**Edge cases covered explicitly:**

- A title that kebab-cases to a slug `adr.py` rejects (empty, leading digit,
  double hyphen) — refuse with the rule, do not silently mangle.
- An entry with an empty `**Context:**` or `**Scope:**` (both optional at write
  time) promotes with those ADR sections left as the template's own placeholder,
  not as the literal empty string.
- Promotion under `layout.docs_root: "."` (spec 084) writes both files where the
  layout actually puts them, not at the hardcoded default.

**Anti-horizontal-phasing check:** after this slice a flagged entry can be
corrected with one command, end-to-end — ADR created, entry stubbed, both linked
— rather than the flag naming a job the operator still has to do by hand.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [x] AC6 (atomicity) is proven by an induced `adr.py` failure, not by
      inspection.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] Host packages regenerated (`scripts/build_host_packages.py`).
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.
      _(No deferred DECISIONS — the three deferred follow-ups are scoped work,
      not open questions, so they went to `docs/inbox.md` per the routing
      rubric: refinement-todo is for decisions with a resolution trigger.)_

### Reconciliation sweep

| Artifact | Disposition | Why |
|---|---|---|
| `skills/memory-sync/decisions.py` | **rewrite** | `promote`, the sibling-`adr.py` locator, slug-based ADR resolution, ADR seeding + back-link, the forward-linking stub, and `OSError` handling for post-creation failures. |
| `skills/memory-sync/test_decisions.py` | **rewrite** | `PromoteDefaultPushModeTests` (real bare `origin`) — the coverage whose absence hid the push-mode defect — plus the atomicity and spacing regressions. |
| `skills/adr-workflow/adr.py` | **no-op (knowing)** | Not touched: `promote` calls it by subprocess and now depends on its `adr-NNNN-<slug>.md` filename contract. Nothing on that side guards the contract — inboxed as a follow-up drift test rather than fixed here. |
| `docs/inbox.md` | **new** | The adr.py drift test, and `promote`'s missing `docs_root: "."` coverage. |
| `hosts/**` | **regenerate** | Helper mirror. |

See the spec-level `## Reconciliation sweep` for the full cross-slice table.

### Deviation log

The original slice text is preserved above. Implementation notes:

**§1 — `promote` worked only under `--no-push`, and failed destructively
elsewhere.** Both reviews found this independently; confirmed against
`adr.py`'s source before fixing. The implementation took `adr.py new`'s **last
stdout line** as the created ADR's path. That holds only for `--no-push`:
`adr.py` prints the path (`adr.py:818`) and then keeps printing — `reserved
adr-NNNN-slug on origin/main` on a successful push (`:837`), the PR URL on the
`--pr` fallback (`:400-402`). So in the **default** mode and `--pr` — both
documented in `SKILL.md` — the ADR was created, committed and pushed, and only
*then* did `promote` abort with "reported a path that does not exist". The
lightweight file was indeed untouched, but the repo was not: exactly the
half-promoted state AC6's ordering exists to prevent, and a re-run then hit
adr.py's slug-collision refusal.

This survived because every end-to-end test passed `--no-push`; the one
non-`--no-push` test asserted a *failure* (no origin remote), which concealed
that the success path was untested. Fixed by resolving the ADR by **slug**
(`adr-NNNN-<slug>.md` in the layout's decisions dir — the same filename contract
`adr.py index` relies on) instead of by position in stdout, and by adding
`PromoteDefaultPushModeTests`, which runs a real default-mode promotion against
a real bare `origin` and asserts the ADR actually landed there. Verified the new
test catches the original defect by reverting to the positional parse and
watching it fail.

The off-main detached-worktree path (`adr.py:589,619`) writes no local ADR at
all; the slug glob finds nothing and `promote` now refuses with a message naming
what adr.py said, leaving the lightweight file untouched. That is the correct
degradation, and it is now a refusal rather than a confusing path error.

**§2 — post-creation failures no longer surface as tracebacks.** Everything that
can fail is ordered before the single `path.write_text`, so an `OSError` at that
point means the ADR already exists (and may be reserved on origin/main).
`_cmd_promote` now catches it and names the orphaned ADR, instead of letting a
traceback leave the operator unaware a record was stranded.

**§3 — Scope has no ADR heading.** The ADR template has no `## Scope` section,
so the entry's Scope is folded into `## Context` as a `**Scope:** …` line, with
the template's own placeholder when it was left blank. Defensible reading of
AC2/AC4, but not literally specified — flagged here rather than left implicit.

**§4 — a heading-spacing defect, found by probing rather than by test.** The
`## <heading>` matcher used `\s*$`; `\s` matches newlines, so the match swallowed
the blank line after the heading and the re-added spacing rendered every seeded
ADR section with a doubled blank line. Invisible to the substring assertions the
tests used — caught only by running a real promotion and reading the file.
Extracted `_h2_pattern` (`[ \t]*$`) and pinned it with a spacing regression test.

**§5 — known coupling, deliberately accepted.** `promote` shells `adr.py` as a
subprocess (the documented carve-out from this helper's no-cross-tree-*import*
rule — a subprocess is not an import). Resolution is now by filename contract
rather than stdout text, which removes the fragile coupling §1 exposed, but a
coupling to `adr-NNNN-<slug>.md` remains and nothing on the adr-workflow side
guards it. Recorded here; a drift test on that side is the natural follow-up.

**§6 — `layout.docs_root: "."` is untested for `promote`.** The slice lists it
as an explicit edge case; `lint` and `add-lightweight` have coverage, `promote`
does not. The code path resolves through `project_layout.decisions_dir` exactly
as the covered helpers do, so this is a coverage gap rather than a known defect
— stated plainly rather than silently left unticked.
