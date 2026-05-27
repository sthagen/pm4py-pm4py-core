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
"""Lifecycle-aware directly-follows graph + loop discovery.

The refined DFG records ``a -> b`` whenever a lifecycle ``end`` of ``a``
is followed by a lifecycle ``start`` of ``b`` in the same trace with no
other ``end`` event observed in between. Short-loop detection then runs
on the end-event projection of the refined trace, which mirrors the
classic short-loop semantics over completed activity executions.
"""
from collections import defaultdict
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.dfg_discovery.abc import DFGDiscoverer
from pm4py.algo.discovery.split_miner.dfg_discovery.classic import (
    short_loop_frequencies,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.log import RefinedTrace
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo


def _build_refined_dfg(
    refined_traces: List[RefinedTrace],
) -> Tuple[DFG, Set[str]]:
    """Build the refined DFG: ``a -> b`` iff ``a_end`` is followed by
    ``b_start`` in the same trace with no intervening ``end`` event."""
    dfg: Dict[Tuple[str, str], int] = defaultdict(int)
    labels: Set[str] = set()
    for trace in refined_traces:
        for i, (a, lc_a, _) in enumerate(trace):
            labels.add(a)
            if lc_a != "end":
                continue
            for j in range(i + 1, len(trace)):
                b, lc_b, _ = trace[j]
                if lc_b == "end":
                    break
                if lc_b == "start":
                    dfg[(a, b)] += 1
    return dict(dfg), labels


def _discover_loops_refined(
    dfg: DFG, refined_traces: List[RefinedTrace]
) -> LoopInfo:
    """Short-loop detection on the end-event projection of the refined log."""
    self_loops = {a for (a, b), f in dfg.items() if a == b and f > 0}
    end_projection = [
        [lbl for lbl, lc, _ in trace if lc == "end"]
        for trace in refined_traces
    ]
    short_freq = short_loop_frequencies(end_projection)
    short_loops: Set[FrozenSet[str]] = set()
    for (a, b), f in short_freq.items():
        if f == 0:
            continue
        if a in self_loops or b in self_loops:
            continue
        if short_freq.get((a, b), 0) + short_freq.get((b, a), 0) == 0:
            continue
        short_loops.add(frozenset((a, b)))
    return LoopInfo(
        self_loops=self_loops,
        short_loops=short_loops,
        short_loop_freq=short_freq,
    )


class RefinedDFGDiscoverer(DFGDiscoverer[RefinedTrace]):
    """Lifecycle-aware refined directly-follows graph."""

    @classmethod
    def apply(
        cls,
        traces: List[RefinedTrace],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DFG, LoopInfo]:
        dfg, _ = _build_refined_dfg(traces)
        loops = _discover_loops_refined(dfg, traces)
        return dfg, loops
