"""
jig adr-workflow helper — slice 005-01 (adr-helper) + 005-02 (supersede)
+ 008-03 (ADR-0004 shape).

Deterministic ADR lifecycle helper:
  - `new`          : scaffold a new ADR from the template, auto-numbered.
  - `accept`       : flip Status from Proposed to Accepted (atomic write).
  - `supersede`    : append Superseded-by / Supersedes lines to two
                     already-Accepted ADRs (the one edit allowed on an
                     accepted ADR per the Nygard convention).
  - `index`        : regenerate the `## Index` section of
                     docs/decisions/README.md.
  - `resolve-todo` : strike through a refinement-todo entry and link the
                     resolving ADR.

Mirrors the shape of workflow.py / review.py / memory.py / scaffold.py.

Usage:
    python3 adr.py new <slug> [--title "<Title>"]
    python3 adr.py accept <NNNN>
    python3 adr.py supersede <old-NNNN> <new-NNNN>
    python3 adr.py index <decisions-dir>
    python3 adr.py resolve-todo <NNNN> "<heading fragment>"

Run from the project root that contains `docs/decisions/` (for `new`,
`accept`, `supersede`, `resolve-todo`); `index` takes an explicit
`<decisions-dir>` argument. Files are named `adr-NNNN-<slug>.md` per
ADR-0004.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import project_layout, subtree
from _common import review_evidence as _evidence
from _common.atomic_io import atomic_write_text
from _common.parsing import frontmatter_flag_truthy as _frontmatter_flag_truthy
from _common.parsing import parse_frontmatter as _parse_frontmatter
from _common.parsing import set_frontmatter_field as _set_frontmatter_field
from _common.scaffold_state import classify_scaffold_state
from _common.scaffold_state import precondition_enabled as _scaffold_precondition_enabled


class AdrError(RuntimeError):
    """User-facing error; CLI exits with status 2."""


# Template/placeholder constants — kept in module scope so tests can read them.
PLACEHOLDER_NUMBER = "{{NUMBER}}"
PLACEHOLDER_TITLE = "{{TITLE}}"
PLACEHOLDER_DATE = "{{DATE}}"

TEMPLATE_RELATIVE = (
    Path("templates") / "docs" / "decisions" / "adr-0000-template.md"
)


# ---------- shared helpers ----------


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _template_path() -> Path:
    return _plugin_root() / TEMPLATE_RELATIVE


def _adr_files(adrs_dir: Path) -> list:
    """Return sorted list of `adr-NNNN-*.md` files under `adrs_dir`,
    excluding README.md. Files whose basename does not start with
    `adr-NNNN-` are also excluded (per ADR-0004's canonical shape)."""
    if not adrs_dir.is_dir():
        return []
    out = []
    for p in sorted(adrs_dir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        if not re.match(r"^adr-\d{4}-", p.name):
            continue
        out.append(p)
    return out


def _parse_adr_number(filename: str) -> int:
    m = re.match(r"^adr-(\d{4})-", filename)
    if not m:
        raise AdrError(
            f"file does not start with `adr-NNNN-` prefix: {filename}"
        )
    return int(m.group(1))


def _slug_to_title(slug: str) -> str:
    """`my-decision` → `My Decision`. Empty/edge-case slugs are passed through."""
    parts = [p for p in re.split(r"[-_]", slug) if p]
    return " ".join(p[0].upper() + p[1:] if p else p for p in parts)


def _check_slug_collision(existing: list, slug: str) -> None:
    """Raise AdrError if any `existing` ADR file already uses `slug` as
    its body (NNNN-<slug>). Shared by `cmd_new` and `reserve_adr` — both
    paths must refuse the same collisions."""
    for p in existing:
        # Strip leading "adr-NNNN-" prefix (9 chars).
        body = p.stem[9:] if len(p.stem) > 9 else ""
        if body == slug:
            raise AdrError(f"slug collision: {p.name} already exists")


def _render_adr_content(template_text: str, number: str, title: str,
                        today_iso: str) -> str:
    """Apply the three template placeholders. Shared by `cmd_new` and
    `reserve_adr` so the rendered shape stays consistent across both.

    Slice 064-05 (ADR-0020 OQ3 — ADRs always-on): stamp `frame_review: true`
    into the new ADR's frontmatter at creation. The ADR template (064-02)
    doesn't carry the flag; every newly-created ADR gets it here so the
    `adr.py accept` gate (gated on a truthy `frame_review`) always applies
    going forward. Legacy ADRs without the marker are NOT gated (the grace
    path)."""
    content = template_text.replace(PLACEHOLDER_NUMBER, number)
    content = content.replace(PLACEHOLDER_TITLE, title)
    content = content.replace(PLACEHOLDER_DATE, today_iso)
    content = _set_frontmatter_field(content, "frame_review", "true")
    # Slice 073-02 (ADR-0026): `status: Proposed` is NOT stamped here — it
    # comes from the template's frontmatter, so a new ADR inherits it in the
    # same single atomic write as the prose `Proposed (date)` line. (Contrast
    # `frame_review`, stamped above because the 064-02 template omits it.)
    return content


# ---------- new ----------


def cmd_new(adrs_dir: Path, slug: str, title: str) -> Path:
    """Scaffold `docs/decisions/adr-NNNN-<slug>.md` from the template."""
    _validate_slug(slug)
    if not adrs_dir.is_dir():
        raise AdrError(f"decisions directory not found: {adrs_dir}")

    template = _template_path()
    if not template.is_file():
        raise AdrError(f"template not found: {template}")

    existing = _adr_files(adrs_dir)
    _check_slug_collision(existing, slug)

    # Auto-number: max existing + 1, or 1 if none. Zero-padded to 4 digits.
    if existing:
        next_n = max(_parse_adr_number(p.name) for p in existing) + 1
    else:
        next_n = 1
    number = f"{next_n:04d}"

    if not title:
        title = _slug_to_title(slug)

    content = _render_adr_content(template.read_text(), number, title,
                                  _today())

    target = adrs_dir / f"adr-{number}-{slug}.md"
    # Slice 005-01 deviation #7 cleanup (005-02): auto-numbering + the
    # slug-collision refusal above guarantee `target` is fresh. Downgraded
    # from a raise-AdrError to an assert so the unreachable branch is
    # explicit about its postcondition status.
    assert not target.exists(), f"target unexpectedly exists: {target}"
    atomic_write_text(target, content)
    return target


# ---------- Slice 028-01: reserve-adr-on-main ----------
# Inline-mirror of workflow.py 003-03 helpers per ADR-0002's "three-callers
# triggers extraction" rule (ADR-0003 applied that rule to find_slice_section
# — this is the same precedent, two callers, extraction deferred). Mirrored:
# _PUSH_PROTECTION_SIGNALS, _PUSH_RACE_SIGNALS, _run, _classify_push_failure,
# _current_branch, _refuse_if_dirty, _check_gh_and_remote, _do_pr_fallback,
# _build_pr_body. `_validate_slug` is shared with cmd_new and uses adr.py's
# looser `^[a-z0-9][a-z0-9-]*$` regex (intentionally divergent from
# workflow.py's `^[a-z][a-z0-9-]*$` so existing digit-prefixed ADR slugs
# don't silently break).

_PUSH_PROTECTION_SIGNALS = (
    "protected branch",
    "permission denied",
    "pre-receive hook declined",
    "not authorized",
    "cannot lock ref",
)

_PUSH_RACE_SIGNALS = (
    "non-fast-forward",
    "fetch first",
    "[rejected]",
    "rejected",
)


def _run(argv: list, cwd: Path) -> tuple:
    """Run a subprocess and return (returncode, stdout, stderr).

    Uses module-level `subprocess.run` so tests can patch it via
    `patch.object(_adr, "subprocess")`. Inline-mirror of workflow.py's
    `_run` (slice 003-03) per ADR-0002's three-callers rule."""
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, cwd=str(cwd),
        )
    except FileNotFoundError:
        return 127, "", f"{argv[0]}: not found on PATH"
    return result.returncode, result.stdout or "", result.stderr or ""


def _classify_push_failure(stderr: str) -> str:
    """Classify a `git push origin main` stderr into one of:
      - "protection" — protected branch / permission denied / ...
      - "race" — non-fast-forward / fetch first / rejected
      - "other" — anything else

    Race wins over protection if both appear (race recovery requires the
    stranded commit drop)."""
    low = stderr.lower()
    for sig in _PUSH_RACE_SIGNALS:
        if sig in low:
            return "race"
    for sig in _PUSH_PROTECTION_SIGNALS:
        if sig in low:
            return "protection"
    return "other"


def _validate_slug(slug: str) -> None:
    """Raise AdrError naming both the slug and the violated rule. The
    check happens BEFORE any mutation (preflight or git call).

    The regex (`^[a-z0-9][a-z0-9-]*$`) deliberately accepts a leading
    digit — intentionally looser than workflow.py's `^[a-z][a-z0-9-]*$`."""
    if not slug:
        raise AdrError(
            "invalid slug: empty (use lowercase letters, digits, hyphens)"
        )
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise AdrError(
            f"invalid slug: {slug!r} (use lowercase letters, digits, "
            f"hyphens; must start with a letter or digit)"
        )


def _refuse_if_dirty(project_dir: Path) -> None:
    """Refuse if the worktree has uncommitted changes. The on-main
    reservation path commits on local `main`, so it must start clean.

    The branch==main check that used to live here moved to the
    `_current_branch` dispatch in `reserve_adr` (see the worktree-aware
    reservation block) so off-main callers route to the detached-worktree
    path instead of being refused. Mirrors workflow.py."""
    rc, stdout, _stderr = _run(
        ["git", "status", "--porcelain"], cwd=project_dir,
    )
    if rc != 0:
        # Non-fatal if status itself fails; downstream git will fail anyway.
        return
    if stdout.strip():
        raise AdrError(
            "refusing: working tree has uncommitted changes (rule: "
            "clean worktree required). Run `git status` to see them, "
            "then stash or commit before reserving."
        )


def _check_gh_and_remote(project_dir: Path) -> None:
    """PR-fallback prereqs: `gh` on PATH AND `origin` URL contains
    `github.com`."""
    if shutil.which("gh") is None:
        raise AdrError(
            "refusing PR-fallback: 'gh' CLI not found on PATH. "
            "Install GitHub CLI (https://cli.github.com/) or re-run "
            "with `--no-push` to commit locally only."
        )
    rc, stdout, stderr = _run(
        ["git", "config", "--get", "remote.origin.url"], cwd=project_dir,
    )
    if rc != 0 or not stdout.strip():
        raise AdrError(
            "refusing PR-fallback: no 'origin' remote configured "
            f"(git: {stderr.strip() or 'empty url'})"
        )
    url = stdout.strip()
    if "github.com" not in url:
        raise AdrError(
            f"refusing PR-fallback: remote 'origin' does not point at "
            f"github.com (url: {url}). PR-fallback requires a GitHub "
            f"remote; re-run with `--no-push` for local-only commit."
        )


def _build_pr_body(number: str, slug: str) -> str:
    """Compose a PR body explaining the reservation. Mirrors the shape
    of workflow.py 003-03's _build_pr_body but references spec 028-01."""
    return (
        f"Reserves ADR number `{number}` for slug `{slug}` on the "
        f"shared trunk, so parallel worktrees cannot both claim the "
        f"same `NNNN`.\n"
        f"\n"
        f"This PR adds the scaffold `docs/decisions/adr-{number}-{slug}.md` "
        f"(Status: Proposed; sections per ADR-0004). The actual decision "
        f"body will be drafted in a separate feature branch.\n"
        f"\n"
        f"Generated by `adr.py new {slug}` "
        f"(see spec 028-01 adr-numbering-on-main for rationale).\n"
    )


def _do_pr_fallback(project_dir: Path, branch_name: str,
                    number: str, slug: str, pr_body: str) -> None:
    """Branch-and-PR sequence. Any step's failure aborts and surfaces
    what state the user's repo is left in.

    Sequence (inline-mirror of workflow.py 003-03 _do_pr_fallback):
      1. git branch <branch> HEAD
      2. git reset --hard origin/main
      3. git checkout <branch>
      4. git push -u origin <branch>
      5. gh pr create --title ... --body ...
    """
    _check_gh_and_remote(project_dir)

    # 1. Create the branch at the reservation commit.
    rc, _out, err = _run(
        ["git", "branch", branch_name, "HEAD"], cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback failed at `git branch {branch_name} HEAD`: "
            f"{err.strip()}. The reservation commit is still on local main; "
            f"re-run after fixing, or `git reset --hard origin/main` to drop it."
        )

    # 2. Reset local main so it no longer carries the stranded commit.
    rc, _out, err = _run(
        ["git", "reset", "--hard", "origin/main"], cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback failed at `git reset --hard origin/main`: "
            f"{err.strip()}. The reservation commit lives on local "
            f"{branch_name!r}; check `git log {branch_name}` to confirm "
            f"before pushing manually."
        )

    # 3. Switch to the reservation branch.
    rc, _out, err = _run(
        ["git", "checkout", branch_name], cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback failed at `git checkout {branch_name}`: "
            f"{err.strip()}. The branch exists locally; switch to it "
            f"manually with `git checkout {branch_name}`."
        )

    # 4. Push the branch to origin.
    rc, _out, err = _run(
        ["git", "push", "-u", "origin", branch_name], cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback failed at `git push -u origin {branch_name}`: "
            f"{err.strip()}. The reservation commit lives on local "
            f"{branch_name!r}; push manually once the remote allows it."
        )

    # 5. Open the PR.
    title = f"docs(decisions): reserve adr-{number}-{slug}"
    rc, out, err = _run(
        ["gh", "pr", "create", "--title", title, "--body", pr_body],
        cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback failed at `gh pr create`: {err.strip()}. "
            f"The branch is already pushed to origin/{branch_name}; "
            f"open the PR manually via the GitHub web UI."
        )
    pr_url = out.strip()
    if pr_url:
        print(pr_url)


# ---------- Worktree-aware reservation (prototype) ----------
#
# Inline-mirror of workflow.py's worktree-aware reservation (per ADR-0002's
# two-caller rule). The flow above commits on local `main` then pushes
# `origin main`, which requires BEING on `main` — impossible from a linked
# worktree (it can't check out `main`; the primary worktree holds it). The
# helpers below build the reservation commit in an EPHEMERAL DETACHED
# worktree checked out at origin/main, then push `HEAD:main`, so reservation
# works from any branch or worktree without touching the caller's checkout.


def _current_branch(project_dir: Path):
    """Return the current branch name, or None if detached / undeterminable."""
    rc, out, _err = _run(
        ["git", "symbolic-ref", "--short", "HEAD"], cwd=project_dir,
    )
    if rc != 0:
        return None
    return out.strip() or None


def _print_draft_hint(number: str, slug: str) -> None:
    """The reservation lands on origin/main, not in the caller's branch.
    Tell them how to pull it in (stderr — keeps the stdout contract clean)."""
    sys.stderr.write(
        f"note: reservation adr-{number}-{slug} lives on origin/main, not in "
        f"your current branch. To draft it here:\n"
        f"    git fetch origin main && git merge origin/main\n"
        f"then edit docs/decisions/adr-{number}-{slug}.md\n"
    )


def _reserve_local_on_current_branch(slug: str, project_dir: Path,
                                     adrs_dir: Path, title: str) -> int:
    """`--no-push` from off-main: commit a provisional reservation stub to
    the CURRENT branch. The number is computed from the local working tree,
    so it is PROVISIONAL — use the default (push) mode to claim it for real
    on origin/main."""
    existing = _adr_files(adrs_dir)
    _check_slug_collision(existing, slug)
    next_n = (max(_parse_adr_number(p.name) for p in existing) + 1
              if existing else 1)
    number = f"{next_n:04d}"
    if not title:
        title = _slug_to_title(slug)
    template = _template_path()
    if not template.is_file():
        raise AdrError(f"template not found: {template}")
    content = _render_adr_content(template.read_text(), number, title,
                                  _today())
    target = adrs_dir / f"adr-{number}-{slug}.md"
    if target.exists():
        raise AdrError(f"target already exists: {target}")
    # Spec 066-01: the scaffold-state precondition replaced the top-level
    # `adrs_dir.is_dir()` guard, so ensure docs/decisions/ exists before the
    # atomic write (a scaffold.json-bearing project need not already have it;
    # mirrors the detached-worktree path's mkdir).
    adrs_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, content)
    rel_path = f"docs/decisions/adr-{number}-{slug}.md"
    rc, _out, err = _run(["git", "add", rel_path], cwd=project_dir)
    if rc != 0:
        raise AdrError(
            f"`git add {rel_path}` failed: {err.strip()}. "
            f"The stub ADR file is on disk; stage and commit manually."
        )
    # Pathspec-limited commit so unrelated staged work can't leak in.
    rc, _out, err = _run(
        ["git", "commit", "-m",
         f"docs(decisions): reserve adr-{number}-{slug}", "--", rel_path],
        cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"`git commit` failed: {err.strip()}. "
            f"The stub ADR file is staged; commit manually."
        )
    print(f"reserved adr-{number}-{slug} (local provisional — not yet on "
          f"origin/main)")
    print(str(target.resolve()))
    return 0


