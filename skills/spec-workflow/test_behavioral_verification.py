"""Spec 118: proportional behavioral contracts and verification evidence."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "skills/independent-review/review.py"
WORKED = ROOT / "skills/spec-workflow/worked-example-behavioral-verification.md"
REVIEW_MARKER = "**Behavioral verification (when supplied)**"


def normalized(path: str) -> str:
    return " ".join((ROOT / path).read_text().lower().split())


class BehavioralRulesSurfaceTests(unittest.TestCase):
    def test_template_offers_traceable_optional_rules(self):
        text = (ROOT / "templates/docs/specs/slice-template.md").read_text()
        self.assertIn("### Behavioral rules (optional)", text)
        for column in ("Rule", "Operation/control", "Actor", "State/precondition",
                       "Outcome", "Rationale", "AC"):
            self.assertIn(column, text)
        lower = normalized("templates/docs/specs/slice-template.md")
        self.assertIn("omit", lower)
        self.assertIn("existing contract", lower)
        self.assertIn("ids do not encode precedence", lower)

    def test_authoring_guidance_reconciles_authority(self):
        text = normalized("skills/spec-workflow/SKILL.md")
        self.assertIn("behavioral rules", text)
        self.assertIn("ids do not encode precedence", text)
        self.assertIn("authority and revision", text)
        self.assertIn("demo does not override", text)

    def test_clarify_checks_state_and_preservation_without_new_taxonomy(self):
        text = normalized("skills/clarify/SKILL.md")
        self.assertIn("behavioral rules", text)
        self.assertIn("actor/state", text)
        self.assertIn("preservation paths", text)
        self.assertIn("authority and revision", text)
        self.assertIn("optional table", text)
        self.assertIn("up to five", text)


class VerificationScenarioSurfaceTests(unittest.TestCase):
    def test_template_records_reproducible_honest_evidence(self):
        text = (ROOT / "templates/docs/specs/slice-template.md").read_text()
        self.assertIn("### Verification scenario (optional)", text)
        for label in ("Preconditions", "Invocation", "Preserved behavior",
                      "Code revision", "dirty-change", "Expected", "Observed",
                      "Outcome", "Evidence"):
            self.assertIn(label, text)
        lower = normalized("templates/docs/specs/slice-template.md")
        for outcome in ("pass", "fail", "not-run", "environment-error"):
            self.assertIn(outcome, lower)
        self.assertIn("not a pass", lower)
        self.assertIn("required ac", lower)

    def test_authoring_and_clarification_reach_the_evidence_shape(self):
        authoring = normalized("skills/spec-workflow/SKILL.md")
        for phrase in ("verification scenario", "dirty-change", "not-run",
                       "environment-error", "existing test", WORKED.name):
            self.assertIn(phrase, authoring)
        clarify = normalized("skills/clarify/SKILL.md")
        self.assertIn("verification scenario", clarify)
        self.assertIn("environment", clarify)
        self.assertIn("expected and observed", clarify)

    def test_workflow_documentation_explains_optional_scope(self):
        for path in ("docs/workflow.md", "templates/docs/workflow.md.template"):
            with self.subTest(path=path):
                text = normalized(path)
                self.assertIn("behavioral rules", text)
                self.assertIn("verification scenario", text)
                self.assertIn("optional", text)

    def test_example_identifies_dirty_runtime_dependencies(self):
        self.assertTrue(WORKED.is_file())
        text = WORKED.read_text()
        self.assertIn('jig / "skills/_common"', text)
        self.assertIn('rglob("*.py")', text)
        self.assertIn('"runtime_manifest": runtime_manifest', text)
        self.assertIn('"dirty_change_identity": runtime_identity', text)
        self.assertIn('"python_version": sys.version', text)
        self.assertIn("runtime-sha256:", text)

    def test_worked_example_runs_real_cli_and_preservation_check(self):
        self.assertTrue(WORKED.is_file(), "A packaged runnable example is required")
        text = WORKED.read_text()
        script = re.search(r"<<'PY'\n(.*?)\nPY\n", text, re.DOTALL)
        self.assertIsNotNone(script, "Example must carry executable fixture steps")
        assert script is not None
        result = subprocess.run(
            [sys.executable, "-c", script.group(1), str(ROOT)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(
            [(step["ac"], step["outcome"]) for step in evidence["steps"]],
            [("AC-1", "pass"), ("AC-2", "pass")],
        )
        self.assertIn("1/2 slices done", evidence["steps"][0]["observed"])
        self.assertTrue(evidence["steps"][1]["unchanged"])
        self.assertTrue(evidence["code_revision"])
        self.assertIn("dirty_change_identity", evidence)
        self.assertIn("skills/spec-workflow/workflow.py", evidence["runtime_manifest"])
        self.assertTrue(any(path.startswith("skills/_common/")
                            for path in evidence["runtime_manifest"]))
        runtime_files = [ROOT / "skills/spec-workflow/workflow.py"] + sorted(
            path for path in (ROOT / "skills/_common").rglob("*.py")
            if not path.name.startswith("test_")
        )
        expected_manifest = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in runtime_files
        }
        self.assertEqual(evidence["runtime_manifest"], expected_manifest)
        self.assertEqual(
            evidence["dirty_change_identity"],
            "runtime-sha256:" + hashlib.sha256(
                json.dumps(expected_manifest, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        )
        self.assertEqual(evidence["coverage"], "fixture CLI, not live host hooks")


class BehavioralVerificationPromptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spec = Path(self.tmp.name) / "spec.md"
        self.spec.write_text(
            "# Spec\n\n## Slice 001-01 example\n\n**STATUS: IN_PROGRESS**\n\n"
            "**Acceptance Criteria:**\n1. Observable outcome.\n"
        )

    def prompt(self, mode: str) -> str:
        args = [sys.executable, str(REVIEW), mode, str(self.spec), "001-01"]
        if mode != "reconciliation":
            args += ["app.py"]
        if mode in ("pr-review", "arch-review", "code-health"):
            args += ["--richer-skill", "none", "--non-interactive"]
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_legacy_slice_gets_bounded_non_blocking_guidance(self):
        prompt = self.prompt("implementation")
        self.assertIn(REVIEW_MARKER, prompt)
        block = prompt.split(REVIEW_MARKER, 1)[1].split("\n## ", 1)[0]
        self.assertLessEqual(len(REVIEW_MARKER) + len(block), 1400)
        lower = " ".join(block.lower().split())
        for phrase in ("absence alone", "not a blocker", "owning ac",
                       "preserved behavior", "expected and observed", "code revision",
                       "dirty-change", "not-run", "environment-error", "not a pass"):
            self.assertIn(phrase, lower)

    def test_supplied_sections_keep_the_same_compliance_path(self):
        with self.spec.open("a") as handle:
            handle.write(
                "\n### Behavioral rules\n\nBR-1 -> AC-1\n"
                "\n### Verification scenario\n\nEnvironment unavailable; not-run.\n"
            )
        prompt = self.prompt("implementation")
        self.assertIn(REVIEW_MARKER, prompt)
        self.assertIn(str(self.spec), prompt)
        self.assertIn("VERDICT: pass | fail | needs-changes", prompt)

    def test_other_review_passes_do_not_gain_the_guidance(self):
        for mode in ("pr-review", "arch-review", "frame-critique",
                     "reconciliation", "design-review"):
            with self.subTest(mode=mode):
                self.assertNotIn(REVIEW_MARKER, self.prompt(mode))


if __name__ == "__main__":
    unittest.main()
