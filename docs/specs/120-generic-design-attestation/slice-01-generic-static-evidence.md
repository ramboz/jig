---
status: DONE
dependencies: [adr-0066]
last_verified: 2026-10-22
arch_review: true
review_reopened_at: 2026-10-22T19:11:28Z
---

## Slice 120-01 — attest generic static evidence

**Goal:** A developer can record and reuse an honest, current design
attestation for different non-card interfaces using the existing review rail,
without shipping the former pilot runtime.

**DoR:**
- The owner explicitly selected retirement of unmerged pilot interfaces and
  clean product-only replacement pull requests.
- The retained source profile, normalizers, comparisons and tolerances keep
  their meanings. Successor helper filenames are confirmed, not invented.
- The original effort union and clean main boundary are identified in spec.md.
- ADR-0066 captures the bounded read/hash-only design and retirement policy.

**Acceptance Criteria:**

1. **Public rail.** `review.py design-review`, `record-review`,
   `check-reviews`, and the existing REVIEWED/DONE evidence gates share the
   selected static binding check. A fresh supported native PASS can be
   recorded/reused. Invalid selected passing evidence is rejected before
   overwriting existing evidence; checks/transitions refuse without changing
   state. No new pass, lifecycle, frontmatter contract selector or evaluator.
2. **Native authority.** Preserve the producer's overall PASS/FAIL/UNKNOWN,
   exit code, required inventory/outcomes and reasons. A component success or
   high composite never overrides native nonpass, missing/unknown required
   outcomes, contradictions, or incomplete run/nonce/raw-digest links.
   Required expectations come from independently approved policy, not result
   rows. No recomputed score, threshold waiver or producer repair.
3. **Independent source and policy.** Verify selected source approval,
   manifest/request domains, approved target, complete source artifacts,
   current original root/file/git freshness, independent exact-policy review,
   frozen/installed grading/config/driver and runtime identity. Verify the
   actual generic transitive helper bytes; no card module dependency or old
   approval relabelling. Current git identity uses only a bounded local
   identity read; no producer execution or network.
4. **Independent delivery.** Verify separately selected current candidate
   inputs/configuration, build recipe/input/output hashes, complete output
   and delivery trees, and retained served-response bytes. Different current
   candidate/build/delivery, output or response tampering, changed runtime,
   missing/foreign run/nonce links, ownership/link substitutions, partial or
   aliased inventories and unsafe paths cannot clear.
5. **Explicit retirement.** Any selected `jig/design-freshness/1` or
   `vellum-design-input/0.1-pilot` contract refuses actionably, including mixed
   static/retired namespaces, malformed/missing selected comparisons and
   binding-only selection. No silent scalar fallback or schema alias.
   Public instructions do not prescribe the old C1/pilot validator lane.
6. **Component-agnostic product.** Reuse the bounded
   `vellum-confirmed-source/0.2` / `static-css-subset/1` /
   `static-source-contract-app/1` profile. IDs, roles, source goals,
   environment and resources are input data, never card inventories or
   geometry in runtime. Keep supported producer restrictions that validate
   actual evidence meaning. Do not add a provider registry, query language,
   arbitrary build framework, new quality engine, or producer imports/calls.
7. **Preserved baseline.** Existing no-selection scalar design-review and
   unflagged slice behavior remain unchanged. Compliance, craft,
   reconciliation and other flagged reviews stay independently necessary.
8. **Executable proof.** Two structurally different non-card fixture inputs
   use the actual supported generic profile, with different roles, required
   IDs/counts and resource layouts. Exercise the actual public
   recording/check/lifecycle boundary, native FAIL/UNKNOWN, independent
   source/build/delivery staleness, output/served tamper, ownership and
   explicit retired-contract refusals. Synthetic prerequisite review records
   exist only inside tests and are labelled TEST ONLY; they are not
   application completion or a real approved-source epoch.
9. **Installable closure.** New and changed selected-attestation payloads in
   regenerated Claude, Codex, Copilot and supported project-vendored packages
   include the generic helper import closure and usable instructions. Those
   payloads contain no pilot validator/runtime/C1 pointer, old proof exports,
   or absolute private roots. Tests verify installed entrypoints, not only
   source imports. Unrelated inherited skill/example cleanup is outside the
   owner-authorized effort-only replacement.
