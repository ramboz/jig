---
slice: 084-02 — Route read/write helpers through the layout helper
pass: reconciliation
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T14:38:07Z
prompt_source: review.py reconciliation (084-02); jig:reviewer subagent
---

VERDICT: pass

Reconciliation review of slice 084-02. All eight deviation-log + sweep claims
verified against the code: migrate.py's docs/ sites are pre-sentinel adoption /
ADR-0004 rename machinery (correctly excluded); review_evidence.bug_evidence_path
is file-relative (unchanged, correct); lexicon.py imports no _common and carries
the inline fail-soft _memory_dir, with test_lexicon_overlay_honors_dot_root
exercising docs_root="." behaviorally; project_layout.docs_base is public; the
sys.path bootstrap is present in decisions.py + stocktake.py; review._find_project_root
uses the os.devnull marker; all three slice-02 verdict files exist (verdict: pass).
The only retained "docs" literal in a rewired writer (memory.py:76 templates/docs)
is an allowlisted scaffold-source path. The docs_base() extension of the DONE
084-01 module is additive (no closed-spec-drift). Deferred follow-ups each name a
credible trigger and are non-blocking. No undisclosed deviations.
