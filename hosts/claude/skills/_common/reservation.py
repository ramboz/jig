#!/usr/bin/env python3
"""Shared reservation machinery for jig's numbered-record lifecycles.

Number reservation (bugs, specs, ADRs) is mirrored across three helpers —
`bug.py`, `adr.py`, `workflow.py`. Two pieces of that machinery were copied
into all three, drifted, and grew a latent defect (see
docs/decisions/adr-0053-reservation-numbering-sees-in-flight-branches.md):

  1. `classify_push_failure` — sorts a failed `git push` into protection /
     race / other. The copies disagreed (only `bug.py` carried `gh006`), and
     all three checked the generic race markers before the specific protection
     markers, so a protected-branch refusal (which always contains the
     substring `rejected`) was reported as a race and the PR fallback never
     fired.

  2. `scan_max_reserved_number` — the next id must account for claims sitting
     on any in-flight branch, not only files already merged to `origin/main`.

Per ADR-0002's three-caller rule (deferred at two callers in the inline-mirror
comments), the third caller triggers extraction. This module is the single
home; the three helpers import from it and keep a module-level
`_classify_push_failure` re-export so existing call sites are unchanged.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Push-failure classification
# ---------------------------------------------------------------------------

# Substrings (case-insensitive) that mark a `git push origin main` refusal as a
# branch-protection / ruleset / permission refusal. These route to the PR
# fallback. `gh006` is classic protected branches; `gh013` /
# `repository rule violations` is the repository-rulesets mechanism GitHub uses
# now (issue #147 gap 1) — the ruleset trailer is
# `push declined due to repository rule violations`, which none of the older
# signals matched.
_PUSH_PROTECTION_SIGNALS = (
    "protected branch",
    "gh006",
    "gh013",
    "repository rule violations",
    "permission denied",
    "pre-receive hook declined",
    "not authorized",
    "cannot lock ref",
)

# Substrings that mark a failure as a race — someone advanced `main` between
# fetch and push. Deliberately SPECIFIC: every non-fast-forward refusal git
# prints names its reason in parens — `(non-fast-forward)`, `(fetch first)`,
# `(stale info)`. The bare `rejected` / `[rejected]` markers were removed
# (issue #147 direction 3): they appear on protection refusals too, and with
# protection checked first they would otherwise swallow every failed push —
# including genuine unknown failures — into the race path, telling the user to
# re-run something that cannot succeed.
_PUSH_RACE_SIGNALS = (
    "non-fast-forward",
    "fetch first",
    "stale info",
)


def classify_push_failure(stderr: str) -> str:
    """Classify a failed `git push origin main` stderr as one of:

      - "protection" — branch protection / ruleset / permission refusal;
        routes to the PR fallback.
      - "race" — `origin/main` advanced between fetch and push; the recovery
        is to drop the stranded commit and re-run.
      - "other" — anything else; surfaced to the caller as a hard error.

    Protection is checked BEFORE race: protection markers only ever appear on
    protection refusals, and a protection refusal never advances `origin/main`,
    so there is no stranded-commit race to recover from. Specific wins over
    generic.
    """
    low = stderr.lower()
    for sig in _PUSH_PROTECTION_SIGNALS:
        if sig in low:
            return "protection"
    for sig in _PUSH_RACE_SIGNALS:
        if sig in low:
            return "race"
    return "other"


# ---------------------------------------------------------------------------
# In-flight number scan
# ---------------------------------------------------------------------------


def _git(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def list_branch_refs(project_dir: Path, *, run=None) -> tuple[int, list[str]]:
    """`git for-each-ref --format=%(refname) refs/heads refs/remotes` — every
    local branch + remote-tracking ref this checkout can see. Returns
    `(rc, refs)`; `rc != 0` means the enumeration failed (git unusable /
    not a repo) and `refs` is empty — the caller degrades.

    Extracted from `scan_max_reserved_number`'s inline call (ADR-0053) so
    a second reader of "every ref this checkout can see" — `_common.
    cross_ref_state.find_sibling_done` (ADR-0058 Class C, spec 112-03) —
    reuses the same enumeration rather than re-issuing the `for-each-ref`
    call with its own copy of the refspec. This is the third distinct call
    site for the underlying git invocation (ADR-0053's scan was already the
    second, after ADR-0058's Class-A read reused `identifier_state_on_ref`'s
    OWN per-ref content read rather than this enumeration) — per ADR-0002's
    rule-of-three, the shared shape earns its own name.
    """
    git = run if run is not None else _git
    rc, out, _err = git(
        ["git", "for-each-ref", "--format=%(refname)",
         "refs/heads", "refs/remotes"],
        project_dir,
    )
    if rc != 0:
        return rc, []
    return rc, [line.strip() for line in out.splitlines() if line.strip()]


def _max_in_listing(listing: str, docs_relpath: str, number_re: re.Pattern) -> int:
    """Extract the highest number from a `git ls-tree --name-only` listing (or
    a newline-joined directory listing). `number_re` is applied to each entry's
    basename."""
    highest = 0
    prefix = docs_relpath.rstrip("/") + "/"
    for line in listing.splitlines():
        name = line.strip()
        if not name:
            continue
        # ls-tree prints paths relative to the repo root; a plain dir scan
        # passes basenames. Normalize to a basename either way.
        if name.startswith(prefix):
            name = name[len(prefix):]
        name = name.rstrip("/").split("/")[0]
        match = number_re.match(name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def scan_max_reserved_number(
    project_dir: Path,
    docs_relpath: str,
    number_re: re.Pattern,
    *,
    local_dir: Path | None = None,
    fetch: bool = True,
    run=None,
    warn=sys.stderr,
) -> int:
    """Return the highest reserved number visible anywhere git can see it: the
    working tree (`local_dir`, if given), every local branch (`refs/heads/*`),
    and every remote-tracking branch (`refs/remotes/*`). Returns 0 when nothing
    matches.

    Best-effort by construction (ADR-0053): a failed `git fetch` proceeds over
    the refs already in the local cache with one warning; a failed ref
    enumeration falls back to whatever could be read. Numbering never raises
    because the network — or git — is unavailable. `number_re` must capture the
    number in group 1 and is applied to each entry's basename.

    `run` is an optional `(argv, cwd) -> (rc, stdout, stderr)` callable; the
    three helpers pass their own `_run` so their tests can intercept git the
    same way they already do. Defaults to a private `subprocess.run` wrapper.
    """
    git = run if run is not None else _git
    highest = 0

    # 0. The working tree the caller is about to write into.
    if local_dir is not None and local_dir.is_dir():
        names = "\n".join(p.name for p in local_dir.iterdir())
        highest = max(highest, _max_in_listing(names, "", number_re))

    # 1. Best-effort refresh of remote-tracking refs.
    if fetch:
        rc, _out, err = git(["git", "fetch", "--quiet"], project_dir)
        if rc != 0:
            warn.write(
                "warning: `git fetch` failed while scanning for the next "
                f"number ({err.strip() or 'unknown error'}); using the local "
                "git cache — a number claimed on a not-yet-fetched branch may "
                "be missed\n"
            )

    # 2. Enumerate every local + remote-tracking ref.
    rc, refs = list_branch_refs(project_dir, run=git)
    if rc != 0:
        # git is unusable here — fall back to the working-tree view only.
        return highest

    # 3. Read each ref's docs directory (non-recursive) and fold in its max.
    for ref in refs:
        rc, listing, _err = git(
            ["git", "ls-tree", "--name-only", ref, "--",
             docs_relpath.rstrip("/") + "/"],
            project_dir,
        )
        if rc != 0 or not listing.strip():
            # Ref lacks the docs dir, or a detached/odd lineage — contributes 0.
            continue
        highest = max(highest, _max_in_listing(listing, docs_relpath, number_re))

    return highest


# Number-extraction patterns for the three families. Group 1 is the number.
BUG_NUMBER_RE = re.compile(r"^(\d{3})-")
SPEC_NUMBER_RE = re.compile(r"^(\d{3})-")
ADR_NUMBER_RE = re.compile(r"^adr-(\d{4})-")
