---
slice: 084-01 — `_common/project_layout.py` layout helper + validation
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-29T23:27:43Z
prompt_source: review.py frame-critique (ADR-0033 + spec 084 + slices 01-03); jig:reviewer subagent; 2 rounds
---

Adversarial frame-critique of ADR-0033 (configurable docs root) + the paired spec 084 / slices 01–03 — shared design. Slice 084-01 (the `project_layout` helper, the path-escape validator, and the sentinel-anchored `project_root_for` resolver) IS the load-bearing mechanism the ADR's §5a rests on, so its frame is critiqued here jointly with the ADR (cf. spec 083-05/06/07 carrying the ADR-0031 shared-design pass). Two independent jig:reviewer rounds.

Round 1 — needs-changes: confirmed the frame's core cleavage (artifact-placement vs git-anchoring) and the marker-up-walk discovery finding are grounded, then found a THIRD discovery category the ADR and the orchestrator pre-critique both missed: depth-arithmetic root derivation — `_project_root_for_spec` (workflow.py:992-1008) and bare `parents[3]` at `_record_spec_ref` (981) and the DONE-dependency check (1149) assume `docs/specs/<dir>/spec.md` (root = parents[3]), with a `.git` fallback that also climbs to the enclosing repo. Under `docs_root="."` these resolve to the enclosing repo for the post-`new` lifecycle (transition / slice-claim `claimed_by` / DONE-dependency / `.jig/spec-ref`), which slice 084-02's status-board/new/adr ACs never exercise.

Resolution: this slice (084-01) gained `project_root_for(path)` as the single sentinel-anchored resolver subsuming BOTH the marker up-walk AND the depth arithmetic (AC5), with a sentinel-less fallback preserving default + jig-self behavior. ADR §5a reframed to the stronger invariant — project-root discovery is sentinel-anchored, never structure-derived. The push-guard well-definedness (slice 084-03 AC5) pinned to the same `project_root_for` anchor.

Round 2 — pass: all four load-bearing code claims re-grounded independently. The single new assumption the resolution introduces — that one sentinel-anchored resolver subsumes both discovery categories — survives because its fallback fires ONLY for sentinel-less paths (jig's own repo, test fixtures), while every scaffolded adopter carries `scaffold.json` (the spec 063 completion sentinel) and resolves via the sentinel. Non-blocking implementer note captured in 084-01 AC5: the "single resolver" is one sentinel-walk wrapping N per-caller legacy fallbacks; prefer a single `fallback` callable parameter so each legacy path stays correct.
