"""Regression tests for spec 039 review-queue cleanup."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ".claude/review-queue.json"


class ReviewQueueCleanupTests(unittest.TestCase):
    def test_implementer_agent_does_not_write_review_queue(self):
        text = (ROOT / "agents" / "implementer.md").read_text()
        self.assertNotIn(QUEUE, text)
        self.assertIn("Report the deliverable paths", text)

    def test_stale_review_queue_file_removed(self):
        self.assertFalse(
            (ROOT / QUEUE).exists(),
            "stale review queue must not remain in the repository",
        )

    def test_gitignore_blocks_future_review_queue_file(self):
        lines = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn(QUEUE, lines)

    def test_no_live_runtime_references_to_review_queue(self):
        live_roots = [
            ROOT / "agents",
            ROOT / "hooks",
            ROOT / "scripts",
            ROOT / "skills",
            ROOT / "templates",
        ]
        offenders = []
        for base in live_roots:
            for path in base.rglob("*"):
                if path == Path(__file__).resolve() or not path.is_file():
                    continue
                if "__pycache__" in path.parts:
                    continue
                try:
                    text = path.read_text()
                except UnicodeDecodeError:
                    continue
                if QUEUE in text:
                    offenders.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
