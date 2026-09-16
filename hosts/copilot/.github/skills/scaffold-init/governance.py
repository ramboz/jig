"""jig autonomy governance plane — slice 106-01 (ADR-0051).

Pure helpers (plus a thin CLI) for the *scaffoldable half* of the governance
firewall and the identity/capability-separation precondition for autonomy.

Two responsibilities, both deterministic and side-effect-free (the CLI is the
only I/O surface):

1. **Render the protected plane.** `render_codeowners`,
   `render_governance_workflow`, and `render_governance_doc` produce the
   CODEOWNERS file, the protected-path CI workflow, and the governance doc that
   `scaffold-init` writes. `PROTECTED_PATHS` is the single source of truth for
   the protected-glob set; note the **self-reference** — `.github/workflows/**`
   and `CODEOWNERS` are in the set by construction, so an ordinary PR that edits
   the CI job or removes the owner is itself gated (ADR-0051 Kill criteria).

   The scaffolded material states plainly that **these files are inert until
   branch protection is armed** (require-status-check + require-Code-Owner-review
   + forbid-bypass) — scaffold-init writes files, not server-side settings.

2. **Identity/capability separation.** `check_identity_separation` is a
   deterministic comparison **over supplied/attested inputs** — jig does not
   observe GitHub merge permissions in-process. It keys on merge *capability*,
   not identity name, and fails safe (reports not-ready) when the capability
   signal is unavailable. The servo readiness gate (servo 023) derives the
   capability input from the GitHub API and subprocess-invokes the CLI's
   `identity-check`. **Cross-repo contract (servo 023):** stdout is the
   `IdentityVerdict` JSON (the `ready` boolean is authoritative); exit code is
   `0` = ready, `3` = not-ready, `2` = argparse/usage error. Consumers should
   key on the `ready` field and/or exit `0` vs non-`0`; the `3` vs `2` split
   distinguishes a computed not-ready verdict from a malformed invocation.

Python 3.9 compatible. stdlib-only, no heavy imports.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Protected-glob set — the single source of truth.
# --------------------------------------------------------------------------- #
# NOTE the self-reference: `.github/workflows/**` and `CODEOWNERS` are members
# by construction, so the CI job and the owner list cannot be edited by an
# ordinary (non-owner-approved) PR — the property ADR-0051's Kill criteria
# require. `scaffold.py` mirrors this into `scaffold.json.protected_paths`,
# which the soft hooks read.
# NOTE `.servo/**/config.json` matches a config under a `.servo/` SUBDIRECTORY
# (e.g. `.servo/evals/config.json`) — not a top-level `.servo/config.json`. This
# is intentional: frozen servo configs live in named subtrees (ADR-0051 names
# "frozen `.servo/**/config.json`"), and `**` here requires an intervening
# segment. Widen to `.servo/**config.json` only if a top-level config ever needs
# protecting.
PROTECTED_PATHS: Tuple[str, ...] = (
    "docs/conventions.md",
    "docs/decisions/**",
    "oracle.sh",
    ".servo/**/config.json",
    ".github/workflows/**",
    "CODEOWNERS",
)

# Placeholder owner. Deliberately NOT any autonomous-agent identity — a human or
# team must own these paths for the non-author-approval gate to be real.
_PLACEHOLDER_OWNER = "@OWNER"


# --------------------------------------------------------------------------- #
# Glob matching (`**` recursive + `*` single-segment).
# --------------------------------------------------------------------------- #
def path_matches_glob(rel_path: str, glob: str) -> bool:
    """True iff project-relative posix `rel_path` matches `glob`.

    Supports `**` (matches across `/`) and `*` (matches within a segment). A
    `dir/**`-style glob also matches the directory prefix itself. Everything
    else is matched literally."""
    rel = rel_path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    glob = glob.replace("\\", "/")

    # A `dir/**` glob should also match the bare directory `dir`.
    if glob.endswith("/**"):
        prefix = glob[: -len("/**")]
        if rel == prefix:
            return True

    regex = _glob_to_regex(glob)
    return re.match(regex, rel) is not None


def _glob_to_regex(glob: str) -> str:
    out: List[str] = ["^"]
    i = 0
    n = len(glob)
    while i < n:
        c = glob[i]
        if c == "*":
            if i + 1 < n and glob[i + 1] == "*":
                out.append(".*")  # `**` — cross segment boundaries
                i += 2
                continue
            out.append("[^/]*")  # `*` — within a single segment
            i += 1
            continue
        out.append(re.escape(c))
        i += 1
    out.append("$")
    return "".join(out)


def workflow_diff_verdict(
    changed_paths, protected_globs=PROTECTED_PATHS
) -> Tuple[str, List[str]]:
    """Return ``("fail", [matched...])`` if any changed path matches a protected
    glob, else ``("pass", [])``.

    This is the unit-testable core the CI workflow's embedded python step
    inlines: a diff touching a protected path signals "owner review required"
    (the check fails); a clean diff passes."""
    matched: List[str] = []
    for path in changed_paths:
        path = (path or "").strip()
        if not path:
            continue
        if any(path_matches_glob(path, g) for g in protected_globs):
            matched.append(path)
    return ("fail", matched) if matched else ("pass", [])


# --------------------------------------------------------------------------- #
# Renderers — CODEOWNERS, the CI workflow, and the governance doc.
# --------------------------------------------------------------------------- #
def render_codeowners(paths=PROTECTED_PATHS, owner: str = _PLACEHOLDER_OWNER) -> str:
    """Render the GitHub CODEOWNERS file for the protected plane.

    The header states (a) these paths are governance-protected; (b) the
    surface-and-stop rule (open an ADR/spec, never a self-edit — spec 102); and
    (c) that these entries are **inert until branch protection is armed**. The
    `@OWNER` placeholder must be set to a human/team owner distinct from any
    autonomous agent."""
    header = f"""# jig governance plane — CODEOWNERS (scaffolded by scaffold-init, ADR-0051)
