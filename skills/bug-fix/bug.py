#!/usr/bin/env python3
"""
jig bug-fix helper — spec 058 core.

Deterministic file mutations for bug records. The host skill owns judgment and
subagent orchestration; this helper handles records, triage, the bug board,
claim/release bookkeeping, and transition gates.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import project_layout
from _common import review_evidence as _evidence
from _common.atomic_io import atomic_write_text
from _common.parsing import (
    clear_frontmatter_field,
    frontmatter_flag_truthy,
    parse_frontmatter,
    set_frontmatter_field,
)

VALID_TIERS = ("trivial", "standard", "gnarly")
VALID_FIX_CLASSES = (
    "workaround",
    "local_patch",
    "structural_fix",
    "guardrail",
    "observability",
)
VALID_BUG_STATUSES = (
    "REPORTED",
    "DIAGNOSING",
    "ROOT_CAUSED",
    "FIXING",
    "REVIEWED",
    "VERIFIED",
    "DONE",
    "ESCALATED",
    "RESOLVED_ON_MAIN",
)
VALID_MAIN_REPRO_RESULTS = ("reproduces", "resolved_on_main")
OPEN_STATUSES = {
    "REPORTED",
    "DIAGNOSING",
    "ROOT_CAUSED",
    "FIXING",
    "REVIEWED",
    "VERIFIED",
}
_ORDERED_TRANSITIONS = {
    "REPORTED": {"DIAGNOSING"},
    "DIAGNOSING": {"ROOT_CAUSED"},
    "ROOT_CAUSED": {"FIXING"},
    "FIXING": {"REVIEWED", "DIAGNOSING"},
    "REVIEWED": {"VERIFIED", "DONE", "DIAGNOSING"},
    "VERIFIED": {"DONE", "DIAGNOSING"},
}
_DISABLE_VALUES = {"0", "false", "off", "no"}
_PUSH_RACE_SIGNALS = (
    "non-fast-forward",
    "fetch first",
    "stale info",
    "rejected",
)
_PUSH_PROTECTION_SIGNALS = (
    "protected branch",
    "gh006",
    "permission denied",
    "pre-receive hook declined",
)


class BugError(RuntimeError):
    """User-facing helper error."""


def _today() -> str:
    return datetime.date.today().isoformat()


def _bugs_dir(project_dir: Path) -> Path:
    return project_layout.docs_base(project_dir) / "bugs"


def _run(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def _slugify(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if not slug:
        raise BugError("slug must contain at least one letter or number")
    return slug


def _current_branch(project_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    branch = result.stdout.strip()
    return branch or None


def _claim_identifier(project_dir: Path) -> str:
    env = os.environ.get("JIG_CLAIM_ID")
    if env and env.strip():
        return env.strip()
    return _current_branch(project_dir) or "detached"


def _next_number(bugs_dir: Path) -> int:
    highest = 0
    if bugs_dir.is_dir():
        for path in bugs_dir.glob("*.md"):
            match = re.match(r"^(\d{3})-", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def _is_bug_record(path: Path) -> bool:
    return re.fullmatch(r"\d{3}-.+\.md", path.name) is not None


def _resolve_bug(project_dir: Path, ident: str) -> Path:
    bugs_dir = _bugs_dir(project_dir)
    if not bugs_dir.is_dir():
        raise BugError(f"bug directory not found: {bugs_dir}")
    raw = ident.strip()
    candidate = Path(raw)
    if candidate.suffix == ".md" and candidate.is_file():
        resolved_candidate = candidate.resolve()
        resolved_bugs_dir = bugs_dir.resolve()
        if resolved_candidate.parent != resolved_bugs_dir:
            raise BugError(
                f"direct bug paths must live under {resolved_bugs_dir}"
            )
        if not _is_bug_record(resolved_candidate):
            raise BugError(
                "direct bug paths must name a NNN-slug.md record under "
                f"{resolved_bugs_dir}"
            )
        return resolved_candidate
    if re.fullmatch(r"\d+", raw):
        prefix = f"{int(raw):03d}-"
    else:
        prefix = raw.removesuffix(".md")
        if not prefix.endswith("-"):
            prefix += "-"
    matches = sorted(
        p for p in bugs_dir.glob("*.md")
        if _is_bug_record(p)
        and (p.name == raw or p.stem == raw or p.name.startswith(prefix))
    )
    if not matches:
        raise BugError(f"bug not found: {ident}")
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise BugError(f"ambiguous bug id {ident!r}: {names}")
    return matches[0]


def _bug_id_and_slug(path: Path) -> tuple[str, str]:
    match = re.match(r"^(\d{3})-(.+)\.md$", path.name)
    if not match:
        raise BugError(f"invalid bug filename: {path.name}")
    return match.group(1), match.group(2)


def _gate_enabled(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return True
    return raw.strip().lower() not in _DISABLE_VALUES


def _record_text(number: int, slug: str, claimed_by: str) -> str:
    fields = [
        "---",
        "status: REPORTED",
        "tier:",
        "severity:",
        f"claimed_by: {claimed_by}",
        "regression_test:",
        "main_repro_checked_at:",
        "main_repro_ref:",
        "main_repro_result:",
        "red_confirmed_at:",
        "green_confirmed_at:",
        "fix_class:",
        "security_surface: false",
        "escalated_to:",
        "---",
        "",
        f"# Bug {number:03d}: {slug}",
        "",
        "## Symptom",
        "",
        "## Repro",
        "",
        "## Evidence",
        "",
        "## Hypotheses",
        "",
        "## Root cause",
        "",
        "## Fix class",
        "",
        "## Fix",
        "",
        "## Already tried",
        "",
        "## Regression test",
        "",
        "## Proof",
        "",
        "## Learning",
        "",
    ]
    return "\n".join(fields)


def _classify_push_failure(stderr: str) -> str:
    low = stderr.lower()
    for sig in _PUSH_RACE_SIGNALS:
        if sig in low:
            return "race"
    for sig in _PUSH_PROTECTION_SIGNALS:
        if sig in low:
            return "protection"
    return "other"


def _check_gh_and_remote(project_dir: Path) -> None:
    if shutil.which("gh") is None:
        raise BugError(
            "refusing PR-fallback: 'gh' CLI not found on PATH. "
            "Install GitHub CLI or re-run without --pr."
        )
    rc, stdout, stderr = _run(
        ["git", "config", "--get", "remote.origin.url"], cwd=project_dir,
    )
    if rc != 0 or not stdout.strip():
        raise BugError(
            "refusing PR-fallback: no 'origin' remote configured "
            f"(git: {stderr.strip() or 'empty url'})"
        )
    if "github.com" not in stdout.strip():
        raise BugError(
            "refusing PR-fallback: remote 'origin' does not point at "
            "github.com"
        )


def _push_bug_reservation_pr(project_dir: Path, sha: str, branch: str,
                             bug_name: str) -> None:
    _check_gh_and_remote(project_dir)
    rc, _out, err = _run(
        ["git", "push", "origin", f"{sha}:refs/heads/{branch}"],
        cwd=project_dir,
    )
    if rc != 0:
        raise BugError(
            f"PR-fallback push to {branch!r} failed: {err.strip()}."
        )
    rc, out, err = _run(
        [
            "gh", "pr", "create",
            "--title", f"docs(bugs): reserve {bug_name}",
            "--body", (
                f"Reserves bug number `{bug_name}` on the shared trunk so "
                "parallel worktrees cannot claim the same bug id."
            ),
            "--head", branch,
            "--base", "main",
        ],
        cwd=project_dir,
    )
    if rc != 0:
        raise BugError(
            f"PR-fallback `gh pr create` failed: {err.strip()}. "
            f"Branch origin/{branch} is pushed; open the PR manually."
        )
    if out.strip():
        print(out.strip())


def reserve_bug_on_origin(project_dir: Path, slug: str,
                          pr_mode: bool = False) -> tuple[str, str]:
    """Reserve a bug number on origin/main from an ephemeral detached
    worktree. The caller's worktree and branch tip are not touched."""
    slug = _slugify(slug)
    rc, _out, err = _run(["git", "fetch", "origin", "main"], cwd=project_dir)
    if rc != 0:
        print(
            f"warning: `git fetch origin main` failed: {err.strip()}; "
            "proceeding with the local origin/main view",
            file=sys.stderr,
        )

    wt = Path(tempfile.mkdtemp(prefix="jig-reserve-bug-"))
    try:
        rc, _out, err = _run(
            ["git", "worktree", "add", "--detach", str(wt), "origin/main"],
            cwd=project_dir,
        )
        if rc != 0:
            raise BugError(
                "could not create the ephemeral bug reservation worktree at "
                f"origin/main ({err.strip()})"
            )
        bugs_dir = _bugs_dir(wt)
        bugs_dir.mkdir(parents=True, exist_ok=True)
        number = _next_number(bugs_dir)
        bug_name = f"{number:03d}-{slug}"
        path = bugs_dir / f"{bug_name}.md"
        if path.exists():
            raise BugError(f"refusing: {bug_name}.md already exists on origin/main")
        atomic_write_text(path, _record_text(number, slug, _claim_identifier(project_dir)))
        rel = f"docs/bugs/{bug_name}.md"
        rc, _out, err = _run(["git", "add", rel], cwd=wt)
        if rc != 0:
            raise BugError(f"`git add` in reservation worktree failed: {err.strip()}")
        rc, _out, err = _run(
            ["git", "commit", "-m", f"docs(bugs): reserve {bug_name}"],
            cwd=wt,
        )
        if rc != 0:
            raise BugError(
                f"`git commit` in reservation worktree failed: {err.strip()}"
            )
        print(f"reserved bug {bug_name}")
        rc, sha, err = _run(["git", "rev-parse", "HEAD"], cwd=wt)
        if rc != 0 or not sha.strip():
            raise BugError(f"could not resolve reservation commit SHA: {err.strip()}")
        sha = sha.strip()
        branch = f"reserve/bug-{bug_name}"
        if pr_mode:
            _push_bug_reservation_pr(project_dir, sha, branch, bug_name)
            return f"{number:03d}", slug
        rc, _out, err = _run(
            ["git", "push", "origin", f"{sha}:refs/heads/main"],
            cwd=project_dir,
        )
        if rc == 0:
            print(f"reserved bug {bug_name} on origin/main")
            return f"{number:03d}", slug
        kind = _classify_push_failure(err)
        if kind == "race":
            print(
                "race detected: origin/main advanced during bug reservation. "
                f"Re-run 'bug.py new {slug} --push' to pick the next free number.",
                file=sys.stderr,
            )
            raise BugError(f"race-on-push: {err.strip()}")
        if kind == "protection":
            print(
                f"direct push refused ({err.strip()}); falling back to PR mode...",
                file=sys.stderr,
            )
            _push_bug_reservation_pr(project_dir, sha, branch, bug_name)
            return f"{number:03d}", slug
        raise BugError(
            f"`git push origin {sha}:refs/heads/main` failed: {err.strip()}"
        )
    finally:
        _run(["git", "worktree", "remove", "--force", str(wt)], cwd=project_dir)
        shutil.rmtree(wt, ignore_errors=True)
        _run(["git", "worktree", "prune"], cwd=project_dir)


