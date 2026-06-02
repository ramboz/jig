---
status: DONE
skill: pr-review
tier: 1
---

# Spec 012: pr-review (Tier 1)

## Overview

Introduce `pr-review` — the fourth Tier 1 skill — as a **lightweight default**
PR review codified inside jig. The skill auto-triggers on PR-review prompts
("review this PR", "check this diff", "what do you think of these changes")
but its description explicitly defers to richer user-installed PR-review
skills, so a user who already ships their own `~/.claude/skills/pr-review`
(multi-persona, language-specific references, etc.) is not shadowed by jig's
baseline.

This is **not** a port of the heavyweight personal `pr-review` skill. It is
intentionally slim: structured gather → scope summary → blockers/nits split →
strengths call-out. No language-specific reference files, no five-persona
matrix, no Adobe-security-suite coupling. The goal is "jig users get *some*
PR review out of the box; power users keep their own thing."

This spec is the long-deferred Tier 1 candidate parked in
[`docs/inbox.md`](../../inbox.md) on 2026-05-12 under the multi-persona-reviewer
entry: "ship as separate `/jig:arch-review` and `/jig:pr-review` skills, ported
and slimmed from personal versions, **when slice-land creates a PR-shaped
artifact to review**." Slice 007-01 (land-prepare) shipped that artifact —
`land.py prepare --mode pr` emits a PR body file — so the gate is open.

## Why now

- **Gate is open.** Slice 007-01 ships `land.py prepare --mode pr`, which
  emits a PR-shaped artifact (PR body file + push/`gh pr create` checklist).
  pr-review now has a concrete surface to act on.
- **Last unblocked Tier 1 candidate.** Per CLAUDE.md sprint focus, the
  remaining Tier 1 candidates were `pr-review` (this spec) and
  `local-dev-parity` (still no signal — jig is pure-Python, no external deps,
  no CI). Shipping `pr-review` closes the Tier 1 sprint for now.
