"""Focused unit tests for the Split Miner internals.

Covers the two algorithmically tricky helpers:

* ``rpst_tree.compute_rpst`` — the RPST / triconnected-component
  decomposition: polygons, bonds, rigids, and the rejection of graphs
  that are not single-source / single-sink.
* ``gateway_map.replace_inclusive_joins`` — OR-join elimination: the
  rigid bond case, loop regions, and (on a real log) token-generator
  placement and the ``apply_hagen=False`` inclusive-retention path.

The first group is self-contained. The token-generator / inclusive
cases need a structure only large real logs produce, so they run against
the SM-Experiment logs when present and are skipped otherwise.
"""
import copy
import datetime
import os
import sys
import unittest
from collections import Counter

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd

import pm4py
from pm4py.algo.discovery.split_miner.dtypes import rpst_tree
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.dtypes.gateway_map import (
    replace_inclusive_joins,
)
from pm4py.algo.discovery.split_miner.variants.classic import ClassicSplitMiner
from pm4py.algo.discovery.split_miner.dfg_discovery.classic import (
    strip_self_loops,
)

_EXPERIMENT_LOGS = r"C:\Users\rennert\Downloads\SM-Experiment\Logs"


# ----------------------------------------------------------------------
# rpst_tree.compute_rpst
# ----------------------------------------------------------------------

def _fragment_types(root):
    out: list[str] = []
    stack = [root]
    while stack:
        f = stack.pop()
        out.append(f.ttype)
        stack.extend(f.children)
    return out


def test_rpst():
    # A plain sequence is a polygon whose children are all trivial edges.
    res = rpst_tree.compute_rpst([("a", "b"), ("b", "c")])
    assert res is not None
    root, src, snk = res
    assert (src, snk) == ("a", "c")
    assert root.ttype == "P"
    assert set(_fragment_types(root)) == {"P", "T"}

    # A nested bond yields a B fragment whose entry/exit are the split and
    # join nodes of the parallel block.
    res = rpst_tree.compute_rpst([
        ("s", "a"), ("a", "x"), ("a", "y"), ("x", "b"), ("y", "b"),
        ("b", "e"),
    ])
    assert res is not None
    root, _, _ = res
    bonds = []
    stack = [root]
    while stack:
        f = stack.pop()
        if f.ttype == "B":
            bonds.append(f)
        stack.extend(f.children)
    assert len(bonds) == 1, "expected exactly one bond fragment"
    assert (bonds[0].entry, bonds[0].exit) == ("a", "b")

    # A grid (two interleaved diamonds) is not series-parallel: the root
    # is a rigid (R) fragment — this is the triconnected-component path.
    res = rpst_tree.compute_rpst([
        ("s", "a"), ("s", "b"), ("a", "c"), ("a", "d"),
        ("b", "c"), ("b", "d"), ("c", "e"), ("d", "e"),
    ])
    assert res is not None
    root, _, _ = res
    assert root.ttype == "R", f"grid should be rigid, got {root.ttype}"

    # Graphs that are not single-source / single-sink are rejected.
    assert rpst_tree.compute_rpst([("a", "c"), ("b", "c")]) is None
    assert rpst_tree.compute_rpst([("a", "b"), ("a", "c")]) is None
    print("rpst_tree: polygon / bond / rigid / rejection — OK")


# ----------------------------------------------------------------------
# gateway_map.replace_inclusive_joins — self-contained
# ----------------------------------------------------------------------

def _connected(wg: WorkingGraph) -> bool:
    """Every node is reachable from the start and reaches the end."""
    def reach(starts, adj):
        seen = set(starts)
        stack = list(starts)
        while stack:
            n = stack.pop()
            for m in adj.get(n, []):
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        return seen
    nodes = set(wg.nodes)
    fwd = reach([wg.start_id], wg.out_edges)
    bwd = reach([wg.end_id], wg.in_edges)
    return nodes <= fwd and nodes <= bwd


def _or_join_bond(split_kind: str) -> WorkingGraph:
    """start -> <split> -> {a, b} -> OR-join -> end."""
    wg = WorkingGraph()
    for kind, nid in [("start", "start"), ("end", "end"),
                      (split_kind, "sp"), ("or", "oj"),
                      ("task", "a"), ("task", "b")]:
        wg.add_node(kind, label=nid, node_id=nid)
    wg.start_id, wg.end_id = "start", "end"
    for s, t in [("start", "sp"), ("sp", "a"), ("sp", "b"),
                 ("a", "oj"), ("b", "oj"), ("oj", "end")]:
        wg.add_edge(s, t)
    return wg


def test_gateway_map_micro():
    # A pure-XOR bond's OR-join collapses to an XOR-join.
    wg = _or_join_bond("xor")
    replace_inclusive_joins(wg, apply_hagen=True)
    assert wg.nodes["oj"].kind == "xor"
    assert _connected(wg)
    print("gateway_map: XOR bond OR-join -> XOR — OK")


