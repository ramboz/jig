# Changelog

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
