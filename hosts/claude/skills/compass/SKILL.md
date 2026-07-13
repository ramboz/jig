---
name: compass
description: >-
  Answer "what's next" / "where do things stand" for a code project run with
  jig/servo/shaper, in one fixed, readable shape. Use whenever the user invokes
  /compass, or asks "what's next", "what's the status", "what should I do next",
  "where are we", "what's outstanding", "what's blocked", "what should I work on",
  or wants a grounded menu of pickable work for a spec-driven code repo. Surveys the
  project's own artifacts — spec status boards and slice STATUS markers, ADRs in
  docs/decisions/, DEFERRED slices and their triggers, servo's refinement-todo,
  shaper's release plans, the inbox, and any standalone bugs — then renders a briefing
  with an honest headline, titled sections, one recommendation, and an offer to start.
  Read-only with respect to project work: it never transitions lifecycle state, edits
  specs, or accepts ADRs. Its ONE write is an append-only run log — after each briefing
  it appends a single JSON line to docs/status/compass-history.jsonl (timestamp, headline,
  recommendation, blockers, open counts) so runs become trackable data points over time.
  Hands off to jig/servo/shaper skills to actually do the work. Assumes a spec-driven code
  project; if none is found, say so and point at the right setup skill. For non-code studio
  projects, defer to studio:project-desk instead.
---

# Compass

**One job: tell the user what to do next, in a shape they can actually read.**

The user comes back to a project after time away and asks the calm manager's question —
*"what's next?"* Compass answers it by reading the project's own truth (not guessing),
and presenting it in **one fixed, scannable layout**: a headline that tells the honest
state, then a short stack of **titled sections**, each a list of **titled bullets** —
never a wall of inline prose with items buried mid-sentence.

The substance is grounded; the **format is the point**. If the answer reads like a
paragraph with five things crammed into it, the skill has failed even if every fact is
right.

---

## The prime directive — formatting

These rules are non-negotiable. They are the reason this skill exists.

- **Every distinct item is its own bullet, led by a short bold title.**
  `- **Recents (002-07)** — the last fork of the quick-add split; needs a Home-row mockup first.`
  Never `favourites are done and recipes are done but recents still needs a design and also backup restore is parked and…`
- **Group bullets under `##` / `###` section headers.** The reader should be able to
  jump to "the deferred stuff" or "the one decision" by scanning headers alone.
- **No inline lists.** If you catch yourself writing "X, plus Y, and also Z" where X/Y/Z
  are separate pieces of work, stop and turn them into three bullets.
- **One line per item where possible.** Title — what it is — the blocker or trigger.
  Keep each bullet to roughly one sentence; detail goes in a sub-bullet only if it earns it.
- **Lead with the answer.** The headline and the obvious next step come first, before any
  exhaustive lists.
- **Omit empty sections.** Only render a section if it has real content. A project with no
  pending ADR simply has no "one decision" section — don't print an empty heading.

If you honor nothing else here, honor this section.

---

## What it reads (the survey)

Compass is **read-only reconnaissance**. Before answering, scan the project for its
truth. Projects vary — look for these, use what exists, don't assume exact paths:

- **Spec status** — `docs/specs/<MNN-slug>/` slice files (and any `STATUS.md` /
  status-board). Read each slice's STATUS marker: `DRAFT`, `READY_FOR_REVIEW`,
  `READY_FOR_IMPLEMENTATION`, `IN_PROGRESS`, `REVIEWED`, `RECONCILED`, `DONE`,
  `DEFERRED`. This is the spine of "what's shipped vs. open."
- **DEFERRED slices + their triggers** — a DEFERRED slice carries a *resolution trigger*
  ("revisit once X"). Check whether that trigger is now met — a met trigger is often the
  best "obvious next step."
- **ADRs** — `docs/decisions/adr-*.md`. Note any with `Status: Proposed` (awaiting the
  user's acceptance) — a pending ADR is usually "the one decision blocking the most."
  Accepted/Superseded ones are context, not action.
- **Refinement / deferred decisions** — servo's `.servo/refinement-todo.md` (or a
  `refinement-todo.md`), and jig's `docs/inbox.md`. These hold parked owner-decisions and
  polish follow-ups.
- **Release plans** — shaper's `docs/releases/*.md` and `docs/releases/README.md`. Tells
  you what's in-scope for the next release vs. deferred, and whether a milestone is at risk.
- **Recent work** — the last few commits and any IN_PROGRESS slice, to say honestly
  what just landed (and flag when the board may be stale vs. a very recent commit).
- **Standalone issues** — real bugs or gaps noted in docs/comments that don't need spec
  ceremony but are worth surfacing (a mislabeled pack, a failing threshold, dead config).

If tests or a green-count are cheaply visible (a recent run, an oracle summary), cite the
number in the headline as a proof point — but **don't run long suites** just to decorate
the answer.

If there's **no spec-driven project here** (no `docs/specs/`, no jig/servo/shaper
artifacts), don't invent a status. Say plainly that nothing spec-driven was found, and
point at the right setup skill (`jig:scaffold-init` for a new code workflow), or — if this
looks like a non-code project — hand to **studio:project-desk**.

---

## The output shape (the fixed layout)

Render these sections **in this order**, including only the ones with content. Not every
project has every section — a freshly-shipped MVP may have only a headline, an obvious
next step, deferred bets, and a recommendation.

### 1. Headline — the honest state (always)

One to three sentences. What's the overall state? Is there **required** work outstanding,
or is "what's next" a **prioritization call** among optional items? Be honest about both
"we're further than you think" and "this is quietly slipping." Cite a proof point if one
is cheap (e.g. "252 tests green").

