"""Regression test: Split Miner 2.0 ignores ``eta`` and ``minimize_or_joins``.

The reference Split Miner 2.0 (``MineWithSMTC``) pins the frequency
threshold to ``eta = 1.0`` and always runs its OR handling
(``replaceIORs = false`` plus the OR-split heuristic). There is no way to
change either in the Java tool. The pm4py wrapper keeps ``eta`` and
``minimize_or_joins`` in the signature for API symmetry with the classic
variant, but the SM2 variant must *ignore* them.

This test exists so a future reader does not "fix" that as if it were an
accidental parameter bug. It checks both the behaviour (SM2 output is
invariant to the two flags) and the mechanism (SM2 pins ``eta`` and
declares its OR handling mandatory), and contrasts it with the classic
variant, which honours ``minimize_or_joins``.
"""
import datetime
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd

import pm4py
import networkx as nx
from pm4py.algo.discovery.split_miner.variants.classic import (
    ClassicSplitMiner,
)
from pm4py.objects.bpmn.obj import BPMN
from pm4py.algo.discovery.split_miner.variants.sm2 import SM2SplitMiner
from pm4py.algo.discovery.split_miner.filtering.max_min import (
    Parameters as FilterParameters,
)

assert pm4py.__file__.startswith(_REPO_ROOT)


def _mklog(variants, lifecycle=False):
    base = datetime.datetime(2026, 1, 1)
    rows: list[dict] = []
    ci = 0
    for trace, count in variants:
        for _ in range(count):
            cid = f"c{ci:04d}"
            ci += 1
            for j, a in enumerate(trace):
                ts = base + datetime.timedelta(minutes=10 * j)
                if lifecycle:
                    rows.append({"case:concept:name": cid, "concept:name": a,
                                 "lifecycle:transition": "complete",
                                 "time:timestamp": ts})
                else:
                    rows.append({"case:concept:name": cid, "concept:name": a,
                                 "time:timestamp": ts})
    return pd.DataFrame(rows)


def _node_label(node):
    if isinstance(node, BPMN.Task):
        return "task:" + node.get_name()
    if isinstance(node, BPMN.StartEvent):
        return "start"
    if isinstance(node, BPMN.EndEvent):
        return "end"
    if isinstance(node, BPMN.ParallelGateway):
        return "and"
    if isinstance(node, BPMN.ExclusiveGateway):
        return "xor"
    if isinstance(node, BPMN.InclusiveGateway):
        return "or"
    return type(node).__name__


def _h(bpmn):
    """Structural Weisfeiler-Lehman fingerprint of a BPMN, independent of
    node identity: two models with the same hash are isomorphic with
    matching node labels. Inlined so the test has no external helper."""
    g = nx.DiGraph()
    for node in bpmn.get_nodes():
        g.add_node(id(node), lab=_node_label(node))
    for flow in bpmn.get_flows():
        g.add_edge(id(flow.get_source()), id(flow.get_target()))
    return nx.weisfeiler_lehman_graph_hash(g, node_attr="lab")


# A "grid" / rigid structure: classic leaves OR-joins unless they are
# minimised, so it is sensitive to ``minimize_or_joins``.
GRID = [
    (list("abdf"), 10), (list("acef"), 10),
    (list("abef"), 10), (list("acdf"), 10),
]


def main() -> int:
    df = _mklog(GRID, lifecycle=True)

    # --- SM2 is invariant to eta -----------------------------------------
    sm2_etas = {
        _h(pm4py.discover_bpmn_split_miner(
            df, epsilon=0.1, eta=e, variant="sm2"))
        for e in (0.0, 0.4, 1.0)
    }
    assert len(sm2_etas) == 1, f"SM2 output changed with eta: {sm2_etas}"

    # --- SM2 is invariant to minimize_or_joins ---------------------------
    sm2_minor = {
        _h(pm4py.discover_bpmn_split_miner(
            df, epsilon=0.1, variant="sm2", minimize_or_joins=m))
        for m in (True, False)
    }
    assert len(sm2_minor) == 1, (
        f"SM2 output changed with minimize_or_joins: {sm2_minor}"
    )
    print("SM2 output is invariant to eta and minimize_or_joins.")

    # --- contrast: classic DOES honour minimize_or_joins -----------------
    df_classic = _mklog(GRID)
    cls_min_true = _h(pm4py.discover_bpmn_split_miner(
        df_classic, epsilon=0.1, eta=0.4, variant="classic",
        minimize_or_joins=True))
    cls_min_false = _h(pm4py.discover_bpmn_split_miner(
        df_classic, epsilon=0.1, eta=0.4, variant="classic",
        minimize_or_joins=False))
    assert cls_min_true != cls_min_false, (
        "classic should change with minimize_or_joins on a rigid log; "
        "if this fails the contrast is no longer meaningful"
    )
    print("Classic output DOES change with minimize_or_joins (flag is live).")

    # --- mechanism: the design is explicit, not an accidental no-op ------
    # SM2 declares its OR handling mandatory; classic leaves it optional.
    assert SM2SplitMiner().or_handling_is_mandatory() is True
    assert ClassicSplitMiner().or_handling_is_mandatory() is False

    # SM2.do_filter overrides whatever eta reaches it with 1.0: spy on the
    # eta that actually reaches the filter.
    from pm4py.algo.discovery.split_miner.filtering.max_min import (
        MaxMinFilterer,
    )
    seen = {}
    orig = MaxMinFilterer.apply.__func__

    def _spy(cls, pdfg, parameters=None):
        seen["eta_used"] = (parameters or {}).get(FilterParameters.ETA.value)
        return orig(cls, pdfg, parameters)

    MaxMinFilterer.apply = classmethod(_spy)
    try:
        SM2SplitMiner().apply(
            pm4py.convert_to_event_log(_mklog(GRID, lifecycle=True)),
            {"split_miner_epsilon": 0.1, FilterParameters.ETA.value: 0.123},
        )
    finally:
        MaxMinFilterer.apply = classmethod(orig)
    assert seen["eta_used"] == 1.0, (
        f"SM2 must apply eta=1.0, not the supplied 0.123 (got {seen})"
    )
    print("Mechanism check: SM2 pins eta=1.0 and forces OR handling.")

    print("OK — SM 2.0 ignores eta and minimize_or_joins by design.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
