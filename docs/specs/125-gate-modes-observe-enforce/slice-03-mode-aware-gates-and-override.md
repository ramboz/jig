---
status: DRAFT
dependencies: [adr-0070, 125-01, 125-02]
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

## Slice 125-03 — mode-aware-gates-and-override

**Goal:** the other nine refusing gates (six CLI families, two hooks) resolve
their mode through the shared resolver with the same events and messages as
review-evidence, and a lifecycle transition can pass one named gate with a
written reason that stays on the slice or bug record.

**Decision:** [ADR-0070](../../decisions/adr-0070-gate-modes-off-observe-enforce.md)
§2–§3, §6 (reasoned override; anti-stuck release stays unbuilt), §7; spec 125
D1–D3. Takes the preamble half of the `docs/refinement-todo.md` entry "unify
the cross-ref guard family (now FOUR sites)" (*"The obligation stands for the
next guard-touching slice."*).

**DoR:**
- ⬜ ADR-0070 Accepted; 125-01 and 125-02 `DONE`.
- ✅ Gate sites and escapes are in the spec's inventory table.
- ✅ Precedent for a reasoned per-action flag: `--release --reason` writes a
  dated `## Release log` line (`workflow.py:5638-5645`, flag at `:5888`);
  `--reopen` already logs as `env_var="--reopen"` (`workflow.py:5530-5532`).
- ✅ Hook gates already import from `skills/_common` inside a `try`
  (`jig-spec-gate.sh:63-71`).
- ⬜ Re-run the inventory grep (spec A1); add any gate that landed since.
- ⬜ Re-read the guard-family entry; confirm which residuals are still open.

**Assumptions:** spec A1, A2, A4. Host behaviour of hook gates in Codex and
Copilot is not runtime-probed here (A4); the ACs below test what can be
tested in-repo.

**Acceptance Criteria:**

1. **CLI gates on the resolver.** `scaffold-precondition` (`workflow.py:4544`,
   `adr.py:675`), `start-collision` (`workflow.py:5366`, `:5422`),
   `cross-ref` (`workflow.py:5529-5536`, `:5604-5610`, `land.py:213`) and the
   four bug gates (`bug.py:894-989`) resolve their mode through
   `gate_mode`, keep their env vars and defaults, print the 125-01 header
   line, and emit `gate_bypassed` / `gate_would_block` / `gate_blocked` as
   125-01 and 125-02 define. `bug.py`'s private `_DISABLE_VALUES` and
   `_gate_enabled` (`bug.py:95`, `:216-220`) are removed.
2. **Observe writes no attestation.** When a gate in `observe` lets through
   something it would have refused, the command writes none of the fields
   its pass would write: no `red_confirmed_at` on a bug whose regression test
   was not red (`bug.py` stamps it after the red check), no review-passed DoD
   tick (125-01 AC4). The note and the event name the check that failed, for
   example a `→ REVIEWED` green check that was still red. The record shows
   only what was actually verified.
3. **Bug-diagnose keeps its tier split.** With no env or config mode,
   `bug-diagnose` refuses on `gnarly` and warns on `standard`, exactly as
   `bug.py:894-903` does today; the warning becomes a `gate_would_block`
   event. An explicit mode applies to both tiers.
4. **Hook gates on the resolver.** `jig-spec-gate.sh` and
   `jig-secret-scan.sh` read `gates.conventions.mode` /
   `gates.secret-scan.mode`.
   - The approval vars keep working and resolve as `off` (source `env`).
   - `observe`: exit 0 with no output, and a `gate_would_block` event naming
     the rule only (for secret-scan the pattern name, never the value).
   - Both hooks still evaluate their cheap match when approved, so a
     `gate_bypassed` event is written only when the approval actually let a
     match through. Secret-scan gains this event (078 deferred it).
   - Any import, read or resolve failure falls back to `enforce`, today's
     behaviour. A test per hook breaks the import and shows exit 2 on a match.
   - Through `copilot_hook_adapter.py --enforce`, observe yields an allow and
     enforce a deny (adapter test).
5. **Reasoned override on transitions.** `workflow.py transition` and
   `bug.py transition` accept `--override <gate> --reason "<why>"`:
   - it passes the named gate for this one transition when that gate is in
     `enforce` and would refuse; every other gate still applies;
   - it appends `- <date> — <gate> overridden at → <STATE>: <reason>` to a
     `## Gate override log` section on the slice or bug record (created if
     absent), mirroring `_append_release_log`;
   - it emits `gate_overridden` (gate, spec ref, timestamp; not the reason
     text), and `gate-stats` gains an `overridden` column;
   - `--override` without `--reason`, or naming an unknown gate, is refused
     before anything changes; naming a gate that did not fire prints a note
     and writes nothing.
   This gives `start-collision` a per-action escape, closing the `--reopen`
   asymmetry the guard-family entry names. `--reopen` keeps its meaning (a
   sanctioned re-open for cross-ref) and is not folded in.
6. **One guard preamble.** The four start-collision / cross-ref sites share
   one preamble for mode resolution, the event, and `--reopen` / `--override`
   handling, with tests pinning each site's current refusal first.
7. **Inventory documented, packages rebuilt.** `docs/architecture.md` lists
   every resolver-backed gate: config key, env var, default mode, rule
   source, and host behaviour (observe exits 0 on every host; enforce blocks
   via exit 2 on Claude, via the adapter's deny on Copilot, and only once
   the user has trusted the hook on Codex). Host packages are regenerated with
   `scripts/build_host_packages.py` and its drift check passes.

**Edge cases to cover explicitly:**
- `JIG_CROSSREF_GATE=observe` with `--reopen`: `--reopen` wins (no check run),
  as today.
- `--override cross-ref` when two cross-ref sites would both refuse: one
  override covers the gate, one log line.
- Two `--override` flags for two different gates on one transition: both
  logged.
- Secret-scan approved and the content has no match: no event.
- Conventions gate in `observe` editing `docs/conventions.md`: edit allowed,
  one event, nothing printed.
- A `bug.py transition → FIXING` in `observe` where the regression test passes
  without a fix: proceeds, no `red_confirmed_at`, one event.

**Not in this slice:** the anti-stuck release (ADR-0070 §6; no current gate
qualifies); `--override` on `adr.py accept`, `land.py execute` and
`workflow.py new` (ADR-0070, open question 4); the guard-family entry's
`endswith` branch-exclusion and ADR-evidence keying residuals.

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
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the
      spec): `CLAUDE.md`'s Key-terms lines that name `JIG_*=0` bypasses may
      need the mode words.

**Anti-horizontal-phasing check:** after this slice, any jig gate can be
trialled in `observe`, every refusal says why, and passing a lifecycle gate
on purpose leaves a reason a reviewer can read on the record.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `updated` | _TODO: gate inventory with host behaviour (AC7)._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `updated` | _TODO: guard-family entry — preamble half done, residuals re-deferred._ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
