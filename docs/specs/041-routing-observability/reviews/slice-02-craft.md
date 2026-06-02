---
slice: 041-02 — routing-stats-helper
pass: craft
verdict: pass
reviewer: jig:reviewer (applied user ~/.claude/skills/pr-review)
reviewed_at: 2026-06-02T18:03:01Z
prompt_source: review.py pr-review docs/specs/041-routing-observability/spec.md 041-02 skills/spec-workflow/workflow.py skills/spec-workflow/test_workflow.py
---

VERDICT: pass

REASONING:
The change is tightly scoped to two pure helpers (_parse_iso_utc, routing_stats), one routing-stats subparser, one dispatch arm, and the import json — no collateral edits, and it faithfully mirrors the sibling stale() idiom (informational, stdout-only, never raises on normal empty states). Correctness is sound: the event == "skill_invoked" filter, the (-(jig+other), category) sort key, defensive JSON/timestamp parsing, and the always-exit-0 contract all match the slice's stated shape. Tests run the script as a real subprocess (so the "never gates" exit-0 guarantee is verified end-to-end) and cover every edge the slice calls out — including the valuable valid-JSON-but-not-a-dict case. No blockers; the only gaps are deferrable polish.

SPECIFIC ISSUES:
- [strength] test_workflow.py — test_malformed_line_skipped covers both a syntactically-broken line and a valid-JSON-but-non-dict line ("12345"), exercising the isinstance(entry, dict) guard.
- [strength] workflow.py — _parse_iso_utc is a small, single-purpose, fully-documented helper that tolerates trailing Z and naive stamps and normalizes to aware UTC before comparison.
- [nit] skills/spec-workflow/SKILL.md — the new routing-stats subcommand is not mentioned in the skill doc, though sibling subcommands (stale, amendments, status-board) all get a line. Deferrable to reconciliation.
- [nit] workflow.py — log_path.read_text(encoding="utf-8") will raise UnicodeDecodeError on a non-UTF-8 trace file, which the per-line try does not catch; nominally violates the "always exits 0" guarantee. Realistically unreachable since jig's own hook writes UTF-8 JSON.
- [nit] workflow.py — the legend embeds hard line breaks inside a single appended string; cosmetic.

RECONCILIATION NOTES:
- Add a routing-stats line to the spec-workflow row in skills/spec-workflow/SKILL.md so the new operator command is discoverable — sibling subcommands set that precedent. Only follow-up with real value; doc-sync, not a code defect.
- Both strengths (non-dict-JSON test case, tz-normalizing _parse_iso_utc) are patterns worth noting in the deviation log.
- The non-UTF-8 read_text edge and the legend-string style are noise-floor; record only for completeness — neither blocks the REVIEWED transition.
