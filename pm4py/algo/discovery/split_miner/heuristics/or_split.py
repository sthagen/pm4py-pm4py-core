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
"""OR-split identification heuristic.

For every AND-split we check, pairwise, whether its task successors are
sometimes mutually exclusive and sometimes concurrent (in roughly equal
proportions). When that pattern holds for the majority of pairs, the
AND-split is rewritten as an OR-split — modelling inclusive-choice
behaviour rather than strict parallelism.
"""
from collections import defaultdict
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.dtypes.log import RefinedTrace
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.heuristics.abc import Heuristic


def _collect_intervals(
    trace: RefinedTrace,
) -> Dict[str, List[Tuple[int, int]]]:
    open_starts: Dict[str, List[int]] = defaultdict(list)
    intervals: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for idx, (label, lc, _) in enumerate(trace):
        if lc == "start":
            open_starts[label].append(idx)
        else:
            if open_starts[label]:
                s = open_starts[label].pop(0)
                intervals[label].append((s, idx))
            else:
                intervals[label].append((idx, idx))
    return intervals


def _pair_observation(
    refined_traces: List[RefinedTrace],
) -> Tuple[Dict[FrozenSet[str], int], Dict[FrozenSet[str], int]]:
    concurrent: Dict[FrozenSet[str], int] = defaultdict(int)
    exclusive: Dict[FrozenSet[str], int] = defaultdict(int)

    universe: Set[str] = set()
    for trace in refined_traces:
        for label, _, _ in trace:
            universe.add(label)

    for trace in refined_traces:
        intervals = _collect_intervals(trace)
        labels = list(intervals.keys())
        for i, a in enumerate(labels):
            for b in labels[i + 1:]:
                pair = frozenset((a, b))
                if any(
                    s1 < e2 and s2 < e1
                    for (s1, e1) in intervals[a]
                    for (s2, e2) in intervals[b]
                ):
                    concurrent[pair] += 1
        present = {label for label, _, _ in trace}
        absent = universe - present
        for a in present:
            for b in absent:
                exclusive[frozenset((a, b))] += 1
    return concurrent, exclusive


def _pair_eligible(conc: int, excl: int) -> bool:
    if conc == 0 or excl == 0:
        return False
    return 2 * conc >= excl and 2 * excl >= conc


def _resolve_to_task(
    wg: WorkingGraph, node: str, depth: int = 0
) -> Optional[str]:
    if depth > 32:
        return None
    n = wg.nodes.get(node)
    if n is None:
        return None
    if n.kind == "task":
        return n.label
    if n.kind in {"start", "end"}:
        return None
    for s in wg.successors(node):
        label = _resolve_to_task(wg, s, depth + 1)
        if label is not None:
            return label
    return None


class OrSplitHeuristic(Heuristic):
    """Relabel AND-splits as OR-splits when the log supports it."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        refined_traces: Optional[List[RefinedTrace]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not refined_traces:
            return
        conc_counts, excl_counts = _pair_observation(refined_traces)

        for and_id in [
            nid for nid, n in list(wg.nodes.items()) if n.kind == "and"
        ]:
            succs = wg.successors(and_id)
            if len(succs) < 2:
                continue
            resolved = [
                lbl
                for lbl in (_resolve_to_task(wg, s) for s in succs)
                if lbl is not None
            ]
            if len(resolved) < 2:
                continue
            eligible = 0
            total = 0
            for i, a in enumerate(resolved):
                for b in resolved[i + 1:]:
                    pair = frozenset((a, b))
                    total += 1
                    if _pair_eligible(
                        conc_counts.get(pair, 0), excl_counts.get(pair, 0)
                    ):
                        eligible += 1
            if total > 0 and eligible * 2 > total:
                wg.nodes[and_id].kind = "or"
