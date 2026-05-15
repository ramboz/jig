# Changelog

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
