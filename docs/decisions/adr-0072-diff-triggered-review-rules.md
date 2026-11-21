---
status: Proposed
dependencies: [adr-0014, adr-0016, adr-0051, adr-0055, adr-0068]
last_verified: 2026-11-21
frame_review: true
---

# ADR-0072: Review rules are structured, diff-triggered, and read-only to the reviewer

## Status

Proposed (2026-11-21)

## Context

[R-002](../research/R-002-claude-code-verification-assessment.md) reads the
Claude Code team's verification post against jig. Four of its mechanisms are
about turning past misses into checks a reviewer actually runs:

- **Diff-triggered checklist (R-002 item 7).** Each item has "a trigger that can
  be read from a diff, a check, and the incidents or PRs behind it". Only the
  matching items run, "usually 3 to 10–so nobody has to memorize past outages."
- **Per-area review guidance (item 8).** A `REVIEW.md` tells the one reviewer
  what to watch, and Code Review reads it from the base branch (item 9).
- **Misses become rules (item 13).** Candidate patterns must occur in at least
  two PRs and be identifiable from a diff; three agents try to disprove each
  one; a human approves it in a PR. Replaying bug finders against an incident
  PR separates detectable bugs from undetectable ones.
- **Prune on a routine (item 15).** "Test suites, verification steps and .md
  files only grow if you let them."

**What jig has today.** Every closed bug leaves a lesson: `bug.py transition
<id> DONE` refuses unless `docs/memory/learnings.md` mentions the bug
(`skills/bug-fix/bug.py:1035-1040`; the check is a substring match in
`_learning_recorded`, `bug.py:726-736`). `learnings.md` is now 1,519 lines and
77 `##` entries, 25 of them headed `Bug NNN:` (probed 2026-11-21). None of it
reaches a reviewer. `review.py` mentions memory in two places only: the
prohibition "Do not write to `docs/memory/`" (`skills/independent-review/review.py:149-150`)
and a pointer to a refinement-todo entry inside the craft output format
(`review.py:903`). The entries are prose for people: they carry no trigger,
so there is no cheap way to pick the three that matter for a given diff, and
loading the whole file into every review would break the context-cost model of
[spec 055](../specs/055-context-cost-discipline/spec.md).

Which review passes run is decided by author-set slice flags
(`required_passes`, `skills/_common/review_evidence.py:261-305`, reading
`arch_review:` / `code_health_review:` / `design_review:` through
`_review_flag`, `review_evidence.py:589`). Nothing in the diff itself selects
a check. Compliance and craft always run for a slice
(`review_evidence.py:293-295`). Compliance walks the slice's acceptance
criteria one by one; craft looks at the change as a whole. On the bug path
the always-run passes are `bug-review` and `craft` (`review_evidence.py:318-322`), and only `bug-review`
has a `review.py` builder — bug craft runs the `pr-review` skill directly
(`skills/bug-fix/SKILL.md:334-339`).

**Constraints this decision must keep.**

- **The reviewer is read-only.** `agents/reviewer.md:4-7` grants only Read,
  Glob and Grep; jig's `CLAUDE.md` says the reviewer "cannot write to memory";
  `review.py`'s `_PROHIBITIONS` (`review.py:142-151`) forbid it. Independence of
  the review is the point of the pattern.
- **The refinement-todo entry "Instrument the review→learnings→clarify loop
  before building it"** (`docs/refinement-todo.md:140-152`) gates a different
  loop: review findings → learnings → a smarter `clarify`. Its trigger is "A
  **spec-level** finding theme recurs across **≥3 distinct specs** AND has no
  existing `learnings.md` entry", and it records "**Count today: 1**". It also
  says "the learnings-*harvest* seam routes through `memory-sync`
  (judgment-gated), **NOT** the read-only reviewer". That trigger has **not**
  fired, and this ADR does not claim it. This decision is owner-directed from
  R-002. It builds the reviewer's *read* path and a harvest that starts from
  bug records the author already writes. It does not build that entry's
  `[spec]`-theme rollup or the clarify grounding pass, and it keeps the entry's
  routing rule: the reviewer never writes.
