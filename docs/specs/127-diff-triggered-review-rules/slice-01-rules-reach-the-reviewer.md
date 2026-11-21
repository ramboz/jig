---
status: DRAFT
dependencies: [adr-0072, adr-0068, 123-03]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 127-01 — rules-reach-the-reviewer

**Goal:** a project has one structured, linted `docs/memory/review-rules.md`.
When a slice's or a bug's diff matches a rule's trigger, the craft or
`bug-review` prompt asks the reviewer that rule's check and says which
incidents it comes from. The rules are read from the base ref, so the change
under review cannot edit them.

**Decision:** [ADR-0072](../../decisions/adr-0072-diff-triggered-review-rules.md)
§1, §2, §4 and §5; spec 127 D2–D5.

**DoR:**
- ⬜ ADR-0072 is Accepted.
- ⬜ Spec 123-03's `_common` seam (`resolve_base`, `read_at_base`,
  `modified_on_branch`) is DONE, and its contract matches spec A8. If it
  differs, reword AC3 and AC4 to the real contract before
  READY_FOR_IMPLEMENTATION.
- ✅ The merge-base computation exists (`_touched_files_block`, spec A3).
- ✅ The craft builder (`build_pr_review_prompt`, `review.py:919`) and the
  bug-review builder (`build_bug_review_prompt`, `review.py:1024`) are the
  only two prompts this slice changes.
- ✅ `governance.PROTECTED_PATHS` and its mirror tests exist (spec A7;
  `skills/scaffold-init/test_governance.py`,
  `skills/scaffold-init/test_scaffold_governance.py`).

**Acceptance Criteria:**

1. **The file contract is parsed and linted.** A new leaf module
   `skills/_common/review_rules.py` parses `<memory>/review-rules.md` into
   entries `{id, paths, diff, check, provenance, added}` and ignores fenced
   code blocks and the header blockquote. `python3 skills/memory-sync/memory.py
   rules-lint` exits `0` on a valid file. It exits `1` and names the id and line
   for each problem:
   - a duplicate or non-kebab-case id;
   - neither `Paths` nor `Diff`;
   - a `Diff` that does not compile as a Python regex;
   - a missing `Check`, or one longer than 200 characters;
   - fewer than two distinct occurrence refs (`bug NNN`, `PR #N`, `spec NNN-NN`)
     in `Provenance` — `learning "…"` refs do not count;
   - a missing or non-ISO `Added` date.
2. **It is scaffolded.** `templates/docs/memory/review-rules.md.template`
   renders a file with a blockquote header that explains the format (example
   in a fenced block, no `##` instructional headings) and zero rules. A fresh
   `scaffold-init` output passes `rules-lint`. `memory.py summary` output is
   unchanged.
3. **Rules are read from the base ref.** `review.py` reads the rules file
   with 123-03's `read_at_base`.
   - **Branch-only edits:** a rule added or edited only on the branch or in the
     working tree does not change which rules are selected.
   - **Branch modifies the file:** when `modified_on_branch` reports it, the
     prompt says the branch edits the review rules, that the base rules were
     applied, and that the edit is in scope for review.
   - **File absent at the base:** no rules are selected, even though the seam
     would fall back to the working tree (ADR-0072 §4). If the branch adds the
     file, the prompt says its rules apply after merge.
   - **No base resolves, or not a git repository:** no selection runs. The
     prompt carries one line, `Review rules: unavailable (<reason>)`, with
     123-03's reason (`no_base` or `not_a_git_repo`; `absent_at_base` is the
     case above).
   - **Under `JIG_BASE_DEFINITIONS=0`:** the working-tree copy is read, as for
     every base-anchored definition.
4. **Selection matches the diff.** The changed set is taken against the merge
   base with `resolve_base`'s ref:
   - tracked changes from the merge base to the working tree, committed or not;
   - plus untracked, non-ignored files, whose every line counts as added.

   A rule matches as follows:
   - `Paths` only: when any changed path matches a glob.
   - `Diff` only: when any added line matches the regex.
   - Both: when an added line in a glob-matched file matches the regex.

   An entry the parser cannot use is skipped and named in the prompt; the
   review is not blocked by it.
5. **Matched rules are injected, capped, with provenance.** When at least one
   rule matches, the craft prompt (slices) and the `bug-review` prompt (bugs)
   gain a `## Review rules matched by this diff` section. It lists each rule's
   id, its check, and "why: <provenance>". It holds at most 10 rules, ordered
   by distinct occurrence count (descending) then id, and names any overflow by
   id. The section tells the reviewer to:
   - answer each check against the diff;
   - tag a finding raised from a rule `[rule:<id>]`: beside its `[blocker]` /
     `[nit]` tag in the craft envelope, and at the start of the entry in
     `bug-review`'s untagged envelope (`_OUTPUT_FORMAT`, `review.py:204-221`);
   - judge the verdict by the pass's usual rule: a matched rule is not a
     blocker by itself (ADR-0014 §3);
   - open a cited learning only if it needs the detail.

   The section is present whether or not a richer craft skill resolved, and
   says the rules apply in addition to that skill's rubric.
6. **No match, no change.** With no matching rule, or an empty rules file, the
   craft and `bug-review` prompts are byte-identical to today's. The
   compliance, arch, code-health, reconciliation, frame-critique and
   design-review prompts are byte-identical with or without matching rules.
7. **The reviewer stays read-only.** `_PROHIBITIONS`, `agents/reviewer.md` and
   the reviewer's tool list are unchanged. A test pins that no `review.py`
   code path writes to the rules file.
8. **The file is a protected path.** `governance.PROTECTED_PATHS` lists
   `docs/memory/review-rules.md`, mirroring how `docs/conventions.md` is
   listed. The scaffolded CODEOWNERS and `scaffold.json.protected_paths` mirror
   it, and the existing governance tests are updated. If 123-01 has landed,
   jig's own governance plane (the four artifacts 123-01 pins) is
   re-rendered in the same change, so 123-01's drift test stays green. The
   generated host packages are rebuilt, so
   `scripts/build_host_packages.py --check` passes.

**Edge cases to cover explicitly:**
- A slice whose diff edits `review-rules.md` itself: selection uses the base
  copy, and the prompt carries AC3's "branch edits the review rules" note.
- Same glob grammar as `governance.path_matches_glob`: `dir/**` matches `dir`
  itself, and `*` stops at `/`.
- A `Diff` regex that would match a removed line but no added line does not
  match.
- An embedded `## Slice` section with no slice file: selection still runs on
  the project diff.
- `resolve_base` resolves no ref: AC3's unavailable line, with no crash.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: if this slice closes the spec,
      compress the Active-specs entry; otherwise leave it.

**Anti-horizontal-phasing check:** after this slice, an owner can merge one
hand-written rule. The next slice or bug whose diff touches that area gets a
review that asks the rule's question and names the incidents behind it, with
no other step from anyone.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TBD — not yet implemented (recorded, not built)._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | _TBD — regenerate by `workflow.py status-board` at close._ |
| `docs/architecture.md` | `updated` | _TBD — new `_common/review_rules.py` leaf and the base-ref read path._ |
| `skills/independent-review/SKILL.md` / `docs/workflow.md` | `updated` | _TBD — describe the matched-rules section of the craft / bug-review prompts._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | _TBD — new memory template; check primer mentions of the memory layer._ |
| `docs/inbox.md` | `updated` | _TBD — note on `memory/correction-must-be-read-at-invocation` that the review skill now pulls rules at invocation; the entry stays open for other skills._ |
| `docs/memory/**` | `no-op` | _TBD at close._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TBD at close._ |
