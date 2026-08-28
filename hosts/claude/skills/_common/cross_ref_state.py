"""Ref-aware lifecycle-state primitive (ADR-0058 / spec 112-01).

`identifier_state_on_ref(identifier, ref, repo_root=None)` reads the
lifecycle marker (`DONE`, `Accepted`, another status token, or the
`ABSENT` sentinel) of a slice (`NNN-MM`) or ADR (`NNNN`) identifier AS
COMMITTED ON A GIVEN GIT REF — not the current checkout. This is the read
side of ADR-0058's fix for "the current checkout is not the whole truth":
a stale on-disk marker (e.g. `DRAFT`) can coexist with the same identifier
already `DONE` on `origin/main` or a sibling branch.

Matches on the identifier's NUMBER, not its filename — a renamed slug
survives (`docs/specs/112-old-slug/` and `docs/specs/112-new-slug/` both
resolve identifier `112-01`). Reads via `git show <ref>:<path>` (a content
read, distinct from ADR-0053's filename-only `--name-only` scan this module
reuses the enumeration shape of). Best-effort by construction: ANY git
failure (ref unreachable, not a git repo, git not on PATH) returns `None`
("unknown") rather than raising — callers (e.g. `land.py prepare`'s
Class-A blocker) degrade `None` to a non-blocking warning, mirroring
`_branch_freshness_warning`'s posture.

Status parsing reuses `_common.parsing.status_marker_from_section` (slice
status) and `_common.parsing.parse_frontmatter` (ADR status) — the same
readers `land.py` / `adr.py` use — so a cross-ref read can never diverge
from what a normal checkout-local read would report for the identical
content.
"""

from __future__ import annotations

import re
import subprocess
import time
from collections import namedtuple
from pathlib import Path
from typing import Optional

from . import project_layout
from .parsing import (
    SliceLookupError,
    find_slice_section,
    parse_frontmatter,
    status_marker_from_section,
)
from .reservation import list_branch_refs

# Sentinel: the identifier's file/section is not present on the given ref
# (normal case for un-landed work — never a blocker). Distinct from `None`
# ("unknown" — a git/ref error, degrades to an advisory, never a blocker
# either, but for a different reason).
ABSENT = "absent"

_SLICE_ID_RE = re.compile(r"^(\d{3})-(\d{2})$")
_ADR_ID_RE = re.compile(r"^(\d{4})$")

_DEFAULT_SPECS_RELPATH = "docs/specs"
_DEFAULT_DECISIONS_RELPATH = "docs/decisions"


def _git(argv: list, cwd: Path) -> tuple:
    """Same shape as `_common.reservation._git` — a private, module-local
    git runner (not imported cross-module: that helper is underscore-private
    to its own module). Never raises; an OSError (e.g. git missing) becomes
    a non-zero return code with the exception text as stderr."""
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def _relpath(base: Path, root: Path) -> str:
    try:
        return base.relative_to(root).as_posix()
    except ValueError:
        return base.as_posix()


def _specs_relpath(repo_root: Path) -> str:
    try:
        return _relpath(project_layout.specs_dir(repo_root), repo_root)
    except project_layout.LayoutError:
        return _DEFAULT_SPECS_RELPATH


def _decisions_relpath(repo_root: Path) -> str:
    try:
        return _relpath(project_layout.decisions_dir(repo_root), repo_root)
    except project_layout.LayoutError:
        return _DEFAULT_DECISIONS_RELPATH


def _ls_tree(git, repo_root: Path, ref: str, relpath: str):
    """`git ls-tree --name-only <ref> -- <relpath>/`. Returns (rc, entries)
    where `entries` is a list of basenames (directory prefix stripped)."""
    rc, out, _err = git(
        ["git", "ls-tree", "--name-only", ref, "--", relpath.rstrip("/") + "/"],
        repo_root,
    )
    if rc != 0:
        return rc, []
    prefix = relpath.rstrip("/") + "/"
    entries = []
    for line in out.splitlines():
        name = line.strip()
        if not name:
            continue
        if name.startswith(prefix):
            name = name[len(prefix):]
        entries.append(name.rstrip("/"))
    return rc, entries