- **The inbox entry `memory/correction-must-be-read-at-invocation`**
  (`docs/inbox.md:68`, 2026-09-08) asks whether jig's learnings reach the skill
  that needs them, and answers its own design question: "The fix is NOT to
  bloat the hot cache … it is skill-scoped pull at invocation." This decision
  is that pull for one skill, independent review. Recall for other skills stays
  open in that entry.
- **A check the change can edit is broken** (R-002 item 9).
  [ADR-0068](adr-0068-base-anchored-gate-definitions.md) (Proposed) reads gate
  definitions from the base ref. Review rules are gate definitions in that
  sense.
- **No new pass or gate.** [ADR-0055](adr-0055-leanness-lens-folds-into-existing-passes.md)
  folds new lenses into existing passes, and
  [ADR-0056](adr-0056-adversarial-register-quarantine.md) keeps the
  flaw-hunting register inside the review passes.

**Adjacent in-flight work.** Open PR #230 proposes stable ids, MUST/SHOULD
severity and an advisory → enforced promotion state for the rules in
`docs/conventions.md`, rendered into the review passes. Its spec and ADR
numbers are provisional and collide with `main`, so this record cites it by PR
number. Both proposals give rules ids and a two-step lifecycle; they differ in
what the rules are and who may change them (see Recommended Decision §7).

## Decision Options Considered

### Option A: Status quo — prose learnings, flag-selected passes
- **Pros:** No change. `learnings.md` stays a free-form record for people, and
  the →DONE learning gate already guarantees a lesson exists for every bug.
- **Cons:** Lessons never reach the reviewer, so the same class of miss can
  pass review again. Passes are selected by what the author remembered to flag,
  not by what the diff touches. Nothing prunes.

### Option B: Hand the reviewer `learnings.md` (whole, or by keyword search)
- **Pros:** No new artifact; every lesson is reachable.
- **Cons:** 1,519 lines per review is the context cost spec 055 exists to
  avoid. Keyword search over prose is noisy and is not "readable from a diff".
  Many entries are process gotchas that no diff check can catch. A lesson gives
  no single question to answer, so findings stay vague.

### Option C: Per-directory `REVIEW.md` files, read from the base ref (the post's shape)
- **Pros:** Guidance sits next to the code it covers, and code owners own their
  area. If a team also uses Anthropic's Code Review, that tool reads a file of
  the same name.
- **Cons:** The trigger is implicit (the directory), so there is no diff-pattern
  trigger and no provenance field unless jig imposes a schema on a file another
  tool also reads with its own expectations. `scaffold-init` writes only under
  the docs root (`layout.docs_root`, ADR-0033), so it would have to start
  writing into source directories. Selection, base-ref reads, linting and
  pruning all become directory walks.

### Option D: One structured rules file in the memory layer, diff-triggered, written only by `memory-sync` (recommended)
- **Pros:** Per-area scoping comes from path-glob triggers, so one file gives
  the post's per-area effect without scattering files. Each entry carries the
  post's three parts (trigger, check, provenance), so a check always says why it
  is there. The file can be read from the base ref, linted, and pruned in one
  place. Candidates come from bug records, which `bug-fix` already requires; the
  reviewer only reads; promotion goes through `memory-sync` and a human-reviewed
  PR. It rides existing passes (craft, `bug-review`), so no new gate.
