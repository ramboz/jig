"""
AC verification tests for slice 003-01 (lifecycle-helper).

Run from the repo root:
    python3 skills/spec-workflow/test_workflow.py
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
WORKFLOW = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_workflow(*args: str, gate: bool = False) -> subprocess.CompletedProcess:
    """Invoke workflow.py as a subprocess.

    Slice 045-03: the review-evidence gate (`transition → REVIEWED/
    RECONCILED/DONE`) is ON by default in production. The pre-045-03 test
    suite transitions to those gated states WITHOUT recording evidence,
    so this helper sets the documented bypass `JIG_REVIEW_EVIDENCE_GATE=0`
    by default — tests that aren't *about* the gate keep their old
    behavior. Gate-specific tests pass `gate=True` to exercise the real
    enforcement (or set the env var explicitly).
    """
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if not gate:
        env["JIG_REVIEW_EVIDENCE_GATE"] = "0"
    else:
        # Ensure an inherited bypass from the parent shell can't mask a
        # gate-on test.
        env.pop("JIG_REVIEW_EVIDENCE_GATE", None)
    return subprocess.run(
        [sys.executable, str(WORKFLOW), *args],
        capture_output=True, text=True, env=env,
    )


def scaffold(target: Path) -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target)],
        capture_output=True, text=True, env=env, check=True,
    )


def write_synthetic_spec(path: Path, slices: list) -> None:
    """Build a spec.md from a list of (slice_name, status) pairs."""
    lines = ["---", "status: DRAFT", "---", "", "# Spec X", "", "## Overview", "", "synthetic.", ""]
    for name, status in slices:
        lines.extend([
            "---",
            "",
            f"## Slice {name}",
            "",
            f"**STATUS: {status}**",
            "",
            "**Goal:** placeholder.",
            "",
        ])
    path.write_text("\n".join(lines))


class TransitionTests(unittest.TestCase):
    """workflow.py transition <spec.md> <slice-name> <new-status>."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_transition_updates_status(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT"),
                                          ("001-02 beta", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self.spec.read_text()
        # The named slice should be transitioned
        m = re.search(r"## Slice 001-01[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", content)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "IN_PROGRESS")
        # The other slice should be untouched
        m2 = re.search(r"## Slice 001-02[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", content)
        self.assertEqual(m2.group(1), "DRAFT")

    def test_transition_chains(self):
        """Multiple sequential transitions on the same slice work."""
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        for new_status in ("IN_PROGRESS", "REVIEWED", "RECONCILED", "DONE"):
            r = run_workflow("transition", str(self.spec), "001-01", new_status)
            self.assertEqual(r.returncode, 0, f"failed at {new_status}: {r.stderr}")
        content = self.spec.read_text()
        self.assertIn("**STATUS: DONE**", content)

    def test_slice_path_transition_is_not_overwritten_by_spec_rollup(self):
        """Issue #86: a slice-file input must resolve its sibling overview.

        Before the fix, the requested status was written to the slice and then
        `_write_spec_rollup()` treated that same slice path as `spec.md`,
        overwriting `status:` back to the computed spec rollup. The
        `last_verified` stamp survived because the rollup only writes status.
        """
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec 002\n"
        )
        target = self.spec.parent / "slice-01-add-and-view.md"
        sibling = self.spec.parent / "slice-02-more.md"
        target.write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 002-01 — add and view\n\nBody.\n"
        )
        sibling.write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 002-02 — more\n\nBody.\n"
        )

        expected_old = "IN_PROGRESS"
        for new_status in ("REVIEWED", "RECONCILED", "DONE"):
            result = run_workflow(
                "transition", str(target), "002-01", new_status,
            )
            self.assertEqual(
                result.returncode, 0,
                f"failed at {new_status}: {result.stderr}",
            )
            self.assertIn(
                f"{expected_old} → {new_status}", result.stdout,
            )
            self.assertRegex(
                target.read_text(),
                rf"(?m)^status:\s*{new_status}\s*$",
            )
            self.assertRegex(
                self.spec.read_text(),
                r"(?m)^status:\s*IN_PROGRESS\s*$",
            )
            expected_old = new_status

        today = __import__("datetime").date.today().isoformat()
        self.assertIn(f"last_verified: {today}", target.read_text())
        self.assertRegex(
            sibling.read_text(), r"(?m)^status:\s*DRAFT\s*$",
        )

    def test_missing_slice_path_is_rejected_before_fragment_lookup(self):
        """A typo in the path must not fall through to a real sibling slice."""
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 002\n"
        )
        target = self.spec.parent / "slice-01-real.md"
        target.write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 002-01 — real\n\nBody.\n"
        )
        missing = self.spec.parent / "slice-99-typo.md"

        result = run_workflow(
            "transition", str(missing), "002-01", "IN_PROGRESS",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr.lower())
        self.assertRegex(
            target.read_text(), r"(?m)^status:\s*DRAFT\s*$",
        )

    def test_transition_refuses_invalid_status(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "BOGUS")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status", result.stderr.lower())

    def test_transition_refuses_unknown_slice(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "999-99", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr.lower() + result.stdout.lower())

    def test_transition_refuses_ambiguous_slice(self):
        """If two slices match the name fragment, refuse to transition either."""
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT"),
                                          ("001-01 alpha-fork", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambig", result.stderr.lower() + result.stdout.lower())

    def test_transition_lenient_on_slice_name_match(self):
        """`001-01` should match `## Slice 001-01 — greenfield-scaffold` (substring)."""
        self.spec.write_text(
            "# Spec X\n\n## Slice 001-01 — greenfield-scaffold\n\n**STATUS: DRAFT**\n"
        )
        result = run_workflow("transition", str(self.spec), "001-01", "DONE")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DONE**", self.spec.read_text())

    def test_transition_prints_summary(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "IN_PROGRESS")
        self.assertEqual(result.returncode, 0)
        self.assertIn("DRAFT", result.stdout)
        self.assertIn("IN_PROGRESS", result.stdout)

    def test_transition_does_not_clobber_prose_status_marker(self):
        """Inbox 2026-05-18 `spec-workflow/transition/status-marker-clobber` —
        the status-rewrite regex `(\\*\\*STATUS:\\s*)([A-Z_]+)(\\*\\*)`
        matched the FIRST `**STATUS: …**` anywhere in the slice section
        body, not the slice's own status line.

        Hit on slice 030-01 (a per-file slice that uses frontmatter-only
        status, no prose `**STATUS:**` line) during REVIEWED → RECONCILED:
        the deviation log quoted another slice's marker in prose. The
        regex had nothing canonical to find for THIS slice's own status,
        so it matched the prose example and rewrote DRAFT → RECONCILED
        in the quoted text. Frontmatter `status:` still flipped correctly
        (so lifecycle-wise harmless), but the prose got corrupted.

        Synthetic spec: a per-file-style slice with frontmatter-only
        status (no prose STATUS line at the top) whose deviation log
        contains a prose example with `**STATUS: DEFERRED**` markup.
        After `transition ... IN_PROGRESS`:
        - The frontmatter `status:` field must read `IN_PROGRESS`.
        - The prose example must read `**STATUS: DEFERRED**` unchanged.
        """
        # Sibling slice file (post-018 layout — frontmatter authoritative,
        # no prose `**STATUS:**` line at the top).
        slice_file = self.spec.parent / "slice-01-alpha.md"
        slice_file.write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified: 2026-05-19\n---\n\n"
            "## Slice 001-01 — alpha\n\n"
            "**Goal:** placeholder.\n\n"
            "**DoD:**\n- [x] placeholder.\n\n"
            "### Deviation log (after reconciliation)\n\n"
            "When slice 002-02 was parked, its marker read "
            "`**STATUS: DEFERRED**` per the convention — that should "
            "stay unchanged when this slice transitions.\n"
        )
        # Parent spec.md pointing at the sibling slice (the parser walks
        # both inline `## Slice X` sections AND sibling slice-*.md files).
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n## Overview\n\nsynthetic.\n"
        )
        result = run_workflow("transition", str(self.spec), "001-01",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        slice_text = slice_file.read_text()
        # Frontmatter status must be flipped.
        self.assertRegex(slice_text,
                         r"(?m)^status:\s*IN_PROGRESS\s*$",
                         "frontmatter status was not updated")
        # The prose-quoted marker must be untouched.
        self.assertIn("`**STATUS: DEFERRED**`", slice_text,
                      "prose-quoted STATUS marker was clobbered")
        # And no spurious `**STATUS: IN_PROGRESS**` should have been
        # written into the slice body — frontmatter-only slices stay
        # frontmatter-only.
        self.assertNotIn("**STATUS: IN_PROGRESS**", slice_text,
                         "transition leaked a prose STATUS line into a "
                         "frontmatter-only slice")


class SpecRefMarkerTests(unittest.TestCase):
    """Slice 056-03: transition -> IN_PROGRESS stamps a `.jig/spec-ref`
    marker in the project working tree recording the spec number + the
    current slice. The write is idempotent and best-effort (never blocks
    the transition or its review-evidence gates).
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-specref-")
        # A project-root layout so workflow.py can derive the root from the
        # spec path (docs/specs/<dir>/spec.md -> parents[3] is the root, the
        # `.jig/` home). The root needn't be a scaffold for the marker write.
        self.root = Path(self.tmpdir) / "proj"
        self.spec_dir = self.root / "docs" / "specs" / "056-token-usage-tracking"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, label: str, status: str = "DRAFT") -> None:
        self.spec.write_text(
            f"---\nstatus: {status}\n---\n\n# Spec X\n\n## Overview\n\nsynthetic.\n"
            f"\n## Slice {label}\n\n"
            f"**STATUS: {status}**\n\n**Goal:** placeholder.\n"
        )

    def _marker(self) -> Path:
        return self.root / ".jig" / "spec-ref"

    def test_in_progress_writes_spec_ref_marker(self):
        self._write_slice("056-03 alpha")
        result = run_workflow("transition", str(self.spec), "056-03",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        marker = self._marker()
        self.assertTrue(marker.is_file(), "marker not written")
        text = marker.read_text()
        # Records the spec number AND the current slice, parseably.
        self.assertRegex(text, r"(?m)^spec=056\s*$")
        self.assertRegex(text, r"(?m)^slice=056-03\s*$")

    def test_marker_is_idempotent_across_repeated_transitions(self):
        self._write_slice("056-03 alpha")
        run_workflow("transition", str(self.spec), "056-03", "IN_PROGRESS")
        first = self._marker().read_text()
        # Transition the same slice to IN_PROGRESS again (idempotent re-stamp).
        run_workflow("transition", str(self.spec), "056-03", "IN_PROGRESS")
        second = self._marker().read_text()
        self.assertEqual(first, second, "re-stamp duplicated / drifted marker")

    def test_marker_reflects_the_transitioning_slice(self):
        # Two slices; transitioning the SECOND must stamp slice=056-02.
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n## Overview\n\nsynthetic.\n"
            "\n## Slice 056-01 first\n\n**STATUS: DONE**\n\n**Goal:** x.\n"
            "\n## Slice 056-02 second\n\n**STATUS: DRAFT**\n\n**Goal:** y.\n"
        )
        run_workflow("transition", str(self.spec), "056-02", "IN_PROGRESS")
        text = self._marker().read_text()
        self.assertRegex(text, r"(?m)^spec=056\s*$")
        self.assertRegex(text, r"(?m)^slice=056-02\s*$")

    def test_non_in_progress_transition_does_not_require_marker(self):
        # A DRAFT->READY transition is not the stamping point; it must not
        # fail even though no marker is written for it.
        self._write_slice("056-03 alpha")
        result = run_workflow("transition", str(self.spec), "056-03",
                              "READY_FOR_IMPLEMENTATION")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    def test_marker_write_failure_does_not_block_transition(self):
        # AC1/AC4: a failed marker write must NOT block the transition.
        # Simulate an unwritable target by occupying `.jig` with a regular
        # FILE (so `.jig/spec-ref` can't be created — NotADirectoryError).
        self._write_slice("056-03 alpha")
        (self.root / ".jig").write_text("not a directory")
        result = run_workflow("transition", str(self.spec), "056-03",
                              "IN_PROGRESS")
        # Transition still succeeds despite the marker write failing.
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # And the status actually flipped.
        self.assertIn("**STATUS: IN_PROGRESS**", self.spec.read_text())

    def test_marker_write_does_not_disturb_review_evidence_gate(self):
        # AC4 regression: the marker write is additive — it must not affect
        # the review-evidence gate. With the gate ON and no evidence, a
        # transition to REVIEWED must STILL be refused (the marker logic does
        # not run for REVIEWED, and does not relax the gate).
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n## Overview\n\nsynthetic.\n"
            "\n## Slice 056-03 alpha\n\n**STATUS: IN_PROGRESS**\n\n"
            "**Goal:** placeholder.\n"
        )
        result = run_workflow("transition", str(self.spec), "056-03",
                              "REVIEWED", gate=True)
        self.assertNotEqual(result.returncode, 0,
                            "review-evidence gate must still refuse REVIEWED")
        self.assertIn("review evidence", result.stderr.lower())


class StatusBoardTests(unittest.TestCase):
    """workflow.py status-board <project-dir>."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-board-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)
        # Drop in synthetic specs
        spec1 = self.target / "docs/specs/100-alpha"
        spec1.mkdir(parents=True)
        write_synthetic_spec(spec1 / "spec.md", [
            ("100-01 first", "DONE"),
            ("100-02 second", "IN_PROGRESS"),
            ("100-03 third", "DRAFT"),
        ])
        spec2 = self.target / "docs/specs/101-beta"
        spec2.mkdir(parents=True)
        write_synthetic_spec(spec2 / "spec.md", [
            ("101-01 alpha", "RECONCILED"),
        ])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_board_regenerates_table(self):
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        # All four slices should be in the table
        self.assertIn("100-01 first", board)
        self.assertIn("100-02 second", board)
        self.assertIn("100-03 third", board)
        self.assertIn("101-01 alpha", board)
        # And their statuses
        self.assertRegex(board, r"100-01[^|]*\|[^|]*DONE")
        self.assertRegex(board, r"101-01[^|]*\|[^|]*RECONCILED")

    def test_status_board_preserves_preamble(self):
        # Inject a preamble before the existing table
        board_path = self.target / "docs/specs/README.md"
        original = board_path.read_text()
        preamble = "# Spec Status Board\n\n> Custom preamble that must survive regen.\n\n"
        board_path.write_text(preamble + original)
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0)
        new_content = board_path.read_text()
        self.assertIn("Custom preamble that must survive regen", new_content)

    def test_status_board_preserves_existing_notes(self):
        """Curated Notes column content must survive regen."""
        # First regen to establish baseline table
        run_workflow("status-board", str(self.target))
        board_path = self.target / "docs/specs/README.md"
        content = board_path.read_text()
        # Hand-edit a Note cell for one slice (DONE statuses render as **DONE**)
        new_content = content.replace(
            "| 100-01 first | **DONE** |  |",
            "| 100-01 first | **DONE** | 42 tests green; reviewed + reconciled |",
        )
        self.assertNotEqual(new_content, content, "test setup failed: edit was a no-op")
        board_path.write_text(new_content)
        # Second regen — the curated Note must survive
        run_workflow("status-board", str(self.target))
        new_content = board_path.read_text()
        self.assertIn("42 tests green; reviewed + reconciled", new_content)

    def test_status_board_preamble_links_bug_board(self):
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        preamble = board.split("| Spec |", 1)[0]
        self.assertIn("../bugs/README.md", preamble)
        self.assertIn("Bug Status Board", preamble)

    def test_status_board_idempotent(self):
        """Re-running on a current board produces no change."""
        run_workflow("status-board", str(self.target))
        first = (self.target / "docs/specs/README.md").read_text()
        run_workflow("status-board", str(self.target))
        second = (self.target / "docs/specs/README.md").read_text()
        self.assertEqual(first, second)


class SkillPromotionTests(unittest.TestCase):
    """The spec-workflow SKILL.md must be promoted from stub to active."""

    def setUp(self):
        self.skill_path = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
        self.skill = self.skill_path.read_text()

    def test_skill_frontmatter_has_no_disable_invocation(self):
        # Extract frontmatter
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md must have frontmatter")
        fm = m.group(1)
        self.assertNotIn("disable-model-invocation: true", fm,
                         "spec-workflow must auto-trigger (frontmatter promoted)")

    def test_skill_is_user_invocable(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        # user-invocable should be true (or absent — default is true)
        self.assertNotIn("user-invocable: false", fm)

    def test_skill_body_no_stub_banner(self):
        """The 'Status: DRAFT — not yet implemented' banner must be gone."""
        self.assertNotRegex(
            self.skill,
            r"(?i)status:\s*draft\s*—\s*not\s+yet\s+implemented",
            "stub banner must be removed",
        )
        self.assertNotIn("(when implemented)", self.skill,
                         "'when implemented' phrasing must be removed")

    def test_creating_spec_cross_checks_bug_registry(self):
        creating = self.skill.split("### Creating a new spec", 1)[1].split(
            "### Picking up a slice", 1,
        )[0]
        self.assertIn("docs/bugs/README.md", creating)
        self.assertIn("feedback/triage", creating)
        self.assertIn("bug-fix", creating)

    def test_skill_reconciliation_checklist_intact(self):
        """Slice 002-04's reconciliation checklist with memory-sync must survive."""
        # Locate the reconciliation H2
        header = re.search(r"(?im)^##\s+[^\n]*reconcil[^\n]*$", self.skill)
        self.assertIsNotNone(header)
        rest = self.skill[header.end():]
        nxt = re.search(r"(?m)^##\s", rest)
        section = rest[: nxt.start()] if nxt else rest
        self.assertIn("memory-sync", section,
                      "memory-sync must stay in the reconciliation section after promotion")
        self.assertIn("Primer hygiene", section)
        self.assertIn("CLAUDE.md", section)
        self.assertIn("AGENTS.md", section)
        self.assertIn("scaffold templates", section)
        self.assertNotIn("**CLAUDE.md hygiene**", section,
                         "live checklist should use host-portable primer hygiene")
        live_surfaces = "\n".join(
            [
                self.skill,
                (REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md").read_text(),
                (REPO_ROOT / "skills" / "spec-workflow" / "workflow.py").read_text(),
                (REPO_ROOT / "docs" / "workflow.md").read_text(),
            ]
        )
        self.assertNotIn("CLAUDE.md hygiene", live_surfaces,
                         "live workflow surfaces should use primer hygiene")
        self.assertNotIn("REVIEWED --> RECONCILED: review pass + deviation log\n", live_surfaces,
                         "workflow summaries should include the reconciliation sweep gate")
        self.assertIn("Reconciliation sweep", section,
                      "closing guidance must name the sweep transition gate")

    def test_skill_references_workflow_helper(self):
        """The promoted SKILL.md should tell Claude to use workflow.py."""
        self.assertIn("workflow.py", self.skill,
                      "SKILL.md must reference the workflow.py helper")


class AutoTickReviewPassedTests(unittest.TestCase):
    """Slice 003-04: workflow.py transition auto-ticks the two review-passed
    DoD boxes on the gating transitions."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-autotick-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, slice_name: str, status: str, dod_lines: list) -> None:
        body = [
            "---", "status: DRAFT", "---", "",
            "# Spec X", "",
            f"## Slice {slice_name}", "",
            f"**STATUS: {status}**", "",
            "**Goal:** placeholder.", "",
            "**Definition of Done:**", "",
        ]
        body.extend(dod_lines)
        self.spec.write_text("\n".join(body) + "\n")

    def _read(self) -> str:
        return self.spec.read_text()

    # AC #1
    def test_transition_to_REVIEWED_auto_ticks_implementation_review(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [ ] Implementation review passed.",
            "- [ ] Reconciliation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        self.assertIn("- [x] Implementation review passed.", text)
        # Recon row stays unticked
        self.assertIn("- [ ] Reconciliation review passed.", text)

    # AC #2
    def test_transition_to_RECONCILED_auto_ticks_reconciliation_review(self):
        self._write("009-99 alpha", "REVIEWED", [
            "- [x] Implementation review passed.",
            "- [ ] Reconciliation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "RECONCILED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        self.assertIn("- [x] Reconciliation review passed.", text)

    # AC #3
    def test_other_transitions_leave_checkboxes_alone(self):
        self._write("009-99 alpha", "DRAFT", [
            "- [ ] Implementation review passed.",
            "- [ ] Reconciliation review passed.",
        ])
        # DRAFT → READY_FOR_REVIEW shouldn't touch the boxes
        result = run_workflow("transition", str(self.spec), "009-99", "READY_FOR_REVIEW")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        self.assertIn("- [ ] Implementation review passed.", text)
        self.assertIn("- [ ] Reconciliation review passed.", text)

    def test_RECONCILED_to_DONE_does_not_re_tick(self):
        self._write("009-99 alpha", "RECONCILED", [
            "- [x] Implementation review passed.",
            "- [x] Reconciliation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "DONE")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # Both stay ticked, neither is added/removed
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)
        self.assertEqual(text.count("- [x] Reconciliation review passed."), 1)

    # AC #4 (idempotent)
    def test_auto_tick_is_idempotent_when_box_already_ticked(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [x] Implementation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # Still exactly one ticked instance, no `- [x] - [x]` corruption
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)

    # AC #4 (scoping: Close-out subsection excluded)
    def test_auto_tick_skips_close_out_subsection(self):
        body = [
            "---", "status: DRAFT", "---", "",
            "# Spec X", "",
            "## Slice 009-99 alpha", "",
            "**STATUS: IN_PROGRESS**", "",
            "**Definition of Done:**", "",
            "- [ ] Implementation review passed.",
            "",
            "### Close-out (post-DONE)",
            "",
            "- [ ] Implementation review passed.  # would be a duplicate label if reached",
            "",
        ]
        self.spec.write_text("\n".join(body) + "\n")
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # The DoD line (above Close-out) is ticked
        self.assertIn("- [x] Implementation review passed.", text)
        # The Close-out duplicate stays unticked
        # (count: 1 ticked + 1 unticked-in-Close-out = 1 each)
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)
        self.assertEqual(
            text.count("- [ ] Implementation review passed."), 1,
            f"Close-out duplicate should remain unticked; spec was:\n{text}",
        )

    # AC #4 (scoping: other slices in same spec untouched)
    def test_auto_tick_does_not_touch_other_slices(self):
        body = [
            "---", "status: DRAFT", "---", "",
            "# Spec X", "",
            "## Slice 009-99 alpha", "",
            "**STATUS: IN_PROGRESS**", "",
            "**Definition of Done:**", "",
            "- [ ] Implementation review passed.",
            "",
            "## Slice 009-98 beta", "",
            "**STATUS: DRAFT**", "",
            "**Definition of Done:**", "",
            "- [ ] Implementation review passed.",  # should stay unticked
            "",
        ]
        self.spec.write_text("\n".join(body) + "\n")
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # alpha is ticked; beta is not
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)
        self.assertEqual(text.count("- [ ] Implementation review passed."), 1)

    # AC #5 (multiple matches in same DoD: warn + skip + name spec/slice)
    def test_auto_tick_warns_on_multiple_matches_and_skips_all(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [ ] Implementation review passed (first take).",
            "- [ ] Implementation review passed (second take).",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0,
                         msg=f"transition should still succeed; stderr: {result.stderr}")
        text = self._read()
        # Neither got ticked
        self.assertEqual(text.count("- [x] Implementation review passed"), 0)
        # Stderr describes the ambiguity AND names the spec + slice so a
        # CI/log grep can disambiguate which slice triggered the warning.
        self.assertRegex(
            result.stderr,
            r"(?i)multiple.*implementation review passed",
            "stderr should describe the ambiguous match",
        )
        self.assertIn(
            "spec.md", result.stderr,
            f"stderr should name the spec file; got: {result.stderr!r}",
        )
        self.assertIn(
            "009-99", result.stderr,
            f"stderr should name the slice; got: {result.stderr!r}",
        )

    # AC #5 (no matching label → no-op, no warn)
    def test_auto_tick_noop_when_label_absent(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [ ] Some unrelated item.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # The unrelated item stays unticked
        self.assertIn("- [ ] Some unrelated item.", text)
        # No stderr noise about absent labels
        self.assertNotIn("Implementation review passed", result.stderr or "")

    # AC #7: existing tests still pass — covered implicitly by running the
    # whole test_workflow.py module.


class DeferredLifecycleTests(unittest.TestCase):
    """Slice 014-02: `DEFERRED` is a recognized state with bounded
    outbound transitions and a separate status-board section."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-defer-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec(self, rel_dir: str, label: str, status: str,
                    trigger: str = "") -> Path:
        """Append a slice to the spec under rel_dir, creating the spec
        file with a preamble on first call."""
        spec_dir = self.target / "docs/specs" / rel_dir
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        slice_block = (
            f"\n## Slice {label}\n\n**STATUS: {status}**\n\n**Goal:** x.\n"
        )
        if trigger:
            slice_block += f"\n**Resolution trigger:** {trigger}\n"
        if spec_md.is_file():
            spec_md.write_text(spec_md.read_text() + slice_block)
        else:
            spec_md.write_text("# Spec\n" + slice_block)
        return spec_md

    def test_transition_any_to_deferred(self):
        """From any active state, → DEFERRED succeeds."""
        spec_md = self._write_spec("500-alpha", "500-01 alpha", "DRAFT")
        result = run_workflow("transition", str(spec_md), "500-01", "DEFERRED")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DEFERRED**", spec_md.read_text())

    def test_transition_deferred_to_draft(self):
        """DEFERRED → DRAFT (re-open) is allowed."""
        spec_md = self._write_spec("501-alpha", "501-01 alpha", "DEFERRED")
        result = run_workflow("transition", str(spec_md), "501-01", "DRAFT")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DRAFT**", spec_md.read_text())

    def test_transition_deferred_to_done_refused(self):
        """DEFERRED → DONE (or any non-DRAFT) must be refused."""
        spec_md = self._write_spec("502-alpha", "502-01 alpha", "DEFERRED")
        result = run_workflow("transition", str(spec_md), "502-01", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEFERRED", result.stderr)

    def test_status_board_renders_deferred_section(self):
        """Slices in DEFERRED appear under `## Deferred slices` with
        their `**Resolution trigger:**` line as the per-row context."""
        self._write_spec("600-alpha", "600-01 active", "IN_PROGRESS")
        self._write_spec("600-alpha", "600-02 parked", "DEFERRED",
                         trigger="When the third caller appears.")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        # Active table has 600-01 only (600-02 is in the Deferred section)
        active = board.split("## Deferred slices")[0]
        self.assertIn("600-01 active", active)
        # Deferred section is present with the trigger
        self.assertIn("## Deferred slices", board)
        self.assertIn("600-02 parked", board)
        self.assertIn("When the third caller appears.", board)

    def test_status_board_omits_deferred_section_when_empty(self):
        """No `## Deferred slices` heading when nothing is deferred."""
        self._write_spec("700-alpha", "700-01 active", "IN_PROGRESS")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0)
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertNotIn("## Deferred slices", board)

    def test_status_board_idempotent_with_deferred(self):
        """Re-running on a board that already has a Deferred section
        produces no diff."""
        self._write_spec("800-alpha", "800-01 a", "DEFERRED",
                         trigger="When X happens.")
        run_workflow("status-board", str(self.target))
        first = (self.target / "docs/specs/README.md").read_text()
        run_workflow("status-board", str(self.target))
        second = (self.target / "docs/specs/README.md").read_text()
        self.assertEqual(first, second)

    def test_status_board_does_not_glue_adjacent_rows_across_tables(self):
        """Regression: `parse_existing_notes`'s row regex used `\\s*` between
        the status and notes cells, which could consume `\\n` and continue
        matching `(.*?)\\|$` on the NEXT line. When the prior board had a
        `## Deferred slices` table (3-cell rows), this glued the next
        deferred row's content into the active row's Notes cell. Bug
        symptom: lines in the regenerated README contained two `|...|`
        rows mashed onto one physical line. Fix: tightened the inter-cell
        `\\s*` to `[^\\S\\n]*` so the match cannot cross newlines.

        This test seeds a board with one active + two deferred slices,
        regenerates twice (so the second regen reads the first's output),
        then asserts every `^| ... |$` line contains exactly 4 cells
        (active row) OR 3 cells (deferred row) — never glued.
        """
        self._write_spec("900-alpha", "900-01 active", "IN_PROGRESS")
        # Curate a note on the active row so we exercise preservation
        # without the glue bug stomping it.
        self._write_spec("900-alpha", "900-02 parked-a", "DEFERRED",
                         trigger="When trigger A fires.")
        self._write_spec("900-alpha", "900-03 parked-b", "DEFERRED",
                         trigger="When trigger B fires.")
        board_path = self.target / "docs/specs/README.md"

        first = run_workflow("status-board", str(self.target))
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")

        # Hand-curate a note on the active row so we can confirm it survives
        # regen unaltered (and isn't replaced by glued-row content).
        board_text = board_path.read_text()
        marker = "| 900-01 active | IN_PROGRESS |  |"
        replacement = "| 900-01 active | IN_PROGRESS | curated note here |"
        self.assertIn(marker, board_text, "active row not found before curation")
        board_path.write_text(board_text.replace(marker, replacement))

        second = run_workflow("status-board", str(self.target))
        self.assertEqual(second.returncode, 0, f"stderr: {second.stderr}")
        final = board_path.read_text()

        # Every `|`-prefixed line must have <=5 pipes (4 cells max) or
        # exactly 4 pipes (3 cells, deferred table). Anything more means
        # two rows got glued.
        for line in final.splitlines():
            if not line.startswith("|") or set(line.strip()) == {"|", "-"}:
                continue  # skip separator rows
            pipe_count = line.count("|")
            self.assertIn(
                pipe_count, (4, 5),
                f"row has {pipe_count} pipes (expected 4 or 5) — glue bug "
                f"resurfaced:\n  {line!r}",
            )

        # Spot-check: curated note survived regen unchanged.
        self.assertIn(
            "| 900-01 active | IN_PROGRESS | curated note here |", final,
            "curated note on active row was not preserved across regen",
        )

        # Spot-check: deferred-table rows are NOT pulled into the active
        # row's Notes cell. The active row's Notes must not contain a
        # markdown link to another spec (which would be cross-row glue).
        active_section = final.split("## Deferred slices")[0]
        active_900_lines = [
            ln for ln in active_section.splitlines()
            if "900-01 active" in ln
        ]
        self.assertEqual(len(active_900_lines), 1)
        self.assertNotIn(
            "900-02", active_900_lines[0],
            "active row's Notes cell contains content from a deferred row "
            "(cross-row glue bug)",
        )
        self.assertNotIn(
            "900-03", active_900_lines[0],
            "active row's Notes cell contains content from a deferred row "
            "(cross-row glue bug)",
        )


class AbandonedLifecycleTests(unittest.TestCase):
    """Slice 085-01: `ABANDONED` is a recognized state with bounded
    outbound transitions (mirrors DEFERRED), refused from DONE, a
    separate status-board section, and a live-dependents warning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-abandon-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec(self, rel_dir: str, label: str, status: str,
                    reason: str = "", dependencies: str = None) -> Path:
        """Append a slice to the spec under rel_dir, creating the spec
        file with a preamble on first call. When `dependencies` is given,
        writes a file-per-slice fixture (frontmatter carries
        `dependencies:`, required for the AC8 dependents scan); otherwise
        an embedded prose-marker `## Slice` section in spec.md."""
        spec_dir = self.target / "docs/specs" / rel_dir
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        if not spec_md.is_file():
            spec_md.write_text("# Spec\n")
        if dependencies is not None:
            fragment = label.split()[0]
            slice_file = spec_dir / f"slice-{fragment}.md"
            body = (
                f"---\nstatus: {status}\ndependencies: {dependencies}\n"
                f"last_verified:\n---\n\n## Slice {label}\n\n**Goal:** x.\n"
            )
            if reason:
                body += f"\n**Abandonment reason:** {reason}\n"
            slice_file.write_text(body)
            return spec_md
        slice_block = (
            f"\n## Slice {label}\n\n**STATUS: {status}**\n\n**Goal:** x.\n"
        )
        if reason:
            slice_block += f"\n**Abandonment reason:** {reason}\n"
        spec_md.write_text(spec_md.read_text() + slice_block)
        return spec_md

    # AC1: reachable from every pre-DONE state.
    def test_transition_from_each_pre_done_state_to_abandoned(self):
        for i, status in enumerate((
                "DRAFT", "READY_FOR_REVIEW", "READY_FOR_IMPLEMENTATION",
                "IN_PROGRESS", "REVIEWED", "RECONCILED", "DEFERRED")):
            spec_md = self._write_spec(
                f"51{i}-alpha", f"51{i}-01 alpha", status)
            result = run_workflow(
                "transition", str(spec_md), f"51{i}-01", "ABANDONED")
            self.assertEqual(
                result.returncode, 0,
                f"from {status}: stderr: {result.stderr}")
            self.assertIn("**STATUS: ABANDONED**", spec_md.read_text())

    # AC1: DONE -> ABANDONED refused, names the reason.
    def test_transition_done_to_abandoned_refused(self):
        spec_md = self._write_spec("520-alpha", "520-01 alpha", "DONE")
        result = run_workflow(
            "transition", str(spec_md), "520-01", "ABANDONED")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DONE", result.stderr)
        self.assertIn("ABANDONED", result.stderr)
        self.assertIn("out of scope", result.stderr.lower())

    # AC1: ABANDONED -> ABANDONED idempotent.
    def test_transition_abandoned_to_abandoned_idempotent(self):
        spec_md = self._write_spec("521-alpha", "521-01 alpha", "ABANDONED")
        result = run_workflow(
            "transition", str(spec_md), "521-01", "ABANDONED")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    # AC2: ABANDONED -> DRAFT (re-open) succeeds.
    def test_transition_abandoned_to_draft(self):
        spec_md = self._write_spec("522-alpha", "522-01 alpha", "ABANDONED")
        result = run_workflow(
            "transition", str(spec_md), "522-01", "DRAFT")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DRAFT**", spec_md.read_text())

    # AC2: every other outbound transition from ABANDONED refused.
    def test_transition_abandoned_to_other_refused(self):
        spec_md = self._write_spec("523-alpha", "523-01 alpha", "ABANDONED")
        result = run_workflow(
            "transition", str(spec_md), "523-01", "IN_PROGRESS")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ABANDONED", result.stderr)
        self.assertIn("DRAFT", result.stderr)

    # AC3: status board renders Abandoned section with reason.
    def test_status_board_renders_abandoned_section(self):
        self._write_spec("610-alpha", "610-01 active", "IN_PROGRESS")
        self._write_spec("610-alpha", "610-02 dropped", "ABANDONED",
                         reason="Approach superseded by ADR-0099.")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        active = board.split("## Abandoned slices")[0]
        self.assertIn("610-01 active", active)
        self.assertIn("## Abandoned slices", board)
        self.assertIn("610-02 dropped", board)
        self.assertIn("Approach superseded by ADR-0099.", board)

    # AC3: section omitted entirely when no slice is ABANDONED.
    def test_status_board_omits_abandoned_section_when_empty(self):
        self._write_spec("710-alpha", "710-01 active", "IN_PROGRESS")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0)
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertNotIn("## Abandoned slices", board)

    # AC3: renders even without a reason (empty cell, not a crash).
    def test_status_board_renders_abandoned_without_reason(self):
        self._write_spec("720-alpha", "720-01 dropped", "ABANDONED")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("## Abandoned slices", board)
        self.assertIn("720-01 dropped", board)

    # AC3 + AC (both sections present): Deferred comes before Abandoned.
    def test_status_board_deferred_before_abandoned(self):
        self._write_spec("730-alpha", "730-01 parked", "DEFERRED",
                         reason="")
        spec_md = self.target / "docs/specs/730-alpha/spec.md"
        # Append a Resolution trigger for the deferred slice manually.
        spec_md.write_text(
            spec_md.read_text() + "\n**Resolution trigger:** X happens.\n")
        self._write_spec("730-alpha", "730-02 dropped", "ABANDONED",
                         reason="No longer needed.")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        deferred_idx = board.index("## Deferred slices")
        abandoned_idx = board.index("## Abandoned slices")
        self.assertLess(deferred_idx, abandoned_idx)

    # AC5: session_plan skips ABANDONED slices.
    def test_session_plan_skips_abandoned(self):
        spec_dir = self.target / "docs/specs/740-alpha"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )
        (spec_dir / "slice-01-live.md").write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 740-01 live\n\n**Goal:** x.\n"
        )
        (spec_dir / "slice-02-dropped.md").write_text(
            "---\nstatus: ABANDONED\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 740-02 dropped\n\n**Goal:** x.\n"
        )
        result = run_workflow("session-plan", str(spec_md))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("740-01 live", result.stdout)
        self.assertNotIn("740-02 dropped", result.stdout)

    # AC6: auto-tick ticks nothing for -> ABANDONED / ABANDONED -> DRAFT.
    def test_auto_tick_ticks_nothing_for_abandoned_transitions(self):
        spec_dir = self.target / "docs/specs/750-alpha"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "---\nstatus: DRAFT\n---\n\n"
            "## Slice 750-01 alpha\n\n**STATUS: IN_PROGRESS**\n\n"
            "**Goal:** x.\n\n**Definition of Done:**\n\n"
            "- [ ] Implementation review passed.\n"
            "- [ ] Reconciliation review passed.\n"
        )
        result = run_workflow(
            "transition", str(spec_md), "750-01", "ABANDONED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = spec_md.read_text()
        self.assertIn("- [ ] Implementation review passed.", text)
        self.assertIn("- [ ] Reconciliation review passed.", text)

        result2 = run_workflow(
            "transition", str(spec_md), "750-01", "DRAFT")
        self.assertEqual(result2.returncode, 0, msg=result2.stderr)
        text2 = spec_md.read_text()
        self.assertIn("- [ ] Implementation review passed.", text2)
        self.assertIn("- [ ] Reconciliation review passed.", text2)

    # AC8: warns about a live dependent, once, non-blocking.
    def test_transition_to_abandoned_warns_about_live_dependent(self):
        # Dependency target: 800-01 in one spec.
        target_md = self._write_spec("800-target", "800-01 alpha", "DRAFT",
                                     dependencies="[]")
        # Dependent: a different spec/slice that depends on 800-01 and is
        # itself not DONE/ABANDONED (still "live").
        self._write_spec("801-dependent", "801-01 beta", "DRAFT",
                         dependencies="[800-01]")
        result = run_workflow(
            "transition", str(target_md), "800-01", "ABANDONED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("801-01", result.stderr)

    # AC8: no dependents -> no warning printed.
    def test_transition_to_abandoned_no_dependents_no_warning(self):
        target_md = self._write_spec("810-target", "810-01 alpha", "DRAFT",
                                     dependencies="[]")
        result = run_workflow(
            "transition", str(target_md), "810-01", "ABANDONED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stderr.strip(), "")

    # AC8: a dependent that is already DONE or ABANDONED is not "live" —
    # no warning.
    def test_transition_to_abandoned_done_dependent_not_warned(self):
        target_md = self._write_spec("820-target", "820-01 alpha", "DRAFT",
                                     dependencies="[]")
        self._write_spec("821-dependent", "821-01 beta", "DONE",
                         dependencies="[820-01]")
        result = run_workflow(
            "transition", str(target_md), "820-01", "ABANDONED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stderr.strip(), "")

    # AC7 (rollup, mixed DONE+ABANDONED -> DONE)
    def test_rollup_mixed_done_abandoned_returns_done(self):
        spec_dir = self.target / "docs/specs/830-alpha"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text("---\nstatus: DRAFT\n---\n\n# Spec X\n")
        (spec_dir / "slice-01-a.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 830-01 alpha\n\n**Goal:** x.\n"
        )
        (spec_dir / "slice-02-b.md").write_text(
            "---\nstatus: ABANDONED\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 830-02 beta\n\n**Goal:** x.\n"
        )
        self.assertEqual(_workflow.compute_spec_status(spec_md), "DONE")

    # AC7 (rollup, unanimous ABANDONED -> ABANDONED)
    def test_rollup_all_abandoned_returns_abandoned(self):
        spec_dir = self.target / "docs/specs/831-alpha"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text("---\nstatus: DRAFT\n---\n\n# Spec X\n")
        (spec_dir / "slice-01-a.md").write_text(
            "---\nstatus: ABANDONED\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 831-01 alpha\n\n**Goal:** x.\n"
        )
        (spec_dir / "slice-02-b.md").write_text(
            "---\nstatus: ABANDONED\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 831-02 beta\n\n**Goal:** x.\n"
        )
        self.assertEqual(
            _workflow.compute_spec_status(spec_md), "ABANDONED")

    # AC7 (rollup, mixed DEFERRED+ABANDONED only -> DRAFT)
    def test_rollup_mixed_deferred_abandoned_returns_draft(self):
        spec_dir = self.target / "docs/specs/832-alpha"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text("---\nstatus: DRAFT\n---\n\n# Spec X\n")
        (spec_dir / "slice-01-a.md").write_text(
            "---\nstatus: DEFERRED\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 832-01 alpha\n\n**Goal:** x.\n"
        )
        (spec_dir / "slice-02-b.md").write_text(
            "---\nstatus: ABANDONED\ndependencies: []\nlast_verified:\n"
            "---\n\n## Slice 832-02 beta\n\n**Goal:** x.\n"
        )
        self.assertEqual(
            _workflow.compute_spec_status(spec_md), "DRAFT")


class StaleCheckTests(unittest.TestCase):
    """Slice 014-03: `workflow.py stale` lists items whose last_verified
    is more than N days old AND whose dep file was modified since."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-stale-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _touch(self, path: Path, iso_date: str) -> None:
        """Set both mtime and atime to the given YYYY-MM-DD (00:00 UTC)."""
        import time
        dt = __import__("datetime").datetime.fromisoformat(iso_date)
        ts = time.mktime(dt.timetuple())
        os.utime(path, (ts, ts))

    def _write_dep_slice(self, dep_spec: str, dep_label: str,
                         touch_date: str) -> Path:
        """Create a 'dependency' spec file and touch it to the given date."""
        dep_dir = self.target / "docs/specs" / dep_spec
        dep_dir.mkdir(parents=True, exist_ok=True)
        dep_md = dep_dir / "spec.md"
        dep_md.write_text(
            f"# Dep\n\n## Slice {dep_label}\n\n**STATUS: DONE**\n\nBody.\n"
        )
        self._touch(dep_md, touch_date)
        return dep_md

    def _write_consumer_slice(self, spec_dir: str, label: str,
                              last_verified: str, deps: list) -> Path:
        """Write the consumer slice with frontmatter."""
        cons_dir = self.target / "docs/specs" / spec_dir
        cons_dir.mkdir(parents=True, exist_ok=True)
        cons_md = cons_dir / "spec.md"
        cons_md.write_text(
            f"# Spec\n\n## Slice {label}\n\n"
            f"---\nstatus: RECONCILED\n"
            f"dependencies: [{', '.join(deps)}]\n"
            f"last_verified: {last_verified}\n---\n\nBody.\n"
        )
        return cons_md

    def test_no_stale_items_when_recent(self):
        """Recently verified slice with old deps → not stale."""
        self._write_dep_slice("900-dep", "900-01 old-dep", "2020-01-01")
        today = __import__("datetime").date.today().isoformat()
        self._write_consumer_slice("901-cons", "901-01 c", today, ["900-01"])
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "30")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_stale_item_listed_when_dep_changed_since(self):
        """Old verify date + dep changed since → stale."""
        # Dep touched yesterday (recent change)
        import datetime as _dt
        yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        self._write_dep_slice("910-dep", "910-01 fresh-dep", yesterday)
        # Consumer verified 200 days ago
        old = (_dt.date.today() - _dt.timedelta(days=200)).isoformat()
        self._write_consumer_slice("911-cons", "911-01 c", old, ["910-01"])
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("stale items", result.stdout)
        self.assertIn("911-01", result.stdout)
        self.assertIn(old, result.stdout)

    def test_old_verify_without_dep_change_not_stale(self):
        """Conjunctive criterion: old verify alone is not enough."""
        import datetime as _dt
        ancient = "2018-01-01"
        # Dep also old — no change since verify
        self._write_dep_slice("920-dep", "920-01 ancient", ancient)
        old = (_dt.date.today() - _dt.timedelta(days=300)).isoformat()
        self._write_consumer_slice("921-cons", "921-01 c", old, ["920-01"])
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_legacy_slice_without_frontmatter_skipped(self):
        """Slices with no frontmatter (no last_verified) are skipped."""
        # Write a legacy slice in the same project
        legacy_dir = self.target / "docs/specs/930-legacy"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "spec.md").write_text(
            "# Spec\n\n## Slice 930-01 legacy\n\n**STATUS: DONE**\n\nBody.\n"
        )
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_missing_dependencies_skipped(self):
        """Slice with last_verified but empty dependencies → skipped."""
        old = "2020-01-01"
        cons_dir = self.target / "docs/specs/940-empty"
        cons_dir.mkdir(parents=True)
        (cons_dir / "spec.md").write_text(
            f"# Spec\n\n## Slice 940-01 c\n\n"
            f"---\nstatus: DONE\ndependencies: []\nlast_verified: {old}\n---\n\n"
            f"Body.\n"
        )
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_days_flag_overrides_default(self):
        """`--days 1` makes a 5-day-old verify stale; default 90 wouldn't."""
        import datetime as _dt
        yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        self._write_dep_slice("950-dep", "950-01 fresh", yesterday)
        five_days_ago = (_dt.date.today() - _dt.timedelta(days=5)).isoformat()
        self._write_consumer_slice("951-cons", "951-01 c", five_days_ago,
                                   ["950-01"])
        # Default 90 → not stale yet
        r1 = run_workflow("stale", "--project-dir", str(self.target))
        self.assertEqual(r1.returncode, 0)
        self.assertIn("no stale items", r1.stdout)
        # --days 1 → stale
        r2 = run_workflow("stale", "--project-dir", str(self.target),
                          "--days", "1")
        self.assertEqual(r2.returncode, 0)
        self.assertIn("951-01", r2.stdout)


