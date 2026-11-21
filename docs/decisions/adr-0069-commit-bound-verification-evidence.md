---
status: Proposed
dependencies: [adr-0014]
last_verified: 2026-11-21
frame_review: true
---

# ADR-0069: Verification evidence is bound to a commit, and none is a recorded value

## Status

Proposed (2026-11-21)

## Context

Review verdicts bind to the bytes they judged, and every landing records how it was verified, `none` included.

[R-002](../research/R-002-claude-code-verification-assessment.md) reads the
Claude Code team's verification post against jig. Two of its practices are the
subject here (R-002 items 9 and 11): "A passing review on an out-of-date commit
means nothing.", and "we stamp each commit with how it was verified. The stamp
even includes "none" so we can query for commits that weren't verified." A
commit can carry an explanation of why it wasn't verified instead.

What jig records today (probed 2026-11-21 on `87610a9` plus the reservation
commits of branch `ccr-8cc8a4fd-rgnriz`):

1. **The PR body states checks it didn't make.** `render_pr_body`
   (`skills/slice-land/land.py:689`) ends every body with three ticked lines,
   "All ACs pass (full suite green)", "Reviewed by `reviewer` subagent" and
   "Reconciliation review pass" (`land.py:704-707`), whatever the readiness
   checks found. `prepare` runs the tests (`land.py:980`) but does not pass the
   result to the body (`land.py:1048`), and `execute --mode pr` rebuilds the
   body with no check results at all (`land.py:1537`). A readiness report that
   says `Tests: NOT RUN` (`land.py:524-530`) still yields a body that says
   "full suite green". The slice-land skill calls the lines placeholders
   (`skills/slice-land/SKILL.md:255-259`).
2. **Review records say when, not what.** A verdict file carries `slice`,
   `pass`, `verdict`, `reviewer`, `reviewed_at`, `prompt_source`
   ([ADR-0014](./adr-0014-review-evidence-model.md) §2;
   `skills/_common/review_evidence.py:75`), overwritten per (slice, pass)
   (§4). Nothing names the commit or the bytes the reviewer saw.
   `prompt_source` is free text and abbreviated in practice
   (`docs/specs/122-arch-pass-escalation-and-rounds/reviews/slice-01-compliance.md`:
   `… 122-01 <6 deliverables>`), so the deliverable list can't be recovered
   from it.
3. **Staleness is a named deferral, narrowed once.** `docs/refinement-todo.md`,
   "Decision: Code-staleness hard-gating for review evidence": "It does NOT
   detect *stale-but-passing* evidence — a `pass` artifact whose `reviewed_at`
   predates a later change to the slice's deliverable." Its trigger: "First
   incident where stale-but-passing evidence lets a materially-changed slice
   transition to `REVIEWED`/`DONE` without re-review. Until then, staleness is
   at most a `check-reviews` warning, not a gate." Bug 039 gated the back-edge
   case: a review back-edge stamps `review_reopened_at` and older verdicts stop
   clearing (`review_evidence.py:119`, `:142`; ADR-0014 Amendments
   2026-10-04). The general case, a deliverable changed after a `pass` with no
   back-edge, is still invisible, and the promised warning was never built
   (`skills/independent-review/SKILL.md:378-380`: "deliberately NOT checked").
4. **Bug records carry days, not commits.** `bug.py` stamps
   `red_confirmed_at` / `green_confirmed_at` with a date
   (`skills/bug-fix/bug.py:969`, `:1008`).
5. **One place already binds evidence to code.** Spec 118's worked example
   records `code_revision` (`git rev-parse HEAD`) and a `runtime-sha256:`
   digest over a sorted per-file manifest of the exercised sources, which
   covers uncommitted edits
   (`skills/spec-workflow/worked-example-behavioral-verification.md:45-60`).
   It is an example in prose, not a shared helper.
