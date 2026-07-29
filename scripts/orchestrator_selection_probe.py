#!/usr/bin/env python3
"""orchestrator_selection_probe.py — spec 096-04 (ADR-0040 Assumptions).

Behavioral probe for the design's self-declared most likely failure mode: does an
orchestrating agent, given jig's SKILL.md recipe and a working `candidates` step,
actually RUN the sequence and emit a valid `--richer-skill <name|none>`?

This is a *compliance* question (did the agent run the step?), not a *visibility*
question (what was in the prompt) — so the behavioral run is the ground truth
(ADR-0040; slice 096-04 AC2). It is a necessary-condition FLOOR test: a stub
inherently foregrounds the recipe, so a PASS establishes reachability, not
durability under mid-slice cost pressure (durability rests on 096-05's
`substrate:` aggregate).

Method: in a fresh temp cwd per fixture we drop a stub `candidates` executable
that prints a fixed TIERED list (096-03's contract) and hand the agent jig's
recipe prose, then observe the final `RICHER_SKILL=<name|none>` line the recipe
asks it to emit (standing in for the real `--richer-skill` argument). This is a
*fresh-cwd* probe, not an isolated-home one — it intentionally uses the real host
auth, because the behavioral run needs a live agent loop.

**Two instruments (AC2).** The *behavioral* run is ground truth (did the agent
run the step?). For Codex a *context-inspection* diagnostic (`codex debug
prompt-input`, which renders the assembled prompt locally with NO API call and
NO auth) is the supporting instrument: it confirms the recipe text actually
reached the model-visible prompt, so a null behavioral result can be attributed
to host auth rather than a mis-registered fixture.

Two control fixtures make a null distinguishable from a mis-registered fixture
(AC2):
  - POSITIVE: non-empty tiered list → expect `RICHER_SKILL=review-pr-deep`
    (the agent ran `candidates` and picked the high-confidence candidate).
  - EMPTY:    `candidates` prints an empty list → expect `RICHER_SKILL=none`
    (the agent ran `candidates` and HONORED the empty result rather than
    fabricating a pick).

A host PASSes iff BOTH fixtures produce the expected emission. Any other outcome
(agent errored, could not run, host unavailable / unauthenticated) is
INCONCLUSIVE — never silently laundered into FAIL (AC3).

Usage:
    python3 scripts/orchestrator_selection_probe.py --host claude
    python3 scripts/orchestrator_selection_probe.py --host codex
    python3 scripts/orchestrator_selection_probe.py --host both   # default

Requires the host CLI on PATH: `claude` (uses `claude -p`) or `codex`
(uses `codex exec`). Re-runnable, with a fresh temp cwd per fixture — but NOT
hermetic: it deliberately uses the host's real auth, because the behavioral run
needs a live agent loop. The verdict-routing contract is separately unit-tested
via injected runners in `test_orchestrator_selection_probe.py`.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_RECIPE = """\
You are a review orchestrator about to run the craft (pr-review) pass. Before \
running it you MUST select which richer skill to apply, following these steps \
EXACTLY:

1. Run the executable in the current directory: `./candidates pr-review`
   It prints a tiered candidate list (a high-confidence tier and a speculative \
tier).
2. Choose the single BEST high-confidence candidate for the pr-review category. \
If the high-confidence tier is empty, choose `none`.
3. As your FINAL line, output your selection in EXACTLY this format (nothing \
after it):
   RICHER_SKILL=<name-or-none>

