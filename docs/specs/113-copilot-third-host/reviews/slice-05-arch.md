---
slice: 113-05 — enforcing-hooks-and-permissions
pass: arch
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T17:53:42Z
prompt_source: review-113-05-arch.txt (jig:reviewer subagent, Opus)
substrate: non-interactive
---

Arch review on slice 113-05 (enforcing-hooks-and-permissions). Reviewer:
read-only jig:reviewer (Opus). VERDICT: pass (upgraded from needs-changes after
the one blocker was cleared — see below).

The built architecture is sound and well-tested:

- **Enforcing/advisory split** is clean and correct — one adapter, mode-gated by a
  shared `--enforce` constant, with the right asymmetric posture (advisory fail-open
  exit-0; enforcing preserves exit code and fails CLOSED on spawn failure), and
  exit-2-alone-denies as primary with the deny body as belt-and-suspenders. Directly
  satisfies ADR-0061's "keep their teeth / degrade visibly." Safe because the
  fronted gates fail-open (exit 0) on every non-block path (confirmed
  jig-spec-gate.sh:42,49,54,72,86), so their only non-zero is a deliberate exit 2.
- **113-04 schema correction** (nested→flat) is central, complete, and correctly
  folded into 113-05 where `render_copilot_hook_file` is already being touched.
  Folding the DONE-slice's bug-fix into 113-05 (rather than reopening 113-04) is the
  right seam call — the fix lives with the code being modified; amending the DONE
  113-04 record separately matches ADR-0010 closed-spec-drift policy.
- **Permissions-floor reshape** to a real preToolUse deny hook is the right call
  over a dead settings.json; appropriately lean; the standalone-duplicate-drift-
  guarded pattern is genuinely test-pinned; it also closes a real capability gap
  (the 2 mid-string force-push variants Copilot's own `shell()` syntax can't
  express). UNMAPPABLE calls (Task/Skill/AskUserQuestion) are genuinely unmappable
  within render-layer scope and honestly annotated.
- **Inventory** is a real structural invariant (cross-checked both ways vs
  hooks.json; every SHIPPED entry asserted actually built); enforcement verified by
  positive-confirmation subprocess tests against the real adapter+scripts.
- **Live-firing deferral** (verified via deterministic positive-confirmation
  subprocess tests; runtime "Copilot honors exit 2" homed to post-push/113-06) is
  acceptable: the enforcing model rests on one docs-authoritative fact (exit 2 =
  deny, re-verified vs CLI 1.0.86-0), and the adapter's exit-2 + deny-body behavior
  is itself proven against the real scripts.

BLOCKER (raised, then CLEARED in-review):
- [blocker][spec] Nine MAPPABLE advisory hooks (11 registrations) carried inventory
  notes "homed to 113-06," but slice-06's ACs contained no AC that rendered them and
  its DoR falsely asserted "renderer emits the full hosts/copilot/ content." The
  ADR-0061 "no silent drop" invariant was technically met (loudly MAPPABLE) but the
  residual pointed at a home that did not own the work. RESOLUTION APPLIED: added
  slice-06 **AC6 "Remaining advisory-hook parity"** (renders every MAPPABLE hook via
  the existing advisory-render path, flips each MAPPABLE→SHIPPED, test asserts no
  MAPPABLE entry remains — mechanically closing the invariant); corrected the false
  DoR claim; reworded all 11 inventory notes + both header pointers to "rendered in
  113-06 (AC6)". Reviewer re-verified: **blocker cleared**; disposition (render in
  113-06 AC6, not defer beyond spec 113) is the sound choice under the full-parity
  bar and the stronger of the two offered fixes.

Reconciliation-log notes (non-blocking):
- [concern][impl] `copilot_permissions_floor.py:111-136` — cross-host floor-semantics
  divergence: `regex.search` (anywhere-match) is broader than Claude/Codex's
  prefix-anchored `permissions.deny` (e.g. `echo "... rm -rf /"` DENIED on Copilot,
  ALLOWED on Claude). Deliberate + fail-safe in direction, but a genuine behavior
  divergence that can produce confusing false-positive denies — record explicitly in
  the deviation log, not only a docstring aside.
- [concern][impl] `copilot_hook_adapter.py:242,186-187` — in `--enforce` mode a
  `translate_payload` exception still forwards RAW bytes to the gate, which then
  can't read its snake_case fields and exits 0 (allow) — i.e. a malformed/
  untranslatable payload fails OPEN in the enforcing path. Defensible (a gate can't
  block on data it can't parse), but slightly inconsistent with the enforcing
  branch's otherwise fail-closed stance; note the deliberate choice.
- [nit][impl] `scaffold.py:2233` — `render_permissions_floor_hook` hardcodes the
  top-level key `"preToolUse"` instead of `cls.copilot_event_name("PreToolUse")`
  used by `render_copilot_hook_file`; a tiny drift seam if `CLAUDE_TO_COPILOT_EVENTS`
  ever changes (value is test-pinned, so low risk).
