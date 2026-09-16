---
slice: 113-06 — committed-package-and-release
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T20:13:02Z
prompt_source: review-113-06-craft.txt (jig:reviewer subagent, Opus) — cleared after 2 fix rounds
substrate: non-interactive
---

Craft review on slice 113-06 (committed-package-and-release). Reviewer: read-only
jig:reviewer (Opus). VERDICT: pass (cleared after two fix rounds — a real blocker
this pass found that compliance + arch missed by not tracing the runtime input path).

The packaging/release half was solid from the start: the multi-event hook merge is
correct (setdefault + guarded per-event insert over distinct Copilot event keys;
single-event scripts byte-identical — corroborated by git status showing no prior
.json modified); validate_copilot_package is robust (rejects nested/malformed hook
schemas); release.yml + release-please copilot entries are correct; _copy_templates
mirrors codex's ${CLAUDE_PLUGIN_ROOT} rewrite; the 9-hook lib-dependency audit is
clean (every dep, incl. transitive decision_scratch → decision_scan, is shipped).

BLOCKER (raised, then CLEARED over two rounds):
- The 9 new hooks route through copilot_hook_adapter.translate_payload (built in
  113-04 for hooks reading only source/tool_input), which dropped `prompt`,
  `messages`, `transcript_path` — the fields 6 of the 9 read. They were
  registered-but-inert, and AC6 over-claimed "fires jig's FULL hook set". RESOLUTION
  (grounded in Copilot SDK types, CLI 1.0.86):
  * translate_payload now forwards `prompt` (UserPromptSubmittedHookInput) →
    memory-scan + decision-inflight fire fully; unit + end-to-end firing tests added
    (memory-scan surfaces lexicon terms from a forwarded Copilot prompt; negative
    control). Both fail if the forwarding is reverted.
  * The `messages`-reading Stop hooks (task-capture, claim-check, decision-capture)
    + context-check's sessionStart transcript-tail are host-gated (Copilot supplies
    no inline `messages` on agentStop; no transcriptPath on sessionStart). Honestly
    reclassified INPUT-DEGRADED (fail-open no-op) across the inventory notes, the
    slice-06 AC6 "Input-parity caveat", and a new refinement-todo entry. AC6 "fires"
    corrected to "registers". decision-capture's in-flight stubs still land via the
    fixed decision-inflight.
  * The dead `transcriptPath` forwarding (no agentStop consumer) was removed, with a
    regression test pinning the deliberate non-forwarding against silent re-add.

Nits (both fixed + confirmed):
- install_contract.py dead `_COPILOT_HOOK_REQUIRED_ENTRY_FIELDS` removed.
- build_copilot_plugin.py merge now RAISES on a same-stem/same-event key collision
  (was a silent `.update()`), with a test forcing + asserting the raise.

Cleared: only the genuinely-fixable input-consumers are claimed fixed; the host-gated
remainder is honestly documented + homed; AC6's "registers vs fires fully" distinction
is drawn honestly and matches the code. No residual craft issues.