def _pr_fallback_from_worktree(sha: str, project_dir: Path,
                               reserve_branch: str, number: str,
                               slug: str, pr_body: str) -> None:
    """Protected-branch fallback for the detached-worktree path: push the
    detached reservation commit (BY SHA, from `project_dir` so a relative
    `origin` URL resolves) straight to a new remote branch and open the PR
    (no local `main` to un-strand). Mirrors workflow.py."""
    _check_gh_and_remote(project_dir)
    rc, _out, err = _run(
        ["git", "push", "origin", f"{sha}:refs/heads/{reserve_branch}"],
        cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback push to {reserve_branch!r} failed: {err.strip()}. "
            f"The reservation commit exists only in the reservation "
            f"worktree; re-run to retry."
        )
    title = f"docs(decisions): reserve adr-{number}-{slug}"
    rc, out, err = _run(
        ["gh", "pr", "create", "--title", title, "--body", pr_body,
         "--head", reserve_branch, "--base", "main"],
        cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"PR-fallback `gh pr create` failed: {err.strip()}. "
            f"Branch origin/{reserve_branch} is pushed; open the PR "
            f"manually via the GitHub web UI."
        )
    pr_url = out.strip()
    if pr_url:
        print(pr_url)


def _reserve_via_detached_worktree(slug: str, project_dir: Path,
                                   title: str, pr_mode: bool = False) -> int:
    """Push-mode ADR reservation that works from ANY branch or worktree.
    Claims the next free ADR number on origin/main by building the
    reservation commit in an ephemeral detached worktree checked out at
    origin/main, then pushing `HEAD:main`. Mirrors workflow.py."""
    rc, _out, err = _run(["git", "fetch", "origin", "main"], cwd=project_dir)
    if rc != 0:
        sys.stderr.write(
            f"warning: `git fetch origin main` failed: {err.strip()}; "
            f"proceeding with the local origin/main view\n"
        )

    wt = Path(tempfile.mkdtemp(prefix="jig-reserve-adr-"))
    try:
        rc, _out, err = _run(
            ["git", "worktree", "add", "--detach", str(wt), "origin/main"],
            cwd=project_dir,
        )
        if rc != 0:
            raise AdrError(
                f"could not create the ephemeral reservation worktree at "
                f"origin/main ({err.strip()}). Most likely there is no "
                f"origin/main to reserve against — use `--no-push` for a "
                f"local provisional reservation, or run from a clone with "
                f"an 'origin' remote."
            )

        adrs_dir = wt / "docs" / "decisions"
        existing = _adr_files(adrs_dir)
        _check_slug_collision(existing, slug)
        next_n = (max(_parse_adr_number(p.name) for p in existing) + 1
                  if existing else 1)
        number = f"{next_n:04d}"
        if not title:
            title = _slug_to_title(slug)
        template = _template_path()
        if not template.is_file():
            raise AdrError(f"template not found: {template}")
        content = _render_adr_content(template.read_text(), number, title,
                                      _today())
        target = adrs_dir / f"adr-{number}-{slug}.md"
        if target.exists():
            raise AdrError(
                f"refusing: adr-{number}-{slug} already exists on origin/main."
            )
        # origin/main may not have docs/decisions/ yet (reserving the very
        # first ADR); the stub lands directly in it, so ensure it exists.
        adrs_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target, content)
        rel_path = f"docs/decisions/adr-{number}-{slug}.md"
        rc, _out, err = _run(["git", "add", rel_path], cwd=wt)
        if rc != 0:
            raise AdrError(
                f"`git add` in the reservation worktree failed: {err.strip()}."
            )
        rc, _out, err = _run(
            ["git", "commit", "-m",
             f"docs(decisions): reserve adr-{number}-{slug}"],
            cwd=wt,
        )
        if rc != 0:
            raise AdrError(
                f"`git commit` in the reservation worktree failed: "
                f"{err.strip()}."
            )
        print(f"reserved adr-{number}-{slug}")

        # Resolve the reservation commit's SHA so we can push it BY SHA from
        # `project_dir`. Pushing from `wt` would resolve a RELATIVE `origin`
        # URL against the temp dir and fail; the commit's objects live in the
        # shared object store, so its SHA is reachable from `project_dir`,
        # where the `origin` remote-name resolves correctly.
        rc, sha, err = _run(["git", "rev-parse", "HEAD"], cwd=wt)
        if rc != 0 or not sha.strip():
            raise AdrError(
                f"could not resolve the reservation commit SHA ({err.strip()}); "
                f"the ephemeral worktree will be removed."
            )
        sha = sha.strip()

        pr_body = _build_pr_body(number, slug)
        reserve_branch = f"reserve/adr-{number}-{slug}"

        if pr_mode:
            _pr_fallback_from_worktree(
                sha, project_dir, reserve_branch, number, slug, pr_body,
            )
            _print_draft_hint(number, slug)
            return 0

        rc, _out, err = _run(
            ["git", "push", "origin", f"{sha}:refs/heads/main"],
            cwd=project_dir,
        )
        if rc == 0:
            print(f"reserved adr-{number}-{slug} on origin/main")
            _print_draft_hint(number, slug)
            return 0

        kind = _classify_push_failure(err)
        if kind == "race":
            # No `reset --hard HEAD~1` needed: the stranded commit lives
            # only in the worktree the `finally` removes.
            sys.stderr.write(
                f"race detected: origin/main advanced during reservation. "
                f"Re-run 'adr.py new {slug}' to pick the next free number.\n"
            )
            raise AdrError(f"race-on-push: {err.strip()}")

        if kind == "protection":
            sys.stderr.write(
                f"direct push refused ({err.strip()}); falling back to "
                f"PR mode...\n"
            )
            _pr_fallback_from_worktree(
                sha, project_dir, reserve_branch, number, slug, pr_body,
            )
            _print_draft_hint(number, slug)
            return 0

        raise AdrError(
            f"`git push origin {sha}:refs/heads/main` failed: {err.strip()} "
            f"(the reservation commit lived only in the reservation "
            f"worktree, which has been removed; inspect and re-run)."
        )
    finally:
        _run(["git", "worktree", "remove", "--force", str(wt)],
             cwd=project_dir)
        shutil.rmtree(wt, ignore_errors=True)
        # Prune any stale .git/worktrees/ admin entry so it can't accumulate
        # if `worktree remove` ever failed above.
        _run(["git", "worktree", "prune"], cwd=project_dir)


