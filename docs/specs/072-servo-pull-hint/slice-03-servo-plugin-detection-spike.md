---
status: DONE
dependencies: []
last_verified: 2026-06-15
kind: spike
---

## Slice 072-03 — servo-plugin-detection-spike

**Goal:** Settle spec Open Question 2 — can `land.py` **reliably** detect that
the servo *plugin* is available (distinct from the per-project `.servo/`
filesystem probe that 072-01 already does), without invoking a subprocess,
without coupling jig to undocumented host internals, and without forcing servo
on non-servo users? Produce a documented **go/no-go** that gates 072-02.

**DoR:**
- ✅ 072-01 DONE — the project-level `.servo/` probe, opt-out, and never-gate
  scaffolding exist.
- ✅ Q1 resolved by the human (2026-06-15): *yes* — when servo is available and
  the project is unscaffolded, jig should nudge toward `/servo:scaffold-init`.
  (Approves the ADR-0022 §5 reversal **in principle**; this spike tests whether
  it is **implementable** without an unacceptable cost.)

**Question:** Is there a robust, host-supported, install-method-independent,
subprocess-free way for `land.py prepare` to know the servo *plugin* is
installed/available — so 072-02 can fire its `/servo:scaffold-init` suggestion
*only* for servo users (honoring "no advertising to non-servo users")?

**Time-box:** 1 session (~half a day).

**Acceptance Criteria:**

1. **A documented finding exists** enumerating the candidate plugin-detection
   signals (`installed_plugins.json`; `CLAUDE_PLUGIN_ROOT` sibling; `claude
   plugin list`; `plugin.json` dependency; a reciprocal servo-side marker) and,
   for each, whether it is (a) documented/supported, (b) install-method-robust,
   (c) host-agnostic, (d) subprocess-free, (e) compatible with the
   loosest-coupling boundary (no forced servo dependency).
2. **A go/no-go recommendation** is recorded in Outcome, tied to whether *any*
   candidate clears all five — and explicitly to the user's own environment
   (does the chosen signal fire for a **local-clone** servo user?).
3. **If no-go:** the honest end-states are named (defer 072-02 + soften servo's
   README; OR a reciprocal servo-side signal as a cross-repo dependency), so the
   human can choose direction.

**DoD:**
- [x] All ACs pass; Findings + Outcome blocks filled.
- [x] Reviewed by `reviewer` subagent (read-only; judges the spike reasoning,
      not code). Reviewer prompt built by `review.py`. (compliance + craft,
      both `VERDICT: pass`; the reviewer independently corroborated the NO-GO
      against the live filesystem.)
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (No
      jig-internal decision deferred — the cross-repo servo-side breadcrumb
      contract is tracked in `docs/inbox.md`, the home for cross-repo /
      not-yet-a-spec items.)

**Findings:**

