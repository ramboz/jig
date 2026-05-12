"""Shared spec-parsing helpers used by multiple jig skills.

Extracted per ADR-0002's "three callers needing the same helper" trigger.
Today's callers: workflow.py / review.py / land.py — all three resolve
`## Slice <label>` headers via lenient case-insensitive substring matching
against a user-supplied fragment. adr.py uses a divergent
`### Decision: ...` shape and stays standalone.

Helpers in this module:
  - find_slice_section(text, fragment) -> (start, end, label)

Callers wrap `SliceLookupError` to re-raise as their own user-facing
error type (WorkflowError / ReviewError / LandError) so CLI messages
keep their original prefix.
"""

import re


class SliceLookupError(RuntimeError):
    """Raised when a slice fragment can't be uniquely resolved in a spec."""


_SLICE_HEADER_RE = re.compile(r"(?im)^##\s+Slice\s+([^\n]+)$")


def find_slice_section(spec_text: str, slice_fragment: str):
    """Locate the `## Slice ...` H2 whose label contains `slice_fragment`
    (case-insensitive substring match). Returns ``(start, end, label)``:

    - ``start`` — byte offset of the opening ``##`` in the header line.
    - ``end`` — byte offset of the next ``^##\\s`` heading, or EOF.
    - ``label`` — trimmed header text after ``Slice `` (e.g.
      ``001-01 — greenfield-scaffold``).

    Raises ``SliceLookupError`` on zero or multiple matches.
    """
    headers = list(_SLICE_HEADER_RE.finditer(spec_text))
    if not headers:
        raise SliceLookupError("no '## Slice ...' headings found in spec")
    needle = slice_fragment.lower()
    matches = [h for h in headers if needle in h.group(0).lower()]
    if not matches:
        raise SliceLookupError(f"slice not found: '{slice_fragment}'")
    if len(matches) > 1:
        names = [h.group(1).strip() for h in matches]
        raise SliceLookupError(
            f"ambiguous slice fragment '{slice_fragment}' matches: {names}"
        )
    header = matches[0]
    rest = spec_text[header.end():]
    nxt = re.search(r"(?m)^##\s", rest)
    end = header.end() + (nxt.start() if nxt else len(rest))
    label = header.group(1).strip()
    return header.start(), end, label
