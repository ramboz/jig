---
bug: 037
pass: craft
verdict: pass
reviewer: pr-review skill craft pass
reviewed_at: 2026-09-17T19:32:21Z
prompt_source: pr-review skill craft pass (diff-shaped; /tmp/craft037_prompt.txt)
---

Independent craft (pr-review methodology) pass (jig:reviewer subagent,
read-only, diff-shaped).

VERDICT: PASS

Verified correct: the liveness branch-walk is sound and fail-safe on every path
(fetch-failed / no-base / claim==base / "detached" / on-origin-contained →
merged / on-origin-ahead → silence / absent+local → silence / absent+absent →
gone); squash-merge and pushed-ahead cases correctly stay silent. Hot path
(fetch=False) is byte-identical (`_focus_candidate` is pure row processing,
`claim_status=""`, segment ordering unchanged). Blast radius clean:
`_freshness_summary` fully removed, no dangling callers, freshness output
preserved and still exercised by `OrientOriginFreshnessTests`. Injection-safe:
new stale labels reuse `_sanitize_orient_claim`. Python 3.9 floor respected
(`X | None`/`tuple[...]` only in annotations under `from __future__`). Tests pin
behavior non-vacuously against a real bare origin (both stale cases + four
fail-safe guards, asserting presence of the right label and absence of the
wrong one).

Only limitations are documented, deliberately-chosen fail-safe residuals: a
merged-then-origin-pruned branch with a lingering local ref is not flagged (it
is indistinguishable from a fresh local branch at base); a custom
`JIG_CLAIM_ID`/other-clone claim reads as "gone; verify". Neither is a
correctness blocker. INFO: each verify helper opens its own budget deadline
(acceptable — interactive `--fetch` path only, never the 4s hot path).
