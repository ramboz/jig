import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import ci_check
import skill_routing as sr


class CiCheckTests(unittest.TestCase):
    def test_ci_steps_roster_and_order(self):
        # Asserts ci_check's OWN step roster + order. It does NOT parse
        # .github/workflows/ci.yml — a real ci_check<->ci.yml parity guard is a
        # logged follow-up (spec 086-03 deviation log / refinement-todo).
        steps = ci_check.ci_steps("python3")
        self.assertEqual(
            [step.name for step in steps],
            [
                "Skill-routing eval",
                "Run test suite",
                "Lint specs",
                "Validate manifests",
                "Code-health floor",
                "Host-package drift guard",
            ],
        )
        # Routing gate runs FIRST so a regression fails the NAMED step; its floor
        # is single-sourced from the module so it can't lag a future ratchet.
        self.assertEqual(
            steps[0].argv,
            ("python3", "scripts/skill_routing.py",
             "--min-rank1", str(sr.MIN_RANK1_RATE)),
        )
        self.assertEqual(steps[1].argv, ("python3", "scripts/run_tests.py"))
        self.assertEqual(
            steps[4].argv,
            ("python3", "skills/code-health/health.py", "check", "."),
        )
        self.assertEqual(
            steps[5].argv,
            ("python3", "scripts/build_host_packages.py", "--check"),
        )

    def test_routing_regression_fails_named_gate_before_suite(self):
        # AC2 (086-03): verify the named-failure WIRING — a routing regression
        # must surface at the NAMED routing gate, not the anonymous "Run test
        # suite". We exercise the wiring with a fake runner that fails only the
        # routing step (the real collision / rank-1 regression is induced in
        # test_skill_routing.py) and assert run_steps stops there, having run and
        # named the routing gate before the suite.
        steps = ci_check.ci_steps("python3")
        self.assertEqual(steps[0].name, "Skill-routing eval")
        ran = []

        def fake_run(argv, cwd):
            ran.append(argv)
            rc = 1 if any("skill_routing.py" in a for a in argv) else 0
            return SimpleNamespace(returncode=rc)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ci_check.run_steps(steps, root=Path("/tmp/root"), run=fake_run)

        self.assertEqual(rc, 1)
        self.assertEqual(len(ran), 1)  # stopped at the routing gate; suite never ran
        self.assertIn("scripts/skill_routing.py", ran[0])
        self.assertIn("Skill-routing eval", buf.getvalue())  # the failure is NAMED

    def test_dependency_preflight_uses_jig_lint_command_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".jig").mkdir()
            (root / ".jig" / "lint-command").write_text(
                "pipx run --spec ruff==0.15.16 ruff check .\n",
                encoding="utf-8",
            )
            stderr = io.StringIO()

            ok = ci_check.dependencies_available(
                root=root,
                which=lambda name: None,
                stderr=stderr,
            )

        self.assertFalse(ok)
        self.assertIn("pipx", stderr.getvalue())
        self.assertIn(".jig/lint-command", stderr.getvalue())

    def test_run_steps_stops_on_first_failure(self):
        steps = (
            ci_check.CheckStep("one", ("one",)),
            ci_check.CheckStep("two", ("two",)),
        )
        calls = []

        def fake_run(argv, cwd):
            calls.append((argv, cwd))
            return SimpleNamespace(returncode=17)

        with redirect_stdout(io.StringIO()):
            result = ci_check.run_steps(steps, root=Path("/tmp/root"), run=fake_run)

        self.assertEqual(result, 17)
        self.assertEqual(calls, [(("one",), "/tmp/root")])


if __name__ == "__main__":
    unittest.main()
