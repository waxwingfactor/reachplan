# Architecture and acceptance criteria

`core.compute(inputs, since, as_of)` is the public pure library API. It accepts exactly three canonical filename-to-byte entries and ISO date strings, returning the JSON-compatible plan or raising `InputError`. `core` validates every record, converts intervals to canonical chainage, merges accepted coverage, subtracts it from pipe extent, and intersects each gap with physical endpoint envelopes. `bundle` renders consistent exports, writes guarded directories, and independently recomputes all outputs during verification. `cli` handles arguments, concise status and documented exit codes.

There are no runtime dependencies or network operations. Decimal arithmetic, standard-library CSV parsing and restrictive IDs avoid float merging, executable data and path-derived output names.

## Allocation algorithm

For length L, the from-end envelope is [0,min(L,reach,nearest barrier start)], enabled only by current access. The to-end envelope is [max(0,L-reach,nearest barrier end),L]. Existing coverage has no influence on these envelopes. Intersect remaining gaps with both, union the reachable targets, and retain the difference as review intervals.

If one endpoint covers every reachable target, use it (from-end wins ties). Otherwise, disjoint envelopes already partition the targets. Where envelopes overlap, partition at L/2 rounded down to the 0.001-unit grid and clamped inside the overlap. This assigns every reachable target exactly once and preserves input precision. It does not optimize routes, costs, safety or cleaning effectiveness. Each used endpoint becomes one draft setup containing its assigned target intervals.

Sorting/union is O(n log n) in each pipe's records; gaps, intersections and lengths are linear in their resulting intervals. No network graph search is inferred from node labels.

## Acceptance criteria

- Unique verified plus remaining equals pipe length exactly.
- Draft target union plus review equals remaining exactly; targets never overlap coverage, barriers or each other.
- Every draft coordinate respects the declared endpoint access and full travel limit.
- Reverse-direction passes count correctly; duplicates never inflate unique coverage.
- Current barriers remain effective even inside old verified coverage.
- Attempts and out-of-period records never contribute coverage; in-period attempts remain review items.
- No header-only pass list produces an optimistic coverage-complete result.
- Malformed or unsupported data fails before any new valid bundle is emitted.
- Moving a bundle preserves verification; changing any derived file or source snapshot fails verification.
- Published wheel and source archive install independently of this checkout and carry the constructed example; source archives carry docs/tests.

Tests include concrete failure fixtures, random interval accounting against an independent grid oracle, package CLI lifecycle, malformed inputs, relocation and tamper checks. Review and verification records identify exact tested revisions and environments.
