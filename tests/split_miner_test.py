"""Quick smoke test for the Split Miner integration.

Reproduces the running example of Augusto et al. (2019) — 10 distinct
traces, 10 occurrences each. The expected gateway counts are not taken
from the paper's idealised Fig. 3c but from the *reference Java Split
Miner 1.0* run on the same log at ``epsilon=0.2, eta=0.4`` (verified
byte-identical to this Python port): 8 tasks, 2 AND-splits, 4 XOR-splits
and no surviving OR-joins.
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
    f"Smoke test must run against the local pm4py copy in {_REPO_ROOT}, "
    f"but pm4py was imported from {pm4py.__file__}"
)

PAPER_EXAMPLE = (
        [list("abcgeh")] * 10
        + [list("abcfgh")] * 10
        + [list("abdgeh")] * 10
        + [list("abdegh")] * 10
        + [list("abecgh")] * 10
        + [list("abedgh")] * 10
        + [list("acbegh")] * 10
        + [list("acbfgh")] * 10
        + [list("adbegh")] * 10
        + [list("adbfgh")] * 10
)


def build_log() -> pd.DataFrame:
    base = datetime.datetime(2026, 1, 1)
    rows = []
    for i, trace in enumerate(PAPER_EXAMPLE):
        for j, label in enumerate(trace):
            rows.append(
                {
                    "case:concept:name": f"c{i:03d}",
                    "concept:name": label,
                    "time:timestamp": base + datetime.timedelta(minutes=10 * j),
                }
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


def main() -> int:
    df = build_log()
    print(f"log: {len(df)} events, {df['case:concept:name'].nunique()} cases")

    bpmn = pm4py.discover_bpmn_split_miner(
        df,
        epsilon=0.2,
        eta=0.4,
        variant="classic",
        minimize_or_joins=False,
    )

    counts = gateway_counts(bpmn)
    edges = len(bpmn.get_flows())
    print(f"classic SM 1.x : nodes={dict(counts)} edges={edges}")
    assert counts["task"] == 8, counts
    assert counts["and"] == 2, counts
    assert counts["xor"] == 4, counts
    assert counts["or"] == 0, counts

    bpmn2 = pm4py.discover_bpmn_split_miner(
        df,
        epsilon=0.2,
        eta=0.0,
        variant="sm2",
    )
    counts2 = gateway_counts(bpmn2)
    print(f"SM 2.0         : nodes={dict(counts2)} edges={len(bpmn2.get_flows())}")
    assert counts2["task"] == 8

    print("OK — Split Miner integration works through pm4py top-level API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