def reserve_adr(slug: str, project_dir: Path, title: str = "",
                no_push: bool = False, pr_mode: bool = False) -> int:
    """Slice 028-01 entry point. Reserve the next free ADR number by
    committing a stub `adr-NNNN-<slug>.md` and (by default) pushing it
    to origin/main. PR-fallback when direct push is refused; race-on-
    push surfaces as a re-run instruction (no auto-renumber).

    Returns the intended process exit code (0 on success). Raises
    AdrError for refusals — main() converts these to exit 2.
    """
    # Bad slug refuses BEFORE any git invocation (parity with
    # workflow.py 003-03 AC #5).
    _validate_slug(slug)

    adrs_dir = project_layout.decisions_dir(project_dir)

    # Spec 066-01: scaffold-state PRECONDITION (the ADR-creation sibling of
    # 063-01's spec-creation gate). Replaces the weak, dead-end
    # `docs/decisions/`-presence check with the three-way, scaffold.json-first
    # classification that ROUTES an unscaffolded project to the right setup
    # skill instead of refusing into a dead end (ADR-0011 / ADR-0013:
    # route-don't-block; jig redirects, the user/agent acts — it never runs
    # scaffold-init / migrate on the user's behalf). `project_dir` is the repo
    # root the reserve flow already threads (for `_refuse_if_dirty` etc.); the
    # shared classifier reads its `scaffold.json` sentinel + trigger predicate.
    #
    # Consumes the 063-01 helper UNCHANGED (no second classifier, no
    # trigger-counting here — spec 066 non-goal). The bypass
    # (`JIG_SCAFFOLD_PRECONDITION=0|false|off|no`) is a deliberateness signal,
    # not human-only enforcement: when set it skips classification and
    # preserves TODAY's behavior, including the legacy weak
    # `docs/decisions/`-absent refusal below. One env var governs both the
    # spec (063) and ADR (066) doors.
    if _scaffold_precondition_enabled():
        state = classify_scaffold_state(project_dir)
        if state == "greenfield":
            raise AdrError(
                f"refusing: {project_dir} is not a scaffolded jig project "
                f"(detected state: greenfield — no scaffold.json and no "
                f"spec-driven layout). Run `/jig:scaffold-init` to set jig "
                f"up here first, then re-run `new`."
            )
        if state == "adoptable":
            raise AdrError(
                f"refusing: {project_dir} is not a scaffolded jig project "
                f"(detected state: adoptable — a spec-driven layout exists "
                f"but no scaffold.json). Run `/jig:migrate` to adopt it into "
                f"jig first, then re-run `new`."
            )
        # state == "scaffolded": fall through to the existing reserve flow
        # unchanged (number computation, stub write, commit, push routing).
    else:
        # Bypass active — preserve today's behavior, including the legacy
        # weak refusal so a deliberate actor sees identical output.
        if not adrs_dir.is_dir():
            raise AdrError(
                f"refusing: docs/decisions/ not found under {project_dir} "
                f"(not inside a scaffolded jig project)"
            )

    # Slice 084-03 (AC5): refuse PUSH-mode ADR reservation in a track-local
    # subtree — parity with workflow.py `new` (the same shared-`main` /
    # wrong-root failure applies to `adr new --push`). Shared detection in
    # `_common.subtree`; this door raises AdrError. Local mode is unaffected.
    if not no_push:
        found = subtree.detect_subtree(project_dir)
        if found is not None:
            repo_root, subproject_root = found
            raise AdrError(
                f"subtree push-mode unsupported: {project_dir} is a track-local "
                f"subproject (root {subproject_root}) inside git repo "
                f"{repo_root}. Push-mode reservation would reserve against a "
                f"shared main — use local mode (--no-push). Subtree push is a "
                f"spec 084 non-goal."
            )

    # Worktree-aware routing (prototype): the original flow below REQUIRES
    # being on `main`. A linked worktree can't check out `main`, so route
    # off-main callers to the detached-worktree path (push) or a
    # current-branch commit (`--no-push`). On `main`, the existing 028-01
    # flow runs unchanged. Mirrors workflow.py.
    if _current_branch(project_dir) != "main":
        if no_push:
            return _reserve_local_on_current_branch(
                slug, project_dir, adrs_dir, title,
            )
        return _reserve_via_detached_worktree(
            slug, project_dir, title, pr_mode=pr_mode,
        )

    # On `main`: enforce a clean tree (the commit lands on local main).
    # The branch check already happened at the dispatch above.
    _refuse_if_dirty(project_dir)

    # Fetch origin/main so the next-number scan + slug-collision check
    # reflect the freshest state. Skipped for --no-push.
    if not no_push:
        rc, _out, err = _run(
            ["git", "fetch", "origin", "main"], cwd=project_dir,
        )
        # A failed fetch isn't fatal — we proceed with the local view.
        # The push step catches any out-of-date condition via the
        # race-on-push classifier.
        if rc != 0:
            sys.stderr.write(
                f"warning: `git fetch origin main` failed: "
                f"{err.strip()}; proceeding with local view\n"
            )

    # Slug-collision check runs AFTER fetch (collision view is freshest)
    # but BEFORE writing the new file.
    existing = _adr_files(adrs_dir)
    _check_slug_collision(existing, slug)

    # Auto-number: max + 1, or 1 if none. 4-digit zero-pad.
    if existing:
        next_n = max(_parse_adr_number(p.name) for p in existing) + 1
    else:
        next_n = 1
    number = f"{next_n:04d}"

    if not title:
        title = _slug_to_title(slug)

    # Render and atomically write the file.
    template = _template_path()
    if not template.is_file():
        raise AdrError(f"template not found: {template}")
    today_iso = _today()
    content = _render_adr_content(template.read_text(), number, title,
                                  today_iso)
    target = adrs_dir / f"adr-{number}-{slug}.md"
    if target.exists():  # Defensive — auto-num should have prevented this.
        raise AdrError(f"target already exists: {target}")
    # Spec 066-01: the scaffold-state precondition replaced the top-level
    # `adrs_dir.is_dir()` guard, so ensure docs/decisions/ exists before the
    # atomic write (a scaffold.json-bearing project need not already have it;
    # mirrors the detached-worktree path's mkdir).
    adrs_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, content)

    # Stage + commit locally.
    rel_path = f"docs/decisions/adr-{number}-{slug}.md"
    rc, _out, err = _run(["git", "add", rel_path], cwd=project_dir)
    if rc != 0:
        raise AdrError(
            f"`git add {rel_path}` failed: {err.strip()}. "
            f"The stub ADR file is on disk; stage and commit manually."
        )
    commit_msg = f"docs(decisions): reserve adr-{number}-{slug}"
    rc, _out, err = _run(
        ["git", "commit", "-m", commit_msg], cwd=project_dir,
    )
    if rc != 0:
        raise AdrError(
            f"`git commit` failed: {err.strip()}. "
            f"The stub ADR file is staged; commit manually."
        )

    print(f"reserved adr-{number}-{slug}")
    print(str(target.resolve()))

    # --no-push stops here.
    if no_push:
        return 0

    pr_body = _build_pr_body(number, slug)
    branch_name = f"reserve/adr-{number}-{slug}"

    # --pr skips the direct-push attempt entirely.
    if pr_mode:
        _do_pr_fallback(project_dir, branch_name, number, slug, pr_body)
        return 0

    # Default: try direct push first.
    rc, _out, err = _run(
        ["git", "push", "origin", "main"], cwd=project_dir,
    )
    if rc == 0:
        print(f"reserved adr-{number}-{slug} on origin/main")
        return 0

    kind = _classify_push_failure(err)
    if kind == "race":
        # Drop the stranded commit so re-run starts clean.
        sys.stderr.write(
            f"race detected: origin/main advanced during reservation. "
            f"Re-run 'adr.py new {slug}' to pick the next free "
            f"number.\n"
        )
        _reset_rc, _reset_out, _reset_err = _run(
            ["git", "reset", "--hard", "HEAD~1"], cwd=project_dir,
        )
        # `git reset --hard HEAD~1` un-strands the commit but leaves the
        # ADR file on disk (under mocking, also under real git when the
        # file path was outside the index when reset ran). Remove it
        # unconditionally on race recovery; harmless if already gone.
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise AdrError(
            f"race-on-push: {err.strip()}"
        )

    if kind == "protection":
        sys.stderr.write(
            f"direct push refused ({err.strip()}); falling back to "
            f"PR mode...\n"
        )
        _do_pr_fallback(project_dir, branch_name, number, slug, pr_body)
        return 0

    # Anything else: hard error; leave commit in place.
    raise AdrError(
        f"`git push origin main` failed: {err.strip()} "
        f"(local commit left in place; inspect with `git log -1` "
        f"and decide how to recover)."
    )


