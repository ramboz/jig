"""Bounded trusted-local reading for selected static design attestations.

No producer runs here. Static readback also uses one fixed local Git HEAD
metadata probe; it does not offer command execution through selected data.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import stat
import unicodedata
from pathlib import Path
from typing import Any

MAX_JSON = 32 * 1024 * 1024
MAX_FILES = 100_000
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PRIVATE = {".ssh", ".aws", ".gnupg", ".git", ".azure", ".kube"}
RETIRED = {"jig/design-freshness/1", "vellum-design-input/0.1-pilot"}


class BindingError(ValueError):
    """A named comparison cannot be established."""


def _require(ok: bool, label: str, reason: str) -> None:
    if not ok:
        raise BindingError(f"{label}: {reason}")


def _object(value: Any, label: str, keys: set[str] | None = None) -> dict:
    _require(isinstance(value, dict), label, "expected object")
    if keys is not None:
        missing = keys - value.keys()
        extra = value.keys() - keys
        _require(not missing and not extra, label,
                 f"keys mismatch (missing {', '.join(sorted(missing)) or 'none'}; "
                 f"unknown {', '.join(sorted(extra)) or 'none'})")
    return value


def _list(value: Any, label: str, *, empty: bool = False) -> list:
    _require(isinstance(value, list), label, "expected list")
    _require((empty or bool(value)) and len(value) <= MAX_FILES, label,
             "missing or oversized inventory")
    return value


def _string(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value), label, "expected nonempty string")
    return value


def _pairs(pairs: list) -> dict:
    result: dict = {}
    for key, value in pairs:
        _require(key not in result, "JSON", "duplicate key")
        result[key] = value
    return result


def _constant(_value: str) -> Any:
    raise BindingError("JSON: nonfinite number")


def _float(value: str) -> float:
    number = float(value)
    _require(math.isfinite(number), "JSON", "nonfinite number")
    return number


def _json_value(text: str, label: str) -> Any:
    _require(len(text.encode("utf-8")) <= MAX_JSON, label, "oversized JSON")
    try:
        value = json.loads(text, object_pairs_hook=_pairs,
                           parse_constant=_constant, parse_float=_float)
    except (ValueError, RecursionError) as exc:
        raise BindingError(f"{label}: malformed, duplicate or nonfinite JSON") from exc
    return value


def _json(text: str, label: str) -> dict:
    return _object(_json_value(text, label), label)


def _block(text: str, name: str) -> dict | None:
    tag = f"jig-design-{name}"
    starts = re.findall(rf"(?m)^[ \t]*`{{3,}}{tag}\b[^\n]*", text)
    if not starts:
        return None
    _require(len(starts) == 1, name, "duplicate fenced block")
    found = re.search(rf"(?m)^```{tag}\n(.*?)\n```[ \t]*$", text, re.DOTALL)
    _require(found is not None and starts == [f"```{tag}"], name,
             "malformed fenced block")
    assert found is not None
    return _json(found.group(1), name)


def _relative(value: Any, label: str) -> str:
    text = _string(value, label)
    parts = text.split("/")
    _require(not text.startswith("/") and len(parts) <= 64
             and all(p not in {"", ".", ".."} for p in parts)
             and not any(p.casefold() in _PRIVATE for p in parts)
             and not any(c in text for c in ("\\", ":"))
             and not any(ord(c) < 32 or ord(c) == 127 for c in text)
             and unicodedata.normalize("NFC", text) == text,
             label, "unsafe or ambiguous relative path")
    return text


def _hash(value: Any, label: str) -> str:
    text = _string(value, label)
    _require(_HASH.fullmatch(text) is not None, label, "expected raw sha256 hash")
    return text


class _Reader:
    def __init__(self, value: Any):
        roots = _object(value, "selection roots")
        _require("project" in roots and 1 <= len(roots) <= 64,
                 "selection roots", "explicit project root required (at most 64 roots)")
        _require(all(isinstance(raw, str)
                     and not any(ord(c) < 32 or ord(c) == 127 for c in raw)
                     for raw in roots.values()),
                 "selection root", "expected root strings without control characters")
        self.roots: dict[str, Path] = {}
        self.count = 0
        for name, raw in roots.items():
            _require(re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) is not None,
                     "selection roots", "invalid root name")
            text = _string(raw, "selection root")
            root = Path(text)
            home = Path.home().resolve()
            try:
                canonical = root.resolve()
            except (OSError, RuntimeError) as exc:
                raise BindingError("selection root: inaccessible or symlink loop") from exc
            _require(root.is_absolute() and str(root) == text
                     and canonical == root and len(root.parts) >= 4
                     and root != home and root not in home.parents
                     and not any(p.casefold() in _PRIVATE for p in root.parts)
                     and root.parts[1] not in {
                         "etc", "dev", "proc", "sys", "System", "Library",
                         "usr", "bin", "sbin", "Applications",
                     } and not str(root).startswith("/private/etc"),
                     "selection root", "unsafe broad, private or aliased root")
            _require(root.is_dir(), "selection root", "inaccessible directory")
            for other in self.roots.values():
                a, b = str(root).casefold(), str(other).casefold()
                _require(a != b and not a.startswith(b + "/") and not b.startswith(a + "/"),
                         "selection roots", "overlapping or aliased roots")
            self.roots[name] = root

    def path(self, root_id: Any, relative: Any, label: str) -> Path:
        _require(isinstance(root_id, str) and root_id in self.roots, label,
                 "unknown reviewed root")
        name = _relative(relative, label)
        current = self.roots[root_id]
        for part in name.split("/"):
            try:
                aliases = [p.name for p in current.iterdir()
                           if p.name.casefold() == part.casefold()]
            except OSError as exc:
                raise BindingError(f"{label}: inaccessible comparison path") from exc
            _require(aliases == [part], label, "missing file or ambiguous case alias")
            current = current / part
            _require(not current.is_symlink(), label, "symlink reference refused")
        return current

    def ref(self, value: Any, label: str) -> Path:
        ref = _object(value, label, {"root", "path", "hash"})
        expected = _hash(ref["hash"], label)
        path = self.path(ref["root"], ref["path"], label)
        self.count += 1
        _require(self.count <= MAX_FILES, label, "comparison limit exceeded")
        try:
            _require(stat.S_ISREG(path.stat().st_mode), label, "not a regular file")
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
        except OSError as exc:
            raise BindingError(f"{label}: inaccessible comparison bytes") from exc
        _require("sha256:" + hasher.hexdigest() == expected, label,
                 "raw hash mismatch; changed binding")
        return path

    def document(self, value: Any, label: str) -> dict:
        return _object(self.data(value, label), label)

    def data(self, value: Any, label: str) -> Any:
        """Strict JSON, including the static producer's finite manifest arrays."""
        path = self.ref(value, label)
        try:
            _require(path.stat().st_size <= MAX_JSON, label, "oversized JSON")
            return _json_value(path.read_text(encoding="utf-8"), label)
        except (OSError, UnicodeError) as exc:
            raise BindingError(f"{label}: inaccessible or non-UTF-8 JSON") from exc

    def tree(self, value: Any, label: str) -> dict[Path, str]:
        tree = _object(value, label, {"root", "path", "files"})
        directory = self.path(tree["root"], tree["path"], label)
        _require(directory.is_dir(), label, "missing closed directory")
        rows = _list(tree["files"], label)
        expected: dict[Path, str] = {}
        names: list[str] = []
        for row in rows:
            row = _object(row, label, {"path", "hash"})
            name = _relative(row["path"], label)
            names.append(name)
            path = self.ref({
                "root": tree["root"], "path": tree["path"] + "/" + name,
                "hash": row["hash"],
            }, label)
            expected[path] = row["hash"]
        _require(names == sorted(names) and len({n.casefold() for n in names}) == len(names),
                 label, "duplicate, aliased or unsorted inventory")
        actual: set[Path] = set()
        pending = [(directory, 0)]
        entries = 0
        while pending:
            parent, depth = pending.pop()
            _require(depth <= 64, label, "directory depth limit exceeded")
            children = list(parent.iterdir())
            _require(len({p.name.casefold() for p in children}) == len(children),
                     label, "ambiguous case aliases in directory")
            for child in children:
                entries += 1
                _require(entries <= MAX_FILES, label, "directory inventory limit exceeded")
                mode = child.lstat().st_mode
                _require(not stat.S_ISLNK(mode), label, "symlink in closed inventory")
                if stat.S_ISDIR(mode):
                    pending.append((child, depth + 1))
                else:
                    _require(stat.S_ISREG(mode), label, "nonregular file in inventory")
                    actual.add(child)
        _require(actual == set(expected), label, "partial closed inventory; added/missing files")
        return expected

    def producer_path(self, raw: Any, label: str) -> Path:
        """Resolve only the fixed producer link fields, never arbitrary JSON."""
        text = _string(raw, label)
        path = Path(text)
        _require(str(path) == text, label, "ambiguous producer path alias")
        if not path.is_absolute():
            return self.path("project", text, label)
        for root_id, root in self.roots.items():
            if root in path.parents:
                return self.path(root_id, path.relative_to(root).as_posix(), label)
        raise BindingError(f"{label}: link outside reviewed roots")


