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
"""SESE / RPST helpers shared by joins discovery and OR-join minimisation.

A full Refined Process Structure Tree implementation needs triconnected-
component decomposition. For Split Miner's purposes we only need to know,
for every task with multiple incoming edges, (a) which incoming edges are
back-edges of a loop and (b) the unique entry of the smallest enclosing
single-entry single-exit fragment. We compute (a) with an iterative DFS
and (b) with NetworkX's ``immediate_dominators`` on the back-edge-free
skeleton.
"""
from dataclasses import dataclass
from typing import Dict, Set, Tuple

import networkx as nx

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.util import nx_utils


@dataclass
class SeseInfo:
    back_edges: Set[Tuple[str, str]]
    dominator: Dict[str, str]


def _to_digraph(wg: WorkingGraph):
    g = nx_utils.DiGraph()
    g.add_nodes_from(wg.nodes.keys())
    for s, t in wg.edges():
        g.add_edge(s, t)
    return g


def _back_edges(g, source: str) -> Set[Tuple[str, str]]:
    color: Dict[str, int] = {n: 0 for n in g.nodes}
    back: Set[Tuple[str, str]] = set()

    def _dfs(start: str) -> None:
        color[start] = 1
        stack = [(start, list(g.successors(start)))]
        while stack:
            u, children = stack[-1]
            if not children:
                color[u] = 2
                stack.pop()
                continue
            v = children.pop()
            if color[v] == 1:
                back.add((u, v))
            elif color[v] == 0:
                color[v] = 1
                stack.append((v, list(g.successors(v))))

    _dfs(source)
    for n in g.nodes:
        if color[n] == 0:
            _dfs(n)
    return back


def analyse(wg: WorkingGraph) -> SeseInfo:
    """Compute back-edges + immediate dominators of ``wg``."""
    g = _to_digraph(wg)
    if not wg.start_id:
        raise ValueError(
            "WorkingGraph.start_id must be set before SESE analysis"
        )
    back = _back_edges(g, wg.start_id)

    acyclic = nx_utils.DiGraph()
    acyclic.add_nodes_from(g.nodes)
    for e in g.edges:
        if e not in back:
            acyclic.add_edge(*e)

    dom: Dict[str, str] = {}
    reachable = nx_utils.descendants(acyclic, wg.start_id) | {wg.start_id}
    sub = acyclic.subgraph(reachable)
    imm = nx.immediate_dominators(sub, wg.start_id)
    for v, d in imm.items():
        if v != d:
            dom[v] = d
    return SeseInfo(back_edges=back, dominator=dom)
