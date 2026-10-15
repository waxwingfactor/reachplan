"""Pure computations; all distances use exact Decimal arithmetic."""
from __future__ import annotations
import csv
import hashlib
import io
import re
from datetime import date
from decimal import Decimal, ROUND_DOWN

HEADERS = {
    "pipes.csv": ["pipe_id", "from_node", "to_node", "length", "unit", "from_access", "to_access", "from_reach", "to_reach"],
    "passes.csv": ["pass_id", "pipe_id", "date", "origin", "start", "end", "status", "notes"],
    "barriers.csv": ["barrier_id", "pipe_id", "start", "end", "reason"],
}
MAX_BYTES = 5_000_000
MAX_ROWS = 20_000
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
NUMBER = re.compile(r"(?:0|[1-9][0-9]{0,6})(?:\.[0-9]{1,3})?\Z")
ZERO = Decimal(0)

class InputError(ValueError):
    """Unsupported, ambiguous, or invalid input; no partial result is valid."""

def number(value: str, context: str) -> Decimal:
    if not NUMBER.fullmatch(value):
        raise InputError(f"{context}: expected nonnegative plain decimal, at most 3 fractional digits")
    result = Decimal(value)
    if result > 1_000_000:
        raise InputError(f"{context}: distance exceeds 1000000")
    return result

def fmt(value: Decimal) -> str:
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")

def day(value: str, context: str) -> date:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise InputError(f"{context}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{context}: invalid date") from exc

def identifier(value: str, context: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise InputError(f"{context}: expected 1-64 ASCII letters/digits/._-, beginning with a letter/digit")
    return value

def plain(value: str, context: str) -> str:
    if len(value) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise InputError(f"{context}: text must be at most 200 characters with no control characters")
    return value

def rows(data: bytes, name: str) -> list[dict[str, str]]:
    if len(data) > MAX_BYTES:
        raise InputError(f"{name}: exceeds {MAX_BYTES} bytes")
    try:
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, None)
        if header != HEADERS[name]:
            raise InputError(f"{name}: exact header required: {','.join(HEADERS[name])}")
        out = []
        for line, values in enumerate(reader, 2):
            if len(values) != len(header):
                raise InputError(f"{name} row {line}: expected {len(header)} fields")
            if any(len(v) > 1024 for v in values):
                raise InputError(f"{name} row {line}: field exceeds 1024 characters")
            if len(out) >= MAX_ROWS:
                raise InputError(f"{name}: exceeds {MAX_ROWS} records")
            out.append(dict(zip(header, values)))
        return out
    except (UnicodeError, csv.Error) as exc:
        raise InputError(f"{name}: invalid UTF-8 or CSV: {exc}") from exc

def union(spans):
    result = []
    for lo, hi in sorted(spans):
        if hi <= lo:
            continue
        if result and lo <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], hi))
        else:
            result.append((lo, hi))
    return result

def subtract(spans, covered):
    result = []
    covered = union(covered)
    index = 0
    for lo, hi in union(spans):
        cursor = lo
        while index < len(covered) and covered[index][1] <= lo:
            index += 1
        scan = index
        while scan < len(covered) and covered[scan][0] < hi:
            a, b = covered[scan]
            if a > cursor:
                result.append((cursor, min(a, hi)))
            cursor = max(cursor, b)
            if cursor >= hi:
                break
            scan += 1
        index = scan
        if cursor < hi:
            result.append((cursor, hi))
    return result

def intersect(spans, lo, hi):
    return [(max(a, lo), min(b, hi)) for a, b in spans if max(a, lo) < min(b, hi)]

def total(spans):
    return sum((b-a for a, b in spans), ZERO)

def encoded(spans):
    return [{"start": fmt(a), "end": fmt(b), "length": fmt(b-a)} for a, b in spans]

def unique(records, key, name):
    seen = set()
    for record in records:
        identifier(record[key], f"{name} {key}")
        if record[key] in seen:
            raise InputError(f"{name}: duplicate {key} {record[key]}")
        seen.add(record[key])