10. **Honest documentation and records.** Document the supported profile,
    exact local selection grammar, retirement/renewal and ownership limits.
    Keep old accepted/DONE effort records untouched, and claim no new real
    app approval/completion or arbitrary-provider support.

**DoD:**
- [x] All ACs pass with focused existing test runners.
- [x] Witnessed failing regression tests precede implementation.
- [x] Independent compliance review passed.
- [x] Independent craft and architecture review passed.
- [x] Implementation review passed.
- [x] Deviation log and reconciliation sweep reflect actual changes.
- [x] Reconciliation review passed.
- [x] Generated host packages and status board are current.

**Anti-horizontal-phasing check:** One slice delivers public recording and
lifecycle enforcement for reusable static evidence, including installable
packages and explicit refusal of the retired interface.

### Close-out (post-DONE)

- [x] Regenerate and audit `docs/specs/README.md`.
- [x] Check primer surfaces and scaffold templates; no permanent active-spec
  detail is needed beyond the derived board.

### Deviation log (after reconciliation)

1. The first compliance pass found an incomplete interpreter-alias chain and a
   source-relative grammar reference in installed prompts. Both were corrected
   test-first: aliases must form a complete bounded chain ending at the pinned
   interpreter, and the prompt resolves the reference beside its actual helper.
2. The recovery pass verified those fixes, then interpreted the original AC9
   literally across every existing package. It found pre-existing private
   paths in unrelated `vision-elicitation` examples. The owner's scope is only
   effort PRs 242–245, so AC9 was clarified to the new/changed selected-
   attestation payloads rather than expanding into unrelated product cleanup.
   The original wording was:

   > **Installable closure.** Regenerated Claude, Codex, Copilot and supported
   > project-vendored packages include the generic helper import closure and
   > usable instructions. They contain no pilot validator/runtime/C1 pointer,
   > old proof exports, or absolute private roots. Tests verify installed
   > entrypoints, not only source imports.

3. The wider regression run exercised 1,137 tests: 1,135 passed and two
   unchanged reservation end-to-end tests failed. Both failures reproduced
   from freshly fetched `origin/main` at `e3fb1283`; no unrelated fix was
   folded into this effort. The initial focused boundary recovery exercised
   539 tests successfully; the final native-profile recovery exercised 545.
4. Craft and architecture passed. The craft nit about repeated raw-file reads
   was accepted as non-blocking without adding speculative caching or altering
   the preserved reader semantics; optimization can follow measured gate cost.
   No provider or quality framework, new lifecycle/pass, or additional
   configurability was introduced.
5. Two producer-generated non-card TEST ONLY native epochs, with seven and nine
   required facts, cleared the actual Jig read/hash, public recording/checking
   and REVIEWED path. Foreign-run recording refused atomically; a changed
   scratch attestation blocked DONE without changing state, and restoration
   cleared again. All 215 indexed upstream artifacts were unchanged afterward.
   Vellum source cut `d41c5ef56fa41be618d5cf1e6aac1705622de2fd` is final.
   Servo subsequently found a preparation collision/no-follow defect requiring
   changed evaluator bytes and new test epochs. Both fresh epochs were then
   checked independently against reviewed Servo implementation commit
   `a62a475ac8f2cc4a33fa0c15c3393ec24224018b`: every captured code row, all
   215 artifacts, four static helpers, six source helpers and native engines
   matched. Fresh public Jig readback/refusal checks cleared without any
   producer/evaluator/browser invocation or upstream artifact mutation.
   The producer's correspondence receipt has raw SHA-256
   `4072117c6fccfc2fa53d5a5c6fd9e4dfd3f12834b04049b65e291f9111e9195b`.
   Original acquisition claims and earlier wrappers remain unchanged historical
   evidence. This establishes post-acquisition byte correspondence and product
   compatibility only, not retrospective approval of an acquisition, real
   source approval or application completion.