def _build_wg(log, eps, eta):
    """Run the classic pipeline up to (not including) OR-min."""
    miner = ClassicSplitMiner()
    params = {"split_miner_epsilon": eps, "split_miner_eta": eta}
    traces = miner.do_extract_traces(log, params)
    dfg, loops = miner.do_dfg_discovery(traces, params)
    conc = miner.do_concurrency(strip_self_loops(dfg), traces, loops, params)
    filt = miner.do_filter(conc.pdfg, params)
    wg = miner.do_build_initial_bpmn(filt, conc, loops, params)
    miner.do_discover_splits(wg, params)
    miner.do_discover_joins(wg, params)
    return wg


_GRID = [(list("abdf"), 10), (list("acef"), 10),
         (list("abef"), 10), (list("acdf"), 10)]


def _mklog(variants, lifecycle=False):
    base = datetime.datetime(2026, 1, 1)
    rows = []
    ci = 0
    for trace, count in variants:
        for _ in range(count):
            cid = f"c{ci:04d}"
            ci += 1
            for j, a in enumerate(trace):
                row = {"case:concept:name": cid, "concept:name": a,
                       "time:timestamp": base + datetime.timedelta(minutes=10 * j)}
                if lifecycle:
                    row["lifecycle:transition"] = "complete"
                rows.append(row)
    return pd.DataFrame(rows)


def test_gateway_map_rigid():
    # A rigid (grid) model produces OR-joins; apply_hagen resolves all of
    # them to XOR/AND while keeping the graph connected. This exercises
    # the generateMap entry/exit sentinels for the boundary bonds.
    wg = _build_wg(_mklog(_GRID), 0.1, 0.4)
    pre = Counter(n.kind for n in wg.nodes.values())
    assert pre.get("or", 0) > 0, "grid log should yield OR-joins pre-min"
    for hagen in (True, False):
        w = copy.deepcopy(wg)
        replace_inclusive_joins(w, apply_hagen=hagen)
        assert Counter(n.kind for n in w.nodes.values()).get("or", 0) == 0
        assert _connected(w)
    print("gateway_map: rigid OR-joins resolved + connected — OK")


def test_gateway_map_loop():
    # A model with a level-1 loop must pass through the loop-join /
    # explore-loops machinery without crashing and stay connected.
    from tests.split_miner_2_loop_test import build_log as loop_log
    wg = _build_wg(loop_log(), 0.2, 1.0)
    for hagen in (True, False):
        w = copy.deepcopy(wg)
        replace_inclusive_joins(w, apply_hagen=hagen)
        assert _connected(w)
    print("gateway_map: loop region handled + connected — OK")


# ----------------------------------------------------------------------
# gateway_map — token generators + inclusive retention (real log)
# ----------------------------------------------------------------------

def test_gateway_map_token_generators():
    log_path = os.path.join(_EXPERIMENT_LOGS, "2012 BPI_Challenge.xes.gz")
    if not os.path.exists(log_path):
        print("gateway_map: token-gen test SKIPPED (experiment log absent)")
        return
    log = pm4py.read_xes(log_path, return_legacy_log_object=True)
    wg = _build_wg(log, 0.1, 0.4)
    pre = Counter(n.kind for n in wg.nodes.values())
    assert pre.get("or", 0) > 0
    n0 = len(wg.nodes)

    # apply_hagen=True: every OR-join is eliminated, and replacing some by
    # AND in non-trivial regions inserts token-generator gateways.
    w_true = copy.deepcopy(wg)
    replace_inclusive_joins(w_true, apply_hagen=True)
    assert Counter(n.kind for n in w_true.nodes.values()).get("or", 0) == 0
    assert len(w_true.nodes) > n0, "expected token-generator gateways"
    assert _connected(w_true)

    # apply_hagen=False (the SM 2.0 path): a non-trivial inclusive join is
    # left as an OR gateway instead of being expanded.
    w_false = copy.deepcopy(wg)
    replace_inclusive_joins(w_false, apply_hagen=False)
    assert Counter(n.kind for n in w_false.nodes.values()).get("or", 0) >= 1
    assert _connected(w_false)
    print("gateway_map: token generators placed + inclusive retained — OK")


class SplitMinerInternalsTest(unittest.TestCase):
    def test_rpst(self):
        test_rpst()

    def test_gateway_map_micro(self):
        test_gateway_map_micro()

    def test_gateway_map_rigid(self):
        test_gateway_map_rigid()

    def test_gateway_map_loop(self):
        test_gateway_map_loop()

    def test_gateway_map_token_generators(self):
        test_gateway_map_token_generators()


def main() -> int:
    test_rpst()
    test_gateway_map_micro()
    test_gateway_map_rigid()
    test_gateway_map_loop()
    test_gateway_map_token_generators()
    print("OK — Split Miner internals (rpst_tree, gateway_map).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