def _show(git, repo_root: Path, ref: str, relpath: str):
    """`git show <ref>:<relpath>`. Returns (rc, content)."""
    return git(["git", "show", f"{ref}:{relpath}"], repo_root)[:2]


def _find_spec_dir(git, repo_root: Path, ref: str,
                   spec_num: str) -> Optional[str]:
    """Locate the `docs/specs/<NNN-slug>` directory NAME for `spec_num` on
    `ref`. Returns `None` when `ref` (or git) is unreadable — an unknown,
    distinct from `""` (readable ref, no such spec dir — the identifier is
    simply ABSENT there). Shared by `_slice_state` and
    `_slice_evidence_complete` (spec 112-03) so the two agree on which
    directory a slice number resolves to on a given ref."""
    specs_rel = _specs_relpath(repo_root)
    rc, entries = _ls_tree(git, repo_root, ref, specs_rel)
    if rc != 0:
        return None
    for name in entries:
        m = re.match(r"^(\d{3})-", name)
        if m and m.group(1) == spec_num:
            return name
    return ""


def _find_adr_file(git, repo_root: Path, ref: str,
                   adr_num: str) -> Optional[str]:
    """Locate the `docs/decisions/adr-NNNN-<slug>.md` file NAME for
    `adr_num` on `ref`. Returns `None` when unreadable, `""` when the ref
    is readable but no such ADR file exists there. Shared by `_adr_state`
    and `_adr_evidence_complete` (spec 112-03)."""
    decisions_rel = _decisions_relpath(repo_root)
    rc, entries = _ls_tree(git, repo_root, ref, decisions_rel)
    if rc != 0:
        return None
    for name in entries:
        m = re.match(r"^adr-(\d{4})-.*\.md$", name)
        if m and m.group(1) == adr_num:
            return name
    return ""


def _slice_content(git, repo_root: Path, ref: str,
                   spec_num: str, slice_num: str) -> tuple:
    """Locate and read the raw section/file text for a slice identifier ON
    `ref` — the shared read `_slice_state` (status only) and `_slice_claim`
    (status + `claimed_by`, spec 112-05 / ADR-0058 Class B) both derive
    from, so the two readers can never disagree about WHICH bytes they are
    looking at.

    Returns `(kind, content)`:
      - `("unknown", None)`  — `ref`/git unreadable.
      - `("absent", None)`   — `ref` readable, identifier not present on it.
      - `("ok", content)`    — the slice file's, or the embedded `## Slice
                               ...` section's, text as committed on `ref`.
    """
    specs_rel = _specs_relpath(repo_root)
    spec_dir = _find_spec_dir(git, repo_root, ref, spec_num)
    if spec_dir is None:
        return "unknown", None  # ref/repo unreadable — unknown, not absent
    if not spec_dir:
        return "absent", None

    spec_dir_rel = f"{specs_rel}/{spec_dir}"
    rc, files = _ls_tree(git, repo_root, ref, spec_dir_rel)
    if rc != 0:
        return "unknown", None

    slice_file = None
    for name in files:
        m = re.match(r"^slice-(\d{2})-", name)
        if m and m.group(1) == slice_num:
            slice_file = name
            break

    if slice_file is not None:
        rc, content = _show(git, repo_root, ref, f"{spec_dir_rel}/{slice_file}")
        if rc != 0:
            return "unknown", None
        return "ok", content

    # Fall back to an embedded `## Slice NNN-MM ...` section in spec.md.
    rc, content = _show(git, repo_root, ref, f"{spec_dir_rel}/spec.md")
    if rc != 0:
        return "absent", None  # no per-slice file AND no spec.md on this ref
    try:
        start, end, _label = find_slice_section(content, f"{spec_num}-{slice_num}")
    except SliceLookupError:
        return "absent", None
    return "ok", content[start:end]


def _slice_state(git, repo_root: Path, ref: str,
                  spec_num: str, slice_num: str) -> Optional[str]:
    kind, content = _slice_content(git, repo_root, ref, spec_num, slice_num)
    if kind == "unknown":
        return None
    if kind == "absent":
        return ABSENT
    status = status_marker_from_section(content)
    return status or ABSENT