def new_bug(project_dir: Path, slug: str, *, push: bool = False,
            pr_mode: bool = False) -> Path | None:
    slug = _slugify(slug)
    if push or pr_mode:
        reserve_bug_on_origin(project_dir, slug, pr_mode=pr_mode)
        return None
    bugs_dir = _bugs_dir(project_dir)
    bugs_dir.mkdir(parents=True, exist_ok=True)
    number = _next_number(bugs_dir)
    path = bugs_dir / f"{number:03d}-{slug}.md"
    if path.exists():
        raise BugError(f"bug record already exists: {path}")
    atomic_write_text(path, _record_text(number, slug, _claim_identifier(project_dir)))
    return path


def triage_bug(project_dir: Path, ident: str, tier: str | None,
               severity: str | None) -> Path | None:
    path = _resolve_bug(project_dir, ident)
    text = path.read_text()
    fields, _ = parse_frontmatter(text)
    chosen = (tier or str(fields.get("tier") or "").strip()).lower()
    if chosen not in VALID_TIERS:
        raise BugError(
            "triage requires --tier trivial|standard|gnarly "
            "or an existing tier field"
        )
    if chosen == "trivial":
        path.unlink()
        print(
            "Trivial bug: write the failing test with `tdd-loop`, fix, "
            "commit; no bug record needed."
        )
        return None
    text = set_frontmatter_field(text, "tier", chosen)
    if severity is not None:
        text = set_frontmatter_field(text, "severity", severity)
    atomic_write_text(path, text)
    return path


