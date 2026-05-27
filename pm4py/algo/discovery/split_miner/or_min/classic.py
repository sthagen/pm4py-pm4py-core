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
"""OR-join minimisation.

Replace every *trivial* OR-join with the semantically equivalent
XOR- or AND-join. An OR-join is trivial when, for every split gateway
between its minimal dominator and itself, the incoming edges that may
receive tokens via that split all carry the same semantic (all XOR or
all AND).
"""
from typing import Any, Dict, Optional, Set, Tuple

import networkx as nx

from pm4py.algo.discovery.split_miner.sese.rpst import analyse
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.or_min.abc import OrJoinMinimizer


def _to_digraph(wg: WorkingGraph) -> "nx.DiGraph":
    g = nx.DiGraph()
    g.add_nodes_from(wg.nodes.keys())
    for s, t in wg.edges():
        g.add_edge(s, t)
    return g


def _check_or_semantic(
    wg: WorkingGraph,
    g: "nx.DiGraph",
    j: str,
    info,
) -> str:
    d = info.dominator.get(j)
    if d is None:
        return "or"

    forward = nx.descendants(g, d) | {d}
    backward = nx.ancestors(g, j) | {j}
    between = forward & backward
    # ``between`` is a Python ``set``; sort before iterating so the
    # eventual semantic decision is independent of hash randomisation.
    splits = [
        n
        for n in sorted(between, reverse=True)
        if wg.nodes[n].kind in {"xor", "and", "or"}
        and len(wg.out_edges.get(n, [])) > 1
        and n != j
    ]
    if not splits:
        return "or"

    incoming_of_j = set(wg.in_edges.get(j, []))

    def reaches(x: str) -> Set[Tuple[str, str]]:
        if x == j:
            return set()
        try:
            descendants_x = nx.descendants(g, x) | {x}
        except nx.NetworkXError:
            return set()
        return {(p, j) for p in incoming_of_j if p in descendants_x}

    semantic: str = ""
    for g_s in splits:
        outs = list(wg.out_edges.get(g_s, []))
        reach: Dict[str, Set[Tuple[str, str]]] = {
            x: reaches(x) for x in outs
        }
        g_kind = wg.nodes[g_s].kind
        if g_kind == "or":
            return "or"

        for i in range(len(outs)):
            for k in range(len(outs)):
                if i == k:
                    continue
                t1, t2 = reach[outs[i]], reach[outs[k]]
                if t1 == t2:
                    continue
                inter = t1 & t2
                s1 = t1 - inter
                s2 = t2 - inter
                fully_separating = bool(s1 and s2)
                asymmetric = bool(s1) ^ bool(s2)
                if fully_separating or (asymmetric and g_kind == "and"):
                    if semantic and semantic != g_kind:
                        return "or"
                    semantic = g_kind

        if g_kind == "xor" and any(not reach[x] for x in outs):
            if semantic and semantic != "xor":
                return "or"
            semantic = "xor"

    return semantic if semantic else "or"


class ClassicOrJoinMinimizer(OrJoinMinimizer):
    """Replace trivial OR-joins in-place."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        or_joins = [
            nid
            for nid, n in list(wg.nodes.items())
            if n.kind == "or" and len(wg.in_edges.get(nid, [])) > 1
        ]
        if not or_joins:
            return

        info = analyse(wg)
        g = _to_digraph(wg)
        for be in info.back_edges:
            if g.has_edge(*be):
                g.remove_edge(*be)

        for j in or_joins:
            new_kind = _check_or_semantic(wg, g, j, info)
            if new_kind in {"xor", "and"}:
                wg.nodes[j].kind = new_kind
                wg.nodes[j].label = new_kind
