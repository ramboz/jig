"""
copilot_live_hook_smoke.py — slice 113-08 (live-hook-runtime-contract), AC5.

The repeatable, AUTHENTICATED/MANUAL E2E smoke command AC5 requires: a real
`copilot` CLI session, driven against a fresh install of the committed
`hosts/copilot/` package (or a freshly-built one), that proves at least one
ADVISORY hook and one ENFORCING hook actually fire THROUGH COPILOT'S OWN
hook runtime — not a constructed-payload direct adapter invocation.

Why this is a SEPARATE script from the test suite, not a `unittest` case
`python3 -m unittest discover` picks up by default: it requires a signed-in
`copilot` CLI (an interactive `copilot login`, or an inherited
`GH_TOKEN`/`COPILOT_GH_ACCOUNT_*` session) able to make a real,
non-interactive `-p` model call. A CI runner or a fresh contributor
checkout has neither by default — the SAME reason
`scripts/orchestrator_selection_probe.py` treats an unauthenticated host as
INCONCLUSIVE rather than a plain pass/fail. `scripts/test_copilot_live_hook_smoke.py`
unit-tests this module's PURE log-parsing/detection helpers (deterministic,
no CLI, always run in CI) and gates the one true end-to-end invocation of
`run_smoke()` behind `shutil.which("copilot")` AND an explicit
`JIG_COPILOT_LIVE_HOOK_E2E=1` opt-in (a live model call costs real
quota/money and must never run silently on every `unittest discover`).

HONEST LABELLING (AC5's other half): `test_build_copilot_plugin.py`'s
`CopilotAdvisoryHookPackagingTests` / `CopilotEnforcingHookPackagingTests`
(`_run_rendered_command` helpers) are STATIC PACKAGE CHECKS — they invoke
the rendered `bash` command directly with a constructed stdin payload and a
manually-set `cwd`/`CLAUDE_PROJECT_DIR`. They prove the command, once
spawned, behaves correctly — they do NOT prove Copilot itself discovers,
resolves, and spawns that command from an installed plugin cache with a
real working directory. THIS script is what proves that; those are not
E2E and their own docstrings/class names say so.

What this proves, mechanically:
  1. Installs `--package` (default: the committed `hosts/copilot/`) into a
     fresh, isolated `COPILOT_HOME` — the real
     `copilot plugin install <path>` path, same as
     `CopilotLivePluginDiscoverySmokeTests` (113-07).
  2. Starts one non-interactive `copilot -p` session (`--allow-all-tools`,
     `--silent`) with `--log-level debug --log-dir <tmp>`, from a fresh git
     repo containing `docs/conventions.md`, asking the model to reply
     `READY` without using tools. Copilot's SessionStart advisory hooks
     fire unconditionally at session start — this session's debug log is
     parsed for a genuine `additionalContext` hook-stdout line (AC1 + AC2 —
     "asserts the emitted Copilot continuation/context response, not just
     a zero exit code").
  3. Starts a second session asking the model to edit
     `docs/conventions.md` via its edit tool. The rendered `jig-spec-gate`
     enforcing hook (`preToolUse`/`edit|create`) must fire; the log is
     parsed for a genuine `{"permissionDecision": "deny", ...}` hook-stdout
     line (AC1 + AC3's "known-disallowed operation ... deny decision with a
     reason").
  4. Starts a third session asking the model to edit a plain `README.md`
     file — the safe-operation counterpart AC3 also requires ("a safe
     operation remains allowed"): the log must show NO deny for that
     session, and the file must actually change.

Exit codes (machine-checkable — AC5's "success evidence"):
    0  every check passed.
    1  the CLI ran (authenticated) but the expected evidence was absent —
       a genuine hook-runtime failure.
    2  INCONCLUSIVE: `copilot` is not installed, or the session could not
       authenticate — not a proof of failure either way.

Usage:
    python3 scripts/copilot_live_hook_smoke.py [--package <hosts/copilot dir>]
        [--keep] [--timeout <seconds>]

A JSON summary (one object, `{"verdict": ..., "checks": {...}}`) is always
printed to stdout, whatever the exit code — the "machine-checkable success
evidence" AC5 requires, parseable by a caller without re-deriving it from
free-form CLI transcript text.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Mirrors `orchestrator_selection_probe._AUTH_MARKERS` — the same
# "an unauthenticated host surfaces an auth error and never really runs"
# idiom, restated here (not imported) since these two probes fire against
# different CLIs (`copilot` vs. `claude`/`codex`) with their own message
# text, and neither module currently depends on the other.
_AUTH_MARKERS = (
    "access token", "log out and sign in", "not authenticated",
    "please log in", "authentication required", "run `copilot login`",
    "no github account", "sign in with", "login required",
)

# The exact log substring Copilot's Rust hook runtime writes for a hook's
# raw stdout (observed live against installed CLI 1.0.86-0's
# `--log-level debug` output — see the slice's report for the capture
# session). One JSON object always follows on the SAME line.
_HOOK_STDOUT_RE = re.compile(r"\[hook stdout\]\s+(\{.*\})\s*$")


def find_copilot_binary() -> "str | None":
    return shutil.which("copilot")


def is_unauthenticated(text: str) -> bool:
    """Return True when `text` (combined stdout+stderr from a `copilot`
    invocation) looks like an auth failure rather than a genuine run —
    pure, synthetic-log-testable (see `_AUTH_MARKERS`)."""
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _AUTH_MARKERS)


def iter_hook_stdout_events(log_text: str) -> list[dict]:
    """Parse every `[hook stdout] {...}` line out of a Copilot debug log
    into its JSON body. Malformed JSON on a matched line is skipped (never
    raises) — a real log line's JSON is always well-formed; a skip here
    would only mask a body this function does not need to understand."""
    events: list[dict] = []
    for line in (log_text or "").splitlines():
        match = _HOOK_STDOUT_RE.search(line)
        if not match:
            continue
        try:
            body = json.loads(match.group(1))
        except ValueError:
            continue
        if isinstance(body, dict):
            events.append(body)
    return events


def find_advisory_context(log_text: str) -> "str | None":
    """Return the first non-empty `additionalContext` string emitted by any
    hook in `log_text`, or `None` if none fired — AC2's "asserts the
    emitted Copilot continuation/context response, not just a zero exit
    code"."""
    for event in iter_hook_stdout_events(log_text):
        context = event.get("additionalContext")
        if isinstance(context, str) and context.strip():
            return context
    return None