#
# These paths are GOVERNANCE-PROTECTED: they govern how this repo is changed
# (conventions, decision log, the oracle, the governance plane's own files).
#
# Surface-and-stop rule (spec 102): a change to any path below must open an
# ADR/spec and route through owner review — never a self-edit by the agent.
#
# INERT UNTIL ARMED: these CODEOWNERS entries enforce nothing on their own.
# They only force review once branch protection *requires review from Code
# Owners* AND *forbids bypassing* the rule (server-side settings scaffold-init
# cannot commit — see docs governance.md for the arming checklist).
#
# Set {owner} to a human or team owner DISTINCT from the autonomous agent — the
# non-author-approval gate is fictional if the agent can approve its own PR.
"""
    lines = [f"{glob} {owner}" for glob in paths]
    return header + "\n" + "\n".join(lines) + "\n"


def render_governance_workflow(paths=PROTECTED_PATHS) -> str:
    """Render the `jig-governance` GitHub Actions workflow.

    On every pull_request it computes the changed files and fails the check when
    any protected path is touched — signalling "owner review required". The
    matching semantics mirror :func:`workflow_diff_verdict` (unit-testable
    without running Actions).

    YAML comments state that this job only *flags* protected-path touches;
    actual approval enforcement is branch protection (require-this-status-check
    + require-Code-Owner-review + forbid-bypass), which scaffold-init cannot
    set — see the governance doc."""
    globs_literal = ", ".join(repr(g) for g in paths)
    return f"""# jig governance plane — protected-path CI (scaffolded, ADR-0051).
#
# This job only FLAGS a PR whose diff touches a governance-protected path, so an
# owner review is required. It is NOT enforcement on its own: actual approval
# enforcement is BRANCH PROTECTION (require this status check + require review
# from Code Owners + forbid bypassing), a server-side repository setting
# scaffold-init cannot commit. Until branch protection is armed this check is
# INERT — a red X nobody is required to heed. See docs governance.md for the
# arming checklist. The workflow file itself is a protected path (self-reference).
name: jig-governance

on:
  pull_request:

