"""Shared primitives for jig's derived index files.

Three artifacts in a jig project are *derived*: their content is computed
from a directory of numbered records, and hand-editing them is always a
mistake.

    docs/bugs/README.md       <- docs/bugs/NNN-<slug>.md
    docs/specs/README.md      <- docs/specs/NNN-<slug>/
    docs/decisions/README.md  <- docs/decisions/adr-NNNN-<slug>.md

Each is a single file that every parallel branch appends to at the same
end-of-table position, so every parallel branch conflicts on it. The plan is to
stop hand-resolving those conflicts (issue #149) — but the conflict marker is
also the only thing that currently catches *two branches allocating the same
number*, because a renderer emits two records sharing an id as two rows without
complaint and a staleness check can't see it either (both rows are faithfully
derived). Number reservation is unreachable for contributors without bypass on
branch protection (issue #147), so the collisions are routine, not theoretical.

Hence a duplicate-id detector per family. This module holds the part that is
genuinely the same across all three; how an id is read off a path differs by
family and stays with the family's own helper.

Extracted at the third occurrence, per ADR-0023's rule for the lifecycle
family: two implementations are a coincidence, three are a shape.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["duplicate_ids", "id_from_numeric_prefix"]


def duplicate_ids(items) -> dict:
    """Map id -> sorted claimant names, for ids claimed more than once.

    `items` is an iterable of `(id, name)` pairs. Returns only the collisions;
    an empty dict means clean. Both the ids and each id's claimants come back
    sorted: this feeds a CI failure message, and output that reorders itself
    between runs reads as a new failure.
    """
    by_id: dict = {}
    for artifact_id, name in items:
        by_id.setdefault(artifact_id, []).append(name)
    return {
        artifact_id: sorted(names)
        for artifact_id, names in sorted(by_id.items())
        if len(names) > 1
    }


def id_from_numeric_prefix(path: Path, prefix: str = "") -> str | None:
    """Read a record's id off its filename, or None if it isn't numbered.

    Ids keep their zero padding: `017` and `17` are the same number but
    different names on disk, and the boards render the padded form, so
    collisions are compared padded too.

    `prefix` covers the ADR shape, where the digits follow a fixed word
    (`adr-0041-slug.md` -> `0041`).
    """
    m = re.match(r"^" + re.escape(prefix) + r"(\d+)", path.name)
    return m.group(1) if m else None