def find_permission_deny(log_text: str) -> "str | None":
    """Return the first `permissionDecisionReason` for an event whose
    `permissionDecision` is `"deny"`, or `None` if no hook denied anything —
    AC3's "verifies Copilot receives a deny decision with a reason"."""
    for event in iter_hook_stdout_events(log_text):
        if event.get("permissionDecision") == "deny":
            return event.get("permissionDecisionReason") or ""
    return None


def any_permission_deny(log_text: str) -> bool:
    return any(
        event.get("permissionDecision") == "deny"
        for event in iter_hook_stdout_events(log_text)
    )


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True,
    )


def _init_project(work_dir: Path) -> None:
    (work_dir / "docs").mkdir(parents=True, exist_ok=True)
    (work_dir / "docs" / "conventions.md").write_text(
        "# Conventions\nRule 1: do not break things.\n"
    )
    (work_dir / "README.md").write_text("hello\n")
    _git(["init", "-q", "-b", "main"], work_dir)
    _git(["config", "user.email", "jig-smoke@example.com"], work_dir)
    _git(["config", "user.name", "jig-smoke"], work_dir)
    _git(["add", "."], work_dir)
    _git(["commit", "-q", "-m", "init"], work_dir)


def _run_copilot(
    copilot_bin: str, *, copilot_home: Path, cwd: Path, log_dir: Path,
    prompt: str, timeout: int,
) -> tuple["subprocess.CompletedProcess[str]", str]:
    """Run one non-interactive `copilot -p` session with debug logging to a
    FRESH per-call log directory (so each session's log is unambiguous —
    no need to disambiguate multiple `process-*.log` files by timestamp).
    Returns the completed process and the concatenated text of every log
    file written this call."""
    log_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            copilot_bin, "-C", str(cwd), "--log-level", "debug",
            "--log-dir", str(log_dir), "-p", prompt,
            "--allow-all-tools", "--silent",
        ],
        cwd=str(cwd),
        env={**_env_with_home(copilot_home)},
        capture_output=True, text=True, timeout=timeout,
    )
    log_text = "\n".join(
        p.read_text(errors="replace") for p in sorted(log_dir.glob("*.log"))
    )
    return result, log_text


def _env_with_home(copilot_home: Path) -> dict:
    import os
    return {**os.environ, "COPILOT_HOME": str(copilot_home)}


