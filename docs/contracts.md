# Input contracts and trust boundaries

Release 1.0 supports one campaign of independent linear pipes. Every file has its exact ordered header. Blank records, missing/extra columns, duplicate IDs, unknown pipe references, invalid values and unsupported precision are errors, including in records outside the campaign. Files use UTF-8 (optional BOM), standard quoted CSV and LF or CRLF. There is no unit conversion, implicit direction reversal or schema guessing.

## pipes.csv

```csv
pipe_id,from_node,to_node,length,unit,from_access,to_access,from_reach,to_reach
P1,A,B,100,m,yes,yes,60,60
```

- IDs: 1–64 ASCII letters, digits, dot, underscore or hyphen, beginning with a letter or digit. `pipe_id` is unique; endpoint names must differ. Reusing a node name does not create network connectivity.
- `length`: positive, at most 1,000,000. Units `m` or `ft`, identical throughout the file. Measurements use the same reference points as the cleaning records; centre-to-centre and face-to-face lengths cannot be mixed.
- Access: exactly `yes` or `no`, meaning current operator-declared availability for planning. No access is inferred from previous work.
- Reach: nonnegative usable travel from that access node. Values beyond pipe length are geometrically capped at the opposite endpoint; access `no` disables that end. Zero reach is allowed. This is an operator-supplied usable reach, not nominal hose capacity.

All numbers are plain unsigned decimal strings with at most three fractional places and value at most 1,000,000. No scientific notation, commas, whitespace, signs, NaN or infinity. Output target coordinates stay on this grid so accepted work can be entered later without rounding. No epsilon closes a small gap.

## passes.csv

```csv
pass_id,pipe_id,date,origin,start,end,status,notes
R1,P1,2026-01-02,to,0,20,verified,Operator accepted this extent
```

`pass_id` is unique, `date` is a valid `YYYY-MM-DD`, `origin` is exactly `from` or `to`. Start/end are increasing distances measured from that origin, with `0 <= start <= end <= length`. A to-origin interval [a,b] becomes [length-b,length-a] in canonical from-node coordinates. **Do not enter decreasing end/start values to express direction.**

`status` is `verified`, `attempted` or `reviewed_attempt`. Verified means a responsible operator accepted the whole submitted interval as adequately cleaned; its length must be positive. An attempt may have zero length. Attempts never contribute coverage. They do not automatically define an impassable obstruction: enter a known current obstruction in barriers.csv. In-period `attempted` records force `review_required` and remain visible even if other verified records cover the same area. Once a responsible person has reviewed the unsuccessful effort and current constraints, change that record to `reviewed_attempt` with a nonempty review note. This acknowledges the review, adds no coverage, and preserves the record in the exclusion list. Keep prior bundles as history; never change the original event date to hide an attempt.

Campaign start and end are explicit and inclusive. Exclusions use `before_campaign`, `after_campaign`, `unverified_attempt`, or `reviewed_attempt`, in that precedence. Historical verified work outside the campaign is not coverage for this job. Duplicate evidence with different IDs counts as repeated pass length; duplicate IDs are always rejected.

`notes` may be empty; otherwise at most 200 characters, with no control characters. Notes are retained in source snapshots, not interpreted as data or executable instructions. A prose warning does not modify reachability.

## barriers.csv

```csv
barrier_id,pipe_id,start,end,reason
B1,P1,40,45,Current obstruction requiring investigation
```

Optional on the command line; omission means **the operator asserts no known impassable barriers**. A header-only file is equivalent. `barrier_id` is unique; coordinates are always canonical distances from the pipe's from-node; `0 <= start < end <= length`. Reason is required, printable text of at most 200 characters.

Each interval is currently impassable. Travel from the from-node stops at the nearest barrier's start; travel from the to-node stops at the nearest barrier's end. Contact at the boundary may bound a geometric target; this does not authorize touching an obstruction in the field. A barrier beginning at zero or ending at length disables travel from that endpoint. All barrier interiors remain unreachable even if endpoints can reach their edges. An old accepted interval does not remove a current barrier. Resolve a barrier explicitly in the input before replanning beyond it.

## Result semantics

`schema_version` is 1. Distances in JSON are exact decimal **strings**, avoiding binary floating-point ambiguity. Coverage and target intervals have positive length, sorted and nonoverlapping; touching verified intervals merge. Results include canonical verified records, date/status exclusions, source SHA-256 hashes, current barriers and endpoint travel envelopes. Arrays are deterministic by pipe/record identifier and chainage. Reordering input records changes source hashes; equivalent numeric results remain unchanged.

A setup can contain separated target intervals. `target_length` is their sum; `travel_from_endpoint` is the distance to the farthest target, including intervening clean spans. CSV repeats that travel for each target row: do not sum it to obtain setup travel. No total travel or minimum-cost claim is made.

## Resource, filesystem and privacy boundaries

Each input: 5,000,000 bytes and 20,000 records maximum; fields at most 1,024 characters before semantic validation. Up to 20,000 pipes are accepted within those limits. All computations occur in memory; worst-case files can require substantial memory. Bundles produced by this scope have a 100 MB per-derived-file verification limit. Inputs and all bundle members must be regular files, not symlinks. Unsupported encodings, formats and limits fail clearly.

The program does no networking, subprocess execution, executable deserialization or file deletion outside its own newly created output. It reads explicitly supplied files and writes a new output directory under an existing parent. It refuses existing destinations, including empty directories. Bytes are staged before exclusive destination creation; the manifest is published last. An interrupted process can leave an incomplete directory; verification rejects it. There is no concurrent-editor or hostile-local-filesystem guarantee.

Bundles contain exact input snapshots, so treat them with the same confidentiality as the input. Source paths, host identifiers and wall-clock timestamps are not embedded. Markdown escapes input free text; CSV output prefixes spreadsheet formula leaders. JSON retains original barrier text. Hashes/recomputation expose modification or inconsistency, but an attacker can regenerate a coherent different bundle: this is not a digital signature or authenticity system.
