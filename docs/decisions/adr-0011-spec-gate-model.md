---
dependencies: []
last_verified: 2026-05-29
---

# ADR-0011: Spec-gate model — deliberateness signal, not human-only approval

## Status

Accepted (2026-05-29)

## Context

`hooks/scripts/jig-spec-gate.sh` blocks `Edit`/`Write`/`MultiEdit` to
`docs/conventions.md` unless `JIG_CONVENTIONS_APPROVED=1` is set in the
environment (PreToolUse, exit 2 to block). The docstring at line 7 states:

> Changes should be a deliberate, human-approved act — not something an
> agent does as a side effect of unrelated work.

The block message (line 36) similarly says changes "require human approval."

**The framing overstates what the hook enforces.** The agent has the Bash
tool. An agent that decides to edit `conventions.md` can satisfy the gate
itself in a single call —
`JIG_CONVENTIONS_APPROVED=1 <command-that-edits>`, or an `export` followed
by the edit. Nothing in the hook distinguishes a human who set the variable
from an agent who set it. The gate therefore does **not** enforce *human*
approval; it enforces *deliberateness* — the actor (whoever it is) had to
form explicit intent to set the flag.

That distinction matters because it changes what problem the hook actually
solves. Mapping the three threats:

- **(i) Unauthorized changes** (an actor who shouldn't be editing the rules
  does so anyway). The env var addresses this **poorly** — any actor with a
  shell sets it.
- **(ii) Accidental changes** (`conventions.md` edited as a side effect of
  unrelated work). The env var addresses this **well** — an agent doing
  something else won't have the flag set, so the stray edit is blocked. This
  is the realistic, common failure the hook genuinely prevents.
- **(iii) True human-only enforcement.** **Impossible for any in-process
  hook.** A hook runs inside the same trust boundary as the agent it gates;
  any gate the agent can read, the agent can satisfy. Real human-only
  enforcement requires an *out-of-band* channel — a CI check on the PR,
  `CODEOWNERS` on `docs/conventions.md`, or branch protection — none of
  which a hook can substitute for.

So the honest description is: the gate is a **deliberateness speed-bump that
catches accidental edits (ii)**, not a human-approval gate. This is the same
framing-vs-enforcement gap that [spec 040](../specs/040-isolation-honesty/spec.md)
corrected for reviewer "isolation": claiming a hard guarantee the mechanism
doesn't provide.

A second design force points the same way. jig targets AI-native
development and should not bake in a hard human-in-the-loop assumption.
Unattended / eval-driven operation is a plausible mode for a jig-scaffolded
project. A *true* human-only gate would deadlock such a loop the moment a
legitimate `conventions.md` change is warranted — there is no human to ask.
A programmatically-satisfiable signal keeps that path open: the deliberate
actor (a human at a terminal, or an orchestrator that has decided a rule
change is warranted) sets the flag; an agent doing unrelated work does not.

It helps to see `conventions.md` in the context of jig's artifact tiers:

| Tier | Artifact | Mutability posture |
|---|---|---|
| **Constitution** | `docs/conventions.md` | Gated — a deliberate intent signal is required to edit |
| **Decisions** | ADRs | Append-only — *create* freely; accepted ones are immutable (ADR-0006 / ADR-0008) |
| **Work products** | specs, code | Freely modifiable |

The gate guards the constitution (tier 1). It is the only file jig
mechanically protects, and the protection is a *deliberateness* check, not a
permission system.

**Secondary concern — path specificity.** The hook matches
`docs/conventions.md` literally (lines 28–29). A project using
`CONVENTIONS.md` at the repository root, or any other naming, gets no gate.
The hook is implicitly jig-layout-specific, and that is not documented today.
Path resolution does use `os.path.realpath` (line 22) to defeat traversal
bypasses — that part of the gate is solid and is not in question here.

## Decision Options Considered

### Option A: Speed-bump model with honest framing

