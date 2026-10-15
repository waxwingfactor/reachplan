# Distribution and verification

Release 1.0.0 ships a pure-Python wheel and source archive through GitHub Releases. No PyPI publication is claimed. The wheel has no runtime dependencies and can be installed using `python -m pip install --no-index path/to/reachplan-1.0.0-py3-none-any.whl`.

The source archive includes the package, examples, tests and documentation. Build with Python 3.10+ and setuptools 77+ using `python -m pip wheel --no-deps source.tar.gz`, or `python -m build` after unpacking it. Source builds require build tooling; offline builds require those tools to be installed or cached. The bundled example is synthetic, not a utility's operating record.

CI tests Python 3.10 and 3.13 on Linux, Windows and macOS. Every matrix job installs the package before running the tests. Required aggregate check `ci` gates main; branch protection applies to the repository owner. Separate AI-agent reviews are recorded candidly; there is no claim of approval by another human or GitHub account.

Actual public release artifact hashes, download/install observations, exact revision and CI links are published in a separate release-verification record after the assets are downloaded from their final public URLs. Preparing a local artifact does not satisfy that verification.
