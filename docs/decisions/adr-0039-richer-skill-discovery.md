---
status: Accepted
dependencies: []
last_verified: 2026-07-27
frame_review: true
---

# ADR-0039: Host-portable richer-skill discovery for extensible review passes

## Status

Accepted (2026-07-27)

## Context

jig ships **shallow baselines** for several review/judgment skills and is meant
to **defer to a richer skill the user has installed** when one is present. Two
different mechanisms implement that deferral today, and both are narrower than
the product vision promises ([product-vision.md](../product-vision.md) §"the
deferral pattern is per-skill", lines ~177–187: a richer skill self-identifies
via its **description**, and jig yields to it).

**Mechanism 1 — file-read dispatch for the read-only review passes** (spec
[053](../specs/053-craft-pass-skill-dispatch/spec.md)). The post-implementation
**craft** (`pr-review`) and **arch** (`arch-review`) passes run in a read-only
`reviewer` subagent (`agents/reviewer.md`, tools: Read/Glob/Grep) with **no
`Skill` tool**, so it cannot reach Claude's skill router. Spec 053 resolved this
by having `review.py detect_richer_skill(name)` look for a skill on disk and
handing the reviewer that concrete path to *read-and-apply*. But it resolves by
**exact folder name at a single scope**: `~/.claude/skills/<name>/SKILL.md`.

**Mechanism 2 — interactive router deferral** for the skills the orchestrator
invokes directly (`security-review`, `code-health`'s interactive path,
`vision-elicitation`, `contracts`, `explain`, `orient`, `reframe`). These carry
a "defers to any other installed skill whose description identifies it as
handling X" hint in their description; Claude's **skill router** matches on that
description and prefers the richer skill.

**The reported failure.** A colleague installed a richer PR-review skill at
**user scope under a different name** (`review-pr-deep`). The workflow craft pass
silently used jig's baseline. Root cause: `detect_richer_skill("pr-review")`
keys on the literal folder name `pr-review`, so a skill that *is* a PR-review
skill but is not *named* `pr-review` is invisible to it.

A review of **all** jig skills against this failure exposed three couplings and
one boundary that this ADR exists to settle:

1. **Name-coupling.** Mechanism 1 resolves by folder name, not by what the skill
   *is*. The vision always intended **description/category**-based pickup — the
   same signal Mechanism 2's router already uses.
2. **Scope-coupling.** Mechanism 1 checks **user scope only** (project- and
   plugin-scope deferred in spec 053, since a scaffolded baseline copy is
   indistinguishable *by path* from a genuinely richer project skill).
3. **Host-coupling.** Mechanism 2 depends on the **Claude Code skill router**,
   which does not exist on the **Codex** host (ADR-[0018](./adr-0018-dual-host-generated-plugin-artifacts.md),
   dual-host generated artifacts). So every router-only deferral —
   `security-review`, `vision-elicitation`, and the interactive judgment skills —
   is **inert on Codex**. This is the asymmetry the user flagged as the real
   concern: depth pickup must work on **both** hosts.
4. **The defer / never-defer boundary.** Extending *quality/domain-judgment*
   review with a richer skill is desirable; extending the **strict
   spec-compliance pass** (`independent-review`) or jig's **methodology gates**
   (`frame-critique`, the bug-fix diagnose + red→green teeth) is not — their
   value *is* being jig-canonical. The mechanism must serve the first set and
   structurally exclude the second.

Two governing constraints frame every option:

- **jig stays generic and shallow by default.** Depth arrives only through a
  user's richer skill via this override mechanism — never by jig's baselines
  themselves growing domain-specific depth. (Note: jig's baseline
  `security-review` today carries scanner-specific orchestration per
  ADR-[0013](./adr-0013-security-floor-policy.md); whether that floor is "too
  deep" for a shallow default is a **separate** decision — see Open questions
  OQ3 — not resolved here.)
