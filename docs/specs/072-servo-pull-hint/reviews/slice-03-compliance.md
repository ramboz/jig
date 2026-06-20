---
slice: 072-03 — servo-plugin-detection-spike
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (read-only)
reviewed_at: 2026-06-15T17:52:26Z
prompt_source: review.py implementation 072-03 (spike reasoning review)
---

VERDICT: pass

REASONING:
The spike meets all three ACs and the spike-shape DoD (Question / Time-box / Findings / Outcome filled). The central NO-GO is sound and **independently corroborated against the live filesystem**: the reviewer verified `~/.claude/plugins/installed_plugins.json` exists, is keyed `<name>@<marketplace>`, and does NOT list servo despite servo being actively used from a local clone (`~/Projects/misc/servo`) — so "inert for local-clone servo, incl. the user's own setup" is factual, not asserted. An attempt to name a sixth mechanism clearing all five tests (incl. a marketplace-cache-dir walk and a `CLAUDE_PLUGIN_ROOT` sibling probe) failed — each fails install-method-robustness / local-clone. servo's `plugin.json` declares no PATH binary (confirms "no `which servo`"). The reciprocal-breadcrumb direction mirrors servo ADR-0004's writer-owns-contract precedent (which already names jig's `slice-land prepare` as the intended cross-plugin reader).

SPECIFIC ISSUES:
- slice-03:58-68 — [transparency nit, Medium] Two sub-claims (`installed_plugins.json` "don't rely on it"; `CLAUDE_CONFIG_DIR` can relocate `~/.claude`) rest on a Claude-Code-mechanics consult not inspectable in-repo. Plausible, unfalsified; the filesystem evidence (servo absent from the live registry despite active use) independently carries the NO-GO regardless. Not a correctness defect.

RECONCILIATION NOTES:
- Record in the deviation log that the local-clone disqualifier was empirically checked against the live environment, not just reasoned.
- Deviation log + close-out still TODO (expected for IN_PROGRESS); fill before RECONCILED/DONE. 072-02's reshape-vs-defer disposition is already encoded (reciprocal breadcrumb; blocked on the cross-repo contract).