def _frontmatter_fields_from_section(section: str) -> dict:
    """Layout-aware frontmatter extraction — mirrors
    `status_marker_from_section`'s dual-layout handling (a whole slice file
    carries frontmatter at offset 0; an embedded `## Slice ...` section
    carries it after the header line), but returns every field rather than
    only `status` (needed for `claimed_by` — spec 112-05)."""
    fm_fields, _ = parse_frontmatter(section)
    if not fm_fields:
        nl = section.find("\n")
        if nl >= 0 and section.startswith("##"):
            fm_fields, _ = parse_frontmatter(section[nl + 1:].lstrip("\n"))
    return fm_fields


def _slice_claim(git, repo_root: Path, ref: str,
                 spec_num: str, slice_num: str) -> Optional[tuple]:
    """Like `_slice_state`, but also reads the `claimed_by:` frontmatter
    field (ADR-0058 Class B / spec 112-05) — `_slice_state` alone can only
    answer "what state is it in", not "who holds it".

    Returns `(status, claimed_by)` (`claimed_by` is `""` when absent),
    `(ABSENT, "")` when `ref` is readable but the identifier is not present
    on it, or `None` when `ref`/git could not be read."""
    kind, content = _slice_content(git, repo_root, ref, spec_num, slice_num)
    if kind == "unknown":
        return None
    if kind == "absent":
        return ABSENT, ""
    status = status_marker_from_section(content) or ABSENT
    claimed_by = str(
        _frontmatter_fields_from_section(content).get("claimed_by", "")
    ).strip()
    return status, claimed_by


def _adr_state(git, repo_root: Path, ref: str, adr_num: str) -> Optional[str]:
    decisions_rel = _decisions_relpath(repo_root)
    adr_file = _find_adr_file(git, repo_root, ref, adr_num)
    if adr_file is None:
        return None
    if not adr_file:
        return ABSENT

    rc, content = _show(git, repo_root, ref, f"{decisions_rel}/{adr_file}")
    if rc != 0:
        return None
    fm_fields, _ = parse_frontmatter(content)
    status = str(fm_fields.get("status", "")).strip()
    return status or ABSENT


def identifier_state_on_ref(identifier: str, ref: str,
                            repo_root: Optional[Path] = None,
                            *, run=None) -> Optional[str]:
    """Return the lifecycle marker for `identifier` as committed on `ref`.

    `identifier` is a slice id (`NNN-MM`, e.g. `112-01`) or an ADR id
    (`NNNN`, e.g. `0058`) — matched by NUMBER against `docs/specs/NNN-*` /
    `docs/decisions/adr-NNNN-*.md` on `ref`, so a renamed slug still
    resolves. `repo_root` defaults to `Path.cwd()`.

    Returns:
      - the raw status string (`"DONE"`, `"Accepted"`, `"IN_PROGRESS"`, …)
        when the identifier's file/section is present on `ref` and a status
        marker was found;
      - `ABSENT` ("absent") when `ref` is readable but the identifier's
        file is not present on it (the normal not-yet-landed case);
      - `None` when `ref` (or git itself) could not be read — offline, no
        remote, unreachable ref, not a git repo, git missing. Best-effort:
        never raises.

    `run` is an optional `(argv, cwd) -> (rc, stdout, stderr)` callable
    (mirrors `_common.reservation.scan_max_reserved_number`'s `run` param)
    so tests can intercept git without a real repository.
    """
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    git = run if run is not None else _git

    identifier = identifier.strip()
    m = _SLICE_ID_RE.match(identifier)
    if m:
        return _slice_state(git, repo_root, ref, m.group(1), m.group(2))
    m = _ADR_ID_RE.match(identifier)
    if m:
        return _adr_state(git, repo_root, ref, m.group(1))
    return None  # unrecognized identifier shape — best-effort unknown


