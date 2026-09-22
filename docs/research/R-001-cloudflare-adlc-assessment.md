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
2026-08-04) and its two practice-report siblings propose, how do they line up
with jig's spec-driven, gated-evidence approach, and which ideas are worth
adopting here?

## Sources / findings

**Provenance.** The posts were egress-blocked from the authoring
environment; a first draft of this note was reconstructed from search
snippets and coverage. The owner then supplied the full text of three posts
(2026-09-22) and this note was corrected against them: the ADLC post, "How
Cloudflare enforces engineering standards using AI", and "How we built a
software factory to drive Astro's GitHub issue count to zero". The
`@cloudflare/ci` self-healing mechanics were read directly from the
`cloudflare/ci` repository on GitHub (README + `examples/self-healing`).
**Still second-hand:** the tracing/observability sibling posts (nothing filed
depends on them). The "Agent Access Model" is a *separate* Cloudflare post
and is not part of the ADLC post.

### The ADLC post (verified)

**Thesis.** The SDLC (RAND 1975: Plan, Design, Implement, Test, Deploy,
Maintain, Retire) was sized for implementation being the slowest, most
expensive step. "AI has made the step that was previously the slowest and
most expensive — implementation — the fastest and cheapest," which overwhelms
everyone downstream (maintainers "bombarded with thousands of pull requests
and issues," production engineers). "The answer — paradoxically — is to
empower agents to do more": today most teams still have a human manage each
SDLC step and delegate *within* it, so the proposal is the ADLC, "for
software factories" — "agent-driven systems that take input and autonomously
build, improve, deploy and manage software." The stated human role is "the
things that truly require human inspiration, taste, and judgement."

**The seven properties every formerly-manual step must have** when "you hand
over the keys" (the post's own names):

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

**The bar.** The self-driving analogy: 80%-as-good was reached years ago; the
bar is "some number of nines past 99%," which needs purpose-built
instrumentation. The post's own test: "why haven't you yet just let your
agent auto-approve and merge its own PRs to your production services? The
higher the stakes … the longer your list of reasons almost surely is."

**Orchestration.** "A CI/CD pipeline is just a Workflow. But a Workflow can
be so much more than a CI/CD pipeline." The unit is a durable Workflow that
can spawn containers, agents, and browsers; set feature flags; watch a
gradual rollout; and dispatch to a Flue agent and read back a receipt.
Pipelines are TypeScript, not YAML. From the `cloudflare/ci` repo: the
self-healing example's application-owned agent receives neutral
runner-failure diagnostics, pushes a *verified* fix to `ci-autofix/<run-id>`,
and **the source run still fails** (`CiRunFailedWithFix`) "because its
original revision remains broken"; a human merges.

**The ADLC stage table (the most useful single finding).** The post maps its
stack onto the seven SDLC stages. Implement, Test, Deploy, and
Maintain/Retire each list products. **Plan and Design are blank.** The
software-factory stack starts at Implement; the phase where intent is
specified, split, decided, and reviewed is not addressed. That is precisely
jig's territory (specs, SPIDR slices, ADRs, the review passes, the memory
layer), so the relationship is complementary rather than competing.

### The standards-enforcement post (verified)

- **The Codex** is a governed body of engineering standards "built for
  people and agents," split into domains (architectural, cross-cutting,
  per-language), each with an owner responsible for content and quality.
  60+ RFCs and counting.
- **Shape.** Each standard is an RFC with RFC 2119 SHOULD/MUST keywords and a
  front-matter header (domain, status). Proposed by merge request, several
  rounds of widening review, domain-owner final approval, then published.
- **Lifecycle, exactly as ADR-0062 assumes.** "Approved RFCs can be consumed
  by Codex clients and agents, which may then start to flag Codex violations
  … immediately. However, they block based on Codex statements only after an
  RFC moves from the approved to the enforced lifecycle state. This separate
  promotion step gives teams time to absorb new requirements and
  accommodates cases where enforcement needs additional work."
- **Derived, filterable index.** Feeding 60+ RFCs whole "would put a lot of
  stress on the context window," so a purpose-built agent *extracts* the
  SHOULD/MUST statements from the prose into JSON (per statement: a **stable
  slug** that survives RFC edits, section path, level, text, href) "enrich[ed]
  with metadata that supports lazy discovery and progressive disclosure."
  Direction is prose → index, never the reverse. They started with a
  condensed Markdown file and moved to JSON so agents could filter more
  accurately; planned next: SDLC-stage metadata (design, implementation,
  runtime) per statement. The stable id "is essential for monitoring,
  analysis, and exception handling."
