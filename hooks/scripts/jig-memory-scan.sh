#!/bin/bash
# Fires on UserPromptSubmit. Scans the user's prompt for capitalized references
# (proper nouns, acronyms) not found in the hot cache (AGENTS.md/CLAUDE.md)
# or docs/memory/glossary.md. Surfaces unknowns as additionalContext so Claude
# can ask about them naturally in the current response.
#
# Heuristic refinements (slice 002-03):
# - Strip fenced + inline code blocks before scanning
# - Strip URL hosts (https://Foo.com → " ")
# - Strip absolute paths (/Users/Foo/Bar → " ")
# - Skip COMMON acronyms (API, JSON, etc.)
python3 -c "
import sys, json, os, re

try:
    data = json.load(sys.stdin)
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    prompt = data.get('prompt', '')

    # Strip fenced code blocks (\`\`\`...\`\`\`) — multi-line, non-greedy
    prompt = re.sub(r'\`\`\`.*?\`\`\`', ' ', prompt, flags=re.DOTALL)
    # Strip inline code spans (\`...\`)
    prompt = re.sub(r'\`[^\`]*\`', ' ', prompt)
    # Strip URLs (greedy through non-space)
    prompt = re.sub(r'https?://\S+', ' ', prompt)
    # Strip absolute paths (rough — /word/word/...)
    prompt = re.sub(r'(?<!\w)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', ' ', prompt)

    known = set()
    for path in ['AGENTS.md', 'CLAUDE.md', 'docs/memory/glossary.md']:
        full = os.path.join(project_dir, path)
        if os.path.exists(full):
            with open(full) as f:
                content = f.read()
            known.update(re.findall(r'\b[A-Z][A-Za-z0-9_-]+\b', content))

    COMMON = {
        'I', 'A', 'The', 'In', 'On', 'At', 'To', 'Of', 'Or', 'And', 'But',
        'For', 'Is', 'It', 'Be', 'Do', 'If', 'As', 'We', 'He', 'She', 'You',
        'My', 'No', 'OK', 'Hi', 'So', 'Go', 'Mr', 'Ms', 'Dr', 'St',
        'API', 'URL', 'HTTP', 'HTTPS', 'JSON', 'XML', 'YAML', 'TOML',
        'CSV', 'TSV', 'PDF', 'HTML', 'CSS', 'CLI', 'GUI', 'IDE', 'PR',
        'UI', 'UX', 'AI', 'ML', 'LLM', 'SDK', 'MCP', 'TDD', 'BDD', 'ADR',
        'CI', 'CD', 'MVP', 'OS', 'DB', 'SQL', 'NoSQL', 'AWS', 'GCP',
    }
    candidates = re.findall(r'\b[A-Z]{2,}|[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', prompt)
    unknowns = [c for c in candidates if c not in known and c not in COMMON]
    unknowns = list(dict.fromkeys(unknowns))

    if unknowns:
        refs = ', '.join(unknowns)
        msg = (
            f'Unrecognized references in prompt: {refs}. '
            'If these are project-specific terms, ask the user once and persist the answer to '
            'AGENTS.md (if high-frequency) or docs/memory/glossary.md (if niche).'
        )
        print(json.dumps({'continue': True, 'additionalContext': msg}))
except Exception:
    pass
"
exit 0
