"""Independent acceptance tests written without changing the planner.

The randomized oracle uses integer millimetre cells, rather than the interval
helpers under test, to check complete coverage and reachability accounting.
"""
from __future__ import annotations

import contextlib
import csv
from decimal import Decimal
import io
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from reachplan import core
from reachplan.bundle import csv_bytes, publish, read_file, render, verify
from reachplan.cli import main
from reachplan.core import HEADERS, InputError, compute, number, rows


SINCE = "2026-01-01"
AS_OF = "2026-03-31"
D = Decimal


def pipe(**changes):
    result = dict(pipe_id="P1", from_node="A", to_node="B", length="100",
                  unit="m", from_access="yes", to_access="no",
                  from_reach="100", to_reach="100")
    result.update(changes)
    return result


def cleaning(pass_id="C1", **changes):
    result = dict(pass_id=pass_id, pipe_id="P1", date="2026-02-01",
                  origin="from", start="0", end="10", status="verified", notes="")
    result.update(changes)
    return result


def barrier(barrier_id="B1", **changes):
    result = dict(barrier_id=barrier_id, pipe_id="P1", start="30", end="31",
                  reason="Observed obstruction")
    result.update(changes)
    return result


def make_csv(name, records):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(HEADERS[name])
    for record in records:
        writer.writerow([record[key] for key in HEADERS[name]])
    return stream.getvalue().encode()


def inputs(pipes=None, passes=(), barriers=()):
    return {name: make_csv(name, records) for name, records in (
        ("pipes.csv", [pipe()] if pipes is None else pipes),
        ("passes.csv", passes), ("barriers.csv", barriers))}


def plan(pipes=None, passes=(), barriers=()):
    return compute(inputs(pipes, passes, barriers), SINCE, AS_OF)


def intervals(records):
    return [(D(record["start"]), D(record["end"])) for record in records]


def all_targets(result):
    return [span for setup in result["setups"] for span in intervals(setup["targets"])]


def integer_distance(value):
    return format(D(value) / 1000, "f")


