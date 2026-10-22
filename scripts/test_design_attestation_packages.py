"""120-01: actual installed/vendored review rail; all records are TEST ONLY."""

import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "scaffold-init"))

import build_host_packages
import scaffold


class DesignAttestationPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="jig-attestation-packages-")
        cls.base = Path(cls.tmp.name).resolve()
        cls.hosts = cls.base / "hosts"
        output = io.StringIO()
        result = build_host_packages.build_all(
            source_root=ROOT, hosts_root=cls.hosts, out=output)
        if result:
            raise AssertionError(output.getvalue())
        cls.runtimes = [
            cls.hosts / "claude" / "skills",
            cls.hosts / "codex" / "plugins" / "jig" / "skills",
            cls.hosts / "copilot" / ".github" / "skills",
        ]
        for host, infra in (("claude", ".claude"), ("codex", ".codex")):
            project = cls.base / ("vendored-" + host)
            project.mkdir()
            scaffold.copy_machinery(ROOT, project, host=host)
            cls.runtimes.append(project / infra / "skills")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cli(self, runtime, *args, skill="independent-review"):
        names = (skill, "jig-" + skill)
        helper = "workflow.py" if skill == "spec-workflow" else "review.py"
        script = next(runtime / name / helper for name in names
                      if (runtime / name / "SKILL.md").is_file())
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("JIG_")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(script), *map(str, args)],
            cwd=self.base, env=env, text=True, capture_output=True, timeout=30)

    def test_ships_generic_reader_and_reference_without_pilot_runtime(self):
        for runtime in self.runtimes:
            with self.subTest(runtime=runtime):
                for module in ("design_bindings.py", "static_design_bindings.py"):
                    self.assertTrue((runtime / "_common" / module).is_file())
                    self.assertEqual(
                        (runtime / "_common" / module).read_bytes(),
                        (ROOT / "skills" / "_common" / module).read_bytes())
                consumer = (runtime / "_common" / "design_bindings.py").read_text()
                self.assertNotIn('"c0"', consumer)
                self.assertNotIn("FILE_ROLES", consumer)
                self.assertFalse(list(runtime.rglob("card_*.py")))
                self.assertFalse(list(runtime.rglob("approved_card.py")))
                public = next(runtime / name for name in
                              ("independent-review", "jig-independent-review")
                              if (runtime / name / "SKILL.md").is_file())
                reference = public / "design-bindings.md"
                self.assertTrue(reference.is_file())
                self.assertNotIn("CLAUDE_PLUGIN_ROOT", reference.read_text())
                for path in (public / "SKILL.md", reference, public / "review.py"):
                    text = path.read_text()
                    for forbidden in ("/Users/", "approved-card",
                                      "0.1 fixtures/epoch support"):
                        self.assertFalse(forbidden in text, f"{path}: {forbidden}")
                    self.assertIsNone(re.search(r"\bC1\b", text), str(path))

    def test_public_legacy_and_retired_selection_behavior_in_each_install(self):
        for index, runtime in enumerate(self.runtimes):
            with self.subTest(runtime=runtime):
                fixture = self.base / ("legacy-case-" + str(index))
                fixture.mkdir()
                spec_dir = fixture / "docs" / "specs" / "999-test-only"
                spec_dir.mkdir(parents=True)
                spec = spec_dir / "spec.md"
                spec.write_text("---\nstatus: IN_PROGRESS\n---\n# TEST ONLY\n")
                slice_path = spec_dir / "slice-01-fixture.md"
                slice_path.write_text(
                    "---\nstatus: IN_PROGRESS\ndependencies: []\n"
                    "design_review: true\n---\n"
                    "## Slice 999-01 - fixture\n\nTEST ONLY synthetic prerequisites.\n")
                body = fixture / "body.txt"
                body.write_text(
                    "TEST ONLY fixture, not a real application's review or DONE.\n")
                for review_pass in ("compliance", "craft", "design-review"):
                    result = self.cli(
                        runtime, "record-review", spec, "999-01",
                        "--pass", review_pass, "--verdict", "pass",
                        "--reviewer", "test-only-synthetic",
                        "--prompt-source", "TEST ONLY package smoke",
                        "--summary-file", body)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = self.cli(
                    runtime, "check-reviews", spec, "999-01", "--stage", "REVIEWED")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                slice_path.write_text(slice_path.read_text() + (
                    "\n```jig-design-selection\n"
                    '{"schema":"jig/design-freshness/1","roots":{},"context":{}}\n'
                    "```\n"))
                previous = (spec_dir / "reviews" / "slice-01-design-review.md").read_bytes()
                result = self.cli(
                    runtime, "record-review", spec, "999-01", "--pass",
                    "design-review", "--verdict", "pass", "--reviewer",
                    "test-only-synthetic", "--prompt-source", "TEST ONLY retirement",
                    "--summary-file", body)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("retired", (result.stdout + result.stderr).lower())
                self.assertEqual(
                    (spec_dir / "reviews" / "slice-01-design-review.md").read_bytes(),
                    previous)
                result = self.cli(
                    runtime, "check-reviews", spec, "999-01", "--stage", "REVIEWED")
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("design-freshness", result.stdout + result.stderr)

    def test_selected_static_record_check_and_lifecycle_in_each_install(self):
        sys.path.insert(0, str(ROOT / "skills"))
        from _common.test_static_design_bindings import StaticFixture

        for index, (runtime, variant) in enumerate(
                product(self.runtimes, ("notice", "composer"))):
            with self.subTest(runtime=runtime, variant=variant):
                case = self.base / ("static-case-" + str(index))
                case.mkdir()
                fixture = StaticFixture(case, variant=variant)
                body = case / "test-only-attestation.txt"
                body.write_text(fixture.body())
                result = self.cli(
                    runtime, "design-review", fixture.spec, "999-01", body)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                public = next(runtime / name for name in
                              ("independent-review", "jig-independent-review")
                              if (runtime / name / "SKILL.md").is_file())
                self.assertIn(str(public / "design-bindings.md"), result.stdout)
                result = self.cli(
                    runtime, "record-review", fixture.spec, "999-01",
                    "--pass", "design-review", "--verdict", "pass",
                    "--reviewer", "test-only-synthetic", "--prompt-source",
                    "TEST ONLY supported static package smoke", "--summary-file", body)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = self.cli(
                    runtime, "check-reviews", fixture.spec, "999-01", "--stage", "REVIEWED")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = self.cli(
                    runtime, "transition", fixture.spec, "999-01", "REVIEWED",
                    skill="spec-workflow")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                before = fixture.slice.read_bytes()
                tree = fixture.context["trees"]["delivery"]
                delivered = fixture.project / tree["path"] / tree["files"][0]["path"]
                delivered.write_bytes(delivered.read_bytes() + b"\nTEST ONLY changed delivery")
                result = self.cli(
                    runtime, "check-reviews", fixture.spec, "999-01", "--stage", "REVIEWED")
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("design-freshness", result.stdout + result.stderr)
                result = self.cli(
                    runtime, "transition", fixture.spec, "999-01", "DONE",
                    skill="spec-workflow")
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("design-freshness", result.stdout + result.stderr)
                self.assertEqual(fixture.slice.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
