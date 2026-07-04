"""Unit tests for skills/_common/gate_telemetry.py (spec 078-01)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common.gate_telemetry import emit_gate_bypass, read_spec_ref  # noqa: E402


def _read_log(project_dir: Path):
    log = Path(project_dir) / ".claude" / "skill-usage.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]


class EmitGateBypassTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-gate-telemetry-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_appends_content_free_event(self):
        emit_gate_bypass(self.project, "review-evidence",
                          "JIG_REVIEW_EVIDENCE_GATE")
        entries = _read_log(self.project)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["event"], "gate_bypassed")
        self.assertEqual(entry["gate"], "review-evidence")
        self.assertEqual(entry["env_var"], "JIG_REVIEW_EVIDENCE_GATE")
        self.assertIn("timestamp", entry)
        self.assertNotIn("spec_ref", entry)

    def test_includes_spec_ref_when_given(self):
        emit_gate_bypass(self.project, "conventions",
                          "JIG_CONVENTIONS_APPROVED", spec_ref="078")
        entries = _read_log(self.project)
        self.assertEqual(entries[0]["spec_ref"], "078")

    def test_appends_rather_than_overwrites(self):
        emit_gate_bypass(self.project, "review-evidence",
                          "JIG_REVIEW_EVIDENCE_GATE")
        emit_gate_bypass(self.project, "conventions",
                          "JIG_CONVENTIONS_APPROVED")
        gates = [e["gate"] for e in _read_log(self.project)]
        self.assertEqual(gates, ["review-evidence", "conventions"])

    def test_creates_claude_dir_if_absent(self):
        self.assertFalse((self.project / ".claude").exists())
        emit_gate_bypass(self.project, "conventions",
                          "JIG_CONVENTIONS_APPROVED")
        self.assertTrue((self.project / ".claude" / "skill-usage.jsonl").is_file())

    def test_fail_open_when_sink_unwritable(self):
        # Make the target path a directory instead of a file, so open(path,
        # "a") raises — the write must be swallowed, never raised.
        log_dir = self.project / ".claude"
        log_dir.mkdir(parents=True)
        (log_dir / "skill-usage.jsonl").mkdir()
        try:
            emit_gate_bypass(self.project, "conventions",
                              "JIG_CONVENTIONS_APPROVED")
        except Exception as exc:  # pragma: no cover - defensive
            self.fail(f"emit_gate_bypass must never raise; raised {exc!r}")


class ReadSpecRefTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-gate-telemetry-ref-")
        self.project = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_reads_spec_from_marker(self):
        jig_dir = self.project / ".jig"
        jig_dir.mkdir()
        (jig_dir / "spec-ref").write_text("spec=078\nslice=078-01\n")
        self.assertEqual(read_spec_ref(self.project), "078")

    def test_absent_marker_returns_empty(self):
        self.assertEqual(read_spec_ref(self.project), "")

    def test_marker_without_spec_line_returns_empty(self):
        jig_dir = self.project / ".jig"
        jig_dir.mkdir()
        (jig_dir / "spec-ref").write_text("slice=078-01\n")
        self.assertEqual(read_spec_ref(self.project), "")


if __name__ == "__main__":
    unittest.main()
