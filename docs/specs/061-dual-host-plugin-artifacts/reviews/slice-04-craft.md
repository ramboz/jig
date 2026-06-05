---
slice: 061-04 - host-explicit release zips
pass: craft
verdict: pass
reviewer: pr-review
reviewed_at: 2026-06-05T23:54:44Z
prompt_source: review.py pr-review <spec> host-explicit <deliverables>
---

VERDICT: pass

Clean, well-tested per-host zip builder and release-workflow wiring. The heredoc-in-YAML round-trip was independently simulated (YAML literal block-scalar dedent + plain `<<EOF` heredoc executed with VERSION=1.10.0): backticks render literally, `${VERSION}` expands, list-continuation lines land at a proper 2-space markdown indent — no corruption. Backtick escaping is necessary and correct. The fetch-then-append release-note pattern correctly avoids clobbering release-please's changelog. All 45 tests across both test files pass.

BLOCKERS: none

NOTES (non-blocking):
- `build_release_zip.py` `_smoke_codex`: `passed = result.status == PASS` could inline. Trivial.
- `_read_manifest_version` typed `tuple[str | None, str | None]` but returns `data.get("version")` unguarded — a `str()`/isinstance guard would tighten the contract against a malformed manifest.
- release.yml release-note list items soft-wrap mid-sentence; GitHub renders single newlines in a list item as a space so bold spans correctly. One-line-per-item would be marginally more robust. Cosmetic.
- No unit test asserts the generated release-note markdown itself (only that the workflow file contains the right substrings); heredoc correctness verified by inspection/CI, not a unit test. Acceptable for an infra slice; a "dedent + run heredoc, assert backticks/$VERSION" test would lock in the behavior.