- **Determinism is load-bearing.** `transition` gates REVIEWED/DONE on a
  recorded `verdict: pass` artifact (ADR-[0014](./adr-0014-review-evidence-model.md)).
  Whatever resolves the richer skill must be deterministic and observable so the
  verdict envelope stays trustworthy.

## Decision Options Considered

### Option A: Keep spec 053's per-skill exact-name file-read lookup
- **Pros:** Already shipped; deterministic; read-only; host-portable (pure
  filesystem). No router dependency.
- **Cons:** Is the reported bug. Name-coupled (misses `review-pr-deep`),
  scope-coupled (user-scope only), and covers only `pr-review`/`arch-review`.
  Does nothing for the router-only skills' Codex gap.

### Option B: Grant the review subagent a `Skill` tool and use the router
- **Pros:** "Auto pickup" for free on Claude via the router's description match;
  no new discovery code.
- **Cons:** **Claude-only** — the Codex reviewer is a read-only TOML agent with
  no router, so this deepens the host asymmetry instead of fixing it.
  **Non-deterministic** — router matching is probabilistic, breaking the
  ADR-0014 verdict gate's observability. **Destroys read-only independence** —
  a richer PR/security skill assumes `gh`/Bash/WebFetch; loaded in the reviewer
  it either can't run its own procedure or forces us to grant the tools that
  make the reviewer no longer independent. This is the alternative spec 053
  already rejected; it fails harder once "both hosts" is a requirement.

### Option C: Host-portable, category-based richer-skill discovery service (partially adopted — enumeration only)
A single deterministic discovery helper, consumed by every **extensible review
pass**, that:
- **enumerates installed skills across all scopes** on the *active host* (Claude:
  `~/.claude/skills`, project `.claude/skills`, plugin dirs; Codex: the
  equivalent surface — see OQ1), reading each skill's `name` + `description`
  frontmatter;
- **matches by review category, not folder name** — the same description signal
  the router uses, evaluated deterministically in Python (so `review-pr-deep`
  resolves for the `pr-review` category);
- **excludes jig's own baselines** via an explicit marker (a `jig_baseline: true`
  frontmatter field, or a scaffold-manifest record — OQ4), so a scaffolded copy
  never masquerades as "richer";
- **picks deterministically** — most-specific scope wins (project > user >
  plugin), then lexical tiebreak;
- hands the read-only reviewer the winning **concrete path** to *read-and-apply*
  (Mechanism 1's proven file-read dispatch is retained; only *resolution*
  changes).
- **Pros:** Fixes the reported bug by construction. **Host-portable** — pure
  filesystem + frontmatter, no router, so it backs both Claude and Codex and
  closes the asymmetry. Deterministic and observable (preserves the ADR-0014
  gate). One service for all review passes. Keeps the reviewer read-only and
  independent. Category-matching honors the vision's original intent.
- **Cons:** Needs a robust category signal + a reliable baseline-exclusion marker
  or it false-positives (the exact risk that made spec 053 defer project-scope).
  Codex's enumeration surface is currently **unknown** (a spike gates the "both
  hosts" promise). More surface to test; a new frontmatter marker to maintain
  across baselines and migrate onto already-scaffolded repos.

### Option D: Orchestrator resolves the skill; the reviewer is handed the path (recommended)
The read-only reviewer never resolves anything. The **orchestrator** — which
already carries every installed skill's `name` + `description` in its context —
selects the right richer skill for the category, and passes the resolved
identity down into `review.py`, which converts name → concrete path and builds
the reviewer's read-and-apply prompt.

Note there is **no router "query" API** to call: the `Skill` tool only invokes,
and routing is not a separate service. Routing *is* the model selecting over the
skill descriptions in its context — so the orchestrator does not ask, it simply
decides and reports. Python keeps the deterministic jobs (enumerate candidates,
exclude jig baselines, resolve name → path, verify the file exists); the model
keeps the judgment job (which of these is actually a PR reviewer).

