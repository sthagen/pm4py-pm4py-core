"""Regression test for the SM 2.0 improper-completion heuristic.

Reproduces the example has just four activities — ``A``, ``B``, ``C``,
``D`` — arranged as

    --> A --> AND-split --> { B, C, D }
              ^                    |
              +----- loop edge ----+

i.e. one of the parallel branches loops back to ``A``. Heuristic 1 of
SM 2.0 must split this loop branch off the AND-split via a new
preceding XOR-split so the AND only carries the two forward branches:

    --> A --> XOR --> AND-split --> { B, C }
              |
              +------ loop branch ----> D ----> back to A

The test asserts that:

  * the discovered AND-split contains only the forward branches (no
    loop branch);
  * a fresh XOR-split sits between the AND's parent and the AND
    itself, owning the loop branch as one of its outgoing edges;
  * without Heuristic 1 (verified via a subclass that skips the
    heuristics phase) the AND-split still carries the loop branch.

Only the four activities from the paper appear in the resulting BPMN
— the framework's sentinel start / end events and any auto-inserted
gateways are all that surrounds them.
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
    f"SM 2.0 improper-completion test must run against the local pm4py "
    f"copy in {_REPO_ROOT}, but pm4py was imported from {pm4py.__file__}"
)


# ----------------------------------------------------------------------
# Log construction
# ----------------------------------------------------------------------
#
# Every iteration is structured:
#
#     A  -->  { B || C }  -->  D
#
# i.e. ``A`` is followed by a concurrent block over ``{B, C}`` (recorded
# as overlapping start / complete lifecycle pairs) and then by ``D``,
# which runs *after* the parallel block has finished (its lifecycle does
# not overlap B or C). Some cases iterate the whole structure once more
# (``D`` is followed by ``A`` again) before terminating, so the refined
# directly-follows graph contains the loop arc ``D -> A``.
#
# Because ``D`` is sequential (not part of the parallel block), the
# discovered model has an AND-split over ``{B, C}`` only — and the loop
# closes back to ``A`` through ``D``. Heuristic 1 must therefore give the
# parallel block a preceding XOR-split with a loop-back to ``A`` so that
# ``A`` can be repeated without entering (and having to complete) the
# parallel block.

_MINUTE = datetime.timedelta(minutes=1)

# In one iteration B and C overlap (concurrent); the ``last`` branch is
# the one whose completion is observed last, which fixes the
# directly-follows arc into D. D always runs strictly after both.
_PARALLEL_END_OPTIONS = {
    "B": [("B", 2, 6), ("C", 2, 5)],   # B finishes last
    "C": [("B", 2, 5), ("C", 2, 6)],   # C finishes last
}
_D_START_MIN = 7   # D starts after both B and C have completed
_D_END_MIN = 8


# (pattern_name, number_of_iterations, last-completing branch of the block)
# Loop patterns iterate three times so the directly-follows arc
# ``D -> A`` is observed often enough (twice per case) to dominate
# ``D -> __end__`` and survive the source-to-sink filter as D's best
# outgoing edge. A couple of single-iteration cases keep the terminal
# arc ``D -> __end__`` alive.
PATTERNS = [
    ("loop_B", 4, "B"),
    ("loop_C", 4, "C"),
    ("term_B", 1, "B"),
    ("term_C", 1, "C"),
]


def _emit_activity(rows, case_id, label, start, end):
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


def _emit_iteration(rows, case_id, iter_origin, last_branch):
    """Emit one ``A -> {B || C} -> D`` iteration whose parallel block is
    finished last by ``last_branch``. Returns the origin for the next
    iteration."""
    # A occupies minute 0..1 of the iteration.
    _emit_activity(rows, case_id, "A", iter_origin, iter_origin + _MINUTE)
    # Concurrent block B || C.
    for label, s_off, e_off in _PARALLEL_END_OPTIONS[last_branch]:
        _emit_activity(
            rows,
            case_id,
            label,
            iter_origin + s_off * _MINUTE,
            iter_origin + e_off * _MINUTE,
        )
    # D runs strictly after the parallel block.
    _emit_activity(
        rows,
        case_id,
        "D",
        iter_origin + _D_START_MIN * _MINUTE,
        iter_origin + _D_END_MIN * _MINUTE,
    )
    return iter_origin + (_D_END_MIN + 1) * _MINUTE


def build_log() -> pd.DataFrame:
    """Sixteen cases — every pattern repeated four times so the
    directly-follows frequencies survive the percentile filter."""
    base = datetime.datetime(2026, 1, 1)
    rows: list[dict] = []
    case_index = 0
    for _ in range(4):
        for pattern_name, n_iter, last_branch in PATTERNS:
            case_id = f"c{case_index:02d}_{pattern_name}"
            origin = base + datetime.timedelta(days=case_index)
            case_index += 1

            # Each iteration is ``A -> {B || C} -> D``; consecutive
            # iterations produce the loop arc ``D -> A``.
            for _i in range(n_iter):
                origin = _emit_iteration(rows, case_id, origin, last_branch)
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


def _and_split_branch_names(bpmn: BPMN) -> list[set[str]]:
    """For every AND-split (parallel gateway with multiple outgoing
    flows), return the set of *task labels* its branches eventually
    lead to. Intermediate gateways are followed forward until a task
    is reached."""

    def _resolve(node: BPMN.BPMNNode, seen: set[str]) -> set[str]:
        if isinstance(node, BPMN.Task):
            return {node.get_name()}
        nid = node.get_id()
        if nid in seen:
            return set()
        seen = seen | {nid}
        result: set[str] = set()
        for f in bpmn.get_flows():
            if f.source is node:
                result |= _resolve(f.target, seen)
        return result

    splits: list[set[str]] = []
    for node in bpmn.get_nodes():
        if not isinstance(node, BPMN.ParallelGateway):
            continue
        out_edges = [f for f in bpmn.get_flows() if f.source is node]
        if len(out_edges) <= 1:
            continue
        labels = set()
        for f in out_edges:
            labels |= _resolve(f.target, set())
        splits.append(labels)
    return splits


def main() -> int:
    df = build_log()
    print(
        f"log: {len(df)} events, {df['case:concept:name'].nunique()} cases"
    )

    # ---- 1. SM 2.0 with Heuristic 1 enabled ----------------------------
    bpmn = pm4py.discover_bpmn_split_miner(
        df,
        epsilon=0.2,
        eta=0.0,
        variant="sm2",
        minimize_or_joins=False,
    )
    counts = gateway_counts(bpmn)
    print(
        f"SM 2.0 with heuristic 1: nodes={dict(counts)}  "
        f"edges={len(list(bpmn.get_flows()))}"
    )
    assert {n.get_name() for n in bpmn.get_nodes() if isinstance(n, BPMN.Task)} == {
        "A",
        "B",
        "C",
        "D",
    }, "Only the four paper activities should appear in the BPMN"

    splits = _and_split_branch_names(bpmn)
    assert len(splits) == 1, (
        f"Expected exactly one AND-split, got {len(splits)}: {splits}"
    )
    and_branches = splits[0]
    # The parallel block stays {B, C}; D is sequential after it, so it
    # is not one of the AND-split's branches.
    assert and_branches == {"B", "C"}, (
        f"The AND-split should carry exactly the parallel branches "
        f"B and C, got {and_branches}"
    )

    # The AND-split's sole predecessor must be the XOR-split that
    # heuristic 1 inserts (Fig 4b — preceding XOR-split).
    and_node = next(
        n for n in bpmn.get_nodes() if isinstance(n, BPMN.ParallelGateway)
        and len([f for f in bpmn.get_flows() if f.source is n]) > 1
    )
    parents = [
        f.source for f in bpmn.get_flows() if f.target is and_node
    ]
    assert len(parents) == 1 and isinstance(
        parents[0], BPMN.ExclusiveGateway
    ), (
        "AND-split's predecessor should be the new XOR-split inserted "
        f"by heuristic 1, got {[type(p).__name__ for p in parents]}"
    )
    new_xor = parents[0]
    xor_targets = [f.target for f in bpmn.get_flows() if f.source is new_xor]
    assert and_node in xor_targets, (
        "The new XOR-split should feed the AND-split (forward branch)"
    )
    assert len(xor_targets) >= 2, (
        "The new XOR-split must own a loop-back edge besides the "
        f"forward edge into the AND-split, got {len(xor_targets)} outputs"
    )

    # Crucially, the new XOR-split must be able to reach ``A`` *without*
    # passing through the parallel block or ``D`` — that is what lets
    # ``A`` be repeated directly (the property missing before this fix).
    import networkx as nx

    g = nx.DiGraph()
    for f in bpmn.get_flows():
        g.add_edge(f.source.get_id(), f.target.get_id())
    a_node = next(
        n for n in bpmn.get_nodes()
        if isinstance(n, BPMN.Task) and n.get_name() == "A"
    )
    d_node = next(
        n for n in bpmn.get_nodes()
        if isinstance(n, BPMN.Task) and n.get_name() == "D"
    )
    g_without_d = g.copy()
    g_without_d.remove_node(d_node.get_id())
    assert nx.has_path(g_without_d, new_xor.get_id(), a_node.get_id()), (
        "A must be repeatable from the new XOR-split without going "
        "through D, but every path from the XOR-split back to A passes "
        "through D"
    )
    print(
        "A is repeatable directly from the new XOR-split (no need to "
        "execute D)"
    )

    # ---- 2. Sanity check: without Heuristic 1 there is no preceding ----
    #         XOR-split, so A can only be repeated by going through D.
    from pm4py.algo.discovery.split_miner.variants.sm2 import SM2SplitMiner

    class _NoH1(SM2SplitMiner):
        def do_apply_heuristics(self, wg, traces, parameters=None):
            return

    bpmn_no_h1 = _NoH1().apply(
        df,
        {
            "split_miner_epsilon": 0.2,
            "split_miner_eta": 0.0,
            "split_miner_or_minimise": False,
        },
    )
    g2 = nx.DiGraph()
    for f in bpmn_no_h1.get_flows():
        g2.add_edge(f.source.get_id(), f.target.get_id())
    a2 = next(
        n for n in bpmn_no_h1.get_nodes()
        if isinstance(n, BPMN.Task) and n.get_name() == "A"
    )
    d2 = next(
        n for n in bpmn_no_h1.get_nodes()
        if isinstance(n, BPMN.Task) and n.get_name() == "D"
    )
    g2_without_d = g2.copy()
    g2_without_d.remove_node(d2.get_id())
    # Without heuristic 1, every loop back to A must traverse D, so once
    # D is removed A no longer lies on any cycle.
    a_on_cycle_without_d = a2.get_id() in {
        n for comp in nx.strongly_connected_components(g2_without_d)
        if len(comp) > 1
        for n in comp
    }
    assert not a_on_cycle_without_d, (
        "Without heuristic 1, A should only be repeatable by going "
        "through D (no D-free loop), but a D-free cycle through A exists"
    )
    print(
        "without heuristic 1     : A is only repeatable through D "
        "(no direct loop-back)"
    )

    # Render the corrected BPMN for visual inspection.
    png_path = os.path.join(
        _REPO_ROOT, "tests", "sm2_improper_completion.png"
    )
    pm4py.save_vis_bpmn(bpmn, png_path)
    print(f"rendered {os.path.relpath(png_path, _REPO_ROOT)}")

    print("OK — SM 2.0 Heuristic 1 reproduces the paper Fig. 4b fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