def compute(inputs: dict[str, bytes], since: str, as_of: str) -> dict:
    """Compute a deterministic plan from the three canonical CSV byte streams.

    All input records, even excluded dates/statuses, are validated. The campaign
    is inclusive. Current barriers constrain travel independently of old coverage.
    """
    if set(inputs) != set(HEADERS):
        raise InputError("expected pipes.csv, passes.csv and barriers.csv")
    start_day, end_day = day(since, "since"), day(as_of, "as-of")
    if start_day > end_day:
        raise InputError("since must be on or before as-of")
    pipes = rows(inputs["pipes.csv"], "pipes.csv")
    passes = rows(inputs["passes.csv"], "passes.csv")
    barriers = rows(inputs["barriers.csv"], "barriers.csv")
    if not pipes:
        raise InputError("pipes.csv: at least one pipe required")
    unique(pipes, "pipe_id", "pipes.csv")
    unique(passes, "pass_id", "passes.csv")
    unique(barriers, "barrier_id", "barriers.csv")
    parsed = {}
    units = set()
    for p in pipes:
        pid = p["pipe_id"]
        for key in ("from_node", "to_node"):
            identifier(p[key], f"{pid} {key}")
        if p["from_node"] == p["to_node"]:
            raise InputError(f"{pid}: endpoints must differ")
        length = number(p["length"], f"{pid} length")
        if length <= 0:
            raise InputError(f"{pid}: length must be positive")
        if p["unit"] not in ("m", "ft"):
            raise InputError(f"{pid}: unit must be m or ft")
        units.add(p["unit"])
        for key in ("from_access", "to_access"):
            if p[key] not in ("yes", "no"):
                raise InputError(f"{pid} {key}: expected yes or no")
        parsed[pid] = dict(p, size=length,
            reach_a=number(p["from_reach"], f"{pid} from_reach"),
            reach_b=number(p["to_reach"], f"{pid} to_reach"),
            verified=[], attempts=[], blocks=[])
    if len(units) != 1:
        raise InputError("mixed units unsupported: use one unit for the entire campaign")
    excluded = []
    included = []
    for p in passes:
        pid = p["pipe_id"]
        if pid not in parsed:
            raise InputError(f"{p['pass_id']}: unknown pipe_id {pid}")
        pipe = parsed[pid]
        when = day(p["date"], f"{p['pass_id']} date")
        a, b = number(p["start"], f"{p['pass_id']} start"), number(p["end"], f"{p['pass_id']} end")
        if a > b or b > pipe["size"]:
            raise InputError(f"{p['pass_id']}: require 0 <= start <= end <= pipe length")
        if p["origin"] not in ("from", "to"):
            raise InputError(f"{p['pass_id']}: origin must be from or to")
        if p["status"] not in ("verified", "attempted", "reviewed_attempt"):
            raise InputError(f"{p['pass_id']}: status must be verified, attempted or reviewed_attempt")
        if p["status"] == "verified" and a == b:
            raise InputError(f"{p['pass_id']}: verified interval must have positive length")
        plain(p["notes"], f"{p['pass_id']} notes")
        if p["status"] == "reviewed_attempt" and not p["notes"].strip():
            raise InputError(f"{p['pass_id']}: reviewed_attempt requires a review note")
        if p["origin"] == "to":
            a, b = pipe["size"]-b, pipe["size"]-a
        reason = "before_campaign" if when < start_day else "after_campaign" if when > end_day else ("unverified_attempt" if p["status"] == "attempted" else "reviewed_attempt") if p["status"] != "verified" else None
        if reason:
            excluded.append({"pass_id": p["pass_id"], "pipe_id": pid, "reason": reason})
            if start_day <= when <= end_day and p["status"] == "attempted":
                pipe["attempts"].append(p["pass_id"])
        else:
            pipe["verified"].append((a, b))
            included.append({"pass_id": p["pass_id"], "pipe_id": pid, "date": p["date"], "start": fmt(a), "end": fmt(b)})
    for b in barriers:
        pid = b["pipe_id"]
        if pid not in parsed:
            raise InputError(f"{b['barrier_id']}: unknown pipe_id {pid}")
        a, z = number(b["start"], f"{b['barrier_id']} start"), number(b["end"], f"{b['barrier_id']} end")
        if not (a < z <= parsed[pid]["size"]):
            raise InputError(f"{b['barrier_id']}: require 0 <= start < end <= pipe length")
        if not plain(b["reason"], f"{b['barrier_id']} reason").strip():
            raise InputError(f"{b['barrier_id']}: reason required")
        parsed[pid]["blocks"].append((a, z, b["barrier_id"], b["reason"]))
    output = []
    for pid, p in sorted(parsed.items()):
        length = p["size"]
        coverage = union(p["verified"])
        gaps = subtract([(ZERO, length)], coverage)
        a_end = min(length, p["reach_a"]) if p["from_access"] == "yes" else ZERO
        b_start = max(ZERO, length-p["reach_b"]) if p["to_access"] == "yes" else length
        if p["blocks"]:
            a_end = min(a_end, min(b[0] for b in p["blocks"]))
            b_start = max(b_start, max(b[1] for b in p["blocks"]))
        a_targets, b_targets = intersect(gaps, ZERO, a_end), intersect(gaps, b_start, length)
        reachable = union(a_targets + b_targets)
        review = subtract(gaps, reachable)
        # Prefer one endpoint if it reaches every reachable target. Otherwise
        # partition at a clamped midpoint: deterministic and disjoint, no travel
        # budget resets at gaps. This is not a vehicle or cost optimizer.
        if total(a_targets) == total(reachable):
            b_targets = []
        elif total(b_targets) == total(reachable):
            a_targets = []
        elif b_start < a_end:
            midpoint = (length/2).quantize(Decimal("0.001"), rounding=ROUND_DOWN)
            split = max(b_start, min(a_end, midpoint))
            a_targets = intersect(gaps, ZERO, split)
            b_targets = intersect(gaps, split, length)
        setups = []
        for endpoint, targets, node in (("from", a_targets, p["from_node"]), ("to", b_targets, p["to_node"])):
            if targets:
                travel = max(b for a, b in targets) if endpoint == "from" else length-min(a for a, b in targets)
                setups.append({"endpoint": endpoint, "node": node, "travel_from_endpoint": fmt(travel), "target_length": fmt(total(targets)), "targets": encoded(targets), "status": "draft_requires_field_review"})
        repeat = total(p["verified"])-total(coverage)
        reasons = []
        if review:
            if p["from_access"] == "no" or p["to_access"] == "no": reasons.append("endpoint_access_unavailable")
            if p["blocks"]: reasons.append("current_barriers_limit_travel")
            reasons.append("outside_current_geometric_reach")
        output.append({"pipe_id": pid, "from_node": p["from_node"], "to_node": p["to_node"], "length": fmt(length),
            "verified_pass_length": fmt(total(p["verified"])), "unique_verified_length": fmt(total(coverage)), "repeat_length": fmt(repeat),
            "remaining_length": fmt(total(gaps)), "draft_target_length": fmt(total(reachable)), "review_length": fmt(total(review)),
            "coverage": encoded(coverage), "gaps": encoded(gaps), "setups": setups, "review_intervals": encoded(review), "review_reasons": reasons,
            "travel_envelopes": {"from": {"start": "0", "end": fmt(a_end)}, "to": {"start": fmt(b_start), "end": fmt(length)}},
            "barriers": [{"barrier_id": b[2], "start": fmt(b[0]), "end": fmt(b[1]), "reason": b[3]} for b in sorted(p["blocks"])],
            "unverified_attempt_ids": sorted(p["attempts"])})
    keys = ("length", "verified_pass_length", "unique_verified_length", "repeat_length", "remaining_length", "draft_target_length", "review_length")
    totals = {key: fmt(sum((Decimal(p[key]) for p in output), ZERO)) for key in keys}
    return {"schema_version": 1, "product": "reachplan", "product_version": "1.0.0", "campaign": {"since": since, "as_of": as_of, "unit": next(iter(units))},
        "status": "review_required" if any(p["review_intervals"] or p["unverified_attempt_ids"] for p in output) else "draft_ready" if any(p["setups"] for p in output) else "coverage_complete",
        "totals": totals, "pipes": output, "included_passes": sorted(included, key=lambda p: p["pass_id"]), "excluded_passes": sorted(excluded, key=lambda p: p["pass_id"]),
        "source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(inputs.items())}}
