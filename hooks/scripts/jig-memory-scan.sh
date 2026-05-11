#!/bin/bash
# Fires on UserPromptSubmit. Scans the user's prompt for capitalized references
# (proper nouns, acronyms) not found in the hot cache (CLAUDE.md) or
# docs/memory/glossary.md. Surfaces unknowns as additionalContext so Claude
# can ask about them naturally in the current response.
python3 - <<'EOF'
import sys, json, os, re

try:
    data = json.load(sys.stdin)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    prompt = data.get("prompt", "")

    # Load known terms from hot cache and glossary
    known = set()
    for path in ["CLAUDE.md", "docs/memory/glossary.md"]:
        full = os.path.join(project_dir, path)
        if os.path.exists(full):
            with open(full) as f:
                content = f.read()
            # Extract capitalized words and multi-word caps sequences
            known.update(re.findall(r'\b[A-Z][A-Za-z0-9_-]+\b', content))

    # Find capitalized references in the prompt (2+ chars, not common English words)
    COMMON = {
        "I", "A", "The", "In", "On", "At", "To", "Of", "Or", "And", "But",
        "For", "Is", "It", "Be", "Do", "If", "As", "We", "He", "She", "You",
        "My", "We", "No", "OK", "Hi", "So", "Go", "Mr", "Ms", "Dr", "St",
        "API", "URL", "HTTP", "JSON", "CLI", "PR", "UI", "UX", "AI", "ML",
        "LLM", "SDK", "MCP", "TDD", "ADR", "CI", "CD", "MVP",
    }
    candidates = re.findall(r'\b[A-Z]{2,}|[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', prompt)
    unknowns = [c for c in candidates if c not in known and c not in COMMON]
    unknowns = list(dict.fromkeys(unknowns))  # deduplicate, preserve order

    if unknowns:
        refs = ", ".join(unknowns)
        msg = (
            f"Unrecognized references in prompt: {refs}. "
            "If these are project-specific terms, ask the user once and persist the answer to "
            "CLAUDE.md (if high-frequency) or docs/memory/glossary.md (if niche)."
        )
        print(json.dumps({"continue": True, "additionalContext": msg}))
except Exception:
    pass  # Never block a prompt
exit(0)
EOF
exit 0
