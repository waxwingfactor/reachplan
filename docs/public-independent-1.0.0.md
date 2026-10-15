# Independent public ReachPlan v1.0.0 verification

Verified UTC: 2026-10-15T19:34:49.650316+00:00

Result: **PASSED**. Independent AI-agent verification of the actual [public release](https://github.com/waxwingfactor/reachplan/releases/tag/v1.0.0). Downloads used unauthenticated public browser-download URLs with curl; no development checkout, editable installation or PYTHONPATH supplied package code.

The public tag, build record and [successful CI run](https://github.com/waxwingfactor/reachplan/actions/runs/38794423881) all identify source commit `a48c9ec480866ffd51aabc36977b58fa7592e179`. The public Git commit API also verifies the build-record source tree as `fdb088905547767167cb7248fd96324cd725724b`. Public wheel and source core, bundle and CLI files match the supplied independently reviewed SHA-256 values.

## Published assets

| Asset | SHA-256 |
| --- | --- |
| [BUILD-INFO.json](https://github.com/waxwingfactor/reachplan/releases/download/v1.0.0/BUILD-INFO.json) | `0195e66b94284af48108a1f3c316cdfffaf4cbf58ddd413ad9eec5479ff99845` |
| [reachplan-1.0.0-py3-none-any.whl](https://github.com/waxwingfactor/reachplan/releases/download/v1.0.0/reachplan-1.0.0-py3-none-any.whl) | `19971f03670271c7de39327e3f1d0fca2951ef6fcaf70e493c7aae885edf2221` |
| [reachplan-1.0.0.tar.gz](https://github.com/waxwingfactor/reachplan/releases/download/v1.0.0/reachplan-1.0.0.tar.gz) | `30b2f8bd81d923ce4a121335eca7a6adb68ae14487c7646d5a685f34b39564de` |
| [SHA256SUMS](https://github.com/waxwingfactor/reachplan/releases/download/v1.0.0/SHA256SUMS) | `c93d494c8fa6b57010e0e5b3f4dfdf3c1141acc71cd6bab59bb6902f4dc6fc82` |

All three entries in SHA256SUMS matched. All four downloaded assets also matched their GitHub release-API SHA-256 digests. Every hashed wheel RECORD member matched its recorded digest and size.

## Fresh environment checks

Environment: Darwin 25.5.0, arm64; Python 3.12.13. Separate wheel and source virtual environments were created outside the development checkout. The wheel installed with `pip install --no-index`; the sdist built and installed from the downloaded archive with separately obtained build tooling. All package imports were checked to resolve inside the appropriate fresh virtual environment. Extracted package source was removed before executing the installed-package tests.

| Check | Public wheel | Public sdist installation |
| --- | --- | --- |
| Constructed example | Exit 3 | Exit 3 |
| Unique / repeated verified length | 160 / 20 m | 160 / 20 m |
| Draft / review length | 125 / 35 m | 125 / 35 m |
| Invalid header; no output directory | Exit 2; passed | Exit 2; passed |
| Reviewed attempt with accepted follow-up dated 2026-10-15 | coverage_complete; 0 remaining | coverage_complete; 0 remaining |
| Original campaign excludes later follow-up | Passed | Passed |
| Relocated bundle after removing original inputs | Passed | Passed |
| Relocated verification with sockets disabled | Exit 0 | Exit 0 |
| Modified summary rejected; restored bundle accepted | Exit 2 then 0 | Exit 2 then 0 |
| Tests shipped in actual public sdist, installed packages only | 40 passed | 40 passed |

Socket-disabled verification used a separate `python -I` process with both `socket.socket` and `socket.create_connection` replaced by functions that raise before the installed CLI was imported. This demonstrates the verification path needs no Python socket connection; it is not an operating-system firewall test.

The actual source archive includes architecture, contracts, research, review and verification documentation; all three CSV example inputs; and its test suite. The wheel includes the built-in example resources.

## Reviewed code hashes

| File | SHA-256; matches wheel and sdist |
| --- | --- |
| core.py | `aecc11755843ab1cc211b91fbe2a421deaaba084b47e42a94a4c7af6c810678f` |
| bundle.py | `aa0fb12f976db9d2783afa765e077670b71565abb8bc08a7237326ae661bb2db` |
| cli.py | `02363b7d50df636d6dcc072be9f55f3bd6bd4dca1f107b941e0c64d62f94fb0e` |

## Limits

These checks exercise synthetic records within the advertised supported workflow. They do not validate real sewer records, field safety, cleaning effectiveness or evidence authenticity. Source rebuild success is established; byte-for-byte reproducible archive builds are not claimed.

One additional verifier assertion was corrected during this run: replaying the original date window after resolving synthetic barriers still properly returned exit 3 because 30 m remained beyond declared reach. This was an incorrect harness expectation, not a release failure.

The accompanying machine-readable record is [public-independent-1.0.0.json](public-independent-1.0.0.json). Neither report includes user-specific filesystem paths or secrets.
