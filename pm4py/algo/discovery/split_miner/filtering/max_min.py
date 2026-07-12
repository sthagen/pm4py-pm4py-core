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
"""Frequency filter with connectedness guarantees for the pruned DFG.

This reproduces the reference Split Miner ``filterWithGuarantees`` (the
"FWG" filter used by the command-line miner):

1. A frequency threshold is taken as the ``eta`` order statistic of the
   per-node most-frequent incoming/outgoing edges.
2. A max-capacity (widest path) spanning set is computed from source and
   to sink so the highest-throughput backbone is always retained.
3. Every edge is kept when it belongs to that backbone or when its
   frequency reaches the threshold; the remaining edges are dropped, but
   never the sole incoming edge of a node nor the sole outgoing edge of a
   node (the connectedness guard).

This is a faithful port of the Java ``filterWithGuarantees``, validated
to produce the same pruned DFG as ``splitminer.jar`` on the
SM-Experiment logs (see ``..algorithm`` for the validation summary). The
max-capacity backbone plus the connectedness guard frequently make the
result insensitive to ``eta`` — a high threshold still keeps the
backbone — which mirrors the reference tool and is not a bug.
"""
import math
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.filtering import FilterResult
from pm4py.algo.discovery.split_miner.dtypes.log import END_LABEL, START_LABEL
from pm4py.algo.discovery.split_miner.filtering.abc import Filterer
from pm4py.util import exec_utils


class Parameters(Enum):
    ETA = "split_miner_eta"


DEFAULT_ETA = 0.4

Edge = Tuple[str, str]


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


def _edge_rank(edge: Edge, freq: int) -> Tuple[int, str, str]:
    """Total order matching the reference DFGEdge comparator.

    Edges are ordered by frequency, then by source label, then by target
    label. ``max`` therefore picks the most frequent edge, breaking ties
    towards the lexicographically greatest endpoints.
    """
    a, b = edge
    return (freq, a, b)


def _max_frequency_best_edges(
    dfg: DFG, source: str, sink: str, nodes: Set[str]
) -> Set[Edge]:
    """Per-node most frequent incoming/outgoing edges (deduplicated).

    Mirrors ``bestEdgesOnMaxFrequencies``: every node except the sink
    contributes its most frequent outgoing edge and every node except the
    source contributes its most frequent incoming edge.
    """
    out_edges: Dict[str, List[Edge]] = {n: [] for n in nodes}
    in_edges: Dict[str, List[Edge]] = {n: [] for n in nodes}
    for (a, b) in dfg.keys():
        out_edges[a].append((a, b))
        in_edges[b].append((a, b))

    best: Set[Edge] = set()
    for n in nodes:
        if n != sink and out_edges[n]:
            best.add(max(out_edges[n], key=lambda e: _edge_rank(e, dfg[e])))
        if n != source and in_edges[n]:
            best.add(max(in_edges[n], key=lambda e: _edge_rank(e, dfg[e])))
    return best


def _filter_threshold(dfg: DFG, best_freq_edges: Set[Edge], eta: float) -> int:
    """``computeFilterThreshold``: the ``eta`` order statistic.

    The most-frequent best edges are sorted ascending; the threshold is
    the frequency at index ``round(N * eta)`` (clamped to the last index).
    """
    if not best_freq_edges:
        return 0
    ordered = sorted(best_freq_edges, key=lambda e: _edge_rank(e, dfg[e]))
    i = int(round(len(ordered) * eta))
    if i >= len(ordered):
        i = len(ordered) - 1
    return dfg[ordered[i]]


def _max_capacity_best_edges(
    dfg: DFG, source: str, sink: str, nodes: Set[str]
) -> Set[Edge]:
    """Widest-path backbone from source and to sink (``bestEdgesOnMaxCapacities``).

    A Bellman-Ford style relaxation computes, for every node, the maximum
    bottleneck capacity reachable from the source and the symmetric value
    towards the sink, recording the edge that realises each optimum.
    """
    out_adj: Dict[str, List[Tuple[str, int]]] = {n: [] for n in nodes}
    in_adj: Dict[str, List[Tuple[str, int]]] = {n: [] for n in nodes}
    for (a, b), f in dfg.items():
        out_adj[a].append((b, f))
        in_adj[b].append((a, f))

    best: Set[Edge] = set()

    # Forward: widest path from the source.
    cap_from: Dict[str, float] = {n: 0 for n in nodes}
    cap_from[source] = math.inf
    best_pred: Dict[str, Edge] = {}
    queue = deque([source])
    in_q: Set[str] = {source}
    while queue:
        p = queue.popleft()
        in_q.discard(p)
        cap_p = cap_from[p]
        for b, f in out_adj[p]:
            c = f if cap_p > f else cap_p
            if c > cap_from[b]:
                cap_from[b] = c
                best_pred[b] = (p, b)
                if b not in in_q:
                    queue.append(b)
                    in_q.add(b)
    best.update(best_pred.values())

    # Backward: widest path to the sink.
    cap_to: Dict[str, float] = {n: 0 for n in nodes}
    cap_to[sink] = math.inf
    best_succ: Dict[str, Edge] = {}
    queue = deque([sink])
    in_q = {sink}
    while queue:
        n = queue.popleft()
        in_q.discard(n)
        cap_n = cap_to[n]
        for a, f in in_adj[n]:
            c = f if cap_n > f else cap_n
            if c > cap_to[a]:
                cap_to[a] = c
                best_succ[a] = (a, n)
                if a not in in_q:
                    queue.append(a)
                    in_q.add(a)
    best.update(best_succ.values())

    return best


class MaxMinFilterer(Filterer):
    """Port of the reference ``filterWithGuarantees`` (FWG) filter."""

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

        # (1) threshold from the most-frequent best edges,
        # (2) widest-path backbone that must survive the filter.
        freq_best = _max_frequency_best_edges(pdfg, source, sink, nodes)
        threshold = _filter_threshold(pdfg, freq_best, eta)
        cap_best = _max_capacity_best_edges(pdfg, source, sink, nodes)

        # Live degree bookkeeping for the connectedness guard.
        in_deg: Dict[str, int] = {n: 0 for n in nodes}
        out_deg: Dict[str, int] = {n: 0 for n in nodes}
        for (a, b) in pdfg.keys():
            out_deg[a] += 1
            in_deg[b] += 1

        kept: Set[Edge] = set()
        removable: List[Edge] = []
        for (a, b), f in pdfg.items():
            if (a, b) in cap_best or f >= threshold:
                kept.add((a, b))
            else:
                removable.append((a, b))

        # Drop the remaining edges deterministically, but never the sole
        # incoming edge of a node nor the sole outgoing edge of a node.
        for (a, b) in sorted(
            removable, key=lambda e: _edge_rank(e, pdfg[e])
        ):
            if in_deg[b] == 1 or out_deg[a] == 1:
                kept.add((a, b))
                continue
            in_deg[b] -= 1
            out_deg[a] -= 1

        return FilterResult(edges=kept, source=source, sink=sink)
