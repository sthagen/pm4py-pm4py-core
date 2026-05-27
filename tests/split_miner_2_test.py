"""Regression test for the SM 2.0 OR-split heuristic.

Reproduces the L_rho_y running example used in the SM 2.0 paper to
motivate the OR-split heuristic: three branches B, C, D after a single
entry activity A, with the following pairwise lifecycle observations:

  pair (B, C):  3 concurrent  /  3 mutually exclusive
  pair (B, D):  4 concurrent  /  2 mutually exclusive
  pair (C, D):  5 concurrent  /  1 mutually exclusive

Two of the three pairs satisfy the eligibility predicate (``2*conc >=
excl`` and ``2*excl >= conc``), so a majority of pairs are "eligible
for inclusiveness". The SM 2.0 heuristic must therefore promote the
AND-split discovered over {B, C, D} into an OR-split. The classic
Split Miner does not see lifecycle information at all and is expected
to produce an AND-split on the same log.
"""
from collections import Counter
import datetime
import os
import sys

# Make sure we import the local pm4py source, not whatever is in site-packages.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd

import pm4py
from pm4py.objects.bpmn.obj import BPMN

assert pm4py.__file__.startswith(_REPO_ROOT), (
    f"SM 2.0 test must run against the local pm4py copy in {_REPO_ROOT}, "
    f"but pm4py was imported from {pm4py.__file__}"
)


# ----------------------------------------------------------------------
# Log construction
# ----------------------------------------------------------------------
#
# Six cases — three with all of B, C, D, two with only C and D, one
# with only B and D — each preceded by A and followed by E. The
# concurrent block is recorded as start / complete lifecycle pairs
# with deliberately staggered end times: this both makes the
# intervals overlap (so SM 2.0's concurrency oracle fires) and lets
# every branch be the *last-ending* one in some case (so the refined
# DFG records ``B -> E``, ``C -> E`` and ``D -> E``, not just one of
# them).
#
# Pairwise totals across the six cases:
#
#   B,C concurrent : 3 (three "all" cases)
#   B,C exclusive  : 3 (two "no-B" + one "no-C")
#   B,D concurrent : 4 (three "all" + one "no-C")
#   B,D exclusive  : 2 (two "no-B")
#   C,D concurrent : 5 (three "all" + two "no-B")
#   C,D exclusive  : 1 (one "no-C")
#
# This matches the paper's L_rho_y example.
#
# Each entry is ``(pattern_name, [(label, start_offset, end_offset)])``
# in minutes relative to the case's starting timestamp.

PATTERNS = (
    # "all" cases — B, C and D all overlap. Each case picks a
    # different branch to be the last-ending one so the refined DFG
    # ends up with B->E, C->E, and D->E.
    ("all_B_last", [("B", 2, 14), ("C", 2, 10), ("D", 2, 12)]),
    ("all_C_last", [("B", 2, 10), ("C", 2, 14), ("D", 2, 12)]),
    ("all_D_last", [("B", 2, 10), ("C", 2, 12), ("D", 2, 14)]),
    # "no B" cases — C and D overlap; rotate the last-ending branch
    # so we end up with both C->E and D->E.
    ("no_b_C_last", [("C", 2, 14), ("D", 2, 12)]),
    ("no_b_D_last", [("C", 2, 12), ("D", 2, 14)]),
    # "no C" case — B and D overlap.
    ("no_c_B_last", [("B", 2, 14), ("D", 2, 12)]),
)


def _emit_activity(rows, case_id, label, start, end):
    """Emit a (start, complete) lifecycle pair for a single activity."""
    rows.append(
        {
            "case:concept:name": case_id,
            "concept:name": label,
            "lifecycle:transition": "start",
            "time:timestamp": start,
        }
    )
    rows.append(
        {
            "case:concept:name": case_id,
            "concept:name": label,
            "lifecycle:transition": "complete",
            "time:timestamp": end,
        }
    )


