"""AC tests for slice 106-01 — governance plane + identity-separation gate.

Run from repo root:
    python3 -m unittest skills.scaffold-init.test_governance
or via the suite:
    python3 scripts/run_tests.py

Each test notes which AC it pins.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))

import governance  # noqa: E402


class ProtectedPathsTests(unittest.TestCase):
    """AC1/AC2 — the default protected-glob set, incl. the self-reference."""

    def test_default_set_contents(self):
        got = set(governance.PROTECTED_PATHS)
        for expected in (
            "docs/conventions.md",
            "docs/decisions/**",
            "oracle.sh",
            ".servo/**/config.json",
        ):
            self.assertIn(expected, got)

    def test_self_reference_holds_by_construction(self):
        # AC1/AC2 Kill-criteria: the governance plane's own files are protected.
        self.assertIn(".github/workflows/**", governance.PROTECTED_PATHS)
        self.assertIn("CODEOWNERS", governance.PROTECTED_PATHS)


class GlobMatcherTests(unittest.TestCase):
    """AC2/AC3 — the `**`-aware glob matcher."""

    def test_recursive_decisions(self):
        self.assertTrue(
            governance.path_matches_glob(
                "docs/decisions/adr-0001.md", "docs/decisions/**"
            )
        )

    def test_recursive_workflows(self):
        self.assertTrue(
            governance.path_matches_glob(
                ".github/workflows/x.yml", ".github/workflows/**"
            )
        )

    def test_exact_codeowners(self):
        self.assertTrue(governance.path_matches_glob("CODEOWNERS", "CODEOWNERS"))

    def test_non_match(self):
        self.assertFalse(
            governance.path_matches_glob("README.md", "docs/decisions/**")
        )
        for glob in governance.PROTECTED_PATHS:
            self.assertFalse(governance.path_matches_glob("README.md", glob))

    def test_servo_config(self):
        self.assertTrue(
            governance.path_matches_glob(
                ".servo/frozen/config.json", ".servo/**/config.json"
            )
        )

    def test_single_star_stops_at_slash(self):
        self.assertFalse(governance.path_matches_glob("a/b.py", "a*"))


class RenderCodeownersTests(unittest.TestCase):
    """AC1/AC5 — CODEOWNERS content."""

    def setUp(self):
        self.text = governance.render_codeowners()

    def test_has_owner_placeholder(self):
        self.assertIn("@OWNER", self.text)

    def test_owner_distinct_from_agent_documented(self):
        low = self.text.lower()
        self.assertIn("human", low)

    def test_surface_and_stop_rule(self):
        low = self.text.lower()
        self.assertIn("adr", low)
        self.assertTrue("102" in self.text)

    def test_inert_until_armed(self):
        low = self.text.lower()
        self.assertIn("inert", low)
        self.assertIn("branch protection", low)

    def test_all_paths_present(self):
        for glob in governance.PROTECTED_PATHS:
            self.assertIn(glob, self.text)


class RenderWorkflowTests(unittest.TestCase):
    """AC2 — the protected-path CI workflow YAML."""

    def setUp(self):
        self.text = governance.render_governance_workflow()

    def test_named_and_pr_triggered(self):
        self.assertIn("jig-governance", self.text)
        self.assertIn("pull_request", self.text)

    def test_mentions_branch_protection_inert(self):
        low = self.text.lower()
        self.assertIn("branch protection", low)
        self.assertIn("inert", low)

    def test_fetch_depth_zero(self):
        self.assertIn("fetch-depth", self.text)


class WorkflowDiffVerdictTests(unittest.TestCase):
    """AC2 — the unit-testable matching semantics."""

    def test_fail_on_protected_diff(self):
        verdict, matched = governance.workflow_diff_verdict(
            ["src/app.py", "docs/decisions/adr-0002.md"]
        )
        self.assertEqual(verdict, "fail")
        self.assertIn("docs/decisions/adr-0002.md", matched)

    def test_pass_on_non_protected_diff(self):
        verdict, matched = governance.workflow_diff_verdict(
            ["src/app.py", "README.md"]
        )
        self.assertEqual(verdict, "pass")
        self.assertEqual(matched, [])

    def test_fail_on_workflow_self_edit(self):
        verdict, matched = governance.workflow_diff_verdict(
            [".github/workflows/jig-governance.yml"]
        )
        self.assertEqual(verdict, "fail")


class RenderDocTests(unittest.TestCase):
    """AC5 — the governance doc."""

    def setUp(self):
        self.text = governance.render_governance_doc()

    def test_routing_rule(self):
        low = self.text.lower()
        self.assertIn("surface-and-stop", low)
        self.assertIn("102", self.text)

    def test_arming_checklist(self):
        low = self.text.lower()
        self.assertIn("branch protection", low)
        self.assertIn("code owner", low)
        self.assertIn("jig-governance", self.text)
        self.assertIn("bypass", low)

    def test_inert_statement(self):
        self.assertIn("inert", self.text.lower())

    def test_identity_note(self):
        low = self.text.lower()
        self.assertIn("identity", low)
        self.assertIn("merge", low)


class IdentitySeparationTests(unittest.TestCase):
    """AC4 — the four fixtures + fail-safe edges."""

    def test_single_identity_not_ready(self):
        v = governance.check_identity_separation("bot@x", merge_identity="bot@x")
        self.assertFalse(v.ready)
        self.assertIn("single", v.reason.lower())

    def test_distinct_but_capable_not_ready(self):
        v = governance.check_identity_separation(
            "bot@x", merge_identity="human@y", merge_capable=True
        )
        self.assertFalse(v.ready)

    def test_distinct_and_not_capable_ready(self):
        v = governance.check_identity_separation(
            "bot@x", merge_identity="human@y", merge_capable=False
        )
        self.assertTrue(v.ready)
        self.assertIn("least-privilege", v.reason.lower())

    def test_unknown_capability_not_ready(self):
        v = governance.check_identity_separation("bot@x")
        self.assertFalse(v.ready)
        self.assertIn("unavailable", v.reason.lower())

    def test_run_identity_missing_not_ready(self):
        v = governance.check_identity_separation("")
        self.assertFalse(v.ready)
        self.assertIn("run identity", v.reason.lower())

    def test_name_mismatch_without_attestation_not_ready(self):
        # Distinct name but capability unattested — mismatch does NOT prove
        # non-capability.
        v = governance.check_identity_separation("bot@x", merge_identity="human@y")
        self.assertFalse(v.ready)
        self.assertIn("unattested", v.reason.lower())

    def test_capable_flag_authoritative_over_names(self):
        # Same names but attested not-capable → ready (flag wins).
        v = governance.check_identity_separation(
            "bot@x", merge_identity="bot@x", merge_capable=False
        )
        self.assertTrue(v.ready)

    def test_normalized_identity_comparison(self):
        v = governance.check_identity_separation("Bot@X ", merge_identity="bot@x")
        self.assertFalse(v.ready)
        self.assertIn("single", v.reason.lower())

    def test_to_json_round_trips(self):
        v = governance.check_identity_separation(
            "bot@x", merge_identity="human@y", merge_capable=False
        )
        data = json.loads(v.to_json())
        self.assertEqual(data["ready"], True)
        self.assertEqual(data, v.as_dict())


class ParseCapableTests(unittest.TestCase):
    def test_truthy(self):
        for s in ("true", "1", "yes", "TRUE"):
            self.assertIs(governance._parse_capable(s), True)

    def test_falsy(self):
        for s in ("false", "0", "no"):
            self.assertIs(governance._parse_capable(s), False)

    def test_unknown(self):
        for s in ("unknown", "", None):
            self.assertIsNone(governance._parse_capable(s))


class CliTests(unittest.TestCase):
    """AC4 — machine-readable verdict + exit codes."""

    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(Path(governance.__file__)), *args],
            capture_output=True, text=True,
        )

    def test_identity_check_ready_exit_zero(self):
        r = self._run([
            "identity-check", "--run", "bot@x",
            "--merge", "human@y", "--merge-capable", "false",
        ])
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["ready"])

    def test_identity_check_not_ready_exit_three(self):
        r = self._run([
            "identity-check", "--run", "bot@x",
            "--merge", "bot@x", "--merge-capable", "true",
        ])
        self.assertEqual(r.returncode, 3, r.stderr)
        data = json.loads(r.stdout)
        self.assertFalse(data["ready"])

    def test_render_subcommands(self):
        for sub in ("render-codeowners", "render-workflow", "render-doc"):
            r = self._run([sub])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(r.stdout.strip())


if __name__ == "__main__":
    unittest.main()