class IndependentPlanningFixtures(unittest.TestCase):
    def test_existing_coverage_does_not_reset_travel(self):
        result = plan([pipe(from_reach="50")], [
            cleaning("C1", start="0", end="40"),
            cleaning("C2", start="60", end="80")])["pipes"][0]
        self.assertEqual(all_targets(result), [(D(40), D(50))])
        self.assertEqual(intervals(result["review_intervals"]), [(D(50), D(60)), (D(80), D(100))])
        self.assertEqual(result["setups"][0]["travel_from_endpoint"], "50")
        self.assertEqual(result["setups"][0]["target_length"], "10")

    def test_barrier_in_prior_coverage_still_blocks(self):
        result = plan(passes=[cleaning(end="50")], barriers=[barrier()])["pipes"][0]
        self.assertEqual(result["setups"], [])
        self.assertEqual(intervals(result["review_intervals"]), [(D(50), D(100))])
        self.assertEqual(result["travel_envelopes"]["from"]["end"], "30")

    def test_both_ends_leave_middle_unreachable(self):
        result = plan([pipe(to_access="yes", from_reach="40", to_reach="40")])["pipes"][0]
        self.assertEqual(all_targets(result), [(D(0), D(40)), (D(60), D(100))])
        self.assertEqual(intervals(result["review_intervals"]), [(D(40), D(60))])

    def test_overlapping_envelopes_count_each_target_once(self):
        result = plan([pipe(to_access="yes", from_reach="60", to_reach="60")])["pipes"][0]
        targets = all_targets(result)
        self.assertEqual(len(result["setups"]), 2)
        self.assertEqual(sum(b - a for a, b in targets), D(100))
        self.assertEqual(result["draft_target_length"], "100")
        self.assertEqual(result["review_length"], "0")
        self.assertLessEqual(targets[0][1], targets[1][0])

    def test_covered_middle_requires_two_useful_end_setups(self):
        result = plan([pipe(to_access="yes", from_reach="40", to_reach="40")],
                      [cleaning(start="40", end="60")])["pipes"][0]
        self.assertEqual(all_targets(result), [(D(0), D(40)), (D(60), D(100))])
        self.assertEqual(result["review_length"], "0")

    def test_two_barrier_segments_enclose_unreachable_region(self):
        result = plan([pipe(to_access="yes")], barriers=[
            barrier("B1", start="30", end="31"),
            barrier("B2", start="69", end="70")])["pipes"][0]
        self.assertEqual(all_targets(result), [(D(0), D(30)), (D(70), D(100))])
        self.assertEqual(intervals(result["review_intervals"]), [(D(30), D(70))])

    def test_complete_coverage_needs_no_access_or_setup(self):
        result = plan([pipe(from_access="no")], [cleaning(end="100")])
        self.assertEqual(result["status"], "coverage_complete")
        self.assertEqual(result["pipes"][0]["setups"], [])
        self.assertEqual(result["pipes"][0]["review_intervals"], [])

    def test_smallest_supported_positive_gap_is_preserved(self):
        result = plan([pipe(length="1")], [
            cleaning("C1", end="0.3"), cleaning("C2", start="0.301", end="1")])["pipes"][0]
        self.assertEqual(intervals(result["gaps"]), [(D("0.3"), D("0.301"))])
        self.assertEqual(result["remaining_length"], "0.001")

    def test_to_origin_is_reflected_into_canonical_chainage(self):
        result = plan(passes=[cleaning(origin="to", start="10", end="40")])
        self.assertEqual(intervals(result["pipes"][0]["coverage"]), [(D(60), D(90))])
        self.assertEqual(result["included_passes"][0]["start"], "60")
        self.assertEqual(result["included_passes"][0]["end"], "90")

    def test_overlapping_and_touching_passes_have_exact_repeat_accounting(self):
        result = plan(passes=[cleaning("C1", end="30"),
                              cleaning("C2", start="20", end="40"),
                              cleaning("C3", start="40", end="50")])["pipes"][0]
        self.assertEqual(intervals(result["coverage"]), [(D(0), D(50))])
        self.assertEqual(result["verified_pass_length"], "60")
        self.assertEqual(result["unique_verified_length"], "50")
        self.assertEqual(result["repeat_length"], "10")

    def test_attempted_work_never_counts_as_coverage(self):
        result = plan(passes=[cleaning(status="attempted", end="100")])
        self.assertEqual(result["totals"]["unique_verified_length"], "0")
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["excluded_passes"], [dict(pass_id="C1", pipe_id="P1", reason="unverified_attempt")])
        self.assertEqual(result["pipes"][0]["unverified_attempt_ids"], ["C1"])

    def test_zero_length_attempt_is_explicitly_excluded(self):
        result = plan(passes=[cleaning(start="10", end="10", status="attempted")])
        self.assertEqual(result["totals"]["verified_pass_length"], "0")
        self.assertEqual(result["excluded_passes"][0]["reason"], "unverified_attempt")

    def test_campaign_inclusive_boundaries_and_exclusion_reasons(self):
        result = plan(passes=[cleaning("C1", date=SINCE, end="10"),
                              cleaning("C2", date=AS_OF, start="10", end="20"),
                              cleaning("C3", date="2025-12-31", end="100"),
                              cleaning("C4", date="2026-04-01", end="100")])
        self.assertEqual(result["totals"]["unique_verified_length"], "20")
        self.assertEqual([(p["pass_id"], p["reason"]) for p in result["excluded_passes"]],
                         [("C3", "before_campaign"), ("C4", "after_campaign")])

    def test_no_evidence_means_whole_pipe_uncovered(self):
        result = plan()["pipes"][0]
        self.assertEqual(result["remaining_length"], "100")
        self.assertEqual(result["coverage"], [])

    def test_endpoint_barrier_prevents_entry_and_zero_travel_prevents_targets(self):
        for change, blocks in (({}, [barrier(start="0", end="1")]),
                               ({"from_reach": "0"}, []),
                               ({"from_access": "no"}, [])):
            with self.subTest(change=change, blocks=blocks):
                result = plan([pipe(**change)], barriers=blocks)["pipes"][0]
                self.assertEqual(result["setups"], [])
                self.assertEqual(result["review_length"], "100")

    def test_separate_pipes_do_not_inherit_shared_node_access(self):
        result = plan([pipe(), pipe(pipe_id="P2", from_node="B", to_node="C", from_access="no")])
        self.assertEqual(result["pipes"][1]["draft_target_length"], "0")
        self.assertEqual(result["pipes"][1]["review_length"], "100")
        self.assertEqual(result["totals"]["length"], "200")


