# Spec 080 Plan

## 080-04 - usage attribution digest

Implementation approach:

1. Extend `scripts/usage.py` with a `semantic-index` subcommand that reads
   `.jig/semantic-index-events.jsonl` and renders activation attempts by
   bucket, provider, provider profile, outcome, repo-root class, and host.
2. Keep activation telemetry and transcript/read-growth proxies aggregated over
   the same configurable time window. The telemetry intentionally has no
   session id, so the digest must not imply a row-level join.
3. Reuse existing Claude transcript fixtures and read-attribution fixture style
   to count raw `Read` tool calls, broad `Grep`/`Search` calls, cache-read peak
   bands, and large/duplicate read nudges without requiring providers or host
   runtimes.
4. Preserve the no-content-leak boundary: print only counts and compact status
   labels, never search queries, file bodies, diffs, read paths, or provider
   command output.

Verification:

- `python3 scripts/test_usage.py`
- `python3 -m unittest discover -s scripts -p 'test_*.py'`
- `python3 skills/_common/test_semantic_index.py`
- `python3 scripts/spec_lint.py`
