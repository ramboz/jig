"""
Tests that docs/prompts.md is a usable prompt cookbook (spec 054-02).

Mechanical ACs; prose/usability quality is the reviewer's call.

- AC#1 — exists, single H1, no forward-broken relative links.
- AC#2 — a scaffold recipe (the scaffold-init command appears).
- AC#3 — a full spec-loop recipe (draft → implement → review → reconcile → land).
- AC#4 — copy-paste fenced blocks (>= 6).
- AC#5 — every /jig:<cmd> referenced is a real jig skill (no invented commands).

Run:
    python3 scripts/test_prompt_cookbook.py
    # or from repo root:
    python3 -m unittest scripts.test_prompt_cookbook
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
COOKBOOK = DOCS / "prompts.md"

# The only valid /jig:<name> commands — jig's real skills.
KNOWN_COMMANDS = {
    "scaffold-init", "vision-elicitation", "memory-sync", "spec-workflow",
    "independent-review", "contracts", "adr-workflow", "tdd-loop",
    "slice-land", "migrate", "pr-review", "arch-review", "clarify", "analyze",
}
JIG_CMD_RE = re.compile(r"/jig:([a-z][a-z0-9-]*)")
REL_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")
# The spec-loop recipe must walk these phases (matched case-insensitively).
LOOP_PHASES = ("spec", "implement", "review", "reconcile", "land")


def _read() -> str:
    return COOKBOOK.read_text(encoding="utf-8")


class CookbookExists(unittest.TestCase):
    def test_exists(self) -> None:
        self.assertTrue(
            COOKBOOK.is_file(), "docs/prompts.md must exist (054-02 AC#1)"
        )

    def test_single_h1(self) -> None:
        h1s = [ln for ln in _read().splitlines() if ln.startswith("# ")]
        self.assertEqual(len(h1s), 1, f"one H1 expected; found {len(h1s)}")


class CookbookLinksResolve(unittest.TestCase):
    """AC#1: no forward-broken relative links."""

    def test_relative_links_resolve(self) -> None:
        for target in REL_LINK_RE.findall(_read()):
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            with self.subTest(link=target):
                self.assertTrue(
                    (DOCS / path_part).resolve().is_file(),
                    f"prompts.md links {target!r} which does not exist (AC#1)",
                )


class CookbookScaffoldRecipe(unittest.TestCase):
    """AC#2."""

    def test_has_scaffold_recipe(self) -> None:
        self.assertIn("scaffold", _read().lower())
        self.assertIn(
            "/jig:scaffold-init", _read(),
            "scaffold recipe must show the scaffold-init command (AC#2)",
        )


class CookbookSpecLoopRecipe(unittest.TestCase):
    """AC#3."""

    def test_walks_full_loop(self) -> None:
        low = _read().lower()
        for phase in LOOP_PHASES:
            with self.subTest(phase=phase):
                self.assertIn(
                    phase, low,
                    f"spec-loop recipe must cover the {phase!r} phase (AC#3)",
                )

    def test_reaches_landing(self) -> None:
        self.assertIn(
            "/jig:slice-land", _read(),
            "spec-loop recipe must reach landing (AC#3)",
        )


class CookbookHasCopyPasteBlocks(unittest.TestCase):
    """AC#4."""

    def test_has_fenced_blocks(self) -> None:
        blocks = _read().count("```") // 2
        self.assertGreaterEqual(
            blocks, 6,
            f"cookbook needs copy-paste fenced blocks; found {blocks} (AC#4)",
        )


class CookbookOnlyRealCommands(unittest.TestCase):
    """AC#5: no invented commands."""

    def test_no_invented_commands(self) -> None:
        for cmd in sorted(set(JIG_CMD_RE.findall(_read()))):
            with self.subTest(cmd=cmd):
                self.assertIn(
                    cmd, KNOWN_COMMANDS,
                    f"prompts.md references /jig:{cmd}, which is not a real jig "
                    f"skill (AC#5 — no invented commands)",
                )


if __name__ == "__main__":
    unittest.main()
