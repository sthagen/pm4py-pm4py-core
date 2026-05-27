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
"""Max-min-frequency BFS filter for the pruned DFG.

A Dijkstra-style BFS retains every node on at least one source-to-sink
path while minimising the number of edges kept. The output is the union
of each node's best-incoming and best-outgoing edges plus every edge
with frequency above the eta-percentile threshold.
"""
import math
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.filtering import FilterResult
from pm4py.algo.discovery.split_miner.dtypes.log import END_LABEL, START_LABEL
from pm4py.algo.discovery.split_miner.filtering.abc import Filterer
from pm4py.util import exec_utils


class Parameters(Enum):
    ETA = "split_miner_eta"


DEFAULT_ETA = 0.4


def _node_set(dfg: DFG) -> Set[str]:
    s: Set[str] = set()
    for a, b in dfg.keys():
        s.add(a)
        s.add(b)
    return s


def _find_source_sink(dfg: DFG, nodes: Set[str]) -> Tuple[str, str]:
    has_in = {b for (_, b) in dfg.keys()}
    has_out = {a for (a, _) in dfg.keys()}
    sources = [n for n in nodes if n not in has_in]
    sinks = [n for n in nodes if n not in has_out]
    if len(sources) != 1 or len(sinks) != 1:
        if START_LABEL in nodes and END_LABEL in nodes:
            return START_LABEL, END_LABEL
        raise ValueError(
            f"Filtered PDFG must have exactly one source/sink; "
            f"got sources={sources}, sinks={sinks}"
        )
    return sources[0], sinks[0]


def _best_incoming(
    dfg: DFG, source: str, nodes: Set[str]
) -> Tuple[Dict[str, float], Dict[str, Tuple[str, str]]]:
    capacity: Dict[str, float] = {n: 0 for n in nodes}
    capacity[source] = math.inf
    best: Dict[str, Tuple[str, str]] = {}

    out_adj: Dict[str, List[Tuple[str, int]]] = {n: [] for n in nodes}
    for (a, b), f in dfg.items():
        out_adj[a].append((b, f))

    in_queue: Set[str] = {source}
    unexplored: Set[str] = set(nodes) - {source}
    queue = deque([source])
    while queue:
        p = queue.popleft()
        in_queue.discard(p)
        for n, f_e in out_adj[p]:
            c_max = min(capacity[p], f_e)
            updated = False
            if c_max > capacity[n]:
                capacity[n] = c_max
                best[n] = (p, n)
                updated = True
            if updated:
                if n in unexplored:
                    unexplored.discard(n)
                if n not in in_queue:
                    queue.append(n)
                    in_queue.add(n)
            elif n in unexplored:
                unexplored.discard(n)
                if n not in in_queue:
                    queue.append(n)
                    in_queue.add(n)
    return capacity, best


def _best_outgoing(
    dfg: DFG, sink: str, nodes: Set[str]
) -> Tuple[Dict[str, float], Dict[str, Tuple[str, str]]]:
    capacity: Dict[str, float] = {n: 0 for n in nodes}
    capacity[sink] = math.inf
    best: Dict[str, Tuple[str, str]] = {}

    in_adj: Dict[str, List[Tuple[str, int]]] = {n: [] for n in nodes}
    for (a, b), f in dfg.items():
        in_adj[b].append((a, f))

    in_queue: Set[str] = {sink}
    unexplored: Set[str] = set(nodes) - {sink}
    queue = deque([sink])
    while queue:
        n = queue.popleft()
        in_queue.discard(n)
        for p, f_e in in_adj[n]:
            c_max = min(capacity[n], f_e)
            updated = False
            if c_max > capacity[p]:
                capacity[p] = c_max
                best[p] = (p, n)
                updated = True
            if updated:
                if p in unexplored:
                    unexplored.discard(p)
                if p not in in_queue:
                    queue.append(p)
                    in_queue.add(p)
            elif p in unexplored:
                unexplored.discard(p)
                if p not in in_queue:
                    queue.append(p)
                    in_queue.add(p)
    return capacity, best


class MaxMinFilterer(Filterer):
    """Dijkstra-style BFS that retains each node's best in/out edges."""

    @classmethod
    def apply(
        cls,
        pdfg: DFG,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        eta = exec_utils.get_param_value(
            Parameters.ETA, parameters or {}, DEFAULT_ETA
        )
        nodes = _node_set(pdfg)
        source, sink = _find_source_sink(pdfg, nodes)

        fmax_in: Dict[str, int] = {n: 0 for n in nodes}
        fmax_out: Dict[str, int] = {n: 0 for n in nodes}
        for (a, b), f in pdfg.items():
            if f > fmax_out[a]:
                fmax_out[a] = f
            if f > fmax_in[b]:
                fmax_in[b] = f

        frequencies: List[int] = []
        for n in nodes:
            if n != source:
                frequencies.append(fmax_in[n])
            if n != sink:
                frequencies.append(fmax_out[n])

        f_th = (
            float(np.percentile(frequencies, eta * 100.0)) if frequencies else 0.0
        )

        _, best_in = _best_incoming(pdfg, source, nodes)
        _, best_out = _best_outgoing(pdfg, sink, nodes)
        kept_best: Set[Tuple[str, str]] = set(best_in.values()) | set(
            best_out.values()
        )

        edges_out: Set[Tuple[str, str]] = set()
        for (a, b), f in pdfg.items():
            if (a, b) in kept_best or f > f_th:
                edges_out.add((a, b))
        return FilterResult(edges=edges_out, source=source, sink=sink)
