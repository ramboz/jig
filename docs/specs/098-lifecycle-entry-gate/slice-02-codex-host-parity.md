---
status: DONE
dependencies: [adr-0044, 098-01]
last_verified: 2026-08-02
frame_review: true  # the Codex hook payload shape can only be proven on the
#                   # actual Codex runtime — the point of this slice.
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about runnable
     surfaces by probe first (run it / read source) or a citation, else mark them
     as assumptions — never assert an unverified claim as fact. -->

## Slice 098-02 — Codex host parity

**Goal:** The entry gate behaves the same on **Codex** as on Claude, and that
sameness is *verified explicitly and separately* rather than assumed from the
build transform. Where the Codex runtime cannot support the mechanism, the gate
degrades honestly and the degradation is written down — never a half-shipped
feature that silently works on one host only
([ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)).

**Why a separate slice** (settled call #4): the maintainer's call is to stay
symmetric across hosts and keep the Codex work in this spec, but as its own
slice that can be verified on its own. Packaging parity is cheap and mechanical;
*runtime* parity is not, and it needs the Codex runtime in hand — 083-08 is the
precedent for splitting exactly there.

**DoR:**
- ✅ Slice 098-01 is DONE on the Claude host (this slice verifies its Codex twin).
- ✅ The build transform exists and is automatic: `scripts/build_codex_plugin.py`
  `_write_codex_hooks` generates `hosts/codex/plugins/jig/hooks/hooks.json` from
  `hooks/hooks.json`, rewriting script paths to
  `${PLUGIN_ROOT}/hooks/scripts/`. Probed 2026-07-27: the Codex package's
  `PostToolUse` / `Edit|Write|MultiEdit` matcher already carries
  `jig-post-edit-verify.sh` and `jig-boundary-change-warn.sh` — the exact
  matcher 098-01's hook joins, so it mirrors for free.
- ⏳ Runtime confirmation needs the actual Codex host; it cannot be proven from
  the Claude side by inspection. Same constraint 083-08 hit.

**Acceptance criteria:**

1. **Packaging parity (provable here).** A test asserts the generated Codex
   package carries `jig-entry-gate.sh` in the `PostToolUse` /
   `Edit|Write|MultiEdit` matcher, with the `${PLUGIN_ROOT}` prefix and the
   script copied into `hosts/codex/plugins/jig/hooks/scripts/`.
   `scripts/build_host_packages.py --check` stays green.
2. **Payload parity (needs the runtime).** Confirm the Codex `PostToolUse`
   payload exposes the edited path as `tool_input.file_path` — 098-01's whole
   trigger. If it does not, wire the Codex-side reader to the actual field and
   record the difference here.
3. **Boundary parity.** The two-part source boundary (settled call #3) resolves
   the same on Codex: `git check-ignore` behaves identically (it is git, not the
   host), and the lifecycle-artifact list resolves the docs root through the
   same `_common/project_layout.py`. Assert on a relocated docs root too.
4. **Env/opt-out parity.** `JIG_ENTRY_GATE=0` disables the gate on Codex with the
   same token set `{0,false,off,no}`.
5. **Cadence parity.** The once-per-session `$TMPDIR` state file works under the
   Codex runtime's session model, or the divergence is documented and the gate
   degrades to a safe cadence rather than nagging every edit.
6. **Host-capability row.** Add the entry gate as a row in the host-capability
   matrix (Claude vs Codex): `supported` / `degraded` / `unsupported`, with the
   fallback named for anything not `supported`. This is the artifact that makes
   "verified explicitly and separately" real.
7. **Fail-open on both hosts.** No Codex-only failure mode; any error leaves the
   session untouched.

**Tests first (TDD):**
- generated Codex `hooks.json` contains `jig-entry-gate.sh` under `PostToolUse` /
  `Edit|Write|MultiEdit` with the `${PLUGIN_ROOT}` prefix.
- the hook script is present in the Codex package's `hooks/scripts/`.
- `build_host_packages.py --check` green.
- Codex payload fixture → nudge fires on an out-of-lifecycle source edit.
- Codex payload fixture → silent on a lifecycle artifact and on a
  `.gitignore`-matched path.
- `JIG_ENTRY_GATE=0` on the Codex fixture → silent.

**DoD:**
- [x] AC1 (packaging) green from the Claude side (`test_codex_entry_gate_parity.py`); AC2 (payload) + AC5 (cadence) recorded as **`degraded`** in the host-capability matrix with fail-open fallbacks wired — no silent assumption of parity. AC3 (boundary) + AC4 (opt-out) proven on the shipped Codex copy.
- [x] Host-capability matrix row committed (`docs/architecture.md`) with a supported/degraded/unsupported legend.
- [x] Post-impl review (compliance + craft + frame) — all three returned needs-changes round 1; every finding applied + test-verified; verdicts recorded **pass** (applied state). See `reviews/slice-02-{compliance,craft,frame-critique}.md`.
- [x] Deviation log written; reconciliation review.
- [x] Reconciliation sweep produced under this slice heading.

### Deviation log (after reconciliation)

**1. `assumed` → `degraded` (frame review).** The first matrix draft labeled the two runtime-dependent rows (`PostToolUse` payload, cadence) `assumed` — a state outside the AC6 legend, and the exact "assumed-from-transform" parity the slice Goal set out to eliminate. Relabeled **`degraded`** (a wired fail-open / safe-over-fire fallback is degraded semantics) and added an explicit supported/degraded/unsupported legend to the matrix.

**2. Dual-host `_INFRA_DIRS` refinement (frame review) — touches 098-01's shipped helper.** AC3's "boundary resolves the same on Codex" was over-stated: the Codex build's blind `.claude`→`.codex` rewrite dropped `.claude` from `_INFRA_DIRS`, so a Codex session treated `.claude/` as source — a hole the jig repo's own `.claude/`+`.codex/` state hits. The source `_INFRA_DIRS` now lists **both** `.claude` and `.codex`, so the **Claude** gate treats an also-present `.codex/` as infra (closes the dogfood case). The **Codex** copy collapses to `.codex` only, so it still nudges on `.claude/` — a residual accepted limit, **documented** in the matrix AC3 caveat and **pinned** by `test_dual_host_claude_dir_nudges_on_codex_accepted_limit`. This edits 098-01's shipped `entry_gate.py` (already DONE); the change is a cross-host parity refinement squarely in 098-02's scope, and 098-01's own tests were updated (`.codex` added to `test_infra_dirs_are_silent`). Fully closing the Codex side needs a build change and is deferred until a real dual-host project reports it.

**3. architecture.md hook-count drift swept (compliance + craft).** Adding the 15th hook in 098-01 left five stale "fourteen"/"14 hooks" references (lines 82/109/131 + the spine paragraph + diagram). All corrected to fifteen/15; the diagram gained the `h15` entry-gate node + edge. (The spine-paragraph count was fixed in 098-01; the other four were caught here.)

**4. Runtime parity is honestly `degraded`, not `supported` (design posture).** AC2/AC5 need the Codex runtime in hand (the 083-08 constraint); they are not claimed `supported`. The "shares `jig-boundary-change-warn`'s payload contract" argument is kept as a packaging fact (that sibling ships in the same Codex matcher), not used to upgrade a row — a shared-fate plausibility, not corroboration.

**5. Test-craft fixes (craft + compliance).** Added `tearDownClass` to pop the injected `sys.path` entry + corrected the inaccurate `_common`-isolation comment; asserted `.claude` absent in the Codex transform; parametrized the opt-out over `{0,false,off,no}`; added relocated-docs-root and `.gitignore`-matched-path parity cases.

### Reconciliation sweep

- **`docs/architecture.md`** — host-capability matrix + legend + AC3 dual-host caveat added; hook-spine counts + diagram corrected (14→15). Not shipped in host packages (docs/ excluded), so no host regen for the doc. Disposition: **updated**.
- **`hooks/scripts/lib/entry_gate.py`** (+ both host mirrors) — `_INFRA_DIRS` gains `.codex`; host packages regenerated, `--check` in sync. Disposition: **updated**.
- **`scripts/test_codex_entry_gate_parity.py`** — new Codex parity suite (11 tests: 2 packaging + 2 transform + 7 behavior; the opt-out test parametrizes 4 tokens). Disposition: **added**.
- **CLAUDE.md hot cache** — a one-line entry-gate term is added at spec close via `/jig:memory-sync` (next step), not per-slice. Disposition: **deferred to spec close**.
- **`docs/specs/README.md` status board** — regenerated at spec close. Disposition: **deferred to spec close**.

### Close-out (post-DONE)
- [ ] Dogfood on Codex: a normal in-slice session produces no false fire.
      (Requires the Codex runtime — the `degraded` rows' real-world confirmation;
      tracked, not blocking this Claude-host-verifiable slice.)
