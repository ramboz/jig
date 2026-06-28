---
status: DONE
dependencies: [072-01, 072-03]
frame_review: true
last_verified: 2026-06-27
---

## Slice 072-02 — unscaffolded-suggestion

> **Reshaped — now UNBLOCKED (2026-06-27).** Q1 and Q2 are resolved (see spec
> Open Questions): Q1 — *yes*, nudge when servo is available and the project is
> unscaffolded; Q2 — spike [072-03](slice-03-servo-plugin-detection-spike.md)
> found servo-*plugin* auto-detection **unworkable**, so the trigger is
> reshaped onto a **reciprocal servo-side "available" breadcrumb** (servo writes
> a host-agnostic marker; jig reads it). **That servo-side contract now exists
> and is shipped:** servo **ADR-0013** (Accepted 2026-06-18) + servo **spec 014**
> (DONE) emit `${XDG_STATE_HOME:-$HOME/.local/state}/servo/available.json` from
> three writer paths. Keep `frame_review: true`: it still reverses ADR-0022 §5's
> "absent → no mention" for the slice-land surface. **The DRAFT hold is lifted**
> — this slice may now proceed through the gates (frame-critique BEFORE
> READY_FOR_REVIEW).
>
> **Frame-critique iterated 2026-06-27 (two rounds, both `needs-changes`).** A
> pre-impl frame-critique
> ([`reviews/slice-02-frame-critique.md`](reviews/slice-02-frame-critique.md))
> caught, across two rounds: (1) machine-global marker vs per-project nudge
> (forever-nag); (2) unexamined writer-timing; (3) reachability mis-grounded on
> an *assumed* verify step; (4) AC6 conflating "shown" with "seen" (an
> unobserved CI/headless `prepare` could burn the one budgeted nudge). All
> addressed in `## Assumptions` (A1–A3) + the reworked ACs: **AC2** = a
> per-*machine* guarantee; **AC6** = a once-per-project `.jig/servo-hint-shown`
> gate **consumed only on an interactive land** (cadence chosen by the
> maintainer 2026-06-27); **A2** reachability now rests on the *scaffold*
> writers (the Q1 target has the marker by construction), verify-install demoted
> to a bonus. **Round 3 frame-critique PASSED → transitioned to
> READY_FOR_REVIEW 2026-06-27** (one non-blocking residual captured below for
> reconciliation). Ready for spec-authoring review, then
> READY_FOR_IMPLEMENTATION.

**Goal:** When a **reciprocal servo-side "available" breadcrumb** indicates
servo is set up on this machine **but the target project is *not*
servo-scaffolded** (no `.servo/`), `land.py prepare` emits a single, gentle,
opt-out-able suggestion to run `/servo:scaffold-init` for oracle-gated /
headless iteration — making servo's README "emit … when servo-style
infrastructure is missing" claim true **without** advertising servo to users
who don't have it. Reads the breadcrumb only (filesystem, no subprocess);
builds on 072-01's `.servo/` probe, `.jig/no-servo-hint` opt-out, and
never-gate scaffolding.

**Assumptions (frame-critique grounding — recorded 2026-06-27 after a
`needs-changes` frame-critique; evidence:
[`reviews/slice-02-frame-critique.md`](reviews/slice-02-frame-critique.md)):**

- **A1 — Machine-global presence is the *intended* trigger, not a bug.** The
  servo marker is one file per machine
  (`${XDG_STATE_HOME:-$HOME/.local/state}/servo/available.json`), so it answers
  "has servo been used **anywhere** on this machine?", **not** "should *this*
  project use servo?". That global signal paired with the project-local
  `.servo/`-absent test is exactly Q1's approved shape ("servo *available* AND
  *this project* unscaffolded") and the anti-horizontal-phasing target ("a dev
  who uses servo on other projects but hasn't scaffolded it here"). The
  cross-project breadth is deliberate; **AC6's once-per-project gate + the
  `.jig/no-servo-hint` opt-out are the scoping levers** (resolves the
  frame-critique **primary** blocker — AC2 reworded to a per-*machine*
  guarantee).
