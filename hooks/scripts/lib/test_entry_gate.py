"""AC verification tests for spec 098-01 (lifecycle entry gate).

Run from the repo root:
    python3 -m unittest hooks/scripts/lib/test_entry_gate.py
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
# entry_gate imports `_common.*`, which lives under skills/.
for p in (str(HERE), str(REPO_ROOT / "skills")):
    if p not in os.sys.path:
        os.sys.path.insert(0, p)

import entry_gate  # noqa: E402


class EntryGateTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = tempfile.TemporaryDirectory()
        self.state_dir = self.state.name
        # Default identity for "this checkout" (no git needed).
        self._env = patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}, clear=False)
        self._env.start()
        # Ensure the opt-out is not set from the ambient environment.
        os.environ.pop("JIG_ENTRY_GATE", None)

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()
        self.state.cleanup()

    # ---- fixtures ----
    def _marker(self, content: str) -> None:
        d = self.root / ".jig"
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec-ref").write_text(content, encoding="utf-8")

    def _scaffold_json(self, docs_root: str) -> None:
        (self.root / "scaffold.json").write_text(
            json.dumps({"layout": {"docs_root": docs_root}}), encoding="utf-8")

    def _write_slice(self, *, spec="098", mm="01", slug="entry-gate",
                     status="IN_PROGRESS", claimed_by="wt-me", docs="docs") -> Path:
        base = self.root if docs == "." else self.root / docs
        d = base / "specs" / f"{spec}-{slug}"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"slice-{mm}-x.md"
        f.write_text(
            f"---\nstatus: {status}\nclaimed_by: {claimed_by}\n---\n## Slice\n",
            encoding="utf-8")
        return f

    def _write_bug(self, *, num="001", slug="x", status="DIAGNOSING",
                   claimed_by="wt-me", docs="docs") -> Path:
        base = self.root if docs == "." else self.root / docs
        d = base / "bugs"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{num}-{slug}.md"
        f.write_text(
            f"---\nstatus: {status}\nclaimed_by: {claimed_by}\n---\n## Symptom\n",
            encoding="utf-8")
        return f

    def _payload(self, file_path: str, *, session="s1", tool="Edit") -> dict:
        return {"tool_name": tool, "tool_input": {"file_path": file_path},
                "session_id": session}

    def _eval(self, file_path: str, **kw):
        return entry_gate.evaluate(self._payload(file_path, **kw),
                                   self.root, self.state_dir)


class InLifecycleTests(EntryGateTestBase):
    def test_out_of_lifecycle_source_edit_nudges_once(self):
        # No marker at all → clean tree → outside.
        out = self._eval(str(self.root / "app.py"))
        self.assertIsNotNone(out)
        self.assertIn("app.py", out)
        self.assertIn("informational, not a gate", out)

    def test_anti_dead_gate_unrelated_open_work_still_nudges(self):
        # The falsifying case: an unrelated IN_PROGRESS slice and an unclaimed
        # open bug exist, but this tree holds NO live claim (no marker). This is
        # jig's own `main` steady state; the pre-critique presence rule went
        # silent here. It must nudge.
        self._write_slice(spec="088", mm="02", slug="other",
                          status="IN_PROGRESS", claimed_by="someone-else")
        self._write_bug(num="008", slug="flaky", status="REPORTED",
                        claimed_by="detached")
        # no .jig/spec-ref marker in this tree
        out = self._eval(str(self.root / "app.py"))
        self.assertIsNotNone(out)

    def test_live_slice_claim_is_silent(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-me")
        self._marker("spec=098\nslice=098-01\n")
        self.assertIsNone(self._eval(str(self.root / "app.py")))

    def test_reconciliation_edit_is_silent(self):
        # anti-false-fire #1: editing architecture.md/CLAUDE.md during
        # reconciliation (slice at REVIEWED then RECONCILED, claim still held).
        self._marker("spec=098\nslice=098-01\n")
        for status in ("REVIEWED", "RECONCILED"):
            self._write_slice(status=status, claimed_by="wt-me")
            self.assertIsNone(
                self._eval(str(self.root / "CLAUDE.md")),
                f"should be silent while claim held at {status}")

    def test_reconciliation_silence_depends_on_claim_state(self):
        # The silence must come from the claim being HELD in a working status,
        # not from the marker alone. Flip the slice to a release point (DONE) and
        # the same edit must nudge — proving the status cross-check is load-bearing.
        self._marker("spec=098\nslice=098-01\n")
        self._write_slice(status="RECONCILED", claimed_by="wt-me")
        self.assertIsNone(self._eval(str(self.root / "CLAUDE.md")))
        self._write_slice(status="DONE", claimed_by="wt-me")
        self.assertIsNotNone(self._eval(str(self.root / "CLAUDE.md"),
                                        session="s2"))

    def test_bug_fix_picked_up_is_silent(self):
        # anti-false-fire #2: a bug opened via new_bug(push=True) then picked up
        # locally (098-04's marker). The local pickup is what quiets the gate.
        self._write_bug(num="007", slug="auth", status="REPORTED",
                        claimed_by="wt-me")
        self._marker("bug=007\n")
        self.assertIsNone(self._eval(str(self.root / "auth.py")))

    def test_bug_marker_in_working_status_is_silent(self):
        self._write_bug(num="007", slug="auth", status="FIXING",
                        claimed_by="wt-me")
        self._marker("bug=007\n")
        self.assertIsNone(self._eval(str(self.root / "auth.py")))

    def test_stale_slice_marker_at_release_point_nudges(self):
        # anti-stale-marker: nothing clears .jig/spec-ref when a slice leaves a
        # working state, so a DONE slice named by the marker must NOT read as
        # inside.
        self._write_slice(status="DONE", claimed_by="wt-me")
        self._marker("spec=098\nslice=098-01\n")
        self.assertIsNotNone(self._eval(str(self.root / "app.py")))

    def test_foreign_slice_claim_nudges(self):
        # branch scoping (AC2): marker names a slice claimed by a DIFFERENT
        # checkout → outside.
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-other")
        self._marker("spec=098\nslice=098-01\n")
        self.assertIsNotNone(self._eval(str(self.root / "app.py")))

    def test_foreign_bug_claim_nudges(self):
        self._write_bug(num="007", slug="auth", status="FIXING",
                        claimed_by="wt-other")
        self._marker("bug=007\n")
        self.assertIsNotNone(self._eval(str(self.root / "auth.py")))

    def test_unresolvable_marker_nudges(self):
        # Marker names a slice that does not exist on disk → cannot confirm
        # inside → nudge (never silently trust the marker).
        self._marker("spec=999\nslice=999-99\n")
        self.assertIsNotNone(self._eval(str(self.root / "app.py")))


class SourceBoundaryTests(EntryGateTestBase):
    def test_tracked_lifecycle_artifacts_are_silent(self):
        # Boundary (b): specs/, bugs/, decisions/, memory/ are TRACKED — the
        # case git check-ignore alone would miss.
        for rel in ("docs/specs/098-x/spec.md", "docs/bugs/001-x.md",
                    "docs/decisions/adr-0044-x.md", "docs/memory/glossary.md"):
            self.assertIsNone(self._eval(str(self.root / rel)),
                              f"{rel} is a lifecycle artifact — must be silent")

    def test_infra_dirs_are_silent(self):
        # Both host adapter dirs count as infra on the Claude host (dual-host
        # robustness — a Claude session editing an also-present `.codex/` is
        # silent, not nudged).
        for rel in (".jig/spec-ref", ".claude/settings.json", ".codex/hooks.json"):
            self.assertIsNone(self._eval(str(self.root / rel)))

    def test_source_file_nudges(self):
        self.assertIsNotNone(self._eval(str(self.root / "src" / "app.py")))

    def test_relocated_docs_root_artifacts_silent_source_nudges(self):
        self._scaffold_json("documentation")
        self.assertIsNone(
            self._eval(str(self.root / "documentation" / "specs" / "098-x" / "spec.md")))
        # A path under the DEFAULT "docs" dir is now source, not an artifact.
        self.assertIsNotNone(self._eval(str(self.root / "docs" / "notes.py")))

    def test_dot_docs_root_still_fires_on_source(self):
        # anti-dead-gate #2: docs_root="." makes docs_base == project root. A
        # "everything under docs_base" rule would silence the whole repo; the
        # named-subtree rule must still nudge on source at the root.
        self._scaffold_json(".")
        self.assertIsNotNone(self._eval(str(self.root / "app.py")))
        # ...while the named subtrees resolved at the root stay silent.
        self.assertIsNone(self._eval(str(self.root / "specs" / "098-x" / "spec.md")))
        self.assertIsNone(self._eval(str(self.root / "bugs" / "001-x.md")))

    def test_gitignored_path_is_silent(self):
        # Boundary (a): a real git repo with a .gitignore.
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / ".gitignore").write_text("build/\n*.pyc\n", encoding="utf-8")
        (self.root / "build").mkdir()
        self.assertIsNone(self._eval(str(self.root / "build" / "out.js")))
        self.assertIsNone(self._eval(str(self.root / "x.pyc")))
        # A non-ignored source file in the same repo still nudges.
        self.assertIsNotNone(self._eval(str(self.root / "app.py")))

    def test_git_check_ignore_error_degrades_without_raising(self):
        # git missing / erroring → degrade to boundary (b) only: artifacts stay
        # silent, source still nudges, never raises (AC8).
        with patch.object(entry_gate.subprocess, "run",
                          side_effect=OSError("no git")):
            self.assertIsNone(self._eval(str(self.root / "docs/specs/098-x/spec.md")))
            self.assertIsNotNone(self._eval(str(self.root / "app.py")))


class CadenceTests(EntryGateTestBase):
    def test_second_edit_same_state_is_silent(self):
        first = self._eval(str(self.root / "app.py"), session="sess")
        self.assertIsNotNone(first)
        second = self._eval(str(self.root / "other.py"), session="sess")
        self.assertIsNone(second, "cadence: at most once per session per state")

    def test_state_change_rearms_cadence(self):
        self.assertIsNotNone(self._eval(str(self.root / "app.py"), session="sess"))
        # Lifecycle state changes (a marker appears then is released) → re-arm.
        self._marker("bug=007\n")  # marker now present (different signature)
        self.assertIsNotNone(
            self._eval(str(self.root / "app.py"), session="sess"),
            "a lifecycle-state change must re-arm the nudge")

    def test_missing_session_id_does_not_globally_silence(self):
        # Two DIFFERENT sessions both with an empty session_id must each fire;
        # the gate must not dedupe them against a shared 'default' key.
        self.assertIsNotNone(self._eval(str(self.root / "a.py"), session=""))
        self.assertIsNotNone(self._eval(str(self.root / "b.py"), session=""))
        # And no 'default'-keyed state file was written.
        self.assertFalse(
            (Path(self.state_dir) / "jig-entry-gate-default.json").exists())


class FailOpenAndOptOutTests(EntryGateTestBase):
    def test_opt_out_disables(self):
        for token in ("0", "false", "off", "no"):
            with patch.dict(os.environ, {"JIG_ENTRY_GATE": token}):
                self.assertIsNone(self._eval(str(self.root / "app.py")))

    def test_non_edit_tool_is_ignored(self):
        self.assertIsNone(
            entry_gate.evaluate(self._payload(str(self.root / "app.py"), tool="Read"),
                                self.root, self.state_dir))

    def test_missing_file_path_returns_none(self):
        self.assertIsNone(entry_gate.evaluate(
            {"tool_name": "Edit", "tool_input": {}}, self.root, self.state_dir))

    def test_malformed_payload_returns_none(self):
        for bad in (None, "garbage", 42, {"tool_input": None}):
            self.assertIsNone(entry_gate.evaluate(bad, self.root, self.state_dir))


class ConstantSyncTests(unittest.TestCase):
    """The gate re-lists status sets for hook self-containment; pin them in sync
    with their source-of-truth constants so a lifecycle change can't drift them."""

    def test_slice_working_statuses_match_workflow(self):
        import importlib.util
        wf = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
        spec = importlib.util.spec_from_file_location("wf_sync", wf)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(entry_gate._SLICE_WORKING_STATUSES,
                         set(mod._CLAIM_WORKING_STATUSES))

    def test_bug_open_statuses_match_bug_py(self):
        import importlib.util
        bp = REPO_ROOT / "skills" / "bug-fix" / "bug.py"
        spec = importlib.util.spec_from_file_location("bug_sync", bp)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(entry_gate._BUG_OPEN_STATUSES, set(mod.OPEN_STATUSES))

    def test_disable_values_match_parsing_env_falsey(self):
        from _common.parsing import ENV_FALSEY
        self.assertEqual(entry_gate._DISABLE_VALUES, set(ENV_FALSEY))


