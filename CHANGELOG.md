# Changelog

## [2.7.1](https://github.com/ramboz/jig/compare/v2.7.0...v2.7.1) (2026-07-15)


### Bug Fixes

* **install-contract:** reject unregistered public skills ([#93](https://github.com/ramboz/jig/issues/93)) ([6769508](https://github.com/ramboz/jig/commit/67695085467fc80032af35cc7041c465e4cf7fd8)), closes [#89](https://github.com/ramboz/jig/issues/89) [#91](https://github.com/ramboz/jig/issues/91)
* **skills:** enforce codex description limit ([#101](https://github.com/ramboz/jig/issues/101)) ([7d538ea](https://github.com/ramboz/jig/commit/7d538ea068db8cd8f1a1d381abf8935b516df8c7))
* **spec-workflow:** preserve slice status through rollup ([#87](https://github.com/ramboz/jig/issues/87)) ([a247f76](https://github.com/ramboz/jig/commit/a247f76a17804f702cdb9963b59bcb51774de7f7))
* **tdd-loop:** preserve node default test discovery ([#102](https://github.com/ramboz/jig/issues/102)) ([950242d](https://github.com/ramboz/jig/commit/950242d9e5cf3da39feabd86cddd310b75ba2400))


### Documentation

* **bugs:** reserve 008-flaky-host-package-drift-guard ([de9f171](https://github.com/ramboz/jig/commit/de9f17158df3809eceaf89838eeba82a94a39b7d))
* **contributing:** document bundled skill workflow ([#94](https://github.com/ramboz/jig/issues/94)) ([53d66c3](https://github.com/ramboz/jig/commit/53d66c31a0920b23da35cd68fe58de05b44c79f9)), closes [#92](https://github.com/ramboz/jig/issues/92)
* **decisions:** accept adr-0036 ([2a5497f](https://github.com/ramboz/jig/commit/2a5497fda331a399df289e744321c7923fa18ab5))
* **spec-090:** draft immutable release contract ([b2a6182](https://github.com/ramboz/jig/commit/b2a6182d2d5520bed9aac413d259b4bc7cbeadca))
* **spec-090:** refine immutable release contract ([6978213](https://github.com/ramboz/jig/commit/69782133f4d852acc6330ec1c6a688682bb1be93))

## [2.7.0](https://github.com/ramboz/jig/compare/v2.6.0...v2.7.0) (2026-07-12)


### Features

* **spec-workflow:** orient existing projects on pickup ([0c57970](https://github.com/ramboz/jig/commit/0c57970111d4c5ba94c0f35ba7bb2c0feeadb0f2))


### Documentation

* **specs:** reserve 088-project-orientation ([3e14298](https://github.com/ramboz/jig/commit/3e14298e7f3dbda5faa3f250ea4f878cc9f9ac55))

## [2.6.0](https://github.com/ramboz/jig/compare/v2.5.0...v2.6.0) (2026-07-11)


### Features

* **051-04:** start-time claim-collision guard on → IN_PROGRESS ([#83](https://github.com/ramboz/jig/issues/83)) ([000c836](https://github.com/ramboz/jig/commit/000c836d83a64f31d35d69b7cf6f24fcebd47e89))
* **078:** gate-bypass telemetry + refinement-todo cleanup pass ([5c31da0](https://github.com/ramboz/jig/commit/5c31da069fa1559c33198477cc1ea9409aac60c6))
* **086:** skill-routing eval harness + description sharpening + CI gate ([fbee6a7](https://github.com/ramboz/jig/commit/fbee6a7f73a58f511f5f2a468f7881c66282dadc))
* **087-01:** narrow-first investigation guidance in reviewer prompts + agent ([8d999b5](https://github.com/ramboz/jig/commit/8d999b57cdb68a1c58c49d2bf37a1b39d37617fe))


### Bug Fixes

* **bug-004:** segregate terminal bug-board rows + document terminal invariant ([#77](https://github.com/ramboz/jig/issues/77)) ([9ee24a9](https://github.com/ramboz/jig/commit/9ee24a9090c2b59c970a3184539c3cd033c68aaf))
* **bug-005:** count top-level markdown list items in diagnose gate ([#82](https://github.com/ramboz/jig/issues/82)) ([bebefd7](https://github.com/ramboz/jig/commit/bebefd781e68db6d8622fd7804b7bbfaa6eb3384)), closes [#80](https://github.com/ramboz/jig/issues/80)
* **build:** swap README logo asset jig.png → jig.jpg ([772664c](https://github.com/ramboz/jig/commit/772664c33c0515872e33b73228130a7b1630a54c))
* **explain:** sync no-cap surface test with reworded SKILL.md prose ([8273ec9](https://github.com/ramboz/jig/commit/8273ec9d3a485b1015ee75579051696e396990c4))


### Documentation

* **034:** reframe federation into two topologies — hub-first (ADR-0028) ([6cc57d2](https://github.com/ramboz/jig/commit/6cc57d2bb8dc514119a2fb39508cb22944962b11))
* **bug-fix:** fix craft-pass instruction (pr-review skill, not review.py pr-review) ([1f828cf](https://github.com/ramboz/jig/commit/1f828cfd4c7c599cc71b00a082df897070ff9d43))
* **conventions:** add output-shape + host-neutral skill rules; bound explain term-lists ([ff4191c](https://github.com/ramboz/jig/commit/ff4191c2c143126b72214e7ab5578546f70aae97))
* **decisions:** add ADR-0034 (interaction altitude) + ADR-0035 (active plan-mode driving) ([6cee6d1](https://github.com/ramboz/jig/commit/6cee6d1dede49e754fba3c22b49dde5047196264))
* **readme:** add logo ([8ae9c4c](https://github.com/ramboz/jig/commit/8ae9c4c8204011f25186341afcce3cd5942a4508))
* **readme:** add logo ([0f02bc4](https://github.com/ramboz/jig/commit/0f02bc47d4aca5985a0e1e0bf976697d4cb485ca))
* **specs:** reserve 086-skill-routing-eval ([888557d](https://github.com/ramboz/jig/commit/888557da4643c5f752ded093a2c0079e6da72592))
* **specs:** reserve 087-narrow-first-review ([272ce01](https://github.com/ramboz/jig/commit/272ce01b4978badc33d2c7b6449108fd7eef8188))

## [2.5.0](https://github.com/ramboz/jig/compare/v2.4.1...v2.5.0) (2026-07-04)


### Features

* **reframe:** jig:reframe corpus re-baselining — accept ADR-0024 + implement spec 067 ([#70](https://github.com/ramboz/jig/issues/70)) ([25d6c7b](https://github.com/ramboz/jig/commit/25d6c7bedf076233e4a07c87e4380e8efa7f8da3))
* **spec-workflow:** abandoned as lifecycle state ([#73](https://github.com/ramboz/jig/issues/73)) ([84887d1](https://github.com/ramboz/jig/commit/84887d157c700a4ac2fb9f037c2a0b6a25893999))


### Documentation

* **conventions:** document new abandonned state ([143e1e9](https://github.com/ramboz/jig/commit/143e1e9ad27327bd9434961708fd2bc7b9894625))
* **inbox:** record reframe occurrence-3 (ASV platform-agnostic re-baseline) ([fa1a844](https://github.com/ramboz/jig/commit/fa1a84483224c6a4ff42304b546f6b38e277a309))
* **specs:** reserve 085-abandoned-state ([d932559](https://github.com/ramboz/jig/commit/d932559969d8cdb58cf14fcbcd4e734a596b4040))

## [2.4.1](https://github.com/ramboz/jig/compare/v2.4.0...v2.4.1) (2026-06-30)


### Bug Fixes

* **spec-workflow:** surface bug registry ([#66](https://github.com/ramboz/jig/issues/66)) ([c24a9e6](https://github.com/ramboz/jig/commit/c24a9e614fd016b71d74fe82a792fa28b2a045d1))
* **test-detection:** detect node --test runner ([#68](https://github.com/ramboz/jig/issues/68)) ([027a194](https://github.com/ramboz/jig/commit/027a194d5bbd96aa1b6dee7ca95823b766765ed6))

## [2.4.0](https://github.com/ramboz/jig/compare/v2.3.0...v2.4.0) (2026-06-30)


### Features

* **layout:** configurable docs_root foundation — ADR-0033 + spec 084-01 ([b620120](https://github.com/ramboz/jig/commit/b620120018dd2cda17d9df9bc47bd0db735aedfc))
* **layout:** route helpers + discovery through project_layout (spec 084-02) ([bddac71](https://github.com/ramboz/jig/commit/bddac71dd5f74835b6deaa81a551d44f228fe547))
* **layout:** scaffold-init --docs-root + subtree push-refusal (spec 084-03) ([80d92b4](https://github.com/ramboz/jig/commit/80d92b49cdbbff2ecf14bc208d1246304e68cfa1))


### Documentation

* **memory:** sync spec 084 (configurable docs root) ([557775a](https://github.com/ramboz/jig/commit/557775a12ecab194328da4939a01d20be4bc0437))

## [2.3.0](https://github.com/ramboz/jig/compare/v2.2.0...v2.3.0) (2026-06-29)


### Features

* **slice-land:** servo unscaffolded-suggestion (spec 072-02) ([e040a45](https://github.com/ramboz/jig/commit/e040a45c91090b69241ce69d8be82b238909730c))


### Bug Fixes

* **workflow:** warn on stale branch base ([fe413ce](https://github.com/ramboz/jig/commit/fe413ce5b5fb193907b6d81d82df2a71e0bbed91))


### Documentation

* **decisions:** ADR-0024 — add rewrite disposition + emergent-work section (reframe n=2) ([be2ea25](https://github.com/ramboz/jig/commit/be2ea259413db73317e3d357e60ea267bb5be340))
* **decisions:** ADR-0032 (Proposed) — conformance-layer topology half ([966c870](https://github.com/ramboz/jig/commit/966c870032cb91b76333e58c7c0b72ae057dc1b0))

## [2.2.0](https://github.com/ramboz/jig/compare/v2.1.0...v2.2.0) (2026-06-27)


### Features

* **decisions:** lightweight decision records for non-spec changes (083-01..03) ([2875fd7](https://github.com/ramboz/jig/commit/2875fd73d11ad034d827eec88f33565566235870))
* **decisions:** session decision scan Stop hook (083-04) ([16ae3db](https://github.com/ramboz/jig/commit/16ae3db84352099f6f0eae6b56b852bce8157917))
* **decisions:** spec 083 Phase 2 — routing rubric, single-sourced ADR trigger, in-flight capture (083-05/06/07) ([#60](https://github.com/ramboz/jig/issues/60)) ([006d67d](https://github.com/ramboz/jig/commit/006d67d38b509b6b425a7a4fa088ab0f22580f4a))


### Bug Fixes

* **python:** restore Python 3.9 compatibility + add 3.9.6 to CI matrix ([8ac2181](https://github.com/ramboz/jig/commit/8ac21816f336fd477caca6424566950042f522c3))


### Documentation

* **decisions:** ADR-0030 — minimum supported Python is 3.9 (Accepted) ([ca78899](https://github.com/ramboz/jig/commit/ca78899b6515e4f6bb01af56162b95c5b267ef05))
* **decisions:** reserve adr-0031-load-bearing-decision-adr-trigger ([e52578a](https://github.com/ramboz/jig/commit/e52578a60242db731d30436b80f4c86fc46b96e8))
* **specs:** reserve 083-lightweight-decision-records (DRAFT) ([bdf0187](https://github.com/ramboz/jig/commit/bdf018790eb52f12fa0264c67a80a2c3497c23b4))
* **specs:** spec 083 Phase 2 design — scan-triage-route + Codex validation (083-04..08) ([882c7ca](https://github.com/ramboz/jig/commit/882c7caf51f2fc1dc44e3e9104922c7179d79405))

## [2.1.0](https://github.com/ramboz/jig/compare/v2.0.1...v2.1.0) (2026-06-25)


### Features

* **bug-fix:** add bug core helper ([570d6bb](https://github.com/ramboz/jig/commit/570d6bb9c58d219ba96a8e43c26b64311a706590))
* **bug-fix:** add escalation seam, close gate, origin reservation ([648815c](https://github.com/ramboz/jig/commit/648815cec7eb987a27172824c38a64d341dbc13f))
* **bug-fix:** add review evidence gate ([ecc78b4](https://github.com/ramboz/jig/commit/ecc78b4e8e64f0807c82829a338c92b8381b8a27))
* **bug-fix:** add transition gates ([31cbcb4](https://github.com/ramboz/jig/commit/31cbcb4e52526badf8e90c6adf47433859a9aeca))
* **bug-fix:** ship jig:bug-fix skill + plugin wiring + workflow routing (058-06) ([045de44](https://github.com/ramboz/jig/commit/045de4410e412d0b8db868974fad65f75517ae3b))
* **tdd-loop:** add targeted test selector ([bf7f2e5](https://github.com/ramboz/jig/commit/bf7f2e5f59bdf574f963bfccdf0d1bdeece41022))


### Bug Fixes

* **release:** refresh v2.0.1 host packages ([87580fb](https://github.com/ramboz/jig/commit/87580fb71ec957a4663ade0a4f2877c54027bd47))


### Documentation

* **specs:** close 058-01 ([cd486ba](https://github.com/ramboz/jig/commit/cd486baa1bc11289f9ddb43ac9ed1552d15998d9))
* **specs:** close 058-02 ([7925b5d](https://github.com/ramboz/jig/commit/7925b5d372afd178c99c6f1b0732a5b655ff3787))
* **specs:** close 058-03 ([dfcf76d](https://github.com/ramboz/jig/commit/dfcf76d96a3a9a22a6890a8a04b2db84d37ec6c8))
* **specs:** start 058-03 ([40d9dbb](https://github.com/ramboz/jig/commit/40d9dbb8562a04450f8726da6c8616b2f5f30eed))

## [2.0.1](https://github.com/ramboz/jig/compare/v2.0.0...v2.0.1) (2026-06-23)


### Bug Fixes

* **ci:** satisfy ruff after v2 release ([9881a4d](https://github.com/ramboz/jig/commit/9881a4d39def2c7f1c24bdf169bc5d52975df68a))
* **codex:** add root marketplace descriptor ([9f127c9](https://github.com/ramboz/jig/commit/9f127c9a21ad3ebab351e0c0076eda8d972f1e54))


### Documentation

* align codex agent primer ([add7f09](https://github.com/ramboz/jig/commit/add7f0920d055d99b6318525316cb0162fb18d82))
* simplify install commands ([d1e05d7](https://github.com/ramboz/jig/commit/d1e05d72e53e46602e081a3178013215104919a2))

## [1.15.0](https://github.com/ramboz/jig/compare/v1.14.0...v1.15.0) (2026-06-13)


### Features

* **review:** add attest-only design_review pass (spec 071) ([#52](https://github.com/ramboz/jig/issues/52)) ([1d23958](https://github.com/ramboz/jig/commit/1d23958f0d0edf3a48d76efe52fec02929e01fa7))
* **usage:** add attribution levers ([ab95b6b](https://github.com/ramboz/jig/commit/ab95b6bbbb8290cada5e87405202af8ca7e4a603))
* **usage:** add token usage top rollup ([2761a71](https://github.com/ramboz/jig/commit/2761a71a5960f1adde66de05781b4d90d1965fac))


### Bug Fixes

* **usage:** rename loop var shadowing dataclasses.field import ([a273c11](https://github.com/ramboz/jig/commit/a273c1141774df21969ba71b9c81b840c5ed0396))


### Documentation

* capture design-conformance / visual-oracle thread (inbox + ADR-0022) ([61872cb](https://github.com/ramboz/jig/commit/61872cb739a5c1fd7ab1f4843151a78844065354))
* **specs:** add DRAFT spec 069 — builder-consumes-install-contract ([8d36f0b](https://github.com/ramboz/jig/commit/8d36f0b435247415d8b576e2f3cfb6c62e59e98f))
* **specs:** reserve 070-context-growth-attribution ([e6c6a40](https://github.com/ramboz/jig/commit/e6c6a4023408e95a3f477b5c536038ba1a8fc2ed))

## [1.14.0](https://github.com/ramboz/jig/compare/v1.13.0...v1.14.0) (2026-06-11)


### Features

* **063:** scaffold-precondition gate — route on new, not dead-end ([d1027fb](https://github.com/ramboz/jig/commit/d1027fb6aee9a883f4ed5cd2f34b037aa3506d4d))
* **066:** scaffold-precondition gate for ADR creation (mirror of 063) ([0e551b1](https://github.com/ramboz/jig/commit/0e551b19820b34522efe07b9b218d81169ba6882))
* **spec-workflow:** 068-02 — feed-forward + use-case trace links + grow-on-discovery ([22df91f](https://github.com/ramboz/jig/commit/22df91f3cf7499c943e41e7451805a3777fc6d7f))
* **spec-workflow:** 068-03 — reconcile-phase use-case coverage check ([d9ded4b](https://github.com/ramboz/jig/commit/d9ded4b27e50cc43c5460f8bf2cd9afa3bd0b368))
* **vision-elicitation:** spec 068 slice 01 — use-case capture-seed ([#50](https://github.com/ramboz/jig/issues/50)) ([53f09dc](https://github.com/ramboz/jig/commit/53f09dc4bdecc640da2b7d2f8eaac30787f10a04))


### Bug Fixes

* **063:** jig carries its own scaffold.json so `new` works in the jig repo ([15b3a98](https://github.com/ramboz/jig/commit/15b3a986f132946301dea90f557a400a46bc5e32))


### Documentation

* add ADR-0025 (Accepted) + spec 068 (use-cases breadth layer) — frame-critique passed ([8eb3c12](https://github.com/ramboz/jig/commit/8eb3c123376a75f0020df2608aaf03493f284798))
* **decisions:** add ADR-0022 (oracle boundary, parked) + ADR-0023 (lifecycle spine) ([e1920e3](https://github.com/ramboz/jig/commit/e1920e3bfe8f47da5522822637bfd422b8dbdbe3))
* **decisions:** add ADR-0024 (reference reframe, Proposed) — frame-critique passed ([496639e](https://github.com/ramboz/jig/commit/496639e2664270b06bc41615765607c75b243399))
* **decisions:** reserve adr-0022-pluggable-oracle-boundary ([80d55af](https://github.com/ramboz/jig/commit/80d55afd245f425e8237fa9ceedf7662474e63a4))
* **decisions:** reserve adr-0023-lifecycle-family-spine ([153ef63](https://github.com/ramboz/jig/commit/153ef631eb13873644b952f8c38fd9d48d3df494))
* **inbox:** capture workspace-coexistence-map gap + validated four-layer positioning ([995f100](https://github.com/ramboz/jig/commit/995f100938d8b214c0f8a63b289e69e654052afd))
* **memory:** capture ADR-0022/0023 learnings + lifecycle-spine hot-cache entry ([c03d4f3](https://github.com/ramboz/jig/commit/c03d4f3896d4f0ea42bc4fd58f866aee155aa4a3))
* reconcile spec 068 §A4 framing + park detailed-use-case-MD design ([341a492](https://github.com/ramboz/jig/commit/341a49283bb853a8b51e4c2b9a2c7cf3d1f822cb))
* regen status board + ADR index for ADR-0025 / spec 068 ([6919487](https://github.com/ramboz/jig/commit/691948709dfe536929ea8ad2409f0e8025d125f5))
* **specs:** draft spec 067 (reframe) — /jig:reframe correction capability ([c531b45](https://github.com/ramboz/jig/commit/c531b45c53d32b97c52b088cc491601b4181b59a))

## [1.13.0](https://github.com/ramboz/jig/compare/v1.12.0...v1.13.0) (2026-06-08)


### Features

* **064-04:** derived frame_review trigger + close the session-plan dispatch gap ([c60f677](https://github.com/ramboz/jig/commit/c60f677db0057e644e91d226f452b0b3c98d1e24))
* **064-05:** ADR-side frame-critique accept-gate — closes spec 064 ([e37b60b](https://github.com/ramboz/jig/commit/e37b60bd938652c38fff38c4994b02c346fa28ec))
* **064:** spec/ADR frame-hardening — spike GO, grounding, frame-critique pass (spec-side) ([bcc4cc2](https://github.com/ramboz/jig/commit/bcc4cc2b36dc0732a66f4b0485895f4566feb2a3))


### Documentation

* add milestone roadmap (1.x on main, 2.0 multi-host on v2) ([#48](https://github.com/ramboz/jig/issues/48)) ([61d26b3](https://github.com/ramboz/jig/commit/61d26b347a4ac63dbc20687377b98a38c876c9b4))
* add token-cost reduction principle to vision + README ([541e8ae](https://github.com/ramboz/jig/commit/541e8aecf109255af557ae98dd4e44ffec28eff1))
* **memory:** consolidate spec-064 session learnings ([3a7d4f9](https://github.com/ramboz/jig/commit/3a7d4f99f0202be196e11f7348f52ab31e9c829a))
* **refinement-todo:** park learning-loop idea as evidence-gated ([a583072](https://github.com/ramboz/jig/commit/a583072e95ddb73e393b0f3cad4a2161a5758dc6))

## [1.12.0](https://github.com/ramboz/jig/compare/v1.11.0...v1.12.0) (2026-06-07)


### Features

* **065-01:** lexicon foundation — shipped lexicon + project-glossary overlay ([aa06bc3](https://github.com/ramboz/jig/commit/aa06bc3256b0b2286690288f97d8060f27f58977))
* **065-02:** jig-memory-scan surfaces lexicon definitions ([5e79b43](https://github.com/ramboz/jig/commit/5e79b4339d0ab98843edf155c31614848ba6fcdc))
* **065-03:** /jig:explain skill — term + artifact modes ([a319ba7](https://github.com/ramboz/jig/commit/a319ba7172a6c092ad810126281a4cdbd03b2327))
* **065-04:** self-defining vocabulary convention — closes spec 065 ([d21401a](https://github.com/ramboz/jig/commit/d21401a046e79c51a590d9217fd5bde04b916892))
* **065-05:** /jig:explain passage mode — explain a pasted snippet ([dd83c2d](https://github.com/ramboz/jig/commit/dd83c2dc11911a4f3dba5f422e93b56f9e85f753))


### Documentation

* accept ADR-0021 (lexicon home + overlay) ([4cf6089](https://github.com/ramboz/jig/commit/4cf60891083ee52b49dcb84a3cab52af05898e5c))
* **refinement-todo:** park cross-spec sequencing affordance behind a 3-signal trigger ([ff661a9](https://github.com/ramboz/jig/commit/ff661a9bd3bcc6a4a9fe1afdbd9cae57f0992c7b))

## [1.11.0](https://github.com/ramboz/jig/compare/v1.10.0...v1.11.0) (2026-06-07)


### Features

* **code-health:** distinct code-health reviewer pass, gated (060-05) ([7c9468d](https://github.com/ramboz/jig/commit/7c9468d8ace210dad6b49b8ebd475e30306523f3))
* **code-health:** dogfood a CI Ruff floor onto jig (060-02) ([091d9f7](https://github.com/ramboz/jig/commit/091d9f717ab71913f987ff926f5ed56ab8f5fc7b))
* **code-health:** duplication dimension — native-first + npx jscpd fallback (060-04) ([de13966](https://github.com/ramboz/jig/commit/de1396672bd4a692837eb50b1d7282bff695daff))
* **code-health:** jig:code-health skill + health.py — Python lint detect-and-drive (060-01) ([5a5bf45](https://github.com/ramboz/jig/commit/5a5bf451b93b9d5a6e9d8c411ac96496282bc91d))
* **code-health:** table-driven multi-ecosystem health.py — Node + advisory complexity (060-03) ([e3162c9](https://github.com/ramboz/jig/commit/e3162c9266d351037d901e8919d478d2e2e0997b))
* solo→team re-detection — memory-sync nudge + stale audit (spec 050) ([10fecbc](https://github.com/ramboz/jig/commit/10fecbc99ac27d113ac61a079b48d4d2046573f2))


### Bug Fixes

* **scaffold:** ship verifier modules in release zip so completion self-check runs ([3cde55a](https://github.com/ramboz/jig/commit/3cde55a7b48337b398e71fa671791490ecf9aec8))


### Documentation

* **060:** draft code-health-capability — ADR-0017 + 6 slices ([59f8acc](https://github.com/ramboz/jig/commit/59f8accaa0949074ae8ec813b19e80b05bd877d2))
* **architecture:** correct hook count to 9 and refresh runtime wiring ([9ad139b](https://github.com/ramboz/jig/commit/9ad139bcdf753f4818ef455cafc2c5469e0ee635))
* **decisions:** accept adr-0017 scaffolded code-health ([58b3cbc](https://github.com/ramboz/jig/commit/58b3cbcef72acc306eac19951c0672f864844804))
* **decisions:** regen adr index — adr-0017 accepted ([ee7ec30](https://github.com/ramboz/jig/commit/ee7ec309bf6539258ec2e2552730608135ab1109))
* **decisions:** reserve adr-0020-spec-frame-hardening ([d140d40](https://github.com/ramboz/jig/commit/d140d40c4e3084b6dc5c96445d772fbcdf13eb7f))
* **decisions:** reserve adr-0021-lexicon-home-and-overlay ([e5d415a](https://github.com/ramboz/jig/commit/e5d415a58b03ad84aa44178aabecc205847bc48b))
* draft ADR-0020 + spec 064 spec-frame-hardening ([d2b6184](https://github.com/ramboz/jig/commit/d2b61842628ac93ee807f42684fc5c98f5923ec8))
* draft refactor/migration workflow — ADR-0019 + spec 062 ([6824cd1](https://github.com/ramboz/jig/commit/6824cd1d1d4007f3bac230012422c6414ea62511))
* draft spec 065 (lower vocabulary barrier) + ADR-0021 ([02238e3](https://github.com/ramboz/jig/commit/02238e30a9f0ee729fd60cfe737a27cbabc272e3))
* **prompts:** reframe scaffold + spec-loop as consecutive stages ([9e8fbb5](https://github.com/ramboz/jig/commit/9e8fbb5a61e4491b5e53ea327e7e303d917dfe5e))
* **specs:** draft 063-scaffold-precondition-gate ([df16582](https://github.com/ramboz/jig/commit/df16582b70581e556312000e6b68e845353648f8))
* **specs:** reserve 064-spec-frame-hardening ([4c4cc15](https://github.com/ramboz/jig/commit/4c4cc15ed729aa6f940118b8cdf0acd3403d48a7))
* **specs:** reserve 065-lower-vocabulary-barrier ([2f393a6](https://github.com/ramboz/jig/commit/2f393a684825dc26484c48829a7296cc6c5ec4c1))

## [1.10.0](https://github.com/ramboz/jig/compare/v1.9.0...v1.10.0) (2026-06-04)


### Features

* **041:** add routing-stats histogram; close spec 041 (skill-routing observability) ([ceb31ec](https://github.com/ramboz/jig/commit/ceb31ec78c24c294589f37f0cabf86a26abc1611))
* **047:** enforce the plugin/release install contract (047-01) ([61293e7](https://github.com/ramboz/jig/commit/61293e7674f2227dc4a381a0cc8e7c411c018e71))
* **047:** enforce the scaffold-target install contract (047-02; closes spec 047) ([2086c58](https://github.com/ramboz/jig/commit/2086c5815b33f97d512e9a8786b01bbe2613dddf))
* **049:** slice-claim on IN_PROGRESS — claim/release + opt-in reserve-on-main + board rendering (closes spec 049) ([#35](https://github.com/ramboz/jig/issues/35)) ([0cce8b3](https://github.com/ramboz/jig/commit/0cce8b30b5580066f22928b3d35b8d64b03d0f98))
* **055:** keep verbose command output out of the orchestrator (055-04 DONE; closes spec 055) ([59b8404](https://github.com/ramboz/jig/commit/59b8404ee559ee9afdb6068f08ff8a6b707eb174))
* **056:** exact .jig/spec-ref attribution marker (056-03 DONE; closes spec 056) ([6e34bc2](https://github.com/ramboz/jig/commit/6e34bc2f09a725dbecaeedc3e5c00b8640cae198))
* **056:** per-spec orchestrator usage report — usage.py (056-01 DONE) ([206bbe7](https://github.com/ramboz/jig/commit/206bbe7211aeb6a25c8c0edeecca1dbac852967c))
* **056:** subagent accounting via nested transcripts (056-02 DONE) ([d7cfc2e](https://github.com/ramboz/jig/commit/d7cfc2e27e444690281d1fe8cf010b19b35d4d3b))
* **057:** thin-orchestrator discipline — three cost levers ([#36](https://github.com/ramboz/jig/issues/36)) ([cea217a](https://github.com/ramboz/jig/commit/cea217a16e6f8f2a94b472ce7a2255bf8eb57080))
* **reserve:** worktree-aware reservation (workflow.py/adr.py new from any worktree) ([#33](https://github.com/ramboz/jig/issues/33)) ([63fcd32](https://github.com/ramboz/jig/commit/63fcd32291627025f4c661d1fd07cd684bbb94d9))


### Bug Fixes

* **secret-scan:** stop flagging type annotations as .env secrets ([25b2f5e](https://github.com/ramboz/jig/commit/25b2f5e02e66fadff0dbd6fd76ed27d83f9fe603))


### Documentation

* **057:** apply clarify — pin 057-01/02 decisions + add 057-03 output-discipline slice ([96a435b](https://github.com/ramboz/jig/commit/96a435ba29fd6efe0abc3e17e7c974539425056d))
* **057:** draft thin-orchestrator spec — delegation-first sessions + active compaction ([f57920d](https://github.com/ramboz/jig/commit/f57920d0d5a4eba371294a165d0029f3e2b173d6))
* **057:** move slices to READY_FOR_REVIEW + fix three-lever framing ([81bb9e6](https://github.com/ramboz/jig/commit/81bb9e67290c75b103caa26c96110ab514e25259))
* **058:** design bug-fix workflow — ADR-0016 + spec 058 + slices ([52657f4](https://github.com/ramboz/jig/commit/52657f429170f64e0723cab35be21dc2f4acd8f4))
* **CLAUDE:** add Context-cost discipline pointer to the Key-terms Hot Cache (spec 055 follow-up) ([8ae5cb3](https://github.com/ramboz/jig/commit/8ae5cb33162cdfbff75b73572bf80b3d3a10e849))
* **decisions:** reserve adr-0016-bug-fix-lifecycle ([cfffe08](https://github.com/ramboz/jig/commit/cfffe083095c09451eaa493946710ab7389ef0aa))
* **front-door:** promote release-zip install to a README option ([1d00d0f](https://github.com/ramboz/jig/commit/1d00d0fa22410a2e141a6357ac4f731bff0146dc))
* **readme:** name the AI-native principles jig encodes ([#34](https://github.com/ramboz/jig/issues/34)) ([17b2c60](https://github.com/ramboz/jig/commit/17b2c6002a45fbb5159edacdc12c5fc7f36753ea))
* retire obsolete security-lens slices + sweep stale deferred items ([488dd3e](https://github.com/ramboz/jig/commit/488dd3e72a7cd4aed2d625ecd6576d007900aa7d))
* **specs:** author spec 056 token-usage-tracking (step 1; READY_FOR_REVIEW) ([fcf82d1](https://github.com/ramboz/jig/commit/fcf82d105e430060e0f426dae2ac731becadc0b1))
* **specs:** claim 049-01 — claim-and-release-on-transition (claude/competent-banach-f69ece) ([a98372a](https://github.com/ramboz/jig/commit/a98372a34975b01a04e17abc5197ec654586093d))
* **specs:** release 049-01 live-dogfood claim (restore slice to pre-claim DRAFT state) ([7b5e6f5](https://github.com/ramboz/jig/commit/7b5e6f59497d88ea23e8bf6b0afbc2459090d620))
* **specs:** reserve 058-bug-fix-workflow ([9a5f720](https://github.com/ramboz/jig/commit/9a5f720c3ce5f1f73a000aa587a30e6483d68b42))

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
