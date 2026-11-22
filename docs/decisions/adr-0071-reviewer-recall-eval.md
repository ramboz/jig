---
status: Proposed
dependencies: [adr-0014, adr-0037, adr-0055]
last_verified: 2026-11-21
frame_review: true
---

# ADR-0071: Reviewers are measured offline against jig's own bug history

## Status

Proposed (2026-11-21)

## Context

jig's reviewer prompts are edited often and never measured. Nothing records
whether a prompt change made the reviewer catch more real defects, fewer, or
the same number, or how often a pass raises a blocker on work that was fine.

**What the post says.** The Claude Code team's verification post, read in
[R-002](../research/R-002-claude-code-verification-assessment.md) (item 12),
reviews its reviewers. For each past incident or revert it rebuilds the repo
at review time, writes a one-sentence answer key, and credits only findings
that describe that bug. It uses merged, stable changes as an over-flagging
control and keeps a tuning set apart from a fixed test set. It measures recall
separately for raw findings, after verification, and in the final review, "so
you can see a pipeline losing bugs it found." It tags findings by importance
and tunes recall until the next gain would be overfitting. Item 8 adds:
"Adding a second, more expensive, reviewer on top of the primary one is often
a worse approach than tuning the primary." Tuning needs a measurement.

**What jig runs today.** A slice can face up to six review passes:
compliance and craft always at `REVIEWED`, plus arch, code-health and
design-review when the slice sets their flags. Frame-critique runs at
`READY_FOR_REVIEW` when flagged (`required_passes`,
`skills/_common/review_evidence.py:261-307`). Bug fixes get a bug-review pass
(`required_bug_passes`, `:310`). Each prompt comes from a builder in
`skills/independent-review/review.py` (`build_implementation_prompt` :658,
`build_pr_review_prompt` :919, `build_bug_review_prompt` :1024,
`build_arch_review_prompt` :1085, `build_code_health_review_prompt` :1218,
`build_frame_critique_prompt` :1357, `build_design_review_prompt` :1527).
These prompts keep changing: spec 122-02 added arch-round carry-over, and the
`[spec]`/`[impl]` finding tag was added to `_PR_REVIEW_OUTPUT_FORMAT` on
2026-07-04 (`docs/refinement-todo.md`, "Instrument the
review→learnings→clarify loop"). Nobody measured either change against
defects.

**What jig measures today.** `evals/` scores skill routing only. The scorer
is a stemmed TF-IDF cosine with no model call (`scripts/skill_routing.py:1-30`),
and it runs as a CI step (`.github/workflows/ci.yml:55-61`). No reviewer eval
exists. A model-backed eval has precedent:
`scripts/orchestrator_selection_probe.py` runs `claude -p` under the
developer's own host auth, outside CI. It reports `INCONCLUSIVE` and never
turns that into `FAIL`, and its result routing is unit-tested with injected
runners (`:36-51`, `:113-119`).

**What corpus exists.** The bug board holds 41 records: 38 `DONE`,
2 `REPORTED`, 1 `RESOLVED_ON_MAIN`. Every `DONE` record has a
`## Root cause` section, usually several paragraphs. None states the cause
in one sentence, and none has a structured field naming the change that
introduced the defect. About ten name that change in prose, for example
bug 036 → `dc8d453` (spec 113), bug 039 → `31cbcb4e`, bug 040 → spec 080-02,
and bug 010 → bug 003's fix. Most of these sit in the "Relevant history
inspected" block that spec 091's closure inventory added
(`skills/bug-fix/bug.py:279`, ADR-0037). The repo also holds 597 recorded
verdict files under `docs/specs/*/reviews/`. They cannot stand in for a
measurement. Each is overwritten in place per round
([ADR-0014](./adr-0014-review-evidence-model.md) §4). Of the 25 that record
`applied_skill:`, only 7 used jig's baseline prompt (`none`). So they
describe past pipelines, not the prompts jig ships now.

**Constraints.** The eval adds no review pass and no gate
([ADR-0055](./adr-0055-leanness-lens-folds-into-existing-passes.md)). It adds
no subagent shape (product-vision design principle 3). Token cost is priced
from what the host reports, never from a hand-rolled table (spec 056).
DONE bug records are closed records, so editing them needs owner approval
(spec 102 / [ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md)).
Any servo↔jig evaluation boundary stays parked
([ADR-0022](./adr-0022-pluggable-oracle-boundary.md)).

## Decision Options Considered

### Option A: Status quo — judge reviewer changes by reading them
- **Pros:** Zero cost; no corpus to maintain; dogfooding still surfaces
  egregious misses as bugs.
- **Cons:** A prompt change that loses recall is invisible until a bug ships
  and someone traces it back. Whether a pass is worth its cost is a matter of
  opinion. "Tune the primary" has nothing to tune against.

### Option B: Offline replay against jig's own bug history (recommended)
Build a case corpus from DONE bugs whose defect was introduced by an
identifiable slice or bug fix, with a one-sentence answer key each, plus a
size-matched control set of clean merged slices, split once into a tuning
set and a fixed test set. A dev-time harness replays each code-reviewing
pass's *current* baseline prompt against the repo as it stood when the
defect landed. A separate judge holding the answer key credits matching
findings, and a person audits every credit. The report gives per-pass,
per-stage recall and a flag rate on controls.
- **Pros:** Measures jig's real misses, not imagined ones. Answers "which
  passes earn their cost" from data. Re-scoring is per pass, so the cost
  of a run scales with what changed. It reuses the review envelope jig
  already parses and the `claude -p` precedent, and adds no gate or pass.
- **Cons:** The corpus is small, so results come with wide intervals (see
  Kill criteria). Building cases means backfilling which change introduced
  each defect, plus answer keys. Every run spends model calls and needs a
  person to audit credits. Squash merges mean "review time" can only be
  approximated (see Assumptions).

### Option C: Synthetic seeded-defect benchmark
Inject known defects (mutations, removed guards) into clean slices and
measure how many each pass finds.
- **Pros:** Large N on demand; the answer key comes free with each mutation;
  no history archaeology.
- **Cons:** It measures what the author imagines defects look like. The
  routing eval already names this closed loop as its main weakness
  (`evals/README.md`, "Self-authored cases"). Mutants are mostly local and
  syntactic. jig's real defects are mostly contract and omission defects:
  bug 014's claim scope, bug 023's host resolved from the wrong variable,
  bug 039's missing back-edge. Good scores on mutants would not show recall
  on those.

### Option D: Score the historical verdict records instead of replaying
Run the judge over the 597 recorded verdicts and ask whether the review at
the time mentioned the defect.
- **Pros:** No reviewer model calls; shows directly whether the real pipeline
  lost a bug it saw.
- **Cons:** It cannot evaluate a prompt change, which is the question that
  matters. Records are overwritten per round, so earlier rounds are lost.
  Most records predate today's prompts or applied a user-installed skill.
  Noted as a possible one-off sanity check (Open questions), not the
  mechanism.

### Option E: Add a reviewer, or cut passes, on judgment
- **Pros:** Immediate.
- **Cons:** The post's own finding (item 8) and ADR-0055 argue against
  stacking reviewers. Cutting a pass without recall data trades a known cost
  for an unknown loss. Rejected.

### Option F: Option B, but run in CI on every reviewer-prompt change
- **Pros:** No one has to remember to re-score.
- **Cons:** It needs a model credential in CI and spends tokens on every
  push. Model output varies, so a recall floor would be a flaky gate. It
  becomes a new gate, which ADR-0055 rules out. Kept as an open question once
  noise is measured; not now.

## Recommended Decision

**Option B**, with these rules:

1. **Corpus.** A committed case file under `evals/reviewer-recall/` lists
   bug cases and control cases. A bug case is a DONE bug whose defect was
   introduced by a slice or a bug fix that can be identified. Each case
   records the commit that landed the change, that commit's parent as the
   base, a one-sentence answer key, and a split. Controls are DONE slices
   that have been on `main` long enough to count as stable, that no bug
   names as the source of its defect, and that match a bug case's diff
   size. The split is assigned once by a stated deterministic rule. The
   test set is versioned and frozen. New cases join the tuning set until
   someone deliberately bumps the test-set version.
2. **Where case facts live.** New bug records gain one optional frontmatter
   field, `introduced_by:`, filled at diagnosis when the history search
   finds the change. It is never gated. Legacy DONE records are **not**
   edited. Their backfill lives in the case file, because amending closed
   records needs owner approval (spec 102). Answer keys live only in the
   case file. They are eval data with no use inside an adopter's bug
   lifecycle.
3. **Replay.** A repo-only dev script replays the current baseline prompt of
   each pass that reviews a code deliverable: compliance, craft, arch,
   code-health, and bug-review for cases introduced by a bug fix. It runs
   against a scratch repo that holds only the case's base and case trees,
   with review artifacts stripped. The reviewer runs read-only. The model is
   pinned and recorded. Frame-critique and design-review are out of scope
   for now: frame-critique reviews a spec before code exists, and
   design-review attests servo's verdict instead of finding defects.
4. **Matching.** A separate, tool-less judge call gets the answer key and the
   findings. It does not know which pass or prompt version produced them. It
   must quote any finding it credits. On the test set a person confirms every
   credit, so recall is never inflated by the judge. A person also labels a
   seeded sample of uncredited findings to estimate how many the judge
   missed. Labels are cached, so a later run reuses them.
5. **Metrics.** Per pass, recall at three stages: **found** (any credited
   finding), **blocking** (credited and tagged `[blocker]`, or under a
   non-`pass` verdict for the untagged passes), and **stopped** (blocking
   and the verdict withholds `pass`). Alongside: the flag rate on controls,
   cases only that pass caught, and host-reported cost. Every figure is
   printed as `k/n`; a percentage appears only when `n ≥ 10`.
6. **Re-score nudge.** Each result records a fingerprint of the prompt it
   scored. When a pass's current prompt fingerprint differs from its latest
   result, an advisory notice says so. It never blocks.
7. **Measure, don't cut.** This ADR adds, removes and gates no review pass
   on the eval's numbers. Changing a pass on the strength of a result is its
   own decision, with its own ADR citing the result.
8. **Boundaries.** The live run is on demand, under the developer's own
   host auth, and never a CI step. CI runs only the deterministic parts:
   case-file validation, harness tests with injected runners, and the
   fingerprint notice. The harness never calls servo and defines no
   servo↔jig contract. Apart from the `introduced_by:` field, nothing ships
   to adopters.

**Why B.** It is the only option that measures the prompts jig ships against
defects jig actually had, which is what "tune the primary" needs. The small
corpus is the real risk. The kill criteria turn that risk into a stop rule,
and 126-01 checks it before any model spend.

### Relationship to other decisions

- **Extends [ADR-0014](./adr-0014-review-evidence-model.md)** — reads the
  same `VERDICT / SPECIFIC ISSUES` envelope and the ADR-0014 §3 rule that
  only `pass` clears. Changes no gate, record shape or stage map.
- **Consistent with [ADR-0055](./adr-0055-leanness-lens-folds-into-existing-passes.md)**
  — no new pass, lens or gate; it measures the existing passes.
- **Complements [ADR-0037](./adr-0037-bug-fix-repository-closure-evidence.md)**
  — `introduced_by:` records the result of the "Relevant history inspected"
  search the closure inventory already asks for. No closure gate changes.
- **Does not touch [ADR-0022](./adr-0022-pluggable-oracle-boundary.md)
  (PARKED)** — this is offline dev tooling, not a servo↔jig lifecycle
  boundary. No exit code is read and no oracle is bound. ADR-0022's revisit
  needs "a real eval case". If a replay ever shows a defect that only an
  executed check, not a reading reviewer, could have caught, that case is
  evidence to bring to that revisit. This ADR only reports it.
- **Unrelated to [ADR-0020](./adr-0020-spec-frame-hardening.md)'s rung-3
  trigger for now** — frame-critique is out of scope (rule 3), so this
  produces none of the frame-critique data that trigger asks for.
- **Siblings (Proposed, same promotion from R-002).**
  [ADR-0072](./adr-0072-diff-triggered-review-rules.md) / spec 127 owns
  turning misses into rules (post item 13). A miss this eval finds is an
  input to it, and 127's detectability replay may reuse this harness.
  [ADR-0070](./adr-0070-gate-modes-off-observe-enforce.md) could host the
  re-score nudge as an observe-mode check once built.
  [ADR-0069](./adr-0069-commit-bound-verification-evidence.md) binds evidence
  to commits; results here record the eval checkout's commit for the same
  reason, with no dependency between the two. servo ADR-0053 / spec 048
  applies the same idea, re-scoring on definition change against a frozen
  labelled set, to servo's judges. No code is shared; both borrow the
  human-label audit shape of servo's `judge_audit` (servo spec 008-06).
  Open PR #230 (convention-rule ids) would make per-rule recall possible,
  but this ADR does not depend on it.

## Consequences

**Becomes easier:**
- A reviewer-prompt change can be judged by what it catches and what it
  over-flags on the fixed test set, not by how it reads.
- "Does the arch pass earn its cost?" gets a `k/n` answer. So does "would
  the arch pass have caught this if the slice had set the flag?" (126-03's
  as-configured vs all-on view).
