---
status: DONE
dependencies: [113-08]
last_verified: 2026-09-16
arch_review: true
---

## Slice 113-09 — conversational-hook-parity

**Goal:** Copilot users receive useful task, claim, decision-capture, and
context-check behavior whenever the runtime supplies a Stop transcript, instead
of registered Stop hooks that no-op because Copilot supplies a transcript path
rather than inline messages. Current Copilot CLI sessions that do not dispatch
`agentStop` are recorded as a host-runtime residual, not hidden by a parity
claim.

**DoR:**
- ✅ 113-08 has established the live hook payload and command contract.
- ✅ The current adapter's documented input residual identifies `agentStop`
  `transcriptPath` as available while canonical jig hooks consume
  `messages`; no unverified payload shape is assumed.

**Acceptance Criteria:**

1. **Host-neutral transcript input.** Canonical hook helpers accept an
   explicitly bounded transcript-derived conversation input in addition to the
   existing inline-message input, preserving Claude and Codex behavior.
2. **Copilot Stop input support.** The rendered adapter maps Copilot's
   documented `agentStop` transcript capability to that input. Task capture,
   claim checking, and decision capture produce their expected observable
   result from transcript payloads; installed Copilot evidence distinguishes a
   runtime-dispatched Stop event from the observed no-`agentStop` residual.
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
- [x] All ACs pass; focused cross-host hook tests are green. The attempted
      helper-mediated suite invocation expanded to unrelated repository-wide
      tests and was stopped; direct focused pytest coverage is the slice
      validation evidence.
- [x] Regression tests cover inline messages, valid transcript input, absent
      input, malformed transcripts, and the Copilot-installed execution path.
- [x] Reviewed by `reviewer` subagent — compliance, craft, and architecture
      passes recorded.
- [x] Deviation log and reconciliation sweep produced under this heading.
- [x] Reconciliation review passed.

**Anti-horizontal-phasing check:** After this slice, Copilot sessions have the
same Stop-hook input path as supported hosts when Copilot dispatches Stop, and
current no-Stop behavior is visible in evidence instead of silently described
as complete.

### Deviation log (after reconciliation)

- **Updated AC2 from live-installed Stop parity to honest Stop-input support.**
  Copilot CLI 1.0.86-1 interactive debug logs fired the installed plugin's
  session-start, prompt, pre-tool, and post-tool hooks, but contained zero
  `agentStop`, `transcriptPath`, task-capture, claim-check, or decision-capture
  entries. The implementation therefore proves the canonical/adapted input path
  and records the runtime limitation instead of claiming a host event the CLI
  did not emit.
- **Implemented transcript support as shared canonical hook behavior.** The
  Stop hooks now prefer existing inline `messages` and fall back to a bounded
  `transcript_path` reader, so Claude/Codex behavior remains intact while
  Copilot gains a live path if/when it supplies `agentStop.transcriptPath`.
- **Kept context-check's session-start transcript branch residual.** Copilot
  does not supply `transcriptPath` on `sessionStart`; the branch remains a
  documented fail-open no-op under Copilot, while prompt and pre-tool context
  behavior stays supported.

### Reconciliation sweep

- **Source hooks:** updated `jig-task-capture.sh`, `jig-claim-check.sh`, and
  `jig-decision-capture.sh` to consume `messages_from_payload`.
- **Shared helper:** added `hooks/scripts/lib/transcript.py` with bounded JSONL
  parsing and safe empty-input behavior.
- **Copilot adapter:** restored `transcriptPath` → `transcript_path` forwarding
  now that Stop consumers can use it.
- **Generated host packages:** regenerated Claude, Codex, and Copilot hook and
  adapter copies so committed packages match source.
- **Validation/docs:** added transcript and hook regression tests, updated the
  Copilot hook inventory/refinement entry, and recorded live interactive
  no-`agentStop` evidence in
  `docs/specs/113-copilot-third-host/evidence/slice-09-interactive-agentstop.json`.
- **Review nits disposition:** the architecture reviewer noted that
  `context_fill.py` still has an older host-managed transcript-tail reader
  without this helper's workspace-containment default; that path is advisory,
  bounded to 256 KiB, and uses a different established Claude/Codex transcript
  contract, so convergence is deferred until a future shared context-fill
  transcript contract exists. The reviewer also suggested a distinct inventory
  status for runtime-unobserved hooks; this slice kept the existing
  `SHIPPED`/`MAPPABLE`/`UNMAPPABLE` status enum and qualified the Stop entries
  in notes to avoid expanding inventory semantics inside the parity fix.