- **Consumers.** (a) The AI code reviewer loads statements, pulls full RFC
  bodies only when needed; "findings from approved RFCs are non-blocking
  recommendations. Once an RFC is enforced, an unsatisfied MUST requirement
  causes the reviewer to withhold approval or block a merge request,
  depending on the severity." Nearly 230,000 violations flagged since
  inception, almost 16,000 withholding approval (MUST on enforced RFCs).
  (b) The **spec reviewer** *filters the Codex by domains and sections
  relevant to specs* before reviewing — a by-artifact-type subset — and rates
  findings by SHOULD/MUST; ~600 specs, 3,200+ runs, 65% major / 29% minor /
  6% critical. (c) The incident-report reviewer; mandatory for high-severity
  incidents, "reports are not considered complete until all findings have
  been addressed."
- **Mechanical rules go to linters.** For requirements "that can be verified
  mechanically," Codex-aligned linter configs (oxlint for TypeScript first)
  surface problems in milliseconds; a local CLI runs the same reviewer
  without the CI round trip.
- **Stated future.** Agents "identify issues as well as propose fixes with
  increasing autonomy, while engineers remain responsible for reviewing and
  approving those changes."

### The Astro issue-factory post (verified)

- **Four stages, one isolated subagent each,** passing a `report.md`
  forward: **Reproduce** (clone the reporter's reproduction), **Diagnose**
  (instrument, add logging, find root cause), **Verify** ("determine if the
  behavior is genuinely a bug or intended functionality" from tests,
  comments, docs), **Fix** ("convert the reproduction into failing unit
  tests, identify the appropriate solution via the architecture guide, and
  deploy the fix"). Isolation exists "to prevent the frequent LLM bias toward
  forcing a solution when a bug might not actually exist."
- **Reporter confirmation is a separate, later step.** On a fix the pipeline
  publishes a preview release (pkg.pr.new), posts summary + full logs +
  install instructions to the issue; "the original reporter can then try the
  patch against their own project, and if they confirm it works, the
  automation opens a pull request linked to the issue." A maintainer still
  merges. Two human checkpoints, neither of them the agent.
- **State machine in labels** (`triage needed` → … → `fix verified`); "beyond
  those label transitions the pipeline holds no state of its own; it simply
  reads back through the issue's existing comments." Runs inside GitHub
  Actions; started as a local agent skill and the *same skill* runs in CI.
- **Agent failure is a codebase signal.** When the agent cannot fix a bug,
  "we interpret that failure as an indicator of an underlying architectural
  or documentation issue": opaque abstractions, missing documentation,
  insufficient testing. Worked example: the bot kept re-editing one `if`
  condition and regressing; one descriptive comment on that statement and it
  stopped. "Every time we chase down one of these failures and add the
  missing comment, test, or clearer boundary, the bot gets noticeably better
  … and so does the next human."
- Results: open issues from 200+ to ~30, zero expected within a month, first
  time in 5+ years; engine generalized into Flue; the action decoupled into
  its own tested repo (`triagebot-action`).

### Where jig already lines up (verified against the corpus 2026-09-22)

- **Atomic** is the vertical slice: independently testable (ACs +
  red→green), releasable (`slice-land`), observable (review-evidence
  artifacts, ADR-0014), reversible (one slice, one landing).
- **Self-improving** is the memory layer (spec 002), learnings, lightweight
  decisions, and the ADR corpus.
- **Permissioned** is half-covered: ADR-0051's identity/capability separation
  and ADR-0060's write boundary say what an agent must *not* hold; the
  *escalation* path is not built.
- The Astro stages map onto `bug-fix` one-to-one: Reproduce/Diagnose →
  DIAGNOSING with the ≥2-hypotheses gate; **Verify** (genuine bug vs.
  intended) → bug-fix's routing rule that escalates a *missing behaviour* to
  a spec instead of grinding it through the bug gates; Fix's "convert the
  reproduction into failing unit tests" → the witnessed red→green regression
  test; the reporter-confirms step → jig's VERIFIED state; one isolated
  subagent per stage → design principle 3 (subagents defined by isolation)
  and the diagnose-before-fix gate's rationale.
- "Why haven't you let your agent auto-approve and merge its own PRs" is
  ADR-0051's identity-separation argument stated from the other side; the
  Astro flow's two human checkpoints (reporter, then maintainer) are the
  practice.
- The Codex's stable slug per statement is ADR-0062's `Id`; its prose → index
  extraction is what spec 114-01's parser does deterministically; its spec
  reviewer is a real instance of the "second consumer needs a by-artifact-type
  subset" trigger in the refinement-todo entry, though jig has no such
  consumer yet.
- "Mechanical rules go to linters" is jig's existing split (`spec_lint.py`,
  `validate_manifests.py`, `health.py`) and why ADR-0062 rejects a
  standalone conventions gate.
- Per-subagent cost is **already** in `scripts/usage.py`; spec 041's skill
  trace covers part of the per-session picture.
- **Not jig's:** Programmatic-as-HTTP-API (jig's helpers are CLIs),
  Horizontally scalable previews, Reproducible environments, and Real-time
  push-based triggers are *executor* properties (servo, or an ADR-0060
  orchestrator). jig's hooks are in-session events, not repo-level triggers.

