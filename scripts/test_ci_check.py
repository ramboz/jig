import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import ci_check


class CiCheckTests(unittest.TestCase):
    def test_ci_steps_match_github_workflow_order(self):
        steps = ci_check.ci_steps("python3")
        self.assertEqual(
            [step.name for step in steps],
            [
                "Run test suite",
                "Lint specs",
                "Validate manifests",
                "Code-health floor",
                "Host-package drift guard",
            ],
        )
        self.assertEqual(steps[0].argv, ("python3", "scripts/run_tests.py"))
        self.assertEqual(
            steps[3].argv,
            ("python3", "skills/code-health/health.py", "check", "."),
        )
        self.assertEqual(
            steps[4].argv,
            ("python3", "scripts/build_host_packages.py", "--check"),
        )

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