- R-002's open cost question gets an answer: the developer who changes a
  prompt re-scores that pass under their own auth. The cost scales with the
  passes the change touched.
- Some deferred triggers can be fired from data. An example is "Promote
  the `security_review: true` … pass" in `docs/refinement-todo.md`, whose
  trigger is a security regression that compliance and craft missed.

**Becomes harder:**
- Each new bug needs an `introduced_by:` at diagnosis and, to join the
  corpus, an answer key in the case file.
- Every scored test-set run needs a person to audit the judge's credits.
- Model or judge changes break comparability. A result compares only with
  results from the same model id, judge fingerprint and test-set version.
- Small-N numbers invite over-reading. The report's `k/n` rule and the
  measure-don't-cut rule exist to resist that.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Corpus size (unverified, load-bearing).** Of 38 DONE bugs, about ten
  name the change that introduced them today. The rest need blame-based
  backfill. Some are drift against external host contracts that no
  review-time diff could show (e.g. bug 035, a Copilot marketplace
  descriptor jig never had). Estimated eligible pool: 15–25. 126-01
  measures it before any model spend.
- **Review time can be approximated (unverified).** jig lands slices as
  squash commits (titles end `(#NNN)`; the drafting clone is shallow, 64
  commits, so the pre-squash branch tips were not probed). The case state
  is therefore the merged tree with that slice's review artifacts removed.
  Review-round fixes stay in it. That is acceptable, because the defect
  survived every round.