- **A2 — Reachability is grounded on the *scaffold* writers, not on an assumed
  verify step.** Verified against servo's writers (cross-repo, 2026-06-27): the
  marker is written by `skills/scaffold-init/scaffold.py`,
  `scripts/scaffold_runtime.py`, **and** `scripts/verify_install.py plugin
  <root>`. **The load-bearing reachability for the Q1 target user — "a dev who
  uses servo on *other* projects" — is the scaffold writers:** using servo on
  another project *means* servo was scaffolded there, which wrote the
  machine-global marker. So for the requester this slice exists to serve, the
  marker is present **by construction** before they ever land here — independent
  of any explicit verify step. The `verify_install.py plugin` path is a **bonus**
  that *additionally* reaches a local-clone user who installed servo but has not
  yet scaffolded it anywhere — *if* they ran verification; the frame does **not**
  lean on that path being auto-invoked (the spike's lesson: local-clone
  workflows skip registration steps). A machine with **no** marker has genuinely
  never *used* servo (never scaffolded, never verified); staying silent there is
  the desired behavior — we do not advertise servo to someone who has never used
  it — not the 072-03 "never fires for the person who asked" failure (the Q1
  target always has the marker by construction).
- **A3 — Marker staleness is tolerated, bounded by AC6 + opt-out.** The marker
  is never pruned, so a removed/moved servo leaves a stale `available.json`.
  The cost of acting on a stale marker is **one** extra suggestion line per
  project (AC3/AC6), opt-out one file away (AC2's never-gating posture). jig
  deliberately does **not** freshness-check `updated_at` (rejected: an
  arbitrary threshold + clock logic for a soft advisory). Accepted, bounded
  over-nudge.

**Known residual (frame-critique round 3, PASS — non-blocking; flag at
reconciliation):** AC6's `sys.stdout.isatty()` is a **fail-open** proxy for
"a human saw the nudge." A human observing `prepare` through an agent harness
/ pty wrapper (non-TTY — *jig's own primary dogfooding mode*) does **not**
consume the once-per-project budget, so the one-line nudge re-fires on each
land in that repo until `.jig/no-servo-hint` is dropped. This is the
**deliberate** direction: an *unseen* budget burn is unrecoverable (the nudge
is lost forever), whereas a re-nudge costs one advisory line + a one-file
opt-out. Do **not** add harness/pty detection speculatively (072-03's lesson:
runtime environment detection is brittle); revisit only if a real over-nudge
complaint lands.

**DoR:**
- ✅ 072-01 landed — the advisory section, `.jig/no-servo-hint` opt-out,
  never-gate posture, and filesystem-only detection all exist.
- ✅ **Q1 resolved (human, 2026-06-15):** yes — nudge when servo is available
  and the project is unscaffolded (the §5 reversal is approved in principle).
- ✅ **Q2 resolved by spike [072-03](slice-03-servo-plugin-detection-spike.md):**
  plugin auto-detection is NO-GO; the trigger is a reciprocal servo-side
  breadcrumb instead.
- ✅ **RESOLVED (cross-repo, 2026-06-27):** the **servo-side breadcrumb
  contract** now exists and is shipped. Servo **ADR-0013** (Accepted
  2026-06-18) + servo **spec 014** (DONE) define and emit a host-agnostic
  marker at `${XDG_STATE_HOME:-$HOME/.local/state}/servo/available.json` —
  JSON, `schema_version: 1`, fields `plugin_name` / `source_kind` /
  `source_path` / `source_version` / `updated_at`; best-effort **advisory
  hint** (presence means "servo observed here before"; absence does not prove
  unavailable). Three servo writer paths populate it
  (`skills/scaffold-init/scaffold.py`, `scripts/scaffold_runtime.py`,
  `scripts/verify_install.py plugin <root>`), so it fires even for a
  **local-clone** servo user — the gap that sank plugin auto-detection (spike
  072-03). Per the coupling precedent (the writer owns the contract; cf. servo
  ADR-0004 for `.servo/runs/*`), jig only reads it.

**Acceptance Criteria (frame-critique addressed — see `## Assumptions`
above + [`reviews/slice-02-frame-critique.md`](reviews/slice-02-frame-critique.md)):**

1. **Fires only on the precise state.** A `/servo:scaffold-init` suggestion
   appears **iff** the servo availability marker
   `${XDG_STATE_HOME:-$HOME/.local/state}/servo/available.json` is present and
   parseable as JSON with `schema_version: 1` **AND** `.servo/` is absent at
   the target **AND** `.jig/no-servo-hint` is absent **AND**
   `.jig/servo-hint-shown` is absent (the once-per-project gate — AC6). A
   missing, unreadable, or schema-mismatched marker is treated as "servo not
   available" (silent) — the marker is an advisory hint, never a hard
   capability proof (servo ADR-0013).
2. **No advertising to non-servo-*machine* users — a per-machine guarantee.**
   The marker is **machine-global** (one file per machine, written by servo's
   scaffold / runtime / verify-install paths), so its presence means "servo has
   been used **somewhere** on this machine" — exactly the Q1 trigger ("servo
   *available* AND *this project* unscaffolded"; see A1). When the marker is
   **absent** (servo never set up on this machine), `prepare` stays silent about
   servo — no funnel into autonomy for a user who has never touched servo. This
   is the reconciliation of ADR-0022 §5 with servo's README. Because the
   `verify_install.py plugin` writer fires at local-clone verification time
   (A2), the nudge reaches even a **local-clone** servo user whose first servo
   project is this one (the gap that sank plugin auto-detection — spike 072-03).
   **The "silent" guarantee is per-machine, not per-project:** a servo-using
   machine would otherwise see the nudge in *every* unscaffolded repo — AC6 +
   the opt-out are the per-project scoping levers.
3. **Gentle, single, never-gating.** At most one advisory line naming
   `/servo:scaffold-init`; never adds a blocker; never changes the exit
   code; honored by the `.jig/no-servo-hint` opt-out.
4. **Not on doc-only slices.** The suggestion is suppressed for doc-only
   slices (no test runner detected — mirrors `prepare`'s existing
   test-warn path), so it surfaces only where servo's oracle would
   plausibly help.
5. **Still no servo invocation.** Reading the breadcrumb is read-only
   (a filesystem `stat`/read); no `servo:*` command, no `claude` subprocess,
   no autonomy primitive, is ever run.
6. **Shown at most once per project — counted only when actually surfaced.**
   Because the marker is machine-global, an un-silenced nudge would otherwise
   fire on *every* qualifying land in *every* unscaffolded repo (the
   frame-critique primary blocker). To bound that, the once-per-project budget
   is consumed by a `.jig/servo-hint-shown` breadcrumb (working-tree-local,
   gitignored, **best-effort** — a failed write must not block `prepare` or
   change its exit code); while it is present the nudge stays silent (AC1).
   **The budget is consumed only when the nudge is actually surfaced to a
   human:** `prepare` writes `.jig/servo-hint-shown` **only when its output is
   interactive** (`sys.stdout.isatty()`). In a non-interactive run (CI,
   headless, piped, or a sub-agent invocation) the advisory line may still
   print but the marker is **not** written, so an unobserved `prepare` cannot
   silently burn the project's one budgeted nudge (**"emitted once ≠ seen
   once"** — the advisory-trigger-reachability lesson). `.jig/no-servo-hint`
   remains the **explicit, permanent** opt-out (the user saying "never"),
   semantically distinct from `.jig/servo-hint-shown` (jig recording "already
   surfaced it here once"). Neither file is ever read by a `servo:*`
   invocation (AC5).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC; edge cases: **interactive**
      land, marker present + unscaffolded (→ nudge **and** writes
      `.jig/servo-hint-shown`); **non-interactive** land, `isatty` false (→ line
      may print but `.jig/servo-hint-shown` is **not** written — budget not
      burned, AC6); second interactive land with `.jig/servo-hint-shown` present
      (→ silent, AC6); marker absent / unreadable / schema-mismatched
      (→ silent); `.servo/` present (→ silent); `.jig/no-servo-hint` opt-out
      present (→ silent); doc-only slice (→ suppressed); best-effort:
      `.jig/servo-hint-shown` write fails (→ nudge still shown, exit code
      unchanged). Resolve the marker path via `XDG_STATE_HOME` and stub `isatty`
      in tests (never touch the real home dir or depend on a real TTY),
      mirroring servo spec 014's test seam.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] **Frame-critique pass recorded** (`frame_review: true`) — the
      adversarial check on the ADR-0022 §5 reversal and the
      plugin-detection assumption, BEFORE READY_FOR_REVIEW.
- [x] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `CLAUDE.md` hygiene per spec 025-01: if this slice closes spec 072,
      compress the entry; else leave it. Update the `slice-land` row if the
      missing-infra behaviour shipped.
- [ ] If Q1 resolved by **building** the suggestion: ADR-0022 §5 amended to
      note the slice-land surface emits an opt-out-able suggestion when
      servo is plugin-present-but-unscaffolded. If Q1 resolved by
      **dropping** the slice: servo's README softened to "planned," this
      slice marked `DEFERRED` with the resolution trigger recorded.

**Anti-horizontal-phasing check:** A developer who uses servo on other
projects, but hasn't scaffolded it here, finishes a slice and sees a
one-line nudge to run `/servo:scaffold-init` — observable from CLI. (Q2's
plugin-availability undetectability is resolved not by detecting the plugin
but by reading servo's shipped `available.json` breadcrumb; the frame-critique
should still pressure-test whether that hint is reliable enough to justify the
ADR-0022 §5 reversal.)

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

- **Cross-repo dependency resolved before build.** The slice was unblocked
  2026-06-27 once servo shipped its reciprocal contract (servo **ADR-0013**
  Accepted 2026-06-18 + servo **spec 014** DONE) — a host-global
  `${XDG_STATE_HOME:-$HOME/.local/state}/servo/available.json` marker. jig reads
  it only (filesystem, no subprocess), matching servo's writer path byte-for-byte.
- **Implementation mirrors the 072-01 helpers.** `render_servo_suggestion` +
  `_servo_available` / `_servo_available_marker_path` /
  `_servo_hint_already_shown` / `_output_is_interactive` / `_mark_servo_hint_shown`
  sit directly below 072-01's `render_servo_advisory` / `_servo_present` /
  `_servo_hint_opted_out` in `skills/slice-land/land.py` and reuse them. The two
  surfaces are **mutually exclusive** by the `.servo/`-presence test (advisory
  iff present; suggestion iff absent), so no double `## servo` header can emerge.
  Added `import json` to `land.py`.
- **Frame-critique drove three rounds (all evidence durable in `reviews/`).**
  Round 1 caught machine-global-vs-per-project forever-nag + unexamined
  writer-timing; round 2 caught reachability mis-grounded on an assumed verify
  step + AC6 conflating "shown" with "seen"; round 3 PASS. The framing was
  reshaped into `## Assumptions` A1–A3 + AC2 (per-machine guarantee) + AC6
  (once-per-project `.jig/servo-hint-shown`, consumed only on an interactive
  `isatty()` land).
- **Accepted-by-design residual (frame-critique round 3, carried verbatim):**
  `_output_is_interactive()` via `sys.stdout.isatty()` is a **fail-open** proxy
  for "a human saw the nudge." Under jig's own non-TTY agent-harness / pty
  dogfooding mode the once-per-project budget is never consumed, so the one-line
  nudge re-fires each land until `.jig/no-servo-hint` is dropped. Deliberate
  direction: an *unseen* budget burn is unrecoverable, whereas a re-nudge costs
  one advisory line + a one-file opt-out. Harness/pty detection is explicitly
  **not** added (072-03's lesson: runtime-environment detection is brittle);
  revisit only on a real over-nudge complaint.
- **`.jig/servo-hint-shown` is gitignored** in both jig's own root `.gitignore`
  and the scaffold-generated `_GITIGNORE_SECRET_PATTERNS` tuple (so scaffolded
  projects ignore it too), following the spec-080 semantic-index precedent of
  putting non-secret local-state entries in that same tuple. Note: the tuple now
  mixes secret patterns with local-state markers — a future cleanup could split
  a dedicated local-state block, but that is out of this slice's scope.
- **Review:** compliance PASS (two test-quality nits fixed inline — the
  second-land test is now a real write→silence round-trip; the best-effort test
  asserts exit-code equality against a servo-silent baseline). Craft PASS, zero
  blockers, three strengths; three craft nits fixed inline (paren-wrapped the
  `_servo_available` boolean, deduped `target or Path.cwd()` into one
  `servo_target` local, dropped a non-Optional `raw` annotation — kept
  Python-3.9-safe per the repo floor). Host packages (Claude + Codex)
  regenerated; full suite 3025 green; ruff / spec_lint / drift / contracts clean.
- **No new ADR.** This consumes the existing [ADR-0022](../../decisions/adr-0022-pluggable-oracle-boundary.md)
  §5 boundary (filesystem-only, no servo invocation). Per this slice's own
  Close-out checkbox, ADR-0022 carries a dated `## Amendments` note that the
  §5 "absent → no mention" rule is reversed for the slice-land surface when
  servo is available-on-machine-but-this-project-unscaffolded.

### Reconciliation sweep

- **Deviation log** — `updated` (written above).
- **Architecture impact** — `no-op`. No module boundary or public contract
  changed; the new helpers are private siblings of the 072-01 set in `land.py`.
  The servo-coupling boundary is governed by the pre-existing ADR-0022.
- **Load-bearing decision (ADR trigger)** — `no-op` (no *new* ADR). The
  load-bearing choices (machine-global-presence as the intended trigger;
  once-per-project + interactive-only budget; reject freshness-checking and
  harness-detection; reachability grounded on the scaffold writers) are durably
  recorded in this slice's `## Assumptions` + the three `reviews/` frame-critique
  artifacts, *within* ADR-0022's boundary. ADR-0022 gets a dated `## Amendments`
  note for the §5 slice-land reversal (close-out checkbox), not a new ADR.
- **Conventions impact** — `no-op`. No `docs/conventions.md` rule added/changed.
- **Lightweight decisions** — `no-op`. The advisory wording is the only string
  choice; it mirrors 072-01's advisory voice, not a standalone product decision.
- **Inbox triage** — `updated`. The 2026-06-15 `servo-side breadcrumb contract
  (072-02 cross-repo dependency)` item in `docs/inbox.md` is RESOLVED (servo
  shipped ADR-0013 / spec 014; this slice consumed the marker) and struck through.
- **Primer hygiene** — `updated`. Spec 072 closes with this slice; the lean
  primer (spec 076) carries no per-072 entry, so no `CLAUDE.md` / `AGENTS.md`
  compression is needed; the load-bearing shipped invariant lives in the status
  board Notes column (compressed to the DONE state).
- **Memory-sync** — `updated`. `servo-jig-coupling-boundary` memory updated to
  record 072-02 SHIPPED (was "blocked on cross-repo servo work").
- **Closed-spec drift** — `no-op` for jig records. Servo's README "emit … when
  servo-style infrastructure is missing" claim is now fully true (072-01 present
  case + 072-02 missing case); any servo-side README softening is a servo-repo
  concern, not jig closed-spec drift.
- **Use-case coverage** — `no-op`. `workflow.py coverage` reports the breadth
  layer is not adopted (no `## Use cases` section in jig's product-vision).