- **Pros:** Two reasons, neither of which is "pattern matching cannot
  classify" — the spike disproved that claim (see the honesty note below).
  **(1) Generalization over a hand-tuned matcher.** The strict trigger-intent
  matcher that succeeded in the spike was authored *after* observing the
  `morning-github` failure and validated on the same 26-skill corpus — it is
  **overfit by construction**. Its precision on skill descriptions neither
  author nor spike has seen is unknown, and each new miss requires a regex
  edit shipped in a jig release. A model classifies unseen descriptions without
  a rule update. **(2) Multiplicity beats refusal.** A deterministic matcher
  that refuses to rank genuine candidates yields jig's baseline on exactly the
  machines with the most depth installed — a perverse "more skills installed →
  less depth applied" outcome. Selecting a top candidate is not provably
  correct (see Cons), but it is strictly more useful than refusing, and config
  (rule 1) remains the override when the user disagrees.
  Also: keeps the reviewer read-only and independent (it only reads a path it
  was handed), and costs ~nothing in orchestrator context (spec 057) since the
  descriptions are already loaded.

  > **Honesty note (frame-critique, 2026-07-27).** An earlier revision justified
  > this option by claiming pattern matching is "the wrong instrument," citing
  > the spike's *naive*-matcher failure. That was an overreach: the same spike
  > recorded that a **stricter** matcher correctly rejected `morning-github` and
  > kept all three genuine candidates. Deterministic matching **can** classify.
  > The claim has been withdrawn and replaced by the two reasons above.
- **Cons:** Reintroduces **non-determinism** into resolution — the pick may vary
  between runs, which is exactly what the ADR-0014 verdict gate dislikes
  (mitigated by recording the choice; see below). It is **orchestrator-prose
  behavior**, the same class spec 031's option (a) shipped and spec 053 found
  inert — so it must be backed by a required argument plus a recorded outcome,
  not a prose nudge. Depends on the host surfacing skill descriptions to the
  orchestrator (verified on Claude; second-hand on Codex — see Assumptions).
  **The selecting orchestrator is the agent whose work is being graded**,
  choosing its own grader under a standing spec-057 incentive toward the
  cheaper rubric — an inversion of the independence posture `agents/reviewer.md`
  exists to protect (structural mitigations below).
  **Ranking genuine candidates is not derivable from descriptions.** Which of
  several real PR-review skills a user wants is private preference, absent from
  the metadata; the model is making a *useful heuristic guess*, not a correct
  determination. Accepted deliberately (see Recommended Decision §3 rule 2a),
  with config as the override and the choice always recorded.

### Option E: Config-only — `scaffold.json` names the skill; no discovery at all
No enumeration, no marker, no `--richer-skill`, no model selection. A
`review.<category>_skill` entry names the richer skill; absent it, jig's
baseline runs.

- **Pros:** Fully closes the reported bug (`review-pr-deep` silently baselined)
  with **one config line**, deterministically, on **both hosts**, with no OQ6
  dependency and no Codex spike. Reproducible in CI. No independence inversion —
  nothing judges anything. It is, by this ADR's own admission (Recommended
  Decision §3), the *only* path that actually **guarantees** deferral. Cheapest
  to build and to reason about by a wide margin.
- **Cons:** Abandons zero-config pickup — the property
  [product-vision.md](../product-vision.md) §"the deferral pattern is per-skill"
  asserts, and the reason Options A–D exist. Every user of every richer skill
  must configure each project, and a user who does not know the mechanism exists
  gets the baseline forever with no prompt to do otherwise. Discoverability of
  the feature drops to whatever the docs achieve.

**Why not adopted outright:** zero-config pickup is a stated product property,
not an accident, and dropping it silently would be a vision change made by
omission. **But its cheapness and its guarantee are why it is now sequenced
first** — see Recommended Decision §6.

