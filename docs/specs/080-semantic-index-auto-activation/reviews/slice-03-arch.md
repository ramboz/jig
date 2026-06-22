---
slice: 080-03 - Codex adapter activation
pass: arch
verdict: pass
reviewer: arch-review
reviewed_at: 2026-06-22T03:53:30Z
prompt_source: python3 review.py arch-review docs/specs/080-semantic-index-auto-activation/spec.md 080-03 <080-03 deliverables>
---

VERDICT: pass

REASONING:
The Codex adapter keeps semantic-index activation behind the shared contract and renders host-native scaffold/plugin surfaces without requiring Claude runtime files. The design is coherent: source remains canonical, Codex-specific rewrites are staged in renderer/build paths, hook registration is schema-clean, and internal Scout support stays behind explicit overlay state. One boundary is still weaker than the architecture prose suggests, but it is future-adapter friction rather than a blocker for 080-03.

SPECIFIC ISSUES:
- [nit] skills/scaffold-init/scaffold.py:747 — `HostRenderer` is documented as the adapter boundary, but the real Codex/Claude routing still lives in string branches and free functions such as `copy_machinery(... host=...)` at skills/scaffold-init/scaffold.py:1833 and `scaffold(... host=...)` at skills/scaffold-init/scaffold.py:2166; future hosts would not implement one complete renderer contract.
- [strength] skills/scaffold-init/scaffold.py:1291 — Codex skill copying preserves the shared source while creating discoverable `jig-*` skills plus non-discoverable helper aliases, keeping runtime imports working without registering duplicate skills.
- [strength] skills/scaffold-init/scaffold.py:1412 — Codex hook rendering adapts the canonical hook source by stripping unsupported `async` metadata and adding stable `statusMessage` values instead of forking hook definitions.
- [strength] scripts/build_codex_plugin.py:80 — plugin packaging reuses the same `CodexScaffoldRenderer` transformations as scaffold mode, so Codex plugin and Codex scaffold output stay aligned.

RECONCILIATION NOTES:
Record the `HostRenderer` incompleteness as a design nit/deviation: acceptable for this slice, but future host-adapter work should either expand the renderer interface or stop presenting it as the full public adapter contract.
