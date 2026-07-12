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
"""Split Miner 2.0 OR-split heuristic.

An AND-split is promoted to an inclusive
(OR) split when its activity branches form *potential OR* pairs (pairs
observed both concurrently and exclusively, the ``potentialORs`` matrix)
in sufficient number: counting every ordered pair of distinct
activity-target branches that is a potential OR, the split is promoted
when that count exceeds the split's out-degree. Whenever any split is
promoted, ``matchORs`` walks the RPST and turns the exit gateway of
every bond with an inclusive entry into an inclusive gateway too, so the
new OR-split is matched by an OR-join.
"""
from typing import FrozenSet, Set

from pm4py.algo.discovery.split_miner.dtypes import rpst_tree
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph

_GATE_KINDS = {"xor", "and", "or"}


def apply_or_split_heuristic(
    wg: WorkingGraph,
    potential_ors: Set[FrozenSet[str]],
) -> None:
    """Promote eligible AND-splits to OR-splits and re-match their joins."""
    if not potential_ors:
        return

    converted = False
    for nid in list(wg.nodes.keys()):
        node = wg.nodes.get(nid)
        if node is None or node.kind != "and":
            continue
        succs = wg.successors(nid)
        if len(succs) <= 1:
            continue
        # Only activity (task) branches participate; gateway branches
        # are skipped, mirroring the ``instanceof Gateway`` guard.
        act_labels = [
            wg.nodes[s].label
            for s in succs
            if wg.nodes.get(s) is not None and wg.nodes[s].kind == "task"
        ]
        counter = 0
        for i, a in enumerate(act_labels):
            for j, b in enumerate(act_labels):
                if i == j:
                    continue
                if frozenset((a, b)) in potential_ors:
                    counter += 1
        if counter > len(succs):
            node.kind = "or"
            node.label = "or"
            converted = True

    if converted:
        _match_ors(wg)


def _match_ors(wg: WorkingGraph) -> None:
    """For every RPST bond with an inclusive entry, make the exit
    inclusive too (port of ``DiagramHandler.matchORs``)."""
    edges = [(s, t) for s, ts in wg.out_edges.items() for t in ts]
    res = rpst_tree.compute_rpst(edges)
    if res is None:
        return
    root, _src, _snk = res

    queue = [root]
    while queue:
        frag = queue.pop(0)
        queue.extend(frag.children)
        if frag.ttype != "B":
            continue
        entry = wg.nodes.get(frag.entry) if frag.entry else None
        exit_ = wg.nodes.get(frag.exit) if frag.exit else None
        if (
            entry is not None
            and exit_ is not None
            and entry.kind == "or"
            and exit_.kind in _GATE_KINDS
        ):
            exit_.kind = "or"
            exit_.label = "or"
