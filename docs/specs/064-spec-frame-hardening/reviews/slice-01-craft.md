---
slice: 01 — retro-frame-error-census
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-08T03:41:56Z
prompt_source: review.py pr-review (spike-artifact craft pass, adapted)
---

VERDICT: pass

REASONING:
The census is in scope (a stratified-sample frame-error inventory plus a go/no-go), well-structured, and honestly hedged — n=4 is repeatedly flagged as small, the two known calibration instances are marked, and the GO is correctly tied to ADR-0020's kill criterion. All three spot-checked claims hold; the per-bucket counts now sum cleanly after the scope-arithmetic correction (29 + 3 + 1 = 33). The Findings/Outcome blocks mirror retro.md faithfully.

SPECIFIC ISSUES:
- [nit→resolved] retro.md Scope/Counts — the original "20 ADRs + 14 specs = 34" headline double-counted the driving ADR-0020 and ambiguously folded ADR-paired specs; corrected to a reconstructible "33 distinct artifacts (19 ADRs + 14 specs)" with the paired-spec accounting spelled out.
- [strength] retro.md:14-16 — explicitly probe-verifying the three most load-bearing claims against the repo before recording dogfoods the very grounding-by-probe standard the parent ADR proposes.
- [strength] Surprises section — reports a result that inverts ADR-0020's headline framing (grounding 4/4 load-bearing, critique only 2/4 clean) and carries it into a concrete, scope-preserving priority recommendation rather than burying it.
