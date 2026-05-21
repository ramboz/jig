"""Atomic file-write helper used by every jig helper script.

Slice 032-01 — atomic-write-helper.

Every previous `Path.write_text(...)` call in jig was non-atomic: a process
interrupted mid-write could leave a half-written `spec.md`, `scaffold.json`,
or ADR file on disk. Jig is starting to ship outside personal-dev use, so
torn-write recovery cost has crossed the threshold where "I never see this"
is no longer a safe baseline.

`atomic_write_text` writes via a sibling `.tmp` file then `os.replace()` —
POSIX-atomic on a same-FS rename (Windows uses MoveFileExW under the hood).
The tmp file is created via `tempfile.NamedTemporaryFile(dir=path.parent, ...)`
so it collision-resists against a pre-existing `<path>.tmp` and inherits the
destination's filesystem. On any exception during write or replace, the tmp
file is best-effort removed before the exception propagates.

Non-goals (intentionally left to a follow-up if needed):
  - `fsync` of the directory entry after rename (Windows-portability heavy;
    interrupted-process semantics are the trigger here, not power loss).
  - Cross-file transactional consistency across multiple writes (handled
    per-helper, e.g. spec 032-02 promotes `scaffold.json` to a completion
    marker via write-ordering).
  - Concurrent-writer locks (spec 028-02 covers the append paths).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(
    path: Path, content: str, *, encoding: str = "utf-8"
) -> None:
    """Write `content` to `path` atomically.

    The write goes to a tmp file in `path.parent`, then `os.replace()`s
    onto `path` — POSIX-atomic on a same-FS rename. On any exception the
    tmp file is best-effort removed before the exception is re-raised.

    Args:
        path: Destination path. Caller is responsible for ensuring the
            parent directory exists (mirrors today's `Path.write_text`
            contract).
        content: Already-serialized string content (caller does any
            JSON / YAML serialization upstream).
        encoding: Text encoding for the tmp-file write. Default utf-8.
    """
    parent = path.parent
    tmp_handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        delete=False,
        dir=parent,
        suffix=".tmp",
    )
    tmp_path = Path(tmp_handle.name)
    try:
        try:
            tmp_handle.write(content)
        finally:
            tmp_handle.close()
        os.replace(tmp_path, path)
    except BaseException:
        # `BaseException` (not `Exception`) so KeyboardInterrupt and
        # SystemExit also trigger cleanup — the whole reason this helper
        # exists is interrupted-process safety. Best-effort tmp removal;
        # we swallow OSError so the original exception (typically the
        # os.replace failure or KeyboardInterrupt) propagates unchanged.
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
