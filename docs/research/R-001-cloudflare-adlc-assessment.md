---
status: CONCLUDED
topic: Cloudflare's Agent Development Lifecycle (ADLC) read against jig's own approach
created: 2026-09-22
related:
  - docs/decisions/adr-0062-convention-rule-severity-and-promotion.md
  - docs/decisions/adr-0063-agent-fix-evidence-separation.md
  - docs/specs/114-convention-rule-severity/spec.md
  - docs/specs/115-autonomy-readiness-checklist/spec.md
---

# R-001: Cloudflare's Agent Development Lifecycle, read against jig

> This is an **open investigation**, not a decision and not committed work.
> A decision belongs in an ADR (`docs/decisions/`); committed work belongs in
> a spec (`docs/specs/`). This note holds the question, sources, and
> pros/cons *before* either of those is warranted — see
> [ADR-0054](../decisions/adr-0054-research-notes-artifact-convention.md).

## Question

What does Cloudflare's "Agent Development Lifecycle" post
(`blog.cloudflare.com/agent-development-lifecycle/`, 2026-08-04) propose, how
does it line up with jig's spec-driven, gated-evidence approach, and which of
its ideas are worth adopting here?

## Sources / findings

**Provenance caveat.** The primary post and every syndicated copy were
unreachable from the authoring environment (egress-blocked). Findings below
are reconstructed from search snippets, the `cloudflare/ci` repository on
GitHub (README + `examples/self-healing`), and secondary coverage (InfoQ,
The New Stack, a note.com summary of the "seven conditions"). Treat quoted
structure as second-hand; verify against the post before citing it in a
record that depends on its exact wording.

**Thesis.** AI made "Implement" the fastest and cheapest SDLC stage; every
other stage is still sized for the old ratio. Move from software teams to
"software factories": agents run the lifecycle; engineers define policies,
inspect evidence, and control access to sensitive systems.

**Seven conditions** for handing a process to agents (as summarised by
coverage): API-operable; a preview per agent; reproducible; event-triggered;
handles changes independently; can escalate privileges when needed; learns
from experience.

**Five primitives shipped under it:**
- `@cloudflare/ci` — CI as TypeScript Workflow steps; a self-healing example
  where an application-owned agent receives neutral runner-failure
  diagnostics, pushes a *verified* fix to `ci-autofix/<run-id>`, and **the
  source run still fails** (`CiRunFailedWithFix`) "because its original
  revision remains broken"; a human merges.
- OpenTelemetry tracing in local dev plus an **Agents observability**
  dashboard: sessions, model calls, tools, subagents, tokens, cost.
- The **Cloudflare Codex**: a governed standards body as structured RFCs with
  MUST/SHOULD keywords, explicit ownership, and lifecycle states; a rule starts
  as a non-blocking recommendation and must be explicitly promoted to
  "enforced" before an unmet MUST withholds approval. Three consuming agents
  (CI code reviewer, spec reviewer, incident-report reviewer). Reported
  scale: ~230,000 deviations surfaced, ~16,000 approvals withheld since the
  start of 2026 — reporting dominates blocking.
- The **Astro issue factory**: reproduce → diagnose → verify → fix, one agent
  per stage, state machine encoded in GitHub labels, the *reporter* confirms
  the patch before a PR opens; open issues from ~200 to ~30. Engine open-sourced
  as Flue.
- The **Agent Access Model**: isolation and expiring credentials; prompt-level
  boundaries do not hold at machine speed.

**Where jig already lines up (verified against the corpus 2026-09-22):**
- "Engineers inspect evidence" = the C1–C7 gated-evidence spine and the
  review-evidence gate (ADR-0014).
- The Astro pipeline is nearly isomorphic to `bug-fix`'s
  REPORTED → DIAGNOSING → ROOT_CAUSED → FIXING with the diagnose-before-fix
  gate and the witnessed red→green test as "verify"; jig also has a VERIFIED
  state for the reporter-confirms step.
- The Agent Access Model is ADR-0051's two-principal, capability-keyed
  identity separation, stated as a platform feature.
- "Learns from experience" is the memory layer (spec 002).
- Per-subagent cost is **already** in `scripts/usage.py` (per-spec totals
  broken down by subagent type); what Cloudflare adds is a per-session trace
  of individual model/tool calls, which spec 041's skill trace partly covers.

## Options / pros & cons

Ranked by fit with jig's stated posture (thin scaffold, files a dev can own,
fold lenses into existing passes per ADR-0055, no autonomy primitive in jig's
own always-on flow per ADR-0022/0060):

1. **Rule severity + promotion lifecycle** (MUST/SHOULD; advisory → enforced by
   explicit act). Pros: ADR-0011's deliberateness per rule; supplies the
   missing denominator the spec 078 refinement-todo entry wants; adding a rule
   stops being an implicit blocker. Cons: owner-approved migration of
   `conventions.md`; prompt-size cost. → **Promoted to ADR-0062 / spec 114.**
2. **"Original run still fails" invariant for agent fixes.** Pros: small,
   statable, keeps the failure record and the fix as separate artifacts; the
   home for "never skip a test to get green". Cons: more refs; legitimate test
   corrections need an owner path. → **Promoted to ADR-0063 / spec 115-02.**
3. **Seven conditions as an autonomy-readiness checklist.** Pros: cheap,
   doc-level; jig already ships one precondition (`governance.py
   identity-check`) and can mark its coverage honestly. Cons: a checklist
   nobody runs is decoration. → **Promoted to spec 115-01.**
4. **Event-triggered bug intake + sandbox reproduce.** This is `bug-fix` run
   unattended from a GitHub issue — the servo half of the long-horizon bridge
   (servo specs 023/024/025), not jig's. → **Inbox pointer, routed to servo.**
5. **Filter rules to context** (structured rule registry, load only relevant
   rules). Same instinct as spec 055; premature at ~20 rules. → **Refinement-todo
   entry with a measured trigger** (Option C of ADR-0062).
6. **Per-session, per-call traces.** Mostly covered by `usage.py` +
   spec 041; not adopted absent measured pain.

**Not adopted:** the "replace the SDLC" / factory framing (jig is a thin,
host-neutral, file-owned scaffold; a Workflows-bound runtime is out of scope);
chasing Cloudflare's scale metrics; any standalone conventions gate (ADR-0055).

## Open questions

- Verify the seven-conditions wording against the primary post once
  reachable; the checklist in spec 115-01 should quote it, not the summary.
- Whether Flue's label-encoded state machine has anything jig's bug board
  lacks for *external* visibility (labels are readable by non-jig tooling;
  jig's states live in frontmatter).

## Conclusion

The post is jig's lifecycle with a runtime attached. Two ideas are worth a
decision record (rule severity/promotion; agent-fix evidence separation), one
is a cheap doc addition (readiness checklist), one routes to servo, one is
parked with a trigger, one is already covered.

Promoted to: [ADR-0062](../decisions/adr-0062-convention-rule-severity-and-promotion.md),
[ADR-0063](../decisions/adr-0063-agent-fix-evidence-separation.md),
[spec 114](../specs/114-convention-rule-severity/spec.md),
[spec 115](../specs/115-autonomy-readiness-checklist/spec.md), the
refinement-todo entry "context-filtered convention rules for reviewer prompts",
and the inbox entry `autonomy/event-triggered-bug-intake` (2026-09-22).
