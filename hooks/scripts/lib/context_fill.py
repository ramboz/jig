"""Context-fill estimator for jig's SessionStart soft-warn hook.

Spec 026 (slice 026-01): factor out a byte/token estimator that

  - measures the always-loaded primer footprint (AGENTS.md / CLAUDE.md +
    docs/memory/*.md);
  - returns a stable dict shape so servo (spec 003 hard-gate) can
    subprocess-invoke this module without re-implementing the math;
  - stays pure (no printing, no env-touching side effects) — the
    hook script does the I/O.

Bytes → tokens conversion
-------------------------

``est_tokens = bytes // RATIO`` with ``RATIO = 4``. Four bytes per token
is the well-worn English-prose heuristic (OpenAI tokenizer docs, Andrej
Karpathy's tokenizer notebooks) — close enough for a soft warning where
the absolute number matters less than the order of magnitude. The hook
surfaces the ratio in its warning so the user can mentally calibrate.

Default window size
-------------------

``DEFAULT_WINDOW_BYTES = 800_000`` — sized for Opus 4.7's nominal
~200K-token context window (200_000 × 4 = 800_000 bytes). Override via
``JIG_CONTEXT_WINDOW_BYTES`` (int) when running against a different
model. Future spec 026 slices may wire in model-name detection; the env
var stays as the manual override.

Default threshold
-----------------

``DEFAULT_THRESHOLD = 0.30`` — 30% of the window. Pre-dumb-zone: the
primer hot cache cites Horthy's 40% degradation knee, so a 30%
warning gives the user time to act (run ``/jig:memory-sync`` and
``/compact``) before recall actually starts slipping. Override via
``JIG_CONTEXT_SOFT_WARN_PCT`` — **set as a fraction (e.g. 0.30), not
a percent (30)**. The var name says PCT but the value is a fraction
in (0, 1]; out-of-range or non-numeric values silently fall back to
the default so a typo never crashes the hook.

Public surface
--------------

``estimate(project_root: Path) -> dict`` returns::

    {
        "bytes":        int,    # sum of contributing-file sizes
        "est_tokens":   int,    # bytes // RATIO
        "ratio":        float,  # bytes / window_bytes
        "threshold":    float,  # the configured soft-warn threshold
        "breakdown":    dict,   # {relative_path: bytes} per contribution
        "window_bytes": int,    # effective window size used for ratio
    }

The caller decides what to do with the result — typically
``ratio >= threshold`` → emit a warning.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


RATIO = 4
"""Bytes per token (rough English-prose heuristic)."""

DEFAULT_WINDOW_BYTES = 200_000 * RATIO  # = 800_000
"""Opus 4.7-sized default context window in bytes (~200K tokens)."""

DEFAULT_THRESHOLD = 0.30
"""Soft-warn at 30% of the window — pre-dumb-zone (40% per Horthy)."""


def _resolve_window_bytes() -> int:
    """Read ``JIG_CONTEXT_WINDOW_BYTES`` from env, falling back to the
    Opus 4.7 default. Malformed values silently fall back so a typo in
    the env doesn't crash the hook."""
    raw = os.environ.get("JIG_CONTEXT_WINDOW_BYTES")
    if raw is None:
        return DEFAULT_WINDOW_BYTES
    try:
        value = int(raw)
        if value <= 0:
            return DEFAULT_WINDOW_BYTES
        return value
    except ValueError:
        return DEFAULT_WINDOW_BYTES


def _resolve_threshold() -> float:
    """Read ``JIG_CONTEXT_SOFT_WARN_PCT`` from env, falling back to 0.30."""
    raw = os.environ.get("JIG_CONTEXT_SOFT_WARN_PCT")
    if raw is None:
        return DEFAULT_THRESHOLD
    try:
        value = float(raw)
        if value <= 0 or value > 1:
            return DEFAULT_THRESHOLD
        return value
    except ValueError:
        return DEFAULT_THRESHOLD


def _measure(path: Path) -> int:
    """File size in bytes, or 0 if the file does not exist."""
    try:
        return path.stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def estimate(project_root: Path) -> Dict[str, object]:
    """Estimate the always-loaded context footprint under ``project_root``.

    See module docstring for the dict shape and the threshold / window
    semantics.

    The function is pure: it reads files via ``Path.stat()`` and never
    prints, mutates the environment, or raises on missing inputs. A
    missing primer files or absent ``docs/memory/`` simply contributes
    zero bytes to the total — the hook surface stays unconditional.
    """
    project_root = Path(project_root)
    breakdown: Dict[str, int] = {}

    for primer_name in ("AGENTS.md", "CLAUDE.md"):
        primer = project_root / primer_name
        primer_bytes = _measure(primer)
        if primer_bytes > 0:
            breakdown[primer_name] = primer_bytes

    memory_dir = project_root / "docs" / "memory"
    if memory_dir.is_dir():
        # Sort for deterministic breakdown ordering — tests assert on
        # specific keys, not on order, but stability is friendlier to
        # downstream consumers (servo, logs).
        for md_file in sorted(memory_dir.glob("*.md")):
            size = _measure(md_file)
            if size > 0:
                rel = md_file.relative_to(project_root).as_posix()
                breakdown[rel] = size

    total_bytes = sum(breakdown.values())
    window_bytes = _resolve_window_bytes()
    threshold = _resolve_threshold()
    ratio = total_bytes / window_bytes if window_bytes > 0 else 0.0

    return {
        "bytes": total_bytes,
        "est_tokens": total_bytes // RATIO,
        "ratio": ratio,
        "threshold": threshold,
        "breakdown": breakdown,
        "window_bytes": window_bytes,
    }