## Options / pros & cons

Ranked by fit with jig's stated posture (thin scaffold, files a dev can own,
fold lenses into existing passes per ADR-0055, no autonomy primitive in jig's
own always-on flow per ADR-0022/0060):

1. **Rule severity + promotion lifecycle** (MUST/SHOULD; approved → enforced
   by explicit act; stable id per rule). Pros: ADR-0011's deliberateness per
   rule; supplies the missing denominator the spec 078 refinement-todo entry
   wants; adding a rule stops being an implicit blocker. Cons:
   owner-approved migration of `conventions.md`; prompt-size cost.
   → **Promoted to ADR-0062 / spec 114.**
2. **"Original run still fails" invariant for agent fixes** (from the
   `cloudflare/ci` example, the post's auto-merge test, and Astro's
   preview-then-reporter-then-PR flow). Pros: small, statable, keeps the
   failure record and the fix as separate artifacts; the home for "never skip
   a test to get green". Cons: more refs; legitimate test corrections need an
   owner path. → **Promoted to ADR-0063 / spec 115-02.**
3. **Seven properties as an autonomy-readiness checklist.** Pros: cheap,
   doc-level; jig can mark its coverage honestly (Atomic and Self-improving
   covered, Permissioned partial, the other four the executor's). Cons: a
   checklist nobody runs is decoration. → **Promoted to spec 115-01.**
4. **Event-triggered bug intake + sandbox reproduce** (Real-time push-based +
   Reproducible applied to `bug-fix`). The servo half of the long-horizon
   bridge (servo specs 023/024/025), not jig's. → **Inbox pointer, routed to
   servo.** The Astro "agent failure is a codebase signal" observation rides
   along: it is the recovery path ADR-0050's quarantine
   release-requires-new-evidence rule needs (the new evidence is the missing
   comment, test, or boundary).
5. **Filter rules to context** (derived, filterable index with per-rule
   applies-to metadata; Cloudflare's spec reviewer is a live example).
   Premature at ~20 rules and no second consumer. → **Refinement-todo entry
   with a measured trigger** (Option C of ADR-0062, corrected to the
   prose → index direction).
6. **Per-session, per-call traces.** Mostly covered by `usage.py` +
   spec 041; not adopted absent measured pain.

**Not adopted:** the "replace the SDLC" / factory framing (jig is a thin,
host-neutral, file-owned scaffold; a Workflows-bound runtime is out of scope);
chasing Cloudflare's scale metrics; any standalone conventions gate (ADR-0055).

## Open questions

- Whether Flue's label-encoded state machine has anything jig's bug board
  lacks for *external* visibility (labels are readable by non-jig tooling;
  jig's states live in frontmatter). Astro's pipeline holding *no state of its
  own* beyond labels + comments is a stronger version of jig's
  record-is-the-state stance.
- Positioning: the blank Plan/Design rows are an argument jig's product-vision
  could make explicitly ("the ADLC starts at Implement; jig is the half before
  it"). Not filed — a positioning change wants an owner decision.
- Should bug-fix's Verify-equivalent (bug vs. missing behaviour) be an
  explicit, isolated sub-step of DIAGNOSING rather than a routing note, given
  Astro's stated reason for isolating it (the bias toward forcing a fix)?

## Conclusion

The ADLC post is jig's lifecycle with a runtime attached, and its own stage
table leaves the Plan/Design half — jig's half — blank. The two practice
reports confirm the two ideas worth a decision record (rule severity with an
explicit promotion step and a stable id; agent-fix evidence separation with
human checkpoints), one is a cheap doc addition (readiness checklist), one
routes to servo, one is parked with a trigger, one is already covered.

Promoted to: [ADR-0062](../decisions/adr-0062-convention-rule-severity-and-promotion.md),
[ADR-0063](../decisions/adr-0063-agent-fix-evidence-separation.md),
[spec 114](../specs/114-convention-rule-severity/spec.md),
[spec 115](../specs/115-autonomy-readiness-checklist/spec.md), the
refinement-todo entry "context-filtered convention rules for reviewer prompts",
and the inbox entry `autonomy/event-triggered-bug-intake` (2026-09-22).