- **The current builders accept old trees (unverified).** Today's
  `review.py` must build prompts against specs as they stood at the case
  commit, including pre-spec-018 embedded slices, which `_slice_source`
  handles. 126-02 records any case it cannot build as `inconclusive`, never
  as a miss.
- **A headless run can be confined (unverified).** The host CLI can limit a
  replay to Read/Glob/Grep and keep user-global configuration, plugins and
  hooks out of it. If it cannot, the replay is not a faithful reviewer run,
  and 126-02 stops.
- **Host-reported cost is available (unverified).** `claude -p` JSON output
  carries usage and cost per run, so cost can be summed without a price
  table.
- **Low training contamination (unverified).** jig's bug records are public.
  A model that has seen them could "find" a bug it remembers. See Kill
  criteria.

## Kill criteria

- **Corpus too small to measure.** If fewer than **10 test-set bug cases**
  survive eligibility (about 15 eligible in total at the planned 1:2
  tuning:test split), shelve the numeric eval. At n = 10 and 50% recall, the
  95% Wilson interval is 0.24–0.76, one case moves recall by 10 points, and
  a paired comparison needs about 6 of 6 discordant cases in one direction
  before a sign test reaches p < 0.05. That is an anecdote set, not a
  metric. Keep the corpus as a qualitative replay set and revisit when the
  bug board grows. Absolute recall becomes useful (±~20 points) at about 20
  test cases.