# ---------- end slice 028-01 ----------


# ---------- accept ----------


def _find_adr_by_number(adrs_dir: Path, number: str) -> Path:
    """Locate the single `adr-NNNN-*.md` file matching `number`
    (zero-padded). Raises on miss or ambiguity."""
    if not re.match(r"^\d{4}$", number):
        raise AdrError(f"NNNN must be 4-digit zero-padded: '{number}'")
    matches = list(adrs_dir.glob(f"adr-{number}-*.md"))
    if not matches:
        raise AdrError(f"ADR not found: NNNN={number}")
    if len(matches) > 1:
        names = sorted(p.name for p in matches)
        raise AdrError(
            f"ambiguous ADR prefix '{number}' matches: {names}"
        )
    return matches[0]


# Match a *canonical* Status line body — exactly `Proposed (YYYY-MM-DD)`,
# nothing after the date. Deliberately strict: this pattern drives the prose
# REWRITE (`Proposed (…)` → `Accepted (today)`), and a looser pattern would
# either drop authored trailing text or produce the self-contradictory
# `Accepted (today) — awaiting owner acceptance` (issue #123).
#
# It is NOT the accept gate. Per ADR-0046, `cmd_accept` gates on the
# classified state (frontmatter-first) and uses this pattern only to decide
# whether the prose line is safe to rewrite; a non-canonical line is left
# exactly as authored. Groups are non-capturing: the rewrite substitutes the
# whole line, so no caller reads the state or the date back out of the match.
_STATUS_PROPOSED_RE = re.compile(
    r"(?m)^(?:Proposed)[ \t]*\((?:[0-9]{4}-[0-9]{2}-[0-9]{2})\)[ \t]*$"
)


def _gate_frame_critique(adrs_dir: Path, adr_path: Path, number: str) -> None:
    """Slice 064-05 (ADR-0020 OQ2/OQ3): gate the Proposed→Accepted flip on a
    passing `frame-critique` verdict — the ADR's pre-commitment moment.

    Soft / bypassable deliberateness signal (ADR-0011), mirroring
    `workflow.py`'s transition gate: it shares the SAME enable predicate
    (`evidence_gate_enabled`, reading `JIG_REVIEW_EVIDENCE_GATE`).

    Grace path (DoD): gate ONLY when the ADR's frontmatter carries a truthy
    `frame_review` flag. New ADRs always carry it (stamped at creation by
    `_render_adr_content`), so OQ3 always-on holds going forward; a
    pre-existing/legacy Proposed ADR without the marker is NOT gated — no
    false refusal.

    Raises `AdrError` naming the missing/non-clearing artifact + how to
    produce it when gated and the evidence does not clear.
    """
    fm, _ = _parse_frontmatter(adr_path.read_text())
    if not _frontmatter_flag_truthy(fm.get("frame_review", "")):
        return  # legacy / unflagged ADR — grace path, no gate.
    if not _evidence.evidence_gate_enabled():
        return  # deliberate bypass via JIG_REVIEW_EVIDENCE_GATE=0.

    diagnostics = _evidence.validate_adr_evidence(
        adrs_dir, number, "frame-critique"
    )
    if diagnostics:
        num = f"{int(number):04d}"
        joined = "\n  - ".join(diagnostics)
        raise AdrError(
            f"refusing to accept ADR {adr_path.name}: the frame-critique "
            f"evidence does not clear (ADR-0020 OQ2 — ADRs gate at accept):\n"
            f"  - {joined}\n"
            f"Expected a passing verdict at "
            f"docs/decisions/reviews/adr-{num}-frame-critique.md. To produce "
            f"it: build the prompt via `review.py frame-critique "
            f"docs/decisions/{adr_path.name}`, run a reviewer, then `review.py "
            f"record-review --adr {num} --pass frame-critique --verdict pass "
            f"--reviewer <who> --prompt-source <cmd> --summary-file <path>`. "
            f"Bypass with "
            f"JIG_REVIEW_EVIDENCE_GATE=0 (deliberateness signal, ADR-0011)."
        )


