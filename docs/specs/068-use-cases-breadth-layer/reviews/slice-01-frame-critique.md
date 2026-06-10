---
slice: 068-01 — capture-and-vision-section
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-10T20:38:01Z
prompt_source: review.py frame-critique
---

VERDICT: pass

REASONING:
The single load-bearing assumption for 068-01 — "a goal-level use-case set is knowable and enumerable at init well enough to seed a useful anchor" — is honestly flagged as thin-evidence, sharpened into a distinct *incompleteness/timing* facet (separate from ADR-0025 §A2's coarseness), and explicitly **not** assumed to be complete: slice 01 ships a pure seed and hands all growth + the effectiveness bet to slice 02 (which now carries the `frame_review` for "does prompting-at-spec-draft actually get used"). The grounding the frame rests on was verified (the wizard's "No prior pitch. Start cold" input mode and the verified absence of any behavior concept in `product-vision.md.template` / the wizard / `/jig:clarify`), and the deferral is sound — an acknowledged-incomplete seed misdirects nothing downstream because slices 02–03 are inert without it (it is a pure prerequisite, not a frame others build wrong assumptions on). The risk is named, bounded by the overridable-default scoping + the kill criterion, and cheap to unwind, so the frame survives.

SPECIFIC ISSUES:
- **Primary load-bearing assumption — "a useful goal-level use-case seed is knowable at init":** The strongest attack is that init is structurally the moment of *least* behavior knowledge (the spec concedes this, citing the wizard's "Start cold" mode), so the captured seed could be so thin or generic that it is worse than nothing — an empty/near-empty `## Use cases` section that nonetheless reads as "filled," giving false confidence. Why the frame nonetheless survives for slice 01: (a) the assumption is *not* that the seed is complete — slice 01 assumes only that it is a *seed*, with no completeness claim and no grow mechanism of its own; (b) the downstream consequence of a thin seed is contained because nothing builds on slice 01 except slice 02's grow-on-discovery (which re-seeds with whatever exists and grows it where behaviors actually surface) and slice 03's coverage check (inert until populated) — so a thin seed degrades gracefully rather than misdirecting; (c) the spec installs a discriminating signal (a thin section despite a filled-and-confirmed capture ⇒ init-incompleteness, distinct from "100% coverage yet specs diverge" ⇒ coarseness); and (d) the whole thing is an overridable default a thin-behavior project drops at zero cost. The residual exposure — *does the seed plus spec-draft growth actually reduce divergence* — is correctly relocated to slice 02's `frame_review` and the §A2 kill criterion. This is "risk named, bounded, cheap to unwind," not "risk proven" — the bar for a surviving frame.

---
PROVENANCE: This verdict validates the **Design-Y** frame for slice 01 (capture a pure seed; defer growth to slice 02). History:
- An initial 4-round adversarial iteration (under "Design X", where slice 01 itself owned an additive-grow-on-re-run seam) established the knowability-at-init facet as a distinct, timing-rooted incompleteness risk (vs. §A2 coarseness), corrected a false "free reuse of the re-run protocol" claim, and corrected a grow-trigger wired to hash-divergence (unreachable when behaviors are learned without editing the doc). That iteration passed, with a pass-level note that prompting growth naturally belongs at spec-draft time (slice 02).
- Per the team decision, the grow mechanism + spec-draft prompting were moved out of slice 01 into **slice 02** (slice 02 now carries `frame_review` for the mitigation's *effectiveness* bet). Slice 01 was re-scoped to a pure seed and re-validated here — this pass.
Model policy: all frame-critique passes run at Opus (equal-or-stronger than the author); never downgraded for cost (ADR-0020).