6. The first actual native carrier read refused the supported package-manager
   interpreter chain: file aliases traverse a directory alias before reaching
   the pinned canonical executable. This exposed an overly narrow local
   context restriction, not a producer wire change. With parent-confirmed
   authorization, alias-only metadata now permits a direct child of a selected
   canonical directory and substitutes only declared literal component
   prefixes. Complete file/directory chains remain bounded and pinned;
   ordinary Refs/Trees and canonical root constraints stay no-follow.
   The initial native refusal and regression red are retained outside product
   payloads. Missing/changed hops, cycles, escapes, undeclared prefixes and
   symlinked metadata roots are negative controls.
7. Both native carriers also exposed the old static reader's one-component/
   positive-static-weight restriction. Servo confirmed that its existing
   finite driver can declare static-required weight zero plus a nongated
   scalar quality row. The parent authorized a bounded literal roster read,
   not a new grading framework: exact names/order/declared numeric weights are
   bound to the pinned driver, native overall and required authority stay
   unchanged, and no composite is recomputed. Score zero at allowed threshold
   zero is not relabelled a failure. Dynamic/malformed/extra/duplicate rows,
   invalid scores/weights/exits, missing static evidence and native nonpass
   remain non-clearing. The initial native restriction refusals and test red
   are retained outside the product payload; original carriers were not
   altered or rebound.
8. Delta compliance found a literal-roster reassignment hidden by a Bash
   backslash-newline; craft then found a multiline indexed write that escaped
   assignment-pattern counting. The final correction does not enumerate shell
   writes: require one literal roster in original bytes, normalize lexical
   continuations for reference detection, and reject every non-comment
   `COMPONENTS` reference outside that array. The finite supported native
   driver needs no other reference; unsupported shell forms fail closed.
   Both regressions were witnessed red then green, and independent recovery
   passed. This is not a general shell evaluator.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Existing skill entrypoint and installation choices remain; detailed selected-profile guidance belongs with independent-review. |
| `skills/independent-review/{SKILL.md,design-bindings.md,review.py}` | `updated` | Generic native authority, exact selection grammar, retirement, installed reference, complete alias metadata and bounded literal roster documented. |
| `docs/workflow.md` | `updated` | Existing rail described with selected source/policy/runtime/current-delivery revalidation; no new lifecycle/pass. |
| `docs/product-vision.md` | `no-op` | Existing UC-4/7/15 frame this bounded workflow/review/install behavior. No new product-management or evaluator responsibility. |
| `docs/architecture.md` | `updated` | Shared reader/static checker, limited Git metadata probe, native composition, alias boundary and claim limits grounded in reviewed code anchors. |
| Primers and scaffold primer/workflow templates | `no-op` | No new skill, host requirement or standing user hygiene; the skill-local reference ships through existing copy/render paths. No 120 active entry was added to compress. |
| `docs/inbox.md`, `docs/refinement-todo.md` | `no-op` | Existing deferred oracle/guard decisions are not resolved by this finite consumer. No registry, arbitrary-provider or optimization work was added. |
| `docs/memory/{glossary,learnings}.md` | `updated` | Selected-evidence term and complete interpreter-chain freshness learning persisted; team-check honors existing opt-out. |
| `docs/decisions/README.md` / ADR-0066 | `updated` | Exact owner-approved decision accepted via normal frame-evidence gate; index regenerated/clean. Historical ADR-0065 and closed 119 effort records were not imported or amended. |
| `hosts/{claude,codex,copilot}` | `updated` | Unified generation and drift guard pass; reader/grammar hashes match source; all supported installed/vendored entrypoints exercised. |
| `docs/specs/README.md` | `updated` | Regenerated status and advisory review-routing data; board audit clean. Coverage has no missing use cases; three pre-existing untraced specs remain advisory. |
| Final native carrier / upstream code cut | `no-op` | Fresh two-epoch carriers read/hash-checked against final reviewed Servo `a62a475` and Vellum `d41c5ef` code; all 215 artifacts unchanged. No producer imports/calls, approval rebinding or real-app completion claim. Private raw carriers/wrappers remain session artifacts, not product exports. |

**Leanness:** retained one finite read/hash checker and existing rail; no
producer imports/calls, registry, arbitrary build framework, quality engine,
extra pass, new lifecycle or speculative cache. The non-blocking repeated-read
nit was not turned into new machinery. No lightweight out-of-spec product
decision was made, and no conventions or historical closed record was changed.
