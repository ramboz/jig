#!/usr/bin/env python3
"""
jig tdd-loop test-quality preflight.

Computes deterministic, numerical-ratio signals from a Python test diff so
Claude's TDD-loop judgment has machine-readable evidence to anchor on.
Stdlib-only (argparse, re, subprocess, sys). Designed to complement
`tdd.py` — `tdd.py` runs the suite; this script characterizes what the
diff added.

Patterns are pytest-focused (the most common runner in jig and the only
one with explicit detection in `tdd.py`). The YAML schema and signal
names are deliberately language-agnostic — if jig grows JS/TS test
patterns later, the script can extend rather than fork.

Usage:
    quality.py [--diff-file PATH]            # read a cached unified diff
    quality.py [--against REF]               # git diff against a ref (default: HEAD)

Output: YAML block to stdout. Schema version 1.
"""

import argparse
import re
import subprocess
import sys

SCHEMA_VERSION = 1

# Threshold constants. Calibrated against a 25-commit jig sample in
# slice 043-02 (threshold-calibration spike). assertion-thin was tuned
# 1.5 → 1.0 to stop firing on focused-single-concept surface tests,
# which is jig's normal style and not a defect. per-code-file-flood
# was tuned 30 → 50 so it catches genuine test dumping, not thoughtful
# coverage of an enum or body-shape validator. per-file-flood-max
# (100) and mock-heavy (5.0) saw no fires in the sample but are kept
# as cross-language backstops.
#
# NB: the sample was Python-only. JS/TS and Java diffs may have
# different natural distributions; slice 043-03 (polyglot extension)
# should re-calibrate before relying on these values cross-language.
THR_PER_FILE_FLOOD_MAX = 100
THR_PER_CODE_FILE_FLOOD = 50
THR_ASSERTION_THIN = 1.0
THR_ASSERTION_THIN_MIN_TESTS = 20
THR_MOCK_HEAVY = 5.0
THR_MOCK_HEAVY_MIN_TESTS = 10

# Path classification — Python-flavoured.
TEST_PATH_REGEX = re.compile(
    r"(^|/)(test|tests)/|"
    r"(^|/)test_[^/]+\.py$|"
    r"(^|/)[^/]+_test\.py$"
)
DOCS_PATH_REGEX = re.compile(r"\.md$|^docs/")
# A code path classified as Python source — used as the denominator for
# test-to-code-ratio. Non-Python source ends up as `other` for now (the
# ratio is meaningful only when both sides are the same language).
CODE_PATH_REGEX = re.compile(r"\.py$")

# Line-level regexes. All run only against `+` (added) or `-` (removed)
# lines of the unified diff. Each is anchored with `^[+-]\s*` so
# commented-out and trailing-position occurrences do not count.
TEST_BLOCK_ADDED = re.compile(
    r"^\+\s*(async\s+)?def\s+test_\w+\s*\("
)
TEST_BLOCK_REMOVED = re.compile(
    r"^-\s*(async\s+)?def\s+test_\w+\s*\("
)
PARAMETRIZE_ADDED = re.compile(
    r"^\+\s*@(pytest\.mark\.)?parametrize\s*\("
)
# pytest assertion vocabulary. Plain `assert` is the dominant one but
# unittest-style `self.assertX(` also counts when test classes are used.
ASSERTION_PATTERNS = [
    re.compile(r"^\+\s*assert(\s|\()"),
    re.compile(r"^\+\s*self\.assert\w+\s*\("),
    re.compile(r"^\+\s*pytest\.raises\s*\("),
    re.compile(r"^\+\s*with\s+pytest\.raises\s*\("),
]
# Mock/patch vocabulary — both unittest.mock and pytest's monkeypatch.
# Note: unlike the assertion patterns (which expect the assertion at the
# leftmost position on the line), mock invocations frequently appear in
# assignments (`m = MagicMock()`), context managers (`with patch(...)`),
# and decorators (`@patch(...)`). So we use `^\+.*?\b...` rather than
# `^\+\s*\w*\.?...` — match anywhere on an added line, but require word
# boundary so `MockObject` doesn't trigger and longest-first ordering so
# `MagicMock` wins over `Mock`.
MOCK_PATTERN = re.compile(
    r"^\+.*?\b"
    r"(MagicMock|AsyncMock|PropertyMock|Mock|"
    r"mock\.patch(?:\.\w+)?|"
    r"patch(?:\.\w+)?|"
    r"monkeypatch\.\w+|"
    r"mocker\.\w+)\s*\("
)


def classify_path(path: str) -> str:
    """Return 'test', 'code', or 'other'."""
    if DOCS_PATH_REGEX.search(path):
        return "other"
    if TEST_PATH_REGEX.search(path):
        return "test"
    if CODE_PATH_REGEX.search(path):
        return "code"
    return "other"


