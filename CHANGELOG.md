# Changelog

## [1.9.0](https://github.com/ramboz/jig/compare/v1.8.0...v1.9.0) (2026-06-02)


### Features

* **045:** review-evidence lifecycle gates (slices 01-04) ([#28](https://github.com/ramboz/jig/issues/28)) ([ddb8f35](https://github.com/ramboz/jig/commit/ddb8f35ff90b915a8c36cf9d628a60ea6cb5be0b))
* **048:** close guidelines-gap-response slices 1-4 ([#27](https://github.com/ramboz/jig/issues/27)) ([13b5202](https://github.com/ramboz/jig/commit/13b5202a10f8736ff19b87a81a076ae6849cf89a))
* **052:** security-scaffold floor — secret-scan + permissions.deny + security-review baseline ([#30](https://github.com/ramboz/jig/issues/30)) ([716cf5f](https://github.com/ramboz/jig/commit/716cf5fd6a7bb77c1e2954229b0c1aa6d6aa8494))
* **055:** context-cost discipline — delegate-reads guidance (055-01 DONE) ([e0b6f71](https://github.com/ramboz/jig/commit/e0b6f71dfd9761bfd7fe41b6a153cecc818437cc))
* **055:** in-session context-growth nudge (055-02 DONE) ([4a3679f](https://github.com/ramboz/jig/commit/4a3679f1ffca7e6ac6613909db24c2ff57166fb2))
* **055:** read-once / read-lean discipline (055-03 DONE) ([51c8644](https://github.com/ramboz/jig/commit/51c864407d9518f85a165ac3a7475c7b3633fc81))
* **adr:** spec 036-01 — closed-spec drift policy (ADR-0008) ([9dc3d1c](https://github.com/ramboz/jig/commit/9dc3d1c4378ee10f388c9ce13f395b190b40e5d7))
* **migrate:** spec 038-04 — additive tier upgrade via copy-machinery ([d566f1b](https://github.com/ramboz/jig/commit/d566f1b95241b51be3e81f16cc755b0c569fb3ae))
* **scaffold-init:** spec 038-02 — gate skill copy by installed_tiers ([5cc7afd](https://github.com/ramboz/jig/commit/5cc7afd85fe2b5c1fc8955f8fbdfdb62016e4a76))
* **scaffold:** seed reference spec + scaffold-completion verification (048-05, 048-06) ([325f9ba](https://github.com/ramboz/jig/commit/325f9ba7e9afa3b1e27c58cd0363a10c7a560f62))
* **slice-land:** spec 037-01 — origin-aware FF check + push-fail recovery hint ([d7bc373](https://github.com/ramboz/jig/commit/d7bc373238558584020f963ce4943c7a41df1430))
* **spec-workflow:** spec 036-02 — closed-spec drift sweep + reconciliation hook ([2d2a8d0](https://github.com/ramboz/jig/commit/2d2a8d06d4aa58329d4c8b595fcf6c9a557730a5))
* **spec-workflow:** spec 037-02 — origin-aware reservation + diverged-main preflight ([cdc4ee0](https://github.com/ramboz/jig/commit/cdc4ee0416d1f5a119ce60e847e703c19278f336))


### Bug Fixes

* **agents:** drop dead review queue contract (039-01) ([68e7a33](https://github.com/ramboz/jig/commit/68e7a337bd31c63cd47b1b41eeb0260d48c95447))
* **decisions:** renumber ADR-0010 -&gt; ADR-0012 (collision with landed main ADR-0010) ([7a5d2db](https://github.com/ramboz/jig/commit/7a5d2db33aa7fe6daaed4c260d0b2c80cd150f69))
* **review:** route craft/arch pass to richer user skill via file-read dispatch ([734e424](https://github.com/ramboz/jig/commit/734e4249278dae209aacad17b1ea8ed0187525cc))
* **scaffold:** derive jig_version from plugin manifest (046-02) ([b246f8e](https://github.com/ramboz/jig/commit/b246f8e4fa44f6c9f15abe9c62b75f7229614d1c))
* **scaffold:** render install-shape-aware docs in scaffold mode (046-01) ([cb6bd3f](https://github.com/ramboz/jig/commit/cb6bd3f3f3d39231be2d499a471694c0308f0e00))


### Documentation

* apply ADR-0010 — fold live-prose amendments inline ([cc6e74f](https://github.com/ramboz/jig/commit/cc6e74f631f1cfba58230a0fdb332cb2c3c28e8a))
* **decisions:** land ADR-0010 — amendment scope (records vs. live prose) ([6224f14](https://github.com/ramboz/jig/commit/6224f143de41457cc8e3bb4e36857624193f71c3))
* **front-door:** clarify install shapes (acquire vs scaffold mode) ([5dae981](https://github.com/ramboz/jig/commit/5dae98160d3c6998ad30557bf1d49b1faf294658))
* **front-door:** restructure public docs into a routing hub (spec 054) ([#29](https://github.com/ramboz/jig/issues/29)) ([71053a0](https://github.com/ramboz/jig/commit/71053a0855331de8e5f32e59b90a8a8e2771e1c8))
* **memory:** capture cold-start cliff diagnosis + stale-plugin-install gotcha ([c4dd901](https://github.com/ramboz/jig/commit/c4dd9015768dcd847ac3e2c4a3eafaaf7fbd5846))
* **memory:** capture reserve-numbers-on-origin/main learning ([88096c5](https://github.com/ramboz/jig/commit/88096c568ef42dd81df5a189be62c5362a6a958c))
* **memory:** close-out after spec 036-02 — sweep patterns + status board ([3f64bb6](https://github.com/ramboz/jig/commit/3f64bb681796e790b30b177a14a6651e0c32b288))
* **memory:** memory-sync after spec 036-01 lands ([4b8b1a1](https://github.com/ramboz/jig/commit/4b8b1a107331d68a205ad3f8308037ab56829d88))
* security-scaffold spec 052 + ADR-0013; refresh 048 gap inventory ([#26](https://github.com/ramboz/jig/issues/26)) ([84bee7b](https://github.com/ramboz/jig/commit/84bee7b2263196bf4fc7370c34961ee5a73a5524))
* spec 040-01 — align reviewer-isolation claims with SKILL.md caveat ([b7117c5](https://github.com/ramboz/jig/commit/b7117c516668438159e9c2b9d9ae58902fd56fe2))
* **spec-gate:** spec 042-01 — deliberateness-gate framing (ADR-0011) ([fa5bd3d](https://github.com/ramboz/jig/commit/fa5bd3df9c94eb90f1d2642d52a246d69efc791e))
* **specs:** add federation collision radar slices ([de88ba8](https://github.com/ramboz/jig/commit/de88ba81a222374f3b4594a767de14457e180e0d))
* **specs:** add spec 051 — worktree-aware number reservation ([e9282b7](https://github.com/ramboz/jig/commit/e9282b77a0f79d1989bf630bba6c933795cee534))
* **specs:** add spec 055 context-cost-discipline (READY_FOR_REVIEW) ([1559985](https://github.com/ramboz/jig/commit/155998546a490a48880e7b8b5a7f32e31076c226))
* **specs:** draft spec 048 guidelines gap response ([45d47ea](https://github.com/ramboz/jig/commit/45d47ea1a76f2a8cab3769f092ca804623ced12b))
* **specs:** draft specs 045-047 (review/scaffold/install) ([c7ad0b0](https://github.com/ramboz/jig/commit/c7ad0b0457420da1859aa83d0c21accce281c16d))
* **specs:** rescue specs 049/050 from silly-kilby worktree ([5ce2026](https://github.com/ramboz/jig/commit/5ce20267b898e1a474bf4014d9822820203dbbba))
* **specs:** retroactive spec 053 for craft/arch-pass file-read dispatch ([66bec76](https://github.com/ramboz/jig/commit/66bec769b208e4f1bb86300b9b94f59377a28f3b))
* **specs:** spec 038 — ADR-0010 tier-gating decision + slice reshape ([e36b312](https://github.com/ramboz/jig/commit/e36b312f3d6473e6c15109f18299992bcff827b6))
* **specs:** spec 044 — RTK integration spike DONE (ADR-0009) ([1df03a5](https://github.com/ramboz/jig/commit/1df03a5802094348a8231b28dcf05a8679fa82c5))
* **vision:** spec 038-03 — reconcile tier docs to _TIER_SKILLS ([7210f00](https://github.com/ramboz/jig/commit/7210f0079622462081afe817f8c0d866eda3407d))

## [1.8.0](https://github.com/ramboz/jig/compare/v1.7.0...v1.8.0) (2026-05-27)


### Features

* **_common:** add atomic_write_text helper + sweep 16 callsites (032-01) ([1f2253b](https://github.com/ramboz/jig/commit/1f2253b0aa36388b8ed0a62074672f241b8e5acd))
* **independent-review:** spec 043-04 — wire quality.py into review prompt ([38c0cbb](https://github.com/ramboz/jig/commit/38c0cbba6270126bfe63303b94bca1f9b8d90b4c))
* **scaffold-init:** spec 035-01 — exclude fixtures from installs ([7622869](https://github.com/ramboz/jig/commit/7622869e3247ead9ca2f4a44bc5a3999cfb97b06))
* **scaffold:** scaffold.json is the completion sentinel (032-02) ([d1dd9ec](https://github.com/ramboz/jig/commit/d1dd9ec4841c169b656195727ffb94c1f5793ea3))
* **tdd-loop:** spec 043-02 — calibrate quality.py thresholds ([14c03a8](https://github.com/ramboz/jig/commit/14c03a862b905fe54ae7d31ed6bce3be617a6839))
* **tdd-loop:** spec 043-03 — polyglot extension (vitest + jest) ([8c6084a](https://github.com/ramboz/jig/commit/8c6084aadae33098d95d5f6c23905211ecec9620))


### Bug Fixes

* **scaffold:** copy skills/_common/ in scaffold-mode so helpers import at runtime ([7c2fd23](https://github.com/ramboz/jig/commit/7c2fd233c6a7f9327e251c1c9879e41a80506a64))
* **scripts:** require Python 3.10+ explicitly ([896e8bf](https://github.com/ramboz/jig/commit/896e8bfd60caadab30905dd47906b44b8a49f680))
* support Python 3.9 via __future__.annotations ([bb93747](https://github.com/ramboz/jig/commit/bb93747c3d0a990cf00c0e2f2881118f32cb0da6))


### Documentation

* **specs:** add rtk integration spike ([afb0050](https://github.com/ramboz/jig/commit/afb0050f7dfcc6fe1be277b253869005076dc5c6))
* **specs:** draft 032-atomic-writes — atomic_write_text helper + scaffold marker ([6310cc6](https://github.com/ramboz/jig/commit/6310cc6e559d32762506a81055fcc8a59ee5d927))
* **specs:** draft 034-federation-tier — Tier 2 federation skills ([aedd537](https://github.com/ramboz/jig/commit/aedd5376162bf039f7f2b25372de85f21669edd0))
* **specs:** draft 035-042 — external-review cluster bodies ([2bed474](https://github.com/ramboz/jig/commit/2bed474745e655c7f26bf77863e617421d0e4f00))
* **specs:** draft 043-test-quality-wiring — wire quality.py preflight ([8cbe6ca](https://github.com/ramboz/jig/commit/8cbe6ca6b43c77a1341f9fd07091dd9c574db2f8))
* **specs:** draft host adapter portability ([e09fbb1](https://github.com/ramboz/jig/commit/e09fbb1140f40b20c0070956e4c667df8ba0292e))
* **specs:** reserve 032-atomic-writes ([a33c4ed](https://github.com/ramboz/jig/commit/a33c4ed83e6cebea97c76c11eaad940b445342c7))
* **specs:** reserve 035-fixture-exclusion ([ef2a24b](https://github.com/ramboz/jig/commit/ef2a24b11354927cde3b47fe7c8807e0ecc2c0e8))
* **specs:** reserve 036-closed-spec-drift ([58af583](https://github.com/ramboz/jig/commit/58af5832fa46bc39b077dad72090906fa3bb832c))
* **specs:** reserve 037-git-origin-safety ([204757c](https://github.com/ramboz/jig/commit/204757caeb892cfc0ce21ca5d06fbc8d9b26a5d2))
* **specs:** reserve 038-tier-reconciliation ([5631b67](https://github.com/ramboz/jig/commit/5631b6767895c47cdcde28ff7caab50270d9f07e))
* **specs:** reserve 039-review-queue-cleanup ([4ee9320](https://github.com/ramboz/jig/commit/4ee9320cead513f36d07f0d94af7e57f875701b0))
* **specs:** reserve 040-isolation-honesty ([eff30d8](https://github.com/ramboz/jig/commit/eff30d89cd1778f7cfb5d428df9e3a3ccc55925f))
* **specs:** reserve 041-routing-observability ([4501f7a](https://github.com/ramboz/jig/commit/4501f7abb12541f87912a9004f99f729ffb0c6e4))
* **specs:** reserve 042-spec-gate-model ([e3e8e3c](https://github.com/ramboz/jig/commit/e3e8e3c2eb87f6058d6111eb4e1c619e86b5e1ed))
* **specs:** reshape 043 per clarify pass + transition to READY_FOR_REVIEW ([eda7b87](https://github.com/ramboz/jig/commit/eda7b87e624a700f1190b0d8b5f377309ca02638))
* **specs:** status-board regen + Notes for 035-042 cluster ([6a603b9](https://github.com/ramboz/jig/commit/6a603b942e599dc9ce4929ad37debf5c69bcfd8b))

## [1.7.0](https://github.com/ramboz/jig/compare/v1.6.0...v1.7.0) (2026-05-20)


### Features

* 005-02 — supersede (re-closes spec 005) ([1e04883](https://github.com/ramboz/jig/commit/1e04883ba0632638ae7ca049becd7e11be374ba0))
* 005-03 — boundary-change-detection (closes spec 005) ([1c794ab](https://github.com/ramboz/jig/commit/1c794aba11d0b4b0bcea2d50f7e4ac0848a471b9))
* **review:** adopt richer skill patterns across reviewing skills ([#23](https://github.com/ramboz/jig/issues/23)) ([4164eb8](https://github.com/ramboz/jig/commit/4164eb86cd57fc1056356b241aaf952ad14d8a4b))


### Bug Fixes

* **slice-land:** strip fenced code blocks before counting DoD boxes ([537f041](https://github.com/ramboz/jig/commit/537f0415d4d92244e0d62969c701730b3938a872))
* **spec-workflow:** anchor STATUS regex to line-start to skip prose markers ([d53c5bd](https://github.com/ramboz/jig/commit/d53c5bdbc2407c1dd19788606ae00000979b7183))


### Documentation

* **specs:** 005-02 close-out — status board + close-out checkboxes ([903f1f0](https://github.com/ramboz/jig/commit/903f1f07484e7fcc858cd5d3fe72f064fe0dc124))

## [1.6.0](https://github.com/ramboz/jig/compare/v1.5.0...v1.6.0) (2026-05-20)


### Features

* 028-01 — adr-numbering-on-main ([#20](https://github.com/ramboz/jig/issues/20)) ([42a40fc](https://github.com/ramboz/jig/commit/42a40fcc935de590e5079d0ccda724b758f6a294))
* 028-02 — inbox-and-refinement-todo-append-lock ([d1b4b09](https://github.com/ramboz/jig/commit/d1b4b09a1f7127584c9dbc7a21ff5cd2c189efb0))
* 028-03 — status-board-regen-race-check (closes spec 028) ([1ec8501](https://github.com/ramboz/jig/commit/1ec85010ce87bbaa141a519d643cee4a49fe2488))
* **hooks:** byte-based context-fill estimator + soft-warn (026-01) ([b3a72d0](https://github.com/ramboz/jig/commit/b3a72d0d66a67647bc8eded2a71535b8333ede44))
* **hooks:** post-edit verify hook for Edit/Write/MultiEdit (027-01) ([b63d183](https://github.com/ramboz/jig/commit/b63d1834b858df134f8db6629490a092f83b2013))


### Bug Fixes

* **adr-workflow:** migrate NewTests to mocked subprocess ([#21](https://github.com/ramboz/jig/issues/21)) ([23e9eb8](https://github.com/ramboz/jig/commit/23e9eb85f4dbcac29bf170f49d45a0879b454910))
* **slice-land:** drop `#` prefix from AC labels in PR body ([240e454](https://github.com/ramboz/jig/commit/240e45461f63346d033e6f57ca3bfea0d94e14e1))

## [1.5.0](https://github.com/ramboz/jig/compare/v1.4.0...v1.5.0) (2026-05-19)


### Features

* **spec-workflow:** roll spec.md status up from slice states ([e72c8b2](https://github.com/ramboz/jig/commit/e72c8b2ee1339963aeb3da0f443e004b1123a2f5))
* **spec-workflow:** wire arch-review on-demand pass into post-impl flow (031-02) ([4831112](https://github.com/ramboz/jig/commit/4831112d7c6cbe9c34870acac8aae8fd3f909a0d))
* **spec-workflow:** wire pr-review craft pass into post-impl flow (031-01) ([b353434](https://github.com/ramboz/jig/commit/b353434e13e0d2acf9530fe515d5d0e1edc92206))


### Documentation

* reflect three-pass post-impl review across user-facing docs ([732cf88](https://github.com/ramboz/jig/commit/732cf88ab9e7a424ee4c0fbc3dc362414be48859))
* **specs:** close out 030-01 — spec.md status rollup ([eeddc47](https://github.com/ramboz/jig/commit/eeddc47f29eb91e7945c4f7ef33ff1cb6f8c4416))
* **specs:** draft 031-multi-perspective-review + 2 slices ([d7237d5](https://github.com/ramboz/jig/commit/d7237d5bad12a5f6cd088665c80404ac943dd7fb))
* **specs:** reserve 031-multi-perspective-review ([258d88a](https://github.com/ramboz/jig/commit/258d88aad0ba22169fcda18c7f367e327619f4be))
* **specs:** roll up 029 spec.md status to DONE ([9c6eaaa](https://github.com/ramboz/jig/commit/9c6eaaaa14e1f3a71c73ced1eafe6615696f4cf0))

## [1.4.0](https://github.com/ramboz/jig/compare/v1.3.0...v1.4.0) (2026-05-19)


### Features

* **spec-workflow:** 029-01 — kind: spike frontmatter + body-shape validation ([9a57fe7](https://github.com/ramboz/jig/commit/9a57fe74e63702d9d96813a6373f46e486bf8a2b))
* **spec-workflow:** 029-02 — status-board spike marker ([6b7b36d](https://github.com/ramboz/jig/commit/6b7b36d402f66a269021412eea9b223f56c8b42f))


### Documentation

* add workflow + runtime wiring Mermaid diagrams ([b31ef9e](https://github.com/ramboz/jig/commit/b31ef9eac801407e2effceca917f4014d033c69c))
* **refinement-todo:** close "AI-first onboarding doc" entry ([9d5ebba](https://github.com/ramboz/jig/commit/9d5ebba9adc894a176851ced3cf865e25ef03b75))
* **spec-workflow:** add SPIDR primer + worked-example sibling ([6241f52](https://github.com/ramboz/jig/commit/6241f52485356addb8da109a218ac3400fc0e6c7))
* **specs:** close out spec 013 — all four close-out items resolved ([a4b2433](https://github.com/ramboz/jig/commit/a4b2433bbf3c9521651a4b54db5757a6badd0245))
* **specs:** close out spec 025 — CLAUDE.md compress-on-close-out rule ([e4fe5e9](https://github.com/ramboz/jig/commit/e4fe5e9f6038d3b2ef756ec96f7146d30b93b2d3))
* **specs:** draft 026-028 + refinement-todo entries for jig's long-running-session gaps ([1d5593f](https://github.com/ramboz/jig/commit/1d5593f6c2b1542ebabe4cf380d7962aeea47f34))
* **specs:** draft 029-spike-slices ([6bc01cf](https://github.com/ramboz/jig/commit/6bc01cf6d4deec4aa3f3c384aa4ad6a867a64245))
* **specs:** reserve 029-spike-slices ([171a3b7](https://github.com/ramboz/jig/commit/171a3b7164d13385c7e90c589f1507082101822c))
* **specs:** reserve 030-spec-status-rollup ([859d567](https://github.com/ramboz/jig/commit/859d567a7f974807e5220fceefe15e42881e03df))

## [1.3.0](https://github.com/ramboz/jig/compare/v1.2.0...v1.3.0) (2026-05-18)


### Features

* **analyze:** spec 024-01 — analyze skill + constitution-gate principles-check ([3b9aca9](https://github.com/ramboz/jig/commit/3b9aca93b63a853082f1aef3e1fdb4c6a80f1ddf))
* **clarify:** spec 023-01 — clarify skill (judgment-style, six-category scan) ([77fc3d3](https://github.com/ramboz/jig/commit/77fc3d3320e695e2b1cc011972e82fe7c746f7b1))
* **contracts:** spec 022 — promote stub to judgment-skill + three integrations ([61f51c0](https://github.com/ramboz/jig/commit/61f51c03abe5e443f3c44d2c883bedc67239922b))
* **migrate:** spec 020 slice 020-01 — agentic slice-to-spec workflow ([bfa4e17](https://github.com/ramboz/jig/commit/bfa4e178a94f17d098c13bdb6550bbef3988045d))
* **migrate:** spec 021 slice 021-01 — copy-machinery subcommand ([dedbd74](https://github.com/ramboz/jig/commit/dedbd74541a196b04df42641c605780e01b43426))


### Documentation

* **refinement-todo:** park two follow-ups from spec 022 close-out ([76b864e](https://github.com/ramboz/jig/commit/76b864ea1d1977a58ad55f0335872f79e5c0f808))
* **specs:** draft spec 023-clarify + 024-analyze (DRAFT) ([d77673b](https://github.com/ramboz/jig/commit/d77673b5d3ab352ff99ae76bd2b9d29543b1264f))
* **specs:** reserve 023-clarify ([1c0d906](https://github.com/ramboz/jig/commit/1c0d906a2e05b9c85510d33ac28c55cc307913f9))
* **specs:** reserve 024-analyze ([cd91bac](https://github.com/ramboz/jig/commit/cd91bac4065eaa9e44760767e1e164c5781c6c24))

## [1.2.0](https://github.com/ramboz/jig/compare/v1.1.0...v1.2.0) (2026-05-15)


### Features

* **migrate:** spec 018 slice 018-04 — split-slices subcommand + spec 017 dogfood ([62f5471](https://github.com/ramboz/jig/commit/62f54715f602abbaa1ad39a5101e5236738d7ada))
* **slice-land:** spec 019 slice 019-01 — --no-deviation-log flag ([692c7d1](https://github.com/ramboz/jig/commit/692c7d11c0e105c0d681e6040f57b3a2465a09a1))
* **spec-workflow:** spec 018 slice 018-01 — parser-foundation-and-dual-read ([86d30e0](https://github.com/ramboz/jig/commit/86d30e0a2b2ef6d28cb68cb2a443387787c23cae))
* **spec-workflow:** spec 018 slice 018-02 — caller-recognition-and-fixtures ([057afe7](https://github.com/ramboz/jig/commit/057afe768ffeb2a7f6dc1495ac71e88baf9a5241))
* **spec-workflow:** spec 018 slice 018-03 — scaffold-new-specs-as-file-per-slice ([7300743](https://github.com/ramboz/jig/commit/7300743b3129efa843a4361105635a9d620011c2))
* **vision-elicitation:** spec 017-01 — vision template + arch reshape + product-vision.md seed ([#12](https://github.com/ramboz/jig/issues/12)) ([54e9251](https://github.com/ramboz/jig/commit/54e9251d02feb82ecbbe3951199535ff987c8ca6))
* **vision-elicitation:** spec 017-02 — vision-elicitation skill (judgment-only) ([#14](https://github.com/ramboz/jig/issues/14)) ([bad832f](https://github.com/ramboz/jig/commit/bad832fdca848dec27a4e602a43d9356d083c6d4))
* **vision-elicitation:** spec 017-03 — re-run protocol with hash-based edit detection ([#15](https://github.com/ramboz/jig/issues/15)) ([6db1c8c](https://github.com/ramboz/jig/commit/6db1c8c77e9656920a7c30c27440e526af186879))


### Bug Fixes

* **ci:** derive plugin version from plugin.json in build tests ([75a49aa](https://github.com/ramboz/jig/commit/75a49aab16d4b4909af05513d23fd3c60f5ebd4d))
* **marketplace:** use git-subdir object format for source field ([51a7a12](https://github.com/ramboz/jig/commit/51a7a12943c97bafd0b3efd92a65a5a6b18455b4))

## [1.1.0](https://github.com/ramboz/jig/compare/v1.0.0...v1.1.0) (2026-05-15)


### Features

* **arch-review:** spec 014-01 — lightweight architecture-review baseline with category-based deferral ([1d76d96](https://github.com/ramboz/jig/commit/1d76d96a595da2adb315e402e842030ec24602b0))
* **scaffold-init:** spec 016 slices 01+02 — scaffold-mode (skills/agents + hooks) ([#6](https://github.com/ramboz/jig/issues/6)) ([ba94a2f](https://github.com/ramboz/jig/commit/ba94a2fc89ab65c5725d52aba7e3eef092f80f99))
* **scaffold-init:** spec 016-03 — scaffold-mode default-on + dual-mode docs ([#9](https://github.com/ramboz/jig/issues/9)) ([528b2f6](https://github.com/ramboz/jig/commit/528b2f6acafaa122bf0718928ba61624c6b19e3b))
* **spec-workflow:** revive slice 003-03 as reserve-spec-on-main (READY_FOR_REVIEW) ([b5f528d](https://github.com/ramboz/jig/commit/b5f528df30f1b5b18d5e5ec4f346ff94ff47dc29))
* **spec-workflow:** spec 015 — structured-lifecycle-metadata ([#7](https://github.com/ramboz/jig/issues/7)) ([b518927](https://github.com/ramboz/jig/commit/b5189271b09e5cb16748ab96c3fc8299be7cc2af))
* **spec-workflow:** workflow.py new &lt;slug&gt; reserves spec numbers on origin/main (slice 003-03) ([e9dd318](https://github.com/ramboz/jig/commit/e9dd31833e082d26165050d1bf5c976fbc7faa45))


### Bug Fixes

* **scaffold-init:** refuse-on-unmanaged-hooks safety check before filesystem mutation ([#10](https://github.com/ramboz/jig/issues/10)) ([86a2bd6](https://github.com/ramboz/jig/commit/86a2bd6914a722d03da6b8f4eb307f3a7cfc5656))
* **slice-land:** make ExecuteDryRunTests branch-independent ([#5](https://github.com/ramboz/jig/issues/5)) ([3c25549](https://github.com/ramboz/jig/commit/3c25549e7ac6880029b564e446ff9574bb99211e))
* **spec-workflow:** prevent parse_existing_notes from gluing adjacent table rows ([cdf036d](https://github.com/ramboz/jig/commit/cdf036dde1f819f156cae0890243e3d995553480))


### Documentation

* **memory:** refresh Tier 1 glossary entry for built skills ([36ac94d](https://github.com/ramboz/jig/commit/36ac94d31aefda0c1b47f3a5627f5f515e661de2))
* **readme:** add "Why jig exists" motivation section ([#11](https://github.com/ramboz/jig/issues/11)) ([c767932](https://github.com/ramboz/jig/commit/c7679327b99bfe666c2d82b5b32e6a2047b218bb))
* **readme:** fix Claude Desktop plugin install steps ([8562299](https://github.com/ramboz/jig/commit/85622997be1c42d349c3848045b6efb6c108fe66))
* **spec-workflow:** post-spec-015 close-out — SKILL.md, memory, deferred slices, conventions ([#8](https://github.com/ramboz/jig/issues/8)) ([5f00801](https://github.com/ramboz/jig/commit/5f00801ba1b12577bb0ec8110943b9829cb1d5d9))

## [1.0.0](https://github.com/ramboz/jig/compare/v0.1.0...v1.0.0) (2026-05-15)


### Features

* **adr-workflow:** introduce skill (slice 005-01) ([635afe7](https://github.com/ramboz/jig/commit/635afe722407805eaf9609c2ff336f5e399a93b4))
* **adr-workflow:** jig self-migration to docs/decisions/ (slice 008-03) ([3ef5ec8](https://github.com/ramboz/jig/commit/3ef5ec85af0658631a200841a5801cbec960e384))
* **ci:** spec 013-release-pipeline — CI + release-please + zip + install docs ([#1](https://github.com/ramboz/jig/issues/1)) ([846cc7b](https://github.com/ramboz/jig/commit/846cc7baa0869c128cd9c239707a8f737734a076))
* **independent-review:** promote from stub to active (slice 004-01) ([02354d9](https://github.com/ramboz/jig/commit/02354d934fab2aa4f1f1530d29409740dab2ec4c))
* initialize jig skill pack with Tier 0 structure and specs ([3d04d9b](https://github.com/ramboz/jig/commit/3d04d9b6673688d3b3c6212785805becf5c0f8e5))
* **memory-sync:** implement slice 002-01 (explicit-sync) ([21ba179](https://github.com/ramboz/jig/commit/21ba179e9d9ffc955e1105bd1108604aeb9db020))
* **memory-sync:** implement slice 002-02 (lookup-pattern) ([8ef1319](https://github.com/ramboz/jig/commit/8ef1319fcd4ebd1766c0e8845e42846f88f60c57))
* **memory-sync:** implement slice 002-03 (auto-detect-hooks) ([3be2945](https://github.com/ramboz/jig/commit/3be2945a424682f8fcd926fe04867df3f4fd6e1b))
* **memory-sync:** implement slice 002-04 — spec 002 complete ([7d9b0a0](https://github.com/ramboz/jig/commit/7d9b0a0b185349f61092225ff306a303d781d267))
* **migrate:** introduce skill with report subcommand (slice 008-01) ([75390bc](https://github.com/ramboz/jig/commit/75390bc4a8d0a050f290bff819ca79381802b494))
* **migrate:** rename-decisions subcommand (slice 008-02) ([d133888](https://github.com/ramboz/jig/commit/d1338882963443e9ed82e4a5cde270fd2371637a))
* **plugin-self-install:** spec 011 — local install + verify + caller upgrade ([fd57625](https://github.com/ramboz/jig/commit/fd57625056d3ab69110f808ddd0000dd31374e45))
* **pr-review:** introduce lightweight baseline PR review skill (slice 012-01) ([b5e88ab](https://github.com/ramboz/jig/commit/b5e88abf54f6047c22ebc94d454d44ad1370789a))
* **scaffold-init:** implement slice 001-01 (greenfield-scaffold) ([3ca6207](https://github.com/ramboz/jig/commit/3ca62072d3dcb68af28d4dd39f01b0e587b83546))
* **scaffold-init:** implement slice 001-02 (doc-content) ([235e58a](https://github.com/ramboz/jig/commit/235e58ae78decfe5b59394ce37d720d96ac11f9e))
* **scaffold-init:** implement slice 001-03 (signal-detection) ([e57a198](https://github.com/ramboz/jig/commit/e57a198c83312fbeb7ad45d58c6b7403965b6cce))
* **scaffold-init:** implement slice 001-04 (deferred-decisions) ([3daf79a](https://github.com/ramboz/jig/commit/3daf79afb1c392b7aa4f9df861a35ead2e47db93))
* **scaffold-init:** implement slice 001-05 (wizard-qa) — completes spec 001 ([ce38a0c](https://github.com/ramboz/jig/commit/ce38a0c8c0077a4ad204eae1e1891fab099a2cbc))
* **scaffold-init:** refuse on spec-driven layout, suggest /jig:migrate (slice 008-05) ([07ca5e3](https://github.com/ramboz/jig/commit/07ca5e31cea107b67bd74f1ef0a83280a1f899bc))
* **slice-land:** 007-03 pr-mode-execute — push + gh pr create ([8a56a33](https://github.com/ramboz/jig/commit/8a56a33244e1db2b1764bf1d080e16abc1874dc8))
* **slice-land:** exclude Close-out subsection from DoD count (slice 009-01) ([5faa0a1](https://github.com/ramboz/jig/commit/5faa0a1aa619307244dc1ee98bc6a10509ec92b3))
* **slice-land:** introduce skill (slice 007-01) ([d047a61](https://github.com/ramboz/jig/commit/d047a61886a6a950851107330de2f2e57bf08023))
* **spec-workflow:** auto-tick review-passed DoD boxes on transition (slice 003-04) ([a70891b](https://github.com/ramboz/jig/commit/a70891be1ca4e29d37a817e543039b9111453d37))
* **spec-workflow:** promote from stub to active (slice 003-01) ([4811aa3](https://github.com/ramboz/jig/commit/4811aa31c1988a11dacbcea67ac156a9c8663ff9))
* **tdd-loop/slice-land:** 006-04/05 tdd fixes + 007-02 execute + spec_lint ([91d6724](https://github.com/ramboz/jig/commit/91d67241d8a3d8abbd1204ad05737e9955e22c2a))
* **tdd-loop:** introduce skill (slice 006-01) ([04e638d](https://github.com/ramboz/jig/commit/04e638de5dc3d291ea59fde55d4238f09dcb1fea))


### Bug Fixes

* **pr-review:** broaden deferral from name-specific to category-based ([a096d16](https://github.com/ramboz/jig/commit/a096d16084c38020af0056f2058720d5eec5e475))


### Documentation

* **adr:** ADR-0001 scaffold-stable trigger; resolve refinement-todo item ([ad2401d](https://github.com/ramboz/jig/commit/ad2401df2afe524e761c7830bcf94a169482dcf6))
* **adr:** ADR-0002 — contracts skill stays a deliberate stub ([3920ee0](https://github.com/ramboz/jig/commit/3920ee02fd77d3025987c124c8fc303818e9dcff))
* **adr:** ADR-0004 — rename docs/adrs/ to docs/decisions/ with adr- prefix ([d00e483](https://github.com/ramboz/jig/commit/d00e483c518fa63138db46ce0f9fa3a6229ca024))
* **contributing:** install-snapshot-lag dev-loop runbook ([199e091](https://github.com/ramboz/jig/commit/199e091885094f6c7e25f9b433cc62c6fbf12252))
* **inbox:** park adobe-security-suite lens integration as candidate spec 008 ([5e98892](https://github.com/ramboz/jig/commit/5e9889224a4a50f1cd8d836e59e17da8f5a5358a))
* **inbox:** park JIRA integration idea ([755d952](https://github.com/ramboz/jig/commit/755d952f614216fbfdce50d02065167a602efbd5))
* **inbox:** park multi-persona reviewer expansion idea ([c3a38d1](https://github.com/ramboz/jig/commit/c3a38d1622a5dedd6a10144078bd586fd4cefbdd))
* **inbox:** park plugin self-install as candidate spec 008 ([aea1364](https://github.com/ramboz/jig/commit/aea13641a411dc0ce561fbf1469f0de4d98793bc))
* **inbox:** park slice-landing workflow idea ([656a34c](https://github.com/ramboz/jig/commit/656a34c107eb611c8d4f974833589e4c1916454b))

## [Unreleased]