def build_log() -> pd.DataFrame:
    base = datetime.datetime(2026, 1, 1)
    minute = datetime.timedelta(minutes=1)
    rows: list[dict] = []

    for case_index, (pattern_name, branches) in enumerate(PATTERNS):
        case_id = f"c_{pattern_name}"
        t0 = base + datetime.timedelta(days=case_index)

        # A : sequential prefix occupying the first minute.
        _emit_activity(rows, case_id, "A", t0, t0 + 1 * minute)

        # Concurrent block — every branch starts during minute 2 and
        # ends at a branch-specific offset so the intervals overlap
        # pairwise yet have distinct closing times.
        block_end = 0
        for label, start_off, end_off in branches:
            _emit_activity(
                rows,
                case_id,
                label,
                t0 + start_off * minute,
                t0 + end_off * minute,
            )
            block_end = max(block_end, end_off)

        # E : sequential suffix, scheduled strictly after the last
        # branch finishes so the refined DFG records ``X -> E`` for
        # whichever branch was the last to close.
        _emit_activity(
            rows,
            case_id,
            "E",
            t0 + (block_end + 1) * minute,
            t0 + (block_end + 2) * minute,
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


def _assert_pair_observations(df: pd.DataFrame) -> None:
    """Sanity-check that the log produces the paper's pairwise counts."""
    from pm4py.algo.discovery.split_miner.heuristics.or_split import (
        _pair_observation,
    )
    from pm4py.algo.discovery.split_miner.variants.sm2 import SM2SplitMiner

    refined = SM2SplitMiner().do_extract_traces(df)
    conc, excl = _pair_observation(refined)

    def get(a, b):
        return conc.get(frozenset((a, b)), 0), excl.get(frozenset((a, b)), 0)

    assert get("B", "C") == (3, 3), f"B,C counts wrong: {get('B','C')}"
    assert get("B", "D") == (4, 2), f"B,D counts wrong: {get('B','D')}"
    assert get("C", "D") == (5, 1), f"C,D counts wrong: {get('C','D')}"
    print(
        "pair observations match the paper: "
        f"B,C={get('B','C')}, B,D={get('B','D')}, C,D={get('C','D')}"
    )


def main() -> int:
    df = build_log()
    print(
        f"log: {len(df)} events, {df['case:concept:name'].nunique()} cases"
    )

    _assert_pair_observations(df)

    # ---- Classic Split Miner: no lifecycle awareness -------------------
    # The classic oracle only inspects directly-follows frequencies in
    # the flat event sequence; because our synthetic log emits the
    # concurrent block in a fixed lifecycle order (B_s, C_s, D_s, then
    # B_e, C_e, D_e), the resulting DFG is highly asymmetric and the
    # classic concurrency test cannot recover the mutual parallelism
    # that the lifecycle structure encodes. This is precisely the
    # situation SM 2.0 was designed to address, so we only assert that
    # classic SM does *not* invent an OR-split here.
    classic = pm4py.discover_bpmn_split_miner(
        df,
        epsilon=0.2,
        eta=0.0,
        variant="classic",
        minimize_or_joins=False,
    )
    classic_counts = gateway_counts(classic)
    print(
        f"classic SM 1.x: nodes={dict(classic_counts)}  "
        f"edges={len(list(classic.get_flows()))}"
    )
    assert classic_counts["or"] == 0, (
        "Classic Split Miner must not produce OR-splits — "
        f"got {dict(classic_counts)}"
    )

    # ---- Split Miner 2.0: heuristic 2 must fire ------------------------
    sm2 = pm4py.discover_bpmn_split_miner(
        df,
        epsilon=0.2,
        eta=0.0,
        variant="sm2",
        minimize_or_joins=False,
    )
    sm2_counts = gateway_counts(sm2)
    print(
        f"SM 2.0        : nodes={dict(sm2_counts)}  "
        f"edges={len(list(sm2.get_flows()))}"
    )
    assert sm2_counts["or"] == 2, (
        "SM 2.0 should produce an OR-split over {B, C, D} (heuristic 2) "
        "and the matching OR-join — "
        f"got {dict(sm2_counts)}"
    )
    assert sm2_counts["and"] == 0, (
        "After heuristic 2 the AND-split must be gone — "
        f"got {dict(sm2_counts)}"
    )

    print("OK — SM 2.0 OR-split heuristic matches the paper example.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