def run_smoke(
    package_dir: Path, *, timeout: int = 90, keep: bool = False,
) -> dict:
    """Drive the full live smoke sequence and return the JSON-serializable
    summary this module's `main()` prints. Never raises for an
    ordinary CLI/auth failure — those are reported as the `INCONCLUSIVE`
    verdict; only a genuine internal bug should raise."""
    package_dir = package_dir.resolve()
    copilot_bin = find_copilot_binary()
    if copilot_bin is None:
        return {
            "verdict": "INCONCLUSIVE",
            "reason": "copilot CLI not found on PATH",
            "checks": {},
        }

    tmp = Path(tempfile.mkdtemp(prefix="jig-copilot-live-hook-smoke-"))
    copilot_home = tmp / "copilot_home"
    checks: dict = {}
    try:
        install = subprocess.run(
            [copilot_bin, "plugin", "install", str(package_dir)],
            capture_output=True, text=True, timeout=timeout,
            env=_env_with_home(copilot_home),
        )
        install_out = install.stdout + install.stderr
        if is_unauthenticated(install_out):
            return {
                "verdict": "INCONCLUSIVE",
                "reason": "copilot plugin install looked unauthenticated",
                "checks": {"install": install_out.strip()},
            }
        if install.returncode != 0:
            return {
                "verdict": "FAIL",
                "reason": "copilot plugin install failed",
                "checks": {"install": install_out.strip()},
            }
        checks["install"] = "ok"

        # -- Advisory: SessionStart fires unconditionally. ---------------
        advisory_dir = tmp / "advisory-work"
        _init_project(advisory_dir)
        advisory_res, advisory_log = _run_copilot(
            copilot_bin, copilot_home=copilot_home, cwd=advisory_dir,
            log_dir=tmp / "advisory-logs", timeout=timeout,
            prompt="Reply with exactly READY. Do not use any tools.",
        )
        combined = advisory_res.stdout + advisory_res.stderr
        if is_unauthenticated(combined) or is_unauthenticated(advisory_log):
            return {
                "verdict": "INCONCLUSIVE",
                "reason": "copilot session looked unauthenticated",
                "checks": checks,
            }
        advisory_context = find_advisory_context(advisory_log)
        checks["advisory_additional_context"] = advisory_context
        if not advisory_context:
            return {
                "verdict": "FAIL",
                "reason": "no advisory hook additionalContext observed in the "
                          "session's debug log",
                "checks": checks,
            }

        # -- Enforcing: a gated edit must be denied. ---------------------
        enforcing_dir = tmp / "enforcing-work"
        _init_project(enforcing_dir)
        enforcing_res, enforcing_log = _run_copilot(
            copilot_bin, copilot_home=copilot_home, cwd=enforcing_dir,
            log_dir=tmp / "enforcing-logs", timeout=timeout,
            prompt=(
                "Add a line 'Rule 2: be nice.' to docs/conventions.md using "
                "your edit tool. Just do it, don't ask."
            ),
        )
        deny_reason = find_permission_deny(enforcing_log)
        checks["enforcing_permission_deny_reason"] = deny_reason
        if not deny_reason:
            return {
                "verdict": "FAIL",
                "reason": "no permissionDecision:deny observed for the gated "
                          "docs/conventions.md edit",
                "checks": checks,
            }

        # -- Safe operation: an ungated edit is allowed. ------------------
        safe_dir = tmp / "safe-work"
        _init_project(safe_dir)
        safe_res, safe_log = _run_copilot(
            copilot_bin, copilot_home=copilot_home, cwd=safe_dir,
            log_dir=tmp / "safe-logs", timeout=timeout,
            prompt="Add a line 'safe edit' to README.md using your edit tool.",
        )
        safe_denied = any_permission_deny(safe_log)
        safe_readme = safe_dir / "README.md"
        safe_file_changed = (
            safe_readme.is_file()
            and "safe edit" in safe_readme.read_text(errors="replace")
        )
        checks["safe_operation_denied"] = safe_denied
        checks["safe_operation_file_changed"] = safe_file_changed
        if safe_denied or not safe_file_changed:
            return {
                "verdict": "FAIL",
                "reason": "the safe README.md edit was denied or did not apply",
                "checks": checks,
            }

        return {"verdict": "PASS", "checks": checks}
    except subprocess.TimeoutExpired as exc:
        return {
            "verdict": "INCONCLUSIVE",
            "reason": f"a copilot invocation timed out after {timeout}s: {exc}",
            "checks": checks,
        }
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept working tree at: {tmp}", file=sys.stderr)


_EXIT_CODES = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package", type=Path, default=REPO_ROOT / "hosts" / "copilot",
        help="Copilot package directory to install (default: hosts/copilot)",
    )
    parser.add_argument(
        "--timeout", type=int, default=90,
        help="per-copilot-invocation timeout in seconds (default: 90)",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="keep the temporary COPILOT_HOME/work directories for inspection",
    )
    return parser


def main(argv: list) -> int:
    args = _build_parser().parse_args(argv)
    if not (args.package / ".plugin" / "plugin.json").is_file():
        print(json.dumps({
            "verdict": "INCONCLUSIVE",
            "reason": f"{args.package} is not a built Copilot package "
                      "(missing .plugin/plugin.json)",
            "checks": {},
        }))
        return _EXIT_CODES["INCONCLUSIVE"]
    summary = run_smoke(args.package, timeout=args.timeout, keep=args.keep)
    print(json.dumps(summary, indent=2))
    return _EXIT_CODES.get(summary["verdict"], 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
