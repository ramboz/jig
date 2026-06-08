---
slice: 064-05 — adr-accept-gate
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-08T20:39:14Z
prompt_source: review.py pr-review (064-05; re-reviewed after blocker fix)
---

VERDICT: pass

REASONING:
Tightly scoped to the ADR-side gate + the shared-helper move. The evidence_gate_enabled move (byte-identical workflow alias), parse_verdict_file's defaulted required_fields, adr_evidence_path zero-padding, the gate's grace/bypass ordering (flag → bypass → validate, before any Status mutation), record-review --adr mutual exclusion, and the cwd-relative decisions_dir (agreeing between record + gate) all verified correct. Full suite green (2462).

HISTORY: First craft + arch passes both returned needs-changes for ONE shared [blocker] — `review.py frame-critique <adr>` (the command the accept-gate's refusal advertises) died on an ADR because it required `## Slice` headings (find_slice_label). FIXED: frame-critique now detects an ADR-basename target, skips find_slice_label, and critiques the ADR as its own deliverable; the spec path still requires slice + >=1 deliverable (the relaxed argparse nargs is re-guarded in dispatch); the gate message now advertises the resolvable `docs/decisions/adr-NNNN-*.md` path. Added FrameCritiqueAdrCliTests (ADR-without-slice success + spec-without-slice error); pre-existing test_frame_critique_requires_at_least_one_deliverable intact. An independent focused re-review confirmed the fix end-to-end (exit 0 against a real ADR), no regression.

SPECIFIC ISSUES:
- [strength] evidence_gate_enabled → _common with a byte-identical workflow alias: the two gates provably read JIG_REVIEW_EVIDENCE_GATE identically, can't drift.
- [strength] _gate_frame_critique ordering runs before mutating Status, so a refusal leaves the ADR untouched; message names the artifact + the exact commands.
