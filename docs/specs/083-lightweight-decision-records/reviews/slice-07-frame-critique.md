---
slice: 083-07 — In-flight decision stubs
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-27T00:15:44Z
prompt_source: review.py frame-critique 083-07; 2 rounds
---

Adversarial frame-critique of slice 083-07 (frame_review: true — host-grounding assumptions).

Round 1 — needs-changes (two load-bearing findings): (1) OVER-CLAIM — the slice claimed in-flight capture "most shrinks the recall residue," but the 083-04 scan already extracts the Tier-1 AskUserQuestion/override subset recall-free from the Stop messages payload; the actual discursive residue is explicitly untouched. The genuine value is resilience, not residue-shrink. (2) DURABILITY ASYMMETRY — clearing the scratch after one surface made an in-flight-only stub strictly LESS durable than a scan candidate (which re-surfaces until recorded), inverting the slice's premise for its unique-value case.

Resolution: (1) reframed slice Goal + spec honesty-note + 083-07 section to scope 083-07 as a RESILIENCE layer over the already-covered Tier-1 cell (survives Stop-payload tool-block loss; persists before Stop for abnormal termination; earlier capture) — NOT residue-shrink or a new coverage cell; (2) reworked the Stop hook to prune only RECORDED stubs and persist un-recorded ones (prune_recorded_stubs + write_stubs), giving durability parity with the scan; AC5 reworded; tests added (persist-until-recorded + prune-when-recorded).

Round 2 — pass: "The frame survives the strongest attack I had." The remaining host assumption (PostToolUse(AskUserQuestion) fires with the answer in the payload; UserPromptSubmit exposes prompt text) is correctly bounded — asserted Claude-side, deferred to 083-08 for Codex, with a stated degrade-to-scan fallback (no regression). Residual cosmetic docstring staleness fixed post-pass.