Keep the env-var mechanism unchanged. Correct the docstring, the block
message, the README, and `docs/workflow.md` to describe the hook as a
**deliberateness gate that catches accidental edits**, explicitly disclaim
human-only enforcement, and point at CI / `CODEOWNERS` / branch protection
as the real channel for teams that need to enforce (i)/(iii).

- **Pros:** Smallest change (docs only, no hook logic). Accurate to what the
  mechanism does. Keeps unattended operation viable (signal is
  programmatically satisfiable). No on-disk residue. Consistent with spec
  040's honesty stance.
- **Cons:** Does nothing to close the (i) unauthorized-change gap at the
  hook layer — that gap must be clearly documented as out-of-scope-for-hooks
  rather than papered over.

### Option B: File-marker model

Replace the env var with a short-lived `.jig/conventions-approval-token`
file carrying a recent mtime, created by a documented manual command
(e.g. `python3 scripts/approve_conventions.py`). The hook checks for the
marker's presence and freshness instead of the env var.

- **Pros:** The approval action is auditable on disk; marginally higher
  friction than `export`.
- **Cons:** Does **not** close the actual gap — an agent with Bash creates
  the file just as easily as it sets an env var, so it buys no real
  human-only enforcement. Adds a manual command and disk state that an
  unattended loop must garbage-collect. More moving parts (a script, a
  staleness window, a cleanup obligation) for no enforcement gain. False
  sophistication.

### Option C: Two-step token

The hook requires the env var **and** a file marker. Belt-and-suspenders
over A and B.

- **Pros:** Highest friction; signals "this is a serious edit."
- **Cons:** Still bypassable by any agent with Bash (it can do both steps).
  Largest change, most ceremony, no enforcement gain over A. Worst fit for
  unattended operation.

### Option D: Status quo, no change

Leave the misleading "human-approved" framing in place.

- **Pros:** Zero work.
- **Cons:** The framing keeps claiming a guarantee the mechanism doesn't
  provide. A reader trusts the gate as a security boundary and is wrong.
  Perpetuates exactly the honesty gap spec 040 was created to close.

## Recommended Decision

**Option A — keep the env-var mechanism; correct the framing to
"deliberateness gate, not human-only."**

Reasoning:

1. **B and C don't close the real gap.** The (i) unauthorized-change threat
   is uncloseable at the hook layer by construction — a gate inside the
   agent's trust boundary is satisfiable by the agent. A file marker and a
   two-step token both add friction and ceremony while leaving (i) exactly
   as open as Option A leaves it. They buy nothing on the axis that matters.
2. **The real enforcement channel is out-of-band.** Teams that genuinely
   need human-only control over `docs/conventions.md` should add a
   `CODEOWNERS` rule, a CI check on the PR diff, or branch protection. Those
   grade the *result* (the diff) regardless of who or what produced it, and
   they sit *outside* the agent's trust boundary. The ADR names this
   explicitly so the hook is never mistaken for a substitute.
3. **The env var is the right shape for a deliberateness signal.** A single
   deliberate actor sets it; an agent doing unrelated work doesn't have it,
   so accidental edits (the realistic threat) are blocked. It leaves no
   on-disk residue, and it keeps unattended/eval-driven operation viable
   because it is programmatically satisfiable by a deliberate orchestrator —
   a property a human-only gate would forfeit.
4. **Honesty.** The framing should describe what the mechanism does. This
   mirrors spec 040: stop claiming a hard guarantee the mechanism can't back.

The CLAUDE.md project rule "Do not modify `docs/conventions.md` without
explicit human approval" remains the **policy** for supervised work. The
hook is the deliberateness *backstop* for that policy (it blocks the
side-effect edit), not its enforcement. The policy is upheld by reviewers
and, where a team wants a mechanical guarantee, by the out-of-band channel
named above.

## Consequences

**Becomes easier:**

