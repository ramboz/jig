# Spec 080 Plan

## 080-03 - Codex adapter activation

Implementation approach:

1. Reuse the 080-01 host-neutral semantic-index contract from Codex scaffold
   and plugin hook surfaces; do not create a Codex-only activation path.
2. Render Codex hook scripts through `CodexScaffoldRenderer` so
   SessionStart activation calls `semantic_index.activate(..., host="codex")`,
   uses Codex project env, and records Codex-specific one-time suggestion state.
3. Keep public Codex primer output provider-neutral/public-first and avoid
   Scout-specific prose outside the internal overlay-capable helper code.
4. Rebuild committed host packages after source changes so `hosts/claude` and
   `hosts/codex` stay in sync with the canonical renderer/templates.

Verification:

- `python3 -m unittest skills.scaffold-init.test_scaffold_mode.CodexScaffoldAdapterTests`
- `python3 scripts/test_build_codex_committed_package.py`
- `python3 skills/_common/test_semantic_index.py`
- `python3 scripts/test_codex_install_smoke.py`
- `python3 skills/scaffold-init/test_scaffold.py`
- `python3 scripts/test_build_host_packages.py`
- `python3 scripts/build_host_packages.py --check`
- `python3 scripts/spec_lint.py`

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
