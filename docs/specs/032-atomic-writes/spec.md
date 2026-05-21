---
status: DONE
---

# Spec 032: Atomic writes

## Overview

Every `Path.write_text(...)` call in jig's Python helpers is non-atomic.
An interrupted run (Ctrl-C, OOM kill, power cut) can leave a half-written
`spec.md`, `README.md`, `CLAUDE.md`, `scaffold.json`, or ADR file.
Probability is low (single-call CLIs that complete in milliseconds) but
the impact is "lose state" — and once jig starts running in colleagues'
environments, the "I never see this" baseline no longer holds.

This spec teaches every jig helper to write files via a shared
`atomic_write_text(path, content)` helper that writes to `<path>.tmp`
then `os.replace()` — POSIX-atomic on a same-FS rename. After this spec
lands, no single file write in jig can leave a torn file behind.
Cross-file consistency in `scaffold()` (multi-file writes) graduates to a
sentinel pattern: `scaffold.json` is the last file written, so a crash
before that final write leaves a re-runnable partial state.

## Why now

- **jig is starting to be shared with colleagues.** Both deferred
  decisions ([refinement-todo.md](../../refinement-todo.md) "Transactional
  writes in scaffold()" and "Atomic writes across all helper scripts")
  name the same trigger: "before jig ships outside personal-dev use."
  That trigger has now fired.
- **The fix is mechanical and reversible.** A shared helper + a sweep of
  `Path.write_text` callsites is well-understood (~6 helper files, ~20
  callsites). The scaffold marker pattern adds one constraint: write
  `scaffold.json` last.
- **No competing in-flight work.** Spec 028 closed (parallel-session
  locks). Spec 030 closed (status rollup). The release pipeline shipped
  (1.7.0). This is a natural moment for cross-cutting infrastructure.

## Goals

1. **Single-file atomic write helper.** Add `atomic_write_text(path,
   content)` to `skills/_common/atomic_io.py`. Tmp-file + `os.replace()`;
   same-FS guarantee. Importable from every jig helper via the existing
   `sys.path.insert(0, parent.parent)` + `from _common.atomic_io import
   ...` pattern.
2. **Sweep all `Path.write_text` callers.** Replace direct writes with
   `atomic_write_text` in `scaffold.py`, `workflow.py`, `memory.py`,
   `adr.py`, `land.py`, `review.py`, and any other helper that produces
   user-visible files. Test files and throwaway temp writes excluded.
3. **`scaffold()` completion marker.** Reorder `scaffold()` so
   `scaffold.json` is the LAST file written (after CLAUDE.md, docs/*,
   brief.md, and all machinery copies). The existing "already scaffolded"
   check already keys on `scaffold.json` presence — making it the
   sentinel means a crashed scaffold leaves no `scaffold.json` and is
   re-runnable without `--force`.
4. **Mark both refinement-todo entries RESOLVED**, linking to this spec.

## Non-goals

- **`fsync` after rename.** `os.replace()` is atomic on the rename but
  doesn't `fsync()` the directory entry. Adding `fsync` is a separate,
  OS-portability-heavy concern (Windows behavior differs). For now:
  rename-atomicity is sufficient — the trigger that motivated this spec
  is interrupted-process state, not power-cut-mid-fsync.
- **Multi-file transactions across helpers.** Each helper writes its own
  files; we make each write atomic, but cross-helper coordination (e.g.,
  `workflow.py transition` writes both `spec.md` AND `README.md`) stays
  as separate atomic writes. A "transition is fully atomic" guarantee
  would need a journal or 2-phase pattern — out of scope.
- **Concurrent-writer locks.** Already shipped in spec 028-02 for
  inbox / refinement-todo append paths. Other helpers don't need locks
  today — single-user sessions don't race themselves.
- **Migrating JSON / YAML writes to a dedicated helper.**
  `scaffold.json` is written via `json.dumps(...) → write_text(...)`;
  `atomic_write_text` accepts the already-serialized string. No
  JSON-specific path needed.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** — Spike | Do we need a spike on `os.replace()` semantics across macOS / Linux / Windows? | **No** — `os.replace()` is documented Python stdlib (since 3.3) with POSIX-atomic rename on same-FS; Windows uses MoveFileExW under the hood. Same-FS is the constraint we depend on; the tmp file lives next to the destination, so this holds in practice. |
| **P** — Path | One shared helper vs. per-file inline tmp-write? | **One shared helper** in `_common/atomic_io.py`. Mirrors the precedent of `_common/parsing.py` (the shared parser). Inline tmp-write would duplicate ~5 lines across 20 callsites and drift. |
| **I** — Interface | Two slices (helper + sweep, then marker) or one big slice? | **Two slices** — 032-01 ships the helper + sweep and is independently valuable (every helper benefits immediately). 032-02 adds the scaffold marker pattern on top. Each is independently mergeable. |
| **D** — Data | What files become atomic? | All `Path.write_text(...)` callsites in: `scaffold.py`, `workflow.py`, `memory.py`, `adr.py`, `land.py`, `review.py`. **NOT** in test files. **NOT** in `_common/` (no current write callsites there). The audit captures the exact callsites in 032-01. |
| **R** — Rules | What's the contract for `atomic_write_text`? | Signature: `def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None`. Tmp file is created via `tempfile.NamedTemporaryFile(delete=False, dir=path.parent, suffix=".tmp")` for collision-resistance against an existing `<path>.tmp` from a user. On any exception during write or replace, the tmp file is removed before re-raising. |

## Known constraints

- **Same-FS requirement for `os.replace()` atomicity.** The tmp file
  MUST be in the same filesystem as the destination. The chosen pattern
  uses `path.parent` as the tmp dir, which guarantees same-FS as long as
  the destination dir exists. For destinations that don't yet exist
  (e.g., new spec dirs), the caller must `mkdir(parents=True,
  exist_ok=True)` first — same pattern as today.
- **`os.replace()` clobbers the destination.** Existing files are
  overwritten silently. That matches today's `Path.write_text` behavior;
  no semantic change.
- **Concurrent writers are NOT made safe by this spec.** Two helpers
  writing to the same file at the same moment can still race (last
  writer wins). Spec 028-02 added flock for inbox / refinement-todo;
  other contention paths stay convention-only.
- **Symlinks.** `os.replace()` follows symlinks at the destination per
  Python docs; today's `Path.write_text` has the same behavior, so this
  is not a regression.

---

## Slices

- [032-01 — atomic-write-helper](slice-01-atomic-write-helper.md)
- [032-02 — scaffold-completion-marker](slice-02-scaffold-completion-marker.md)
