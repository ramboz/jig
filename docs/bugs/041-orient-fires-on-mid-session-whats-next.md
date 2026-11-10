---
status: DONE
tier: standard
severity: medium
claimed_by: claude/jig-orient-whats-next-6768fe
regression_test: skills/orient/test_orient_skill_surface.py::Bug041MidSessionScopeTests
main_repro_checked_at: 2026-11-10
main_repro_ref: origin/main@35826fb0
main_repro_result: reproduces
red_confirmed_at: 2026-11-10
green_confirmed_at: 2026-11-10
fix_class: structural_fix
security_surface: false
escalated_to:
closure_schema: 1
review_reopened_at: 2026-11-10T19:06:19Z
---

# Bug 041: orient-fires-on-mid-session-whats-next

Reported: owner, in-session (2026-11-10).

## Symptom

Mid-session, with a plan / task list / slice in progress, a bare *"what's
next?"* (meaning "what's the next step in this plan") has a high chance of
firing `jig:orient`. Orient then runs its full project-wide survey (PRs,
unmerged branches, ADRs, DEFERRED triggers, refinement-todo, inbox, bug board)
and renders the multi-section briefing. The owner's words: *"it's too long, too
verbose, and doesn't really answer my immediate question."*

This contradicts orient's own contract: its description already says *"Do not
use for mid-implementation questions about the current slice such as 'what's
next?'"* (present since the skill shipped, 0b76648c), and spec 088-02 AC3 is the
trigger boundary.

## Repro

Lexical proxy (the repo's own routing eval, `scripts/skill_routing.py`, which
scores the description's *positive* routing surface):

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, 'scripts')
import skill_routing as sr
c = sr.Corpus(sr.load_descriptions())
for p in ["ok, what's next?", "what's the next step in the plan?",
          "done with that task — what's next?", "what should I pick up next?"]:
    print(p, '->', c.rank(p)[:3])
EOF
```

On `origin/main@35826fb0` every prompt ranks `orient` #1, and for three of the
four every other skill scores 0.00:

| Prompt | Top match |
|---|---|
| "ok, what's next?" | orient 0.13, all others 0.00 |
| "what's the next step in the plan?" | orient 0.19, all others 0.00 |
| "done with that task — what's next?" | orient 0.13, all others 0.00 |
| "what should I pick up next?" | orient 0.16, contracts 0.07 |

Model-level repro (non-deterministic, the reported one): in a session with an
active plan, ask "what's next?" → `Skill(jig:orient)` fires and renders the full
briefing.

**Not settled by the lexical surface: "what should I pick up next?"**
It reproduced in the table above and still ranks orient #1 lexically after the
fix (0.11 vs contracts 0.09, via "pick up across the repository"), so it is
left out of the lexical regression set, which uses "next task?" instead. Under
the owner's design it is a "what's next" variant: the description lists it
among the bare next-step questions, and the body's scope check names it there
too, so if orient loads on it anyway the scope check gives the short answer and
the offer (pinned by `test_pick_up_next_is_a_whats_next_variant`).

## Evidence

- `skills/orient/SKILL.md` description, positive surface: *"…or what to pick up
  next across the repository."* No other skill's description contains `next`
  in its positive surface (the ranking above: zero scores everywhere else).
- Same description, negative tail: the exclusion is scoped to
  *"mid-implementation questions about the current slice"*. Between slices,
  right after a plan is written, or after a task completes, the session is not
  "mid-implementation", so the exclusion reads as not applying.
- `skills/orient/SKILL.md` `## Judgment`: *"Check the collaboration layer
  **every run — including on a re-ask later in the same session**"* (spec
  101-01 AC8). Once orient has been loaded in a session, this line tells the
  model to redo the full survey on any later "what's next".
- The body's only early scope statement is the 088-02 paragraph just before
  the headline command: "a bare conversational 'what's next?' while actively
  implementing a slice is asking to continue that slice — not to re-survey
  the whole project". It is as narrow as the description: it tells orient to
  skip the survey only while a slice is being implemented, and never says to
  answer briefly or stop. Between steps of a plan, nothing tells a misfired
  orient to skip the survey. A Gotchas bullet near the end of the file repeats
  it, read after the survey has already run.