class IndependentValidation(unittest.TestCase):
    def assert_bad(self, pipes=None, passes=(), barriers=()):
        with self.assertRaises(InputError):
            plan(pipes, passes, barriers)

    def test_plain_finite_three_decimal_distance_contract(self):
        for text in ("NaN", "Infinity", "-1", "+1", "1e3", ".5", "1.", "01", "1.0000", "1000000.001", "1000001", "", " 1", "1 "):
            with self.subTest(text=text), self.assertRaises(InputError):
                number(text, "test")
        for text in ("0", "0.001", "1.000", "1000000"):
            with self.subTest(text=text):
                self.assertEqual(number(text, "test"), D(text))

    def test_pipe_contract_failures(self):
        for changes in ({"length": "0"}, {"from_node": "B"}, {"unit": "M"},
                        {"from_access": "true"}, {"to_access": "YES"},
                        {"from_node": "=SUM(A1)"}, {"pipe_id": "bad/name"},
                        {"to_reach": "1.0001"}, {"from_reach": "NaN"}):
            with self.subTest(changes=changes):
                self.assert_bad([pipe(**changes)])
        self.assert_bad([])
        self.assert_bad([pipe(), pipe()])
        self.assert_bad([pipe(), pipe(pipe_id="P2", unit="ft")])

    def test_pass_contract_failures_even_when_excluded_by_date(self):
        for changes in ({"pipe_id": "UNKNOWN"}, {"start": "11", "end": "10"},
                        {"end": "100.001"}, {"origin": "upstream"},
                        {"status": "complete"}, {"start": "0", "end": "0"},
                        {"date": "2026-02-30"}, {"date": "2026-2-01"},
                        {"notes": "bad\x1btext"}, {"notes": "x" * 201},
                        {"date": "2020-01-01", "end": "101"}):
            with self.subTest(changes=changes):
                self.assert_bad(passes=[cleaning(**changes)])
        self.assert_bad(passes=[cleaning(), cleaning()])

    def test_barrier_contract_failures(self):
        for changes in ({"pipe_id": "UNKNOWN"}, {"start": "31", "end": "30"},
                        {"start": "30", "end": "30"}, {"end": "101"},
                        {"reason": ""}, {"reason": "  "}, {"reason": "x\n"}):
            with self.subTest(changes=changes):
                self.assert_bad(barriers=[barrier(**changes)])
        self.assert_bad(barriers=[barrier(), barrier()])

    def test_campaign_and_filename_contract(self):
        for since, as_of in (("2026-04-01", AS_OF), ("2026-01-1", AS_OF),
                             (SINCE, "2026-02-29")):
            with self.subTest(since=since, as_of=as_of), self.assertRaises(InputError):
                compute(inputs(), since, as_of)
        for packet in ({}, {**inputs(), "extra.csv": b""}):
            with self.assertRaises(InputError):
                compute(packet, SINCE, AS_OF)

    def test_exact_schema_and_csv_failures(self):
        valid = inputs()["pipes.csv"]
        broken = [b"", valid.replace(b"pipe_id,from_node", b"from_node,pipe_id", 1),
                  valid.replace(b"pipe_id", b"PIPE_ID", 1), valid + b"\n",
                  valid.replace(b"P1,A,B", b"P1,A,B,extra", 1),
                  valid + b'"unfinished', valid + b"\xff"]
        for data in broken:
            with self.subTest(data=data[:80]), self.assertRaises(InputError):
                rows(data, "pipes.csv")
        self.assertEqual(rows(b"\xef\xbb\xbf" + valid, "pipes.csv"), rows(valid, "pipes.csv"))

    def test_resource_limits_are_enforced_at_boundary(self):
        header = (",".join(HEADERS["barriers.csv"]) + "\n").encode()
        row = b"B1,P1,1,2,reason\n"
        accepted = rows(header + row * core.MAX_ROWS, "barriers.csv")
        self.assertEqual(len(accepted), core.MAX_ROWS)
        with self.assertRaises(InputError):
            rows(header + row * (core.MAX_ROWS + 1), "barriers.csv")
        with self.assertRaises(InputError):
            rows(b"x" * (core.MAX_BYTES + 1), "barriers.csv")
        field_header = (",".join(HEADERS["passes.csv"]) + "\n").encode()
        base = b"C1,P1,2026-02-01,from,0,1,verified,"
        self.assertEqual(len(rows(field_header + base + b"x" * 1024 + b"\n", "passes.csv")), 1)
        with self.assertRaises(InputError):
            rows(field_header + base + b"x" * 1025 + b"\n", "passes.csv")