def parse_diff(diff_text: str):
    """Split a unified diff into per-file records.

    Each record: {path, kind ('test'|'code'|'other'), added, removed}.
    `added` and `removed` keep their leading +/- so the line-level regexes
    can anchor with `^[+-]`.
    """
    files = []
    current = None
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            if current is not None:
                files.append(current)
            parts = raw.rsplit(" b/", 1)
            path = parts[-1].strip() if len(parts) > 1 else "?"
            current = {
                "path": path,
                "kind": classify_path(path),
                "added": [],
                "removed": [],
            }
            continue
        if current is None:
            continue
        if raw.startswith("Binary files "):
            current["kind"] = "other"
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            current["added"].append(raw)
        elif raw.startswith("-"):
            current["removed"].append(raw)
    if current is not None:
        files.append(current)
    # Reclassify content-free entries (pure renames, mode-only changes)
    # as 'other' so they don't inflate the per-file-flood denominator.
    for f in files:
        if f["kind"] != "other" and not f["added"] and not f["removed"]:
            f["kind"] = "other"
    return files


def count_parametrize_cases(added_lines, start_idx) -> int:
    """Count top-level argvalues passed to `@pytest.mark.parametrize`.

    The decorator's second positional argument is a list of cases. We
    forward-scan up to 80 added lines past the decorator, joining them
    and walking the character stream tracking bracket depth and
    string-literal state.

    Returns the number of cases (>= 1). Falls back to 1 on parse failure.

    Limitation: the walker is not comment-aware. A `#` line comment
    inside the argvalues that contains a comma at depth-1 will inflate
    the case count. In practice this is narrow — inline `# base case`
    comments don't contain commas. The walker IS quote-aware
    (single/double/triple-quoted strings with backslash escapes), which
    covers the more common false-positive vector.
    """
    joined = added_lines[start_idx][1:]  # strip leading '+'
    look_ahead = 80
    end = min(start_idx + 1 + look_ahead, len(added_lines))
    for j in range(start_idx + 1, end):
        joined += "\n" + added_lines[j][1:]
        if added_lines[j].rstrip().endswith(")"):
            break

    # Find the argvalues list start — the SECOND argument to parametrize,
    # which begins after the first comma at depth 1. We pre-walk to find
    # that comma, then start case-counting on the bracket that follows.
    depth = 0
    in_string = False
    string_char = ""
    escape = False
    cursor = 0
    while cursor < len(joined):
        ch = joined[cursor]
        if escape:
            escape = False
            cursor += 1
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == string_char:
                in_string = False
                string_char = ""
            cursor += 1
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            cursor += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 1:
            # Found the boundary between argnames and argvalues.
            cursor += 1
            break
        cursor += 1

    # Now look for the opening bracket of argvalues and count commas at
    # depth 1 inside it.
    depth = 0
    in_outer = False
    cases = 0
    last_comma_was_trailing = False
    in_string = False
    string_char = ""
    escape = False
    while cursor < len(joined):
        ch = joined[cursor]
        cursor += 1
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
                continue
            if ch == string_char:
                in_string = False
                string_char = ""
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            last_comma_was_trailing = False
            continue
        if ch in (" ", "\t", "\n"):
            continue
        if ch in ("[", "("):
            depth += 1
            if depth == 1 and not in_outer:
                in_outer = True
                cases = 1
            last_comma_was_trailing = False
        elif ch in ("]", ")"):
            depth -= 1
            if depth == 0 and in_outer:
                if last_comma_was_trailing:
                    cases -= 1
                return max(cases, 1)
            last_comma_was_trailing = False
        elif ch == "," and in_outer and depth == 1:
            cases += 1
            last_comma_was_trailing = True
        else:
            last_comma_was_trailing = False
    return max(cases, 1)


def compute_metrics(files):
    test_files = [f for f in files if f["kind"] == "test"]
    code_files = [f for f in files if f["kind"] == "code"]

    new_test_loc = sum(len(f["added"]) for f in test_files)
    new_code_loc = sum(len(f["added"]) for f in code_files)

    new_test_blocks = 0
    removed_test_blocks = 0
    new_assertions = 0
    new_mocks = 0
    max_per_file = 0
    largest_test_file = None

    for f in test_files:
        file_count = 0
        added = f["added"]
        for idx, line in enumerate(added):
            if TEST_BLOCK_ADDED.search(line):
                # A test function decorated with @parametrize counts once
                # per case rather than once per def. Look-back is bounded
                # by `look_back` since the decorator may live a few lines
                # above the `def`.
                cases = 1
                look_back = 10
                for back in range(max(0, idx - look_back), idx):
                    if PARAMETRIZE_ADDED.search(added[back]):
                        cases = count_parametrize_cases(added, back)
                        break
                file_count += cases
            for pat in ASSERTION_PATTERNS:
                if pat.search(line):
                    new_assertions += 1
                    break
            if MOCK_PATTERN.search(line):
                new_mocks += 1
        for line in f["removed"]:
            if TEST_BLOCK_REMOVED.search(line):
                removed_test_blocks += 1
        new_test_blocks += file_count
        if file_count > max_per_file:
            max_per_file = file_count
            largest_test_file = f["path"]

    net_test_blocks = new_test_blocks - removed_test_blocks
    metrics = {
        "new-test-files": len(test_files),
        "new-code-files": len(code_files),
        "new-test-loc": new_test_loc,
        "new-code-loc": new_code_loc,
        "new-it-blocks": new_test_blocks,
        "removed-it-blocks": removed_test_blocks,
        "net-it-blocks": net_test_blocks,
        "new-assertions": new_assertions,
        "new-mocks": new_mocks,
        "max-it-per-file": max_per_file,
        "largest-test-file": largest_test_file,
    }
    if new_test_blocks > 0:
        metrics["assertion-density"] = round(new_assertions / new_test_blocks, 2)
        metrics["mock-density"] = round(new_mocks / new_test_blocks, 2)
    if new_code_loc > 0:
        metrics["test-to-code-ratio"] = round(new_test_loc / new_code_loc, 2)
    return metrics


