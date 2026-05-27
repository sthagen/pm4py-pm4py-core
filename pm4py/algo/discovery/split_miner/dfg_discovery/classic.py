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
"""Classic directly-follows graph + loop discovery.

Builds the DFG from a list of activity-label traces and detects:

  * self-loops — activities ``a`` with ``|a -> a| > 0``;
  * short-loops — pairs ``{a, b}`` for which an ``a, b, a`` sub-sequence
    appears in some trace while neither ``a`` nor ``b`` is a self-loop.
"""
from collections import defaultdict
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.dfg_discovery.abc import DFGDiscoverer
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.log import LabelTrace
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo


def _build_dfg(traces: List[LabelTrace]) -> Tuple[DFG, Set[str]]:
    dfg: Dict[Tuple[str, str], int] = defaultdict(int)
    labels: Set[str] = set()
    for trace in traces:
        for label in trace:
            labels.add(label)
        for a, b in zip(trace, trace[1:]):
            dfg[(a, b)] += 1
    return dict(dfg), labels


def short_loop_frequencies(
    traces: List[LabelTrace],
) -> Dict[Tuple[str, str], int]:
    """Number of (a, b, a) sub-sequences over the supplied traces."""
    freq: Dict[Tuple[str, str], int] = defaultdict(int)
    for trace in traces:
        for i in range(len(trace) - 2):
            a, b, c = trace[i], trace[i + 1], trace[i + 2]
            if a == c and a != b:
                freq[(a, b)] += 1
    return dict(freq)


def _discover_loops(dfg: DFG, traces: List[LabelTrace]) -> LoopInfo:
    self_loops: Set[str] = {
        a for (a, b), f in dfg.items() if a == b and f > 0
    }
    short_freq = short_loop_frequencies(traces)
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


class ClassicDFGDiscoverer(DFGDiscoverer[LabelTrace]):
    """Directly-follows graph built from flat label traces."""

    @classmethod
    def apply(
        cls,
        traces: List[LabelTrace],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DFG, LoopInfo]:
        dfg, _ = _build_dfg(traces)
        loops = _discover_loops(dfg, traces)
        return dfg, loops


def strip_self_loops(dfg: DFG) -> DFG:
    """Drop ``a -> a`` arcs; they are re-attached during BPMN export."""
    return {(a, b): f for (a, b), f in dfg.items() if a != b}