- **Cons:** A new file and a format to keep honest. Rules are injected into a
  prompt, so an ignored rule fails silently (measurable only through
  [ADR-0071](adr-0071-reviewer-recall-eval.md)'s eval). A bar of two occurrences
  means a one-off incident never becomes a rule.

### Option E: Fold incident rules into `docs/conventions.md` (PR #230's tagged rules)
- **Pros:** One rule home with one id scheme. PR #230 would already render the
  rules into the review passes.
- **Cons:** Conventions are project rules about how to build. They are
  protected behind the spec-gate (ADR-0011), edited only with owner approval,
  and rendered every time. Incident rules are narrow, diff-scoped and
  frequently pruned. Putting them behind the spec-gate makes every new rule a
  conventions edit, and rendering them all every time defeats the trigger.
  PR #230 is also unmerged.

### Option F: Let the reviewer propose or write rules from its own findings
- **Pros:** Rules would be harvested at the moment of the miss.
- **Cons:** It breaks the read-only reviewer invariant and the refinement-todo
  entry's explicit routing ("NOT the read-only reviewer"). A reviewer that
  writes the rules it is later judged by is the feedback path the independent
  review exists to avoid. Rejected.

## Recommended Decision

**Option D.**

1. **Home.** Active review rules live in one file, `<memory>/review-rules.md`,
   where `<memory>` is `project_layout.memory_dir` (`docs/memory/` by default).
   The file holds only **active** rules. `scaffold-init` emits it empty, with a
   format header, from `templates/docs/memory/review-rules.md.template`.
2. **Entry contract.** One `## <id>` section per rule:

   ```markdown
   ## hook-heredoc-stdin

   - **Paths:** `hooks/scripts/**`
   - **Diff:** `python3 -\s*<<`
   - **Check:** Does a hook script pass a heredoc to `python3 -` while it still needs the hook's JSON on stdin?
   - **Provenance:** bug NNN; PR #NNN; learning "`python3 - <<'EOF'` consumes stdin — fatal for hook scripts"
   - **Added:** 2026-11-21
   ```

   - `id`: a kebab-case slug, unique in the file. Slugs, not numbers, so two
     branches adding rules do not collide on a counter.
   - **Trigger**: at least one of `Paths` (globs in the grammar of
     `governance.path_matches_glob`, `skills/scaffold-init/governance.py:77`) and
     `Diff` (a Python regex matched against added lines). With both, the regex
     must match an added line in a file the globs match. The trigger is
     readable from a diff by construction, because it can only test paths and
     added lines.
   - `Check`: one question, at most 200 characters.
   - `Provenance`: at least **two distinct occurrences** (`bug NNN`, `PR #N`,
     `spec NNN-NN`), plus optional `learning "<heading>"` references that point
     the reviewer to the full lesson. Learning references do not count toward
     the two.
   - `Added`: an ISO date.

   A lint in `memory.py` enforces this contract. The occurrence bar is part of
   the file contract, so it holds however a rule got there.
3. **Candidates live where the evidence is.** A bug record's `## Learning`
   section may carry an optional `**Review rule candidate:**` block with the
   same fields (id, Paths and/or Diff, Check) plus `Seen in:` references to
   earlier occurrences. `bug.py transition <id> DONE` validates the block's
   shape when it is present and refuses a malformed one. It checks shape, never
   quality, like the other teeth gates (ADR-0016). It writes nothing to
   `docs/memory/`. A candidate is never injected into a review.
4. **Selection and injection.** `review.py` reads `review-rules.md` **from the
   base ref** through ADR-0068's `_common` seam (spec 123-03: `resolve_base`,
   `read_at_base`, `modified_on_branch`), so a branch's edit to the rules never
   changes which rules judge it.
   - **Branch edits the file:** the base rules apply, and the prompt says the
     branch edits them, as 123-03 does for review config.
   - **File absent at the base:** no rules apply. A rules file the branch adds
     takes effect after merge. This is 123-03's choice for a `review` block the
     branch adds (its BR-3), not the seam's working-tree fallback for a missing
     file (123-03 AC5). Here the whole file is the definition, so that fallback
     would let the branch judge itself.
   - **No base resolves, or not a git repository:** there is no diff to select
     against, so the prompt says rules are unavailable and why.
   - **Under the seam's deliberate bypass (`JIG_BASE_DEFINITIONS=0`):** the
     working-tree copy is read, as for every base-anchored definition.

   It selects the rules whose trigger matches the diff from the merge base
   with that base: committed and uncommitted tracked changes, plus untracked
   files that are not ignored. It injects at most **10**, ordered by
   occurrence count then id, and names any overflow by id. Injection goes into the **craft** prompt for slices and the
   **`bug-review`** prompt for bugs. Those are the `review.py`-built passes that
   run on every slice and every bug. Each injected rule shows its check and its
   provenance, so the reviewer sees why the check is there (R-002 item 6: "When
   a check pulls in a reviewer, it should say why"). A finding raised from a
   rule carries a `[rule:<id>]` tag. Rules change neither the verdict rule
   (ADR-0014 §3: a matched rule is not a blocker by itself) nor which passes
   run (author flags still decide that).
5. **The reviewer only reads.** The reviewer's tools, prohibitions and prompt
   contract are unchanged. The rules file is written only by `memory-sync`
   (`memory.py`, which owns `docs/memory/`). The file joins
   `governance.PROTECTED_PATHS` (`governance.py:60-67`) next to
   `docs/conventions.md`, so a promotion or a removal is a PR the file's code
   owner approves. This is the post's "a human approves it in a PR", made real
   once branch protection is armed (ADR-0051).
6. **Promotion and pruning go through `memory-sync`.**
   - `memory.py` lists candidates across bug records with their distinct
     occurrences, and promotes a candidate into an active entry only when it
     meets the two-occurrence bar and lints clean.
   - In the jig repo, once ADR-0071's harness exists (spec 126 is dev-time
     tooling and is not shipped to adopters), replaying the candidate against
     its incidents is the recommended detectability check. It is not
     required. This replaces the post's three disproving agents: the
     structural bar plus an empirical replay plus human approval does the same
     job without a new adversarial pass (ADR-0055, ADR-0056).
   - Historic lessons become rules by hand-writing an active entry with its
     occurrences (§2), not by adding candidate blocks to closed bug records.
     Amending a closed record needs owner approval (ADR-0010, spec 102).
   - `record-review` stamps each craft and `bug-review` verdict with
     `review_rules:` (the ids shown, `none`, or `unavailable (<reason>)`). Like
     ADR-0069's stance, `none` is a recorded value. When ADR-0069's prompt-time
     capture (spec 124-02) exists, the ids are captured there when the prompt
     is built. This extends the ADR-0014 §2 verdict schema with one optional
     field, the way `substrate:` did.
   - `memory.py` reports per-rule shown and cited counts from the review
     records, and proposes removal for rules that are never shown, never cited
     when shown, have globs that match no tracked file, or have provenance that
     no longer exists. The `memory-sync` session-end routine surfaces the
     report. Removal is a reviewed edit, and git history is the audit trail.
     Nothing is deleted automatically.
7. **Coexistence with PR #230.** Conventions (`docs/conventions.md`) are
   protected rules about how the project builds, authored under the spec-gate
   and rendered by kind of artifact. Review rules are narrow, incident-derived,
   selected by the diff, and pruned on a routine. The two files stay separate,
   with separate id namespaces. A review rule that turns out to apply to every
   change of a kind is a candidate convention: it moves to `conventions.md`
   through the spec-gate and is removed from `review-rules.md`. A rule never
   lives in both. If PR #230's per-rule fire counts land in `workflow.py
   gate-stats`, §6's report should feed the same surface rather than add a
   second one.

**Relationship to existing ADRs.** This ADR supersedes nothing.
- **Extends** ADR-0014 (one optional verdict field; gate rule unchanged) and
  ADR-0016 (an optional block on the bug →DONE edge, shape-checked).
- **Extends** ADR-0051's protected-path list by one entry.
- **Depends on** ADR-0068 for the base-ref read.
- **Uses** ADR-0071's harness optionally, and ADR-0069's prompt-time capture
  when present.
- **Conforms to** ADR-0055 and ADR-0056 (no new pass; checks stay inside
  review passes) and ADR-0011 (promotion is a deliberate act; the real control
  is PR review).
- **Unrelated to** ADR-0022 C5 (servo oracle boundary). It does not reopen it.

## Consequences

**Becomes easier:**
- A lesson from a closed bug can reach the next review of a diff that touches
  the same area, without anyone remembering it and without loading
  `learnings.md`.
- Each check says why it exists, and the reviewer can open the linked learning
  for detail.
- Rules that stopped earning their place are visible from data (shown versus
  cited), so pruning is a routine, not an archaeology project.

**Becomes harder:**
- One more memory file, with a lint and a template to keep in step.
- Bug authors who want a rule must write a trigger that a diff can match. Some
  lessons cannot be expressed that way, and those stay prose in `learnings.md`.
- Promotion and removal now need code-owner review once governance is armed.
- Prompt size grows by up to 10 rules on a matching diff. No rule matched means
  no change to the prompt.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Grounded (probed 2026-11-21):** the line references in Context; the
  `learnings.md` counts; the fact that `scaffold-init` emits any
  `templates/docs/**/*.md.template` (`skills/scaffold-init/scaffold.py:3978-3988`);
  and that `memory.py summary` counts only glossary and learnings headings
  (`skills/memory-sync/memory.py:533-553`), so a new memory file does not
  disturb it.
- **Sibling draft, not built:** spec 123-03 (DRAFT) defines the seam §4 uses.
  `resolve_base` is spec 103's base rule. `read_at_base` returns the text, its
  source (`base` or `working-tree`), the ref, and a fallback reason.
  `modified_on_branch` counts commits, uncommitted edits and untracked files
  against the merge base. If 123-03 changes that contract, §4 follows it.
- **Unverified, load-bearing:** a reviewer applies injected checks, including
  under a richer user-installed craft skill whose rubric "supersedes the
  baseline buckets" (`review.py:960-968`). ADR-0071's eval can measure this.
- **Unverified:** jig's own bug history holds patterns that clear the
  two-occurrence bar. `learnings.md` has recurring themes, such as stale bases
  (`learnings.md:9`) and fenced-code scanning (`learnings.md:356`), but no
  count was made.
- **Unverified, external:** Anthropic's Code Review reads `REVIEW.md` (R-002
  item 9), but its expected structure is not known here. That is one reason
  jig does not claim the filename.

## Kill criteria

- ADR-0071's eval shows no recall gain on its fixed set with rules injected
  compared with without, or a higher over-flag rate on its control set. Then
  stop injecting and keep the file as reference only.
- After six months with active rules, rules that were shown are cited in
  almost no findings. Then the checks are noise; drop injection.
- No candidate reaches the two-occurrence bar within six months of 127-02
  landing. Then the harvest is dead weight; stop accepting candidate blocks.
- Typical slices routinely hit the 10-rule cap. Then triggers are too broad,
  and the trigger grammar needs rethinking before more rules are added.

## Open questions

- Should a matched rule be able to *require* a pass or a person (for example,
  pull in the arch pass)? The post's item 6 implies checks can pull in
  reviewers, and ADR-0070 §4 and spec 125 leave "review rules that pull in a
  reviewer" to this ADR. This ADR answers it for a check inside an existing
  pass, with its reason shown; requiring an extra pass or a person stays
  open, and pass selection stays flag-driven.
- Should a newly promoted rule start in ADR-0070's `observe` mode (stamped but
  not injected) until its shown rate is known?
- Besides bug records, should candidates come from reverts or maintainer
  rejections? A review-corpus harvest stays gated by the refinement-todo entry
  above.
- Are the pruning thresholds right (draft: a 90-day window; shown at least 5
  times with 0 citations)?
- For teams that also use Code Review, is an export of matched rules into a
  `REVIEW.md` worth offering?