> *The MVP is fully shipped — slices 002-01 through 002-06 are DONE, plus 002-08 and 002-09
> just landed (252 tests green). There's no required work outstanding; "what's next" is a
> prioritization call among deferred items.*

### 2. The obvious next step (usually)

The single (occasionally two) most natural next thing. A titled bullet with: what it is,
why it follows now, and any dependency/blocker. This is your lead recommendation candidate.

### 3. The one decision blocking the most (when one exists)

If a `Proposed` ADR or a parked owner-decision unblocks more than anything else, surface it
here, prominently, **before** the long lists. Say what it is, that it's awaiting *their*
call, and **what deciding it unblocks**. Only include this section when such a decision
genuinely exists.

### 4. Larger deferred bets / packs (when they exist)

The bigger parked items that need a **trigger or a decision** before they're actionable.
One titled bullet each: title — one-line what — the trigger or what's blocking it. Group
tightly; this is a menu, not an essay.

### 5. The DRAFT queue / ready to build (when specs are DRAFT)

Specs or slices sitting in DRAFT/READY awaiting a go-ahead. One bullet each with the spec
id and a one-line scope. Note if any is beta/release-blocking, and flag any board row that
looks stale against a very recent commit.

### 6. Polish follow-ups (when they exist)

The small, satisfying parked items — extractions, autocompletes, test-depth, a deferred
AC. Terse bullets; these are the "if you have an hour" pile.

### 7. Standalone fixes — no spec ceremony (when they exist)

Real bugs or contained correctness issues worth doing without a spec. One bullet each:
the symptom, and the contained root-cause/fix if known.

### 8. My recommendation (always)

**One** clear pick, with a two-to-three-sentence why. Name the single dependency or first
decision it needs. Don't re-list the menu — commit to a direction.

### 9. The offer (always)

End with a concrete either/or that hands off to the real work:
> *Want me to draft the 002-07 spec slice, or would you rather tackle backup restore — the
> most user-facing of the deferred bets?*

---

## Logging the run — the one write

Compass is read-only about **project work**, but it keeps a memory of **itself**. After
you have rendered the briefing in chat, append exactly **one JSON line** to the project's
run log so each run becomes a trackable data point (morning + evening runs draw a
progress-over-time curve; a dashboard can read this file directly).

- **File:** `docs/status/compass-history.jsonl` — one JSON object per line, **append-only**.
  Create `docs/status/` if it doesn't exist. **Never** rewrite, reorder, or truncate the
  file; only append. If the append fails, say so in one line — don't retry destructively.
- **Timestamp:** get a real one, don't guess — `date -u +%Y-%m-%dT%H:%M:%SZ`.
- **Schema** (stable — keep these keys so the dashboard can rely on them):

  | key | value |
  | --- | --- |
  | `ts` | ISO-8601 UTC timestamp of the run |
  | `project` | the repo/dir basename |
  | `headline` | the one-line honest state you led with |
  | `recommendation` | the single next action you recommended |
  | `blockers` | array of short strings — the decisions/triggers blocking progress (`[]` if none) |
  | `counts` | small object of open-item tallies for trend lines, e.g. `{"deferred":4,"draft":6,"polish":3,"bugs":2}` |

- **Robust append** (quoting-safe — build the object with `jq`, don't hand-concatenate JSON):

  ```bash
  mkdir -p docs/status
  jq -c -n \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg project "$(basename "$PWD")" \
    --arg headline "MVP shipped; what's next is a prioritization call" \
    --arg rec "Start 002-07 recents" \
    --argjson blockers '["ADR-0012 awaiting acceptance"]' \
    --argjson counts '{"deferred":4,"draft":6,"polish":3,"bugs":2}' \
    '{ts:$ts, project:$project, headline:$headline, recommendation:$rec, blockers:$blockers, counts:$counts}' \
    >> docs/status/compass-history.jsonl
  ```

- **Mention it in one line** at the end of the chat briefing (e.g. *"Logged to
  docs/status/compass-history.jsonl — run #7."*), so the write is never silent.

This is the **only** thing Compass writes. It touches nothing under `docs/specs/`,
`docs/decisions/`, or any source file.

## Handoff — Compass points, it doesn't do

Compass is a **map, not the journey**. It never transitions a slice, edits a spec, accepts
an ADR, or writes a file. When the user picks a direction, hand off cleanly to the skill
that owns that work:

- Start / split / transition a spec → **jig:spec-workflow**
- Implement a ready slice → **jig:implementer** (or servo's loop for unattended runs)
- Accept / write the blocking decision → **jig:adr-workflow**
- Fix a standalone bug → **jig:bug-fix**
- Re-shape release scope → **shaper:shape-release** / **shaper:cutline**

Name the handoff in the offer; let the user green-light it.

---

## Judgment

- **Format over completeness.** A readable briefing of the top ~8 items beats an exhaustive
  unreadable dump. If the list is long, group and cap it — and *say* you capped it ("plus 6
  smaller items in the inbox") rather than silently truncating.
- **Grounded, never guessed.** Every item traces to something you actually read. If you're
  unsure whether a trigger is met or a board is stale, say so ("b08a627 just landed 036-05,
  so this row may be stale") rather than asserting.
- **Honest headline.** Surface slippage and shipped-more-than-expected with equal candor.
  Don't cheerlead; don't doom.
- **One recommendation, not a shrug.** The user came for direction. Pick one, say why, and
  offer to start it — keep the rest available if they ask.
- **Stay read-only about the work.** The moment the user says "do it," hand off. Compass's
  honesty depends on it never being the thing that changes *project* state — specs, ADRs,
  lifecycle. The append-only run log (`docs/status/compass-history.jsonl`) is the sole
  exception: it records what Compass said, never what the project is.
- **Adapt the sections to the project.** The order is fixed; the *presence* of each section
  is not. Show only what's real.
