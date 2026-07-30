---
status: DRAFT
dependencies: [adr-0044, 098-01]
last_verified: 2026-07-27
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
- [ ] AC1 (packaging) green from the Claude side; AC2–AC5 confirmed on the Codex
      runtime **or** recorded as `degraded` / `unsupported` with the fallback
      wired — no silent assumption of parity.
- [ ] Host-capability matrix row committed.
- [ ] Post-impl review (compliance + craft; +frame per frontmatter).
- [ ] Deviation log written; reconciliation review.

### Close-out (post-DONE)
- [ ] Dogfood on Codex: a normal in-slice session produces no false fire.
