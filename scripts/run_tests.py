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
    if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
        continue
    # Python 3.11's unittest.discover raises ImportError on a dir with no
    # Python files (Python 3.12 silently returns an empty suite). Skip skill
    # dirs that have no test_*.py to keep both versions happy.
    if not any(skill_dir.glob("test_*.py")):
        continue
    # Skill directories use hyphens in their names (e.g. `independent-review`)
    # which are not valid Python module identifiers. Python 3.11's
    # unittest.discover rejects such directories as "not importable" unless
    # `top_level_dir == start_dir`, in which case the importability check is
    # skipped. Python 3.12 is more lenient. Pin `top_level_dir` to make both
    # versions behave identically.
    suite.addTests(loader.discover(
        start_dir=str(skill_dir),
        pattern="test_*.py",
        top_level_dir=str(skill_dir),
    ))

suite.addTests(loader.discover(
    start_dir=str(ROOT / "scripts"),
    pattern="test_*.py",
    top_level_dir=str(ROOT / "scripts"),
))

result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
