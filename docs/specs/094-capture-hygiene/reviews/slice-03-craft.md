---
slice: 094-03 — decision vocabulary on the routing surface
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (fresh context)
reviewed_at: 2026-07-16T21:17:52Z
prompt_source: review.py pr-review
---

Verdict: **pass-with-findings** → recorded as `pass` (no blockers).

Craft pass over `skills/memory-sync/SKILL.md` + `evals/cases/memory-sync.json`. (Reviewer had no Bash; makes no claim resting on an executed eval.)

**On keyword-stuffing (asked explicitly): no, with one seam.** The discriminator is real routing signal, not padding, and mirrors the distinction `adr-workflow` draws from its side. The one stuffy stretch — three near-synonyms in a row ("record a decision, remember this decision, or write this decision down") — is house style, not a lapse: `adr-workflow` lists four quoted trigger phrases, `bug-fix` seven. In family.

**On length (asked explicitly): no.** ~130 words against `bug-fix` (~12 lines), `pr-review` (~13), `contracts` (~13), `analyze` (~12). Top of the band, not an outlier.

**Findings folded back:**

1. Dangling relative clause on the routing surface — "…or translation fixes — which it records via decisions.py" attaches `which` to "translation fixes", not to the decision. On the one field the host replays into every session, ambiguity is the thing you are paying to avoid. Also two consecutive sentences opened with "Also", and one 45-word compound did three jobs. **Fixed**: split into separate sentences; the mechanism now has its own.
2. The pin was weaker than AC #3's prose implied: both new positives used `top_k: 3`, so the "cards" case passes while `adr-workflow` sits at rank 1 — i.e. while the reported symptom is still live — and the corpus-wide ratchet cannot rescue one case slipping to rank 2. **Fixed**: the reported phrasing is pinned at `top_k: 1`. The "cards" case stays at `top_k: 3` deliberately — pinning *it* to rank 1 is unreachable without keyword-stuffing (see the compliance verdict), which is the counter-pressure the reviewer itself acknowledged.
3. The collision guard was one-directional: `memory-sync.json` pinned the ADR direction, but nothing pinned the reverse, so a future edit widening `adr-workflow`'s description could re-swallow "remember this decision" with every test green. Out of the declared deliverable set, so filed as a suggestion. **Fixed anyway** — it guards precisely the hazard this slice creates: `evals/cases/adr-workflow.json` gains `{"prompt": "Remember this decision so we don't rewrite it tomorrow", "owner": "memory-sync"}`. Negatives now 44/44.

**Strengths the reviewer named:** the positive/negative minimal pair ("Record this decision: we shortened the cards…" vs "Record this decision as an ADR") — identical opening four words, opposite owners — is discrimination testing rather than trigger-phrase echoing; and the ratchet floors were left untouched despite the real pressure that adding positives to a floor-gated corpus creates ("nobody would have noticed if it had been").