def _append_release_log(text: str, released_from: str, reason: str) -> str:
    entry = f"- {_today()} - released claim from {released_from}: {reason.strip()}\n"
    body = text.rstrip("\n")
    if "## Release log" in text:
        return body + "\n" + entry
    return body + "\n\n## Release log\n\n" + entry


def pickup_bug(project_dir: Path, ident: str, release: bool = False,
               reason: str | None = None) -> Path:
    if release and not (reason and reason.strip()):
        raise BugError('--release requires --reason "<text>" for the audit trail')
    path = _resolve_bug(project_dir, ident)
    text = path.read_text()
    fields, _ = parse_frontmatter(text)
    existing = str(fields.get("claimed_by") or "").strip()
    status = str(fields.get("status") or "").strip()
    if release:
        released_from = existing or "(unclaimed)"
        text = clear_frontmatter_field(text, "claimed_by")
        text = _append_release_log(text, released_from, reason or "")
        atomic_write_text(path, text)
        return path

    owner = _claim_identifier(project_dir)
    if existing and existing != owner and status in OPEN_STATUSES:
        raise BugError(
            f"bug {path.name} is currently claimed by {existing!r} "
            f"(status {status}). To take it over, have the owner release it, "
            f'or force-release with: bug.py pickup {ident} --release '
            f'--reason "..."'
        )
    text = set_frontmatter_field(text, "claimed_by", owner)
    atomic_write_text(path, text)
    return path


