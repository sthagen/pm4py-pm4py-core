'''
PM4Py – A Process Mining Library for Python
Copyright (C) 2026 Process Intelligence Solutions GmbH

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
'''
"""Join discovery: SESE joins (RPST) + inner OR-joins.

* ``generateSESEjoins`` repeatedly computes the RPST of the current
  model and, for every bond or rigid fragment whose convergence node is
  not yet a gateway, inserts a join there. A bond inherits the gateway
  type of its matching split; a rigid (and a loop) yields an inclusive
  (OR) join. The convergence node is the fragment exit, or the entry for
  loop fragments.
* ``generateInnerJoins`` then funnels every remaining multi-incoming
  task through a single inclusive (OR) join.

The inclusive joins are subsequently replaced by the OR-join
minimisation step.

This is a faithful port of the reference ``generateSESEjoins`` /
``generateInnerJoins``, validated to be byte-identical to
``splitminer.jar`` on the SM-Experiment logs (see ``..algorithm`` for
the validation summary).
"""
from typing import Any, Dict, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.joins.abc import JoinsDiscoverer
from pm4py.algo.discovery.split_miner.dtypes import rpst_tree

_GATE_KINDS = {"xor", "and", "or"}


def _is_gateway(wg: WorkingGraph, node: str) -> bool:
    n = wg.nodes.get(node)
    return n is not None and n.kind in _GATE_KINDS


def _directed_edges(wg: WorkingGraph) -> List[Tuple[str, str]]:
    return [(s, t) for s, ts in wg.out_edges.items() for t in ts]


def _collect_fragments(root) -> List:
    """RPST fragments in bottom-up order (deepest first)."""
    order: List = []
    queue = [root]
    while queue:
        f = queue.pop(0)
        order.insert(0, f)
        queue.extend(f.children)
    return order


def _generate_sese_joins_once(wg: WorkingGraph) -> bool:
    edges = _directed_edges(wg)
    res = rpst_tree.compute_rpst(edges)
    if res is None:
        return False
    root, _src, _snk = res

    changed: Set[str] = set()
    placed = False
    for f in _collect_fragments(root):
        if f.ttype not in ("B", "R"):
            continue
        entry, exit_ = f.entry, f.exit
        if entry is None or exit_ is None:
            continue
        exit_is_gate = _is_gateway(wg, exit_)
        entry_is_gate = _is_gateway(wg, entry)
        if not exit_is_gate:
            is_loop = False
            gatify, matching = exit_, entry
        elif not entry_is_gate:
            is_loop = True
            gatify, matching = entry, exit_
        else:
            continue  # both endpoints already gateways

        if gatify in changed:
            continue

        if f.ttype == "R":
            gtype = "or"
        else:
            mnode = wg.nodes.get(matching)
            if mnode is None or mnode.kind not in _GATE_KINDS:
                continue
            gtype = mnode.kind

        # fragment-internal predecessors of the convergence node
        frag_preds = {u for (u, v) in f.edges if v == gatify}
        incoming = list(wg.in_edges.get(gatify, []))
        gate = wg.add_node(gtype, label=gtype)
        wg.add_edge(gate, gatify)
        for p in incoming:
            if p in frag_preds or is_loop:
                wg.remove_edge(p, gatify)
                wg.add_edge(p, gate)
        changed.add(gatify)
        placed = True

    return placed


def _generate_inner_joins(wg: WorkingGraph) -> None:
    for nid in list(wg.nodes.keys()):
        n = wg.nodes.get(nid)
        if n is None or n.kind in _GATE_KINDS:
            continue
        preds = list(wg.in_edges.get(nid, []))
        if len(preds) <= 1:
            continue
        gate = wg.add_node("or", label="or")
        for p in preds:
            wg.remove_edge(p, nid)
            wg.add_edge(p, gate)
        wg.add_edge(gate, nid)


class SeseJoinsDiscoverer(JoinsDiscoverer):
    """RPST-based SESE joins followed by inner inclusive joins."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        guard = len(wg.nodes) + 5
        while guard > 0 and _generate_sese_joins_once(wg):
            guard -= 1
        _generate_inner_joins(wg)