# ---------------------------------------------------------------------------
# ADR-0058 Class C — sibling-`DONE` read (spec 112-03)
# ---------------------------------------------------------------------------
#
# `identifier_state_on_ref` (above) answers "what is N's marker on THIS ref".
# Class C needs a second question: "does ANY sibling ref hold N at an
# EVIDENCE-COMPLETE DONE" — the reported incident's actual shape (a slice
# finished, with recorded verdicts, on a branch never merged to
# `origin/main`, whose live claim was already released at DONE — so neither
# Class A (origin/main only) nor Class B (a live claim) sees it).
#
# Evidence-completeness is a SEPARATE read from the status marker: ADR-0014
# gates REVIEWED/RECONCILED/DONE on recorded verdict artifacts
# (`reviews/slice-NN-<pass>.md` / `reviews/adr-NNNN-<pass>.md`), but that gate
# validates the WORKING TREE at transition time — this reads what is
# COMMITTED ON THE REF instead (the "bridge caveat" slice 112-03's
# Assumptions flags for frame-critique). For the reported incident this
# coincides (the sibling branch landed, so its whole tree — marker AND
# evidence files — is committed there); in general a `DONE` marker without
# its evidence files committed on that exact ref is the weaker signal this
# module downgrades to a warning rather than a block (see `find_sibling_done`
# AC2's chosen posture).
#
# The baseline pass sets below are the passes ADR-0014 §5 ALWAYS requires by
# DONE (independent of a slice/ADR's optional arch/code-health/design-review
# flags, which would need parsing the sibling ref's frontmatter to resolve
# and are out of scope for a lean incident-closing check — see slice 112-03's
# judgment-call log).
_SLICE_BASELINE_EVIDENCE_PASSES = ("compliance", "craft", "reconciliation")
_ADR_BASELINE_EVIDENCE_PASSES = ("frame-critique",)


def _slice_evidence_complete(git, repo_root: Path, ref: str,
                             spec_num: str, slice_num: str) -> Optional[bool]:
    specs_rel = _specs_relpath(repo_root)
    spec_dir = _find_spec_dir(git, repo_root, ref, spec_num)
    if spec_dir is None:
        return None  # ref/repo unreadable — unknown
    if not spec_dir:
        return False  # no spec dir at all on this ref — can't be complete

    reviews_rel = f"{specs_rel}/{spec_dir}/reviews"
    rc, files = _ls_tree(git, repo_root, ref, reviews_rel)
    if rc != 0:
        return None  # ref became unreadable mid-scan — unknown
    names = set(files)
    return all(
        f"slice-{slice_num}-{p}.md" in names
        for p in _SLICE_BASELINE_EVIDENCE_PASSES
    )


def _adr_evidence_complete(git, repo_root: Path, ref: str,
                           adr_num: str) -> Optional[bool]:
    decisions_rel = _decisions_relpath(repo_root)
    adr_file = _find_adr_file(git, repo_root, ref, adr_num)
    if adr_file is None:
        return None
    if not adr_file:
        return False

    reviews_rel = f"{decisions_rel}/reviews"
    rc, files = _ls_tree(git, repo_root, ref, reviews_rel)
    if rc != 0:
        return None
    names = set(files)
    return all(
        f"adr-{adr_num}-{p}.md" in names
        for p in _ADR_BASELINE_EVIDENCE_PASSES
    )


def evidence_complete_on_ref(identifier: str, ref: str,
                             repo_root: Optional[Path] = None,
                             *, run=None) -> Optional[bool]:
    """Whether `identifier`'s BASELINE ADR-0014 review-evidence files are
    committed ON `ref` (not just its status marker — see the module-level
    note above for the ref-vs-working-tree bridge caveat).

    Returns:
      - `True` — every baseline pass file is present on `ref`.
      - `False` — `ref` is readable but at least one baseline file is
        missing (includes "no reviews dir at all" and "no spec/ADR file at
        all").
      - `None` — `ref` (or git) could not be read. Best-effort: never
        raises.

    Same `run` injection seam as `identifier_state_on_ref`.
    """
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    git = run if run is not None else _git

    identifier = identifier.strip()
    m = _SLICE_ID_RE.match(identifier)
    if m:
        return _slice_evidence_complete(git, repo_root, ref, m.group(1), m.group(2))
    m = _ADR_ID_RE.match(identifier)
    if m:
        return _adr_evidence_complete(git, repo_root, ref, m.group(1))
    return None


SiblingDone = namedtuple("SiblingDone", ["ref", "evidence_complete"])