6. **Bypasses leave only a local trace.** Spec 078 writes `gate_bypassed`
   events to `.claude/skill-usage.jsonl`
   (`skills/_common/gate_telemetry.py:24`), which is gitignored
   (`.gitignore:1`). A slice landed with `JIG_REVIEW_EVIDENCE_GATE=0` leaves
   nothing in the repository's history.
7. **No jig helper marks a commit.** No trailer, no git note, no git hook
   (jig's hooks are host hooks, `hooks/hooks.json`). `land.py` creates no
   commits: direct mode pushes `<branch>:main` (`land.py:1454`); PR mode pushes
   and runs `gh pr create` (`land.py:1545-1549`). `bug.py` commits only its
   reservation (`bug.py:411`); bug fixes are committed by hand and landed with
   slice-land only "if a formal landing checklist helps"
   (`skills/bug-fix/SKILL.md:367-373`).

How commits reach jig's own `main` constrains where a stamp can live
(probed on the fetched history):

- **Squash merges, PR description as the message.** No merge commits in the
  fetched history; each PR is one `(#NNN)` commit whose body is the PR
  description, followed by GitHub's `---------` line and the consolidated
  `Co-authored-by:` paragraph (`87610a9`, `1ccd3cd`).
- **Branch-commit trailers don't survive.** PR #230's branch commits carry
  `Claude-Session:` trailers (`05d123f`); no squash commit on `main` does.
- **A stamp in the description is not a git trailer after the squash.**
  `git interpret-trailers --parse` on that message shape returns only
  `Co-authored-by` (git 2.43), because GitHub's paragraph is the last one. A
  query has to read message lines, not `%(trailers)`.
- **Merged descriptions are hand-written.** `87610a9` opens with
  `## What changes`, not `render_pr_body`'s `# Slice …` / `## Context` layout.
  Anything land.py puts in a PR body survives only if the author keeps it.

## Decision Options Considered

Two questions: what a review record is bound to (**identity**), and where a
landing's stamp lives (**home**).

### Identity

#### Option I-1: Status quo, `reviewed_at` only
- **Pros:** Nothing to build. Bug 039's back-edge rule already covers the case
  where the lifecycle itself reopens review.
- **Cons:** A `pass` outlives any later edit that takes no back-edge, and the
  record can't say what was reviewed.

#### Option I-2: Commit SHA only
- **Pros:** One field; `git diff <sha>` shows what changed since.
- **Cons:** Rebase, amend and squash change SHAs without changing content, so a
  SHA comparison calls fresh evidence stale. Reviewers usually review an
  uncommitted tree mid-slice, which a SHA doesn't cover.

#### Option I-3: Last-change date (the reuse the refinement entry suggests)
- **Pros:** Existing code (`workflow.py stale`).
- **Cons:** `_file_modified_iso` returns a day (`git log -1 --format=%cs`,
  `skills/spec-workflow/workflow.py:2893-2909`); reviews and fixes happen the
  same day. Blind to uncommitted edits.

#### Option I-4: Content digest of the deliverables, commit as provenance
Spec 118's shape: a `sha256:` over a sorted manifest of per-file hashes of the
working-tree bytes, plus the HEAD commit.
- **Pros:** Content-exact; unaffected by rebase, squash or amend; covers
  uncommitted edits. The commit still tells a person where to look.
- **Cons:** The record must list its deliverables. Files the lifecycle edits
  (the slice file, the review records) must be left out or every record looks
  stale. A `pass` recorded after "fix the nits, then record" shows as stale,
  which is accurate but new.

### Home

#### Option H-1: Status quo, no stamp
- **Pros:** No history change.
- **Cons:** "Which commits weren't verified" has no answer; bypassed landings
  look like any other.

#### Option H-2: A trailer on every commit
- **Pros:** The post's literal shape.
- **Cons:** Dropped by jig's squash merges (probed). jig doesn't create the
  agent's commits and ships no git hooks. Mid-slice commits have no evidence
  to stamp yet.

#### Option H-3: git notes (`refs/notes/…`)
- **Pros:** No change to history; attaches to any commit after the fact.
- **Cons:** Not pushed or fetched by default; GitHub doesn't show them; keyed
  to SHAs, so lost on GitHub's squash and rebase merges.

#### Option H-4: Stamp lines in the landing unit's message only
The PR body for squash merges, a stamp commit at the branch tip otherwise.
- **Pros:** Visible in `git log`. Anyone can write one by hand on any commit.
- **Cons:** In jig's own flow the PR body is rewritten by hand (probed), so the
  stamp is lost unless the author keeps it; squash-message settings vary.

#### Option H-5: An in-tree landing record only
A small file per landed slice, e.g.
`<docs>/specs/NNN-slug/verification/slice-NN-landing.md`.
- **Pros:** It is content, so it survives every merge strategy and any PR body
  edit. Direct-mode landings, which have no PR body, get a record at all.
- **Cons:** Can't cover a commit outside a slice; not visible in `git log`.

#### Option H-6: H-5 as the durable copy, mirrored as message lines by one renderer
- **Pros:** H-5's survival plus H-4's visibility, and hand stamps on commits
  outside any slice still work.
- **Cons:** Two copies, kept equal by rendering both from one function; a hand
  edit can make them differ.

## Recommended Decision

**I-4 for identity, H-6 for home.**

1. **Review records bind to content.** The prompt builders that take
   deliverable paths capture the HEAD commit, the deliverable list and their
   digest when the prompt is built, which is the moment closest to what the
   reviewer reads. `record-review` writes `reviewed_commit`,
   `deliverable_digest` and `deliverables` into the record. The digest is
   spec 118's shape over working-tree bytes. The slice's own `spec.md` and
   slice file and anything under `reviews/` are excluded, because the
   lifecycle edits them. ADR-0014's required fields and §3 gate rule are
   unchanged; a record without the new fields is **unbound**.
2. **Freshness is reported, not gated.** Each bound record is `fresh` or
   `stale`; a stale one names `git diff <reviewed_commit> -- <deliverables>` as
   the way to see what changed. `check-reviews`, `workflow.py transition`,
   `land.py prepare` and the PR body show it; no exit code changes. Making it
   block is a mode decision for [ADR-0070](./adr-0070-gate-modes-off-observe-enforce.md)
   (observe, then enforce). This ADR adds no env var or mode switch, and the
   refinement entry's trigger still decides whether hard gating is warranted.
3. **Landing evidence is rendered, never asserted.** The PR body's Test plan
   derives each row from evidence: the test run with the commit it ran on, one
   row per required review pass, the verification scenario's outcomes. What
   wasn't checked says `NOT RUN` or `NOT RECORDED`.
4. **Every landing carries a stamp, and `none` is a value.** The vocabulary is
   closed: `Verified-by: tests | review | scenario | verify | none`. `none`
   stands alone; `verify` is reserved for the verify skill
   ([ADR-0073](./adr-0073-repo-verify-skill-contract.md)) and not emitted until
   that defines its evidence. `Verified-at: <sha>` names the commit the
   evidence describes; `Verification-note: <one line>` is the optional
   explanation. `land.py execute` writes the landing record and commits only
   that path (the precedent is `workflow.py:4312-4319`). The commit message
   carries the same lines plus `Verified-commits: N` so the commits it covers
   on a fast-forward are known. In PR mode the body ends with the same lines.
5. **One read-only query.** `land.py stamps` lists first-parent commits with
   their stamp, `none` and its note, `covered by <sha>`, or `unstamped`. It
   reads landing records first and message lines second, matching lines
   anywhere in the body because GitHub's squash leaves them outside git's
   trailer block.
6. **The stamp is a record, not a gate.** A `none` landing proceeds exactly as
   today. Blocking commits or landings that lack verification is ADR-0070's
   question.

**Relationship to other decisions.**

- **Extends [ADR-0014](./adr-0014-review-evidence-model.md).** Adds optional
  §2 fields; §3 (only `pass` clears) and §4 (overwrite in place) are
  unchanged. It builds the interim warning ADR-0014's Scope and the refinement
  entry describe ("at most a validator warning"), using a digest instead of
  the git-log/mtime reuse they suggest. ADR-0014's text is not amended here;
  pointing its Scope at this ADR would need owner approval (ADR-0010,
  spec 102). Not a supersession.
- **Bug 039's amendment to ADR-0014 stays as is.** The back-edge rule still
  gates; digest freshness is a separate, report-only check.
- **[ADR-0070](./adr-0070-gate-modes-off-observe-enforce.md) (Proposed,
  spec 125)** owns modes. Freshness, and any "unverified landing" check, are
  candidates for its observe mode.
- **[ADR-0073](./adr-0073-repo-verify-skill-contract.md) (Proposed, spec 128)**
  defines what earns the `verify` token.
- **[ADR-0011](./adr-0011-spec-gate-model.md)**: consistent. Both mechanisms
  are deliberateness signals; neither claims to be a control.
- **Spec 078 (gate-bypass telemetry)**: complementary. Telemetry counts
  bypasses locally; the stamp leaves the result in shared history.
- **PR #230's fix-evidence separation** (clause 3, "green is new evidence on
  the fix revision"): compatible; both key evidence to a revision.
- **servo spec 046** (commit-bound evaluation evidence) is the same idea for
  servo's run state; the digest shape is offered, not imposed.

## Consequences

**Becomes easier:**
- A PR body or landing record can be read at face value: a tick means a
  recorded check.
- "Which commits on `main` weren't verified, and why" is one command.
- A slice landed through a bypassed gate shows a partial or `none` stamp in
  history, not only in a local log.
- Review evidence that predates a later edit shows up before landing.

**Becomes harder:**
- Every landing adds one small commit (the landing record). With squash merges
  it folds into the squash commit; with direct landings it stays visible.
- "Fix the nits, then record" now shows the record as stale. Either re-run the
  pass or accept the flag (Open question 1).
- Prompt builders write one more transient sidecar per (slice, pass),
  gitignored like `reviews/.candidates/` (`.gitignore:47-51`).
- Two copies of the stamp exist; a hand edit can make them disagree, and the
  record wins.

## Assumptions

- **GitHub merge settings beyond jig's own were not probed.** jig squashes
  with the PR description (probed). The "commit messages" and "blank"
  squash settings, and rebase merges, were not exercised; the in-tree record
  is what keeps the stamp across them.
- **Rebase merges keep commit count and order**, so `Verified-commits: N`
  still covers the right commits. Not probed.
- **The reviewer reads the deliverables soon after the prompt is built.** An
  edit between prompt build and the reviewer's read would be missed.
- **ADR-0070 will offer a mode that an existing report-only check can be
  registered under.** ADR-0070 is Proposed and spec 125 is not drafted yet.

## Kill criteria

- Most bound records show `stale` in normal use (noisy deliverable lists, or
  the record-after-fix habit persists). Then move the capture point or narrow
  the digest before anything enforces it.
- Adopters reject the landing commit (history noise, or branch rules refuse
  it) and the PR-body copy is routinely lost. Then revisit H-3 or H-4.
- Nothing reads the stamps (no person, no spec 126 revert analysis, no
  spec 125 check) within two releases of landing. Then prune it, as R-002
  item 15 says.

## Open questions

1. Should the authoring rule change to "record the verdict as returned; if you
   then change a deliverable, re-run the pass", or is a stale flag on a
   nits-only fix acceptable?
2. Amend an unpushed branch tip instead of adding a landing commit? It
   avoids the extra commit but rewrites history whenever the tip is already
   pushed.
3. Bug fixes don't go through `land.py`. Should `land.py` take a bug record
   as a target so bug fixes get a stamp? Today they show `unstamped`.
4. A PR that gains commits after `execute --mode pr` carries a stamp for an
   earlier tip (`Verified-at` shows which). Should re-running `execute`
   refresh the record and the body?
5. Should `review` require bound records once most records are bound, or keep
   counting unbound (pre-ADR) records as today's gate does?