Two independent probes this session (a Claude-Code-mechanics consult + a read
of servo's repo at `/Users/ramboz/Projects/misc/servo`) converge:

- **No documented/supported plugin-discovery contract.** `~/.claude/plugins/installed_plugins.json`
  (which *does* list installed plugins, keyed `<name>@<marketplace>`) is an
  **undocumented internal** — Claude Code docs never mention it; "don't rely on
  it." `CLAUDE_PLUGIN_ROOT` points only at the *currently-executing* plugin
  (jig's own dir), and `CLAUDE_CONFIG_DIR` can relocate `~/.claude` entirely, so
  a hardcoded `~/.claude/plugins/...` path is unsafe. The one read-only CLI,
  `claude plugin list --json`, is a **subprocess** — barred by 072-02 AC5 and
  the spec's no-invocation posture.
- **Install-method-dependent — and inert for the user's own setup.** The local
  registry shows **servo is not an installed plugin here**; the user runs servo
  from a local clone (`~/Projects/misc/servo`). Locally-developed / `--plugin-dir`
  plugins do **not** appear in any persistent registry. So an
  `installed_plugins.json` probe returns "servo absent" → silent → the nudge
  would **never fire for the person who asked for it.**
- **The supported pattern has the wrong semantics.** Claude Code's documented
  way to couple plugins is a `plugin.json` **dependency** (force-install B when A
  is present). Declaring a servo dependency would push servo onto **every** jig
  user — the exact opposite of "no advertising to non-servo users" (Goal 2a /
  ADR-0022 §5) and the loosest-coupling boundary (both independently
  installable).
- **servo's only sanctioned detection contract is filesystem + project-scoped.**
  servo `ADR-0004` frames jig reading `<target>/.servo/runs/*/state.json` as the
  intended coupling — that is the **project** probe 072-01 already ships. servo
  exposes **no PATH binary** (purely `/servo:*` slash commands), so there is no
  `which servo` signal. There is **no** host-agnostic "servo-plugin-available"
  marker that works before a project is scaffolded.

**Outcome:** `072-02 plugin-detection — NO-GO (as specified).` No candidate
clears all five tests; the only robust, host-agnostic, subprocess-free,
boundary-respecting signal is the **project-level `.servo/` probe (= 072-01,
shipped)**, which by definition cannot detect the *unscaffolded* state 072-02
targets. The two honest end-states (a **human direction call**, requested at
reconciliation):

1. **Defer 072-02 + soften servo's README** — jig-only, honest, the spec's own
   anticipated fallback. servo's README stops asserting the missing-infra hint
   as built.
2. **Reciprocal servo-side signal** — servo writes a host-agnostic
   "servo-available" breadcrumb at install/scaffold time that jig's `land.py`
   reads. Honors Q1=yes properly (fires even for local-clone servo), stays
   subprocess-free and loosely coupled — but is a **cross-repo dependency**
   (the "reciprocal servo-side ADR" already named in ADR-0022 Scope), not
   buildable in jig alone.

(A jig-only best-effort `installed_plugins.json` probe is **not** recommended:
host-coupled, undocumented, and inert for local-clone servo — including the
user's current setup.)

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board` (+ Notes
      for the spike outcome and 072-02's disposition).
- [x] 072-02 transitioned per the human direction call: **reshaped around a
      reciprocal servo signal** (stays DRAFT, blocked on the cross-repo
      contract) — the chosen direction, not DEFERRED.
- [x] N/A — "soften README" was **not** chosen (reciprocal-signal was). The
      cross-repo TODO (servo writes the breadcrumb, a reciprocal servo-side ADR)
      is recorded regardless in `docs/inbox.md` (2026-06-15) + ADR-0022 Scope.

**Anti-horizontal-phasing check:** The observable value is a recorded,
evidence-backed go/no-go that prevents building a detection mechanism that is
fragile *and* would not fire in the requester's own environment — decision-
useful on its own.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

- **Outcome confirmed + direction chosen.** The spike's NO-GO (plugin
  auto-detection is unworkable) was accepted; the human chose the **reciprocal
  servo-side breadcrumb** path (spec Open Question 1/2 resolutions). 072-02 is
  **reshaped** around the breadcrumb (not deferred) and **blocked** on the
  cross-repo servo-side contract.
- **Local-clone disqualifier empirically verified (not just reasoned).** The
  compliance reviewer independently confirmed against the live
  `~/.claude/plugins/installed_plugins.json` that servo is **absent** from the
  registry despite being actively used from `~/Projects/misc/servo` — so the
  "an `installed_plugins.json` probe would never fire for the requester's own
  setup" claim is fact, not inference.
- **Two sub-claims rest on a Claude-Code-mechanics consult** (that
  `installed_plugins.json` is undocumented "don't rely on it", and that
  `CLAUDE_CONFIG_DIR` can relocate `~/.claude`). Flagged transparently: these
  came from a tooling consult, not an in-repo source. The **filesystem
  evidence independently carries the NO-GO** even if those were set aside, so
  the conclusion is robust. (Compliance reviewer, Medium-confidence nit.)
- **Two craft nits left as-is** (polish-only, no-code spike): AC1's five
  candidates × five tests are evaluated in woven prose rather than a 5×5 matrix
  (a table would be more scannable); the closing "not recommended" parenthetical
  restates Findings disqualifiers. Neither worth reworking a complete
  investigation. (Craft `[nit]`s.)
- **Cross-repo dependency propagated** to ADR-0022 Scope (the "reciprocal
  servo-side ADR" entry) + `docs/inbox.md` (dated 2026-06-15) — the latter
  confirmed present, satisfying slice-02's "(Tracked in `docs/inbox.md`.)" cite.

**Review evidence:** `reviews/slice-03-compliance.md` (pass),
`reviews/slice-03-craft.md` (pass).