class IndependentRandomizedAccounting(unittest.TestCase):
    def test_integer_cell_oracle_and_reflection(self):
        rng = random.Random(20471015)
        for case in range(160):
            length = rng.randint(2, 200)
            reach_a, reach_b = rng.randint(0, length * 2), rng.randint(0, length * 2)
            access_a, access_b = rng.choice((True, False)), rng.choice((True, False))
            covered = [tuple(sorted(rng.sample(range(length + 1), 2))) for _ in range(rng.randint(0, 8))]
            blocks = [tuple(sorted(rng.sample(range(length + 1), 2))) for _ in range(rng.randint(0, 3))]
            p = pipe(length=integer_distance(length), from_reach=integer_distance(reach_a),
                     to_reach=integer_distance(reach_b), from_access="yes" if access_a else "no",
                     to_access="yes" if access_b else "no")
            passes = [cleaning(f"C{i}", start=integer_distance(a), end=integer_distance(b)) for i, (a, b) in enumerate(covered)]
            barriers = [barrier(f"B{i}", start=integer_distance(a), end=integer_distance(b)) for i, (a, b) in enumerate(blocks)]
            result = plan([p], passes, barriers)["pipes"][0]
            clean_cells = {x for a, b in covered for x in range(a, b)}
            left_end = min(length, reach_a) if access_a else 0
            right_start = max(0, length - reach_b) if access_b else length
            if blocks:
                left_end = min(left_end, min(a for a, b in blocks))
                right_start = max(right_start, max(b for a, b in blocks))
            dirty_cells = set(range(length)) - clean_cells
            reachable_cells = dirty_cells & (set(range(left_end)) | set(range(right_start, length)))
            with self.subTest(case=case):
                self.assertEqual(D(result["unique_verified_length"]) * 1000, len(clean_cells))
                self.assertEqual(D(result["remaining_length"]) * 1000, len(dirty_cells))
                self.assertEqual(D(result["draft_target_length"]) * 1000, len(reachable_cells))
                self.assertEqual(D(result["review_length"]) * 1000, len(dirty_cells - reachable_cells))
                self.assertEqual(D(result["length"]), D(result["unique_verified_length"]) + D(result["remaining_length"]))
                self.assertEqual(D(result["remaining_length"]), D(result["draft_target_length"]) + D(result["review_length"]))
                self.assertEqual(D(result["verified_pass_length"]), D(result["unique_verified_length"]) + D(result["repeat_length"]))
                targets = sorted(all_targets(result))
                self.assertEqual(sum((b-a for a, b in targets), D(0)), D(result["draft_target_length"]))
                for (a, b), (c, d) in zip(targets, targets[1:]):
                    self.assertLessEqual(b, c)
                # Probe each half-cell so even a midpoint setup split cannot
                # conceal a wrong location behind correct aggregate lengths.
                for x in range(length):
                    for quarter in (1, 3):
                        probe = D(4*x + quarter) / 4000
                        self.assertEqual(any(a <= probe < b for a, b in targets), x in reachable_cells)
                        self.assertEqual(any(a <= probe < b for a, b in intervals(result["review_intervals"])),
                                         x in dirty_cells - reachable_cells)
                for setup in result["setups"]:
                    self.assertEqual(setup["status"], "draft_requires_field_review")
                    budget = reach_a if setup["endpoint"] == "from" else reach_b
                    self.assertLessEqual(D(setup["travel_from_endpoint"]) * 1000, budget)
                    setup_spans = intervals(setup["targets"])
                    expected_travel = max(b for a, b in setup_spans) if setup["endpoint"] == "from" else D(result["length"])-min(a for a, b in setup_spans)
                    self.assertEqual(D(setup["travel_from_endpoint"]), expected_travel)
                    for a, b in intervals(setup["targets"]):
                        self.assertGreater(b, a)
                        self.assertGreaterEqual(a, 0)
                        self.assertLessEqual(b * 1000, length)
                        if setup["endpoint"] == "from":
                            self.assertLessEqual(b * 1000, left_end)
                        else:
                            self.assertGreaterEqual(a * 1000, right_start)
                        for x, z in covered:
                            self.assertTrue(b * 1000 <= x or a * 1000 >= z)
                        for x, z in blocks:
                            self.assertTrue(b * 1000 <= x or a * 1000 >= z)
                mirror = dict(p, from_reach=p["to_reach"], to_reach=p["from_reach"],
                              from_access=p["to_access"], to_access=p["from_access"])
                mp = [cleaning(f"C{i}", start=integer_distance(length-b), end=integer_distance(length-a)) for i, (a, b) in enumerate(covered)]
                mb = [barrier(f"B{i}", start=integer_distance(length-b), end=integer_distance(length-a)) for i, (a, b) in enumerate(blocks)]
                reflected = plan([mirror], mp, mb)["pipes"][0]
                for key in ("unique_verified_length", "remaining_length", "draft_target_length", "review_length", "repeat_length"):
                    self.assertEqual(result[key], reflected[key])
                for key in ("coverage", "gaps", "review_intervals"):
                    expected = sorted((D(result["length"])-b, D(result["length"])-a) for a, b in intervals(result[key]))
                    self.assertEqual(intervals(reflected[key]), expected)

    def test_row_permutation_and_equivalent_evidence(self):
        original = [cleaning("C1", start="10", end="30"), cleaning("C2", start="20", end="60")]
        shuffled = plan(passes=list(reversed(original)))
        expected = plan(passes=original)
        for key in ("pipes", "totals", "included_passes", "excluded_passes", "status"):
            self.assertEqual(expected[key], shuffled[key])
        split = plan(passes=[cleaning("C1", start="10", end="20"), cleaning("C2", start="20", end="60")])
        self.assertEqual(expected["pipes"][0]["coverage"], split["pipes"][0]["coverage"])
        self.assertEqual(expected["pipes"][0]["gaps"], split["pipes"][0]["gaps"])


