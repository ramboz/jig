"""Shared review-config helper — spec 096-01's `review.<category>_skill`
resolution (ADR-0040 D1).

jig ships **shallow baseline** review skills and defers to a richer skill the
user installed. The most reliable way to select one — the only path ADR-0040 can
*guarantee* — is explicit config: a `review` block in `<project_dir>/scaffold.json`
naming the richer skill per category:

    { "review": { "pr_review_skill": "review-pr-deep",
                   "arch_review_skill": "/abs/path/to/skills/my-arch",
                   "code_health_skill": "team-health" } }

What this module owns (slice 096-01):
  - `CATEGORIES` — the THREE extensible categories (ADR-0040 D1). `security` and
    `design` are deliberately absent: `security-review` has no `review.py`
    builder (named follow-up, OQ1), and `design-review` is an ADR-0022
    attest-only never-defer pass.
  - `PASS_TO_CATEGORY` — maps a review-evidence pass name to its category, so
    `record-review` can derive the config substrate from the pass it is recording.
  - `configured_skill(project_dir, category) -> str | None` — reads + resolves
    `review.<category>_skill`.
  - `ReviewConfigError` — raised ONLY on a STRUCTURAL config mistake (a non-object
    `review`, or a non-string `<category>_skill`) — the authoring error the user
    deliberately wrote and mistyped. A well-formed value that simply does not
    resolve on this machine returns `None` (quiet baseline fallback), NOT an
    error: `scaffold.json` is committed + team-shared, so a teammate or CI runner
    lacking a user-scope install must not have every review pass hard-fail
    (ADR-0040 D1, fixing an over-strict ADR-0039-era AC; preserves `review.py`'s
    documented "never block the craft/arch pass" posture).

**Bare-name resolution (096-02).** A bare name resolves via
`skill_discovery.resolve_skill_path_any_host` — across project → user → admin
scope on BOTH hosts (Claude then Codex), with the jig-baseline discovery filter
OFF (explicit config overrides discovery exclusion, AC7). This closes the
user-scope-only Codex bare-name seam that 096-01 shipped. An explicit path
(absolute, or containing a path separator) is used as-is — see `_resolve_value`.

This module is a near-leaf: stdlib plus the sibling `_common.skill_discovery`
(the only intra-`_common` import — a one-directional config → discovery
dependency, no cycle). JSON via the `json` stdlib — no `tomllib` (the supported
floor is Python 3.9). `$HOME`-honoring (`Path.home()`), so it is hermetically
testable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from _common import skill_discovery

_SCAFFOLD_SENTINEL = "scaffold.json"

# The THREE extensible categories (ADR-0040 D1). Order is the canonical
# precedence-doc order; not otherwise load-bearing.
CATEGORIES = ("pr_review", "arch_review", "code_health")

# review-evidence pass name -> category. Only these three passes map to a
# category; every other pass (compliance / reconciliation / frame-critique /
# design-review / bug-review / security) maps to nothing, so `record-review`
# stamps no config substrate for them.
PASS_TO_CATEGORY = {
    "craft": "pr_review",
    "arch": "arch_review",
    "code-health": "code_health",
}


class ReviewConfigError(ValueError):
    """A STRUCTURAL `review`-config mistake — a non-object `review` block, or a
    non-string `<category>_skill` value. Subclass of `ValueError` so callers
    that already catch `ValueError` keep working (mirrors `LayoutError`).

    NOT raised for a well-formed value that fails to resolve on this machine —
    that is the documented quiet-baseline-fallback path (returns `None`)."""


def _raw_review_block(project_dir: Path) -> "dict | None":
    """Return the `review` block from `<project_dir>/scaffold.json`, or `None`
    when scaffold.json is absent or carries no `review` block. Raises
    `ReviewConfigError` when `review` is present but is not an object.

    A malformed / unparseable scaffold.json is treated as "no config" (return
    `None`) rather than raised: config resolution must never be the thing that
    breaks a review pass on a broken-but-unrelated scaffold.json. (Structural
    validation of the *review* block specifically is what fails loud — AC2.)"""
    sentinel = Path(project_dir) / _SCAFFOLD_SENTINEL
    if not sentinel.is_file():
        return None
    try:
        data = json.loads(sentinel.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    review = data.get("review")
    if review is None:
        return None
    if not isinstance(review, dict):
        raise ReviewConfigError(
            f"malformed scaffold.json at {sentinel}: 'review' must be an "
            f"object, got {type(review).__name__}"
        )
    return review


def _resolve_value(value: str, project_dir: Path) -> "str | None":
    """Resolve a well-formed `<category>_skill` string to an existing SKILL.md
    path, or `None` when it does not resolve on this machine.

    An explicit path (absolute, or containing a path separator) is used as-is —
    pointing either at a `SKILL.md` file directly or at a skill directory (a
    trailing `/SKILL.md` is appended for a directory). A *relative* explicit path
    is anchored to `project_dir` (NOT the process CWD) — `scaffold.json` is a
    committed, team-shared, project-relative manifest, so a relative path in it
    means "relative to the project." A bare name resolves via
    `skill_discovery.resolve_skill_path_any_host` — across project → user →
    admin scope on BOTH hosts (spec 096-02, closing the 096-01 Codex bare-name
    seam). Exclusion is OFF: explicit config overrides the jig-baseline
    discovery filter (AC7). Conservative on every OS error (returns `None`)."""
    try:
        if os.path.isabs(value) or (os.sep in value) or (
            os.altsep and os.altsep in value
        ):
            p = Path(value)
            if not p.is_absolute():
                # Relative explicit path → anchor to the project, not CWD.
                p = Path(project_dir) / p
            if p.is_file():
                return str(p)
            candidate = p / "SKILL.md"
            return str(candidate) if candidate.is_file() else None
        return skill_discovery.resolve_skill_path_any_host(
            value, project_dir=project_dir, exclude_jig_baselines=False,
        )
    except (OSError, ValueError, RuntimeError):
        return None


def configured_value(project_dir: Path, category: str) -> "str | None":
    """The RAW, structurally-validated `review.<category>_skill` string as written
    in scaffold.json (a bare name or a path), or `None` — WITHOUT resolving it to
    a filesystem path.

    Returns `None` when scaffold.json is absent, has no `review` block, no
    `<category>_skill` key, or an empty value. Raises `ReviewConfigError` on a
    structural mistake (non-object `review`, or non-string value — AC2).

    This is the identifier `record-review` records as `applied_skill` (spec
    096-01 / ADR-0040 D3): the project-relative *identifier* the user configured,
    which is portable across machines — as opposed to `configured_skill`'s
    machine-specific *resolved* absolute path, which must never be baked into a
    committed, team-shared evidence artifact."""
    if category not in CATEGORIES:
        raise ReviewConfigError(
            f"unknown review category {category!r}; expected one of "
            f"{', '.join(CATEGORIES)}"
        )
    review = _raw_review_block(project_dir)
    if review is None:
        return None
    key = f"{category}_skill"
    value = review.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ReviewConfigError(
            f"malformed scaffold.json: 'review.{key}' must be a string, got "
            f"{type(value).__name__}"
        )
    return value


def configured_skill(project_dir: Path, category: str) -> "str | None":
    """Resolve `review.<category>_skill` for `project_dir` to an existing
    SKILL.md path, or `None`.

    Returns `None` (jig's baseline) when: scaffold.json is absent, has no
    `review` block, has no `<category>_skill` key, the value is empty, or the
    value is well-formed but does not resolve on this machine. Raises
    `ReviewConfigError` ONLY on a structural mistake (a non-object `review`, or
    a non-string value — AC2). `category` must be one of `CATEGORIES`.

    The returned path is machine-specific (an absolute path). For a value to
    *record* in committed evidence, use `configured_value` instead."""
    raw = configured_value(project_dir, category)
    if raw is None:
        return None
    return _resolve_value(raw, Path(project_dir))