def _version(value: dict, kind: str, version: int, run: str, label: str) -> None:
    _require(value.get("kind") == kind
             and type(value.get("schema_version")) is int
             and value["schema_version"] == version,
             label, "unsupported record kind/version")
    _require(value.get("run_id") == run, label, "missing or foreign run_id")


def _reject_retired(value: Any) -> None:
    """Reject explicit old identities, including mixed selected namespaces."""
    if isinstance(value, str):
        _require(value not in RETIRED, "selected contract",
                 "retired interface; renew with jig/static-design-freshness/1 "
                 "and vellum-confirmed-source/0.2, never relabel old approvals")
    elif isinstance(value, dict):
        for child in value.values():
            _reject_retired(child)
    elif isinstance(value, list):
        for child in value:
            _reject_retired(child)


def _validate(selection: dict, bindings: dict) -> None:
    from _common.static_design_bindings import validate
    try:
        validate(selection, bindings)
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise BindingError("static contract: malformed required nested field") from exc


def freshness_problem(slice_text: str, review_body: str) -> str:
    """Empty iff unselected historical evidence or all selected bindings match."""
    try:
        selection = _block(slice_text, "selection")
        bindings = _block(review_body, "bindings")
        if selection is None and bindings is None:
            return ""
        _reject_retired(selection)
        _reject_retired(bindings)
        _require(selection is not None, "selection", "missing explicit rich comparison context")
        _require(bindings is not None, "bindings", "missing complete attested comparisons")
        assert selection is not None and bindings is not None
        _validate(selection, bindings)
    except (BindingError, OSError, UnicodeError, RecursionError) as exc:
        # Filesystem errors can contain paths; never echo their contents or credentials.
        reason = str(exc) if isinstance(exc, BindingError) else "inaccessible comparison bytes"
        return (f"design-freshness: {reason}; obtain fresh producer evidence "
                "and independent attestation")
    return ""