def _frontmatter_status(adr_text: str) -> str:
    """The ADR's canonical `status:` frontmatter value, or `''` when the
    field is absent **or present but blank**.

    ADR-0046 ruling 1 (carried forward from ADR-0026): where this field
    carries a value it decides the ADR's lifecycle state, and the value is
    compared exactly and case-sensitively. Collapsing blank-to-absent is
    deliberate — a stamped-but-empty `status:` carries no state, so callers
    fall through to the prose classifier rather than reading `''` as a
    lifecycle value. Note this is *not* identical to
    `workflow.py::_lookup_adr_accepted`, which branches on the field's
    presence; the exact-match discipline is shared, the blank handling is
    not."""
    fields, _ = _parse_frontmatter(adr_text)
    value = fields.get("status", "")
    return value.strip() if isinstance(value, str) else ""


def _adr_status(adr_text: str, section_body: str) -> str:
    """Classify an ADR's lifecycle state **frontmatter-first**
    (ADR-0046 ruling 3).

    Prose is consulted only as the legacy fallback, for ADRs authored
    before spec 073 started stamping `status:`. Because prose is a
    best-effort mirror that may lag the frontmatter (ruling 2), no gate or
    reader in this module may take the state from prose while a `status:`
    field exists — that is what keeps divergence cosmetic rather than
    behaviour-changing. (`_classify_status` is defined in the supersede
    section below; both are module-level, so the order is immaterial.)"""
    return _frontmatter_status(adr_text) or _classify_status(section_body)


def _first_nonempty_line(section_body: str) -> str:
    for raw_line in section_body.splitlines():
        if raw_line.strip():
            return raw_line.strip()
    return ""


def _note_stale_prose_status(adr_path: Path, section_body: str,
                             expected: str) -> None:
    """ADR-0046 ruling 2: the prose Status line was not canonical, so it was
    left exactly as authored. Name the file, the surviving line, and the
    value it should carry, so the agent can reconcile the prose."""
    found = _first_nonempty_line(section_body) or "(empty)"
    sys.stderr.write(
        f"note: {adr_path.name} frontmatter is now `status: Accepted`, but "
        f"its prose `## Status` line is not a canonical "
        f"`Proposed (YYYY-MM-DD)` line — the only shape the rewrite can "
        f"safely replace — so it was left untouched:\n"
        f"    {found}\n"
        f"Update it to `{expected}`. Deterministic tooling does not rewrite "
        f"prose it cannot fully parse (ADR-0046: frontmatter is "
        f"authoritative, prose is a best-effort mirror).\n"
    )


def cmd_accept(adrs_dir: Path, number: str) -> Path:
    """Flip the Status from Proposed → Accepted (today's date).

    ADR-0046 (supersedes ADR-0026 ruling 2): the flip is gated on the ADR's
    *classified* state — frontmatter first, lenient prose classifier as the
    legacy fallback — and never on prose formatting. Frontmatter
    `status: Accepted` is stamped unconditionally; the prose `## Status`
    line is rewritten only when it is canonical, and is otherwise left
    exactly as authored with a touch-up note on stderr. Prose and
    frontmatter may therefore be briefly out of step (a deliberate,
    recorded trade — every reader here is frontmatter-first)."""
    adr_path = _find_adr_by_number(adrs_dir, number)

    # Slice 064-05: gate the flip on a passing frame-critique verdict BEFORE
    # touching the Status (so a refusal leaves the ADR untouched).
    _gate_frame_critique(adrs_dir, adr_path, number)

    text = adr_path.read_text()
    status_end, section_end, section_body = _status_section_body(
        text, adr_path.name,
    )

    state = _adr_status(text, section_body)
    if state != "Proposed":
        if state == "Accepted":
            raise AdrError(
                f"ADR {adr_path.name} is already Accepted; refusing to "
                "re-accept (ADRs are immutable — supersede instead)"
            )
        if state == "Superseded":
            raise AdrError(
                f"ADR {adr_path.name} is Superseded; refusing to accept a "
                "superseded decision — accept its superseder instead."
            )
        raise AdrError(
            f"ADR {adr_path.name} is not Proposed (state: {state}); refusing "
            "to flip — only Proposed → Accepted is supported. State is read "
            "from the frontmatter `status:` field, falling back to the prose "
            "`## Status` section for legacy ADRs."
        )

    # Prose is best-effort (ADR-0046 ruling 2): rewrite the Status line ONLY
    # when it is canonical. A decorated / hand-edited line is left byte-
    # identical rather than truncated or mangled into `Accepted (today) —
    # <stale clause>` (issue #123).
    accepted_line = f"Accepted ({_today()})"
    prose_is_canonical = _STATUS_PROPOSED_RE.search(section_body) is not None
    if prose_is_canonical:
        new_body = _STATUS_PROPOSED_RE.sub(
            lambda _m: accepted_line, section_body, count=1
        )
        new_text = text[:status_end] + new_body + text[section_end:]
    else:
        new_text = text

    # Slice 014-01: stamp `last_verified: <today>` in the ADR frontmatter
    # at the single point where an ADR becomes decision-of-record. Adds
    # the frontmatter block if absent; updates the field if present.
    new_text = _set_frontmatter_field(new_text, "last_verified", _today())
    # Spec 073-02 / ADR-0046 ruling 2: the canonical `status: Accepted`
    # stamp is unconditional, and still lands in the SAME single atomic
    # write as any prose mutation — no second write pass.
    new_text = _set_frontmatter_field(new_text, "status", "Accepted")
    atomic_write_text(adr_path, new_text)

    if not prose_is_canonical:
        _note_stale_prose_status(adr_path, section_body, accepted_line)
    return adr_path


# ---------- supersede (slice 005-02) ----------


# Match an `Accepted (YYYY-MM-DD)` line. Used to locate the insertion point for
# the supersession lines and to verify the old/new ADRs are in Accepted state.
_STATUS_ACCEPTED_RE = re.compile(
    r"(?m)^Accepted[ \t]*\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)[ \t]*$"
)


