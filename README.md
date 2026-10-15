# ReachPlan

Turn operator-verified partial sewer-cleaning records into exact remaining intervals, draft endpoint setups, and an explicit review list.

ReachPlan is an offline Python CLI and library for an office planner working on independent manhole-to-manhole reaches. It normalizes reverse-direction measurements, counts overlapping coverage once, and respects current endpoint access, usable hose travel and impassable barrier intervals. It generates a portable report bundle that can be recomputed after relocation.

**Supported release: 1.0.0 · Python 3.10+ · no runtime dependencies · MIT**

## Install and run

Download the wheel from the [public release](https://github.com/waxwingfactor/reachplan/releases/tag/v1.0.0), then:

```sh
python -m venv .venv
# Activate .venv using the command for your shell, then:
python -m pip install --no-index ./reachplan-1.0.0-py3-none-any.whl
reachplan example demo
reachplan plan --pipes demo/pipes.csv --passes demo/passes.csv --barriers demo/barriers.csv --since 2026-01-01 --as-of 2026-03-31 --out result
reachplan verify result
```

The constructed example intentionally returns **exit 3**, meaning the bundle was generated and contains work requiring review. It reports 160 m unique verified coverage, 20 m repeated pass length, 125 m draft targets and 35 m outside current geometric reach. Read `result/report.md`; open `summary.csv`, `setups.csv` and `review.csv` in a spreadsheet as needed. All target coordinates are measured from each pipe's **from-node**, even for a setup at its to-node. Travel is separately measured from the chosen access node.

A wheel installs without network access or compilation. Building the source archive requires setuptools 77+; see [distribution and verification](docs/verification.md). Use `python -m reachplan` if the script directory is absent from PATH.

## Complete one job

1. Prepare the three CSV files using the [exact input contracts](docs/contracts.md). State only extents an operator has **verified as adequately cleaned**. Nozzle extension, an attempted pass or CCTV distance alone is insufficient. Use `attempted` for unverified extents.
2. Supply the current access and operator-approved usable travel from each endpoint. List current impassable barrier intervals, including ones inside previously cleaned portions. A shared manhole does not connect separate pipes in this model.
3. Generate a new bundle for an explicit inclusive campaign period. Review every proposed setup and unresolved interval using your approved field procedures. A draft never changes coverage.
4. After work, append new independently identified `verified` passes with the actual accepted extents. For an investigated attempt, change its status to `reviewed_attempt` and record the responsible review in its notes; it still contributes no coverage. Preserve the earlier bundle as history. Generate another bundle with the same start date and an end date that includes the actual follow-up date to reconcile remaining work. Existing bundles are never overwritten.
5. Archive the bundle with its exact source snapshots. `reachplan verify result` recomputes every derived file, offline and after moving the directory.

## What the calculation means

For every pipe, `length = unique verified + remaining`, and `remaining = draft target length + review length`. Raw verified pass length remains separate, so repeated work is visible without overstating coverage. Attempted and out-of-period records appear in the exclusion list. Unverified in-period attempts force a review status even if other records cover the pipe.

Hose travel starts at the access node and includes all intervening already-cleaned distance. Current barriers stop each endpoint's travel at the nearest barrier edge. The planner uses one endpoint if it can cover all reachable targets; otherwise it partitions overlapping envelopes at the midpoint, on the input's 0.001-unit grid, with a deterministic from-end tie preference. This is a geometric allocation, not a cost, vehicle-routing or cleaning-effectiveness optimization. Every remaining interval is either assigned once or retained in `review.csv`.

## Outputs and exit codes

| File | Purpose |
| --- | --- |
| `report.md` | Human-readable job summary, draft setups and review notes |
| `summary.csv` | Per-pipe unique/repeated/remaining/draft/review lengths |
| `setups.csv` | One row per target interval; shared pipe/endpoint rows are one draft setup |
| `review.csv` | Unreachable intervals; unverified attempts are also listed in report/JSON |
| `plan.json` | Versioned exact interval data, travel envelopes, barriers, included/excluded records |
| `inputs/` | Exact original input snapshots |
| `manifest.json` | SHA-256 hashes of all other files |

Exit **0**: valid bundle without unresolved review, or successful integrity verification. Exit **3** from `plan`: valid bundle with unreachable work or an unverified in-period attempt. Exit **2**: invalid/unsupported input, integrity failure or filesystem error; no valid new result is claimed. Verification checks integrity and consistency, not authenticity, work completion or permission to perform it.

## Scope and limits

Supports independent linear reaches; one unit (`m` or `ft`) per campaign; nonnegative chainage with up to three decimal places; explicit campaign dates; current endpoint access/reach and positive-width impassable barrier intervals. Exact Decimal arithmetic preserves positive gaps. Inputs are UTF-8 CSV, up to 5 MB and 20,000 records per file. See [contracts and trust boundaries](docs/contracts.md).

ReachPlan does not read PACP databases, infer cleaned condition, model hydraulics, choose pressure/nozzles, plan traffic or confined-space access, authorize field work, certify compliance, or provide a CMMS/mobile collection system. It assumes the submitted lengths, accepted extents and current constraints are correct. Unknown barriers cannot be inferred from notes. Teams with a configured KANDIS, WinCan or GIS workflow may already have an adequate solution.

## Why this exists

Public utility documents distinguish true footage from repeated passes, require reverse attempts for incomplete cleaning and record access constraints. Existing products provide capable cleaning management and GIS interval tools. The bounded rationale is completing the combined verified-interval-to-residual-draft workflow for one CSV job. Demand for this particular automation remains inferred; no customer interviews, adoption or measured savings are claimed.

Read [dated research, alternatives and positioning](docs/research.md), [architecture](docs/architecture.md), [independent AI review](docs/review.md), and [release verification](docs/verification.md).

## Development and support

```sh
python -m pip install .
python -m unittest discover -s tests -v
python -m pip install build
python -m build
```

Report reproducible issues using synthetic inputs at [GitHub Issues](https://github.com/waxwingfactor/reachplan/issues). Do not upload private utility records. Support is community best effort; no operational service or response time is promised.
