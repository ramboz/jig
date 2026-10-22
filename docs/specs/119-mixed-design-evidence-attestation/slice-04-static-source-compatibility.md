---
status: DONE
dependencies: [119-02, adr-0065]
last_verified: 2026-10-21
frame_review: true
arch_review: true
---

## Slice 119-04 — static-source-compatibility

**Goal:** A developer can attest a current, explicitly finite real-source static
contract through Jig's existing public record/revalidation/completion rail,
without promoting a static measurement to whole-app or visual-quality approval.

The change adds the published Vellum 0.2 / Servo static evidence variant to the
existing read/hash-only consumer. Its tradeoff is explicit complete provenance
and closure selection, rather than a permissive format-name allowlist.

**DoR:**
- [x] 119-02 is DONE; ADR-0065 is Accepted and supplies existing ownership:
  producer verdict authority, distinct namespaces, independent delivery and
  versioned explicit variants. No evaluator or new architecture authority.
- [x] Exact starting HEAD/base is `756f39dcdd842f9cdf3b34b6924e9b216212af13`,
  open PR #244; verified with `rev-parse`, `merge-base` and live PR metadata.
- [x] Read vision (UC-4/7/20), workflow, architecture, conventions and bug board;
  this is missing new-format behavior, not a duplicate tracked defect.
- [x] Read actual producer records and the published static APP protocol.
- [x] Independent frame and readiness reviews pass before implementation.

### Grounded frame and authority

At starting HEAD, `skills/_common/design_bindings.py:15-23,263-333`
selects only `vellum-design-input/0.1-pilot` plus `design_evidence` schema 1.
The complete `_validate` body was read, including output/served comparisons;
its explicit version predicate cannot accept the new component kind.
This is a finite code observation, not a claim about every Jig consumer.

