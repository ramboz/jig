---
slice: 096-04 — codex-orchestrator-visibility
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (frame-critique pass)
reviewed_at: 2026-07-28T02:09:38Z
prompt_source: review.py frame-critique
---

Frame-critique of 096-04 returned **needs-changes**.

**Primary.** The spike treats host-injected skill metadata as a *capability
gate* on Codex zero-config selection ("the one unverified premise the
zero-config path rests on"). That is asserted, never argued. The design already
retains Option C's enumeration layer, and jig can enumerate Codex skills from
`$HOME/.agents/skills` (VERIFIED, spec.md:66-70) and simply *print* the
candidate set: `enumerate → print name+description → orchestrator picks from the
text it was just shown → --richer-skill <name>`. That needs no router and no
hidden-prompt injection. ADR-0039's own justification for leaning on host
injection is a **cost** argument — "costs ~nothing in orchestrator context …
since the descriptions are already loaded" (`adr-0039:159-161`) — so a cost
optimization has been promoted to a capability gate. ADR-0039's calibration
requirement (fire the anomaly only against the set the orchestrator was actually
shown) means jig must show an explicit candidate set on both hosts anyway, which
makes host-injected visibility redundant rather than load-bearing.

Damage on the FAIL branch: AC4 mandates writing "Codex is config-only" into an
Accepted ADR and explicitly *not* reserving 096-06 — a decision-grade wrong
negative that forecloses a buildable path. The ripple is already upstream:
`slice-03:29-32` fences Codex out of 096-03 on the strength of this unexamined
gate. The question worth 4 hours is jig-side, not OpenAI-side: can the Codex
orchestrator running jig's own surface reliably execute the select-and-pass step
and get `--richer-skill` through? Testable with jig's prose today.

**Secondary.** The time-box permits `abandoned (inconclusive)` but AC3 demands
the assumption be updated to "VERIFIED or REFUTED … no assumption left
dangling" — pressuring the implementer to launder a weak negative into REFUTED,
the exact conversion that triggers the primary damage. Add an explicit
`INCONCLUSIVE (probed, time-boxed)` state or drop the FAIL → "config-only
confirmed" mapping.

**Secondary.** AC1 mandates the weaker instrument: a *behavioral* probe whose
negative is confounded by prompt shape, model reticence, and
non-interactive-vs-interactive context assembly, with no positive/negative
control — a null is indistinguishable from a mis-registered fixture. The DoR's
own prior art has the direct instrument: `scripts/codex_agent_discovery_probe.py`
inspects the assembled prompt JSON via `codex debug prompt-input` (a fact, not a
behavior). Require context inspection as ground truth, behavioral run as
confirmation. Note `scripts/codex_role_capability_probe.py:7` already records
that the debug surface under-reports, so a null from either surface must not be
read as absence.
