---
bug: 028
pass: craft
verdict: pass
reviewer: pr-review skill craft pass
reviewed_at: 2026-08-02T07:25:58Z
prompt_source: pr-review skill craft pass (diff-shaped; no review.py builder for bugs)
---

Craft / PR-review pass — VERDICT: pass.

The runtime block reuses the established `_upsert_marked_block` mechanic
correctly; the fresh-file concat vs existing-file upsert paths handle newline
separators and idempotency correctly (the fresh-file branch is justified —
feeding `""` into `_upsert_marked_block` would prepend a spurious leading blank
line). Naming/marker style is consistent with the secret block; comments
accurately cite bug 028/#107, ADR-0013, and the relevant slices.
`_GITIGNORE_RUNTIME_PATTERNS` is faithfully in sync with jig's own `.gitignore`
and does not duplicate the semantic-index/servo-hint entries already in the
secret block. Tests cover fresh/marker/plugin-only/no-duplication/idempotency/
preservation meaningfully.

Non-blocking notes: (1) host-packaged copies were stale at review time —
addressed post-review by rebuilding via `scripts/build_host_packages.py` (drift
`--check` clean). (2) The Bug028 idempotency test asserts marker counts; strict
byte-equality is covered by the shared unit test at test_scaffold.py.