> **Note on the vision axiom.** Options A–E all inherit
> `product-vision.md:180` ("a richer user-installed skill … wins **without
> configuration**") as the goal. This ADR's own evidence *partially falsifies*
> that axiom: ranking genuine candidates is not derivable from descriptions by
> any selector (Assumptions), so for any category with >1 installed candidate
> "wins without configuration" is unachievable in principle — the best any
> option can do is a labelled heuristic. The axiom holds for the
> single-candidate case and degrades to a guess beyond it. It is **not**
> re-opened here, but it is no longer treated as unconditionally true.

## Recommended Decision

Adopt **Option D**, retaining Option C's enumeration layer beneath it (C's
discovery machinery is kept; only its *picking* role is withdrawn). Concretely:

1. **The extensible set** (these review passes discover-and-defer to a richer
   installed skill): `pr-review`, `arch-review`, `security-review`,
   `code-health`, `design-review`. The bug-fix workflow's craft + security
   passes reuse `pr-review`/`security-review` and inherit the behavior.
2. **The never-defer set** (stay jig-canonical, no discovery): the strict
   spec-compliance pass `independent-review`, the `frame-critique` pass, the
   bug-fix diagnose + red→green rigor gates, and all process/orchestration
   skills (`spec-workflow`, `bug-fix` orchestration, `adr-workflow`, `clarify`,
   `analyze`, `memory-sync`, `migrate`, `scaffold-init`, `slice-land`,
   `tdd-loop`).