def _git_on_path() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


@unittest.skipUnless(_git_on_path(), "git not available")
class StaleTeamSignalTests(unittest.TestCase):
    """Slice 050-02: `workflow.py stale` surfaces a `category: team-context`
    finding when the team signal fires but `docs/memory/people.md` is absent
    (and the `.jig/no-people-md` opt-out marker is absent). Read-only; exit
    code is unchanged (stale stays exit-0 — see the AC4 resolution in the
    deviation log)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-teamstale-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- git fixture helpers (mirror test_scaffold.py / test_memory.py) ---
    def _git(self, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["git", "-C", str(self.target), *args],
            capture_output=True, text=True, env=env, check=True,
        )

    def _commit_as(self, name, email, filename):
        (self.target / filename).write_text("seed")
        self._git("add", filename)
        self._git("commit", "-m", f"add {filename}", env_extra={
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        })

    def _make_team_repo(self):
        """>= 2 distinct authors → team signal fires."""
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")

    def _make_solo_repo(self):
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")

    def _people(self) -> Path:
        return self.target / "docs" / "memory" / "people.md"

    def _marker(self) -> Path:
        return self.target / ".jig" / "no-people-md"

    # AC1 — finding present: signal fires + no people.md + no marker → a row
    # naming the contributor count N and the bootstrap hint.
    def test_finding_present_when_signal_fires_and_people_absent(self):
        self._make_team_repo()
        self.assertFalse(self._people().exists())
        result = run_workflow("stale", "--project-dir", str(self.target))
        self.assertIn("team-signal:", result.stdout)
        self.assertIn("2 contributors", result.stdout)
        self.assertIn("people.md is absent", result.stdout)
        self.assertIn("/jig:memory-sync", result.stdout)

    # AC5 — the finding carries a `category: team-context` tag distinct from
    # last_verified rows. Asserted at the structured `find_stale_items` level.
    def test_finding_carries_team_context_category(self):
        self._make_team_repo()
        items = _workflow.find_stale_items(self.target)
        team_rows = [it for it in items if it[2] == "team-context"]
        self.assertEqual(len(team_rows), 1,
                         "exactly one team-context finding expected")
        display, reason, category = team_rows[0]
        self.assertEqual(category, "team-context")
        self.assertIn("team-signal", display)
        self.assertIn("2 contributors", reason)
        # The bootstrap hint must be carried at the structured (reason)
        # level too, not only in the human-rendered stdout — downstream
        # filters reading `find_stale_items` should see the actionable
        # remedy without re-parsing the printed output.
        self.assertIn("/jig:memory-sync", reason)

    # AC3 — opt-out marker present → no finding.
    def test_no_finding_when_marker_present(self):
        self._make_team_repo()
        self._marker().parent.mkdir(parents=True, exist_ok=True)
        self._marker().write_text("# opt out\n")
        items = _workflow.find_stale_items(self.target)
        self.assertEqual([it for it in items if it[2] == "team-context"], [])
        result = run_workflow("stale", "--project-dir", str(self.target))
        self.assertNotIn("team-signal:", result.stdout)

    # people.md exists → no finding.
    def test_no_finding_when_people_md_exists(self):
        self._make_team_repo()
        self._people().parent.mkdir(parents=True, exist_ok=True)
        self._people().write_text("# People\n")
        items = _workflow.find_stale_items(self.target)
        self.assertEqual([it for it in items if it[2] == "team-context"], [])

    # Solo repo → signal does not fire → no finding.
    def test_no_finding_on_solo_repo(self):
        self._make_solo_repo()
        items = _workflow.find_stale_items(self.target)
        self.assertEqual([it for it in items if it[2] == "team-context"], [])

    # Monorepo-parent → guarded to solo → no finding.
    def test_no_finding_on_monorepo_parent(self):
        # self.target is a SUBDIR of a multi-author parent repo.
        parent = Path(self.tmpdir)
        env = os.environ.copy()
        subprocess.run(["git", "-C", str(parent), "init", "-q"],
                       capture_output=True, env=env, check=True)
        for name, email, fn in [("Alice", "alice@x.com", "pa.txt"),
                                 ("Bob", "bob@x.com", "pb.txt")]:
            (parent / fn).write_text("x")
            subprocess.run(["git", "-C", str(parent), "add", fn],
                           capture_output=True, env=env, check=True)
            subprocess.run(["git", "-C", str(parent), "commit", "-q", "-m", fn],
                           capture_output=True, check=True, env={
                               **env,
                               "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
                               "GIT_COMMITTER_NAME": name,
                               "GIT_COMMITTER_EMAIL": email,
                           })
        items = _workflow.find_stale_items(self.target)
        self.assertEqual([it for it in items if it[2] == "team-context"], [])

    # AC4 (resolved intent) — stale stays exit-0 even when the team-signal
    # finding is the only finding present. The finding is surfaced like every
    # other stale row; it does not flip the exit code (see the deviation log).
    def test_stale_exits_zero_with_team_finding(self):
        self._make_team_repo()
        result = run_workflow("stale", "--project-dir", str(self.target))
        self.assertIn("team-signal:", result.stdout)
        self.assertEqual(result.returncode, 0,
                         "stale must stay exit-0 even with a team-signal finding")

    # AC2 (read-only) — the check writes/mutates nothing: no people.md, no
    # marker, no docs/memory dir created by the audit itself.
    def test_finding_is_read_only(self):
        self._make_team_repo()
        run_workflow("stale", "--project-dir", str(self.target))
        self.assertFalse(self._people().exists(),
                         "stale must not create people.md")
        self.assertFalse(self._marker().exists(),
                         "stale must not write the opt-out marker")

    # AC6 (no double-walk) — a single `find_stale_items` invocation computes
    # the contributor count at most once (no per-finding git re-shell).
    def test_no_double_walk_counts_once(self):
        self._make_team_repo()
        # Also seed a last_verified drift row so there are MULTIPLE findings;
        # the team count must still be computed exactly once for the run.
        import datetime as _dt
        import unittest.mock as _mock
        yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        dep_dir = self.target / "docs/specs/960-dep"
        dep_dir.mkdir(parents=True, exist_ok=True)
        dep_md = dep_dir / "spec.md"
        dep_md.write_text("# Dep\n\n## Slice 960-01 d\n\n**STATUS: DONE**\n\nB.\n")
        import time as _time
        _ts = _time.mktime(_dt.datetime.fromisoformat(yesterday).timetuple())
        os.utime(dep_md, (_ts, _ts))
        old = (_dt.date.today() - _dt.timedelta(days=200)).isoformat()
        cons_dir = self.target / "docs/specs/961-cons"
        cons_dir.mkdir(parents=True, exist_ok=True)
        (cons_dir / "spec.md").write_text(
            f"# Spec\n\n## Slice 961-01 c\n\n---\nstatus: RECONCILED\n"
            f"dependencies: [960-01]\nlast_verified: {old}\n---\n\nBody.\n"
        )
        with _mock.patch.object(
            _workflow.team_signal, "count_team_contributors",
            wraps=_workflow.team_signal.count_team_contributors,
        ) as spy:
            items = _workflow.find_stale_items(self.target)
        # Both finding kinds present.
        self.assertTrue(any(it[2] == "team-context" for it in items))
        self.assertTrue(any(it[2] == "last-verified" for it in items))
        self.assertLessEqual(
            spy.call_count, 1,
            "count_team_contributors must be invoked at most once per stale run",
        )


class RoutingStatsTests(unittest.TestCase):
    """Slice 041-02: `workflow.py routing-stats` renders a category-split
    histogram (jig baseline vs. richer/other) from the shared
    `.claude/skill-usage.jsonl` trace written by jig-skill-trace.sh."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-routing-")
        self.project = Path(self.tmpdir) / "proj"
        (self.project / ".claude").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _iso_days_ago(self, days: int) -> str:
        import datetime as _dt
        return (_dt.datetime.now(_dt.timezone.utc)
                - _dt.timedelta(days=days)).isoformat()

    def _write_log(self, entries: list) -> None:
        """entries: list of dicts → JSONL. A dict carrying key '__raw__'
        injects a verbatim line (for malformed-input tests)."""
        import json as _json
        log = self.project / ".claude" / "skill-usage.jsonl"
        lines = []
        for e in entries:
            lines.append(e["__raw__"] if "__raw__" in e else _json.dumps(e))
        log.write_text("\n".join(lines) + "\n")

    def _skill(self, name, *, days_ago=0):
        return {
            "timestamp": self._iso_days_ago(days_ago),
            "session_id": "s",
            "event": "skill_invoked",
            "tool_name": "Skill",
            "skill_name": name,
        }

    def _task(self, *, days_ago=0):
        # A jig-telemetry.sh Task-spawn row — no event / skill_name.
        return {
            "timestamp": self._iso_days_ago(days_ago),
            "session_id": "s",
            "tool_name": "Task",
            "prompt_snippet": "spawn something",
        }

    def _run(self, *extra):
        return run_workflow("routing-stats", "--project-dir",
                            str(self.project), *extra)

    def _row(self, stdout: str, category: str) -> str:
        return next(ln for ln in stdout.splitlines()
                    if ln.strip().startswith(category + " ")
                    or ln.strip() == category)

    def test_missing_log_friendly_message(self):
        # No skill-usage.jsonl written at all → friendly, no crash.
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("no routing data", r.stdout)

    def test_empty_log_friendly_message(self):
        (self.project / ".claude" / "skill-usage.jsonl").write_text("")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("no skill invocations", r.stdout)

    def test_counts_jig_vs_other_per_category(self):
        entries = [self._skill("jig:pr-review") for _ in range(3)]
        entries += [self._skill("pr-review") for _ in range(7)]
        self._write_log(entries)
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # category pr-review: jig=3, other=7, total=10
        self.assertRegex(self._row(r.stdout, "pr-review"),
                         r"\bpr-review\b.*\b3\b.*\b7\b.*\b10\b")

    def test_excludes_task_spawn_rows(self):
        # Load-bearing shared-file invariant: Task-spawn rows (no 'event'/
        # 'skill_name') must NOT count as skill invocations.
        self._write_log([self._task(), self._task(),
                         self._skill("jig:analyze")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # exactly 1 invocation; the two Task rows excluded
        self.assertRegex(self._row(r.stdout, "analyze"),
                         r"\banalyze\b.*\b1\b.*\b0\b.*\b1\b")

    def test_days_window_excludes_old_entries(self):
        self._write_log([
            self._skill("jig:contracts", days_ago=60),
            self._skill("jig:contracts", days_ago=0),
        ])
        r = self._run("--days", "30")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # only the in-window invocation counted
        self.assertRegex(self._row(r.stdout, "contracts"),
                         r"\bcontracts\b.*\b1\b.*\b0\b.*\b1\b")
        self.assertIn("1 outside window", r.stdout)

    def test_malformed_line_skipped(self):
        self._write_log([
            {"__raw__": "{ not valid json"},
            self._skill("jig:tdd-loop"),
            {"__raw__": "12345"},  # valid JSON but not a dict
        ])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "tdd-loop"),
                         r"\btdd-loop\b.*\b1\b.*\b0\b.*\b1\b")

    def test_non_utf8_bytes_do_not_crash(self):
        # A corrupted (non-UTF-8) trace must not break the "always exits 0"
        # contract: bad bytes decode to replacement chars and drop out via
        # the json.loads guard, while valid lines still count.
        import json as _json
        log = self.project / ".claude" / "skill-usage.jsonl"
        good = _json.dumps(self._skill("jig:analyze")).encode("utf-8")
        log.write_bytes(b"\xff\xfe not utf-8 at all\n" + good + b"\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "analyze"),
                         r"\banalyze\b.*\b1\b.*\b0\b.*\b1\b")

    def test_jig_only_category_zero_other(self):
        self._write_log([self._skill("jig:spec-workflow"),
                         self._skill("jig:spec-workflow")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "spec-workflow"),
                         r"\bspec-workflow\b.*\b2\b.*\b0\b.*\b2\b")

    def test_sorted_by_total_descending(self):
        entries = [self._skill("jig:spec-workflow") for _ in range(5)]
        entries += [self._skill("jig:clarify")]
        self._write_log(entries)
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertLess(r.stdout.index("spec-workflow"),
                        r.stdout.index("clarify"),
                        "higher-total category should sort first")

    def test_legend_explains_jig_vs_other(self):
        self._write_log([self._skill("pr-review")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("legend", r.stdout.lower())
        self.assertIn("jig", r.stdout)
        self.assertIn("other", r.stdout)


class GateStatsTests(unittest.TestCase):
    """Slice 078-02: `workflow.py gate-stats` renders a per-gate bypass
    histogram from the shared `.claude/skill-usage.jsonl` trace written by
    078-01's gate instrumentation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-gatestats-")
        self.project = Path(self.tmpdir) / "proj"
        (self.project / ".claude").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _iso_days_ago(self, days: int) -> str:
        import datetime as _dt
        return (_dt.datetime.now(_dt.timezone.utc)
                - _dt.timedelta(days=days)).isoformat()

    def _write_log(self, entries: list) -> None:
        import json as _json
        log = self.project / ".claude" / "skill-usage.jsonl"
        lines = []
        for e in entries:
            lines.append(e["__raw__"] if "__raw__" in e else _json.dumps(e))
        log.write_text("\n".join(lines) + "\n")

    def _bypass(self, gate, *, days_ago=0):
        return {
            "timestamp": self._iso_days_ago(days_ago),
            "event": "gate_bypassed",
            "gate": gate,
            "env_var": f"JIG_{gate.upper().replace('-', '_')}_GATE",
        }

    def _skill(self, name, *, days_ago=0):
        # A skill_invoked row (spec 041) — must NOT count as a gate bypass.
        return {
            "timestamp": self._iso_days_ago(days_ago),
            "event": "skill_invoked",
            "skill_name": name,
        }

    def _run(self, *extra):
        return run_workflow("gate-stats", "--project-dir",
                            str(self.project), *extra)

    def _row(self, stdout: str, gate: str) -> str:
        return next(ln for ln in stdout.splitlines()
                    if ln.strip().startswith(gate + " "))

    def test_missing_log_friendly_message(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("no gate-bypass data", r.stdout)

    def test_empty_log_friendly_message(self):
        (self.project / ".claude" / "skill-usage.jsonl").write_text("")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("no gate bypasses", r.stdout)

    def test_counts_per_gate(self):
        entries = [self._bypass("review-evidence") for _ in range(3)]
        entries += [self._bypass("conventions") for _ in range(2)]
        self._write_log(entries)
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "review-evidence"),
                         r"\breview-evidence\b.*\b3\b")
        self.assertRegex(self._row(r.stdout, "conventions"),
                         r"\bconventions\b.*\b2\b")

    def test_excludes_skill_invoked_rows(self):
        # Load-bearing shared-file invariant: skill_invoked / task_spawned
        # rows must NOT count as gate bypasses.
        self._write_log([self._skill("jig:analyze"),
                         self._bypass("conventions")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "conventions"),
                         r"\bconventions\b.*\b1\b")
        self.assertNotIn("analyze", r.stdout)

    def test_days_window_excludes_old_entries(self):
        self._write_log([
            self._bypass("conventions", days_ago=60),
            self._bypass("conventions", days_ago=0),
        ])
        r = self._run("--days", "30")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "conventions"),
                         r"\bconventions\b.*\b1\b")
        self.assertIn("1 outside window", r.stdout)

    def test_malformed_line_skipped(self):
        self._write_log([
            {"__raw__": "{ not valid json"},
            self._bypass("review-evidence"),
            {"__raw__": "12345"},
        ])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "review-evidence"),
                         r"\breview-evidence\b.*\b1\b")

    def test_sorted_by_count_descending(self):
        entries = [self._bypass("review-evidence") for _ in range(5)]
        entries += [self._bypass("conventions")]
        self._write_log(entries)
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertLess(r.stdout.index("review-evidence"),
                        r.stdout.index("conventions"),
                        "higher-count gate should sort first")


class SliceTemplateTests(unittest.TestCase):
    """Slice 014-01: a new slice template exists with the right frontmatter."""

    def test_slice_template_present(self):
        template = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"
        self.assertTrue(template.is_file(),
                        "templates/docs/specs/slice-template.md must exist")
        text = template.read_text()
        self.assertIn("status: DRAFT", text)
        self.assertIn("dependencies: []", text)
        self.assertIn("last_verified:", text)
        # Close-out section per slice 009 convention
        self.assertIn("### Close-out (post-DONE)", text)
        # Spec 082-01: reconciliation sweep manifest is a required
        # close-out section next to the deviation log.
        self.assertIn("### Reconciliation sweep", text)
        self.assertIn("`updated`", text)
        self.assertIn("`no-op`", text)
        self.assertIn("`deferred`", text)

    def test_slice_template_is_file_per_slice_shape(self):
        """Slice 018-03: template's frontmatter must come BEFORE the
        `## Slice` heading (file-per-slice layout). Embedded layout
        had heading first, frontmatter after — but the template is now
        meant as a whole-file template, not a `## Slice` block to
        append to spec.md."""
        template = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"
        text = template.read_text().lstrip()
        # First non-blank line is the frontmatter delimiter, not a heading.
        first_line = text.splitlines()[0]
        self.assertEqual(first_line, "---",
                         f"expected '---' (frontmatter open) at top, "
                         f"got: {first_line!r}")
        # Heading appears AFTER the closing frontmatter delimiter.
        fm_end = text.index("\n---\n", 4)  # second `---` line
        self.assertIn("## Slice {{NUMBER}}", text[fm_end:],
                      "## Slice heading must follow the frontmatter block")


class FrontmatterTransitionTests(unittest.TestCase):
    """Slice 014-01: transitions handle slice-level frontmatter."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-fm-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_fm_slice(self, name: str, status: str, deps: list = None,
                        body: str = "") -> None:
        deps_line = (f"\ndependencies: [{', '.join(deps)}]"
                     if deps else "\ndependencies: []")
        self.spec.write_text(
            f"# Spec X\n\n## Slice {name}\n\n"
            f"---\nstatus: {status}{deps_line}\nlast_verified:\n---\n\n"
            f"{body}"
        )

    # AC #1: slice frontmatter is parsed and used as the source of truth.
    def test_status_board_reads_frontmatter_status(self):
        # Set up a full scaffold so the status-board has somewhere to write.
        target = Path(self.tmpdir) / "demo-project"
        target.mkdir()
        scaffold(target)
        spec_dir = target / "docs/specs/200-frontmatter-spec"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "# Spec\n\n## Slice 200-01 — alpha\n\n"
            "---\nstatus: IN_PROGRESS\ndependencies: []\n---\n\n"
            "Body.\n"
        )
        result = run_workflow("status-board", str(target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (target / "docs/specs/README.md").read_text()
        # The board should show IN_PROGRESS for slice 200-01, sourced
        # from frontmatter (no prose `**STATUS:**` marker present).
        self.assertRegex(board, r"200-01[^|]*\|[^|]*IN_PROGRESS")

    # AC #2: legacy prose marker fallback still works (existing tests
    # cover that exhaustively).

    # AC #3: transition writes to frontmatter when present.
    def test_transition_updates_frontmatter_status(self):
        self._write_fm_slice("300-01 alpha", "DRAFT")
        result = run_workflow("transition", str(self.spec), "300-01",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = self.spec.read_text()
        self.assertIn("status: IN_PROGRESS", text)
        # No spurious prose marker leak — none was present originally.
        self.assertNotIn("**STATUS:", text)

    # AC #3: `last_verified` is stamped on RECONCILED transitions.
    def test_reconciled_transition_stamps_last_verified(self):
        self._write_fm_slice("301-01 alpha", "REVIEWED")
        result = run_workflow("transition", str(self.spec), "301-01",
                              "RECONCILED")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = self.spec.read_text()
        self.assertIn("status: RECONCILED", text)
        # Today's date should appear in last_verified
        today = __import__("datetime").date.today().isoformat()
        self.assertIn(f"last_verified: {today}", text)

    # AC #3: non-RECONCILED transitions don't stamp.
    def test_non_reconciled_transition_does_not_stamp(self):
        self._write_fm_slice("302-01 alpha", "DRAFT")
        result = run_workflow("transition", str(self.spec), "302-01",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = self.spec.read_text()
        # last_verified field stays empty
        self.assertIn("last_verified:\n", text)

    # AC #4: DONE transition refuses on unsatisfied slice dependency.
    def test_done_refuses_when_dependency_not_done(self):
        target = Path(self.tmpdir) / "demo-project"
        target.mkdir()
        scaffold(target)
        # Spec A with a DRAFT slice; spec B with a slice depending on A.
        spec_a = target / "docs/specs/400-alpha"
        spec_a.mkdir(parents=True)
        (spec_a / "spec.md").write_text(
            "# Spec A\n\n## Slice 400-01 — first\n\n"
            "---\nstatus: DRAFT\ndependencies: []\n---\n\nBody.\n"
        )
        spec_b = target / "docs/specs/401-beta"
        spec_b.mkdir(parents=True)
        spec_b_path = spec_b / "spec.md"
        spec_b_path.write_text(
            "# Spec B\n\n## Slice 401-01 — second\n\n"
            "---\nstatus: REVIEWED\ndependencies: [400-01]\n---\n\nBody.\n"
        )
        result = run_workflow("transition", str(spec_b_path), "401-01",
                              "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("400-01", result.stderr)
        self.assertIn("DRAFT", result.stderr)

    # AC #4: DONE succeeds when dependency is DONE.
    def test_done_succeeds_when_dependency_done(self):
        target = Path(self.tmpdir) / "demo-project"
        target.mkdir()
        scaffold(target)
        spec_a = target / "docs/specs/410-alpha"
        spec_a.mkdir(parents=True)
        (spec_a / "spec.md").write_text(
            "# Spec A\n\n## Slice 410-01 — first\n\n"
            "---\nstatus: DONE\ndependencies: []\n---\n\nBody.\n"
        )
        spec_b = target / "docs/specs/411-beta"
        spec_b.mkdir(parents=True)
        spec_b_path = spec_b / "spec.md"
        spec_b_path.write_text(
            "# Spec B\n\n## Slice 411-01 — second\n\n"
            "---\nstatus: RECONCILED\ndependencies: [410-01]\n---\n\nBody.\n"
        )
        result = run_workflow("transition", str(spec_b_path), "411-01",
                              "DONE")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("status: DONE", spec_b_path.read_text())


# Load workflow.py as a module for direct-call tests (needed for mocking
# subprocess.run inside the helper). importlib bypasses the hyphen-in-
# directory-name limitation. Mirrors the pattern in skills/slice-land/
# test_land.py.
import importlib.util as _ilu


def _load_workflow():
    spec = _ilu.spec_from_file_location("_workflow_module", WORKFLOW)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_workflow = _load_workflow()


class _SubprocessRecorder:
    """Captures subprocess.run calls and returns canned results based on
    a sequence of (matcher, returncode, stdout, stderr) tuples.

    Each call to the recorder consumes the first matching tuple in the
    sequence (FIFO). Matcher is a callable that takes the argv list and
    returns True if this tuple should fire. Unmatched calls return
    (returncode=0, stdout="", stderr="") by default — useful for
    benign reads like `git status --porcelain`.
    """

    def __init__(self):
        self.calls = []            # list of argv-lists
        self._responses = []       # list of (matcher, rc, stdout, stderr)

    def stub(self, matcher, returncode=0, stdout="", stderr=""):
        self._responses.append((matcher, returncode, stdout, stderr))
        return self

    def __call__(self, *args, **kwargs):
        # First positional arg is the argv list (or string).
        argv = args[0] if args else kwargs.get("args")
        if isinstance(argv, str):
            argv_list = argv.split()
        else:
            argv_list = list(argv)
        self.calls.append(argv_list)
        for i, (matcher, rc, out, err) in enumerate(self._responses):
            if matcher(argv_list):
                # One-shot: pop after match.
                self._responses.pop(i)
                return _make_proc(rc, out, err)
        return _make_proc(0, "", "")

    def argv_log(self):
        """Returns a list of space-joined command strings for assertion."""
        return [" ".join(a) for a in self.calls]


def _make_proc(returncode: int, stdout: str = "", stderr: str = ""):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _matches(*prefix_tokens):
    """Build a matcher that returns True when argv starts with the given
    tokens (in order, contiguous from index 0). E.g. _matches("git",
    "push") fires for ["git", "push", "origin", "main"]."""
    def _m(argv):
        return tuple(argv[: len(prefix_tokens)]) == tuple(prefix_tokens)
    return _m


def _matches_full(*tokens):
    """Exact full-argv matcher."""
    def _m(argv):
        return tuple(argv) == tuple(tokens)
    return _m


class LookupAdrAcceptedTests(unittest.TestCase):
    """Slice 073-01 / ADR-0026: `_lookup_adr_accepted` resolves an ADR's
    status frontmatter-first, prose-fallback, with `Superseded` treated as
    NOT accepted in BOTH paths (fixes the prose-only bug where a superseded
    ADR — e.g. adr-0002 / adr-0008 — read as satisfied)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-adrstatus-")
        self.decisions = Path(self.tmpdir) / "docs" / "decisions"
        self.decisions.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_adr(self, num: str, slug: str, text: str) -> Path:
        path = self.decisions / f"adr-{num}-{slug}.md"
        path.write_text(text)
        return path

    # --- AC1: frontmatter status: Accepted → satisfied (no prose consult) ---
    def test_frontmatter_accepted_satisfied(self):
        self._write_adr(
            "0100", "fm-accepted",
            "---\nstatus: Accepted\n---\n\n# ADR-0100\n\n## Status\n\n"
            "Accepted (2026-06-15)\n\n## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0100")
        self.assertTrue(ok, f"expected satisfied; reason={reason}")

    def test_frontmatter_accepted_ignores_absent_prose_status(self):
        # Frontmatter wins: even with NO prose `## Status` section, an
        # `status: Accepted` frontmatter is satisfied (no prose consult).
        self._write_adr(
            "0101", "fm-accepted-no-prose",
            "---\nstatus: Accepted\n---\n\n# ADR-0101\n\n## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0101")
        self.assertTrue(ok, f"expected satisfied; reason={reason}")

    # --- AC2: frontmatter Superseded / Proposed → not satisfied ---
    def test_frontmatter_superseded_not_satisfied_names_superseder(self):
        self._write_adr(
            "0102", "fm-superseded",
            "---\nstatus: Superseded\n---\n\n# ADR-0102\n\n## Status\n\n"
            "Accepted (2026-01-01)\n\n"
            "Superseded by [ADR-0200](./adr-0200-newer.md) (2026-06-15)\n\n"
            "## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0102")
        self.assertFalse(ok)
        # Names the superseder pulled from the prose `Superseded by` line.
        self.assertIn("0200", reason)

    def test_frontmatter_superseded_no_prose_line_generic_reason(self):
        # Superseded in frontmatter but no prose `Superseded by` line → still
        # not satisfied, with a generic superseded reason.
        self._write_adr(
            "0103", "fm-superseded-bare",
            "---\nstatus: Superseded\n---\n\n# ADR-0103\n\n## Status\n\n"
            "Accepted (2026-01-01)\n\n## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0103")
        self.assertFalse(ok)
        self.assertIn("supersed", reason.lower())

    def test_frontmatter_proposed_not_satisfied_names_state(self):
        self._write_adr(
            "0104", "fm-proposed",
            "---\nstatus: Proposed\n---\n\n# ADR-0104\n\n## Status\n\n"
            "Proposed (2026-06-15)\n\n## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0104")
        self.assertFalse(ok)
        self.assertIn("Proposed", reason)

    # --- AC3: no frontmatter status → prose fallback, plain Accepted ---
    def test_no_frontmatter_status_prose_accepted_satisfied(self):
        # Legacy shape: frontmatter present but no `status:` field; prose
        # `Accepted (date)` only → satisfied via the unchanged prose scan.
        self._write_adr(
            "0105", "prose-accepted",
            "---\ndependencies: []\nlast_verified: 2026-06-15\n---\n\n"
            "# ADR-0105\n\n## Status\n\nAccepted (2026-06-15)\n\n"
            "## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0105")
        self.assertTrue(ok, f"expected satisfied; reason={reason}")

    def test_no_frontmatter_block_at_all_prose_accepted_satisfied(self):
        # Truly frontmatter-less ADR → prose fallback still applies.
        self._write_adr(
            "0106", "no-frontmatter",
            "# ADR-0106\n\n## Status\n\nAccepted (2026-06-15)\n\n"
            "## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0106")
        self.assertTrue(ok, f"expected satisfied; reason={reason}")

    def test_inline_status_line_only_names_both_encodings(self):
        # Reported gap: a bare inline `**Status:** Accepted` line (a common
        # pre-jig house style) is neither frontmatter `status:` nor a
        # `## Status` section → not satisfied. The reason must name BOTH
        # accepted encodings, not only the prose section, so the fix is
        # discoverable.
        self._write_adr(
            "0111", "inline-status-only",
            "# ADR-0111\n\n- **Status:** Accepted\n- **Date:** 2026-01-01\n\n"
            "## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0111")
        self.assertFalse(ok, "inline-status-only ADR must not be satisfied")
        self.assertIn("status:", reason)
        self.assertIn("## Status", reason)

    # --- AC4: prose fallback recognizes Superseded (the bug fix) ---
    def test_prose_fallback_superseded_with_accepted_line_not_satisfied(self):
        # Mirrors real adr-0002 / adr-0008: no frontmatter `status:`, prose
        # `## Status` has BOTH `Accepted (date)` AND `Superseded by …`. The
        # old reader matched `^Accepted` and wrongly passed; now → not
        # satisfied, reason names the superseder.
        self._write_adr(
            "0107", "prose-superseded",
            "---\ndependencies: []\nlast_verified: 2026-06-15\n---\n\n"
            "# ADR-0107\n\n## Status\n\nAccepted (2026-01-01)\n\n"
            "Superseded by [ADR-0210](./adr-0210-replacement.md) (2026-06-15)\n\n"
            "## Context\n\nbody.\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0107")
        self.assertFalse(ok, "superseded prose ADR must NOT be satisfied")
        self.assertIn("0210", reason)

    # --- AC5: diagnostic parity — reasons name the ADR file ---
    def test_reason_names_adr_file_frontmatter_superseded(self):
        path = self._write_adr(
            "0108", "fm-superseded-named",
            "---\nstatus: Superseded\n---\n\n# ADR-0108\n\n## Status\n\n"
            "Accepted (2026-01-01)\n\n"
            "Superseded by [ADR-0220](./adr-0220-x.md) (2026-06-15)\n\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0108")
        self.assertFalse(ok)
        self.assertIn(path.name, reason)

    def test_reason_names_adr_file_frontmatter_proposed(self):
        path = self._write_adr(
            "0109", "fm-proposed-named",
            "---\nstatus: Proposed\n---\n\n# ADR-0109\n\n## Status\n\n"
            "Proposed (2026-06-15)\n\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0109")
        self.assertFalse(ok)
        self.assertIn(path.name, reason)

    def test_reason_names_adr_file_prose_superseded(self):
        path = self._write_adr(
            "0110", "prose-superseded-named",
            "# ADR-0110\n\n## Status\n\nAccepted (2026-01-01)\n\n"
            "Superseded by [ADR-0230](./adr-0230-y.md) (2026-06-15)\n\n",
        )
        ok, reason = _workflow._lookup_adr_accepted(self.decisions, "0110")
        self.assertFalse(ok)
        self.assertIn(path.name, reason)


class ReserveSpecTests(unittest.TestCase):
    """Slice 003-03: `workflow.py new <slug>` reserves the next free
    spec number by committing — and by default pushing — a stub
    spec.md to origin/main."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-reserve-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Build minimal scaffolding: docs/specs/ exists; a couple of
        # existing spec dirs so the next-number computation has signal.
        (self.target / "docs" / "specs").mkdir(parents=True)
        # Spec 063-01: the scaffold-state precondition classifies on
        # `scaffold.json` (the completion sentinel). A scaffolded project
        # carries it, so `reserve_spec` proceeds to the legacy flow.
        (self.target / "scaffold.json").write_text("{}\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mkspec(self, name: str) -> None:
        d = self.target / "docs" / "specs" / name
        d.mkdir(parents=True)
        (d / "spec.md").write_text("# Spec\n")

    def _stub_preflight_ok(self, rec: _SubprocessRecorder,
                            dirty: bool = False) -> None:
        """Stub the preflight git calls: branch == main, clean worktree,
        origin URL on github.com. `dirty=True` simulates uncommitted
        changes."""
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0,
                 stdout=("M somefile\n" if dirty else ""))
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")

    # AC #1 + AC #2 + AC #7 (--no-push) — happy path; verify stub contents
    # and commit semantics without any remote calls.
    def test_new_reserves_next_number_and_writes_stub(self):
        self._mkspec("001-existing")
        self._mkspec("015-other")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # Local commit step.
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "parallel-worktree-collision",
                project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        spec_dir = self.target / "docs" / "specs" / "016-parallel-worktree-collision"
        self.assertTrue(spec_dir.is_dir(), f"missing: {spec_dir}")
        spec_md = spec_dir / "spec.md"
        self.assertTrue(spec_md.is_file())
        text = spec_md.read_text()
        # AC #2: frontmatter (spec 068-02 added the `use_cases:` trace field).
        self.assertIn("---\nstatus: DRAFT\nskill:\nuse_cases: []\n---", text)
        # AC #2: title-cased header
        self.assertIn("# Spec 016: Parallel-worktree collision", text)
        # AC #2: today's date in the reservation line
        import datetime as _dt
        today = _dt.date.today().isoformat()
        self.assertIn(f"Reserved on {today}", text)
        # AC #2: required headers (slice 018-03 renamed "SPIDR analysis"
        # → "Decomposition" + added "Slices" section pointing at the
        # starter slice file emitted alongside spec.md).
        self.assertIn("## Overview", text)
        self.assertIn("## Decomposition", text)
        self.assertIn("## Slices", text)
        self.assertIn("slice-01-tbd.md", text)
        # Spec 064-02: risk-gated grounding/assumptions section, placed
        # after ## Overview. The act of authoring surfaces the load-bearing
        # assumptions that slice 064-04 derives its frame_review trigger from.
        self.assertIn("## Assumptions", text)
        # Placement: Assumptions sits between Overview and Decomposition.
        self.assertLess(
            text.index("## Overview"),
            text.index("## Assumptions"),
            "## Assumptions must follow ## Overview",
        )
        self.assertLess(
            text.index("## Assumptions"),
            text.index("## Decomposition"),
            "## Assumptions must precede ## Decomposition",
        )
        # Spec 068-02 AC2: the spec stub carries an (empty) `use_cases:` trace
        # field in its frontmatter, the `dependencies:`-style flow-list shape
        # parse_frontmatter already parses. Empty by default (AC4: soft — an
        # empty trace field is non-erroring and trips the AC5 grow prompt).
        self.assertIn("use_cases: []", text,
                      "spec stub must seed an empty use_cases: trace field")
        # `_common` is importable because loading `_workflow` (spec_from_file
        # _location, above) ran workflow.py's `sys.path.insert(skills/)`.
        from _common.parsing import parse_frontmatter as _pf
        fm, _ = _pf(text)
        self.assertEqual(fm.get("use_cases"), [],
                         "use_cases: must round-trip through parse_frontmatter")
        # AC #1: commit message
        commit_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("docs(specs): reserve 016-parallel-worktree-collision",
                      " ".join(commit_calls[0]))
        # AC #7 (--no-push): no fetch / push calls.
        flat_log = " | ".join(rec.argv_log())
        self.assertNotIn("git push", flat_log)
        self.assertNotIn("git fetch", flat_log)

    # AC #1 — gap-tolerance: max + 1 across gaps, non-spec entries ignored.
    def test_new_uses_max_plus_one_across_gaps(self):
        self._mkspec("001-x")
        self._mkspec("015-y")
        self._mkspec("003-z")
        # Non-spec sibling entries don't perturb the max
        (self.target / "docs" / "specs" / "README.md").write_text("# stub\n")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # 015 was the max → reserve 016
        spec_dir = self.target / "docs" / "specs" / "016-newslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 016-newslot, got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")

    # AC #5 — refuse on non-main branch.
    # Worktree-aware reservation (prototype): off-main no longer refuses.
    # With --no-push it commits a provisional reservation to the CURRENT
    # branch (the push path is exercised by the detached-worktree tests).
    def test_new_off_main_no_push_reserves_on_current_branch(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/something\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "myslug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Provisional stub created locally (002 = max(001) + 1).
        self.assertTrue((self.target / "docs/specs/002-myslug/spec.md").is_file())
        # Committed with a pathspec-limited commit so unrelated staged work
        # can't leak into the reservation commit.
        commit_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("--", commit_calls[0])
        # No push / fetch — --no-push is purely local.
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git push", flat)
        self.assertNotIn("git fetch", flat)

    # Worktree-aware reservation — default (push) from off-main claims the
    # number on origin/main via an EPHEMERAL DETACHED worktree, never
    # touching the caller's branch.
    def test_new_off_main_push_uses_detached_worktree(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/x\n")
        # The reservation commit is pushed BY SHA, so rev-parse must return a
        # non-empty SHA. fetch / worktree add / add / commit / push <sha>:main
        # / worktree remove all default to rc=0 in the recorder.
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="0a1b2c3d\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "fromtree", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        # Detached checkout of origin/main — NOT a checkout of `main`
        # (which a linked worktree can't do).
        self.assertIn("git worktree add --detach", flat)
        self.assertIn("origin/main", flat)
        # Pushes the detached commit onto main BY SHA — NOT `git push origin
        # main` and NOT `HEAD:main` (which would resolve a relative origin URL
        # against the temp worktree).
        self.assertIn("git push origin 0a1b2c3d:refs/heads/main", flat)
        # The ephemeral worktree is always torn down.
        self.assertIn("git worktree remove --force", flat)
        # The caller's branch is never checked out or reset.
        self.assertNotIn("git checkout main", flat)
        self.assertNotIn("git reset --hard", flat)

    # Worktree path race recovery: the stranded commit lives only in the
    # ephemeral worktree, so recovery is just the teardown — no on-main-style
    # `git reset --hard HEAD~1`.
    def test_new_off_main_race_cleans_up_worktree(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/x\n")
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="0a1b2c3d\n")
        # Push argv now starts with the SHA refspec, so match on the prefix.
        rec.stub(_matches("git", "push", "origin"),
                 returncode=1,
                 stderr="! [rejected] HEAD -> main (non-fast-forward)\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "raced", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        self.assertIn("race", str(ctx.exception).lower())
        flat = " | ".join(rec.argv_log())
        self.assertIn("git worktree remove --force", flat)
        self.assertNotIn("git reset --hard HEAD~1", flat)

    # Worktree path protected-branch fallback: push the detached commit to
    # a reserve/ branch and open a PR (no local-main to un-strand).
    def test_new_off_main_protected_falls_back_to_pr(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/x\n")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="0a1b2c3d\n")
        # First push (direct to main, by SHA) is refused by branch protection;
        # the one-shot stub fires on it, the later PR-fallback push to the
        # reserve/ branch falls through to the recorder's rc=0 default.
        rec.stub(_matches("git", "push", "origin"),
                 returncode=1,
                 stderr="remote: error: GH006: Protected branch update failed.\n")
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/7\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "protd", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        # Reservation commit pushed straight to a reserve/ branch (by SHA)...
        self.assertIn(":refs/heads/reserve/", flat)
        # ...and a PR opened with explicit head/base.
        self.assertIn("gh pr create", flat)
        self.assertIn("--head", flat)
        self.assertIn("--base", flat)
        # Ephemeral worktree still torn down.
        self.assertIn("git worktree remove --force", flat)

    # AC #5 — refuse on dirty worktree.
    def test_new_refuses_on_dirty_worktree(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec, dirty=True)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertTrue("dirty" in msg or "uncommitted" in msg or "clean" in msg,
                        f"unexpected message: {ctx.exception!r}")
        # No spec dir created
        self.assertFalse(any((self.target / "docs/specs").glob("*-myslug")))

    # AC #5 — bad slug variants: uppercase, leading digit, empty, double-dash.
    def test_new_refuses_on_bad_slug(self):
        self._mkspec("001-existing")
        bad = ["BadSlug", "1leadingdigit", "", "double--dash",
                "-leading", "with space"]
        for slug in bad:
            with self.subTest(slug=slug):
                rec = _SubprocessRecorder()
                # No preflight stubs needed — slug check happens first
                # for clearly-invalid shapes that argparse / regex
                # rejects before any git command runs.
                from unittest.mock import patch
                with patch.object(_workflow, "subprocess") as sp_mod:
                    sp_mod.run = rec
                    with self.assertRaises(_workflow.WorkflowError) as ctx:
                        _workflow.reserve_spec(
                            slug, project_dir=self.target,
                            no_push=True, pr_mode=False,
                        )
                msg = str(ctx.exception).lower()
                self.assertIn("slug", msg,
                              f"slug={slug!r}: error didn't name 'slug': "
                              f"{ctx.exception!r}")

    # Spec 063-01 (supersedes the old "refuse when docs/specs/ absent"):
    # a bare dir with no scaffold.json and no spec-driven layout is
    # `greenfield` → route to /jig:scaffold-init (not a dead-end refusal).
    def test_new_refuses_when_specs_dir_absent(self):
        # Build a fresh target without docs/specs or scaffold.json.
        bare = Path(self.tmpdir) / "bare"
        bare.mkdir()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "validslug", project_dir=bare,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        # Names the detected state + the exact next command.
        self.assertIn("greenfield", msg.lower())
        self.assertIn("/jig:scaffold-init", msg)
        # No reservation commit attempted.
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git commit", flat)

    # AC #3 — direct push succeeds; no fallback branch created.
    def test_new_direct_push_succeeds(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # fetch + add + commit + push all succeed
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # No fallback branch operations: no `git branch reserve/`, no
        # `git checkout reserve/`, no `git push -u origin reserve/`.
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git branch reserve", flat)
        self.assertNotIn("git checkout reserve", flat)
        self.assertNotIn("git push -u origin reserve", flat)
        self.assertNotIn("gh pr create", flat)

    # AC #3 + AC #4 — protected-branch stderr triggers PR fallback.
    def test_new_falls_back_on_protected_branch(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # Spec 037-02: `_next_spec_number` (push mode) consumes the
        # origin-url stub from `_stub_preflight_ok`. Re-stub for the
        # downstream `_check_gh_and_remote` call.
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        # push origin main FAILS with protection signal
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1, stderr="remote: error: GH006: Protected branch update failed.\n")
        # Fallback sequence
        rec.stub(_matches("git", "branch"), returncode=0)
        rec.stub(_matches("git", "reset", "--hard", "origin/main"),
                 returncode=0)
        rec.stub(_matches("git", "checkout"), returncode=0)
        rec.stub(_matches("git", "push", "-u", "origin"), returncode=0)
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/42\n")
        # shutil.which('gh') needs to be true; we patch shutil.which.
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertIn("git branch", flat)
        self.assertIn("git reset --hard origin/main", flat)
        self.assertIn("git checkout", flat)
        self.assertIn("git push -u origin", flat)
        self.assertIn("gh pr create", flat)

    # AC #6 — non-fast-forward triggers race-detection (NOT fallback).
    def test_new_does_not_fall_back_on_non_fast_forward(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="! [rejected]  main -> main (non-fast-forward)\n")
        # The race-recovery does `git reset --hard HEAD~1`
        rec.stub(_matches("git", "reset", "--hard", "HEAD~1"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "newslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("race", msg)
        # Local commit dropped: reset HEAD~1 fired.
        flat = " | ".join(rec.argv_log())
        self.assertIn("git reset --hard HEAD~1", flat)
        # No fallback branch / gh pr create
        self.assertNotIn("git branch reserve", flat)
        self.assertNotIn("gh pr create", flat)

    # Refinement-todo (slice 003-03 review): the race-recovery's
    # `git reset --hard HEAD~1` un-strands the commit but leaves the
    # now-empty spec dir on disk. The fix `shutil.rmtree`s the dir
    # after the reset so the user's worktree stays clean.
    def test_new_race_recovery_removes_empty_spec_dir(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="! [rejected]  main -> main (non-fast-forward)\n")
        # In tests `git reset --hard HEAD~1` is mocked so the worktree
        # files aren't actually rolled back; the helper must still clean
        # up the dir it just created.
        rec.stub(_matches("git", "reset", "--hard", "HEAD~1"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError):
                _workflow.reserve_spec(
                    "newslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        # The dir would have been created as 002-newslot
        spec_dir = self.target / "docs" / "specs" / "002-newslot"
        self.assertFalse(
            spec_dir.exists(),
            f"race recovery left empty spec dir on disk: {spec_dir}",
        )

    # AC #7 (--pr) — skip direct-push, go straight to branch + PR.
    def test_new_pr_mode_skips_direct_push(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # Spec 037-02: re-stub origin-url for `_check_gh_and_remote`
        # (the first stub is consumed by `_next_spec_number`).
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        # Fallback sequence — direct push NOT attempted.
        rec.stub(_matches("git", "branch"), returncode=0)
        rec.stub(_matches("git", "reset", "--hard", "origin/main"),
                 returncode=0)
        rec.stub(_matches("git", "checkout"), returncode=0)
        rec.stub(_matches("git", "push", "-u", "origin"), returncode=0)
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/u/r/pull/7\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "myslot", project_dir=self.target,
                no_push=False, pr_mode=True,
            )
        self.assertEqual(code, 0)
        # No `git push origin main`
        push_main = [c for c in rec.calls
                     if tuple(c[:4]) == ("git", "push", "origin", "main")]
        self.assertEqual(push_main, [],
                         f"--pr should skip direct push; calls: "
                         f"{rec.argv_log()}")
        # But the branch + PR creation happened
        flat = " | ".join(rec.argv_log())
        self.assertIn("git push -u origin", flat)
        self.assertIn("gh pr create", flat)

    # AC #4 — PR fallback refuses without `gh` on PATH.
    def test_new_pr_mode_refuses_without_gh(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value=None):
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslot", project_dir=self.target,
                    no_push=False, pr_mode=True,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("gh", msg, f"prereq message must name 'gh': "
                                 f"{ctx.exception!r}")

    # AC #4 — PR fallback refuses when origin isn't on github.com.
    def test_new_pr_mode_refuses_without_github_remote(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        # Override preflight: origin URL points elsewhere
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0,
                 stdout="git@gitlab.example.com:foo/bar.git\n")
        # Spec 037-02: re-stub origin-url for `_check_gh_and_remote`
        # (the first stub is consumed by `_next_spec_number`).
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0,
                 stdout="git@gitlab.example.com:foo/bar.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslot", project_dir=self.target,
                    no_push=False, pr_mode=True,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("github.com", msg,
                      f"prereq message must name 'github.com': "
                      f"{ctx.exception!r}")

    # AC #7 (--no-push) — never calls fetch or push.
    def test_new_no_push_skips_remote_calls(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "soloslot", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git fetch", flat)
        self.assertNotIn("git push", flat)

    # AC #7 — mutex: --no-push and --pr together is a usage error.
    def test_new_no_push_and_pr_are_mutually_exclusive(self):
        self._mkspec("001-existing")
        # argparse usage error → exit 2 from main()
        result = run_workflow("new", "myslot", "--no-push", "--pr")
        self.assertNotEqual(result.returncode, 0)

    # AC #2 — title casing example from the spec.
    def test_new_title_cases_slug_per_spec_example(self):
        # Seed enough specs to push the reservation to 016 (matches the
        # spec example for clarity).
        self._mkspec("001-existing")
        self._mkspec("015-other")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "parallel-worktree-collision",
                project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        text = (self.target / "docs/specs/016-parallel-worktree-collision/"
                              "spec.md").read_text()
        self.assertIn("Parallel-worktree collision", text)


class MixedLayoutTransitionTests(unittest.TestCase):
    """Slice 018-02 AC #2: `transition` writes to the slice file when the
    slice lives in one; writes to spec.md when it's embedded. Same
    command, layout-aware target."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-mixed-"))
        # Slice 018-01 in its own file
        self.slice_file = self.tmpdir / "slice-01-file-based.md"
        self.slice_file.write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 018-01 — file-slice\n\n"
            "**Goal:** placeholder.\n"
        )
        # Slice 018-02 embedded in spec.md
        self.spec = self.tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec\n\n"
            "## Slice 018-02 — embedded-slice\n\n"
            "**STATUS: DRAFT**\n\n"
            "**Goal:** placeholder.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_transition_writes_to_slice_file_not_spec_md(self):
        result = run_workflow(
            "transition", str(self.spec), "018-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Slice file's frontmatter updated
        slice_after = self.slice_file.read_text()
        self.assertIn("status: IN_PROGRESS", slice_after)
        # spec.md's slice content section is UNCHANGED — the slice
        # mutation must go to loc.path, not blindly spec_md. Slice 030-01
        # adds an additional valid write to spec.md's frontmatter
        # `status:` field (rollup), so the file is allowed to change ONLY
        # in that field. The embedded slice section (018-02) must not
        # have been touched.
        spec_after = self.spec.read_text()
        m = re.search(
            r"## Slice 018-02[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", spec_after,
        )
        self.assertIsNotNone(m)
        self.assertEqual(
            m.group(1), "DRAFT",
            "spec.md's embedded slice 018-02 should remain DRAFT — only "
            "the slice file's 018-01 was transitioned",
        )

    def test_transition_writes_to_spec_md_for_embedded_slice(self):
        slice_before = self.slice_file.read_text()
        result = run_workflow(
            "transition", str(self.spec), "018-02", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # spec.md changed — embedded slice's STATUS marker rewritten
        spec_after = self.spec.read_text()
        m = re.search(r"## Slice 018-02[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", spec_after)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "IN_PROGRESS")
        # Slice file untouched
        self.assertEqual(self.slice_file.read_text(), slice_before)


class NewSpecScaffoldsFilePerSliceTests(unittest.TestCase):
    """Slice 018-03 AC #1+#2+#4: `workflow.py new` scaffolds spec.md
    (header-only) + a starter `slice-01-*.md` file. spec.md must NOT
    contain an embedded `## Slice` section."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-new-fps-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        # Minimal git init so reserve_spec's stage+commit path doesn't
        # break — we mock subprocess anyway, but the dir must look git-like.
        (self.target / "docs/specs").mkdir(parents=True)
        # Spec 063-01: scaffold.json sentinel → `reserve_spec` classifies as
        # `scaffolded` and proceeds to the legacy reserve flow under test.
        (self.target / "scaffold.json").write_text("{}\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _stub_subprocess(self, rec):
        rec.stub(_matches("git", "symbolic-ref"), returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status"), returncode=0)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "merge-base"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)

    def test_emits_spec_md_plus_starter_slice_file(self):
        import importlib
        from unittest.mock import patch

        import skills  # noqa: F401 — namespace anchor
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "demo-slug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        spec_dir = self.target / "docs/specs/001-demo-slug"
        self.assertTrue((spec_dir / "spec.md").is_file())
        self.assertTrue((spec_dir / "slice-01-tbd.md").is_file(),
                        "starter slice file slice-01-tbd.md must be emitted")

    def test_spec_md_has_no_embedded_slice_section(self):
        import importlib
        from unittest.mock import patch
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            _workflow.reserve_spec("demo-slug",
                                    project_dir=self.target,
                                    no_push=True, pr_mode=False)
        spec_text = (self.target / "docs/specs/001-demo-slug/spec.md").read_text()
        self.assertNotIn("## Slice ", spec_text,
                         "spec.md must not contain a `## Slice` heading "
                         "(slices live in sibling files now)")

    def test_starter_slice_file_has_file_per_slice_shape(self):
        import importlib
        from unittest.mock import patch
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            _workflow.reserve_spec("demo-slug",
                                    project_dir=self.target,
                                    no_push=True, pr_mode=False)
        slice_text = (self.target / "docs/specs/001-demo-slug"
                      / "slice-01-tbd.md").read_text()
        # Frontmatter at top (file-per-slice shape)
        self.assertTrue(slice_text.startswith("---\n"))
        # Heading after frontmatter, with the right slice fragment
        self.assertIn("## Slice 001-01 — tbd", slice_text)
        # Placeholders substituted
        self.assertNotIn("{{NUMBER}}", slice_text)
        self.assertNotIn("{{NAME}}", slice_text)

    def test_iter_slices_picks_up_starter_slice(self):
        """End-to-end: after `new`, `iter_slices(spec.md)` yields the
        starter slice — proves the helpers from 018-01/02 see the
        scaffolded shape end-to-end."""
        import importlib
        from unittest.mock import patch
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            _workflow.reserve_spec("demo-slug",
                                    project_dir=self.target,
                                    no_push=True, pr_mode=False)
        # Import iter_slices from the common parser
        sys.path.insert(0, str(REPO_ROOT / "skills" / "_common"))
        from parsing import iter_slices
        spec_md = self.target / "docs/specs/001-demo-slug/spec.md"
        locs = list(iter_slices(spec_md))
        labels = [sl.label for sl in locs]
        self.assertIn("001-01 — tbd", labels)


class ReserveSpecPreconditionRoutingTests(unittest.TestCase):
    """Spec 063-01: `reserve_spec` replaces the weak `docs/specs/`-presence
    check with a three-way scaffold-state classification that ROUTES — an
    `adoptable` project to /jig:migrate, a `greenfield` one to
    /jig:scaffold-init — while a `scaffolded` project (scaffold.json present)
    proceeds to the legacy reserve flow unchanged. `JIG_SCAFFOLD_PRECONDITION`
    bypasses the classification entirely (ADR-0011 deliberateness gate)."""

    def setUp(self):
        import shutil
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-063-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        self._saved = os.environ.pop("JIG_SCAFFOLD_PRECONDITION", None)
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

        def _restore():
            if self._saved is not None:
                os.environ["JIG_SCAFFOLD_PRECONDITION"] = self._saved
            else:
                os.environ.pop("JIG_SCAFFOLD_PRECONDITION", None)
        self.addCleanup(_restore)

    def _make_greenfield(self):
        # Empty project: no scaffold.json, no spec-driven layout.
        pass

    def _make_adoptable(self):
        # >=3 triggers, no scaffold.json, no jig watermark.
        (self.target / "docs" / "specs").mkdir(parents=True)
        (self.target / "docs" / "decisions").mkdir(parents=True)
        (self.target / "docs" / "workflow.md").write_text("# wf\n")

    def _make_scaffolded(self):
        (self.target / "docs" / "specs").mkdir(parents=True)
        (self.target / "scaffold.json").write_text("{}\n")

    def _run_reserve(self):
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "validslug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        return code, rec

    # AC3 — adoptable → /jig:migrate, no reservation commit.
    def test_adoptable_routes_to_migrate(self):
        self._make_adoptable()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "validslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("adoptable", msg.lower())
        self.assertIn("/jig:migrate", msg)
        # No directory created, no reservation commit.
        self.assertFalse(
            (self.target / "docs" / "specs" / "001-validslug").exists())
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git commit", flat)

    # AC2 — greenfield → /jig:scaffold-init, no reservation commit.
    def test_greenfield_routes_to_scaffold_init(self):
        self._make_greenfield()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "validslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("greenfield", msg.lower())
        self.assertIn("/jig:scaffold-init", msg)
        self.assertFalse((self.target / "docs" / "specs").exists())
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git commit", flat)

    # Interrupted scaffold (jig watermark, no scaffold.json) → greenfield
    # routing (scaffold-init recovery), even with >=3 triggers present.
    def test_interrupted_scaffold_routes_to_scaffold_init(self):
        (self.target / "CLAUDE.md").write_text(
            "# Proj\n\n<!-- Generated by [jig] -->\n")
        (self.target / "docs" / "specs").mkdir(parents=True)
        (self.target / "docs" / "decisions").mkdir(parents=True)
        (self.target / "docs" / "workflow.md").write_text("# wf\n")
        (self.target / "docs" / "architecture.md").write_text("# arch\n")
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "validslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("greenfield", msg.lower())
        self.assertIn("/jig:scaffold-init", msg)

    # AC4 — scaffolded → proceeds through the legacy reserve flow.
    def test_scaffolded_proceeds_to_reserve(self):
        self._make_scaffolded()
        rec = _SubprocessRecorder()
        # Stub the legacy preflight + commit path (branch==main, clean tree,
        # github origin, add/commit succeed) — no remote calls for --no-push.
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "validslug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # The legacy flow created the reservation directory + stub.
        self.assertTrue(
            (self.target / "docs" / "specs" / "001-validslug" / "spec.md")
            .is_file())

    # AC6 — bypass: JIG_SCAFFOLD_PRECONDITION=0 skips classification and
    # runs the legacy flow even on a greenfield project.
    def test_bypass_runs_legacy_flow_on_greenfield(self):
        # Greenfield but the legacy flow still needs docs/specs/ to exist
        # (the bypass restores *today's* behavior, including its own weak
        # docs/specs/ check). Provide docs/specs/ so the legacy path runs.
        (self.target / "docs" / "specs").mkdir(parents=True)
        os.environ["JIG_SCAFFOLD_PRECONDITION"] = "0"
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "validslug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        self.assertTrue(
            (self.target / "docs" / "specs" / "001-validslug" / "spec.md")
            .is_file())

    # AC6 — bypass with the legacy weak check still firing: docs/specs/
    # absent under bypass → the OLD dead-end refusal (preserves today's
    # behavior exactly, no scaffold-state routing).
    def test_bypass_preserves_legacy_weak_refusal(self):
        os.environ["JIG_SCAFFOLD_PRECONDITION"] = "false"
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "validslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        # Legacy message (not the scaffold-state routing message).
        self.assertIn("docs/specs", msg)
        self.assertNotIn("/jig:scaffold-init", msg)
        self.assertNotIn("/jig:migrate", msg)


class MixedLayoutDependencyValidationTests(unittest.TestCase):
    """Slice 018-02 follow-up (reviewer §SPECIFIC ISSUES):
    `_lookup_slice_status` and `_resolve_dep_path` must see file-per-slice
    slices when resolving DONE-transition dependencies."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-deps-"))
        # Dep slice lives in a sibling file, marked DONE.
        dep_spec_dir = self.tmpdir / "docs/specs/050-deps"
        dep_spec_dir.mkdir(parents=True)
        (dep_spec_dir / "slice-01-prereq.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified: 2026-05-15\n---\n\n"
            "## Slice 050-01 — prereq\n\nBody.\n"
        )
        (dep_spec_dir / "spec.md").write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 050\n\n## Overview\n\nNote.\n"
        )
        # Consumer slice depends on it. Lives in spec.md, RECONCILED.
        consumer_dir = self.tmpdir / "docs/specs/051-consumer"
        consumer_dir.mkdir(parents=True)
        self.consumer_spec = consumer_dir / "spec.md"
        self.consumer_spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 051\n\n"
            "## Slice 051-01 — consumes-prereq\n\n"
            "---\nstatus: RECONCILED\ndependencies: [050-01]\nlast_verified:\n---\n\n"
            "**Goal:** depends on 050-01.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_done_transition_finds_dep_in_slice_file(self):
        """Pre-018-02 bug: dependency validation walked `## Slice` headers
        inside spec.md only. A consumer slice whose `dependencies: [050-01]`
        targets a slice that's been split out to `slice-01-prereq.md`
        would be reported as 'slice not found' even though it IS DONE.
        After the fix, the DONE transition succeeds."""
        result = run_workflow(
            "transition", str(self.consumer_spec), "051-01", "DONE",
        )
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")


class MixedLayoutStatusBoardTests(unittest.TestCase):
    """Slice 018-02: status-board regen sees both layouts in one spec."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-board-mixed-"))
        # Status-board requires the README.md target to already exist
        # (it regenerates an existing board, doesn't create one from
        # nothing). Stub one in.
        (self.tmpdir / "docs/specs").mkdir(parents=True)
        (self.tmpdir / "docs/specs/README.md").write_text(
            "# Status board\n\n| Spec | Slice | Status | Notes |\n"
            "|---|---|---|---|\n"
        )
        spec_dir = self.tmpdir / "docs/specs/099-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "slice-01-from-file.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 099-01 — alpha\n\nBody.\n"
        )
        (spec_dir / "spec.md").write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 099\n\n"
            "## Slice 099-02 — beta\n\n**STATUS: DRAFT**\n\nBody.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_board_lists_both_layouts(self):
        result = run_workflow("status-board", str(self.tmpdir))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = (self.tmpdir / "docs/specs/README.md").read_text()
        self.assertIn("099-01 — alpha", board)
        self.assertIn("099-02 — beta", board)
        # Status from each layout is read correctly
        # Slice file → DONE; embedded → DRAFT
        self.assertRegex(board, r"099-01 — alpha\s*\|\s*\*\*DONE\*\*")
        self.assertRegex(board, r"099-02 — beta\s*\|\s*DRAFT")


# ---------- spike documentation surface (slice 029-01) ----------


class SpikeSliceTemplateTests(unittest.TestCase):
    """Slice 029-01 AC #4: the slice template documents the spike body
    shape under a `kind: spike` subsection.

    AC #7 also concerns this surface — the three outcome forms
    (`ADR-NNNN created`, `spec NNN-NN unblocked`, `abandoned (reason)`)
    and the semicolon multi-outcome convention must be documented here
    so the template, SKILL.md, and SPIDR primer agree.
    """

    def setUp(self):
        template = (REPO_ROOT / "templates" / "docs" / "specs"
                    / "slice-template.md")
        self.template = template
        self.text = template.read_text()

    def test_template_has_spike_subsection_heading(self):
        # AC #4: a subsection introducing the spike body shape exists.
        self.assertRegex(
            self.text,
            r"(?im)^###\s+.*kind:\s*spike.*",
            "expected a '### For `kind: spike` slices' (or similar) "
            "subsection in the slice template",
        )

    def test_template_lists_all_four_spike_labels(self):
        # AC #4: the four labelled blocks are documented.
        for label in ("**Question:**", "**Time-box:**",
                      "**Findings:**", "**Outcome:**"):
            self.assertIn(label, self.text,
                          f"spike body label {label!r} missing from template")

    def test_template_documents_three_outcome_forms(self):
        # AC #7: all three outcome forms documented.
        self.assertIn("ADR-NNNN created", self.text)
        self.assertIn("spec NNN-NN unblocked", self.text)
        self.assertIn("abandoned (reason)", self.text)

    def test_template_documents_semicolon_multi_outcome(self):
        # AC #7: multiple outcomes joined by `;` documented.
        self.assertIn(";", self.text)
        # Cheap pin: at least one prose mention of "semicolon" or "multiple"
        # near the spike section.
        self.assertRegex(
            self.text,
            r"(?is)kind:\s*spike.*(semicolon|multiple outcomes)",
            "template must say multiple outcomes are separated by `;`",
        )


class SpidrPrimerSpikeTests(unittest.TestCase):
    """Slice 029-01 AC #5 + AC #8: the SPIDR primer at
    `docs/spec-workflow/spidr-primer.md` documents the
    "when S fires → kind: spike" rule with a worked example.
    """

    def setUp(self):
        primer = REPO_ROOT / "docs" / "spec-workflow" / "spidr-primer.md"
        self.primer_path = primer
        self.assertTrue(primer.is_file(),
                        f"SPIDR primer must exist at {primer}")
        self.text = primer.read_text()

    def test_primer_documents_when_s_fires_rule(self):
        # AC #5: explicit "when the S axis fires, mark `kind: spike`" rule.
        # Match the load-bearing phrasing: a mention of `kind: spike` near
        # the discussion of when the Spike axis applies.
        self.assertIn("kind: spike", self.text,
                      "SPIDR primer must reference `kind: spike` explicitly")
        # The rule should appear in the context of S/Spike axis.
        self.assertRegex(
            self.text,
            r"(?is)(spike|S axis|S\s*—)[^\n]*?kind:\s*spike|"
            r"kind:\s*spike[^\n]*?(spike|S axis|S\s*—)",
            "the `kind: spike` rule must appear in the context of the S axis",
        )

    def test_primer_worked_example_has_four_labels(self):
        # AC #8: a worked spike example with all four labels.
        for label in ("**Question:**", "**Time-box:**",
                      "**Findings:**", "**Outcome:**"):
            self.assertIn(label, self.text,
                          f"SPIDR primer worked example missing {label!r}")

    def test_primer_worked_example_has_concrete_outcome(self):
        # AC #8: the worked example should show one of the three outcome
        # forms (ADR-NNNN / spec NNN-NN / abandoned) concretely.
        outcome_section = self.text
        self.assertRegex(
            outcome_section,
            r"(?im)\*\*Outcome:\*\*[^\n]*?"
            r"(ADR-\d{4}\s+created|spec\s+\d{3}-\d{2}\s+unblocked"
            r"|abandoned\s*\([^)]+\))",
            "worked example must show a concrete Outcome value",
        )

    def test_primer_documents_three_outcome_forms(self):
        # AC #7: outcome forms documented in the primer too.
        self.assertIn("ADR-NNNN created", self.text)
        self.assertIn("spec NNN-NN unblocked", self.text)
        self.assertIn("abandoned (reason)", self.text)


class SpecWorkflowSkillMdSpikeTests(unittest.TestCase):
    """Slice 029-01 AC #6 + AC #7: `skills/spec-workflow/SKILL.md` gains a
    "Spike slices" subsection covering (a) when to introduce a spike,
    (b) the four-label body shape, (c) always-nested rule, (d) abandoned
    failure mode.
    """

    def setUp(self):
        skill = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
        self.skill_path = skill
        self.text = skill.read_text()

    def test_skill_has_spike_slices_subsection(self):
        # AC #6: a `## Spike slices` (or `### Spike slices`) section exists.
        self.assertRegex(
            self.text,
            r"(?im)^#{2,3}\s+Spike slices\s*$",
            "expected a 'Spike slices' subsection in spec-workflow/SKILL.md",
        )

    def test_skill_lists_four_body_labels(self):
        # AC #6(b): the four labelled blocks are named.
        for label in ("Question", "Time-box", "Findings", "Outcome"):
            self.assertIn(label, self.text,
                          f"SKILL.md missing spike body label {label!r}")

    def test_skill_documents_always_nested_rule(self):
        # AC #6(c): the always-nested rule must be stated.
        # Look for "always nested" or "never standalone" phrasing near
        # the spike section.
        self.assertRegex(
            self.text,
            r"(?is)spike slices.*?(always[- ]nested|never standalone"
            r"|no standalone|no\s+`?docs/spikes/?`?)",
            "SKILL.md must document the always-nested rule for spikes",
        )

    def test_skill_documents_abandoned_failure_mode(self):
        # AC #6(d): abandoned-spike manual reshape pattern documented.
        self.assertRegex(
            self.text,
            r"(?is)abandon",
            "SKILL.md must document the abandoned-spike failure mode",
        )
        # The mode must mention manual review / audit of dependents,
        # not automatic cascade.
        self.assertRegex(
            self.text,
            r"(?is)(manual|human).*?(audit|reshape|review).*?depend|"
            r"depend.*?(manual|human).*?(audit|reshape|review)",
            "SKILL.md must say abandoned spikes require manual dependent audit",
        )

    def test_skill_documents_three_outcome_forms(self):
        # AC #7: outcome forms appear in SKILL.md too.
        self.assertIn("ADR-NNNN created", self.text)
        self.assertIn("spec NNN-NN unblocked", self.text)
        self.assertIn("abandoned (reason)", self.text)


# ---------- status-board spike marker (slice 029-02) ----------


class StatusBoardSpikeMarkerTests(unittest.TestCase):
    """Slice 029-02: `kind: spike` slices render with a visible marker
    in the status board, derived from the slice's `kind:` field at render
    time. The marker is additive — it does not introduce a new column,
    change column shape, or break parser round-trips."""

    # The marker chosen (per spec Open question #3 lean): a leading
    # microscope emoji on the slice cell. Single-char prefix, no schema
    # churn, survives the `parse_existing_notes` regex round-trip.
    MARKER = "\U0001f52c"  # 🔬

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-spike-board-"))
        self.target = self.tmpdir / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spike_slice(self, spec_dir: str, label: str,
                            status: str, kind: str = "spike") -> Path:
        """Create a file-per-slice spec dir with a `kind: spike`
        frontmatter slice."""
        sd = self.target / "docs/specs" / spec_dir
        sd.mkdir(parents=True, exist_ok=True)
        # Stub spec.md (frontmatter only — slice lives in slice-NN-*.md).
        spec_md = sd / "spec.md"
        if not spec_md.is_file():
            spec_md.write_text("---\nstatus: DRAFT\n---\n\n# Spec\n")
        # File-per-slice slice file with `kind:` frontmatter.
        slice_num = label.split()[0].split("-")[1]  # "029-02 alpha" → "02"
        slice_file = sd / f"slice-{slice_num}-test.md"
        kind_line = f"kind: {kind}\n" if kind else ""
        slice_file.write_text(
            f"---\nstatus: {status}\ndependencies: []\n{kind_line}---\n\n"
            f"## Slice {label}\n\n**Goal:** investigate something.\n"
        )
        return slice_file

    def _write_feature_slice(self, spec_dir: str, label: str,
                              status: str) -> Path:
        """Create a regular (non-spike) slice — no `kind:` field, or
        `kind: feature`. Default: no `kind:` field at all (most realistic
        for legacy slices)."""
        return self._write_spike_slice(spec_dir, label, status, kind="")

    def _read_board(self) -> str:
        return (self.target / "docs/specs/README.md").read_text()

    # ----- AC #1: spike slices carry the marker; non-spike unchanged.

    def test_spike_slice_renders_with_marker(self):
        self._write_spike_slice("100-spike-test", "100-01 — investigate-x",
                                 "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # The slice cell carries the marker prefix on the spike slice row.
        # Anchor against the slice label so we catch the prefix and the
        # column shape together.
        self.assertRegex(
            board,
            rf"\|\s*{re.escape(self.MARKER)}\s+100-01 — investigate-x\s*\|",
            f"spike row missing marker; board:\n{board}",
        )

    def test_non_spike_slice_renders_without_marker(self):
        self._write_feature_slice("101-feature", "101-01 — regular-work",
                                   "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # The non-spike slice cell has no leading marker.
        self.assertIn("101-01 — regular-work", board)
        self.assertNotRegex(
            board,
            rf"\|\s*{re.escape(self.MARKER)}\s+101-01 — regular-work",
            f"non-spike row has unexpected marker; board:\n{board}",
        )

    def test_explicit_kind_feature_renders_without_marker(self):
        """`kind: feature` (the documented explicit-default synonym for
        unset) must NOT trigger the marker."""
        self._write_spike_slice("102-feature-explicit",
                                 "102-01 — explicit-feature",
                                 "DRAFT", kind="feature")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        self.assertIn("102-01 — explicit-feature", board)
        self.assertNotRegex(
            board,
            rf"\|\s*{re.escape(self.MARKER)}\s+102-01 — explicit-feature",
        )

    # ----- AC #2: marker is derived from `kind:`, not stored separately.

    def test_marker_derived_from_kind_field_on_regen(self):
        """Manual-edit-to-the-board that strips the marker is re-added
        on the next regen (marker is recomputed from each slice's `kind:`,
        not stored in the board itself)."""
        self._write_spike_slice("110-derive", "110-01 — a-spike", "DRAFT")
        # First regen — marker present.
        run_workflow("status-board", str(self.target))
        board1 = self._read_board()
        self.assertIn(self.MARKER, board1)
        # Hand-strip the marker from the board (manual edit).
        stripped = board1.replace(f"{self.MARKER} 110-01", "110-01")
        self.assertNotEqual(stripped, board1)
        (self.target / "docs/specs/README.md").write_text(stripped)
        # Second regen — marker is restored from the slice's `kind:`.
        run_workflow("status-board", str(self.target))
        board2 = self._read_board()
        self.assertIn(f"{self.MARKER} 110-01", board2,
                       "marker must be re-added on regen even after manual strip")

    def test_flipping_kind_field_propagates_on_next_regen(self):
        """Editing the slice's `kind:` field from `spike` to nothing
        (regular feature) removes the marker on the next regen."""
        slice_file = self._write_spike_slice(
            "111-flip", "111-01 — flippable", "DRAFT",
        )
        run_workflow("status-board", str(self.target))
        board_with = self._read_board()
        self.assertIn(f"{self.MARKER} 111-01", board_with)
        # Now flip the slice's frontmatter — drop `kind: spike`.
        original = slice_file.read_text()
        flipped = original.replace("kind: spike\n", "")
        self.assertNotEqual(flipped, original)
        slice_file.write_text(flipped)
        # Re-regen the board — marker should be gone for this slice.
        run_workflow("status-board", str(self.target))
        board_after = self._read_board()
        self.assertIn("111-01 — flippable", board_after)
        self.assertNotRegex(
            board_after,
            rf"\|\s*{re.escape(self.MARKER)}\s+111-01",
            "marker must vanish when `kind: spike` is removed from the slice",
        )

    # ----- AC #3: marker does not break parsers; round-trip preserved.

    def test_marker_does_not_corrupt_notes_preservation(self):
        """The marker must round-trip through `parse_existing_notes` —
        manual notes on a spike row must survive subsequent regens
        unchanged, with the marker still in place."""
        self._write_spike_slice("120-roundtrip", "120-01 — survive-notes",
                                 "DRAFT")
        run_workflow("status-board", str(self.target))
        board_path = self.target / "docs/specs/README.md"
        first = board_path.read_text()
        # Find the spike row and curate a note on it.
        # The row reads: `| [spec] | 🔬 120-01 — survive-notes | DRAFT |  |`
        # We replace the trailing empty notes cell with a curated note.
        empty_cell = (
            f"| {self.MARKER} 120-01 — survive-notes | DRAFT |  |"
        )
        curated_cell = (
            f"| {self.MARKER} 120-01 — survive-notes | DRAFT "
            f"| curated note — spike-row test |"
        )
        self.assertIn(empty_cell, first,
                       f"baseline row shape missing; board:\n{first}")
        board_path.write_text(first.replace(empty_cell, curated_cell))
        # Re-regen — note must survive AND marker stays.
        run_workflow("status-board", str(self.target))
        final = board_path.read_text()
        self.assertIn("curated note — spike-row test", final,
                       f"curated note on spike row lost on regen; board:\n{final}")
        self.assertIn(f"{self.MARKER} 120-01 — survive-notes", final)

    # ----- AC #4: marker is documented (status-board preamble).

    def test_status_board_preamble_documents_the_marker(self):
        """A reader who sees `🔬` should be able to find out what it
        means without grepping for `kind: spike`. The status-board
        preamble (or a small header sentence) names the marker."""
        # Existing repo's board carries the documentation; scaffolded
        # projects get the same documentation via the template (pinned
        # by `test_scaffold_template_documents_spike_marker` below).
        # Here we pin the in-repo board itself, which is what real
        # readers see.
        board_path = REPO_ROOT / "docs" / "specs" / "README.md"
        text = board_path.read_text()
        # The preamble lives above the first `| Spec` table header.
        m = re.search(r"(?m)^\|\s*Spec\b", text)
        self.assertIsNotNone(m, "no `| Spec` table header in board")
        preamble = text[: m.start()]
        # Marker + an explanatory mention of "spike" in the preamble.
        self.assertIn(self.MARKER, preamble,
                       f"preamble must show the marker glyph; got:\n{preamble}")
        self.assertRegex(
            preamble,
            r"(?i)spike",
            "preamble must mention 'spike' so the marker meaning is recoverable",
        )

    # ----- AC #5: tests cover presence, absence, and mixed.

    def test_no_spike_spec_renders_with_no_markers(self):
        """A spec with no spike slices produces a status board with no
        marker character anywhere in its rows."""
        self._write_feature_slice("130-no-spikes", "130-01 — a", "DRAFT")
        self._write_feature_slice("130-no-spikes", "130-02 — b", "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # Pull only the active table rows for this spec; the preamble
        # documents the marker so we must scope the assertion to rows.
        active = board.split("## Deferred slices")[0]
        spec_rows = [
            ln for ln in active.splitlines()
            if "130-no-spikes" in ln
        ]
        self.assertEqual(len(spec_rows), 2)
        for row in spec_rows:
            self.assertNotIn(
                self.MARKER, row,
                f"unexpected marker on non-spike row: {row!r}",
            )

    def test_mixed_spec_marks_spikes_only(self):
        """A spec with one spike + one feature slice marks only the spike."""
        self._write_spike_slice("131-mixed", "131-01 — a-spike",
                                 "DRAFT", kind="spike")
        self._write_feature_slice("131-mixed", "131-02 — a-feature", "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spike_rows = [
            ln for ln in active.splitlines() if "131-01 — a-spike" in ln
        ]
        feature_rows = [
            ln for ln in active.splitlines() if "131-02 — a-feature" in ln
        ]
        self.assertEqual(len(spike_rows), 1)
        self.assertEqual(len(feature_rows), 1)
        self.assertIn(self.MARKER, spike_rows[0])
        self.assertNotIn(self.MARKER, feature_rows[0])

    def test_all_spike_spec_marks_every_row(self):
        """A spec where every slice is a spike — all rows carry the marker."""
        self._write_spike_slice("132-all-spike", "132-01 — q1",
                                 "DRAFT", kind="spike")
        self._write_spike_slice("132-all-spike", "132-02 — q2",
                                 "IN_PROGRESS", kind="spike")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spec_rows = [
            ln for ln in active.splitlines() if "132-all-spike" in ln
        ]
        self.assertEqual(len(spec_rows), 2)
        for row in spec_rows:
            self.assertIn(
                self.MARKER, row,
                f"row missing marker in all-spike spec: {row!r}",
            )

    def test_one_slice_spec_with_spike_renders_marker(self):
        """The 1-slice-spec case from the 029 Overview: a normal spec
        where the only slice is `kind: spike` (the "investigation with
        no clear downstream spec yet" pattern). The marker still renders
        — this is exactly the scenario the spike workflow targets."""
        self._write_spike_slice("133-one-slice", "133-01 — sole-spike",
                                 "DRAFT", kind="spike")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spec_rows = [
            ln for ln in active.splitlines() if "133-one-slice" in ln
        ]
        self.assertEqual(len(spec_rows), 1)
        self.assertIn(self.MARKER, spec_rows[0])

    # ----- AC #6: no regressions to existing column shape.

    def test_existing_column_shape_unchanged(self):
        """Snapshot the row shape: pipe count + cell-content shape on a
        spike row matches a non-spike row except for the marker prefix
        in the slice cell. The marker is additive — no new column, no
        re-alignment."""
        self._write_spike_slice("140-shape", "140-01 — spike-row",
                                 "DRAFT", kind="spike")
        self._write_feature_slice("140-shape", "140-02 — feature-row",
                                   "DRAFT")
        run_workflow("status-board", str(self.target))
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spike_rows = [
            ln for ln in active.splitlines() if "140-01 — spike-row" in ln
        ]
        feature_rows = [
            ln for ln in active.splitlines() if "140-02 — feature-row" in ln
        ]
        self.assertEqual(len(spike_rows), 1)
        self.assertEqual(len(feature_rows), 1)
        # Same pipe count (i.e., same column count).
        self.assertEqual(
            spike_rows[0].count("|"), feature_rows[0].count("|"),
            f"column count drift between rows:\n"
            f"  spike:   {spike_rows[0]!r}\n  feature: {feature_rows[0]!r}",
        )
        # Spike row has exactly 5 pipes (4 cells).
        self.assertEqual(spike_rows[0].count("|"), 5,
                          f"unexpected pipe count on spike row: "
                          f"{spike_rows[0]!r}")
        # Snapshot: spike row's slice cell content is exactly
        # `<marker> <label>` (single space).
        expected_spike_cell = f"| {self.MARKER} 140-01 — spike-row |"
        self.assertIn(
            expected_spike_cell, spike_rows[0],
            f"spike row cell shape drift; got: {spike_rows[0]!r}",
        )
        # Snapshot: feature row's slice cell content is exactly `<label>`.
        expected_feature_cell = "| 140-02 — feature-row |"
        self.assertIn(
            expected_feature_cell, feature_rows[0],
            f"feature row cell shape drift; got: {feature_rows[0]!r}",
        )

    # ----- AC #7: regen idempotency.

    def test_status_board_regen_idempotent_with_spike(self):
        """Two consecutive regens against a spike-bearing project produce
        identical output."""
        self._write_spike_slice("150-idem", "150-01 — spike-idem", "DRAFT")
        self._write_feature_slice("150-idem", "150-02 — feature-idem", "DRAFT")
        run_workflow("status-board", str(self.target))
        first = self._read_board()
        run_workflow("status-board", str(self.target))
        second = self._read_board()
        self.assertEqual(
            first, second,
            "non-idempotent regen — diff suggests marker round-trip churn",
        )
        # And the marker is present in both passes.
        self.assertIn(f"{self.MARKER} 150-01 — spike-idem", first)
        self.assertIn(f"{self.MARKER} 150-01 — spike-idem", second)

    def test_status_board_idempotency_message_when_current(self):
        """When the board is already current, regen prints the
        already-current message (slice 003-01 idempotency contract held)."""
        self._write_spike_slice("151-idem", "151-01 — spike-curr", "DRAFT")
        # First regen produces the canonical state.
        run_workflow("status-board", str(self.target))
        # Second regen — already-current message must surface.
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already current", result.stdout,
                       f"idempotent regen path skipped; stdout:\n{result.stdout}")

    # ----- AC #4 (scaffold parity): the scaffold template carries the
    # same marker documentation so newly-scaffolded projects don't need
    # to re-discover the convention.

    def test_scaffold_template_documents_spike_marker(self):
        """The scaffold template at `templates/docs/specs/README.md.template`
        carries the spike-marker explanation so freshly-scaffolded
        projects ship with the documentation already in place — same
        AC #4 surface as the in-repo board (pinned above)."""
        template_path = REPO_ROOT / "templates" / "docs" / "specs" / "README.md.template"
        text = template_path.read_text()
        # Preamble sits above the first `| Spec` table header (same
        # layout as the rendered board).
        m = re.search(r"(?m)^\|\s*Spec\b", text)
        self.assertIsNotNone(m, "no `| Spec` table header in template")
        preamble = text[: m.start()]
        self.assertIn(self.MARKER, preamble,
                       f"template preamble must show the marker glyph; got:\n{preamble}")
        self.assertRegex(
            preamble,
            r"(?i)spike",
            "template preamble must mention 'spike' so the marker meaning is recoverable",
        )

    # ----- AC #1 (deferred-table parity): DEFERRED `kind: spike` rows
    # render with the marker too — same visual contract as active rows.

    def test_deferred_spike_renders_with_marker(self):
        """A DEFERRED spike slice carries the marker in the `## Deferred
        slices` table, same as it would in the active table."""
        self._write_spike_slice("160-deferred-spike",
                                 "160-01 — investigate-later",
                                 "DEFERRED")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # Locate the deferred section and scope the assertion to it.
        deferred_idx = board.find("## Deferred slices")
        self.assertNotEqual(deferred_idx, -1,
                            f"no deferred section in board:\n{board}")
        deferred = board[deferred_idx:]
        self.assertIn(f"{self.MARKER} 160-01 — investigate-later", deferred,
                      f"deferred spike row missing marker; section:\n{deferred}")

    def test_deferred_non_spike_renders_without_marker(self):
        """A DEFERRED non-spike slice renders unchanged in the deferred
        table — the marker is spike-only."""
        self._write_feature_slice("161-deferred-feature",
                                   "161-01 — wait-on-trigger",
                                   "DEFERRED")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        deferred_idx = board.find("## Deferred slices")
        self.assertNotEqual(deferred_idx, -1,
                            f"no deferred section in board:\n{board}")
        deferred = board[deferred_idx:]
        # The row exists in the deferred section.
        self.assertIn("161-01 — wait-on-trigger", deferred,
                      f"deferred feature row missing; section:\n{deferred}")
        # And does NOT carry the marker prefix on its slice cell.
        self.assertNotIn(f"{self.MARKER} 161-01", deferred,
                         f"deferred feature row erroneously carries marker; section:\n{deferred}")

class ComputeSpecStatusTests(unittest.TestCase):
    """Slice 030-01 AC #1: `compute_spec_status(spec_path)` derives the
    spec-level rollup from slice states. Pure-function tests across the
    enumerated fixtures: empty, single-DRAFT, single-DONE, single-DEFERRED,
    all-DEFERRED, mixed-DONE-DRAFT, mixed-DONE-DEFERRED,
    mixed-IN_PROGRESS-DONE, legacy embedded, file-per-slice, both layouts."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-rollup-"))
        self.spec_dir = self.tmpdir / "spec-dir"
        self.spec_dir.mkdir()
        self.spec_md = self.spec_dir / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec_md(self, body: str = "") -> None:
        """Write a spec.md with frontmatter and optional body (embedded
        sections)."""
        self.spec_md.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n## Overview\n\nSyn.\n"
            + body
        )

    def _write_slice_file(self, name: str, status: str,
                          filename: str = None) -> None:
        """Write a file-per-slice file with frontmatter status."""
        if filename is None:
            # Derive a default filename from the slice fragment portion.
            tag = name.split()[0].replace("—", "").replace("-", "")[:6]
            filename = f"slice-{tag}.md"
        path = self.spec_dir / filename
        path.write_text(
            f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
            f"## Slice {name}\n\n**Goal:** placeholder.\n"
        )

    def _embedded(self, name: str, status: str) -> str:
        """Build an embedded `## Slice ...` block w/ `**STATUS:**` marker."""
        return (
            f"\n## Slice {name}\n\n**STATUS: {status}**\n\n"
            f"**Goal:** placeholder.\n"
        )

    # AC #1: empty spec dir (no slices at all)
    def test_empty_spec_returns_draft(self):
        self._write_spec_md()
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: single DRAFT slice → DRAFT
    def test_single_draft_slice_returns_draft(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DRAFT")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: single DONE slice → DONE
    def test_single_done_slice_returns_done(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DONE")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #1: single DEFERRED slice → DRAFT (no live work)
    def test_single_deferred_slice_returns_draft(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DEFERRED")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: all slices DEFERRED → DRAFT
    def test_all_deferred_returns_draft(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DEFERRED",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DEFERRED",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: mixed DONE + DRAFT → IN_PROGRESS (work has begun)
    def test_mixed_done_draft_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DRAFT",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: mixed DONE + DEFERRED → DONE (every non-DEFERRED slice is DONE)
    def test_mixed_done_deferred_returns_done(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DEFERRED",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #1: mixed IN_PROGRESS + DONE → IN_PROGRESS
    def test_mixed_in_progress_done_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "IN_PROGRESS",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DONE",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: a single READY_FOR_REVIEW slice → IN_PROGRESS (active work)
    def test_single_ready_for_review_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "READY_FOR_REVIEW")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: a single REVIEWED slice → IN_PROGRESS
    def test_single_reviewed_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "REVIEWED")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: legacy embedded-section spec.md with a DONE slice
    def test_legacy_embedded_done_returns_done(self):
        self._write_spec_md(self._embedded("100-01 alpha", "DONE"))
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #1: legacy embedded section with mixed DONE + DRAFT → IN_PROGRESS
    def test_legacy_embedded_mixed_returns_in_progress(self):
        body = (
            self._embedded("100-01 alpha", "DONE")
            + self._embedded("100-02 beta", "DRAFT")
        )
        self._write_spec_md(body)
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: both layouts in one spec (mid-migration shape)
    def test_mixed_layouts_in_one_spec(self):
        # Slice file: DONE.  Embedded: DRAFT.  Mixed → IN_PROGRESS.
        self._write_spec_md(self._embedded("100-02 beta", "DRAFT"))
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: both layouts, all DONE
    def test_mixed_layouts_all_done(self):
        self._write_spec_md(self._embedded("100-02 beta", "DONE"))
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #6: spec.md without frontmatter still gets a computed status
    # (it's the WRITE step that's skipped, not the compute).
    def test_no_frontmatter_still_computes(self):
        # Write a spec.md that has NO frontmatter block at all
        self.spec_md.write_text("# Spec\n\n## Overview\n\nSyn.\n")
        self._write_slice_file("100-01 alpha", "DONE")
        # compute_spec_status still returns its rule-derived value
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")


class TransitionRollupTests(unittest.TestCase):
    """Slice 030-01 AC #2: `workflow.py transition` writes the rollup
    to spec.md frontmatter `status:` after the slice mutation."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-tr-rollup-"))
        self.spec_dir = self.tmpdir / "spec-dir"
        self.spec_dir.mkdir()
        self.spec_md = self.spec_dir / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec_md(self, status: str = "DRAFT") -> None:
        self.spec_md.write_text(
            f"---\nstatus: {status}\n---\n\n# Spec X\n\n## Overview\n\nSyn.\n"
        )

    def _write_slice_file(self, name: str, status: str,
                          filename: str = "slice-01-a.md") -> None:
        (self.spec_dir / filename).write_text(
            f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
            f"## Slice {name}\n\n**Goal:** placeholder.\n"
        )

    # AC #2: transition writes rollup to spec.md
    def test_transition_writes_rollup_to_spec_md(self):
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "DRAFT")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self.spec_md.read_text()
        # spec.md frontmatter status should now be IN_PROGRESS (rollup)
        m = re.search(r"^status:\s*(\w+)", text, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "IN_PROGRESS",
                         f"expected IN_PROGRESS rollup, spec.md was:\n{text}")

    # AC #2: rollup flips to DONE when only DONE slices remain
    def test_transition_to_done_flips_spec_to_done(self):
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "RECONCILED")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "DONE",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self.spec_md.read_text()
        m = re.search(r"^status:\s*(\w+)", text, re.MULTILINE)
        self.assertEqual(m.group(1), "DONE",
                         f"expected DONE rollup, spec.md was:\n{text}")

    # AC #2: idempotent — same rollup value → no spurious write
    def test_transition_rollup_is_idempotent(self):
        # Two slices: both DRAFT. spec.md frontmatter already says DRAFT.
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "DRAFT",
                               filename="slice-01-a.md")
        self._write_slice_file("200-02 beta", "DRAFT",
                               filename="slice-02-b.md")
        before = self.spec_md.read_text()
        # Transition one slice DRAFT → DRAFT (no-op-ish; rollup stays DRAFT
        # because the OTHER slice is still DRAFT).
        # Use a real change that doesn't flip rollup: transition to DRAFT.
        # We need a state transition that keeps both slices as DRAFT in
        # aggregate; transitioning 200-01 to DEFERRED keeps spec DRAFT
        # (the other slice is still DRAFT, all non-DEFERRED are DRAFT).
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "DEFERRED",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        after = self.spec_md.read_text()
        # spec.md status field should still be DRAFT
        m = re.search(r"^status:\s*(\w+)", after, re.MULTILINE)
        self.assertEqual(m.group(1), "DRAFT",
                         f"expected DRAFT rollup, spec.md was:\n{after}")
        # spec.md content unchanged (idempotent — no spurious write)
        self.assertEqual(before, after,
                         "spec.md was rewritten despite no rollup change")

    # AC #4: spec.md without frontmatter is left untouched
    def test_transition_does_not_write_to_no_frontmatter_spec(self):
        # Write a spec.md without frontmatter
        no_fm = "# Spec X\n\n## Overview\n\nNo frontmatter here.\n"
        self.spec_md.write_text(no_fm)
        self._write_slice_file("200-01 alpha", "DRAFT")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "DONE",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # spec.md content unchanged (no frontmatter insertion)
        self.assertEqual(self.spec_md.read_text(), no_fm,
                         "spec.md without frontmatter was modified — "
                         "defensive case should leave it untouched")

    # AC #2: slice mutation still happens (rollup is ADDITIONAL, not replacement)
    def test_transition_still_writes_slice_status(self):
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "DRAFT")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # The slice's status should be updated too
        slice_text = (self.spec_dir / "slice-01-a.md").read_text()
        self.assertIn("status: IN_PROGRESS", slice_text)


class StatusBoardRollupTests(unittest.TestCase):
    """Slice 030-01 AC #3: `workflow.py status-board` writes the rollup
    to every spec.md it walks (during regen)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-board-rollup-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        (self.target / "docs/specs").mkdir(parents=True)
        # Seed the board file so status-board has something to regenerate
        (self.target / "docs/specs/README.md").write_text(
            "# Status board\n\n| Spec | Slice | Status | Notes |\n"
            "|---|---|---|---|\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mk_spec(self, dirname: str, frontmatter_status: str,
                  slices: list) -> Path:
        """Build a spec dir with a spec.md (frontmatter `status:`) and a
        set of file-per-slice files. `slices` is [(name, status), ...]."""
        spec_dir = self.target / "docs/specs" / dirname
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            f"---\nstatus: {frontmatter_status}\n---\n\n"
            f"# Spec\n\n## Overview\n\nSyn.\n"
        )
        for i, (name, status) in enumerate(slices, start=1):
            (spec_dir / f"slice-{i:02d}-x.md").write_text(
                f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
                f"## Slice {name}\n\n**Goal:** placeholder.\n"
            )
        return spec_md

    # AC #3: status-board flips DRAFT → DONE for fully-done specs
    def test_status_board_flips_done_specs(self):
        spec_md = self._mk_spec("300-alpha", "DRAFT",
                                 [("300-01 a", "DONE"),
                                  ("300-02 b", "DONE")])
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        m = re.search(r"^status:\s*(\w+)", spec_md.read_text(),
                      re.MULTILINE)
        self.assertEqual(m.group(1), "DONE",
                         f"expected DONE rollup, spec.md was:\n"
                         f"{spec_md.read_text()}")

    # AC #3: status-board flips DRAFT → IN_PROGRESS for partial-done specs
    def test_status_board_flips_in_progress_specs(self):
        spec_md = self._mk_spec("301-beta", "DRAFT",
                                 [("301-01 a", "DONE"),
                                  ("301-02 b", "IN_PROGRESS")])
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        m = re.search(r"^status:\s*(\w+)", spec_md.read_text(),
                      re.MULTILINE)
        self.assertEqual(m.group(1), "IN_PROGRESS",
                         f"expected IN_PROGRESS rollup, spec.md was:\n"
                         f"{spec_md.read_text()}")

    # AC #3: status-board leaves an already-correct spec.md untouched
    # (idempotent — no spurious write)
    def test_status_board_idempotent_on_correct_specs(self):
        spec_md = self._mk_spec("302-gamma", "DONE",
                                 [("302-01 a", "DONE")])
        before = spec_md.read_text()
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        after = spec_md.read_text()
        # spec.md not changed (rollup matched what's already there)
        self.assertEqual(before, after,
                         "spec.md was rewritten despite no rollup change")

    # AC #3: status-board writes regardless of board-table-changes
    # (a spec whose status flips DRAFT → DONE updates spec.md even if
    # the board's per-slice rows are unchanged from the previous version).
    def test_status_board_writes_spec_even_when_table_unchanged(self):
        # Set up a fully-DONE spec with frontmatter status: DRAFT
        spec_md = self._mk_spec("303-delta", "DRAFT",
                                 [("303-01 a", "DONE")])
        # First regen to establish baseline table content
        run_workflow("status-board", str(self.target))
        # After first regen: spec.md should be DONE, board table reflects DONE.
        first_text = spec_md.read_text()
        m = re.search(r"^status:\s*(\w+)", first_text, re.MULTILINE)
        self.assertEqual(m.group(1), "DONE")
        # Manually flip spec.md back to DRAFT (simulating drift)
        spec_md.write_text(first_text.replace(
            "status: DONE", "status: DRAFT"
        ))
        # Second regen — table content already matches slices (idempotent
        # on its own), but spec.md frontmatter is now stale. The rollup
        # write should fire regardless.
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        m = re.search(r"^status:\s*(\w+)", spec_md.read_text(),
                      re.MULTILINE)
        self.assertEqual(m.group(1), "DONE",
                         "rollup write should fire even when the board "
                         "table itself is already current")

    # AC #4: status-board leaves a spec.md without frontmatter alone
    def test_status_board_does_not_write_to_no_frontmatter_spec(self):
        spec_dir = self.target / "docs/specs/304-epsilon"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        no_fm = "# Spec\n\n## Overview\n\nLegacy.\n"
        spec_md.write_text(no_fm)
        (spec_dir / "slice-01-a.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 304-01 — alpha\n\n**Goal:** placeholder.\n"
        )
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # spec.md content unchanged (no frontmatter insertion)
        self.assertEqual(spec_md.read_text(), no_fm,
                         "spec.md without frontmatter was modified")


# ---------------------------------------------------------------------------
# Slice 031-02 — `slice_needs_arch_review` helper + slice-template hint
# ---------------------------------------------------------------------------


class SliceNeedsArchReviewTests(unittest.TestCase):
    """Slice 031-02 AC #4 + AC #6: `workflow.py` exposes
    `slice_needs_arch_review(spec_md, slice_fragment) -> bool` that
    reads the slice's frontmatter and returns the `arch_review:` value,
    defaulting to `false` when the field is absent.

    The helper is exposed as a CLI subcommand `arch-review-needed` so
    SKILL.md's bash recipe can shell out the same way it shells out
    `subagent-type`.

    Test fixtures use the canonical post-018-03 file-per-slice layout:
    `spec.md` carries the overview + spec-level frontmatter, and a
    sibling `slice-NN-<short>.md` carries the slice content + the
    slice-level frontmatter (where `arch_review:` lives).
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-arch-needed-"))
        self.spec = self.tmpdir / "spec.md"
        self.slice_file = self.tmpdir / "slice-02-arch.md"
        # Minimum spec.md — overview only; slice content lives in sibling.
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, fm_extra: str, slice_name: str = "031-02 alpha") -> None:
        """Write a synthetic slice FILE (file-per-slice layout) with the
        given frontmatter extras. `fm_extra` goes between
        `last_verified:` and the closing `---`."""
        self.slice_file.write_text(
            "---\n"
            "status: IN_PROGRESS\n"
            "dependencies: []\n"
            "last_verified:\n"
            f"{fm_extra}"
            "---\n\n"
            f"## Slice {slice_name}\n\n"
            "**Goal:** placeholder.\n"
        )

    def _run(self, slice_fragment: str = "031-02"):
        return run_workflow(
            "arch-review-needed", str(self.spec), slice_fragment,
        )

    # AC #4 — defaults to false when field is absent
    def test_returns_false_when_field_absent(self):
        self._write_slice(fm_extra="")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "false")

    # AC #4 — reads true when frontmatter sets it
    def test_returns_true_when_field_is_true(self):
        self._write_slice(fm_extra="arch_review: true\n")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "true")

    # AC #4 — reads false explicitly
    def test_returns_false_when_field_is_false(self):
        self._write_slice(fm_extra="arch_review: false\n")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "false")

    # AC #6 — embedded slice (no per-slice frontmatter) defaults to false
    def test_returns_false_for_legacy_embedded_slice(self):
        # Legacy shape: slice embedded in spec.md with no per-slice
        # frontmatter — the `arch_review:` field can't exist there, so
        # the helper must default to false.
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n"
            "## Slice 031-02 alpha\n\n**STATUS: DRAFT**\n\n"
            "**Goal:** placeholder.\n"
        )
        # No slice_file written; spec.md carries the embedded slice.
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "false")

    def test_returns_true_for_embedded_slice_with_post_heading_frontmatter(self):
        # Legacy 015-01 layout: an embedded slice may carry per-slice
        # frontmatter inserted AFTER the `## Slice` heading. The helper
        # must read it via the layout-aware `_slice_frontmatter` path
        # (consistent with `collect_slices` / `compute_spec_status`).
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n"
            "## Slice 031-02 alpha\n\n"
            "---\nstatus: IN_PROGRESS\narch_review: true\n---\n\n"
            "**Goal:** placeholder.\n"
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "true")

    # Edge: case-insensitive truthy values
    def test_returns_true_for_truthy_variations(self):
        for truthy in ("true", "True", "TRUE", "yes"):
            self._write_slice(fm_extra=f"arch_review: {truthy}\n")
            result = self._run()
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(
                result.stdout.strip(), "true",
                f"value {truthy!r} should be treated as true",
            )

    # Edge: stdout-only (no trailing noise) for shell substitution
    def test_stdout_only_emits_clean_value(self):
        self._write_slice(fm_extra="arch_review: true\n")
        result = self._run()
        self.assertEqual(result.returncode, 0)
        # Same hygiene as `subagent-type`: single word + optional newline
        self.assertIn(result.stdout, ("true\n", "true"))


class SliceNeedsCodeHealthReviewTests(unittest.TestCase):
    """Slice 060-05: `workflow.py code-health-review-needed` mirrors
    `arch-review-needed`, reading the slice's `code_health_review:`
    frontmatter flag and defaulting to false when absent (back-compat —
    every existing slice has no flag)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-ch-needed-"))
        self.spec = self.tmpdir / "spec.md"
        self.slice_file = self.tmpdir / "slice-05-ch.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, fm_extra: str) -> None:
        self.slice_file.write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n"
            f"{fm_extra}---\n\n## Slice 060-05 alpha\n\n**Goal:** x.\n"
        )

    def _run(self):
        return run_workflow("code-health-review-needed", str(self.spec), "060-05")

    def test_false_when_absent(self):
        self._write_slice("")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "false")

    def test_true_when_set(self):
        self._write_slice("code_health_review: true\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "true")

    def test_false_when_explicit_false(self):
        self._write_slice("code_health_review: false\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "false")

    def test_truthy_variations(self):
        for tok in ("yes", "True", "1", "on"):
            self._write_slice(f"code_health_review: {tok}\n")
            r = self._run()
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(r.stdout.strip(), "true",
                             f"{tok!r} should be truthy")


class SliceNeedsDesignReviewTests(unittest.TestCase):
    """Slice 071-01: `workflow.py design-review-needed` mirrors
    `arch-review-needed`, reading the slice's `design_review:` frontmatter
    flag and defaulting to false when absent (back-compat — every existing
    slice has no flag)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-design-needed-"))
        self.spec = self.tmpdir / "spec.md"
        self.slice_file = self.tmpdir / "slice-01-design.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, fm_extra: str) -> None:
        self.slice_file.write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n"
            f"{fm_extra}---\n\n## Slice 071-01 alpha\n\n**Goal:** x.\n"
        )

    def _run(self):
        return run_workflow("design-review-needed", str(self.spec), "071-01")

    def test_false_when_absent(self):
        self._write_slice("")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "false")

    def test_true_when_set(self):
        self._write_slice("design_review: true\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "true")

    def test_false_when_explicit_false(self):
        self._write_slice("design_review: false\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "false")

    def test_truthy_variations(self):
        for tok in ("yes", "True", "1", "on"):
            self._write_slice(f"design_review: {tok}\n")
            r = self._run()
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(r.stdout.strip(), "true",
                             f"{tok!r} should be truthy")


class SliceTemplateArchReviewHintTests(unittest.TestCase):
    """Slice 031-02 AC #1 + AC #6: the slice template at
    `templates/docs/specs/slice-template.md` ships the `arch_review:`
    field commented out with a one-line guide, so authors discover it
    organically when copying the template for a new slice."""

    def setUp(self):
        template = (REPO_ROOT / "templates" / "docs" / "specs"
                    / "slice-template.md")
        self.template = template
        self.text = template.read_text()

    def test_template_mentions_arch_review_field(self):
        # AC #1: the commented-out hint must mention the field
        self.assertIn(
            "arch_review:", self.text,
            "slice template must mention the `arch_review:` "
            "frontmatter field (031-02 AC #1)",
        )

    def test_template_has_arch_review_hint_in_frontmatter_block(self):
        # AC #1: the hint sits inside the leading frontmatter block,
        # commented out (lines start with `#`).
        m = re.match(r"---\n(.*?)\n---", self.text, re.DOTALL)
        self.assertIsNotNone(m, "slice template must start with frontmatter")
        fm = m.group(1)
        self.assertIn(
            "arch_review:", fm,
            "`arch_review:` hint must be in the leading frontmatter "
            "block (031-02 AC #1)",
        )
        # The hint must be commented out — search for `# arch_review:`
        self.assertRegex(
            fm,
            r"#\s*arch_review:",
            "the `arch_review:` hint must be commented out (031-02 AC #1: "
            "existing slices without the field are unaffected)",
        )

    def test_template_explains_when_to_set_arch_review(self):
        # AC #1: a one-line guide explains when to flip the flag.
        # Search for module/boundary/contract/architecture vocab near the hint.
        m = re.match(r"---\n(.*?)\n---", self.text, re.DOTALL)
        fm = m.group(1)
        self.assertRegex(
            fm,
            r"(?is)arch_review:.*(?:module|boundar|contract|architect)",
            "the `arch_review:` hint must explain when to set it "
            "(031-02 AC #1: module boundaries / public contracts / "
            "architecture-shaped concerns)",
        )

    # Slice 071-01: the design_review flag hint mirrors the arch_review one.
    def test_template_has_design_review_hint_in_frontmatter_block(self):
        m = re.match(r"---\n(.*?)\n---", self.text, re.DOTALL)
        self.assertIsNotNone(m, "slice template must start with frontmatter")
        fm = m.group(1)
        self.assertIn(
            "design_review:", fm,
            "`design_review:` hint must be in the leading frontmatter "
            "block (071-01)",
        )
        # The hint must be commented out — search for `# design_review:`.
        self.assertRegex(
            fm,
            r"#\s*design_review:",
            "the `design_review:` hint must be commented out (071-01: "
            "existing slices without the field are unaffected)",
        )

    def test_template_explains_when_to_set_design_review(self):
        # The one-line guide must mention the design-fidelity eval / attest.
        m = re.match(r"---\n(.*?)\n---", self.text, re.DOTALL)
        fm = m.group(1)
        self.assertRegex(
            fm,
            r"(?is)design_review:.*(?:design-fidelity|eval|attest)",
            "the `design_review:` hint must explain when to set it "
            "(071-01: UI gated by an external design-fidelity eval)",
        )


# Slice 028-03: importlib-load workflow.py as a module so tests can
# monkeypatch `_checksum` directly to inject deterministic mid-regen
# mutations. Mirrors the loader pattern slice 028-02 added for memory.py.
def _import_workflow_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_workflow_under_test", WORKFLOW,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StatusBoardRaceCheckTests(unittest.TestCase):
    """Slice 028-03 — checksum-based race-detection guard on
    `workflow.py status-board`.

    ACs covered:
      - AC #1: pre-regen checksum captured (verified indirectly via
        race-detected case: if pre-checksum wasn't captured, the
        post-checksum compare couldn't detect the mutation).
      - AC #2: pre-write checksum compared; refuses on mismatch.
      - AC #3: exact refusal message + exit code 4.
      - AC #4: `--force` flag bypasses the check (CLI + Python API).
      - AC #5: tests cover all three branches (no-race / detected-race /
        forced-overwrite) + the stale-checksum false-positive edge case.
      - AC #6: regression test on Notes-column preservation.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-board-race-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)
        # Drop in a synthetic spec so the regen has something to write.
        spec1 = self.target / "docs/specs/200-race-check"
        spec1.mkdir(parents=True)
        write_synthetic_spec(spec1 / "spec.md", [
            ("200-01 first", "DONE"),
            ("200-02 second", "IN_PROGRESS"),
        ])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #5 branch 1: no-race (default behavior). Existing tests in
    # StatusBoardTests already cover this thoroughly; one regression-pin
    # here so a future refactor that breaks the no-race path fails
    # alongside the slice-028-03 tests.
    def test_no_race_default_behavior_unchanged(self):
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(
            result.returncode, 0,
            f"no-race regen must succeed; stderr: {result.stderr}",
        )
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("200-01 first", board)
        self.assertIn("200-02 second", board)

    # AC #2 + AC #3 + AC #5 branch 2: race detected → refusal raised.
    def test_race_detected_raises_status_board_race_error(self):
        wf = _import_workflow_module()
        # Establish baseline so the regen has new content to write
        # (otherwise the idempotent fast path skips the race check
        # entirely — that's intentional per Design decision #3).
        run_workflow("status-board", str(self.target))
        # Mutate one of the slices so the next regen has real new content.
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Patch _checksum to return different values on the two calls
        # (pre-regen vs pre-write) — simulates a concurrent writer
        # mutating the board between the two reads.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre-regen", "sha-mid-regen-different"],
        ):
            with self.assertRaises(wf.StatusBoardRaceError) as cm:
                wf.regenerate_status_board(self.target)
        # AC #3: exact refusal message. Match character-for-character so
        # future auditors can grep for it.
        self.assertEqual(
            str(cm.exception),
            "status board changed during regen — another writer may "
            "have run. Re-run `workflow.py status-board` to retry.",
        )

    # AC #3: CLI exits 4 (not 2) when a race is detected.
    def test_cli_exits_4_on_race(self):
        wf = _import_workflow_module()
        # Set up so the regen would write something.
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Patch checksum on the loaded module via a wrapper subprocess.
        # Simpler approach: use the Python API directly via the module
        # path, since the CLI subprocess can't easily share a mock.
        # Invoke main() directly so the exception → exit-code mapping is
        # exercised in-process.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre", "sha-post"],
        ):
            rc = wf.main(
                ["workflow.py", "status-board", str(self.target)],
            )
        self.assertEqual(rc, 4,
                         "race detection must surface as exit code 4")

    # AC #4 + AC #5 branch 3: forced-overwrite bypasses the guard.
    # Python API path: pass `force=True`.
    def test_force_python_api_bypasses_race_check(self):
        wf = _import_workflow_module()
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Patch _checksum to a divergent side_effect — but with force=True
        # the guard should be skipped entirely (no checksum call at all,
        # so the side_effect is irrelevant).
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre-WOULD-be-race", "sha-post-WOULD-be-race"],
        ):
            # Should not raise; write proceeds despite checksum mismatch
            # because force=True turns off the guard.
            summary = wf.regenerate_status_board(self.target, force=True)
        self.assertIn("regenerated status board", summary)
        # Confirm the write actually happened (REVIEWED status landed).
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("REVIEWED", board)

    # AC #4: `--force` CLI flag works (matches Python API).
    def test_force_cli_flag_bypasses_race_check(self):
        wf = _import_workflow_module()
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre", "sha-post-diverged"],
        ):
            rc = wf.main(
                ["workflow.py", "status-board", str(self.target), "--force"],
            )
        self.assertEqual(rc, 0, "force flag must bypass the guard and exit 0")
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("REVIEWED", board)

    # AC #5 edge case: stale-checksum false-positive. If the file is
    # rewritten with identical content (SHA256 stays the same), the
    # content-based check correctly treats it as "no race" and the write
    # proceeds. Documented in deviation log; this test pins the behavior.
    def test_identical_content_rewrite_does_not_trigger_race(self):
        wf = _import_workflow_module()
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Same checksum on both calls — simulates a concurrent writer
        # rewriting with identical content. Should NOT raise.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-same", "sha-same"],
        ):
            summary = wf.regenerate_status_board(self.target)
        self.assertIn("regenerated status board", summary)

    # AC #1 / AC #5 idempotent-fast-path: when the regen produces no new
    # content (new == existing), the write is skipped and the race check
    # is unreachable. This pins that no false-positive race is reported
    # on the idempotent path.
    def test_idempotent_fast_path_does_not_trigger_race(self):
        wf = _import_workflow_module()
        # First regen establishes the baseline.
        run_workflow("status-board", str(self.target))
        # Second regen with the same spec state — new_content == existing,
        # so the function returns "already current" before reaching the
        # race-check / write code. Patch _checksum with divergent values:
        # if the race-check code ran on the fast path (it shouldn't), the
        # divergent side_effect would raise.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre", "sha-DIVERGENT-would-race"],
        ):
            summary = wf.regenerate_status_board(self.target)
        self.assertEqual(summary, "status board already current; no changes")

    # Craft-pass coverage gap: --force + idempotent state should still
    # respect the fast path (return "already current") rather than writing
    # unconditionally. Pins the behavior against a future refactor that
    # might move the fast-path below the race-check block.
    def test_force_respects_idempotent_fast_path(self):
        wf = _import_workflow_module()
        # First regen establishes the baseline.
        run_workflow("status-board", str(self.target))
        # Second regen with `force=True` — no content change, so the
        # function must still short-circuit on the fast path.
        summary = wf.regenerate_status_board(self.target, force=True)
        self.assertEqual(summary, "status board already current; no changes")

    # AC #6: regression — Notes column preservation must still work.
    def test_notes_column_preserved_across_regen(self):
        # First regen to establish baseline table
        run_workflow("status-board", str(self.target))
        board_path = self.target / "docs/specs/README.md"
        content = board_path.read_text()
        # Hand-edit a Note cell for one slice
        new_content = content.replace(
            "| 200-01 first | **DONE** |  |",
            "| 200-01 first | **DONE** | curated note that must survive |",
        )
        self.assertNotEqual(new_content, content,
                            "test setup failed: edit was a no-op")
        board_path.write_text(new_content)
        # Mutate a spec so the second regen has new content (so the
        # actual write path runs, exercising the race check + Notes
        # preservation together).
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0,
                         f"regen failed: {result.stderr}")
        regenerated = board_path.read_text()
        self.assertIn("curated note that must survive", regenerated)


class ReserveSpecAgainstOriginTests(unittest.TestCase):
    """Spec 037-02: `reserve_spec` reads `origin/main` in push mode and
    refuses on diverged local main. Mirrors slice 037-01's tuple-key
    behavior dispatcher (see `test_land.py:1750-1787`).

    `_next_spec_number` and `_current_branch` / `_refuse_if_dirty` (and
    `reserve_spec`'s post-fetch diverged-main check) all call
    `subprocess.run` via the module-level `_run`. We patch the module's
    `subprocess` so the recorder intercepts every call.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-037-02-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        (self.target / "docs" / "specs").mkdir(parents=True)
        # Spec 063-01: scaffold.json sentinel → `reserve_spec` classifies as
        # `scaffolded` and proceeds to the legacy origin-aware reserve flow.
        (self.target / "scaffold.json").write_text("{}\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mkspec(self, name: str) -> None:
        d = self.target / "docs" / "specs" / name
        d.mkdir(parents=True)
        (d / "spec.md").write_text("# Spec\n")

    def _patched_run(self, behavior):
        """Return a fake `subprocess.run` that consults `behavior`.

        `behavior` is a dict mapping a tuple key (the command's
        identifying suffix) to either a `_make_proc(...)` result OR a
        callable returning one. Mirrors the dispatcher in
        `test_land.py:1750-1787`.

        Tuple keys recognized:
          ("symbolic-ref",)             -> git symbolic-ref --short HEAD
          ("status",)                   -> git status --porcelain
          ("origin-url",)               -> git config --get remote.origin.url
          ("fetch",)                    -> git fetch origin main
          ("ls-tree",)                  -> git ls-tree --name-only origin/main docs/specs/
          ("verify", "origin/main")     -> git rev-parse --verify origin/main
          ("verify", "main")            -> git rev-parse --verify main
          ("ancestor", "main", "origin/main") -> git merge-base --is-ancestor main origin/main
          ("rev-parse", "main")         -> git rev-parse main (SHA print)
          ("add",)                      -> git add
          ("commit",)                   -> git commit
          ("push-main",)                -> git push origin main
          ("reset-head1",)              -> git reset --hard HEAD~1
          ("branch",)                   -> git branch
          ("checkout",)                 -> git checkout
          ("push-u",)                   -> git push -u origin <branch>
          ("reset-origin",)             -> git reset --hard origin/main
          ("gh-pr",)                    -> gh pr create
        """
        calls = []

        def fake_run(*args, **kwargs):
            argv = args[0] if args else kwargs.get("args")
            if isinstance(argv, str):
                argv_list = argv.split()
            else:
                argv_list = list(argv)
            calls.append(argv_list)

            # Identify by suffix/role
            if argv_list[:1] == ["gh"] and "pr" in argv_list:
                key = ("gh-pr",)
            elif argv_list[:2] == ["git", "symbolic-ref"]:
                key = ("symbolic-ref",)
            elif argv_list[:3] == ["git", "status", "--porcelain"]:
                key = ("status",)
            elif (argv_list[:3] == ["git", "config", "--get"]
                  and "remote.origin.url" in argv_list):
                key = ("origin-url",)
            elif argv_list[:2] == ["git", "fetch"]:
                key = ("fetch",)
            elif argv_list[:2] == ["git", "ls-tree"]:
                key = ("ls-tree",)
            elif (argv_list[:3] == ["git", "rev-parse", "--verify"]):
                key = ("verify", argv_list[-1])
            elif (argv_list[:2] == ["git", "rev-parse"]
                  and "--verify" not in argv_list):
                key = ("rev-parse", argv_list[-1])
            elif (argv_list[:2] == ["git", "merge-base"]
                  and "--is-ancestor" in argv_list):
                # last two positional args are the ancestor pair
                key = ("ancestor", argv_list[-2], argv_list[-1])
            elif argv_list[:2] == ["git", "add"]:
                key = ("add",)
            elif argv_list[:2] == ["git", "commit"]:
                key = ("commit",)
            elif argv_list[:4] == ["git", "push", "origin", "main"]:
                key = ("push-main",)
            elif (argv_list[:4] == ["git", "reset", "--hard", "HEAD~1"]):
                key = ("reset-head1",)
            elif (argv_list[:4] == ["git", "reset", "--hard", "origin/main"]):
                key = ("reset-origin",)
            elif argv_list[:2] == ["git", "branch"]:
                key = ("branch",)
            elif argv_list[:2] == ["git", "checkout"]:
                key = ("checkout",)
            elif argv_list[:3] == ["git", "push", "-u"]:
                key = ("push-u",)
            else:
                key = tuple(argv_list[-2:])

            entry = behavior.get(key)
            if entry is None:
                # default success, empty output
                return _make_proc(0, "", "")
            # Guard against MagicMock-instance silent bypass: only treat
            # FunctionType/lambda/method as a dispatcher. Mirrors
            # test_land.py:1780-1786 lesson.
            import types
            if isinstance(entry, (types.FunctionType, types.LambdaType,
                                  types.MethodType)):
                return entry(argv_list, **kwargs)
            return entry

        fake_run._calls = calls
        return fake_run

    def _default_preflight_behavior(self):
        """Common stub set: on main, clean worktree, GitHub origin."""
        return {
            ("symbolic-ref",): _make_proc(0, "main\n", ""),
            ("status",): _make_proc(0, "", ""),
            ("origin-url",): _make_proc(
                0, "git@github.com:user/repo.git\n", ""),
            ("fetch",): _make_proc(0, "", ""),
            ("add",): _make_proc(0, "", ""),
            ("commit",): _make_proc(0, "", ""),
            ("push-main",): _make_proc(0, "", ""),
        }

    # ----------- AC #1: push-mode scan reads `origin/main` -----------

    def test_push_mode_scan_reads_origin_main_not_working_tree(self):
        """AC #1 — a spec committed to origin/main but absent from the
        working tree is counted. Working tree has only 001; origin/main
        ls-tree returns 020-other, so the next number is 021."""
        from unittest.mock import patch
        self._mkspec("001-local-only")  # working tree only
        behavior = self._default_preflight_behavior()
        # origin/main has both 001 and a 020-other; verify ref present.
        behavior[("verify", "origin/main")] = _make_proc(
            0, "abc123\n", "")
        behavior[("verify", "main")] = _make_proc(0, "abc123\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "abc123\n", "")
        # ancestor: equal SHAs → in sync (not behind)
        behavior[("ancestor", "main", "origin/main")] = _make_proc(
            0, "", "")
        # ls-tree returns directory entries from origin/main
        behavior[("ls-tree",)] = _make_proc(
            0, "001-local-only\n020-other\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # 020 was the max on origin/main → reserve 021
        spec_dir = self.target / "docs" / "specs" / "021-newslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 021-newslot from origin/main scan; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # Confirm we actually called ls-tree against origin/main
        ls_tree_calls = [
            c for c in fake._calls
            if c[:2] == ["git", "ls-tree"] and "origin/main" in c
        ]
        self.assertEqual(
            len(ls_tree_calls), 1,
            f"expected 1 ls-tree origin/main call; got: {fake._calls}",
        )

    # ----------- AC #2: --no-push preserves working-tree scan -----------

    def test_no_push_keeps_working_tree_scan(self):
        """AC #2 — `--no-push` mode never calls `git ls-tree`; spec
        number derives from working-tree scan."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        self._mkspec("015-other")
        behavior = self._default_preflight_behavior()
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Working-tree max=015, so reserve 016
        spec_dir = self.target / "docs" / "specs" / "016-newslot"
        self.assertTrue(spec_dir.is_dir())
        # AC #2 absence-of-effect: no ls-tree call against origin/main
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"--no-push must not call ls-tree; got: {c}",
            )
        # And no fetch either (matches existing AC #7 no-push contract)
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "fetch"],
                f"--no-push must not fetch; got: {c}",
            )

    def test_pr_mode_is_push_mode_equivalent_for_scan(self):
        """AC #2 — `--pr` (push-mode-equivalent) scans `origin/main`."""
        import shutil as _shutil
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        behavior[("verify", "origin/main")] = _make_proc(0, "abc\n", "")
        behavior[("verify", "main")] = _make_proc(0, "abc\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "abc\n", "")
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        behavior[("ls-tree",)] = _make_proc(
            0, "001-existing\n050-large\n", "")
        # PR-mode helpers
        behavior[("branch",)] = _make_proc(0)
        behavior[("reset-origin",)] = _make_proc(0)
        behavior[("checkout",)] = _make_proc(0)
        behavior[("push-u",)] = _make_proc(0)
        behavior[("gh-pr",)] = _make_proc(
            0, "https://github.com/u/r/pull/9\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "prslot", project_dir=self.target,
                no_push=False, pr_mode=True,
            )
        self.assertEqual(code, 0)
        # Origin/main max=050 → reserve 051
        spec_dir = self.target / "docs" / "specs" / "051-prslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 051-prslot from origin/main scan; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        ls_tree_calls = [
            c for c in fake._calls
            if c[:2] == ["git", "ls-tree"] and "origin/main" in c
        ]
        self.assertEqual(len(ls_tree_calls), 1)

    # ----------- AC #3: no origin / no origin/main → silent fall-back ---

    def test_no_origin_remote_falls_back_silently(self):
        """AC #3 — no origin → working-tree scan with no warning."""
        import io
        from unittest.mock import patch
        self._mkspec("001-existing")
        self._mkspec("007-other")
        behavior = self._default_preflight_behavior()
        # origin-url lookup FAILS → silent fall-through to working tree
        behavior[("origin-url",)] = _make_proc(1, "", "")
        # Even though origin-url fails, the existing fetch step at
        # workflow.py:1271-1282 still runs (warn-and-proceed). To keep
        # this test focused on the silent local-only fall-back, treat
        # the fetch as a no-op (default rc=0).
        fake = self._patched_run(behavior)
        captured = io.StringIO()
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_workflow.sys, "stderr", captured):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "fallbackslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Working-tree max=007 → reserve 008
        spec_dir = self.target / "docs" / "specs" / "008-fallbackslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 008-fallbackslot from working-tree "
                        f"fall-back; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # AC #3: silent — no "warning:" prefix from THIS code path. The
        # fetch warning (AC #6) is a different path; we don't trigger
        # it here because fetch defaulted to rc=0.
        stderr_text = captured.getvalue()
        self.assertNotIn(
            "no origin", stderr_text.lower(),
            f"expected silent fall-back; got: {stderr_text!r}",
        )
        self.assertNotIn(
            "origin remote", stderr_text.lower(),
            f"expected silent fall-back; got: {stderr_text!r}",
        )
        # And absence-of-effect: no ls-tree against origin/main
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"no-origin path must not call ls-tree; got: {c}",
            )

    def test_no_origin_main_ref_falls_back_silently(self):
        """AC #3 — origin exists, fetch succeeds, but `rev-parse --verify
        origin/main` fails → fall back to working-tree scan, silently."""
        import io
        from unittest.mock import patch
        self._mkspec("001-existing")
        self._mkspec("003-other")
        behavior = self._default_preflight_behavior()
        # origin exists; fetch succeeds; rev-parse --verify origin/main FAILS
        behavior[("verify", "origin/main")] = _make_proc(1, "", "")
        # No ls-tree stub → if called, defaults to rc=0 stdout="" which
        # would mistakenly produce next_n=1; we assert ls-tree wasn't
        # called instead.
        fake = self._patched_run(behavior)
        captured = io.StringIO()
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_workflow.sys, "stderr", captured):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "missingref", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Working-tree max=003 → reserve 004
        spec_dir = self.target / "docs" / "specs" / "004-missingref"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 004-missingref; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # AC #3 distinguished from AC #6: this is silent (no warning).
        stderr_text = captured.getvalue()
        self.assertNotIn("origin/main", stderr_text,
                         f"expected silent fall-back; got: {stderr_text!r}")
        # Absence-of-effect: ls-tree not called
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"no-origin-main path must not call ls-tree; got: {c}",
            )

    # ----------- AC #4: preflight refuses on diverged local main -------

    def test_preflight_refuses_when_local_main_behind_origin(self):
        """AC #4 — local main strictly behind origin/main → refuse with
        a message containing 'origin/main' AND 'pull or rebase'."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        # origin/main present; local SHA != origin SHA; main is strict
        # ancestor of origin/main → behind.
        behavior[("verify", "origin/main")] = _make_proc(0, "ORIG\n", "")
        behavior[("verify", "main")] = _make_proc(0, "LOCL\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "LOCL\n", "")
        # `--is-ancestor main origin/main` returns 0 → main IS ancestor →
        # since SHAs differ, local is strictly behind.
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        # ls-tree wouldn't be reached if preflight runs after fetch +
        # before scan. The slice says preflight runs after the fetch.
        # Either order is fine for refusal; we just need the WorkflowError.
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "divergedslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        msg = str(ctx.exception)
        # AC #4: message contains both substrings
        self.assertIn("origin/main", msg,
                      f"refusal must name 'origin/main'; got: {msg!r}")
        self.assertTrue(
            "pull or rebase" in msg.lower(),
            f"refusal must hint 'pull or rebase'; got: {msg!r}",
        )
        # AC #4 + close-out invariant: no spec dir was created
        self.assertFalse(
            any((self.target / "docs/specs").glob("*-divergedslot")),
            "refusal must happen BEFORE any spec dir mutation",
        )

    def test_preflight_allows_when_local_equals_origin(self):
        """AC #4 negative — when local main == origin/main (same SHA),
        no refusal: reservation proceeds. Distinguishes equality from
        behind."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        # Same SHA — caller should NOT refuse even though `--is-ancestor`
        # also returns 0 for equal commits.
        behavior[("verify", "origin/main")] = _make_proc(0, "SAME\n", "")
        behavior[("verify", "main")] = _make_proc(0, "SAME\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "SAME\n", "")
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "syncedslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Origin/main max=001 → reserve 002
        spec_dir = self.target / "docs" / "specs" / "002-syncedslot"
        self.assertTrue(spec_dir.is_dir())

    def test_preflight_allows_when_local_ahead_of_origin(self):
        """AC #4 negative — when local main is ahead of origin/main
        (unpushed commits), don't refuse on the diverged-main check.
        The push step's race classifier handles any actual conflict."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        behavior[("verify", "origin/main")] = _make_proc(0, "OLDR\n", "")
        behavior[("verify", "main")] = _make_proc(0, "NEWR\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "NEWR\n", "")
        # main is NOT ancestor of origin/main (rc=1) → local is ahead
        behavior[("ancestor", "main", "origin/main")] = _make_proc(1)
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "aheadslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        spec_dir = self.target / "docs" / "specs" / "002-aheadslot"
        self.assertTrue(spec_dir.is_dir())

    # ----------- AC #5: shared exit code ------------------------------

    def test_diverged_refusal_exits_2_through_main(self):
        """AC #5 — `WorkflowError` routes through main() to exit 2, the
        same code as today's dirty/off-main refusals. Smoke check at the
        process boundary (not just at the helper level)."""
        # Build a minimal scaffolded layout in tmp and run the CLI with
        # PYTHONPATH set so our patched module can be imported. Rather
        # than spawning git for real, we just check exit-code semantics:
        # WorkflowError → exit 2 is established by 003-03. The
        # diverged-main refusal MUST go through the same path.
        # We assert structurally: the new helper raises WorkflowError
        # (already covered by `test_preflight_refuses_when_local_main_
        # behind_origin`); here we additionally check that `main()`'s
        # WorkflowError handler still maps to exit 2 — i.e. no new
        # exit-code class was added.
        # Simplest assertion: pass a slug that fails preflight (off-main)
        # via the actual CLI and confirm exit 2 — proving the shared
        # path still works. Then assert via inspection that the new
        # diverged path raises WorkflowError (not some new exception
        # type).
        # AC #5 part A: WorkflowError → exit 2 via main() is intact.
        result = run_workflow(
            "new", "valid-slug",
            "--project-dir", str(self.target),
            "--no-push",
        )
        # This run will fail preflight (no git init in tmpdir →
        # symbolic-ref fails). Exit code 2 confirms the WorkflowError
        # → exit 2 contract.
        self.assertEqual(
            result.returncode, 2,
            f"WorkflowError must exit 2; got rc={result.returncode}, "
            f"stderr={result.stderr!r}",
        )
        # AC #5 part B: structural — the new diverged-main helper raises
        # the SAME exception class. We verify by introspection.
        self.assertTrue(
            issubclass(_workflow.WorkflowError, Exception),
            "new refusal path must use the existing WorkflowError class",
        )

    # ----------- AC #6: fetch failure preserves warn-and-proceed ------

    def test_fetch_failure_preserves_warn_and_proceed(self):
        """AC #6 — `git fetch origin main` fails → existing warning to
        stderr (workflow.py:1278-1282) is emitted verbatim; the new
        diverged-main check is skipped (no origin/main to compare); the
        scan falls back to working-tree per AC #3."""
        import io
        from unittest.mock import patch
        self._mkspec("001-existing")
        self._mkspec("004-other")
        behavior = self._default_preflight_behavior()
        # fetch FAILS
        behavior[("fetch",)] = _make_proc(
            1, "", "fatal: unable to access: network down")
        # Because fetch failed, origin/main may be stale or absent.
        # Even if a previous fetch left it present, the new check must
        # be guarded; here we simulate "no ref" so the diverged check
        # has nothing to compare and the scan falls back.
        behavior[("verify", "origin/main")] = _make_proc(1, "", "")
        fake = self._patched_run(behavior)
        captured = io.StringIO()
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_workflow.sys, "stderr", captured):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "warnslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # AC #6: existing warn-and-proceed text preserved
        stderr_text = captured.getvalue()
        self.assertIn("warning:", stderr_text)
        self.assertIn("git fetch origin main", stderr_text)
        self.assertIn("proceeding with local view", stderr_text)
        # AC #6: scan fell back to working-tree (max=004 → 005)
        spec_dir = self.target / "docs" / "specs" / "005-warnslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 005-warnslot via working-tree fallback; "
                        f"got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # AC #6 absence-of-effect: ls-tree not called (no origin/main)
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"fetch-failed path must not call ls-tree; got: {c}",
            )

    # ----------- AC #7: race classifier path still reachable ----------

    def test_race_classifier_path_still_reachable(self):
        """AC #7 — `_classify_push_failure` and the on-push race-recovery
        path (workflow.py:1352-1374) remain wired. Simulate a race-on-
        push (non-fast-forward) and confirm the classifier's race branch
        fires and the recovery path runs (reset HEAD~1 + spec-dir
        cleanup)."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        # origin/main present, in sync — preflight passes.
        behavior[("verify", "origin/main")] = _make_proc(0, "X\n", "")
        behavior[("verify", "main")] = _make_proc(0, "X\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "X\n", "")
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        # push fails with race signal
        behavior[("push-main",)] = _make_proc(
            1, "", "! [rejected] main -> main (non-fast-forward)\n")
        behavior[("reset-head1",)] = _make_proc(0)
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "raceslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        # AC #7: classifier surfaced 'race-on-push'
        self.assertIn("race-on-push", str(ctx.exception))
        # AC #7 absence-of-effect: recovery ran reset --hard HEAD~1
        reset_calls = [
            c for c in fake._calls
            if c[:4] == ["git", "reset", "--hard", "HEAD~1"]
        ]
        self.assertEqual(
            len(reset_calls), 1,
            f"race-recovery must reset HEAD~1; got: {fake._calls}",
        )
        # AC #7: classifier helper still importable + behaves
        self.assertEqual(
            _workflow._classify_push_failure(
                "! [rejected] main -> main (non-fast-forward)"),
            "race",
        )
        self.assertEqual(
            _workflow._classify_push_failure(
                "remote: error: GH006: Protected branch update failed."),
            "protection",
        )

    # ----------- AC #8: stale comment at workflow.py:1269 updated -----

    def test_stale_comment_at_fetch_step_updated(self):
        """AC #8 — the comment at the fetch step is rewritten to reflect
        both effects (the scan AND the divergence preflight consult
        origin/main). We assert the new prose is present and the old
        misleading line is gone."""
        text = Path(_workflow.__file__).read_text()
        # The old single-purpose phrasing must be removed
        self.assertNotIn(
            "so the next-number scan reflects the freshest state",
            text,
            "stale single-purpose fetch comment must be replaced",
        )
        # The new phrasing must mention BOTH effects: the scan AND
        # the divergence preflight reading from origin/main.
        # We accept a few wordings; the load-bearing bits are
        # "next-number scan" and "divergence preflight" (or
        # synonyms like "diverged-main" / "preflight").
        self.assertIn("next-number scan", text)
        self.assertTrue(
            ("divergence preflight" in text
             or "diverged-main" in text
             or "diverged preflight" in text),
            "fetch comment must name the divergence preflight effect "
            "alongside the next-number scan",
        )


# ===========================================================================
# Slice 045-03: lifecycle-transition-gates.
#
# `workflow.py transition` refuses REVIEWED / RECONCILED / DONE moves
# unless the review evidence required by ADR-0014 §5 exists and clears.
# These tests run the gate ON (gate=True → JIG_REVIEW_EVIDENCE_GATE unset)
# and build evidence fixtures as `reviews/slice-NN-<pass>.md` files in a
# temp spec dir, mirroring the 045-02 recorder layout.
# ===========================================================================


class SliceClaimTests(unittest.TestCase):
    """Slice 049-01: claim-and-release on the IN_PROGRESS transition.

    `transition <slice> IN_PROGRESS` stamps a `claimed_by:` identifier
    and refuses a foreign on-disk claim; `push`/`pr_mode` additionally
    reserve the claim on origin/main (mocked here — no real push). The
    claim is cleared on REVIEWED / back-transitions, and `--release`
    force-clears with an audit reason. Off-network (default) behaviors
    call `transition()` directly; the reserve paths use the
    `_SubprocessRecorder` git mock (same pattern as ReserveSpecTests)."""

    REL = "docs/specs/200-demo/slice-01-demo.md"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-claim-")
        self.root = Path(self.tmpdir)
        self.spec_dir = self.root / "docs" / "specs" / "200-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 200\n\n## Overview\n\nx\n"
        )
        self.slice = self.spec_dir / "slice-01-demo.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, status="READY_FOR_IMPLEMENTATION",
                     claimed_by=None, extra=""):
        fm = f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n"
        if claimed_by:
            fm += f"claimed_by: {claimed_by}\n"
        fm += ("---\n\n## Slice 200-01 — demo\n\n"
               "**Goal:** placeholder.\n\n**DoD:**\n- [ ] placeholder.\n")
        self.slice.write_text(fm + extra)

    def _fm(self):
        fields, _ = _workflow.parse_frontmatter(self.slice.read_text())
        return fields

    # ---- AC1: stamp claimed_by ----------------------------------------

    def test_in_progress_stamps_claimed_by_from_env(self):
        """JIG_CLAIM_ID override is stamped verbatim (no human-identity
        inference — spec 049 non-goal)."""
        self._write_slice()
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-alpha"}):
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        fm = self._fm()
        self.assertEqual(fm["status"], "IN_PROGRESS")
        self.assertEqual(fm.get("claimed_by"), "wt-alpha")

    def test_in_progress_stamps_branch_name_when_no_env(self):
        """Absent JIG_CLAIM_ID, the current branch name is used."""
        self._write_slice()
        from unittest.mock import patch
        env = {k: v for k, v in os.environ.items() if k != "JIG_CLAIM_ID"}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(_workflow, "_current_branch",
                          return_value="feature/x"):
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        self.assertEqual(self._fm().get("claimed_by"), "feature/x")

    def test_default_claim_touches_no_network(self):
        """The default (local) claim performs no git fetch / push /
        worktree calls — preserves the offline 'start a slice' UX."""
        self._write_slice()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git fetch", flat)
        self.assertNotIn("git push", flat)
        self.assertNotIn("git worktree", flat)
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    def test_project_root_for_spec_is_depth_safe(self):
        """Regression (CI, PR #35): the claim path derived the project root
        via a bare `spec_md.resolve().parents[3]`, which raises
        `IndexError(3)` on a shallow path — CI's `/tmp/jig-x/spec.md` has
        only three parents, so every frontmatter→IN_PROGRESS transition
        crashed (`workflow.py failed: 3`). It passed locally only because
        macOS tmp resolves to a deeper `/private/tmp/...`. The depth-safe
        helper must return `parents[3]` for a real nested spec path and
        fall back (never raise) for a shallow one."""
        nested = Path("/proj/docs/specs/049-x/spec.md")
        self.assertEqual(_workflow._project_root_for_spec(nested).name,
                         "proj")
        shallow = Path("/x/spec.md")  # two parents → must fall back, not crash
        self.assertIsInstance(_workflow._project_root_for_spec(shallow), Path)

    # ---- AC3: collision refusal ---------------------------------------

    def test_collision_refuses_foreign_in_progress_claim(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-other")
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}):
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        msg = str(ctx.exception)
        self.assertIn("wt-other", msg)
        self.assertIn("--release", msg)
        # The on-disk claim is untouched by the refusal.
        self.assertEqual(self._fm().get("claimed_by"), "wt-other")

    def test_reclaim_by_same_owner_is_idempotent(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-me")
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}):
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    def test_claim_overrides_stale_foreign_claim_when_not_in_progress(self):
        """AC3 refuses only when the foreign claim is ALSO IN_PROGRESS.
        A leftover claimed_by on a non-IN_PROGRESS slice is overwritten."""
        self._write_slice(status="READY_FOR_IMPLEMENTATION",
                          claimed_by="wt-other")
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}):
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    # ---- AC4: claim cleared on forward / back transition --------------

    def test_claim_cleared_on_reviewed(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-me")
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_REVIEW_EVIDENCE_GATE": "0"}):
            _workflow.transition(self.spec, "200-01", "REVIEWED")
        self.assertNotIn("claimed_by", self._fm())

    def test_claim_cleared_on_back_to_ready(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-me")
        _workflow.transition(self.spec, "200-01", "READY_FOR_IMPLEMENTATION")
        self.assertNotIn("claimed_by", self._fm())

    def test_claim_cleared_on_back_to_draft(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-me")
        _workflow.transition(self.spec, "200-01", "DRAFT")
        self.assertNotIn("claimed_by", self._fm())

    # ---- AC5: --release ------------------------------------------------

    def test_release_without_reason_refuses(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-me")
        with self.assertRaises(_workflow.WorkflowError) as ctx:
            _workflow.transition(self.spec, "200-01",
                                 "READY_FOR_IMPLEMENTATION", release=True)
        self.assertIn("--reason", str(ctx.exception))

    def test_release_clears_claim_and_logs_reason(self):
        self._write_slice(status="IN_PROGRESS", claimed_by="wt-other")
        _workflow.transition(self.spec, "200-01", "READY_FOR_IMPLEMENTATION",
                             release=True, reason="original worktree abandoned")
        text = self.slice.read_text()
        fm = self._fm()
        self.assertNotIn("claimed_by", fm)
        self.assertEqual(fm["status"], "READY_FOR_IMPLEMENTATION")
        self.assertIn("## Release log", text)
        self.assertIn("original worktree abandoned", text)
        self.assertIn("wt-other", text)

    def test_release_on_prose_slice_refuses(self):
        """Claims require a frontmatter slice; --release on a legacy
        prose-only slice is refused rather than synthesizing a block."""
        prose = self.spec_dir / "spec.md"
        prose.write_text(
            "# Spec 200\n\n## Slice 200-09 — legacy\n\n"
            "**STATUS: IN_PROGRESS**\n"
        )
        with self.assertRaises(_workflow.WorkflowError) as ctx:
            _workflow.transition(prose, "200-09",
                                 "READY_FOR_IMPLEMENTATION",
                                 release=True, reason="x")
        self.assertIn("frontmatter", str(ctx.exception).lower())

    # ---- AC2 / AC7: reserve-on-main (mocked subprocess) ---------------

    def _push_recorder(self, origin_content, sha="abc123",
                       push_rc=0, push_stderr=""):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "show"), returncode=0, stdout=origin_content)
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout=f"{sha}\n")
        if push_rc != 0:
            rec.stub(_matches("git", "push", "origin"),
                     returncode=push_rc, stderr=push_stderr)
        return rec

    def _assert_claim_branch_ref_valid(self, rec):
        """The PR-fallback pushes `<sha>:refs/heads/claim/<branch>`; the
        slice label has spaces / an em-dash, so the branch must be slugged
        into a valid git ref. Catch a raw-label regression."""
        import re as _re
        refs = [tok.split(":", 1)[1]
                for call in rec.calls if call[:2] == ["git", "push"]
                for tok in call if ":refs/heads/claim/" in tok]
        self.assertTrue(refs, "no claim/ ref was pushed")
        for ref in refs:
            self.assertNotRegex(ref, r"\s",
                                f"claim branch ref has whitespace: {ref!r}")
            self.assertTrue(_re.fullmatch(r"refs/heads/claim/[A-Za-z0-9._/-]+",
                                          ref),
                            f"invalid git ref name: {ref!r}")

    def test_push_reserves_claim_on_origin_main(self):
        self._write_slice()
        origin = self.slice.read_text()  # READY_FOR_IMPLEMENTATION, unclaimed
        rec = self._push_recorder(origin)
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS", push=True)
        flat = " | ".join(rec.argv_log())
        # AC7: fetch → show(origin/main) → detached worktree → commit →
        # push BY SHA → teardown, in that order.
        self.assertIn("git fetch origin main", flat)
        self.assertIn(f"git show origin/main:{self.REL}", flat)
        self.assertIn("git worktree add --detach", flat)
        self.assertIn("git commit", flat)
        self.assertIn("git push origin abc123:refs/heads/main", flat)
        self.assertIn("git worktree remove --force", flat)
        # Caller's branch is never checked out / reset.
        self.assertNotIn("git checkout main", flat)
        self.assertNotIn("git reset --hard", flat)
        # Local slice file also reflects the claim.
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    def test_push_origin_collision_refuses(self):
        """The origin/main copy is already claimed IN_PROGRESS by another
        worktree → refuse before creating any worktree or pushing."""
        self._write_slice()
        origin = ("---\nstatus: IN_PROGRESS\ndependencies: []\n"
                  "last_verified:\nclaimed_by: wt-other\n---\n\n"
                  "## Slice 200-01 — demo\n")
        rec = self._push_recorder(origin)
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.transition(self.spec, "200-01", "IN_PROGRESS",
                                     push=True)
        self.assertIn("wt-other", str(ctx.exception))
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git worktree add", flat)
        self.assertNotIn("git push", flat)

    def test_push_race_refuses_and_leaves_local_untouched(self):
        self._write_slice()
        original = self.slice.read_text()
        rec = self._push_recorder(
            original, push_rc=1,
            push_stderr="! [rejected] main -> main (non-fast-forward)\n")
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.transition(self.spec, "200-01", "IN_PROGRESS",
                                     push=True)
        self.assertIn("race", str(ctx.exception).lower())
        flat = " | ".join(rec.argv_log())
        self.assertIn("git worktree remove --force", flat)
        # Reserve runs BEFORE the local write → caller's file untouched.
        self.assertEqual(self.slice.read_text(), original)

    def test_push_protection_falls_back_to_pr(self):
        self._write_slice()
        origin = self.slice.read_text()
        rec = self._push_recorder(
            origin, push_rc=1,
            push_stderr="remote: error: GH006: Protected branch update failed.\n")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/9\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp.run = rec
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS", push=True)
        flat = " | ".join(rec.argv_log())
        self.assertIn(":refs/heads/claim/", flat)
        self.assertIn("gh pr create", flat)
        self.assertIn("git worktree remove --force", flat)
        self._assert_claim_branch_ref_valid(rec)

    def test_pr_mode_implies_push_via_pr(self):
        """--pr reserves on origin/main via a PR even without --push,
        and never attempts a direct push to main."""
        self._write_slice()
        origin = self.slice.read_text()
        rec = self._push_recorder(origin)
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/9\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp.run = rec
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS",
                                 pr_mode=True)
        flat = " | ".join(rec.argv_log())
        self.assertIn(":refs/heads/claim/", flat)
        self.assertIn("gh pr create", flat)
        self.assertNotIn("abc123:refs/heads/main", flat)
        self._assert_claim_branch_ref_valid(rec)

    def test_push_unreachable_origin_refuses(self):
        """Opting into --push with an unreachable origin refuses (and
        points at the local-only default)."""
        self._write_slice()
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "fetch", "origin", "main"),
                 returncode=1, stderr="fatal: unable to access origin\n")
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.transition(self.spec, "200-01", "IN_PROGRESS",
                                     push=True)
        self.assertIn("unreachable", str(ctx.exception).lower())


class StartCollisionGuardTests(unittest.TestCase):
    """Slice 051-04: → IN_PROGRESS consults the authoritative origin/main copy
    and hard-blocks a start-time collision — the slice already DONE (duplicate
    landed work) or IN_PROGRESS under a foreign claim on origin/main. Soft on
    reachability (offline degrades to proceed). The transition-level guard runs
    on the DEFAULT (local) path; --push/--pr delegate to _reserve_claim_on_main
    (which grew the AC6 DONE refusal)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-startcol-")
        self.root = Path(self.tmpdir)
        self.spec_dir = self.root / "docs" / "specs" / "200-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 200\n\n## Overview\n\nx\n")
        self.rel = "docs/specs/200-demo/slice-01-demo.md"
        self.slice = self.spec_dir / "slice-01-demo.md"
        self._write_slice()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, status="READY_FOR_IMPLEMENTATION"):
        self.slice.write_text(
            f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 200-01 — demo\n\n**Goal:** placeholder.\n\n"
            "**DoD:**\n- [ ] placeholder.\n")

    def _fm(self):
        fields, _ = _workflow.parse_frontmatter(self.slice.read_text())
        return fields

    def _transition(self, **kw):
        return _workflow.transition(self.spec, "200-01", "IN_PROGRESS", **kw)

    # ---- AC2: DONE on origin/main hard-blocks ------------------------------

    def test_blocks_when_slice_done_on_origin(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("present", ("DONE", ""))):
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                self._transition()
        msg = str(ctx.exception)
        self.assertIn("DONE on origin/main", msg)
        self.assertIn("duplicate", msg.lower())
        # A refusal leaves the local file untouched (no status flip, no claim).
        self.assertEqual(self._fm()["status"], "READY_FOR_IMPLEMENTATION")
        self.assertNotIn("claimed_by", self._fm())

    def test_done_block_wins_over_stale_foreign_claim(self):
        """Edge case: origin copy is DONE but still carries a stale claim —
        the clearer DONE message must win."""
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("present", ("DONE", "wt-other"))):
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                self._transition()
        self.assertIn("DONE on origin/main", str(ctx.exception))

    # ---- AC3: foreign IN_PROGRESS on origin/main hard-blocks ---------------

    def test_blocks_when_foreign_claim_on_origin(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("present", ("IN_PROGRESS", "wt-other"))):
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                self._transition()
        msg = str(ctx.exception)
        self.assertIn("wt-other", msg)
        self.assertIn("--release", msg)
        self.assertEqual(self._fm()["status"], "READY_FOR_IMPLEMENTATION")

    # ---- AC4: no false block on normal cases -------------------------------

    def test_proceeds_when_absent_on_origin(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("absent", "")):
            self._transition()
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    def test_proceeds_when_origin_draft(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("present", ("DRAFT", ""))):
            self._transition()
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")

    def test_proceeds_on_idempotent_same_owner_in_progress(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("present", ("IN_PROGRESS", "wt-me"))):
            self._transition()
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    # ---- AC5: offline-degrade ----------------------------------------------

    def test_warns_and_proceeds_on_fetch_failure(self):
        import io
        from unittest.mock import patch
        cap = io.StringIO()
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("fetch-failed", "unable to access")), \
             patch.object(_workflow.sys, "stderr", cap):
            self._transition()
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")
        self.assertIn("start-collision check skipped", cap.getvalue())
        self.assertIn("unable to access", cap.getvalue())

    def test_silent_proceed_on_no_origin(self):
        import io
        from unittest.mock import patch
        cap = io.StringIO()
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state",
                          return_value=("no-origin", "")), \
             patch.object(_workflow.sys, "stderr", cap):
            self._transition()
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")
        self.assertNotIn("start-collision", cap.getvalue())

    # ---- AC8: explicit, audited bypass -------------------------------------

    def test_bypass_skips_origin_read_and_proceeds(self):
        from unittest.mock import patch

        def _boom(*a, **k):
            raise AssertionError("origin read must not run when bypassed")

        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me",
                                     "JIG_START_COLLISION_GATE": "0"}), \
             patch.object(_workflow, "_origin_slice_state", _boom):
            self._transition()
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")

    # ---- AC1: the guard fetches + reads the origin/main copy ---------------

    def test_origin_slice_state_reads_origin_via_git(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "fetch", "origin", "main"), returncode=0)
        rec.stub(_matches("git", "show"), returncode=0,
                 stdout=("---\nstatus: DONE\ndependencies: []\n---\n\n"
                         "## Slice 200-01 — demo\n"))
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            kind, payload = _workflow._origin_slice_state(self.root, self.rel)
        self.assertEqual(kind, "present")
        self.assertEqual(payload, ("DONE", ""))
        flat = " | ".join(rec.argv_log())
        self.assertIn("git fetch origin main", flat)
        self.assertIn(f"git show origin/main:{self.rel}", flat)

    def test_origin_slice_state_absent_when_show_fails(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "fetch", "origin", "main"), returncode=0)
        rec.stub(_matches("git", "show"), returncode=128,
                 stderr="fatal: path does not exist in 'origin/main'\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            kind, _payload = _workflow._origin_slice_state(self.root, self.rel)
        self.assertEqual(kind, "absent")

    def test_origin_slice_state_no_origin_short_circuits(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=1, stderr="")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            kind, _payload = _workflow._origin_slice_state(self.root, self.rel)
        self.assertEqual(kind, "no-origin")
        # No fetch attempted when there is no origin remote.
        self.assertNotIn("git fetch", " | ".join(rec.argv_log()))

    def test_origin_slice_state_fetch_failed(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "fetch", "origin", "main"),
                 returncode=1, stderr="fatal: unable to access origin\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            kind, payload = _workflow._origin_slice_state(self.root, self.rel)
        self.assertEqual(kind, "fetch-failed")
        self.assertIn("unable to access", payload)
        # git show is never attempted once the fetch fails.
        self.assertNotIn("git show", " | ".join(rec.argv_log()))

    def test_origin_slice_state_unreadable_when_no_status(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "fetch", "origin", "main"), returncode=0)
        # present on origin/main, but the frontmatter carries no `status:`.
        rec.stub(_matches("git", "show"), returncode=0,
                 stdout="---\ndependencies: []\n---\n\n## Slice 200-01 — demo\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            kind, payload = _workflow._origin_slice_state(self.root, self.rel)
        self.assertEqual(kind, "unreadable")
        self.assertIn("no parseable status", payload)

    # ---- AC6: _reserve_claim_on_main refuses a DONE origin copy ------------

    def test_reserve_claim_refuses_done_origin(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "fetch", "origin", "main"), returncode=0)
        rec.stub(_matches("git", "show"), returncode=0,
                 stdout=("---\nstatus: DONE\ndependencies: []\n---\n\n"
                         "## Slice 200-01 — demo\n"))
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow._reserve_claim_on_main(
                    self.root, self.rel, "wt-me", "200-01")
        self.assertIn("DONE on origin/main", str(ctx.exception))
        flat = " | ".join(rec.argv_log())
        # Refuses BEFORE building any worktree / commit / push.
        self.assertNotIn("git worktree add", flat)
        self.assertNotIn("git push", flat)

    # ---- AC7: prose-only slice takes no remote read ------------------------

    def test_prose_only_slice_no_remote_read(self):
        prose = self.spec_dir / "spec.md"
        prose.write_text(
            "# Spec 200\n\n## Slice 200-09 — legacy\n\n"
            "**STATUS: READY_FOR_IMPLEMENTATION**\n")
        from unittest.mock import patch

        def _boom(*a, **k):
            raise AssertionError("no origin read for a prose-only slice")

        with patch.object(_workflow, "_origin_slice_state", _boom):
            _workflow.transition(prose, "200-09", "IN_PROGRESS")

    # ---- push path delegates to reserve (no double origin read) ------------

    def test_push_path_does_not_run_transition_guard(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "show"), returncode=0,
                 stdout=self.slice.read_text())
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="abc\n")
        from unittest.mock import patch

        def _boom(*a, **k):
            raise AssertionError("transition guard must not run on push path")

        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}), \
             patch.object(_workflow, "_origin_slice_state", _boom), \
             patch.object(_workflow, "subprocess") as sp:
            sp.run = rec
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS", push=True)
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")

    # ---- AC8: bypass leaves a content-free audit event ---------------------

    def test_bypass_emits_start_collision_telemetry(self):
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["JIG_CLAIM_ID"] = "wt-me"
        env["JIG_START_COLLISION_GATE"] = "0"
        r = subprocess.run(
            [sys.executable, str(WORKFLOW), "transition", str(self.spec),
             "200-01", "IN_PROGRESS"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        log = self.root / ".claude" / "skill-usage.jsonl"
        import json as _json
        events = ([_json.loads(x) for x in log.read_text().splitlines()
                   if x.strip()] if log.is_file() else [])
        start = [e for e in events if e.get("gate") == "start-collision"]
        self.assertEqual(len(start), 1, f"events={events}")
        self.assertEqual(start[0]["event"], "gate_bypassed")
        self.assertEqual(start[0]["env_var"], "JIG_START_COLLISION_GATE")


@unittest.skipUnless(_git_on_path(), "git not available")
class StartCollisionGuardE2E(unittest.TestCase):
    """Real-git proof of the 051-04 guard: a working tree whose local slice is
    a stale READY_FOR_IMPLEMENTATION while origin/main already has it DONE —
    `transition ... IN_PROGRESS` must refuse after a real `git fetch` +
    `git show origin/main:<path>`. Unlike the recorder tests, this drives REAL
    git against a `file://`-style bare origin (parity with 051-01's E2E)."""

    def _git(self, *args, cwd):
        return subprocess.run(["git", *args], cwd=str(cwd),
                              capture_output=True, text=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-startcol-e2e-"))
        self.work = self.tmp / "work"
        self._git("init", str(self.work), cwd=self.tmp)
        self._git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.work)
        for k, v in (("user.email", "t@e.x"), ("user.name", "T"),
                     ("commit.gpgsign", "false")):
            self._git("config", k, v, cwd=self.work)
        self.spec_dir = self.work / "docs" / "specs" / "200-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec 200\n\n## Overview\n\nx\n")
        self.slice = self.spec_dir / "slice-01-demo.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_slice(self, status):
        self.slice.write_text(
            f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 200-01 — demo\n\n**Goal:** x.\n\n**DoD:**\n- [ ] x.\n")

    def _commit_all(self, msg):
        self._git("add", "-A", cwd=self.work)
        self._git("commit", "-m", msg, cwd=self.work)

    def _add_origin_and_push(self):
        self.origin = self.tmp / "origin.git"
        self._git("init", "--bare", str(self.origin), cwd=self.tmp)
        self._git("remote", "add", "origin", str(self.origin), cwd=self.work)
        push = self._git("push", "-u", "origin", "main", cwd=self.work)
        self.assertEqual(push.returncode, 0, f"push failed: {push.stderr}")

    def _fm(self):
        fields, _ = _workflow.parse_frontmatter(self.slice.read_text())
        return fields

    def test_refuses_when_origin_has_slice_done(self):
        from unittest.mock import patch
        self._write_slice("DONE")
        self._commit_all("land slice DONE")
        self._add_origin_and_push()
        # Local working copy rewound to a stale READY — the issue-81 scenario.
        self._write_slice("READY_FOR_IMPLEMENTATION")
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}):
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        self.assertIn("DONE on origin/main", str(ctx.exception))
        self.assertEqual(self._fm()["status"], "READY_FOR_IMPLEMENTATION")
        self.assertNotIn("claimed_by", self._fm())

    def test_proceeds_when_slice_absent_on_origin(self):
        from unittest.mock import patch
        # origin/main carries only spec.md; the slice is a local-only file.
        self._commit_all("seed spec only")
        self._add_origin_and_push()
        self._write_slice("READY_FOR_IMPLEMENTATION")
        with patch.dict(os.environ, {"JIG_CLAIM_ID": "wt-me"}):
            _workflow.transition(self.spec, "200-01", "IN_PROGRESS")
        self.assertEqual(self._fm()["status"], "IN_PROGRESS")
        self.assertEqual(self._fm().get("claimed_by"), "wt-me")


