"""Spec 124-01 / ADR-0069: the `owner_review` flag in `workflow.py` — the
`REVIEWED` gate, `owner-review-needed`, and `session-plan`.

Run from the repo root:
    python3 skills/spec-workflow/test_owner_review_pass.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"

OWNER_BODY = ("VERDICT: pass\n\nTRIED: saved an entry\n\n"
              "SURFACE: Pixel 8\n\nOWNER SAID:\n> good\n")


def run_workflow(*args):
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
           "JIG_CROSSREF_GATE": "0", "JIG_START_COLLISION_GATE": "0"}
    env.pop("JIG_REVIEW_EVIDENCE_GATE", None)
    return subprocess.run([sys.executable, str(WORKFLOW), *args],
                          capture_output=True, text=True, env=env)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-owner-wf-"))
        self.spec_dir = self.tmp / "docs" / "specs" / "900-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text("---\nstatus: IN_PROGRESS\n---\n\n# Spec\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_slice(self, flag=None, status="IN_PROGRESS", extra=""):
        fm = f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n"
        if flag is not None:
            fm += f"owner_review: {flag}\n"
        (self.spec_dir / "slice-01-thing.md").write_text(
            fm + extra + "---\n\n## Slice 900-01 — thing\n\n**Goal:** x.\n")

    def write_evidence(self, pass_name, verdict="pass",
                       body="VERDICT: pass\n"):
        reviews = self.spec_dir / "reviews"
        reviews.mkdir(exist_ok=True)
        (reviews / f"slice-01-{pass_name}.md").write_text(
            "---\nslice: 900-01 — thing\n"
            f"pass: {pass_name}\nverdict: {verdict}\nreviewer: r\n"
            "reviewed_at: 2026-11-20T10:00:00Z\nprompt_source: review.py x\n"
            "---\n\n" + body)


class GateTests(Base):
    def test_flagged_slice_is_refused_without_the_owner_verdict(self):
        self.write_slice("true")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec), "900-01", "REVIEWED")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("owner-review", r.stderr)
        self.assertIn("status: IN_PROGRESS",
                      (self.spec_dir / "slice-01-thing.md").read_text())

    def test_flagged_slice_clears_with_the_owner_verdict(self):
        self.write_slice("true")
        for name in ("compliance", "craft"):
            self.write_evidence(name)
        self.write_evidence("owner-review", body=OWNER_BODY)
        r = run_workflow("transition", str(self.spec), "900-01", "REVIEWED")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_unflagged_slice_is_unaffected(self):
        for flag in (None, "false"):
            self.write_slice(flag)
            self.write_evidence("compliance")
            self.write_evidence("craft")
            r = run_workflow("transition", str(self.spec), "900-01",
                             "REVIEWED")
            self.assertEqual(r.returncode, 0, (flag, r.stderr))

    def test_done_rechecks_the_owner_verdict(self):
        self.write_slice("true", status="RECONCILED")
        slice_file = self.spec_dir / "slice-01-thing.md"
        slice_file.write_text(
            slice_file.read_text()
            + "\n### Deviation log\n\nNone.\n\n### Reconciliation sweep\n\n"
              "| Artifact | Disposition | Rationale |\n|---|---|---|\n"
              "| `README.md` | `no-op` | checked |\n")
        for name in ("compliance", "craft", "reconciliation"):
            self.write_evidence(name)
        r = run_workflow("transition", str(self.spec), "900-01", "DONE")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("owner-review", r.stderr)
        self.write_evidence("owner-review", body=OWNER_BODY)
        r = run_workflow("transition", str(self.spec), "900-01", "DONE")
        self.assertEqual(r.returncode, 0, r.stderr)


class NeededTests(Base):
    def test_prints_true_only_for_a_truthy_flag(self):
        for flag, expected in (("true", "true"), ("yes", "true"),
                               ("false", "false"), (None, "false")):
            self.write_slice(flag)
            r = run_workflow("owner-review-needed", str(self.spec), "900-01")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), expected, flag)

    def test_unknown_slice_is_an_error(self):
        self.write_slice("true")
        r = run_workflow("owner-review-needed", str(self.spec), "999-99")
        self.assertNotEqual(r.returncode, 0)


class SessionPlanTests(Base):
    def _phases(self, out):
        return re.findall(r"^\s+\d+\. ([a-z-]+) — ", out, re.MULTILINE)

    def test_flagged_slice_lists_the_owner_right_after_implement(self):
        self.write_slice("true", extra="arch_review: true\n")
        r = run_workflow("session-plan", str(self.spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            self._phases(r.stdout),
            ["implement", "owner-review", "compliance", "craft", "arch",
             "reconcile", "land"])
        line = next(ln for ln in r.stdout.splitlines()
                    if "owner-review — " in ln)
        self.assertIn("WAITING ON THE OWNER", line)
        self.assertIn("in parallel", line)
        self.assertIn("review.py owner-review", line)
        self.assertIn("host-mode hint: review; advisory only", line)
        self.assertNotIn("DELEGATE", line)

    def test_unflagged_slice_plan_is_unchanged(self):
        for flag in (None, "false"):
            self.write_slice(flag)
            r = run_workflow("session-plan", str(self.spec))
            self.assertEqual(
                self._phases(r.stdout),
                ["implement", "compliance", "craft", "reconcile", "land"])
            self.assertNotIn("owner-review — ", r.stdout)


if __name__ == "__main__":
    unittest.main()
