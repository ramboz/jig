---
status: DRAFT
dependencies: [113-08]
last_verified:
arch_review: true
---

## Slice 113-09 — conversational-hook-parity

**Goal:** Copilot users receive useful task, claim, decision-capture, and
context-check behavior after a session, instead of registered Stop hooks that
no-op because Copilot supplies a transcript path rather than inline messages.

**DoR:**
- ✅ 113-08 has established the live hook payload and command contract.
- ✅ The current adapter's documented input residual identifies `agentStop`
  `transcriptPath` as available while canonical jig hooks consume
  `messages`; no unverified payload shape is assumed.

**Acceptance Criteria:**

1. **Host-neutral transcript input.** Canonical hook helpers accept an
   explicitly bounded transcript-derived conversation input in addition to the
   existing inline-message input, preserving Claude and Codex behavior.
2. **Copilot Stop functionality.** The rendered adapter maps Copilot's real
   `agentStop` transcript capability to that input, and task capture, claim
   checking, and decision capture each produce their expected observable
   result from an installed Copilot session.
3. **Context-check behavior.** The context-check hook uses the best
   host-supplied source available for its session-start/transcript behavior or
   records a narrowly evidenced residual when the required input is not
   available on that event.
4. **Safe transcript handling.** Transcript reads are bounded, reject
   untrusted/out-of-workspace paths where the host contract permits them, and
   fail open only for advisory hooks. Enforcing hooks retain their documented
   failure semantics.
5. **Residual closure.** The Copilot conversational-input refinement entry and
   hook inventory are updated to distinguish solved functionality from any
   remaining host limitation; no hook is labelled parity-complete solely
   because it is registered.

**DoD:**
- [ ] All ACs pass; focused cross-host hook tests and the full suite are green.
- [ ] Regression tests cover inline messages, valid transcript input, absent
      input, malformed transcripts, and the Copilot-installed execution path.
- [ ] Reviewed by `reviewer` subagent — compliance, craft, and architecture
      passes recorded.
- [ ] Deviation log and reconciliation sweep produced under this heading.
- [ ] Reconciliation review passed.

**Anti-horizontal-phasing check:** After this slice, Copilot sessions gain the
same actionable close-of-session guidance that jig users receive on supported
hosts.

### Deviation log (after reconciliation)

_Pending implementation._

### Reconciliation sweep

_Pending implementation._