Do the steps now. You may run shell commands."""

_CANDIDATES_POSITIVE = """\
#!/usr/bin/env bash
# stub `candidates <category>` — prints a fixed tiered list (096-03 contract).
echo "CANDIDATES for category '${1:-pr-review}':"
echo "[high-confidence]"
echo "- review-pr-deep :: Deep, blocking-focused PR review with security checks"
echo "[speculative]"
echo "- morning-github :: Morning briefing that mentions staging draft PR reviews"
"""

_CANDIDATES_EMPTY = """\
#!/usr/bin/env bash
# stub `candidates <category>` — prints an EMPTY tiered list.
echo "CANDIDATES for category '${1:-pr-review}':"
echo "[high-confidence]"
echo "(none)"
echo "[speculative]"
echo "(none)"
"""

# Note: no `.` in the class, so a trailing sentence period
# (`RICHER_SKILL=none.`) is not absorbed into the value. Case-insensitive so a
# capitalized `None` reads as the empty pick, not a skill name.
_EMISSION_RE = re.compile(r"RICHER_SKILL=([A-Za-z0-9_-]+)", re.IGNORECASE)


def _write_fixture(root: Path, candidates_body: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix="jig-selprobe-", dir=root))
    cand = d / "candidates"
    cand.write_text(candidates_body)
    cand.chmod(0o755)
    return d


def _run_claude(cwd: Path, timeout: int) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["claude", "-p", _RECIPE,
         "--allowedTools", "Bash",
         "--permission-mode", "acceptEdits"],
        cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )


def _run_codex(cwd: Path, timeout: int) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["codex", "exec", "--skip-git-repo-check", _RECIPE],
        cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )


def _last_emission(output: str) -> "str | None":
    matches = _EMISSION_RE.findall(output or "")
    return matches[-1].lower() if matches else None


_AUTH_MARKERS = (
    "access token", "log out and sign in", "not authenticated",
    "please log in", "authentication required",
    "run `claude login`", "run `codex login`",
)


def _codex_prompt_has_recipe(cwd: Path, timeout: int) -> "bool | None":
    """AC2 supporting instrument: render Codex's model-visible prompt locally
    (`codex debug prompt-input`, NO API call / NO auth) and report whether the
    recipe's distinctive token (`candidates`) reached it. `None` if the
    diagnostic itself could not run. Lets a null behavioral result be attributed
    to host auth rather than a mis-registered fixture."""
    try:
        res = subprocess.run(
            ["codex", "debug", "prompt-input", _RECIPE],
            cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    blob = (res.stdout or "") + (res.stderr or "")
    if not blob.strip():
        return None
    return "candidates" in blob.lower()


def _probe_host(host: str, root: Path, timeout: int, *,
                runner=None, prompt_inspector=None,
                check_cli: bool = True) -> dict:
    """Probe one host. `runner(cwd, timeout) -> CompletedProcess` and
    `prompt_inspector(cwd, timeout) -> bool | None` are injectable so the
    verdict-routing contract can be table-tested without a live host (mirrors
    the injected-runner convention of the sibling `codex_*_probe.py` scripts).
    `check_cli=False` skips the PATH check for those tests."""
    runner = runner or (_run_claude if host == "claude" else _run_codex)
    prompt_inspector = prompt_inspector or _codex_prompt_has_recipe
    if check_cli and shutil.which(host) is None:
        return {"host": host, "verdict": "INCONCLUSIVE",
                "reason": f"{host} CLI not found on PATH"}
    fixtures = [("positive", _CANDIDATES_POSITIVE, "review-pr-deep"),
                ("empty", _CANDIDATES_EMPTY, "none")]
    observations = []
    for name, body, expected in fixtures:
        d = _write_fixture(root, body)
        try:
            res = runner(d, timeout)
        except subprocess.TimeoutExpired:
            # A timeout is a WEAK negative (host slowness / hang), never a
            # compliance FAIL — flag it so the verdict routes to INCONCLUSIVE
            # (AC3: no weak negative laundered into a decision).
            observations.append({"fixture": name, "emission": None,
                                 "expected": expected, "timed_out": True,
                                 "error": f"timed out after {timeout}s"})
            continue
        out = (res.stdout or "") + "\n" + (res.stderr or "")
        emission = _last_emission(out)
        # A revoked / unauthenticated host surfaces an auth error and never runs
        # the agent loop — mark INCONCLUSIVE rather than FAIL.
        auth_broken = any(m in out.lower() for m in _AUTH_MARKERS)
        observations.append({
            "fixture": name, "emission": emission, "expected": expected,
            "auth_broken": auth_broken,
            "tail": out.strip().splitlines()[-3:] if out.strip() else [],
        })
    # -- verdict: INCONCLUSIVE guards BEFORE the PASS/FAIL comparison ------
    if any(o.get("timed_out") for o in observations):
        return {"host": host, "verdict": "INCONCLUSIVE",
                "reason": "a fixture timed out (a weak negative — host slowness "
                          "or hang, not non-compliance); re-run",
                "observations": observations}
    if any(o.get("auth_broken") for o in observations):
        reason = ("host unauthenticated — agent loop never ran; re-auth and "
                  "re-run")
        if host == "codex":
            has_recipe = prompt_inspector(Path(root), timeout)
            if has_recipe is True:
                reason += (". Context-inspection (`codex debug prompt-input`) "
                           "CONFIRMS the recipe reached the model-visible "
                           "prompt, so the null is host-auth, not a "
                           "mis-registered fixture")
            elif has_recipe is False:
                reason += (". Context-inspection found the recipe ABSENT from "
                           "the prompt — investigate fixture registration")
        return {"host": host, "verdict": "INCONCLUSIVE", "reason": reason,
                "observations": observations}
    if all(o.get("emission") == o.get("expected") for o in observations):
        return {"host": host, "verdict": "PASS",
                "reason": "agent ran `candidates` and emitted the expected "
                          "RICHER_SKILL for both the non-empty and empty "
                          "fixtures",
                "observations": observations}
    # FAIL requires a POSITIVELY WRONG emission (a non-None value that does not
    # match) — a genuine positive signal of non-compliance. A missing emission
    # (None) is a weak negative, so any all-/partial-None-among-correct case
    # routes to INCONCLUSIVE, never FAIL (AC3).
    wrong = [o for o in observations
             if o.get("emission") is not None
             and o.get("emission") != o.get("expected")]
    if wrong:
        return {"host": host, "verdict": "FAIL",
                "reason": "agent emitted a positively WRONG selection "
                          f"({[o['emission'] for o in wrong]}) — non-compliance",
                "observations": observations}
    return {"host": host, "verdict": "INCONCLUSIVE",
            "reason": "at least one fixture produced no RICHER_SKILL emission "
                      "(a weak negative — cannot distinguish non-compliance "
                      "from a transient / mis-registered fixture); inspect tails",
            "observations": observations}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", choices=["claude", "codex", "both"],
                    default="both")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args(argv)
    hosts = ["claude", "codex"] if args.host == "both" else [args.host]
    with tempfile.TemporaryDirectory(prefix="jig-selprobe-root-") as root:
        results = [_probe_host(h, Path(root), args.timeout) for h in hosts]
    for r in results:
        print(f"\n=== HOST: {r['host']} — {r['verdict']} ===")
        print(f"reason: {r['reason']}")
        for o in r.get("observations", []):
            print(f"  [{o['fixture']}] emission={o.get('emission')!r} "
                  f"expected={o.get('expected')!r}"
                  + (f" error={o['error']}" if o.get("error") else ""))
            for line in o.get("tail", []):
                print(f"      | {line}")
    # Exit non-zero only on a genuine FAIL; INCONCLUSIVE is exit 0 (it is a
    # first-class outcome, not an error — AC3).
    return 1 if any(r["verdict"] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