def _section(text: str, heading: str) -> str:
    pattern = re.compile(
        r"(?ms)^##\s+" + re.escape(heading) + r"\s*\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _proof_attests_original_repro(text: str) -> bool:
    proof = _section(text, "Proof").lower()
    return bool(proof and "original reported repro" in proof)


def _learning_recorded(project_dir: Path, bug_path: Path) -> bool:
    learnings = project_layout.memory_dir(project_dir) / "learnings.md"
    if not learnings.is_file():
        return False
    try:
        text = learnings.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return False
    bug_id, slug = _bug_id_and_slug(bug_path)
    needles = (f"bug {bug_id}", bug_path.name.lower(), f"{bug_id}-{slug}".lower())
    return any(needle in text for needle in needles)


def _requires_verified(fields: dict) -> bool:
    tier = str(fields.get("tier") or "").strip().lower()
    return tier == "gnarly" or frontmatter_flag_truthy(
        fields.get("security_surface", "")
    )


def _diagnosis_gaps(text: str) -> list[str]:
    gaps = []
    hypotheses = _section(text, "Hypotheses")
    evidence = _section(text, "Evidence")
    hypothesis_lines = [
        line.strip() for line in hypotheses.splitlines()
        if line.strip().startswith("-")
    ]
    if len(hypothesis_lines) < 2:
        gaps.append("at least two candidate hypotheses")
    has_leading = any("[x]" in line.lower() for line in hypothesis_lines)
    has_leading = has_leading or re.search(
        r"(?im)^leading\s*:", hypotheses
    ) is not None
    if not has_leading:
        gaps.append("a leading hypothesis")
    if not evidence:
        gaps.append("an evidence pointer")
    return gaps


def _default_tdd_helper() -> Path:
    return Path(__file__).resolve().parent.parent / "tdd-loop" / "tdd.py"


def _run_tdd(project_dir: Path, selector: str) -> subprocess.CompletedProcess:
    helper = Path(os.environ.get("JIG_TDD_HELPER", str(_default_tdd_helper())))
    return subprocess.run(
        [sys.executable, str(helper), "run", str(project_dir), "--test", selector],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def _append_already_tried(text: str, message: str) -> str:
    entry = f"- {_today()} - {message.strip()}\n"
    pattern = re.compile(r"(?ms)^##\s+Already tried\s*\n")
    match = pattern.search(text)
    if not match:
        return text.rstrip("\n") + "\n\n## Already tried\n\n" + entry
    insert_at = match.end()
    return text[:insert_at] + "\n" + entry + text[insert_at:]


def _append_main_recheck(text: str, ref: str, result: str, evidence: str) -> str:
    entry = (
        f"- {_today()} - `{ref}` -> {result}: "
        f"{evidence.strip() or '(no evidence note)'}\n"
    )
    body = text.rstrip("\n")
    if "## Main recheck" in text:
        return body + "\n" + entry
    return body + "\n\n## Main recheck\n\n" + entry


def _main_recheck_gaps(fields: dict) -> list[str]:
    checked_at = str(fields.get("main_repro_checked_at") or "").strip()
    ref = str(fields.get("main_repro_ref") or "").strip()
    result = str(fields.get("main_repro_result") or "").strip()
    gaps = []
    if not checked_at:
        gaps.append("main_repro_checked_at")
    if not ref:
        gaps.append("main_repro_ref")
    if not result:
        gaps.append("main_repro_result")
    elif result == "resolved_on_main":
        gaps.append("main recheck says the bug is resolved on main")
    elif result != "reproduces":
        gaps.append(
            "main_repro_result must be reproduces before FIXING "
            f"(got {result!r})"
        )
    return gaps


def _validate_order(current: str, new_status: str) -> None:
    if new_status not in VALID_BUG_STATUSES:
        raise BugError(
            f"invalid status: {new_status}. valid: {', '.join(VALID_BUG_STATUSES)}"
        )
    if current == new_status:
        return
    allowed = _ORDERED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise BugError(f"invalid transition: {current} -> {new_status}")


def transition_bug(project_dir: Path, ident: str, new_status: str) -> Path:
    new_status = new_status.strip().upper()
    path = _resolve_bug(project_dir, ident)
    text = path.read_text()
    fields, _ = parse_frontmatter(text)
    current = str(fields.get("status") or "").strip()
    if current not in VALID_BUG_STATUSES:
        raise BugError(f"bug {path.name} has invalid status: {current or '(empty)'}")
    _validate_order(current, new_status)

    if new_status == "ROOT_CAUSED" and _gate_enabled("JIG_BUG_DIAGNOSE_GATE"):
        gaps = _diagnosis_gaps(text)
        tier = str(fields.get("tier") or "standard").strip().lower()
        if gaps and tier == "gnarly":
            raise BugError("diagnose gate missing: " + ", ".join(gaps))
        if gaps:
            print(
                "warning: diagnose gate missing: " + ", ".join(gaps),
                file=sys.stderr,
            )

    if new_status == "FIXING":
        if _gate_enabled("JIG_BUG_MAIN_CHECK_GATE"):
            gaps = _main_recheck_gaps(fields)
            if gaps:
                raise BugError(
                    "main recheck required before FIXING: " + ", ".join(gaps)
                    + ". Run `bug.py main-check <id> --result reproduces "
                    "--ref origin/main@<sha> --evidence \"...\"` after "
                    "checking fresh origin/main."
                )
        fix_class = str(fields.get("fix_class") or "").strip()
        if fix_class not in VALID_FIX_CLASSES:
            raise BugError(
                "fix_class must be one of: " + ", ".join(VALID_FIX_CLASSES)
            )
        selector = str(fields.get("regression_test") or "").strip()
        if not selector:
            raise BugError("regression_test is required before FIXING")
        if _gate_enabled("JIG_BUG_TEST_GATE"):
            result = _run_tdd(project_dir, selector)
            if result.returncode == 0:
                raise BugError(
                    "the regression test passes without a fix — it does not "
                    "capture the bug"
                )
            if result.returncode == 2:
                raise BugError(
                    "tdd.py environment error while checking regression test"
                )
            if result.returncode != 1:
                raise BugError(
                    f"unexpected tdd.py exit {result.returncode} while "
                    "checking red regression test"
                )
            text = set_frontmatter_field(text, "red_confirmed_at", _today())

    if new_status == "REVIEWED":
        selector = str(fields.get("regression_test") or "").strip()
        if not selector:
            raise BugError("regression_test is required before REVIEWED")
        if _gate_enabled("JIG_BUG_TEST_GATE"):
            result = _run_tdd(project_dir, selector)
            if result.returncode != 0:
                text = set_frontmatter_field(text, "status", "DIAGNOSING")
                text = _append_already_tried(
                    text,
                    f"green check failed for `{selector}` "
                    f"(tdd.py exit {result.returncode})",
                )
                atomic_write_text(path, text)
                raise BugError(
                    "green check failed; routed bug back to DIAGNOSING"
                )
            text = set_frontmatter_field(text, "green_confirmed_at", _today())
        diagnostics = _evidence.validate_bug_evidence(path, "REVIEWED")
        if diagnostics:
            raise BugError(
                "review evidence does not clear REVIEWED for bug "
                f"{path.name}:\n  - " + "\n  - ".join(diagnostics)
            )

    if new_status == "VERIFIED":
        if not _proof_attests_original_repro(text):
            raise BugError(
                "VERIFIED requires an attested re-run of the original "
                "reported repro in the bug record's ## Proof section"
            )

    if new_status == "DONE":
        if current == "REVIEWED" and _requires_verified(fields):
            raise BugError(
                "VERIFIED is required before DONE for gnarly or "
                "security-surface bugs"
            )
        diagnostics = _evidence.validate_bug_evidence(path, "REVIEWED")
        if diagnostics:
            raise BugError(
                "review evidence does not clear DONE for bug "
                f"{path.name}:\n  - " + "\n  - ".join(diagnostics)
            )
        if not _learning_recorded(project_dir, path):
            bug_id, _slug = _bug_id_and_slug(path)
            raise BugError(
                "DONE requires a learning recorded in "
                f"docs/memory/learnings.md for bug {bug_id}"
            )

    text = set_frontmatter_field(text, "status", new_status)
    atomic_write_text(path, text)
    return path


def record_main_check(
    project_dir: Path,
    ident: str,
    result: str,
    ref: str,
    evidence: str,
) -> Path:
    result = result.strip().lower().replace("-", "_")
    if result not in VALID_MAIN_REPRO_RESULTS:
        raise BugError(
            "main-check --result must be one of: reproduces, resolved-on-main"
        )
    if not evidence.strip():
        raise BugError(
            'main-check requires --evidence "<repro command + observed outcome>"'
        )
    ref = ref.strip() or "origin/main"
    path = _resolve_bug(project_dir, ident)
    text = path.read_text()
    fields, _ = parse_frontmatter(text)
    current = str(fields.get("status") or "").strip()
    if current != "ROOT_CAUSED":
        raise BugError(
            "main-check runs after ROOT_CAUSED and before FIXING "
            f"(current status: {current or '(empty)'})"
        )
    text = set_frontmatter_field(text, "main_repro_checked_at", _today())
    text = set_frontmatter_field(text, "main_repro_ref", ref)
    text = set_frontmatter_field(text, "main_repro_result", result)
    text = _append_main_recheck(text, ref, result, evidence)
    if result == "resolved_on_main":
        text = set_frontmatter_field(text, "status", "RESOLVED_ON_MAIN")
    atomic_write_text(path, text)
    return path


def _workflow_helper() -> Path:
    return Path(
        os.environ.get(
            "JIG_WORKFLOW_HELPER",
            str(Path(__file__).resolve().parent.parent / "spec-workflow" / "workflow.py"),
        )
    )


def _parse_reserved_spec(stdout: str) -> tuple[str, Path | None]:
    spec_num = ""
    spec_path: Path | None = None
    for line in stdout.splitlines():
        stripped = line.strip()
        m = re.search(r"\breserved\s+(\d{3})-", stripped)
        if m and not spec_num:
            spec_num = m.group(1)
        if stripped.endswith("spec.md"):
            spec_path = Path(stripped)
    if not spec_num:
        raise BugError("workflow.py new did not report a reserved spec number")
    return spec_num, spec_path


def _stamp_originated_from_bug(spec_path: Path, bug_id: str,
                               bug_rel: str) -> None:
    text = spec_path.read_text(encoding="utf-8")
    text = set_frontmatter_field(text, "originated_from_bug", bug_id)
    note = f"Originated from bug {bug_id}: `{bug_rel}`."
    if note.lower() not in text.lower():
        text = text.rstrip() + "\n\n" + note + "\n"
    atomic_write_text(spec_path, text)


def escalate_bug(project_dir: Path, ident: str, slug: str | None = None) -> Path:
    path = _resolve_bug(project_dir, ident)
    bug_id, bug_slug = _bug_id_and_slug(path)
    spec_slug = _slugify(slug or bug_slug)
    helper = _workflow_helper()
    result = subprocess.run(
        [
            sys.executable, str(helper), "new", spec_slug,
            "--project-dir", str(project_dir), "--no-push",
        ],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BugError(
            "workflow.py new failed while escalating bug "
            f"{bug_id}: {(result.stderr or result.stdout).strip()}"
        )
    spec_num, spec_path = _parse_reserved_spec(result.stdout)
    if spec_path is None:
        spec_path = project_layout.specs_dir(project_dir) / f"{spec_num}-{spec_slug}" / "spec.md"
    if not spec_path.is_file():
        raise BugError(f"escalated spec was not created: {spec_path}")
    bug_rel = str(path.relative_to(project_dir))
    _stamp_originated_from_bug(spec_path, bug_id, bug_rel)
    text = path.read_text()
    text = set_frontmatter_field(text, "escalated_to", spec_num)
    text = set_frontmatter_field(text, "status", "ESCALATED")
    atomic_write_text(path, text)
    return path


def _parse_existing_notes(existing: str) -> dict[tuple[str, str], str]:
    notes: dict[tuple[str, str], str] = {}
    row_re = re.compile(
        r"^\|\s*(\d{3})\s*\|\s*([^|]+?)\s*\|(?:[^|]*\|){7}\s*([^|\n]*?)\s*\|\s*$",
        re.MULTILINE,
    )
    for match in row_re.finditer(existing):
        bug_id = match.group(1).strip()
        slug = match.group(2).strip()
        note = match.group(3).strip()
        if bug_id == "ID":
            continue
        notes[(bug_id, slug)] = note
    return notes


def _bug_rows(project_dir: Path) -> list[dict[str, str]]:
    bugs_dir = _bugs_dir(project_dir)
    if not bugs_dir.is_dir():
        return []
    rows = []
    for path in sorted(bugs_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        bug_id, slug = _bug_id_and_slug(path)
        fields, _ = parse_frontmatter(path.read_text())
        red = str(fields.get("red_confirmed_at") or "").strip()
        main_result = str(fields.get("main_repro_result") or "").strip()
        rows.append({
            "id": bug_id,
            "slug": slug,
            "severity": str(fields.get("severity") or "").strip(),
            "tier": str(fields.get("tier") or "").strip(),
            "status": str(fields.get("status") or "").strip(),
            "reproduces": "yes" if red or main_result == "reproduces" else "no",
            "regression_test": str(fields.get("regression_test") or "").strip(),
            "claimed_by": str(fields.get("claimed_by") or "").strip(),
            "escalated_to": str(fields.get("escalated_to") or "").strip(),
        })
    return rows


def _render_board(rows: list[dict[str, str]],
                  notes: dict[tuple[str, str], str]) -> str:
    lines = [
        "| ID | slug | severity | tier | status | reproduces? | "
        "regression test | claimed_by | escalated_to | Notes |",
        "|----|------|----------|------|--------|-------------|"
        "-----------------|------------|--------------|-------|",
    ]
    for row in rows:
        note = notes.get((row["id"], row["slug"]), "")
        lines.append(
            f"| {row['id']} | {row['slug']} | {row['severity']} | "
            f"{row['tier']} | {row['status']} | {row['reproduces']} | "
            f"{row['regression_test']} | {row['claimed_by']} | "
            f"{row['escalated_to']} | {note} |"
        )
    return "\n".join(lines) + "\n"


def regenerate_status_board(project_dir: Path) -> Path:
    bugs_dir = _bugs_dir(project_dir)
    bugs_dir.mkdir(parents=True, exist_ok=True)
    board = bugs_dir / "README.md"
    existing = board.read_text() if board.exists() else "# Bug Status Board\n\n"
    notes = _parse_existing_notes(existing)
    table_start = existing.find("| ID |")
    preamble = existing[:table_start].rstrip() if table_start != -1 else existing.rstrip()
    if not preamble:
        preamble = "# Bug Status Board"
    content = preamble + "\n\n" + _render_board(_bug_rows(project_dir), notes)
    atomic_write_text(board, content)
    return board


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bug.py")
    project_parent = argparse.ArgumentParser(add_help=False)
    project_parent.add_argument(
        "--project-dir",
        default=".",
        help="project root containing docs/bugs (default: current directory)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    new_p = sub.add_parser(
        "new", parents=[project_parent], help="create a local bug record")
    new_p.add_argument("slug")
    new_p.add_argument("--push", action="store_true",
                       help="reserve the bug number on origin/main")
    new_p.add_argument("--pr", dest="pr_mode", action="store_true",
                       help="reserve the bug number on origin/main via PR")

    triage_p = sub.add_parser(
        "triage", parents=[project_parent], help="persist or de-escalate tier")
    triage_p.add_argument("id")
    triage_p.add_argument("--tier", choices=VALID_TIERS)
    triage_p.add_argument("--severity")

    pickup_p = sub.add_parser(
        "pickup", parents=[project_parent], help="claim or release a bug record")
    pickup_p.add_argument("id")
    pickup_p.add_argument("--release", action="store_true")
    pickup_p.add_argument("--reason")

    transition_p = sub.add_parser(
        "transition", parents=[project_parent], help="transition a bug record")
    transition_p.add_argument("id")
    transition_p.add_argument("status")

    main_check_p = sub.add_parser(
        "main-check",
        parents=[project_parent],
        help=(
            "record the post-root-cause check against fresh origin/main "
            "before FIXING"
        ),
    )
    main_check_p.add_argument("id")
    main_check_p.add_argument(
        "--result",
        required=True,
        choices=("reproduces", "resolved-on-main"),
        help=(
            "whether the original repro still fails on main or has already "
            "been resolved there"
        ),
    )
    main_check_p.add_argument(
        "--ref",
        default="origin/main",
        help="main ref/SHA that was checked (default: origin/main)",
    )
    main_check_p.add_argument(
        "--evidence",
        required=True,
        help="short note naming the repro command or observed outcome",
    )

    escalate_p = sub.add_parser(
        "escalate", parents=[project_parent],
        help="escalate a bug to a spec and mark it ESCALATED",
    )
    escalate_p.add_argument("id")
    escalate_p.add_argument("--slug")

    sub.add_parser(
        "status-board",
        parents=[project_parent],
        help="regenerate docs/bugs/README.md",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    project_dir = Path(ns.project_dir).resolve()
    try:
        if ns.command == "new":
            path = new_bug(
                project_dir, ns.slug, push=ns.push, pr_mode=ns.pr_mode,
            )
            if path is not None:
                print(path.relative_to(project_dir))
        elif ns.command == "triage":
            path = triage_bug(project_dir, ns.id, ns.tier, ns.severity)
            if path is not None:
                print(path.relative_to(project_dir))
            else:
                return 1
        elif ns.command == "pickup":
            path = pickup_bug(project_dir, ns.id, ns.release, ns.reason)
            print(path.relative_to(project_dir))
        elif ns.command == "transition":
            path = transition_bug(project_dir, ns.id, ns.status)
            print(path.relative_to(project_dir))
        elif ns.command == "main-check":
            path = record_main_check(
                project_dir, ns.id, ns.result, ns.ref, ns.evidence,
            )
            print(path.relative_to(project_dir))
        elif ns.command == "escalate":
            path = escalate_bug(project_dir, ns.id, ns.slug)
            print(path.relative_to(project_dir))
        elif ns.command == "status-board":
            path = regenerate_status_board(project_dir)
            print(path.relative_to(project_dir))
        else:  # pragma: no cover - argparse enforces this.
            parser.error(f"unknown command: {ns.command}")
    except BugError as exc:
        print(f"bug.py failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
