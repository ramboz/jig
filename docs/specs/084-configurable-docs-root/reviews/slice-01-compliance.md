---
slice: 084-01 — `_common/project_layout.py` layout helper + validation
pass: compliance
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T04:24:19Z
prompt_source: review.py implementation (084-01); jig:reviewer subagent
---

VERDICT: pass

Reviewed slice 084-01 (`_common/project_layout.py` + tests) against ACs 1–5. All
five met; tests exercise each meaningfully (behavior, not code paths).

The escape validator (ADR-0033 §3, the only barrier between config and an
arbitrary-write primitive) was actively attacked for a bypass: absolute (`/etc`,
`//x`) → `os.path.isabs` rejects; `../docs`/`..`/`a/../../x` → normpath yields a
`..`-prefixed path → rejected; `foo/..` → `.` accepted (correct, == project_dir);
backslash sequences on POSIX → literal filename, not an escape (within the
documented POSIX-lexical scope); NUL/control chars → no traversal. No bypass
found within scope. The symlink known-limit is implemented as designed and pinned
by a test.

`project_root_for` is sentinel-anchored with a required `fallback`; the
nested-subproject-wins cross-project-bleed trap is proven (the legacy `parents[3]`
trap is asserted to fire before the sentinel walk overrides it). Leaf
import-discipline holds (AST guard). No bugs, no TODO/FIXME, no untracked debt.
No deviations from ADR-0033 §3/§5a.

Minor non-blocking: `sys` is in the test's `stdlib_ok` allowlist though the module
doesn't import it (harmless over-permissiveness; the guard still flags genuine
non-stdlib imports).
