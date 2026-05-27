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
"""Improper-completion heuristic.

When an AND-split participates in a cycle — i.e. a loop re-enters the
parallel block before it has completed — Split Miner can produce a
model with improper completion. This heuristic repairs that by

  1. inserting a new XOR-split between the AND-split and its single
     parent, and
  2. relocating the loop-closing back-edge so that it now originates
     from the new XOR-split instead of from inside the parallel block.

A gateway left trivial (a single incoming and a single outgoing edge)
by the relocation is spliced out. The net effect matches Fig. 4b of the
paper: the parent activity (``A`` in the running example) can be
repeated through the new XOR-split's loop-back edge without committing
to the parallel block, while the activity that used to close the loop
(``D``) now flows straight on instead of looping.
"""
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from pm4py.algo.discovery.split_miner.dtypes.log import RefinedTrace
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.heuristics.abc import Heuristic
from pm4py.algo.discovery.split_miner.sese.rpst import analyse


def _to_digraph(wg: WorkingGraph) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_nodes_from(wg.nodes.keys())
    for s, t in wg.edges():
        g.add_edge(s, t)
    return g


def _splice_if_trivial(wg: WorkingGraph, node: str) -> None:
    """Remove ``node`` if it is a gateway with one incoming and one
    outgoing edge, reconnecting its predecessor to its successor."""
    n = wg.nodes.get(node)
    if n is None or n.kind not in {"xor", "and", "or"}:
        return
    ins = wg.predecessors(node)
    outs = wg.successors(node)
    if len(ins) == 1 and len(outs) == 1:
        p, s = ins[0], outs[0]
        wg.remove_edge(p, node)
        wg.remove_edge(node, s)
        if s != p:
            wg.add_edge(p, s)
        wg.remove_node(node)


class ImproperCompletionHeuristic(Heuristic):
    """Relocate an AND-split's loop-closing back-edge onto a new
    preceding XOR-split."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        refined_traces: Optional[List[RefinedTrace]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Iterate over a snapshot of the AND-split ids: new nodes
        # created by the heuristic must not be re-processed.
        for and_id in [
            nid for nid, n in list(wg.nodes.items()) if n.kind == "and"
        ]:
            if and_id not in wg.nodes:
                continue
            if len(wg.successors(and_id)) <= 1:
                continue

            graph = _to_digraph(wg)
            back_edges = analyse(wg).back_edges

            try:
                and_descendants = nx.descendants(graph, and_id)
            except nx.NodeNotFound:
                continue

            # A loop-closing back-edge of this AND-split is an edge
            # (u, v) such that the AND-split can reach u and v can reach
            # the AND-split — following it therefore re-enters the
            # parallel block.
            closing: List[Tuple[str, str]] = []
            for (u, v) in back_edges:
                reaches_u = u == and_id or u in and_descendants
                if not reaches_u:
                    continue
                v_reaches_and = v == and_id or (
                    v in graph and nx.has_path(graph, v, and_id)
                )
                if v_reaches_and:
                    closing.append((u, v))
            if not closing:
                continue

            preds = wg.predecessors(and_id)
            if len(preds) != 1:
                continue
            parent = preds[0]

            # Insert the new XOR-split between the parent and the
            # AND-split, keeping every parallel branch on the AND-split.
            xor_id = wg.add_node("xor", label="xor_lc")
            wg.remove_edge(parent, and_id)
            wg.add_edge(parent, xor_id)
            wg.add_edge(xor_id, and_id)

            # Relocate every loop-closing back-edge so its source is the
            # new XOR-split; the parallel block then completes properly.
            for (u, v) in closing:
                wg.remove_edge(u, v)
                wg.add_edge(xor_id, v)
                _splice_if_trivial(wg, u)