class StatusBoardClaimRenderTests(unittest.TestCase):
    """Slice 049-02: the status board renders `IN_PROGRESS (<claimed_by>)`
    for claimed in-progress slices; everything else is byte-identical to the
    pre-049-02 render."""

    def _status_cell(self, table, label):
        for line in table.splitlines():
            if f"| {label} |" in line:
                return line.split("|")[3].strip()
        raise AssertionError(f"row not found for label {label!r}:\n{table}")

    # AC1
    def test_in_progress_renders_claim_suffix(self):
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "", "wt-foo")]
        table = _workflow.render_status_table(rows)
        self.assertEqual(self._status_cell(table, "200-01 — a"),
                         "IN_PROGRESS (wt-foo)")

    # AC1 — fallback when unclaimed
    def test_in_progress_without_claim_renders_plain(self):
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "", "")]
        table = _workflow.render_status_table(rows)
        self.assertEqual(self._status_cell(table, "200-01 — a"), "IN_PROGRESS")

    # AC1 — legacy 5-tuple row (pre-049-02 collect_slices shape) is tolerated
    def test_legacy_5tuple_row_renders_plain(self):
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "")]
        table = _workflow.render_status_table(rows)
        self.assertEqual(self._status_cell(table, "200-01 — a"), "IN_PROGRESS")

    # AC2 — other states unchanged; claimed_by ignored on non-IN_PROGRESS
    def test_other_states_unchanged(self):
        cases = [("DRAFT", "DRAFT"), ("READY_FOR_REVIEW", "READY_FOR_REVIEW"),
                 ("READY_FOR_IMPLEMENTATION", "READY_FOR_IMPLEMENTATION"),
                 ("REVIEWED", "REVIEWED"), ("RECONCILED", "RECONCILED"),
                 ("DONE", "**DONE**")]
        for status, expect in cases:
            rows = [("200-x", "200-01 — a", status, "", "", "wt-foo")]
            table = _workflow.render_status_table(rows)
            self.assertEqual(self._status_cell(table, "200-01 — a"), expect,
                             f"status {status} should ignore claimed_by")

    # AC6 — truncation above the bound
    def test_long_claim_truncated(self):
        long = "claude/" + "x" * 40
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "", long)]
        cell = self._status_cell(_workflow.render_status_table(rows),
                                 "200-01 — a")
        self.assertEqual(cell, f"IN_PROGRESS ({long[:27]}…)")

    def test_claim_at_bound_not_truncated(self):
        c = "x" * 30
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "", c)]
        cell = self._status_cell(_workflow.render_status_table(rows),
                                 "200-01 — a")
        self.assertEqual(cell, f"IN_PROGRESS ({c})")

    # AC5 — DEFERRED table carries no claim suffix
    def test_deferred_table_unaffected(self):
        rows = [("200-x", "200-09 — d", "DEFERRED", "trigger here", "",
                 "wt-foo")]
        deferred = _workflow.render_deferred_table(rows)
        self.assertIn("trigger here", deferred)
        self.assertNotIn("wt-foo", deferred)

    # AC3 — render idempotence
    def test_render_idempotent(self):
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "", "wt-foo"),
                ("200-x", "200-02 — b", "DONE", "", "", "")]
        once = _workflow.render_status_table(rows)
        twice = _workflow.render_status_table(rows)
        self.assertEqual(once, twice)

    # AC2/AC7 — byte-identity snapshot over mixed rows
    def test_byte_identity_mixed_snapshot(self):
        rows = [("200-x", "200-01 — a", "IN_PROGRESS", "", "", "wt-foo"),
                ("200-x", "200-02 — b", "IN_PROGRESS", "", "", ""),
                ("200-x", "200-03 — c", "DONE", "", "", "")]
        table = _workflow.render_status_table(rows)
        expected = (
            "| Spec | Slice | Status | Notes |\n"
            "|------|-------|--------|-------|\n"
            "| [200-x](200-x/spec.md) | 200-01 — a | IN_PROGRESS (wt-foo) |  |\n"
            "| [200-x](200-x/spec.md) | 200-02 — b | IN_PROGRESS |  |\n"
            "| [200-x](200-x/spec.md) | 200-03 — c | **DONE** |  |\n"
        )
        self.assertEqual(table, expected)

    # AC3/AC4 — end-to-end regen: claim surfaces, Notes preserved, idempotent
    def test_regen_surfaces_claim_and_is_idempotent(self):
        tmp = tempfile.mkdtemp(prefix="jig-board-claim-")
        try:
            root = Path(tmp)
            sd = root / "docs" / "specs" / "200-demo"
            sd.mkdir(parents=True)
            (sd / "spec.md").write_text(
                "---\nstatus: IN_PROGRESS\n---\n\n# Spec 200\n\n"
                "## Overview\n\nx\n")
            (sd / "slice-01-a.md").write_text(
                "---\nstatus: IN_PROGRESS\nclaimed_by: wt-foo\n---\n\n"
                "## Slice 200-01 — a\n\n**Goal:** x.\n")
            (root / "docs" / "specs" / "README.md").write_text(
                "# Spec Status Board\n\n"
                "| Spec | Slice | Status | Notes |\n"
                "|------|-------|--------|-------|\n"
                "| [200-demo](200-demo/spec.md) | 200-01 — a | IN_PROGRESS | "
                "curated note |\n")
            _workflow.regenerate_status_board(root)
            board = (root / "docs" / "specs" / "README.md").read_text()
            self.assertIn("IN_PROGRESS (wt-foo)", board)
            self.assertIn("curated note", board)  # AC4: Notes preserved
            msg = _workflow.regenerate_status_board(root)  # AC3: idempotent
            self.assertIn("already current", msg)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class _GateFixture(unittest.TestCase):
    """Builds a temp spec dir with one slice file and (optionally) review
    evidence + reconciliation close-out sections, then drives gated transitions
    with the gate enabled."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-gate-"))
        # docs/specs/NNN-slug/ layout so evidence_path resolves a sibling
        # reviews/ dir under the spec.
        self.spec_dir = self.tmpdir / "docs" / "specs" / "045-gate-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec_md = self.spec_dir / "spec.md"
        self.spec_md.write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec\n\n## Overview\n\nx.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write_slice(self, status: str, *, slice_no: str = "01",
                    slug: str = "thing", arch_review: bool = False,
                    code_health_review: bool = False,
                    frame_review: bool = False,
                    design_review: bool = False,
                    deviation_log: bool = False,
                    reconciliation_sweep: bool = False,
                    dod_lines: list = None,
                    label: str = None) -> None:
        """Write `slice-NN-<slug>.md` with the given status. The `## Slice`
        label defaults to `045-NN — <slug>` so the fragment `045-NN`
        resolves it."""
        label = label or f"045-{slice_no} — {slug}"
        fm = ["---", f"status: {status}", "dependencies: []", "last_verified:"]
        if arch_review:
            fm.append("arch_review: true")
        if code_health_review:
            fm.append("code_health_review: true")
        if frame_review:
            fm.append("frame_review: true")
        if design_review:
            fm.append("design_review: true")
        fm.append("---")
        body = ["", f"## Slice {label}", "", "**Goal:** placeholder.", ""]
        if dod_lines:
            body.extend(["**Definition of Done:**", ""])
            body.extend(dod_lines)
            body.append("")
        if deviation_log:
            body.extend(["### Deviation log (after reconciliation)", "",
                         "Real reconciliation prose here.", ""])
        if reconciliation_sweep:
            body.extend([
                "### Reconciliation sweep",
                "",
                "| Artifact | Disposition | Rationale |",
                "|----------|-------------|-----------|",
                "| `README.md` | `no-op` | Checked; no front-door drift. |",
                "| `docs/specs/README.md` | `deferred` | Regenerate at close-out. |",
                "",
            ])
        (self.spec_dir / f"slice-{slice_no}-{slug}.md").write_text(
            "\n".join(fm) + "\n" + "\n".join(body) + "\n"
        )

    def write_evidence(self, pass_name: str, *, slice_no: str = "01",
                       verdict: str = "pass",
                       reviewer: str = "jig:reviewer",
                       reviewed_at: str = "2026-06-02T14:30:00Z",
                       prompt_source: str = "review.py x",
                       slice_field: str = None,
                       omit: tuple = (),
                       raw: str = None) -> Path:
        """Write `reviews/slice-NN-<pass>.md` verdict file (ADR-0014 §1/§2).
        `omit` drops named frontmatter fields (malformed-input fixtures);
        `raw` overrides the entire file content verbatim."""
        slice_field = slice_field or f"045-{slice_no}"
        reviews = self.spec_dir / "reviews"
        reviews.mkdir(exist_ok=True)
        path = reviews / f"slice-{slice_no}-{pass_name}.md"
        if raw is not None:
            path.write_text(raw)
            return path
        fields = {
            "slice": slice_field,
            "pass": pass_name,
            "verdict": verdict,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "prompt_source": prompt_source,
        }
        lines = ["---"]
        for k, v in fields.items():
            if k in omit:
                continue
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        lines.append("## VERDICT")
        lines.append(verdict)
        path.write_text("\n".join(lines) + "\n")
        return path

    def _status_in_slice(self, slice_no: str = "01",
                         slug: str = "thing") -> str:
        text = (self.spec_dir / f"slice-{slice_no}-{slug}.md").read_text()
        m = re.search(r"^status:\s*(\w+)", text, re.MULTILINE)
        return m.group(1) if m else "?"


class TransitionReadyForReviewFrameGateTests(_GateFixture):
    """Slice 064-03 / ADR-0020 AC3: READY_FOR_REVIEW is gated on the
    frame-critique verdict IFF the slice declares `frame_review: true`.
    Default-off slices transition freely (no regression for existing specs).
    """

    def test_flagged_slice_blocked_when_frame_missing(self):
        self.write_slice("DRAFT", frame_review=True)
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_REVIEW", gate=True)
        self.assertNotEqual(r.returncode, 0,
                            f"frame_review: true with no verdict must block; "
                            f"stderr={r.stderr}")
        # Names the missing artifact + the record command (ADR-0014 AC3).
        self.assertIn("frame-critique", r.stderr)
        self.assertIn("record-review", r.stderr)
        self.assertEqual(self._status_in_slice(), "DRAFT")

    def test_flagged_slice_clears_with_passing_frame_verdict(self):
        self.write_slice("DRAFT", frame_review=True)
        self.write_evidence("frame-critique")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_REVIEW", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected READY_FOR_REVIEW to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "READY_FOR_REVIEW")

    def test_unflagged_slice_passes_freely(self):
        # No frame_review flag → empty required set → no regression for the
        # many existing specs that transition DRAFT → READY_FOR_REVIEW.
        self.write_slice("DRAFT")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_REVIEW", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"unflagged slice must pass freely; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "READY_FOR_REVIEW")

    def test_flagged_slice_bypassed_by_disabled_gate(self):
        # JIG_REVIEW_EVIDENCE_GATE=0 skips the gate (deliberateness signal).
        self.write_slice("DRAFT", frame_review=True)
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_REVIEW", gate=False)
        self.assertEqual(r.returncode, 0,
                         f"bypass must let it through; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "READY_FOR_REVIEW")

    def test_frame_critique_not_required_at_done(self):
        # frame-critique is a ONE-TIME pre-implementation gate — NOT
        # re-validated at DONE (only REVIEWED + RECONCILED sets are).
        self.write_slice("RECONCILED", frame_review=True, deviation_log=True,
                         reconciliation_sweep=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("reconciliation")
        # No frame-critique verdict recorded — DONE must still clear.
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"DONE must not require frame-critique; stderr={r.stderr}")


class TransitionReviewedGateTests(_GateFixture):
    """AC1: REVIEWED is gated on compliance + craft (+ arch when flagged)."""

    # --- clears ---
    def test_reviewed_clears_with_compliance_and_craft_pass(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected REVIEWED to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "REVIEWED")

    # --- missing ---
    def test_reviewed_blocked_when_compliance_missing(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("craft")  # compliance absent
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compliance", r.stderr.lower())
        # Status not advanced.
        self.assertEqual(self._status_in_slice(), "IN_PROGRESS")

    def test_reviewed_blocked_when_craft_missing(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")  # craft absent
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr.lower())

    # --- malformed ---
    def test_reviewed_blocked_when_evidence_malformed(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        # craft file with no frontmatter block at all.
        self.write_evidence("craft", raw="no frontmatter here\n")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr.lower())

    def test_reviewed_blocked_when_required_field_missing(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft", omit=("verdict",))
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("verdict", r.stderr.lower())

    # --- fail / needs-changes (superseded-only) ---
    def test_reviewed_blocked_when_compliance_fail(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance", verdict="fail")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compliance", r.stderr.lower())

    def test_reviewed_blocked_when_craft_needs_changes(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft", verdict="needs-changes")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr.lower())

    # --- arch: required only when flagged ---
    def test_reviewed_blocked_when_arch_flagged_but_missing(self):
        self.write_slice("IN_PROGRESS", arch_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        # arch evidence absent though the slice declares arch_review: true
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("arch", r.stderr.lower())

    def test_reviewed_clears_when_arch_flagged_and_present(self):
        self.write_slice("IN_PROGRESS", arch_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("arch")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected REVIEWED to clear; stderr={r.stderr}")

    def test_reviewed_ignores_arch_when_not_flagged(self):
        # No arch_review flag → arch evidence not required even if absent.
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"arch should not be required; stderr={r.stderr}")

    # --- code-health: required only when flagged (slice 060-05) ---
    def test_reviewed_blocked_when_code_health_flagged_but_missing(self):
        self.write_slice("IN_PROGRESS", code_health_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        # code-health evidence absent though the slice declares the flag.
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("code-health", r.stderr.lower())
        self.assertEqual(self._status_in_slice(), "IN_PROGRESS")

    def test_reviewed_clears_when_code_health_flagged_and_present(self):
        self.write_slice("IN_PROGRESS", code_health_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("code-health")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected REVIEWED to clear; stderr={r.stderr}")

    def test_reviewed_ignores_code_health_when_not_flagged(self):
        # BACK-COMPAT (critical): a slice WITHOUT code_health_review must NOT
        # suddenly require a code-health verdict.
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"code-health should not be required; stderr={r.stderr}")

    # --- design-review: required only when flagged (slice 071-01 / ADR-0022) ---
    def test_reviewed_blocked_when_design_flagged_but_missing(self):
        self.write_slice("IN_PROGRESS", design_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        # design-review evidence absent though the slice declares the flag.
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("design-review", r.stderr.lower())
        self.assertEqual(self._status_in_slice(), "IN_PROGRESS")

    def test_reviewed_clears_when_design_flagged_and_present(self):
        self.write_slice("IN_PROGRESS", design_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("design-review")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected REVIEWED to clear; stderr={r.stderr}")

    def test_reviewed_ignores_design_when_not_flagged(self):
        # BACK-COMPAT: a slice WITHOUT design_review must NOT suddenly require
        # a design-review verdict.
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"design-review should not be required; stderr={r.stderr}")


class TransitionBranchFreshnessWarningTests(_GateFixture):
    """Bug 001 / issue #62 — review/reconcile transitions should surface a
    stale base before failures are recorded as main breakage."""

    def test_reviewed_emits_branch_freshness_warning_without_blocking(self):
        self.write_slice("IN_PROGRESS")
        import io
        from unittest.mock import patch
        captured = io.StringIO()
        warning = (
            "warning: current branch is 2 commits behind `origin/main`; "
            "integrate before review/reconcile/landing. Test results against "
            "a stale base may misattribute failures to main."
        )

        with patch.dict(os.environ, {"JIG_REVIEW_EVIDENCE_GATE": "0"}), \
             patch.object(_workflow, "_branch_freshness_warning",
                          return_value=warning), \
             patch.object(_workflow.sys, "stderr", captured):
            _workflow.transition(self.spec_md, "045-01", "REVIEWED")

        self.assertEqual(self._status_in_slice(), "REVIEWED")
        self.assertIn("2 commits behind `origin/main`", captured.getvalue())
        self.assertIn("stale base", captured.getvalue())


class TransitionReconciledGateTests(_GateFixture):
    """AC2: RECONCILED needs the reconciliation verdict, deviation log, and
    reconciliation sweep."""

    def test_reconciled_clears_with_verdict_devlog_and_sweep(self):
        self.write_slice("REVIEWED", deviation_log=True,
                         reconciliation_sweep=True)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected RECONCILED to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "RECONCILED")

    def test_reconciled_blocked_when_reconciliation_evidence_missing(self):
        self.write_slice("REVIEWED", deviation_log=True,
                         reconciliation_sweep=True)
        # no reconciliation verdict file
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation", r.stderr.lower())

    def test_reconciled_blocked_when_deviation_log_missing(self):
        self.write_slice("REVIEWED", deviation_log=False,
                         reconciliation_sweep=True)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("deviation log", r.stderr.lower())

    def test_reconciled_blocked_when_sweep_missing(self):
        self.write_slice("REVIEWED", deviation_log=True,
                         reconciliation_sweep=False)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation sweep", r.stderr.lower())
        self.assertIn("reviewer", r.stderr.lower())
        self.assertEqual(self._status_in_slice(), "REVIEWED")

    def test_reconciled_blocked_when_reconciliation_fail(self):
        self.write_slice("REVIEWED", deviation_log=True,
                         reconciliation_sweep=True)
        self.write_evidence("reconciliation", verdict="fail")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation", r.stderr.lower())


class TransitionDoneGateTests(_GateFixture):
    """AC2: DONE re-validates the full set AND keeps the dependency check."""

    def _write_full_evidence(self):
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("reconciliation")

    def test_done_clears_with_full_evidence(self):
        self.write_slice("RECONCILED", deviation_log=True,
                         reconciliation_sweep=True)
        self._write_full_evidence()
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected DONE to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "DONE")

    def test_done_blocked_when_reviewed_evidence_missing(self):
        # Reconciliation present but compliance/craft absent — the DONE
        # re-validation must catch a hand-edited status that skipped REVIEWED.
        self.write_slice("RECONCILED", deviation_log=True,
                         reconciliation_sweep=True)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compliance", r.stderr.lower())

    def test_done_blocked_when_reconciliation_missing(self):
        self.write_slice("RECONCILED", deviation_log=True,
                         reconciliation_sweep=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation", r.stderr.lower())

    def test_done_blocked_when_sweep_missing(self):
        self.write_slice("RECONCILED", deviation_log=True,
                         reconciliation_sweep=False)
        self._write_full_evidence()
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation sweep", r.stderr.lower())

    def test_done_still_enforces_dependency_check(self):
        # Full evidence present, but a dependency is unsatisfied — the
        # existing dependency gate must still fire (belt-and-suspenders).
        # Add an unsatisfied dep to the slice frontmatter.
        (self.spec_dir / "slice-01-thing.md").write_text(
            "---\nstatus: RECONCILED\ndependencies: [099-99]\n"
            "last_verified:\n---\n\n## Slice 045-01 — thing\n\n"
            "**Goal:** x.\n\n### Deviation log\n\nprose.\n"
        )
        self._write_full_evidence()
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("dependen", r.stderr.lower())


class TransitionGateDiagnosticsTests(_GateFixture):
    """AC3: refusals name the missing/invalid artifact AND the command."""

    def test_diagnostic_names_artifact_and_command(self):
        self.write_slice("IN_PROGRESS")
        # compliance missing entirely
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        err = r.stderr.lower()
        # Names the pass.
        self.assertIn("compliance", err)
        # Names the recorder command a contributor runs next.
        self.assertIn("record-review", err)


class TransitionUngatedStatesTests(_GateFixture):
    """AC4: ungated transitions + the two review back-edges still work
    with the gate ON and no evidence present."""

    def test_draft_to_ready_for_review_ungated(self):
        self.write_slice("DRAFT")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_REVIEW", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_ready_for_review_to_ready_for_implementation_ungated(self):
        self.write_slice("READY_FOR_REVIEW")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_IMPLEMENTATION", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_ready_for_implementation_to_in_progress_ungated(self):
        self.write_slice("READY_FOR_IMPLEMENTATION")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "IN_PROGRESS", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_any_to_deferred_ungated(self):
        self.write_slice("IN_PROGRESS")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DEFERRED", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_deferred_to_draft_reopen_ungated(self):
        self.write_slice("DEFERRED")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DRAFT", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_reviewed_to_in_progress_back_edge_ungated(self):
        # needs-changes back-edge relaxes status → nothing to gate, even
        # with no evidence on disk.
        self.write_slice("REVIEWED")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "IN_PROGRESS", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_reconciled_to_in_progress_back_edge_ungated(self):
        # reconciliation-fails back-edge relaxes status → ungated.
        self.write_slice("RECONCILED")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "IN_PROGRESS", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")


class TransitionGateBypassTests(_GateFixture):
    """Bypass: JIG_REVIEW_EVIDENCE_GATE in the falsey set skips the
    evidence check (a deliberate-actor escape hatch, ADR-0011 stance)."""

    def _run_with_gate_env(self, value, *args):
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["JIG_REVIEW_EVIDENCE_GATE"] = value
        return subprocess.run(
            [sys.executable, str(WORKFLOW), *args],
            capture_output=True, text=True, env=env,
        )

    def test_bypass_zero_lets_reviewed_through_without_evidence(self):
        self.write_slice("IN_PROGRESS")
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "REVIEWED",
        )
        self.assertEqual(r.returncode, 0,
                         f"bypass=0 should skip the gate; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "REVIEWED")

    def test_bypass_accepts_false_off_no(self):
        for value in ("false", "off", "no", "FALSE", "Off"):
            with self.subTest(value=value):
                self.write_slice("IN_PROGRESS")
                r = self._run_with_gate_env(
                    value, "transition", str(self.spec_md), "045-01",
                    "RECONCILED",
                )
                self.assertEqual(
                    r.returncode, 0,
                    f"bypass={value!r} should skip the gate; stderr={r.stderr}",
                )

    def test_bypass_zero_skips_reconciliation_sweep_check(self):
        self.write_slice("REVIEWED", deviation_log=True,
                         reconciliation_sweep=False)
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "RECONCILED",
        )
        self.assertEqual(
            r.returncode, 0,
            f"bypass=0 should skip sweep presence check; stderr={r.stderr}",
        )
        self.assertEqual(self._status_in_slice(), "RECONCILED")

    def test_bypass_still_enforces_dependency_check_on_done(self):
        # The bypass only skips the *evidence* check; the DONE dependency
        # check must still run (per the slice brief).
        (self.spec_dir / "slice-01-thing.md").write_text(
            "---\nstatus: RECONCILED\ndependencies: [099-99]\n"
            "last_verified:\n---\n\n## Slice 045-01 — thing\n\n**Goal:** x.\n"
        )
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "DONE",
        )
        self.assertNotEqual(r.returncode, 0,
                            "dependency check must still fire under bypass")
        self.assertIn("dependen", r.stderr.lower())


class TransitionGateBypassTelemetryTests(_GateFixture):
    """Spec 078-01: the review-evidence gate's bypass emits a content-free
    `gate_bypassed` event to .claude/skill-usage.jsonl (project root =
    `_project_root_for_spec(spec_md)`, same tree `_GateFixture` builds)."""

    def _run_with_gate_env(self, value, *args):
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        if value is None:
            env.pop("JIG_REVIEW_EVIDENCE_GATE", None)
        else:
            env["JIG_REVIEW_EVIDENCE_GATE"] = value
        return subprocess.run(
            [sys.executable, str(WORKFLOW), *args],
            capture_output=True, text=True, env=env,
        )

    def _read_events(self):
        log = self.tmpdir / ".claude" / "skill-usage.jsonl"
        if not log.is_file():
            return []
        import json as _json
        return [_json.loads(line) for line in log.read_text().splitlines()
                if line.strip()]

    def test_bypass_emits_one_content_free_event(self):
        self.write_slice("IN_PROGRESS")
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "REVIEWED",
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        events = self._read_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "gate_bypassed")
        self.assertEqual(events[0]["gate"], "review-evidence")
        self.assertEqual(events[0]["env_var"], "JIG_REVIEW_EVIDENCE_GATE")
        # content-free: never the target status or slice body.
        import json as _json
        self.assertNotIn("REVIEWED", _json.dumps(events[0]))

    def test_normal_path_emits_nothing(self):
        # Gate ON (no bypass) with full evidence present — a clean pass,
        # not a bypass — must emit no event.
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = self._run_with_gate_env(
            None, "transition", str(self.spec_md), "045-01", "REVIEWED",
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        self.assertEqual(self._read_events(), [])

    def test_ungated_transition_emits_nothing(self):
        # DRAFT -> READY_FOR_IMPLEMENTATION is not an evidence-gated state
        # at all — the gate function no-ops before ever checking bypass.
        self.write_slice("DRAFT")
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01",
            "READY_FOR_IMPLEMENTATION",
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        self.assertEqual(self._read_events(), [])

    def test_bypass_telemetry_fails_open(self):
        # Unwritable sink (a directory in place of the file) must not
        # block the transition.
        claude_dir = self.tmpdir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "skill-usage.jsonl").mkdir()
        self.write_slice("IN_PROGRESS")
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "REVIEWED",
        )
        self.assertEqual(
            r.returncode, 0,
            f"unwritable telemetry sink must not block transition; "
            f"stderr={r.stderr}",
        )


class ArchReviewTruthyUnificationTests(unittest.TestCase):
    """045-03 must-do (d): a SINGLE shared truthy predicate backs both
    `workflow.slice_needs_arch_review` and
    `review_evidence._arch_review_flag` so they cannot drift."""

    def test_workflow_and_evidence_share_one_truthy_source(self):
        sys.path.insert(0, str(REPO_ROOT / "skills"))
        sys.path.insert(0, str(REPO_ROOT / "skills" / "spec-workflow"))
        import importlib
        parsing = importlib.import_module("_common.parsing")
        review_evidence = importlib.import_module("_common.review_evidence")
        workflow = importlib.import_module("workflow")
        # The shared constant exists in the common module.
        self.assertTrue(hasattr(parsing, "FRONTMATTER_TRUTHY"))
        shared = parsing.FRONTMATTER_TRUTHY
        # Both callers' truthy tuples are the SAME object as the shared one
        # (identity, not just equality — that's what "cannot drift" means).
        self.assertIs(workflow._ARCH_REVIEW_TRUTHY, shared)
        self.assertIs(review_evidence._ARCH_REVIEW_TRUTHY, shared)

    def test_shared_predicate_accepts_permissive_truthy_set(self):
        sys.path.insert(0, str(REPO_ROOT / "skills"))
        import importlib
        parsing = importlib.import_module("_common.parsing")
        for tok in ("true", "yes", "on", "1", "YES", "On", "TRUE"):
            self.assertTrue(parsing.frontmatter_flag_truthy(tok),
                            f"{tok!r} should be truthy")
        for tok in ("false", "no", "0", "maybe", "", None):
            self.assertFalse(parsing.frontmatter_flag_truthy(tok),
                             f"{tok!r} should not be truthy")

class AmendmentDigestTests(unittest.TestCase):
    """workflow.py amendments — read-only digest of the `## Amendments`
    overrides on closed records (slice 048-04). Indexes current truth so a
    reader needn't reread historical drift; never modifies any artifact."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-amd-")
        self.proj = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, rel: str, text: str) -> None:
        p = self.proj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    # AC #1 / #2 — lists amendment-bearing artifacts (path + date + title),
    # sorted; AC #5 — an artifact without amendments is not listed.
    def test_lists_amendment_bearing_artifacts_sorted(self):
        self._write(
            "docs/specs/016-scaffold-mode/spec.md",
            "---\nstatus: DONE\n---\n\n# Spec 016\n\nbody\n\n"
            "## Amendments\n\n### 2026-05-27 — Hook count: five → seven\n"
            "prose.\n",
        )
        self._write(
            "docs/decisions/adr-0008-closed-spec-drift-policy.md",
            "# ADR-0008\n\nbody\n\n## Amendments\n\n"
            "### 2026-05-27 — Hook count: five → seven\nprose.\n",
        )
        self._write(
            "docs/specs/099-no-amendments/spec.md",
            "---\nstatus: DONE\n---\n\n# Spec 099\n\nno amendments here.\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        out = result.stdout
        self.assertIn("docs/decisions/adr-0008-closed-spec-drift-policy.md", out)
        self.assertIn("docs/specs/016-scaffold-mode/spec.md", out)
        self.assertIn("2026-05-27 — Hook count: five → seven", out)
        self.assertNotIn("099-no-amendments", out)
        # Stable, sorted by path: decisions/ precedes specs/.
        self.assertLess(
            out.index("docs/decisions/adr-0008"),
            out.index("docs/specs/016-scaffold-mode"),
            "digest must be sorted by artifact path",
        )

    # AC #5 — absence case: clear message, exit 0.
    def test_handles_no_amendments(self):
        self._write(
            "docs/specs/099-no-amendments/spec.md",
            "---\nstatus: DONE\n---\n\n# Spec 099\n\nno amendments.\n",
        )
        self._write("docs/decisions/adr-0001-foo.md", "# ADR-0001\n\nbody.\n")
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("No amendment-bearing artifacts", result.stdout)

    # Edge: a `## Amendments` heading with no dated entries is not a real
    # override — skip it (don't crash or emit an empty artifact block).
    def test_ignores_empty_amendments_section(self):
        self._write(
            "docs/specs/016-scaffold-mode/spec.md",
            "# Spec 016\n\nbody\n\n## Amendments\n\n(none yet)\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("No amendment-bearing artifacts", result.stdout)

    # Edge: a `## Amendments` heading INSIDE a ```-fenced code block is an
    # illustrative example (this is exactly ADR-0008's shape — it documents
    # the amendment *format* in a fence), NOT a live amendment. It must be
    # ignored, or the digest reports a false override.
    def test_ignores_fenced_amendments_example(self):
        self._write(
            "docs/decisions/adr-0008-closed-spec-drift-policy.md",
            "# ADR-0008\n\nThe amendment shape:\n\n"
            "```markdown\n## Amendments\n\n"
            "### 2026-05-27 — Hook count: five → seven\nillustrative prose.\n"
            "```\n\n(the above is just an example of the format.)\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("No amendment-bearing artifacts", result.stdout)
        self.assertNotIn("adr-0008", result.stdout)

    # AC #1 — amendments can live in slice files, not only spec.md / ADRs.
    def test_finds_amendments_in_slice_files(self):
        self._write(
            "docs/specs/016-scaffold-mode/slice-01-foo.md",
            "---\nstatus: DONE\n---\n\n## Slice 016-01\n\nbody\n\n"
            "## Amendments\n\n### 2026-06-01 — Renamed widget → gadget\nprose.\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("slice-01-foo.md", result.stdout)
        self.assertIn("2026-06-01 — Renamed widget → gadget", result.stdout)


class ReserveSpecFromLinkedWorktreeE2E(unittest.TestCase):
    """Real-git end-to-end proof of the worktree-aware reservation fix.

    Reproduces the exact friction that motivated it: a linked worktree on a
    feature branch with `main` checked out in the primary worktree (so the
    linked worktree CANNOT `git checkout main`). The reservation must still
    land on origin/main, clean up its ephemeral worktree, and leave the
    caller's branch and working tree untouched.

    Unlike the recorder-based tests above, this class drives REAL `git` (no
    subprocess patching) — the bug was about git's one-checkout-per-branch
    worktree semantics, which only real git exercises."""

    def _git(self, *args, cwd):
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        )

    def setUp(self):
        import shutil
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-wf-wt-e2e-"))
        # Build `work` on `main` directly (robust across git versions —
        # avoids empty-clone default-branch quirks), seed two specs, then
        # push to a bare `origin`.
        self.work = self.tmp / "work"
        self._git("init", str(self.work), cwd=self.tmp)
        self._git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.work)
        for k, v in (("user.email", "t@e.x"), ("user.name", "T"),
                     ("commit.gpgsign", "false")):
            self._git("config", k, v, cwd=self.work)
        for name in ("001-alpha", "002-beta"):
            d = self.work / "docs" / "specs" / name
            d.mkdir(parents=True)
            (d / "spec.md").write_text(f"# Spec {name}\n")
        # Spec 063-01: the scaffold-state precondition classifies on the
        # `scaffold.json` completion sentinel; a scaffolded project carries
        # it, so `reserve_spec` proceeds to the worktree-aware reserve flow.
        (self.work / "scaffold.json").write_text("{}\n")
        self._git("add", "-A", cwd=self.work)
        self._git("commit", "-m", "seed specs", cwd=self.work)
        self.origin = self.tmp / "origin.git"
        self._git("init", "--bare", str(self.origin), cwd=self.tmp)
        self._git("remote", "add", "origin", str(self.origin), cwd=self.work)
        push = self._git("push", "-u", "origin", "main", cwd=self.work)
        self.assertEqual(push.returncode, 0, f"seed push failed: {push.stderr}")
        # Linked worktree on a feature branch — `main` stays held by `work`.
        self.feat = self.tmp / "feat"
        add = self._git("worktree", "add", "-b", "feature", str(self.feat),
                        cwd=self.work)
        self.assertEqual(add.returncode, 0, f"worktree add failed: {add.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reserve_from_linked_worktree_lands_on_origin_main(self):
        # Precondition the whole fix rests on: the linked worktree genuinely
        # cannot check out `main` (it's held by `work`).
        co = self._git("checkout", "main", cwd=self.feat)
        self.assertNotEqual(co.returncode, 0)
        self.assertIn("already used by worktree", co.stderr)

        feat_head_before = self._git(
            "rev-parse", "HEAD", cwd=self.feat).stdout.strip()

        # Reserve from the linked worktree — REAL git, no mocking.
        code = _workflow.reserve_spec(
            "gamma", project_dir=self.feat, no_push=False, pr_mode=False,
        )
        self.assertEqual(code, 0)

        # The reservation landed on origin/main as 003-gamma (max + 1).
        ls = self._git("ls-tree", "-r", "--name-only", "main", cwd=self.origin)
        self.assertIn("docs/specs/003-gamma/spec.md", ls.stdout)

        # The ephemeral reservation worktree was cleaned up — only `work`
        # and `feat` remain registered.
        wl = self._git("worktree", "list", cwd=self.work).stdout
        self.assertNotIn("jig-reserve-spec", wl)
        self.assertEqual(len(wl.strip().splitlines()), 2, wl)

        # The caller's branch tip and working tree are untouched: identical
        # HEAD, and the stub does NOT appear in the feature worktree.
        feat_head_after = self._git(
            "rev-parse", "HEAD", cwd=self.feat).stdout.strip()
        self.assertEqual(feat_head_before, feat_head_after)
        self.assertFalse((self.feat / "docs/specs/003-gamma").exists())

    def test_reserve_from_linked_worktree_with_relative_origin_url(self):
        # B1 regression lock: when `origin`'s URL is RELATIVE, the old code
        # (which pushed from the ephemeral temp worktree under $TMPDIR)
        # resolved the URL against the wrong base and the push died late.
        # Pushing the commit BY SHA from `project_dir` resolves the relative
        # URL correctly. This test FAILS before the fix and PASSES after.
        rel = self._git("remote", "set-url", "origin", "../origin.git",
                        cwd=self.work)
        self.assertEqual(rel.returncode, 0, f"set-url failed: {rel.stderr}")
        # Confirm the precondition: the linked worktree genuinely sees a
        # relative origin URL.
        url = self._git("remote", "get-url", "origin", cwd=self.feat)
        self.assertEqual(url.stdout.strip(), "../origin.git")

        # Reserve in push mode from the real linked worktree — REAL git.
        code = _workflow.reserve_spec(
            "gamma", project_dir=self.feat, no_push=False, pr_mode=False,
        )
        self.assertEqual(code, 0)

        # The ref REALLY moved on origin: the new spec is on origin/main.
        ls = self._git("ls-tree", "-r", "--name-only", "main", cwd=self.origin)
        self.assertIn("docs/specs/003-gamma/spec.md", ls.stdout)

        # And the ephemeral reservation worktree was still cleaned up.
        wl = self._git("worktree", "list", cwd=self.work).stdout
        self.assertNotIn("jig-reserve-spec", wl)

    def test_reserve_no_push_does_not_sweep_unrelated_staged_file(self):
        # M1 regression lock: --no-push commits ONLY the two stub files via a
        # pathspec-limited commit, even when the caller has unrelated work
        # already staged. The staged file must survive uncommitted.
        (self.feat / "unrelated.txt").write_text("do not commit me\n")
        add = self._git("add", "unrelated.txt", cwd=self.feat)
        self.assertEqual(add.returncode, 0, f"git add failed: {add.stderr}")

        code = _workflow.reserve_spec(
            "delta", project_dir=self.feat, no_push=True, pr_mode=False,
        )
        self.assertEqual(code, 0)

        # (a) The reservation commit contains ONLY the two stub files.
        names = self._git(
            "show", "--name-only", "--pretty=format:", "HEAD", cwd=self.feat
        ).stdout.split()
        self.assertEqual(
            sorted(names),
            ["docs/specs/003-delta/slice-01-tbd.md",
             "docs/specs/003-delta/spec.md"],
            f"commit swept extra files: {names}",
        )

        # (b) The unrelated file is still staged/uncommitted (not swept in).
        self.assertNotIn("unrelated.txt", names)
        staged = self._git(
            "diff", "--cached", "--name-only", cwd=self.feat).stdout
        self.assertIn("unrelated.txt", staged)


# ---------------------------------------------------------------------------
# Slice 057-01 — `session-plan` delegation-first dispatch plan
# ---------------------------------------------------------------------------


class SessionPlanTests(unittest.TestCase):
    """Slice 057-01: `workflow.py session-plan <spec>` emits, per
    non-DEFERRED slice, the standard phase sequence (implement →
    compliance → craft → [arch iff `arch_review: true`] → reconcile →
    land) naming the subagent type + skill for each phase. stdout-only,
    no side effects (clarify Q1/Q2).

    Fixtures use the canonical file-per-slice layout: `spec.md` carries
    the overview, sibling `slice-NN-<short>.md` files carry the slice
    frontmatter (where `arch_review:` / `status:` live).
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-session-plan-"))
        self.spec = self.tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, fname: str, label: str, status: str = "DRAFT",
                     arch_review: str = None,
                     code_health_review: str = None,
                     frame_review: str = None,
                     design_review: str = None) -> None:
        fm = [f"status: {status}", "dependencies: []", "last_verified:"]
        if arch_review is not None:
            fm.append(f"arch_review: {arch_review}")
        if code_health_review is not None:
            fm.append(f"code_health_review: {code_health_review}")
        if frame_review is not None:
            fm.append(f"frame_review: {frame_review}")
        if design_review is not None:
            fm.append(f"design_review: {design_review}")
        block = "---\n" + "\n".join(fm) + "\n---\n\n"
        (self.tmpdir / fname).write_text(
            block + f"## Slice {label}\n\n**Goal:** placeholder.\n"
        )

    def _run(self):
        return run_workflow("session-plan", str(self.spec))

    # AC #1 — deterministic per-slice phase sequence, named subagent+skill
    def test_emits_phase_sequence_per_slice(self):
        self._write_slice("slice-01-alpha.md", "057-01 alpha")
        self._write_slice("slice-02-beta.md", "057-02 beta")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        out = result.stdout
        # Both slices appear.
        self.assertIn("057-01 alpha", out)
        self.assertIn("057-02 beta", out)
        # The standard non-arch phase set is named with subagent + skill.
        for phase in ("implement", "compliance", "craft", "reconcile", "land"):
            self.assertIn(phase, out.lower())
        self.assertIn("implementer", out)
        self.assertIn("jig:independent-review", out)
        self.assertIn("pr-review", out)
        self.assertIn("slice-land", out)

    # AC #1 — arch phase iff slice declares arch_review: true
    def test_arch_phase_only_for_arch_review_slice(self):
        self._write_slice("slice-01-plain.md", "057-01 plain")
        self._write_slice("slice-02-arch.md", "057-02 arch",
                           arch_review="true")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        out = result.stdout
        # The arch-review skill is named (for the arch slice).
        self.assertIn("arch-review", out)
        # Split output per slice and assert presence/absence of arch phase.
        idx_plain = out.index("057-01 plain")
        idx_arch = out.index("057-02 arch")
        plain_block = out[idx_plain:idx_arch]
        arch_block = out[idx_arch:]
        self.assertNotIn("arch-review", plain_block,
                         "plain slice must NOT include the arch phase")
        self.assertIn("arch-review", arch_block,
                      "arch_review:true slice must include the arch phase")

    # AC #1 — truthy variations route to arch phase via FRONTMATTER_TRUTHY
    def test_arch_phase_for_truthy_variations(self):
        for truthy in ("yes", "True", "1", "on"):
            with self.subTest(truthy=truthy):
                self._write_slice("slice-01-arch.md", "057-01 arch",
                                  arch_review=truthy)
                result = self._run()
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn("arch-review", result.stdout)

    # Slice 060-05 — code-health phase iff slice declares code_health_review
    def test_code_health_phase_only_for_flagged_slice(self):
        self._write_slice("slice-01-plain.md", "057-01 plain")
        self._write_slice("slice-02-ch.md", "057-02 ch",
                           code_health_review="true")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        out = result.stdout
        self.assertIn("jig:code-health", out)
        idx_plain = out.index("057-01 plain")
        idx_ch = out.index("057-02 ch")
        plain_block = out[idx_plain:idx_ch]
        ch_block = out[idx_ch:]
        self.assertNotIn("jig:code-health", plain_block,
                         "plain slice must NOT include the code-health phase")
        self.assertIn("jig:code-health", ch_block,
                      "code_health_review:true slice must include the phase")

    def test_code_health_phase_after_arch_when_both(self):
        self._write_slice("slice-01-both.md", "057-01 both",
                           arch_review="true", code_health_review="true")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        out = result.stdout
        # arch must be emitted before code-health (after-craft ordering).
        self.assertIn("arch-review", out)
        self.assertIn("jig:code-health", out)
        self.assertLess(out.index("arch-review"), out.index("jig:code-health"),
                        "arch phase must come before code-health phase")

    # Slice 074-02 — phase-mode hints are visible, advisory, and
    # host-neutral (`plan` / `implement` / `review` / `reconcile` / `land`).
    def test_host_mode_hints_are_advisory_and_host_neutral(self):
        self._write_slice(
            "slice-01-hinted.md", "074-02 hinted",
            arch_review="true", code_health_review="true",
            frame_review="true", design_review="true",
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        out = result.stdout

        self.assertIn("Host-mode hints are advisory only", out)
        self.assertIn("never satisfy or block workflow.py transitions", out)
        for expected in (
            "frame-critique — DELEGATE to [reviewer] subagent, "
            "runs {jig:independent-review} "
            "(host-mode hint: plan; advisory only)",
            "implement — DELEGATE to [implementer] subagent "
            "(host-mode hint: implement; advisory only)",
            "compliance — DELEGATE to [reviewer] subagent, "
            "runs {jig:independent-review} "
            "(host-mode hint: review; advisory only)",
            "craft — DELEGATE to [reviewer] subagent, runs {pr-review} "
            "(host-mode hint: review; advisory only)",
            "arch — DELEGATE to [reviewer] subagent, runs {arch-review} "
            "(host-mode hint: review; advisory only)",
            "code-health — DELEGATE to [reviewer] subagent, "
            "runs {jig:code-health} "
            "(host-mode hint: review; advisory only)",
            "design-review — DELEGATE to [reviewer] subagent, "
            "runs {jig:independent-review} "
            "(host-mode hint: review; advisory only)",
            "reconcile — ORCHESTRATOR step, runs {jig:independent-review} "
            "(host-mode hint: reconcile; advisory only)",
            "land — ORCHESTRATOR step, runs {jig:slice-land} "
            "(host-mode hint: land; advisory only)",
        ):
            self.assertIn(expected, out)

        hints = set(re.findall(r"host-mode hint: ([a-z-]+); advisory only", out))
        self.assertLessEqual(
            hints, {"plan", "implement", "review", "reconcile", "land"},
        )

    # Slice 074-02 AC #4 — hints are rendered by session-plan only; transition
    # gates still use their original evidence and dependency inputs.
    def test_host_mode_hints_do_not_affect_review_gate(self):
        self._write_slice("slice-01-alpha.md", "057-01 alpha",
                          status="IN_PROGRESS")
        plan = self._run()
        self.assertEqual(plan.returncode, 0, msg=plan.stderr)
        self.assertIn("host-mode hint", plan.stdout)

        result = run_workflow("transition", str(self.spec), "057-01",
                              "REVIEWED", gate=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("compliance", result.stderr.lower())
        self.assertNotIn("host-mode", result.stderr.lower())

    def test_host_mode_hints_do_not_affect_dependency_gate(self):
        root = self.tmpdir / "project"
        spec_dir = root / "docs" / "specs" / "074-host-mode-demo"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec 074\n\n## Overview\n\nx.\n"
        )
        slice_md = spec_dir / "slice-02-demo.md"
        slice_md.write_text(
            "---\n"
            "status: RECONCILED\n"
            "dependencies: [999-01]\n"
            "last_verified: 2026-06-21\n"
            "---\n\n"
            "## Slice 074-02 — demo\n\n"
            "**Goal:** placeholder.\n\n"
            "### Deviation log (after reconciliation)\n\n"
            "No deviations.\n\n"
            "### Reconciliation sweep\n\n"
            "| Artifact | Disposition | Rationale |\n"
            "|----------|-------------|-----------|\n"
            "| `docs/specs/README.md` | `deferred` | Checked later. |\n"
        )

        plan = run_workflow("session-plan", str(spec_md))
        self.assertEqual(plan.returncode, 0, msg=plan.stderr)
        self.assertIn("host-mode hint", plan.stdout)

        result = run_workflow("transition", str(spec_md), "074-02", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsatisfied dependencies", result.stderr.lower())
        self.assertIn("999-01", result.stderr)
        self.assertNotIn("host-mode", result.stderr.lower())

    # AC #1 — DEFERRED slices are excluded
    def test_deferred_slice_excluded(self):
        self._write_slice("slice-01-live.md", "057-01 live",
                          status="IN_PROGRESS")
        self._write_slice("slice-02-parked.md", "057-02 parked",
                          status="DEFERRED")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("057-01 live", result.stdout)
        self.assertNotIn("057-02 parked", result.stdout)

    # AC #2 — delegation-first: marks delegated phases vs the dispatch loop,
    # and states the turn-count rationale.
    def test_delegation_first_framing(self):
        self._write_slice("slice-01-alpha.md", "057-01 alpha")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        low = result.stdout.lower()
        # Names the subagent delegation explicitly.
        self.assertIn("subagent", low)
        # States the turn-count rationale (re-reads context every turn).
        self.assertIn("turn", low)
        self.assertTrue(
            "re-read" in low or "every turn" in low or "re-reads" in low,
            "plan should state the orchestrator re-reads its context each turn",
        )

    # AC #4 — soft / no side effects on spec or slice state.
    def test_no_side_effects(self):
        self._write_slice("slice-01-alpha.md", "057-01 alpha")
        slice_path = self.tmpdir / "slice-01-alpha.md"
        spec_before = self.spec.read_text()
        slice_before = slice_path.read_text()
        before_files = sorted(p.name for p in self.tmpdir.iterdir())
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(self.spec.read_text(), spec_before)
        self.assertEqual(slice_path.read_text(), slice_before)
        self.assertEqual(sorted(p.name for p in self.tmpdir.iterdir()),
                         before_files)

    # Edge: zero non-DEFERRED slices → clear message, no crash.
    def test_no_slices_to_plan_message(self):
        self._write_slice("slice-01-parked.md", "057-01 parked",
                          status="DEFERRED")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("no slices to plan", result.stdout.lower())

    def test_no_slices_at_all_message(self):
        # Spec with overview only, no slice files.
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("no slices to plan", result.stdout.lower())


class SessionPlanDocTests(unittest.TestCase):
    """Slice 057-01 AC #3: `docs/workflow.md` gains a delegation-first /
    'run thin' dispatch-and-integrate section, reachable from the
    Context-cost-discipline guidance (parity with 055-01's doc pattern)."""

    def setUp(self):
        self.text = (REPO_ROOT / "docs" / "workflow.md").read_text()

    def test_run_thin_section_present(self):
        self.assertRegex(
            self.text,
            r"(?im)^###\s+Run thin",
            "docs/workflow.md must gain a 'Run thin' delegation-first section",
        )

    def test_section_names_dispatch_and_turn_count_rationale(self):
        # The section should explain dispatch-and-integrate + the
        # turn-count cost rationale, and point at session-plan.
        low = self.text.lower()
        self.assertIn("dispatch", low)
        self.assertIn("session-plan", low)
        self.assertIn("turn count", low)


class OutputDisciplineDocTests(unittest.TestCase):
    """Slice 057-03 AC #1: `docs/workflow.md` gains an output-discipline
    section — bound the size of the delegation prompts the orchestrator
    writes and the summaries subagents return (output is 5x-priced, the
    sibling lever to 055-04's verbose-Bash containment)."""

    def setUp(self):
        self.text = (REPO_ROOT / "docs" / "workflow.md").read_text()

    def test_output_discipline_section_present(self):
        # Match the new 057-03 heading specifically — not the pre-existing
        # 055-04 "Keep verbose command output out of the orchestrator"
        # heading, which a bare `.*output` regex would also satisfy (so the
        # test would stay green even if the 057-03 section were removed).
        self.assertRegex(
            self.text,
            r"(?im)^###\s+.*(emitted output|output lean|lean.*output)",
            "docs/workflow.md must gain an output-discipline section",
        )

    def test_section_covers_scoped_prompts_and_return_envelope(self):
        # The section should say delegation prompts point at files/paths to
        # READ rather than pasting contents, state the deliverable + return
        # envelope, and prefer a prompt FILE over inlining a large prompt.
        low = self.text.lower()
        self.assertIn("return envelope", low)
        self.assertIn("prompt file", low)
        # Mentions pointing at paths to read rather than pasting contents.
        self.assertRegex(self.text, r"(?i)point .*(read|path|file)")


class AgentReturnEnvelopeDocTests(unittest.TestCase):
    """Slice 057-03 AC #2: the subagent return convention is codified in the
    relevant `agents/*.md` — reviewers/implementers return a tight envelope
    (verdict / summary / changed-files), not full logs or transcripts."""

    def test_implementer_return_envelope_present(self):
        text = (REPO_ROOT / "agents" / "implementer.md").read_text().lower()
        self.assertIn("envelope", text)
        # The implementer's tight return covers changed files + the result.
        self.assertIn("changed", text)
        self.assertIn("not full logs", text.replace("-", " "))

    def test_reviewer_return_envelope_present(self):
        text = (REPO_ROOT / "agents" / "reviewer.md").read_text().lower()
        self.assertIn("envelope", text)
        # The reviewer's tight return is verdict + summary, not a transcript.
        self.assertIn("verdict", text)
        self.assertIn("not full logs", text.replace("-", " "))


class SelfDefiningReminderInRenderersTests(unittest.TestCase):
    """Spec 065-04 AC2(b): the self-defining-vocabulary reminder is emitted by
    the DISTRIBUTED workflow.py renderers (`_render_stub_spec` and the inline
    fallback inside `_render_stub_slice`), so an author still meets the reminder
    where they write, whichever renderer runs.

    The original rationale — "a scaffolded project, where
    `templates/docs/specs/slice-template.md` is NOT copied and the inline
    fallback is used" — expired with slice 095-01, which copies `templates/`
    beside the copied machinery, so scaffold mode now renders the real
    template. The class still earns its place: the fallback remains live for
    projects scaffolded before 095-01 and for any unreachable-template case,
    and `_render_stub_spec` has no on-disk template at all. Only the premise
    changed, not the invariant."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO_ROOT / "skills" / "spec-workflow"))
        import importlib
        cls.workflow = importlib.import_module("workflow")

    def test_spec_stub_carries_reminder(self):
        text = self.workflow._render_stub_spec("099", "demo", "2026-06-07")
        self.assertIn("self-defining vocabulary", text.lower())
        self.assertIn("glossary.md", text)

    def test_slice_inline_fallback_carries_reminder(self):
        # Exercise the REAL OSError fallback branch (the path taken in a
        # scaffolded project where templates/ is not distributed): patch
        # Path.read_text to raise so _render_stub_slice falls back to its
        # inline body, then assert that inline body carries the reminder.
        from unittest import mock
        with mock.patch.object(
            self.workflow.Path, "read_text", side_effect=OSError("no template")
        ):
            text = self.workflow._render_stub_slice("099")
        self.assertIn("self-defining vocabulary", text.lower())
        self.assertIn("glossary.md", text)
        self.assertIn("### Deviation log (after reconciliation)", text)
        self.assertIn("### Reconciliation sweep", text)
        self.assertIn("`updated`", text)
        self.assertIn("`no-op`", text)
        self.assertIn("`deferred`", text)
        self.assertIn("`docs/refinement-todo.md`", text)
        # Sanity: substitutions still applied in the fallback path.
        self.assertIn("099-01", text)

    def test_on_disk_slice_template_renders_reminder(self):
        # When the template IS reachable (jig tree), the rendered slice also
        # carries the reminder (parity with the inline fallback).
        text = self.workflow._render_stub_slice("099")
        self.assertIn("self-defining vocabulary", text.lower())


# ---------------------------------------------------------------------------
# Slice 064-04 — derived frame_review trigger + dispatch-gap closure
# ---------------------------------------------------------------------------


class DeriveFrameReviewTests(unittest.TestCase):
    """Slice 064-04 AC1/AC2: `derive_frame_review(spec_path, slice_fragment)`
    derives whether `frame_review: true` should be set — it does NOT read an
    existing flag. The rule (ADR-0020 Option B §3 + Amendments OQ3):

    - ADR target (path under docs/decisions/adr-*.md) → True (always-on).
    - else a spec/slice → True iff its `## Assumptions` section is present
      AND carries >=1 real (non-placeholder) assumption.
    - else → False.

    Conservative + pure: any parse miss / empty / placeholder-only → False
    (default-off, existing specs unaffected).
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-derive-frame-"))
        self.spec = self.tmpdir / "spec.md"
        self.slice_file = self.tmpdir / "slice-04-derive.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, body: str) -> None:
        self.slice_file.write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 064-04 derive\n\n**Goal:** placeholder.\n\n" + body
        )

    # AC2 positive — a real `## Assumptions` bullet flips the trigger on.
    def test_true_for_real_assumption_bullet(self):
        self._write_slice(
            "## Assumptions\n\n"
            "- A1: the foo API returns a list (verified by running it).\n"
        )
        self.assertTrue(
            _workflow.derive_frame_review(self.spec, "064-04"))

    # AC2 positive (REALISTIC) — assumptions live in spec.md per 064-02 (the
    # slice template only *points* at the spec's section). The trigger must
    # read the SPEC-level `## Assumptions`, not only the slice's own.
    def test_true_for_spec_level_assumption(self):
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n\n"
            "## Assumptions\n\n"
            "- A1: the bar lib supports streaming (assumed — not probed).\n\n"
            "## Decomposition\n\n_TBD_\n"
        )
        # The slice itself carries NO `## Assumptions` (the realistic case).
        self._write_slice("**Acceptance Criteria:**\n\n1. Does a thing.\n")
        self.assertTrue(
            _workflow.derive_frame_review(self.spec, "064-04"))

    # AC2 negative — no `## Assumptions` section at all.
    def test_false_when_section_absent(self):
        self._write_slice("## Decomposition\n\nSPIDR.\n")
        self.assertFalse(
            _workflow.derive_frame_review(self.spec, "064-04"))

    # AC2 negative — explicit "None" (the risk-gated empty marker).
    def test_false_for_none_placeholder(self):
        self._write_slice("## Assumptions\n\nNone\n")
        self.assertFalse(
            _workflow.derive_frame_review(self.spec, "064-04"))

    def test_false_for_none_bullet(self):
        self._write_slice("## Assumptions\n\n- None\n")
        self.assertFalse(
            _workflow.derive_frame_review(self.spec, "064-04"))

    # Negative — the stub `_TBD_` / `_TODO_` italic placeholders.
    def test_false_for_tbd_placeholder(self):
        for ph in ("_TBD_", "_TODO_",
                   "_TBD — list load-bearing assumptions; write \"None\"._"):
            with self.subTest(ph=ph):
                self._write_slice(f"## Assumptions\n\n{ph}\n")
                self.assertFalse(
                    _workflow.derive_frame_review(self.spec, "064-04"),
                    f"placeholder {ph!r} must not trigger frame-review")

    # Negative — heading present but body empty.
    def test_false_for_empty_section(self):
        self._write_slice("## Assumptions\n\n## Decomposition\n\nx\n")
        self.assertFalse(
            _workflow.derive_frame_review(self.spec, "064-04"))

    # Section-reader edge — body stops at the next `## ` heading.
    def test_section_body_bounded_by_next_heading(self):
        self._write_slice(
            "## Assumptions\n\n"
            "- A1: real load-bearing assumption.\n\n"
            "## Decomposition\n\n- not an assumption\n"
        )
        self.assertTrue(
            _workflow.derive_frame_review(self.spec, "064-04"))

    # Regression (064-04 craft review) — a REAL assumption that merely
    # *begins* with a placeholder word must NOT be misclassified as a
    # placeholder (the old first-token heuristic false-negatived these and
    # silently suppressed the trigger).
    def test_true_for_assumption_starting_with_placeholder_word(self):
        for bullet in (
            "- None of the dates are timezone-aware (assumed, not probed).",
            "- TBD-style configs are validated at load (assumed).",
            "- Todo items persist across restarts — unverified.",
        ):
            with self.subTest(bullet=bullet):
                self._write_slice(f"## Assumptions\n\n{bullet}\n")
                self.assertTrue(
                    _workflow.derive_frame_review(self.spec, "064-04"),
                    f"real assumption {bullet!r} must trigger frame-review")

    # AC1 — ADR target is always-on (OQ3), regardless of assumptions.
    def test_true_for_adr_path(self):
        adr = self.tmpdir / "adr-0099-some-decision.md"
        adr.write_text(
            "---\nstatus: Proposed\n---\n\n# ADR-0099\n\n## Context\n\nx.\n")
        # Path-based: ADR docs live under docs/decisions/adr-*.md. The
        # deriver keys on the adr-*.md basename, so a sibling decisions path
        # also resolves. We assert on the basename rule directly.
        self.assertTrue(
            _workflow.derive_frame_review(adr, "ADR-0099"))

    def test_true_for_adr_path_in_decisions_dir(self):
        decisions = self.tmpdir / "docs" / "decisions"
        decisions.mkdir(parents=True)
        adr = decisions / "adr-0099-some-decision.md"
        adr.write_text("# ADR-0099\n\n## Context\n\nx.\n")
        self.assertTrue(
            _workflow.derive_frame_review(adr, "ADR-0099"))

    # Conservative — a parse miss (bad slice) is surfaced as an error by the
    # CLI but the helper itself raises (mirrors slice_needs_arch_review).
    def test_raises_on_unknown_slice(self):
        self._write_slice("## Assumptions\n\n- A1: real.\n")
        with self.assertRaises(_workflow.WorkflowError):
            _workflow.derive_frame_review(self.spec, "999-99 nonesuch")


class FrameReviewNeededCLITests(unittest.TestCase):
    """Slice 064-04 AC1/AC2/AC3: `workflow.py frame-review-needed
    <spec.md> <slice-fragment>` prints the DERIVED value (true/false),
    mirroring `arch-review-needed`'s CLI/exit-code shape (non-zero only
    on slice-lookup failure)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-frame-needed-"))
        self.spec = self.tmpdir / "spec.md"
        self.slice_file = self.tmpdir / "slice-04-derive.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, body: str) -> None:
        self.slice_file.write_text(
            "---\nstatus: IN_PROGRESS\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 064-04 derive\n\n**Goal:** placeholder.\n\n" + body
        )

    def test_prints_true_for_real_assumption(self):
        self._write_slice("## Assumptions\n\n- A1: a real assumption.\n")
        r = run_workflow("frame-review-needed", str(self.spec), "064-04")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "true")

    def test_prints_false_for_no_assumptions(self):
        self._write_slice("## Decomposition\n\nx.\n")
        r = run_workflow("frame-review-needed", str(self.spec), "064-04")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(r.stdout.strip(), "false")

    def test_stdout_only_clean_value(self):
        self._write_slice("## Assumptions\n\n- A1: a real assumption.\n")
        r = run_workflow("frame-review-needed", str(self.spec), "064-04")
        self.assertIn(r.stdout, ("true\n", "true"))

    def test_nonzero_exit_on_unknown_slice(self):
        self._write_slice("## Assumptions\n\n- A1: real.\n")
        r = run_workflow("frame-review-needed", str(self.spec), "no-such-slice")
        self.assertNotEqual(r.returncode, 0)


class SessionPlanFramePhaseTests(unittest.TestCase):
    """Slice 064-04 Part B (carried-forward dispatch-gap closure): a slice
    declaring `frame_review: true` gets a PRE-implementation `frame-critique`
    phase emitted FIRST in its session-plan block; an unflagged slice does
    not. Existing arch/code-health phase behavior is unchanged."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-frame-plan-"))
        self.spec = self.tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, fname: str, label: str, status: str = "DRAFT",
                     frame_review: str = None, arch_review: str = None) -> None:
        fm = [f"status: {status}", "dependencies: []", "last_verified:"]
        if frame_review is not None:
            fm.append(f"frame_review: {frame_review}")
        if arch_review is not None:
            fm.append(f"arch_review: {arch_review}")
        block = "---\n" + "\n".join(fm) + "\n---\n\n"
        (self.tmpdir / fname).write_text(
            block + f"## Slice {label}\n\n**Goal:** placeholder.\n"
        )

    def _run(self):
        return run_workflow("session-plan", str(self.spec))

    def test_frame_phase_only_for_flagged_slice(self):
        self._write_slice("slice-01-plain.md", "064-01 plain")
        self._write_slice("slice-02-frame.md", "064-02 frame",
                           frame_review="true")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        out = r.stdout
        self.assertIn("frame-critique", out)
        idx_plain = out.index("064-01 plain")
        idx_frame = out.index("064-02 frame")
        plain_block = out[idx_plain:idx_frame]
        frame_block = out[idx_frame:]
        self.assertNotIn("frame-critique", plain_block,
                         "plain slice must NOT include the frame-critique phase")
        self.assertIn("frame-critique", frame_block,
                      "frame_review:true slice must include frame-critique")

    def test_frame_phase_emitted_before_implement(self):
        self._write_slice("slice-01-frame.md", "064-01 frame",
                           frame_review="true")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # Scope to the per-slice block (the preamble also says "implement").
        out = r.stdout[r.stdout.index("064-01 frame"):]
        self.assertIn("frame-critique", out)
        self.assertIn("implement", out)
        self.assertLess(out.index("frame-critique"), out.index("implement"),
                        "frame-critique must precede implement (pre-impl gate)")

    def test_frame_phase_notes_pre_implementation(self):
        self._write_slice("slice-01-frame.md", "064-01 frame",
                           frame_review="true")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        low = r.stdout.lower()
        self.assertIn("frame_review", low)
        self.assertTrue(
            "pre-implementation" in low or "ready_for_review" in low,
            "frame-critique note should signal it is the pre-impl gate")

    def test_frame_phase_truthy_variations(self):
        for truthy in ("yes", "True", "1", "on"):
            with self.subTest(truthy=truthy):
                self._write_slice("slice-01-frame.md", "064-01 frame",
                                  frame_review=truthy)
                r = self._run()
                self.assertEqual(r.returncode, 0, msg=r.stderr)
                self.assertIn("frame-critique", r.stdout)

    # Regression — unflagged slice's existing output is unchanged (no
    # frame-critique phase appears).
    def test_unflagged_slice_has_no_frame_phase(self):
        self._write_slice("slice-01-plain.md", "064-01 plain")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertNotIn("frame-critique", r.stdout)

    # Regression — arch phase still fires independently of frame phase.
    def test_arch_phase_unchanged_alongside_frame(self):
        self._write_slice("slice-01-both.md", "064-01 both",
                           frame_review="true", arch_review="true")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        out = r.stdout
        self.assertIn("frame-critique", out)
        self.assertIn("arch-review", out)
        # frame is pre-implement; arch is post-craft → frame precedes arch.
        self.assertLess(out.index("frame-critique"), out.index("arch-review"))