jobs:
  protected-paths:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Flag protected-path changes for owner review
        run: |
          git diff --name-only origin/${{{{ github.base_ref }}}}...HEAD > changed.txt
          python3 - <<'PY'
          import re, sys

          PROTECTED = [{globs_literal}]

          def glob_to_regex(glob):
              out = ["^"]
              i, n = 0, len(glob)
              while i < n:
                  c = glob[i]
                  if c == "*":
                      if i + 1 < n and glob[i + 1] == "*":
                          out.append(".*"); i += 2; continue
                      out.append("[^/]*"); i += 1; continue
                  out.append(re.escape(c)); i += 1
              out.append("$")
              return "".join(out)

          def matches(path, glob):
              path = path.replace("\\\\", "/")
              if path.startswith("./"):
                  path = path[2:]
              if glob.endswith("/**") and path == glob[:-3]:
                  return True
              return re.match(glob_to_regex(glob), path) is not None

          changed = [l.strip() for l in open("changed.txt") if l.strip()]
          hit = [p for p in changed if any(matches(p, g) for g in PROTECTED)]
          if hit:
              print("Protected paths touched — owner review required:")
              for p in hit:
                  print("  " + p)
              sys.exit(1)
          print("No protected paths touched.")
          PY
"""


def render_governance_doc(paths=PROTECTED_PATHS) -> str:
    """Render the markdown governance doc (`<docs>/governance.md`).

    Contains the surface-and-stop routing rule, the branch-protection arming
    checklist, the explicit "inert until armed" statement, and a note that
    autonomy-readiness additionally requires identity/capability separation."""
    path_list = "\n".join(f"- `{g}`" for g in paths)
    return f"""# Governance plane

> Scaffolded by jig `scaffold-init` (ADR-0051). This documents the *scaffoldable
> half* of the governance firewall and the out-of-band step that arms it.

## Protected paths

These paths govern how this repo changes and are owner-protected via
`CODEOWNERS` + the `jig-governance` CI workflow:

{path_list}

The set is the single source of truth in `scaffold.json` (`protected_paths`),
read by jig's soft hooks to nudge in-boundary; CI + branch protection enforce
out-of-boundary. Note the **self-reference**: `.github/workflows/**` and
`CODEOWNERS` are themselves protected, so the CI job and the owner list cannot
be edited without owner review.

## Governance-proposal routing (surface-and-stop, spec 102)

A change to a protected artifact must **open an ADR/spec and route through owner
review — never a self-edit**. Surface the conflict and stop; approving a
behaviour is not authority to rewrite the governing record.

## INERT UNTIL ARMED

The scaffolded `CODEOWNERS` + CI files enforce **nothing** on their own. They
become a blocking gate only once you complete the branch-protection arming step
below. A repo that looks protected but isn't is worse than an honest
recommendation — do not treat the scaffolded files as enforcement until armed.

## Branch-protection arming checklist

On the default branch (a server-side repository setting scaffold-init cannot
commit):

1. Enable branch protection on the default branch.
2. Require the `jig-governance` status check to pass before merging.
3. Require review from Code Owners.
4. Do not allow bypassing the above settings (forbid-bypass, including for
   admins).

The autonomy-readiness gate (servo) verifies the *armed* state — it is never
inferred from the presence of the scaffolded files.

## Identity / capability separation (autonomy precondition)

Arming branch protection is necessary but not sufficient. Autonomy-readiness
additionally requires **identity/capability separation**: the run identity (the
principal that runs the loop) must **not** be merge-capable — it must hold no
credential that can merge to the base branch or edit branch protection. A single
identity (the agent commits/pushes as the human) makes every owner-approval gate
fictional, and even a *distinct* bot that is merge-capable is over-privileged.

