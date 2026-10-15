# Distribution and verification

Release 1.0.0 ships a pure-Python wheel and source archive through GitHub Releases. No PyPI publication is claimed. The wheel has no runtime dependencies and can be installed using `python -m pip install --no-index path/to/reachplan-1.0.0-py3-none-any.whl`.

The source archive includes the package, examples, tests and documentation. Build with Python 3.10+ and setuptools 77+ using `python -m pip wheel --no-deps source.tar.gz`, or `python -m build` after unpacking it. Source builds require build tooling; offline builds require those tools to be installed or cached. The bundled example is synthetic, not a utility's operating record.

CI tests Python 3.10 and 3.13 on Linux, Windows and macOS. Every matrix job installs the package before running the tests. Required aggregate check `ci` gates main; branch protection applies to the repository owner. Separate AI-agent reviews are recorded candidly; there is no claim of approval by another human or GitHub account.

Actual public release artifact hashes, download/install observations, exact revision and CI links are published in a separate release-verification record after the assets are downloaded from their final public URLs. Preparing a local artifact does not satisfy that verification.

## Actual public release 1.0.0

The [published wheel and source archive](https://github.com/waxwingfactor/reachplan/releases/tag/v1.0.0) were downloaded through unauthenticated public URLs on 2026-10-15. The final assets were installed in separate fresh environments outside the development checkout, without editable installation or PYTHONPATH. Public downloads returned HTTP 200 and matched both SHA256SUMS and GitHub's asset digests.

| Artifact | SHA-256 |
| --- | --- |
| reachplan-1.0.0-py3-none-any.whl | `19971f03670271c7de39327e3f1d0fca2951ef6fcaf70e493c7aae885edf2221` |
| reachplan-1.0.0.tar.gz | `30b2f8bd81d923ce4a121335eca7a6adb68ae14487c7646d5a685f34b39564de` |

Exact release source: [`a48c9ec480866ffd51aabc36977b58fa7592e179`](https://github.com/waxwingfactor/reachplan/commit/a48c9ec480866ffd51aabc36977b58fa7592e179). It has the same tree as the [independently reviewed implementation](https://github.com/waxwingfactor/reachplan/pull/3#issuecomment-6200557557). [Release-source CI](https://github.com/waxwingfactor/reachplan/actions/runs/38794423881) passed 40 tests in each of six Python/OS combinations and a fresh wheel/source installation job. These are source/build checks; public-download tests below were performed separately on macOS arm64 with Python 3.12.13.

The lead's [machine-readable public-artifact observations](public-lead-1.0.0.json) record successful independent wheel/source installations, isolated imports from the fresh environment, expected example review status (160 m unique, 125 m draft, 35 m review), invalid-input and existing-output failures, later-dated closeout with reviewed attempts, relocated verification after deleting original inputs, and tamper rejection. All 40 tests shipped inside the actual downloaded source archive passed against the isolated installed public wheel. The wheel RECORD and the reviewed core/bundle/CLI SHA-256 values also matched. Relocated verification passed with socket access disabled in the Python process.

This establishes the stated synthetic supported workflows in the recorded environments. It does not establish field deployment, customer adoption, hydraulic accuracy of operator-supplied measurements, authenticity of arbitrary result bundles or universal competitor neglect. The original wheel and source assets remain unchanged and tied to the original tag; this later documentation does not replace them. GitHub-enforced release immutability is not enabled.

A separate AI agent independently downloaded the same public assets and repeated installation/workflow checks. It removed extracted package source before running all 40 archived tests against **each** installed distribution. It also independently verified public tag/tree/CI provenance, reviewed code hashes, wheel RECORD, later-date closeout, invalid input, relocation, tampering and socket-disabled verification. See the [independent human-readable report](public-independent-1.0.0.md) and [machine-readable observations](public-independent-1.0.0.json), also published as the release asset [PUBLIC-VERIFICATION.json](https://github.com/waxwingfactor/reachplan/releases/download/v1.0.0/PUBLIC-VERIFICATION.json).
