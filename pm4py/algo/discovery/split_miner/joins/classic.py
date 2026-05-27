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
"""Join-gateway discovery.

Without an explicit RPST we approximate the SESE hierarchy by computing,
for each incoming edge of a multi-incoming target, the *set* of split
gateways that gate tokens reaching that edge — the nearest split on
every backward path, traversed transitively through intermediate join
gateways. Two predecessors can be grouped under one homogeneous join
only if their origin sets are identical and contain exactly one split;
the resulting join carries the same type as that split. Otherwise the
predecessors fall through to a single OR-join, modelling the
heterogeneous SESE fragment they sit in. Loop-joins (any incoming
back-edge) collapse into a single XOR-join as a special case.
"""
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.sese.rpst import analyse
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.joins.abc import JoinsDiscoverer


_SPLIT_KINDS = {"xor", "and", "or"}


def _is_split(wg: WorkingGraph, node: str) -> bool:
    n = wg.nodes.get(node)
    if n is None:
        return False
    return n.kind in _SPLIT_KINDS and len(wg.out_edges.get(node, [])) > 1


def _split_origins(
    wg: WorkingGraph,
    edge_source: str,
    skip: Set[str],
    back_edges: Set[Tuple[str, str]],
) -> Set[str]:
    """Collect every split that is the first split on a backward path.

    Walks backward from ``edge_source``. When a split gateway is reached
    on a path the walk terminates *that path* and records the split.
    When a join gateway is reached (single outgoing edge, multiple
    incoming edges) the walk recurses into each predecessor — a join
    receives tokens from every split feeding it, so every such split is
    a legitimate origin for any edge leaving the join. Cycles and
    back-edges are skipped.
    """
    origins: Set[str] = set()
    on_path: Set[str] = set()

    def visit(node: str) -> None:
        if node in on_path:
            return
        if _is_split(wg, node) and node not in skip:
            origins.add(node)
            return
        on_path.add(node)
        for p in wg.predecessors(node):
            if (p, node) in back_edges:
                continue
            visit(p)
        on_path.discard(node)

    visit(edge_source)
    return origins


def _add_single_join(
    wg: WorkingGraph,
    t: str,
    kind: str,
    sources: List[str],
) -> None:
    g = wg.add_node(kind, label=kind)
    for p in sources:
        wg.remove_edge(p, t)
        wg.add_edge(p, g)
    wg.add_edge(g, t)


def _join_one(
    wg: WorkingGraph,
    t: str,
    back_edges: Set[Tuple[str, str]],
) -> None:
    if any((p, t) in back_edges for p in wg.predecessors(t)):
        _add_single_join(wg, t, "xor", list(wg.predecessors(t)))
        return

    skip: Set[str] = set()
    max_rounds = len(wg.nodes) + 4
    for _ in range(max_rounds):
        preds = list(wg.predecessors(t))
        if len(preds) <= 1:
            return

        # Group predecessors by their full origin set. Only predecessors
        # whose origin sets are identical (and contain exactly one
        # split) can collapse into a homogeneous join.
        pred_origins: Dict[str, FrozenSet[str]] = {
            p: frozenset(_split_origins(wg, p, skip, back_edges))
            for p in preds
        }
        groups: Dict[FrozenSet[str], List[str]] = {}
        for p in preds:
            key = pred_origins[p]
            if not key:
                continue
            groups.setdefault(key, []).append(p)

        progress = False
        for origin_set, group in groups.items():
            if len(group) < 2:
                continue
            if len(origin_set) != 1:
                # Heterogeneous origin set — leave for the fallback
                # OR-join below; trying to merge here would silently
                # synchronise tokens from unrelated splits.
                continue
            single_origin = next(iter(origin_set))
            kind = wg.nodes[single_origin].kind
            _add_single_join(wg, t, kind, group)
            skip.add(single_origin)
            progress = True

        if not progress:
            remaining = list(wg.predecessors(t))
            if len(remaining) > 1:
                _add_single_join(wg, t, "or", remaining)
            return


class ClassicJoinsDiscoverer(JoinsDiscoverer):
    """Bottom-up join insertion guided by split-origin grouping."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        info = analyse(wg)
        targets = [
            nid
            for nid, n in list(wg.nodes.items())
            if n.kind in {"task", "end"}
            and len(wg.in_edges.get(nid, [])) > 1
        ]
        for t in targets:
            _join_one(wg, t, info.back_edges)
