# Independent review record

The repository uses required CI and pull requests on protected main. The sole GitHub maintainer may merge after the gate passes. Required approving review count is zero because another account's approval cannot honestly be supplied; independent AI-agent reviews are posted as attributed review comments and recorded here.

Separate agents challenged the discovery and competition, tested the algorithm, and will inspect the implementation before merge. Their findings and the corresponding exact revisions are recorded with the implementation PR. These reviews are AI-agent assessments, not human or customer approval.

A design challenge caught a subtle round-trip precision issue: splitting a 0.003-unit pipe at an unrestricted midpoint produced a 0.0015-unit coordinate that the three-decimal input contract could not accept later. The allocator now splits on the 0.001-unit grid. The same review required independent physical reach envelopes, current barriers within previous coverage, and explicit attempted-pass exclusions.

## Implementation review findings and corrections

A separate AI-agent implementation reviewer ran the tests and examined core/bundle/CLI code and distribution configuration. It found no blocking calculation or unsafe-completion defect, and raised three corrections:

1. Follow-up guidance had retained the old campaign end date, which would exclude genuinely later work. README and generated reports now say to advance the end date to include actual follow-up work; a test demonstrates both outcomes.
2. Fragmented interval subtraction could rescan coverage quadratically. It now retains monotone scan indices. A local 20,000-span subtraction check completed with zero residual intervals; the independent randomized oracle still passes.
3. Historical attempted work needed an explicit resolution path. A responsible reviewer can now mark it `reviewed_attempt` with a required note, preserving the excluded evidence while adding no coverage. A closeout test confirms that unreviewed attempts keep review status, then explicit acknowledgement can clear it after accepted coverage is complete.

The test suite at this stage contains 40 tests, including a separately authored set of 30 tests and 160 seeded randomized oracle cases. Local wheel and source-archive installations also pass in fresh environments outside the checkout. Final revision-specific review comments and CI evidence are attached to the implementation pull request; public downloaded-artifact validation remains a separate gate.

## Exact implementation revision and final signoff

The final separate AI-agent review found no remaining actionable issues in `8523f6f9f6aa1957df71c4f9477db9d573335c5a`. In addition to the 40-test suite, the reviewer compared 5,000 randomized subtraction cases to an independent cell-set oracle and checked a 20,000-pass fragmented job. See the [full attributed review comment](https://github.com/waxwingfactor/reachplan/pull/3#issuecomment-6200557557). After passing required CI, PR #3 merged to release-source commit `a48c9ec480866ffd51aabc36977b58fa7592e179`, with the identical source tree.

The [public-release verification record](verification.md) separately covers actual final-asset download/install checks; no local build is substituted for that release gate.