jig checks this deterministically over supplied/attested inputs
(`governance.py identity-check`); the servo readiness gate derives the
merge-capability input from the GitHub API and feeds it in. jig fails safe
(reports not-ready) when the capability signal is unavailable.
"""


# --------------------------------------------------------------------------- #
# Identity / capability separation.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class IdentityVerdict:
    """Machine-readable verdict for the identity-separation precondition."""

    ready: bool
    reason: str
    run_identity: Optional[str]
    merge_identity: Optional[str]
    merge_capable: Optional[bool]

    def as_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict())


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().casefold()


def check_identity_separation(
    run_identity: Optional[str],
    merge_identity: Optional[str] = None,
    merge_capable: Optional[bool] = None,
) -> IdentityVerdict:
    """Deterministic identity/capability-separation check over supplied inputs.

    Reports `ready` **only** for a distinct, least-privilege (not merge-capable)
    run identity. Keys on merge *capability*, not identity name; fails safe
    (not-ready) when the capability signal is unavailable. See ADR-0051 point 4.
    """
    if not (run_identity or "").strip():
        return IdentityVerdict(
            ready=False,
            reason="run identity unknown — cannot assess least-privilege",
            run_identity=None,
            merge_identity=merge_identity,
            merge_capable=merge_capable,
        )

    single_identity = False
    if merge_capable is not None:
        capable: Optional[bool] = bool(merge_capable)
        # A name match still colours the reason when capable.
        single_identity = (
            merge_identity is not None
            and _norm(run_identity) == _norm(merge_identity)
        )
    elif merge_identity is not None and merge_identity.strip():
        if _norm(run_identity) == _norm(merge_identity):
            capable = True
            single_identity = True
        else:
            # Distinct NAME does not prove non-capability — multiple
            # merge-capable principals can exist. Fail safe.
            return IdentityVerdict(
                ready=False,
                reason=(
                    "distinct identity but merge capability unattested — "
                    "cannot confirm least-privilege"
                ),
                run_identity=run_identity,
                merge_identity=merge_identity,
                merge_capable=None,
            )
    else:
        return IdentityVerdict(
            ready=False,
            reason="merge-capability signal unavailable (fail-safe)",
            run_identity=run_identity,
            merge_identity=merge_identity,
            merge_capable=None,
        )

    if capable:
        if single_identity:
            reason = (
                "single identity — run identity is the merge identity; no "
                "GitHub-side owner-approval gate can work"
            )
        else:
            reason = (
                "distinct but merge-capable (over-privileged) run identity — "
                "distinct name is necessary but not sufficient"
            )
        return IdentityVerdict(
            ready=False,
            reason=reason,
            run_identity=run_identity,
            merge_identity=merge_identity,
            merge_capable=True,
        )

    return IdentityVerdict(
        ready=True,
        reason="distinct, least-privilege run identity",
        run_identity=run_identity,
        merge_identity=merge_identity,
        merge_capable=False,
    )


def resolve_run_identity() -> Optional[str]:
    """Locally observable run identity: `JIG_RUN_IDENTITY` env else
    `git config user.email`. None when neither is available."""
    import os

    env = (os.environ.get("JIG_RUN_IDENTITY") or "").strip()
    if env:
        return env
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        email = (result.stdout or "").strip()
        return email or None
    except Exception:
        return None


def _parse_capable(s: Optional[str]) -> Optional[bool]:
    if s is None:
        return None
    v = s.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None  # "unknown" / "" / anything else


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="governance.py",
        description="jig autonomy governance plane (ADR-0051)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    ic = sub.add_parser(
        "identity-check",
        help="check the identity/capability-separation precondition",
    )
    ic.add_argument("--run", default=None, help="run identity (else resolved)")
    ic.add_argument("--merge", default=None, help="merge identity")
    ic.add_argument(
        "--merge-capable", choices=("true", "false", "unknown"), default=None,
        help="attested merge capability of the run identity",
    )

    sub.add_parser("render-codeowners", help="print the CODEOWNERS file")
    sub.add_parser("render-workflow", help="print the CI workflow YAML")
    sub.add_parser("render-doc", help="print the governance doc")

    args = parser.parse_args(argv)

    if args.cmd == "identity-check":
        run_identity = args.run if args.run is not None else resolve_run_identity()
        verdict = check_identity_separation(
            run_identity,
            merge_identity=args.merge,
            merge_capable=_parse_capable(args.merge_capable),
        )
        print(verdict.to_json())
        return 0 if verdict.ready else 3
    if args.cmd == "render-codeowners":
        print(render_codeowners(), end="")
        return 0
    if args.cmd == "render-workflow":
        print(render_governance_workflow(), end="")
        return 0
    if args.cmd == "render-doc":
        print(render_governance_doc(), end="")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