# Per-git-call timeout (AC5 — one slow/unreachable ref must not hang the
# whole scan) and a total wall-clock budget across the whole scan (AC5 — a
# large sibling-ref set must not add up to an unbounded delay even though
# each individual call is bounded).
_SIBLING_SCAN_PER_CALL_TIMEOUT = 5
_SIBLING_SCAN_TOTAL_BUDGET = 20

_DONE_LIKE_STATES = ("DONE", "Accepted")


def _timeout_git(argv: list, cwd: Path) -> tuple:
    """Same shape as `_git`, but timeout-guarded (AC5) — the default `run`
    for `find_sibling_done`'s scan, which touches many refs in one call and
    so cannot rely on the caller supplying its own timeout."""
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, check=False,
            timeout=_SIBLING_SCAN_PER_CALL_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def _short_ref_name(refname: str) -> str:
    """`refs/heads/foo` -> `foo`; `refs/remotes/origin/foo` -> `origin/foo`
    — the short form `git` itself prints, and the form callers pass to
    `exclude_refs` / compare against `current_branch`."""
    for prefix in ("refs/heads/", "refs/remotes/"):
        if refname.startswith(prefix):
            return refname[len(prefix):]
    return refname


def find_sibling_done(identifier: str, project_dir: Optional[Path] = None, *,
                      current_branch: Optional[str] = None,
                      exclude_refs=(), run=None) -> tuple:
    """ADR-0058 Class C (spec 112-03): scan local + remote-tracking sibling
    refs for `identifier` already at a DONE-like marker (`DONE` for a
    slice, `Accepted` for an ADR) — the reported incident's shape: finished
    work on a branch that was never integrated to `origin/main`, whose live
    claim was already released at DONE (so Class A's origin/main-only read
    and Class B's live-claim read both miss it).

    Reuses `_common.reservation.list_branch_refs`'s `for-each-ref`
    enumeration (local `refs/heads/*` + remote-tracking `refs/remotes/*` —
    the same plumbing ADR-0053's number scan built; this is its THIRD
    reader, which is what earned the extraction into a shared name — see
    `list_branch_refs`'s docstring) and this module's own
    `identifier_state_on_ref` / `evidence_complete_on_ref` per-ref content
    reads.

    EXCLUDES (never treated as a "sibling"):
      - the current branch itself (`refs/heads/<current_branch>`);
      - its own remote-tracking ref, ANY remote (`refs/remotes/*/<current_branch>`);
      - every refname/short-name in `exclude_refs` — callers pass the
        Class-A base ref (e.g. `origin/main`) here, since that ref is
        already covered by `_refuse_integrated_advance` /
        `_refuse_start_collision`; ADR-0058 defines Class C as the
        NOT-on-`main` case, so re-matching `origin/main` here would blur
        the two classes' boundary, not just duplicate work.

    Returns `(hit, warnings)`:
      - `hit` — `None`, or a `SiblingDone(ref, evidence_complete=True)`
        namedtuple for the FIRST ref (scan order: local branches before
        remote-tracking, then lexicographic short-name) found
        EVIDENCE-COMPLETE (see `evidence_complete_on_ref`). A DONE-marker
        hit whose evidence files are NOT committed on that ref is the
        weaker signal (AC2's bridge caveat) and is downgraded to a warning
        rather than returned as a hit — the scan keeps going past it, so a
        later evidence-complete ref still wins.
      - `warnings` — human-readable strings for: (a) any individual ref
        whose state/evidence read failed (unreachable / timed out — AC5);
        (b) any marker-only DONE hit found along the way; (c) a
        scan-truncation notice if the wall-clock budget
        (`_SIBLING_SCAN_TOTAL_BUDGET`) was exceeded before every candidate
        ref was checked. A ref-ENUMERATION failure (not a git repo at all,
        or git unavailable) is SILENT — `(None, [])` — mirroring
        `workflow.py`'s `_origin_slice_state` "no-origin" convention: an
        unset-up / non-git checkout is the routine case, not an error,
        distinct from an individual ref failing AFTER enumeration
        succeeded.

    Never raises. `run` is the same `(argv, cwd) -> (rc, stdout, stderr)`
    injection seam as `identifier_state_on_ref`; when omitted, defaults to
    a TIMEOUT-GUARDED runner (`_timeout_git`, distinct from
    `identifier_state_on_ref`'s un-timed default) because this function
    touches many refs in one call.
    """
    project_dir = Path(project_dir) if project_dir is not None else Path.cwd()
    git = run if run is not None else _timeout_git

    rc, refs = list_branch_refs(project_dir, run=git)
    if rc != 0:
        # `for-each-ref` itself failed — overwhelmingly "this directory is
        # not (yet) a git repository at all" (a brand-new local-only
        # project, or a fixture with no `.git`), the exact scenario
        # `_origin_slice_state`'s "no-origin" branch treats as silent
        # elsewhere in `workflow.py`. SILENT by the same convention: this
        # is the routine case, not an error, and it must not make every
        # transition in a non-git checkout noisy. Distinct from AC5's
        # "unreachable remote ref" warning below, which fires only once
        # enumeration has already succeeded and an INDIVIDUAL ref's content
        # read then fails.
        return None, []

    exclude = {str(r) for r in exclude_refs}
    candidates = []
    for refname in refs:
        short = _short_ref_name(refname)
        # `refs/remotes/<remote>/HEAD` is a symbolic pointer to that
        # remote's default branch (e.g. `origin/HEAD` -> `origin/main`), not
        # an independent sibling — scanning it would report a phantom
        # duplicate hit for whatever `origin/main` already resolves to.
        if short == "HEAD" or short.endswith("/HEAD"):
            continue
        if current_branch and (
            short == current_branch
            or short.endswith("/" + current_branch)
        ):
            continue
        if short in exclude or refname in exclude:
            continue
        candidates.append((short, refname))
    # Deterministic scan order: local branches before remote-tracking refs,
    # then lexicographic by short name.
    candidates.sort(
        key=lambda pair: (0 if pair[1].startswith("refs/heads/") else 1, pair[0])
    )

    warnings = []
    checked = 0
    started = time.monotonic()
    for short, refname in candidates:
        if time.monotonic() - started > _SIBLING_SCAN_TOTAL_BUDGET:
            warnings.append(
                "warning: sibling-ref scan stopped early (time budget "
                f"exceeded) after checking {checked} ref(s) — some sibling "
                "branches were not checked"
            )
            break
        checked += 1
        state = identifier_state_on_ref(identifier, refname,
                                        repo_root=project_dir, run=git)
        if state is None:
            warnings.append(
                f"warning: could not read sibling ref {short!r} "
                "(unreachable or timed out) — skipped"
            )
            continue
        if state not in _DONE_LIKE_STATES:
            continue
        evidence = evidence_complete_on_ref(identifier, refname,
                                            repo_root=project_dir, run=git)
        if evidence:
            return SiblingDone(short, True), warnings
        if evidence is None:
            warnings.append(
                f"warning: could not read review-evidence files for "
                f"sibling ref {short!r} (unreachable or timed out) — "
                "treating its DONE marker as not evidence-complete"
            )
        else:
            warnings.append(
                f"warning: sibling ref {short!r} has identifier {identifier} "
                f"at {state!r}, but its recorded review-evidence files are "
                "not present on that ref — not treated as evidence-complete, "
                "so not blocking"
            )
    return None, warnings