Producer authority: Servo PR [ramboz/servo#47](https://github.com/ramboz/servo/pull/47)
at `c23fafdcb581fa52d849687ece36b0e9b0fddd48`,
`docs/specs/036-deterministic-design-evidence/static-app-contract.md`;
Vellum PR [PinkException/vellum#53](https://github.com/PinkException/vellum/pull/53),
source API `confirmed_source.py` raw SHA-256
`4f88ce4fe6af14ba044146eee27543116e3d9180977fdf5150125f9983e9ae5d`.
Read these local published sources without importing or executing them.

Actual M04 run `41a3554e-8fd3-4d14-a59c-e7b8f2ec7593` has native
`gate_result/2` pass, exit 0, all 15 required IDs passed; its subordinate output
is `static_source_contract_evidence/1` with
`vellum-confirmed-source/0.2`, `static-css-subset/1` and explicit residuals.
Actual M04 required-UNKNOWN run `9bef2a53-924e-4d0f-b4ec-eb323c488823`
has diagnostic component fraction 1.0 but native composite null / exit 2.
These are existing executions, not a request for new producer runs.

No new load-bearing ownership choice is proposed: this is an additive finite
contract implementation within ADR-0065, not a generic adapter/evaluator,
legacy threshold expansion (119-03), or amendment of 119-01/02 or ADR-0065.
New fields/encoding must explicitly version the incompatible static shape.
The source's historical residual saying Jig does not yet support 0.2 remains
immutable historical producer data, not authority to relabel or rewrite it.

**Acceptance Criteria:**

1. **Explicit finite contract selection.** Through `review.py record-review`
   and `check-reviews`, support the separately named Vellum confirmed-source 0.2,
   static source profile, Servo native overall/component/output and static APP
   policy namespaces. Preserve the new native kind and original producer bytes;
   no old card C0 fabrication, relabeling to `design_evidence`, guessed version,
   missing-field scalar fallback or producer invocation.
2. **Native authority and closed required inventory.** A pass requires native
   overall PASS/exit 0 and conclusive complete required PASS consistent with the
   independently pinned installed policy/checks, component and static envelope.
   Reject duplicate, missing, extra, foreign-run or contradictory required rows.
   Native FAIL and required-UNKNOWN remain nonclearing even at threshold
   0 or component diagnostic 1.0; preserve distinct producer reasons.
   This is consistency checking, not a second evaluator or score derivation.
3. **Owned identities and complete closure.** Pin original source input,
   approval, request, target, policy/independent policy review, grading, native
   gate/driver/evaluator and runtime identities. Bind invocation, run, nonce,
   acquisition claim/receipt, complete immutable output and observations to the
   overall/component references. Rehash explicit runtime file closures and
   closed browser membership (including declared symlink identities without
   broadly allowing symlink Ref traversal). Resolve only finite owned fields
   beneath reviewed narrow roots, never arbitrary path-shaped strings.
4. **Independent current app and served responses.** Compare the separately
   selected current candidate/selection/build/delivery inventories with the
   evaluated source/build/response bytes. Verify every declared resource's
   completed status/type/body and the complete output tree, not merely one
   document or a URL. Added/deleted/changed input, output, runtime, source,
   policy, grading, delivery, response, run or nonce refuses at recording,
   REVIEWED and DONE without requiring a back-edge. Exact-byte restoration
   restores consistency; documentation outside the app closure does not
   invalidate solely because repository HEAD changes.
5. **Genuine bounded positive and negatives.** Obtain a fresh independent
   read-only finite-scope attestation of the actual published M04 all-15-PASS
   records and exercise public CLI record/revalidation and lifecycle completion
   in an isolated fixture. Use the independent M04 UNKNOWN records for
   nonpass control proof. Exercise safe disposable copy mutations and restored positive,
   preserving the original recorded positive body during reuse probes.
   Label genuine producer evidence, independent reviewer verdict, synthetic
   unrelated lifecycle prerequisites and copy-mutation probes separately.
6. **Preservation.** Existing 0.1 fixtures and actual historical epoch records
   remain supported within their original currentness semantics. Unflagged
   slices retain ordinary review/dependency gates. Do not change external
   artifacts/targets/runtime, installed plugins, closed records, accepted ADRs,
   conventions, source-writer history, goals or tolerances. Preserve genuine
   nonpasses rather than overwriting history without retention.
7. **Scope stays visible.** Prompt, recorded review and live guidance explicitly
   distinguish finite static declarations from visual quality, actual font
   faces, interactions, backend truth, full APP and arbitrary Jig app-DONE.
   Retain policy/source residuals and independent compliance's authority.
   No Servo imports, evaluator/browser/model/network calls in the consumer;
   no convergence loop, broad CSS/Figma or recurring-reader nit.
8. **Normal delivery.** Test-first implementation, independent compliance,
   craft and architecture reviews, reconciliation, normal evidence/dependency/
   commit/DONE gates, memory/board and generated three-host packages complete.
   Publish an unmerged ready PR stacked on `jig-delivery-freshness-guard`;
   verify lineage and report exact head/base and durable proof paths/hashes.

### Verification scenario

**Preconditions:** Existing immutable evidence under session
`43b73062-3958-42e3-879f-4f588494ff00/files`, independently selected context,
actual reviewer response, and explicitly synthetic ordinary prerequisites in
an isolated consumer fixture. Parent preservation baseline:
`61f2e313-f28a-403a-9433-724268681e33/files/jig-static-compatibility-parent-baseline.json`,
raw SHA-256 `ec3da3e6a4b6352eb7b9d04d2ca80e6d550a54f8d943b734e75f1bc85ca8427f`.

**Invocation:** Actual commands and machine-readable observations were retained
privately as historical epochs. The retained independent-control attestations
are distinct from the synthetic fixtures; edited publication exports are not
substitutes for original selected evidence. Never run the producer, browser,
source writer or regrader.

**Preserved behavior:** Legacy card epoch, explicit opt-in, independent ordinary
reviews, complete currentness and original external bytes.

**Code revision / dirty-change identity:** Record the exercised Jig commit/diff
digest separately from frozen producer/helper and candidate/build identities.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| Published M04 all-15-PASS | 1–5, 7 | Scoped independent record/check/lifecycle pass | Genuine attester PASS; actual public record/check/REVIEWED/RECONCILED/DONE clear | pass | [Independent control attestation](verification/slice-04-M04-attestation.md) |
| M04 required UNKNOWN | 2, 5 | Refusal, native verdict preserved | Attempted PASS refused; independent nonpass preserved | pass | [Independent UNKNOWN attestation](verification/slice-04-UNKNOWN-attestation.md) |
| Synthetic copied binding mutations/restoration | 3–5 | Record/reuse/DONE refusal then exact restoration | 222 explicitly synthetic copy-data CLI probes | pass | `skills/_common/test_static_design_bindings.py`; exact historical transcripts private |
| Legacy/currentness and originals | 6 | Supported old contract; originals unchanged | 25 legacy tests; original epoch retained privately | pass | `skills/_common/test_design_bindings.py` |

**DoD:**
- [x] All ACs verified; witnessed red-to-green tests and affected suites green.
- [x] Actual finite-scope independent attestation and consumer proof preserved.
- [x] Independent compliance, craft and architecture reviews recorded.
- [x] Implementation review passed.
- [x] Deviation log produced.
- [x] Reconciliation sweep produced.
- [x] Reconciliation review passed.
- [x] Memory, generated hosts and board checked.

### Close-out (post-DONE)

- [x] Regenerate/audit the board after DONE; preserve finite scope in Notes.
- [x] Spec remains open for distinct 119-03; no compress-on-spec-close claim.

**Anti-horizontal-phasing check:** A developer gets an actual supported finite
attestation and completion/refusal across public CLI, review storage and
lifecycle reuse, not just a parser or an allowlist.

## Assumptions

- **A1:** Trusted-local published records and independent reviewed closures are
  sufficient within ADR-0065's consistency boundary. Hashes do not authenticate
  honest producer execution or hostile host/backend/native APIs.

### Deviation log (after reconciliation)

1. **No scope/ownership deviation.** The additive schema is
   `jig/static-design-freshness/1`; native source/static kinds remain original.
   A package-local helper split keeps the legacy reader intact. Independent
   architecture review found no new load-bearing decision requiring an ADR.
2. **Proof categories remain separate.** Actual M04 native evidence plus a
   fresh independent finite attestation clears public recording/revalidation
   and isolated lifecycle completion. Required UNKNOWN remains nonclearing.
   Ordinary fixture prerequisites and 222 disposable
   copy-data probes are explicitly synthetic, not producer executions or APP
   compliance. Original source/runtime/targets and closed records are unchanged.
3. **Real craft recovery, not erased history.** The first craft verdict was
   `needs-changes` for a missing-screenshot/null-equality bypass, with an
   ordering-test nit. Both are fixed with witnessed regression evidence.
   The original nonpass is preserved in
   `verification/slice-04-craft-first.md`; final bounded compliance/craft
   recovery passes preserve their prior whole-review scope honestly.
4. **Validation corrections.** Four initial type-check errors were fixed with
   a guarded non-null narrowing and JSON-object annotation; final pyright has
   zero errors. The inherited test Git environment required command-scoped
   `safe.bareRepository=all` for disposable repository fixtures, not a
   persistent config edit or a Jig gate bypass. All original failure logs
   remain indexed. Final source has 26 static + 25 card tests green; affected
   full review/workflow suites and parent targeted host tests also pass.
5. **Trust and transport limits.** This remains unsigned trusted-local
   consistency over selected static snapshots. Canonical runtime targets are
   rehashed; native loader labels are provenance, not host-loader attestation.
   No visual-quality/actual-face/interaction/backend/full-APP or arbitrary
   app-DONE claim follows. Original source/policy residuals, including old
   unsupported-Jig prose, remain byte-exact.
6. **Remaining ceremony is not pre-credited.** Reconciliation review, normal
   RECONCILED/commit/DONE and stacked ready PR follow this log. Publication is
   the post-DONE delivery action in AC8; the all-AC/close-out boxes are checked
   only after those actions really complete.
7. **Reconciliation accounting recovery.** The first reconciliation pass
   returned `needs-changes` solely because the sweep did not explicitly name
   the shared implementation/test and spec/planning files. Its actual nonpass
   is retained in `verification/slice-04-reconciliation-first.md`. The grouped
   dispositions below now account for the complete child-owned changed-file
   set; implementation and the frozen proof index are unchanged.

### Reconciliation sweep

Scope is this child's tracked diff against exact parent
`756f39dcdd842f9cdf3b34b6924e9b216212af13` plus its untracked new deliverables,
enumerated with `git diff --name-only <parent>` and
`git ls-files --others --exclude-standard`. Inherited parent-stack changes
that a generic `main...HEAD` inventory also lists are not this slice's edits;
the old 119-01/02/ADR-0065 records remain separately byte-preserved.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `skills/_common/{design_bindings.py,static_design_bindings.py,test_static_design_bindings.py}` | `updated` | Explicit schema dispatch and strict JSON-array reads reuse the existing reader; the finite package-local consumer and synthetic regression fixtures cover complete static binding, including craft repairs. No evaluator/runtime boundary added. |
| `docs/specs/119-mixed-design-evidence-attestation/{spec.md,plan.md,tasks.md,slice-04-static-source-compatibility.md}` | `updated` | Additive 119-04 framing, exact-parent plan, actual progress, verification table, honest deviation log and this sweep. Original closed 119-01/02 and distinct 119-03 are not repurposed. |
| `docs/specs/119-mixed-design-evidence-attestation/{reviews,verification}/slice-04-*.md` | `updated` | Actual independent verdicts, original nonpasses, full-pass/recovery provenance and proof receipt retained. Later ceremony metadata is distinguished from the frozen implementation-proof index. |
| `README.md` | `no-op` | Existing external review rail, no new skill/default/install command. Finite encoding belongs in owning live guidance. |
| `docs/specs/README.md` | `updated` | Regenerated from real lifecycle; finite-scope invariant retained in Notes. Regenerate/audit again after DONE. |
| `docs/product-vision.md` | `no-op` | UC-4/7/20 already frame gated slices, independent review and producer consumption. No broader product-management/evaluator scope. |
| `docs/architecture.md` | `updated` | Grounded package-local static helper, same ADR-0065 ownership, strict link/alias authority and exact finite proof limits. |
| `CLAUDE.md`, `AGENTS.md`, scaffold primers | `no-op` | No new skill/hook/decision surface; 119-03 remains DRAFT, so spec-close compression does not apply. |
| `docs/inbox.md` | `no-op` | Related broad visual-oracle/autonomy ideas remain broader; this finite consumer does not resolve them. |
| `docs/refinement-todo.md` | `no-op` | No parked runtime/oracle/quality or other deferred decision is silently activated. No new deferred decision from this slice. |
| `docs/memory/learnings.md` | `updated` | `memory.py add-learning` records witness-presence-before-equality and nonvacuous semantic regressions; summary run, existing team opt-out respected. |
| ADR index / ADR-0065 / closed 119-01/02 | `no-op` | Existing accepted ownership; independent architecture pass requires no new ADR. Fourteen closed/accepted byte pins rechecked unchanged; no amendment authorization inferred. |
| `skills/independent-review/{SKILL.md,design-bindings.md,review.py}` | `updated` | Explicit static grammar/authority, public recipe, no scalar downgrade, original residuals and finite-only scope. |
| `hosts/{claude,codex,copilot}` | `updated` | Official generation and drift guard, including corrected final screenshot guard. No installed plugin changes. |
| Proof and nonpass history | `updated` | Actual independent responses, real native refusals, original craft nonpass/repair, actual vs synthetic transcripts and frozen 247-file implementation-proof index retained. |
| Leanness / lightweight decisions / conventions | `no-op` | Required finite closures justify package-local code; arch pass found no speculative framework. No out-of-spec UI/copy decision and no convention change. |

## Amendments

### 2026-10-22 — Explicit owner-directed publication removal

The owner explicitly requested removal of app-specific examples and proof
documents, including affected mixed-document sections. Those materials were
removed rather than pseudonymized, and the corresponding portions above were
removed under that grant. Exact pre-cleanup files and PR text were privately
archived first; this edited publication is not the original selected record
bytes and does not revise the historical result or rebind an old hash.

Generic consumer behavior, FAIL/UNKNOWN policy, strict binding/currentness
requirements, independent synthetic/control tests and conventions are
unchanged. Private pilot/runtime/worktrees and original producer records were
not deleted or rerun. Historical branch/toolchain pins describe only their
preserved original epoch, not the current identity of edited documents.