- `evals/cases/orient.json` negatives cover only prompts carrying another
  skill's vocabulary ("I just wrote the failing test — what's next?" →
  tdd-loop). No bare next-step prompt is tested, and the negative gate is a
  rate floor (`MIN_NEG_ROUTE_AWAY = 0.90` over 44 negatives), so 4 failing
  negatives (44/48 = 92%) would not turn the suite red.
- Environmental contributor (out of scope): in the reporting session the host's
  skill listing showed `tdd-loop` name-only (description dropped under the
  listing budget) while orient's 950-char description showed in full, twice in
  the jig repo (plugin + `.claude/skills` symlinks).

## Hypotheses

- [ ] H1: Host-side listing budget hides the rival owners (`tdd-loop` shown
  name-only), so orient wins by default. Falsify by: the lexical eval, which
  sees every description in full, still ranks orient #1 for bare next-step
  prompts. **Falsified as the root cause** (ranking above) — it is a
  contributor that makes the misroute worse, not its origin.
- [ ] H2: The model ignores negative clauses in descriptions in general.
  Falsify by: other skills' route-away negatives pass at 100% in the lexical
  eval, and orient's own existing negatives route away correctly. The negative
  clause is not ignored; it is *too narrow* for the reported case.
- [x] H3 (leading): orient's routing contract is mis-scoped. (a) Its positive
  surface is the only one in the pack that claims "next" ("what to pick up next
  across the repository"); (b) its exclusion names only mid-implementation of
  the current slice, not the broader in-session next-step question; (c) its
  body's early scope paragraph is just as narrow and gives no stop
  instruction, and its Judgment re-ask rule mandates a full rescan on any
  same-session re-ask. Confirm by: the ranking above (a), the description
  text (b), and the 088-02 paragraph plus the Judgment line (c).

## Root cause

The process producing the misfire is orient's own routing contract, not the
model:

1. **Positive surface claims "next" alone.** The phrase "what to pick up next
   across the repository" is the only "next" vocabulary in any jig skill
   description (enumerated: `scripts/skill_routing.py` scores every
   `skills/*/SKILL.md` description; for the four prompts all non-orient skills
   score 0.00 except `contracts` 0.07 on one prompt — the set is closed by the
   eval loading every description).
2. **Exclusion too narrow.** "Mid-implementation questions about the current
   slice" does not cover "the next step in the plan / task list / slice queue"
   asked between steps.
3. **The body's scope note is too narrow, and the re-ask rule
   over-applies.** The 088-02 paragraph before the headline command is as
   narrow as the description ("while actively implementing a slice") and
   never says to answer briefly or stop. The Judgment rule (101-01 AC8) was
   written for a re-ask *of orientation* — the
   field incident was a project-level "what's next" pass that missed an open
   PR — but is phrased as any re-ask in the session.

Spec 101's incident must stay fixed: when the user wants the project-level
"what's next", orient must run the collaboration survey. A bare "what's next?"
can mean either the next step in the current plan or the whole project, so the
fix (per the owner decision below) always gives the cheap answer first and
offers the expensive one, rather than guessing.

## Owner decision

The first fix inferred the scope from context (work in progress → short
answer; nothing in progress → full; unsure → short). After talking with a
user, the owner redesigned it (2026-11-10, owner's words):

> * if the user explicitly calls /jig:orient => run the full skill
> * if the user asks "what's next", prompt them if they want just the next
>   task the llm knows about in its plan, or the full project orientation
>    * just the next => let the llm answer directly
>    * the full => run orient skill

Revised again the same day, before any review of that version completed
(owner's words):

> * "what's next" always runs the short version
> * and it asks if the user wants the full version
>    * if no, stops there
>    * if yes, runs the full jig:orient

The explicit-`/jig:orient` rule from the first revision stands. The fix
implements this last version.

## Repository closure inventory

<!-- Spec 091 / ADR-0037: pre-fix repository closure. Standard & gnarly
     bugs gate ROOT_CAUSED -> FIXING on substantive answers below. This
     is an effort-and-protocol standard, NOT a completeness proof: show
     the search you actually ran. A bare "none found" fails; record
     residual uncertainty as an assumption WITH the protocol behind it,
     applying the same enumeration standard as `## Root cause` (ADR-0052).
     Prefer a configured semantic index; the portable floor is targeted
     search + `git log`/`git blame`. -->

**Equivalent / convergent logic searched:** `grep -rn -i` over
`*.md/*.json/*.py/*.toml/*.template` for `pick up next`, `what to pick up`,
`whole-project session pickup`, `what's next` / `whats next` / `what next`;
`grep -rn orient hooks/`; `grep -n orient` in `templates/CLAUDE.md.template`,
`templates/AGENTS.md.template`, `docs/memory/glossary.md`, `docs/workflow.md`,
`docs/architecture.md`, `README.md`. Found: orient's description in
`skills/orient/SKILL.md` + three generated host copies; the SessionStart hook
`hooks/scripts/jig-project-orient.sh` (emits the `jig hint:` headline, never
names the skill or "next"); templates point to `/jig:orient` "before selecting
work" (project-level, correct); `docs/product-vision.md` UC-11 ("see where the
project stands and what to pick up next" — a use-case statement, not a routing
surface). No other skill description carries next-step vocabulary (the
lexical eval loads every description; see Root cause 1).

**Relevant history inspected:** `git log -S "mid-implementation questions"` →
0b76648c (orient shipped with the narrow exclusion, 2026-07-15). `git log` on
`skills/orient/SKILL.md`: f0a5be4e (101-01, added the Judgment re-ask rule and
the "what's next means blocked on a human" principle — the `bouge` field
incident, a project-level "what's next" that missed an open PR), fafa42a9 (bug
031 `--fetch`), aef9cb7f (088-02 close-out), 13a691a2 (116-02 progress). No
change ever revisited the trigger boundary after 088-02.

**Affected call sites:**
1. `skills/orient/SKILL.md` — frontmatter `description:` (positive surface +
   exclusion).
2. `skills/orient/SKILL.md` — body: intro "project-level rescan" paragraph,
   `## Judgment` re-ask rule, `## Gotchas` mid-flow bullet.
3. `hosts/claude/skills/orient/SKILL.md`, `hosts/codex/plugins/jig/skills/orient/SKILL.md`,
   `hosts/copilot/.github/skills/orient/SKILL.md` — generated copies.
4. `evals/cases/orient.json` — trigger cases.
5. `skills/orient/test_orient_skill_surface.py::OrientJudgmentRuleTests` — pins
   the 101-01 AC8 re-ask phrase.
6. `templates/CLAUDE.md.template` / `templates/AGENTS.md.template` — route
   "before selecting work" to orient.
7. `docs/product-vision.md` UC-11.

**Reuse decision:** Reuse the existing routing machinery — description
wording + `evals/cases/` + `scripts/skill_routing.py` — and the existing
surface-test file; no new hook, gate, or helper. The in-body scope check reuses
the 088-02 "project-level rescan, not a mid-flow nudge" paragraph rather than
adding a parallel section.

## Fix class

`structural_fix` — corrects the routing contract (positive surface, exclusion,
in-body scope rule) that produces the misfire, rather than suppressing orient
output after the fact.

## Fix

Three edits to `skills/orient/SKILL.md`, one per root cause, following the
owner decision:

1. **Description, positive surface** — "what to pick up next across the
   repository" → "what to pick up across the repository". The survey list now
   says "release scope" instead of "release plans" (the body's survey bullet
   says these docs tell you "what's in-scope for the next release"; "plans"
   lexically matched "the next step in the plan"), and the list was
   tightened so the description stays under Copilot's 1024-character
   skill-loader limit: 994 characters (950 before), below memory-sync's 1010,
   so memory-sync stays the longest and the
   `scripts/test_build_copilot_plugin.py` docstrings that say so stay true.
   Note the limit is not a hard gate: `build_copilot_plugin.py` silently
   shortens an over-limit description in the render.
2. **Description, exclusion** — "mid-implementation questions about the
   current slice" is replaced by the shipped clause: *Do not use for a bare
   "what's next?" ("next step?", "what should I pick up next?"): answer it
   directly with the next step from the current plan or session context,
   then ask whether the user wants the full project orientation, and run
   this skill only if they say yes.* The "what's blocking this test?" example
   is kept. The clause sits in the negative tail, so orient's lexical
   positive surface still claims no "next". To make room, the output-format
   clause ("render one readable headline, titled sections, one
   recommendation, and an owning-skill handoff") became "then recommend where
   to start".
3. **Body** — the 088-02 "project-level rescan, not a mid-flow nudge"
   paragraph becomes a `## Scope check — before running anything` section
   placed ahead of the headline command (a backstop for when the skill loads
   on a "what's next?" anyway):
   - the user invoked `/jig:orient`, or explicitly asked for the whole-project
     picture → run the full orientation, don't ask first;
   - the user asked "what's next?" or any bare next-step question ("next
     step?", "next task?", "what should I pick up next?") → give the short
     answer first, in a line or two (the next step in the plan or task list in
     progress, else the SessionStart `jig hint:` focus, else say you have no
     current plan in view), then ask one question: do they want the full
     project orientation?
     - no → stop, with no headline command, survey, or briefing;
     - yes → run the full orientation, collaboration survey included (spec
       101's path).
   - unsure which case a question fits → treat it as a "what's next?".

   The `## Judgment` bold lead is scoped to the full orientation ("In a full
   orientation, 'what's next' means what is blocked on a human"), so it no
   longer contradicts the scope check. The `## Judgment` re-ask rule (101-01
   AC8) now reads "a later re-ask for orientation in the same session", and
   says a "what's next?" becomes one only once the user says yes to the full
   orientation. The `## Gotchas` bullet treats "what's next?" as a request
   for the next step plus the offer.

   **Cost (accepted by the owner's design):** every bare "what's next?" ends
   with one extra question. In exchange the immediate question is always
   answered, there is never an unasked-for briefing, and a project-level ask
   (spec 101's PR case) is one "yes" away; the offer is always made, never
   skipped on a guess.

Plus four owner-less negatives in `evals/cases/orient.json`, a note in
`evals/README.md`, and the two regression-test classes; host packages
regenerated (`scripts/build_host_packages.py`, `--check` clean).

**Why the new negatives have no `owner`** (the first owner-less negatives in
`evals/cases/`): no skill should be routed to directly for a bare next-step
question; the agent answers it itself and then offers the full orientation.
An owner-less negative only checks "orient is not rank #1", which on an
all-zero tie passes or fails on alphabetical order alone. So the real guard is
the score-based `Bug041OrientNextStepRoutingTests`, which asserts orient
scores 0 or below another skill per prompt.

Orient's project-level triggers are unchanged or stronger. Orient's lexical
rank, old description → new (re-run 2026-11-10): "I'm back after a week off —
where are we overall?" 1→1, "give me the big picture of the project" 1→1,
"orient me" 1→1, "what should I pick up across the repo?" 1→1, and "where does
the project stand and what should I start on?" 3→1 (contracts 0.10 led the
old ranking; the new "recommend where to start" wording lifted orient to
0.13).

## Spec interactions (closed records untouched)

- **101-01 AC8** says to "check the collaboration layer again on a later
  re-ask in the same session". The live SKILL.md prose now scopes that to a
  re-ask *for orientation*, which a "what's next?" becomes once the user says
  yes to the full orientation; the full path then re-checks as AC8 requires. The
  closed 101 record is not amended (spec 102 / ADR-0010); surfaced to the
  owner. AC8's principle line ("'what's next' means what is blocked on a
  human") also now carries the qualifier "In a full orientation".
- **Session start:** a bare "what's next?" with nothing in progress now gets
  the short answer (the `jig hint:` focus) first, so a PR waiting on the user
  (spec 101's incident) surfaces only after the user says yes. Owner-accepted:
  the offer is always made.
- **088-02 AC3** (trigger boundary) named "a bare conversational 'what's
  next?' inside an active implementation flow" as a route-away case. The
  owner decision makes every bare "what's next?" a short answer plus an offer
  of the full orientation. The 088-02 record is not amended.
- **Description wording (088-02 AC2's survey list):** the description's
  survey list says "release scope" where it said "release plans" (the body's
  survey bullet is unchanged), and the output-format clause became "then
  recommend where to start". No AC or test pins either string; both changes
  serve the lexical proxy and the Copilot 1024-character limit.
- **Environmental contributor (out of scope, logged):** the description grew
  from 950 to 994 characters, which slightly adds to the host skill-listing
  budget that dropped rival descriptions (e.g. `tdd-loop`) to name-only in the
  reporting session.

## Implementer choices beyond the owner's wording

- "Explicitly asked for the whole-project picture" (session pickup, return
  after time away) also runs the full orientation without asking. That is
  inference, not owner text; it keeps orient's existing positive triggers.
- The short answer's fallbacks (the SessionStart `jig hint:` focus, else
  "say you have no current plan in view" — not "nothing is in progress",
  which would claim an unchecked project state) and the "unsure → treat it as
  a 'what's next?'" tie-breaker. The tie-breaker errs toward the owner's
  short-answer rule.

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**

1. `skills/orient/SKILL.md` `description:` — **changed** (Fix 1–2);
   **tested** by `Bug041MidSessionScopeTests` (positive surface, exclusion) and
   `Bug041OrientNextStepRoutingTests` (per-prompt lexical check).
2. `skills/orient/SKILL.md` body (intro paragraph, `## Judgment`, `## Gotchas`)
   — **changed** (Fix 3); **tested** by `Bug041MidSessionScopeTests` (scope
   check placement, explicit invocation runs without asking, "what's next?"
   short answer then offer, the no and yes paths, re-ask scoping).
3. Host copies (`hosts/claude`, `hosts/codex`, `hosts/copilot`) —
   **changed** by regeneration; **tested** by `build_host_packages.py --check`
   (CI drift gate).
4. `evals/cases/orient.json` — **changed** (four negatives); **tested** by
   `test_bare_next_step_prompts_are_authored_orient_negatives` and the
   route-away ratchet.
5. `OrientJudgmentRuleTests::test_re_ask_within_a_session_is_covered` (101-01
   AC8) — **left alone, still green**: the re-ask rule is kept, only scoped to
   orientation.
6. `templates/CLAUDE.md.template` / `templates/AGENTS.md.template` —
   **intentionally left alone**: they send the agent to `/jig:orient` "before
   selecting work", which is the project-level case orient still owns. Edge
   case, untested: if the agent loads orient on its own at session pickup
   (no user ask), the scope check's "unsure → treat it as a 'what's next?'"
   rule gives a short answer plus the offer rather than a full briefing. That
   fits the owner's cheap-first intent.
7. `docs/product-vision.md` UC-11 — **intentionally left alone**: a use-case
   statement ("see where the project stands and what to pick up next"), not a
   routing surface; it describes the project-level need orient still serves.
8. `hooks/scripts/jig-project-orient.sh` — **intentionally left alone**: emits
   the one-line `jig hint:` headline, never names the skill or next-step
   wording.

## Already tried

- **First design (superseded by the owner decision):** infer the scope from
  context. Work in progress → answer in a line or two and offer
  `/jig:orient`; nothing in progress (or right after a briefing) → full
  orientation; can't tell → short path plus the offer. It passed both review
  passes (bug-review needed a second round to pin the explicit-invocation and
  post-briefing cases) and reached `DONE` in the working tree before commit.
  Its residual risk was a project-level "what's next?" misread as in-session,
  leaving a waiting PR unmentioned until the user took the offer. The owner
  replaced the inference with a question; see `## Reopen log`.
- **Second design (superseded the same day, review stopped unfinished):** on
  "what's next?", ask first whether the user wants just the next step or the
  full orientation, then branch. The owner revised it to always give the short
  answer first and offer the full orientation after, so the immediate question
  is answered without a round-trip.
- First description rewrite kept "release plans" in the survey list and added
  "explicitly asks to step back for": the routing check still ranked orient #1
  for "what's the next step in the plan?" (first via "plans", then via "step"),
  and the description was 1046 characters, over Copilot's 1024 limit. Replaced
  "release plans" with "release scope", dropped "to step back", and tightened
  the survey list.

## Regression test

`skills/orient/test_orient_skill_surface.py::Bug041MidSessionScopeTests`
(surface: positive surface, short-answer-then-offer exclusion, in-body scope
check with explicit invocation / short answer + offer / no / yes, re-ask rule
scoped to orientation) and
`scripts/test_skill_routing.py::Bug041OrientNextStepRoutingTests` (hard
per-prompt lexical check: orient scores 0 or below another skill for each
bare next-step prompt). Plus four new owner-less negatives in
`evals/cases/orient.json`.

## Proof

- **Red, witnessed by the gate in round 1** (`→ FIXING`,
  `red_confirmed_at: 2026-11-10`): the full suite failed with the first
  design's regression classes in place and the old SKILL.md. The reopen's
  `REVIEWED → FIXING` back-edge is ungated, so the gate did not re-witness red
  for the final classes.
- **Red re-run for the final classes** (2026-11-10, against `origin/main`'s
  `skills/orient/SKILL.md` in a scratch copy): `Bug041MidSessionScopeTests`
  3 failures + 8 errors (no `## Scope check` section to index; positive
  surface contains "next"; no answer-then-offer exclusion);
  `Bug041OrientNextStepRoutingTests` 4 failing prompts (orient scores above
  every other skill on each).
- **Green in round 1** (`→ REVIEWED`, first design): the gate ran the full
  suite + pyright green and stamped `green_confirmed_at`. That run predates
  the final classes; the final `→ REVIEWED` gate run is recorded below.
- **Green, witnessed by the gate on the final code** (`FIXING → REVIEWED`,
  2026-11-10, after the reopen): full suite + pyright green, re-stamping
  `green_confirmed_at`. That run covers both final classes
  (`regression_test:` names `Bug041MidSessionScopeTests`;
  `scripts/test_skill_routing.py::Bug041OrientNextStepRoutingTests` runs in
  the same suite), and both verdicts were recorded after
  `review_reopened_at`.
- **Routing report after the fix** (`python3 scripts/skill_routing.py`): all 11
  orient cases pass, three positives at rank 1; the four bare next-step
  prompts put orient at rank 12 (score 0.00).
- **CI-only checks run locally:** `uvx ruff check .` clean;
  `scripts/skill_routing.py --min-rank1 0.85` exit 0; `scripts/spec_lint.py
  --all` no contradictions; `scripts/validate_manifests.py` 5/5 valid;
  `scripts/build_host_packages.py --check` in sync; `bug.py check-board` clean.

## Learning

Recorded in `docs/memory/learnings.md` → "Bug 041: a route-away clause can't
beat being the only positive match".

## Main recheck

- 2026-11-10 - `origin/main@35826fb0` -> reproduces: skill_routing Corpus.rank on origin/main@35826fb0 (skills/scripts/evals identical to HEAD): orient ranks #1 for all four in-session next-step prompts ('ok, what's next?' 0.13, 'what's the next step in the plan?' 0.19, 'done with that task — what's next?' 0.13, 'what should I pick up next?' 0.16); every other skill 0.00 except contracts 0.07 on one.
- Note (2026-11-10, after the fix): the entry above counts "what should I
  pick up next?" among the reproducing prompts. It was later moved out of the
  lexical regression set as a "what's next" variant handled by the body's
  scope check (see `## Repro`). The other three bare next-step prompts plus
  "next task?" form the regression set.

## Reopen log

- 2026-11-10: reopened before commit. The first fix reached `DONE` in the
  working tree only (never committed or pushed). The owner then redesigned the
  behaviour after talking with a user (see `## Owner decision`). `bug.py` has
  no `DONE` back-edge, so `status:` was hand-reset `DONE → REVIEWED` (the
  state the helper had last written before `DONE`), then the helper's
  `REVIEWED → FIXING` review back-edge was taken, which stamps
  `review_reopened_at` and invalidates the earlier verdicts. The missing
  `DONE` back-edge (for a reopen before commit) is a gap in `bug.py`; if it
  recurs, it is a refinement-todo candidate.
- 2026-11-10: second owner revision (short answer first, then offer the full
  orientation) arrived while the ask-first design's review passes were
  running. Those passes were stopped before recording any verdict; the record
  stayed in `FIXING`, so no further state change was needed.
