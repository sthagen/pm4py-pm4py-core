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
"""Lifecycle-overlap concurrency oracle.

Two activities are flagged as concurrent when, over the whole log, the
fraction of observed lifecycle overlaps relative to their combined
number of complete executions is at least ``eps``:

    a || b   iff   2 * |a >< b| / (|a| + |b|) >= eps

where ``|a >< b|`` is the number of times an execution of ``a`` overlaps
in wall-clock time with an execution of ``b``.
"""
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.concurrency.abc import ConcurrencyOracle
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.log import RefinedTrace
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.util import exec_utils


class Parameters(Enum):
    EPSILON = "split_miner_epsilon"


DEFAULT_EPSILON = 0.1


def _build_intervals(
        trace: RefinedTrace,
) -> List[Tuple[str, int, int]]:
    intervals: List[Tuple[str, int, int]] = []
    open_starts: Dict[str, List[int]] = defaultdict(list)
    for idx, (label, lc, _) in enumerate(trace):
        if lc == "start":
            open_starts[label].append(idx)
        else:
            if open_starts[label]:
                s = open_starts[label].pop(0)
                intervals.append((label, s, idx))
            else:
                intervals.append((label, idx, idx))
    return intervals


class RefinedConcurrencyOracle(ConcurrencyOracle):
    """Concurrency test based on lifecycle overlaps."""

    @classmethod
    def apply(
            cls,
            dfg: DFG,
            traces: Optional[List[RefinedTrace]],
            loops: LoopInfo,
            parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        if traces is None:
            raise ValueError(
                "RefinedConcurrencyOracle requires the refined log"
            )
        eps = exec_utils.get_param_value(
            Parameters.EPSILON, parameters or {}, DEFAULT_EPSILON
        )

        counts: Dict[str, int] = defaultdict(int)
        overlaps: Dict[FrozenSet[str], int] = defaultdict(int)
        for trace in traces:
            intervals = _build_intervals(trace)
            for label, _, _ in intervals:
                counts[label] += 1
            for i, (l1, s1, e1) in enumerate(intervals):
                for l2, s2, e2 in intervals[i + 1:]:
                    if l1 == l2:
                        continue
                    if s1 < e2 and s2 < e1:
                        overlaps[frozenset((l1, l2))] += 1

        concurrent: Set[FrozenSet[str]] = set()
        for pair, ov in overlaps.items():
            if ov == 0:
                continue
            if pair in loops.short_loops:
                continue
            a, b = tuple(pair)
            if a in loops.self_loops or b in loops.self_loops:
                continue
            total = counts.get(a, 0) + counts.get(b, 0)
            if total == 0:
                continue
            score = 2.0 * ov / total
            if score >= eps:
                concurrent.add(pair)

        pdfg: DFG = {}
        for (a, b), f in dfg.items():
            if frozenset((a, b)) in concurrent:
                continue
            pdfg[(a, b)] = f
        return ConcurrencyResult(pdfg=pdfg, concurrent_pairs=concurrent)