3. **Resolution is host-portable and multi-scope**, with this **precedence
   chain** (OQ2 + OQ6, resolved 2026-07-27):

   1. **`scaffold.json` config wins, always.** An explicit
      `review.<category>_skill` entry (skill name or path) is authoritative and
      ends resolution — no enumeration, no model judgment. The deterministic
      escape hatch, and reproducible in CI.
   2. **Otherwise the orchestrator selects the single best candidate**, and
      passes the chosen skill name to `review.py` as an **explicit required
      argument** (`--richer-skill <name|none>`). It must be a *required* value,
      not a prose instruction: omission is a visible error, never a silent
      fallback. This is the lesson of spec 031's option (a), which was prose the
      runtime could ignore.

      2a. **Multiple genuine candidates → still pick one; do not refuse.**
      Refusing to rank would hand jig's baseline to precisely the users with the
      most depth installed. The selection is an explicit heuristic, not a
      correctness claim: it is always recorded (below), always overridable by
      rule 1, and the alternatives are always listed alongside it so a user can
      see what was not chosen.
   3. **Python enumerates candidates** — deterministic, host-portable, cheap —
      to inform the selection and to validate it. Enumeration carries **recall,
      not precision**: it may over-offer, because a model, not a regex, does the
      choosing. Naive substring matching is explicitly rejected *as a picker*
      (spike evidence), but is acceptable as a candidate-nominator.
   4. **The selection is validated deterministically.** `review.py` resolves the
      supplied name → concrete path across scopes, confirms the file exists, and
      confirms it is **not** a jig baseline. An unresolvable or baseline-marked
      name falls back to jig's baseline rather than erroring the pass.
   5. **Only when no candidate is selected → jig's bundled baseline**, plus a
      surfaced note listing any candidates that existed. Ambiguity is *not* a
      fallback trigger (rule 2a picks); the baseline is reached when the
      orchestrator selected `none`, when nothing was installed, or when
      validation (rule 4) rejected the pick.

   **Both the chosen skill (or `none`) AND the enumerated candidate set are
   recorded in the review evidence artifact.** Recording the choice alone is
   insufficient: it cannot distinguish "no richer skill was installed" from
   "three were installed and none was applied." The candidate set is what makes
   that distinction visible.

   **The unapplied-candidates anomaly is recorded and surfaced, but does NOT
   block.** A baseline fallback while enumeration found ≥1 non-baseline
   candidate is written to the evidence artifact as a distinguishable state, so
   a baseline-derived `verdict: pass` with unapplied candidates is separable
   from a clean baseline pass on a machine with nothing installed.

   **It is deliberately not a gate.** ADR-0014 §3 fixes the evidence gate as a
   uniform one-line predicate on `verdict:` alone; making this anomaly blocking
   would silently amend that rule and would refuse REVIEWED to a user who
   legitimately does not want an installed skill applied. This ADR therefore
   claims **auditability, not enforcement** — an earlier revision called the
   anomaly a "structural guarantee," which overstated it, since a non-blocking
   record cannot guarantee anything. Withdrawn.

   **Named consumer (required, or the record is inert).** `check-reviews` reads
   the anomaly and warns; `workflow.py status-board` aggregates a count. Without
   at least one committed consumer the record is spec 031's inert prose in YAML,
   and the kill criterion below becomes undetectable by construction. Which
   additional surfaces carry it (a `jig hint:`, an `orient` line) stays an
   implementation choice.

   **The anomaly must be calibrated, or it measures its own noise.** The
   nominator is recall-only and deliberately over-offers, so a naive definition
   ("baseline fallback while ≥1 candidate was nominated") fires on nomination
   noise — on the probed corpus, a legitimate `none` would trip it because
   `morning-github` was nominated. Two requirements follow:
   - Fire the anomaly only against the candidate set the orchestrator was
     **actually shown and declined**, and record that set — not the raw
     nomination list.
   - **Matcher precision therefore still matters**, contrary to an earlier
     revision's claim that only recall does: precision governs the
     false-positive rate of this ADR's only observability surface, even though
     it no longer governs the pick.

   **Known blind spot — the anomaly cannot see a recall failure.** If
   enumeration nominates nothing, the orchestrator selects `none`, no anomaly
   fires, and the originating `review-pr-deep` failure recurs *silently* — the
   exact discovery path this ADR exists to remove. Nothing in the design detects
   this; it is visible only when a human notices their skill was not applied.
   This is a **real, accepted gap**, not a solved problem, and it is the
   strongest standing argument for precedence rule 1 (config), which is immune
   to it. Slice 1's config-first sequencing (§6) is the mitigation.

   This matters because **every fallback path in rules 2–5 converges on jig's
   baseline — precisely the reported bug's terminal state.** A required
   `--richer-skill` argument enforces *arity*, not *correctness*:
   `--richer-skill none` satisfies it and reproduces the original failure
   byte-for-byte. So the honest answer to *"how can I guarantee the deferral
   works?"* (spec 053 References) is: **you cannot guarantee it; you can only
   make its absence visible.** Rule 1 (config) is the only path that *does*
   guarantee it, which is why it sits at the top of the chain.

   Two forces make the `none` path actively attractive and must be designed
   against, not assumed away: the selecting orchestrator is the same agent that
   produced and supervised the work being graded (inverting the independence
   posture `agents/reviewer.md` exists to protect), and it carries a standing
   spec-057 cost incentive to choose the cheaper rubric.

   jig's own baselines are excluded from candidacy by an explicit
   **`jig_baseline: true` frontmatter marker** (OQ4, resolved 2026-07-27) added
   to every shipped baseline skill. No migration path is provided for
   already-scaffolded projects: machinery-scaffolded projects are not yet
   expected to exist in the field. Discovery treats a *missing* marker on a
   jig-shipped baseline as a packaging bug, not as evidence of richness.
3a. **Recorded override of a review finding (2026-07-27).** The second
   frame-critique returned `needs-changes` arguing Option D should be dropped
   for Option C's stricter deterministic matcher, on the grounds that the spike
   *measured* the matcher working while the model's advantage is only asserted.
   That argument is correct on its own terms and is preserved above (Option D
   Cons; the Option D honesty note). It was **deliberately overridden by the
   project owner** on the reasoning that a hand-tuned matcher validated against
   the corpus that produced it is overfit, and will fail on unseen skill
   descriptions in a way that requires a jig release to repair — whereas
   misjudgment by the model is recoverable in-session via rule 1. The residual
   risk is accepted and is exactly what the first kill criterion watches.
   Recorded so a future session sees a weighed trade, not an unnoticed finding.
4. **This supersedes spec 053's exact-name / user-scope-only resolution.** The
   file-read *dispatch* into the read-only reviewer is retained; only the
   *lookup* that feeds it generalizes. Spec 053's rejection of "grant the
   reviewer a `Skill` tool" (Option B here) is reaffirmed and strengthened.