class FrameReviewSkillDocTests(unittest.TestCase):
    """Slice 064-04 AC3: SKILL.md '### Creating a new spec' frames
    frame_review as a DERIVATION from the surfaced assumptions, not a
    human 'is frame-review needed?' decision; mentions ADRs are always-on
    and points at `frame-review-needed`."""

    def setUp(self):
        self.text = (REPO_ROOT / "skills" / "spec-workflow"
                     / "SKILL.md").read_text()

    def test_mentions_frame_review_derivation(self):
        low = self.text.lower()
        self.assertIn("frame_review", low)
        self.assertIn("frame-review-needed", low)

    def test_framed_as_derivation_not_decision(self):
        low = self.text.lower()
        # The contract must say the assumptions decide — not ask the author.
        self.assertTrue(
            "you are not asked" in low or "not a human" in low
            or "the assumptions" in low and "decide" in low,
            "SKILL.md must frame frame_review as derived, not a human call")

    def test_mentions_adrs_always_on(self):
        low = self.text.lower()
        self.assertIn("adr", low)


# ---------------------------------------------------------------------------
# Slice 068-03 — reconcile-coverage-grounding (bidirectional coverage check)
# ---------------------------------------------------------------------------


class CoverageTests(unittest.TestCase):
    """Slice 068-03: `workflow.py coverage` is a read-only, advisory,
    project-wide BIDIRECTIONAL use-case coverage check — a deterministic
    set-difference over slice 02's `use_cases:` trace links. It reports
    use cases with no implementing spec (coverage GAP) and specs with no
    parent use case (scope CREEP), is computed from frontmatter metadata
    (not prose re-read), is no-op when the project has no `## Use cases`
    section, and NEVER blocks (always exits 0). Sibling of `stale` /
    `routing-stats` / `amendments`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-coverage-")
        self.proj = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, rel: str, text: str) -> None:
        p = self.proj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def _vision(self, body: str) -> None:
        """Write docs/product-vision.md with the given trailing body."""
        self._write("docs/product-vision.md",
                    "# Vision\n\nIntro prose.\n\n" + body)

    def _three_uc_vision(self) -> None:
        self._vision(
            "## Use cases\n\n"
            "- UC-1: A crafter can search for a yarn by name\n"
            "- UC-2: A crafter can save a project to their stash\n"
            "- UC-3: A crafter can share a pattern with a friend\n"
        )

    def _spec(self, dirname: str, use_cases_line: str,
              prose: str = "Spec body prose.") -> None:
        """Write docs/specs/<dirname>/spec.md with a `use_cases:` line."""
        self._write(
            f"docs/specs/{dirname}/spec.md",
            f"---\nstatus: DONE\n{use_cases_line}\n---\n\n"
            f"# {dirname}\n\n## Overview\n\n{prose}\n",
        )

    # ---- AC1: bidirectional — gap AND scope-creep both surface --------------

    def test_reports_gap_and_scope_creep_both_directions(self):
        self._three_uc_vision()
        # UC-1 cited (resolved); UC-2 cited by nobody (→ gap); UC-3 cited.
        self._spec("100-search", "use_cases: [UC-1]")
        self._spec("101-share", "use_cases: [UC-3]")
        # Orphan spec: cites nothing → scope creep.
        self._spec("102-internal-refactor", "use_cases: []")
        report = _workflow.coverage(self.proj)
        # Direction 1: coverage gap names UC-2 (uncited use case).
        self.assertIn("UC-2", report)
        self.assertIn("save a project to their stash", report,
                      "gap must render the UC goal text, not just the id")
        # Direction 2: scope creep names the orphan spec.
        self.assertIn("102-internal-refactor", report)
        # A covered use case (UC-1, UC-3) must NOT appear as a gap. Bound to
        # the coverage-gap section, since the ids legitimately appear in the
        # specs they resolve from elsewhere in the report.
        low = report.lower()
        gap_start = low.index("coverage gap")
        gap_section = report[gap_start:]
        for marker in ("scope creep", "unresolvable", "summary"):
            if marker in gap_section.lower():
                gap_section = gap_section[:gap_section.lower().index(marker)]
                break
        self.assertNotIn("UC-1", gap_section,
                         "a covered use case must not be a coverage gap")
        self.assertNotIn("UC-3", gap_section)

    def test_both_finding_sections_present_in_report(self):
        self._three_uc_vision()
        self._spec("100-search", "use_cases: [UC-1]")
        self._spec("102-internal-refactor", "use_cases: []")
        report = _workflow.coverage(self.proj).lower()
        self.assertIn("coverage gap", report)
        self.assertIn("scope creep", report)

    # ---- AC2: query (frontmatter), NOT prose re-read ------------------------

    def test_scope_creep_from_metadata_not_prose(self):
        """A spec whose PROSE mentions a use case but whose `use_cases:` list
        is empty must still show as scope creep — proving the check reads the
        link metadata (AC2), never the prose."""
        self._three_uc_vision()
        # Cover UC-2/UC-3 elsewhere so the only finding is the orphan.
        self._spec("100-a", "use_cases: [UC-1, UC-2]")
        self._spec("101-b", "use_cases: [UC-3]")
        self._write(
            "docs/specs/102-prose-only/spec.md",
            "---\nstatus: DONE\nuse_cases: []\n---\n\n"
            "# 102\n\n## Overview\n\nThis spec implements UC-1: search "
            "for a yarn. It clearly serves a stated use case in prose.\n",
        )
        report = _workflow.coverage(self.proj)
        self.assertIn("102-prose-only", report,
                      "scope creep must be computed from `use_cases:` "
                      "metadata, not prose mentions")

    def test_bare_use_cases_key_counts_as_no_citation(self):
        """A bare `use_cases:` (parses to '') is 'no citations', same as
        `use_cases: []` — both → scope creep."""
        self._three_uc_vision()
        self._spec("100-a", "use_cases: [UC-1, UC-2, UC-3]")
        self._write(
            "docs/specs/103-bare/spec.md",
            "---\nstatus: DONE\nuse_cases:\n---\n\n# 103\n\n## Overview\n\nx.\n",
        )
        report = _workflow.coverage(self.proj)
        self.assertIn("103-bare", report)

    # ---- AC3: advisory — CLI exits 0 even with findings ---------------------

    def test_cli_exits_zero_with_findings(self):
        self._three_uc_vision()
        self._spec("100-search", "use_cases: [UC-1]")  # UC-2/UC-3 are gaps
        self._spec("102-orphan", "use_cases: []")
        r = run_workflow("coverage", "--project-dir", str(self.proj))
        self.assertEqual(r.returncode, 0,
                         f"coverage is advisory; must exit 0. stderr: {r.stderr}")
        self.assertIn("UC-2", r.stdout)
        self.assertIn("102-orphan", r.stdout)

    def test_report_banner_marks_advisory_nonblocking(self):
        self._three_uc_vision()
        self._spec("100-search", "use_cases: [UC-1]")
        report = _workflow.coverage(self.proj).lower()
        self.assertIn("advisory", report)
        self.assertTrue(
            "non-blocking" in report or "does not block" in report
            or "never blocks" in report,
            "report must state it is non-blocking",
        )

    # ---- AC4 / honesty: unresolvable citations are reported -----------------

    def test_reports_unresolvable_trace_link(self):
        """A spec citing UC-9 (absent from the vision) is a dangling link —
        surfaced as a distinct, minor third category, never silently dropped."""
        self._three_uc_vision()
        self._spec("100-search", "use_cases: [UC-1, UC-2, UC-3]")  # cover all
        self._spec("104-typo", "use_cases: [UC-9]")
        report = _workflow.coverage(self.proj)
        self.assertIn("UC-9", report)
        self.assertIn("104-typo", report)
        self.assertIn("unresolvable", report.lower())

    def test_unresolvable_spec_not_also_scope_creep(self):
        """A spec that DOES cite (even a bad id) is not 'no parent use case' —
        it cited one, it just doesn't resolve. It must read as unresolvable,
        not scope creep."""
        self._three_uc_vision()
        self._spec("100-search", "use_cases: [UC-1, UC-2, UC-3]")
        self._spec("104-typo", "use_cases: [UC-9]")
        report = _workflow.coverage(self.proj)
        creep_section = ""
        low = report.lower()
        if "scope creep" in low:
            start = low.index("scope creep")
            creep_section = report[start:]
            # bound to the next section heading if present
            for marker in ("unresolvable", "summary", "✓"):
                if marker in creep_section.lower():
                    creep_section = creep_section[
                        :creep_section.lower().index(marker)]
                    break
        self.assertNotIn("104-typo", creep_section,
                         "a spec that cited a (bad) id is unresolvable, "
                         "not scope creep")

    # ---- NO_SECTION no-op (the jig-self / opted-out case) -------------------

    def test_no_use_cases_section_is_noop(self):
        """A vision with NO `## Use cases` section → no-op note, ZERO
        findings, exit 0. This is exactly jig's own repo and opted-out
        project classes (libraries / single-flow CLIs)."""
        self._vision("## Some other section\n\nNot use cases.\n")
        self._spec("100-x", "use_cases: []")  # would be creep IF adopted
        report = _workflow.coverage(self.proj)
        low = report.lower()
        self.assertIn("no-op", low.replace("noop", "no-op"))
        self.assertNotIn("coverage gap", low)
        self.assertNotIn("scope creep", low)
        self.assertNotIn("100-x", report)
        r = run_workflow("coverage", "--project-dir", str(self.proj))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    def test_absent_vision_file_is_skipped(self):
        """No docs/product-vision.md at all → advisory 'skipped' note, no
        crash, exit 0."""
        self._spec("100-x", "use_cases: [UC-1]")
        report = _workflow.coverage(self.proj)
        self.assertIn("vision", report.lower())
        r = run_workflow("coverage", "--project-dir", str(self.proj))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")

    # ---- Clean case: every UC covered + every spec resolvable ---------------

    def test_clean_when_fully_covered(self):
        self._three_uc_vision()
        self._spec("100-search", "use_cases: [UC-1]")
        self._spec("101-stash", "use_cases: [UC-2]")
        self._spec("102-share", "use_cases: [UC-3]")
        report = _workflow.coverage(self.proj)
        self.assertIn("✓", report)  # ✓ clean marker
        self.assertIn("clean", report.lower())
        # A clean report still exits 0 via the CLI.
        r = run_workflow("coverage", "--project-dir", str(self.proj))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")


class ProjectOrientationTests(unittest.TestCase):
    """Slice 088-01: project-level orientation before slice pickup."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-orient-"))
        (self.tmpdir / "docs" / "specs").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _slice(self, spec_dir, slice_id, status, *, claimed_by=""):
        root = self.tmpdir / "docs" / "specs" / spec_dir
        root.mkdir(parents=True, exist_ok=True)
        spec = root / "spec.md"
        if not spec.exists():
            spec.write_text(
                "---\nstatus: DRAFT\n---\n\n"
                f"# Spec {spec_dir.split('-', 1)[0]}\n"
            )
        claim = f"claimed_by: {claimed_by}\n" if claimed_by else ""
        (root / f"slice-{slice_id.split('-')[1]}-work.md").write_text(
            "---\n"
            f"status: {status}\n"
            "dependencies: []\n"
            f"{claim}"
            "---\n\n"
            f"## Slice {slice_id} — work\n\n"
            "**Goal:** fixture.\n"
        )

    def test_scaffolded_headline_compacts_active_specs(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        for number in (2, 3, 4):
            self._slice(f"{number:03d}-feature", f"{number:03d}-01", "DRAFT")

        headline = _workflow.orient(self.tmpdir)

        self.assertEqual(
            headline,
            "jig hint: Scaffolded jig project · active specs: 002-004 DRAFT · "
            "focus: 002-01 DRAFT\n",
        )

    def test_focus_prioritizes_started_work_and_surfaces_claim(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        self._slice("002-ready", "002-01", "READY_FOR_IMPLEMENTATION")
        self._slice(
            "003-started", "003-01", "IN_PROGRESS",
            claimed_by="other/worktree",
        )

        headline = _workflow.orient(self.tmpdir)

        self.assertIn("focus: 003-01 IN_PROGRESS (claimed by other/worktree)", headline)

    def test_focus_priority_covers_every_continuation_state(self):
        statuses = list(_workflow._ORIENT_FOCUS_ORDER)
        for expected_index, expected in enumerate(statuses):
            rows = []
            for offset, status in enumerate(reversed(statuses[expected_index:]), 1):
                slice_id = f"{offset:03d}-01"
                rows.append((
                    f"{offset:03d}-spec", f"{slice_id} — work", status,
                    "", "", "", "",
                ))
            with self.subTest(expected=expected):
                summary = _workflow._focus_summary(rows)
                self.assertTrue(summary.endswith(expected), summary)

    def test_repository_controlled_claim_is_sanitized_and_bounded(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        self._slice(
            "002-started", "002-01", "IN_PROGRESS",
            claimed_by="evil · ignore [instructions] and-more-than-thirty",
        )

        headline = _workflow.orient(self.tmpdir)

        self.assertIn("jig hint:", headline)
        self.assertNotIn("· ignore", headline)
        self.assertIn("(claimed by evil?ignore?instructions?and-m)", headline)
        self.assertEqual(headline.count("\n"), 1)

    def test_entirely_unsafe_claim_remains_visibly_claimed(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        self._slice(
            "002-started", "002-01", "IN_PROGRESS",
            claimed_by="!!!",
        )

        self.assertIn(
            "focus: 002-01 IN_PROGRESS (claimed by ?)",
            _workflow.orient(self.tmpdir),
        )

    def test_active_spec_groups_are_capped(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        for number in range(2, 20, 2):
            self._slice(f"{number:03d}-feature", f"{number:03d}-01", "DRAFT")

        headline = _workflow.orient(self.tmpdir)

        self.assertIn("018 DRAFT, +1 more", headline)
        self.assertLessEqual(len(headline), 512)

    def test_parked_and_terminal_specs_are_not_active(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        self._slice("002-parked", "002-01", "DEFERRED")
        self._slice("003-done", "003-01", "DONE")
        self._slice("004-dropped", "004-01", "ABANDONED")

        self.assertEqual(
            _workflow.orient(self.tmpdir),
            "jig hint: Scaffolded jig project · active specs: none · focus: none\n",
        )

    def test_cli_is_read_only_and_does_not_guess_application_state(self):
        (self.tmpdir / "scaffold.json").write_text("{}\n")
        (self.tmpdir / "docs" / "architecture.md").write_text("# Architecture\n")
        self._slice("002-app", "002-01", "READY_FOR_IMPLEMENTATION")
        installed = (
            self.tmpdir / ".claude" / "skills" / "jig-spec-workflow"
            / "workflow.py"
        )
        installed.parent.mkdir(parents=True)
        import shutil
        shutil.copy2(WORKFLOW, installed)
        shutil.copytree(
            REPO_ROOT / "skills" / "_common",
            self.tmpdir / ".claude" / "skills" / "_common",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        before = {
            path.relative_to(self.tmpdir): path.read_bytes()
            for path in self.tmpdir.rglob("*") if path.is_file()
        }

        result = subprocess.run(
            [
                sys.executable, str(installed), "orient",
                "--project-dir", str(self.tmpdir),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Scaffolded jig project", result.stdout)
        self.assertNotRegex(result.stdout.lower(), r"app(lication)? skeleton|tech(nology)? stack")
        after = {
            path.relative_to(self.tmpdir): path.read_bytes()
            for path in self.tmpdir.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
