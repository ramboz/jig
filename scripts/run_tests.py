"""
Run all jig tests: one test per skill directory + the scripts directory.

Usage:
    python3 scripts/run_tests.py

This is the command pointed to by .jig/test-command, so:
    python3 skills/tdd-loop/tdd.py run .
...runs this script instead of trying to invoke pytest directly.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Ensure namespace-package imports (e.g. `from skills.migrate import migrate`) work.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
loader = unittest.TestLoader()
suite = unittest.TestSuite()

for skill_dir in sorted((ROOT / "skills").iterdir()):
    if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
        suite.addTests(loader.discover(start_dir=str(skill_dir), pattern="test_*.py"))

suite.addTests(loader.discover(start_dir=str(ROOT / "scripts"), pattern="test_*.py"))

result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
