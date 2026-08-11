---
adr: 0054
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (fresh-context, Opus)
reviewed_at: 2026-08-11T18:15:55Z
prompt_source: review.py frame-critique docs/decisions/adr-0054-research-notes-artifact-convention.md
---

Frame-critique of ADR-0054 (research notes as a lightweight standalone-investigation artifact). Adversarial pass per ADR-0020; fresh-context `jig:reviewer` subagents (Opus — equal-or-stronger than the Opus author). Ran across three rounds against successive revisions.

## Verdict: pass

The frame survives the strongest attack: the ADR no longer overclaims the phase distinction, and stakes only a cheap, reversible, disclosed bet with a genuine retirement test keyed on the exact collapse-to-A′ failure mode.

## How the frame hardened (round-by-round)

- **Round 1 — needs-changes.** Caught the load-bearing weakness: the demand count was inflated. Three of four cited "thick inbox entries" (positioning map, "jobs", design-conformance) already carry a named decision + resolution trigger, making them `refinement-todo`-shaped, not homeless; and `refinement-todo.md` already holds thick multi-paragraph entries. The ADR had not ruled out the nearest alternative (route thick investigations into `refinement-todo`).
  - Fix: added **Option A′** (rule out `refinement-todo` directly, on charter-mismatch grounds), recast the load-bearing frame as a **phase/altitude distinction** (open investigation with no decision named yet, vs. named deferred decision + trigger — sequential, not competing), and recounted honestly.

- **Round 2 — needs-changes (explicitly "not a fail").** Caught residual motivated reasoning: claim (i) — "the trigger was accreted at the end, evidence of a missing open-phase home" — is an unfalsifiable narrative presented as conceded evidence, propping up the "act now" decision. Also: the distinctness kill-criterion tested only birth-state, leaving a "born-open but crystallizes instantly = zero distinct-phase value" hole.
  - Fix: **demoted claim (i) to an explicitly-labeled hypothesis, NOT counted as evidence**; re-grounded "act now" on the two honest data points (existing frozen seed corpus, n=1 genesis; external #196, n=1) plus near-zero reversible cost + tripwire; conceded recurring internal open-phase demand is ≈ n=0–1 and unproven; **strengthened the kill criterion to test persistence** (born open AND stayed open across a non-trivial window), self-labeled as a mitigation not a proof.

- **Round 3 — pass.** All three fixes applied faithfully; both primary and secondary findings resolved.

## Reconciliation notes to carry forward (from the passing reviewer)

1. **Deviation-log requirement (baked into the ADR body):** if this ADR proceeds, the deviation log must record that "act now" is justified by external ask (#196) + frozen seed corpus + low reversible cost, and explicitly **not** by demonstrated recurring internal open-phase demand. Carry verbatim into the spec's deviation log.
2. **Residual (disclosed, not blocking):** both kill-criterion conditions are self-judged by a party invested in the convention, and the "stayed open across a non-trivial window" threshold is informal ("multiple sessions / days"). Honestly flagged as a mitigation, not a proof — watch that the distinctness test is actually run against a real sample rather than assumed to pass.
3. **Un-probed assumption stands:** no broader in-repo sweep was run for a competing living-research home beyond `docs/research/` and `docs/design/`. Honestly disclosed; carry forward.