- **The judge cannot be trusted.** If, on two consecutive audited runs, the
  sampled miss rate of uncredited findings exceeds 0.2 (servo 008-06's
  provisional pass-miss-rate floor), fall back to full human labelling or
  shelve.
- **Noise swamps signal.** If repeated runs of one prompt on one model
  differ by as much as the prompt changes being compared, the eval cannot
  tell changes apart. Stop and re-plan (repeats, or a different matcher).
- **Nobody runs it.** If the re-score nudge stays unanswered across three
  consecutive prompt changes to the same pass, the cost is higher than the
  owner will pay. Demote the nudge and record why.
- **Contamination.** If replays credit findings that the case's diff and
  tree could not support, the model is likely remembering. Restrict the
  test set to defects filed after the reviewer model's training cutoff, or
  shelve.

## Open questions

- **Repeats.** One run per case keeps cost down. Is that enough to compare
  two prompts, or does a decision-grade run need three per case? Settle it
  after 126-02 measures run-to-run noise on the tuning set.
- **Split rule.** A hash split is unbiased in time. A chronological split
  (test = most recent bugs) resists contamination and matches the forward
  question. The draft uses the hash rule; revisit if the contamination kill
  criterion fires.
- **Scoring the historical records once (Option D).** A one-off pass over
  the recorded verdicts of the corpus's own cases would show whether the
  real pipeline saw and lost any of them. Is that worth one judge run as a
  baseline?
- **Frame-critique.** When should cases whose defect sits in a spec or ADR,
  not in code (bug 026's grounding rule scoped in ADR-0020 is one), become
  frame-critique cases? Proposed trigger: 10 such cases.
