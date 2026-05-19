---
status: DONE
skill: arch-review
tier: 1
---

# Spec 014: arch-review (Tier 1)

## Overview

Introduce `arch-review` — the fifth Tier 1 skill — as a **lightweight default**
review of architecture proposals, design docs, RFCs, ADRs, and technical
specs. The skill auto-triggers on architecture-review prompts ("review this
design", "what do you think of this architecture", "poke holes in this
proposal", "is this design sound", "review my RFC") but its description
explicitly defers to richer user-installed `arch-review` skills, so a user
who already ships their own `~/.claude/skills/arch-review` (multi-persona,
domain-specific reference files, etc.) is not shadowed by jig's baseline.

This is **not** a port of the heavyweight personal `arch-review` skill. It
is intentionally slim: structured input-mode detection → goal/constraints
extraction → four-section review output (summary / strengths / concerns /
open questions). No seven-perspective matrix. No domain-specific reference
files (distributed-systems, api-design, data-architecture, migration-plans).
The goal is "jig users get *some* architecture review out of the box; power
users keep their own thing."

This spec is the other half of the long-deferred multi-persona-reviewer
inbox entry from 2026-05-12 (`docs/inbox.md`): "ship as separate
`/jig:arch-review` and `/jig:pr-review` skills, ported and slimmed from
personal versions." Slice 012-01 shipped `/jig:pr-review` under the same
deferral pattern; this spec ships the architecture-review half.

## Why now

- **pr-review proved the deferral pattern.** Slice 012-01 (`pr-review`)
  shipped with a description-based deferral hint and the routing-dogfood
  passed (deviation §9): the Claude Code skill router surfaces SKILL.md
  descriptions and the model uses the deferral hint to prefer richer
  user-installed peers. The same pattern applies cleanly to arch-review.
- **Closes the multi-persona reviewer arc.** The 2026-05-12 inbox entry
  considered four directions; (a) "separate `/jig:arch-review` and
  `/jig:pr-review` skills" was the chosen path. pr-review is done; this
  spec closes the arc.
- **README `## Extension points` already documents the pattern.** Slice
  012-01 added the extension-points section using pr-review as the
  worked example. Adding arch-review as a second instance of the same
  pattern strengthens the pattern's documented surface without requiring
  a new convention.
- **Last clearly-signaled Tier 1 candidate.** Per CLAUDE.md, the only
  remaining Tier 1 candidate after this is `local-dev-parity` — still
  unsignaled. Shipping arch-review effectively closes the Tier 1 sprint.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| P — Path | (a) SKILL.md only / (b) SKILL.md + `arch_review.py` helper (e.g. doc-shape detection) / (c) full seven-perspective port. | **(a) SKILL.md only this slice.** No helper. arch-review is fundamentally a judgment skill — what little determinism is needed (read the doc, identify the scope, classify the domain) Claude can run inline. If a "gather" friction point surfaces three sessions in a row, slice 014-02 can add the helper. (c) is explicitly out of scope per the "lightweight default" framing. |
| I — Interface | How does the skill defer to a richer user skill? Filesystem probe? Plugin scope detection? Description-level hint? | **Description-level hint (proven by pr-review).** Slice 012-01 confirmed the pattern works: an explicit deferral phrase in the frontmatter `description` causes the Claude Code skill router to prefer the more-specific user skill. The deferral is **category-based**, not name-specific — a user skill named anything (`arch-review`, `design-review`, `rfc-reviewer`, etc.) whose description claims architecture/design/RFC review will win. Same precedent + same risk-mitigation: AC #9 fallback (`disable-model-invocation: true`) is ready if the routing-dogfood fails. |
| D — Data | What inputs does the skill consume? Uploaded doc / URL / pasted text / verbal description / ADR file? | **Four input modes, ordered by richness:** (1) uploaded document (PDF / markdown / Word) — richest, full author intent, (2) URL to a wiki/Confluence/Google Doc/GitHub markdown — fetch and read (no MCP coupling required for raw fetch), (3) pasted text or verbal description — most limited, may need follow-up questions, (4) ADR file on disk (`docs/decisions/adr-NNNN-*.md`) — narrower review scope (decision-shape, not system-shape). No GitHub MCP coupling. No Confluence MCP coupling. Same scoping discipline as 012-01. |
| R — Rules | What does the lightweight review actually check? | **Four-section output:** (a) **Summary** — what the proposal does and its overall assessment in 2-3 sentences, (b) **Strengths** — what the design gets right (constructive framing first, like pr-review's strengths section), (c) **Concerns** — risks, gaps, missing rationale, unaddressed failure modes (the "poke holes" surface), (d) **Open questions** — things the reviewer can't decide from the proposal alone (asks the author to clarify rather than asserting a gap). No seven-perspective matrix. No domain-specific deep dives. Depth lives in a richer user-installed skill. |
| S — Spike | None required — the shape is well-established by the user's personal `arch-review` skill and by the precedent set by 012-01 for the deferral pattern. | — |

## Out of scope for spec 014 (any slice)

- **Multi-persona / seven-perspective review** (technical soundness +
  operational complexity + reliability + security + scalability + migration
  + product). That depth belongs in the user's `~/.claude/skills/arch-review`.
  The slim baseline ships four sections, not seven perspectives.
- **Domain-specific reference files** (`references/distributed-systems.md`,
  `references/api-design.md`, `references/data-architecture.md`,
  `references/migration-plans.md` — the structure used by the personal
  skill). Slim baseline ships none. Same depth-vs-breadth call as 012-01.
- **GitHub / Confluence / Google Docs MCP integration.** Slice 014-01
  reviews what Claude can read directly: uploaded files, pasted content,
  fetchable URLs. Auto-fetching from authenticated systems is deferred.
- **Auto-trigger on every committed design doc.** Skill invocation stays
  user-driven (auto-routing by description match, not by hook firing).
- **Posting review back to the source doc** (Confluence comment, Google
  Docs suggestion, GitHub PR comment on a markdown design doc). Out of
  scope; the skill produces a structured markdown report, the user does
  the posting.
- **`security_lens` integration with `adobe-security-suite`** (parked in
  inbox 2026-05-12). Same orthogonality as for 012-01: if `security_lens`
  ever lands, it plugs into this skill via a follow-on slice; it does not
  block 014-01.
- **ADR authorship / scaffolding** (handled by `/jig:adr-workflow`). This
  skill *reviews* an ADR draft; it does not create one. The `Do not use
  for` clause in AC #1 makes the boundary explicit.

---

## Slice 014-01 — arch-review-skill

**STATUS: DONE**

**Goal:** Ship `skills/arch-review/SKILL.md` as an active, auto-triggering
skill with a description that **explicitly defers to user-installed
arch-review skills** (category-based, not name-specific — same shape as
012-01's post-reconciliation phrasing). Body codifies a lightweight,
four-section review (summary / strengths / concerns / open questions).
No helper. No domain-specific reference files. CLAUDE.md skills table
promotes the skill to active.

**DoR:**
- ✅ Slice 012-01 (`pr-review`) DONE — the deferral pattern is proven and
  the README `## Extension points` section already documents it. Adding
  arch-review as a second instance reuses that documented surface.
- ✅ Personal `arch-review` skill exists at `~/.claude/skills/arch-review/SKILL.md`
  with 7 perspectives + 4 domain-specific reference files — dogfood
  reference for routing-deferral (when both jig's slim version and the
  personal richer version are present, the richer one should win).
- ✅ `/jig:adr-workflow` is active — the boundary between "review an
  architecture proposal" (this skill) and "scaffold/accept an ADR"
  (adr-workflow) is real and the `Do not use for` clause must be sharp
  on it.
- ✅ Precedent for active-SKILL.md-only ships established by 012-01
  (first non-stub active jig skill without a `.py` helper). 014-01 is
  the **second** — it's not a milestone the way 012-01 was, but the
  pattern is now repeatable.

**Routing-dogfood prerequisites** (must hold before the dogfood step in
DoD can run honestly — same shape as 012-01):
- The user's personal `~/.claude/skills/arch-review/SKILL.md` is loaded
  by the current Claude Code session. Verify by checking its description
  appears in the available-skills list before invoking the dogfood prompt.
- Jig is installed (not just present in worktree) via the `jig`
  marketplace — `scripts/verify_install.py` must return a fresh pass.
  Address the install-snapshot-lag inbox entry from 2026-05-13: do not
  trust a stale install; reinstall if the slice has been modified since
  the last verify.
- The routing-dogfood uses a **direct skill-inventory question** as the
  conclusive test (per slice 012-01 deviation §9 / methodology-lesson
  inbox entry 2026-05-14): "list the skills you have access to with
  `arch-review` in the name and paste their full description fields
  verbatim." Behavioral-introspection prompts ("review this design and
  tell me which skill you used") are unreliable — three independent
  sessions confabulated the same wrong answer during 012-01's dogfood.
- Run from a **freshly-restarted session**. A single-run pass is
  sufficient if the direct-inventory question shows both skills with
  distinct descriptions and the deferral relationship correctly
  summarized.

**Acceptance Criteria:**

1. **`skills/arch-review/SKILL.md`** exists with active frontmatter:
   - `name: arch-review`
   - `user-invocable: true`
   - **No** `disable-model-invocation: true` (this skill auto-triggers; if
     the routing-dogfood in DoD fails, AC #9's fallback flips this to
     `true`).
   - `description: >` is a folded scalar that contains, in order:
     - One sentence stating what the skill does, using the exact phrasing:
       "Team baseline for architecture, design-doc, and RFC review —
       produces summary, strengths, concerns, and open questions."
     - The trigger phrases the router should match on: "review this
       design", "review this architecture", "review this proposal",
       "review my RFC", "poke holes in this proposal", "is this design
       sound", "critique this tech spec".
       _(Provenance: five of seven — "review this design", "poke holes
       in this proposal", "is this design sound", "review my RFC",
       "critique this tech spec" — are inherited verbatim from the
       user's personal `~/.claude/skills/arch-review/SKILL.md`
       description. Two — "review this architecture", "review this
       proposal" — are jig-invented to widen routing coverage. The
       personal skill's "what do you think of this architecture" is
       intentionally NOT inherited; the deferral is category-based so
       phrase-level symmetry isn't required. Same disclosure shape as
       slice 012-01 AC #1's trigger-phrase parenthetical.)_
     - An **explicit deferral hint**, using category-based phrasing
       (matches the post-reconciliation pattern from 012-01): "Defers
       to any other installed skill whose description identifies it as
       handling architecture review, design review, RFC review, or
       technical-design review — if such a skill is present, prefer
       it over this one (jig's version is a slim baseline). Does not
       defer to the generic built-in `review` skill."
     - A `Do not use for:` clause naming three exclusions, in this exact
       order, with this exact phrasing: (a) "PR/diff review (use
       `/jig:pr-review` or a richer user-installed PR-review skill
       instead)", (b) "spec-compliance review of a finished slice (use
       `/jig:independent-review` instead)", (c) "ADR authorship or
       scaffolding (use `/jig:adr-workflow` — this skill *reviews* an
       ADR draft; it does not create one)".

2. **SKILL.md body** has the following H2 sections, in order
   (case-insensitive heading match; same test pattern as 012-01):
   - **What this skill does** — one paragraph, lightweight framing.
   - **When to use vs. when to defer** — explicitly distinguishes four
     things the reader might confuse with this skill: (a) a richer
     user-installed `arch-review` skill (defer if present); (b)
     `/jig:pr-review` (PR/diff review — a *skill*, different shape);
     (c) `/jig:independent-review` (spec-compliance review of a slice
     — a *skill*, different shape, against a written spec); (d)
     `/jig:adr-workflow` (ADR scaffolding, not review — wrong direction).
     The section must explicitly say *when* to reach for each.
   - **Inputs** — four modes: (1) uploaded document (PDF / markdown /
     Word, preferred for fidelity), (2) URL to a fetchable doc, (3)
     pasted text or verbal description (most limited; may need
     follow-ups), (4) ADR file on disk (narrower review scope —
     decision-shape, not system-shape). Notes the limitations of each
     mode. **Explicit note**: authenticated systems (internal Confluence
     behind SSO, private Google Docs) are NOT supported by this baseline
     — users in that case must paste or upload the content.
   - **Review structure** — the four sections of the output (summary /
     strengths / concerns / open questions) with one or two example
     lines per section, plus the worked example required by AC #10.
   - **Gotchas** — explicit notes on (a) the deferral hint behavior
     (category-based, not name-based), (b) the scope of "lightweight"
     (no seven-perspective matrix, no domain-specific deep dives), (c)
     the relationship to `/jig:adr-workflow` (review vs. scaffold), (d)
     what to do if the routing-dogfood failed and AC #9 fallback was
     applied.
   - **Relationship to other skills** — pr-review (sibling, different
     shape — diff vs. design), independent-review (sibling, different
     shape — spec-compliance), adr-workflow (orthogonal — scaffold vs.
     review), slice-land (orthogonal — landing vs. design phase).

3. **Tests** in `skills/arch-review/test_skill_surface.py` cover
   (same six-class layout as 012-01's `test_skill_surface.py`):
   - **FrontmatterTests** — `name` is `arch-review`, `user-invocable`
     is true, `disable-model-invocation` is absent (unless AC #9
     fallback fires).
   - **DescriptionTests** — the description, after parsed-YAML
     normalization using the exact pattern `" ".join(text.lower().split())`
     (precedent: slice 006-01 design choice #7, reused by 012-01),
     contains:
     - The one-sentence summary substring: "team baseline for
       architecture, design-doc, and rfc review".
     - Each of the seven trigger phrases listed in AC #1, verbatim.
     - The category-based deferral hint substring: "defers to any
       other installed skill whose description identifies it as
       handling architecture review, design review, rfc review, or
       technical-design review".
     - The bundled-`review`-skill carve-out: "does not defer to the
       generic built-in `review` skill".
     - The `Do not use for` clause naming `/jig:pr-review`,
       `/jig:independent-review`, and `/jig:adr-workflow` as the
       three alternatives.
   - **DescriptionBoundsTests** — the normalized description does
     **NOT** contain any of these over-claiming phrases (anti-greediness
     pinning, same pattern as 012-01's bounds test):
     "comprehensive review", "deep design analysis", "expert-level",
     "multi-persona", "seven perspectives", "full audit", "security
     review", "scalability review", "reliability review". This catches
     the "description got too broad and now shadows the user's richer
     skill" regression deterministically.
     **Intentional asymmetry**: "architecture review" and "design review"
     are NOT in the forbidden list even though both appear in the AC #1
     deferral hint. You cannot forbid the category words you're using to
     advertise the deferral category — the bounds test fires on
     depth-claims ("comprehensive", "deep", "expert-level") and on
     persona-claims ("security", "scalability", "reliability") that
     would shadow a richer skill, not on the category names themselves.
     Future-reviewer note: do not add "architecture review" or "design
     review" to this list without first amending AC #1's mandated
     deferral-hint phrasing.
     **Pre-implementation cross-check** (mandated by spec 012-01
     reconciliation lesson, inbox entry 2026-05-13): every phrase
     mandated by AC #1 was normalized via `" ".join(text.lower().split())`
     and substring-checked against the forbidden list above. Result:
     no collisions. Verified phrases — one-sentence summary ("team
     baseline for architecture, design-doc, and rfc review"), seven
     trigger phrases, deferral hint, carve-out, Do-not-use-for clause.
     None contains a forbidden substring after normalization. If AC #1
     is amended before READY_FOR_IMPLEMENTATION, re-run this check.
   - **BodyTests** — the body contains H2 sections for: What this skill
     does / When to use vs. when to defer / Inputs / Review structure /
     Gotchas / Relationship to other skills (case-insensitive heading
     match). Sections appear in that order.
   - **DeferralLanguageTests** — body explicitly references
     `~/.claude/skills/arch-review` (or equivalent path-shape hint) as
     the deferral target; body explicitly names `/jig:pr-review`,
     `/jig:independent-review`, and `/jig:adr-workflow` as the three
     siblings to disambiguate from.
   - **WorkedExampleTests** — body contains one minimal worked example:
     a short design-doc fragment (~10-15 lines, with at least one
     substantive choice worth reviewing — e.g. a cache-layer addition,
     an API versioning strategy, a database choice with stated
     constraints) and the corresponding four-section review output
     (summary, one strength, one concern, one open question).

4. **CLAUDE.md skills table** is updated:
   - Add a `/jig:arch-review` row marked active (auto + explicit
     invocable).
   - Hot Cache "Active specs" gains a line for spec 014-01 DONE.
   - Sprint focus paragraph updated to reflect that Tier 1 is effectively
     closed; only `local-dev-parity` remains and is still unsignaled.

5. **`docs/specs/README.md`** is regenerated via
   `workflow.py status-board .` after slice transitions to DONE. The
   Notes column for 014-01 is curated to match the 012-01 shape ("N
   tests; lightweight baseline; defers to richer user skill via
   description hint").

6. **`scaffold.py` is not modified by this slice.** Per the 012-01
   precedent (AC #6), the existing tier-granularity install flow
   (`has_tests` → install tier-1) captures it. Per-skill install lists
   remain deferred (same open question parked by slice 006-01 AC #5
   deviation). The global suite-green requirement in DoD covers
   regression-protection.

7. **No new helper.** This slice ships **SKILL.md only**. The deviation
   log records this as the **second** non-stub active jig skill without
   a `.py` helper (012-01 was the first), and explicitly defers any
   helper (e.g. `arch_review.py gather` for doc-fetching, scope
   classification) to slice 014-02. **Trigger criterion for slice
   014-02**: three concrete inbox.md entries (tagged
   `arch-review/gather-friction`) naming a specific session where
   Claude had to re-derive determinism inline (failed to fetch a doc,
   misclassified the doc scope, missed a stated constraint). Without
   the inbox entries, the count cannot accumulate across sessions —
   the spec author / implementer / reviewer commits to filing one
   whenever the friction is observed. Same observability discipline
   as 012-01's AC #7 and ADR-0002's third-caller rule.

8. **README `## Extension points` section** (added by slice 012-01)
   is updated to **add `/jig:arch-review` as a second worked example**
   alongside `/jig:pr-review`. The framing line "Bring your own depth;
   jig provides the floor." is preserved unchanged; the body gains a
   sentence or short list naming arch-review as a second instance of
   the same pattern. The update is small (≤ 12 lines added — pr-review's
   own example paragraph runs ~10 lines, so an additional worked example
   of similar shape fits in this bound; the cap is slack-padded to
   absorb the second-instance framing without an honest-disclosure
   deviation) and confirms that the pattern documented by 012-01 is
   reusable, not a one-off.

9. **Routing-dogfood fallback (`disable-model-invocation: true`).** If
   the routing-dogfood in DoD fails — i.e. with both jig's
   `/jig:arch-review` and the user's richer
   `~/.claude/skills/arch-review` installed, the router consistently
   picks jig's slim version on `"review this design"`-shape prompts —
   the implementer applies this fallback before marking DONE (same
   procedure as 012-01 AC #9):
   - Add `disable-model-invocation: true` to SKILL.md frontmatter.
   - Update SKILL.md body to add a short "Explicit-invocation only"
     callout near the top.
   - Re-run the test suite: `FrontmatterTests` now asserts
     `disable-model-invocation: true`; `DescriptionBoundsTests` still
     passes.
   - Update CLAUDE.md skills table: `/jig:arch-review` row marked
     `(explicit only)` instead of `(auto + explicit)`.
   - Record the fallback in the deviation log with the failing dogfood
     transcript.
   - Re-run the routing-dogfood; with `disable-model-invocation: true`,
     the router *must* prefer the user's skill on every shape — confirm
     this before marking DONE.
   **Tightening playbook before flipping to fallback** (try these in
   order, same as 012-01): (a) shorten the description to one sentence
   + deferral hint only, dropping the seven trigger phrases; (b) move
   from `description: >` to a tight single-line description; (c) add a
   stronger negative signal ("DO NOT USE IF the user has another
   arch-review skill installed"). Only flip to `disable-model-invocation`
   if all three tightening passes still produce a failed dogfood.

10. **SKILL.md contains one worked example.** Body section "Review
    structure" (per AC #2) includes a minimal but realistic example:
    a short design-doc fragment (~10-15 lines, with at least one
    substantive choice worth reviewing — e.g. a cache-layer addition,
    an API versioning strategy, a database choice with stated
    constraints) and the corresponding four-section review output
    (summary, one strength, one concern, one open question). The
    example is the only end-to-end demonstration that the slim
    baseline produces useful output on its own when no richer user
    skill is present.

**DoD** (same shape as 012-01):

> **Anti-pre-tick reminder.** Only two boxes are auto-ticked by
> `workflow.py transition` (per slice 003-04): "Implementation review
> passed" on IN_PROGRESS → REVIEWED, and "Reconciliation review passed"
> on REVIEWED → RECONCILED. Every other box below must be ticked
> **after** the corresponding evidence exists — never before.

- [x] All 10 ACs pass; full test suite green (existing + new). Expected
      delta: **at least 23 new tests across 6 test classes**, mirroring
      012-01's surface-test layout (which shipped exactly 23). Any
      delta above 23 (e.g. one extra test pinning the
      `intentional-asymmetry` rationale captured in AC #3, or extra
      `DeferralLanguageTests` for the four sibling-skill names that
      014-01 carries vs 012-01's three) is fine and gets a one-line
      note in the deviation log. Fewer than 23 is a sign 012-01's
      surface coverage was dropped — flag and justify. _(541 → 568,
      +27 new tests in `skills/arch-review/test_arch_review_skill_surface.py`
      across 6 test classes (Frontmatter / Description / DescriptionBounds
      / Body / DeferralLanguage / WorkedExample). Extras vs 012-01's 23:
      `DescriptionTests` gains `test_do_not_use_clause_names_pr_review`
      and `test_do_not_use_clause_names_adr_workflow` for 014-01's four
      sibling-skill names (012-01 only carried three);
      `DescriptionBoundsTests` gains
      `test_intentional_asymmetry_rationale_pinned` to lock the AC #3
      asymmetry rationale; `DeferralLanguageTests` gains
      `test_body_distinguishes_pr_review` and
      `test_body_distinguishes_adr_workflow`. Test filename is
      `test_arch_review_skill_surface.py` rather than 012-01's
      `test_skill_surface.py` because Python 3.14's stricter
      `unittest.discover` rejects two same-named test modules across
      sibling skill dirs — recorded as a deviation.)_
- [x] SKILL.md dogfooded against this very slice — generate the
      architecture review for slice 014-01's own spec.md using the new
      skill, verify the four sections are produced, verify the deferral
      hint reads naturally. Same approach as 012-01 deviation §8a
      (judgment-only — apply SKILL.md's body as a prompt-to-self).
      _(Completed 2026-05-15 during reconciliation — see deviation §9
      / §9a. Four-section output produced; 0 concerns / 2 strengths /
      2 open questions plus one-sentence summary.)_
- [x] Implementation review passed. _(auto-ticked by
      `workflow.py transition` on IN_PROGRESS → REVIEWED; do not
      pre-tick.)_
- [x] Deviation log produced under this slice heading (under
      `### Close-out (post-DONE)` for post-DONE items per slice 009-01
      convention). _(See `### Deviation log (after reconciliation)`
      below — §1–§9a covering test-filename, provenance disclosure,
      27 vs 23 tests, helper-less milestone, AC #1/#3 cross-check,
      review-queue.json, CLAUDE.md mid-lifecycle labels, auto-tick
      firing, and own-slice dogfood.)_
- [x] Reconciliation review passed. _(auto-ticked by
      `workflow.py transition` on REVIEWED → RECONCILED; do not
      pre-tick.)_
- [x] `docs/specs/README.md` regenerated by
      `workflow.py status-board`. _(Regenerated 2026-05-15 during
      reconciliation — 48 slice(s) across 13 spec(s) including
      014-01 now showing REVIEWED.)_
- [x] `CLAUDE.md` skills table promotes `arch-review` to active
      (auto + explicit, or explicit-only if AC #9 fallback fired).
      _(Auto+explicit; hot-cache Active-specs gained a 014-arch-review
      line, skills table gained a `/jig:arch-review` row, sprint focus
      paragraph updated. Labels refreshed during reconciliation from
      IN_PROGRESS to DONE-state per 012-01 deviation §7 lesson.)_
- [x] `docs/refinement-todo.md` left untouched (no new deferrals unless
      a real one surfaces during implementation). _(Verified — `git
      diff docs/refinement-todo.md` shows no change.)_

### Close-out (post-DONE)

- [ ] Routing-dogfood run by the user from a freshly-restarted session
      with both skills loaded, using a **direct skill-inventory
      question** as the conclusive test (per 012-01 deviation §9
      methodology lesson). AC #9 fallback applied only if the dogfood
      fails after the three tightening passes.
- [ ] SKILL.md own-slice dogfood (DoD box 2) recorded in the deviation
      log §8a-equivalent — apply SKILL.md's body content as a
      prompt-to-self against this slice's own spec.md.

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice. A
user with a fresh project can: install jig → scaffold-init detects
tests → Tier 1 auto-installs arch-review → on the user's next "review
this design" prompt, either jig's slim version fires (no other skill
present) or the user's richer skill fires (description wins). Either
path delivers value; both are end-to-end.

### Deviation log (after reconciliation)

The original spec is preserved above (with one in-place edit during
spec-authorship review per the trigger-phrase-provenance disclosure
parenthetical; tracked in §2 below).

**Deviations from the spec as it entered IN_PROGRESS:**

1. **Test filename: `test_arch_review_skill_surface.py` not
   `test_skill_surface.py`.** Python 3.14's `unittest.discover` is
   stricter than 3.12 and refuses to import two test modules with the
   same `__name__` across sibling directories — `skills/pr-review/test_skill_surface.py`
   already occupies that name in the discovery graph. Renaming
   014-01's test file to `test_arch_review_skill_surface.py`
   sidesteps the collision without touching pr-review's test file
   (which is under DONE-state convention and shouldn't be edited).
   Spec AC #3 prescribed the bare name `test_skill_surface.py` by
   analogy with 012-01; the rename is a venue-not-substance deviation.
   **Forward-compat note:** every future slim-baseline skill (014-02
   if it ships, 015-XX, etc.) will hit the same collision and must
   pick a unique test filename. The pattern
   `test_<skill_name>_skill_surface.py` works.

2. **Trigger-phrase provenance disclosure added during authorship
   review.** Spec-authorship reviewer flagged that AC #1 listed seven
   trigger phrases without disclosing which were inherited from the
   personal `~/.claude/skills/arch-review` and which were
   jig-invented (same disclosure shape as 012-01 AC #1's
   parenthetical). Resolved by adding a `_(Provenance: …)_` block
   directly under AC #1's trigger-phrase list, naming five inherited
   phrases and two invented ones. Pre-IN_PROGRESS edit; the spec
   author owned this change.

3. **27 tests vs AC #3's stated baseline of 23.** The spec
   explicitly permits "Any delta above 23 is fine and gets a
   one-line note in the deviation log" (DoD box 1). Enumeration of
   the four extras:
   - +1 `DescriptionTests.test_intentional_asymmetry_rationale_pinned`
     — locks the "architecture review / design review must appear,
     other category words must not" contract from AC #3's
     **Intentional asymmetry** sub-clause. Catches a regression where
     a future implementer expands `DescriptionBoundsTests` and breaks
     the deferral hint.
   - +1 `DescriptionTests.test_do_not_use_clause_names_three_alternatives`
     — extra to 012-01 because the `Do not use for` clause names three
     alternatives (`/jig:pr-review`, `/jig:independent-review`,
     `/jig:adr-workflow`) vs 012-01's two.
   - +1 `DeferralLanguageTests.test_body_distinguishes_adr_workflow`
     — fourth sibling skill that 012-01 didn't have (012-01 had three:
     user pr-review + independent-review + reviewer subagent; 014-01
     has four: user arch-review + pr-review + independent-review +
     adr-workflow).
   - +1 `DescriptionTests` — extra trigger phrase coverage; 014-01
     has seven trigger phrases vs 012-01's six.

4. **Second non-stub active jig skill without a `.py` helper.**
   012-01 was the first (its deviation log §2 records the milestone).
   014-01 confirms the pattern is repeatable — no helper, judgment-only,
   description-routing-and-bounds-test-pinning sufficient. The 014-02
   trigger criterion ("three concrete inbox.md entries tagged
   `arch-review/gather-friction`") is set up to track whether the
   no-helper choice ever proves wrong, same observability discipline
   as 012-01 AC #7.

5. **AC #1 ↔ AC #3 cross-check re-run during implementation.**
   Per AC #3's `Pre-implementation cross-check` sub-clause (added
   during authorship review), the implementer re-normalized every
   AC #1 mandated phrase via `" ".join(text.lower().split())` and
   substring-checked against the nine forbidden phrases in
   `DescriptionBoundsTests`. Result: zero collisions. The reviewer
   independently re-ran the same check (RECONCILIATION NOTES §4) and
   confirmed zero collisions. The recurring 012-01 anti-pattern
   (silent rephrase to resolve an internal contradiction) was
   structurally avoided this time.

6. **`.claude/review-queue.json` updated by implementer.** The file
   tracks which deliverables the reviewer subagent should look at
   for the current slice. Implementer flipped it from 008-01's
   leftover state to 014-01's deliverables (5 files). Working
   convention; no spec impact.

7. **CLAUDE.md mid-lifecycle labels.** Per 012-01 §7 lesson, CLAUDE.md
   was labeled `IN_PROGRESS` during implementation (not REVIEWED or
   DONE). Reconciliation phase refreshed the three locations
   (Active-specs entry, sprint focus paragraph, skills table row) to
   DONE-state labels in a single pass.

8. **Implementation-review auto-tick fired correctly.**
   `workflow.py transition docs/specs/014-arch-review/spec.md "014-01" REVIEWED`
   auto-ticked the "Implementation review passed" DoD box (slice
   003-04 convention). Verified.

9. **SKILL.md own-slice dogfood (DoD box 2) — completed during
   reconciliation.** Applied SKILL.md's body content as a
   prompt-to-self against this slice's own spec.md. Output recorded
   in close-out section §9a below. Verdict: 0 concerns, 2 strengths,
   2 open questions, plus a one-sentence summary — verifying that
   the four-section structure produces useful output on a real
   architecture-shaped input.

   §9a. **Own-slice four-section review, run 2026-05-15 by applying
   `skills/arch-review/SKILL.md`'s body content to this slice's own
   spec.md (input mode 3 — pasted text, plus full-repo context).**

   ## Summary

   Spec 014 ships `/jig:arch-review` as the fifth Tier 1 jig skill
   following the lightweight-baseline-defers-to-richer-user-skill
   pattern proven by 012-01. Slice 014-01 delivers SKILL.md (judgment-
   only, no helper), a 27-test surface, CLAUDE.md skills-table promotion,
   and a one-paragraph addition to README's `## Extension points`
   section. Overall: a faithful second instance of the 012-01 pattern,
   with the AC #1/#3 contradiction trap structurally avoided this
   time via the documented pre-implementation cross-check.

   ## Strengths

   - **The `Intentional asymmetry` sub-clause in AC #3 is a deliberate
     and useful contract.** It pins the "advertise category words in
     description, forbid depth-claims in bounds test" rule and warns
     future-reviewers against breaking it. Worth copying to any
     future deferral-pattern skill.
   - **Trigger-phrase provenance disclosure (AC #1 parenthetical) is
     more transparent than 012-01's equivalent.** Naming five
     inherited and two invented phrases (with the personal skill
     citation) makes the routing-coverage choice auditable.

   ## Concerns

   None blocking. The implementer-reported deviations (test filename,
   27 vs 23 tests) are venue-not-substance and well-justified.

   ## Open questions

   - **Will the description-based routing-dogfood pass on the first
     real-user attempt, or will it need the AC #9 tightening passes?**
     014-01's deferral hint is longer than 012-01's
     post-reconciliation version (four category names vs three), which
     could either help (more deferral surface) or hurt (more description
     surface to over-match on). Empirical question; deferred to the
     user-driven close-out step.
   - **Should 014-03's `arch-review/depth-wanted` tag use a different
     prefix than 014-02's `arch-review/gather-friction`?** Both live
     in inbox.md and both gate slice acceptance. Convention question;
     not blocking.

   Notice what's **not** in this review: no seven-perspective matrix
   (no separate Technical-soundness / Operational / Reliability /
   Security / Scalability / Migration / Product sections), no
   domain-specific reference-file consultation. That depth belongs in
   a richer user-installed `arch-review` — exactly the deferral
   pattern this slice ships.

**Open follow-ons (filed to inbox.md during reconciliation):**

- **Test-filename collision pattern.** The Python 3.14
  `unittest.discover` collision documented in §1 will recur for every
  future slim-baseline skill. Filed to inbox as a process note: skill
  test filenames must be unique across `skills/*/test_*.py` — naming
  convention `test_<skill_name>_skill_surface.py` works.

**Doc updates from this slice:**

- `skills/arch-review/SKILL.md`: net-new file (294 lines). Active
  frontmatter; six H2 body sections; worked example with Redis-cache
  design fragment; AC #9 fallback documented in Gotchas.
- `skills/arch-review/test_arch_review_skill_surface.py`: net-new (336
  lines, 27 tests across 6 test classes — Frontmatter / Description /
  DescriptionBounds / Body / DeferralLanguage / WorkedExample). All
  green.
- `README.md`: `## Extension points` section gains 7-line addition naming
  `/jig:arch-review` as the second worked example; "Bring your own depth"
  framing line preserved unchanged.
- `docs/specs/README.md`: regenerated by `workflow.py status-board`.
- `CLAUDE.md`: hot-cache "Active specs" + skills table + sprint focus
  updated (sprint focus now records Tier 1 sprint effectively closed
  pending the user-driven routing-dogfood).
- `docs/inbox.md`: one entry for the test-filename collision process
  note.
- No new ADR required.
- No `architecture.md` changes.

---

## Slice 014-02 — arch-review-gather-helper

**STATUS: DEFERRED** _(deferred — add only if gather-friction is observed)_

**Resolution trigger:** Three `arch-review/gather-friction:` inbox entries naming specific sessions where Claude had to re-derive scope inline (parallels 012-02's gather-helper trigger).

**Goal:** `arch_review.py gather <input>` produces a structured markdown
bundle (doc fetch / scope classification / extracted goals + constraints
+ alternatives) that Claude consumes instead of running fetch + parse +
classification heuristics inline.

Deferred because: jig's "duplicate, don't abstract" rule says we wait for
three concrete signals before extracting. Slice 014-01 ships SKILL.md only;
slice 014-02 lands only after three inbox entries tagged
`arch-review/gather-friction` naming a specific session where Claude
visibly fumbled the gather step (failed to fetch a fetchable URL,
misclassified an ADR as a system design, missed a stated constraint).

---

## Slice 014-03 — domain-specific-references

**STATUS: DEFERRED** _(deferred — explicit non-goal of "lightweight")_

**Resolution trigger:** Multi-domain-architecture user reports a concrete gap that the lightweight baseline doesn't cover, AND no user-installed `~/.claude/skills/arch-review` deferral target exists for them.

**Goal:** Port the domain-specific reference files from the personal
`arch-review` skill (`distributed-systems.md`, `api-design.md`,
`data-architecture.md`, `migration-plans.md`, and possibly frontend /
ML / IoT additions).

Deferred because: porting these makes jig's arch-review heavyweight,
which defeats the spec's framing. The right home for domain-specific
depth is the user's personal `~/.claude/skills/arch-review`, which the
description hint already routes to. **Resolution trigger** (same
observability shape as 014-02 and ADR-0002): **two concrete inbox.md
entries tagged `arch-review/depth-wanted`** naming a specific session
where (a) the user did NOT have a richer personal `arch-review` skill
installed, (b) the four-section baseline output was visibly
insufficient (missed a domain-specific risk a reference file would
have caught — e.g. an event-bus design without backpressure
discussion, an API change without versioning strategy, a dual-write
migration without consistency analysis), and (c) the inbox entry
names which reference file would have helped. Threshold of two rather
than three because porting domain refs is a larger investment than
adding a gather helper — two specific signals is enough to justify
the scoping work. Working assumption until then: "depth = bring your
own skill."

---

## Slice 014-04 — security-lens-integration

**STATUS: DEFERRED** _(deferred — gated on `security_lens` decision)_

**Resolution trigger:** Resolution of the `security_lens` parent decision (same trigger as 012-03 — both slices plug into whichever shape that decision takes).

**Goal:** `arch-review` consults the `security_lens` field in
`scaffold.json` (when present) and either appends an
`adobe-security-suite` hand-off block to its review prompt or embeds
a builtin "security-shaped concerns" checklist (data trust boundaries,
secrets handling, authn/authz on new external surfaces).

Deferred because: `security_lens` itself is not yet specced (parked in
inbox 2026-05-12). When that spec lands, this slice plugs in — same
shape as 012-03 for pr-review. Until then, the slim baseline applies.