- **Skill router is expected to handle the supersede-by-user-skill pattern
  via description-based routing.** Claude reads all available skill
  descriptions and picks the best match. We hypothesize that an explicit
  deferral hint in jig's description ("if you have another pr-review skill
  installed, use that instead") will cause the router to prefer the
  more-specific user skill. **This hypothesis is load-bearing and untested.**
  The `anthropic-skills:claude-api` `SKIP:` precedent is *not* a direct
  match — SKIP filters when a skill shouldn't fire at all, not when it
  should yield to a peer on the same shape. The routing-dogfood step in
  DoD (AC #4 of this slice's DoD list) is the empirical test. If the
  dogfood fails, the fallback path is documented in AC #9 below
  (ship with `disable-model-invocation: true` and document explicit
  invocation only). We accept this risk because the alternative
  (filesystem probing of `~/.claude/skills/`) is more fragile across
  marketplace / user / project install scopes.
- **PR-shaped review is dogfooded.** Every reconciled slice in this repo has
  passed through `agents/reviewer.md` (spec-compliance review). The PR-shape
  is similar but distinct — diff-centric rather than spec-centric. Codifying
  the diff-centric path matches what the personal `pr-review` skill already
  does in practice; we just ship a slim version of it.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| P — Path | (a) SKILL.md only / (b) SKILL.md + `pr_review.py gather` helper / (c) full multi-persona port. | **(a) SKILL.md only this slice.** No helper. pr-review is fundamentally a judgment skill — what little determinism is needed (`git diff`, file-type detection) Claude can run inline. If a "gather" friction point surfaces three sessions in a row, slice 012-02 can add the helper. (c) is explicitly out of scope per the "lightweight default" framing. |
| I — Interface | How does the skill defer to a richer user skill? Filesystem probe? Plugin scope detection? Description-level hint? | **Description-level hint (hypothesis).** The skill router picks the best description match against the request. We expect an explicit "if you have another PR review skill installed, use that instead" line in the frontmatter `description` to cause the router to prefer the more-specific user skill. **This is untested**; the routing-dogfood in DoD validates it before DONE. We're choosing this over filesystem probing because the alternative is more fragile (plugin install paths vary across marketplace / user / project scopes, same concern flagged for `security_lens` in the inbox); if the hypothesis breaks, AC #9 specifies the fallback (ship explicit-invocation-only). |
| D — Data | What inputs does the skill consume? Full repo / GitHub URL / pasted diff / `land.py` PR body file? | **Three input modes, ordered by richness:** (1) full repo context (preferred — `git diff main...HEAD`), (2) `land.py prepare --mode pr` output (the PR body file + branch name), (3) pasted diff. No GitHub MCP coupling in this slice (jig has no current MCP dependency; adding one for the baseline would over-scope). |
| R — Rules | What does the lightweight review actually check? | **Four-section output:** (a) Scope summary (what the PR is), (b) Blockers (must-fix; explicit list), (c) Nits (nice-to-haves; explicit list), (d) Strengths (what's well done — keeps the tone constructive). No persona matrix. No language-specific reference files. The depth-vs-breadth call leans firmly toward breadth (catch the obvious) over depth (catch every Java-specific antipattern). Anyone wanting depth installs a richer skill. |
| S — Spike | None required — the shape is well-established by the user's existing personal skill and by `agents/reviewer.md`. | — |

## Out of scope for spec 012 (any slice)

- **Multi-persona review** (security / SRE / product / etc.). Inbox entry
  from 2026-05-12 considered this and parked it. If revisited, it belongs in
  a separate `/jig:arch-review` skill, not in this baseline.
- **Language-specific reference files** (`nodejs-typescript.md`,
  `java-aem.md`, `python.md` in the user's personal skill). Slim baseline
  ships none — the general framework applies to any language.
- **GitHub MCP integration / `gh` CLI auto-invocation.** Slice 012-01
  reviews what Claude can already see (current repo state + diff). Auto-fetching
  PR metadata from GitHub MCP is deferred — premature coupling.
- **`security_lens` integration with `adobe-security-suite`.** Separate
  concern, parked in inbox 2026-05-12. If `security_lens` ever lands, it plugs
  into this skill via a follow-on slice; it does not block 012-01.
- **Auto-trigger on every git commit / PR-mode `slice-land` run.** Skill
  invocation stays user-driven (auto-routing by description match, not by
  hook firing).
- **Comment-back-to-GitHub** (writing review comments to the actual PR via
  `gh`). Out of scope; the skill produces a structured markdown report, the
  user does the posting.

---

## Slice 012-01 — pr-review-skill

**STATUS: DONE**

**Goal:** Ship `skills/pr-review/SKILL.md` as an active, auto-triggering
skill with a description that **explicitly defers to user-installed
pr-review skills**. Body codifies a lightweight, four-section review
(scope / blockers / nits / strengths). No helper. No language-specific
references. CLAUDE.md skills table promotes the skill to active.

**DoR:**
- ✅ Slice 007-01 (`land.py prepare`) DONE — the PR-shaped artifact
  exists. pr-review has a concrete input mode to document.
- ✅ Personal `pr-review` skill exists at `~/.claude/skills/pr-review/SKILL.md`
  — dogfood reference for routing-deferral (when both jig's slim version and
  the personal richer version are present, the richer one should win).
- ✅ `agents/reviewer.md` already encodes spec-compliance review; the new
  skill explicitly demarcates itself from that (PR-shape vs. spec-shape,
  skill-vs-subagent — SKILL.md's "When to use vs. when to defer" section
  per AC #2 must be sharp on this boundary).
- ✅ Precedent for active-SKILL.md-only ships exists (the personal
  `pr-review` itself has no helper); jig's `contracts` ships SKILL.md-only
  but as a stub. Slice 012-01 is the **first non-stub active jig skill
  without a `.py` helper** — that's worth flagging in the deviation log but
  not a blocker.

**Routing-dogfood prerequisites** (must hold before the dogfood step in DoD
can run honestly):
- The user's personal `~/.claude/skills/pr-review/SKILL.md` is loaded by the
  current Claude Code session. Verify by checking its description appears
  in the available-skills list before invoking the dogfood prompt.
- Jig is installed (not just present in worktree) via the `jig-dev`
  marketplace — `scripts/verify_install.py` must return a fresh pass.
  Address the install-snapshot-lag inbox entry from 2026-05-13: do not
  trust a stale install; reinstall if the slice has been modified since
  the last verify.
- The dogfood is run **at least twice from a freshly-restarted session**,
  on two different prompt phrasings (one from the AC #1 trigger list,
  one paraphrased — e.g. "can you look at the changes I just made?").
  A single-run pass may be a coin-flip; consistent winner across both
  runs is required.

**Acceptance Criteria:**

1. **`skills/pr-review/SKILL.md`** exists with active frontmatter:
   - `name: pr-review`
   - `user-invocable: true`
   - **No** `disable-model-invocation: true` (this skill auto-triggers; if
     the routing-dogfood in DoD fails, AC #9's fallback flips this to
     `true`).
   - `description: >` is a folded scalar that contains, in order:
     - One sentence stating what the skill does, using the exact phrasing:
       "Lightweight default PR review for jig projects — scope summary,
       blockers vs. nits, and strengths call-out."
     - The trigger phrases the router should match on: "review this PR",
       "check this diff", "review these changes", "pre-review before I share",
       "what do you think of this PR", "review the diff on this branch".
       (The last phrase replaces an earlier draft's "code review this branch"
       which overlapped semantically with the spec-compliance review that
       `agents/reviewer.md` performs — disambiguation is intentional.)
     - An **explicit deferral hint**, using this exact phrasing: "If you
       have another `pr-review` skill installed (e.g. a richer personal
       reviewer at `~/.claude/skills/pr-review`), prefer that — jig's
       version is a slim baseline." _(Revised during reconciliation: the
       earlier draft prescribed "personal multi-persona reviewer", which
       contradicted AC #3's `DescriptionBoundsTests` anti-greediness
       pinning that forbids "multi-persona" in the description. Resolved
       in favor of anti-greediness — see deviation log §1.)_
     - A `Do not use for:` clause naming three exclusions, in this exact
       order, with this exact phrasing: (a) "spec-compliance review of a
       finished slice (use `/jig:independent-review` instead)", (b)
       "standalone architecture-doc review (jig does not ship an
       arch-review skill today)", (c) "single-line typo fixes or trivial
       whitespace changes (just merge and move on)".

2. **SKILL.md body** has the following sections, in order:
   - **What this skill does** — one paragraph, lightweight framing.
   - **When to use vs. when to defer** — explicitly distinguishes three
     things the reader might confuse with this skill: (a) a richer
     user-installed `pr-review` skill (defer if present); (b)
     `/jig:independent-review` (spec-compliance review of a slice — a
     *skill*, different shape); (c) `agents/reviewer.md` (the reviewer
     *subagent* spawned via Task — different invocation primitive, same
     conceptual neighborhood). The section must explicitly say *when*
     to reach for each.
   - **Inputs** — three modes: (1) full repo context (preferred), (2)
     `land.py prepare --mode pr` output (links to slice 007-01), (3) pasted
     diff. Notes the limitations of each mode. **Explicit note**: a
     GitHub-PR-URL-only input shape (no local repo, no MCP integration)
     is NOT supported by this baseline — users in that case must paste
     the diff manually (the URL alone cannot be fetched by the baseline,
     by deliberate scoping per Out-of-Scope item 3).
   - **Review structure** — the four sections of the output (scope / blockers
     / nits / strengths) with one or two example lines per section, plus
     the worked example required by AC #10 (one diff fragment + one
     four-section review).
   - **Gotchas** — explicit notes on (a) the deferral hint behavior, (b) the
     scope of "lightweight" (no language-specific deep-dives), (c) the
     relationship to `agents/reviewer.md` (different gate), (d) what to do
     if the routing-dogfood failed and AC #9 fallback was applied
     (mention that the skill is now explicit-invocation-only).
   - **Relationship to other skills** — slice-land (consumes), independent-review
     (sibling, different shape), contracts (orthogonal).

3. **Tests** in `skills/pr-review/test_skill_surface.py` cover:
   - **FrontmatterTests** — `name` is `pr-review`, `user-invocable` is true,
     `disable-model-invocation` is absent (unless AC #9 fallback fires; see
     that AC for the alternate-test variant).
   - **DescriptionTests** — the description, after parsed-YAML normalization
     using the exact pattern `" ".join(text.lower().split())` (precedent:
     slice 006-01 design choice #7, `test_description_has_trigger_phrases`),
     contains:
     - Each of the six trigger phrases listed in AC #1, verbatim.
     - The deferral hint substring: "If you have another `pr-review` skill
       installed".
     - The `Do not use for` clause naming "spec-compliance review" and
       referencing `/jig:independent-review` as the alternative.
   - **DescriptionBoundsTests** — the normalized description does **NOT**
     contain any of these over-claiming phrases (anti-greediness pinning):
     "comprehensive review", "deep code analysis", "expert-level",
     "multi-persona", "full audit", "security review",
     "architecture review". This catches the "description got too broad
     and now shadows the user's richer skill" regression deterministically
     instead of only via the one-shot routing-dogfood.
   - **BodyTests** — the body contains H2 sections for: What this skill does
     / When to use vs. when to defer / Inputs / Review structure / Gotchas /
     Relationship to other skills (case-insensitive heading match).
   - **DeferralLanguageTests** — body explicitly references `~/.claude/skills/pr-review`
     (or equivalent path-shape hint) as the deferral target.
   - **WorkedExampleTests** — body contains one minimal worked example
     (one realistic diff fragment + one realistic four-section review)
     so the baseline's output quality is testable beyond shape (per AC #10).

4. **CLAUDE.md skills table** is updated:
   - Add a `/jig:pr-review` row marked active (auto + explicit invocable).
   - Hot Cache "Active specs" gains a line for spec 012-01 DONE.
   - Sprint focus paragraph updated to reflect that the last unblocked
     Tier 1 candidate has shipped; only `local-dev-parity` remains and is
     still unsignaled.

5. **`docs/specs/README.md`** is regenerated via `workflow.py status-board .`
   after slice transitions to DONE. The Notes column for 012-01 is curated
   to match the 006-01 / 007-01 / 011-02 shape ("N tests; lightweight
   baseline; defers to richer user skill via description hint").

6. **`scaffold.py` is not modified by this slice.** Spec-drafting check
   only — no AC enforcement needed. pr-review is a Tier 1 skill; the
   existing tier-granularity install flow (`has_tests` → install tier-1)
   captures it. The brief.md "Tier 1 `tdd-loop` and friends auto-installed."
   line already implicitly covers pr-review. Per-skill install lists remain
   deferred (same open question parked by slice 006-01 AC #5 deviation). The
   global suite-green requirement in DoD covers regression-protection for
   the scaffold-init test surface; no separate AC is needed (the prior
   "no regression in `_detect_tests`'s callers" framing was tautological —
   reviewer caught this).

7. **No new helper.** This slice ships **SKILL.md only**. The deviation log
   records this as the first non-stub active jig skill without a `.py`
   helper, and explicitly defers any helper (`pr_review.py gather`, etc.) to
   slice 012-02. **Trigger criterion for slice 012-02**: three concrete
   inbox.md entries (tagged `pr-review/gather-friction`) naming a specific
   session where Claude had to re-derive determinism inline (forgot the
   right base for the diff, missed a renamed file, miscounted lines).
   Without the inbox entries, the count cannot accumulate across sessions
   — the spec author / implementer / reviewer commits to filing one
   whenever the friction is observed. Same observability discipline as
   ADR-0002's third-caller rule, just adapted to a session-judgment
   signal instead of a code-site signal.

8. **README.md `## Extension points` section** (already added during spec
   drafting, between `## Design philosophy` and `## Installation`) is
   verified to contain: (a) one paragraph explaining the lightweight-
   baseline-defers-to-user-skill pattern, (b) `/jig:pr-review` named as
   the worked example with the path `~/.claude/skills/pr-review`, (c) the
   framing line "Bring your own depth; jig provides the floor."
   **Honest disclosure**: this section was added during the conversation
   that drafted this spec (before the spec entered READY_FOR_REVIEW). The
   reviewer flagged this as an AC-level pre-tick anti-pattern. Slice 012-01
   ships the *verification* (test or visual inspection) that the section
   has the right shape; the section itself is pre-existing. Acceptable
   because the section is small (≤ 12 lines), trivially revertible if
   the routing-dogfood fails, and its presence enables the spec's
   "discoverable to users" goal even during the review-and-implement
   window. Recorded in the deviation log when slice transitions to DONE.

9. **Routing-dogfood fallback (`disable-model-invocation: true`).** If the
   routing-dogfood in DoD fails — i.e. with both jig's `/jig:pr-review`
   and the user's richer `~/.claude/skills/pr-review` installed, the
   router picks jig's slim version on `"review this PR"`-shape prompts —
   the implementer applies this fallback before marking DONE:
   - Add `disable-model-invocation: true` to SKILL.md frontmatter.
   - Update SKILL.md body to add a short "Explicit-invocation only"
     callout near the top.
   - Re-run the test suite: `FrontmatterTests` now asserts
     `disable-model-invocation: true`; `DescriptionBoundsTests` still
     passes (the description is still lightweight, just non-auto-firing).
   - Update CLAUDE.md skills table: `/jig:pr-review` row marked
     `(explicit only)` instead of `(auto + explicit)`.
   - Record the fallback in the deviation log with the failing dogfood
     transcript.
   - Re-run the routing-dogfood; with `disable-model-invocation: true`,
     the router *must* prefer the user's skill on every shape — confirm
     this before marking DONE.
   **Tightening playbook before flipping to fallback** (try these in
   order): (a) shorten the description to one sentence + deferral hint
   only, dropping the six trigger phrases; (b) move from `description: >`
   (folded scalar) to a tight single-line description, which gives the
   router less surface area to over-match on; (c) add a stronger negative
   signal to the description ("DO NOT USE IF the user has another
   pr-review skill installed"). Only flip to `disable-model-invocation`
   if all three tightening passes still produce a failed dogfood.

10. **SKILL.md contains one worked example.** Body section "Review
    structure" (per AC #2) includes a minimal but realistic example: one
    diff fragment (~15 lines, with at least one substantive change worth
    flagging — e.g. missing error handling, a magic number, a renamed
    function affecting callers) and the corresponding four-section review
    output (scope summary, one blocker, one nit, one strength). The
    example is the only end-to-end demonstration that the slim baseline
    produces useful output on its own when no richer user skill is
    present — without it, the skill is testable for shape but not for
    output quality.

**DoD** (same shape as 006-01 / 007-01 / 011-02):

> **Anti-pre-tick reminder.** Only two boxes are auto-ticked by
> `workflow.py transition` (per slice 003-04): "Implementation review
> passed" on IN_PROGRESS → REVIEWED, and "Reconciliation review passed"
> on REVIEWED → RECONCILED. Every other box below must be ticked
> **after** the corresponding evidence exists — never before. This is the
> recurring anti-pattern that bit 007-01, 008-03, and 011-02; surfacing
> it here to break the streak.

- [x] All 10 ACs pass; full test suite green (existing + new). _(394 tests
      green: 374 skills + 20 scripts; 23 new in `skills/pr-review/test_skill_surface.py`.)_
- [x] SKILL.md dogfooded against this very slice — generate the PR review
      for slice 012-01's own branch using the new skill, verify the four
      sections are produced, verify the deferral hint reads naturally.
      _(Completed 2026-05-14 — see deviation §8a. The skill is
      judgment-only; the implementer applied SKILL.md's body as a
      prompt-to-self against the slice's own diff. Verdict: 0 blockers,
      3 nits, 4 strengths.)_
- [x] Implementation review passed. _(auto-ticked by `workflow.py transition`
      on IN_PROGRESS → REVIEWED; do not pre-tick.)_
- [x] Deviation log produced under this slice heading (under
      `### Close-out (post-DONE)` for post-DONE items per slice 009-01
      convention). _(Records §1–§8: AC#1/#3 contradiction, helper-less
      milestone, README pre-existence, AC#9-not-applied, trigger-phrase
      replacement, status-board regen omission, CLAUDE.md staleness, and
      SKILL.md own-slice dogfood deferral.)_
- [x] Reconciliation review passed. _(auto-ticked by `workflow.py transition`
      on REVIEWED → RECONCILED; do not pre-tick.)_
- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      _(Reconciliation reviewer flagged the missed regen during verification
      and inadvertently triggered it as a read-side-effect; the implementer
      accepted the change rather than reverting. See deviation §6.)_
- [x] `CLAUDE.md` skills table promotes `pr-review` to active
      (auto + explicit, or explicit-only if AC #9 fallback fired).
      _(Auto+explicit. Hot-cache + sprint focus + skills table refreshed
      from REVIEWED → DONE during reconciliation per deviation §7.)_
- [x] `docs/refinement-todo.md` left untouched (no new deferrals unless a
      real one surfaces during implementation). _(Verified — `git diff`
      shows no change.)_

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice. A user
with a fresh project can: install jig → scaffold-init detects tests →
Tier 1 auto-installs pr-review → on the user's next "review this PR" prompt,
either jig's slim version fires (no other skill present) or the user's richer
skill fires (description wins). Either path delivers value; both are end-to-end.

### Deviation log (after reconciliation)

The original spec is preserved above (with AC #1 corrected in-place — the
correction itself is recorded as deviation §1 below).

**Deviations from the spec as it entered IN_PROGRESS:**

1. **AC #1 prescribed-phrasing vs. AC #3 anti-greediness contradiction
   (reviewer-flagged, resolved by spec amendment).** As entered, AC #1
   mandated the deferral hint contain the exact phrase "a personal
   multi-persona reviewer at `~/.claude/skills/pr-review`", while AC #3's
   new `DescriptionBoundsTests` forbade the word "multi-persona" anywhere
   in the description. The two ACs were unsatisfiable simultaneously. The
   implementer chose to honor AC #3 (anti-greediness has more downstream
   protection value — it catches future regressions where the description
   gets broad enough to shadow user skills) and wrote the SKILL.md
   deferral hint as "a richer personal reviewer at
   `~/.claude/skills/pr-review`". The reviewer flagged the deviation and
   recommended amending AC #1 (not loosening AC #3). Applied: AC #1's
   exact-phrasing block now matches what shipped, with the rationale
   inlined.

2. **First non-stub active jig skill without a `.py` helper (per AC #7).**
   Confirmed: `skills/pr-review/` ships `SKILL.md` and
   `test_skill_surface.py` only. No helper. `skills/contracts/` is the
   only precedent for a SKILL.md-only skill in jig, and it's a deliberate
   stub (ADR-0002). 012-01 is therefore the first **active** SKILL.md-only
   skill. The slice 012-02 trigger criterion (three inbox.md entries
   tagged `pr-review/gather-friction` naming a specific session where
   Claude had to re-derive determinism inline) is set up to track whether
   the no-helper choice ever proves wrong.

3. **README `## Extension points` section pre-existence (per AC #8's
   honest-disclosure clause).** Confirmed: the section was added during
   the spec-drafting conversation (before slice 012-01 transitioned to
   READY_FOR_REVIEW). The slice as implemented ships only the *verification*
   that the section exists with the documented content shape — the
   section itself is pre-existing. The spec's AC #8 acknowledges this in
   its "honest disclosure" sub-clause; this entry confirms it for the
   record. The section is small (≤ 16 lines including the framing
   blockquote moved to the top during spec revision) and trivially
   revertible if the routing-dogfood fails.

4. **AC #9 fallback was NOT applied during implementation.** The
   `disable-model-invocation: true` flag is absent from SKILL.md (auto-
   triggering is in effect). The routing-dogfood test that gates the
   fallback (per DoD) requires a freshly-restarted Claude Code session
   with both `~/.claude/skills/pr-review/SKILL.md` and jig's
   `/jig:pr-review` loaded, running at least two prompt phrasings.
   **That test cannot be run from inside the implementation session** —
   the worktree session has its skill list loaded at session-start time
   and re-running the prompt here exercises the *current* skill list, not
   a freshly-restarted one with the new jig skill registered. The
   routing-dogfood is therefore a **user-driven post-merge action**: the
   user runs it from their next Claude Code session after `jig` is
   installed-and-restarted. If the dogfood fails, AC #9's fallback
   procedure applies and gets recorded as a §5 entry in this log. Until
   then, the auto-triggering path is the shipped default.

5. **Trigger phrase replacement (per AC #1).** As implemented: the sixth
   trigger phrase is "review the diff on this branch" (not "code review
   this branch", which was in an early spec draft). The replacement
   disambiguates from the spec-compliance review surface that
   `agents/reviewer.md` exercises. Documented in AC #1's parenthetical.

6. **Status-board regen was missed during the IN_PROGRESS → REVIEWED →
   RECONCILED window (reconciliation-reviewer-flagged).** The initial
   regen happened when spec 012 was first drafted at DRAFT state, but
   subsequent transitions did not trigger a fresh regen, leaving the
   status board out of sync with the slice's lifecycle. The
   reconciliation reviewer ran `workflow.py status-board .` during
   verification as a read-side-effect and was correctly blocked from
   reverting the mutation (read-only tools). The implementer accepts
   the regen rather than reverting — the status board now correctly
   reflects `RECONCILED → DONE`. **Process improvement candidate**:
   `workflow.py transition` could call `status-board` as a side effect
   on every transition. Filed for consideration; not implemented in
   this slice.

7. **CLAUDE.md was updated mid-lifecycle (REVIEWED-stage labels) and
   needed a refresh during reconciliation.** When the implementer
   updated CLAUDE.md after the IN_PROGRESS → REVIEWED transition, the
   labels read "REVIEWED" across the Active-specs entry, sprint-focus
   paragraph, and skills-table row. The subsequent REVIEWED → RECONCILED
   transition only auto-ticked the DoD box; it did not refresh CLAUDE.md
   text. Reconciliation reviewer flagged the staleness. **Fix applied
   inline during reconciliation**: all three CLAUDE.md mentions updated
   to DONE-state labels. **Convention note**: update CLAUDE.md once,
   in reconciliation, using DONE-state labels — not mid-lifecycle.
   Mirrors slice 006-01's deviation §1b which hit the same pattern.

8. **SKILL.md dogfood against this slice's own diff was not recorded
   (reconciliation-reviewer-flagged).** DoD box 2 asked for a four-
   section review of slice 012-01's own work using the new skill. Not
   run from the implementation session for the same reason as §4: the
   skill router can't see jig's `/jig:pr-review` from the worktree
   session because the available-skills list is fixed at session start
   and the jig install is the install-snapshot version, not the live
   worktree. **Resolved in §8a below** — the dogfood is judgment-only
   (no helper, no slash-command invocation required), so the implementer
   applied the SKILL.md body as a prompt-to-self against the slice's
   own diff in this same session. The routing-dogfood (§4) still
   requires session-restart and remains user-driven.

   §8a. **Own-slice four-section review, run 2026-05-14 by applying
   `skills/pr-review/SKILL.md`'s body content to this slice's own diff.**
   Diff input: 4 modified files (CLAUDE.md, README.md, docs/inbox.md,
   docs/specs/README.md) + 3 new files (docs/specs/012-pr-review/spec.md,
   skills/pr-review/SKILL.md, skills/pr-review/test_skill_surface.py).

   ## Scope

   New-feature PR: introduces `/jig:pr-review` as the fourth Tier 1 jig
   skill and the first non-stub active skill that ships without a `.py`
   helper. Lightweight four-section review (scope / blockers / nits /
   strengths) with description-based deferral to richer user-installed
   `~/.claude/skills/pr-review` skills. Adds 23 surface tests including
   a novel anti-greediness `DescriptionBoundsTests` class. Documents the
   pattern in a new README `## Extension points` section. Closes the
   long-deferred "ship pr-review when slice-land creates a PR-shaped
   artifact" inbox entry from 2026-05-12.

   ## Blockers

   - None. The skill ships green (394 tests, 0 regressions), the spec
     went through all three review gates (authorship / implementation /
     reconciliation) with all findings resolved inline, and the two
     deferred dogfoods are correctly identified as needing session
     prerequisites the implementation session can't satisfy.

   ## Nits

   - `docs/specs/012-pr-review/spec.md:178-186` — AC #6 says "no AC
     enforcement needed" inside an AC numbered as if it were one. It's
     effectively dead-AC and the numbering shifts AC #7 / AC #8 etc.
     down by one in the reader's mental model. Could be moved to the
     spec body (e.g., a "Scaffold note" section) and the AC count
     reduced to 9; preserved at 10 here only because the spec is DONE
     and the renumber would churn the deviation log refs. Worth a
     convention note for future specs.
   - `skills/pr-review/test_skill_surface.py:189-202` — `test_sections_in_order`
     uses `body_lower.find(phrase)` for each section name, which returns
     the **first** occurrence. If a future SKILL.md edit introduces the
     literal phrase "when to use" or "inputs" inside a paragraph **above**
     the corresponding H2, the test would silently pass against the wrong
     position. Tightening idea: change to a regex match on `(?m)^## .*<phrase>`
     so only H2 lines count. Not a regression risk today (no early-body
     mentions), but the test is more permissive than intended.
   - `skills/pr-review/SKILL.md:165-168` — Gotchas section says "If you
     see `disable-model-invocation: true` in this skill's frontmatter,
     that's why" — readers landing here BEFORE any routing-dogfood has
     run will have no context for why the flag might appear. Minor
     comprehension paper-cut; would resolve by phrasing as "if the
     post-merge routing-dogfood (see spec 012-01 §4) ever flips this".

   ## Strengths

   - **Anti-greediness `DescriptionBoundsTests` is a genuinely useful
     test pattern that caught a real implementer-deviation in this very
     slice.** It fired during the green-pass on the original "multi-
     persona" phrasing, forced the implementer to surface the AC #1/#3
     contradiction, and the reconciliation review correctly recommended
     resolving in favor of the bounds test (downstream protection
     value). Worth copying to other description-routing skills.
   - **Three-gate review discipline (authorship + implementation +
     reconciliation) caught real issues at each gate** — 11 spec-
     authorship findings, the AC #1/#3 contradiction at implementation,
     and three reconciliation findings (status-board regen, stale
     CLAUDE.md labels, missing own-slice dogfood). None were missed by
     all three; each found something the others didn't.
   - **The deferral pattern is small enough to be auditable.** Single
     SKILL.md, single test file, ~150 lines of documented skill body,
     6 test classes. Compare to the user's personal `pr-review` (~900
     lines + reference files): the jig baseline is unambiguously slim.
     "Bring your own depth; jig provides the floor" is honestly served
     by what shipped.
   - **Process-improvement candidates were captured inline rather than
     scope-crept into the slice.** Auto-status-board-on-transition (§6),
     the convention note on updating CLAUDE.md only in reconciliation
     (§7), and the cross-AC consistency lint idea (inbox 2026-05-13)
     are all parked appropriately.

   Notice what's **not** in this review: no language-specific deep dive
   (no "your Python f-string would be more idiomatic", no "this YAML
   should use `>-` instead of `>`"), no multi-persona security/SRE/
   architecture lens. That depth belongs in a richer user-installed
   `pr-review` — exactly the deferral pattern this slice ships.

9. **Routing-dogfood PASS (post-merge, fresh session, 2026-05-14).**
   After the slice merged to main and the user refreshed the jig install,
   the routing-dogfood was run in a fresh Claude Code session. Three test
   prompts were attempted; the conclusive evidence came from a direct
   skill-inventory question rather than from the original two trigger
   prompts.

   **Conclusive test — direct skill inventory question.** The user asked
   the fresh session: *"what review skills do you have access to?"* The
   model's response correctly:
   - Listed both `pr-review` (user-installed, richer) and `jig:pr-review`
     (lightweight baseline) as separate, distinct skills.
   - Reported each skill's actual description content — `Multi-perspective…`
     for the user's, `Lightweight baseline…` for jig's. Not identical.
   - **Explicitly identified the deferral relationship**, summarizing
     jig:pr-review as "defers to the richer `pr-review` skill when
     present."

   That last point is the load-bearing hypothesis confirmed: Claude Code's
   skill router does surface jig's SKILL.md `description` field (including
   the deferral hint) to the model, and the model uses it to understand
   the routing relationship between the two skills.

   **Earlier test-session reports of "identical descriptions" between
   the two skills were model confabulation, not a Claude Code router
   bug.** Three independent test sessions all produced the same wrong
   answer — consistent enough to look like signal but actually just
   three samples of the same hallucination pattern from similar
   inference paths. The terminal `cat` of both `~/.claude/skills/pr-review/SKILL.md`
   and `~/.claude/plugins/marketplaces/local-desktop-app-uploads/jig/skills/pr-review/SKILL.md`
   was the ground truth that pinned this — files different on disk,
   exactly as shipped. The implementer (initially) read the consistent
   confabulation across sessions as evidence of a real bug and
   prematurely recommended applying the AC #9 fallback; that
   recommendation was retracted before any code change after the direct
   inventory test produced conclusive evidence.

   **Earlier inconclusive prompts** (recorded for completeness, not as
   pass/fail):
   - *"review this PR"* → reported as routing to `pr-review` (the
     user's). Test-session reasoning was unreliable (cited a confabulated
     description), but the *choice* matches the deferral.
   - *"can you look at the changes I just made?"* → no skill fired.
     Defensible — neither skill's trigger language was a tight match for
     that phrasing. Not a jig-shadowing failure.
   - *"review the most recent commit on the currently-checked-out branch"*
     → produced a four-section review (`**Scope:**` / `**Blockers:**` /
     `**Nits:**` / `**Strengths:**`) with no UI-visible "Using skill: X"
     signal. Ambiguous: could have been jig:pr-review firing without UI
     surfacing, or Claude producing a sensible four-section format on its
     own without invoking either skill. Not used as a pass/fail signal.

   **AC #9 fallback NOT applied.** Frontmatter stays at the auto-
   triggering default (no `disable-model-invocation: true`). The
   deferral hint remains the routing mechanism.

   **Methodology lessons captured to inbox (filed during this close-out):**
   - When a test depends on a fresh model's self-report about its own
     skill list, prefer **direct inventory questions** ("list the skills
     you have access to with X in the name and paste their descriptions
     verbatim") over **behavioral observation prompts** ("review this PR
     and tell me which skill you used"). The former is harder for the
     model to confabulate against because it asks for ground-truth
     enumeration; the latter conflates routing decision with output
     production with self-report — three layers of potential
     unreliability.
   - When multiple test sessions produce the same confused answer,
     that's not automatically a bug signal — it can be three samples
     of the same hallucination from similar inference paths.
     Disambiguate with non-LLM evidence (terminal `cat`, file
     inspection, direct API calls) before concluding a system bug.

**Open follow-ons (filed to inbox.md during reconciliation):**

- The internal AC #1/#3 contradiction surfaced a meta-issue:
  exact-phrasing ACs that contain free-form sentences are inherently
  fragile in the face of negative-assertion tests added later in the same
  spec. Filed as an inbox entry — future specs writing exact-phrasing
  ACs should run them through any anti-greediness/bounds tests as a
  pre-check.
- The "trigger criterion for slice 012-02 is three inbox entries" rule
  (AC #7) requires the implementer and reviewer to remember to file an
  inbox entry whenever gather-friction is observed in real use. Tagging
  convention: `pr-review/gather-friction` as a leading bullet prefix in
  `docs/inbox.md`.

**Doc updates from this slice:**

- `skills/pr-review/SKILL.md`: net-new file. Active frontmatter; six
  H2 body sections; worked example with substantive blocker; AC #9
  fallback documented in Gotchas.
- `skills/pr-review/test_skill_surface.py`: net-new — 23 tests across 6
  test classes (Frontmatter / Description / DescriptionBounds / Body /
  DeferralLanguage / WorkedExample). All green.
- `README.md`: `## Extension points` section between `## Design philosophy`
  and `## Installation`; framing blockquote moved to top during spec
  revision.
- `docs/specs/README.md`: regenerated by `workflow.py status-board`.
- `CLAUDE.md`: hot-cache "Active specs" + skills table + sprint focus
  updated (sprint focus now records Tier 1 sprint effectively closed
  pending the user-driven routing-dogfood).
- `docs/inbox.md`: one entry for the AC #1/#3 contradiction pattern; one
  bullet noting the `pr-review/gather-friction` tagging convention.
- No new ADR required.
- No `architecture.md` changes.

### Close-out (post-DONE)

- [x] Routing-dogfood run by the user from a freshly-restarted session
      with both skills loaded. _(Completed 2026-05-14 — see deviation §9.
      Conclusive evidence from a direct skill-inventory question: the
      fresh-session model correctly listed both skills, reported each
      one's distinct description, and explicitly identified the deferral
      relationship. AC #9 fallback NOT applied; auto-triggering stays the
      default. Methodology lessons (prefer direct-inventory questions
      over behavioral-routing-introspection prompts; consistent
      confabulation can mimic real bugs) captured to inbox.)_
- [x] SKILL.md dogfood against this slice's own diff (DoD box 2).
      _(Completed 2026-05-14. The skill is judgment-only — no helper, no
      slash-command invocation needed — so the implementer ran it by
      applying SKILL.md's body content as a prompt-to-self against the
      slice's own diff. Output recorded as deviation §8a above: 0
      blockers, 3 nits, 4 strengths, and a four-section structure that
      verified all four headings render and the breadth-not-depth
      framing reads naturally.)_

---

## Slice 012-02 — pr-review-gather-helper

**STATUS: DEFERRED** _(deferred — add only if gather-friction is observed)_

**Resolution trigger:** Three `pr-review/gather-friction:` inbox entries naming specific sessions where Claude had to re-derive determinism inline. Count today: 0 (per inbox 2026-05-13 entry).

**Goal:** `pr_review.py gather <target-branch>` produces a structured
markdown bundle (diff, file list, scope classification, language detection)
that Claude consumes instead of running `git diff` + `git log` + file-type
heuristics inline.

Deferred because: jig's "duplicate, don't abstract" rule says we wait for
three concrete signals before extracting. Slice 012-01 ships SKILL.md only;
slice 012-02 lands only after three sessions where Claude visibly fumbled
the gather step (forgot to compare against the right base, missed a renamed
file, miscounted lines changed, etc.).

---

## Slice 012-03 — security-lens-integration

**STATUS: DEFERRED** _(OBSOLETE — superseded by spec 052 / ADR-0013)_

**Resolution trigger:** OBSOLETE (2026-06-01) — superseded by spec 052 / ADR-0013. Security review shipped as a standalone `jig:security-review` skill, NOT a `security_lens` field consulted by `pr-review`, so this slice's plug-in surface was never built. Will not be built as specified; the remaining lever (a `security_review: true` review pass) is tracked in docs/refinement-todo.md.

**Original goal (not pursued):** `pr-review` consults the `security_lens`
field in `scaffold.json` (when present) and either appends an
`adobe-security-suite` hand-off block to its review prompt or embeds the
builtin ~10-rule checklist.

**Obsolete because:** the `security_lens` parent decision (inbox
2026-05-12) was resolved on 2026-06-01 — but in a **different shape** than
this slice assumed. [Spec 052](../052-security-scaffold/spec.md) /
[ADR-0013](../../decisions/adr-0013-security-floor-policy.md) shipped
security review as a **standalone `jig:security-review` skill** (slice
052-05) that defers to any richer installed security skill via
description-based routing — **not** a `security_lens` field in
`scaffold.json` read by `review.py`, and **not** Adobe-specific. The
surface this slice was designed to plug into (`pr-review` consulting a
`security_lens` flag) was therefore never built and will not be. The one
remaining open lever — wiring a `security_review: true` post-implementation
review pass parallel to `arch_review` — is tracked separately in
[`docs/refinement-todo.md`](../../refinement-todo.md) ("Promote the
`security_review: true` post-implementation review-flow pass"), not here.

---

## Slice 012-04 — language-specific-references

**STATUS: DEFERRED** _(deferred — explicit non-goal of "lightweight")_

**Resolution trigger:** Multi-language-codebase user reports a concrete gap that the lightweight baseline doesn't cover, AND no user-installed `~/.claude/skills/pr-review` deferral target exists for them.

**Goal:** Port the language-specific reference files from the personal
`pr-review` skill (`nodejs-typescript.md`, `java-aem.md`, `python.md`).

Deferred because: porting these makes jig's pr-review heavyweight, which
defeats the spec's framing. The right home for language-specific depth is
the user's personal `~/.claude/skills/pr-review`, which the description
hint already routes to. If a clear signal emerges that users without a
personal skill want depth, revisit — but the working assumption is that
"depth = bring your own skill."