class IndependentBundleAndCli(unittest.TestCase):
    def test_portable_bundle_recomputes_after_relocation(self):
        packet = inputs(passes=[cleaning(end="40")])
        expected = compute(packet, SINCE, AS_OF)
        with tempfile.TemporaryDirectory() as temp:
            first, moved = Path(temp)/"first", Path(temp)/"moved"
            publish(first, render(expected, packet))
            shutil.move(first, moved)
            self.assertEqual(verify(moved), expected)

    def test_each_published_file_is_checked_for_tampering(self):
        packet = inputs()
        files = render(compute(packet, SINCE, AS_OF), packet)
        with tempfile.TemporaryDirectory() as temp:
            location = Path(temp)/"bundle"
            publish(location, files)
            for name, original in files.items():
                with self.subTest(name=name):
                    (location/name).write_bytes(original + b" ")
                    with self.assertRaises(InputError):
                        verify(location)
                    (location/name).write_bytes(original)
            self.assertEqual(verify(location)["product"], "reachplan")

    def test_closed_inventory_symlinks_and_existing_destination(self):
        packet = inputs()
        files = render(compute(packet, SINCE, AS_OF), packet)
        with tempfile.TemporaryDirectory() as temp:
            location = Path(temp)/"bundle"
            publish(location, files)
            with self.assertRaises(InputError):
                publish(location, files)
            self.assertEqual((location/"plan.json").read_bytes(), files["plan.json"])
            (location/"unexpected.csv").write_text("unexpected")
            with self.assertRaises(InputError):
                verify(location)
            (location/"unexpected.csv").unlink()
            target = location/"summary.csv"
            target.unlink()
            target.symlink_to(location/"review.csv")
            with self.assertRaises(InputError):
                verify(location)
            with self.assertRaises(InputError):
                read_file(target)

    def test_csv_formula_leaders_are_neutralized(self):
        text = csv_bytes(["value"], [["=1+1"], ["  +SUM(A1)"], ["-2+2"], ["@cmd"], ["ordinary"]]).decode()
        parsed = list(csv.reader(io.StringIO(text)))
        self.assertEqual([r[0] for r in parsed[1:]], ["'=1+1", "'  +SUM(A1)", "'-2+2", "'@cmd", "ordinary"])

    def test_cli_review_exit_and_input_failure_do_not_create_false_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet = inputs([pipe(from_reach="20")])
            for name, data in packet.items():
                (root/name).write_bytes(data)
            args = ["plan", "--pipes", str(root/"pipes.csv"), "--passes", str(root/"passes.csv"),
                    "--since", SINCE, "--as-of", AS_OF, "--out", str(root/"result")]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 3)
                self.assertEqual(main(["verify", str(root/"result")]), 0)
                (root/"passes.csv").write_bytes(b"invalid\n")
                args[-1] = str(root/"invalid-result")
                self.assertEqual(main(args), 2)
            self.assertFalse((root/"invalid-result").exists())


if __name__ == "__main__":
    unittest.main()