# ---------------------------------------------------------------------------
# ADR-0058 Class B — sibling foreign-`IN_PROGRESS`-claim read (spec 112-05)
# ---------------------------------------------------------------------------
#
# `_refuse_start_collision` (workflow.py, slice 051-04) already hard-blocks a
# `→ IN_PROGRESS` transition when BOTH ends are `IN_PROGRESS` — but it only
# ever reads `origin/main`. Class B (ADR-0058, item 3) *extends the read
# scope* of that SAME block to every OTHER sibling/remote-tracking ref (a
# same-machine worktree on a different branch, or a peer's pushed feature
# branch never merged to `origin/main`) — it does NOT change *when* the halt
# fires (still exactly `status == IN_PROGRESS` + a foreign `claimed_by`).
#
# This is a SECOND per-ref scan reusing the SAME enumeration/exclusion/
# timeout-budget shape as `find_sibling_done` (Class C, above) — for a
# DIFFERENT hit condition (a foreign `IN_PROGRESS` claim, not an
# evidence-complete `DONE`), which is why it is a sibling function rather
# than a parameterization of `find_sibling_done` itself: the two conditions
# read different fields (`claimed_by` vs review-evidence files) and have
# different "what counts as a hit" semantics. Per the refinement-todo
# "unify the cross-ref guard family" trigger (now touched by THIS slice),
# converging the READ here onto this shared module — rather than adding a
# bespoke sibling scan inline in `workflow.py` — is the deliberate choice
# that keeps the guard family at four divergent SITES (unchanged) without
# adding a fifth divergent READ implementation; the full guard-preamble
# unification itself remains the documented, deferred residual.

