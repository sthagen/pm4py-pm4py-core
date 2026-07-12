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
"""Lifecycle (overlap-based) concurrency oracle for Split Miner 2.0.

Faithful port of ``DirectlyFollowGraphPlus.detectParallelismsFromComplex
Log``. Unlike the classic oracle — which infers concurrency from a
*balanced bidirectional* directly-follows pair — this oracle marks two
activities concurrent when their execution intervals overlap often
enough: ``relativeConcurrency[a][b] = overlap[a][b] / (obs[a] + obs[b])``
exceeds ``epsilon``. Each such directly-follows edge is then dropped
under the same connectedness guard the classic oracle uses; a vetoed
removal demotes the pair and drops the opposite direction instead.
"""
from typing import Dict, FrozenSet, List, Set, Tuple

from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG


def apply_overlap_concurrency(
    dfg: DFG,
    overlap: Dict[FrozenSet[str], int],
    observed: Dict[str, int],
    eps: float,
) -> ConcurrencyResult:
    """Detect concurrency from lifecycle overlaps on a complex log."""
    out_count: Dict[str, int] = {}
    in_count: Dict[str, int] = {}
    for (a, b) in dfg.keys():
        out_count[a] = out_count.get(a, 0) + 1
        in_count[b] = in_count.get(b, 0) + 1

    # Directly-follows edges whose endpoints overlap often enough are
    # candidate parallelisms. Java thresholds the *directed* relative
    # concurrency, but the matrix is symmetric, so a frozenset lookup is
    # equivalent.
    potential: List[Tuple[Tuple[str, str], int]] = []
    for (a, b), f in dfg.items():
        if a == b:
            continue
        ov = overlap.get(frozenset((a, b)), 0)
        if ov <= 0:
            continue
        denom = observed.get(a, 0) + observed.get(b, 0)
        if denom <= 0:
            continue
        if ov / denom > eps:
            potential.append(((a, b), f))

    # Ascending frequency (then lexicographic edge) reproduces
    # Collections.sort on Java's DFGEdge.
    potential.sort(key=lambda x: (x[1], x[0]))

    removed: Set[Tuple[str, str]] = set()
    concurrent_pairs: Set[FrozenSet[str]] = set()

    def _can_drop(edge: Tuple[str, str]) -> bool:
        a, b = edge
        return out_count.get(a, 0) > 1 and in_count.get(b, 0) > 1

    def _do_drop(edge: Tuple[str, str]) -> None:
        a, b = edge
        removed.add(edge)
        out_count[a] -= 1
        in_count[b] -= 1

    for edge, _f in potential:
        if edge in removed:
            continue
        src, tgt = edge
        if _can_drop(edge):
            _do_drop(edge)
            concurrent_pairs.add(frozenset((src, tgt)))
        else:
            # Guard veto: demote the pair and drop the opposite
            # direction instead (Java removes dfgp[tgt][src]).
            concurrent_pairs.discard(frozenset((src, tgt)))
            reverse = (tgt, src)
            if (
                reverse in dfg
                and reverse not in removed
                and _can_drop(reverse)
            ):
                _do_drop(reverse)

    pdfg: DFG = {
        (a, b): f for (a, b), f in dfg.items() if (a, b) not in removed
    }
    return ConcurrencyResult(pdfg=pdfg, concurrent_pairs=concurrent_pairs)
