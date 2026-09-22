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

What does Cloudflare's "The Agent Development Lifecycle has arrived on
Cloudflare" post (`blog.cloudflare.com/agent-development-lifecycle/`,
2026-08-04) propose, how does it line up with jig's spec-driven,
gated-evidence approach, and which of its ideas are worth adopting here?

## Sources / findings

**Provenance.** The primary post was egress-blocked from the authoring
environment; a first draft of this note was reconstructed from search
snippets and coverage. The owner then supplied the post's full text
(2026-09-22) and this note was corrected against it. The mechanics of
`@cloudflare/ci`'s self-healing example were read directly from the
`cloudflare/ci` repository on GitHub (README + `examples/self-healing`).
**Still second-hand:** the five *sibling* posts the ADLC post links (the
engineering-standards "Codex" post, the Astro issue-factory post, and the
observability/tracing posts) — their figures below come from InfoQ / The New
Stack coverage and should be re-checked before any record depends on their
exact wording. The "Agent Access Model" is a *separate* Cloudflare post and is
not part of the ADLC post; it is noted below only because coverage bundled it.

**Thesis (verified).** The SDLC (RAND 1975: Plan, Design, Implement, Test,
Deploy, Maintain, Retire) was sized for implementation being the slowest,
most expensive step. "AI has made the step that was previously the slowest
and most expensive — implementation — the fastest and cheapest," which
overwhelms everyone downstream (maintainers "bombarded with thousands of pull
requests and issues," production engineers). "The answer — paradoxically — is
to empower agents to do more": today most teams still have a human manage
each SDLC step and delegate *within* it, so the proposal is the ADLC, "for
software factories" — "agent-driven systems that take input and autonomously
build, improve, deploy and manage software." The stated human role is not
policy-and-evidence (that phrasing came from coverage, not the post) but
"the things that truly require human inspiration, taste, and judgement."

**The seven properties every formerly-manual step must have** when "you hand
over the keys" (verified, the post's own names):

1. **Programmatic** — "every last operation needs APIs that agents can call,
   debug, and rely on"; ClickOps is a non-starter.
2. **Horizontally scalable** — "every agent must have its own preview that
   matches production."
3. **Reproducible** — environment reproduction (a bug only on "4G on an
   iPhone 15," or "from an IP in a certain country"), beyond unit/integration
   tests.
4. **Real-time, push based** — "You need an event that triggers an agent to
   do work," not a human watching a dashboard.
5. **Atomic** — "every change needs to be independently testable,
   releasable, observable, and reversible without affecting unrelated
   behavior."
6. **Permissioned** — no standing SSH-to-prod for an agent, but "without the
   ability to escalate and get more permissions, how can it do its job?"
7. **Self-improving** — "Agents, too, need ways to learn from experience."

**The bar (verified).** The self-driving analogy: 80%-as-good was reached
years ago; the bar is "some number of nines past 99%," which needs
purpose-built instrumentation, not a car designed for humans. The post's own
test: "why haven't you yet just let your agent auto-approve and merge its own
PRs to your production services? The higher the stakes … the longer your list
of reasons almost surely is."

**Orchestration (verified).** "A CI/CD pipeline is just a Workflow. But a
Workflow can be so much more than a CI/CD pipeline." The unit is a durable
Workflow that can spawn containers, agents, and browsers; set feature flags;
watch a gradual rollout; and dispatch to a Flue agent and read back a receipt
(`agent.dispatch` → `agent.read`). Pipelines are TypeScript, not YAML.

**Five launches under the umbrella (verified list; details second-hand):**
- `@cloudflare/ci` — CI/CD as Workflows "that can self-heal and spawn
  agents." From the repo: an application-owned healing agent receives neutral
  runner-failure diagnostics, pushes a *verified* fix to
  `ci-autofix/<run-id>`, and **the source run still fails**
  (`CiRunFailedWithFix`) "because its original revision remains broken"; a
  human merges.
- OpenTelemetry traces in local dev (Wrangler / Vite plugin).
- Cloudflare Agents + Agent Traces: sessions, model calls, tools, subagents,
  tokens, cost.
- Engineering-standards enforcement (sibling post; per InfoQ): a governed
  "Codex" of standards as structured RFC items with MUST/SHOULD keywords and
  lifecycle states; a rule starts as a non-blocking recommendation and must be
  *explicitly promoted* to "enforced" before an unmet MUST withholds approval;
  three consuming agents (CI code reviewer, spec reviewer, incident-report
  reviewer); ~230,000 deviations surfaced, ~16,000 approvals withheld since
  the start of 2026.
- Astro issue factory (sibling post; per InfoQ / The New Stack): reproduce →
  diagnose → verify → fix, one agent per stage, state machine encoded in
  GitHub labels, the *reporter* confirms the patch before a PR opens; open
  issues from ~200 to ~30; engine open-sourced as Flue.

**The ADLC stage table (verified, and the most useful single finding).** The
post maps its stack onto the seven SDLC stages. Implement, Test, Deploy, and
Maintain/Retire each list products. **Plan and Design are blank.** The
software-factory stack starts at Implement; the phase where intent is
specified, split, decided, and reviewed is not addressed. That is precisely
jig's territory (specs, SPIDR slices, ADRs, the review passes, the memory
layer), so the relationship is complementary rather than competing.

**Where jig already lines up (verified against the corpus 2026-09-22):**
- **Atomic** is the vertical slice: independently testable (ACs +
  red→green), releasable (`slice-land`), observable (review-evidence
  artifacts, ADR-0014), reversible (one slice, one landing).
- **Self-improving** is the memory layer (spec 002), learnings, lightweight
  decisions, and the ADR corpus.
- **Permissioned** is half-covered: ADR-0051's identity/capability separation
  and ADR-0060's write boundary say what an agent must *not* hold; the
  *escalation* path is not built.
- The Astro pipeline is nearly isomorphic to `bug-fix`'s
  REPORTED → DIAGNOSING → ROOT_CAUSED → FIXING with the diagnose-before-fix
  gate and the witnessed red→green test as "verify"; jig also has VERIFIED
  for the reporter-confirms step.
- "Why haven't you let your agent auto-approve and merge its own PRs" is
  ADR-0051's identity-separation argument stated from the other side.
- Per-subagent cost is **already** in `scripts/usage.py` (per-spec totals by
  subagent type); spec 041's skill trace covers part of the per-session
  picture.
- **Not jig's:** Programmatic-as-HTTP-API (jig's helpers are CLIs; that is
  API-operable for an in-repo executor, not a service), Horizontally scalable
  previews, Reproducible environments, and Real-time push-based triggers are
  all *executor* properties (servo, or an ADR-0060 orchestrator). jig's hooks
  are in-session events, not repo-level triggers.