SiblingClaim = namedtuple("SiblingClaim", ["ref", "claimed_by"])

_IN_PROGRESS_STATE = "IN_PROGRESS"


def find_sibling_in_progress_claim(identifier: str,
                                   project_dir: Optional[Path] = None, *,
                                   current_branch: Optional[str] = None,
                                   exclude_refs=(), run=None) -> tuple:
    """ADR-0058 Class B (spec 112-05): scan local + remote-tracking sibling
    refs for `identifier` (a slice `NNN-MM` id — ADRs carry no claim) already
    `IN_PROGRESS` under a foreign `claimed_by`.

    EXCLUDES the same three things `find_sibling_done` does: the current
    branch, its own remote-tracking ref on any remote, and every ref/short
    name in `exclude_refs` (callers pass `{"origin/main"}` — that ref is
    Class A/`_refuse_start_collision`'s own territory, already checked).

    Returns `(hit, warnings)`:
      - `hit` — `None`, or the FIRST `SiblingClaim(ref, claimed_by)` found
        (scan order: local branches before remote-tracking, then
        lexicographic short name — same determinism as `find_sibling_done`).
      - `warnings` — human-readable strings for any ref whose read failed
        (unreachable/timed out) or a scan-truncation notice. Ref-
        ENUMERATION failure is SILENT (`(None, [])`) — the same "not a git
        repo yet" convention `find_sibling_done` uses.

    Never raises. Same `run` injection seam / default timeout-guarded
    runner (`_timeout_git`) as `find_sibling_done`, and the SAME
    `_SIBLING_SCAN_PER_CALL_TIMEOUT` / `_SIBLING_SCAN_TOTAL_BUDGET` budgets
    (AC6 — a large/slow sibling-ref set must not hang the transition)."""
    project_dir = Path(project_dir) if project_dir is not None else Path.cwd()
    git = run if run is not None else _timeout_git

    m = _SLICE_ID_RE.match(identifier.strip())
    if not m:
        return None, []  # not a slice id (e.g. an ADR) — no claim concept
    spec_num, slice_num = m.group(1), m.group(2)

    rc, refs = list_branch_refs(project_dir, run=git)
    if rc != 0:
        return None, []

    exclude = {str(r) for r in exclude_refs}
    candidates = []
    for refname in refs:
        short = _short_ref_name(refname)
        if short == "HEAD" or short.endswith("/HEAD"):
            continue
        if current_branch and (
            short == current_branch
            or short.endswith("/" + current_branch)
        ):
            continue
        if short in exclude or refname in exclude:
            continue
        candidates.append((short, refname))
    candidates.sort(
        key=lambda pair: (0 if pair[1].startswith("refs/heads/") else 1, pair[0])
    )

    warnings = []
    checked = 0
    started = time.monotonic()
    for short, refname in candidates:
        if time.monotonic() - started > _SIBLING_SCAN_TOTAL_BUDGET:
            warnings.append(
                "warning: sibling claim-scan stopped early (time budget "
                f"exceeded) after checking {checked} ref(s) — some sibling "
                "branches were not checked"
            )
            break
        checked += 1
        result = _slice_claim(git, project_dir, refname, spec_num, slice_num)
        if result is None:
            warnings.append(
                f"warning: could not read sibling ref {short!r} "
                "(unreachable or timed out) — skipped"
            )
            continue
        status, claimed_by = result
        if status == _IN_PROGRESS_STATE and claimed_by:
            return SiblingClaim(short, claimed_by), warnings
    return None, warnings
