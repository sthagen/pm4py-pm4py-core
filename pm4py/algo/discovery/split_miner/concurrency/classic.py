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
"""Classic Split Miner concurrency oracle.

Two activities ``a`` and ``b`` are concurrent when they appear as both
``a -> b`` and ``b -> a`` in the DFG, are not a short-loop pair, and the
bidirectional frequencies are roughly balanced (imbalance under epsilon).

When an imbalanced bidirectional pair is detected the less frequent
direction is dropped instead and concurrency is *not* recorded.

Both pruning operations are performed greedily in ascending-frequency
order and respect a connectedness invariant inherited from the
reference Java implementation: an edge is only dropped when its source
retains another outgoing edge *and* its target retains another incoming
edge in the pruned DFG. When the favoured direction cannot be dropped
the algorithm falls back to dropping the opposite direction (if that is
itself removable) and demotes the pair from concurrent to sequential,
mirroring the behaviour of ``DirectlyFollowGraphPlus.removeEdge`` with
``ensureConnectedness=true``.
"""
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.concurrency.abc import ConcurrencyOracle
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.util import exec_utils


class Parameters(Enum):
    EPSILON = "split_miner_epsilon"


DEFAULT_EPSILON = 0.1


class ClassicConcurrencyOracle(ConcurrencyOracle):
    """Imbalance test on directly-follows frequencies, with a
    connectedness guard that prevents pruning from isolating any task.
    """

    @classmethod
    def apply(
            cls,
            dfg: DFG,
            traces: Optional[List[Any]],  # unused (kept to share signature)
            loops: LoopInfo,
            parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        eps = exec_utils.get_param_value(
            Parameters.EPSILON, parameters or {}, DEFAULT_EPSILON
        )

        # Live in/out degree per node in the working DFG. The oracle
        # mutates these counters as it drops edges so the connectedness
        # guard reflects intermediate state, exactly like Java's
        # incomings/outgoings maps.
        out_count: Dict[str, int] = {}
        in_count: Dict[str, int] = {}
        for (a, b) in dfg.keys():
            out_count[a] = out_count.get(a, 0) + 1
            in_count[b] = in_count.get(b, 0) + 1

        # Candidate drops, paired with their frequencies. For every
        # bidirectional pair both directions are queued when the pair is
        # balanced enough to be concurrent; when imbalanced only the
        # weaker direction is queued (and concurrency is not asserted).
        # ``pair_kind`` records whether each queued drop belongs to a
        # concurrent pair (``"par"``) or an imbalance demotion
        # (``"imb"``); this drives the bookkeeping that demotes
        # concurrency back to a sequence arc when a removal is vetoed by
        # the connectedness guard.
        candidates: List[Tuple[Tuple[str, str], int]] = []
        pair_kind: Dict[Tuple[str, str], str] = {}
        concurrent_pairs: Set[FrozenSet[str]] = set()
        seen: Set[FrozenSet[str]] = set()

        # Deterministic iteration: sorting up front keeps the set of
        # candidate pairs identical across runs regardless of dict
        # insertion order.
        for (a, b), f_ab in sorted(dfg.items()):
            if a == b:
                continue
            pair = frozenset((a, b))
            if pair in seen:
                continue
            seen.add(pair)

            f_ba = dfg.get((b, a), 0)
            if f_ab <= 0 or f_ba <= 0:
                continue
            if pair in loops.short_loops:
                continue

            denom = f_ab + f_ba
            imbalance = abs(f_ab - f_ba) / denom

            # Reference uses a strict comparison (Math.abs(score) <
            # parallelismsThreshold); a pair whose imbalance is exactly
            # epsilon is NOT concurrent.
            if imbalance < eps:
                concurrent_pairs.add(pair)
                candidates.append(((a, b), f_ab))
                candidates.append(((b, a), f_ba))
                pair_kind[(a, b)] = "par"
                pair_kind[(b, a)] = "par"
            else:
                drop = (a, b) if f_ab < f_ba else (b, a)
                drop_f = min(f_ab, f_ba)
                candidates.append((drop, drop_f))
                pair_kind[drop] = "imb"

        # Process candidate drops in ascending-frequency order so the
        # least informative arcs are challenged by the guard first
        # (matching Collections.sort on Java's DFGEdge).
        candidates.sort(key=lambda x: (x[1], x[0]))

        to_drop: Set[Tuple[str, str]] = set()

        def _can_drop(edge: Tuple[str, str]) -> bool:
            a, b = edge
            return out_count.get(a, 0) > 1 and in_count.get(b, 0) > 1

        def _do_drop(edge: Tuple[str, str]) -> None:
            a, b = edge
            to_drop.add(edge)
            out_count[a] -= 1
            in_count[b] -= 1

        for edge, _f in candidates:
            if edge in to_drop:
                continue
            if _can_drop(edge):
                _do_drop(edge)
                continue
            # Connectedness guard vetoed the drop. For concurrent pairs
            # this demotes the pair to a sequence arc: discard the pair
            # from ``concurrent_pairs`` and instead try to drop the
            # reverse direction (if it has not been dropped already and
            # the guard allows it).
            a, b = edge
            if pair_kind.get(edge) == "par":
                concurrent_pairs.discard(frozenset((a, b)))
                reverse = (b, a)
                if reverse in dfg and reverse not in to_drop and _can_drop(reverse):
                    _do_drop(reverse)
            # Imbalance drops vetoed by the guard simply stay in the
            # DFG; Java behaves the same way (the edge survives because
            # removing it would orphan a node).

        pdfg: DFG = {
            (a, b): f for (a, b), f in dfg.items() if (a, b) not in to_drop
        }
        return ConcurrencyResult(pdfg=pdfg, concurrent_pairs=concurrent_pairs)