def compute_signals(metrics):
    new_tests = metrics["new-it-blocks"]
    new_code_files = metrics["new-code-files"]
    max_per_file = metrics["max-it-per-file"]

    per_file_flood = max_per_file > THR_PER_FILE_FLOOD_MAX
    if new_code_files > 0 and (new_tests / new_code_files) > THR_PER_CODE_FILE_FLOOD:
        per_file_flood = True

    assertion_thin = False
    if new_tests >= THR_ASSERTION_THIN_MIN_TESTS:
        density = metrics["new-assertions"] / new_tests
        assertion_thin = density < THR_ASSERTION_THIN

    mock_heavy = False
    if new_tests >= THR_MOCK_HEAVY_MIN_TESTS:
        density = metrics["new-mocks"] / new_tests
        mock_heavy = density > THR_MOCK_HEAVY

    return {
        "per-file-flood": per_file_flood,
        "assertion-thin": assertion_thin,
        "mock-heavy": mock_heavy,
    }


def _yaml_quote(s: str) -> str:
    """Quote a string for safe YAML emission. Always quote, escape `"`
    and `\\` — safer than guessing whether a value needs quoting."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_yaml(applicable, metrics=None, signals=None, reason=None):
    """Render the YAML output. Schema is deliberately language-agnostic
    so a future polyglot extension stays trivial."""
    lines = ["test-quality-snapshot:"]
    lines.append(f"  schema-version: {SCHEMA_VERSION}")
    lines.append(f"  applicable: {'true' if applicable else 'false'}")
    if not applicable:
        lines.append(f"  reason: {_yaml_quote(reason or '')}")
        return "\n".join(lines) + "\n"

    lines.append("  signals:")
    for k in ("per-file-flood", "assertion-thin", "mock-heavy"):
        lines.append(f"    {k}: {'true' if signals[k] else 'false'}")
    lines.append("  metrics:")
    key_order = [
        "new-test-files", "new-code-files", "new-test-loc", "new-code-loc",
        "new-it-blocks", "removed-it-blocks", "net-it-blocks",
        "new-assertions", "new-mocks",
        "max-it-per-file", "largest-test-file",
        "assertion-density", "mock-density", "test-to-code-ratio",
    ]
    for k in key_order:
        if k not in metrics or metrics[k] is None:
            continue
        v = metrics[k]
        if isinstance(v, float):
            lines.append(f"    {k}: {v:.2f}")
        elif isinstance(v, str):
            lines.append(f"    {k}: {_yaml_quote(v)}")
        else:
            lines.append(f"    {k}: {v}")
    return "\n".join(lines) + "\n"


def read_diff(args):
    """Resolve the diff input from CLI args.

    Precedence: --diff-file beats --against. With neither, default to
    `git diff HEAD` so the live working tree is the implicit input
    (matches the TDD flow: "I just wrote tests, what do they look like?").
    """
    if args.diff_file:
        with open(args.diff_file, "r", encoding="utf-8") as fh:
            return fh.read()
    ref = args.against or "HEAD"
    result = subprocess.run(
        ["git", "diff", ref],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(
            f"ERROR: git diff {ref} failed (exit {result.returncode}): "
            f"{result.stderr}"
        )
        sys.exit(2)
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="quality.py",
        description="jig tdd-loop test-quality preflight",
    )
    parser.add_argument("--diff-file", help="path to a cached unified diff")
    parser.add_argument(
        "--against",
        default=None,
        help="git ref to diff against (default: HEAD)",
    )
    args = parser.parse_args(argv)

    diff_text = read_diff(args)
    if not diff_text.strip():
        # Distinguish empty / unreadable from docs-only so a failed fetch
        # doesn't masquerade as a legitimate no-op result.
        sys.stdout.write(emit_yaml(False, reason="empty-or-unreadable-diff"))
        return 0

    files = parse_diff(diff_text)
    if not files:
        sys.stdout.write(emit_yaml(False, reason="malformed-diff-no-file-headers"))
        return 0

    test_count = sum(1 for f in files if f["kind"] == "test")
    code_count = sum(1 for f in files if f["kind"] == "code")
    if test_count == 0 and code_count == 0:
        sys.stdout.write(emit_yaml(False, reason="docs-only-or-no-test-or-code-changes"))
        return 0

    metrics = compute_metrics(files)
    signals = compute_signals(metrics)
    sys.stdout.write(emit_yaml(True, metrics=metrics, signals=signals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
