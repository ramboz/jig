#!/bin/bash
# Fires on Stop. Scans the completed session exchange for task-capture language
# patterns ("we should also", "don't forget", "TODO:", etc.). If found, surfaces
# them as additionalContext at the START OF THE NEXT TURN for triage.
# Note: additionalContext from Stop hooks is injected into the next turn, not this one.
python3 - <<'EOF'
import sys, json, re

PATTERNS = [
    r"we should also\b",
    r"don'?t forget\b",
    r"\bTODO\s*:",
    r"later we'?ll?\s+need\b",
    r"remind me to\b",
    r"we need to\b.{0,60}(later|eventually|at some point)",
    r"follow[- ]?up[:\s]",
]

try:
    data = json.load(sys.stdin)
    # Stop hook receives the full exchange; check assistant + user messages
    messages = data.get("messages", [])
    text = " ".join(
        m.get("content", "") if isinstance(m.get("content"), str)
        else " ".join(c.get("text", "") for c in m.get("content", []) if isinstance(c, dict))
        for m in messages
    )

    found = []
    for pattern in PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend(matches)

    if found:
        examples = "; ".join(dict.fromkeys(found[:3]))  # up to 3 unique snippets
        msg = (
            f"Task-capture patterns detected ({examples}). "
            "Please triage any unresolved items: "
            "(a) add to an existing spec, "
            "(b) create a new spec via spec-workflow, or "
            "(c) park in docs/inbox.md."
        )
        print(json.dumps({"continue": True, "additionalContext": msg}))
except Exception:
    pass  # Never block completion
exit(0)
EOF
exit 0
