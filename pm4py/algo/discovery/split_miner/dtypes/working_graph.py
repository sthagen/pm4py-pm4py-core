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
"""Mutable adjacency representation used during the Split Miner pipeline.

The split / join discovery phases need fast structural edits (re-target an
edge, insert a gateway, remove a node) that the immutable pm4py BPMN
object does not support efficiently. We therefore keep an internal
``WorkingGraph`` for the duration of the discovery and only materialise
the final :class:`pm4py.objects.bpmn.obj.BPMN` object at the end (see
:mod:`pm4py.algo.discovery.split_miner.bpmn_export`).
"""
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Literal, Optional, Set, Tuple

NodeKind = Literal["task", "xor", "and", "or", "start", "end"]


@dataclass
class Node:
    id: str
    kind: NodeKind
    label: str = ""


@dataclass
class WorkingGraph:
    """Adjacency-list representation of a BPMN graph in construction."""

    nodes: Dict[str, Node] = field(default_factory=dict)
    out_edges: Dict[str, List[str]] = field(default_factory=dict)
    in_edges: Dict[str, List[str]] = field(default_factory=dict)

    start_id: str = ""
    end_id: str = ""

    concurrency: Set[FrozenSet[str]] = field(default_factory=set)
    self_loops: Set[str] = field(default_factory=set)

    _id_counter: int = 0

    # ------------------------------------------------------------------
    # mutation helpers
    # ------------------------------------------------------------------

    def fresh_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}_{self._id_counter}"

    def add_node(
        self,
        kind: NodeKind,
        label: str = "",
        node_id: Optional[str] = None,
    ) -> str:
        if node_id is None:
            node_id = self.fresh_id(kind)
        self.nodes[node_id] = Node(id=node_id, kind=kind, label=label)
        self.out_edges.setdefault(node_id, [])
        self.in_edges.setdefault(node_id, [])
        return node_id

    def add_edge(self, src: str, tgt: str) -> None:
        if tgt not in self.out_edges[src]:
            self.out_edges[src].append(tgt)
        if src not in self.in_edges[tgt]:
            self.in_edges[tgt].append(src)

    def remove_edge(self, src: str, tgt: str) -> None:
        if tgt in self.out_edges.get(src, []):
            self.out_edges[src].remove(tgt)
        if src in self.in_edges.get(tgt, []):
            self.in_edges[tgt].remove(src)

    def remove_node(self, node_id: str) -> None:
        for s in list(self.in_edges.get(node_id, [])):
            self.remove_edge(s, node_id)
        for t in list(self.out_edges.get(node_id, [])):
            self.remove_edge(node_id, t)
        self.in_edges.pop(node_id, None)
        self.out_edges.pop(node_id, None)
        self.nodes.pop(node_id, None)

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    def successors(self, node_id: str) -> List[str]:
        return list(self.out_edges.get(node_id, []))

    def predecessors(self, node_id: str) -> List[str]:
        return list(self.in_edges.get(node_id, []))

    def edges(self) -> List[Tuple[str, str]]:
        return [(s, t) for s, ts in self.out_edges.items() for t in ts]

    def is_concurrent(self, a: str, b: str) -> bool:
        return frozenset((a, b)) in self.concurrency