class GitTimeoutTests(EntryGateTestBase):
    def test_hung_git_times_out_and_still_evaluates(self):
        # A hung git must not stall the session: the subprocess timeout raises
        # TimeoutExpired, which is swallowed → claim identity degrades to
        # "detached" and the boundary degrades to (b)-only, so a source edit
        # still nudges rather than hanging.
        import subprocess as _sp
        with patch.object(entry_gate.subprocess, "run",
                          side_effect=_sp.TimeoutExpired(cmd="git", timeout=5)):
            out = self._eval(str(self.root / "app.py"))
        self.assertIsNotNone(out)

    def test_git_subprocess_calls_pass_a_timeout(self):
        # Guard the fix directly: every subprocess.run in entry_gate must carry a
        # timeout kwarg (a hung git otherwise stalls every edit).
        calls = []
        real = entry_gate.subprocess.run

        def recording(*args, **kwargs):
            calls.append(kwargs)
            return real(*args, **kwargs)

        # git repo so check-ignore actually runs; no JIG_CLAIM_ID so git branch runs.
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JIG_CLAIM_ID", None)
            with patch.object(entry_gate.subprocess, "run", side_effect=recording):
                self._eval(str(self.root / "app.py"))
        self.assertTrue(calls, "expected at least one git subprocess call")
        for kw in calls:
            self.assertIn("timeout", kw, "every git subprocess.run must set timeout")


if __name__ == "__main__":
    unittest.main()
