---
adr: 0061
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-15T20:37:40Z
prompt_source: review.py frame-critique docs/decisions/adr-0061-copilot-third-host.md
---

Adversarial frame-critique of ADR-0061 (GitHub Copilot CLI as a third committed
host). Reviewer: independent `jig:reviewer` subagent, read-only, no access to the
authoring conversation. Two rounds.

## Round 1 — needs-changes

The reviewer found two load-bearing exposures:

1. **Survival/parity conflation.** The ADR let the 2026-09-28 cutover justify the
   maximal Option-C build without proving it survival-necessary — while its own
   grounding concedes Copilot reads `.claude/`/`CLAUDE.md`/`.mcp.json` directly and
   installs Claude-format plugins via `/plugin`, and the only *hard* failures
   probed were 2 over-long skill descriptions + the unverified `:`-namespace. A
   minimal Option-A lifeboat looked ~1–2 days; the ADR neither named it nor
   justified rejecting it on non-deadline grounds.
2. **Seam-fit asserted, not grounded.** "The render layer absorbs the hook-schema
   translation" was unproven: the real seam `translate_hook_protocol`
   (`scaffold.py:1076`) is a single Claude-shaped `logical_result -> dict`
   mapping, and `CodexScaffoldRenderer` inherits it unchanged (Codex is a Claude
   near-clone). The seam has never faced a host with a genuinely different hook
   model (14 camelCase events, per-event-differing payload/response schemas).

## Resolution

Owner scope decision: **ignore the deadline; the goal is full Claude<->Copilot
parity.** This dissolves finding 1 as a stated product decision rather than an
ungrounded premise. The ADR + spec were revised (commit fb20c1f + coherence
follow-ups):

- Parity is the explicit bar; cutover demoted to motivation-only and not
  load-bearing; Option A rejected on parity grounds (degraded gates, empty native
  homes), not held as a deadline hedge; "Deadline-aware sequencing" -> "Slice
  ordering" (ordinary vertical slicing); deadline reversal is explicitly *not* a
  kill.
- Finding 2 folded in: the seam-fit is now an explicit unverified Assumption +
  Open question in the ADR, and spike 113-01 gained AC5 (inspect the `scaffold.py`
  seam, map Copilot's verified hook schema onto it, record any minimal reshaping
  as the 113-02 entry condition), Question (2), and a 1->1–2d time-box bump.

## Round 2 — pass

The reviewer re-read the revised artifacts and confirmed both findings resolved
and the reframe internally coherent, with no new load-bearing wrong premise (it
checked whether "full parity" is itself unachievable given Copilot lacks some
Claude events — and found the mapped-or-explicitly-unmappable invariant, the
gate-mapping kill criterion, and spike AC3 already handle that residual honestly).

VERDICT: pass.

Two **non-blocking** notes, both incorporated before acceptance:
- Softened the absolutist "full parity ... not a degraded subset" wording to
  "maximal expressible parity with an honest, visible residual" (consistent with
  L62 + the mapped-or-unmappable invariant).
- Made the Consequences `.github/` cloud-agent/code-review benefit conditional on
  the committed-layout-adopted-into-a-repo delivery path (vs. session-loaded
  `/plugin`), a routed spike-113-01 question rather than a settled fact.