5. **The interactive judgment skills** (`contracts`, `explain`, `orient`,
   `reframe`, `vision-elicitation`) adopt the same portable discovery helper in
   a **follow-up slice** to gain Codex parity — lower priority than the read-only
   review passes, since they already work on Claude via the router.
6. **Sequencing — guaranteed layer first.**

   **Slice 1 ships precedence rule 1 alone (Option E's mechanism):**
   `review.<category>_skill` in scaffold.json, honored by all five extensible
   passes, on both hosts. This **fully closes the reported bug**
   deterministically, with no marker, no enumeration, no `--richer-skill`, and
   no OQ6 dependency. It is the layer the ADR can actually guarantee, and the
   destination every kill criterion falls back to — so it should exist *before*
   the layers that fall back to it, not after.

   **Slice 2+ adds the zero-config layer** (enumeration, `jig_baseline:` marker,
   orchestrator selection, anomaly recording) on top of a working floor. This
   ordering means a kill criterion firing degrades to a *shipped, working*
   config path rather than unwinding a half-built one — and it lets real usage
   inform whether users configure or need the automatic layer, instead of
   assuming.

   **Codex spike (OQ6) gates only the slice-2 orchestrator-selection path**, not
   slice 1. The 2026-07-27 spike cleared **OQ1** (filesystem enumerability) —
   Option **C**'s premise, not Option D's. Option D rests on OQ6, which is
   second-hand for Codex and unprobed; Claude needs no spike (directly
   observed).

## Consequences

**Becomes easier:**
- A richer skill is picked up by **what it is** (its description), regardless of
  folder name — the reported failure cannot recur.
- Depth pickup works on **Claude** for the review passes with no router
  dependency. **On Codex it is contingent on OQ6** (see Assumptions): the
  filesystem layer is verified, but orchestrator skill-visibility is not. If
  OQ6 fails on Codex, zero-config pickup there is **structurally impossible**,
  not merely degraded — Option D withdrew Option C's picking role, so config +
  enumeration leaves no picker at all. Codex would then be config-only. This is
  still strictly better than today's fully-inert Codex deferral, but it is not
  the same guarantee as Claude's, and must not be described as one.
- One discovery service backs every extensible review pass, and later the
  interactive skills — no more per-skill, per-scope special cases.
- Closes the **description-vs-behavior gaps**: `code-health` and `design-review`
  advertise (or should advertise) deferral their subagent passes don't honor
  today; both now honor it.

- **Selection precision stops being a pattern-matching problem.** The layer that
  decides "is this actually a PR reviewer?" is a model reading descriptions, not
  a regex — the spike's `morning-github` misclassification cannot recur.

**Becomes harder:**
- **Resolution is no longer reproducible.** The orchestrator's pick may vary
  between runs, so "which rubric produced this verdict?" is answerable only
  because the choice is *recorded* in the evidence artifact. Auditability
  replaces determinism as the property that keeps the ADR-0014 gate meaningful —
  a deliberate trade, and the one most likely to be regretted if recording is
  ever skipped.
- **A required argument must stay required.** The moment `--richer-skill`
  acquires a silent default, this degrades into spec 031's inert prose. The
  argument's mandatoriness is load-bearing, not ergonomic.
- Discovery must still exclude jig's own baselines reliably, or a scaffolded
  repo offers jig's baseline back to itself as "richer" — the risk that made
  spec 053 conservative. The marker must be right.
- A **new frontmatter marker** to maintain across all shipped baselines, and to
  regenerate through the host-package build. (No migration for existing
  scaffolds — see Recommended Decision §3 / OQ4.)
- More test surface (multi-scope, multi-host, ambiguity/tiebreak, marker
  present/absent).
- The "both hosts" guarantee is **contingent on the Codex spike**; until it
  lands, portability is a design intent, not a shipped fact.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **VERIFIED (OQ1 spike, 2026-07-27):** the Codex host exposes an enumerable
  user-installable-skill surface. Codex documents **three** scopes — user
  `$HOME/.agents/skills`, repo `.agents/skills`, admin `/etc/codex/skills` —
  plus plugins as the distribution unit (spec 059-04 implementation notes,
  re-checked against the official Codex manual). Probed live on a machine
  running `codex-cli 0.133.0`: `$HOME/.agents/skills` present with 4 installed
  skills, each a `SKILL.md` with YAML frontmatter **identical in shape** to
  Claude's (`name` + `description`). One Python parser covers both hosts; no
  router needed. The "works across both hosts" premise is **sound**.
- **VERIFIED (OQ1 spike, 2026-07-27) — with a material caveat:** description
  frontmatter carries enough signal to classify by category, but **naive
  substring matching does not reach acceptable precision.** Probed against the
  real 26-skill corpus on this machine: naive matching flagged `morning-github`
  as a `pr-review` skill (its description says it stages *"draft PR reviews"* —
  it is a briefing skill, not a reviewer), and a naive lexical tiebreak
  **elevated that false positive to category winner** over the genuine
  `pr-review` and `scout-pr-review`. A stricter *trigger-intent* matcher
  (does the description declare reviewing as the skill's **purpose**, with
  negative signals for skills that merely produce/stage review artifacts)
  correctly rejected it and kept all three genuine candidates. See the
  Recommended Decision's precision rules.
- **OBSERVED on n=1 (OQ1 spike, 2026-07-27) — not established as typical:**
  multiple legitimate candidates per category can coexist. Three `pr-review`
  candidates were present on the single machine probed (`pr-review` +
  `scout-pr-review` on Claude, `scout-pr-review` on Codex). One well-equipped
  developer machine is **not** evidence that ambiguity is the population norm;
  an earlier revision asserted it was, and that is withdrawn. The design must
  merely *handle* multiplicity, not assume its frequency.
  Separately and independently of frequency: **ranking genuine candidates is
  not derivable from descriptions at all** — it is private user preference. No
  selector, deterministic or model, can extract it, which is why config
  precedence (OQ2) is load-bearing and why rule 2a's pick is labelled a
  heuristic rather than a determination.
- **Confirmed for user scope, assumed for others:** the read-only reviewer can
  `Read` a resolved SKILL.md path — spec 053's live probe confirmed it for
  `~/.claude`; project- and plugin-scope paths are assumed equivalent (cheap to
  verify during implementation).
- **SECOND-HAND (not independently verified) — the Option D host premise:** both
  hosts surface installed skill `name` + `description` into the orchestrator's
  context, which is what lets the orchestrator select a skill at all.
  *Claude:* directly observed — the skill listing with descriptions is present
  in the orchestrating session's context. *Codex:* per OpenAI documentation as
  relayed by the user (2026-07-27, via ChatGPT): a skill's `name`/`description`
  are read from `SKILL.md` into the hidden system-prompt context and are the
  primary signals Codex uses to decide whether to invoke a skill. **Attempted
  local verification failed to confirm or refute** — `codex-cli 0.133.0` exposes
  no `skills` subcommand, so the claim could not be checked from the CLI. It is
  consistent with the directly-verified fact that Codex skills carry the same
  `name`/`description` frontmatter, but it remains a relayed claim. If it proves
  false on Codex, Option D degrades there to config + enumeration (precedence
  rules 1, 3–5) — still strictly better than today's fully-inert Codex
  deferral, so the decision does not hinge on it.

## Kill criteria

- ~~**Codex has no user-installable-skill concept.**~~ **RETIRED 2026-07-27** —
  the OQ1 spike confirmed three documented Codex scopes and a frontmatter format
  identical to Claude's, probed live against `codex-cli 0.133.0`. The
  portability premise held; this criterion can no longer fire.
- **Silent NON-selection persists** *(re-aimed at Option D's dominant failure
  mode — the pre-D criteria pointed at Option C's picker, which D withdrew)*.
  If, after implementation, sessions routinely produce baseline craft verdicts
  while non-baseline candidates sit unapplied — i.e. the anomaly state fires
  often and nobody acts on it — then orchestrator selection has failed as a
  mechanism. Response: drop model selection entirely and go **config-only**
  (precedence rule 1), which needs none of the enumeration or `--richer-skill`
  machinery. **This is the criterion most likely to fire**, and the cheapest to
  act on early: it is why the anomaly state must ship in slice 1 rather than be
  deferred to a later observability pass.
- **Silent misrouting is observed in practice.** If a real session applies a
  wrongly-*chosen* richer skill without the user noticing, discovery must become
  opt-in (config-only). The craft verdict feeding the ADR-0014 gate is only as
  trustworthy as the rubric behind it.
- **Enumeration recall proves inadequate.** If candidate enumeration misses
  genuinely richer skills (so the orchestrator never sees them to select), the
  fallback is an explicit opt-in `provides: [pr-review]` frontmatter tag on
  richer skills, accepting an authoring cost. **This criterion has no automatic
  instrument** — a recall miss produces silence, not a signal (see the blind
  spot in §3). It is detectable only by user report, which is a weaker trigger
  than the other criteria and is acknowledged as such. Precedence rule 1
  (config) is the standing workaround for any user who hits it.
  *(Matcher **precision** is no longer a kill criterion for the **pick** —
  Option D moved that to the model — but it still governs the anomaly surface's
  false-positive rate; see §3's calibration requirement.)*

## Open questions

- ~~**OQ1 (spike — first slice):** What is Codex's skill-discovery surface?~~
  **RESOLVED 2026-07-27 by spike.** Codex exposes user `$HOME/.agents/skills`,
  repo `.agents/skills`, and admin `/etc/codex/skills`, each holding
  `SKILL.md` files with the same `name`/`description` YAML frontmatter Claude
  uses. A Python helper enumerates and parses both hosts with one code path.
  **Consequence for decomposition:** the planned spike slice is no longer
  needed — implementation can start directly on the discovery helper.
- ~~**OQ2 (category signal authority):**~~ **RESOLVED 2026-07-27.**
  `scaffold.json` config is authoritative; trigger-intent description matching
  is the zero-config fallback; ambiguity falls back to jig's baseline rather
  than guessing. See Recommended Decision §3.
- **OQ3 (out of scope here — flagged):** Should ADR-0013's baseline
  scanner-orchestration depth be thinned to honor "shallow by default"? Tracked
  as a **separate** decision against ADR-0013; explicitly *not* resolved by this
  ADR.
- ~~**OQ4 (baseline-exclusion marker):**~~ **RESOLVED 2026-07-27.**
  `jig_baseline: true` frontmatter on every shipped baseline; **no migration**
  for already-scaffolded projects (none expected in the field at this stage).
- ~~**OQ5 (from the spike):** How are ambiguous candidates *surfaced*?~~
  **RESOLVED 2026-07-27 by frame-critique** — promoted from a deferred
  "implementation-slice decision" to an architectural requirement: the
  unapplied-candidates anomaly is a **gate-visible recorded state**, not an
  advisory note (Recommended Decision §3). Deferring it was the frame's primary
  defect: it was the one mechanism that would make Option D's dominant failure
  mode observable. The *presentation* surface (pass output vs. `jig hint:` vs.
  `orient` line) remains an implementation choice; the *recorded state* does not.
- **OQ6 (Option D's load-bearing premise) — OPEN for Codex; spike required.**
  Does the Codex orchestrator see installed skill descriptions? Claude: yes
  (directly observed). Codex: per relayed OpenAI documentation yes, but
  **second-hand and locally unconfirmable** (`codex-cli 0.133.0` exposes no
  `skills` subcommand). This — not OQ1 — is the premise Option D rests on, so
  the spike slice retired against OQ1 is **reinstated and re-aimed at OQ6**,
  gating the Codex orchestrator-selection path only. If it fails, Codex is
  config-only (see Consequences).