def _status_section_body(text: str, adr_name: str) -> tuple:
    """Locate the `## Status` section body in `text`. Returns
    (status_match_end, section_end, body_text). Raises AdrError if there's
    no `## Status` heading."""
    status_match = re.search(r"(?m)^##\s+Status\s*$", text)
    if not status_match:
        raise AdrError(f"ADR has no '## Status' section: {adr_name}")
    rest = text[status_match.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    section_end = status_match.end() + (next_h2.start() if next_h2 else len(rest))
    body = text[status_match.end():section_end]
    return status_match.end(), section_end, body


def _classify_status(section_body: str) -> str:
    """Classify the Status body as 'Proposed' / 'Accepted' / 'Superseded' /
    'Unknown'. Superseded wins over Accepted when both lines are present.

    `_SUPERSEDED_BY_RE` is anchored on `^...$` without a `(?m)` flag, so we
    iterate stripped lines rather than a whole-body `.search()`."""
    if any(_SUPERSEDED_BY_RE.match(line.strip())
           for line in section_body.splitlines()):
        return "Superseded"
    if _STATUS_ACCEPTED_RE.search(section_body):
        return "Accepted"
    if re.search(r"(?m)^Proposed[ \t]*\(", section_body):
        return "Proposed"
    return "Unknown"


def cmd_supersede(adrs_dir: Path, old_number: str, new_number: str) -> tuple:
    """Append supersession lines to both ADRs. Returns (old_path, new_path).

    - Old ADR's `## Status` body gains a
      `Superseded by [ADR-<new>](./adr-<new>-<slug>.md) (TODAY)` line.
    - New ADR's `## Status` body gains a `Supersedes ADR-<old>` line (plain text).
    Both Accepted (date) lines are preserved. Atomic writes; refusal-on-precondition
    happens BEFORE any file mutation (so a failed precondition never leaves either
    ADR partially modified).
    """
    # Self-supersession check happens BEFORE any file reads.
    if old_number == new_number:
        raise AdrError(
            f"refusing self-supersession: <old> and <new> are the same "
            f"({old_number}). An ADR cannot supersede itself."
        )

    # NNNN validation — same shape as `_find_adr_by_number` so the error message
    # is consistent across the helper.
    if not re.match(r"^\d{4}$", old_number):
        raise AdrError(f"NNNN must be 4-digit zero-padded: '{old_number}'")
    if not re.match(r"^\d{4}$", new_number):
        raise AdrError(f"NNNN must be 4-digit zero-padded: '{new_number}'")

    # Locate both ADR files.
    old_path = _find_adr_by_number(adrs_dir, old_number)
    new_path = _find_adr_by_number(adrs_dir, new_number)

    old_text = old_path.read_text()
    new_text = new_path.read_text()

    # Extract Status section bodies, then classify.
    old_status_end, old_section_end, old_body = _status_section_body(
        old_text, old_path.name,
    )
    new_status_end, new_section_end, new_body = _status_section_body(
        new_text, new_path.name,
    )

    # ADR-0046 ruling 3: gate on the frontmatter-canonical state, with the
    # prose classifier as the legacy fallback — a prose line that lags the
    # frontmatter must not decide whether a supersession is allowed.
    old_status = _adr_status(old_text, old_body)
    new_status = _adr_status(new_text, new_body)

    if old_status != "Accepted":
        if old_status == "Proposed":
            raise AdrError(
                f"refusing to supersede: old ADR {old_path.name} is "
                f"Proposed; accept the old ADR first "
                f"(`adr.py accept {old_number}`)."
            )
        if old_status == "Superseded":
            raise AdrError(
                f"refusing to supersede: old ADR {old_path.name} is "
                f"already Superseded; refusing to double-supersede."
            )
        raise AdrError(
            f"refusing to supersede: old ADR {old_path.name} Status is "
            f"not Accepted (got {old_status}); only Accepted ADRs can "
            f"be superseded."
        )

    if new_status != "Accepted":
        if new_status == "Proposed":
            raise AdrError(
                f"refusing to supersede: new ADR {new_path.name} is "
                f"Proposed; accept the new ADR first "
                f"(`adr.py accept {new_number}`)."
            )
        if new_status == "Superseded":
            raise AdrError(
                f"refusing to supersede: new ADR {new_path.name} is "
                f"itself Superseded; pick a different replacement ADR."
            )
        raise AdrError(
            f"refusing to supersede: new ADR {new_path.name} Status is "
            f"not Accepted (got {new_status}); only Accepted ADRs can "
            f"supersede others."
        )

    # Build the two new lines.
    today_iso = _today()
    new_slug = new_path.stem[9:] if len(new_path.stem) > 9 else new_path.stem
    superseded_by_line = (
        f"Superseded by [ADR-{new_number}]"
        f"(./adr-{new_number}-{new_slug}.md) ({today_iso})"
    )
    supersedes_line = f"Supersedes ADR-{old_number}"

    # Insert supersession line into the old ADR's Status body, right after the
    # Accepted (date) line.
    new_old_body = _insert_after_accepted(old_body, superseded_by_line)
    if new_old_body == old_body:
        # ADR-0046 ruling 5: unlike `accept`, supersede does not rewrite a
        # line — it INSERTS the `Superseded by …` link, which is load-bearing
        # (both `_classify_status` and human navigation read it). With no
        # canonical `Accepted (YYYY-MM-DD)` anchor there is nowhere to put
        # it, and dropping it silently would lose information — so refuse,
        # before either file is written.
        raise AdrError(_no_anchor_message(old_path, "old"))
    new_old_text = (
        old_text[:old_status_end] + new_old_body + old_text[old_section_end:]
    )
    # Slice 073-02: stamp the OLD ADR's canonical `status: Superseded`
    # frontmatter field in the SAME atomic write that appends the prose
    # `Superseded by …` line. Prose and frontmatter stay sync-locked *here*
    # — but that is ADR-0046 ruling 5's doing, not ADR-0026's surviving
    # invariant: supersede refuses without a canonical anchor (above), so by
    # this line the prose is known-parseable and the pairing is reachable.
    # `accept` has no such guarantee and may diverge (ruling 2).
    # The NEW (superseding) ADR's status is NOT touched here: it retains
    # `status: Accepted` (new-style ADRs carry it from `accept`; legacy ones
    # grandfather via the reader's prose fallback). No backfill (carried
    # forward as an ADR-0046 Open question).
    new_old_text = _set_frontmatter_field(new_old_text, "status", "Superseded")

    new_new_body = _insert_after_accepted(new_body, supersedes_line)
    if new_new_body == new_body:
        raise AdrError(_no_anchor_message(new_path, "new"))
    new_new_text = (
        new_text[:new_status_end] + new_new_body + new_text[new_section_end:]
    )

    # Atomic writes — both ADRs.
    atomic_write_text(old_path, new_old_text)
    atomic_write_text(new_path, new_new_text)
    return old_path, new_path


def _no_anchor_message(adr_path: Path, role: str) -> str:
    """Refusal text for ADR-0046 ruling 5 — the ADR is Accepted per its
    canonical state, but its prose `## Status` carries no canonical
    `Accepted (YYYY-MM-DD)` line to anchor the supersession link to.

    The message names where the acceptance date can be recovered, because
    the record itself no longer holds it: the prose date belongs to the
    stale state, and `last_verified` is a *freshness* field (ADR-0024's
    `reaffirm` refreshes it), not an acceptance date. Pointing at the accept
    commit is the only honest answer — suggesting `last_verified` would
    invite a plausible wrong date into an immutable record.

    The pathspec is `adr_path`, not its basename: git resolves pathspecs
    relative to cwd, so a bare filename matches nothing from a repo root and
    exits 0 — output indistinguishable from "there is no accept commit".
    `--reverse` puts the oldest matching commit first, because `-S` matches
    every commit that changed the string's occurrence count (a later prose
    mention counts), and the acceptance is the earliest of them.

    Reachable **only** when frontmatter supplied the Accepted state. A
    prose-only ADR classifies Accepted through `_STATUS_ACCEPTED_RE`, which is
    the same pattern `_insert_after_accepted` searches — so if it classified
    Accepted, the anchor exists by construction and this refusal cannot
    fire."""
    return (
        f"refusing to supersede: {role} ADR {adr_path.name} is Accepted, but "
        f"its prose `## Status` section has no canonical "
        f"`Accepted (YYYY-MM-DD)` line to anchor the supersession link to. "
        f"Unlike `accept`, supersede cannot fall back to a frontmatter-only "
        f"write — the `Superseded by …` / `Supersedes …` lines live in prose "
        f"and are load-bearing (ADR-0046 ruling 5). Put the Status line in "
        f"canonical form (move any trailing text to the paragraph below it) "
        f"and re-run. The acceptance date is not in the record: the prose "
        f"date belongs to the pre-acceptance state, and `last_verified` is a "
        f"freshness field, not an acceptance date. Recover it from the "
        f"accept commit — the first line is the one you want:\n"
        f"    git log --reverse -S'status: Accepted' --format='%as %h' "
        f"-- '{adr_path}'\n"
        f"Neither ADR was modified."
    )


def _insert_after_accepted(section_body: str, new_line: str) -> str:
    """Insert `new_line` immediately after the existing `Accepted (date)`
    line in `section_body`. Returns the new body. If no Accepted line is
    found, returns `section_body` unchanged."""
    m = _STATUS_ACCEPTED_RE.search(section_body)
    if not m:
        return section_body
    insert_at = m.end()
    # Ensure there's exactly one `\n` between the existing Accepted line and
    # the inserted text. If `section_body[insert_at:]` already starts with
    # `\n`, the inserted line keeps that as its leading separator.
    return (
        section_body[:insert_at] + "\n" + new_line + section_body[insert_at:]
    )


# ---------- index ----------


def _extract_title(adr_text: str) -> str:
    m = re.search(r"(?m)^#\s+ADR-\d{4}:\s+(.+?)\s*$", adr_text)
    return m.group(1).strip() if m else "(untitled)"


_SUPERSEDED_BY_RE = re.compile(
    r"^Superseded[ \t]+by[ \t]+\[ADR-\d{4}\]\([^)]+\)[ \t]*"
    r"\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)[ \t]*$"
)


def _extract_status_and_date(adr_text: str) -> tuple:
    """Returns (status, date) for the README index and `resolve-todo`'s
    Accepted check — **frontmatter-first** (ADR-0046 ruling 3).

    Where frontmatter carries a `status:` field it decides the state; the
    prose parse below supplies only the date. When the two disagree — the
    divergence ADR-0046 ruling 2 permits — the prose date belongs to the
    *stale* state, so pairing it with the frontmatter state would advertise
    a combination that never existed. **No date is published for a diverged
    ADR** (the renderer omits the date and shows the state alone).

    There is deliberately no substitute date. `last_verified` is the obvious
    candidate and the wrong one: it is a *freshness* field, not an
    acceptance date — ADR-0024's `reaffirm` disposition refreshes it and
    `workflow.py`'s staleness check reads it as "verified N days ago", so on
    a reaffirmed ADR it is simply a later date that would read as a genuine
    acceptance date. A plausible wrong date is worse than no date.

    ADRs with no `status:` field resolve entirely from prose, as before.
    """
    prose_status, prose_date = _extract_prose_status_and_date(adr_text)
    fm_status = _frontmatter_status(adr_text)
    if not fm_status:
        return (prose_status, prose_date)
    if fm_status == prose_status:
        return (fm_status, prose_date)
    return (fm_status, "")


def _extract_prose_status_and_date(adr_text: str) -> tuple:
    """Returns (status, date) extracted from the `## Status` section.

    - If the body contains a `Superseded by [ADR-NNNN](...) (date)` line,
      returns `("Superseded", "<date>")` — Superseded wins over an earlier
      `Accepted (date)` line (most-recent-state wins). Slice 005-02 AC #3.
    - Otherwise returns the (status, date) parsed from the first non-empty
      line: `Proposed (date)` or `Accepted (date)`.
    - Falls back to ('(unknown)', '') on miss.
    """
    m = re.search(r"(?m)^##\s+Status\s*$", adr_text)
    if not m:
        return ("(unknown)", "")
    rest = adr_text[m.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    body = rest[: next_h2.start()] if next_h2 else rest

    # First pass: look for a `Superseded by ... (date)` line anywhere in the
    # Status body. If found, it wins over any earlier Accepted/Proposed line.
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sm = _SUPERSEDED_BY_RE.match(line)
        if sm:
            return ("Superseded", sm.group(1))

    # Second pass: original first-non-empty-line logic for Proposed/Accepted.
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sm = re.match(r"^([A-Za-z][A-Za-z _-]*?)\s*\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)\s*$",
                      line)
        if sm:
            return (sm.group(1).strip(), sm.group(2))
        # Free-form fallback: take the first word as status, no date.
        return (line.split()[0], "")
    return ("(unknown)", "")


_DESCRIPTION_MAX = 120

# Inbox 2026-05-12 refinement: common abbreviations whose trailing period is
# NOT a sentence boundary. The detector below looks back from each candidate
# period and refuses to truncate when one of these endings matches.
# Kept intentionally small: this is a sentence-boundary heuristic, not NLP.
_ABBREVIATIONS = (
    "e.g.", "i.e.", "etc.", "cf.", "vs.", "viz.",
    "al.", "et al.",
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "St.",
)


def _is_abbreviation_ending_at(text: str, period_index: int) -> bool:
    """Return True iff `text[: period_index + 1]` ends with a known
    abbreviation. `period_index` points at the candidate `.`.

    Match is case-sensitive on purpose: `Mr.` should match but a stray `e.g.`
    in a code-style identifier won't accidentally match `E.G.`.
    """
    head = text[: period_index + 1]
    for abbr in _ABBREVIATIONS:
        if head.endswith(abbr):
            # Boundary check: the char before the abbreviation must not be a
            # letter (otherwise `mile.` would accidentally match `le.`).
            before_idx = len(head) - len(abbr) - 1
            if before_idx < 0 or not head[before_idx].isalpha():
                return True
    return False


def _first_sentence_end(paragraph: str) -> Optional[int]:
    """Index of the first sentence-ending `.` / `?` / `!` followed by a space
    or EOL, skipping periods that belong to a known abbreviation. Returns
    None when the paragraph carries no complete sentence."""
    for i, ch in enumerate(paragraph):
        if ch in ".?!":
            after = paragraph[i + 1: i + 2]
            if after == "" or after.isspace():
                if ch == "." and _is_abbreviation_ending_at(paragraph, i):
                    continue
                return i
    return None


def _context_paragraph(adr_text: str) -> tuple:
    """Return `(paragraph, line_count)` for the first non-empty paragraph of
    `## Context` — contiguous lines joined with spaces. `('', 0)` on miss."""
    m = re.search(r"(?m)^##\s+Context\s*$", adr_text)
    if not m:
        return ("", 0)
    rest = adr_text[m.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    body = rest[: next_h2.start()] if next_h2 else rest

    paragraph_lines = []
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if paragraph_lines:
                break
            continue
        paragraph_lines.append(line.strip())
    return (" ".join(paragraph_lines), len(paragraph_lines))


def _extract_description(adr_text: str) -> str:
    """First non-empty paragraph from `## Context`, truncated to its first
    complete sentence when the paragraph is multi-line, > 120 chars, or ends
    in a colon.

    Returns '' when the paragraph holds NO complete sentence — the shape of a
    lead-in to a list or table (`jig has two scaffold topologies, selected by
    one axis in \\`scaffold.py\\`:`). Bug 020 / [issue #140]: that used to be
    written verbatim, or hard-truncated with a trailing `…` when it ran past
    the cap, producing an index line that read like a decision summary and
    was not one. The index stays a pure function of the ADR files, so the
    answer is not to let a human overwrite the bullet — it is to say plainly
    that this record has no derivable summary, and name it, so its `## Context`
    opening gets reworded at the source.

    Also returns '' on miss (no `## Context`). Caller fills in."""
    paragraph, line_count = _context_paragraph(adr_text)
    if not paragraph:
        return ""

    boundary = _first_sentence_end(paragraph)
    if boundary is None:
        # No sentence at all — a lead-in, not a summary.
        return ""

    multi_line = line_count > 1
    too_long = len(paragraph) > _DESCRIPTION_MAX
    # The colon case covers a one-line lead-in that happens to open with a
    # complete sentence: keep the sentence, drop the dangling lead-in.
    if multi_line or too_long or paragraph.endswith(":"):
        return paragraph[: boundary + 1]
    return paragraph


_NO_DESCRIPTION = "(no description)"


def _is_degenerate_description(description: str) -> bool:
    """True for a summary that is a fragment or a placeholder rather than a
    sentence. Guards the write path: `_extract_description` returns '' for a
    paragraph with no sentence in it, but a paragraph CAN end in `…` or open
    with the template's `_TODO` stub and still carry a boundary, and neither
    belongs in the index."""
    text = (description or "").strip()
    if not text or text == _NO_DESCRIPTION:
        return True
    if text.endswith(":") or text.endswith("…"):
        return True
    # The ADR template's italic stubs, indexed before the record was written.
    if text.startswith("_TODO") or text.startswith("_TBD"):
        return True
    return False


def _no_summary_reason(adr_text: str) -> str:
    """Name why no summary could be derived, so the warning is actionable."""
    paragraph, _ = _context_paragraph(adr_text)
    if not paragraph:
        return "it has no `## Context` prose to summarize"
    if paragraph.startswith("_TODO") or paragraph.startswith("_TBD"):
        return "its `## Context` is still the template stub"
    # Every remaining case is "the first paragraph has no complete sentence".
    # A lead-in to a list or table is the common one, but a paragraph that
    # merely lacks terminal punctuation lands here too — so state the fact,
    # and name the likely cause without asserting it.
    return ("its `## Context` opens with no complete first sentence "
            "(typically a lead-in to a list or table)")


def _render_index_entries(adr_paths: list,
                          warnings: Optional[list] = None) -> list:
    """Return one bullet line per ADR, sorted ascending by NNNN.

    Records with no derivable summary get `(no description)` and append a
    line to `warnings` naming the record and why."""
    rows = []
    for p in sorted(adr_paths, key=lambda x: _parse_adr_number(x.name)):
        text = p.read_text()
        number = f"{_parse_adr_number(p.name):04d}"
        title = _extract_title(text)
        status, date_str = _extract_status_and_date(text)
        description = _extract_description(text)
        if _is_degenerate_description(description):
            description = _NO_DESCRIPTION
            if warnings is not None:
                warnings.append(
                    f"adr.py index: ADR-{number} ({p.name}) — "
                    f"{_no_summary_reason(text)}. Wrote {_NO_DESCRIPTION}. "
                    f"Reword that record's `## Context` opening into a "
                    f"standalone sentence and re-run — the index is derived "
                    f"from the ADR files, so the fix belongs at the source."
                )
        # Filename stem is `adr-NNNN-<slug>` (9-char prefix to strip).
        slug = p.stem[9:] if len(p.stem) > 9 else p.stem
        meta = f"({date_str}, {status})" if date_str else f"({status})"
        rows.append(
            f"- [ADR-{number}: {title}](adr-{number}-{slug}.md) — "
            f"{description} {meta}"
        )
    return rows


def cmd_index(adrs_dir: Path) -> Path:
    """Regenerate the `## Index` section of `<decisions-dir>/README.md`."""
    if not adrs_dir.is_dir():
        raise AdrError(f"decisions directory not found: {adrs_dir}")
    readme = adrs_dir / "README.md"
    if not readme.is_file():
        raise AdrError(f"README.md not found in: {adrs_dir}")
    text = readme.read_text()

    # Match the `## Index` heading line. Use `[ \t]*$` instead of `\s*$` so the
    # regex does NOT consume the trailing newline — preserving it keeps our
    # replacement boundary clean (and idempotent).
    index_h2 = re.search(r"(?m)^##[ \t]+Index[ \t]*$", text)
    if not index_h2:
        raise AdrError(
            f"README.md has no '## Index' heading: {readme}"
        )
    # Find the next `## ` heading (or EOF) to bound the section we replace.
    rest = text[index_h2.end():]
    next_h2 = re.search(r"(?m)^##\s", rest)
    section_end = index_h2.end() + (next_h2.start() if next_h2 else len(rest))

    adrs = _adr_files(adrs_dir)
    warnings = []
    bullets = _render_index_entries(adrs, warnings)
    for line in warnings:
        sys.stderr.write(line + "\n")

    # New body: two blank lines after the heading, then bullets (or empty if
    # none), then a trailing blank line before the next section (preserves
    # spacing for readability).
    if bullets:
        body = "\n\n" + "\n".join(bullets) + "\n\n"
    else:
        body = "\n\n"
    new_text = text[: index_h2.end()] + body + text[section_end:]

    if new_text == text:
        # Idempotent no-op.
        return readme
    atomic_write_text(readme, new_text)
    return readme


# ---------- resolve-todo ----------


def _is_struck_through(heading_line: str) -> bool:
    """Heading already wrapped in strikethrough? Detect by `### ~~` prefix."""
    return bool(re.match(r"^###\s+~~", heading_line))


def _find_todo_section(todo_text: str, fragment: str) -> tuple:
    """Locate the H3 section whose heading text contains `fragment`
    (case-insensitive substring). Returns (header_start, header_end,
    section_end, heading_line). Raises on miss/ambiguity."""
    headers = list(re.finditer(r"(?im)^###\s+[^\n]+$", todo_text))
    if not headers:
        raise AdrError("no '### ' headings found in refinement-todo.md")
    needle = fragment.lower()
    matches = [h for h in headers if needle in h.group(0).lower()]
    if not matches:
        raise AdrError(f"section not found: fragment '{fragment}' matches nothing")
    if len(matches) > 1:
        names = [h.group(0).strip() for h in matches]
        raise AdrError(
            f"ambiguous fragment '{fragment}' matches: {names}"
        )
    header = matches[0]
    heading_line = header.group(0)
    rest = todo_text[header.end():]
    nxt = re.search(r"(?m)^(?:##|###)\s", rest)
    section_end = header.end() + (nxt.start() if nxt else len(rest))
    return header.start(), header.end(), section_end, heading_line


def cmd_resolve_todo(project_dir: Path, number: str, fragment: str) -> Path:
    """Strikethrough a refinement-todo section + append Resolved-by link.

    `project_dir` must contain both `docs/decisions/` and
    `docs/refinement-todo.md`."""
    adrs_dir = project_layout.decisions_dir(project_dir)
    todo_path = project_layout.refinement_todo_path(project_dir)

    if not todo_path.is_file():
        raise AdrError(f"refinement-todo.md not found: {todo_path}")
    if not adrs_dir.is_dir():
        raise AdrError(
            f"docs/decisions/ not found in project: {project_dir}"
        )

    # Resolve ADR + verify Accepted state.
    adr_path = _find_adr_by_number(adrs_dir, number)
    adr_text = adr_path.read_text()
    status, _ = _extract_status_and_date(adr_text)
    if status != "Accepted":
        raise AdrError(
            f"ADR {adr_path.name} is not Accepted (status={status}); "
            "refusing to resolve-todo. Accept the ADR first."
        )
    title = _extract_title(adr_text)

    todo_text = todo_path.read_text()
    h_start, h_end, s_end, heading_line = _find_todo_section(todo_text, fragment)

    if _is_struck_through(heading_line):
        raise AdrError(
            f"section already struck through: '{heading_line}'. "
            "Refusing to double-resolve."
        )

    # 1) Rewrite the heading: `### Decision: Foo` → `### ~~Decision: Foo~~ — RESOLVED YYYY-MM-DD`.
    new_heading = _strikethrough_heading(heading_line)

    # 2) Wrap the first **Deferred:** line in the section body.
    body = todo_text[h_end:s_end]
    new_body = _strikethrough_first_deferred(body)

    # 3) Append Resolved-by line at the section's end. Preserve trailing
    # whitespace pattern: insert before any trailing newlines so the next
    # heading still has its leading blank line.
    # Filename stem is `adr-NNNN-<slug>` (9-char prefix to strip).
    slug = adr_path.stem[9:] if len(adr_path.stem) > 9 else adr_path.stem
    number_str = f"{_parse_adr_number(adr_path.name):04d}"
    resolved_line = (
        f"**Resolved by:** [ADR-{number_str}: {title}]"
        f"(decisions/adr-{number_str}-{slug}.md).\n"
    )
    new_body = _append_to_section(new_body, resolved_line)

    new_text = todo_text[:h_start] + new_heading + new_body + todo_text[s_end:]
    atomic_write_text(todo_path, new_text)
    return todo_path


def _strikethrough_heading(heading_line: str) -> str:
    """`### Decision: Foo` → `### ~~Decision: Foo~~ — RESOLVED YYYY-MM-DD`."""
    m = re.match(r"^(###\s+)(.+?)\s*$", heading_line)
    if not m:
        # Defensive — _find_todo_section already enforced the prefix.
        return f"### ~~{heading_line.lstrip('# ').rstrip()}~~ — RESOLVED {_today()}\n"
    return f"{m.group(1)}~~{m.group(2)}~~ — RESOLVED {_today()}"


def _strikethrough_first_deferred(section_body: str) -> str:
    """Wrap the first `**Deferred:** ...` line in `~~...~~`.

    If no Deferred line is found, the body is returned unchanged."""
    lines = section_body.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.lstrip().startswith("**Deferred:**"):
            stripped = line.rstrip("\n")
            trailing = line[len(stripped):]
            # Avoid double-wrapping if (somehow) already struck.
            if stripped.lstrip().startswith("~~") and stripped.rstrip().endswith("~~"):
                return section_body
            lines[i] = f"~~{stripped}~~{trailing}"
            break
    return "".join(lines)


def _append_to_section(section_body: str, line: str) -> str:
    """Append `line` to the end of the section body, preserving the trailing
    blank-line buffer before the next heading. Idempotent on exact-line presence."""
    if line.rstrip() in section_body:
        return section_body  # Already appended (defensive).

    # Strip trailing newlines, append, then restore one trailing blank line.
    stripped = section_body.rstrip("\n")
    return stripped + "\n" + line + "\n"


# ---------- CLI plumbing ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adr.py",
        description=(
            "jig adr-workflow helper "
            "(new / accept / supersede / index / resolve-todo)"
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("new", help="scaffold a new ADR file")
    pn.add_argument("slug", help="kebab-case slug, e.g. my-decision")
    pn.add_argument("--title", default="", help="Title (default: title-cased slug)")
    # Slice 028-01: reserve-on-main with PR-fallback. --no-push opts out
    # of the remote interaction (local-only allocation).
    push_group = pn.add_mutually_exclusive_group()
    push_group.add_argument(
        "--no-push", action="store_true",
        help="Skip the direct push to origin/main (local-only allocation)",
    )
    push_group.add_argument(
        "--pr", action="store_true",
        help="Skip the direct-push attempt; go straight to branch + PR",
    )
    pn.add_argument(
        "--project-dir", default=None,
        help="Project root (default: current working directory)",
    )

    pa = sub.add_parser("accept", help="flip an ADR's Status from Proposed → Accepted")
    pa.add_argument("number", help="4-digit ADR number (e.g. 0003)")

    ps = sub.add_parser(
        "supersede",
        help="append Superseded-by / Supersedes lines to two Accepted ADRs",
    )
    ps.add_argument("old", help="4-digit NNNN of the ADR being superseded")
    ps.add_argument("new", help="4-digit NNNN of the replacement ADR")

    pi = sub.add_parser("index", help="regenerate the Index section of ADR README.md")
    pi.add_argument("adrs_dir", help="path to docs/decisions/")

    pr = sub.add_parser("resolve-todo",
                        help="mark a refinement-todo section resolved by an ADR")
    pr.add_argument("number", help="4-digit ADR number")
    pr.add_argument("fragment", help="case-insensitive substring of the heading text")

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        if ns.cmd == "new":
            # Slice 028-01: default behavior changed from local-only to
            # reserve-on-main with PR-fallback. --no-push opts out.
            project_dir = (Path(ns.project_dir).resolve()
                           if ns.project_dir else Path.cwd())
            reserve_adr(ns.slug, project_dir, title=ns.title,
                        no_push=ns.no_push, pr_mode=ns.pr)
        elif ns.cmd == "accept":
            adrs_dir = project_layout.decisions_dir(Path.cwd())
            target = cmd_accept(adrs_dir, ns.number)
            print(str(target.relative_to(Path.cwd())) if target.is_relative_to(Path.cwd())
                  else str(target))
        elif ns.cmd == "supersede":
            adrs_dir = project_layout.decisions_dir(Path.cwd())
            old_path, new_path = cmd_supersede(adrs_dir, ns.old, ns.new)
            for target in (old_path, new_path):
                print(str(target.relative_to(Path.cwd()))
                      if target.is_relative_to(Path.cwd())
                      else str(target))
        elif ns.cmd == "index":
            adrs_dir = Path(ns.adrs_dir).resolve()
            target = cmd_index(adrs_dir)
            print(str(target))
        elif ns.cmd == "resolve-todo":
            project_dir = Path.cwd()
            target = cmd_resolve_todo(project_dir, ns.number, ns.fragment)
            print(str(target.relative_to(Path.cwd())) if target.is_relative_to(Path.cwd())
                  else str(target))
    except AdrError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — surface programming errors clearly.
        sys.stderr.write(f"adr.py failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
