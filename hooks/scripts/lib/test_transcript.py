import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcript import messages_from_payload, read_transcript


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-transcript-"))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)

    def test_reads_supported_nested_jsonl_records(self):
        path = self.tmp / "session.jsonl"
        path.write_text("\n".join([
            json.dumps({"type": "user", "message": {
                "role": "user", "content": "Use a banner instead."}}),
            json.dumps({"type": "assistant", "message": {
                "role": "assistant", "content": [
                    {"type": "text", "text": "We should also test it."},
                    {"type": "tool_use", "name": "edit"},
                ]}}),
        ]) + "\n")
        self.assertEqual(
            messages_from_payload({"transcript_path": str(path)}, str(self.tmp)),
            [
                {"role": "user", "content": "Use a banner instead."},
                {"role": "assistant", "content": ["We should also test it."]},
            ],
        )

    def test_inline_messages_win_without_reading_transcript(self):
        self.assertEqual(
            messages_from_payload({"messages": [{"role": "assistant",
                                                  "content": "inline"}],
                                   "transcript_path": "/no/such/file"},
                                  str(self.tmp)),
            [{"role": "assistant", "content": "inline"}],
        )

    def test_rejects_out_of_workspace_path(self):
        outside = self.tmp.parent / "outside.jsonl"
        outside.write_text(json.dumps({"role": "assistant", "content": "TODO: x"}) + "\n")
        self.addCleanup(outside.unlink)
        self.assertIsNone(read_transcript(str(outside), str(self.tmp)))

    def test_malformed_and_unknown_records_are_ignored(self):
        path = self.tmp / "bad.jsonl"
        path.write_text("not json\n" + json.dumps({"type": "tool_result"}) + "\n")
        self.assertEqual(read_transcript(str(path), str(self.tmp)), [])

    def test_missing_or_oversized_input_is_rejected(self):
        self.assertIsNone(read_transcript("", str(self.tmp)))
        path = self.tmp / "large.jsonl"
        path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        self.assertIsNone(read_transcript(str(path), str(self.tmp)))


if __name__ == "__main__":
    unittest.main()