## Options / pros & cons

Ranked by fit with jig's stated posture (thin scaffold, files a dev can own,
fold lenses into existing passes per ADR-0055, no autonomy primitive in jig's
own always-on flow per ADR-0022/0060):

1. **Rule severity + promotion lifecycle** (MUST/SHOULD; advisory → enforced by
   explicit act; from the standards sibling post). Pros: ADR-0011's
   deliberateness per rule; supplies the missing denominator the spec 078
   refinement-todo entry wants; adding a rule stops being an implicit blocker.
   Cons: owner-approved migration of `conventions.md`; prompt-size cost.
   → **Promoted to ADR-0062 / spec 114.**
2. **"Original run still fails" invariant for agent fixes** (from the
   `cloudflare/ci` example, backed by the post's own auto-merge test). Pros:
   small, statable, keeps the failure record and the fix as separate
   artifacts; the home for "never skip a test to get green". Cons: more refs;
   legitimate test corrections need an owner path.
   → **Promoted to ADR-0063 / spec 115-02.**
3. **Seven properties as an autonomy-readiness checklist.** Pros: cheap,
   doc-level; jig already ships one precondition (`governance.py
   identity-check`) and can mark its coverage honestly (Atomic and
   Self-improving covered, Permissioned partial, the other four the
   executor's). Cons: a checklist nobody runs is decoration.
   → **Promoted to spec 115-01.**
4. **Event-triggered bug intake + sandbox reproduce** (Real-time push-based +
   Reproducible applied to `bug-fix`). This is the servo half of the
   long-horizon bridge (servo specs 023/024/025), not jig's.
   → **Inbox pointer, routed to servo.**
5. **Filter rules to context** (structured rule registry, load only relevant
   rules). Same instinct as spec 055; premature at ~20 rules.
   → **Refinement-todo entry with a measured trigger** (Option C of ADR-0062).
6. **Per-session, per-call traces.** Mostly covered by `usage.py` +
   spec 041; not adopted absent measured pain.

**Not adopted:** the "replace the SDLC" / factory framing (jig is a thin,
host-neutral, file-owned scaffold; a Workflows-bound runtime is out of scope);
chasing Cloudflare's scale metrics; any standalone conventions gate (ADR-0055).

## Open questions

- Read the standards-enforcement and Astro sibling posts directly before any
  record quotes their figures; ADR-0062's Context leans on the Codex
  promotion-state description, which is InfoQ's rendering of it.
- Whether Flue's label-encoded state machine has anything jig's bug board
  lacks for *external* visibility (labels are readable by non-jig tooling;
  jig's states live in frontmatter).
- Positioning: the blank Plan/Design rows are an argument jig's product-vision
  could make explicitly ("the ADLC starts at Implement; jig is the half before
  it"). Not filed — a positioning change wants an owner decision.

## Conclusion

The post is jig's lifecycle with a runtime attached, and its own stage table
leaves the Plan/Design half — jig's half — blank. Two ideas are worth a
decision record (rule severity/promotion; agent-fix evidence separation), one
is a cheap doc addition (readiness checklist), one routes to servo, one is
parked with a trigger, one is already covered.

Promoted to: [ADR-0062](../decisions/adr-0062-convention-rule-severity-and-promotion.md),
[ADR-0063](../decisions/adr-0063-agent-fix-evidence-separation.md),
[spec 114](../specs/114-convention-rule-severity/spec.md),
[spec 115](../specs/115-autonomy-readiness-checklist/spec.md), the
refinement-todo entry "context-filtered convention rules for reviewer prompts",
and the inbox entry `autonomy/event-triggered-bug-intake` (2026-09-22).
