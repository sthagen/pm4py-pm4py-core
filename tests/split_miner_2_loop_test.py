"""Regression test for Split Miner 2.0 loop handling.

Replaces the earlier ``split_miner_2_heuristics_test`` which exercised an
*improper-completion* heuristic. That heuristic was an approximation: it
restructured an ``A -> {B || C} -> D -> A`` loop so that ``A`` could
repeat through a *D-free* loop branch (a fresh XOR-split before the
AND-split, owning the loop edge). The reference Java Split Miner 2.0
(``MineWithSMTC``) does **not** do this — it closes the loop *after* the
whole parallel block plus ``D``. This test pins down that faithful
behaviour, which was verified byte-identical to the Java reference on
this exact log (Java SM2 and this port both yield 4 tasks, 2 AND, 2 XOR,
0 OR, and the same edge set).

The example (B and C parallel, D sequential, D looping back to A):

    --> A --> AND-split --> { B, C } --> AND-join --> D --> XOR-split -+
        ^                                                  |          |
        +------------------ XOR-join <---------------------+        (end)

So ``A`` can only be re-entered by completing ``B``, ``C`` and ``D`` —
there is no D-free shortcut back to ``A``.
"""
import datetime
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd

import pm4py
from pm4py.objects.bpmn.obj import BPMN

assert pm4py.__file__.startswith(_REPO_ROOT), (
    f"test must run against the local pm4py copy in {_REPO_ROOT}, "
    f"but pm4py was imported from {pm4py.__file__}"
)

_MINUTE = datetime.timedelta(minutes=1)
# B and C overlap (parallel); the staggered end times let each branch be
# the last to complete in some case, so the DFG records both B->D and
# C->D. D runs strictly after the block.
_PARALLEL_END_OPTIONS = {
    "B": [("B", 2, 6), ("C", 2, 5)],
    "C": [("B", 2, 5), ("C", 2, 6)],
}
_D_START_MIN, _D_END_MIN = 7, 8
# (name, iterations, last-completing branch). Looping cases iterate so
# the D->A arc dominates; single-iteration cases keep D->end alive.
PATTERNS = [
    ("loop_B", 4, "B"),
    ("loop_C", 4, "C"),
    ("term_B", 1, "B"),
    ("term_C", 1, "C"),
]


def _emit(rows, case_id, label, start, end):
    for phase, ts in (("start", start), ("complete", end)):
        rows.append({
            "case:concept:name": case_id,
            "concept:name": label,
            "lifecycle:transition": phase,
            "time:timestamp": ts,
        })


def _emit_iteration(rows, case_id, origin, last_branch):
    _emit(rows, case_id, "A", origin, origin + _MINUTE)
    for label, s_off, e_off in _PARALLEL_END_OPTIONS[last_branch]:
        _emit(rows, case_id, label, origin + s_off * _MINUTE,
              origin + e_off * _MINUTE)
    _emit(rows, case_id, "D", origin + _D_START_MIN * _MINUTE,
          origin + _D_END_MIN * _MINUTE)
    return origin + (_D_END_MIN + 1) * _MINUTE


def build_log() -> pd.DataFrame:
    base = datetime.datetime(2026, 1, 1)
    rows: list[dict] = []
    case_index = 0
    for _ in range(4):
        for pattern_name, n_iter, last_branch in PATTERNS:
            case_id = f"c{case_index:02d}_{pattern_name}"
            origin = base + datetime.timedelta(days=case_index)
            case_index += 1
            for _i in range(n_iter):
                origin = _emit_iteration(rows, case_id, origin, last_branch)
    return pd.DataFrame(rows)


def _by_kind(bpmn):
    tasks, ands, xors, ors = {}, [], [], []
    for n in bpmn.get_nodes():
        if isinstance(n, BPMN.Task):
            tasks[n.get_name()] = n
        elif isinstance(n, BPMN.ParallelGateway):
            ands.append(n)
        elif isinstance(n, BPMN.ExclusiveGateway):
            xors.append(n)
        elif isinstance(n, BPMN.InclusiveGateway):
            ors.append(n)
    return tasks, ands, xors, ors


def _succ(bpmn, node):
    return [f.target for f in bpmn.get_flows() if f.source is node]


def _pred(bpmn, node):
    return [f.source for f in bpmn.get_flows() if f.target is node]


def main() -> int:
    df = build_log()
    print(f"log: {len(df)} events, {df['case:concept:name'].nunique()} cases")

    bpmn = pm4py.discover_bpmn_split_miner(df, epsilon=0.2, variant="sm2")
    tasks, ands, xors, ors = _by_kind(bpmn)

    # Faithful counts (verified byte-identical to Java SM 2.0 on this log).
    assert set(tasks) == {"A", "B", "C", "D"}, set(tasks)
    assert len(ands) == 2, f"expected 2 AND gateways, got {len(ands)}"
    assert len(xors) == 2, f"expected 2 XOR gateways, got {len(xors)}"
    assert len(ors) == 0, f"expected no OR gateways, got {len(ors)}"

    # The AND-split carries exactly the parallel block {B, C}; D is *not*
    # under the AND-split (it is sequential, after the AND-join).
    and_split = next(g for g in ands if len(_succ(bpmn, g)) > 1)
    and_branches = {t.get_name() for t in _succ(bpmn, and_split)}
    assert and_branches == {"B", "C"}, and_branches
    assert "D" not in and_branches

    # The loop is closed *after* D: D -> XOR-split -> {end, back-edge},
    # and the back-edge reaches A's preceding XOR-join. So A can only be
    # re-entered after completing B, C and D — there is no D-free loop.
    a_join = _pred(bpmn, tasks["A"])
    assert len(a_join) == 1 and isinstance(a_join[0], BPMN.ExclusiveGateway)
    a_join = a_join[0]
    d_split = _succ(bpmn, tasks["D"])
    assert len(d_split) == 1 and isinstance(d_split[0], BPMN.ExclusiveGateway)
    d_split = d_split[0]
    assert a_join in _succ(bpmn, d_split), (
        "the loop back-edge must originate after D (no D-free loop)"
    )
    # Nothing re-enters A except the start and the post-D back-edge.
    assert all(
        p is d_split or isinstance(p, BPMN.StartEvent)
        for p in _pred(bpmn, a_join)
    ), "A's loop-entry join must only be fed by start and the post-D edge"

    print("OK — SM 2.0 closes the A/{B||C}/D loop after D (no D-free loop).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