- The mental model is accurate. A reader of the hook, the README, or
  `docs/workflow.md` learns that the gate catches accidental edits and that
  real enforcement is a CI/`CODEOWNERS` concern — and is not misled into
  trusting it as a security boundary.
- Unattended operation stays possible: the signal is programmatically
  satisfiable by a deliberate actor, so a future loop is not deadlocked by a
  human-only gate it can't pass.
- Teams that want hard control over the constitution have a documented,
  correct recipe (`CODEOWNERS` / CI / branch protection) instead of
  over-trusting the hook.

**Becomes harder:**

- Nothing closes the (i) unauthorized-change gap *at the hook layer* — and
  that must be stated plainly so no one mistakes the hook for what it isn't.
  The mitigation is documentation, not mechanism.

**Implementation status (slice 042-01):**

- Docs-only alignment. Edit the `hooks/scripts/jig-spec-gate.sh` docstring
  and the block message to say "deliberate approval" / name the out-of-band
  channel, drop "human-approved" as a guarantee.
- Align the corresponding prose in `docs/workflow.md`. (`README` carries no
  conventions-gate prose, so there is nothing to align there.)
- Add a one-line note that the gate is jig-layout-specific (matches
  `docs/conventions.md` only) — see Scope.
- No hook *logic* change; the env-var check and the `realpath` traversal
  defense stay exactly as they are. No new tests are required for a
  logic-preserving change, though the existing gate tests must stay green.

## Scope

**Path specificity (spec 042 Q2):** the gate stays **jig-layout-specific**.
It continues to match `docs/conventions.md` literally. Slice 042-01 documents
this layout-specificity so downstream / migrate-mode adopters with a
differently-named constitution aren't surprised by silent no-op gating.

A configurable gated set (`JIG_GATED_FILES`, or a per-project constitution
pointer) is named here as a **deferred enhancement** with no slice reserved.
Resolution trigger: a real downstream project with a differently-named
constitution file (e.g. root `CONVENTIONS.md`) asks for the gate to cover it.
Until that surfaces, the literal match is acceptable and the path-flexibility
work stays unbuilt.

**Out of scope:** removing the hook; expanding the gate to files beyond the
constitution; any "always-allow" sudo mode (these are spec 042 non-goals).

## Relationship to other decisions

- **[ADR-0008](./adr-0008-closed-spec-drift-policy.md) (closed-spec drift
  policy).** ADR-0008 anticipated this ADR: "if 042 picks a stricter
  immutability gate on `docs/conventions.md` edits, this ADR is the more
  general rule and 042's gate becomes one specific case." We did **not** pick
  a stricter gate — Option A keeps the deliberateness model. So there is no
  conflict to resolve. Note also that `docs/conventions.md` is not a "closed
  spec," so ADR-0008's `## Amendments` rule does not govern it; the
  deliberateness gate plus the CLAUDE.md policy do.
- **[ADR-0006](./adr-0006-adr-accept-then-index-ordering.md) / Nygard
  immutability.** Governs ADRs (tier 2 above). This ADR does not change ADR
  rules; it only addresses the constitution tier.
- **[Spec 040](../specs/040-isolation-honesty/spec.md) (isolation honesty).**
  Same framing-vs-enforcement theme. Landing both compounds the trust
  improvement: claims about what jig's mechanisms guarantee should match what
  they enforce.
- **[Spec 041](../specs/041-routing-observability/spec.md) (routing
  observability).** Light coupling. Whether the gate catches edits in
  practice (spec 042 Q1) becomes answerable if gate trips can be logged
  through the telemetry hook. Deferred to 041; not a blocker for this ADR.

## Open questions

- **Is the gate catching accidental edits in practice, or is it deadweight?**
  Unanswerable without telemetry today. Pairs with spec 041 — if the trace
  logs gate trips, this becomes measurable. Not blocking: the gate is cheap
  and the (ii) failure it prevents is real regardless of frequency.
