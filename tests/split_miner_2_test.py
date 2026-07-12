"""Regression test for the SM 2.0 OR-split heuristic (faithful pipeline).

Reproduces the L_rho_y running example used in the SM 2.0 paper to
motivate the OR-split heuristic: three branches B, C, D after a single
entry activity A, with the following pairwise lifecycle observations:

  pair (B, C):  3 concurrent  /  3 mutually exclusive
  pair (B, D):  4 concurrent  /  2 mutually exclusive
  pair (C, D):  5 concurrent  /  1 mutually exclusive

Every pair is observed *both* concurrently and exclusively, so every
pair is a ``potential OR`` (the reference ``potentialORs`` matrix). The
AND-split discovered over {B, C, D} therefore has every ordered branch
pair eligible (count 6 > out-degree 3), so the faithful SM 2.0 pipeline
promotes it to an OR-split and ``matchORs`` turns the matching join into
an OR-join. Classic Split Miner, which is lifecycle-blind, must not
invent an OR-split on the same log.
"""
from collections import Counter
import datetime
import os
import sys

# Make sure we import the local pm4py source, not whatever is in
# site-packages.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd

import pm4py
from pm4py.objects.bpmn.obj import BPMN
from pm4py.algo.discovery.split_miner.variants.sm2 import SM2SplitMiner

assert pm4py.__file__.startswith(_REPO_ROOT), (
    f"SM 2.0 test must run against the local pm4py copy in {_REPO_ROOT}, "
    f"but pm4py was imported from {pm4py.__file__}"
)

# Each entry is ``(pattern_name, [(label, start_offset, end_offset)])`` in
# minutes relative to the case's starting timestamp. The staggered end
# offsets make the intervals overlap pairwise while letting every branch
# be the last-ending one in some case (so the DFG records B->E, C->E and
# D->E).
PATTERNS = (
    ("all_B_last", [("B", 2, 14), ("C", 2, 10), ("D", 2, 12)]),
    ("all_C_last", [("B", 2, 10), ("C", 2, 14), ("D", 2, 12)]),
    ("all_D_last", [("B", 2, 10), ("C", 2, 12), ("D", 2, 14)]),
    ("no_b_C_last", [("C", 2, 14), ("D", 2, 12)]),
    ("no_b_D_last", [("C", 2, 12), ("D", 2, 14)]),
    ("no_c_B_last", [("B", 2, 14), ("D", 2, 12)]),
)


def _emit_activity(rows, case_id, label, start, end):
    rows.append({
        "case:concept:name": case_id,
        "concept:name": label,
        "lifecycle:transition": "start",
        "time:timestamp": start,
    })
    rows.append({
        "case:concept:name": case_id,
        "concept:name": label,
        "lifecycle:transition": "complete",
        "time:timestamp": end,
    })


def build_log() -> pd.DataFrame:
    base = datetime.datetime(2026, 1, 1)
    minute = datetime.timedelta(minutes=1)
    rows: list[dict] = []
    for case_index, (pattern_name, branches) in enumerate(PATTERNS):
        case_id = f"c_{pattern_name}"
        t0 = base + datetime.timedelta(days=case_index)
        _emit_activity(rows, case_id, "A", t0, t0 + 1 * minute)
        block_end = 0
        for label, start_off, end_off in branches:
            _emit_activity(
                rows, case_id, label,
                t0 + start_off * minute, t0 + end_off * minute,
            )
            block_end = max(block_end, end_off)
        _emit_activity(
            rows, case_id, "E",
            t0 + (block_end + 1) * minute, t0 + (block_end + 2) * minute,
        )
    return pd.DataFrame(rows)


def gateway_counts(bpmn: BPMN) -> Counter:
    counts: Counter[str] = Counter()
    for node in bpmn.get_nodes():
        if isinstance(node, BPMN.Task):
            counts["task"] += 1
        elif isinstance(node, BPMN.StartEvent):
            counts["start"] += 1
        elif isinstance(node, BPMN.EndEvent):
            counts["end"] += 1
        elif isinstance(node, BPMN.ParallelGateway):
            counts["and"] += 1
        elif isinstance(node, BPMN.ExclusiveGateway):
            counts["xor"] += 1
        elif isinstance(node, BPMN.InclusiveGateway):
            counts["or"] += 1
    return counts


def _assert_potential_ors(df: pd.DataFrame) -> None:
    """The complex-log parser must classify the log as a complex log and
    flag all three branch pairs as potential ORs."""
    miner = SM2SplitMiner()
    miner.do_extract_traces(df)
    assert miner._is_complex, "log should be parsed as a complex log"
    pors = {tuple(sorted(p)) for p in miner._potential_ors}
    expected = {("B", "C"), ("B", "D"), ("C", "D")}
    assert pors == expected, f"potential ORs wrong: {sorted(pors)}"
    print(f"potential ORs match the paper: {sorted(pors)}")


def main() -> int:
    df = build_log()
    print(f"log: {len(df)} events, {df['case:concept:name'].nunique()} cases")

    _assert_potential_ors(df)

    # Classic Split Miner is lifecycle-blind and must never invent ORs.
    classic = pm4py.discover_bpmn_split_miner(
        df, epsilon=0.2, eta=0.0, variant="classic",
    )
    classic_counts = gateway_counts(classic)
    print(f"classic SM 1.x: nodes={dict(classic_counts)}")
    assert classic_counts["or"] == 0, (
        "Classic Split Miner must not produce OR-splits — "
        f"got {dict(classic_counts)}"
    )

    # Faithful SM 2.0: the OR-split heuristic + matchORs must fire.
    sm2 = pm4py.discover_bpmn_split_miner(df, epsilon=0.2, variant="sm2")
    sm2_counts = gateway_counts(sm2)
    print(f"SM 2.0        : nodes={dict(sm2_counts)}")
    assert sm2_counts["or"] == 2, (
        "SM 2.0 should produce an OR-split over {B, C, D} and the "
        f"matching OR-join — got {dict(sm2_counts)}"
    )
    assert sm2_counts["and"] == 0, (
        "After the OR-split heuristic the AND-split must be gone — "
        f"got {dict(sm2_counts)}"
    )

    print("OK — SM 2.0 OR-split heuristic matches the paper example.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
